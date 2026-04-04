"""
전 요원 맵별 × 액트별 픽률 크롤러
vstats.gg API: /statistics/{act_uuid}/ALL/{map_id}/agent.json.gz
→ 한 요청으로 전 요원 데이터 수집 (UUID 필터 없음)

출력:
  all_agents_map_stats.csv      원본 (act × map × agent × matches)
  map_dependency_scores.csv     요원별 맵 의존도 지수 (act × agent)

실행: python crawl_map_all_agents.py
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── 요원 UUID → 이름 매핑 ───────────────────────────────────
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

MAPS = [
    {"name": "ALL",      "id": "ALL"},
    {"name": "Abyss",    "id": "Infinity"},
    {"name": "Ascent",   "id": "Ascent"},
    {"name": "Bind",     "id": "Duality"},
    {"name": "Breeze",   "id": "Foxtrot"},
    {"name": "Corrode",  "id": "Rook"},
    {"name": "Fracture", "id": "Canyon"},
    {"name": "Haven",    "id": "Triad"},
    {"name": "Icebox",   "id": "Port"},
    {"name": "Lotus",    "id": "Jam"},
    {"name": "Pearl",    "id": "Pitt"},
    {"name": "Split",    "id": "Bonsai"},
    {"name": "Sunset",   "id": "Juliett"},
]

# 현재 맵풀 로테이션 (패치 시점별로 업데이트 필요)
# 패치 → 해당 시점 맵풀
MAP_ROTATION = {
    "E6A3":  {"Ascent","Bind","Breeze","Fracture","Haven","Icebox","Pearl","Split"},
    "E7A1":  {"Ascent","Bind","Breeze","Fracture","Haven","Icebox","Lotus","Pearl"},
    "E7A2":  {"Ascent","Bind","Breeze","Fracture","Haven","Icebox","Lotus","Pearl"},
    "E7A3":  {"Ascent","Bind","Breeze","Fracture","Haven","Icebox","Lotus","Pearl"},
    "E8A1":  {"Ascent","Bind","Breeze","Haven","Icebox","Lotus","Pearl","Split"},
    "E8A2":  {"Ascent","Bind","Breeze","Haven","Icebox","Lotus","Pearl","Split"},
    "E8A3":  {"Ascent","Bind","Haven","Icebox","Lotus","Pearl","Split","Sunset"},
    "E9A1":  {"Ascent","Bind","Haven","Icebox","Lotus","Pearl","Split","Sunset"},
    "E9A2":  {"Ascent","Bind","Haven","Icebox","Lotus","Pearl","Split","Sunset"},
    "E9A3":  {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "E10A1": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "E10A2": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "E10A3": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "E11A1": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Pearl","Split"},
    "E11A2": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Pearl","Split"},
    "E11A3": {"Abyss","Ascent","Bind","Haven","Icebox","Pearl","Split","Sunset"},
    "E12A1": {"Abyss","Ascent","Bind","Haven","Icebox","Pearl","Split","Sunset"},
    "V26A2": {"Abyss","Ascent","Bind","Corrode","Haven","Icebox","Pearl","Split"},
}

BASE_URL = "https://www.vstats.gg/statistics/{act_uuid}/ALL/{map_id}/agent.json.gz"

DIAMOND_R = 19  # Diamond 티어 r값 (대표 티어)


def fetch_map_act(page, act_uuid, map_id):
    """(act × map) JSON → 전 요원 Diamond 티어 데이터 반환"""
    url = BASE_URL.format(act_uuid=act_uuid, map_id=map_id)
    try:
        result = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{url}');
                if (!resp.ok) return {{ _status: resp.status }};
                const text = await resp.text();
                if (!text || text.trim() === '' || text.trim() === '[]') return [];
                const data = JSON.parse(text);
                return data.filter(d => d.r === {DIAMOND_R});
            }}
        """)
        return result
    except Exception as e:
        return {"_error": str(e)[:80]}


