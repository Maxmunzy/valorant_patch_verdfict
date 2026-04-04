"""
vstats.gg 요루(Yoru) 맵별 × 액트별 히스토리 크롤러 v3
- r 필드 = 티어 ID (에이전트 순위 아님)
- 다이아+(r=19,22,25,27) 합산
- 픽률 포함
- 경쟁 요원(KAY/O, 피닉스, 스카이) ALL 맵 동시 수집
- 전 지역 합산 (vstats.gg URL에 리전 파라미터 없음)

실행: python crawl_map_act_history_v3.py
결과:
  yoru_map_act_history_YYYYMMDD_HHMM.csv
  rival_act_history_YYYYMMDD_HHMM.csv
"""

import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── 설정 ─────────────────────────────────────────────────
YORU_UUID = "7f94d92c-4234-0a36-9646-3a87eb8b5c89"

RIVALS = [
    {"name": "KAYO",   "uuid": "601dbbe7-43ce-be57-2a40-4abd24953621"},
    {"name": "Phoenix", "uuid": "eb93336a-449b-9c1e-0ac9-d37d44d6e8e4"},
    {"name": "Skye",   "uuid": "6f2a04ca-43e0-be17-7f36-b3908627744d"},
]

# 다이아+ 티어 r값
DIAMOND_PLUS_R = [19, 22, 25, 27]

