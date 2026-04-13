"""
Valorant 스킬 변경 시뮬레이터
────────────────────────────────────────────────────────────────────────
유저가 "이 요원의 이 스킬을 이렇게 바꾸면 어떻게 될까?" 를 입력하면:
  - 킷 가치 변화 계산
  - 예상 랭크 픽률 변화 예측
  - 메타 픽 진입 가능성 평가
  - 프로 기용 가능성 평가
  - 어떤 요원과의 경쟁에서 유리/불리해지는지 분석

사용 예시:
  python skill_simulator.py --agent 게코 --skill C --change buff --magnitude 0.8
  python skill_simulator.py --agent 킬조이 --skill E --change nerf --magnitude 0.6
  python skill_simulator.py  (대화형 모드)
"""

import sys
import json
import argparse
from pathlib import Path
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ─── Phase 1/2 데이터 로드 ────────────────────────────────────────────────────
_skills_path  = Path(__file__).parent / "data" / "agent_skills.json"
_lookup_path  = Path(__file__).parent / "impact_lookup.json"
AGENT_SKILLS  = json.loads(_skills_path.read_text(encoding="utf-8"))  if _skills_path.exists()  else {}
IMPACT_LOOKUP = json.loads(_lookup_path.read_text(encoding="utf-8"))  if _lookup_path.exists()  else {}

# 낮을수록 버프인 스탯 키워드
_LOWER_IS_BUFF = ("cooldown", "windup", "cost", "cred", "unequip", "equip",
                  "deploy", "recharge", "restock", "charge time", "cast time",
                  "recovery", "reload", "reactivation")

# ─── 요원 메타 데이터 임포트 ───────────────────────────────────────────────────
try:
    from agent_data import (
        AGENT_DESIGN, AGENT_KIT, AGENT_RELATIONS,
        SKILL_TIER_SCORE, compute_kit_score, get_kit_flags,
        _DEFAULT_DESIGN, _DEFAULT_KIT,
    )
except ImportError as e:
    print(f"[오류] agent_data.py 임포트 실패: {e}")
    sys.exit(1)

# ─── 한국어 이름 → 영어 맵핑 ──────────────────────────────────────────────────
KO_TO_EN = {
    "레이나": "Reyna", "제트": "Jett", "레이즈": "Raze", "네온": "Neon",
    "피닉스": "Phoenix", "아이소": "Iso", "요루": "Yoru", "웨이레이": "Waylay",
    "오멘": "Omen", "바이퍼": "Viper", "브림스톤": "Brimstone", "아스트라": "Astra",
    "클로브": "Clove", "하버": "Harbor",
    "소바": "Sova", "스카이": "Skye", "페이드": "Fade", "브리치": "Breach",
    "케이오": "KAYO", "케이/오": "KAYO", "게코": "Gekko", "테호": "Tejo",
    "사이퍼": "Cypher", "킬조이": "Killjoy", "세이지": "Sage",
    "챔버": "Chamber", "데드록": "Deadlock", "바이스": "Vyse",
}

SKILL_KEYS = ("Q", "E", "C", "X")

# ─── 픽률 민감도 모델 ─────────────────────────────────────────────────────────
# 킷 가치 1점 변화 시 예상 픽률 변화량 (경험 기반 추정치)
# 랭크는 숙련도 변동이 커서 민감도 낮음, VCT는 수치에 직결되어 민감도 높음
PR_SENSITIVITY_RANK = {
    "S→A": -2.5,   # S급 스킬을 A급으로 너프 → 랭크 픽률 -2.5%p
    "S→B": -4.5,
    "S→C": -7.0,
    "A→S": +2.5,
    "A→B": -1.5,
    "A→C": -3.5,
    "B→S": +4.5,
    "B→A": +1.5,
    "B→C": -1.5,
    "C→S": +7.0,
    "C→A": +3.5,
    "C→B": +1.5,
}
PR_SENSITIVITY_VCT = {
    "S→A": -5.0,
    "S→B": -10.0,
    "S→C": -18.0,
    "A→S": +5.0,
    "A→B": -3.0,
    "A→C": -8.0,
    "B→S": +10.0,
    "B→A": +3.0,
    "B→C": -3.0,
    "C→S": +18.0,
    "C→A": +8.0,
    "C→B": +3.0,
}

