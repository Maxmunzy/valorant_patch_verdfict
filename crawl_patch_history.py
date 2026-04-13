"""
crawl_patch_history.py
Liquipedia에서 전 요원 패치 히스토리 크롤 → data/patch_history/<Agent>.json 저장
"""

import requests
import json
import re
import time
from bs4 import BeautifulSoup
from pathlib import Path

# ── 설정 ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("data/patch_history")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Liquipedia URL 매핑 (이름이 다른 경우)
AGENT_URL_OVERRIDES = {
    "KAYO": "KAY%2FO",
    "KAY/O": "KAY%2FO",
    "Veto": "Veto",     # 신규 요원, 없을 수 있음
    "Miks": "Miks",
}

AGENTS = [
    "Astra", "Breach", "Brimstone", "Chamber", "Clove",
    "Cypher", "Deadlock", "Fade", "Gekko", "Harbor",
    "Iso", "Jett", "KAYO", "Killjoy", "Miks",
    "Neon", "Omen", "Phoenix", "Raze", "Reyna",
    "Sage", "Skye", "Sova", "Tejo", "Veto",
    "Viper", "Vyse", "Waylay", "Yoru",
]

# ── 수치 변경 파싱 패턴 ────────────────────────────────────────────────────
# "4.5s >>> 2.5s" / "7 >>> 8" / "100 >>> 200" etc.
RE_ARROW = re.compile(
    r'([\d.]+)\s*(?:s|seconds?)?\s*>>>\s*([\d.]+)\s*(?:s|seconds?)?',
    re.IGNORECASE
)
RE_ARROW_LABELED = re.compile(
    r'([\w\s\(\)]+?)\s+([\d.]+)\s*([a-zA-Z%]*)\s*>>>\s*([\d.]+)\s*([a-zA-Z%]*)'
)

# 스킬 슬롯 키워드
ABILITY_MAP = {
    "cloudburst": "C", "updraft": "Q", "tailwind": "E", "blade storm": "X",
    "bladestorm": "X", "drift": "passive",
    # Astra
    "nova pulse": "Q", "nebula": "E", "astral form": "X", "cosmic divide": "X",
    "gravity well": "C",
    # Breach
    "flashpoint": "Q", "fault line": "E", "aftershock": "C", "rolling thunder": "X",
    # Brimstone
    "stim beacon": "Q", "incendiary": "C", "sky smoke": "E", "orbital strike": "X",
    # Chamber
    "headhunter": "Q", "rendezvous": "E", "trademark": "C", "tour de force": "X",
    # Clove
    "meddle": "C", "ruse": "Q", "pick-me-up": "E", "not dead yet": "X",
    # Cypher
    "cyber cage": "C", "spycam": "E", "trapwire": "Q", "neural theft": "X",
    # Deadlock
    "sonic sensor": "C", "barrier mesh": "E", "gravnet": "Q", "annihilation": "X",
    # Fade
    "prowler": "C", "seize": "E", "haunt": "Q", "nightfall": "X",
    # Gekko
    "wingman": "Q", "dizzy": "C", "thrash": "X", "mosh pit": "E",
    # Harbor
    "cascade": "C", "cove": "Q", "high tide": "E", "reckoning": "X",
    # Iso
    "contingency": "C", "undercut": "Q", "double tap": "E", "kill contract": "X",
    # KAYO
    "flash/drive": "Q", "zero/point": "C", "frag/ment": "E", "null/cmd": "X",
    # Killjoy
    "nanoswarm": "C", "alarmbot": "Q", "turret": "E", "lockdown": "X",
    # Neon
    "fast lane": "C", "relay bolt": "Q", "high gear": "E", "overdrive": "X",
    # Omen
    "paranoia": "Q", "dark cover": "E", "shrouded step": "C", "from the shadows": "X",
    # Phoenix
    "curveball": "Q", "blaze": "E", "hot hands": "C", "run it back": "X",
    # Raze
    "blast pack": "C", "boom bot": "Q", "paint shells": "E", "showstopper": "X",
    # Reyna
    "leer": "C", "devour": "Q", "dismiss": "E", "empress": "X",
    # Sage
    "slow orb": "C", "healing orb": "Q", "barrier orb": "E", "resurrection": "X",
    # Skye
    "trailblazer": "Q", "guiding light": "E", "regrowth": "C", "seekers": "X",
    # Sova
    "shock dart": "Q", "recon bolt": "E", "owl drone": "C", "hunter's fury": "X",
    # Tejo
    "stealth drone": "C", "guided salvo": "Q", "special delivery": "E", "armageddon": "X",
    # Viper
    "snake bite": "C", "poison cloud": "Q", "toxic screen": "E", "viper's pit": "X",
    # Vyse
    "shear": "C", "arc rose": "Q", "razorvine": "E", "steel garden": "X",
    # Yoru
    "blindside": "Q", "gatecrash": "E", "fakeout": "C", "dimensional drift": "X",
}


