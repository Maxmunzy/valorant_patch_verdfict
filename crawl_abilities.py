"""
요원별 스킬(ability) 사용 통계 크롤러
vstats.gg API: /statistics/{act_uuid}/ALL/ALL/abilities.json.gz

필드:
  r  : 랭크 티어 (19=Diamond)
  a  : 요원 UUID
  ab : 스킬 슬롯 (Ability1=Q, Ability2=E, Grenade=C, Ultimate=X)
  c  : 총 사용 횟수 (casts)
  k  : 직접 킬 수
  tk : 팀킬 수

출력:
  abilities_raw.csv         원본 (act × agent × ability_slot)
  abilities_by_agent_act.csv  정제본 (C/Q/E/X 컬럼으로 피벗)
"""

import time
import pandas as pd
import numpy as np
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from agent_data import VSTATS_AGENT_UUID_MAP as AGENTS, CRAWL_ACTS as ACTS, DIAMOND_R

# vstats.gg 스킬 슬롯 → C/Q/E/X 키 매핑
# 대부분 Grenade=C, Ability1=Q, Ability2=E, Ultimate=X
# 요원마다 다를 수 있으므로 나중에 valorant-api.com으로 교차검증 필요
SLOT_TO_KEY = {
    "GrenadeAbility": "C",
    "Ability1":       "Q",
    "Ability2":       "E",
    "Ultimate":       "X",
}

BASE_URL = "https://www.vstats.gg/statistics/{act_uuid}/ALL/ALL/abilities.json.gz"


def fetch_abilities(page, act_uuid):
    url = BASE_URL.format(act_uuid=act_uuid)
    try:
        result = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{url}');
                if (!resp.ok) return {{_status: resp.status}};
                const text = await resp.text();
                if (!text || text.trim() === '' || text.trim() === '[]') return [];
                return JSON.parse(text).filter(d => d.r === {DIAMOND_R});
            }}
        """)
        return result
    except Exception as e:
        return {"_error": str(e)[:80]}


def crawl():
    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        print("vstats.gg 로드...", end=" ", flush=True)
        page.goto("https://www.vstats.gg", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        print("OK\n")

        print(f"수집: {len(ACTS)}개 액트 / Diamond 티어 / ALL 맵")
        print("-" * 50)

        for i, act in enumerate(ACTS, 1):
            data = fetch_abilities(page, act["uuid"])

            if isinstance(data, dict):
                err = data.get("_error") or data.get("_status", "unknown")
                print(f"[{i:2d}/{len(ACTS)}] {act['name']:<7}  ERROR: {err}")
                time.sleep(0.3)
                continue

            if not data:
                print(f"[{i:2d}/{len(ACTS)}] {act['name']:<7}  (empty)")
                time.sleep(0.2)
                continue

            count = 0
            for entry in data:
                uuid = entry.get("a", "")
                name = AGENTS.get(uuid)
                if not name:
                    continue
                slot = entry.get("ab", "")
                rows.append({
                    "act":   act["name"],
                    "agent": name,
                    "uuid":  uuid,
                    "slot":  slot,
                    "key":   SLOT_TO_KEY.get(slot, slot),
                    "casts": entry.get("c", 0) or 0,
                })
                count += 1

            print(f"[{i:2d}/{len(ACTS)}] {act['name']:<7}  {count}행")
            time.sleep(0.3)

        browser.close()

    return pd.DataFrame(rows)


def build_agent_act_table(df):
    """
    (act, agent) 단위로 피벗
    각 스킬별 casts, kills 컬럼 생성
    + 파생 피처: kill_ratio per skill, total_ability_kills
    """
    rows = []
    for (act, agent), grp in df.groupby(["act", "agent"]):
        row = {"act": act, "agent": agent}
        total_casts = 0
        total_kills = 0

        for _, r in grp.iterrows():
            k = r["key"]
            if k == "X":
                continue  # 궁극기 제외
            row[f"casts_{k}"] = int(r["casts"])
            total_casts += int(r["casts"])

        row["total_skill_casts"] = total_casts

        # 스킬별 사용 비중 (0~1) — 어느 스킬에 의존하는지
        for k in ["C", "Q", "E"]:
            c = row.get(f"casts_{k}", 0)
            row[f"cast_share_{k}"] = round(c / total_casts, 4) if total_casts > 0 else np.nan

        rows.append(row)

    return pd.DataFrame(rows)


def main():
    print("=" * 55)
    print("요원별 스킬 사용 통계 크롤러")
    print("=" * 55 + "\n")

    df = crawl()

    if df.empty:
        print("데이터 없음")
        return

    df.to_csv("abilities_raw.csv", index=False, encoding="utf-8-sig")
    print(f"\n원본 저장: abilities_raw.csv ({len(df)}행)")

    pivot = build_agent_act_table(df)
    pivot.to_csv("abilities_by_agent_act.csv", index=False, encoding="utf-8-sig")
    print(f"피벗 저장: abilities_by_agent_act.csv ({len(pivot)}행)")

    # 샘플 확인
    print("\n[Jett 스킬 사용 추이]")
    jett = pivot[pivot["agent"] == "Jett"][
        ["act","casts_C","casts_Q","casts_E",
         "cast_share_C","cast_share_Q","cast_share_E","total_skill_casts"]
    ]
    print(jett.to_string(index=False))

    print("\n[Viper 스킬 사용 추이]")
    viper = pivot[pivot["agent"] == "Viper"][
        ["act","casts_C","casts_Q","casts_E",
         "cast_share_C","cast_share_Q","cast_share_E","total_skill_casts"]
    ]
    print(viper.to_string(index=False))


if __name__ == "__main__":
    main()
