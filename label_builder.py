"""
label_builder.py
(요원, 액트) 쌍의 패치 레이블 생성 함수군

레이블 구조:
  stable                          ← 패치 없음
  nerf_{skill}_{trigger}          ← 일반 너프
  nerf_{skill}_{trigger}_followup ← 1차 너프 효과 없어 추가 너프
  correction_nerf                 ← 과버프 후 재조정
  buff_{skill}_{trigger}          ← 일반 버프
  buff_{skill}_{trigger}_followup ← 1차 버프 효과 없어 추가 버프
  correction_buff                 ← 과너프 후 복구
  rework                          ← 반복 DUAL_MISS → 수치 조정 한계
"""

from agent_data import SKILL_WEIGHT


def dominant_skill(patch_rows):
    """패치에서 가장 중요한 스킬 키 반환"""
    nb = patch_rows[patch_rows["direction"].isin(["nerf", "buff"])]
    if nb.empty:
        return "multi"
    weights = nb["skill_key"].map(lambda k: SKILL_WEIGHT.get(k, 1.0))
    best_idx = weights.idxmax()
    sk = nb.loc[best_idx, "skill_key"]
    return sk if sk in ("E", "Q", "C", "X") else "multi"


def dominant_trigger(patch_rows):
    """패치에서 주된 trigger_type 반환"""
    nb = patch_rows[patch_rows["direction"].isin(["nerf", "buff"])]
    if nb.empty:
        return "rank"
    nb = nb.dropna(subset=["trigger_type"])
    if nb.empty:
        return "rank"
    counts = nb["trigger_type"].value_counts()
    if counts.empty:
        return "rank"
    t = counts.index[0]
    if t == "pro_dominance": return "pro_dom"
    if t == "role_invasion":  return "role_inv"
    if t == "skill_ceiling":  return "skill_ceil"
    return "rank"


def classify_stable_state(feat):
    """
    패치 없는 행에 대한 레이블 결정.

    핵심 원칙: 매 액트마다 현재 수치만으로 재판정.
    acts_since / last_direction 같은 이력 조건 없음.
    액트 = ~2개월 단위이므로 매 액트 독립 판정이 가장 단순하고 정확함.

      nerf_followup  ← 랭크 or VCT 수치가 너프 기준 초과 상태인데 패치 없음
      buff_followup  ← 랭크 수치가 버프 기준 미달 상태인데 패치 없음
      stable_*       ← 수치가 임계치 안에 있어서 조정 불필요
    """
    rank_pr      = float(feat.get("rank_pr", 0) or 0)      # slots 단위 (×5 = %)
    vct_pr       = float(feat.get("vct_pr_last", 0) or 0)  # % 단위
    rank_wr_vs50 = float(feat.get("rank_wr_vs50", 0) or 0)
    vct_profile  = feat.get("vct_profile", "")
    map_hhi      = float(feat.get("map_hhi", 0.3) or 0.3)

    rank_pr_pct = rank_pr * 5  # % 단위로 변환

    # ── 1) 너프 기준 ──────────────────────────────────────────────────────────
    # 신호 A — 랭크 지배: 픽률 높고 AND 승률 평균 이상
    nerf_rank = rank_pr_pct >= 20.0 and rank_wr_vs50 >= 0.0
    # 신호 B — 승률 극단: 픽률 무관하게 승률이 비정상적으로 높음
    nerf_wr   = rank_wr_vs50 >= 2.5
    # 신호 C — VCT 지배 + 맵 비종속: pro_dom 패턴 (맵 로테 영향 없는 요원)
    nerf_vct  = vct_pr >= 40.0 and map_hhi <= 0.15 and rank_wr_vs50 >= -1.0
    if nerf_rank or nerf_wr or nerf_vct:
        return "nerf_followup"

    # ── 2) 버프 기준 ──────────────────────────────────────────────────────────
    # 신호 A — 랭크 부진: 픽률 낮고 AND 승률도 낮음
    buff_rank = rank_pr_pct <= 12.0 and rank_wr_vs50 <= -1.5
    # 신호 B — 승률 극단: 픽률 무관하게 승률이 비정상적으로 낮음
    buff_wr   = rank_wr_vs50 <= -4.0
    # 신호 C — 존재감 없음: 픽률이 사실상 0에 가까움
    buff_pr   = rank_pr_pct <= 5.0
    if buff_rank or buff_wr or buff_pr:
        return "buff_followup"

    # ── 3) stable 세분화 ──────────────────────────────────────────────────────
    if rank_pr > 12 or vct_pr > 35 or rank_wr_vs50 > 3.0:
        return "stable_strong"

    if rank_pr < 3.0 and vct_pr < 3.0 and vct_profile not in ("pro_absent", "pro_unknown"):
        return "stable_weak"

    return "stable_balanced"


