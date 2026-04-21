"""
백테스트 — 과거 패치에 대해 모델이 실제로 맞췄나?

설계:
- step2_training_data.csv 를 act_idx 기준으로 walk-forward 재학습
- 각 폴드: 직전까지의 act로 Stage A + Stage B 학습 → 해당 act(들) 예측
- 예측 결과를 CSV로 저장 + 콘솔에 요약 (정/재현율, 액트별 적중, 고확신 구간)

출력:
  backtest_predictions.csv — per-row (agent, act, label_true, verdict, p_*)
  콘솔 — 3-class confusion, verdict별 precision/recall, act별 BA, 고확신 hit rate

실행:
  python backtest.py            # fold_size=2 (기본)
  python backtest.py --step 1   # leave-one-act-out (더 많은 fold)
  python backtest.py --min 0.4  # min_train_ratio 조정
"""

import argparse
import json
import os
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline as SkPipeline
from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (balanced_accuracy_score, classification_report,
                             confusion_matrix)
import xgboost as xgb

from train_step2 import (
    prepare, collapse_label, CAT_COLS,
    DROP_COLS_COMMON, DROP_COLS_A_ONLY, DROP_COLS_B_ONLY,
)

SEED = 42
PARAMS_FILE = "best_params.json"
EXCLUDE_ACTS = {"V26A2"}  # 레이블 미확정

# ── 3-class verdict로 접기 ────────────────────────────────────────────────────
def to_dir3(label: str) -> str:
    """5-class → 3-class (stable / buff / nerf)"""
    if "buff" in label: return "buff"
    if "nerf" in label: return "nerf"
    return "stable"

