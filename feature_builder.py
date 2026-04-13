"""
feature_builder.py
(요원, 액트) 기준 피처 계산 함수군
"""

import numpy as np
import pandas as pd

from agent_data import (
    AGENT_DESIGN, _DEFAULT_DESIGN,
    AGENT_KIT, _DEFAULT_KIT,
    AGENT_TIER_SCORE, SKILL_TIER_SCORE,
    AGENT_ROLE,
    IDX_ACT,
    compute_kit_score, get_kit_flags,
)
from label_builder import dominant_trigger

# 요원별 역대 평균 픽률 (training_data.csv rank_pr_t-1 기준)
# 팬덤/인기도 베이스라인: 이 이상으로 픽되면 성능 외 팬덤이 픽률을 지탱한다는 신호
AGENT_PR_BASELINE: dict[str, float] = {
    "Astra":     2.49,
    "Breach":    2.05,
    "Brimstone": 2.42,
    "Chamber":   9.51,
    "Clove":    11.82,
    "Cypher":    5.36,
    "Deadlock":  1.82,
    "Fade":      5.46,
    "Gekko":     3.05,
    "Harbor":    0.43,
    "Iso":       1.81,
    "Jett":     13.93,
    "KAYO":      4.10,
    "Killjoy":   3.76,
    "Neon":      1.92,
    "Omen":      6.96,
    "Phoenix":   1.83,
    "Raze":      7.27,
    "Reyna":     9.36,
    "Sage":      6.35,
    "Skye":      4.57,
    "Sova":      6.39,
    "Tejo":      1.89,
    "Viper":     3.59,
    "Vyse":      2.25,
    "Waylay":    2.00,   # 신규 요원, 베이스라인 미확정 → 평균값 사용
    "Yoru":      1.89,
}

# 상대 픽률 비교에 사용할 유틸 타입 목록 (랭크 전용 피처)
_UTIL_RATIO_TYPES = ["smoke", "cc", "info", "mobility", "heal", "revive", "flash", "blind"]


def precompute_role_util_avgs(rank_df: "pd.DataFrame") -> dict:
    """역할군·유틸 타입별 액트 평균 픽률 사전 계산 (랭크 전용).

    각 액트에서 같은 역할군/같은 유틸 타입을 가진 요원들의 픽률 평균을 구해
    상대 픽률 비율 피처 계산에 사용.

    Returns
    -------
    dict: (act_idx, agent) → {
        "role_rank_pr_ratio": float,
        "util_smoke_rank_pr_ratio": float | nan,
        ...
    }
    """
    # 요원별 보유 유틸 타입 집합 사전 계산
    agent_util_types: dict[str, set] = {}
    for ag in AGENT_ROLE:
        kit = AGENT_KIT.get(ag, _DEFAULT_KIT)
        types: set[str] = set()
        for v in kit.values():
            types.add(v["type"])
            if "secondary_type" in v:
                types.add(v["secondary_type"])
        agent_util_types[ag] = types

    result: dict[tuple, dict] = {}

    # 액트별 요원 픽률: 같은 (act_idx, agent) 중복이면 평균 사용
    act_agent_pr = (
        rank_df.groupby(["act_idx", "agent"])["pick_rate_pct"]
        .mean()
        .reset_index()
    )

    for act_idx, grp in act_agent_pr.groupby("act_idx"):
        pr_map: dict[str, float] = dict(zip(grp["agent"], grp["pick_rate_pct"]))

        # 역할군 평균
        role_prs: dict[str, list] = {}
        for ag, pr in pr_map.items():
            role = AGENT_ROLE.get(ag)
            if role:
                role_prs.setdefault(role, []).append(pr)
        role_avg: dict[str, float] = {r: float(np.mean(ps)) for r, ps in role_prs.items()}

        # 유틸 타입 평균
        util_prs: dict[str, list] = {}
        for ag, pr in pr_map.items():
            for ut in agent_util_types.get(ag, set()):
                if ut in _UTIL_RATIO_TYPES:
                    util_prs.setdefault(ut, []).append(pr)
        util_avg: dict[str, float] = {ut: float(np.mean(ps)) for ut, ps in util_prs.items()}

        # 메타 전체 평균/표준편차 (agent identity 없이 "이 요원이 얼마나 튀냐" 포착)
        all_prs   = list(pr_map.values())
        meta_mean = float(np.mean(all_prs)) if all_prs else 5.0
        meta_std  = float(np.std(all_prs))  if len(all_prs) > 1 else 1.0

        for ag, pr in pr_map.items():
            role = AGENT_ROLE.get(ag)
            entry: dict[str, float] = {}

            # 역할군 내 상대 픽률
            if role and role_avg.get(role, 0) > 0:
                entry["role_rank_pr_ratio"] = pr / role_avg[role]
            else:
                entry["role_rank_pr_ratio"] = 1.0

            # 메타 전체 대비 픽률: rank_pr / 전체평균 (비율), (rank_pr - 평균) / std (z점수)
            entry["rank_pr_rel_meta"] = pr / meta_mean if meta_mean > 0 else 1.0
            entry["rank_pr_zscore"]   = (pr - meta_mean) / max(meta_std, 0.5)

            # 유틸 타입별 보유 여부 (0/1 이진)
            # 비율 대신 보유 여부만 인코딩 → NaN 제거, 요원 정체성 피처로 사용
            ag_types = agent_util_types.get(ag, set())
            for ut in _UTIL_RATIO_TYPES:
                key = f"util_{ut}_rank_pr_ratio"
                entry[key] = 1.0 if ut in ag_types else 0.0

            result[(int(act_idx), ag)] = entry

    return result


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


