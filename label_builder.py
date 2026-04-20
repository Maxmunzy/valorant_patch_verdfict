"""
label_builder.py
(요원, 액트) 쌍의 패치 레이블 생성 함수군

5-class 레이블:
  stable      — 지표가 평균 근처, 패치 없음
  mild_nerf   — 비패치: 너프 신호 지속 중  /  패치: 첫 너프 + 보조 스킬
  strong_nerf — 패치: followup/correction 너프 OR 핵심 스킬(E/X) 너프
  mild_buff   — 비패치: 버프 신호 지속 중  /  패치: 첫 버프 + 보조 스킬
  strong_buff — 패치: followup/correction 버프 OR 핵심 스킬(E/X) 버프 OR rework

비패치 행 레이블 원칙:
  - strong은 실제 패치 행에서만 부여 (비패치는 최대 mild)
  - rank_pr_excess (요원별 베이스라인 대비 초과) 기준 → 제트 등 고베이스 요원 자연 처리
  - 지속성 조건: rank_pr_slope >= -0.5 (신호가 유지되는 중, 이미 해소 중이면 stable)
  - 랭크 + VCT 중 하나라도 명확한 방향 신호 있으면 mild 부여
"""

from agent_data import SKILL_WEIGHT, AGENT_PR_BASELINE as _PR_BASELINE

_DEFAULT_BASELINE = 5.0


def classify_stable_state(feat, agent=None, prev_label=None):
    """
    비패치 행 레이블 결정 — 최대 mild (strong은 실제 패치에서만)

    너프 방향 조건 (하나라도 해당):
      A) rank 신호: rank_pr_excess > NERF_PR_THRESH  AND  rank_wr_vs50 > 0
      B) VCT 상대 신호: vct_pr_excess > NERF_VCT_THRESH
      C) VCT 절대 지배: vct_pr > 35% (역대 평균 무관 — Viper/Omen 타입)

    버프 방향 조건 (하나라도 해당):
      A) rank 신호: rank_pr_excess < BUFF_PR_THRESH  AND  rank_wr_vs50 < BUFF_WR_THRESH
      B) 픽률 극단: rank_pr_pct < FLOOR_THRESH

    지속성 조건: rank_pr_slope >= -0.8

    신호 캐리오버: 이전 액트에서 mild_nerf/mild_buff였고, 현재 지표가 여전히
    이상(해소되지 않음)이면 이전 레이블 유지
    """
    rank_pr      = float(feat.get("rank_pr", 0) or 0)  # 원본 스케일 (1~17)
    rank_wr      = float(feat.get("rank_wr", 50) or 50)
    rank_wr_vs50 = rank_wr - 50.0
    rank_pr_slope = float(feat.get("rank_pr_slope", 0) or 0)
    rank_pr_avg3 = float(feat.get("rank_pr_avg3", rank_pr) or rank_pr)
    vct_pr_last  = float(feat.get("vct_pr_last", 0) or 0)
    vct_pr_avg   = float(feat.get("vct_pr_avg", 0) or 0)

    # baseline도 원본 스케일 → ×5 없이 직접 비교
    baseline = _PR_BASELINE.get(agent, _DEFAULT_BASELINE) if agent else _DEFAULT_BASELINE
    rank_pr_excess = rank_pr - baseline           # 원본 스케일 비교
    vct_pr_excess  = vct_pr_last - vct_pr_avg

    # ── 임계값 (원본 스케일 기준: 1 ≈ 5%p) ─────────────────────────────��──────
    NERF_PR_THRESH    =  1.5   # baseline 대비 ~7.5%p 초과
    NERF_VCT_REL      = 10.0   # VCT 역대 평균보다 10%p 초과
    NERF_VCT_ABS      = 35.0   # VCT 절대 지배 기준 (Viper/Omen 타입)
    BUFF_PR_THRESH    = -0.5   # baseline 대비 ~2.5%p 미달
    BUFF_WR_THRESH    = -0.5   # 승률 49.5% 미만
    FLOOR_THRESH      =  1.0   # 픽률 ~5% 미만 (원본 스케일)
    PERSIST_SLOPE     = -0.8   # 급하락 중이면 해소 간주

    sustained = rank_pr_slope >= PERSIST_SLOPE

    # ── 너프 신호 ──────────────────────────────────────────────────────────────
    nerf_rank    = rank_pr_excess > NERF_PR_THRESH and rank_wr_vs50 > 0
    nerf_vct_rel = vct_pr_excess > NERF_VCT_REL
    nerf_vct_abs = vct_pr_last > NERF_VCT_ABS     # ★ 신규: VCT 절대 지배

    if (nerf_rank or nerf_vct_rel or nerf_vct_abs) and sustained:
        return "mild_nerf"

    # ── 버프 신호 ──────────────────────────────────────────────────────────────
    buff_rank  = rank_pr_excess < BUFF_PR_THRESH and rank_wr_vs50 < BUFF_WR_THRESH
    buff_floor = rank_pr < FLOOR_THRESH

    if (buff_rank or buff_floor) and sustained:
        return "mild_buff"

    # ── 신호 캐리오버: 이전 액트 신호가 해소되지 않았으면 유지 ─────────────────
    # 해소 = 현재 독립적으로 봤을 때 신호가 하나도 안 잡히는 상태
    if prev_label == "mild_nerf":
        # 랭크 너프 신호 OR VCT 너프 신호 중 하나라도 남아있으면 유지
        still_nerf_rank = rank_pr_excess > NERF_PR_THRESH and rank_wr_vs50 > 0
        still_nerf_vct  = vct_pr_last > NERF_VCT_ABS or vct_pr_excess > NERF_VCT_REL
        if still_nerf_rank or still_nerf_vct:
            return "mild_nerf"

    if prev_label == "mild_buff":
        # 버프 신호가 남아있으면 유지
        still_buff_rank = rank_pr_excess < BUFF_PR_THRESH and rank_wr_vs50 < BUFF_WR_THRESH
        still_buff_floor = rank_pr < FLOOR_THRESH
        if still_buff_rank or still_buff_floor:
            return "mild_buff"

    return "stable"


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
    5-class 패치 레이블 생성

    strong 기준:
      - followup/correction (이전 패치 효과 없어 추가 조정)
      - 핵심 스킬(E/X) 변경
      - rework 필요 (랭크+VCT 모두 극단적으로 낮음)
    """
    nb = patch_rows[patch_rows["direction"].isin(["nerf", "buff"])]
    if nb.empty:
        return "stable", {}

    direction = "nerf" if (nb["direction"] == "nerf").sum() >= (nb["direction"] == "buff").sum() else "buff"
    skill     = dominant_skill(nb)
    trigger   = dominant_trigger(nb)
    context   = detect_context(agent, target_act_idx, step1_df)

    is_strong = (
        context in ("followup", "correction")
        or skill in ("E", "X")
        or check_rework_needed(feat)
    )

    if direction == "nerf":
        label = "strong_nerf" if is_strong else "mild_nerf"
    else:
        label = "strong_buff" if is_strong else "mild_buff"

    meta = {
        "label_direction": direction,
        "label_skill":     skill,
        "label_trigger":   trigger,
        "label_context":   context,
    }
    return label, meta
