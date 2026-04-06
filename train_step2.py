"""
Step 2 Model Training
Stage A: stable vs patched (binary)
Stage B: patched → nerf/buff/rework + followup/correction 세분화

시계열 보정: StratifiedKFold(shuffle) 대신 walk-forward temporal split 사용
→ 미래 act 정보가 과거 검증에 누출되는 leakage 방지
"""

import pandas as pd
import numpy as np
import warnings
import argparse
import json
import os
warnings.filterwarnings("ignore")

from sklearn.preprocessing import OrdinalEncoder, LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import (classification_report, confusion_matrix,
                             balanced_accuracy_score)
from sklearn.utils.class_weight import compute_class_weight
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline as SkPipeline
import xgboost as xgb
import shap
import joblib
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ─── 레이블 매핑 ─────────────────────────────────────────────────────────────

def collapse_label(label):
    """
    세분화 레이블 → 학습 가능한 그룹으로 묶기
    방향(nerf/buff) × 컨텍스트(first/followup/rework) 기준

    병합 규칙:
      correction_buff → buff_followup  (과너프 후 복구 = 버프 추가 필요)
      correction_nerf → nerf_followup  (과버프 후 재조정 = 너프 추가 필요)
      nerf_pro        → nerf_rank      (샘플 4개, 학습 불가)
      buff_pro        → buff_rank      (샘플 5개, 학습 불가)
    → 최종 5클래스: nerf_rank / nerf_followup / buff_rank / buff_followup / rework
    """
    if label == "stable_balanced":  return "stable"
    if label == "stable_strong":    return "stable_strong"
    if label == "stable_weak":      return "stable_weak"
    if label == "stable_rank_only": return "stable_rank_only"
    if label == "stable":           return "stable"
    if label == "rework":           return "rework"
    # correction → followup 병합
    if label.startswith("correction_buff"): return "buff_followup"
    if label.startswith("correction_nerf"): return "nerf_followup"

    parts     = label.split("_")
    direction = parts[0]
    is_followup = label.endswith("followup")

    if direction == "nerf":
        return "nerf_followup" if is_followup else "nerf_rank"
    if direction == "buff":
        return "buff_followup" if is_followup else "buff_rank"

    return "other"


def stable_weight(label_collapsed):
    """
    stable_strong / stable_weak / stable_rank_only 는 노이즈 → 가중치 낮춤
    stable_rank_only: 버프가 아닌 설계 문제인 요원 → 패치 예측에 혼선 유발
    """
    if label_collapsed in ("stable_strong", "stable_weak", "stable_rank_only"):
        return 0.3
    return 1.0

# ─── 시계열 교차검증 ──────────────────────────────────────────────────────────

