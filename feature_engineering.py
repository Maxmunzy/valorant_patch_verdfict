"""
Patch Verdict - Feature Engineering (v2: 시계열 통합)

패치 기준점으로 랭크/VCT를 시계열로 매핑:
  rank: t-3 ~ t+3 액트 윈도우
  VCT:  t-2 ~ t+2 대회 윈도우
  cross: 랭크-VCT 갭, 0픽 플래그, 패치 이력

입력:
  agent_act_history_all.csv
  maxmunzy_diamond_plus.csv
  vct_summary.csv
  patch_notes_classified.csv

출력:
  training_data.csv

실행: python feature_engineering.py
"""

import pandas as pd
import numpy as np
import warnings
from pathlib import Path
warnings.filterwarnings("ignore")

# ─── 상수 ────────────────────────────────────────────────────────────────────

ALL_ACTS = [
    "E2A1","E2A2","E2A3",
    "E3A1","E3A2","E3A3",
    "E4A1","E4A2","E4A3",
    "E5A1","E5A2",
    "E6A1","E6A2","E6A3",
    "E7A1","E7A2","E7A3",
    "E8A1","E8A2","E8A3",
    "E9A1","E9A2","E9A3",
    "V25A1","V25A2","V25A3",
    "V25A4","V25A5","V25A6",
    "V26A1","V26A2",
]
ACT_IDX = {a: i for i, a in enumerate(ALL_ACTS)}

PATCH_TO_ACT = {
    # E2
    "2.01":"E2A1","2.02":"E2A1","2.03":"E2A1",
    "2.04":"E2A2","2.05":"E2A2","2.06":"E2A2",
    "2.07":"E2A3","2.08":"E2A3","2.09":"E2A3","2.11":"E2A3",
    # E3
    "3.01":"E3A1","3.02":"E3A1","3.03":"E3A1","3.04":"E3A1",
    "3.05":"E3A2","3.06":"E3A2","3.07":"E3A2","3.08":"E3A2",
    "3.09":"E3A3","3.10":"E3A3","3.12":"E3A3",
    # E4
    "4.01":"E4A1","4.02":"E4A1","4.03":"E4A1",
    "4.04":"E4A2","4.05":"E4A2","4.07":"E4A2",
    "4.08":"E4A3","4.09":"E4A3","4.10":"E4A3","4.11":"E4A3",
    # E5
    "5.01":"E5A1","5.03":"E5A1","5.04":"E5A1",
    "5.05":"E5A2","5.06":"E5A2","5.07":"E5A2","5.08":"E5A2",
    "5.09":"E5A2","5.10":"E5A2",
    # E6
    "5.12":"E6A1","6.01":"E6A1","6.02":"E6A1","6.03":"E6A1",
    "6.04":"E6A2","6.05":"E6A2",
    "6.06":"E6A3","6.07":"E6A3",
    # E7
    "6.08":"E7A2","6.10":"E7A2",
    "6.11":"E7A3","7.01":"E7A3","7.02":"E7A3","7.03":"E7A3",
    # E8
    "7.04":"E8A1","7.05":"E8A1","7.06":"E8A1","7.07":"E8A1","7.08":"E8A1",
    "7.09":"E8A2","7.10":"E8A2",
    "7.12":"E8A3","8.01":"E8A3",
    # E9
    "8.02":"E9A1","8.03":"E9A1","8.04":"E9A1","8.05":"E9A1",
    "8.07":"E9A2","8.08":"E9A2","8.09":"E9A2","8.10":"E9A2",
    "8.11":"E9A3",
    # E9 (2024)
    "9.03":"E9A1",
    "9.04":"E9A2","9.05":"E9A2","9.06":"E9A2","9.07":"E9A2",
    "9.08":"E9A3","9.09":"E9A3","9.10":"E9A3","9.11":"E9A3",
    # V25A1: 2025-01-08 ~ 03-04
    "10.0":"V25A1","10.01":"V25A1","10.02":"V25A1","10.03":"V25A1",
    # V25A2: 2025-03-05 ~ 04-29
    "10.04":"V25A2","10.05":"V25A2","10.06":"V25A2","10.07":"V25A2",
    # V25A3: 2025-04-30 ~ 06-24
    "10.08":"V25A3","10.09":"V25A3","10.10":"V25A3","10.11":"V25A3",
    # V25A4: 2025-06-25 ~ 08-19
    "11.0":"V25A4","11.01":"V25A4","11.02":"V25A4","11.03":"V25A4",
    # V25A5: 2025-08-20 ~ 10-14
    "11.04":"V25A5","11.05":"V25A5","11.06":"V25A5","11.07":"V25A5","11.07b":"V25A5",
    # V25A6: 2025-10-15 ~ 2026-01-06
    "11.08":"V25A6","11.09":"V25A6","11.10":"V25A6","11.11":"V25A6",
    # V26A1: 2026-01-07 ~ 03-17
    "12.00":"V26A1","12.01":"V26A1","12.02":"V26A1","12.03":"V26A1","12.04":"V26A1",
    # V26A2: 2026-03-18 ~
    "12.05":"V26A2","12.06":"V26A2",
}

# VCT 대회 -> 진행 시점 액트
VCT_TO_ACT = {
    "Masters Reykjavik 2022":       "E4A3",
    "Masters Copenhagen 2022":      "E5A1",
    "Champions 2022":               "E6A1",
    "VCT LOCK//IN 2023":            "E7A1",
    "VCT Americas League 2023":     "E7A2",
    "VCT EMEA League 2023":         "E7A2",
    "VCT Pacific League 2023":      "E7A2",
    "Masters Tokyo 2023":           "E7A3",
    "Champions 2023":               "E9A2",
    "VCT Americas Kickoff 2024":    "E8A1",
    "VCT EMEA Kickoff 2024":        "E8A1",
    "VCT Pacific Kickoff 2024":     "E8A1",
    "VCT CN Kickoff 2024":          "E8A1",
    "VCT Americas Stage 1 2024":    "E8A2",
    "VCT EMEA Stage 1 2024":        "E8A2",
    "VCT Pacific Stage 1 2024":     "E8A2",
    "VCT CN Stage 1 2024":          "E8A2",
    "Masters Madrid 2024":          "E8A3",
    "VCT Americas Stage 2 2024":    "E9A1",
    "VCT EMEA Stage 2 2024":        "E9A1",
    "VCT Pacific Stage 2 2024":     "E9A1",
    "VCT CN Stage 2 2024":          "E9A1",
    "Masters Shanghai 2024":        "E9A2",
    "Champions 2024":               "E9A3",
    "VCT Americas Kickoff 2025":    "V25A1",
    "VCT EMEA Kickoff 2025":        "V25A1",
    "VCT Pacific Kickoff 2025":     "V25A1",
    "VCT CN Kickoff 2025":          "V25A1",
    "VCT Americas Stage 1 2025":    "V25A2",
    "VCT EMEA Stage 1 2025":        "V25A2",
    "VCT Pacific Stage 1 2025":     "V25A2",
    "VCT CN Stage 1 2025":          "V25A2",
    "Masters Bangkok 2025":         "V25A3",
    "VCT Americas Stage 2 2025":    "V25A4",
    "VCT EMEA Stage 2 2025":        "V25A4",
    "VCT Pacific Stage 2 2025":     "V25A4",
    "VCT CN Stage 2 2025":          "V25A4",
    "Champions 2025":               "V25A5",
    "VCT Americas Kickoff 2026":    "V26A1",
    "VCT EMEA Kickoff 2026":        "V26A1",
    "VCT Pacific Kickoff 2026":     "V26A1",
    "VCT CN Kickoff 2026":          "V26A1",
    "Masters Santiago 2026":        "V26A1",
    "VCT EMEA Stage 1 2026":        "V26A2",
    "VCT Pacific Stage 1 2026":     "V26A2",
    "VCT Americas Stage 1 2026":    "V26A2",
    "VCT CN Stage 1 2026":          "V26A2",
}

