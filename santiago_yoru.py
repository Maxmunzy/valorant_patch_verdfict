"""
VCT 2026 Masters Santiago 요원 픽 크롤러
- vlr.gg 매치 페이지에서 팀별 · 맵별 · 요원별 픽 수집
- 출력: vct_santiago_2026_YYYYMMDD_HHMM.csv

수집 구조:
  match_id | match_label | stage | team | map | player | agent | result(win/loss)
"""

import time
import re
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

# ─── 대회 정보 ───────────────────────────────────────────
EVENT_ID   = 2760
EVENT_NAME = "Masters Santiago 2026"

# Masters Santiago 2026 전체 매치 목록 (vlr.gg match id)
# 스위스 스테이지 + 플레이오프, 총 24매치
MATCHES = [
    # Swiss Stage Round 1
    {"id": 625788, "label": "GM vs EDG",  "stage": "Swiss R1"},
    {"id": 625791, "label": "XLG vs NRG", "stage": "Swiss R1"},
    {"id": 625790, "label": "G2 vs PRX",  "stage": "Swiss R1"},
    {"id": 625789, "label": "T1 vs TL",   "stage": "Swiss R1"},
    # Swiss Stage Round 2 (1-0)
    {"id": 626529, "label": "PRX vs NRG", "stage": "Swiss R2 (1-0)"},
    {"id": 626530, "label": "GM vs TL",   "stage": "Swiss R2 (1-0)"},
    # Swiss Stage Round 2 (0-1)
    {"id": 626532, "label": "EDG vs T1",  "stage": "Swiss R2 (0-1)"},
    {"id": 626533, "label": "XLG vs G2",  "stage": "Swiss R2 (0-1)"},
    # Swiss Stage Round 3
    {"id": 626534, "label": "G2 vs T1",   "stage": "Swiss R3"},
    {"id": 626535, "label": "NRG vs TL",  "stage": "Swiss R3"},
    # Upper Quarterfinals
    {"id": 626537, "label": "NS vs GM",   "stage": "UQF"},
    {"id": 626538, "label": "AG vs G2",   "stage": "UQF"},
    {"id": 626539, "label": "FURIA vs PRX","stage": "UQF"},
    {"id": 626540, "label": "BBL vs NRG", "stage": "UQF"},
    # Upper Semifinals
    {"id": 626541, "label": "NS vs G2",   "stage": "USF"},
    {"id": 626542, "label": "PRX vs NRG", "stage": "USF"},
    # Lower Round 1
    {"id": 626545, "label": "GM vs AG",   "stage": "LR1"},
    {"id": 626546, "label": "FURIA vs BBL","stage": "LR1"},
    # Lower Round 2
    {"id": 626547, "label": "PRX vs AG",  "stage": "LR2"},
    {"id": 626548, "label": "G2 vs BBL",  "stage": "LR2"},
    # Upper Final
    {"id": 626543, "label": "NS vs NRG",  "stage": "UF"},
    # Lower Round 3
    {"id": 626549, "label": "PRX vs G2",  "stage": "LR3"},
    # Lower Final
    {"id": 626550, "label": "NRG vs PRX", "stage": "LBF"},
    # Grand Final
    {"id": 626544, "label": "NS vs PRX",  "stage": "GF"},
]

BASE_URL = "https://www.vlr.gg/{match_id}/{slug}/?map=all"

# 맵 id → 이름 (vlr.gg 매치 페이지 텍스트 기준)
MAP_ALIASES = {
    "haven":   "Haven",
    "pearl":   "Pearl",
    "split":   "Split",
    "abyss":   "Abyss",
    "breeze":  "Breeze",
    "corrode": "Corrode",
    "bind":    "Bind",
    "ascent":  "Ascent",
    "icebox":  "Icebox",
    "lotus":   "Lotus",
    "sunset":  "Sunset",
    "fracture":"Fracture",
}


def fetch_match_page(page, match_id: int) -> str | None:
    """매치 전체 맵 페이지 HTML 반환 (?map=all)"""
    # slug는 URL 어디든 매치 id만 있으면 리다이렉트됨
    url = f"https://www.vlr.gg/{match_id}/?map=all"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(1.5)
        return page.content()
    except Exception as e:
        print(f"  ⚠ fetch 실패: {e}")
        return None


