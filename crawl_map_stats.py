"""
vstats.gg 요루(Yoru) 맵별 × 액트별 × 티어별 승률 히스토리 크롤러
범위: E10A1 ~ V26A2 (리워크 이후 8액트)

실행: python crawl_map_stats.py
결과: yoru_map_act_history_YYYYMMDD_HHMM.csv

─── 데이터 구조 ────────────────────────────────────────────────
URL: /statistics/{act_uuid}/ALL/{map_id}/agent.json.gz

JSON 한 파일에 모든 티어 데이터가 포함됨.
에이전트별로 r(rank tier) 값이 다른 여러 행이 존재.

r 필드 → 티어 매핑:
  19 → Diamond
  22 → Immortal
  25 → Immortal+
  27 → Radiant

맵 내부 ID (브라우저 네트워크 캡처로 확정):
  ALL      → 전맵 합산
  Infinity → Abyss
  Ascent   → Ascent
  Duality  → Bind
  Foxtrot  → Breeze
  Rook     → Corrode
  Canyon   → Fracture
  Triad    → Haven
  Port     → Icebox
  Jam      → Lotus
  Pitt     → Pearl
  Bonsai   → Split
  Juliett  → Sunset
────────────────────────────────────────────────────────────────
"""

import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── 상수 ───────────────────────────────────────────────────
YORU_UUID = "7f94d92c-4234-0a36-9646-3a87eb8b5c89"

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

# r 필드 기반 티어 정의
TIERS = [
    {"r": 19, "name": "Diamond"},
    {"r": 22, "name": "Immortal"},
    {"r": 25, "name": "Immortal+"},
    {"r": 27, "name": "Radiant"},
]

BASE_URL = "https://www.vstats.gg/statistics/{act_uuid}/ALL/{map_id}/agent.json.gz"

ACT_ORDER = ["E10A1","E10A2","E10A3","E11A1","E11A2","E11A3","E12A1","V26A2"]


# ─── 수집 ───────────────────────────────────────────────────
def fetch_all_tiers(page, act_uuid: str, map_id: str):
    """맵+액트 JSON 한 번 fetch → 요루의 모든 티어 행 반환"""
    url = BASE_URL.format(act_uuid=act_uuid, map_id=map_id)
    try:
        result = page.evaluate(f"""
            async () => {{
                const resp = await fetch('{url}');
                if (!resp.ok) return {{ _status: resp.status }};
                const text = await resp.text();
                if (!text || text.trim() === '' || text.trim() === '[]') return null;
                const data = JSON.parse(text);
                return data.filter(d => d.a === '{YORU_UUID}');
            }}
        """)
        return result
    except Exception as e:
        return {"_error": str(e)[:60]}