# VCT 대회 순서 인덱스 (같은 act 내 시간 순서 구분용)
VCT_EVENT_ORDER = {v: i for i, v in enumerate(VCT_TO_ACT.keys())}

# 요원 역할군 분류
AGENT_ROLE = {
    # Duelists
    "Jett":      "duelist", "Raze":    "duelist", "Reyna":   "duelist",
    "Phoenix":   "duelist", "Neon":    "duelist", "Yoru":    "duelist",
    "Iso":       "duelist", "Waylay":  "duelist",
    # Initiators
    "Sova":      "initiator", "Breach":  "initiator", "Fade":    "initiator",
    "Gekko":     "initiator", "Skye":    "initiator", "Kayo":    "initiator",
    "Tejo":      "initiator",
    # Controllers
    "Brimstone": "controller", "Viper":   "controller", "Astra":   "controller",
    "Omen":      "controller", "Harbor":  "controller", "Clove":   "controller",
    # Sentinels
    "Killjoy":   "sentinel", "Cypher":   "sentinel", "Sage":    "sentinel",
    "Deadlock":  "sentinel", "Vyse":     "sentinel", "Chamber": "sentinel",
    "Veto":      "sentinel",
}

# 요원별 이동기 스킬 (mobility_skill_nerfed 피처용)
# entry_fragger는 이 스킬이 핵심 정체성 → 너프 시 픽률 타격 직결
MOBILITY_SKILL = {
    # entry_fragger: 즉발 이동으로 에임 흔드는 스킬
    "Jett":    "E",   # Tailwind (대쉬)
    "Raze":    "Q",   # Blast Pack (자폭점프)
    "Neon":    "E",   # High Gear (전력질주)
    "Waylay":  "E",   # (이동기)
    # skirmisher: 탈출/기만 이동기
    "Yoru":    "E",   # Gatecrash (텔레포트)
    "Reyna":   "E",   # Dismiss (투명화 이탈)
    "Phoenix": "Q",   # Blaze (화염 이동)
    "Iso":     "E",   # Contingency (보호막 돌진)
    # sentinel: 포지셔닝 이동기
    "Chamber": "E",   # Rendezvous (앵커 텔레포트)
    # initiator
    "Skye":    "E",   # Trailblazer (돌격 정찰)
}

# 서브역할 분류 (역할군 내 실질 경쟁 그룹)
AGENT_SUBROLE = {
    # 1선 타격대: 즉발 이동기로 에임 흔드는 진입형 (entry fragger)
    "Jett":    "entry_fragger", "Neon":   "entry_fragger",
    "Raze":    "entry_fragger", "Waylay": "entry_fragger",
    # 2선 타격대: 이동기 없는 교전형 (skirmisher)
    "Reyna":   "skirmisher",   "Phoenix": "skirmisher",
    "Yoru":    "skirmisher",   "Iso":     "skirmisher",
    # 섬광 이니시에이터: 직접 섬광/기절로 진입 지원
    "Skye":    "flash_init",   "Breach":  "flash_init",
    "Kayo":    "flash_init",
    # 정보 이니시에이터: 드론/정찰로 정보 수집
    "Sova":    "intel_init",   "Fade":    "intel_init",
    "Gekko":   "intel_init",   "Tejo":    "intel_init",
    # 스모크 컨트롤러
    "Brimstone":"smoker",      "Omen":    "smoker",
    "Astra":   "smoker",       "Clove":   "smoker",
    # 벽/독 컨트롤러
    "Viper":   "waller",       "Harbor":  "waller",
    # 트래퍼 센티널: 트랩/터렛으로 구역 지킴
    "Killjoy": "trapper",      "Cypher":  "trapper",
    "Vyse":    "trapper",      "Veto":    "trapper",
    # 앵커 센티널: 힐/부활/벽으로 포지션 지킴
    "Sage":    "anchor",       "Chamber": "anchor",
    "Deadlock":"anchor",
}


# 스킬 슬롯별 중요도 가중치 (E=시그니처 최우선, C>Q 순)
# E: 무료 시그니처 스킬, 거의 모든 요원의 핵심
# C: 구매 스킬 중 주력
# Q: 구매 스킬 중 보조
SKILL_WEIGHT_BY_KEY = {"E": 3.0, "C": 2.0, "Q": 1.0}

# VCT 프로필은 정적 분류 대신 패치 당시 VCT 이력으로 동적 계산
# compute_vct_profile() 함수에서 처리
def compute_vct_profile(vct_pre_avg):
    """
    패치 직전 VCT 평균 픽률 기반 동적 프로필
    특정 요원을 하드코딩하지 않음 — 메타 변화 자동 반영
    """
    if pd.isna(vct_pre_avg) or vct_pre_avg is None:
        return "pro_unknown"   # 데이터 없는 초기 패치
    v = float(vct_pre_avg)
    if   v >= 15: return "pro_staple"    # 주요 픽 (Jett, Viper 전성기 등)
    elif v >= 5:  return "pro_viable"    # 정기 출전
    elif v >= 1:  return "pro_marginal"  # 가끔 출전
    else:         return "pro_absent"    # 거의 안 나옴 (Reyna, 초기 Yoru 등)


# ─── 데이터 로드 ──────────────────────────────────────────────────────────────

def load_data():
    rank_v   = pd.read_csv("agent_act_history_all.csv")
    rank_m   = pd.read_csv("maxmunzy_diamond_plus.csv")
    vct      = pd.read_csv("vct_summary.csv")
    pn       = pd.read_csv("patch_notes_classified.csv")
    map_dep  = pd.read_csv("map_dependency_scores.csv")  if Path("map_dependency_scores.csv").exists()  else None
    abil     = pd.read_csv("abilities_by_agent_act.csv") if Path("abilities_by_agent_act.csv").exists() else None
    return rank_v, rank_m, vct, pn, map_dep, abil


# ─── 랭크 히스토리 통합 ───────────────────────────────────────────────────────

def build_rank_history(rank_v, rank_m):
    v = rank_v[rank_v["note"] == "ok"].copy()
    v = v.rename(columns={"act": "act_name", "win_rate": "win_rate_pct"})
    v["source"]  = "vstats"
    v["act_idx"] = v["act_name"].map(ACT_IDX)

    m = rank_m.copy()
    m["source"]  = "maxmunzy"
    m["act_idx"] = m["act_name"].map(ACT_IDX)

    vstats_keys = set(zip(v["agent"], v["act_name"]))
    m_excl = m[~m.apply(lambda r: (r["agent"], r["act_name"]) in vstats_keys, axis=1)]

    common = ["agent", "act_name", "act_idx", "win_rate_pct", "pick_rate_pct", "matches", "kd", "source"]
    combined = pd.concat(
        [v[[c for c in common if c in v.columns]],
         m_excl[[c for c in common if c in m_excl.columns]]],
        ignore_index=True
    ).sort_values(["agent", "act_idx"]).reset_index(drop=True)
    return combined


