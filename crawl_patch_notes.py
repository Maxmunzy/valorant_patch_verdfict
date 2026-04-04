"""
Valorant 패치 노트 크롤러
playvalorant.com/en-us/news/game-updates/valorant-patch-notes-X-XX/

수집 대상:
  - 에이전트별 변경 내용 (skill_key, change_type, value_before/after)
  - 개발자 코멘트 (change_reason) — trigger_type 분류의 입력값

실행:
  python crawl_patch_notes.py              # 전체 패치 수집
  python crawl_patch_notes.py --patch 12.05  # 특정 패치만

출력:
  patch_notes_raw.csv    # 전 패치 원본 변경 내용
"""

import re
import time
import argparse
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup


# ─── 패치 목록 ───────────────────────────────────────────────────────────────
# playvalorant.com에 존재하는 모든 패치 노트 (HEAD 요청으로 확인된 106개)

PATCHES = [
    # ── E2 ───────────────────────────────────────────────────────────────────
    {"version": "2.01",  "act": "E2A1",  "url": "valorant-patch-notes-2-01"},
    {"version": "2.02",  "act": "E2A1",  "url": "valorant-patch-notes-2-02"},
    {"version": "2.03",  "act": "E2A1",  "url": "valorant-patch-notes-2-03"},
    {"version": "2.04",  "act": "E2A2",  "url": "valorant-patch-notes-2-04"},
    {"version": "2.05",  "act": "E2A2",  "url": "valorant-patch-notes-2-05"},
    {"version": "2.06",  "act": "E2A2",  "url": "valorant-patch-notes-2-06"},
    {"version": "2.07",  "act": "E2A3",  "url": "valorant-patch-notes-2-07"},
    {"version": "2.08",  "act": "E2A3",  "url": "valorant-patch-notes-2-08"},
    {"version": "2.09",  "act": "E2A3",  "url": "valorant-patch-notes-2-09"},
    {"version": "2.11",  "act": "E2A3",  "url": "valorant-patch-notes-2-11"},
    # ── E3 ───────────────────────────────────────────────────────────────────
    {"version": "3.01",  "act": "E3A1",  "url": "valorant-patch-notes-3-01"},
    {"version": "3.02",  "act": "E3A1",  "url": "valorant-patch-notes-3-02"},
    {"version": "3.03",  "act": "E3A1",  "url": "valorant-patch-notes-3-03"},
    {"version": "3.04",  "act": "E3A1",  "url": "valorant-patch-notes-3-04"},
    {"version": "3.05",  "act": "E3A2",  "url": "valorant-patch-notes-3-05"},
    {"version": "3.06",  "act": "E3A2",  "url": "valorant-patch-notes-3-06"},
    {"version": "3.07",  "act": "E3A2",  "url": "valorant-patch-notes-3-07"},
    {"version": "3.08",  "act": "E3A2",  "url": "valorant-patch-notes-3-08"},
    {"version": "3.09",  "act": "E3A3",  "url": "valorant-patch-notes-3-09"},
    {"version": "3.10",  "act": "E3A3",  "url": "valorant-patch-notes-3-10"},
    {"version": "3.12",  "act": "E3A3",  "url": "valorant-patch-notes-3-12"},
    # ── E4 ───────────────────────────────────────────────────────────────────
    {"version": "4.01",  "act": "E4A1",  "url": "valorant-patch-notes-4-01"},
    {"version": "4.02",  "act": "E4A1",  "url": "valorant-patch-notes-4-02"},
    {"version": "4.03",  "act": "E4A1",  "url": "valorant-patch-notes-4-03"},
    {"version": "4.04",  "act": "E4A2",  "url": "valorant-patch-notes-4-04"},
    {"version": "4.05",  "act": "E4A2",  "url": "valorant-patch-notes-4-05"},
    {"version": "4.07",  "act": "E4A2",  "url": "valorant-patch-notes-4-07"},
    {"version": "4.08",  "act": "E4A3",  "url": "valorant-patch-notes-4-08"},
    {"version": "4.09",  "act": "E4A3",  "url": "valorant-patch-notes-4-09"},
    {"version": "4.10",  "act": "E4A3",  "url": "valorant-patch-notes-4-10"},
    {"version": "4.11",  "act": "E4A3",  "url": "valorant-patch-notes-4-11"},
    # ── E5 ───────────────────────────────────────────────────────────────────
    {"version": "5.01",  "act": "E5A1",  "url": "valorant-patch-notes-5-01"},
    {"version": "5.03",  "act": "E5A1",  "url": "valorant-patch-notes-5-03"},
    {"version": "5.04",  "act": "E5A1",  "url": "valorant-patch-notes-5-04"},
    {"version": "5.05",  "act": "E5A2",  "url": "valorant-patch-notes-5-05"},
    {"version": "5.06",  "act": "E5A2",  "url": "valorant-patch-notes-5-06"},
    {"version": "5.07",  "act": "E5A2",  "url": "valorant-patch-notes-5-07"},
    {"version": "5.08",  "act": "E5A2",  "url": "valorant-patch-notes-5-08"},
    {"version": "5.09",  "act": "E5A2",  "url": "valorant-patch-notes-5-09"},
    {"version": "5.10",  "act": "E5A2",  "url": "valorant-patch-notes-5-10"},
    # ── E6 ───────────────────────────────────────────────────────────────────
    {"version": "5.12",  "act": "E6A1",  "url": "valorant-patch-notes-5-12"},
    {"version": "6.01",  "act": "E6A1",  "url": "valorant-patch-notes-6-01"},
    {"version": "6.02",  "act": "E6A1",  "url": "valorant-patch-notes-6-02"},
    {"version": "6.03",  "act": "E6A1",  "url": "valorant-patch-notes-6-03"},
    {"version": "6.04",  "act": "E6A2",  "url": "valorant-patch-notes-6-04"},
    {"version": "6.05",  "act": "E6A2",  "url": "valorant-patch-notes-6-05"},
    {"version": "6.06",  "act": "E6A3",  "url": "valorant-patch-notes-6-06"},
    {"version": "6.07",  "act": "E6A3",  "url": "valorant-patch-notes-6-07"},
    # ── E7 ───────────────────────────────────────────────────────────────────
    {"version": "6.08",  "act": "E7A2",  "url": "valorant-patch-notes-6-08"},
    {"version": "6.10",  "act": "E7A2",  "url": "valorant-patch-notes-6-10"},
    {"version": "6.11",  "act": "E7A3",  "url": "valorant-patch-notes-6-11"},
    {"version": "7.01",  "act": "E7A3",  "url": "valorant-patch-notes-7-01"},
    {"version": "7.02",  "act": "E7A3",  "url": "valorant-patch-notes-7-02"},
    {"version": "7.03",  "act": "E7A3",  "url": "valorant-patch-notes-7-03"},
    # ── E8 ───────────────────────────────────────────────────────────────────
    {"version": "7.04",  "act": "E8A1",  "url": "valorant-patch-notes-7-04"},
    {"version": "7.05",  "act": "E8A1",  "url": "valorant-patch-notes-7-05"},
    {"version": "7.06",  "act": "E8A1",  "url": "valorant-patch-notes-7-06"},
    {"version": "7.07",  "act": "E8A1",  "url": "valorant-patch-notes-7-07"},
    {"version": "7.08",  "act": "E8A1",  "url": "valorant-patch-notes-7-08"},
    {"version": "7.09",  "act": "E8A2",  "url": "valorant-patch-notes-7-09"},
    {"version": "7.10",  "act": "E8A2",  "url": "valorant-patch-notes-7-10"},
    {"version": "7.12",  "act": "E8A3",  "url": "valorant-patch-notes-7-12"},
    # ── E9 ───────────────────────────────────────────────────────────────────
    {"version": "8.01",  "act": "E8A3",  "url": "valorant-patch-notes-8-01"},
    {"version": "8.02",  "act": "E9A1",  "url": "valorant-patch-notes-8-02"},
    {"version": "8.03",  "act": "E9A1",  "url": "valorant-patch-notes-8-03"},
    {"version": "8.04",  "act": "E9A1",  "url": "valorant-patch-notes-8-04"},
    {"version": "8.05",  "act": "E9A1",  "url": "valorant-patch-notes-8-05"},
    {"version": "8.07",  "act": "E9A2",  "url": "valorant-patch-notes-8-07"},
    {"version": "8.08",  "act": "E9A2",  "url": "valorant-patch-notes-8-08"},
    {"version": "8.09",  "act": "E9A2",  "url": "valorant-patch-notes-8-09"},
    {"version": "8.10",  "act": "E9A2",  "url": "valorant-patch-notes-8-10"},
    {"version": "8.11",  "act": "E9A3",  "url": "valorant-patch-notes-811"},
    # ── E10 ──────────────────────────────────────────────────────────────────
    {"version": "9.03",  "act": "E10A1", "url": "valorant-patch-notes-9-03"},
    {"version": "9.04",  "act": "E10A1", "url": "valorant-patch-notes-9-04"},
    {"version": "9.05",  "act": "E10A1", "url": "valorant-patch-notes-9-05"},
    {"version": "9.07",  "act": "E10A1", "url": "valorant-patch-notes-9-07"},
    {"version": "9.08",  "act": "E10A2", "url": "valorant-patch-notes-9-08"},
    {"version": "9.09",  "act": "E10A2", "url": "valorant-patch-notes-9-09"},
    {"version": "9.10",  "act": "E10A2", "url": "valorant-patch-notes-9-10"},
    {"version": "9.11",  "act": "E10A3", "url": "valorant-patch-notes-9-11"},
    # ── E11 ──────────────────────────────────────────────────────────────────
    {"version": "10.01", "act": "E11A1", "url": "valorant-patch-notes-10-01"},
    {"version": "10.02", "act": "E11A1", "url": "valorant-patch-notes-10-02"},
    {"version": "10.03", "act": "E11A1", "url": "valorant-patch-notes-10-03"},
    {"version": "10.04", "act": "E11A1", "url": "valorant-patch-notes-10-04"},
    {"version": "10.05", "act": "E11A1", "url": "valorant-patch-notes-10-05"},
    {"version": "10.06", "act": "E11A1", "url": "valorant-patch-notes-10-06"},
    {"version": "10.08", "act": "E11A2", "url": "valorant-patch-notes-10-08"},
    {"version": "10.09", "act": "E11A2", "url": "valorant-patch-notes-10-09"},
    {"version": "10.10", "act": "E11A2", "url": "valorant-patch-notes-10-10"},
    {"version": "10.11", "act": "E11A2", "url": "valorant-patch-notes-10-11"},
    # ── E12 / V26 ────────────────────────────────────────────────────────────
    {"version": "11.01", "act": "E11A3", "url": "valorant-patch-notes-11-01"},
    {"version": "11.02", "act": "E11A3", "url": "valorant-patch-notes-11-02"},
    {"version": "11.04", "act": "E11A3", "url": "valorant-patch-notes-11-04"},
    {"version": "11.05", "act": "E11A3", "url": "valorant-patch-notes-11-05"},
    {"version": "11.06", "act": "E12A1", "url": "valorant-patch-notes-11-06"},
    {"version": "11.07", "act": "E12A1", "url": "valorant-patch-notes-11-07"},
    {"version": "11.08", "act": "E12A1", "url": "valorant-patch-notes-11-08"},
    {"version": "11.09", "act": "E12A1", "url": "valorant-patch-notes-11-09"},
    {"version": "11.10", "act": "E12A1", "url": "valorant-patch-notes-11-10"},
    {"version": "11.11", "act": "E12A1", "url": "valorant-patch-notes-11-11"},
    {"version": "12.01", "act": "V26A2", "url": "valorant-patch-notes-12-01"},
    {"version": "12.02", "act": "V26A2", "url": "valorant-patch-notes-12-02"},
    {"version": "12.03", "act": "V26A2", "url": "valorant-patch-notes-12-03"},
    {"version": "12.04", "act": "V26A2", "url": "valorant-patch-notes-12-04"},
    {"version": "12.05", "act": "V26A2", "url": "valorant-patch-notes-12-05"},
    {"version": "12.06", "act": "V26A2", "url": "valorant-patch-notes-12-06"},
]

