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

# ─── 요원 UUID → 이름 ───────────────────────────────────────
AGENTS = {
    "41fb69c1-4189-7b37-f117-bcaf1e96f1bf": "Astra",
    "5f8d3a7f-467b-97f3-062c-13acf203c006": "Breach",
    "9f0d8ba9-4140-b941-57d3-a7ad57c6b417": "Brimstone",
    "22697a3d-45bf-8dd7-4fec-84a9e28c69d7": "Chamber",
    "1dbf2edd-4729-0984-3115-daa5eed44993": "Clove",
    "117ed9e3-49f3-6512-3ccf-0cada7e3823b": "Cypher",
    "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235": "Deadlock",
    "dade69b4-4f5a-8528-247b-219e5a1facd6": "Fade",
    "e370fa57-4757-3604-3648-499e1f642d3f": "Gekko",
    "95b78ed7-4637-86d9-7e41-71ba8c293152": "Harbor",
    "efba5359-4016-a1e5-7626-b1ae76895940": "Iso",
    "add6443a-41bd-e414-f6ad-e58d267f4e95": "Jett",
    "601dbbe7-43ce-be57-2a40-4abd24953621": "Kayo",
    "1e58de9c-4950-5125-93e9-a0aee9f98746": "Killjoy",
    "bb2a4828-46eb-8cd1-e765-15848195d751": "Neon",
    "8e253930-4c05-31dd-1b6c-968525494517": "Omen",
    "eb93336a-449b-9c1b-0a54-a891f7921d69": "Phoenix",
    "f94c3b30-42be-e959-889c-5aa313dba261": "Raze",
    "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc": "Reyna",
    "569fdd95-4d10-43ab-ca70-79becc718b46": "Sage",
    "6f2a04ca-43e0-be17-7f36-b3908627744d": "Skye",
    "320b2a48-4d9b-a075-30f1-1f93a9b638fa": "Sova",
    "df1cb487-4902-002e-5c17-d28e83e78588": "Tejo",
    "707eab51-4836-f488-046a-cda6bf494859": "Viper",
    "b444168c-4e35-8076-db47-ef9bf368f384": "Vyse",
    "7c8a4701-4de6-9355-b254-e09bc2a34b72": "Waylay",
    "7f94d92c-4234-0a36-9646-3a87eb8b5c89": "Yoru",
}

ACTS = [
    {"name": "E6A3",  "uuid": "2de5423b-4aad-02ad-8d9b-c0a931958861"},
    {"name": "E7A1",  "uuid": "0981a882-4e7d-371a-70c4-c3b4f46c504a"},
    {"name": "E7A2",  "uuid": "22d10d66-4d2a-a340-6c54-408c7bd53807"},
    {"name": "E7A3",  "uuid": "4401f9fd-4170-2e4c-4bc3-f3b4d7d150d1"},
    {"name": "E8A1",  "uuid": "ec876e6c-43e8-fa63-ffc1-2e8d4db25525"},
    {"name": "E8A2",  "uuid": "4539cac3-47ae-90e5-3d01-b3812ca3274e"},
    {"name": "E8A3",  "uuid": "52ca6698-41c1-e7de-4008-8994d2221209"},
    {"name": "E9A1",  "uuid": "292f58db-4c17-89a7-b1c0-ba988f0e9d98"},
    {"name": "E9A2",  "uuid": "03dfd004-45d4-ebfd-ab0a-948ce780dac4"},
    {"name": "E9A3",  "uuid": "dcde7346-4085-de4f-c463-2489ed47983b"},
    {"name": "E10A1", "uuid": "476b0893-4c2e-abd6-c5fe-708facff0772"},
    {"name": "E10A2", "uuid": "16118998-4705-5813-86dd-0292a2439d90"},
    {"name": "E10A3", "uuid": "aef237a0-494d-3a14-a1c8-ec8de84e309c"},
    {"name": "E11A1", "uuid": "ac12e9b3-47e6-9599-8fa1-0bb473e5efc7"},
    {"name": "E11A2", "uuid": "5adc33fa-4f30-2899-f131-6fba64c5dd3a"},
    {"name": "E11A3", "uuid": "4c4b8cff-43eb-13d3-8f14-96b783c90cd2"},
    {"name": "E12A1", "uuid": "3ea2b318-423b-cf86-25da-7cbb0eefbe2d"},
    {"name": "V26A2", "uuid": "9d85c932-4820-c060-09c3-668636d4df1b"},
]

# vstats.gg 스킬 슬롯 → C/Q/E/X 키 매핑
# 대부분 Grenade=C, Ability1=Q, Ability2=E, Ultimate=X
# 요원마다 다를 수 있으므로 나중에 valorant-api.com으로 교차검증 필요
SLOT_TO_KEY = {
    "GrenadeAbility": "C",
    "Ability1":       "Q",
    "Ability2":       "E",
    "Ultimate":       "X",
}

DIAMOND_R = 19
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