def fetch_agent_page(agent_name: str) -> str | None:
    url_name = AGENT_URL_OVERRIDES.get(agent_name, agent_name.replace(" ", "_"))
    url = f"https://liquipedia.net/valorant/{url_name}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.text
        print(f"  [{agent_name}] HTTP {r.status_code}")
        return None
    except Exception as e:
        print(f"  [{agent_name}] Error: {e}")
        return None


def parse_version_table(html: str, agent_name: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # Version History 섹션
    vh_h2 = soup.find("h2", {"id": "Version_History"})
    if not vh_h2:
        return {"agent": agent_name, "patch_history": [], "error": "no_version_history"}

    parent_div = vh_h2.parent
    version_table = parent_div.find_next_sibling("table")
    if not version_table:
        return {"agent": agent_name, "patch_history": [], "error": "no_version_table"}

    # 현재 스킬 스탯 (Abilities 섹션에서)
    initial_stats = parse_current_stats(soup, agent_name)

    # 패치 히스토리 파싱
    rows = version_table.find_all("tr")
    patch_history = []
    current_patch = None

    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        text = cells[0].get_text(separator=" ", strip=True)

        # 패치 버전 행 (숫자만 있는 경우)
        if re.match(r"^\d+\.\d+$", text):
            current_patch = text
            continue

        # 헤더 행 skip
        if text.lower() in ("version", "balance changes"):
            continue

        # 변경 내용 행
        if current_patch and text:
            changes = parse_change_text(text, agent_name)
            if changes:
                patch_history.append({
                    "patch": current_patch,
                    "raw_text": text[:500],
                    "changes": changes,
                })
            current_patch = None

    return {
        "agent": agent_name,
        "source": "liquipedia.net/valorant",
        "current_stats": initial_stats,
        "patch_history": patch_history,
    }


def parse_current_stats(soup: BeautifulSoup, agent_name: str) -> dict:
    """현재 스킬 스탯 파싱 (Abilities 섹션 테이블에서)"""
    stats = {}
    tables = soup.find_all("table")
    for table in tables:
        text = table.get_text(separator="\n", strip=True)
        if "Ability:" not in text and "Cost:" not in text:
            continue
        # 스탯 추출
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Cost, Duration, Charges, HP, Damage 등 추출
            m = re.search(r"(Cost|Duration|Charges|HP|Damage|Cooldown|Range|Equip)\s*[:\s]+([0-9.,]+)\s*([a-zA-Z%]*)", line, re.IGNORECASE)
            if m:
                key = m.group(1).lower()
                val = m.group(2)
                unit = m.group(3)
                stats[key] = {"value": float(val.replace(",", "")), "unit": unit}
    return stats


def identify_ability(text_lower: str) -> str | None:
    """텍스트에서 스킬 슬롯 식별"""
    for keyword, slot in ABILITY_MAP.items():
        if keyword in text_lower:
            return slot
    # 일반 패턴: (Q), (E), (C), (X)
    m = re.search(r'\(([QECX])\)', text_lower, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def parse_change_text(text: str, agent_name: str) -> list:
    """패치 텍스트에서 구조화된 변경 데이터 추출"""
    changes = []
    text_lower = text.lower()

    # >>> 패턴으로 수치 변경 찾기
    for m in RE_ARROW_LABELED.finditer(text):
        label = m.group(1).strip()
        before_val = float(m.group(2))
        before_unit = m.group(3)
        after_val = float(m.group(4))
        after_unit = m.group(5) or before_unit

        ability = identify_ability(label.lower()) or identify_ability(text_lower)
        direction = "nerf" if after_val < before_val else ("buff" if after_val > before_val else "neutral")

        # 스탯 이름 추론
        stat = infer_stat_name(label)

        changes.append({
            "ability_slot": ability,
            "ability_hint": label.strip()[:60],
            "stat": stat,
            "before": before_val,
            "before_unit": before_unit or "?",
            "after": after_val,
            "after_unit": after_unit or "?",
            "change_type": "stat_change",
            "direction": direction,
        })

    # 수치 변경이 없는 경우 — 메커닉/QoL/버그픽스 등
    if not changes:
        direction = classify_text_direction(text_lower)
        ability = identify_ability(text_lower)
        changes.append({
            "ability_slot": ability,
            "stat": "mechanic",
            "before": None,
            "after": None,
            "change_type": classify_change_type(text_lower),
            "direction": direction,
            "description": text[:200],
        })

    return changes


def infer_stat_name(label: str) -> str:
    label_lower = label.lower()
    if any(w in label_lower for w in ["duration", "time", "window"]):
        return "duration"
    if "cost" in label_lower or "credit" in label_lower:
        return "cost"
    if "charge" in label_lower:
        return "charges"
    if "damage" in label_lower:
        return "damage"
    if any(w in label_lower for w in ["health", "hp"]):
        return "health"
    if "cooldown" in label_lower:
        return "cooldown"
    if "range" in label_lower or "radius" in label_lower:
        return "range"
    if "point" in label_lower or "ult" in label_lower:
        return "ult_cost"
    if any(w in label_lower for w in ["speed", "velocity"]):
        return "speed"
    if "delay" in label_lower:
        return "delay"
    if "multiplier" in label_lower or "multi" in label_lower:
        return "multiplier"
    return "other"


def classify_text_direction(text_lower: str) -> str:
    nerf_words = ["decreased", "reduced", "increase cooldown", "nerfed", "slower",
                  "no longer", "removed", "lost", "cost increased", "points increased"]
    buff_words = ["increased damage", "increased duration", "increased range", "buffed",
                  "faster", "added", "gain", "cost decreased", "points decreased",
                  "improved", "enhanced"]
    bug_words = ["fixed", "bug", "exploit"]

    if any(w in text_lower for w in bug_words):
        return "bugfix"
    if any(w in text_lower for w in nerf_words):
        return "nerf"
    if any(w in text_lower for w in buff_words):
        return "buff"
    return "neutral"


def classify_change_type(text_lower: str) -> str:
    if any(w in text_lower for w in ["fixed", "bug"]):
        return "bugfix"
    if any(w in text_lower for w in ["rework", "redesign", "overhaul"]):
        return "rework"
    if any(w in text_lower for w in ["no longer", "removed", "added", "new "]):
        return "mechanic_change"
    return "stat_change"


def crawl_all_agents(agents: list[str]) -> None:
    total = len(agents)
    for i, agent in enumerate(agents, 1):
        out_path = OUTPUT_DIR / f"{agent}.json"
        if out_path.exists():
            print(f"[{i}/{total}] {agent} — 이미 존재, skip")
            continue

        print(f"[{i}/{total}] {agent} 크롤 중...", end=" ", flush=True)
        html = fetch_agent_page(agent)
        if html is None:
            print("FAILED")
            continue

        data = parse_version_table(html, agent)
        n_patches = len(data.get("patch_history", []))
        n_changes = sum(len(p["changes"]) for p in data.get("patch_history", []))

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"OK — {n_patches} patches, {n_changes} changes")
        time.sleep(1.5)  # rate limit


if __name__ == "__main__":
    import sys
    targets = sys.argv[1:] if len(sys.argv) > 1 else AGENTS
    print(f"크롤 대상: {len(targets)}개 요원")
    crawl_all_agents(targets)
    print("\n완료!")