BASE_URL = "https://playvalorant.com/en-us/news/game-updates/{url}/"

# change_type 키워드 매핑 (description 텍스트에서 추론)
CHANGE_TYPE_KEYWORDS = {
    "damage":    ["damage", "dmg"],
    "duration":  ["duration", "time", "seconds", "sec"],
    "charges":   ["charge", "charges", "equip"],
    "range":     ["range", "radius", "distance", "width"],
    "cooldown":  ["cooldown", "recharge", "recovery"],
    "cost":      ["cost", "credits", "price"],
    "mechanic":  ["now requires", "changed to", "instead of",
                  "no longer", "now allows", "replaced", "reworked"],
    "rework":    ["rework", "redesign", "overhauled", "completely changed"],
    "bugfix_nerf":  ["bug", "exploit", "unintended", "fix"],
    "bugfix_buff":  ["bug", "exploit", "unintended", "fix"],
}

# 에이전트명 목록 (패치 노트 섹션 식별용)
AGENTS = [
    "Astra", "Breach", "Brimstone", "Chamber", "Clove", "Cypher",
    "Deadlock", "Fade", "Gekko", "Harbor", "Iso", "Jett", "KAYO",
    "Killjoy", "Neon", "Omen", "Phoenix", "Raze", "Reyna", "Sage",
    "Skye", "Sova", "Tejo", "Viper", "Vyse", "Waylay", "Yoru",
]

