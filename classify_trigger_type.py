"""
Claude API — 패치 노트 trigger_type 자동 분류

입력:  patch_notes_raw.csv (crawl_patch_notes.py 결과)
출력:  patch_notes_classified.csv (trigger_type, change_reason 보완)

trigger_type 분류:
  rank_stat      픽률·승률 초과형
  pro_dominance  프로씬 지배형
  role_invasion  포지션 잠식형
  map_anchor     맵 고착형
  skill_ceiling  숙련도 천장형

실행:
  python classify_trigger_type.py
  python classify_trigger_type.py --dry-run   # API 호출 없이 프롬프트만 출력
"""

import json
import argparse
import pandas as pd
import anthropic

# ─── 설정 ────────────────────────────────────────────────────────────────────

MODEL   = "claude-opus-4-6"
IN_CSV  = "patch_notes_raw.csv"
OUT_CSV = "patch_notes_classified.csv"

TRIGGER_TYPES = {
    "rank_stat":      "픽률·승률이 기준치를 초과해서 패치",
    "pro_dominance":  "VCT·프로씬에서 지배적인 픽률을 보여서 패치",
    "role_invasion":  "다른 포지션 요원의 역할까지 잠식해서 패치",
    "map_anchor":     "특정 맵에 과도하게 고착돼서 패치",
    "skill_ceiling":  "고숙련자·프로에게 퍼포먼스가 지나치게 집중돼서 패치",
}

SYSTEM_PROMPT = """당신은 Valorant 밸런스 패치를 분석하는 전문가입니다.
패치 노트의 개발자 코멘트와 변경 내용을 보고 너프/버프의 원인 유형(trigger_type)을 분류합니다.

trigger_type 정의:
  rank_stat      : 랭크 픽률·승률이 기준치를 초과해서 패치 (수치 이상형)
  pro_dominance  : VCT·프로씬에서 압도적 픽률을 보여서 패치 (프로씬 지배형)
  role_invasion  : 다른 포지션 요원의 역할까지 잠식해서 패치 (포지션 잠식형)
  map_anchor     : 특정 맵에 고착돼서 패치 (맵 고착형)
  skill_ceiling  : 고숙련자·프로에게만 퍼포먼스가 쏠려서 패치 (숙련도 천장형)

복수 해당 시 쉼표로 구분 (예: "pro_dominance,role_invasion")
근거가 명확하지 않으면 "rank_stat" (가장 일반적)으로 기본 처리.
"""


# ─── Claude API 호출 ─────────────────────────────────────────────────────────

def classify_batch(client: anthropic.Anthropic, group: pd.DataFrame) -> dict:
    """에이전트 × 패치 단위로 묶어서 한 번에 분류"""
    agent   = group["agent"].iloc[0]
    patch   = group["patch"].iloc[0]
    changes = group[["skill_key", "change_type", "description", "change_reason"]].to_dict("records")

    prompt = f"""패치 {patch} — {agent}

변경 내용:
{json.dumps(changes, ensure_ascii=False, indent=2)}

위 변경의 trigger_type을 분류하고, change_reason이 비어 있으면 패치 내용에서 유추해서 채워주세요.

JSON 형식으로 응답:
{{
  "trigger_type": "...",
  "change_reason": "...",
  "confidence": "high|medium|low",
  "reasoning": "한 문장 설명"
}}"""

    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # JSON 블록 추출
        json_match = __import__("re").search(r"\{.*\}", raw, __import__("re").DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"  [!] API 오류 ({agent} {patch}): {e}")

    return {"trigger_type": "rank_stat", "change_reason": "", "confidence": "low", "reasoning": ""}


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 프롬프트만 출력")
    args = parser.parse_args()

    df = pd.read_csv(IN_CSV)
    # nerf / buff 행만 분류 (neutral, bugfix 제외)
    target = df[df["direction"].isin(["nerf", "buff"])].copy()
    print(f"분류 대상: {len(target)}행 (nerf/buff) / 전체 {len(df)}행\n")

    if args.dry_run:
        sample = target.groupby(["agent", "patch"]).first().reset_index().head(3)
        for _, row in sample.iterrows():
            print(f"[{row['patch']} / {row['agent']}]")
            print(f"  description: {row['description']}")
            print(f"  change_reason: {row['change_reason']}")
            print()
        return

    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[!] ANTHROPIC_API_KEY 환경변수가 없습니다.")
        print("    set ANTHROPIC_API_KEY=sk-ant-... 후 재실행하세요.")
        return
    client = anthropic.Anthropic(api_key=api_key)

    results = []
    groups  = list(target.groupby(["agent", "patch"]))
    print(f"에이전트×패치 그룹: {len(groups)}개\n")

    for i, ((agent, patch), group) in enumerate(groups, 1):
        print(f"[{i:3d}/{len(groups)}] {patch} / {agent}", end=" ... ", flush=True)
        result = classify_batch(client, group)
        trigger = result.get("trigger_type", "rank_stat")
        reason  = result.get("change_reason", "")
        conf    = result.get("confidence", "low")
        print(f"{trigger}  ({conf})")

        idx = group.index
        df.loc[idx, "trigger_type"]   = trigger
        df.loc[idx, "change_reason"]  = reason if reason else df.loc[idx, "change_reason"]
        df.loc[idx, "claude_confidence"] = conf

        # 10건마다 중간 저장
        if i % 10 == 0:
            df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n저장: {OUT_CSV}  ({len(df)}행)")

    print("\n[trigger_type 분포]")
    print(df[df["trigger_type"] != ""]["trigger_type"].value_counts().to_string())

    print("\n[!] 사람 검토 필요 항목 (confidence=low):")
    low = df[df.get("claude_confidence", "") == "low"]
    if not low.empty:
        print(low[["patch", "agent", "trigger_type", "description"]].to_string(index=False))
    else:
        print("  없음")


if __name__ == "__main__":
    main()