# ─── VCT 히스토리 구축 ────────────────────────────────────────────────────────

def build_vct_history(vct):
    vct = vct.copy()
    vct["act_name"]   = vct["event"].map(VCT_TO_ACT)
    vct["act_idx"]    = vct["act_name"].map(ACT_IDX)
    vct["event_order"] = vct["event"].map(VCT_EVENT_ORDER)

    unmapped = vct[vct["act_name"].isna()]["event"].unique()
    if len(unmapped):
        print(f"  [VCT] 매핑 안 된 대회: {list(unmapped)}")

    vct["is_pre_patch"]  = vct["patch_before"].notna()
    vct["is_post_patch"] = vct["patch_after"].notna()
    vct["patch_ref"]     = vct["patch_before"].fillna(vct["patch_after"])

    return vct.dropna(subset=["act_idx"])


# ─── 패치 피처 집계 ───────────────────────────────────────────────────────────

def aggregate_patch_features(pn):
    nb = pn[pn["direction"].isin(["nerf", "buff"])].copy()
    nb["patch"] = nb["patch"].astype(str)
    nb["value_change_ratio"] = pd.to_numeric(nb["value_before"], errors="coerce").pipe(
        lambda before: (pd.to_numeric(nb["value_after"], errors="coerce") - before) / before.replace(0, np.nan)
    )

    agg = nb.groupby(["agent", "patch"]).agg(
        direction         = ("direction",  lambda x: "nerf" if "nerf" in x.values else x.mode()[0]),
        n_changes         = ("skill_key",  "count"),
        trigger_type      = ("trigger_type", lambda x: x.dropna().mode()[0] if len(x.dropna()) > 0 else "rank_stat"),
        confidence        = ("claude_confidence", lambda x: x.dropna().mode()[0] if len(x.dropna()) > 0 else "low"),
        has_bugfix        = ("has_bugfix",  "max"),
        value_chg_mean    = ("value_change_ratio", "mean"),
        value_chg_max_abs = ("value_change_ratio", lambda x: x.abs().max()),
        has_mechanic      = ("change_type", lambda x: int("mechanic" in x.values or "rework" in x.values)),
        n_skills_changed  = ("skill_key",  lambda x: x[x != "?"].nunique()),
    ).reset_index()

    agg["change_types"] = (
        nb.groupby(["agent", "patch"])["change_type"]
        .apply(lambda x: ",".join(sorted(set(x.dropna()))))
        .values
    )
    agg["patch_act"]     = agg["patch"].map(PATCH_TO_ACT)
    agg["patch_act_idx"] = agg["patch_act"].map(ACT_IDX)

    # 이동기 스킬 너프 여부 (entry_fragger/skirmisher 핵심 피처)
    # pandas 3.0+: groupby().apply() excludes group-by columns from grp
    # → agent name must come from grp.name tuple
    def _mobility_nerfed(grp):
        agent = grp.name[0]  # (agent, patch) 튜플의 첫 번째 원소
        mob_key = MOBILITY_SKILL.get(agent)
        if mob_key is None:
            return 0
        mob_nerfs = grp[(grp["skill_key"] == mob_key) & (grp["direction"] == "nerf")]
        return int(not mob_nerfs.empty)

    mob_flags = (
        nb.groupby(["agent", "patch"])
        .apply(_mobility_nerfed)
        .reset_index(name="mobility_skill_nerfed")
    )
    agg = agg.merge(mob_flags, on=["agent", "patch"], how="left")
    agg["mobility_skill_nerfed"] = agg["mobility_skill_nerfed"].fillna(0).astype(int)

    # 얼티밋 변경 여부
    def _ult_changed(grp):
        return int((grp["skill_key"] == "X").any())

    ult_flags = (
        nb.groupby(["agent", "patch"])
        .apply(_ult_changed)
        .reset_index(name="has_ult_change")
    )
    agg = agg.merge(ult_flags, on=["agent", "patch"], how="left")
    agg["has_ult_change"] = agg["has_ult_change"].fillna(0).astype(int)

    # 스킬 중요도 피처 (궁극기 제외)
    def _skill_importance_feats(grp):
        # E=3(identity), C=2(core), Q=1(utility) 단순 규칙
        feats = {"n_identity_changed": 0, "n_core_changed": 0, "n_utility_changed": 0,
                 "has_identity_change": 0, "patch_importance_score": 2.0, "max_skill_weight": 2.0,
                 "identity_nerfed": 0, "identity_buffed": 0}

        weights = []
        for _, row in grp.iterrows():
            sk = row["skill_key"]
            if sk == "X" or sk == "?":
                continue
            w = SKILL_WEIGHT_BY_KEY.get(sk, 2.0)
            weights.append(w)
            if sk == "E":
                feats["n_identity_changed"] += 1
                if row["direction"] == "nerf":
                    feats["identity_nerfed"] = 1
                elif row["direction"] == "buff":
                    feats["identity_buffed"] = 1
            elif sk == "C":
                feats["n_core_changed"] += 1
            elif sk == "Q":
                feats["n_utility_changed"] += 1

        if weights:
            feats["has_identity_change"] = int(feats["n_identity_changed"] > 0)
            feats["patch_importance_score"] = round(float(np.mean(weights)), 3)
            feats["max_skill_weight"] = float(max(weights))
        return pd.Series(feats)

    skill_imp = (
        nb.groupby(["agent", "patch"])
        .apply(_skill_importance_feats)
        .reset_index()
    )
    agg = agg.merge(skill_imp, on=["agent", "patch"], how="left")

    return agg


# ─── 랭크 시계열 피처 ─────────────────────────────────────────────────────────

def _slope(series):
    """선형 기울기 (act 당 픽률 변화량)"""
    s = series.dropna().values
    if len(s) < 2:
        return 0.0
    x = np.arange(len(s))
    return float(np.polyfit(x, s, 1)[0])


def compute_rank_timeseries(rank, agent, patch_act_idx, pre_n=3, post_n=3):
    """
    패치 기준 랭크 시계열 피처
    pre: t-1 ~ t-n (패치 직전 n액트, t-1이 가장 최근)
    post: t+1 ~ t+n (패치 직후 n액트)
    """
    ag  = rank[rank["agent"] == agent].sort_values("act_idx")
    pre = ag[ag["act_idx"] < patch_act_idx].tail(pre_n)
    post = ag[ag["act_idx"] >= patch_act_idx].head(post_n)

    result = {}

    # pre 시계열: t-1이 patch에 가장 가까운 act
    pre_vals_pr = list(pre["pick_rate_pct"].values)
    pre_vals_wr = list(pre["win_rate_pct"].values)
    for i, (pr, wr) in enumerate(zip(reversed(pre_vals_pr), reversed(pre_vals_wr))):
        result[f"rank_pr_t-{i+1}"] = round(float(pr), 3)
        result[f"rank_wr_t-{i+1}"] = round(float(wr), 3)

    # post 시계열: t+1이 patch 직후
    post_vals_pr = list(post["pick_rate_pct"].values)
    post_vals_wr = list(post["win_rate_pct"].values)
    for i, (pr, wr) in enumerate(zip(post_vals_pr, post_vals_wr)):
        result[f"rank_pr_t+{i+1}"] = round(float(pr), 3)
        result[f"rank_wr_t+{i+1}"] = round(float(wr), 3)

    # 요약 피처
    if len(pre_vals_pr) > 0:
        result["rank_pr_pre_avg"]   = round(float(np.mean(pre_vals_pr)), 3)
        result["rank_wr_pre_avg"]   = round(float(np.mean(pre_vals_wr)), 3)
        result["rank_pr_pre_last"]  = round(float(pre_vals_pr[-1]), 3)
        result["rank_pr_pre_peak"]  = round(float(np.max(pre_vals_pr)), 3)
        result["rank_pr_pre_slope"] = round(_slope(pre["pick_rate_pct"]), 4)
        result["rank_wr_vs50_pre"]  = round(float(np.mean(pre_vals_wr)) - 50.0, 3)
        result["rank_pre_n_acts"]   = len(pre_vals_pr)

    if len(post_vals_pr) > 0:
        result["rank_pr_post_avg"]   = round(float(np.mean(post_vals_pr)), 3)
        result["rank_wr_post_avg"]   = round(float(np.mean(post_vals_wr)), 3)
        result["rank_pr_post_slope"] = round(_slope(post["pick_rate_pct"]), 4)

    if len(pre_vals_pr) > 0 and len(post_vals_pr) > 0:
        result["rank_pr_delta"]     = round(float(np.mean(post_vals_pr)) - float(np.mean(pre_vals_pr)), 3)
        result["rank_pr_pct_chg"]   = round(
            (float(np.mean(post_vals_pr)) - float(np.mean(pre_vals_pr)))
            / float(np.mean(pre_vals_pr)) * 100, 2
        ) if float(np.mean(pre_vals_pr)) != 0 else np.nan

    return result