# 공식 사이트에서 표기가 다른 요원 별칭 (소문자 → 정규 이름)
AGENT_ALIASES = {
    "kay/o": "KAYO",
    "kayo":  "KAYO",
}

def _resolve_agent(text_lower: str):
    """텍스트에서 요원 이름 매칭 (별칭 포함)"""
    for a in AGENTS:
        if a.lower() in text_lower:
            return a
    for alias, canonical in AGENT_ALIASES.items():
        if alias in text_lower:
            return canonical
    return None

# 스킬 키워드 → skill_key 매핑
SKILL_KEY_MAP = {
    # Yoru
    "blindside":          ("Q", "Blindside"),
    "gatecrash":          ("E", "Gatecrash"),
    "fakeout":            ("C", "Fakeout"),
    "dimensional drift":  ("X", "Dimensional Drift"),
    # Jett
    "tailwind":           ("E", "Tailwind"),
    "cloudburst":         ("C", "Cloudburst"),
    "updraft":            ("Q", "Updraft"),
    "blade storm":        ("X", "Bladestorm"),
    # Chamber
    "trademark":          ("C", "Trademark"),
    "headhunter":         ("Q", "Headhunter"),
    "rendezvous":         ("E", "Rendezvous"),
    "tour de force":      ("X", "Tour de Force"),
    # Neon
    "fast lane":          ("C", "Fast Lane"),
    "relay bolt":         ("Q", "Relay Bolt"),
    "high gear":          ("E", "High Gear"),
    "overdrive":          ("X", "Overdrive"),
    # Raze
    "boom bot":           ("C", "Boom Bot"),
    "blast pack":         ("Q", "Blast Pack"),
    "paint shells":       ("E", "Paint Shells"),
    "showstopper":        ("X", "Showstopper"),
    # Reyna
    "leer":               ("C", "Leer"),
    "devour":             ("Q", "Devour"),
    "dismiss":            ("E", "Dismiss"),
    "empress":            ("X", "Empress"),
    # Iso
    "undercut":           ("C", "Undercut"),
    "double tap":         ("Q", "Double Tap"),
    "contingency":        ("E", "Contingency"),
    "kill contract":      ("X", "Kill Contract"),
    # Clove
    "pick-me-up":         ("C", "Pick-Me-Up"),
    "meddle":             ("Q", "Meddle"),
    "ruse":               ("E", "Ruse"),
    "not dead yet":       ("X", "Not Dead Yet"),
    # Vyse
    "arc rose":           ("C", "Arc Rose"),
    "shear":              ("Q", "Shear"),
    "razorvine":          ("E", "Razorvine"),
    "steel garden":       ("X", "Steel Garden"),
    # Gekko
    "mosh pit":           ("C", "Mosh Pit"),
    "dizzy":              ("Q", "Dizzy"),
    "wingman":            ("E", "Wingman"),
    "thrash":             ("X", "Thrash"),
    # Skye
    "regrowth":           ("C", "Regrowth"),
    "guiding light":      ("Q", "Guiding Light"),
    "trailblazer":        ("E", "Trailblazer"),
    "seekers":            ("X", "Seekers"),
    # Astra
    "nebula":             ("C", "Nebula"),
    "nova pulse":         ("Q", "Nova Pulse"),
    "gravity well":       ("E", "Gravity Well"),
    "cosmic divide":      ("X", "Cosmic Divide"),
    # Viper
    "snake bite":         ("C", "Snake Bite"),
    "poison cloud":       ("Q", "Poison Cloud"),
    "toxic screen":       ("E", "Toxic Screen"),
    "viper's pit":        ("X", "Viper's Pit"),
    # Cypher
    "cyber cage":         ("C", "Cyber Cage"),
    "trapwire":           ("Q", "Trapwire"),
    "spycam":             ("E", "Spycam"),
    "neural theft":       ("X", "Neural Theft"),
    # Killjoy
    "nanoswarm":          ("C", "Nanoswarm"),
    "alarm bot":          ("Q", "Alarm Bot"),
    "turret":             ("E", "Turret"),
    "lockdown":           ("X", "Lockdown"),
    # Sova
    "shock bolt":         ("C", "Shock Bolt"),
    "owl drone":          ("Q", "Owl Drone"),
    "recon bolt":         ("E", "Recon Bolt"),
    "hunter's fury":      ("X", "Hunter's Fury"),
    # Waylay
    "saturate":           ("C", "Saturate"),
    "waveform":           ("E", "Waveform"),
    # 일반 패턴
    "c ability":          ("C", ""),
    "q ability":          ("Q", ""),
    "e ability":          ("E", ""),
    "ultimate":           ("X", ""),
}


