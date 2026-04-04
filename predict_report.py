"""
Valorant Patch Verdict Report
각 요원의 버프/너프 확률과 근거를 리포트 형태로 출력.
픽률(rank/vct) + 승률 + 인과관계(counter/replace/kit가치) 통합 분석.
"""

import sys
import joblib
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# Windows 콘솔 UTF-8 출력
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ─── 요원 메타 데이터 임포트 ───────────────────────────────────────────────────
try:
    from build_step2_data import (
        AGENT_DESIGN, AGENT_RELATIONS, AGENT_KIT,
        compute_kit_score, get_kit_flags, _DEFAULT_DESIGN,
    )
except ImportError:
    AGENT_DESIGN = {}
    AGENT_RELATIONS = {}
    AGENT_KIT = {}
    def compute_kit_score(a): return 2.5
    def get_kit_flags(a): return {}
    _DEFAULT_DESIGN = {}

# ─── 설정 ────────────────────────────────────────────────────────────────────

BUFF_CLASSES = {"buff_followup", "buff_pro", "buff_rank", "correction_buff"}
NERF_CLASSES = {"nerf_followup", "nerf_pro", "nerf_rank", "correction_nerf"}

PATCH_TYPE_KO = {
    "buff_rank":        "버프 (랭크)",
    "buff_pro":         "버프 (대회)",
    "buff_followup":    "버프 (추가)",
    "correction_buff":  "버프 (과너프 복구)",
    "nerf_rank":        "너프 (랭크)",
    "nerf_pro":         "너프 (대회)",
    "nerf_followup":    "너프 (추가)",
    "correction_nerf":  "너프 (과버프 조정)",
    "rework":           "리워크",
    "stable":           "안정",
}

# ─── 도메인 규칙 보정 ─────────────────────────────────────────────────────────

def apply_domain_rules(row, p_patch, p_buff_raw, p_nerf_raw):
    """
    Stage B의 원시 확률에 도메인 규칙을 적용해 최종 버프/너프 확률 반환.
    방향 혼동(buff_miss인데 nerf 예측) 및 구조적 억제(랭크 전용 요원)를 보정.
    """
    buff_miss        = float(row.get("buff_miss_flag", 0) or 0)
    nerf_miss        = float(row.get("nerf_miss_flag", 0) or 0)
    both_weak        = float(row.get("both_weak_signal", 0) or 0)
    rank_pr          = float(row.get("rank_pr", 0) or 0)
    vct_pr           = float(row.get("vct_pr_last", 0) or 0)
    dir_code         = float(row.get("dir_verdict_code", 0) or 0)
    _acts_raw = row.get("_raw_acts_since_patch", None)
    acts_since = int(_acts_raw) if _acts_raw is not None else int(row.get("acts_since_patch", 99) or 99)
    last_dir   = str(row.get("_raw_last_direction", None) or row.get("last_direction", "none") or "none")

    # 규칙 0: 이번 액트에 이미 패치됨 (acts_since_patch=0) → 효과 대기 중, 추가 패치 억제
    if acts_since == 0:
        if last_dir == "nerf":
            p_nerf_raw = p_nerf_raw * 0.2
            p_patch    = p_patch * 0.4
        elif last_dir == "buff":
            p_buff_raw = p_buff_raw * 0.2
            p_patch    = p_patch * 0.4

    # 규칙 1: 버프 후 MISS인데 nerf 확률이 더 높음 → buff 방향으로 재가중
    if buff_miss and p_nerf_raw > p_buff_raw:
        p_buff_raw, p_nerf_raw = p_buff_raw * 2.2, p_nerf_raw * 0.45

    # 규칙 2: 너프 후 MISS인데 buff 확률이 더 높음 → nerf 방향으로 재가중
    if nerf_miss and p_buff_raw > p_nerf_raw:
        p_nerf_raw, p_buff_raw = p_nerf_raw * 2.2, p_buff_raw * 0.45

    # 규칙 3 (구 design_rank_only 억제 룰 제거):
    # "랭크 전용 요원"을 고정 분류하면 메타 변화에 대응 못 함.
    # 대신 rank_pr/vct_pr 실수값이 모델에서 직접 신호로 작동.

    # 규칙 4: 두 도메인 모두 낮음 + 버프 방향 → p_patch 상향
    # both_weak: rank_pr < 3% AND vct_pr < 5% AND "both" 설계 요원
    if both_weak and dir_code > 0:
        p_patch = min(1.0, p_patch * 1.3)

    # 규칙 5: 실력 천장 높은 요원 (Neon, Yoru, Jett, Sova, Viper 등) — 평균 랭크 통계가
    # 장인 가치를 과소평가. 랭크 저픽이 관찰돼도 너프 신호로 해석 금지.
    # high 천장 + 낮은 랭크 픽률 → p_nerf 억제 (실제 강도는 평균보다 높음)
    skill_ceil = float(row.get("skill_ceiling_score", 0.5) or 0.5)
    vct_pr_r5  = float(row.get("vct_pr_last", 0) or 0)
    vct_wr     = float(row.get("vct_wr_last", 50) or 50)

    # 규칙 5: 실력 천장 높은 요원 — 잘 쓰면 고점이 높아서 너프 위험군
    if skill_ceil >= 0.7 and vct_pr_r5 >= 6.0:
        p_nerf_raw = p_nerf_raw * 1.25

    # 규칙 6: VCT 승률 이상 고점 — 픽률이 낮아도 이기는 비율이 극도로 높으면 너프 신호
    # 픽률은 너프로 억눌렸지만 쓰는 팀은 여전히 압도적으로 이기는 경우 (네온 등)
    # → acts_since 기반 보수성(1액트=효과관찰중)을 VCT 승률로 오버라이드
    if vct_wr >= 60.0 and vct_pr_r5 >= 5.0:
        if vct_wr >= 65.0:
            # 65% 이상 → 패치 억눌려도 여전히 강함. 강하게 강화
            p_nerf_raw = p_nerf_raw * 2.5
            p_patch    = min(1.0, p_patch * 1.6)
        else:
            # 60~65% → 경고 수준
            p_nerf_raw = p_nerf_raw * 1.7
            p_patch    = min(1.0, p_patch * 1.4)

    # 정규화
    total = p_buff_raw + p_nerf_raw
    if total > 0:
        p_buff_norm = p_buff_raw / total
        p_nerf_norm = p_nerf_raw / total
    else:
        p_buff_norm = p_nerf_norm = 0.5

    return p_patch, p_buff_norm, p_nerf_norm