# ─── VCT 시계열 피처 ──────────────────────────────────────────────────────────

def _get_all_post_events(vct_h, patch_act_idx):
    """패치 이후 존재하는 모든 VCT 이벤트 목록 (에이전트 무관)"""
    post = vct_h[
        (vct_h["act_idx"] >= patch_act_idx) &
        (vct_h["is_pre_patch"] == False)
    ]
    return post[["event", "act_idx", "event_order", "total_maps"]].drop_duplicates("event")


def compute_vct_timeseries(vct_h, agent, patch_act_idx, pre_n=2, post_n=2):
    """
    패치 기준 VCT 시계열 피처
    - pre: patch_before 태그 우선, 그 다음 patch_act_idx 이전 대회들
    - post: patch_after 태그 우선, 없으면 patch_act_idx 이후 대회들
    - 0픽: 대회는 존재하지만 에이전트가 픽되지 않은 경우 pick_rate=0 처리
    """
    ag = vct_h[vct_h["agent"] == agent].sort_values(["act_idx", "event_order"])

    # ── pre 시계열 ──
    pb = ag[(ag["act_idx"] <= patch_act_idx) & (ag["is_pre_patch"] == True)].sort_values(["act_idx","event_order"])
    if not pb.empty:
        pre_rows = pb.tail(pre_n)
    else:
        pre_rows = ag[ag["act_idx"] < patch_act_idx].tail(pre_n)

    # ── post 시계열 ──
    # 패치 이후 존재하는 대회 전체 (에이전트 픽 여부 무관)
    all_post_events = _get_all_post_events(vct_h, patch_act_idx)
    post_tagged = ag[
        (ag["is_post_patch"] == True) & (ag["act_idx"] >= patch_act_idx)
    ].sort_values(["act_idx","event_order"])
    post_all = ag[
        (ag["act_idx"] >= patch_act_idx) & (ag["is_pre_patch"] == False)
    ].sort_values(["act_idx","event_order"])

    if not post_tagged.empty:
        post_rows = post_tagged.head(post_n)
    elif not post_all.empty:
        post_rows = post_all.head(post_n)
    else:
        post_rows = pd.DataFrame()

    result = {}

    # pre 시계열 피처 (t-1이 가장 최근)
    pre_pr_list, pre_wr_list = [], []
    for i, (_, row) in enumerate(reversed(list(pre_rows.iterrows()))):
        result[f"vct_pr_t-{i+1}"] = round(float(row["pick_rate_pct"]), 3)
        result[f"vct_wr_t-{i+1}"] = round(float(row["win_rate_pct"]), 3)
        result[f"vct_event_t-{i+1}"] = row["event"]
        pre_pr_list.append(float(row["pick_rate_pct"]))
        pre_wr_list.append(float(row["win_rate_pct"]))

    # post 시계열 피처
    # 먼저 post_n개 대회 슬롯 결정 (에이전트 픽 유무 포함)
    post_pr_list, post_wr_list = [], []
    post_event_names = []

    if not all_post_events.empty:
        candidate_events = all_post_events.sort_values(["act_idx","event_order"]).head(post_n)
        for _, ev_row in candidate_events.iterrows():
            ev_name = ev_row["event"]
            agent_in_event = post_all[post_all["event"] == ev_name]
            if not agent_in_event.empty:
                pr = float(agent_in_event.iloc[0]["pick_rate_pct"])
                wr = float(agent_in_event.iloc[0]["win_rate_pct"])
            else:
                pr, wr = 0.0, np.nan   # 대회 존재하나 에이전트 0픽
            post_pr_list.append(pr)
            post_wr_list.append(wr)
            post_event_names.append(ev_name)
    elif not post_rows.empty:
        for _, row in post_rows.iterrows():
            post_pr_list.append(float(row["pick_rate_pct"]))
            post_wr_list.append(float(row["win_rate_pct"]))
            post_event_names.append(row["event"])

    for i, (pr, wr, ev) in enumerate(zip(post_pr_list, post_wr_list, post_event_names)):
        result[f"vct_pr_t+{i+1}"]    = round(pr, 3)
        result[f"vct_wr_t+{i+1}"]    = round(wr, 3) if not np.isnan(wr) else np.nan
        result[f"vct_event_t+{i+1}"] = ev

    # 요약 피처
    if pre_pr_list:
        result["vct_pr_pre_avg"]   = round(float(np.mean(pre_pr_list)), 3)
        result["vct_pr_pre_last"]  = round(pre_pr_list[-1], 3)   # t-1
        result["vct_pr_pre_slope"] = round(_slope(pd.Series(pre_pr_list)), 4)
        result["vct_pre_n_events"] = len(pre_pr_list)

    if post_pr_list:
        result["vct_pr_post_avg"]  = round(float(np.mean(post_pr_list)), 3)
        result["vct_pr_post_first"]= round(post_pr_list[0], 3)   # t+1
        result["vct_zero_pick_post"]= int(post_pr_list[0] == 0.0)
        result["vct_n_post_events"] = len(post_pr_list)

    # 메인 타겟: t-1 -> t+1 변화율 (verdict는 메인 루프에서 direction 알고 난 뒤 적용)
    if pre_pr_list and post_pr_list:
        pre_pr  = pre_pr_list[-1]   # t-1
        post_pr = post_pr_list[0]   # t+1
        if pre_pr > 0:
            result["vct_pr_delta_pct"] = round((post_pr - pre_pr) / pre_pr * 100, 2)
        else:
            result["vct_pr_delta_pct"] = np.nan
    else:
        result["vct_pr_delta_pct"] = np.nan

    # VCT 부재 연속 대회 수 (최근 n대회 중 픽 없는 수)
    recent_vcts = vct_h[vct_h["act_idx"] < patch_act_idx]["event"].unique()
    agent_vcts  = ag[ag["act_idx"] < patch_act_idx]["event"].unique()
    result["vct_absence_pre"] = len(set(recent_vcts) - set(agent_vcts))

    return result