# 연속 변화는 중간 경로 합산
TIER_ORDER = {"S": 4, "A": 3, "B": 2, "C": 1}
TIER_NAME  = {4: "S", 3: "A", 2: "B", 1: "C"}

def tier_delta_to_pr(from_tier: str, to_tier: str) -> tuple:
    """두 등급 간 픽률 변화 추정 (랭크, VCT)"""
    f = TIER_ORDER[from_tier]
    t = TIER_ORDER[to_tier]
    total_rank = 0.0
    total_vct  = 0.0
    step = 1 if t > f else -1
    curr = f
    while curr != t:
        nxt = curr + step
        key = f"{TIER_NAME[curr]}→{TIER_NAME[nxt]}"
        total_rank += PR_SENSITIVITY_RANK.get(key, 0.0)
        total_vct  += PR_SENSITIVITY_VCT.get(key, 0.0)
        curr = nxt
    return total_rank, total_vct


# ─── 메타 임계값 ─────────────────────────────────────────────────────────────
META_RANK_THRESH  = 8.0   # 랭크 메타픽 기준
META_VCT_THRESH   = 15.0  # VCT 메타픽 기준
VIABLE_RANK_THRESH = 4.0
VIABLE_VCT_THRESH  = 8.0


# ─── 핵심 시뮬레이션 함수 ─────────────────────────────────────────────────────