# ─── 파싱 ────────────────────────────────────────────────────────────────────

def infer_change_type(text: str) -> str:
    text_lower = text.lower()
    for ctype, keywords in CHANGE_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return ctype
    return "other"


def extract_numbers(text: str) -> tuple[str | None, str | None]:
    """'30 >>> 15' 또는 '30s → 15s' 같은 패턴에서 전후 수치 추출"""
    # 여러 구분자 패턴
    pattern = r"([\d.]+)\s*(?:>>>|→|->|to)\s*([\d.]+)"
    m = re.search(pattern, text)
    if m:
        return m.group(1), m.group(2)
    return None, None


def infer_direction(text: str, section_header: str) -> str:
    text_lower = (text + " " + section_header).lower()
    buff_words  = ["increase", "buff", "improved", "added", "new", "now can", "reduced cooldown"]
    nerf_words  = ["decrease", "nerf", "reduced", "removed", "no longer", "increased cooldown"]
    if any(w in text_lower for w in buff_words):
        return "buff"
    if any(w in text_lower for w in nerf_words):
        return "nerf"
    return "neutral"


def _make_row(version, act, agent, text, skill_key, skill_name, reason_list):
    val_before, val_after = extract_numbers(text)
    unit = ""
    if "second" in text.lower(): unit = "sec"
    elif "%" in text: unit = "%"
    elif "hp" in text.lower(): unit = "hp"
    return {
        "patch": version, "act": act, "agent": agent,
        "direction": infer_direction(text, agent),
        "skill_key": skill_key, "skill_name": skill_name,
        "change_type": infer_change_type(text),
        "description": text[:300],
        "value_before": val_before, "value_after": val_after, "unit": unit,
        "change_reason": " | ".join(reason_list[-2:]),
        "trigger_type": "",
        "has_bugfix": 1 if "bug" in text.lower() else 0,
    }


