"""
전체 요원 랭크 히스토리 배치 크롤러
crawl_tracker.py 구조 재사용 — UUID만 교체

수집 대상:
  - 전 요원 × E6A3 ~ V26A2 (vstats.gg 지원 구간)
  - 다이아+ 합산, 전 지역
  - 픽률·승률·KD·티어별 승률

실행:
  python crawl_all_agents.py                   # 전 요원
  python crawl_all_agents.py --agent Jett      # 특정 요원만
  python crawl_all_agents.py --from Chamber    # 해당 요원부터

출력:
  agent_act_history/{agent_name}.csv           # 요원별 CSV
  agent_act_history_all.csv                    # 전체 합본
"""

import time
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


# ─── 전체 요원 UUID ──────────────────────────────────────────────────────────
# vstats.gg 내부 UUID (브라우저 네트워크 캡처 기준)

AGENTS = [
    {"name": "Astra",     "uuid": "41fb69c1-4189-7b37-f117-bcaf1e96f1bf"},
    {"name": "Breach",    "uuid": "5f8d3a7f-467b-97f3-062c-13acf203c006"},
    {"name": "Brimstone", "uuid": "9f0d8ba9-4140-b941-57d3-a7ad57c6b417"},
    {"name": "Chamber",   "uuid": "22697a3d-45bf-8dd7-4fec-84a9e28c69d7"},
    {"name": "Clove",     "uuid": "1dbf2edd-4729-0984-3115-daa5eed44993"},
    {"name": "Cypher",    "uuid": "117ed9e3-49f3-6512-3ccf-0cada7e3823b"},
    {"name": "Deadlock",  "uuid": "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235"},
    {"name": "Fade",      "uuid": "dade69b4-4f5a-8528-247b-219e5a1facd6"},
    {"name": "Gekko",     "uuid": "e370fa57-4757-3604-3648-499e1f642d3f"},
    {"name": "Harbor",    "uuid": "95b78ed7-4637-86d9-7e41-71ba8c293152"},
    {"name": "Iso",       "uuid": "efba5359-4016-a1e5-7626-b1ae76895940"},
    {"name": "Jett",      "uuid": "add6443a-41bd-e414-f6ad-e58d267f4e95"},
    {"name": "KAYO",      "uuid": "601dbbe7-43ce-be57-2a40-4abd24953621"},
    {"name": "Killjoy",   "uuid": "1e58de9c-4950-5125-93e9-a0aee9f98746"},
    {"name": "Neon",      "uuid": "bb2a4828-46eb-8cd1-e765-15848195d751"},
    {"name": "Omen",      "uuid": "8e253930-4c05-31dd-1b6c-968525494517"},
    {"name": "Phoenix",   "uuid": "eb93336a-449b-9c1b-0a54-a891f7921d69"},
    {"name": "Raze",      "uuid": "f94c3b30-42be-e959-889c-5aa313dba261"},
    {"name": "Reyna",     "uuid": "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc"},
    {"name": "Sage",      "uuid": "569fdd95-4d10-43ab-ca70-79becc718b46"},
    {"name": "Skye",      "uuid": "6f2a04ca-43e0-be17-7f36-b3908627744d"},
    {"name": "Sova",      "uuid": "320b2a48-4d9b-a075-30f1-1f93a9b638fa"},
    {"name": "Tejo",      "uuid": "df1cb487-4902-002e-5c17-d28e83e78588"},
    {"name": "Viper",     "uuid": "707eab51-4836-f488-046a-cda6bf494859"},
    {"name": "Vyse",      "uuid": "b444168c-4e35-8076-db47-ef9bf368f384"},
    {"name": "Veto",      "uuid": "0e38b510-41a8-5780-5e8f-568b2a4f2d6c"},
    {"name": "Waylay",    "uuid": "7c8a4701-4de6-9355-b254-e09bc2a34b72"},
    {"name": "Yoru",      "uuid": "7f94d92c-4234-0a36-9646-3a87eb8b5c89"},
    {"name": "Miks",      "uuid": "92eeef5d-43b5-1d4a-8d03-b3927a09034b"},
]

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
    {"name": "V25A1", "uuid": "476b0893-4c2e-abd6-c5fe-708facff0772"},
    {"name": "V25A2", "uuid": "16118998-4705-5813-86dd-0292a2439d90"},
    {"name": "V25A3", "uuid": "aef237a0-494d-3a14-a1c8-ec8de84e309c"},
    {"name": "V25A4", "uuid": "ac12e9b3-47e6-9599-8fa1-0bb473e5efc7"},
    {"name": "V25A5", "uuid": "5adc33fa-4f30-2899-f131-6fba64c5dd3a"},
    {"name": "V25A6", "uuid": "4c4b8cff-43eb-13d3-8f14-96b783c90cd2"},
    {"name": "V26A1", "uuid": "3ea2b318-423b-cf86-25da-7cbb0eefbe2d"},
    {"name": "V26A2", "uuid": "9d85c932-4820-c060-09c3-668636d4df1b"},
]

DIAMOND_PLUS_R  = {19, 22, 25, 27}
STATS_URL       = "https://www.vstats.gg/statistics/{act_uuid}/ALL/ALL/agent.json.gz"
OUT_DIR         = Path("agent_act_history")


# ─── fetch (crawl_tracker.py 코어 재사용) ────────────────────────────────────

