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
import argparse
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ─── 요원 메타 데이터 임포트 ───────────────────────────────────────────────────
try:
    from build_step2_data import (
        AGENT_DESIGN, AGENT_KIT, AGENT_RELATIONS,
        SKILL_TIER_SCORE, compute_kit_score, get_kit_flags,
        _DEFAULT_DESIGN, _DEFAULT_KIT,
    )
except ImportError as e:
    print(f"[오류] build_step2_data.py 임포트 실패: {e}")
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


# ─── 대화형 모드 ─────────────────────────────────────────────────────────────

def interactive_mode():
    print()
    print("=" * 65)
    print("  Valorant 스킬 변경 시뮬레이터  (종료: q)")
    print("=" * 65)
    print("  사용법: <요원> <스킬Q/E/C/X> <새등급S/A/B/C> <현재랭크픽%> <현재VCT픽%>")
    print("  예시:   게코 C A 2.1 3.5")
    print("  스캔:   게코 scan 2.1 3.5  (모든 변경 효과 비교)")
    print("-" * 65)

    while True:
        try:
            user_input = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input or user_input.lower() in ("q", "quit", "exit"):
            break

        parts = user_input.split()
        if len(parts) < 4:
            print("  [오류] 입력 형식: <요원> <스킬> <새등급> <현재랭크픽%> [현재VCT픽%]")
            continue

        agent_input = parts[0]
        agent = KO_TO_EN.get(agent_input, agent_input)
        if agent not in AGENT_KIT and agent not in AGENT_DESIGN:
            # 퍼지 매칭 시도
            matched = [k for k in list(AGENT_KIT.keys()) + list(KO_TO_EN.values())
                       if agent_input.lower() in k.lower()]
            if matched:
                agent = matched[0]
                print(f"  [자동 매칭] '{agent_input}' → '{agent}'")
            else:
                print(f"  [오류] 요원을 찾을 수 없습니다: {agent_input}")
                print(f"  사용 가능: {', '.join(sorted(AGENT_KIT.keys()))}")
                continue

        # scan 모드
        if parts[1].lower() == "scan":
            try:
                cur_rank = float(parts[2])
                cur_vct  = float(parts[3]) if len(parts) > 3 else 0.0
            except ValueError:
                print("  [오류] 픽률은 숫자로 입력하세요.")
                continue
            compare_scenarios(agent, cur_rank, cur_vct)
            continue

        if len(parts) < 4:
            print("  [오류] 입력 형식: <요원> <스킬Q/E/C/X> <새등급S/A/B/C> <현재랭크픽%> [현재VCT픽%]")
            continue

        skill_key = parts[1].upper()
        new_tier  = parts[2].upper()
        try:
            cur_rank = float(parts[3])
            cur_vct  = float(parts[4]) if len(parts) > 4 else 0.0
        except ValueError:
            print("  [오류] 픽률은 숫자로 입력하세요.")
            continue

        if skill_key not in SKILL_KEYS:
            print(f"  [오류] 스킬은 Q/E/C/X 중 하나여야 합니다. 입력: {skill_key}")
            continue
        if new_tier not in ("S", "A", "B", "C"):
            print(f"  [오류] 등급은 S/A/B/C 중 하나여야 합니다. 입력: {new_tier}")
            continue

        try:
            simulate(agent, skill_key, new_tier, cur_rank, cur_vct, verbose=True)
        except Exception as e:
            print(f"  [오류] 시뮬레이션 실패: {e}")


# ─── CLI 진입점 ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Valorant 스킬 변경 시뮬레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python skill_simulator.py --agent 게코 --skill C --new-tier A --rank-pr 2.1 --vct-pr 3.5
  python skill_simulator.py --agent 킬조이 --skill E --new-tier S --rank-pr 4.2 --vct-pr 6.0
  python skill_simulator.py --agent 게코 --scan --rank-pr 2.1 --vct-pr 3.5
  python skill_simulator.py  (대화형 모드)
        """
    )
    parser.add_argument("--agent",    type=str, help="요원 이름 (한국어 또는 영문)")
    parser.add_argument("--skill",    type=str, choices=["Q","E","C","X"], help="스킬 키")
    parser.add_argument("--new-tier", type=str, choices=["S","A","B","C"], help="변경 후 등급")
    parser.add_argument("--rank-pr",  type=float, default=0.0, help="현재 랭크 픽률 (%)")
    parser.add_argument("--vct-pr",   type=float, default=0.0, help="현재 VCT 픽률 (%)")
    parser.add_argument("--scan",     action="store_true", help="모든 변경 시나리오 스캔")

    args = parser.parse_args()

    if not args.agent:
        # 대화형 모드
        interactive_mode()
        return

    agent = KO_TO_EN.get(args.agent, args.agent)
    if agent not in AGENT_KIT:
        print(f"[오류] 요원을 찾을 수 없습니다: {args.agent}")
        print(f"사용 가능: {', '.join(sorted(AGENT_KIT.keys()))}")
        sys.exit(1)

    if args.scan:
        compare_scenarios(agent, args.rank_pr, args.vct_pr)
    elif args.skill and args.new_tier:
        simulate(agent, args.skill, args.new_tier, args.rank_pr, args.vct_pr, verbose=True)
    else:
        print("[오류] --scan 또는 --skill + --new-tier 를 지정하세요.")
        parser.print_help()


if __name__ == "__main__":
    main()