def simulate(
    agent: str,
    skill_key: str,
    new_tier: str,
    current_rank_pr: float,
    current_vct_pr: float,
    verbose: bool = True,
) -> dict:
    """
    agent        : 요원 영문명 (예: "Gekko")
    skill_key    : "Q" | "E" | "C" | "X"
    new_tier     : "S" | "A" | "B" | "C"
    current_rank_pr : 현재 랭크 픽률 (%)
    current_vct_pr  : 현재 VCT 픽률 (%)
    """
    kit = AGENT_KIT.get(agent, _DEFAULT_KIT)
    if skill_key not in kit:
        raise ValueError(f"스킬 {skill_key}를 찾을 수 없습니다.")

    old_info  = kit[skill_key]
    old_tier  = old_info["tier"]
    skill_type= old_info["type"]

    if old_tier == new_tier:
        return {
            "agent": agent, "skill": skill_key,
            "old_tier": old_tier, "new_tier": new_tier,
            "rank_delta": 0.0, "vct_delta": 0.0,
            "new_rank_pr": current_rank_pr,
            "new_vct_pr": current_vct_pr,
            "meta_rank": current_rank_pr >= META_RANK_THRESH,
            "meta_vct": current_vct_pr >= META_VCT_THRESH,
            "change_type": "none",
            "notes": ["변경 없음 (동일 등급)"],
        }

    # 픽률 변화 계산
    rank_delta, vct_delta = tier_delta_to_pr(old_tier, new_tier)

    # 대체 가능성 보정: 대체 가능성 높은 요원은 버프 효과가 상대적으로 작음
    design = AGENT_DESIGN.get(agent, _DEFAULT_DESIGN)
    repl = design.get("replaceability", 0.5)
    if TIER_ORDER[new_tier] > TIER_ORDER[old_tier]:  # 버프
        # 대체 가능성 높을수록 버프 효과 감쇄 (경쟁 요원이 많음)
        rank_delta *= (1.0 - repl * 0.3)
        vct_delta  *= (1.0 - repl * 0.5)
    else:  # 너프
        # 대체 가능성 낮을수록 너프 효과 감쇄 (고유 역할로 여전히 기용)
        rank_delta *= (1.0 + (1.0 - repl) * 0.2)
        vct_delta  *= (1.0 + (1.0 - repl) * 0.3)

    # 팀 시너지 보정: 팀 조율 필수 요원은 VCT 민감도 더 높음
    team_syn = design.get("team_synergy", 0.5)
    vct_delta *= (1.0 + team_syn * 0.4)

    # 새 픽률 계산
    new_rank_pr = max(0.0, current_rank_pr + rank_delta)
    new_vct_pr  = max(0.0, current_vct_pr  + vct_delta)

    # 새 킷 점수 계산
    old_kit_score = compute_kit_score(agent)
    # 변경된 스킬의 기여분 교체
    n_skills = len(kit)
    old_contrib = SKILL_TIER_SCORE.get(old_tier, 2)
    new_contrib = SKILL_TIER_SCORE.get(new_tier, 2)
    new_kit_score = old_kit_score + (new_contrib - old_contrib) / n_skills

    # 변화 방향
    change_type = "buff" if TIER_ORDER[new_tier] > TIER_ORDER[old_tier] else "nerf"

    # 분석 노트
    notes = []

    # S급 획득/손실 분석
    if new_tier == "S" and old_tier != "S":
        type_ko = {
            "smoke": "연막(S급)", "cc": "CC(S급)",
            "info": "정보획득(S급)", "mobility": "이동기(S급)"
        }.get(skill_type, f"{skill_type}(S급)")
        notes.append(f"★ {type_ko} 획득 → 메타 핵심 유틸 추가")
    elif old_tier == "S" and new_tier != "S":
        notes.append(f"▼ S급 유틸({skill_type}) 손실 → 킷 가치 급감")

    # 메타 임계값 평가
    was_meta_rank = current_rank_pr >= META_RANK_THRESH
    was_meta_vct  = current_vct_pr  >= META_VCT_THRESH
    now_meta_rank = new_rank_pr >= META_RANK_THRESH
    now_meta_vct  = new_vct_pr  >= META_VCT_THRESH

    if not was_meta_rank and now_meta_rank:
        notes.append(f"→ 랭크 메타픽 진입 예상 ({current_rank_pr:.1f}% → {new_rank_pr:.1f}%)")
    elif was_meta_rank and not now_meta_rank:
        notes.append(f"→ 랭크 메타픽 이탈 예상 ({current_rank_pr:.1f}% → {new_rank_pr:.1f}%)")

    if not was_meta_vct and now_meta_vct:
        notes.append(f"→ VCT 메타픽 진입 예상 ({current_vct_pr:.1f}% → {new_vct_pr:.1f}%)")
    elif was_meta_vct and not now_meta_vct:
        notes.append(f"→ VCT 메타픽 이탈 예상 ({current_vct_pr:.1f}% → {new_vct_pr:.1f}%)")

    # 경쟁 요원 영향 분석
    competitors = []
    for other_agent, rel in AGENT_RELATIONS.items():
        for sup in rel.get("suppressed_by", []):
            if sup["agent"] == agent and sup["type"] in ("replaces", "competes"):
                competitors.append((other_agent, sup["reason"]))

    if competitors and change_type == "nerf":
        for comp, reason in competitors[:2]:
            notes.append(f"↑ {comp} 반사이익 예상: {reason[:40]}...")

    # 구조적 한계 경고
    if change_type == "buff" and new_kit_score < 2.3:
        notes.append("⚠ 킷 전체 가치가 낮아 단일 스킬 버프만으로 메타 진입 어려울 수 있음")

    if verbose:
        _print_simulation(
            agent, skill_key, old_tier, new_tier, skill_type,
            old_kit_score, new_kit_score,
            current_rank_pr, new_rank_pr, rank_delta,
            current_vct_pr, new_vct_pr, vct_delta,
            notes, design,
        )

    return {
        "agent": agent, "skill": skill_key,
        "old_tier": old_tier, "new_tier": new_tier,
        "old_kit_score": round(old_kit_score, 3),
        "new_kit_score": round(new_kit_score, 3),
        "rank_delta": round(rank_delta, 2),
        "vct_delta": round(vct_delta, 2),
        "new_rank_pr": round(new_rank_pr, 2),
        "new_vct_pr": round(new_vct_pr, 2),
        "meta_rank": now_meta_rank,
        "meta_vct": now_meta_vct,
        "viable_rank": new_rank_pr >= VIABLE_RANK_THRESH,
        "viable_vct": new_vct_pr >= VIABLE_VCT_THRESH,
        "change_type": change_type,
        "notes": notes,
    }


