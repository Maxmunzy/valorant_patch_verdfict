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
from agent_data import (
    VSTATS_AGENT_UUID_MAP as AGENTS,
    CRAWL_ACTS as ACTS,
    VSTATS_MAPS as MAPS,
    DIAMOND_R,
)

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
    "V25A1": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "V25A2": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "V25A3": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Lotus","Split"},
    "V25A4": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Pearl","Split"},
    "V25A5": {"Abyss","Ascent","Bind","Breeze","Haven","Icebox","Pearl","Split"},
    "V25A6": {"Abyss","Ascent","Bind","Haven","Icebox","Pearl","Split","Sunset"},
    "V26A1": {"Abyss","Ascent","Bind","Haven","Icebox","Pearl","Split","Sunset"},
    "V26A2": {"Abyss","Ascent","Bind","Corrode","Haven","Icebox","Pearl","Split"},
}

BASE_URL = "https://www.vstats.gg/statistics/{act_uuid}/ALL/{map_id}/agent.json.gz"


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
    print("\n[맵 의존도 상위 10 (V26A1 기준)]")
    sample = dep[dep["act"] == "V26A1"].sort_values("map_dep_score", ascending=False).head(10)
    print(sample[["agent","top_map","top_map_frac","map_dep_score","in_rotation","effective_map_dep"]].to_string(index=False))

    print("\n[Viper 맵 의존도 추이]")
    viper = dep[dep["agent"] == "Viper"][["act","top_map","map_dep_score","in_rotation","effective_map_dep"]]
    print(viper.to_string(index=False))


if __name__ == "__main__":
    main()