def temporal_cv_splits(act_idx_arr, n_splits=3, min_train_ratio=0.5):
    """
    Walk-forward temporal split.
    act_idx 순서를 보존해 미래 데이터 누출 방지.

    Returns list of (train_indices, val_indices) as numpy arrays.
    """
    acts = np.sort(np.unique(act_idx_arr))
    n    = len(acts)
    all_idx = np.arange(len(act_idx_arr))

    min_t     = max(int(n * min_train_ratio), 5)
    remaining = n - min_t
    fold_size = max(1, remaining // n_splits)

    splits = []
    for i in range(n_splits):
        train_end = min_t + i * fold_size
        val_end   = min(train_end + fold_size, n)
        if train_end >= n:
            break

        train_acts = acts[:train_end]
        val_acts   = acts[train_end:val_end]

        tr  = all_idx[np.isin(act_idx_arr, train_acts)]
        val = all_idx[np.isin(act_idx_arr, val_acts)]
        if len(tr) > 10 and len(val) > 3:
            splits.append((tr, val))

    return splits

# ─── 전처리 ──────────────────────────────────────────────────────────────────

CAT_COLS = [
    "vct_profile", "last_direction", "last_combined",
    "last_rank_verdict", "last_vct_verdict", "patch_streak_direction",
    "last_trigger_type",
]

DROP_COLS = [
    "agent", "act", "act_idx", "label",
    "vct_last_event_name",   # 표시용 문자열, 모델 피처 아님
    "label_direction", "label_skill", "label_trigger", "label_context",
    "label_has_rework", "label_group",
    "rank_vct_gap",      # NaN 30%
    "map_dep_score",     # raw 맵 의존도 → 모델이 오해석, 조건부 파생 피처로 대체
    "effective_map_dep", # in_rotation 곱해져 있어 이중 인코딩
    "last_combined",     # 방향 정보 없이 DUAL_MISS만으로는 버프/너프 맥락 모호
                         # dir_verdict_code + buff_miss_flag/nerf_miss_flag 로 대체
    # ── SHAP=0 피처 제거 (양 Stage 모두 기여 없음) ──────────────────────────────
    "buff_hit_flag", "nerf_hit_flag",          # hit/miss 비대칭: miss는 유효, hit은 무의미
    "map_specialist", "specialist_low_pr",      # 맵 전문 요원 플래그 신호 없음
    "geo_bonus",                                # 지오메트리 잠재 보너스 분산 없음
    "rank_dominant_flag",                       # design_rank_only 복사본, 둘 다 약함
    "low_kit_weak_signal",                      # 복합 이진 플래그, 변동성 없음
    "op_synergy",                               # 오퍼 시너지 요원 너무 적음
    "replaceable_low_pr",                       # 대체 가능성 × 픽률 플래그 상수
    "versatile_high_pr",                        # 구버전 이진 플래그
    "versatile_nerf_signal",                    # map_hhi × rank_pr 교차 — XGBoost가 원본 두 피처로 이미 학습, 중복
    "rank_low_unexpected",                      # rank_pr 실수값으로 흡수됨, SHAP 0.008로 기여 없음
    "map_versatility",                          # 맵 다양성 수치 분산 부족
    "vct_pr_post", "vct_wr_post",               # 표시용 누적 집계, 모델 피처 아님
    # 이진 임계값 교차 피처: 요원별 상수 → 시간 변동성 없음
    "heal_low_rank", "revive_low_rank",
    "cc_low_rank", "info_low_vct",
    "smoke_vct_dom", "smoke_low_vct",
    # design 분류 플래그: 모델 기여 0, 도메인 룰도 함께 완화
    "design_rank_only", "design_pro_only",
]

# Stage B 추가 제거 피처 (패치 유형 분류에 노이즈)
DROP_COLS_B = [
    "last_trigger_type",      # 레이블 생성 기준과 순환 의존 → Stage A 전용
    "acts_since_patch",       # 패치 압박 누적 타이밍 신호 → 유형과 무관
    "patch_streak_n",         # 연속 패치 횟수 → 패치 여부(Stage A) 신호
    "patch_streak_direction", # 방향 스트릭 → CAT 피처지만 유형 예측엔 노이즈
    "both_weak_signal",       # 버프 후보 이진 플래그 → Stage A 전용
    "skill_ceiling_score",       # 패치 가능성 신호 → Stage A 전용
    "skill_ceiling_x_vct_pr",   # skill_ceiling 파생 교차 피처 → Stage A 전용
    "skill_ceiling_x_vct_wr",
    "skill_ceiling_x_rank_wr",
    "kit_x_rank_pr",          # 킷 × 픽률 교차 → 패치 여부 신호, 유형 불필요
    "map_hhi",                # 맵 편중도 → 패치 타이밍 신호, 유형과 무관
]

def prepare(df, drop_extra=None):
    df = df.copy()
    df["label_collapsed"] = df["label"].apply(collapse_label)
    # vct_wr_last: VCT 데이터 없을 때 NaN → 50%으로 대체 (승률 기준값)
    if "vct_wr_last" in df.columns:
        df["vct_wr_last"] = df["vct_wr_last"].fillna(50.0)

    oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    for col in CAT_COLS:
        if col in df.columns:
            df[col] = oe.fit_transform(df[[col]])

    all_drops = DROP_COLS + (drop_extra or []) + ["label_collapsed"]
    feat_cols = [c for c in df.columns if c not in all_drops]
    return df, feat_cols

# ─── HPO ─────────────────────────────────────────────────────────────────────

def run_hpo(X, y, act_idx_arr, n_trials=60, noise_w=None):
    splits = temporal_cv_splits(act_idx_arr)
    n_cls  = len(np.unique(y))

    def objective(trial):
        params = dict(
            n_estimators     = trial.suggest_int("n_estimators", 80, 500),
            max_depth        = trial.suggest_int("max_depth", 2, 6),
            learning_rate    = trial.suggest_float("lr", 0.02, 0.3, log=True),
            subsample        = trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree = trial.suggest_float("colsample", 0.4, 1.0),
            min_child_weight = trial.suggest_int("min_child_weight", 1, 10),
            gamma            = trial.suggest_float("gamma", 0.0, 2.0),
            reg_alpha        = trial.suggest_float("reg_alpha", 1e-4, 5.0, log=True),
            reg_lambda       = trial.suggest_float("reg_lambda", 1e-4, 5.0, log=True),
            objective        = "binary:logistic" if n_cls == 2 else "multi:softmax",
            num_class        = n_cls if n_cls > 2 else None,
            eval_metric      = "logloss" if n_cls == 2 else "mlogloss",
            random_state     = 42, verbosity = 0,
        )
        if params["num_class"] is None:
            del params["num_class"]

        cw = compute_class_weight("balanced", classes=np.unique(y), y=y)
        sw = np.array([cw[yi] for yi in y])
        if noise_w is not None:
            sw = sw * noise_w

        scores = []
        for tr, val in splits:
            y_tr, y_val = y[tr], y[val]
            le_fold = LabelEncoder()
            y_tr_enc  = le_fold.fit_transform(y_tr)
            if not set(y_val).issubset(set(le_fold.classes_)):
                continue
            y_val_enc = le_fold.transform(y_val)

            n_cls_fold = len(le_fold.classes_)
            fp = {**params}
            if n_cls_fold <= 2:
                fp.pop("num_class", None)
                fp["objective"]   = "binary:logistic"
                fp["eval_metric"] = "logloss"
            else:
                fp["num_class"] = n_cls_fold

            m = xgb.XGBClassifier(**fp)
            m.fit(X[tr], y_tr_enc, sample_weight=sw[tr], verbose=False)
            preds = m.predict(X[val])
            scores.append(balanced_accuracy_score(y_val_enc, preds))

        return np.mean(scores) if scores else 0.0

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params, study.best_value


def train_eval(X, y, labels, best_params, stage_name, act_idx_arr, noise_w=None):
    n_cls  = len(np.unique(y))
    params = dict(
        **best_params,
        objective    = "binary:logistic" if n_cls == 2 else "multi:softmax",
        num_class    = n_cls if n_cls > 2 else None,
        eval_metric  = "logloss" if n_cls == 2 else "mlogloss",
        random_state = 42, verbosity = 0,
    )
    if params["num_class"] is None:
        del params["num_class"]
    if "lr" in params:
        params["learning_rate"] = params.pop("lr")
    if "colsample" in params:
        params["colsample_bytree"] = params.pop("colsample")

    cw = compute_class_weight("balanced", classes=np.unique(y), y=y)
    sw = np.array([cw[yi] for yi in y])
    if noise_w is not None:
        sw = sw * noise_w

    splits = temporal_cv_splits(act_idx_arr)
    oof = np.full(len(y), -1, dtype=int)

    for tr, val in splits:
        le_fold   = LabelEncoder()
        y_tr_enc  = le_fold.fit_transform(y[tr])
        n_cls_fold = len(le_fold.classes_)

        p = {**params}
        if n_cls_fold <= 2:
            p.pop("num_class", None)
            p["objective"]   = "binary:logistic"
            p["eval_metric"] = "logloss"
        else:
            p["num_class"] = n_cls_fold

        m = xgb.XGBClassifier(**p)
        m.fit(X[tr], y_tr_enc, sample_weight=sw[tr], verbose=False)
        pred_enc = m.predict(X[val])

        for vi, pe in zip(val, pred_enc):
            if pe < len(le_fold.classes_):
                oof[vi] = le_fold.classes_[pe]
            else:
                oof[vi] = y[vi]

    # 검증 범위 (OOF가 채워진 행만 평가)
    mask = oof >= 0
    y_eval   = y[mask]
    oof_eval = oof[mask]
    ba = balanced_accuracy_score(y_eval, oof_eval)

    # unique labels actually in eval set
    present = sorted(set(y_eval) | set(oof_eval))
    eval_labels = [labels[i] for i in present if i < len(labels)]

    print(f"\n[{stage_name}] balanced_accuracy (temporal OOF): {ba:.4f}  (eval_rows={mask.sum()}/{len(y)})")
    print(classification_report(y_eval, oof_eval,
                                labels=present, target_names=eval_labels,
                                zero_division=0))
    print("[혼동 행렬]")
    cm = pd.DataFrame(
        confusion_matrix(y_eval, oof_eval, labels=present),
        index=eval_labels, columns=eval_labels
    )
    print(cm.to_string())

    # 전체 데이터로 최종 모델
    model = xgb.XGBClassifier(**params)
    model.fit(X, y, sample_weight=sw)
    return model, oof, ba

# ─── LR 학습/평가 ─────────────────────────────────────────────────────────────

def train_eval_lr(X, y, labels, stage_name, act_idx_arr, noise_w=None):
    """LogisticRegression (StandardScaler 포함) — 소량 데이터 대안"""
    cw = compute_class_weight("balanced", classes=np.unique(y), y=y)
    sw = np.array([cw[yi] for yi in y])
    if noise_w is not None:
        sw = sw * noise_w

    splits = temporal_cv_splits(act_idx_arr)
    oof = np.full(len(y), -1, dtype=int)
    best_ba, best_C = 0.0, 1.0

    # C 후보 간단 탐색 (HPO 대신)
    for C in [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]:
        scores = []
        for tr, val in splits:
            pipe = SkPipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("lr", LogisticRegression(C=C, class_weight="balanced",
                                          max_iter=2000, solver="saga",
                                          random_state=42)),
            ])
            pipe.fit(X[tr], y[tr], lr__sample_weight=sw[tr])
            preds = pipe.predict(X[val])
            scores.append(balanced_accuracy_score(y[val], preds))
        mean_ba = np.mean(scores) if scores else 0.0
        if mean_ba > best_ba:
            best_ba, best_C = mean_ba, C

    # best C로 OOF 재평가
    for tr, val in splits:
        pipe = SkPipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(C=best_C, class_weight="balanced",
                                      max_iter=2000, solver="saga",
                                      random_state=42)),
        ])
        pipe.fit(X[tr], y[tr], lr__sample_weight=sw[tr])
        for vi, pred in zip(val, pipe.predict(X[val])):
            oof[vi] = pred

    mask = oof >= 0
    ba = balanced_accuracy_score(y[mask], oof[mask])
    present = sorted(set(y[mask]) | set(oof[mask]))
    eval_labels = [labels[i] for i in present if i < len(labels)]

    print(f"\n[LR {stage_name}] best C={best_C}  balanced_accuracy={ba:.4f}  (eval_rows={mask.sum()}/{len(y)})")
    print(classification_report(y[mask], oof[mask],
                                labels=present, target_names=eval_labels,
                                zero_division=0))

    # 전체 데이터로 최종 모델
    final = SkPipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(C=best_C, class_weight="balanced",
                                  max_iter=2000, solver="saga",
                                  random_state=42)),
    ])
    final.fit(X, y, lr__sample_weight=sw)
    return final, oof, ba