def _print_simulation(
    agent, skill_key, old_tier, new_tier, skill_type,
    old_kit_score, new_kit_score,
    cur_rank, new_rank, rank_delta,
    cur_vct, new_vct, vct_delta,
    notes, design,
):
    arrow = "▲" if TIER_ORDER[new_tier] > TIER_ORDER[old_tier] else "▼"
    change_ko = "버프" if arrow == "▲" else "너프"
    print()
    print("=" * 65)
    print(f"  스킬 변경 시뮬레이션 — {agent}  [{skill_key}] {old_tier}급 → {new_tier}급 {arrow}{change_ko}")
    print("=" * 65)
    print(f"  스킬 유형  : {skill_type}")
    print(f"  킷 가치    : {old_kit_score:.3f}  →  {new_kit_score:.3f}  (변화 {new_kit_score-old_kit_score:+.3f})")
    print(f"  요원 정체성: {design.get('role_niche','?')}  |  팀시너지 {design.get('team_synergy',0.5):.1f}  |  대체가능성 {design.get('replaceability',0.5):.1f}")
    print()
    print("  ─── 예상 픽률 변화 ───────────────────────────────────────────")
    r_sign = "+" if rank_delta >= 0 else ""
    v_sign = "+" if vct_delta  >= 0 else ""
    print(f"  랭크 픽률  : {cur_rank:.1f}%  →  {new_rank:.1f}%  ({r_sign}{rank_delta:.1f}%p)")
    print(f"  VCT  픽률  : {cur_vct:.1f}%  →  {new_vct:.1f}%  ({v_sign}{vct_delta:.1f}%p)")
    print()

    # 메타 상태 표시
    print("  ─── 메타 진입 평가 ──────────────────────────────────────────")
    rank_status = _meta_bar(new_rank, META_RANK_THRESH, VIABLE_RANK_THRESH)
    vct_status  = _meta_bar(new_vct,  META_VCT_THRESH,  VIABLE_VCT_THRESH)
    print(f"  랭크  {rank_status}")
    print(f"  VCT   {vct_status}")
    print()

    if notes:
        print("  ─── 분석 ────────────────────────────────────────────────────")
        for n in notes:
            print(f"  • {n}")
        print()
    print("=" * 65)


def _meta_bar(pr: float, meta_thresh: float, viable_thresh: float) -> str:
    """픽률을 시각적 상태 바로 표현"""
    if pr >= meta_thresh:
        status = "🔥 메타픽"
    elif pr >= viable_thresh:
        status = "✅ 활용 가능"
    elif pr >= 1.5:
        status = "⚠ 저픽"
    else:
        status = "❌ 거의 미사용"
    bar_len = min(int(pr / meta_thresh * 20), 20)
    bar = "█" * bar_len + "░" * (20 - bar_len)
    return f"[{bar}] {pr:5.1f}%  {status}  (메타 기준: {meta_thresh:.0f}%)"


# ─── 다중 시나리오 비교 ────────────────────────────────────────────────────────

def compare_scenarios(agent: str, current_rank_pr: float, current_vct_pr: float):
    """모든 스킬 × 모든 가능한 등급 변경을 스캔해 가장 효과적인 변경 찾기"""
    kit = AGENT_KIT.get(agent, _DEFAULT_KIT)
    tiers = ["S", "A", "B", "C"]

    results = []
    for skill_key, info in kit.items():
        old_tier = info["tier"]
        for new_tier in tiers:
            if new_tier == old_tier:
                continue
            r = simulate(agent, skill_key, new_tier, current_rank_pr, current_vct_pr, verbose=False)
            results.append(r)

    # 버프 효과 상위 5개
    buffs = sorted([r for r in results if r["change_type"] == "buff"],
                   key=lambda x: x["rank_delta"] + x["vct_delta"], reverse=True)
    nerfs = sorted([r for r in results if r["change_type"] == "nerf"],
                   key=lambda x: x["rank_delta"] + x["vct_delta"])

    print()
    print("=" * 65)
    print(f"  {agent} 스킬 변경 시나리오 전체 스캔")
    print("=" * 65)
    print(f"\n  현재 픽률: 랭크 {current_rank_pr:.1f}% / VCT {current_vct_pr:.1f}%")
    print()
    print("  ─── 버프 효과 Top 5 ─────────────────────────────────────────")
    for r in buffs[:5]:
        meta_r = "🔥메타" if r["meta_rank"] else ("✅가능" if r["viable_rank"] else "⚠저픽")
        meta_v = "🔥메타" if r["meta_vct"]  else ("✅가능" if r["viable_vct"]  else "⚠저픽")
        print(f"  [{r['skill']}] {r['old_tier']}→{r['new_tier']}  "
              f"랭크{r['rank_delta']:+.1f}%→{r['new_rank_pr']:.1f}%({meta_r})  "
              f"VCT{r['vct_delta']:+.1f}%→{r['new_vct_pr']:.1f}%({meta_v})")

    print()
    print("  ─── 너프 효과 Top 5 (픽률 감소) ────────────────────────────")
    for r in nerfs[:5]:
        print(f"  [{r['skill']}] {r['old_tier']}→{r['new_tier']}  "
              f"랭크{r['rank_delta']:+.1f}%→{r['new_rank_pr']:.1f}%  "
              f"VCT{r['vct_delta']:+.1f}%→{r['new_vct_pr']:.1f}%")
    print("=" * 65)