def _simple_verdict(delta, direction, max_w):
    """
    3단계 판정: MISS / HIT / OVERSHOOT
    랭크/VCT 각각의 단일 컨텍스트 판정에 사용
    """
    mult = 2.0 / max(max_w, 0.5)
    t_hit      = 20 * mult   # 유의미한 변화 시작점
    t_overshoot = 60 * mult  # 과도한 변화 경계

    if direction == "nerf":
        if delta >= -t_hit:       return "MISS"
        elif delta >= -t_overshoot: return "HIT"
        else:                      return "OVERSHOOT"
    else:  # buff
        if delta <= t_hit:        return "MISS"
        elif delta <= t_overshoot:  return "HIT"
        else:                      return "OVERSHOOT"


def _compute_rank_verdict(rank_pr_pre, rank_pr_post, direction, max_w):
    """랭크 픽률 기반 판정"""
    if rank_pr_pre is None or rank_pr_post is None:
        return "NO_DATA"
    if pd.isna(rank_pr_pre) or pd.isna(rank_pr_post):
        return "NO_DATA"
    if float(rank_pr_pre) <= 0:
        return "NO_DATA"
    delta = (float(rank_pr_post) - float(rank_pr_pre)) / float(rank_pr_pre) * 100
    return _simple_verdict(delta, direction, max_w)


def _compute_vct_verdict(vct_delta_pct, direction, max_w, vct_profile, vct_post_pr):
    """
    VCT 픽률 기반 판정
    - pro_absent / pro_unknown: 원래 안 나오던 요원 → 버프 후에도 MISS면 의미있는 신호
    - vct_delta 없음 + vct_post=0: 대회 존재하나 0픽 → MISS
    - 데이터 자체 없음 → NO_DATA
    """
    if vct_delta_pct is None or (isinstance(vct_delta_pct, float) and np.isnan(vct_delta_pct)):
        if vct_post_pr is not None and not pd.isna(vct_post_pr) and float(vct_post_pr) == 0.0:
            return "MISS"
        return "NO_DATA"

    return _simple_verdict(float(vct_delta_pct), direction, max_w)


def _combine_verdicts(rank_v, vct_v, vct_profile):
    """
    랭크 + VCT 판정 조합 → Step 2 피처로 쓸 최종 레이블

    vct_profile로 기대치 보정:
    - pro_absent: 원래 안 나오던 요원 → VCT MISS는 덜 의미있음
    - pro_staple/pro_viable: VCT MISS는 명확한 실패 신호
    """
    if "NO_DATA" in (rank_v, vct_v):
        return "UNKNOWN"

    # pro_absent인데 VCT MISS: 원래 안 나오던 거라 PRO_FAIL 아님
    if vct_v == "MISS" and vct_profile in ("pro_absent", "pro_unknown"):
        if rank_v == "HIT":       return "RANK_ONLY_HIT"
        if rank_v == "OVERSHOOT": return "RANK_ONLY_OVERSHOOT"
        return "DUAL_MISS"

    if rank_v == "HIT"       and vct_v == "HIT":       return "DUAL_HIT"
    if rank_v == "HIT"       and vct_v == "MISS":      return "PRO_FAIL"
    if rank_v == "MISS"      and vct_v == "HIT":       return "RANK_FAIL"
    if rank_v == "MISS"      and vct_v == "MISS":      return "DUAL_MISS"
    if rank_v == "OVERSHOOT" and vct_v == "OVERSHOOT": return "DUAL_OVERSHOOT"
    return "MIXED"


def _verdict(delta, direction="nerf", max_skill_weight=2.0):
    """
    direction-aware + skill-importance-aware verdict labeling

    max_skill_weight에 따라 임계값 조정:
      identity (3.0) → threshold × 0.67 (±13, ±40)  → 작은 변화도 EFFECTIVE
      core     (2.0) → threshold × 1.00 (±20, ±60)  → 기본
      utility  (1.0) → threshold × 2.00 (±40, ±120) → 큰 변화만 EFFECTIVE

    nerf: 픽률 감소가 목표 → 감소 크면 EXCESSIVE
    buff: 픽률 증가가 목표 → 증가 크면 EXCESSIVE(과버프)
    """
    mult = 2.0 / max(max_skill_weight, 0.5)   # 0으로 나누기 방지
    t_balanced  = 20 * mult   # BALANCED 경계
    t_effective = 60 * mult   # EFFECTIVE / EXCESSIVE 경계

    if direction == "nerf":
        if delta >= t_balanced:
            return "INEFFECTIVE"
        elif delta >= -t_balanced:
            return "BALANCED"
        elif delta >= -t_effective:
            return "EFFECTIVE"
        else:
            return "EXCESSIVE"
    else:  # buff
        if delta <= -t_balanced:
            return "INEFFECTIVE"
        elif delta <= t_balanced:
            return "BALANCED"
        elif delta <= t_effective:
            return "EFFECTIVE"
        else:
            return "EXCESSIVE"


# ─── 크로스 피처 ─────────────────────────────────────────────────────────────

def compute_cross_features(rank_feats, vct_feats):
    """랭크-VCT 크로스 피처"""
    result = {}

    rank_pre = rank_feats.get("rank_pr_pre_last")
    vct_pre  = vct_feats.get("vct_pr_pre_last")
    if rank_pre is not None and vct_pre is not None:
        result["rank_vct_pr_gap_pre"] = round(rank_pre - vct_pre, 3)
        # 랭크 대비 VCT 픽률 비율 (>1이면 프로에서 더 많이 픽)
        result["vct_rank_pr_ratio"] = round(vct_pre / rank_pre, 3) if rank_pre > 0 else np.nan

    rank_post = rank_feats.get("rank_pr_post_avg")
    vct_post  = vct_feats.get("vct_pr_post_avg")
    if rank_post is not None and vct_post is not None:
        result["rank_vct_pr_gap_post"] = round(rank_post - vct_post, 3)

    # 랭크 반응 속도: 패치 후 랭크 픽률이 얼마나 빨리 떨어졌나
    rank_delta = rank_feats.get("rank_pr_delta")
    vct_delta  = vct_feats.get("vct_pr_delta_pct")
    if rank_delta is not None and vct_delta is not None:
        result["rank_vct_response_gap"] = round(abs(float(rank_delta)) - abs(float(vct_delta) / 10), 3)

    return result


# ─── 역할군 경쟁 피처 ────────────────────────────────────────────────────────

