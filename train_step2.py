"""
Step 2 Model Training
단일 5-class XGBoost: stable / mild_nerf / strong_nerf / mild_buff / strong_buff

시계열 보정: walk-forward temporal split 사용
→ 미래 act 정보가 과거 검증에 누출되는 leakage 방지
"""

import pandas as pd
import numpy as np
import warnings
import argparse
import json
import os
warnings.filterwarnings("ignore")

SEED = 42  # --seed 인자로 덮어씀 (main() 진입 후)

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

try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except ImportError:
    HAS_SMOTE = False

# ─── 레이블 ──────────────────────────────────────────────────────────────────

# 5-class 순서 (ordinal)
LABEL_ORDER = ["strong_buff", "mild_buff", "stable", "mild_nerf", "strong_nerf"]

def collapse_label(label):
    """구버전 레이블 → 5-class 정규화 (CSV 호환용)"""
    if label in LABEL_ORDER:
        return label
    # 구버전 매핑
    if label in ("nerf_followup", "correction_nerf"):       return "strong_nerf"
    if label in ("nerf_rank", "nerf_watch", "nerf_pro"):    return "mild_nerf"
    if label in ("buff_followup", "correction_buff",
                 "rework"):                                  return "strong_buff"
    if label in ("buff_rank", "buff_watch", "buff_pro"):    return "mild_buff"
    return "stable"

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
    "last_direction", "patch_streak_direction", "last_trigger_type",
]

# ── 공통 드롭 (메타/누출/SHAP=0 양쪽) ──────────────────────────────────────
DROP_COLS_COMMON = [
    # 메타 컬럼
    "agent", "act", "act_idx", "label", "horizon",
    "vct_last_event_name",
    "label_direction", "label_skill", "label_trigger", "label_context",
    "label_has_rework", "label_group",
    "rank_vct_gap",
    "map_dep_score", "effective_map_dep",
    "last_combined",

    # 표시용 / 미래 누수 컬럼
    "vct_pr_post", "vct_wr_post",
    "rank_pr_t+1", "rank_wr_t+1",

    # 요원별 고정 상수 (시간 변동 없음)
    "agent_pr_baseline",
    "pr_vs_baseline",
    "pr_wr_gap",

    # SHAP=0 (양쪽 공통)
    "buff_hit_flag", "nerf_hit_flag",
    "buff_hit_wr_weak", "nerf_hit_wr_strong",
    "buff_miss_wr_weak", "nerf_miss_wr_strong",
    "map_specialist", "specialist_low_pr",
    "geo_bonus", "op_synergy",
    "rank_dominant_flag", "low_kit_weak_signal",
    "replaceable_low_pr", "versatile_high_pr", "versatile_nerf_signal",
    "rank_low_unexpected",
    "map_versatility",
    "rank_pr_rel_meta", "rank_pr_zscore",

    # util_*_rank_pr_ratio: 0/1 이진 → has_* 와 동일, 둘 다 SHAP=0
    "has_smoke", "has_cc", "has_info", "has_mobility",
    "has_heal", "has_revive", "has_flash", "has_blind",
    "high_value_smoke", "high_value_cc",
    "util_smoke_rank_pr_ratio", "util_cc_rank_pr_ratio",
    "util_info_rank_pr_ratio", "util_mobility_rank_pr_ratio",
    "util_heal_rank_pr_ratio", "util_revive_rank_pr_ratio",
    "util_flash_rank_pr_ratio", "util_blind_rank_pr_ratio",

    # VCT 교차 피처 SHAP=0
    "vct_pr_excess_x_rank_wr",

    # 중복/저신호 피처
    "patch_streak",
    "rank_pr_local_peak", "rank_pr_peak",
    "last_rank_verdict", "last_vct_verdict",
    "n_rank_acts",
    "overshoot_flag", "correction_risk_flag",
    "last_max_skill_w",
    "both_weak_signal",
    "heal_low_rank", "revive_low_rank", "cc_low_rank", "info_low_vct",
    "smoke_vct_dom", "smoke_low_vct",
    "design_rank_only", "design_pro_only",

    # Phase 4 스킬 피처: SHAP=0 (요원별 고정값)
    "sig_creds", "sig_charges", "sig_stat_count",
    "ult_points", "total_skill_cost",
    "sig_cooldown_val", "sig_duration_val", "sig_damage_val",
    "has_cooldown_sig", "has_damage_sig", "skill_stat_count_total",

    # 기타
    "pro_dominant_flag", "agent_tier_score",
    "patch_streak_direction",
    "recent_buff_fail_count",

    # SHAP=0 (양쪽 공통)
    "vct_profile",
    "buff_miss_flag", "nerf_miss_flag",
    "pr_above_baseline",
    "pr_buff_signal",
    "vct_above_hist_avg",
    "buff_context",
    "correction_buff_signal",

    # 중복/저신호 추가 드롭
    "rank_wr_vs50",
    "dir_verdict_code",
    "last_direction",

    # v3 2D 리팩터에서 제거/대체된 피처
    "pr_nerf_signal",
    "vct_nerf_signal",
    # 구버전 사분면 (v1~v2)
    "rank_q1_nerf", "rank_q2_niche_op", "rank_q3_buff", "rank_q4_fandom",
    "vct_q1_nerf", "vct_q2_niche", "vct_q3_irrelevant",
    "dual_nerf", "vct_dominance", "vct_rank_divergence", "vct_high_rank_low",
    "vct_pr_x_rank_wr", "rank_pr_x_rank_wr",

    # v3 SHAP < 0.02 (양쪽 공통)
    "vct_nerf_2d",              # A=0.000, B=0.000
    "vct_buff_2d",              # A=0.011, B=0.000
    "vct_excess_x_wr",          # A=0.000, B=0.000
    "rank_fandom_2d",           # A=0.010, B=0.000
    "rank_only_nerf",           # A=0.005, B=0.018
    "cross_nerf_2d",            # A=0.015, B=0.006
    "correction_nerf_signal",   # A=0.000, B=0.000
    "nerf_context",             # A=0.000, B=0.000
    "mobility_rank_dom",        # A=0.008, B=0.000
    "vct_low_unexpected",       # A=0.008, B=0.000
    "wr_nerf_signal",           # A=0.016, B=0.013
    "patch_streak_n",           # A=0.011, B=0.010
    "n_buff_patches",           # A=0.004, B=0.019
    "agent_complexity",         # A=0.012, B=0.007
    "agent_team_synergy",       # A=0.013, B=0.019
    "map_explains_vct_drop",    # A=0.000, B=0.000
    "top_map_in_rotation",      # A=0.000, B=0.000
]

