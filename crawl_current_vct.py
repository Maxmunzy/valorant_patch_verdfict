"""
crawl_current_vct.py
현재 액트(V26A2) 매핑 대회만 재크롤 → vct_summary.csv 갱신

매일 자동 실행 용도:
  python crawl_current_vct.py            # 크롤 + 빌드
  python crawl_current_vct.py --no-build # 크롤만
  python crawl_current_vct.py --reload   # 빌드 후 FastAPI /reload 호출

새 대회 추가 시: CURRENT_TOURNAMENTS 리스트에 추가하면 됨
"""

import time
import argparse
import subprocess
import sys
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

from crawl_vct import (
    crawl_tournament, OUT_DIR,
    fetch_match_ids, fetch_match_html, parse_match,
)

VCT_SUMMARY = Path("vct_summary.csv")
API_RELOAD  = "http://localhost:8000/reload"

# V26A2에 매핑된 현재 대회 목록
# 대회가 완전히 끝나면 이 리스트에서 제거해도 되지만
# 매일 돌려도 결과가 같으니 그냥 두면 됨
#
# 12.06 패치(웨이레이 추가) → VCT 적용일: 2026-04-24
# 4/24 이전 경기 = 12.05 기준, 4/24 이후 경기 = 12.06 기준
# patch_after는 현재 대회의 "기준 패치"로, 4/24 이후 12.06으로 변경 필요
CURRENT_TOURNAMENTS = [
    {
        "event_id":    2863,
        "slug":        "vct-2026-emea-stage-1",
        "name":        "VCT EMEA Stage 1 2026",
        "year":        2026,
        "patch_after": "12.05",  # 4/24부터 "12.06"으로 변경
    },
    {
        "event_id":    2775,
        "slug":        "vct-2026-pacific-stage-1",
        "name":        "VCT Pacific Stage 1 2026",
        "year":        2026,
        "patch_after": "12.05",  # 4/24부터 "12.06"으로 변경
    },
    {
        "event_id":    2860,
        "slug":        "vct-2026-americas-stage-1",
        "name":        "VCT Americas Stage 1 2026",
        "year":        2026,
        "patch_after": "12.05",  # 4/24부터 "12.06"으로 변경
    },
    {
        "event_id":    2864,
        "slug":        "vct-2026-cn-stage-1",
        "name":        "VCT CN Stage 1 2026",
        "year":        2026,
        "patch_after": "12.05",  # 4/24부터 "12.06"으로 변경
    },
]


def update_summary(new_summaries: list[pd.DataFrame]):
    """vct_summary.csv에서 현재 대회 행을 교체."""
    current_names = {t["name"] for t in CURRENT_TOURNAMENTS}

    if VCT_SUMMARY.exists():
        old = pd.read_csv(VCT_SUMMARY)
        old = old[~old["event"].isin(current_names)]
    else:
        old = pd.DataFrame()

    new_dfs = [df for df in new_summaries if not df.empty]
    if not new_dfs:
        print("새로 수집된 데이터 없음 — vct_summary.csv 변경 안 함")
        return

    combined = pd.concat([old] + new_dfs, ignore_index=True)
    combined.to_csv(VCT_SUMMARY, index=False, encoding="utf-8-sig")

    total_new = sum(len(df) for df in new_dfs)
    print(f"\n저장 완료: {VCT_SUMMARY}  (기존 {len(old)}행 + 신규 {total_new}행 = {len(combined)}행)")


def build_step2():
    print("\n─── build_step2_data.py 실행 ───")
    result = subprocess.run(
        [sys.executable, "build_step2_data.py"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode == 0:
        print("빌드 완료")
    else:
        print("빌드 실패:")
        print(result.stderr[-500:])
    return result.returncode == 0


def reload_api():
    try:
        import urllib.request, json
        req = urllib.request.Request(
            API_RELOAD,
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read())
            print(f"API 재로드: {body.get('message', 'OK')}")
    except Exception as e:
        print(f"API 재로드 실패 (서버 꺼져 있으면 무시): {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-build", action="store_true")
    parser.add_argument("--reload",   action="store_true")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  현재 VCT 대회 크롤링 — {len(CURRENT_TOURNAMENTS)}개")
    for t in CURRENT_TOURNAMENTS:
        print(f"    · {t['name']} (event_id={t['event_id']})")
    print("=" * 60)

    new_summaries = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        Stealth().apply_stealth_sync(page)

        page.goto("https://www.vlr.gg", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        for tournament in CURRENT_TOURNAMENTS:
            try:
                _, summary_df = crawl_tournament(page, tournament)
                new_summaries.append(summary_df)
            except Exception as e:
                print(f"  ✗ {tournament['name']}: {e}")

        browser.close()

    update_summary(new_summaries)

    if not args.no_build:
        ok = build_step2()
        if ok and args.reload:
            reload_api()

    print("\n완료.")


if __name__ == "__main__":
    main()