# ─── 수치 기반 시뮬레이션 (Phase 1+2 연동) ───────────────────────────────────

def _infer_direction(stat_name: str, old_val: float, new_val: float) -> str:
    """스탯 이름과 변화 방향으로 buff/nerf 판단"""
    sl = stat_name.lower()
    lower_is_buff = any(kw in sl for kw in _LOWER_IS_BUFF)
    if lower_is_buff:
        return "buff" if new_val < old_val else "nerf"
    return "buff" if new_val > old_val else "nerf"


def _mag_bin(magnitude: float) -> str:
    if magnitude < 0.3:
        return "small"
    if magnitude < 1.0:
        return "medium"
    return "large"


def _lookup_impact(direction: str, magnitude: float, has_identity: bool) -> tuple[dict, str]:
    """impact_lookup.json에서 예측 구간 조회"""
    if not IMPACT_LOOKUP:
        return {}, "N/A"
    mbin = _mag_bin(magnitude)
    key = f"{direction}_id{int(has_identity)}_{mbin}"
    if key in IMPACT_LOOKUP:
        return IMPACT_LOOKUP[key], mbin
    for id_val in (0, 1):
        k2 = f"{direction}_id{id_val}_{mbin}"
        if k2 in IMPACT_LOOKUP:
            return IMPACT_LOOKUP[k2], mbin
    fb = IMPACT_LOOKUP.get(f"_fallback_{direction}", IMPACT_LOOKUP.get("_overall", {}))
    return fb, mbin


def _find_stat(agent: str, slot: str, query: str) -> tuple[str, float, str] | None:
    """
    agent_skills.json에서 쿼리와 가장 가까운 스탯 반환
    returns (stat_name, current_value, unit) or None
    """
    abi = AGENT_SKILLS.get(agent, {}).get(slot)
    if not abi:
        return None
    stats = abi.get("stats", {})
    q = query.lower().replace("_", " ").replace("-", " ")

    # 완전 일치 우선
    for name, info in stats.items():
        if name.lower() == q:
            return name, info["value"], info.get("unit", "")

    # 부분 일치 (쿼리가 스탯명에 포함)
    matches = [(name, info) for name, info in stats.items() if q in name.lower()]
    if len(matches) == 1:
        name, info = matches[0]
        return name, info["value"], info.get("unit", "")
    if len(matches) > 1:
        # 복수 매칭 시 사용자에게 알림 후 첫 번째 반환
        print(f"  [알림] '{query}' 와 일치하는 스탯이 {len(matches)}개입니다:")
        for mn, mi in matches:
            print(f"    - {mn}: {mi['value']} {mi.get('unit','')}")
        print(f"  → '{matches[0][0]}' 를 사용합니다. 더 구체적인 이름으로 재시도 가능.")
        name, info = matches[0]
        return name, info["value"], info.get("unit", "")

    # 역방향: 스탯명이 쿼리에 포함
    for name, info in stats.items():
        if name.lower() in q:
            return name, info["value"], info.get("unit", "")

    return None