# ── Stage A 전용 드롭 (Stage A에서만 SHAP ≈ 0, Stage B에서는 유효) ──────────
DROP_COLS_A_ONLY = [
    "geo_synergy",              # A=0.006
    "vct_pr_peak_all",          # A=0.005
    "n_nerf_patches",           # A=0.010
    "n_total_patches",          # A=0.012
    # vct_data_lag: A=0.000이지만 B=SHAP#1(0.477) → A에서만 드롭
    "vct_data_lag",             # A=0.000
]

# ── Stage B 전용 드롭 (Stage B에서만 SHAP ≈ 0, Stage A에서는 유효) ──────────
DROP_COLS_B_ONLY = [
    "vct_pr_avg",               # B=0.000
    "kit_score",                # B=0.000
    "recent_dual_miss_count",   # B=0.000
    # map_hhi: B=0.000이지만 맵 종속 요원 판별에 Stage A에서 유효 가능
    "map_hhi",                  # B=0.000
]

# 하위 호환: 기존 코드에서 DROP_COLS 참조 시
DROP_COLS = list(set(DROP_COLS_COMMON) | set(DROP_COLS_A_ONLY) | set(DROP_COLS_B_ONLY))


def prepare(df):
    """
    전처리 후 Stage A/B 각각의 피처 목록을 반환.
    Returns: (df, feat_cols_a, feat_cols_b)
    """
    df = df.copy()
    df["label_collapsed"] = df["label"].apply(collapse_label)
    if "vct_wr_last" in df.columns:
        df["vct_wr_last"] = df["vct_wr_last"].fillna(50.0)

    oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    for col in CAT_COLS:
        if col in df.columns:
            df[col] = oe.fit_transform(df[[col]])

    meta_drops = {"label_collapsed"}
    drops_a = set(DROP_COLS_COMMON) | set(DROP_COLS_A_ONLY) | meta_drops
    drops_b = set(DROP_COLS_COMMON) | set(DROP_COLS_B_ONLY) | meta_drops
    feat_cols_a = [c for c in df.columns if c not in drops_a]
    feat_cols_b = [c for c in df.columns if c not in drops_b]
    return df, feat_cols_a, feat_cols_b