ACTS = [
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

BASE_URL = "https://www.vstats.gg/statistics/{act_uuid}/ALL/{map_id}/agent.json.gz"


def fetch_map(page, act_uuid: str, map_id: str, target_uuids: list[str]) -> dict:
    """
    전체 배열 fetch →
    - 다이아+ 티어(r∈DIAMOND_PLUS_R)만 필터
    - target_uuids 에이전트별 매치/킬/데스 합산
    - 전체 에이전트 다이아+ 매치 합산 (픽률 분모)
    """
    url = BASE_URL.format(act_uuid=act_uuid, map_id=map_id)
    uuids_js = str(target_uuids).replace("'", '"')

    try:
        result = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{url}');
                if (!resp.ok) return {{ _status: resp.status }};
                const text = await resp.text();
                if (!text || text.trim() === '' || text.trim() === '[]') return null;
                const data = JSON.parse(text);

                const diamondPlusR = new Set({DIAMOND_PLUS_R});
                const targetUuids  = new Set({uuids_js});

                let totalMatches = 0;
                const agentData  = {{}};  // uuid -> {{m, k, d, wr_sum, nwr_sum, tier_count}}

                for (const d of data) {{
                    if (!diamondPlusR.has(d.r)) continue;

                    totalMatches += (d.m || 0);

                    if (targetUuids.has(d.a)) {{
                        if (!agentData[d.a]) {{
                            agentData[d.a] = {{ m: 0, k: 0, d: 0, wr_entries: [], nwr_entries: [] }};
                        }}
                        const ag = agentData[d.a];
                        ag.m += (d.m || 0);
                        ag.k += (d.k || 0);
                        ag.d += (d.d || 0);
                        // 가중평균 계산용
                        if (d.wr  != null) ag.wr_entries.push( {{wr:  d.wr,  m: d.m || 0}});
                        if (d.nwr != null) ag.nwr_entries.push({{nwr: d.nwr, m: d.m || 0}});
                    }}
                }}

                // 가중평균 승률 계산
                const weightedWr = (entries, key) => {{
                    const total = entries.reduce((s, e) => s + e.m, 0);
                    if (!total) return null;
                    return Math.round(entries.reduce((s, e) => s + e[key] * e.m, 0) / total * 100) / 100;
                }};

                const agents = {{}};
                for (const [uuid, ag] of Object.entries(agentData)) {{
                    agents[uuid] = {{
                        m:   ag.m,
                        k:   ag.k,
                        d:   ag.d,
                        wr:  weightedWr(ag.wr_entries,  'wr'),
                        nwr: weightedWr(ag.nwr_entries, 'nwr'),
                    }};
                }}

                return {{ agents, total_matches: totalMatches }};
            }}
        """)
        return result
    except Exception as e:
        return {"_error": str(e)[:60]}


def build_agent_row(act_name, map_name, agent_name, agent_uuid, result) -> dict:
    base = {
        "act": act_name, "map": map_name, "agent": agent_name,
        "win_rate": None, "non_mirror_wr": None,
        "matches": None, "total_matches": None,
        "pick_rate_pct": None, "kd_ratio": None,
    }

    if result is None:
        return {**base, "note": "no_data"}
    if "_status" in result or "_error" in result:
        return {**base, "note": f"error:{result.get('_error') or result.get('_status', '')}"}

    total_m = result.get("total_matches", 0) or 0
    agent = result.get("agents", {}).get(agent_uuid)

    if not agent or agent.get("m", 0) == 0:
        return {**base, "total_matches": total_m, "matches": 0, "note": "no_picks"}

    m = agent["m"]
    k = agent.get("k", 0) or 0
    d = agent.get("d", 0) or 1
    pick_rate = round(m / total_m * 100, 2) if total_m else None

    return {
        "act": act_name, "map": map_name, "agent": agent_name,
        "win_rate": agent.get("wr"),
        "non_mirror_wr": agent.get("nwr"),
        "matches": m,
        "total_matches": total_m,
        "pick_rate_pct": pick_rate,
        "kd_ratio": round(k / d, 3) if d else None,
        "note": "ok",
    }


def crawl(headless: bool = False):
    yoru_rows  = []
    rival_rows = []

    all_target_uuids = [YORU_UUID] + [r["uuid"] for r in RIVALS]
    total = len(ACTS) * len(MAPS)
    done  = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
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
            f"https://www.vstats.gg/history?agents={YORU_UUID}",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        time.sleep(3)
        print("OK\n")

        for act in ACTS:
            print(f"▶ {act['name']}")
            for m in MAPS:
                done += 1
                label = f"  [{done:3d}/{total}] {m['name']:<10}"

                result = fetch_map(page, act["uuid"], m["id"], all_target_uuids)

                # 요루 행 저장
                yoru_row = build_agent_row(act["name"], m["name"], "Yoru", YORU_UUID, result)
                yoru_rows.append(yoru_row)

                # 경쟁 요원 (모든 맵)
                for rival in RIVALS:
                    rival_rows.append(
                        build_agent_row(act["name"], m["name"], rival["name"], rival["uuid"], result)
                    )

                # 콘솔 출력
                note = yoru_row["note"]
                if note == "ok":
                    wr = yoru_row["win_rate"]
                    pr = yoru_row["pick_rate_pct"]
                    rival_parts = []
                    for rival in RIVALS:
                        rr = rival_rows[-len(RIVALS) + RIVALS.index(rival)]
                        if rr["note"] == "ok":
                            rival_parts.append(f"{rival['name']}:{str(rr['win_rate'])+'%':>7}")
                    rival_str = "  |  " + "  ".join(rival_parts) if rival_parts else ""
                    print(f"{label} 요루:{str(wr)+'%':>7}  픽률:{str(pr)+'%':>6}{rival_str}")
                elif note == "no_picks":
                    print(f"{label} 픽 없음 (맵 미로테이션)")
                else:
                    print(f"{label} {note}")

                time.sleep(0.25)

            print()

        browser.close()

    return yoru_rows, rival_rows


def main():
    print("=" * 65)
    print("vstats.gg 경쟁 요원 맵×액트 히스토리 수집")
    print(f"티어: 다이아+(r=19,22,25,27) 합산  |  전 지역")
    print(f"액트: {ACTS[0]['name']} ~ {ACTS[-1]['name']}  |  맵: {len(MAPS)}개")
    print(f"경쟁 요원: {', '.join(r['name'] for r in RIVALS)}")
    print("(요루 데이터는 기존 파일 사용 — 저장 스킵)")
    print("=" * 65 + "\n")

    _, rival_rows = crawl(headless=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    if rival_rows:
        df_rival = pd.DataFrame(rival_rows)
        fname_rival = f"rival_map_act_history_{ts}.csv"
        df_rival.to_csv(fname_rival, index=False, encoding="utf-8-sig")
        ok_r = df_rival[df_rival["note"] == "ok"]
        print(f"\n[경쟁 요원] 저장: {fname_rival}  ({len(ok_r)}/{len(df_rival)} 성공)")

        if not ok_r.empty:
            act_order = [a["name"] for a in ACTS]
            for agent_name in [r["name"] for r in RIVALS]:
                sub = ok_r[ok_r["agent"] == agent_name]
                if sub.empty:
                    continue
                print(f"\n[{agent_name} 승률 피벗 — 맵 × 액트]")
                pivot = sub.pivot_table(index="map", columns="act", values="win_rate", aggfunc="first")
                pivot = pivot.reindex(columns=[a for a in act_order if a in pivot.columns])
                print(pivot.round(2).to_string())

                print(f"\n[{agent_name} 픽률 피벗 — 맵 × 액트]")
                pivot_pr = sub.pivot_table(index="map", columns="act", values="pick_rate_pct", aggfunc="first")
                pivot_pr = pivot_pr.reindex(columns=[a for a in act_order if a in pivot_pr.columns])
                print(pivot_pr.round(2).to_string())

    print("\n" + "=" * 65)

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()