# ── 한 폴드 훈련/예측 ─────────────────────────────────────────────────────────
def train_predict_one_fold(df_train, df_val, feat_cols_a, feat_cols_b,
                           params_a, params_b):
    """
    한 폴드에 대해 Stage A + Stage B 학습 → val 행마다 (p_stable, p_buff, p_nerf) 반환
    """
    # ── Stage A: stable vs patched, 1:1 언더샘플링 ─────────────────────────
    tr_patched = df_train[df_train["label_collapsed"] != "stable"]
    tr_stable  = df_train[df_train["label_collapsed"] == "stable"]
    if len(tr_patched) == 0 or len(tr_stable) == 0:
        return None

    n_pat = len(tr_patched)
    tr_stable_s = tr_stable.sample(n=min(n_pat, len(tr_stable)),
                                   random_state=SEED)
    tr_a = (pd.concat([tr_stable_s, tr_patched])
            .sample(frac=1, random_state=SEED))

    y_a = (tr_a["label_collapsed"] != "stable").astype(int).values
    X_a = tr_a[feat_cols_a].values.astype(np.float32)

    cw_a = compute_class_weight("balanced", classes=np.unique(y_a), y=y_a)
    sw_a = np.array([cw_a[yi] for yi in y_a])

    p_a = dict(**params_a)
    if "lr" in p_a:        p_a["learning_rate"]    = p_a.pop("lr")
    if "colsample" in p_a: p_a["colsample_bytree"] = p_a.pop("colsample")
    p_a.update(dict(objective="binary:logistic", eval_metric="logloss",
                    random_state=SEED, verbosity=0))
    p_a.pop("num_class", None)

    m_a = xgb.XGBClassifier(**p_a)
    m_a.fit(X_a, y_a, sample_weight=sw_a, verbose=False)

    X_val_a = df_val[feat_cols_a].values.astype(np.float32)
    prob_a  = m_a.predict_proba(X_val_a)  # (N, 2): [stable, patched]

    # ── Stage B: patched 행만, buff vs nerf (LR — train_step2 결과와 맞춤) ─
    tr_b = df_train[df_train["label_collapsed"] != "stable"].copy()
    tr_b["label_b"] = tr_b["label_collapsed"].apply(
        lambda x: "buff" if "buff" in x else "nerf"
    )

    le_b = LabelEncoder()
    y_b  = le_b.fit_transform(tr_b["label_b"].values)
    X_b  = tr_b[feat_cols_b].values.astype(np.float32)

    cw_b = compute_class_weight("balanced", classes=np.unique(y_b), y=y_b)
    sw_b = np.array([cw_b[yi] for yi in y_b])

    # LR 파이프라인 (train_step2 Stage B와 동일 설계, C=1.0)
    pipe_b = SkPipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("lr", LogisticRegression(C=1.0, class_weight="balanced",
                                  max_iter=2000, solver="saga",
                                  random_state=SEED)),
    ])
    pipe_b.fit(X_b, y_b, lr__sample_weight=sw_b)

    X_val_b = df_val[feat_cols_b].values.astype(np.float32)
    prob_b  = pipe_b.predict_proba(X_val_b)

    buff_idx = list(le_b.classes_).index("buff")
    nerf_idx = list(le_b.classes_).index("nerf")

    # ── 합성: 각 행 별 (p_stable, p_buff_dir, p_nerf_dir) ─────────────────
    rows = []
    for i in range(len(df_val)):
        p_stable = float(prob_a[i, 0])
        p_patch  = float(prob_a[i, 1])
        p_buff_d = p_patch * float(prob_b[i, buff_idx])
        p_nerf_d = p_patch * float(prob_b[i, nerf_idx])

        # verdict: predict_service 규칙과 맞춤
        if p_stable > max(p_nerf_d, p_buff_d):
            verdict = "stable"
        elif p_nerf_d >= p_buff_d:
            verdict = "strong_nerf" if p_nerf_d > 0.40 else "mild_nerf"
        else:
            verdict = "strong_buff" if p_buff_d > 0.25 else "mild_buff"

        rows.append({
            "p_stable":   p_stable,
            "p_buff_dir": p_buff_d,
            "p_nerf_dir": p_nerf_d,
            "verdict":    verdict,
        })
    return rows


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=2,
                    help="per-fold 평가할 act 수 (기본 2). 1 = leave-one-act-out")
    ap.add_argument("--min", type=float, default=0.4,
                    help="첫 학습에 사용할 act 비율 (기본 0.4)")
    ap.add_argument("--out", type=str, default="backtest_predictions.csv")
    args = ap.parse_args()

    print("=" * 65)
    print(f"Backtest — walk-forward  step={args.step}  min_train_ratio={args.min}")
    print("=" * 65)

    # 파라미터 로드
    if not os.path.exists(PARAMS_FILE):
        raise SystemExit(f"{PARAMS_FILE} 없음 — train_step2.py 먼저 실행")
    with open(PARAMS_FILE) as f:
        saved = json.load(f)
    params_a = saved["stage_a"]
    params_b = saved["stage_b"]

    # 데이터 로드
    raw = pd.read_csv("step2_training_data.csv")
    raw = raw[~raw["act"].isin(EXCLUDE_ACTS)].copy()
    df, feat_cols_a, feat_cols_b = prepare(raw)
    df = df.reset_index(drop=True)

    print(f"  rows:           {len(df)}")
    print(f"  features:       A {len(feat_cols_a)} / B {len(feat_cols_b)}")

    acts_sorted = np.sort(df["act_idx"].unique())
    n_acts      = len(acts_sorted)
    min_t       = max(int(n_acts * args.min), 5)

    # 폴드 구성: [0..min_t) 학습 → [min_t..min_t+step) 예측
    #          그 다음 [0..min_t+step) 학습 → [min_t+step..min_t+2*step) 예측 ...
    fold_starts = list(range(min_t, n_acts, args.step))
    print(f"  total acts:     {n_acts}")
    print(f"  first val act:  {acts_sorted[min_t]} (idx {acts_sorted[min_t]})")
    print(f"  folds:          {len(fold_starts)}")
    print()

    all_preds = []

    for fi, ts in enumerate(fold_starts):
        te   = min(ts + args.step, n_acts)
        tr_acts  = acts_sorted[:ts]
        val_acts = acts_sorted[ts:te]

        df_tr  = df[df["act_idx"].isin(tr_acts)]
        df_val = df[df["act_idx"].isin(val_acts)]
        if len(df_val) == 0 or len(df_tr) < 20:
            continue

        preds = train_predict_one_fold(df_tr, df_val, feat_cols_a, feat_cols_b,
                                       params_a, params_b)
        if preds is None:
            continue

        for local_i, (_, row) in enumerate(df_val.iterrows()):
            p = preds[local_i]
            all_preds.append({
                "agent":        row["agent"],
                "act":          row["act"],
                "act_idx":      int(row["act_idx"]),
                "label_true":   row["label_collapsed"],
                "dir_true":     to_dir3(row["label_collapsed"]),
                "verdict":      p["verdict"],
                "dir_pred":     to_dir3(p["verdict"]),
                "p_stable":     round(p["p_stable"],   4),
                "p_buff_dir":   round(p["p_buff_dir"], 4),
                "p_nerf_dir":   round(p["p_nerf_dir"], 4),
                "hit_5class":   int(row["label_collapsed"] == p["verdict"]),
                "hit_dir":      int(to_dir3(row["label_collapsed"]) == to_dir3(p["verdict"])),
            })

        val_act_names = ",".join(df_val["act"].unique())
        print(f"  fold {fi+1:>2}/{len(fold_starts)}  train={len(df_tr):>3}  val={len(df_val):>3}  ({val_act_names})")

    if not all_preds:
        print("[경고] 예측 결과 없음")
        return

    out = pd.DataFrame(all_preds)
    out.to_csv(args.out, index=False)
    print(f"\n저장: {args.out}  ({len(out)} rows)")

    # ── 요약 ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("전체 3-class 성과 (stable / buff / nerf)")
    print("=" * 60)

    y_t = out["dir_true"].values
    y_p = out["dir_pred"].values
    ba  = balanced_accuracy_score(y_t, y_p)
    labels3 = ["stable", "buff", "nerf"]
    print(f"\nbalanced_accuracy: {ba:.4f}   hit_rate: {out['hit_dir'].mean():.4f}\n")

    print(classification_report(y_t, y_p, labels=labels3,
                                target_names=labels3, zero_division=0))
    print("[혼동 행렬]  row=true, col=pred")
    cm = pd.DataFrame(confusion_matrix(y_t, y_p, labels=labels3),
                      index=labels3, columns=labels3)
    print(cm.to_string())

    # ── 5-class 상세 ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("5-class verdict 상세")
    print("=" * 60)
    labels5 = ["strong_buff", "mild_buff", "stable", "mild_nerf", "strong_nerf"]
    print(classification_report(out["label_true"], out["verdict"],
                                labels=labels5, target_names=labels5,
                                zero_division=0))

    # ── act별 성과 ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Act 별 적중률 (3-class)")
    print("=" * 60)
    per_act = (out.groupby("act")
                  .agg(n=("agent", "size"),
                       hit_dir=("hit_dir", "mean"),
                       hit_5=("hit_5class", "mean"))
                  .reset_index()
                  .sort_values("act"))
    for _, r in per_act.iterrows():
        bar = "#" * int(r["hit_dir"] * 20)
        print(f"  {r['act']:<6}  n={int(r['n']):>3}  dir={r['hit_dir']:.3f}  5c={r['hit_5']:.3f}  {bar}")

    # ── 고확신 구간 분석 ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("고확신 예측 정밀도")
    print("=" * 60)

    def prec(mask, true_col, target):
        sub = out[mask]
        if len(sub) == 0:
            return (0, 0.0)
        hits = (sub[true_col] == target).sum()
        return (len(sub), hits / len(sub))

    print("\nNERF 예측:")
    for thr in [0.30, 0.40, 0.50, 0.60, 0.70]:
        n, p = prec(out["p_nerf_dir"] >= thr, "dir_true", "nerf")
        print(f"  p_nerf ≥ {thr:.2f}  →  n={n:>3}  precision={p:.3f}")

    print("\nBUFF 예측:")
    for thr in [0.15, 0.20, 0.25, 0.35, 0.50]:
        n, p = prec(out["p_buff_dir"] >= thr, "dir_true", "buff")
        print(f"  p_buff ≥ {thr:.2f}  →  n={n:>3}  precision={p:.3f}")

    # ── Top-K "가장 너프 같았다" 들이 실제로 맞았나 ───────────────────────
    print("\n" + "=" * 60)
    print("Top-K 고확신 너프 예측 (각 act 상위 3개)")
    print("=" * 60)
    top_nerf = (out.sort_values(["act", "p_nerf_dir"], ascending=[True, False])
                   .groupby("act")
                   .head(3))
    hit_rate = (top_nerf["dir_true"] == "nerf").mean()
    print(f"  n={len(top_nerf)}  nerf precision(top-3 per act) = {hit_rate:.3f}\n")
    # 최근 5개 act만 보기 (눈으로 검사)
    recent_acts = acts_sorted[-5:]
    recent = top_nerf[top_nerf["act_idx"].isin(recent_acts)]
    for act, g in recent.groupby("act"):
        print(f"  --- {act} ---")
        for _, r in g.iterrows():
            ok = "✓" if r["dir_true"] == "nerf" else "✗"
            print(f"    {ok} {r['agent']:<12}  p_nerf={r['p_nerf_dir']:.3f}  verdict={r['verdict']:<12}  truth={r['label_true']}")


if __name__ == "__main__":
    main()