# ─── 인과 분석 레이어 ─────────────────────────────────────────────────────────

def get_suppression_reasons(agent: str) -> list:
    """
    AGENT_RELATIONS에서 이 요원이 억압받는 인과 관계 목록 반환.
    각 항목은 (억압 요원, 유형, 근거) 튜플.
    """
    rel = AGENT_RELATIONS.get(agent, {})
    results = []
    for item in rel.get("suppressed_by", []):
        results.append((item["agent"], item["type"], item["reason"]))
    return results

def get_structural_note(agent: str) -> str:
    """구조적 설계 한계 또는 지배 메모 반환"""
    rel = AGENT_RELATIONS.get(agent, {})
    return (
        rel.get("structural_weakness", "") or
        rel.get("dominance_note", "") or
        rel.get("buff_note", "") or
        rel.get("resilience_note", "") or
        rel.get("meta_impact", "")
    )

def kit_analysis_text(agent: str, rank_pr: float, vct_pr: float) -> str:
    """
    스킬 등급(S/A/B/C) 기반 구조적 분석 텍스트.
    킷 가치 vs 현재 픽률 불일치를 설명.
    """
    kit_score = compute_kit_score(agent)
    flags = get_kit_flags(agent)

    parts = []

    # 킷 등급 요약
    tier_str = f"킷 가치 {kit_score:.2f}/4.0"
    if kit_score >= 3.5:
        tier_str += " (최고 등급 — S급 유틸 다수)"
    elif kit_score >= 3.0:
        tier_str += " (고등급 — A급 이상 주력)"
    elif kit_score >= 2.5:
        tier_str += " (중등급 — A/B급 혼합)"
    elif kit_score >= 2.0:
        tier_str += " (저등급 — B/C급 위주)"
    else:
        tier_str += " (최저 등급 — C급 스킬 다수)"
    parts.append(tier_str)

    # 핵심 유틸 보유 여부
    utilities = []
    if flags.get("high_value_smoke"): utilities.append("S급 연막")
    if flags.get("high_value_cc"):    utilities.append("S급 CC")
    if flags.get("has_info"):         utilities.append("정보획득")
    if flags.get("has_mobility"):     utilities.append("이동기")
    if utilities:
        parts.append("핵심 유틸: " + "·".join(utilities))

    # 저가치 스킬 경고
    low_val = []
    if flags.get("has_revive"): low_val.append("부활(C급)")
    if flags.get("has_heal"):   low_val.append("힐(C급)")
    if low_val and kit_score < 2.5:
        parts.append("⚠ 저가치 스킬 의존: " + "·".join(low_val) + " → 팀 기여 구조적 한계")

    # 킷 가치 vs 픽률 불일치
    if kit_score >= 3.0 and rank_pr > 10:
        parts.append(f"→ 고가치 킷 + 높은 픽률({rank_pr:.1f}%) = 너프 구조적 근거")
    elif kit_score < 2.3 and rank_pr < 3.0 and vct_pr < 3.0:
        parts.append(f"→ 저가치 킷 + 양쪽 저픽 = 수치 조정만으론 메타 진입 어려움")
    elif kit_score >= 2.5 and rank_pr < 3.0 and vct_pr < 5.0:
        parts.append(f"→ 충분한 킷 가치인데 저픽 = 메타 억압 또는 숙련도 문제")

    return " / ".join(parts)


