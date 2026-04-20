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
from agent_data import VSTATS_AGENTS as AGENTS, CRAWL_ACTS as ACTS, DIAMOND_PLUS_R
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
