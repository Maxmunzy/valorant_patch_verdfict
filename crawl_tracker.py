"""
vstats.gg 요루(Yoru) 액트별 히스토리 크롤러 v3
- r 필드 = 티어 ID (에이전트 순위 아님)
- 다이아+(r=19), 이모탈(r=22), 이모탈+(r=25), 래디언트(r=27) 합산
- 픽률 포함 (전체 에이전트 × 해당 티어 매치 합산 → 분모)
- 전 지역 합산 (vstats.gg URL에 리전 파라미터 없음)

실행: python crawl_act_history_v3.py
결과: yoru_act_history_YYYYMMDD_HHMM.csv

r 필드 → 티어 매핑:
  4  → Iron      7  → Bronze    10 → Silver
  13 → Gold      16 → Platinum  19 → Diamond
  22 → Immortal  25 → Immortal+ 27 → Radiant
"""

import time
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ─── 설정 ─────────────────────────────────────────────────
YORU_UUID = "7f94d92c-4234-0a36-9646-3a87eb8b5c89"

# 다이아+ 티어 r값
DIAMOND_PLUS_R = {19, 22, 25, 27}  # Diamond, Immortal, Immortal+, Radiant

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

STATS_URL = "https://www.vstats.gg/statistics/{act_uuid}/ALL/ALL/agent.json.gz"


