"""
train_impact_model.py
Phase 2: 패치 임팩트 추정
데이터(124행)가 회귀 모델에 부족하므로:
  - 방향 x magnitude_bin x has_identity_change 기반 경험적 룩업
  - 불확실성 구간 (p25~p75, p10~p90)
  - Ridge 회귀 보조 (trend 참고용)

출력: impact_lookup.json (Phase 3 시뮬레이터 주 사용)
      impact_model_pr.pkl / impact_model_wr.pkl (보조)
"""
import sys
import warnings
import json
warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
import joblib

FEATURES = [
    "direction_enc", "n_changes", "n_skills_changed", "max_skill_weight",
    "has_mechanic", "magnitude_filled", "patch_importance_score",
    "has_identity_change", "has_ult_change", "mobility_skill_nerfed",
    "rank_pr_t-1", "rank_wr_vs50_pre", "rank_pr_pre_slope", "rank_pr_pre_avg",
    "vct_pr_t-1_filled", "vct_pr_pre_avg_filled",
    "n_prev_patches", "prev_nerf_count", "prev_buff_count",
    "acts_since_last_patch_clip", "last_dir_enc", "multi_patch_4acts",
    "role_enc", "role_pr_share_pre", "role_rival_pr_mean_pre",
]


def prepare(df):
    d = df.copy()
    d["direction_enc"] = d["direction"].map({"nerf": -1, "buff": 1}).fillna(0)
    d["last_dir_enc"]  = d["last_patch_direction"].map({"nerf": -1, "buff": 1, "none": 0}).fillna(0)
    d["magnitude_filled"] = d["value_chg_max_abs"].fillna(d["patch_importance_score"])
    d["vct_pr_t-1_filled"]      = d["vct_pr_t-1"].fillna(0)
    d["vct_pr_pre_avg_filled"]   = d["vct_pr_pre_avg"].fillna(0)
    d["acts_since_last_patch_clip"] = d["acts_since_last_patch"].clip(upper=8)
    role_map = {"duelist": 3, "initiator": 2, "controller": 1, "sentinel": 0}
    d["role_enc"] = d["agent_role"].map(role_map).fillna(1)
    d["delta_rank_pr"] = d["rank_pr_t+1"] - d["rank_pr_t-1"]
    d["delta_rank_wr"] = d["rank_wr_t+1"] - d["rank_wr_t-1"]
    mag = d["value_chg_max_abs"]
    mag_cut = pd.cut(mag, bins=[0, 0.3, 1.0, 99], labels=["small", "medium", "large"])
    d["mag_bin"] = mag_cut.astype(object).where(mag.notna(), other="mechanic").fillna("mechanic")
    return d


def load():
    df = pd.read_csv("training_data.csv")
    df = prepare(df)
    return df[df["delta_rank_pr"].notna()].copy()


def percentile_stats(series):
    return {
        "n":       int(len(series)),
        "median":  round(float(series.median()), 3),
        "mean":    round(float(series.mean()), 3),
        "std":     round(float(series.std()), 3),
        "p10":     round(float(series.quantile(0.10)), 3),
        "p25":     round(float(series.quantile(0.25)), 3),
        "p75":     round(float(series.quantile(0.75)), 3),
        "p90":     round(float(series.quantile(0.90)), 3),
    }


def build_lookup(df):
    lookup = {}

    # direction x identity x mag_bin
    for direction in ["nerf", "buff"]:
        for identity in [0, 1]:
            for mag_bin in ["small", "medium", "large", "mechanic"]:
                mask = (
                    (df["direction"] == direction) &
                    (df["has_identity_change"] == identity) &
                    (df["mag_bin"] == mag_bin)
                )
                sub = df[mask]
                if len(sub) < 3:
                    continue
                key = f"{direction}_id{identity}_{mag_bin}"
                lookup[key] = {
                    "pr": percentile_stats(sub["delta_rank_pr"]),
                    "wr": percentile_stats(sub["delta_rank_wr"]),
                }

    # direction 단순 fallback
    for direction in ["nerf", "buff"]:
        sub = df[df["direction"] == direction]
        lookup[f"_fallback_{direction}"] = {
            "pr": percentile_stats(sub["delta_rank_pr"]),
            "wr": percentile_stats(sub["delta_rank_wr"]),
        }

    # 전체 통계
    lookup["_overall"] = {
        "n": int(len(df)),
        "pr_std": round(float(df["delta_rank_pr"].std()), 3),
        "wr_std": round(float(df["delta_rank_wr"].std()), 3),
        "pr": percentile_stats(df["delta_rank_pr"]),
        "wr": percentile_stats(df["delta_rank_wr"]),
    }
    return lookup