# ─── SHAP ────────────────────────────────────────────────────────────────────

def loao_cv(df, feat_cols, stable_types, stage="A"):
    """
    Leave-One-Agent-Out CV
    요원 하나씩 통째로 빼고 나머지로 학습 → 빠진 요원 예측
    "특정 요원 패턴 암기 vs 일반 패턴 학습" 검증용
    """
    agents   = df["agent"].unique()
    scores   = []
    failures = []

    for agent in sorted(agents):
        train_df = df[df["agent"] != agent].copy()
        test_df  = df[df["agent"] == agent].copy()

        if stage == "A":
            y_train = (~train_df["label_collapsed"].isin(stable_types)).astype(int).values
            y_test  = (~test_df["label_collapsed"].isin(stable_types)).astype(int).values
        else:
            patched_train = train_df[~train_df["label_collapsed"].isin(stable_types)]
            patched_test  = test_df[~test_df["label_collapsed"].isin(stable_types)]
            if len(patched_test) == 0:
                continue
            all_cats = sorted(df[~df["label_collapsed"].isin(stable_types)]["label_collapsed"].unique())
            cat_enc  = {l: i for i, l in enumerate(all_cats)}
            y_train  = patched_train["label_collapsed"].map(cat_enc).values
            y_test   = patched_test["label_collapsed"].map(cat_enc).values
            train_df = patched_train
            test_df  = patched_test

        if len(np.unique(y_train)) < 2 or len(y_test) == 0:
            continue

        X_train = train_df[feat_cols].values.astype(np.float32)
        X_test  = test_df[feat_cols].values.astype(np.float32)

        cw_classes = np.unique(y_train)
        cw = compute_class_weight("balanced", classes=cw_classes, y=y_train)
        cw_dict = dict(zip(cw_classes, cw))
        sw = np.array([cw_dict[yi] for yi in y_train])

        n_cls = len(np.unique(y_train))
        params = dict(
            n_estimators=100, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="binary:logistic" if n_cls == 2 else "multi:softmax",
            eval_metric="logloss" if n_cls == 2 else "mlogloss",
            random_state=42, verbosity=0,
        )
        if n_cls > 2:
            params["num_class"] = n_cls

        # test 클래스가 train에 없으면 skip
        if not set(np.unique(y_test)).issubset(set(np.unique(y_train))):
            failures.append(agent)
            continue

        m = xgb.XGBClassifier(**params)
        le = LabelEncoder()
        y_tr_enc = le.fit_transform(y_train)
        m.fit(X_train, y_tr_enc, sample_weight=sw, verbose=False)

        y_pred_enc = m.predict(X_test)
        y_test_enc = le.transform(y_test)
        ba = balanced_accuracy_score(y_test_enc, y_pred_enc)
        scores.append((agent, ba, len(y_test)))

    print(f"\n[LOAO-CV Stage {stage}]  요원별 balanced_accuracy:")
    print(f"  {'요원':<12} {'BA':>6}  {'샘플':>4}")
    print(f"  {'-'*26}")
    for ag, ba, n in sorted(scores, key=lambda x: x[1]):
        bar = "#" * int(ba * 20)
        print(f"  {ag:<12} {ba:>6.3f}  ({n:>2}행)  {bar}")
    if scores:
        mean_ba = np.mean([s[1] for s in scores])
        print(f"  {'평균':<12} {mean_ba:>6.3f}")
    if failures:
        print(f"  [skip] 테스트 클래스 미존재: {failures}")
    return scores


