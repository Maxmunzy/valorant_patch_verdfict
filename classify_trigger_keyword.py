"""
키워드 기반 trigger_type 자동 분류
Claude API 없이 change_reason + description 텍스트 분석으로 분류

trigger_type:
  pro_dominance  — VCT/프로씬 지배형
  role_invasion  — 포지션 잠식형
  skill_ceiling  — 숙련도 천장형
  map_anchor     — 맵 고착형
  rank_stat      — 픽률/승률 초과형 (기본값)

실행: python classify_trigger_keyword.py
출력: patch_notes_classified.csv
"""

import re
import pandas as pd

IN_CSV  = "patch_notes_raw.csv"
OUT_CSV = "patch_notes_classified.csv"

# ─── 키워드 규칙 (우선순위 순) ────────────────────────────────────────────────

RULES = [
    # pro_dominance: 프로씬/VCT 언급
    ("pro_dominance", [
        "pro play", "pro scene", "professional", "vct", "esport",
        "competitive scene", "high level play", "top level",
        "tournament", "masters", "champions", "international",
        "pro player", "pro team",
    ]),
    # role_invasion: 포지션 잠식
    ("role_invasion", [
        "bleed into", "other role", "other agent", "crowding out",
        "initiator", "sentinel", "controller", "duelist",
        "outperform", "replacing", "comp diversity", "pick diversity",
        "other classes", "taking over", "encroaching",
        "role of", "job of", "designed for",
    ]),
    # skill_ceiling: 고숙련자 집중
    ("skill_ceiling", [
        "high skill", "skilled player", "skill ceiling", "skill floor",
        "high rank", "higher rank", "top rank", "radiant",
        "immortal player", "experienced", "mastery",
        "outperform", "performance gap", "top player",
        "skilled hand", "in the right hands",
    ]),
    # map_anchor: 맵 의존
    ("map_anchor", [
        "specific map", "certain map", "map dependent", "map pool",
        "bind", "haven", "breeze", "split", "ascent", "icebox",
        "lotus", "pearl", "abyss", "fracture", "sunset",
        "map anchor", "map lock", "map-specific",
    ]),
    # rank_stat: 수치 초과 (기본)
    ("rank_stat", [
        "win rate", "pick rate", "win ratio", "too high",
        "overperform", "above average", "dominant in ranked",
        "ranked", "across the board", "consistently strong",
        "strong in", "too strong", "too powerful", "overpowered",
    ]),
]


def classify_text(text: str) -> tuple[str, float]:
    """텍스트에서 trigger_type과 신뢰도 반환"""
    if not isinstance(text, str) or not text.strip():
        return "rank_stat", 0.0

    text_lower = text.lower()
    scores = {}

    for trigger, keywords in RULES:
        matched = [kw for kw in keywords if kw in text_lower]
        if matched:
            scores[trigger] = len(matched)

    if not scores:
        return "rank_stat", 0.3

    # 최고 점수 trigger 선택
    best = max(scores, key=scores.get)
    confidence = min(scores[best] / 3, 1.0)  # 3개 이상 매칭이면 high

    # 복수 trigger (점수 차이 1 이하)
    sorted_scores = sorted(scores.items(), key=lambda x: -x[1])
    if len(sorted_scores) > 1 and sorted_scores[0][1] - sorted_scores[1][1] <= 1:
        combined = f"{sorted_scores[0][0]},{sorted_scores[1][0]}"
        return combined, confidence

    return best, confidence


def classify_group(group: pd.DataFrame) -> tuple[str, float]:
    """에이전트×패치 그룹 전체 텍스트 합산 분류"""
    combined_text = " ".join([
        str(group["change_reason"].fillna("").str.cat(sep=" ")),
        str(group["description"].fillna("").str.cat(sep=" ")),
    ])
    return classify_text(combined_text)


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(IN_CSV)
    target = df[df["direction"].isin(["nerf", "buff"])].copy()
    print(f"분류 대상: {len(target)}행 (nerf/buff) / 전체 {len(df)}행\n")

    groups = list(target.groupby(["agent", "patch"]))
    print(f"에이전트×패치 그룹: {len(groups)}개\n")

    results = {}  # (agent, patch) -> (trigger_type, confidence)

    for (agent, patch), group in groups:
        trigger, conf = classify_group(group)
        conf_label = "high" if conf >= 0.7 else "medium" if conf >= 0.4 else "low"
        results[(agent, patch)] = (trigger, conf_label)
        print(f"  {str(patch):<6} / {agent:<12} -> {trigger:<35} ({conf_label})")

    # 결과를 원본 df에 반영
    for (agent, patch), (trigger, conf_label) in results.items():
        mask = (
            (df["agent"] == agent) &
            (df["patch"].astype(str) == str(patch)) &
            (df["direction"].isin(["nerf", "buff"]))
        )
        df.loc[mask, "trigger_type"]        = trigger
        df.loc[mask, "claude_confidence"]   = conf_label

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장: {OUT_CSV}  ({len(df)}행)")

    print("\n[trigger_type 분포]")
    classified = df[df["trigger_type"].notna() & (df["trigger_type"] != "")]
    if not classified.empty:
        # 복수 trigger 분리해서 집계
        exploded = classified["trigger_type"].str.split(",").explode()
        print(exploded.value_counts().to_string())

    print("\n[신뢰도 낮은 항목 (수동 검토 필요)]")
    low = df[df.get("claude_confidence", pd.Series()) == "low"]
    if not low.empty:
        print(low[["patch", "agent", "trigger_type", "description"]].drop_duplicates(
            subset=["patch", "agent"]
        ).to_string(index=False))
    else:
        print("  없음")


if __name__ == "__main__":
    main()