def crawl(headless: bool = False) -> pd.DataFrame:
    rows = []

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

        total_requests = len(ACTS) * len(MAPS)
        total_rows = total_requests * len(TIERS)
        done = 0

        print(
            f"수집: {len(ACTS)}액트 × {len(MAPS)}맵 = {total_requests}회 요청\n"
            f"      × {len(TIERS)}티어 = {total_rows}행 예상\n"
        )
        print(f"{'액트':<8} {'맵':<10} {'티어':<12} {'승률':>7} {'매치':>9} {'KD':>6}")
        print("─" * 60)

        for act in ACTS:
            for m in MAPS:
                done += 1
                yoru_rows = fetch_all_tiers(page, act["uuid"], m["id"])

                if yoru_rows is None or (isinstance(yoru_rows, list) and len(yoru_rows) == 0):
                    for tier in TIERS:
                        rows.append({
                            "act": act["name"], "act_uuid": act["uuid"],
                            "map": m["name"],
                            "tier": tier["name"], "tier_r": tier["r"],
                            "win_rate": None, "non_mirror_wr": None,
                            "matches": 0, "kd_ratio": None,
                            "note": "no_picks",
                        })
                    print(f"[{done:3d}/{total_requests}] {act['name']:<8} {m['name']:<10} → 픽 없음")
                    time.sleep(0.2)
                    continue

                if isinstance(yoru_rows, dict) and ("_error" in yoru_rows or "_status" in yoru_rows):
                    err = yoru_rows.get("_error") or yoru_rows.get("_status", "")
                    for tier in TIERS:
                        rows.append({
                            "act": act["name"], "act_uuid": act["uuid"],
                            "map": m["name"],
                            "tier": tier["name"], "tier_r": tier["r"],
                            "win_rate": None, "non_mirror_wr": None,
                            "matches": None, "kd_ratio": None,
                            "note": f"error:{err}",
                        })
                    print(f"[{done:3d}/{total_requests}] {act['name']:<8} {m['name']:<10} → 오류: {err}")
                    time.sleep(0.2)
                    continue

                r_map = {row["r"]: row for row in yoru_rows}

                for tier in TIERS:
                    entry = r_map.get(tier["r"])

                    if entry is None:
                        rows.append({
                            "act": act["name"], "act_uuid": act["uuid"],
                            "map": m["name"],
                            "tier": tier["name"], "tier_r": tier["r"],
                            "win_rate": None, "non_mirror_wr": None,
                            "matches": 0, "kd_ratio": None,
                            "note": "no_picks",
                        })
                        print(f"[{done:3d}/{total_requests}] {act['name']:<8} {m['name']:<10} {tier['name']:<12} → 픽없음")
                        continue

                    k  = entry.get("k", 0) or 0
                    d  = entry.get("d", 1) or 1
                    kd = round(k / d, 3) if d else None
                    wr  = entry.get("wr")
                    m_cnt = entry.get("m", 0)

                    print(
                        f"[{done:3d}/{total_requests}] {act['name']:<8} {m['name']:<10} {tier['name']:<12}"
                        f"  {str(wr)+'%':>7}  {m_cnt:>9,}  {str(kd):>6}"
                    )
                    rows.append({
                        "act": act["name"], "act_uuid": act["uuid"],
                        "map": m["name"],
                        "tier": tier["name"], "tier_r": tier["r"],
                        "win_rate": wr,
                        "non_mirror_wr": entry.get("nwr"),
                        "matches": m_cnt,
                        "kd_ratio": kd,
                        "note": "ok",
                    })

                time.sleep(0.25)

            print()

        browser.close()

    return pd.DataFrame(rows)


# ─── 요약 출력 ──────────────────────────────────────────────
def print_summary(df: pd.DataFrame):
    ok = df[df["note"] == "ok"]
    print("\n" + "=" * 65)
    print(f"총 {len(df)}건 / 성공 {len(ok)}건 / 실패·픽없음 {len(df)-len(ok)}건")

    if ok.empty:
        return

    tier_order = [t["name"] for t in TIERS]
    for tier_name in tier_order:
        sub = ok[ok["tier"] == tier_name]
        if sub.empty:
            continue
        print(f"\n── [{tier_name}] 맵 × 액트 승률 ──────────────────────")
        pivot = sub.pivot_table(index="map", columns="act", values="win_rate", aggfunc="first")
        ordered_cols = [a for a in ACT_ORDER if a in pivot.columns]
        print(pivot.reindex(columns=ordered_cols).round(2).to_string())

    print("=" * 65)


def main():
    print("=" * 65)
    print("vstats.gg 요루 맵별 × 액트별 × 티어별 히스토리 수집")
    print(f"범위: {ACTS[0]['name']} ~ {ACTS[-1]['name']}  |  맵: {len(MAPS)}개")
    print(f"티어: {[t['name'] for t in TIERS]}  |  방식: r 필드로 분리")
    print("=" * 65 + "\n")

    df = crawl(headless=False)

    if df.empty:
        print("⚠️  수집 데이터 없음")
        return

    fname = f"yoru_map_act_history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(fname, index=False, encoding="utf-8-sig")
    print(f"\n저장: {fname}")
    print_summary(df)


if __name__ == "__main__":
    main()