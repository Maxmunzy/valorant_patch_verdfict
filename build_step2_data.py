"""
build_step2_data.py
Step 2 학습 데이터 빌더 — 진입점

(요원, 액트) 쌍 → 다음 액트 패치 예측 레이블 + 피처 생성 후 CSV 저장

모듈 구조:
  agent_data.py    — 상수, 요원 킷/설계/관계 데이터
  label_builder.py — 레이블 생성 함수군
  feature_builder.py — 피처 빌딩 함수군
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from agent_data import (
    ACT_IDX, IDX_ACT, PATCH_TO_ACT, VCT_TO_ACT, VCT_EVENT_ORDER,
    normalize_agent,
)
from label_builder import build_patch_label, classify_stable_state
from feature_builder import build_features, precompute_map_versatility, precompute_role_util_avgs


def main():
    print("=" * 65)
    print("Step 2 Training Data Builder")
    print("=" * 65 + "\n")

    # ── 데이터 로드 ──────────────────────────────────────────────────────────
    rank_v  = pd.read_csv("agent_act_history_all.csv")
    rank_m  = pd.read_csv("maxmunzy_diamond_plus.csv")
    vct_raw = pd.read_csv("vct_summary.csv")
    pn      = pd.read_csv("patch_notes_classified.csv")
    step1   = pd.read_csv("training_data.csv")
    map_dep = pd.read_csv("map_dependency_scores.csv")
    map_raw = pd.read_csv("all_agents_map_stats.csv")
    map_v_dict = precompute_map_versatility(map_raw)

    # ── 요원 이름 정규화 ─────────────────────────────────────────────────────
    for df in [rank_v, rank_m, vct_raw]:
        df["agent"] = df["agent"].map(normalize_agent)
    for df in [pn, step1]:
        if "agent" in df.columns:
            df["agent"] = df["agent"].map(normalize_agent)

    # ── 랭크 데이터 통합 (vstats.gg 우선, 빈 구간은 maxmunzy 보완) ──────────
    rv = rank_v[rank_v["note"] == "ok"].copy()
    rv = rv.rename(columns={"act": "act_name", "win_rate": "win_rate_pct"})
    rv["act_idx"] = rv["act_name"].map(ACT_IDX)

    rm = rank_m.copy()
    rm["act_idx"] = rm["act_name"].map(ACT_IDX)

    vstats_keys = set(zip(rv["agent"], rv["act_name"]))
    rm_excl = rm[~rm.apply(lambda r: (r["agent"], r["act_name"]) in vstats_keys, axis=1)]
    common  = ["agent", "act_name", "act_idx", "win_rate_pct", "pick_rate_pct"]
    rank_df = pd.concat(
        [rv[[c for c in common if c in rv.columns]],
         rm_excl[[c for c in common if c in rm_excl.columns]]],
        ignore_index=True
    ).sort_values(["agent", "act_idx"])

    # ── 실력 천장 프록시: 다이아+ / 전체 픽률 비율 (E6A3~E9A3 겹치는 구간) ──
    _mx_pr     = rm[rm["act_idx"].between(13, 22)][["agent","act_idx","pick_rate_pct"]].rename(columns={"pick_rate_pct":"diamond_pr"})
    _rv_pr     = rv[rv["act_idx"].between(13, 22)][["agent","act_idx","pick_rate_pct"]].rename(columns={"pick_rate_pct":"overall_pr"})
    _sc_merged = pd.merge(_mx_pr, _rv_pr, on=["agent","act_idx"])
    _sc_merged["ratio"] = _sc_merged["diamond_pr"] / _sc_merged["overall_pr"].replace(0, np.nan)
    _sc_per    = _sc_merged.groupby("agent")["ratio"].mean()
    _sc_min, _sc_max = _sc_per.min(), _sc_per.max()
    SKILL_CEILING_PROXY = {
        agent: float(np.clip((ratio - _sc_min) / (_sc_max - _sc_min + 1e-9), 0, 1))
        for agent, ratio in _sc_per.items()
    }

    role_util_dict = precompute_role_util_avgs(rank_df)

    # ── VCT 데이터 통합 ───────────────────────────────────────────────────────
    vct_df = vct_raw.copy()
    vct_df["act_name"]    = vct_df["event"].map(VCT_TO_ACT)
    vct_df["act_idx"]     = vct_df["act_name"].map(ACT_IDX)
    vct_df["event_order"] = vct_df["event"].map(VCT_EVENT_ORDER)
    vct_df = vct_df.dropna(subset=["act_idx"])

    # ── Step 1 이력 ───────────────────────────────────────────────────────────
    step1["patch_act_idx"] = step1["patch_act"].map(ACT_IDX)

    # ── 패치 노트 매핑 ────────────────────────────────────────────────────────
    pn["act"]     = pn["patch"].astype(str).map(PATCH_TO_ACT)
    pn["act_idx"] = pn["act"].map(ACT_IDX)
    pn = pn.dropna(subset=["act_idx"])
    pn["act_idx"] = pn["act_idx"].astype(int)

    print(f"  랭크: {len(rank_df)}행 / VCT: {len(vct_df)}행")
    print(f"  패치노트: {len(pn)}행 / Step1: {len(step1)}행")

    # ── (요원, 액트) 쌍 생성 ─────────────────────────────────────────────────
    agent_acts = rank_df[["agent", "act_name", "act_idx"]].drop_duplicates()
    print(f"\n  (요원, 액트) 후보: {len(agent_acts)}쌍")

    # ── 패치 룩업 테이블 ──────────────────────────────────────────────────────
    patch_lookup = {}
    for _, row in pn.iterrows():
        key = (row["agent"], int(row["act_idx"]))
        patch_lookup.setdefault(key, []).append(row)

    # ── 레이블 & 피처 조립 ───────────────────────────────────────────────────
    rows = []
    for _, aa in agent_acts.iterrows():
        agent   = aa["agent"]
        act     = aa["act_name"]
        act_idx = int(aa["act_idx"])

        next_act_idx    = act_idx + 1
        patch_rows_list = patch_lookup.get((agent, next_act_idx), [])

        feat = build_features(
            agent, act_idx, rank_df, vct_df, step1, map_dep,
            map_versatility_dict=map_v_dict, pn_df=pn,
            skill_ceiling_proxy=SKILL_CEILING_PROXY,
            role_util_dict=role_util_dict,
        )

        if patch_rows_list:
            patch_rows_df = pd.DataFrame(patch_rows_list)
            label, meta   = build_patch_label(agent, next_act_idx, patch_rows_df, step1, feat)
        else:
            label = classify_stable_state(feat)
            meta  = {
                "label_direction": "none",
                "label_skill":     "none",
                "label_trigger":   "none",
                "label_context":   "none",
                "label_has_rework": 0,
            }

        feat.update({"agent": agent, "act": act, "act_idx": act_idx, "label": label})
        feat.update(meta)
        rows.append(feat)

    df = pd.DataFrame(rows)
    print(f"\n  생성: {len(df)}행 / {df.shape[1]}컬럼")

    # ── 레이블 분포 ───────────────────────────────────────────────────────────
    print("\n[레이블 분포]")
    print(df["label"].value_counts().to_string())

    print("\n[방향별 집계]")
    df["label_group"] = df["label"].apply(lambda x:
        "stable" if x == "stable" else
        "rework" if x == "rework" else
        x.split("_")[0]
    )
    print(df["label_group"].value_counts().to_string())

    # ── 저장 ──────────────────────────────────────────────────────────────────
    df.to_csv("step2_training_data.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: step2_training_data.csv  ({len(df)}행 x {df.shape[1]}컬럼)")

    print("\n[패치 케이스 샘플]")
    patched     = df[df["label"] != "stable"].sort_values(["agent", "act_idx"])
    sample_cols = ["agent", "act", "rank_pr", "vct_pr_last", "vct_profile",
                   "last_combined", "label"]
    print(patched[sample_cols].head(25).to_string(index=False))

    return df


if __name__ == "__main__":
    df = main()
