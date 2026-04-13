"""
crawl_current_act.py
현재 액트(V26A2) 랭크 데이터만 크롤링 → CSV 갱신 → step2 데이터 재빌드

매일 자동 실행 용도:
  python crawl_current_act.py            # 크롤 + 빌드
  python crawl_current_act.py --no-build # 크롤만
  python crawl_current_act.py --reload   # 빌드 후 FastAPI /reload 호출

Windows 작업 스케줄러:
  트리거: 매일 오전 9:00
  작업:   python C:\\valrorant_agent\\crawl_current_act.py --reload
"""

import time
import argparse
import subprocess
import sys
import pandas as pd
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# crawl_all_agents.py에서 공통 상수/함수 재사용
from crawl_all_agents import (
    AGENTS, fetch_agent_act, weighted_wr,
    DIAMOND_PLUS_R,
)

CURRENT_ACT = {"name": "V26A2", "uuid": "9d85c932-4820-c060-09c3-668636d4df1b"}
ALL_CSV     = Path("agent_act_history_all.csv")
API_RELOAD  = "http://localhost:8000/reload"


def crawl_current(page) -> pd.DataFrame:
    """V26A2 전 요원 크롤링 → DataFrame 반환."""
    rows = []
    act  = CURRENT_ACT

    print(f"액트: {act['name']}  |  전 요원 {len(AGENTS)}명  |  다이아+  |  전 지역\n")

    for agent in AGENTS:
        result = fetch_agent_act(page, agent["uuid"], act["uuid"])

        if result is None or "_status" in result or "_error" in result:
            err = result.get("_error") or result.get("_status", "") if result else "no_data"
            rows.append({"act": act["name"], "agent": agent["name"], "note": f"error:{err}"})
            print(f"  {agent['name']:<12} ✗  {err}")
            time.sleep(0.3)
            continue

        m      = result.get("matches", 0) or 0
        total  = result.get("total_matches", 0) or 0
        kills  = result.get("kills", 0) or 0
        deaths = result.get("deaths", 0) or 0
        wr_d   = result.get("wr_by_tier", {})
        m_d    = result.get("m_by_tier", {})

        if not m:
            rows.append({"act": act["name"], "agent": agent["name"], "note": "no_data"})
            print(f"  {agent['name']:<12} —  데이터 없음")
            time.sleep(0.3)
            continue

        pick_rate = round(m / total * 100, 2) if total else None
        win_rate  = weighted_wr(wr_d, m_d)
        kd        = round(kills / deaths, 3) if deaths else None

        # 티어별 승률
        tier_map  = {19: "diamond", 22: "immortal", 25: "immortal2", 27: "radiant"}
        tier_rows = {}
        for r_id, label in tier_map.items():
            tier_rows[f"wr_{label}"]  = wr_d.get(str(r_id)) or wr_d.get(r_id)
            tier_rows[f"m_{label}"]   = m_d.get(str(r_id)) or m_d.get(r_id)

        row = {
            "act":           act["name"],
            "agent":         agent["name"],
            "win_rate":      win_rate,
            "pick_rate_pct": pick_rate,
            "matches":       m,
            "total_matches": total,
            "kd_ratio":      kd,
            "note":          "ok",
            **tier_rows,
        }
        rows.append(row)
        print(f"  {agent['name']:<12} ✓  픽률 {pick_rate:.1f}%  승률 {win_rate:.1f}%")
        time.sleep(0.2)

    return pd.DataFrame(rows)


def update_csv(new_df: pd.DataFrame):
    """agent_act_history_all.csv에서 V26A2 행을 교체."""
    if ALL_CSV.exists():
        old = pd.read_csv(ALL_CSV)
        old = old[old["act"] != CURRENT_ACT["name"]]
        combined = pd.concat([old, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_csv(ALL_CSV, index=False, encoding="utf-8-sig")
    ok = new_df[new_df["note"] == "ok"]
    print(f"\n저장 완료: {ALL_CSV}  ({len(ok)}/{len(new_df)} 성공)")
    return combined


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
    parser.add_argument("--no-build", action="store_true", help="크롤링만, 빌드 생략")
    parser.add_argument("--reload",   action="store_true", help="빌드 후 FastAPI /reload 호출")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  현재 액트 랭크 크롤링 — {CURRENT_ACT['name']}")
    print("=" * 60 + "\n")

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

        page.goto(
            f"https://www.vstats.gg/history?agents={AGENTS[0]['uuid']}",
            wait_until="domcontentloaded", timeout=60000,
        )
        time.sleep(3)

        new_df = crawl_current(page)
        browser.close()

    update_csv(new_df)

    if not args.no_build:
        ok = build_step2()
        if ok and args.reload:
            reload_api()

    print("\n완료.")


if __name__ == "__main__":
    main()