def show_skill_stats(agent: str, slot: str | None = None):
    """요원 스킬 현재 수치 표시"""
    if agent not in AGENT_SKILLS:
        print(f"  [{agent}] agent_skills.json에 없음")
        return
    slots = [slot] if slot else ["C", "Q", "E", "X"]
    for s in slots:
        abi = AGENT_SKILLS[agent].get(s)
        if not abi:
            continue
        name = abi.get("name", s)
        creds = abi.get("creds")
        charges = abi.get("charges")
        func = abi.get("function", "")
        cost_str = f"  비용:{creds}c" if creds else "  (무료)"
        chg_str  = f"  충전:{charges}" if charges else ""
        print(f"\n  [{s}] {name}  {func}{cost_str}{chg_str}")
        for stat_name, info in abi.get("stats", {}).items():
            v = info.get("value")
            u = info.get("unit", "")
            if v is not None:
                print(f"      {stat_name:<30} {v} {u}")


def simulate_numeric(
    agent: str,
    slot: str,
    stat_query: str,
    new_val: float,
    current_rank_pr: float,
    current_vct_pr: float  = 0.0,
    verbose: bool          = True,
) -> dict | None:
    """
    수치 스탯 변경 시뮬레이션
    agent     : 영문 요원명
    slot      : C/Q/E/X
    stat_query: 스탯 이름 (부분 일치 허용, e.g. "duration", "windup")
    new_val   : 변경 후 수치
    """
    found = _find_stat(agent, slot, stat_query)
    if not found:
        if verbose:
            print(f"  [오류] '{agent} {slot}'에서 스탯 '{stat_query}'를 찾지 못했습니다.")
            print("  현재 스탯 목록:")
            show_skill_stats(agent, slot)
        return None

    stat_name, old_val, unit = found
    if old_val is None or old_val == 0:
        if verbose:
            print(f"  [오류] 현재 {stat_name} 수치가 0 또는 없음 → magnitude 계산 불가")
        return None

    direction = _infer_direction(stat_name, old_val, new_val)
    magnitude = abs(new_val - old_val) / abs(old_val)
    has_identity = slot in ("E", "X")

    est, mbin = _lookup_impact(direction, magnitude, has_identity)
    pr_est  = est.get("pr", {})
    wr_est  = est.get("wr", {})

    new_rank_pr = max(0.0, current_rank_pr + (pr_est.get("median", 0.0)))
    new_vct_pr  = max(0.0, current_vct_pr  + (wr_est.get("median", 0.0)))

    result = {
        "agent": agent, "slot": slot, "stat": stat_name,
        "old_val": old_val, "new_val": new_val, "unit": unit,
        "direction": direction,
        "magnitude": round(magnitude, 4),
        "mag_bin": mbin,
        "pr_median": pr_est.get("median", 0.0),
        "pr_p25":    pr_est.get("p25", 0.0),
        "pr_p75":    pr_est.get("p75", 0.0),
        "pr_p10":    pr_est.get("p10", 0.0),
        "pr_p90":    pr_est.get("p90", 0.0),
        "wr_median": wr_est.get("median", 0.0),
        "new_rank_pr": round(new_rank_pr, 2),
        "new_vct_pr":  round(new_vct_pr,  2),
        "n_samples":   pr_est.get("n", 0),
    }

    if verbose:
        _print_numeric_sim(result, current_rank_pr, current_vct_pr)
    return result