def build_regression(df):
    X = df[FEATURES].values
    pipe_pr = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("reg", Ridge(alpha=15)),
    ])
    pipe_wr = Pipeline([
        ("imp", SimpleImputer(strategy="median")),
        ("sc",  StandardScaler()),
        ("reg", Ridge(alpha=15)),
    ])
    pipe_pr.fit(X, df["delta_rank_pr"].values)
    pipe_wr.fit(X, df["delta_rank_wr"].values)
    return pipe_pr, pipe_wr


def lookup_estimate(lookup, direction, magnitude, has_identity):
    if magnitude is None or (isinstance(magnitude, float) and np.isnan(magnitude)):
        mag_bin = "mechanic"
    elif float(magnitude) < 0.3:
        mag_bin = "small"
    elif float(magnitude) < 1.0:
        mag_bin = "medium"
    else:
        mag_bin = "large"

    key = f"{direction}_id{int(has_identity)}_{mag_bin}"
    if key in lookup:
        return lookup[key], mag_bin

    # fallback: identity 무시
    for id_val in [0, 1]:
        k2 = f"{direction}_id{id_val}_{mag_bin}"
        if k2 in lookup:
            return lookup[k2], mag_bin

    return lookup.get(f"_fallback_{direction}", lookup["_overall"]), mag_bin


def main():
    print("=" * 65)
    print("Phase 2: 패치 임팩트 추정 (경험적 룩업 + 보조 회귀)")
    print("=" * 65 + "\n")

    df = load()
    print(f"데이터: {len(df)}행 / {df['agent'].nunique()}요원")
    print(f"nerf={len(df[df['direction']=='nerf'])}  buff={len(df[df['direction']=='buff'])}\n")

    # 룩업
    print("── 경험적 룩업 테이블 ──")
    lookup = build_lookup(df)
    for k, v in sorted(lookup.items()):
        if k.startswith("_"):
            continue
        pr = v["pr"]
        print(f"  {k:<35} n={pr['n']:<3}  "
              f"pr_median={pr['median']:+.2f}  IQR=[{pr['p25']:+.2f}~{pr['p75']:+.2f}]")

    print("\n── Fallback (방향별 전체) ──")
    for d in ["nerf", "buff"]:
        v = lookup[f"_fallback_{d}"]
        pr = v["pr"]
        print(f"  {d}: n={pr['n']}  "
              f"pr_median={pr['median']:+.2f}  "
              f"p10~p90=[{pr['p10']:+.2f}~{pr['p90']:+.2f}]  "
              f"wr_median={v['wr']['median']:+.2f}")

    # 회귀
    print("\n── 보조 Ridge 회귀 학습 ──")
    pipe_pr, pipe_wr = build_regression(df)

    # 저장
    json.dump(lookup, open("impact_lookup.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    joblib.dump(pipe_pr, "impact_model_pr.pkl")
    joblib.dump(pipe_wr, "impact_model_wr.pkl")
    json.dump(FEATURES, open("impact_model_features.json", "w"), indent=2)
    print("OK: impact_lookup.json / impact_model_pr.pkl / impact_model_wr.pkl / impact_model_features.json")

    # 추론 샘플
    print("\n── 추론 샘플 ──")
    cases = [
        ("Jett E 33% 버프",          "buff", 0.33, 1),
        ("Gekko C 20% 너프",         "nerf", 0.20, 0),
        ("Chamber X rework (identity)", "nerf", None, 1),
        ("Brimstone E 소규모 너프",   "nerf", 0.15, 0),
        ("Phoenix Q 대형 너프",       "nerf", 2.0,  0),
    ]
    for label, direction, magnitude, identity in cases:
        est, mag_bin = lookup_estimate(lookup, direction, magnitude, identity)
        pr = est.get("pr", est)
        wr = est.get("wr", {})
        print(f"\n  [{label}]  ({mag_bin})")
        print(f"    Δrank_pr: 중앙={pr['median']:+.2f}  IQR=[{pr['p25']:+.2f}~{pr['p75']:+.2f}]  n={pr['n']}")
        if wr:
            print(f"    Δrank_wr: 중앙={wr['median']:+.2f}  IQR=[{wr['p25']:+.2f}~{wr['p75']:+.2f}]")


if __name__ == "__main__":
    main()
