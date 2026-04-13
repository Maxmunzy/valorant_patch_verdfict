"""
VCT 대회별 에이전트 픽 크롤러 (범용)
vlr.gg 이벤트 페이지에서 매치 ID 자동 수집 → 전 매치 파싱

실행:
  python crawl_vct.py                    # 전체 대회 순차 수집
  python crawl_vct.py --event 2760       # 특정 이벤트만
  python crawl_vct.py --from 1014        # 해당 이벤트 ID부터

출력:
  vct_data/{event_id}_{slug}.csv         # 대회별 원본 픽 데이터
  vct_summary.csv                        # 전 대회 에이전트별 집계 (학습용)
"""

import re
import time
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup


# ─── 대회 설정 ───────────────────────────────────────────────────────────────
# patch_before: 해당 대회 직후 발생한 패치 (pre_vct 피처로 사용)
# patch_after:  해당 대회 직전에 발생한 패치 (post_vct 피처로 사용)

TOURNAMENTS = [
    # ── 2022 ────────────────────────────────────────────────────────────────
    {
        "event_id":    926,
        "slug":        "champions-tour-stage-1-masters-reykjavik-2022",
        "name":        "Masters Reykjavik 2022",
        "year":        2022,
        "patch_before": "4.08",   # Jett 대쉬 너프
    },
    {
        "event_id":    1014,
        "slug":        "champions-tour-stage-2-masters-copenhagen-2022",
        "name":        "Masters Copenhagen 2022",
        "year":        2022,
        "patch_before": None,
        "patch_after":  "4.08",   # 제트 너프 이후 첫 대회
    },
    {
        "event_id":    1015,
        "slug":        "champions-tour-2022-champions-istanbul",
        "name":        "Champions 2022",
        "year":        2022,
        "patch_before": "5.12",   # Chamber 대너프
    },
    # ── 2023 권역 리그 ───────────────────────────────────────────────────────
    {
        "event_id":    1188,
        "slug":        "champions-tour-2023-lock-in-sao-paulo",
        "name":        "VCT LOCK//IN 2023",
        "year":        2023,
        "patch_after":  "5.12",   # Chamber 너프 이후 첫 대회
    },
    {
        "event_id":    1189,
        "slug":        "champions-tour-2023-americas-league",
        "name":        "VCT Americas League 2023",
        "year":        2023,
    },
    {
        "event_id":    1190,
        "slug":        "champions-tour-2023-emea-league",
        "name":        "VCT EMEA League 2023",
        "year":        2023,
    },
    {
        "event_id":    1191,
        "slug":        "champions-tour-2023-pacific-league",
        "name":        "VCT Pacific League 2023",
        "year":        2023,
    },
    # ── 2023 인터내셔널 ──────────────────────────────────────────────────────
    {
        "event_id":    1494,
        "slug":        "champions-tour-2023-masters-tokyo",
        "name":        "Masters Tokyo 2023",
        "year":        2023,
    },
    {
        "event_id":    1657,
        "slug":        "champions-tour-2023-champions-los-angeles",
        "name":        "Champions 2023",
        "year":        2023,
    },
    # ── 2024 권역 Kickoff ────────────────────────────────────────────────────
    {
        "event_id":    1923,
        "slug":        "champions-tour-2024-americas-kickoff",
        "name":        "VCT Americas Kickoff 2024",
        "year":        2024,
    },
    {
        "event_id":    1925,
        "slug":        "champions-tour-2024-emea-kickoff",
        "name":        "VCT EMEA Kickoff 2024",
        "year":        2024,
    },
    {
        "event_id":    1924,
        "slug":        "champions-tour-2024-pacific-kickoff",
        "name":        "VCT Pacific Kickoff 2024",
        "year":        2024,
    },
    {
        "event_id":    1926,
        "slug":        "champions-tour-2024-cn-kickoff",
        "name":        "VCT CN Kickoff 2024",
        "year":        2024,
    },
    # ── 2024 권역 Stage 1 ────────────────────────────────────────────────────
    {
        "event_id":    2004,
        "slug":        "champions-tour-2024-americas-stage-1",
        "name":        "VCT Americas Stage 1 2024",
        "year":        2024,
    },
    {
        "event_id":    1998,
        "slug":        "champions-tour-2024-emea-stage-1",
        "name":        "VCT EMEA Stage 1 2024",
        "year":        2024,
    },
    {
        "event_id":    2002,
        "slug":        "champions-tour-2024-pacific-stage-1",
        "name":        "VCT Pacific Stage 1 2024",
        "year":        2024,
    },
    {
        "event_id":    2006,
        "slug":        "champions-tour-2024-cn-stage-1",
        "name":        "VCT CN Stage 1 2024",
        "year":        2024,
    },
    # ── 2024 인터내셔널 ──────────────────────────────────────────────────────
    {
        "event_id":    1921,
        "slug":        "champions-tour-2024-masters-madrid",
        "name":        "Masters Madrid 2024",
        "year":        2024,
    },
    # ── 2024 권역 Stage 2 ────────────────────────────────────────────────────
    {
        "event_id":    2095,
        "slug":        "champions-tour-2024-americas-stage-2",
        "name":        "VCT Americas Stage 2 2024",
        "year":        2024,
    },
    {
        "event_id":    2094,
        "slug":        "champions-tour-2024-emea-stage-2",
        "name":        "VCT EMEA Stage 2 2024",
        "year":        2024,
    },
    {
        "event_id":    2005,
        "slug":        "champions-tour-2024-pacific-stage-2",
        "name":        "VCT Pacific Stage 2 2024",
        "year":        2024,
    },
    {
        "event_id":    2096,
        "slug":        "champions-tour-2024-cn-stage-2",
        "name":        "VCT CN Stage 2 2024",
        "year":        2024,
    },
    # ── 2024 인터내셔널 ──────────────────────────────────────────────────────
    {
        "event_id":    1999,
        "slug":        "champions-tour-2024-masters-shanghai",
        "name":        "Masters Shanghai 2024",
        "year":        2024,
    },
    {
        "event_id":    2097,
        "slug":        "champions-tour-2024-champions-seoul",
        "name":        "Champions 2024",
        "year":        2024,
    },
    # ── 2025 권역 Kickoff ────────────────────────────────────────────────────
    {
        "event_id":    2274,
        "slug":        "champions-tour-2025-americas-kickoff",
        "name":        "VCT Americas Kickoff 2025",
        "year":        2025,
    },
    {
        "event_id":    2275,
        "slug":        "champions-tour-2025-china-kickoff",
        "name":        "VCT CN Kickoff 2025",
        "year":        2025,
    },
    {
        "event_id":    2276,
        "slug":        "champions-tour-2025-emea-kickoff",
        "name":        "VCT EMEA Kickoff 2025",
        "year":        2025,
    },
    {
        "event_id":    2277,
        "slug":        "vct-2025-pacific-kickoff",
        "name":        "VCT Pacific Kickoff 2025",
        "year":        2025,
    },
    # ── 2025 권역 Stage 1 ────────────────────────────────────────────────────
    {
        "event_id":    2347,
        "slug":        "champions-tour-2025-americas-stage-1",
        "name":        "VCT Americas Stage 1 2025",
        "year":        2025,
    },
    {
        "event_id":    2380,
        "slug":        "champions-tour-2025-emea-stage-1",
        "name":        "VCT EMEA Stage 1 2025",
        "year":        2025,
    },
    {
        "event_id":    2379,
        "slug":        "champions-tour-2025-pacific-stage-1",
        "name":        "VCT Pacific Stage 1 2025",
        "year":        2025,
    },
    {
        "event_id":    2359,
        "slug":        "champions-tour-2025-cn-stage-1",
        "name":        "VCT CN Stage 1 2025",
        "year":        2025,
    },
    # ── 2025 인터내셔널 ──────────────────────────────────────────────────────
    {
        "event_id":    2281,
        "slug":        "champions-tour-2025-masters-bangkok",
        "name":        "Masters Bangkok 2025",
        "year":        2025,
    },
    # ── 2025 권역 Stage 2 ────────────────────────────────────────────────────
    {
        "event_id":    2501,
        "slug":        "champions-tour-2025-americas-stage-2",
        "name":        "VCT Americas Stage 2 2025",
        "year":        2025,
    },
    {
        "event_id":    2498,
        "slug":        "champions-tour-2025-emea-stage-2",
        "name":        "VCT EMEA Stage 2 2025",
        "year":        2025,
    },
    {
        "event_id":    2500,
        "slug":        "champions-tour-2025-pacific-stage-2",
        "name":        "VCT Pacific Stage 2 2025",
        "year":        2025,
    },
    {
        "event_id":    2499,
        "slug":        "champions-tour-2025-cn-stage-2",
        "name":        "VCT CN Stage 2 2025",
        "year":        2025,
    },
    # ── 2025 인터내셔널 ──────────────────────────────────────────────────────
    {
        "event_id":    2283,
        "slug":        "champions-tour-2025-champions",
        "name":        "Champions 2025",
        "year":        2025,
    },
    # ── 2026 ────────────────────────────────────────────────────────────────
    # ── 2026 권역 Kickoff (12.05 패치 전 - pre-nerf 기준선) ──────────────────
    {
        "event_id":    2682,
        "slug":        "vct-2026-americas-kickoff",
        "name":        "VCT Americas Kickoff 2026",
        "year":        2026,
        "patch_before": "12.05",
    },
    {
        "event_id":    2683,
        "slug":        "vct-2026-pacific-kickoff",
        "name":        "VCT Pacific Kickoff 2026",
        "year":        2026,
        "patch_before": "12.05",
    },
    {
        "event_id":    2684,
        "slug":        "vct-2026-emea-kickoff",
        "name":        "VCT EMEA Kickoff 2026",
        "year":        2026,
        "patch_before": "12.05",
    },
    {
        "event_id":    2685,
        "slug":        "vct-2026-china-kickoff",
        "name":        "VCT CN Kickoff 2026",
        "year":        2026,
        "patch_before": "12.05",
    },
    # ── 2026 인터내셔널 ──────────────────────────────────────────────────────
    {
        "event_id":    2760,
        "slug":        "champions-tour-2026-masters-santiago",
        "name":        "Masters Santiago 2026",
        "year":        2026,
        "patch_before": "12.05",  # Yoru 너프 전 국제대회
    },
    # ── 2026 권역 Stage 1 (Yoru 너프 12.05 직후 - post-nerf 반응 측정) ────────
    {
        "event_id":    2863,
        "slug":        "vct-2026-emea-stage-1",
        "name":        "VCT EMEA Stage 1 2026",
        "year":        2026,
        "patch_after":  "12.05",  # Yoru 너프 이후 첫 권역 대회
    },
    {
        "event_id":    2775,
        "slug":        "vct-2026-pacific-stage-1",
        "name":        "VCT Pacific Stage 1 2026",
        "year":        2026,
        "patch_after":  "12.05",
    },
    {
        "event_id":    2860,
        "slug":        "vct-2026-americas-stage-1",
        "name":        "VCT Americas Stage 1 2026",
        "year":        2026,
        "patch_after":  "12.05",
    },
    {
        "event_id":    2864,  
        "slug":        "vct-2026-cn-stage-1",
        "name":        "VCT CN Stage 1 2026",
        "year":        2026,
        "patch_after":  "12.05",
    },
    # Masters London, Champions 2026 - 아직 미개최, 필요 시 추가
]