def _print_numeric_sim(r: dict, cur_rank: float, cur_vct: float):
    arrow  = "▲" if r["direction"] == "buff" else "▼"
    pct    = r["magnitude"] * 100
    d_sign = "+" if r["pr_median"] >= 0 else ""
    print()
    print("=" * 65)
    print(f"  수치 변경 시뮬레이션 — {r['agent']}  [{r['slot']}]  {arrow}{r['direction'].upper()}")
    print("=" * 65)
    print(f"  스탯     : {r['stat']}")
    print(f"  변경     : {r['old_val']} {r['unit']}  →  {r['new_val']} {r['unit']}")
    print(f"  크기     : {pct:.1f}%  ({r['mag_bin']})  [n={r['n_samples']}]")
    print()
    print("  ─── 예상 픽률 변화 ─────────────────────────────────────────────")
    print(f"  랭크 픽률  : {cur_rank:.1f}%  →  {r['new_rank_pr']:.1f}%  "
          f"({d_sign}{r['pr_median']:.2f}%p  IQR [{r['pr_p25']:+.2f}~{r['pr_p75']:+.2f}])")
    print(f"  VCT  픽률  : {cur_vct:.1f}%  →  {r['new_vct_pr']:.1f}%  "
          f"(Δ{r['wr_median']:+.2f}%p)")
    print()
    print(f"  ⚠  불확실성 구간 (p10~p90): [{r['pr_p10']:+.2f}~{r['pr_p90']:+.2f}]%p")
    print(f"  ⚠  데이터({r['n_samples']}건) 기반 중앙값 — 실제와 ±2%p 이상 차이 가능")
    print("=" * 65)


# ─── 대화형 모드 ─────────────────────────────────────────────────────────────

def _resolve_agent(agent_input: str) -> str | None:
    agent = KO_TO_EN.get(agent_input, agent_input)
    all_agents = set(AGENT_KIT.keys()) | set(AGENT_SKILLS.keys())
    if agent in all_agents:
        return agent
    matched = [k for k in all_agents if agent_input.lower() in k.lower()]
    if matched:
        print(f"  [자동 매칭] '{agent_input}' → '{matched[0]}'")
        return matched[0]
    print(f"  [오류] 요원을 찾을 수 없습니다: {agent_input}")
    return None


def interactive_mode():
    print()
    print("=" * 65)
    print("  Valorant 스킬 변경 시뮬레이터  (종료: q)")
    print("=" * 65)
    print("  [티어 모드]  <요원> <슬롯> <새등급S/A/B/C> <랭크픽%> [VCT픽%]")
    print("    예)  게코 C A 2.1 3.5")
    print()
    print("  [수치 모드]  <요원> <슬롯> <스탯명> <새수치> <랭크픽%> [VCT픽%]")
    print("    예)  제트 E duration 5.0 55.0 80.0")
    print("    예)  킬조이 E radius 10 4.2 6.0")
    print()
    print("  [기타]  stats <요원> [슬롯]   — 현재 스탯 조회")
    print("          scan  <요원> <랭크픽%> [VCT픽%]  — 전체 시나리오 스캔")
    print("-" * 65)

    while True:
        try:
            user_input = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in ("q", "quit", "exit"):
            break

        parts = user_input.split()

        # stats 명령
        if parts[0].lower() == "stats":
            agent_in = parts[1] if len(parts) > 1 else ""
            slot_in  = parts[2].upper() if len(parts) > 2 else None
            agent = _resolve_agent(agent_in)
            if agent:
                show_skill_stats(agent, slot_in)
            continue

        if len(parts) < 4:
            print("  [오류] 인자가 부족합니다. 도움말을 확인하세요.")
            continue

        agent = _resolve_agent(parts[0])
        if not agent:
            continue

        slot = parts[1].upper()
        if slot not in SKILL_KEYS:
            print(f"  [오류] 슬롯은 Q/E/C/X 여야 합니다: {slot}")
            continue

        # scan 모드
        if slot == "SCAN" or parts[1].lower() == "scan":
            try:
                cur_rank = float(parts[2])
                cur_vct  = float(parts[3]) if len(parts) > 3 else 0.0
            except ValueError:
                print("  [오류] 픽률은 숫자로 입력하세요.")
                continue
            compare_scenarios(agent, cur_rank, cur_vct)
            continue

        third = parts[2]

        # 수치 모드: 세 번째 인자가 S/A/B/C가 아니고 숫자도 아닌 경우 → 스탯명
        if third.upper() not in ("S", "A", "B", "C"):
            # <요원> <슬롯> <스탯명> <새수치> <랭크픽%> [VCT픽%]
            stat_query = third
            if len(parts) < 5:
                print("  [오류] 수치 모드: <요원> <슬롯> <스탯명> <새수치> <랭크픽%>")
                continue
            try:
                new_val  = float(parts[3])
                cur_rank = float(parts[4])
                cur_vct  = float(parts[5]) if len(parts) > 5 else 0.0
            except ValueError:
                print("  [오류] 수치와 픽률은 숫자로 입력하세요.")
                continue
            try:
                simulate_numeric(agent, slot, stat_query, new_val, cur_rank, cur_vct)
            except Exception as e:
                print(f"  [오류] 수치 시뮬레이션 실패: {e}")
        else:
            # 티어 모드: <요원> <슬롯> <새등급> <랭크픽%> [VCT픽%]
            new_tier = third.upper()
            try:
                cur_rank = float(parts[3])
                cur_vct  = float(parts[4]) if len(parts) > 4 else 0.0
            except ValueError:
                print("  [오류] 픽률은 숫자로 입력하세요.")
                continue
            if agent not in AGENT_KIT:
                print(f"  [오류] 티어 모드: '{agent}'의 AGENT_KIT 데이터 없음. 수치 모드를 사용하세요.")
                continue
            try:
                simulate(agent, slot, new_tier, cur_rank, cur_vct, verbose=True)
            except Exception as e:
                print(f"  [오류] 시뮬레이션 실패: {e}")