def detect_context(agent, target_act_idx, step1_df):
    """
    과거 verdict 이력을 보고 패치 컨텍스트 결정
      correction: 이전 패치가 OVERSHOOT이었음
      followup:   이전 패치가 MISS/DUAL_MISS였음
      first:      이전 패치 없거나 HIT → 새 패치
    """
    hist = step1_df[
        (step1_df["agent"] == agent) &
        (step1_df["patch_act_idx"] < target_act_idx)
    ].sort_values("patch_act_idx")

    if hist.empty:
        return "first"

    last = hist.iloc[-1]
    cv        = last.get("combined_verdict", "UNKNOWN")
    direction = last.get("direction", "")

    if "OVERSHOOT" in cv:
        return "correction"
    if "MISS" in cv and direction in ("buff", "nerf"):
        return "followup"
    return "first"


def check_rework_needed(feat):
    """
    랭크도 VCT도 안 나오는 요원 → 수치 조정 한계, rework 필요

    조건:
      rank_pr < 2%  AND  vct_pr < 2%
      AND 과거 평균(rank_pr_avg3)도 낮음  ← 원래부터 안 쓰였음
      AND 급격한 하락 중이 아님           ← 과너프 저점 제외
    """
    rank_pr      = float(feat.get("rank_pr")      or 0)
    vct_pr       = float(feat.get("vct_pr_last")  or 0)
    rank_pr_avg3 = float(feat.get("rank_pr_avg3") or rank_pr)
    rank_slope   = float(feat.get("rank_pr_slope") or 0)

    if rank_pr >= 2.0 or vct_pr >= 2.0:
        return False

    rank_pr_peak = float(feat.get("rank_pr_peak") or 0)
    if rank_pr_peak > 5.0:
        return False

    if rank_pr_avg3 > 3.0 and rank_pr < rank_pr_avg3 * 0.5:
        return False

    if rank_slope < -1.5:
        return False

    return True


def build_patch_label(agent, target_act_idx, patch_rows, step1_df, feat):
    """
    단일 (요원, 다음 액트)에 해당하는 패치 레이블 생성
    patch_rows: 해당 요원, 해당 액트의 실제 패치 행들
    feat: 현재 액트 기준 피처 (rework 판정에 사용)
    """
    nb = patch_rows[patch_rows["direction"].isin(["nerf", "buff"])]
    if nb.empty:
        return "stable", {}

    direction = "nerf" if (nb["direction"] == "nerf").sum() >= (nb["direction"] == "buff").sum() else "buff"
    skill     = dominant_skill(nb)
    trigger   = dominant_trigger(nb)
    context   = detect_context(agent, target_act_idx, step1_df)

    if check_rework_needed(feat):
        label = "rework"
    elif context == "correction":
        label = f"correction_{direction}"
    elif context == "followup":
        label = f"{direction}_{skill}_{trigger}_followup"
    else:
        label = f"{direction}_{skill}_{trigger}"

    meta = {
        "label_direction": direction,
        "label_skill":     skill,
        "label_trigger":   trigger,
        "label_context":   context,
    }
    return label, meta
