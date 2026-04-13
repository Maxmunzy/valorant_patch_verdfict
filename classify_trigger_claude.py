"""
Claude API 기반 trigger_type 분류기

trigger_type:
  pro_dominance  - VCT/프로씬 지배로 인한 패치
  role_invasion  - 다른 포지션 잠식으로 인한 패치
  skill_ceiling  - 고숙련자 집중 문제로 인한 패치
  map_anchor     - 특정 맵 고착으로 인한 패치
  rank_stat      - 픽률/승률 수치 초과로 인한 패치

실행: python classify_trigger_claude.py
출력: patch_notes_classified.csv
"""

import os
import time
import pandas as pd
import anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

IN_CSV  = "patch_notes_raw.csv"
OUT_CSV = "patch_notes_classified.csv"

SYSTEM_PROMPT = """You are a Valorant balance analyst. Your job is to classify WHY Riot Games made a nerf or buff to an agent.

Classify into exactly ONE of these trigger types:

- pro_dominance: The patch was triggered by the agent dominating VCT/pro play, tournament pick rates, or professional competitive scenes.
- role_invasion: The agent was crowding out or replacing other agents in their role, reducing comp diversity.
- skill_ceiling: High-skill / high-rank players were getting outsized value that lower ranks couldn't counter.
- map_anchor: The agent was overpowered on specific maps or locked to certain maps.
- rank_stat: General ranked pick rate or win rate was too high/low across the board.

Rules:
- Return ONLY the trigger type label, nothing else.
- If multiple apply, pick the PRIMARY reason based on the patch notes.
- If no reason text is given, return rank_stat as default."""

def classify_one(client: anthropic.Anthropic, agent: str, patch: str,
                 change_reason: str, description: str) -> tuple[str, str]:
    """단일 에이전트x패치 그룹 분류"""
    user_msg = f"""Agent: {agent}
Patch: {patch}
Change Reason: {change_reason or '(none provided)'}
Description: {description or '(none provided)'}

What is the trigger_type?"""

    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        label = r.content[0].text.strip().lower()
        valid = {"pro_dominance", "role_invasion", "skill_ceiling", "map_anchor", "rank_stat"}
        if label not in valid:
            # 응답이 문장인 경우 첫 단어로 매칭 시도
            for v in valid:
                if v in label:
                    return v, "high"
            return "rank_stat", "low"
        return label, "high"
    except Exception as e:
        print(f"    API 오류: {e}")
        return "rank_stat", "low"


def main():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError(".env 파일에 ANTHROPIC_API_KEY가 없습니다.")

    client = anthropic.Anthropic(api_key=key)

    df = pd.read_csv(IN_CSV)
    target = df[df["direction"].isin(["nerf", "buff"])].copy()
    print(f"분류 대상: {len(target)}행 / 전체 {len(df)}행")

    # 에이전트x패치 단위로 텍스트 합산
    groups = (
        target.groupby(["agent", "patch"])
        .agg(
            change_reason=("change_reason", lambda x: " | ".join(x.dropna().unique())),
            description=("description", lambda x: " | ".join(x.dropna().unique())),
        )
        .reset_index()
    )
    print(f"에이전트x패치 그룹: {len(groups)}개\n")

    results = {}

    for _, row in groups.iterrows():
        agent = row["agent"]
        patch = str(row["patch"])
        trigger, conf = classify_one(
            client, agent, patch,
            row["change_reason"], row["description"]
        )
        results[(agent, patch)] = (trigger, conf)
        print(f"  {patch:<6} / {agent:<14} -> {trigger:<20} ({conf})")
        time.sleep(0.3)  # rate limit 여유

    # trigger_type 컬럼이 없거나 float64이면 object로 변환 (NaN만 있을 때 dtype 문제 방지)
    if "trigger_type" not in df.columns:
        df["trigger_type"] = None
    elif df["trigger_type"].dtype != object:
        df["trigger_type"] = df["trigger_type"].astype(object)
    if "claude_confidence" not in df.columns:
        df["claude_confidence"] = None
    elif df["claude_confidence"].dtype != object:
        df["claude_confidence"] = df["claude_confidence"].astype(object)

    # 원본 df에 반영
    for (agent, patch), (trigger, conf) in results.items():
        mask = (
            (df["agent"] == agent) &
            (df["patch"].astype(str) == patch) &
            (df["direction"].isin(["nerf", "buff"]))
        )
        df.loc[mask, "trigger_type"]      = trigger
        df.loc[mask, "claude_confidence"] = conf

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장: {OUT_CSV}  ({len(df)}행)")

    print("\n[trigger_type 분포]")
    classified = df[df["trigger_type"].notna() & (df["trigger_type"] != "")]
    print(classified["trigger_type"].value_counts().to_string())


if __name__ == "__main__":
    main()