# ─── CLI 진입점 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Valorant 스킬 변경 시뮬레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시 (티어 모드):
  python skill_simulator.py --agent 게코 --skill C --new-tier A --rank-pr 2.1 --vct-pr 3.5
  python skill_simulator.py --agent 게코 --scan --rank-pr 2.1 --vct-pr 3.5

예시 (수치 모드):
  python skill_simulator.py --agent 제트 --skill E --stat duration --new-val 5.0 --rank-pr 55.0 --vct-pr 80.0
  python skill_simulator.py --agent 킬조이 --skill E --stat radius --new-val 10.0 --rank-pr 4.2

예시 (스탯 조회):
  python skill_simulator.py --stats --agent 제트 --skill E
        """
    )
    parser.add_argument("--agent",    type=str, help="요원 이름 (한국어 또는 영문)")
    parser.add_argument("--skill",    type=str, choices=["Q","E","C","X"], help="스킬 키")
    parser.add_argument("--new-tier", type=str, choices=["S","A","B","C"], help="변경 후 등급 (티어 모드)")
    parser.add_argument("--stat",     type=str, help="스탯 이름 (수치 모드)")
    parser.add_argument("--new-val",  type=float, help="변경 후 수치 (수치 모드)")
    parser.add_argument("--rank-pr",  type=float, default=0.0, help="현재 랭크 픽률 (%)")
    parser.add_argument("--vct-pr",   type=float, default=0.0, help="현재 VCT 픽률 (%)")
    parser.add_argument("--scan",     action="store_true", help="모든 변경 시나리오 스캔 (티어 모드)")
    parser.add_argument("--stats",    action="store_true", help="현재 스킬 스탯 조회")

    args = parser.parse_args()

    if not args.agent:
        interactive_mode()
        return

    agent = _resolve_agent(args.agent)
    if not agent:
        sys.exit(1)

    # 스탯 조회
    if args.stats:
        print(f"\n[{agent}] 현재 스킬 스탯")
        show_skill_stats(agent, args.skill)
        return

    # 수치 모드
    if args.stat and args.new_val is not None:
        if not args.skill:
            print("[오류] --skill Q/E/C/X 를 지정하세요.")
            sys.exit(1)
        simulate_numeric(agent, args.skill, args.stat, args.new_val,
                         args.rank_pr, args.vct_pr, verbose=True)
        return

    # 티어 모드
    if agent not in AGENT_KIT:
        print(f"[오류] 티어 모드: '{agent}' AGENT_KIT 없음. --stat/--new-val 로 수치 모드 사용.")
        sys.exit(1)

    if args.scan:
        compare_scenarios(agent, args.rank_pr, args.vct_pr)
    elif args.skill and args.new_tier:
        simulate(agent, args.skill, args.new_tier, args.rank_pr, args.vct_pr, verbose=True)
    else:
        print("[오류] --scan 또는 --skill + --new-tier 또는 --stat + --new-val 을 지정하세요.")
        parser.print_help()


if __name__ == "__main__":
    main()
