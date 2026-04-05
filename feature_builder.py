"""
feature_builder.py
(요원, 액트) 기준 피처 계산 함수군
"""

import numpy as np

from agent_data import (
    AGENT_DESIGN, _DEFAULT_DESIGN,
    AGENT_KIT, _DEFAULT_KIT,
    AGENT_TIER_SCORE, SKILL_TIER_SCORE,
    IDX_ACT,
    compute_kit_score, get_kit_flags,
)
from label_builder import dominant_trigger


def precompute_map_versatility(map_raw_df):
    """all_agents_map_stats 기반 맵 다양성 지표 사전 계산

    Returns dict: (act, agent) → {map_versatility, map_hhi, map_specialist}
    - map_versatility : 해당 액트에서 플레이한 맵 수
    - map_hhi         : 허핀달 집중도 0(균등분산)~1(한 맵 독점)
    - map_specialist  : 1개 맵이 전체 픽의 50%+ → 전문 맵 요원
    """
    result = {}
    df = map_raw_df[map_raw_df["map"] != "ALL"].copy()
    for (act, agent), grp in df.groupby(["act", "agent"]):
        total = grp["matches"].sum()
        if total == 0:
            continue
        n = len(grp)
        shares   = grp["matches"] / total
        hhi_raw  = float((shares ** 2).sum())
        hhi_norm = (hhi_raw - 1/n) / (1 - 1/n) if n > 1 else 1.0
        result[(act, agent)] = {
            "map_versatility": n,
            "map_hhi":         round(hhi_norm, 4),
            "map_specialist":  float(shares.max() > 0.5),
        }
    return result


def compute_vct_profile(vct_pre_avg):
    if vct_pre_avg is None or (isinstance(vct_pre_avg, float) and np.isnan(vct_pre_avg)):
        return "pro_unknown"
    v = float(vct_pre_avg)
    if   v >= 15: return "pro_staple"
    elif v >= 5:  return "pro_viable"
    elif v >= 1:  return "pro_marginal"
    else:         return "pro_absent"