def _infer_skill(text):
    for kw, (sk, sn) in SKILL_KEY_MAP.items():
        if kw in text.lower():
            return sk, sn
    return "?", ""


def _parse_header_format(body, version, act):
    """구포맷: h2/h3/h4 헤더로 에이전트 섹션 구분"""
    rows = []
    current_agent, current_reason, in_section = None, [], False
    for elem in body.find_all(["h1","h2","h3","h4","p","li"]):
        text = elem.get_text(" ", strip=True)
        if not text:
            continue
        if elem.name in ("h2","h3","h4"):
            found = _resolve_agent(text.lower())
            if found:
                current_agent, current_reason, in_section = found, [], True
            elif any(kw in text.lower() for kw in ["map","weapon","bug fix","performance","competitive"]):
                current_agent, in_section = None, False
            continue
        if not in_section or not current_agent:
            continue
        is_italic = bool(elem.find("em") or elem.find("i"))
        if (is_italic or text.startswith('"')) and elem.name == "p":
            current_reason.append(text[:200])
            continue
        if elem.name == "li":
            sk, sn = _infer_skill(text)
            rows.append(_make_row(version, act, current_agent, text, sk, sn, current_reason))
    return rows


def _get_direct_text(tag):
    """태그의 직계 텍스트만 추출 (자식 태그 텍스트 제외)"""
    from bs4 import NavigableString
    return "".join(c.strip() for c in tag.children
                   if isinstance(c, NavigableString) and c.strip())