# ─── HPO ─────────────────────────────────────────────────────────────────────

def run_hpo(X, y, act_idx_arr, n_trials=60, noise_w=None, use_smote=False):
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
            random_state     = SEED, verbosity = 0,
        )
        if params["num_class"] is None:
            del params["num_class"]

        scores = []
        for tr, val in splits:
            y_tr, y_val = y[tr], y[val]
            X_tr = X[tr].copy()

            # SMOTE: train fold만 오버샘플링 (val은 원본 분포 유지)
            if use_smote and HAS_SMOTE and len(np.unique(y_tr)) >= 2:
                min_cls_n = int(np.bincount(y_tr).min())
                k = min(3, min_cls_n - 1)
                if k >= 1:
                    # SMOTE는 NaN 불허 → median imputation 후 적용
                    from sklearn.impute import SimpleImputer as _SI
                    _imp = _SI(strategy="median")
                    X_tr = _imp.fit_transform(X_tr)
                    sm = SMOTE(random_state=SEED, k_neighbors=k)
                    X_tr, y_tr = sm.fit_resample(X_tr, y_tr)

            cw = compute_class_weight("balanced", classes=np.unique(y_tr), y=y_tr)
            sw_tr = np.array([cw[yi] for yi in y_tr])
            if noise_w is not None and not use_smote:
                # noise_w는 원본 인덱스 기준 → SMOTE 사용 시 무의미
                sw_tr = sw_tr * noise_w[tr[:len(sw_tr)]]

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
            m.fit(X_tr, y_tr_enc, sample_weight=sw_tr, verbose=False)
            preds = m.predict(X[val])
            scores.append(balanced_accuracy_score(y_val_enc, preds))

        return np.mean(scores) if scores else 0.0

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=SEED))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return study.best_params, study.best_value


def train_eval(X, y, labels, best_params, stage_name, act_idx_arr, noise_w=None, use_smote=False):
    n_cls  = len(np.unique(y))
    params = dict(
        **best_params,
        objective    = "binary:logistic" if n_cls == 2 else "multi:softmax",
        num_class    = n_cls if n_cls > 2 else None,
        eval_metric  = "logloss" if n_cls == 2 else "mlogloss",
        random_state = SEED, verbosity = 0,
    )
    if params["num_class"] is None:
        del params["num_class"]
    if "lr" in params:
        params["learning_rate"] = params.pop("lr")
    if "colsample" in params:
        params["colsample_bytree"] = params.pop("colsample")

    splits = temporal_cv_splits(act_idx_arr)
    oof = np.full(len(y), -1, dtype=int)

    for tr, val in splits:
        y_tr_raw = y[tr]
        X_tr     = X[tr].copy()

        # SMOTE: train fold만 오버샘플링 (NaN → median impute 선적용)
        if use_smote and HAS_SMOTE and len(np.unique(y_tr_raw)) >= 2:
            min_cls_n = int(np.bincount(y_tr_raw).min())
            k = min(3, min_cls_n - 1)
            if k >= 1:
                from sklearn.impute import SimpleImputer as _SI
                X_tr = _SI(strategy="median").fit_transform(X_tr)
                sm = SMOTE(random_state=SEED, k_neighbors=k)
                X_tr, y_tr_raw = sm.fit_resample(X_tr, y_tr_raw)

        cw_fold = compute_class_weight("balanced", classes=np.unique(y_tr_raw), y=y_tr_raw)
        sw_fold = np.array([cw_fold[yi] for yi in y_tr_raw])
        if noise_w is not None and not use_smote:
            sw_fold = sw_fold * noise_w[tr[:len(sw_fold)]]

        le_fold   = LabelEncoder()
        y_tr_enc  = le_fold.fit_transform(y_tr_raw)
        n_cls_fold = len(le_fold.classes_)

        p = {**params}
        if n_cls_fold <= 2:
            p.pop("num_class", None)
            p["objective"]   = "binary:logistic"
            p["eval_metric"] = "logloss"
        else:
            p["num_class"] = n_cls_fold

        m = xgb.XGBClassifier(**p)
        m.fit(X_tr, y_tr_enc, sample_weight=sw_fold, verbose=False)
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

    # 전체 데이터로 최종 모델 (SMOTE 적용 시 전체에도 오버샘플링)
    X_final, y_final = X, y
    if use_smote and HAS_SMOTE and len(np.unique(y)) >= 2:
        min_cls_n = int(np.bincount(y).min())
        k = min(3, min_cls_n - 1)
        if k >= 1:
            from sklearn.impute import SimpleImputer as _SI
            X_imp = _SI(strategy="median").fit_transform(X)
            sm = SMOTE(random_state=SEED, k_neighbors=k)
            X_final, y_final = sm.fit_resample(X_imp, y)
    cw_fin = compute_class_weight("balanced", classes=np.unique(y_final), y=y_final)
    sw_fin = np.array([cw_fin[yi] for yi in y_final])
    if noise_w is not None and not use_smote:
        sw_fin = sw_fin * noise_w

    model = xgb.XGBClassifier(**params)
    model.fit(X_final, y_final, sample_weight=sw_fin)
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
                                          random_state=SEED)),
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
                                      random_state=SEED)),
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
                                  random_state=SEED)),
    ])
    final.fit(X, y, lr__sample_weight=sw)
    return final, oof, ba