def fetch_agent_act(page, agent_uuid: str, act_uuid: str) -> dict | None:
    url = STATS_URL.format(act_uuid=act_uuid)
    diamond_plus = list(DIAMOND_PLUS_R)

    try:
        result = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{url}');
                if (!resp.ok) return {{ _status: resp.status }};
                const text = await resp.text();
                if (!text || text.trim() === '' || text.trim() === '[]') return null;
                const data = JSON.parse(text);

                const diamondPlusR = new Set({diamond_plus});
                const TARGET = '{agent_uuid}';

                let matches = 0, kills = 0, deaths = 0, totalMatches = 0;
                const wrByTier = {{}}, nwrByTier = {{}}, mByTier = {{}};

                for (const d of data) {{
                    if (!diamondPlusR.has(d.r)) continue;
                    totalMatches += (d.m || 0);
                    if (d.a === TARGET) {{
                        matches += (d.m || 0);
                        kills   += (d.k || 0);
                        deaths  += (d.d || 0);
                        wrByTier[d.r]  = d.wr;
                        nwrByTier[d.r] = d.nwr;
                        mByTier[d.r]   = d.m;
                    }}
                }}

                return {{
                    matches, kills, deaths, total_matches: totalMatches,
                    wr_by_tier: wrByTier, nwr_by_tier: nwrByTier, m_by_tier: mByTier,
                }};
            }}
        """)
        return result
    except Exception as e:
        return {"_error": str(e)[:60]}


def weighted_wr(wr_dict: dict, m_dict: dict) -> float | None:
    total = sum(m_dict.values())
    if not total:
        return None
    w = sum(wr_dict[r] * m_dict[r] for r in wr_dict if r in m_dict and wr_dict[r] is not None)
    return round(w / total, 2)


# ─── 단일 요원 크롤링 ────────────────────────────────────────────────────────

def crawl_agent(page, agent: dict) -> pd.DataFrame:
    name = agent["name"]
    uuid = agent["uuid"]
    rows = []

    print(f"\n▶ {name}")
    for act in ACTS:
        result = fetch_agent_act(page, uuid, act["uuid"])

        if result is None:
            rows.append({"act": act["name"], "agent": name, "note": "no_data"})
            print(f"  {act['name']}: 데이터 없음")
            time.sleep(0.3)
            continue

        if "_status" in result or "_error" in result:
            err = result.get("_error") or result.get("_status", "")
            rows.append({"act": act["name"], "agent": name, "note": f"error:{err}"})
            time.sleep(0.3)
            continue

        m      = result["matches"]
        total  = result["total_matches"]
        k, d   = result["kills"], result["deaths"]

        wr_map  = {int(k): v for k, v in result["wr_by_tier"].items()}
        nwr_map = {int(k): v for k, v in result["nwr_by_tier"].items()}
        m_map   = {int(k): v for k, v in result["m_by_tier"].items()}

        wr  = weighted_wr(wr_map, m_map)
        nwr = weighted_wr(nwr_map, m_map)
        kd  = round(k / d, 3) if d else None
        pr  = round(m / total * 100, 3) if total else None

        row = {
            "act":           act["name"],
            "agent":         name,
            "win_rate":      wr,
            "non_mirror_wr": nwr,
            "matches":       m,
            "total_matches": total,
            "pick_rate_pct": pr,
            "kd_ratio":      kd,
            "wr_diamond":    wr_map.get(19),
            "wr_immortal":   wr_map.get(22),
            "wr_immortal2":  wr_map.get(25),
            "wr_radiant":    wr_map.get(27),
            "m_diamond":     m_map.get(19, 0),
            "m_immortal":    m_map.get(22, 0),
            "m_immortal2":   m_map.get(25, 0),
            "m_radiant":     m_map.get(27, 0),
            "note":          "ok" if m > 0 else "no_picks",
        }
        rows.append(row)

        pr_str = f"{pr:.2f}%" if pr else "-"
        wr_str = f"{wr}%" if wr else "-"
        print(f"  {act['name']:<8} wr={wr_str:<8} pr={pr_str:<8} m={m:>7,}")
        time.sleep(0.4)

    df = pd.DataFrame(rows)
    OUT_DIR.mkdir(exist_ok=True)
    df.to_csv(OUT_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")
    return df


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", type=str, help="특정 요원명 (예: Jett)")
    parser.add_argument("--from",  type=str, dest="from_agent", help="해당 요원부터 실행")
    args = parser.parse_args()

    targets = AGENTS
    if args.agent:
        targets = [a for a in AGENTS if a["name"].lower() == args.agent.lower()]
    elif args.from_agent:
        idx = next((i for i, a in enumerate(AGENTS) if a["name"].lower() == args.from_agent.lower()), 0)
        targets = AGENTS[idx:]

    print("=" * 65)
    print(f"전체 요원 랭크 히스토리 수집 ({len(targets)}명)")
    print(f"구간: {ACTS[0]['name']} ~ {ACTS[-1]['name']}  |  다이아+  |  전 지역")
    print("=" * 65)

    all_dfs = []

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
        page.goto(
            f"https://www.vstats.gg/history?agents={AGENTS[0]['uuid']}",
            wait_until="domcontentloaded", timeout=60000,
        )
        time.sleep(3)
        print("OK\n")

        for agent in targets:
            df = crawl_agent(page, agent)
            all_dfs.append(df)

        browser.close()

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        combined.to_csv("agent_act_history_all.csv", index=False, encoding="utf-8-sig")
        ok = combined[combined["note"] == "ok"]
        print(f"\n\n전체 저장: agent_act_history_all.csv")
        print(f"  요원 {combined['agent'].nunique()}명 / 액트 {combined['act'].nunique()}개 / 성공 {len(ok)}행")


if __name__ == "__main__":
    main()