def _parse_ul_strong_format(body, version, act):
    """
    신포맷 파서: 두 가지 중첩 리스트 변형 모두 처리
    - Format 2: <li><strong>AgentName</strong><ul>...</ul></li>
    - Format 3: <li>AgentName (plain text)<ul>...</ul></li>  (12.05 스타일)
    - Format 4: <li>AgentName's SkillName changed ...</li>  (12.06 단순 설명)
    """
    rows = []
    agents_set = set(AGENTS)

    for agent_li in body.find_all("li"):
        # Format 2: 직계 <strong>이 에이전트명
        direct_strong = agent_li.find("strong", recursive=False)
        if direct_strong:
            agent_name = direct_strong.get_text(strip=True)
        else:
            # Format 3: 직계 plain text가 에이전트명
            agent_name = _get_direct_text(agent_li)

        # 에이전트명 정확 매칭 (별칭 포함)
        agent_name = AGENT_ALIASES.get(agent_name.lower(), agent_name)
        if agent_name not in agents_set:
            # Format 4: "AgentName's ..." 식의 설명 li (플랫 구조)
            full_text = agent_li.get_text(" ", strip=True)
            matched = _resolve_agent(full_text.lower())
            if not matched:
                matched = next((a for a in agents_set if full_text.startswith(a)), None)
            if matched and agent_li.find("ul") is None:
                sk, sn = _infer_skill(full_text)
                rows.append(_make_row(version, act, matched, full_text, sk, sn, []))
            continue

        reason_list = []
        sub_ul = agent_li.find("ul", recursive=False)
        if not sub_ul:
            continue

        current_sk, current_sn = "?", ""

        for sub_li in sub_ul.find_all("li", recursive=False):
            # 스킬명 헤더 감지 (strong 또는 plain text)
            sub_strong = sub_li.find("strong", recursive=False)
            if sub_strong:
                skill_text = sub_strong.get_text(strip=True)
            else:
                skill_text = _get_direct_text(sub_li)

            sk2, sn2 = _infer_skill(skill_text)
            if sk2 != "?":
                current_sk, current_sn = sk2, sn2

            sub_text = sub_li.get_text(" ", strip=True)

            # 이 스킬 아래 변경 li들
            skill_sub_ul = sub_li.find("ul", recursive=False)
            if skill_sub_ul:
                for change_li in skill_sub_ul.find_all("li"):
                    txt = change_li.get_text(" ", strip=True)
                    if not txt or len(txt) < 4:
                        continue
                    has_change = (">>>" in txt or "\u2192" in txt or "->" in txt or
                                  re.search(r"\d+\s*(>>|s\b|%)", txt))
                    if not has_change and len(txt) > 80:
                        reason_list.append(txt[:200])
                        continue
                    rows.append(_make_row(version, act, agent_name, txt, current_sk, current_sn, reason_list))
            else:
                # ul 없는 직접 변경
                has_change = (">>>" in sub_text or "\u2192" in sub_text or "->" in sub_text or
                              re.search(r"\d+\s*(>>|s\b|%)", sub_text))
                if has_change:
                    rows.append(_make_row(version, act, agent_name, sub_text, current_sk, current_sn, reason_list))
                elif len(sub_text) > 30:
                    reason_list.append(sub_text[:200])

    return rows