# ─── Stage A 전용: train-only 언더샘플링 ─────────────────────────────────────

def train_eval_stage_a(df_full: "pd.DataFrame", feat_cols: list, params: dict):
    """
    Stage A (stable vs patched) 학습 및 평가.

    핵심: 언더샘플링을 train split에만 적용, val은 원본 분포로 평가.
    → BA가 실제 서빙 분포(stable 58%, patched 42%)를 반영.
    """
    df_full = df_full.copy().reset_index(drop=True)
    df_full["_label_a"] = (df_full["label_collapsed"] != "stable").astype(int)

    act_idx_arr = df_full["act_idx"].values
    splits      = temporal_cv_splits(act_idx_arr)
    oof         = np.full(len(df_full), -1, dtype=int)

    for tr_idx, val_idx in splits:
        tr_df = df_full.iloc[tr_idx].copy()

        # ── train split만 1:1 언더샘플링 ─────────────────────────────────────
        tr_patched = tr_df[tr_df["_label_a"] == 1]
        tr_stable  = tr_df[tr_df["_label_a"] == 0]
        n_pat      = len(tr_patched)
        tr_stable_s = tr_stable.sample(n=min(n_pat, len(tr_stable)), random_state=SEED)
        tr_bal      = pd.concat([tr_stable_s, tr_patched]).sample(frac=1, random_state=SEED)

        y_tr = tr_bal["_label_a"].values
        X_tr = tr_bal[feat_cols].values.astype(np.float32)

        # val은 원본 분포 그대로
        val_df = df_full.iloc[val_idx]
        y_val  = val_df["_label_a"].values
        X_val  = val_df[feat_cols].values.astype(np.float32)

        cw = compute_class_weight("balanced", classes=np.unique(y_tr), y=y_tr)
        sw = np.array([cw[yi] for yi in y_tr])

        n_cls = len(np.unique(y_tr))
        p = dict(**params)
        if "lr" in p:      p["learning_rate"]    = p.pop("lr")
        if "colsample" in p: p["colsample_bytree"] = p.pop("colsample")
        p.update(dict(
            objective   = "binary:logistic",
            eval_metric = "logloss",
            random_state = SEED, verbosity = 0,
        ))
        p.pop("num_class", None)

        m = xgb.XGBClassifier(**p)
        m.fit(X_tr, y_tr, sample_weight=sw, verbose=False)
        preds = m.predict(X_val)
        for vi, pred in zip(val_idx, preds):
            oof[vi] = pred

    mask     = oof >= 0
    y_true   = df_full["_label_a"].values[mask]
    y_pred   = oof[mask]
    ba       = balanced_accuracy_score(y_true, y_pred)
    label_a_cats = ["stable", "patched"]

    print(f"\n[Stage A XGB - train-only undersampling]  BA: {ba:.4f}  (eval_rows={mask.sum()}/{len(df_full)})")
    print(classification_report(y_true, y_pred,
                                labels=[0, 1], target_names=label_a_cats, zero_division=0))
    print("[혼동 행렬]")
    cm = pd.DataFrame(confusion_matrix(y_true, y_pred, labels=[0, 1]),
                      index=label_a_cats, columns=label_a_cats)
    print(cm.to_string())

    # 전체 데이터로 최종 모델 학습 (train-only 언더샘플링)
    all_patched = df_full[df_full["_label_a"] == 1]
    all_stable  = df_full[df_full["_label_a"] == 0]
    all_stable_s = all_stable.sample(n=min(len(all_patched), len(all_stable)), random_state=SEED)
    df_final     = pd.concat([all_stable_s, all_patched]).sample(frac=1, random_state=SEED)

    y_final = df_final["_label_a"].values
    X_final = df_final[feat_cols].values.astype(np.float32)
    cw_f    = compute_class_weight("balanced", classes=np.unique(y_final), y=y_final)
    sw_f    = np.array([cw_f[yi] for yi in y_final])

    p_fin = dict(**params)
    if "lr" in p_fin:        p_fin["learning_rate"]    = p_fin.pop("lr")
    if "colsample" in p_fin: p_fin["colsample_bytree"] = p_fin.pop("colsample")
    p_fin.update(dict(objective="binary:logistic", eval_metric="logloss",
                      random_state=SEED, verbosity=0))
    p_fin.pop("num_class", None)
    final_model = xgb.XGBClassifier(**p_fin)
    final_model.fit(X_final, y_final, sample_weight=sw_f)

    return final_model, oof, ba