def shap_top(model, X, feat_cols, title, n=15, save_path=None):
    exp  = shap.TreeExplainer(model)
    sv   = exp.shap_values(X)
    if isinstance(sv, list):
        mean_abs = np.mean([np.abs(s) for s in sv], axis=0).mean(axis=0)
    else:
        mean_abs = np.abs(sv).mean(axis=(0, 2)) if sv.ndim == 3 else np.abs(sv).mean(axis=0)
    imp = pd.Series(mean_abs, index=feat_cols).sort_values(ascending=False)
    print(f"\n[SHAP Top {n} - {title}]")
    print(imp.head(n).round(4).to_string())
    print(f"\n[SHAP Bottom (약신호) - {title}]")
    print(imp.tail(20).round(4).to_string())
    if save_path:
        imp.to_csv(save_path, header=["shap_mean_abs"])
    return imp

# ─── 메인 ────────────────────────────────────────────────────────────────────

PARAMS_FILE = "best_params.json"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="HPO 없이 저장된 파라미터로 CV만 실행 (피처 실험용)")
    parser.add_argument("--hpo", action="store_true",
                        help="강제로 HPO 재실행 후 파라미터 저장")
    args = parser.parse_args()

    print("=" * 65)
    if args.fast:
        print("Step 2 Model Training [빠른 모드 - 저장된 파라미터 사용]")
    else:
        print("Step 2 Model Training (Walk-Forward Temporal CV)")
    print("=" * 65 + "\n")

    raw_csv = pd.read_csv("step2_training_data.csv")
    df, feat_cols_a = prepare(raw_csv)
    _, feat_cols_b  = prepare(raw_csv, drop_extra=DROP_COLS_B)

    # B안: stable_strong / stable_weak 학습 제외
    # "패치 기록 없음 + 수치 극단" 케이스는 노이즈 (같은 feature에 다른 레이블 유발)
    noise_labels = {"stable_strong", "stable_weak"}
    n_before = len(df)
    df = df[~df["label_collapsed"].isin(noise_labels)].reset_index(drop=True)
    print(f"전체: {n_before}행 → stable_strong/weak 제외 후 {len(df)}행")
    print(f"Stage A 피처: {len(feat_cols_a)}개 / Stage B 피처: {len(feat_cols_b)}개")
    print("\n[collapsed 레이블 분포]")
    print(df["label_collapsed"].value_counts().to_string())

    X_all       = df[feat_cols_a].values.astype(np.float32)
    act_idx_all = df["act_idx"].values

    # ================================================================
    # Stage A: stable vs patched
    # ================================================================
    print("\n" + "-"*50)
    print("Stage A: stable vs patched")
    print("-"*50)

    stable_types = ["stable", "stable_rank_only"]
    ya = (~df["label_collapsed"].isin(stable_types)).astype(int).values

    # 데이터 부족 요원 가중치 할인: n_rank_acts < 8이면 비례적으로 줄임
    # acts_since=99 (패치 이력 없음) + 데이터 적음 → 모델 학습에 혼란 유발
    if "n_rank_acts" in df.columns:
        _n_acts = df["n_rank_acts"].fillna(99).values.astype(float)
        _no_patch = (df["acts_since_patch"].fillna(99).values.astype(float) >= 99)
        data_quality_w = np.where(
            _no_patch & (_n_acts < 8),
            np.clip(_n_acts / 8.0, 0.2, 1.0),
            1.0
        )
    else:
        data_quality_w = None
    noise_w = data_quality_w  # element-wise multiplier on class weights

    n_stable   = (ya == 0).sum()
    n_patched  = (ya == 1).sum()
    n_rankonly = (df["label_collapsed"] == "stable_rank_only").sum()
    print(f"  stable: {n_stable - n_rankonly}  stable_rank_only: {n_rankonly}  patched: {n_patched}")

    # HPO: --fast면 저장된 파라미터 사용, 없으면 새로 실행
    saved_params = {}
    if os.path.exists(PARAMS_FILE):
        with open(PARAMS_FILE) as f:
            saved_params = json.load(f)

    use_saved_a = args.fast and "stage_a" in saved_params and not args.hpo
    if use_saved_a:
        params_a = saved_params["stage_a"]
        print(f"  [빠른 모드] 저장된 Stage A 파라미터 사용")
    else:
        print("  HPO 중...")
        params_a, best_a = run_hpo(X_all, ya, act_idx_all, n_trials=60, noise_w=noise_w)
        print(f"  best balanced_accuracy: {best_a:.4f}")

    model_a_xgb, oof_a_xgb, ba_a_xgb = train_eval(
        X_all, ya, ["stable", "patched"], params_a, "Stage A (XGB)", act_idx_all, noise_w=noise_w
    )
    model_a_lr, oof_a_lr, ba_a_lr = train_eval_lr(
        X_all, ya, ["stable", "patched"], "Stage A", act_idx_all, noise_w=noise_w
    )
    if ba_a_lr > ba_a_xgb:
        model_a, ba_a = model_a_lr, ba_a_lr
        print(f"\n  [채택] Stage A: LR ({ba_a_lr:.4f} > {ba_a_xgb:.4f})")
    else:
        model_a, ba_a = model_a_xgb, ba_a_xgb
        print(f"\n  [채택] Stage A: XGB ({ba_a_xgb:.4f} >= {ba_a_lr:.4f})")
        shap_top(model_a_xgb, X_all, feat_cols_a, "Stage A (stable vs patched)", save_path="shap_importance_a.csv")
    joblib.dump(model_a, "step2_model_a.pkl")

    # Stage A 파라미터 저장 (--fast가 아닐 때만)
    if not args.fast or args.hpo:
        saved_params["stage_a"] = params_a

    # ================================================================
    # Stage B: patched 케이스 내 세분류
    # ================================================================
    print("\n" + "-"*50)
    print("Stage B: patched 유형 분류")
    print("-"*50)

    patched_df   = df[~df["label_collapsed"].isin(stable_types)].copy()
    X_b          = patched_df[feat_cols_b].values.astype(np.float32)
    act_idx_b    = patched_df["act_idx"].values
    label_b_cats = sorted(patched_df["label_collapsed"].unique())
    label_b_enc  = {l: i for i, l in enumerate(label_b_cats)}
    yb           = patched_df["label_collapsed"].map(label_b_enc).values

    print(f"  케이스: {len(patched_df)}  /  클래스: {len(label_b_cats)}")
    print(f"  클래스: {label_b_cats}")

    small = [l for l in label_b_cats if (patched_df["label_collapsed"] == l).sum() < 4]
    if small:
        print(f"  [경고] 케이스 4개 미만 클래스: {small}")

    use_saved_b = args.fast and "stage_b" in saved_params and not args.hpo
    if use_saved_b:
        params_b = saved_params["stage_b"]
        print(f"  [빠른 모드] 저장된 Stage B 파라미터 사용")
    else:
        print("  HPO 중...")
        params_b, best_b = run_hpo(X_b, yb, act_idx_b, n_trials=60)
        print(f"  best balanced_accuracy: {best_b:.4f}")

    model_b_xgb, oof_b_xgb, ba_b_xgb = train_eval(
        X_b, yb, label_b_cats, params_b, "Stage B (XGB)", act_idx_b
    )
    model_b_lr, oof_b_lr, ba_b_lr = train_eval_lr(
        X_b, yb, label_b_cats, "Stage B", act_idx_b
    )
    if ba_b_lr > ba_b_xgb:
        model_b, ba_b = model_b_lr, ba_b_lr
        print(f"\n  [채택] Stage B: LR ({ba_b_lr:.4f} > {ba_b_xgb:.4f})")
    else:
        model_b, ba_b = model_b_xgb, ba_b_xgb
        print(f"\n  [채택] Stage B: XGB ({ba_b_xgb:.4f} >= {ba_b_lr:.4f})")
        shap_top(model_b_xgb, X_b, feat_cols_b, "Stage B (patch type)", save_path="shap_importance_b.csv")
    joblib.dump(model_b, "step2_model_b.pkl")

    # 파라미터 저장
    if not args.fast or args.hpo:
        saved_params["stage_b"] = params_b
        with open(PARAMS_FILE, "w") as f:
            json.dump(saved_params, f, indent=2)
        print(f"\n  파라미터 저장: {PARAMS_FILE}")

    # ================================================================
    # 현재 시점 예측 (최신 액트 기준)
    # ================================================================
    print("\n" + "-"*50)
    print("현재 시점 예측 (최신 액트 기준)")
    print("-"*50)

    latest = df.loc[df.groupby("agent")["act_idx"].idxmax()].copy()
    X_now_a = latest[feat_cols_a].values.astype(np.float32)
    X_now_b = latest[feat_cols_b].values.astype(np.float32)

    prob_patch = model_a.predict_proba(X_now_a)[:, 1]
    prob_b_all = model_b.predict_proba(X_now_b)   # (n_agents, n_classes)
    pred_b_raw = model_b.predict(X_now_b)
    pred_type  = list([label_b_cats[i] for i in pred_b_raw])
    pred_b_conf = prob_b_all.max(axis=1).copy()
    prob_patch  = prob_patch.copy()

    # ── 도메인 규칙 보정 레이어 ────────────────────────────────────────────────
    # ML 모델은 방향(buff/nerf) 구분에서 데이터 부족으로 혼동이 발생하므로
    # 피처 기반 hard rule로 방향과 신뢰도를 보정

    for i, row in latest.reset_index(drop=True).iterrows():
        buff_miss  = float(row.get("buff_miss_flag", 0) or 0)
        nerf_miss  = float(row.get("nerf_miss_flag", 0) or 0)
        buff_hit   = float(row.get("buff_hit_flag", 0) or 0)
        nerf_hit   = float(row.get("nerf_hit_flag", 0) or 0)
        rank_only  = float(row.get("design_rank_only", 0) or 0)
        pro_only   = float(row.get("design_pro_only", 0) or 0)
        both_weak  = float(row.get("both_weak_signal", 0) or 0)
        rank_pr    = float(row.get("rank_pr", 0) or 0)
        vct_pr     = float(row.get("vct_pr_last", 0) or 0)

        pt = pred_type[i]

        # 규칙 1: 버프 후 MISS인데 nerf 방향 예측 → buff_followup으로 교정
        # 버프가 효과 없으면 더 강한 버프가 필요한 것이지 너프가 아님
        if buff_miss and pt.startswith("nerf") and "correction" not in pt:
            pred_type[i] = "buff_followup"

        # 규칙 2: 너프 후 MISS인데 buff 방향 예측 → nerf_followup으로 교정
        if nerf_miss and pt.startswith("buff") and "correction" not in pt:
            pred_type[i] = "nerf_followup"

        # 규칙 3: 설계상 랭크 전용 요원(레이나, 아이소)이 랭크에서 건재 → p_patch 억제
        # VCT 저픽은 설계 문제이지 패치 신호가 아님. 랭크 픽률이 정상이면 stable
        if rank_only and rank_pr > 2.5:
            prob_patch[i] *= 0.35

        # 규칙 4: both_weak_signal=1인데 pro_only 설계도 rank_only 설계도 아닌 요원
        # + 마지막 패치가 버프 방향이었으나 효과 부족(MISS 또는 FAIL)
        # → 두 도메인 모두 낮음은 강한 버프 신호 → p_patch 소폭 상향
        dir_code = float(row.get("dir_verdict_code", 0) or 0)
        if both_weak and not rank_only and not pro_only and dir_code > 0:
            prob_patch[i] = min(1.0, prob_patch[i] * 1.3)

    # Stage A 임계값 0.35: 요루처럼 Stage B가 명확하게 패치 유형을 가리키는 경우 포착
    THRESHOLD = 0.35
    pred_a_adj = (prob_patch >= THRESHOLD).astype(int)

    latest["p_patch"]    = prob_patch
    latest["patch_type"] = pred_type
    latest["type_conf"]  = pred_b_conf
    latest["final_pred"] = np.where(pred_a_adj == 1, latest["patch_type"], "stable")

    show = latest[["agent","act","rank_pr","vct_pr_last",
                   "p_patch","patch_type","type_conf","final_pred"]].sort_values("p_patch", ascending=False)
    print(show.to_string(index=False))

    # 저장
    joblib.dump({"model_a": model_a, "model_b": model_b,
                 "feat_cols_a": feat_cols_a, "feat_cols_b": feat_cols_b,
                 "label_b_cats": label_b_cats},
                "step2_pipeline.pkl")
    print("\n저장: step2_model_a.pkl / step2_model_b.pkl / step2_pipeline.pkl")
    print(f"\nStage A balanced_accuracy: {ba_a:.4f}")
    print(f"Stage B balanced_accuracy: {ba_b:.4f}")

    # ================================================================
    # Leave-One-Agent-Out CV
    # ================================================================
    print("\n" + "="*50)
    print("Leave-One-Agent-Out CV (일반화 능력 검증)")
    print("="*50)
    loao_cv(df, feat_cols_a, stable_types, stage="A")
    loao_cv(df, feat_cols_b, stable_types, stage="B")

if __name__ == "__main__":
    main()