# ─── 근거 생성 (통합 다층 분석) ──────────────────────────────────────────────

def generate_reasons(row, verdict):
    """
    [Layer 1] 통계 신호 — 픽률(랭크/VCT), 승률, 추세
    [Layer 2] 설계 정체성 — 랭크전용/프로전용/복합, 대체 가능성
    [Layer 3] 킷 가치 — S/A/B/C 스킬 등급 기반 구조적 분석
    [Layer 4] 인과 관계 — counter/replace/compete 관계 (AGENT_RELATIONS)
    """
    agent         = row.get("agent", "")
    rank_pr       = float(row.get("rank_pr", 0) or 0)
    vct_pr        = float(row.get("vct_pr_last", 0) or 0)
    rank_wr_vs50  = float(row.get("rank_wr_vs50", 0) or 0)
    rank_pr_peak  = float(row.get("rank_pr_peak", 0) or 0)
    vct_pr_peak   = float(row.get("vct_pr_peak_all", 0) or 0)
    rank_vs_peak  = float(row.get("rank_pr_vs_peak", 1) or 1)
    map_explains  = float(row.get("map_explains_vct_drop", 0) or 0)
    buff_miss     = float(row.get("buff_miss_flag", 0) or 0)
    nerf_miss     = float(row.get("nerf_miss_flag", 0) or 0)
    buff_hit      = float(row.get("buff_hit_flag", 0) or 0)
    nerf_hit      = float(row.get("nerf_hit_flag", 0) or 0)
    both_weak     = float(row.get("both_weak_signal", 0) or 0)
    rank_low_unexp= float(row.get("rank_low_unexpected", 0) or 0)
    vct_low_unexp = float(row.get("vct_low_unexpected", 0) or 0)
    dir_code      = float(row.get("dir_verdict_code", 0) or 0)
    skill_ceil    = float(row.get("skill_ceiling_score", 0.5) or 0.5)
    vct_wr        = float(row.get("vct_wr_last", 50) or 50)
    acts_since    = int(row.get("acts_since_patch", 0) or 0)
    recent_dmiss  = int(row.get("recent_dual_miss_count", 0) or 0)
    top_map_in    = int(row.get("top_map_in_rotation", 1) or 1)
    kit_score     = float(row.get("kit_score", compute_kit_score(agent)) or 2.5)
    replaceability= float(row.get("agent_replaceability",
                         AGENT_DESIGN.get(agent, _DEFAULT_DESIGN).get("replaceability", 0.5)) or 0.5)

    reasons = []
    causal_reasons = []

    # ────────────────────────────────────────────────────────────────────────
    # Layer 1: 통계 신호 (픽률 + 승률)
    # ────────────────────────────────────────────────────────────────────────

    # ── 안정 ──
    if verdict == "stable":
        if map_explains > 2 and not top_map_in:
            reasons.append("[맵] 주력 맵 대회 풀 미포함 → 픽률 하락은 밸런스 문제 아님")
        elif rank_pr > 5 and vct_pr > 5:
            reasons.append(f"[픽률] 랭크 {rank_pr:.1f}% / VCT {vct_pr:.1f}% — 양쪽 적정")
        elif buff_hit:
            reasons.append("[패치] 최근 버프 효과 확인 (HIT) — 추가 조정 대기")
        elif nerf_hit:
            reasons.append("[패치] 최근 너프 효과 확인 (HIT) — 추가 조정 대기")
        elif acts_since > 4:
            reasons.append(f"[패치이력] {acts_since} 액트 무패치 — 현재 상태 수용 중")
        else:
            reasons.append("[통계] 패치 신호 미약 — 밸런스 유지 중")

    # ── 버프 ──
    elif "buff" in verdict:
        if "correction" in verdict:
            reasons.append(f"[패치] 과너프 복구 필요 — 전성기 대비 {rank_vs_peak*100:.0f}% 수준")
        elif buff_miss:
            if both_weak:
                reasons.append(
                    f"[패치] 버프 후 랭크({rank_pr:.1f}%)·VCT({vct_pr:.1f}%) 모두 개선 없음 (DUAL_MISS)"
                )
            else:
                reasons.append("[패치] 이전 버프 효과 미달 — 추가 조정 필요")

        if rank_low_unexp and rank_pr < 2.5:
            reasons.append(f"[픽률] 랭크 {rank_pr:.1f}% — 설계 의도 대비 낮음")
        if skill_ceil >= 0.7 and rank_pr < 5.0:
            reasons.append(
                f"[실력천장] 고점 높은 요원 — 다루기 어려워서 랭크 {rank_pr:.1f}% 저픽, "
                "숙련 시 강력해지므로 버프 여지 존재"
            )
        if vct_low_unexp and vct_pr < 5:
            reasons.append(f"[픽률] VCT {vct_pr:.1f}% — 기대치 미달")
        if rank_vs_peak < 0.4 and rank_pr_peak > 3:
            reasons.append(f"[추세] 전성기({rank_pr_peak:.1f}%) 대비 {rank_vs_peak*100:.0f}% 수준으로 하락")
        if rank_wr_vs50 < -1.5:
            reasons.append(f"[승률] 랭크 승률 {50+rank_wr_vs50:.1f}% — 기대치 미달")
        if recent_dmiss >= 2:
            reasons.append(f"[패치이력] {recent_dmiss}회 연속 DUAL_MISS — 조정 누적 필요")
        if map_explains > 2 and not top_map_in and vct_pr < 5:
            reasons.append("[맵] 주력 맵 대회 풀 미포함 + 랭크도 저픽 — 맵 무관 버프 검토")

    # ── 너프 ──
    elif "nerf" in verdict:
        if "correction" in verdict:
            reasons.append(f"[패치] 과버프 후 재조정 — VCT {vct_pr:.1f}% 급상승")
        elif nerf_miss:
            reasons.append("[패치] 이전 너프 효과 미달 — 추가 조정 필요")
        if rank_pr > 12:
            reasons.append(f"[픽률] 랭크 {rank_pr:.1f}% — 과도한 선택 집중")
        if vct_pr > 35:
            reasons.append(f"[픽률] VCT {vct_pr:.1f}% — 대회 메타 지배")
        elif vct_pr > 20:
            reasons.append(f"[픽률] VCT {vct_pr:.1f}% — 프로 기용 과다")
        if rank_wr_vs50 > 2.5:
            reasons.append(f"[승률] 랭크 승률 {50+rank_wr_vs50:.1f}% — 밸런스 초과")
        if dir_code < -1.5:
            reasons.append("[패치] 이전 너프 후에도 여전히 강함 (HIT) — 연속 조정")
        if skill_ceil >= 0.7 and vct_pr >= 6.0:
            reasons.append(
                f"[실력천장] 고점 높은 요원 — 장인이 쓸 경우 실제 강도가 랭크 통계 이상 "
                f"(VCT {vct_pr:.1f}% 프로 기용이 이를 뒷받침)"
            )
        if vct_wr >= 60.0 and vct_pr >= 5.0:
            reasons.append(
                f"[VCT승률] VCT 승률 {vct_wr:.1f}% — 픽률이 억눌려도 쓰는 팀은 압도적으로 이김 "
                "(픽률 기반 안정 판단 오류 주의)"
            )

    # ── 리워크 ──
    elif "rework" in verdict:
        reasons.append(
            f"[픽률] 랭크({rank_pr:.1f}%)·VCT({vct_pr:.1f}%) 장기 저픽 — 수치 조정 한계"
        )

    # ────────────────────────────────────────────────────────────────────────
    # Layer 2: 설계 정체성 (대체 가능성)
    # ────────────────────────────────────────────────────────────────────────
    design = AGENT_DESIGN.get(agent, _DEFAULT_DESIGN)
    niche = design.get("role_niche", "")
    unique = design.get("unique_value", "")
    if unique and verdict not in ("stable",):
        reasons.append(f"[정체성] {unique}")

    if replaceability >= 0.7 and rank_pr < 3.0:
        reasons.append(f"[대체성] 대체 가능성 높음({replaceability:.1f}) — 메타 이탈 시 픽률 급감 구조")
    elif replaceability <= 0.3:
        reasons.append(f"[대체성] 대체 불가 역할 ({niche}) — 픽률 바닥 존재")

    # ────────────────────────────────────────────────────────────────────────
    # Layer 3: 킷 가치 분석 (스킬 등급)
    # ────────────────────────────────────────────────────────────────────────
    kit_text = kit_analysis_text(agent, rank_pr, vct_pr)
    if kit_text:
        reasons.append(f"[킷] {kit_text}")

    # ────────────────────────────────────────────────────────────────────────
    # Layer 4: 인과 관계 (counter/replace/compete)
    # ────────────────────────────────────────────────────────────────────────
    suppression = get_suppression_reasons(agent)
    for sup_agent, sup_type, sup_reason in suppression:
        type_ko = {"counter": "카운터", "replaces": "대체", "competes": "경쟁"}.get(sup_type, sup_type)
        causal_reasons.append(f"[{type_ko}] {sup_agent}: {sup_reason}")

    # 구조적 메모 (AGENT_RELATIONS의 special notes)
    struct_note = get_structural_note(agent)
    if struct_note:
        causal_reasons.append(f"[구조] {struct_note}")

    # 인과 관계가 있으면 뒤에 추가
    reasons.extend(causal_reasons)

    if not reasons:
        reasons.append("판단 근거 부족")

    return reasons  # 리스트로 반환 (출력 시 개행 처리)


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    # 파이프라인 로드
    pipe         = joblib.load("step2_pipeline.pkl")
    model_a      = pipe["model_a"]
    model_b      = pipe["model_b"]
    feat_cols    = pipe["feat_cols"]
    label_b_cats = pipe["label_b_cats"]

    # 데이터 로드 (최신 액트)
    df = pd.read_csv("step2_training_data.csv")

    # CAT_COLS 인코딩 (train과 동일하게)
    from sklearn.preprocessing import OrdinalEncoder
    CAT_COLS = [
        "vct_profile", "last_direction",
        "last_rank_verdict", "last_vct_verdict", "patch_streak_direction",
    ]
    # 도메인 규칙에서 문자열 비교에 사용할 원본 컬럼 보존
    raw_cols = ["last_direction", "acts_since_patch"]
    df_raw = df[["agent","act_idx"] + [c for c in raw_cols if c in df.columns]].copy()

    oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    for col in CAT_COLS:
        if col in df.columns:
            df[col] = oe.fit_transform(df[[col]])

    latest = df.loc[df.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
    # 원본 값 merge
    latest_raw = df_raw.loc[df_raw.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
    latest = latest.merge(latest_raw.rename(columns={c: f"_raw_{c}" for c in raw_cols if c in df_raw.columns}),
                          on=["agent","act_idx"], how="left")
    X_now  = latest[feat_cols].values.astype(np.float32)

    # Stage A: p_patch
    prob_patch = model_a.predict_proba(X_now)[:, 1].copy()

    # Stage B: 클래스별 확률
    prob_b_all = model_b.predict_proba(X_now)  # (n_agents, n_classes)

    # 버프/너프 클래스 인덱스
    buff_idx = [i for i, l in enumerate(label_b_cats) if l in BUFF_CLASSES]
    nerf_idx = [i for i, l in enumerate(label_b_cats) if l in NERF_CLASSES]
    rework_idx = [i for i, l in enumerate(label_b_cats) if l == "rework"]

    results = []

    for i, row in latest.iterrows():
        p_raw      = prob_patch[i]
        p_buff_raw = prob_b_all[i, buff_idx].sum()
        p_nerf_raw = prob_b_all[i, nerf_idx].sum()
        p_rework   = prob_b_all[i, rework_idx].sum() if rework_idx else 0.0

        # 도메인 규칙 적용
        p_adj, p_buff_norm, p_nerf_norm = apply_domain_rules(
            row, p_raw, p_buff_raw, p_nerf_raw
        )

        # 최종 확률
        p_stable = 1.0 - p_adj
        p_buff   = p_adj * p_buff_norm
        p_nerf   = p_adj * p_nerf_norm

        # 최고 확률 유형 선택 (max-probability 기준)
        # stable이 최고면 stable, 아니면 buff/nerf 중 높은 방향으로
        if p_stable >= p_buff and p_stable >= p_nerf:
            verdict = "stable"
        elif p_rework * p_adj > 0.28 and p_rework * p_adj > p_buff and p_rework * p_adj > p_nerf:
            verdict = "rework"
        elif p_buff >= p_nerf:
            best_buff = max(buff_idx, key=lambda x: prob_b_all[i, x])
            verdict = label_b_cats[best_buff]
        else:
            best_nerf = max(nerf_idx, key=lambda x: prob_b_all[i, x])
            verdict = label_b_cats[best_nerf]

        # 방향 혼동 보정 (buff_miss인데 nerf 예측)
        buff_miss_f = float(row.get("buff_miss_flag", 0) or 0)
        nerf_miss_f = float(row.get("nerf_miss_flag", 0) or 0)
        if buff_miss_f and "nerf" in verdict and "correction" not in verdict:
            verdict = "buff_followup"
        if nerf_miss_f and "buff" in verdict and "correction" not in verdict:
            verdict = "nerf_followup"

        reason_list = generate_reasons(row, verdict)
        reason = reason_list  # 리스트 보관, 출력 시 개행 처리

        results.append({
            "agent":    row["agent"],
            "act":      row["act"],
            "rank_pr":  row.get("rank_pr", 0),
            "vct_pr":   row.get("vct_pr_last", 0),
            "rank_wr":  float(row.get("rank_wr_vs50", 0) or 0),
            "p_buff":   round(p_buff * 100, 1),
            "p_nerf":   round(p_nerf * 100, 1),
            "p_stable": round(p_stable * 100, 1),
            "verdict":  verdict,
            "reason":   reason,
        })

    res_df = pd.DataFrame(results).sort_values("p_buff", ascending=False)

    # ── 출력 ──────────────────────────────────────────────────────────────────
    act_name = latest["act"].iloc[0]
    print("=" * 70)
    print(f"  Valorant Patch Verdict — {act_name} 기준 예측")
    print("=" * 70)

    buff_agents  = res_df[res_df["verdict"].str.contains("buff|correction_buff", na=False)]
    nerf_agents  = res_df[res_df["verdict"].str.contains("nerf|correction_nerf", na=False)]
    rework_agents= res_df[res_df["verdict"] == "rework"]
    stable_agents= res_df[res_df["verdict"] == "stable"].sort_values("p_stable", ascending=False)

    sections = [
        ("🔺 버프 필요", buff_agents,   "p_buff"),
        ("🔻 너프 필요", nerf_agents,   "p_nerf"),
        ("⚙  리워크",   rework_agents, "p_buff"),
        ("✅  안정",    stable_agents, "p_stable"),
    ]

    for title, group, prob_col in sections:
        if group.empty:
            continue
        print(f"\n{title}")
        print("-" * 72)
        for _, r in group.sort_values(prob_col, ascending=False).iterrows():
            type_ko  = PATCH_TYPE_KO.get(r["verdict"], r["verdict"])
            pct      = r[prob_col]
            agent_nm = r["agent"]
            wr_sign  = "+" if r["rank_wr"] >= 0 else ""
            # 헤더 라인
            print(f"  {agent_nm:<10}  {pct:4.0f}%  [{type_ko}]"
                  f"   랭크 {r['rank_pr']:.1f}%픽 / 승률{wr_sign}{r['rank_wr']:.1f}%"
                  f" | VCT {r['vct_pr']:.1f}%픽")
            # 이유 라인들 (layer별 개행)
            reasons = r["reason"] if isinstance(r["reason"], list) else [r["reason"]]
            for line in reasons:
                print(f"    └ {line}")
            print()

    print("=" * 72)
    print("  확률 요약 (버프% / 너프% / 안정%)")
    print("-" * 72)
    print(f"  {'요원':<12} {'버프':>5} {'너프':>5} {'안정':>5}  {'랭크픽':>6}  {'VCT픽':>6}  예측")
    print("-" * 72)
    for _, r in res_df.sort_values("p_buff", ascending=False).iterrows():
        verdict_ko = PATCH_TYPE_KO.get(r["verdict"], r["verdict"])
        print(f"  {r['agent']:<12} {r['p_buff']:>4.0f}%  {r['p_nerf']:>4.0f}%  {r['p_stable']:>4.0f}%"
              f"  {r['rank_pr']:>5.1f}%  {r['vct_pr']:>5.1f}%  {verdict_ko}")
    print("=" * 72)


if __name__ == "__main__":
    main()