def crawl():
    rows = []
    total = len(ACTS) * len(MAPS)
    done  = 0

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

        print("vstats.gg 로드 중...", end=" ", flush=True)
        page.goto("https://www.vstats.gg", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        print("OK\n")

        print(f"수집: {len(ACTS)}액트 x {len(MAPS)}맵 = {total}회 요청 / 전 요원")
        print("-" * 60)

        for act in ACTS:
            for m in MAPS:
                done += 1
                data = fetch_map_act(page, act["uuid"], m["id"])

                if isinstance(data, dict) and ("_error" in data or "_status" in data):
                    err = data.get("_error") or data.get("_status", "")
                    print(f"[{done:3d}/{total}] {act['name']:<7} {m['name']:<10} ERROR: {err}")
                    time.sleep(0.3)
                    continue

                if not data:
                    print(f"[{done:3d}/{total}] {act['name']:<7} {m['name']:<10} (empty)")
                    time.sleep(0.2)
                    continue

                agent_count = 0
                for entry in data:
                    uuid = entry.get("a", "")
                    name = AGENTS.get(uuid)
                    if not name:
                        continue
                    rows.append({
                        "act":      act["name"],
                        "map":      m["name"],
                        "agent":    name,
                        "uuid":     uuid,
                        "matches":  entry.get("m", 0) or 0,
                        "win_rate": entry.get("wr"),
                        "kd":       round(entry.get("k",0) / max(entry.get("d",1),1), 3),
                    })
                    agent_count += 1

                print(f"[{done:3d}/{total}] {act['name']:<7} {m['name']:<10} {agent_count}요원")
                time.sleep(0.25)

        browser.close()

    return pd.DataFrame(rows)


def compute_map_dependency(df):
    """
    요원 × 액트 단위 맵 의존도 지수 계산

    map_fraction   = 특정 맵 매치수 / ALL맵 총 매치수
    map_dep_score  = max(map_fraction) / mean(map_fraction) 중 특정 맵 제외
                     → 1.0에 가까우면 균등, 클수록 특정 맵 집중

    top_map        = 가장 많이 픽된 맵
    top_map_frac   = top_map의 매치 비중
    in_rotation    = 해당 액트 시점에 top_map이 로테이션에 있는지
    """
    rows = []

    all_data  = df[df["map"] == "ALL"][["act","agent","matches"]].rename(columns={"matches":"total_matches"})
    map_data  = df[df["map"] != "ALL"]

    merged = map_data.merge(all_data, on=["act","agent"], how="left")
    merged["map_frac"] = merged["matches"] / merged["total_matches"].replace(0, np.nan)

    for (act, agent), grp in merged.groupby(["act","agent"]):
        grp = grp[grp["matches"] > 0]
        if grp.empty or grp["total_matches"].iloc[0] == 0:
            continue

        total_m   = grp["total_matches"].iloc[0]
        top_row   = grp.loc[grp["matches"].idxmax()]
        top_map   = top_row["map"]
        top_frac  = top_row["map_frac"] if not pd.isna(top_row["map_frac"]) else 0.0

        fracs = grp["map_frac"].dropna()
        mean_frac = float(fracs.mean()) if not fracs.empty else 0.0

        map_dep = round(float(top_frac) / mean_frac, 3) if mean_frac > 0 else np.nan

        rotation   = MAP_ROTATION.get(act, set())
        in_rotation = int(top_map in rotation)
        effective   = round(map_dep * in_rotation, 3) if not pd.isna(map_dep) else 0.0

        rows.append({
            "act":             act,
            "agent":           agent,
            "top_map":         top_map,
            "top_map_frac":    round(float(top_frac), 4),
            "map_dep_score":   map_dep,
            "in_rotation":     in_rotation,
            "effective_map_dep": effective,
            "total_matches":   int(total_m),
            "n_maps_played":   int((grp["matches"] > 0).sum()),
        })

    return pd.DataFrame(rows)


def main():
    print("=" * 60)
    print("전 요원 맵별 픽률 크롤러")
    print(f"액트: {ACTS[0]['name']} ~ {ACTS[-1]['name']}  |  맵: {len(MAPS)-1}개 + ALL")
    print("=" * 60 + "\n")

    df = crawl()

    if df.empty:
        print("데이터 없음")
        return

    df.to_csv("all_agents_map_stats.csv", index=False, encoding="utf-8-sig")
    print(f"\n원본 저장: all_agents_map_stats.csv ({len(df)}행)")

    dep = compute_map_dependency(df)
    dep.to_csv("map_dependency_scores.csv", index=False, encoding="utf-8-sig")
    print(f"의존도 저장: map_dependency_scores.csv ({len(dep)}행)")

    # 샘플 출력
    print("\n[맵 의존도 상위 10 (E12A1 기준)]")
    sample = dep[dep["act"] == "E12A1"].sort_values("map_dep_score", ascending=False).head(10)
    print(sample[["agent","top_map","top_map_frac","map_dep_score","in_rotation","effective_map_dep"]].to_string(index=False))

    print("\n[Viper 맵 의존도 추이]")
    viper = dep[dep["agent"] == "Viper"][["act","top_map","map_dep_score","in_rotation","effective_map_dep"]]
    print(viper.to_string(index=False))


if __name__ == "__main__":
    main()