def _parse_p_strong_format(body, version, act):
    """
    Format 5: <p><strong>AgentName</strong></p> 뒤에
    - <ul><li>...</li></ul> 직접 변경 리스트, 또는
    - <div class="table-wrapper"><table><tbody><tr><td><ul>...</ul></td></tr></tbody></table></div>
    """
    rows = []
    agents_set = set(AGENTS)

    # <p> 요소들 중 에이전트명 포함 찾기
    all_ps = body.find_all("p")
    for idx, p_tag in enumerate(all_ps):
        # <p><strong>AgentName</strong></p> 또는 <p>AGENTNAME</p>
        strong = p_tag.find("strong", recursive=False)
        if strong:
            candidate = strong.get_text(strip=True)
        else:
            candidate = p_tag.get_text(strip=True)

        # 에이전트명 매칭 (대소문자 무시, 별칭 포함)
        matched_agent = AGENT_ALIASES.get(candidate.lower(), None)
        if not matched_agent:
            matched_agent = next(
                (a for a in agents_set if a.lower() == candidate.lower()), None
            )
        if not matched_agent:
            continue

        # 다음 형제 요소들 탐색 (다음 에이전트 섹션 또는 h2 전까지)
        reason_list = []
        current_sk, current_sn = "?", ""

        sib = p_tag
        while True:
            sib = sib.find_next_sibling()
            if not sib:
                break
            # 다음 에이전트 섹션 또는 주요 헤더 만나면 중단
            if sib.name in ("h2", "h3", "h4"):
                break
            if sib.name == "p":
                sib_strong = sib.find("strong", recursive=False)
                if sib_strong:
                    sib_txt = sib_strong.get_text(strip=True)
                else:
                    sib_txt = sib.get_text(strip=True)
                if any(a.lower() == sib_txt.lower() for a in agents_set):
                    break
                # 개발자 코멘트
                txt = sib.get_text(" ", strip=True)
                if txt:
                    reason_list.append(txt[:200])
                continue

            # <ul> 직접 변경 리스트
            if sib.name == "ul":
                for li in sib.find_all("li", recursive=False):
                    li_text = li.get_text(" ", strip=True)
                    # 스킬명 감지
                    sk2, sn2 = _infer_skill(li_text)
                    if sk2 != "?":
                        current_sk, current_sn = sk2, sn2

                    nested_ul = li.find("ul", recursive=False)
                    if nested_ul:
                        for change_li in nested_ul.find_all("li"):
                            txt = change_li.get_text(" ", strip=True)
                            if not txt or len(txt) < 4:
                                continue
                            is_numeric = (">>>" in txt or "\u2192" in txt or "->" in txt
                                          or re.search(r"\d+\s*(>>>|s\b|%)", txt))
                            is_mechanic = len(txt) <= 120
                            if is_numeric or is_mechanic:
                                rows.append(_make_row(version, act, matched_agent,
                                                      txt, current_sk, current_sn, reason_list))
                            else:
                                reason_list.append(txt[:200])
                    else:
                        is_numeric = (">>>" in li_text or "\u2192" in li_text or "->" in li_text
                                      or re.search(r"\d+\s*(>>>|s\b|%)", li_text))
                        is_mechanic = len(li_text) <= 120
                        if is_numeric or is_mechanic:
                            rows.append(_make_row(version, act, matched_agent,
                                                  li_text, current_sk, current_sn, reason_list))
                        else:
                            reason_list.append(li_text[:200])
                continue

            # <div> table-wrapper 포맷 (7.12 스타일)
            if sib.name == "div":
                # <td> 안의 최상위 <ul>만 처리 (중첩 ul 중복 방지)
                for td in sib.find_all("td"):
                    ul = td.find("ul")  # td 내 첫 번째 ul
                    if not ul:
                        continue
                    for top_li in ul.find_all("li", recursive=False):
                        li_text = top_li.get_text(" ", strip=True)
                        sk2, sn2 = _infer_skill(li_text)
                        if sk2 != "?":
                            current_sk, current_sn = sk2, sn2

                        nested_ul = top_li.find("ul", recursive=False)
                        if nested_ul:
                            for change_li in nested_ul.find_all("li", recursive=False):
                                txt = change_li.get_text(" ", strip=True)
                                if not txt or len(txt) < 4:
                                    continue
                                # 수치변경 OR 메카닉변경(짧은 서술) 모두 캡처
                                is_numeric = (">>>" in txt or "\u2192" in txt or "->" in txt
                                              or re.search(r"\d[\d.]*\s*(>>>|s\b|%)", txt))
                                is_mechanic = len(txt) <= 120
                                if is_numeric or is_mechanic:
                                    rows.append(_make_row(version, act, matched_agent,
                                                          txt, current_sk, current_sn, reason_list))
                        else:
                            # 중첩 ul 없는 직접 변경 항목
                            is_numeric = (">>>" in li_text or "\u2192" in li_text or "->" in li_text
                                          or re.search(r"\d[\d.]*\s*(>>>|s\b|%)", li_text))
                            # 스킬명 헤더 li는 제외 (스킬명만 있는 경우)
                            if is_numeric or (len(li_text) <= 120 and sk2 == "?" and len(li_text) > 10):
                                rows.append(_make_row(version, act, matched_agent,
                                                      li_text, current_sk, current_sn, reason_list))
                continue

    return rows