def parse_match(html: str, match_id: int, label: str, stage: str) -> list[dict]:
    """
    HTML 파싱 → 행 목록 반환
    행 구조: match_id, label, stage, map, team, player, agent, result
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = []

    # 팀명 파싱 (헤더 영역)
    team_names = []
    for el in soup.select(".match-header-link-name .wf-title-med"):
        t = el.get_text(strip=True)
        if t:
            team_names.append(t)
    if len(team_names) < 2:
        # fallback
        for el in soup.select(".match-header-vs .mod-team .mod-2 span"):
            t = el.get_text(strip=True)
            if t:
                team_names.append(t)

    team_a = team_names[0] if len(team_names) > 0 else "Team A"
    team_b = team_names[1] if len(team_names) > 1 else "Team B"

    # 맵별 섹션 파싱
    # vlr.gg 구조: div.vm-stats-game 각각이 맵 하나
    game_sections = soup.select("div.vm-stats-game")

    for section in game_sections:
        # 맵 이름
        map_el = section.select_one(".map")
        if not map_el:
            continue
        map_raw = map_el.get_text(strip=True).lower()
        # "haven pick" → "haven"
        map_raw = re.sub(r"\s+(pick|ban|remain.*)", "", map_raw).strip()
        map_name = MAP_ALIASES.get(map_raw, map_raw.capitalize())

        # 맵 결과 (data-game-id나 score로 파악)
        score_els = section.select(".team .score")
        if len(score_els) >= 2:
            try:
                score_a = int(score_els[0].get_text(strip=True))
                score_b = int(score_els[1].get_text(strip=True))
                result_a = "win" if score_a > score_b else "loss"
                result_b = "loss" if score_a > score_b else "win"
            except:
                result_a = result_b = "unknown"
        else:
            result_a = result_b = "unknown"

        # 플레이어 테이블 (팀A, 팀B 순서로 2개 테이블)
        tables = section.select("table.wf-table-inset")
        for t_idx, table in enumerate(tables):
            team = team_a if t_idx == 0 else team_b
            result = result_a if t_idx == 0 else result_b

            for tr in table.select("tbody tr"):
                # 플레이어명
                player_el = tr.select_one("td.mod-player .text-of")
                if not player_el:
                    player_el = tr.select_one("td.mod-player span")
                player = player_el.get_text(strip=True) if player_el else ""

                # 에이전트명 (img alt 또는 title)
                agent_imgs = tr.select("td.mod-agents img")
                agents = []
                for img in agent_imgs:
                    agent_name = img.get("title") or img.get("alt") or ""
                    agent_name = agent_name.strip()
                    if agent_name:
                        agents.append(agent_name)
                agent_str = "/".join(agents) if agents else ""

                if not player and not agent_str:
                    continue

                rows.append({
                    "match_id":    match_id,
                    "match_label": label,
                    "stage":       stage,
                    "map":         map_name,
                    "team":        team,
                    "player":      player,
                    "agent":       agent_str,
                    "result":      result,
                })

    return rows


def crawl(headless: bool = False) -> pd.DataFrame:
    all_rows = []

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

        print("vlr.gg 로드 중...", end=" ", flush=True)
        page.goto("https://www.vlr.gg", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        print("OK\n")

        print(f"총 {len(MATCHES)}매치 수집 시작\n")
        print(f"{'#':>3}  {'매치':<20} {'스테이지':<15} {'행수':>5}")
        print("─" * 50)

        for i, m in enumerate(MATCHES, 1):
            html = fetch_match_page(page, m["id"])
            if html is None:
                print(f"{i:>3}  {m['label']:<20} {m['stage']:<15}  실패")
                time.sleep(1)
                continue

            rows = parse_match(html, m["id"], m["label"], m["stage"])
            all_rows.extend(rows)
            print(f"{i:>3}  {m['label']:<20} {m['stage']:<15} {len(rows):>5}행")
            time.sleep(0.8)

        browser.close()

    return pd.DataFrame(all_rows)


def print_summary(df: pd.DataFrame):
    ok = df[df["agent"] != ""]
    print("\n" + "=" * 60)
    print(f"총 {len(df)}행 / 에이전트 있음 {len(ok)}행")

    if ok.empty:
        return

    # 요루 픽 현황
    yoru = ok[ok["agent"].str.contains("Yoru", case=False, na=False)]
    print(f"\n[요루 픽] 총 {len(yoru)}번")
    if not yoru.empty:
        print(yoru[["match_label", "stage", "map", "team", "player", "agent", "result"]].to_string(index=False))

    # 에이전트 픽 빈도 (전체)
    print("\n[전체 에이전트 픽 빈도 (맵 단위)]")
    agent_counts = ok["agent"].str.split("/").explode().value_counts()
    print(agent_counts.head(20).to_string())

    print("=" * 60)


def main():
    print("=" * 60)
    print(f"VCT 2026 {EVENT_NAME} 요원 픽 수집")
    print(f"매치: {len(MATCHES)}개  |  팀별·맵별·플레이어별")
    print("=" * 60 + "\n")

    df = crawl(headless=False)

    if df.empty:
        print("⚠  수집 데이터 없음")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"vct_santiago_2026_{ts}.csv"
    df.to_csv(fname, index=False, encoding="utf-8-sig")
    print(f"\n저장: {fname}")
    print_summary(df)


if __name__ == "__main__":
    main()