def compute_role_competition(rank, vct_h, agent, patch_act_idx):
    """
    역할군 내 경쟁 피처:
    - 패치 전후 같은 역할군 타 요원들 픽률 합계 (랭크 + VCT)
    - 역할 독점 여부 (패치 전 역할군 내 픽률 비중)
    - 신규 요원 등장 여부 (패치 후 2액트 내 같은 역할군 신규 진입)
    """
    role    = AGENT_ROLE.get(agent)
    subrole = AGENT_SUBROLE.get(agent)
    result  = {
        "agent_role":    role    if role    else "unknown",
        "agent_subrole": subrole if subrole else "unknown",
    }
    if not role:
        return result

    rivals        = [a for a, r in AGENT_ROLE.items()    if r == role    and a != agent]
    sub_rivals    = [a for a, r in AGENT_SUBROLE.items() if r == subrole and a != agent]

    all_role_agents = [agent] + rivals

    # ── 랭크 경쟁 (패치 직전 act) ──
    pre_rank = rank[rank["act_idx"] < patch_act_idx]
    if not pre_rank.empty:
        last_act = pre_rank["act_idx"].max()
        at_last  = pre_rank[pre_rank["act_idx"] == last_act]

        role_at_last = at_last[at_last["agent"].isin(all_role_agents)].set_index("agent")["pick_rate_pct"]
        agent_pr_val = float(role_at_last.get(agent, 0.0))
        rival_prs    = role_at_last.drop(agent, errors="ignore")

        role_total = float(role_at_last.sum())

        result["role_rival_pr_pre"]        = round(float(rival_prs.sum()), 3)
        result["role_rival_pr_mean_pre"]   = round(float(rival_prs.mean()), 3) if not rival_prs.empty else 0.0
        result["role_monopoly_rank"]       = round(agent_pr_val / role_total, 3) if role_total > 0 else np.nan
        result["role_n_rivals_active_pre"] = int((rival_prs > 3.0).sum())
        result["role_pr_share_pre"]        = round(agent_pr_val / role_total, 3) if role_total > 0 else np.nan

        # 역할군 내 순위 (1=가장 많이 픽)
        sorted_role = role_at_last.sort_values(ascending=False)
        rank_in_role = list(sorted_role.index).index(agent) + 1 if agent in sorted_role.index else np.nan
        result["role_rank_pre"] = rank_in_role

        # 1위 라이벌 픽률
        top_rival = rival_prs.idxmax() if not rival_prs.empty else None
        result["top_rival_pr_pre"]  = round(float(rival_prs.max()), 3) if not rival_prs.empty else 0.0
        result["top_rival_name"]    = top_rival if top_rival else ""

        # 서브역할 내 경쟁 (직접 대체 관계)
        sub_role_at_last = at_last[at_last["agent"].isin(sub_rivals)].set_index("agent")["pick_rate_pct"]
        if not sub_role_at_last.empty:
            result["subrole_rival_pr_pre"]     = round(float(sub_role_at_last.sum()), 3)
            result["subrole_rival_pr_mean_pre"] = round(float(sub_role_at_last.mean()), 3)
            result["subrole_top_rival_pr_pre"]  = round(float(sub_role_at_last.max()), 3)
            sub_total = agent_pr_val + float(sub_role_at_last.sum())
            result["subrole_pr_share_pre"] = round(agent_pr_val / sub_total, 3) if sub_total > 0 else np.nan
            sorted_sub = sub_role_at_last.sort_values(ascending=False)
            all_sub = pd.concat([pd.Series({agent: agent_pr_val}), sub_role_at_last]).sort_values(ascending=False)
            result["subrole_rank_pre"] = list(all_sub.index).index(agent) + 1 if agent in all_sub.index else np.nan

        # 역할군 메타 트렌드 (최근 3액트 역할군 전체 픽률 기울기)
        pre3 = pre_rank[pre_rank["act_idx"] >= last_act - 2]
        role_trend = (
            pre3[pre3["agent"].isin(all_role_agents)]
            .groupby("act_idx")["pick_rate_pct"].sum()
        )
        result["role_meta_trend"] = round(_slope(role_trend), 4) if len(role_trend) > 1 else 0.0

        # 서브역할 메타 트렌드
        sub_trend = (
            pre3[pre3["agent"].isin(sub_rivals + [agent])]
            .groupby("act_idx")["pick_rate_pct"].sum()
        )
        result["subrole_meta_trend"] = round(_slope(sub_trend), 4) if len(sub_trend) > 1 else 0.0

    # ── 랭크 경쟁 (패치 직후 act) ──
    post_rank = rank[rank["act_idx"] >= patch_act_idx]
    if not post_rank.empty:
        first_act = post_rank["act_idx"].min()
        at_first  = post_rank[post_rank["act_idx"] == first_act]

        role_at_first = at_first[at_first["agent"].isin(all_role_agents)].set_index("agent")["pick_rate_pct"]
        rival_prs_post = role_at_first.drop(agent, errors="ignore")
        agent_pr_post  = float(role_at_first.get(agent, 0.0))
        role_total_post = float(role_at_first.sum())

        result["role_rival_pr_post"]        = round(float(rival_prs_post.sum()), 3)
        result["role_rival_pr_delta"]       = round(result.get("role_rival_pr_post", 0) - result.get("role_rival_pr_pre", 0), 3)
        result["role_n_rivals_active_post"] = int((rival_prs_post > 3.0).sum())

        # 서브역할 직후 경쟁
        sub_role_post = at_first[at_first["agent"].isin(sub_rivals)].set_index("agent")["pick_rate_pct"]
        if not sub_role_post.empty:
            result["subrole_rival_pr_post"]  = round(float(sub_role_post.sum()), 3)
            result["subrole_top_rival_pr_post"] = round(float(sub_role_post.max()), 3)
            result["subrole_rival_pr_delta"] = round(
                result.get("subrole_rival_pr_post", 0) - result.get("subrole_rival_pr_pre", 0), 3
            )
            # 직접 대체 라이벌이 반사이익 받았는지
            result["subrole_top_rival_delta"] = round(
                result.get("subrole_top_rival_pr_post", 0) - result.get("subrole_top_rival_pr_pre", 0), 3
            )
            all_sub_post = pd.concat([pd.Series({agent: agent_pr_post}), sub_role_post]).sort_values(ascending=False)
            result["subrole_rank_post"]  = list(all_sub_post.index).index(agent) + 1 if agent in all_sub_post.index else np.nan
            result["subrole_rank_delta"] = result.get("subrole_rank_post", 0) - result.get("subrole_rank_pre", 0)

        # 역할군 내 순위 (패치 후)
        sorted_post = role_at_first.sort_values(ascending=False)
        rank_post = list(sorted_post.index).index(agent) + 1 if agent in sorted_post.index else np.nan
        result["role_rank_post"]  = rank_post
        result["role_rank_delta"] = (rank_post - result.get("role_rank_pre", rank_post)) if not np.isnan(rank_post) else np.nan

        # 1위 라이벌 반사이익
        top_rival_pr_post = float(rival_prs_post.max()) if not rival_prs_post.empty else 0.0
        result["top_rival_pr_post"]  = round(top_rival_pr_post, 3)
        result["top_rival_pr_delta"] = round(top_rival_pr_post - result.get("top_rival_pr_pre", 0.0), 3)

        # 역할군 전체 픽률 비중 (패치 후)
        result["role_pr_share_post"] = round(agent_pr_post / role_total_post, 3) if role_total_post > 0 else np.nan

    # ── VCT 역할군 비교 (패치 직전 대회) ──
    pre_vct = vct_h[vct_h["act_idx"] <= patch_act_idx]
    if not pre_vct.empty:
        last_ev  = pre_vct.sort_values(["act_idx","event_order"]).iloc[-1]["event"]
        at_ev    = pre_vct[pre_vct["event"] == last_ev]
        role_vct = at_ev[at_ev["agent"].isin(all_role_agents)].set_index("agent")["pick_rate_pct"]

        agent_vct_val  = float(role_vct.get(agent, 0.0))
        rival_vct_prs  = role_vct.drop(agent, errors="ignore")
        vct_role_total = float(role_vct.sum())

        result["role_vct_rival_pr_pre"] = round(float(rival_vct_prs.sum()), 3)
        result["role_vct_monopoly"]     = round(agent_vct_val / vct_role_total, 3) if vct_role_total > 0 else np.nan

        # VCT 역할군 내 순위
        sorted_vct = role_vct.sort_values(ascending=False)
        vct_rank = list(sorted_vct.index).index(agent) + 1 if agent in sorted_vct.index else np.nan
        result["role_vct_rank_pre"]         = vct_rank
        result["role_vct_top_rival_pr_pre"] = round(float(rival_vct_prs.max()), 3) if not rival_vct_prs.empty else 0.0

    # ── VCT 역할군 비교 (패치 직후 대회) ──
    post_vct = vct_h[
        (vct_h["act_idx"] >= patch_act_idx) & (vct_h["is_pre_patch"] == False)
    ]
    if not post_vct.empty:
        first_ev  = post_vct.sort_values(["act_idx","event_order"]).iloc[0]["event"]
        at_ev_post = post_vct[post_vct["event"] == first_ev]
        role_vct_post = at_ev_post[at_ev_post["agent"].isin(all_role_agents)].set_index("agent")["pick_rate_pct"]

        rival_vct_post = role_vct_post.drop(agent, errors="ignore")
        result["role_vct_top_rival_pr_post"]  = round(float(rival_vct_post.max()), 3) if not rival_vct_post.empty else 0.0
        result["role_vct_top_rival_pr_delta"] = round(
            result.get("role_vct_top_rival_pr_post", 0) - result.get("role_vct_top_rival_pr_pre", 0), 3
        )

        sorted_vct_post = role_vct_post.sort_values(ascending=False)
        vct_rank_post = list(sorted_vct_post.index).index(agent) + 1 if agent in sorted_vct_post.index else np.nan
        result["role_vct_rank_post"]  = vct_rank_post
        result["role_vct_rank_delta"] = (vct_rank_post - result.get("role_vct_rank_pre", vct_rank_post)) if not np.isnan(vct_rank_post) else np.nan

    # ── 신규 요원 등장 여부 (패치 후 2액트 내) ──
    pre_agents  = set(rank[rank["act_idx"] < patch_act_idx]["agent"].unique())
    post_window = rank[(rank["act_idx"] >= patch_act_idx) & (rank["act_idx"] < patch_act_idx + 2)]
    new_rivals  = [a for a in post_window["agent"].unique() if a in rivals and a not in pre_agents]
    result["new_rival_emerged"] = int(len(new_rivals) > 0)
    result["new_rival_names"]   = ",".join(new_rivals) if new_rivals else ""

    return result