def build_features(agent, act_idx, rank_df, vct_df, step1_df, map_dep_df=None,
                   map_versatility_dict=None, pn_df=None, skill_ceiling_proxy=None):
    """
    (요원, 액트) 기준 현재 상태 피처 계산
    """
    feat = {}

    # ── 랭크 피처 ──────────────────────────────────────────────────────────────
    ag_rank  = rank_df[rank_df["agent"] == agent].sort_values("act_idx")
    all_hist = ag_rank[ag_rank["act_idx"] <= act_idx]
    cur_rank = all_hist.tail(3)
    if not cur_rank.empty:
        latest = cur_rank.iloc[-1]
        feat["rank_pr"]      = float(latest["pick_rate_pct"])
        feat["rank_wr"]      = float(latest["win_rate_pct"])
        feat["rank_wr_vs50"] = float(latest["win_rate_pct"]) - 50.0
        if len(cur_rank) >= 2:
            pr_vals = cur_rank["pick_rate_pct"].values
            x = np.arange(len(pr_vals))
            feat["rank_pr_slope"] = float(np.polyfit(x, pr_vals, 1)[0])
        else:
            feat["rank_pr_slope"] = 0.0
        feat["rank_pr_avg3"] = float(cur_rank["pick_rate_pct"].mean())
        feat["rank_pr_peak"] = float(all_hist["pick_rate_pct"].max())

    # ── VCT 피처 ───────────────────────────────────────────────────────────────
    ag_vct  = vct_df[vct_df["agent"] == agent].sort_values(["act_idx", "event_order"])
    pre_vct = ag_vct[ag_vct["act_idx"] <= act_idx]
    if not pre_vct.empty:
        last_ev = pre_vct.iloc[-1]
        feat["vct_pr_last"] = float(last_ev["pick_rate_pct"])
        feat["vct_wr_last"] = float(last_ev["win_rate_pct"])
        feat["vct_pr_avg"]  = float(pre_vct.tail(3)["pick_rate_pct"].mean())
        feat["vct_pre_n"]   = len(pre_vct)
    else:
        feat["vct_pr_last"] = 0.0
        feat["vct_wr_last"] = np.nan
        feat["vct_pr_avg"]  = 0.0
        feat["vct_pre_n"]   = 0

    feat["vct_profile"]    = compute_vct_profile(feat.get("vct_pr_avg"))
    feat["vct_pr_peak_all"] = float(pre_vct["pick_rate_pct"].max()) if not pre_vct.empty else 0.0

    recent_vct = pre_vct.tail(3)
    if len(recent_vct) >= 2:
        vpr = recent_vct["pick_rate_pct"].values
        feat["vct_pr_slope"] = float(np.polyfit(np.arange(len(vpr)), vpr, 1)[0])
    else:
        feat["vct_pr_slope"] = 0.0

    if "rank_pr" in feat and feat.get("vct_pr_avg", 0) > 0:
        feat["rank_vct_gap"] = feat["rank_pr"] - feat["vct_pr_avg"]
    else:
        feat["rank_vct_gap"] = np.nan

    # ── Step 1 이력 피처 ───────────────────────────────────────────────────────
    hist = step1_df[
        (step1_df["agent"] == agent) &
        (step1_df["patch_act_idx"] <= act_idx)
    ].sort_values("patch_act_idx")

    feat["n_total_patches"] = len(hist)
    feat["n_nerf_patches"]  = int((hist["direction"] == "nerf").sum())
    feat["n_buff_patches"]  = int((hist["direction"] == "buff").sum())

    if not hist.empty:
        feat["acts_since_patch"] = act_idx - int(hist["patch_act_idx"].max())
    elif pn_df is not None:
        pn_agent = pn_df[(pn_df["agent"] == agent) & (pn_df["act_idx"] <= act_idx)]
        feat["acts_since_patch"] = (act_idx - int(pn_agent["act_idx"].max())) if not pn_agent.empty else 99
    else:
        feat["acts_since_patch"] = 99

    if not hist.empty:
        last = hist.iloc[-1]
        feat["last_direction"]    = last.get("direction", "none")
        feat["last_combined"]     = last.get("combined_verdict", "UNKNOWN")
        feat["last_rank_verdict"] = last.get("rank_verdict", "NO_DATA")
        feat["last_vct_verdict"]  = last.get("vct_verdict", "NO_DATA")
        feat["last_max_skill_w"]  = float(last.get("max_skill_weight", 2.0) or 2.0)
        last_act_idx = int(hist["patch_act_idx"].max())
        if pn_df is not None:
            pn_last = pn_df[
                (pn_df["agent"] == agent) &
                (pn_df["act_idx"] == last_act_idx) &
                (pn_df["direction"].isin(["nerf", "buff"]))
            ]
            feat["last_trigger_type"] = dominant_trigger(pn_last)
        else:
            feat["last_trigger_type"] = "rank"
    else:
        feat["last_direction"]    = "none"
        feat["last_combined"]     = "UNKNOWN"
        feat["last_rank_verdict"] = "NO_DATA"
        feat["last_vct_verdict"]  = "NO_DATA"
        feat["last_max_skill_w"]  = 2.0
        feat["last_trigger_type"] = "rank"

    # 최근 4액트 내 DUAL_MISS 누적 (rework 신호)
    recent4 = hist[hist["patch_act_idx"] >= act_idx - 4]
    feat["recent_dual_miss_count"] = int(
        recent4["combined_verdict"].isin(["DUAL_MISS", "RANK_ONLY_MISS"]).sum()
    )
    feat["recent_buff_fail_count"] = int(
        (recent4["combined_verdict"].isin(["DUAL_MISS", "RANK_ONLY_MISS"]) &
         (recent4["direction"] == "buff")).sum()
    )

    # 최근 연속 방향
    if not hist.empty:
        directions = hist["direction"].tolist()
        streak = 1
        for i in range(len(directions)-2, -1, -1):
            if directions[i] == directions[-1]:
                streak += 1
            else:
                break
        feat["patch_streak"]           = streak
        feat["patch_streak_direction"] = directions[-1]
        feat["patch_streak_n"]         = streak
    else:
        feat["patch_streak"]           = 0
        feat["patch_streak_direction"] = "none"
        feat["patch_streak_n"]         = 0

    # ── 맵 의존도 피처 ─────────────────────────────────────────────────────────
    if map_dep_df is not None:
        act_name = IDX_ACT.get(act_idx)
        row = map_dep_df[(map_dep_df["agent"] == agent) & (map_dep_df["act"] == act_name)]
        if not row.empty:
            r = row.iloc[0]
            feat["map_dep_score"]       = float(r["map_dep_score"])
            feat["top_map_in_rotation"] = int(r["in_rotation"])
            feat["effective_map_dep"]   = float(r["effective_map_dep"])
            vct_low = float(feat.get("vct_pr_last", 0) or 0) < 15.0
            feat["map_explains_vct_drop"] = float(r["map_dep_score"]) if (
                int(r["in_rotation"]) == 0 and vct_low
            ) else 0.0
        else:
            feat["map_dep_score"] = feat["top_map_in_rotation"] = feat["effective_map_dep"] = 1.0
            feat["map_explains_vct_drop"] = 0.0
    else:
        feat["map_dep_score"] = feat["top_map_in_rotation"] = feat["effective_map_dep"] = 1.0
        feat["map_explains_vct_drop"] = 0.0

    # ── 프로 vs 랭크 픽률 비율 ─────────────────────────────────────────────────
    vct_pr_last_ = float(feat.get("vct_pr_last", 0) or 0)
    rank_pr_      = float(feat.get("rank_pr", 0) or 0)
    feat["pro_rank_ratio"] = vct_pr_last_ / max(rank_pr_, 0.5)

    # ── 요원 설계 의도 피처 ────────────────────────────────────────────────────
    design   = AGENT_DESIGN.get(agent, _DEFAULT_DESIGN)
    audience = design["design_audience"]
    feat["agent_team_synergy"]   = design["team_synergy"]
    feat["agent_complexity"]     = design["complexity"]
    feat["agent_replaceability"] = design.get("replaceability", 0.5)
    feat["design_rank_only"]     = 1.0 if audience == "rank" else 0.0
    feat["design_pro_only"]      = 1.0 if audience == "pro"  else 0.0

    rank_low = rank_pr_ < 3.0
    vct_low  = vct_pr_last_ < 5.0
    is_both  = (audience == "both")
    is_rank  = (audience == "rank")
    is_pro   = (audience == "pro")

    feat["rank_low_unexpected"] = float(rank_low and not is_pro and not is_rank)
    feat["vct_low_unexpected"]  = float(vct_low and not is_rank)
    feat["both_weak_signal"]    = float(rank_low and vct_low and is_both)

    # ── 킷 가치 피처 ───────────────────────────────────────────────────────────
    feat["kit_score"] = compute_kit_score(agent)
    flags = get_kit_flags(agent)
    feat["has_smoke"]        = float(flags["has_smoke"])
    feat["has_cc"]           = float(flags["has_cc"])
    feat["has_info"]         = float(flags["has_info"])
    feat["has_mobility"]     = float(flags["has_mobility"])
    feat["has_heal"]         = float(flags["has_heal"])
    feat["has_revive"]       = float(flags["has_revive"])
    feat["high_value_smoke"] = float(flags["high_value_smoke"])
    feat["high_value_cc"]    = float(flags["high_value_cc"])
    feat["kit_pr_gap"]       = feat["kit_score"] - (rank_pr_ / 5.0)
    feat["replaceable_low_pr"] = float(design.get("replaceability", 0.5) > 0.6 and rank_low)
    low_value_kit = feat["kit_score"] < 2.3
    feat["low_kit_weak_signal"] = float(low_value_kit and rank_low and vct_low)

    # ── 요원 종합 티어 ─────────────────────────────────────────────────────────
    feat["agent_tier_score"] = AGENT_TIER_SCORE.get(design.get("agent_tier", "B"), 2)
    feat["tier_gap"]         = round(feat["kit_score"] - feat["agent_tier_score"], 3)
    feat["op_synergy"]       = float(design.get("op_synergy", False))
    feat["geo_synergy"]      = {"high": 2.0, "medium": 1.0, "low": 0.0}.get(
        design.get("geo_synergy", "medium"), 1.0
    )
    _geo_bonus = 0
    for _slot, _sk in AGENT_KIT.get(agent, _DEFAULT_KIT).items():
        if "geo_ceiling" in _sk:
            _geo_bonus += SKILL_TIER_SCORE.get(_sk["geo_ceiling"], 2) - SKILL_TIER_SCORE.get(_sk["tier"], 2)
    feat["geo_bonus"] = float(_geo_bonus)

    # ── 킷 × 픽률 교차 피처 ────────────────────────────────────────────────────
    feat["smoke_vct_dom"]      = float(flags["high_value_smoke"]) * min(vct_pr_last_ / 10.0, 3.0)
    feat["mobility_rank_dom"]  = float(flags["has_mobility"])     * min(rank_pr_      / 5.0,  3.0)
    feat["kit_x_rank_pr"]      = round(feat["kit_score"] * min(rank_pr_ / 5.0, 3.0), 3)
    feat["heal_low_rank"]      = float(flags["has_heal"]     and rank_pr_ < 3.0)
    feat["revive_low_rank"]    = float(flags["has_revive"]   and rank_pr_ < 3.0)
    feat["info_low_vct"]       = float(flags["has_info"]     and vct_pr_last_ < 5.0 and vct_pr_last_ > 0)
    feat["cc_low_rank"]        = float(flags["has_cc"]       and rank_pr_ < 2.0)
    feat["smoke_low_vct"]      = float(flags["has_smoke"]    and vct_pr_last_ < 3.0)
    feat["rank_dominant_flag"] = feat["design_rank_only"]

    # ── 실력 천장 프록시 ────────────────────────────────────────────────────────
    if skill_ceiling_proxy:
        feat["skill_ceiling_score"] = skill_ceiling_proxy.get(agent, 0.5)
    else:
        feat["skill_ceiling_score"] = int(design.get("skill_ceiling", 5)) / 10.0

    vct_peak_ = float(feat.get("vct_pr_peak_all", 0) or 0)
    feat["pro_dominant_flag"] = 1.0 if (
        is_pro or (vct_pr_last_ > 5.0 or vct_peak_ > 20.0) and rank_pr_ < 3.0
    ) else 0.0

    # ── 맵 다양성 피처 ─────────────────────────────────────────────────────────
    if map_versatility_dict is not None:
        act_name_mv = IDX_ACT.get(act_idx)
        mv = map_versatility_dict.get((act_name_mv, agent), {})
        feat["map_versatility"]   = float(mv.get("map_versatility", 5))
        feat["map_hhi"]           = float(mv.get("map_hhi", 0.3))
        feat["map_specialist"]    = float(mv.get("map_specialist", 0.0))
        feat["specialist_low_pr"] = float(mv.get("map_specialist", 0.0) == 1.0 and rank_low)
        feat["versatile_nerf_signal"] = round(
            (1.0 - float(mv.get("map_hhi", 0.3))) * min(rank_pr_ / 5.0, 3.0), 3
        )
    else:
        feat["map_versatility"]       = 5.0
        feat["map_hhi"]               = 0.3
        feat["map_specialist"]        = 0.0
        feat["specialist_low_pr"]     = 0.0
        feat["versatile_high_pr"]     = 0.0

    # ── 전성기 대비 현재 픽률 ──────────────────────────────────────────────────
    rank_pr      = float(feat.get("rank_pr", 0) or 0)
    rank_pr_peak = float(feat.get("rank_pr_peak", 0) or 0)
    feat["rank_pr_vs_peak"] = rank_pr / rank_pr_peak if rank_pr_peak > 0 else 1.0

    # ── 상호작용 파생 피처 ─────────────────────────────────────────────────────
    d = feat.get("last_direction", "none")
    c = feat.get("last_combined", "UNKNOWN")

    feat["buff_miss_flag"] = 1.0 if (d == "buff" and c in ("DUAL_MISS", "RANK_ONLY_MISS")) else 0.0
    feat["nerf_miss_flag"] = 1.0 if (d == "nerf" and c in ("DUAL_MISS", "RANK_ONLY_MISS")) else 0.0
    feat["buff_hit_flag"]  = 1.0 if (d == "buff" and c in ("DUAL_HIT",  "RANK_ONLY_HIT"))  else 0.0
    feat["nerf_hit_flag"]  = 1.0 if (d == "nerf" and c in ("DUAL_HIT",  "RANK_ONLY_HIT"))  else 0.0

    hit_types  = ("DUAL_HIT",  "RANK_ONLY_HIT")
    miss_types = ("DUAL_MISS", "RANK_ONLY_MISS")
    fail_types = ("PRO_FAIL",  "RANK_FAIL", "MIXED")
    if d == "buff":
        if c in hit_types:   dir_verdict_code = +2.0
        elif c in miss_types: dir_verdict_code = +1.0
        elif c in fail_types: dir_verdict_code = +0.5
        else:                 dir_verdict_code =  0.0
    elif d == "nerf":
        if c in hit_types:   dir_verdict_code = -2.0
        elif c in miss_types: dir_verdict_code = -1.0
        elif c in fail_types: dir_verdict_code = -0.5
        else:                 dir_verdict_code =  0.0
    else:
        dir_verdict_code = 0.0
    feat["dir_verdict_code"] = dir_verdict_code

    wr_vs50 = float(feat.get("rank_wr_vs50", 0) or 0)
    if d == "buff":
        feat["strength_vs_direction"] = wr_vs50
    elif d == "nerf":
        feat["strength_vs_direction"] = -wr_vs50
    else:
        feat["strength_vs_direction"] = 0.0

    return feat