# ─── SHAP ────────────────────────────────────────────────────────────────────

def loao_cv(df, feat_cols):
    """
    Leave-One-Agent-Out CV (단일 5-class)
    요원 하나씩 통째로 빼고 나머지로 학습 → 빠진 요원 예측
    """
    all_cats = sorted(df["label_collapsed"].unique())
    cat_enc  = {l: i for i, l in enumerate(all_cats)}
    agents   = df["agent"].unique()
    scores   = []
    failures = []

    for agent in sorted(agents):
        train_df = df[df["agent"] != agent].copy()
        test_df  = df[df["agent"] == agent].copy()

        if len(test_df) == 0:
            continue

        y_train = train_df["label_collapsed"].map(cat_enc).values
        y_test  = test_df["label_collapsed"].map(cat_enc).values

        if not set(np.unique(y_test)).issubset(set(np.unique(y_train))):
            failures.append(agent)
            continue
        if len(np.unique(y_train)) < 2:
            continue

        X_train = train_df[feat_cols].values.astype(np.float32)
        X_test  = test_df[feat_cols].values.astype(np.float32)

        cw  = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
        cw_dict = dict(zip(np.unique(y_train), cw))
        sw  = np.array([cw_dict[yi] for yi in y_train])

        n_cls = len(np.unique(y_train))
        params = dict(
            n_estimators=100, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            objective="multi:softmax", num_class=n_cls,
            eval_metric="mlogloss", random_state=SEED, verbosity=0,
        )

        le_fold = LabelEncoder()
        y_tr_enc = le_fold.fit_transform(y_train)
        m = xgb.XGBClassifier(**params)
        m.fit(X_train, y_tr_enc, sample_weight=sw, verbose=False)

        y_pred_enc = m.predict(X_test)
        y_test_enc = le_fold.transform(y_test)
        ba = balanced_accuracy_score(y_test_enc, y_pred_enc)
        scores.append((agent, ba, len(y_test)))

    print(f"\n[LOAO-CV]  요원별 balanced_accuracy:")
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
    global SEED
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true",
                        help="HPO 없이 저장된 파라미터로 CV만 실행 (피처 실험용)")
    parser.add_argument("--hpo", action="store_true",
                        help="강제로 HPO 재실행 후 파라미터 저장")
    parser.add_argument("--seed", type=int, default=42,
                        help="글로벌 랜덤 시드 (기본 42)")
    args = parser.parse_args()
    SEED = args.seed
    np.random.seed(SEED)

    print("=" * 65)
    if args.fast:
        print("Step 2 Model Training [빠른 모드 - 저장된 파라미터 사용]")
    else:
        print("Step 2 Model Training (Walk-Forward Temporal CV)")
    print("=" * 65 + "\n")

    raw_csv = pd.read_csv("step2_training_data.csv")

    # 현재 진행 중인 최신 액트는 학습 제외 (레이블 미확정)
    EXCLUDE_TRAIN_ACTS = {"V26A2"}
    train_raw = raw_csv[~raw_csv["act"].isin(EXCLUDE_TRAIN_ACTS)].copy()
    n_excl = len(raw_csv) - len(train_raw)
    if n_excl > 0:
        print(f"  [{'+'.join(EXCLUDE_TRAIN_ACTS)} 제외] {n_excl}행 학습 제외")

    df, feat_cols_a, feat_cols_b = prepare(train_raw)

    print(f"  피처: Stage A {len(feat_cols_a)}개 / Stage B {len(feat_cols_b)}개")
    print("\n[레이블 분포]")
    print(df["label_collapsed"].value_counts().to_string())

    # ================================================================
    # 2-Stage 계층 분류
    #   Stage A: stable vs patched  (1:1 언더샘플링 + class_weight balanced)
    #   Stage B: buff   vs nerf     (scale_pos_weight 비용 민감 학습)
    # ================================================================

    saved_params = {}
    if os.path.exists(PARAMS_FILE):
        with open(PARAMS_FILE) as f:
            saved_params = json.load(f)

    # ── Stage A 데이터 준비 ───────────────────────────────────────────────────
    print("\n" + "="*50)
    print("Stage A: stable vs patched  [언더샘플링 1:1]")
    print("="*50)

    df_patched = df[df["label_collapsed"] != "stable"].copy()
    df_stable  = df[df["label_collapsed"] == "stable"].copy()
    n_patched  = len(df_patched)

    # stable을 patched 수만큼 언더샘플링 (1:1 균형)
    df_stable_s = df_stable.sample(n=min(n_patched, len(df_stable)), random_state=SEED)
    df_a = pd.concat([df_stable_s, df_patched]).sample(frac=1, random_state=SEED).reset_index(drop=True)

    print(f"  stable(샘플): {len(df_stable_s)} / patched: {n_patched}  (원본 stable: {len(df_stable)})")

    y_a       = (df_a["label_collapsed"] != "stable").astype(int).values  # 0=stable, 1=patched
    X_a       = df_a[feat_cols_a].values.astype(np.float32)
    act_idx_a = df_a["act_idx"].values
    label_a_cats = ["stable", "patched"]

    # HPO는 언더샘플된 df_a로 수행 (속도), 평가는 train_eval_stage_a로 원본 분포 기준
    use_saved_a = args.fast and "stage_a" in saved_params and not args.hpo
    if use_saved_a:
        params_a = saved_params["stage_a"]
        print("  [빠른 모드] 저장된 파라미터 사용")
    else:
        print("  HPO 중 (Stage A)...")
        params_a, best_a = run_hpo(X_a, y_a, act_idx_a, n_trials=60)
        print(f"  best BA (HPO 기준): {best_a:.4f}")

    # ① 원본 분포로 올바른 BA 측정
    model_a, _, ba_a = train_eval_stage_a(df, feat_cols_a, params_a)
    shap_top(model_a, X_a, feat_cols_a, "Stage A", save_path="shap_importance_a.csv")

    # ── Stage B 데이터 준비 ───────────────────────────────────────────────────
    print("\n" + "="*50)
    print("Stage B: buff vs nerf  [patched 행만 / cost-sensitive]")
    print("="*50)

    df_b = df[df["label_collapsed"] != "stable"].copy()
    df_b["label_b"] = df_b["label_collapsed"].apply(lambda x: "buff" if "buff" in x else "nerf")

    le_b = LabelEncoder()
    y_b  = le_b.fit_transform(df_b["label_b"].values)
    label_b_cats = list(le_b.classes_)   # ['buff', 'nerf']
    X_b          = df_b[feat_cols_b].values.astype(np.float32)
    act_idx_b    = df_b["act_idx"].values

    n_buff = (df_b["label_b"] == "buff").sum()
    n_nerf = (df_b["label_b"] == "nerf").sum()

    print(f"  buff: {n_buff} / nerf: {n_nerf}")
    print(f"  클래스: {label_b_cats}")
    print(f"  SMOTE: {'활성' if HAS_SMOTE else '비활성 (imbalanced-learn 없음)'}")

    use_saved_b = args.fast and "stage_b" in saved_params and not args.hpo
    if use_saved_b:
        params_b = saved_params["stage_b"]
        print("  [빠른 모드] 저장된 파라미터 사용")
    else:
        print("  HPO 중 (Stage B + SMOTE)...")
        params_b, best_b = run_hpo(X_b, y_b, act_idx_b, n_trials=60, use_smote=True)
        print(f"  best BA: {best_b:.4f}")

    model_b_xgb, _, ba_b_xgb = train_eval(X_b, y_b, label_b_cats, params_b,
                                            "Stage B (XGB)", act_idx_b, use_smote=True)
    model_b_lr,  _, ba_b_lr  = train_eval_lr(X_b, y_b, label_b_cats,
                                              "Stage B (LR)", act_idx_b)

    if ba_b_lr > ba_b_xgb:
        model_b, ba_b = model_b_lr, ba_b_lr
        print(f"\n  [Stage B 채택] LR ({ba_b_lr:.4f} > {ba_b_xgb:.4f})")
    else:
        model_b, ba_b = model_b_xgb, ba_b_xgb
        print(f"\n  [Stage B 채택] XGB ({ba_b_xgb:.4f} >= {ba_b_lr:.4f})")
        shap_top(model_b_xgb, X_b, feat_cols_b, "Stage B", save_path="shap_importance_b.csv")

    # 파라미터 저장
    if not args.fast or args.hpo:
        saved_params["stage_a"] = params_a
        saved_params["stage_b"] = params_b
        with open(PARAMS_FILE, "w") as f:
            json.dump(saved_params, f, indent=2)
        print(f"\n  파라미터 저장: {PARAMS_FILE}")

    # ── 현재 시점 예측 미리보기 ───────────────────────────────────────────────
    print("\n" + "-"*50)
    print("현재 시점 예측 미리보기 (2-stage 합성 확률)")
    print("-"*50)

    df_all, _, _ = prepare(raw_csv)
    latest    = df_all.loc[df_all.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
    X_now_a   = latest[feat_cols_a].values.astype(np.float32)
    X_now_b   = latest[feat_cols_b].values.astype(np.float32)

    prob_a_now = model_a.predict_proba(X_now_a)  # (N, 2): [stable, patched]
    prob_b_now = model_b.predict_proba(X_now_b)  # (N, 2): [buff, nerf]

    buff_b_idx = label_b_cats.index("buff")
    nerf_b_idx = label_b_cats.index("nerf")

    rows_preview = []
    for i in range(len(latest)):
        row        = latest.iloc[i]
        p_patched  = float(prob_a_now[i, 1])
        p_buff_dir = p_patched * float(prob_b_now[i, buff_b_idx])
        p_nerf_dir = p_patched * float(prob_b_now[i, nerf_b_idx])
        p_stable   = float(prob_a_now[i, 0])

        # verdict: 임계값 기반 mild/strong 분류
        if p_stable > max(p_nerf_dir, p_buff_dir):
            verdict = "stable"
        elif p_nerf_dir >= p_buff_dir:
            verdict = "strong_nerf" if p_nerf_dir > 0.40 else "mild_nerf"
        else:
            verdict = "strong_buff" if p_buff_dir > 0.25 else "mild_buff"

        rows_preview.append({
            "agent":    str(row["agent"]),
            "act":      str(row.get("act", "")),
            "rank_pr%": round(float(row.get("rank_pr", 0) or 0) * 5, 1),
            "vct_pr%":  round(float(row.get("vct_pr_last", 0) or 0), 1),
            "p_nerf":   round(p_nerf_dir * 100, 1),
            "p_buff":   round(p_buff_dir * 100, 1),
            "p_stable": round(p_stable * 100, 1),
            "verdict":  verdict,
        })

    preview_df = pd.DataFrame(rows_preview).sort_values("p_nerf", ascending=False)
    print(preview_df.to_string(index=False))

    # ── 저장 ────────────────────────────────────────────────────────────────
    joblib.dump({
        "model_a":      model_a,
        "model_b":      model_b,
        "feat_cols_a":  feat_cols_a,
        "feat_cols_b":  feat_cols_b,
        "label_b_cats": label_b_cats,   # ['buff', 'nerf']
    }, "step2_pipeline.pkl")
    print(f"\n저장: step2_pipeline.pkl  (Stage A BA: {ba_a:.4f} / Stage B BA: {ba_b:.4f})")

    # ── Leave-One-Agent-Out CV (Stage A 기준) ────────────────────────────────
    print("\n" + "="*50)
    print("Leave-One-Agent-Out CV - Stage A (stable vs patched)")
    print("="*50)
    # LOAO는 Stage A 레이블로 실행
    df_loao = df.copy()
    df_loao["label_collapsed"] = df_loao["label_collapsed"].apply(
        lambda x: "stable" if x == "stable" else "patched"
    )
    loao_cv(df_loao, feat_cols_a)

if __name__ == "__main__":
    main()