def build_skill_stat_features(agent: str, agent_skills: dict) -> dict:
    """agent_skills.json 기반 절대 강도 피처 (Phase 4)

    각 요원의 현재 스킬 수치를 추가 피처로 활용:
    - 비용 구조 (creds, ult_points)
    - 시그니처(E) 스탯 수 / 핵심 스탯 값
    - 킷 전체 복잡도
    """
    feat: dict = {}

    ag = agent_skills.get(agent, {})

    e = ag.get("E", {})
    feat["sig_creds"]   = float(e.get("creds", 0) or 0)
    feat["sig_charges"] = float(e.get("charges", 1) or 1)
    e_stats = e.get("stats", {})
    feat["sig_stat_count"] = float(len(e_stats))

    x = ag.get("X", {})
    feat["ult_points"] = float(x.get("ult_points", 7) or 7)

    c = ag.get("C", {})
    q = ag.get("Q", {})
    feat["total_skill_cost"] = float((c.get("creds", 0) or 0) + (q.get("creds", 0) or 0))

    def _first_stat(stats: dict, *keywords):
        for name, sv in stats.items():
            nl = name.lower()
            if any(kw in nl for kw in keywords):
                v = sv.get("value")
                if v is not None:
                    return float(v)
        return np.nan

    feat["sig_cooldown_val"] = _first_stat(e_stats, "cooldown", "recharge", "recovery")
    feat["sig_duration_val"] = _first_stat(e_stats, "duration")
    feat["sig_damage_val"]   = _first_stat(e_stats, "damage")
    feat["has_cooldown_sig"] = float(not np.isnan(feat["sig_cooldown_val"]))
    feat["has_damage_sig"]   = float(not np.isnan(feat["sig_damage_val"]))

    total_stats = sum(len(ag.get(sl, {}).get("stats", {})) for sl in ("C", "Q", "E", "X"))
    feat["skill_stat_count_total"] = float(total_stats)

    return feat


_SKILL_FEAT_DEFAULTS = {
    "sig_creds": np.nan, "sig_charges": np.nan, "sig_stat_count": np.nan,
    "ult_points": np.nan, "total_skill_cost": np.nan,
    "sig_cooldown_val": np.nan, "sig_duration_val": np.nan, "sig_damage_val": np.nan,
    "has_cooldown_sig": 0.0, "has_damage_sig": 0.0,
    "skill_stat_count_total": np.nan,
}