# ─── 패치 이력 피처 ──────────────────────────────────────────────────────────

def compute_patch_history(all_patches, agent, patch, patch_act_idx):
    """이 패치 이전 동일 에이전트 패치 이력"""
    prev = all_patches[
        (all_patches["agent"] == agent) &
        (all_patches["patch"] != str(patch)) &
        (all_patches["patch_act_idx"] < patch_act_idx)
    ].sort_values("patch_act_idx")

    result = {
        "n_prev_patches":  len(prev),
        "prev_nerf_count": int((prev["direction"] == "nerf").sum()),
        "prev_buff_count": int((prev["direction"] == "buff").sum()),
    }
    if not prev.empty:
        last = prev.iloc[-1]
        result["acts_since_last_patch"] = int(patch_act_idx - last["patch_act_idx"])
        result["last_patch_direction"]  = last["direction"]
    else:
        result["acts_since_last_patch"] = 99
        result["last_patch_direction"]  = "none"

    # 최근 4액트 내 중복 패치 (누적 너프 여부)
    result["multi_patch_4acts"] = int(
        len(prev[prev["patch_act_idx"] >= patch_act_idx - 4]) > 0
    )
    return result


# ─── 메인 파이프라인 ──────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("Patch Verdict - Feature Engineering v2 (시계열 통합)")
    print("=" * 65 + "\n")

    print("[1] 데이터 로드")
    rank_v, rank_m, vct_raw, pn, map_dep, abil = load_data()
    print(f"  vstats: {len(rank_v)}행 / maxmunzy: {len(rank_m)}행 / vct: {len(vct_raw)}행 / patches: {len(pn)}행")
    if map_dep is not None:
        print(f"  map_dep: {len(map_dep)}행")
    if abil is not None:
        print(f"  abilities: {len(abil)}행 / 액트 {abil['act'].nunique()}개")

    print("\n[2] 랭크 히스토리 통합")
    rank = build_rank_history(rank_v, rank_m)
    print(f"  통합: {len(rank)}행 / 요원 {rank['agent'].nunique()}명 / 액트 {rank['act_name'].nunique()}개")

    print("\n[3] VCT 히스토리 구축")
    vct_h = build_vct_history(vct_raw)
    print(f"  VCT: {len(vct_h)}행 / 대회 {vct_h['event'].nunique()}개 / 요원 {vct_h['agent'].nunique()}명")

    print("\n[4] 패치 피처 집계")
    patch_feats = aggregate_patch_features(pn)
    patch_feats = patch_feats.dropna(subset=["patch_act_idx"])
    print(f"  패치x요원 그룹: {len(patch_feats)}개")

    print("\n[5] 시계열 피처 조립")
    rows = []
    for _, pf in patch_feats.iterrows():
        agent         = pf["agent"]
        patch         = pf["patch"]
        patch_act_idx = int(pf["patch_act_idx"])

        row = dict(pf)

        # 랭크 시계열 (t-3 ~ t+3)
        rank_ts = compute_rank_timeseries(rank, agent, patch_act_idx, pre_n=3, post_n=3)
        row.update(rank_ts)

        # VCT 시계열 (t-2 ~ t+2, 0픽 포함)
        vct_ts = compute_vct_timeseries(vct_h, agent, patch_act_idx, pre_n=2, post_n=2)
        row.update(vct_ts)

        # 랭크-VCT 크로스 피처
        cross = compute_cross_features(rank_ts, vct_ts)
        row.update(cross)

        # 역할군 경쟁 피처
        role_comp = compute_role_competition(rank, vct_h, agent, patch_act_idx)
        row.update(role_comp)

        # 패치 이력 피처
        hist = compute_patch_history(patch_feats, agent, patch, patch_act_idx)
        row.update(hist)

        # 맵 의존도 피처 (patch 직전 act 기준)
        if map_dep is not None:
            _md = map_dep[map_dep["agent"] == agent].copy()
            _md["act_idx"] = _md["act"].map(ACT_IDX)
            pre_md = _md[_md["act_idx"] < patch_act_idx].sort_values("act_idx")
            if not pre_md.empty:
                latest = pre_md.iloc[-1]
                row["map_dep_score"]     = latest["map_dep_score"]
                row["map_dep_top_map"]   = latest["top_map"]
                row["map_dep_top_frac"]  = latest["top_map_frac"]
                row["map_dep_in_rotation"] = latest["in_rotation"]
                row["effective_map_dep"] = latest["effective_map_dep"]
            else:
                row["map_dep_score"]     = np.nan
                row["map_dep_top_map"]   = ""
                row["map_dep_top_frac"]  = np.nan
                row["map_dep_in_rotation"] = np.nan
                row["effective_map_dep"] = np.nan

        # 스킬 사용률 피처 (abilities_by_agent_act 기준)
        if abil is not None:
            _ab = abil[abil["agent"] == agent].copy()
            _ab["act_idx"] = _ab["act"].map(ACT_IDX)

            # pre: 패치 직전 act
            ab_pre = _ab[_ab["act_idx"] < patch_act_idx].sort_values("act_idx")
            if not ab_pre.empty:
                ap = ab_pre.iloc[-1]
                for k in ["C", "Q", "E"]:
                    row[f"ab_cast_share_{k}_pre"] = ap.get(f"cast_share_{k}", np.nan)
                row["ab_total_casts_pre"] = ap.get("total_skill_casts", np.nan)
                # E = identity 스킬 사용 비중
                row["ab_identity_cast_share_pre"] = ap.get("cast_share_E", np.nan)

            # post: 패치 직후 act
            ab_post = _ab[_ab["act_idx"] >= patch_act_idx].sort_values("act_idx")
            if not ab_post.empty:
                ap2 = ab_post.iloc[0]
                for k in ["C", "Q", "E"]:
                    row[f"ab_cast_share_{k}_post"] = ap2.get(f"cast_share_{k}", np.nan)
                row["ab_identity_cast_share_post"] = ap2.get("cast_share_E", np.nan)

            # delta: identity 스킬 사용 비중 변화
            pre_id  = row.get("ab_identity_cast_share_pre")
            post_id = row.get("ab_identity_cast_share_post")
            if pre_id is not None and post_id is not None and not (pd.isna(pre_id) or pd.isna(post_id)):
                row["ab_identity_cast_share_delta"] = round(float(post_id) - float(pre_id), 4)

        # ── 랭크 / VCT 분리 판정 ──
        direction = pf["direction"]
        max_w = float(pf.get("max_skill_weight", 2.0))
        if pd.isna(max_w):
            max_w = 2.0

        # 패치 당시 VCT 이력으로 동적 프로필 계산
        vct_pre_avg = vct_ts.get("vct_pr_pre_avg")
        vct_profile = compute_vct_profile(vct_pre_avg)

        # 랭크 판정
        rank_v = _compute_rank_verdict(
            row.get("rank_pr_t-1"), row.get("rank_pr_t+1"), direction, max_w
        )
        row["rank_verdict"] = rank_v

        # VCT 판정
        vct_delta = vct_ts.get("vct_pr_delta_pct")
        vct_post_pr = row.get("vct_pr_t+1")
        vct_v = _compute_vct_verdict(vct_delta, direction, max_w, vct_profile, vct_post_pr)
        row["vct_verdict"]     = vct_v
        row["vct_profile"]     = vct_profile

        # 조합 판정 (Step 2 핵심 피처)
        row["combined_verdict"] = _combine_verdicts(rank_v, vct_v, vct_profile)

        # 하위 호환용 verdict_label (v1): rank 없으면 PENDING
        if rank_v == "NO_DATA":
            row["verdict_label"]  = "PENDING"
            row["verdict_source"] = "none"
        elif vct_v in ("NO_DATA", "MISS", "STRUCTURAL_MISS", "NA") and rank_v != "NO_DATA":
            row["verdict_label"]  = row["combined_verdict"]
            row["verdict_source"] = "rank"
        else:
            row["verdict_label"]  = row["combined_verdict"]
            row["verdict_source"] = "vct"

        rows.append(row)

    df = pd.DataFrame(rows)

    # 6. 요약 출력
    print(f"\n  생성: {len(df)}행 / {df.shape[1]}컬럼")
    print()
    print("[rank_verdict 분포]")
    print(df["rank_verdict"].value_counts().to_string())
    print()
    print("[vct_verdict 분포]")
    print(df["vct_verdict"].value_counts().to_string())
    print()
    print("[combined_verdict 분포]")
    print(df["combined_verdict"].value_counts().to_string())
    print()
    print("[핵심 케이스 확인]")
    key_cols = ["agent","patch","direction","vct_profile",
                "rank_pr_t-1","rank_pr_t+1","rank_verdict",
                "vct_pr_t-1","vct_pr_t+1","vct_verdict","combined_verdict"]
    key = df[df["agent"].isin(["Yoru","Chamber","Jett","Reyna"])][key_cols].sort_values(["agent","patch"])
    print(key.to_string(index=False))

    print()
    print("[PENDING / UNKNOWN]")
    pending = df[df["verdict_label"] == "PENDING"][["agent","patch","direction","rank_verdict","vct_verdict"]]
    if not pending.empty:
        print(pending.to_string(index=False))
    else:
        print("  없음")

    # ── 7. 피처 선택 (데이터 누수 제거, ~35개 핵심 피처) ──
    MODEL_FEATURES = [
        # identifiers
        "agent", "patch", "patch_act",
        # patch-level (14)
        "direction",
        "n_changes",
        "n_skills_changed",
        "trigger_type",
        "has_mechanic",
        "value_chg_max_abs",
        "max_skill_weight",
        "patch_importance_score",
        "has_identity_change",
        "identity_nerfed",
        "identity_buffed",
        "has_ult_change",
        "mobility_skill_nerfed",
        # rank pre-patch (7)
        "rank_pr_t-1",
        "rank_wr_t-1",
        "rank_pr_pre_avg",
        "rank_wr_pre_avg",
        "rank_pr_pre_slope",
        "rank_wr_vs50_pre",
        "rank_pre_n_acts",
        # vct pre-patch (5)
        "vct_pr_t-1",
        "vct_pr_pre_avg",
        "vct_pr_pre_slope",
        "vct_absence_pre",
        "vct_pre_n_events",
        # cross pre-patch (2)
        "rank_vct_pr_gap_pre",
        "vct_rank_pr_ratio",
        # role competition pre-patch (9)
        "agent_role",
        "agent_subrole",
        "role_rank_pre",
        "role_pr_share_pre",
        "role_rival_pr_mean_pre",
        "role_meta_trend",
        "subrole_rank_pre",
        "subrole_rival_pr_mean_pre",
        "subrole_meta_trend",
        # patch history (6)
        "n_prev_patches",
        "prev_nerf_count",
        "prev_buff_count",
        "acts_since_last_patch",
        "last_patch_direction",
        "multi_patch_4acts",
        # rank post-patch (2) — 패치 효과 판정용, step2 피처에서만 사용
        "rank_pr_t+1",
        "rank_wr_t+1",
        # verdict (Step 2 피처 / 레이블)
        "rank_verdict",
        "vct_verdict",
        "vct_profile",
        "combined_verdict",
        "verdict_label",
        "verdict_source",
    ]

    # 존재하는 컬럼만 선택 (없는 피처는 경고만)
    missing = [c for c in MODEL_FEATURES if c not in df.columns]
    if missing:
        print(f"\n  [경고] 없는 컬럼 (스킵): {missing}")
    model_cols = [c for c in MODEL_FEATURES if c in df.columns]
    df_model = df[model_cols].copy()

    print(f"\n  피처 선택: {df.shape[1]}컬럼 → {df_model.shape[1]}컬럼")
    print(f"  (identifiers 3, 타겟 2 제외 실제 피처: {df_model.shape[1]-5}개)")

    # NaN 비율 출력 (피처만)
    feat_cols = [c for c in model_cols if c not in ("agent","patch","patch_act","verdict_label","verdict_source")]
    nan_rates = df_model[feat_cols].isna().mean().sort_values(ascending=False)
    high_nan = nan_rates[nan_rates > 0.1]
    if not high_nan.empty:
        print("\n  [NaN > 10% 피처]")
        for col, rate in high_nan.items():
            print(f"    {col}: {rate:.0%}")

    df_model.to_csv("training_data.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: training_data.csv  ({len(df_model)}행 x {df_model.shape[1]}컬럼)")
    return df_model


if __name__ == "__main__":
    df = main()