def parse_patch_page(html: str, version: str, act: str) -> list[dict]:
    """패치 노트 HTML → 에이전트별 변경 내용 (구/신 포맷 자동 감지)"""
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("article") or soup.find("main") or soup.body
    if not body:
        return []

    # 구포맷 시도 (h2/h3/h4 헤더)
    rows = _parse_header_format(body, version, act)
    found_agents = {r["agent"] for r in rows}

    # <li><strong>AgentName</strong> 포맷
    ul_rows = _parse_ul_strong_format(body, version, act)
    new_ul = {r["agent"] for r in ul_rows} - found_agents
    rows += [r for r in ul_rows if r["agent"] in new_ul]
    found_agents.update(new_ul)

    # <p><strong>AgentName</strong></p> 포맷 (7.12, 8.08 스타일)
    p_rows = _parse_p_strong_format(body, version, act)
    new_p = {r["agent"] for r in p_rows} - found_agents
    rows += [r for r in p_rows if r["agent"] in new_p]
    found_agents.update(new_p)

    return rows


# ─── 크롤링 ──────────────────────────────────────────────────────────────────

def crawl_patch(page, patch: dict) -> list[dict]:
    url = BASE_URL.format(url=patch["url"])
    version = patch["version"]
    print(f"  [{version}] {url}", end=" ... ", flush=True)

    try:
        page.goto(url, wait_until="networkidle", timeout=40000)
        time.sleep(2)
        html = page.content()
    except Exception as e:
        print(f"실패: {e}")
        return []

    rows = parse_patch_page(html, version, patch["act"])
    print(f"{len(rows)}건")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", type=str, help="특정 패치 버전 (예: 12.05)")
    args = parser.parse_args()

    targets = PATCHES
    if args.patch:
        targets = [p for p in PATCHES if p["version"] == args.patch]

    print("=" * 60)
    print(f"Valorant 패치 노트 수집 ({len(targets)}개 패치)")
    print("=" * 60 + "\n")

    all_rows = []

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

        page.goto("https://playvalorant.com/en-us/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)

        for patch in targets:
            rows = crawl_patch(page, patch)
            all_rows.extend(rows)
            time.sleep(1)

        browser.close()

    if not all_rows:
        print("⚠  수집 데이터 없음")
        return

    df_new = pd.DataFrame(all_rows)

    # 기존 CSV와 병합 (--patch 모드에서 기존 데이터 보존)
    import os
    if args.patch and os.path.exists("patch_notes_raw.csv"):
        df_old = pd.read_csv("patch_notes_raw.csv")
        patched_versions = df_new["patch"].unique().tolist()
        df_old = df_old[~df_old["patch"].isin(patched_versions)]
        df = pd.concat([df_old, df_new], ignore_index=True).sort_values(["patch","agent"])
    else:
        df = df_new

    df.to_csv("patch_notes_raw.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: patch_notes_raw.csv  ({len(df)}행)")
    print(f"패치 {df['patch'].nunique()}개 / 에이전트 {df['agent'].nunique()}개")
    print("\n[에이전트별 변경 건수]")
    print(df.groupby(["agent", "direction"])["patch"].count().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