def build_features(agent, act_idx, rank_df, vct_df, step1_df, map_dep_df=None,
                   map_versatility_dict=None, pn_df=None, skill_ceiling_proxy=None,
                   role_util_dict=None, agent_skills=None):
    """
    (요원, 액트) 기준 현재 상태 피처 계산
    """
    feat = {}

    # ── 마지막 패치 액트 인덱스 선행 계산 ────────────────────────────────────────
    _ag_hist_pre = step1_df[
        (step1_df["agent"] == agent) &
        (step1_df["patch_act_idx"] <= act_idx)
    ].sort_values("patch_act_idx")
    _last_patch_act_idx = int(_ag_hist_pre["patch_act_idx"].max()) if not _ag_hist_pre.empty else None

    # ── 랭크 피처 (마지막 패치 이후 평균) ────────────────────────────────────────
    ag_rank  = rank_df[rank_df["agent"] == agent].sort_values("act_idx")
    all_hist = ag_rank[ag_rank["act_idx"] <= act_idx]

    # 마지막 패치 이후 구간 (없으면 최근 3액트 폴백)
    if _last_patch_act_idx is not None:
        post_patch = all_hist[all_hist["act_idx"] >= _last_patch_act_idx]
        cur_rank = post_patch if not post_patch.empty else all_hist.tail(3)
    else:
        cur_rank = all_hist.tail(3)

    # 전체 유효 랭크 데이터 액트 수 (데이터 신뢰도 프록시)
    feat["n_rank_acts"] = len(all_hist)

    if not cur_rank.empty:
        feat["rank_pr"]      = float(cur_rank["pick_rate_pct"].mean())
        feat["rank_wr"]      = float(cur_rank["win_rate_pct"].mean())
        feat["rank_wr_vs50"] = feat["rank_wr"] - 50.0
        if len(cur_rank) >= 2:
            pr_vals = cur_rank["pick_rate_pct"].values
            x = np.arange(len(pr_vals))
            feat["rank_pr_slope"] = float(np.polyfit(x, pr_vals, 1)[0])
        else:
            feat["rank_pr_slope"] = 0.0
        # rank_pr_avg3: 최근 3액트 (단기 추세 포착용, rank_pr와 구분)
        feat["rank_pr_avg3"] = float(all_hist.tail(3)["pick_rate_pct"].mean())
        feat["rank_pr_peak"]       = float(all_hist["pick_rate_pct"].max())
        # 로컬 피크: 최근 5액트 내 최고값 (출시 초반 hype 피크에 끌리지 않도록)
        feat["rank_pr_local_peak"] = float(all_hist.tail(5)["pick_rate_pct"].max())
        # rank_pr_delta: 최근 2액트 간 픽률 변화 (단기 방향성)
        if len(all_hist) >= 2:
            _pr2 = all_hist.tail(2)["pick_rate_pct"].values
            feat["rank_pr_delta"] = float(_pr2[-1] - _pr2[-2])
        else:
            feat["rank_pr_delta"] = 0.0

        # 요원 자신의 역사적 WR 평균 (vs 50 단순 비교 대신 "자기 기준 이탈" 포착)
        if "win_rate_pct" in all_hist.columns:
            feat["rank_wr_hist_mean"] = float(all_hist["win_rate_pct"].mean())
        else:
            feat["rank_wr_hist_mean"] = 50.0

        # PR 슬로프 5액트 (3액트보다 긴 추세 — 서서히 하락하는 버프 후보 포착)
        _hist5 = all_hist.tail(5)
        if len(_hist5) >= 3:
            _pv5 = _hist5["pick_rate_pct"].values
            feat["pr_slope_5act"] = float(np.polyfit(np.arange(len(_pv5)), _pv5, 1)[0])
        else:
            feat["pr_slope_5act"] = 0.0

        # PR as fraction of peak (정규화된 하락 폭 — 피크 대비 얼마나 내려왔나)
        _pr_peak_all = float(all_hist["pick_rate_pct"].max())
        feat["pr_pct_of_peak"] = float(feat.get("rank_pr", 0.0)) / max(_pr_peak_all, 0.01)

        # PR 3액트 전 대비 % 변화 (중기 하락/상승 속도)
        if len(all_hist) >= 4:
            _pr_3ago = float(all_hist.iloc[-4]["pick_rate_pct"])
            feat["rank_pr_pct_change_3act"] = (float(feat.get("rank_pr", 0.0)) - _pr_3ago) / max(_pr_3ago, 0.01)
        else:
            feat["rank_pr_pct_change_3act"] = 0.0

    # ── VCT 피처 ───────────────────────────────────────────────────────────────
    # [모델 피처] vct_pr_last / vct_wr_last = 가장 최근 액트 기준 (신호 강도 유지)
    #   → 같은 액트 내 patch_after 이벤트 우선 (pre/post 혼재 노이즈 방지)
    # [표시용]    vct_pr_post / vct_wr_post = 마지막 패치 이후 누적 가중 평균
    #   → predict_service에서 display에 사용, 모델에는 넣지 않음

    # pn_df에서도 마지막 패치 액트 확인 (step1_df 없는 신규 요원 대비)
    _vct_patch_act_idx = _last_patch_act_idx
    if _vct_patch_act_idx is None and pn_df is not None:
        _pn_ag = pn_df[(pn_df["agent"] == agent) & (pn_df["act_idx"] <= act_idx)]
        if not _pn_ag.empty:
            _vct_patch_act_idx = int(_pn_ag["act_idx"].max())

    ag_vct  = vct_df[vct_df["agent"] == agent].sort_values(["act_idx", "event_order"])
    pre_vct = ag_vct[ag_vct["act_idx"] <= act_idx]
    if not pre_vct.empty:
        vct_with_picks = pre_vct[pre_vct["picks"] > 0]
        if not vct_with_picks.empty:
            # ── [모델] 가장 최근 액트 ────────────────────────────────────────
            last_vct_act = int(vct_with_picks["act_idx"].max())
            last_vct_evs = vct_with_picks[vct_with_picks["act_idx"] == last_vct_act]
            # 같은 액트 내 patch_after 이벤트 우선
            if "patch_after" in last_vct_evs.columns:
                _pp = last_vct_evs[last_vct_evs["patch_after"].notna()]
                if not _pp.empty:
                    last_vct_evs = _pp

            total_picks = last_vct_evs["picks"].sum()
            total_maps  = last_vct_evs["total_maps"].sum()
            feat["vct_pr_last"] = float(
                (last_vct_evs["pick_rate_pct"] * last_vct_evs["total_maps"]).sum() / total_maps
            ) if total_maps > 0 else 0.0

            # VCT 승률: 픽 수 적을수록 50%로 수렴 (Bayesian shrinkage)
            # prior=20 → 픽 5개이면 50% 쪽으로 80% 수렴, 픽 40개이면 거의 raw 유지
            _VCT_WR_PRIOR = 8
            _raw_vct_wr = float(
                (last_vct_evs["win_rate_pct"] * last_vct_evs["picks"]).sum() / total_picks
            )
            feat["vct_wr_last"] = (
                _raw_vct_wr * total_picks + 50.0 * _VCT_WR_PRIOR
            ) / (total_picks + _VCT_WR_PRIOR)
            feat["vct_last_act_idx"] = last_vct_act
            feat["vct_data_lag"]     = act_idx - last_vct_act

            # 이벤트명 추출 (가장 최근 액트 기준)
            import re as _re
            _phases = set()
            for _n in last_vct_evs["event"].unique():
                _m = _re.search(r'(Stage \d+|Kickoff|Masters \w+|Champions|LOCK//IN)\s*(\d{4})', _n)
                if _m:
                    _phases.add(_m.group(0))
            feat["vct_last_event_name"] = " / ".join(sorted(_phases)) if _phases else (list(last_vct_evs["event"].unique())[0] if len(last_vct_evs) else "")

            # ── [표시용] 패치 이후 누적 집계 ────────────────────────────────
            if _vct_patch_act_idx is not None:
                _post_all = vct_with_picks[vct_with_picks["act_idx"] >= _vct_patch_act_idx]
                _in_pa    = _post_all[_post_all["act_idx"] == _vct_patch_act_idx]
                _after_pa = _post_all[_post_all["act_idx"] > _vct_patch_act_idx]
                if "patch_after" in _in_pa.columns:
                    _in_pa_ok = _in_pa[_in_pa["patch_after"].notna()]
                    if not _in_pa_ok.empty:
                        _in_pa = _in_pa_ok
                    elif _after_pa.empty:
                        _in_pa = pd.DataFrame()
                _acc_evs = pd.concat([_in_pa, _after_pa])
                if _acc_evs.empty:
                    _acc_evs = last_vct_evs
            else:
                _acc_evs = last_vct_evs

            _ap = _acc_evs["picks"].sum()
            _am = _acc_evs["total_maps"].sum()
            feat["vct_pr_post"] = float(
                (_acc_evs["pick_rate_pct"] * _acc_evs["total_maps"]).sum() / _am
            ) if _am > 0 else feat["vct_pr_last"]
            if _ap > 0:
                _raw_post_wr = float(
                    (_acc_evs["win_rate_pct"] * _acc_evs["picks"]).sum() / _ap
                )
                feat["vct_wr_post"] = (
                    _raw_post_wr * _ap + 50.0 * _VCT_WR_PRIOR
                ) / (_ap + _VCT_WR_PRIOR)
            else:
                feat["vct_wr_post"] = feat["vct_wr_last"]
        else:
            feat["vct_pr_last"]      = 0.0
            feat["vct_wr_last"]      = 50.0
            feat["vct_last_act_idx"] = -1
            feat["vct_data_lag"]     = 99
            feat["vct_pr_post"]      = 0.0
            feat["vct_wr_post"]      = 50.0
        feat["vct_pr_avg"]  = float(vct_with_picks["pick_rate_pct"].mean()) if not vct_with_picks.empty else 0.0
        feat["vct_pre_n"]   = len(pre_vct)
    else:
        feat["vct_pr_last"]      = 0.0
        feat["vct_wr_last"]      = np.nan
        feat["vct_pr_avg"]       = 0.0
        feat["vct_pre_n"]        = 0
        feat["vct_last_act_idx"] = -1
        feat["vct_data_lag"]     = 99
        feat["vct_pr_post"]      = 0.0
        feat["vct_wr_post"]      = np.nan

    feat["vct_profile"]    = compute_vct_profile(feat.get("vct_pr_avg"))
    feat["vct_pr_peak_all"] = float(pre_vct["pick_rate_pct"].max()) if not pre_vct.empty else 0.0

    recent_vct = pre_vct.tail(3)
    if len(recent_vct) >= 2:
        vpr = recent_vct["pick_rate_pct"].values
        feat["vct_pr_slope"] = float(np.polyfit(np.arange(len(vpr)), vpr, 1)[0])
        feat["vct_pr_delta"]  = float(vpr[-1] - vpr[-2])
    else:
        feat["vct_pr_slope"] = 0.0
        feat["vct_pr_delta"]  = 0.0

    if "rank_pr" in feat and feat.get("vct_pr_avg", 0) > 0:
        feat["rank_vct_gap"] = feat["rank_pr"] - feat["vct_pr_avg"]
    else:
        feat["rank_vct_gap"] = np.nan

    # ── Excess 피처 (urgency 도메인 룰 → 모델 피처로 전환) ─────────────────────
    # VCT 초과: 현재 VCT 픽률이 역대 평균 대비 얼마나 높은가
    _vct_avg = feat.get("vct_pr_avg", 0.0) or 0.0
    _vct_last = feat.get("vct_pr_last", 0.0) or 0.0
    _wr_u = feat.get("rank_wr_vs50", 0.0) or 0.0
    feat["vct_pr_excess"] = max(_vct_last - _vct_avg, 0.0)
    # 인터랙션: VCT 초과 × 랭크 승률 우위 (높은 VCT + 이기는 팀에서 주로 픽 = 너프 핵심 트리거)
    feat["vct_excess_x_wr"] = feat["vct_pr_excess"] * max(_wr_u, 0.0)
    # 랭크 픽률 초과: 역대 평균 대비 현재 랭크 픽률
    _rank_pr = feat.get("rank_pr", 0.0) or 0.0
    _pr_base = AGENT_PR_BASELINE.get(agent, 5.0)
    feat["rank_pr_excess"] = max(_rank_pr - _pr_base, 0.0)
    # 인터랙션: 랭크 픽률 초과 × 승률 우위
    feat["rank_excess_x_wr"] = feat["rank_pr_excess"] * max(_wr_u, 0.0)

    # ── Step 1 이력 피처 ───────────────────────────────────────────────────────
    hist = step1_df[
        (step1_df["agent"] == agent) &
        (step1_df["patch_act_idx"] <= act_idx)
    ].sort_values("patch_act_idx")

    feat["n_total_patches"] = len(hist)
    feat["n_nerf_patches"]  = int((hist["direction"] == "nerf").sum())
    feat["n_buff_patches"]  = int((hist["direction"] == "buff").sum())

    # 마지막 BUFF / NERF 패치로부터 경과 액트 (방향별 분리)
    _buff_hist = hist[hist["direction"] == "buff"]
    _nerf_hist = hist[hist["direction"] == "nerf"]
    feat["last_buff_acts_ago"] = (
        act_idx - int(_buff_hist["patch_act_idx"].max()) if not _buff_hist.empty else 99
    )
    feat["last_nerf_acts_ago"] = (
        act_idx - int(_nerf_hist["patch_act_idx"].max()) if not _nerf_hist.empty else 99
    )

    # patch_notes에서 최신 buff/nerf 액트 조회 (training_data보다 최신 패치 반영)
    pn_last_act_idx = -1
    pn_last_bn = None
    if pn_df is not None:
        pn_agent_bn = pn_df[
            (pn_df["agent"] == agent) &
            (pn_df["act_idx"] <= act_idx) &
            (pn_df["direction"].isin(["buff", "nerf"]))
        ].sort_values("act_idx")
        if not pn_agent_bn.empty:
            pn_last_act_idx = int(pn_agent_bn["act_idx"].max())
            pn_last_bn = pn_agent_bn[pn_agent_bn["act_idx"] == pn_last_act_idx]

    # training_data 마지막 패치 액트
    hist_last_act_idx = int(hist["patch_act_idx"].max()) if not hist.empty else -1

    # 더 최신 소스를 우선 사용
    use_pn_as_last = pn_last_act_idx > hist_last_act_idx

    if hist_last_act_idx >= 0 or pn_last_act_idx >= 0:
        effective_last_act = max(hist_last_act_idx, pn_last_act_idx)
        feat["acts_since_patch"] = act_idx - effective_last_act
    else:
        feat["acts_since_patch"] = 99

    if not hist.empty and not use_pn_as_last:
        # training_data가 더 최신이거나 동일: 기존 로직
        last = hist.iloc[-1]
        feat["last_direction"]    = last.get("direction", "none")
        feat["last_combined"]     = last.get("combined_verdict", "UNKNOWN")
        feat["last_rank_verdict"] = last.get("rank_verdict", "NO_DATA")
        feat["last_vct_verdict"]  = last.get("vct_verdict", "NO_DATA")
        feat["last_max_skill_w"]  = float(last.get("max_skill_weight", 2.0) or 2.0)
        last_act_idx = hist_last_act_idx
        if pn_df is not None:
            pn_last = pn_df[
                (pn_df["agent"] == agent) &
                (pn_df["act_idx"] == last_act_idx) &
                (pn_df["direction"].isin(["nerf", "buff"]))
            ]
            feat["last_trigger_type"] = dominant_trigger(pn_last)
        else:
            feat["last_trigger_type"] = "rank"
        _last_pr_pre  = last.get("rank_pr_t-1",  None)
        _last_wr_pre  = last.get("rank_wr_t-1",  None)
        _last_wr_post = last.get("rank_wr_t+1",  None)
        feat["last_pr_pre"]  = float(_last_pr_pre)  if _last_pr_pre  is not None and not pd.isna(_last_pr_pre)  else np.nan
        feat["last_wr_pre"]  = float(_last_wr_pre)  if _last_wr_pre  is not None and not pd.isna(_last_wr_pre)  else np.nan
        feat["last_wr_post"] = float(_last_wr_post) if _last_wr_post is not None and not pd.isna(_last_wr_post) else np.nan
    elif pn_last_bn is not None:
        # patch_notes가 더 최신: direction/trigger는 pn에서, 나머지는 기본값
        dirs = pn_last_bn["direction"].value_counts()
        feat["last_direction"]    = dirs.index[0] if not dirs.empty else "none"
        feat["last_combined"]     = "UNKNOWN"   # pn에서는 verdict 없음
        feat["last_rank_verdict"] = "NO_DATA"
        feat["last_vct_verdict"]  = "NO_DATA"
        feat["last_max_skill_w"]  = 2.0
        feat["last_trigger_type"] = dominant_trigger(pn_last_bn)
        feat["last_pr_pre"]  = np.nan
        feat["last_wr_pre"]  = np.nan
        feat["last_wr_post"] = np.nan
    else:
        feat["last_direction"]    = "none"
        feat["last_combined"]     = "UNKNOWN"
        feat["last_rank_verdict"] = "NO_DATA"
        feat["last_vct_verdict"]  = "NO_DATA"
        feat["last_max_skill_w"]  = 2.0
        feat["last_trigger_type"] = "rank"
        feat["last_pr_pre"]  = np.nan
        feat["last_wr_pre"]  = np.nan
        feat["last_wr_post"] = np.nan

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

    # rank_pr_rel_meta를 threshold 기반 피처에 미리 추출 (role_util_dict보다 앞서 사용)
    _rel_meta_ = 1.0
    if role_util_dict is not None:
        _ru_early = role_util_dict.get((act_idx, agent), {})
        _rel_meta_ = float(_ru_early.get("rank_pr_rel_meta", 1.0))

    # ── 요원 설계 의도 피처 ────────────────────────────────────────────────────
    design   = AGENT_DESIGN.get(agent, _DEFAULT_DESIGN)
    audience = design["design_audience"]
    feat["agent_team_synergy"]   = design["team_synergy"]
    feat["agent_complexity"]     = design["complexity"]
    feat["agent_replaceability"] = design.get("replaceability", 0.5)
    feat["design_rank_only"]     = 1.0 if audience == "rank" else 0.0
    feat["design_pro_only"]      = 1.0 if audience == "pro"  else 0.0

    rank_low = _rel_meta_ < 0.7
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
    feat["has_flash"]        = float(flags["has_flash"])
    feat["has_blind"]        = float(flags["has_blind"])
    feat["high_value_smoke"] = float(flags["high_value_smoke"])
    feat["high_value_cc"]    = float(flags["high_value_cc"])
    feat["kit_pr_gap"]       = feat["kit_score"] - min(_rel_meta_, 3.0)
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
    feat["mobility_rank_dom"]  = float(flags["has_mobility"])     * min(_rel_meta_, 3.0)
    feat["kit_x_rank_pr"]      = round(feat["kit_score"] * min(_rel_meta_, 3.0), 3)
    feat["heal_low_rank"]      = float(flags["has_heal"]     and _rel_meta_ < 0.7)
    feat["revive_low_rank"]    = float(flags["has_revive"]   and _rel_meta_ < 0.7)
    feat["info_low_vct"]       = float(flags["has_info"]     and vct_pr_last_ < 5.0 and vct_pr_last_ > 0)
    feat["cc_low_rank"]        = float(flags["has_cc"]       and _rel_meta_ < 0.5)
    feat["smoke_low_vct"]      = float(flags["has_smoke"]    and vct_pr_last_ < 3.0)
    feat["rank_dominant_flag"] = feat["design_rank_only"]

    # ── 실력 천장 프록시 ────────────────────────────────────────────────────────
    if skill_ceiling_proxy:
        feat["skill_ceiling_score"] = skill_ceiling_proxy.get(agent, 0.5)
    else:
        feat["skill_ceiling_score"] = int(design.get("skill_ceiling", 5)) / 10.0

    vct_peak_ = float(feat.get("vct_pr_peak_all", 0) or 0)
    # 프로에서 활발하고(vct_pr > 15%) 랭크도 어느 정도 있는 경우 → pro_dominant
    # 혹은 design이 pro_only
    feat["pro_dominant_flag"] = 1.0 if (
        is_pro or vct_pr_last_ >= 15.0
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
            (1.0 - float(mv.get("map_hhi", 0.3))) * min(_rel_meta_, 3.0), 3
        )
    else:
        feat["map_versatility"]       = 5.0
        feat["map_hhi"]               = 0.3
        feat["map_specialist"]        = 0.0
        feat["specialist_low_pr"]     = 0.0
        feat["versatile_high_pr"]     = 0.0


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

    # ── 현재 승률 × 마지막 패치 방향 복합 신호 ────────────────────────────────
    # 패치 후 WR 변화는 액트별 노이즈(±0.2%)로 의미 없음.
    # 대신 "현재 WR 상태" × "마지막 패치 방향" 조합으로 패치 효과를 평가.
    _cur_wr_vs50 = float(feat.get("rank_wr_vs50", 0) or 0)
    _WR_WEAK   = -2.0   # 현재 WR 48% 이하 = 약함
    _WR_STRONG =  2.0   # 현재 WR 52% 이상 = 강함

    # 버프 MISS + 현재 WR도 여전히 약함 → 버프가 픽률도 승률도 못 살린 진짜 실패
    feat["buff_miss_wr_weak"]   = 1.0 if (d == "buff" and c in miss_types and _cur_wr_vs50 < _WR_WEAK) else 0.0
    # 너프 MISS + 현재 WR도 여전히 강함 → 너프가 픽률도 승률도 못 잡은 이중 실패
    feat["nerf_miss_wr_strong"] = 1.0 if (d == "nerf" and c in miss_types and _cur_wr_vs50 > _WR_STRONG) else 0.0
    # 너프 HIT (PR 반응) + 현재 WR은 여전히 강함 → 조정 너프 가능성 신호
    feat["nerf_hit_wr_strong"]  = 1.0 if (d == "nerf" and c not in miss_types and _cur_wr_vs50 > _WR_STRONG) else 0.0
    # 버프 HIT (PR 반응) + 현재 WR은 여전히 약함 → 추가 버프 가능성 신호
    feat["buff_hit_wr_weak"]    = 1.0 if (d == "buff" and c not in miss_types and _cur_wr_vs50 < _WR_WEAK) else 0.0

    wr_vs50 = float(feat.get("rank_wr_vs50", 0) or 0)
    if d == "buff":
        feat["strength_vs_direction"] = wr_vs50
    elif d == "nerf":
        feat["strength_vs_direction"] = -wr_vs50
    else:
        feat["strength_vs_direction"] = 0.0

    # ── 역할군 / 유틸 타입별 상대 픽률 (랭크 전용) ──────────────────────────────
    if role_util_dict is not None:
        ru = role_util_dict.get((act_idx, agent), {})
        feat["role_rank_pr_ratio"] = float(ru.get("role_rank_pr_ratio", 1.0))
        feat["rank_pr_rel_meta"]   = float(ru.get("rank_pr_rel_meta", 1.0))
        feat["rank_pr_zscore"]     = float(ru.get("rank_pr_zscore", 0.0))
        # rank_pr_vs_peak: 현재 액트 메타 평균 대비 픽률
        # 역사적 피크 기준 대신 현재 메타 맥락으로 비교 (매 액트 독립 판단)
        feat["rank_pr_vs_peak"]    = feat["rank_pr_rel_meta"]
        for ut in _UTIL_RATIO_TYPES:
            key = f"util_{ut}_rank_pr_ratio"
            val = ru.get(key, np.nan)
            feat[key] = float(val) if val is not None else np.nan
    else:
        feat["role_rank_pr_ratio"] = 1.0
        feat["rank_pr_rel_meta"]   = 1.0
        feat["rank_pr_zscore"]     = 0.0
        feat["rank_pr_vs_peak"]    = 1.0
        for ut in _UTIL_RATIO_TYPES:
            feat[f"util_{ut}_rank_pr_ratio"] = np.nan

    # ── 장인 × VCT 픽률 교차 피처 (Stage A 전용) ────────────────────────────
    # 스킬 실링 높은 요원이 대회에서도 많이 픽되면 Riot 너프 반응 포착
    feat["skill_ceiling_x_vct_pr"] = (
        float(feat.get("skill_ceiling_score", 0.5) or 0.5)
        * float(feat.get("vct_pr_last", 0.0) or 0.0)
    )

    # ══════════════════════════════════════════════════════════════════════
    # 2D 사분면 피처 v3: 요원별 baseline 중심, 스케일 보정
    # ══════════════════════════════════════════════════════════════════════
    # 핵심 원칙:
    #   1) PR 축: 요원 자신의 역대 평균(baseline) 기준 이탈
    #   2) WR 축: 요원 자신의 역대 WR 평균 기준 이탈 (50% 아님!)
    #   3) VCT 축: 요원 자신의 VCT 평균 기준 이탈 + 절대 지배(35%+)
    #   4) 임계값 없이 순수 곱셈 → 데이터가 고르게 나뉨
    # ──────────────────────────────────────────────────────────────────────

    # 기본 축 계산 — baseline과 같은 원본 스케일 사용 (×5 하지 않음)
    _rank_pr_raw  = float(feat.get("rank_pr", 0.0) or 0.0)        # 원본 스케일 (1~17)
    _baseline_pr  = AGENT_PR_BASELINE.get(agent, 5.0)              # 같은 스케일
    _rank_wr      = float(feat.get("rank_wr", 50.0) or 50.0)
    _rank_wr_avg  = float(feat.get("rank_wr_hist_mean", 50.0) or 50.0)
    _vct_pr       = float(feat.get("vct_pr_last", 0.0) or 0.0)
    _vct_wr       = float(feat.get("vct_wr_last", 50.0) or 50.0) if not pd.isna(feat.get("vct_wr_last")) else 50.0
    _vct_pr_avg   = float(feat.get("vct_pr_avg", 0.0) or 0.0)

    # 축: 요원 자기 자신의 평균 대비 이탈량
    _pr_excess = _rank_pr_raw - _baseline_pr       # +: 평소보다 인기, -: 비인기
    _wr_excess = _rank_wr - _rank_wr_avg           # +: 평소보다 강함, -: 약함
    _vct_excess = _vct_pr - _vct_pr_avg            # +: VCT 평소 이상, -: 이하
    _vct_wr_excess = _vct_wr - 50.0                # VCT WR은 50% 기준 (역대 평균 없음)

    # ── 랭크 2D 사분면 ──────────────────────────────────────────────────
    # 요원 자신의 baseline PR + 역대 WR 평균 기준 → 임계값 0 → 데이터 균등 분할
    feat["rank_nerf_2d"]   = max(_pr_excess, 0) * max(_wr_excess, 0)    # Q1: 인기↑ + 강함↑ → 너프
    feat["rank_buff_2d"]   = max(-_pr_excess, 0) * max(-_wr_excess, 0)  # Q3: 비인기 + 약함 → 버프
    feat["rank_fandom_2d"] = max(_pr_excess, 0) * max(-_wr_excess, 0)   # Q4: 인기↑ + 약함 → 팬덤
    feat["rank_niche_2d"]  = max(-_pr_excess, 0) * max(_wr_excess, 0)   # Q2: 비인기 + 강함 → 니치OP

    # ── VCT 2D 사분면 (요원 VCT 평균 기준) ──────────────────────────────
    feat["vct_nerf_2d"]  = max(_vct_excess, 0) * max(_vct_wr_excess, 0)    # VCT 인기↑ + 승리↑
    feat["vct_buff_2d"]  = max(-_vct_excess, 0) * max(-_vct_wr_excess, 0)  # VCT 이탈 + 패배

    # VCT 절대 지배: 35%+ → 역대 평균 무관, 너프 압박 (Viper/Omen/Neon)
    feat["vct_must_nerf"] = max(_vct_pr - 35.0, 0)

    # ── 통합: 랭크 × VCT 교차 판단 ─────────────────────────────────────
    # 이중 너프: 랭크도 VCT도 너프 방향 (Neon 타입)
    feat["cross_nerf_2d"] = feat["rank_nerf_2d"] + feat["vct_nerf_2d"]

    # 프로 전용 너프: VCT 35%+ 이면서 랭크에서는 상위가 아닌 요원 (Viper 타입)
    # baseline_pr 스케일(1~14)에서 "2배 이상 인기 = 랭크 상위" 기준
    feat["pro_only_nerf"] = feat["vct_must_nerf"] * max(_baseline_pr * 2.0 - _rank_pr_raw, 0) / max(_baseline_pr * 2.0, 1.0)

    # 랭크 전용 너프: 랭크 강한데 VCT 안 뽑힘 (Clove 타입)
    feat["rank_only_nerf"] = feat["rank_nerf_2d"] * max(20.0 - _vct_pr, 0) / 20.0

    # VCT 상대 위치: 현재 / 역대 평균 비율
    feat["vct_pr_vs_agent_avg"] = _vct_pr / max(_vct_pr_avg, 2.0)

    # ── 인기도 프록시 피처 ────────────────────────────────────────────────
    _rank_pr_val    = float(feat.get("rank_pr", 0) or 0)
    feat["agent_pr_baseline"] = _baseline_pr
    feat["pr_vs_baseline"]    = _rank_pr_val - _baseline_pr
    _pr_excess_ratio = (_rank_pr_val - _baseline_pr) / max(_baseline_pr, 0.5)
    _wr_vs50 = _rank_wr - 50.0
    feat["pr_wr_gap"] = _pr_excess_ratio - _wr_vs50 / 2.0

    # ── Pre-patch anchor ────────────────────────────────────────────────
    _last_pr_pre_val = float(feat.get("last_pr_pre", 0) or 0)
    if _last_pr_pre_val > 0.3:
        feat["pr_effect_ratio"] = (_rank_pr_val - _last_pr_pre_val) / _last_pr_pre_val
    else:
        feat["pr_effect_ratio"] = 0.0

    feat["overshoot_flag"] = 1.0 if (
        d == "nerf" and feat["pr_effect_ratio"] < -0.40
    ) else 0.0
    feat["correction_risk_flag"] = 1.0 if (
        feat["overshoot_flag"] == 1.0 and _wr_vs50 < -2.0
    ) else 0.0

    # ── 방향 신호 (1D — SHAP 상위 유지분만 보존) ────────���───────────────
    feat["wr_nerf_signal"] = max(_wr_vs50, 0.0)    # WR > 50%
    feat["wr_buff_signal"] = max(-_wr_vs50, 0.0)   # WR < 50%
    feat["vct_buff_signal"] = max(_vct_pr_avg - _vct_pr, 0.0) if _vct_pr_avg > 0 else 0.0

    # 패치 맥락 일관성
    _ld = feat.get("last_direction", "none")
    feat["nerf_context"]           = float(_ld == "nerf" and _rank_pr_raw > _baseline_pr)
    feat["correction_nerf_signal"] = float(_ld == "buff" and _rank_pr_raw > _baseline_pr * 1.5)

    # WR vs 요원 역사적 평균
    feat["rank_wr_vs_agent_avg"] = _wr_excess

    # VCT 상대 위치 비율
    feat["vct_rel_pos"] = _vct_pr / max(_vct_pr_avg, 0.5) if _vct_pr_avg > 0 else 1.0

    return feat