def fetch_act(page, act_uuid: str) -> dict | None:
    """
    전체 배열 fetch →
    - 다이아+ 티어(r∈{19,22,25,27})의 요루 행들 추출 및 합산
    - 동일 티어의 전체 에이전트 매치 합산 (픽률 분모)
    반환:
      {
        yoru_matches, yoru_kills, yoru_deaths,
        total_matches,           # 다이아+ 전 에이전트 합산
        wr_by_tier,              # {r: wr} 개별 티어 승률 (가중평균 검증용)
        nwr_by_tier,
        m_by_tier,               # {r: matches}
      }
    """
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
                const YORU = '{YORU_UUID}';

                let yoruMatches = 0, yoruKills = 0, yoruDeaths = 0;
                let totalMatches = 0;
                const wrByTier = {{}}, nwrByTier = {{}}, mByTier = {{}};

                for (const d of data) {{
                    if (!diamondPlusR.has(d.r)) continue;

                    // 전체 에이전트 매치 합산 (픽률 분모)
                    totalMatches += (d.m || 0);

                    if (d.a === YORU) {{
                        yoruMatches += (d.m || 0);
                        yoruKills   += (d.k || 0);
                        yoruDeaths  += (d.d || 0);
                        wrByTier[d.r]  = d.wr;
                        nwrByTier[d.r] = d.nwr;
                        mByTier[d.r]   = d.m;
                    }}
                }}

                return {{
                    yoru_matches: yoruMatches,
                    yoru_kills:   yoruKills,
                    yoru_deaths:  yoruDeaths,
                    total_matches: totalMatches,
                    wr_by_tier:   wrByTier,
                    nwr_by_tier:  nwrByTier,
                    m_by_tier:    mByTier,
                }};
            }}
        """)
        return result
    except Exception as e:
        return {"_error": str(e)[:60]}


def weighted_avg_wr(wr_by_tier: dict, m_by_tier: dict) -> float | None:
    """티어별 승률을 매치수 가중평균으로 합산"""
    total_m = sum(m_by_tier.values())
    if not total_m:
        return None
    weighted = sum(
        wr_by_tier[r] * m_by_tier[r]
        for r in wr_by_tier
        if r in m_by_tier and wr_by_tier[r] is not None
    )
    return round(weighted / total_m, 2)


def crawl(headless: bool = False):
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

        print(f"{'액트':<10} {'승률(가중)':>10} {'픽률':>7} {'매치(다이아+)':>14} {'KD':>6}")
        print("─" * 60)

        for act in ACTS:
            result = fetch_act(page, act["uuid"])

            if result is None:
                print(f"{act['name']:<10} → 데이터 없음")
                rows.append({
                    "act": act["name"], "act_uuid": act["uuid"],
                    "win_rate": None, "win_rate_weighted": None,
                    "non_mirror_wr": None,
                    "matches": 0, "total_matches": None,
                    "pick_rate_pct": None, "kd_ratio": None,
                    "note": "no_data",
                })
                time.sleep(0.5)
                continue

            if "_status" in result or "_error" in result:
                err = result.get("_error") or result.get("_status", "")
                print(f"{act['name']:<10} → 오류: {err}")
                rows.append({
                    "act": act["name"], "act_uuid": act["uuid"],
                    "win_rate": None, "win_rate_weighted": None,
                    "non_mirror_wr": None,
                    "matches": None, "total_matches": None,
                    "pick_rate_pct": None, "kd_ratio": None,
                    "note": f"error:{err}",
                })
                time.sleep(0.5)
                continue

            yoru_m  = result["yoru_matches"]
            total_m = result["total_matches"]
            k = result["yoru_kills"]
            d = result["yoru_deaths"]

            kd = round(k / d, 3) if d else None
            pick_rate = round(yoru_m / total_m * 100, 2) if total_m else None

            # 가중평균 승률
            wr_by_tier = {int(k): v for k, v in result["wr_by_tier"].items()}
            m_by_tier  = {int(k): v for k, v in result["m_by_tier"].items()}
            nwr_by_tier = {int(k): v for k, v in result["nwr_by_tier"].items()}
            wr_weighted = weighted_avg_wr(wr_by_tier, m_by_tier)
            nwr_weighted = weighted_avg_wr(nwr_by_tier, m_by_tier)

            print(
                f"{act['name']:<10}"
                f"  {str(wr_weighted)+'%':>10}"
                f"  {str(pick_rate)+'%':>7}"
                f"  {yoru_m:>12,}"
                f"  {str(kd):>6}"
            )

            rows.append({
                "act": act["name"],
                "act_uuid": act["uuid"],
                "win_rate": wr_weighted,        # 다이아+ 티어 가중평균
                "non_mirror_wr": nwr_weighted,
                "matches": yoru_m,              # 다이아+ 합산 매치수
                "total_matches": total_m,       # 다이아+ 전 에이전트 합산
                "pick_rate_pct": pick_rate,
                "kd_ratio": kd,
                # 티어별 원본 (검증용)
                "wr_diamond":   wr_by_tier.get(19),
                "wr_immortal":  wr_by_tier.get(22),
                "wr_immortal2": wr_by_tier.get(25),
                "wr_radiant":   wr_by_tier.get(27),
                "m_diamond":    m_by_tier.get(19, 0),
                "m_immortal":   m_by_tier.get(22, 0),
                "m_immortal2":  m_by_tier.get(25, 0),
                "m_radiant":    m_by_tier.get(27, 0),
                "note": "ok",
            })

            time.sleep(0.5)

        browser.close()

    return rows


def main():
    print("=" * 65)
    print("vstats.gg 요루 액트별 히스토리 수집 v3")
    print("티어: 다이아+(r=19,22,25,27) 합산  |  전 지역")
    print("픽률 포함 (전 에이전트 다이아+ 매치 합산 분모)")
    print("=" * 65 + "\n")

    rows = crawl(headless=False)

    if not rows:
        print("⚠️  수집 데이터 없음")
        return

    df = pd.DataFrame(rows)
    fname = f"yoru_act_history_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    df.to_csv(fname, index=False, encoding="utf-8-sig")

    ok = df[df["note"] == "ok"]
    print(f"\n저장: {fname}  ({len(ok)}/{len(df)} 성공)")

    if not ok.empty:
        print("\n[요루 액트별 요약 — 다이아+ 합산]")
        print(
            ok[["act", "win_rate", "pick_rate_pct", "matches", "kd_ratio"]]
            .to_string(index=False)
        )
    print("=" * 65)


if __name__ == "__main__":
    main()