# 기본 크롤 대상 - python crawl_vct.py 실행 시 이 대회만 수집
# 전체 수집: python crawl_vct.py --all
STAGE1_2026_IDS = {2863, 2775, 2860, 2864}

MAP_ALIASES = {
    "haven": "Haven", "pearl": "Pearl", "split": "Split",
    "abyss": "Abyss", "breeze": "Breeze", "corrode": "Corrode",
    "bind": "Bind", "ascent": "Ascent", "icebox": "Icebox",
    "lotus": "Lotus", "sunset": "Sunset", "fracture": "Fracture",
    "pearl": "Pearl", "drift": "Drift",
}

OUT_DIR = Path("vct_data")


# ─── 매치 ID 수집 ────────────────────────────────────────────────────────────

def fetch_match_ids(page, event_id: int, slug: str) -> list[int]:
    """이벤트 매치 페이지에서 매치 ID 자동 추출"""
    url = f"https://www.vlr.gg/event/matches/{event_id}/{slug}/?series_id=all"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        html = page.content()
    except Exception as e:
        print(f"  ⚠  이벤트 페이지 로드 실패: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    ids = set()
    for a in soup.find_all("a", href=True):
        m = re.match(r"^/(\d+)/", a["href"])
        if m:
            mid = int(m.group(1))
            # vlr.gg 매치 ID는 보통 5자리 이상 (이벤트 ID와 구분)
            if mid > 10000:
                ids.add(mid)

    return sorted(ids)


# ─── 매치 파싱 ───────────────────────────────────────────────────────────────

def fetch_match_html(page, match_id: int) -> str | None:
    url = f"https://www.vlr.gg/{match_id}/?map=all"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(1.5)
        return page.content()
    except Exception as e:
        print(f"  ⚠  매치 {match_id} 로드 실패: {e}")
        return None


def parse_match(html: str, match_id: int, event_name: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    # 팀명
    team_names = [
        el.get_text(strip=True)
        for el in soup.select(".match-header-link-name .wf-title-med")
        if el.get_text(strip=True)
    ]
    team_a = team_names[0] if len(team_names) > 0 else "Team A"
    team_b = team_names[1] if len(team_names) > 1 else "Team B"

    # 스테이지 (breadcrumb 또는 헤더에서)
    stage_el = soup.select_one(".match-header-event-series")
    stage = stage_el.get_text(strip=True) if stage_el else ""

    for section in soup.select("div.vm-stats-game"):
        map_el = section.select_one(".map")
        if not map_el:
            continue
        map_raw = re.sub(r"\s+(pick|ban|remain.*)", "", map_el.get_text(strip=True).lower()).strip()
        map_name = MAP_ALIASES.get(map_raw, map_raw.capitalize())

        # 맵 결과
        score_els = section.select(".team .score")
        if len(score_els) >= 2:
            try:
                sa, sb = int(score_els[0].get_text(strip=True)), int(score_els[1].get_text(strip=True))
                if sa + sb == 0:  # 아직 진행 안 된 맵
                    result_a = result_b = "unknown"
                else:
                    result_a = "win" if sa > sb else "loss"
                    result_b = "loss" if sa > sb else "win"
            except:
                result_a = result_b = "unknown"
        else:
            result_a = result_b = "unknown"

        for t_idx, table in enumerate(section.select("table.wf-table-inset")):
            team   = team_a if t_idx == 0 else team_b
            result = result_a if t_idx == 0 else result_b

            for tr in table.select("tbody tr"):
                player_el = tr.select_one("td.mod-player .text-of") or tr.select_one("td.mod-player span")
                player = player_el.get_text(strip=True) if player_el else ""

                agents = [
                    (img.get("title") or img.get("alt") or "").strip()
                    for img in tr.select("td.mod-agents img")
                    if (img.get("title") or img.get("alt") or "").strip()
                ]
                agent_str = "/".join(agents)

                if not player and not agent_str:
                    continue

                rows.append({
                    "match_id":   match_id,
                    "event":      event_name,
                    "stage":      stage,
                    "map":        map_name,
                    "team":       team,
                    "player":     player,
                    "agent":      agent_str,
                    "result":     result,
                })

    return rows


# ─── 집계 ────────────────────────────────────────────────────────────────────

def summarize(df: pd.DataFrame, event_id: int, event_name: str, year: int) -> pd.DataFrame:
    """에이전트별 픽률·승률 집계 (학습 피처용)"""
    total_maps = df[["match_id", "map"]].drop_duplicates().shape[0]
    if total_maps == 0:
        return pd.DataFrame()

    ag = (
        df.assign(ag=df["agent"].str.split("/")).explode("ag")
          .query("ag != ''")
          .groupby("ag")
          .agg(
              picks=("ag", "count"),
              wins=("result", lambda x: (x == "win").sum()),
          )
          .reset_index()
          .rename(columns={"ag": "agent"})
    )
    ag["pick_rate_pct"] = (ag["picks"] / (total_maps * 2) * 100).round(1)
    ag["win_rate_pct"]  = (ag["wins"] / ag["picks"] * 100).round(1)
    ag["event_id"]      = event_id
    ag["event"]         = event_name
    ag["year"]          = year
    ag["total_maps"]    = total_maps

    return ag.sort_values("picks", ascending=False).reset_index(drop=True)


# ─── 단일 대회 크롤링 ────────────────────────────────────────────────────────

def crawl_tournament(page, tournament: dict,
                     incremental: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    eid   = tournament["event_id"]
    slug  = tournament["slug"]
    name  = tournament["name"]
    year  = tournament["year"]

    print(f"\n{'=' * 60}")
    print(f"[{name}]  event_id={eid}")
    print(f"{'=' * 60}")

    # 1. 매치 ID 수집
    print("  매치 목록 수집 중...", end=" ", flush=True)
    match_ids = fetch_match_ids(page, eid, slug)
    print(f"{len(match_ids)}개")

    if not match_ids:
        print("  → 아직 시작 전 또는 매치 없음 - 건너뜀")
        return pd.DataFrame(), pd.DataFrame()

    # incremental 모드: 기존 CSV에 있는 매치 ID 스킵
    existing_rows: list[dict] = []
    raw_path = OUT_DIR / f"{eid}_{slug[:40]}.csv"
    if incremental and raw_path.exists():
        existing_df = pd.read_csv(raw_path)
        done_ids = set(existing_df["match_id"].unique())
        existing_rows = existing_df.to_dict("records")
        new_ids = [m for m in match_ids if m not in done_ids]
        print(f"  incremental: 기존 {len(done_ids)}매치 스킵, 신규 {len(new_ids)}개 크롤")
        match_ids = new_ids
        if not match_ids:
            print("  → 새 매치 없음 - 건너뜀")
            # 기존 데이터로 summary만 재계산해서 반환
            raw_df = pd.DataFrame(existing_rows)
            return raw_df, summarize(raw_df, eid, name, year)

    # 2. 각 매치 크롤링
    all_rows: list[dict] = list(existing_rows)
    for i, mid in enumerate(match_ids, 1):
        html = fetch_match_html(page, mid)
        if html is None:
            time.sleep(1)
            continue
        rows = parse_match(html, mid, name)
        # 결과 없는 행만 있으면 미완료 경기 - 건너뜀
        valid_rows = [r for r in rows if r["result"] != "unknown"]
        if not valid_rows:
            print(f"  [{i:3d}/{len(match_ids)}] 매치 {mid}  미완료 - 건너뜀")
            time.sleep(0.5)
            continue
        all_rows.extend(valid_rows)
        n_maps = len(set(r["map"] for r in valid_rows))
        print(f"  [{i:3d}/{len(match_ids)}] 매치 {mid}  {n_maps}맵  {len(valid_rows)}행")
        time.sleep(0.8)

    if not all_rows:
        return pd.DataFrame(), pd.DataFrame()

    raw_df = pd.DataFrame(all_rows)
    summary_df = summarize(raw_df, eid, name, year)

    # 3. 저장
    OUT_DIR.mkdir(exist_ok=True)
    raw_path = OUT_DIR / f"{eid}_{slug[:40]}.csv"
    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")

    print(f"\n  저장: {raw_path}")
    print(f"  총 {raw_df[['match_id','map']].drop_duplicates().shape[0]}맵 / {raw_df['agent'].str.split('/').explode().nunique()}에이전트")
    print(f"\n  [픽률 TOP 10]")
    print(summary_df[["agent", "pick_rate_pct", "win_rate_pct", "picks"]].head(10).to_string(index=False))

    return raw_df, summary_df


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event",  type=int, help="특정 이벤트 ID만 실행")
    parser.add_argument("--from",   type=int, dest="from_id", help="해당 ID부터 실행")
    parser.add_argument("--all",         action="store_true", help="전체 대회 수집")
    parser.add_argument("--incremental", action="store_true",
                        help="기존 CSV에 있는 매치는 스킵, 신규/미완료 매치만 크롤")
    args = parser.parse_args()

    if args.event:
        targets = [t for t in TOURNAMENTS if t["event_id"] == args.event]
    elif args.from_id:
        idx = next((i for i, t in enumerate(TOURNAMENTS) if t["event_id"] == args.from_id), 0)
        targets = TOURNAMENTS[idx:]
    elif args.all:
        targets = TOURNAMENTS
    else:
        # 기본값: Stage 1 2026
        targets = [t for t in TOURNAMENTS if t["event_id"] in STAGE1_2026_IDS]

    # event_id 미확정 항목 제외
    targets = [t for t in targets if t["event_id"] is not None]

    print(f"수집 대회: {len(targets)}개")
    for t in targets:
        print(f"  - {t['name']} (event_id={t['event_id']})")

    all_summaries = []

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

        print("\nvlr.gg 로드 중...", end=" ", flush=True)
        page.goto("https://www.vlr.gg", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        print("OK")

        for tournament in targets:
            _, summary = crawl_tournament(page, tournament, incremental=args.incremental)
            if not summary.empty:
                # patch 컨텍스트 추가
                summary["patch_before"] = tournament.get("patch_before")
                summary["patch_after"]  = tournament.get("patch_after")
                all_summaries.append(summary)
            time.sleep(2)

        browser.close()

    if all_summaries:
        combined = pd.concat(all_summaries, ignore_index=True)

        # 기존 vct_summary.csv 보존: 이번에 크롤한 event_id만 교체
        summary_path = Path("vct_summary.csv")
        if summary_path.exists():
            old = pd.read_csv(summary_path)
            crawled_ids = set(combined["event_id"].unique())
            old = old[~old["event_id"].isin(crawled_ids)]
            combined = pd.concat([old, combined], ignore_index=True)

        combined.to_csv("vct_summary.csv", index=False, encoding="utf-8-sig")
        print(f"\n\n전체 집계 저장: vct_summary.csv  ({len(combined)}행)")
        print(f"대회 {combined['event'].nunique()}개 / 에이전트 {combined['agent'].nunique()}개")


if __name__ == "__main__":
    main()
