"""
agent_data.py
요원 메타데이터 모음 — 상수, 킷/설계/관계 데이터, 유틸 함수

build_step2_data.py 에서 분리. 다른 모듈에서 import 해서 사용.
"""

import numpy as np

# ─── 액트 인덱스 ──────────────────────────────────────────────────────────────

ALL_ACTS = [
    "E2A1","E2A2","E2A3",
    "E3A1","E3A2","E3A3",
    "E4A1","E4A2","E4A3",
    "E5A1","E5A2",
    "E6A1","E6A2","E6A3",
    "E7A1","E7A2","E7A3",
    "E8A1","E8A2","E8A3",
    "E9A1","E9A2","E9A3",
    "V25A1","V25A2","V25A3",
    "V25A4","V25A5","V25A6",
    "V26A1","V26A2",
]
ACT_IDX = {a: i for i, a in enumerate(ALL_ACTS)}
IDX_ACT = {i: a for a, i in ACT_IDX.items()}

# ─── 패치 번호 → 액트 매핑 ───────────────────────────────────────────────────

PATCH_TO_ACT = {
    "2.01":"E2A1","2.02":"E2A1","2.03":"E2A1",
    "2.04":"E2A2","2.05":"E2A2","2.06":"E2A2",
    "2.07":"E2A3","2.08":"E2A3","2.09":"E2A3","2.11":"E2A3",
    "3.01":"E3A1","3.02":"E3A1","3.03":"E3A1","3.04":"E3A1",
    "3.05":"E3A2","3.06":"E3A2","3.07":"E3A2","3.08":"E3A2",
    "3.09":"E3A3","3.10":"E3A3","3.12":"E3A3",
    "4.01":"E4A1","4.02":"E4A1","4.03":"E4A1",
    "4.04":"E4A2","4.05":"E4A2","4.07":"E4A2",
    "4.08":"E4A3","4.09":"E4A3","4.10":"E4A3","4.11":"E4A3",
    "5.01":"E5A1","5.03":"E5A1","5.04":"E5A1",
    "5.05":"E5A2","5.06":"E5A2","5.07":"E5A2","5.08":"E5A2",
    "5.09":"E5A2","5.10":"E5A2",
    "5.12":"E6A1","6.01":"E6A1","6.02":"E6A1","6.03":"E6A1",
    "6.04":"E6A2","6.05":"E6A2",
    "6.06":"E6A3","6.07":"E6A3",
    "6.08":"E7A2","6.10":"E7A2",
    "6.11":"E7A3","7.01":"E7A3","7.02":"E7A3","7.03":"E7A3",
    "7.04":"E8A1","7.05":"E8A1","7.06":"E8A1","7.07":"E8A1","7.08":"E8A1",
    "7.09":"E8A2","7.10":"E8A2",
    "7.12":"E8A3","8.01":"E8A3",
    "8.02":"E9A1","8.03":"E9A1","8.04":"E9A1","8.05":"E9A1",
    "8.07":"E9A2","8.08":"E9A2","8.09":"E9A2","8.10":"E9A2",
    "8.11":"E9A3",
    # E9 (2024)
    "9.03":"E9A1",
    "9.04":"E9A2","9.05":"E9A2","9.06":"E9A2","9.07":"E9A2",
    "9.08":"E9A3","9.09":"E9A3","9.10":"E9A3","9.11":"E9A3",
    # V25A1: 2025-01-08 ~ 03-04
    "10.0":"V25A1","10.01":"V25A1","10.02":"V25A1","10.03":"V25A1",
    # V25A2: 2025-03-05 ~ 04-29
    "10.04":"V25A2","10.05":"V25A2","10.06":"V25A2","10.07":"V25A2",
    # V25A3: 2025-04-30 ~ 06-24
    "10.08":"V25A3","10.09":"V25A3","10.10":"V25A3","10.11":"V25A3",
    # V25A4: 2025-06-25 ~ 08-19
    "11.0":"V25A4","11.01":"V25A4","11.02":"V25A4","11.03":"V25A4",
    # V25A5: 2025-08-20 ~ 10-14
    "11.04":"V25A5","11.05":"V25A5","11.06":"V25A5","11.07":"V25A5","11.07b":"V25A5",
    # V25A6: 2025-10-15 ~ 2026-01-06
    "11.08":"V25A6","11.09":"V25A6","11.10":"V25A6","11.11":"V25A6",
    # V26A1: 2026-01-07 ~ 03-17
    "12.00":"V26A1","12.01":"V26A1","12.02":"V26A1","12.03":"V26A1","12.04":"V26A1",
    # V26A2: 2026-03-18 ~
    "12.05":"V26A2","12.06":"V26A2",
}

# ─── VCT 이벤트 → 액트 매핑 ──────────────────────────────────────────────────

VCT_TO_ACT = {
    "Masters Reykjavik 2022":"E4A3","Masters Copenhagen 2022":"E5A1",
    "Champions 2022":"E6A1","VCT LOCK//IN 2023":"E7A1",
    "VCT Americas League 2023":"E7A2","VCT EMEA League 2023":"E7A2",
    "VCT Pacific League 2023":"E7A2","Masters Tokyo 2023":"E7A3",
    "Champions 2023":"E9A2",
    "VCT Americas Kickoff 2024":"E8A1","VCT EMEA Kickoff 2024":"E8A1",
    "VCT Pacific Kickoff 2024":"E8A1","VCT CN Kickoff 2024":"E8A1",
    "VCT Americas Stage 1 2024":"E8A2","VCT EMEA Stage 1 2024":"E8A2",
    "VCT Pacific Stage 1 2024":"E8A2","VCT CN Stage 1 2024":"E8A2",
    "Masters Madrid 2024":"E8A3",
    "VCT Americas Stage 2 2024":"E9A1","VCT EMEA Stage 2 2024":"E9A1",
    "VCT Pacific Stage 2 2024":"E9A1","VCT CN Stage 2 2024":"E9A1",
    "Masters Shanghai 2024":"E9A2","Champions 2024":"E9A3",
    "VCT Americas Kickoff 2025":"V25A1","VCT EMEA Kickoff 2025":"V25A1",
    "VCT Pacific Kickoff 2025":"V25A1","VCT CN Kickoff 2025":"V25A1",
    "VCT Americas Stage 1 2025":"V25A2","VCT EMEA Stage 1 2025":"V25A2",
    "VCT Pacific Stage 1 2025":"V25A2","VCT CN Stage 1 2025":"V25A2",
    "Masters Bangkok 2025":"V25A3",
    "VCT Americas Stage 2 2025":"V25A4","VCT EMEA Stage 2 2025":"V25A4",
    "VCT Pacific Stage 2 2025":"V25A4","VCT CN Stage 2 2025":"V25A4",
    "Champions 2025":"V25A5",
    "VCT Americas Kickoff 2026":"V26A1","VCT Pacific Kickoff 2026":"V26A1",
    "VCT EMEA Kickoff 2026":"V26A1","VCT CN Kickoff 2026":"V26A1",
    "Masters Santiago 2026":"V26A1",
    "VCT EMEA Stage 1 2026":"V26A2","VCT Pacific Stage 1 2026":"V26A2",
    "VCT Americas Stage 1 2026":"V26A2","VCT CN Stage 1 2026":"V26A2",
}
VCT_EVENT_ORDER = {v: i for i, v in enumerate(VCT_TO_ACT.keys())}

# ─── 스킬 가중치 ──────────────────────────────────────────────────────────────

SKILL_WEIGHT = {"E": 3.0, "C": 2.0, "Q": 1.0, "X": 2.5}

# ─── 요원 이름 정규화 ─────────────────────────────────────────────────────────

AGENT_NAME_MAP = {
    "KAY/O": "KAYO",
    "Kayo":  "KAYO",
    "kayo":  "KAYO",
}

def normalize_agent(name: str) -> str:
    return AGENT_NAME_MAP.get(name, name)

# ─── 역할군 매핑 ──────────────────────────────────────────────────────────────

AGENT_ROLE: dict[str, str] = {
    # 타격대 (Duelist)
    "Jett":      "Duelist",
    "Reyna":     "Duelist",
    "Raze":      "Duelist",
    "Neon":      "Duelist",
    "Phoenix":   "Duelist",
    "Iso":       "Duelist",
    "Yoru":      "Duelist",
    "Waylay":    "Duelist",
    # 전술가 (Controller)
    "Brimstone": "Controller",
    "Viper":     "Controller",
    "Omen":      "Controller",
    "Astra":     "Controller",
    "Clove":     "Controller",
    "Harbor":    "Controller",
    "Miks":      "Controller",
    # 개시자 (Initiator)
    "Sova":      "Initiator",
    "Skye":      "Initiator",
    "Fade":      "Initiator",
    "Breach":    "Initiator",
    "KAYO":      "Initiator",
    "Gekko":     "Initiator",
    "Tejo":      "Initiator",
    # 감시자 (Sentinel)
    "Cypher":    "Sentinel",
    "Killjoy":   "Sentinel",
    "Sage":      "Sentinel",
    "Chamber":   "Sentinel",
    "Deadlock":  "Sentinel",
    "Vyse":      "Sentinel",
    "Veto":      "Sentinel",
}

# ─── 스킬 등급 계층 ───────────────────────────────────────────────────────────
# S급(4): 연막(smoke), 광역CC/진탕 → 메타 핵심 유틸
# A급(3): 섬광/시야차단, 정보획득, 이동기, 국지CC → 높은 범용 가치
# B급(2): 장판피해, 감시트랩, 이동기보조 → 상황 의존적
# C급(1): 힐(자가), 부활, 자가버프 → 낮은 팀 기여

SKILL_TIER_SCORE = {"S": 4, "A": 3, "B": 2, "C": 1}
AGENT_TIER_SCORE = {"S": 4, "A": 3, "B": 2, "C": 1}

# ─── 요원 스킬 구성 (나무위키 공식 스킬명 기준, 2026-04-03) ──────────────────

AGENT_KIT = {
    # ── 타격대 ────────────────────────────────────────────────────────────────
    "Jett": {
        "C": {"tier":"B","type":"smoke",    "ko":"연막 폭발",         "en":"Cloudburst"},
        "Q": {"tier":"C","type":"mobility", "ko":"상승 기류",         "en":"Updraft"},
        "E": {"tier":"S","type":"mobility", "ko":"순풍",              "en":"Tailwind"},
        "X": {"tier":"B","type":"selfbuff", "ko":"칼날 폭풍",         "en":"Blade Storm"},
    },
    "Reyna": {
        "C": {"tier":"B","type":"blind",    "ko":"눈총",              "en":"Leer"},
        "Q": {"tier":"C","type":"heal",     "ko":"포식",              "en":"Devour"},
        "E": {"tier":"A","type":"mobility", "ko":"무시",              "en":"Dismiss"},
        "X": {"tier":"C","type":"selfbuff", "ko":"여제",              "en":"Empress"},
    },
    "Raze": {
        "C": {"tier":"A","type":"zone",     "ko":"폭발 봇",           "en":"Boom Bot"},
        "Q": {"tier":"A","type":"mobility", "ko":"폭발 팩",           "en":"Blast Pack"},
        "E": {"tier":"A","type":"zone",     "ko":"페인트 탄",         "en":"Paint Shells"},
        "X": {"tier":"B","type":"zone",     "ko":"대미 장식",         "en":"Showstopper"},
    },
    "Neon": {
        "C": {"tier":"A","type":"zone",     "ko":"추월 차선",         "en":"Fast Lane"},
        "Q": {"tier":"A","type":"cc",       "ko":"릴레이 볼트",       "en":"Relay Bolt"},
        "E": {"tier":"S","type":"mobility", "ko":"고속 기어",         "en":"High Gear"},
        "X": {"tier":"B","type":"selfbuff", "ko":"오버드라이브",      "en":"Overdrive"},
    },
    "Phoenix": {
        "C": {"tier":"B","type":"zone",     "ko":"불길",              "en":"Blaze"},
        "Q": {"tier":"B","type":"zone",     "ko":"뜨거운 손",         "en":"Hot Hands"},
        "E": {"tier":"A","type":"flash",    "ko":"커브볼",            "en":"Curveball"},
        "X": {"tier":"A","type":"revive",   "ko":"역습",              "en":"Run it Back"},
    },
    "Iso": {
        "C": {"tier":"B","type":"zone",     "ko":"대비책",            "en":"Contingency"},
        "Q": {"tier":"B","type":"cc",       "ko":"약화",              "en":"Undercut"},
        "E": {"tier":"B","type":"selfbuff", "ko":"구슬 보호막",       "en":"Double Tap"},
        "X": {"tier":"B","type":"selfbuff", "ko":"청부 계약",         "en":"Kill Contract"},
    },
    "Yoru": {
        "C": {"tier":"B","type":"info",     "ko":"기만",              "en":"Fakeout"},
        "Q": {"tier":"A","type":"flash",    "ko":"기습",              "en":"Blindside"},
        "E": {"tier":"A","type":"mobility", "ko":"관문 충돌",         "en":"Gatecrash"},
        "X": {"tier":"S","type":"info",     "ko":"차원 표류",         "en":"Dimensional Drift"},
    },
    "Waylay": {
        "C": {"tier":"B","type":"cc",       "ko":"포화",              "en":"Barrage"},
        "Q": {"tier":"A","type":"mobility", "ko":"광속",              "en":"Lightspeed"},
        "E": {"tier":"A","type":"mobility", "ko":"굴절",              "en":"Refract"},
        "X": {"tier":"S","type":"cc",       "ko":"초점 교차",         "en":"Focal Point"},
    },
    # ── 전략가 ────────────────────────────────────────────────────────────────
    "Brimstone": {
        "C": {"tier":"B","type":"selfbuff", "ko":"자극제 신호기",     "en":"Stim Beacon"},
        "Q": {"tier":"B","type":"zone",     "ko":"소이탄",            "en":"Incendiary"},
        "E": {"tier":"A","type":"smoke",    "ko":"공중 연막",         "en":"Sky Smoke"},
        "X": {"tier":"B","type":"zone",     "ko":"궤도 일격",         "en":"Orbital Strike"},
    },
    "Viper": {
        "C": {"tier":"A","type":"zone",     "ko":"뱀 이빨",           "en":"Snake Bite"},
        "Q": {"tier":"A","type":"smoke",    "ko":"독성 연기",         "en":"Poison Cloud"},
        "E": {"tier":"S","type":"smoke",    "ko":"독성 장막",         "en":"Toxic Screen"},
        "X": {"tier":"S","type":"smoke",    "ko":"독사의 구덩이",     "en":"Viper's Pit"},
    },
    "Omen": {
        "C": {"tier":"B","type":"mobility", "ko":"어둠의 발자국",     "en":"Shrouded Step"},
        "Q": {"tier":"S","type":"blind",    "ko":"피해망상",          "en":"Paranoia"},
        "E": {"tier":"S","type":"smoke",    "ko":"어둠의 장막",       "en":"Dark Cover"},
        "X": {"tier":"C","type":"mobility", "ko":"그림자 습격",       "en":"From the Shadows"},
    },
    "Astra": {
        "C": {"tier":"A","type":"cc",       "ko":"중력의 샘",         "en":"Gravity Well"},
        "Q": {"tier":"A","type":"cc",       "ko":"신성 파동",         "en":"Nova Pulse"},
        "E": {"tier":"S","type":"smoke",    "ko":"성운",              "en":"Nebula"},
        "X": {"tier":"S","type":"smoke",    "ko":"우주 장벽",         "en":"Cosmic Divide"},
    },
    "Clove": {
        "C": {"tier":"C","type":"heal",     "ko":"활력 회복",         "en":"Pick-me-up"},
        "Q": {"tier":"B","type":"zone",     "ko":"간섭",              "en":"Meddle"},
        "E": {"tier":"S","type":"smoke",    "ko":"계략",              "en":"Ruse"},
        "X": {"tier":"B","type":"revive",   "ko":"아직 안 죽었어",    "en":"Not Dead Yet"},
    },
    "Harbor": {
        "C": {"tier":"A","type":"smoke",    "ko":"폭풍 쇄도",         "en":"Cove"},
        "Q": {"tier":"A","type":"smoke",    "ko":"만조",              "en":"High Tide"},
        "E": {"tier":"B","type":"zone",     "ko":"해만",              "en":"Cascade"},
        "X": {"tier":"B","type":"cc",       "ko":"심판",              "en":"Reckoning"},
    },
    # ── 척후대 ────────────────────────────────────────────────────────────────
    "Sova": {
        "C": {"tier":"A","type":"info",     "ko":"올빼미 드론",       "en":"Owl Drone"},
        "Q": {"tier":"B","type":"zone",     "ko":"충격 화살",         "en":"Shock Bolt"},
        "E": {"tier":"S","type":"info",     "ko":"정찰용 화살",       "en":"Recon Bolt"},
        "X": {"tier":"B","type":"zone",     "ko":"사냥꾼의 분노",     "en":"Hunter's Fury"},
    },
    "Skye": {
        "C": {"tier":"C","type":"heal",     "ko":"재생",              "en":"Regrowth"},
        "Q": {"tier":"A","type":"info",     "ko":"정찰자",            "en":"Trailblazer"},
        "E": {"tier":"A","type":"flash",    "ko":"인도하는 빛",       "en":"Guiding Light"},
        "X": {"tier":"B","type":"info",     "ko":"추적자",            "en":"Seekers"},
    },
    "Fade": {
        "C": {"tier":"B","type":"info",     "ko":"추적귀",            "en":"Haunt"},
        "Q": {"tier":"B","type":"cc",       "ko":"포박",              "en":"Seize"},
        "E": {"tier":"S","type":"info",     "ko":"귀체",              "en":"Prowler"},
        "X": {"tier":"S","type":"cc",       "ko":"황혼",              "en":"Nightfall"},
    },
    "Breach": {
        "C": {"tier":"A","type":"cc",       "ko":"여진",              "en":"Aftershock"},
        "Q": {"tier":"A","type":"flash",    "ko":"섬광 폭발",         "en":"Flashpoint"},
        "E": {"tier":"A","type":"cc",       "ko":"균열",              "en":"Fault Line"},
        "X": {"tier":"S","type":"cc",       "ko":"지진 강타",         "en":"Rolling Thunder"},
    },
    "KAYO": {
        "C": {"tier":"B","type":"zone",     "ko":"파편/탄",           "en":"FRAG/ment"},
        "Q": {"tier":"A","type":"flash",    "ko":"플래시/드라이브",   "en":"FLASH/drive"},
        "E": {"tier":"S","type":"info",     "ko":"제로/포인트",       "en":"ZERO/point"},
        "X": {"tier":"A","type":"cc",       "ko":"무력화/명령",       "en":"NULL/cmd"},
    },
    "Gekko": {
        "C": {"tier":"B","type":"zone",     "ko":"폭파봇 지옥",       "en":"Mosh Pit"},
        "Q": {"tier":"A","type":"zone",     "ko":"지원봇",            "en":"Wingman"},
        "E": {"tier":"A","type":"flash",    "ko":"기절봇",            "en":"Dizzy"},
        "X": {"tier":"A","type":"cc",       "ko":"요동봇",            "en":"Thrash"},
    },
    "Tejo": {
        "C": {"tier":"A","type":"info",     "ko":"잠입 드론",         "en":"Stealth Drone"},
        "Q": {"tier":"B","type":"zone",     "ko":"특별 배송",         "en":"Special Delivery"},
        "E": {"tier":"A","type":"zone",     "ko":"유도 일제 사격",    "en":"Guided Salvo"},
        "X": {"tier":"B","type":"zone",     "ko":"아마겟돈",          "en":"Armageddon"},
    },
    # ── 감시자 ────────────────────────────────────────────────────────────────
    "Cypher": {
        "C": {"tier":"A","type":"trap",     "ko":"함정",              "en":"Trapwire"},
        "Q": {"tier":"B","type":"zone",     "ko":"사이버 감옥",       "en":"Cyber Cage"},
        "E": {"tier":"A","type":"info",     "ko":"스파이캠",          "en":"Spycam"},
        "X": {"tier":"A","type":"info",     "ko":"신경 절도",         "en":"Neural Theft"},
    },
    "Killjoy": {
        "C": {"tier":"A","type":"zone",     "geo_ceiling":"S",        "ko":"나노스웜",          "en":"Nanoswarm"},
        "Q": {"tier":"A","type":"trap",     "ko":"알람봇",            "en":"Alarmbot"},
        "E": {"tier":"A","type":"trap",     "ko":"포탑",              "en":"Turret"},
        "X": {"tier":"S","type":"cc",       "ko":"봉쇄",              "en":"Lockdown"},
    },
    "Sage": {
        "C": {"tier":"A","type":"zone",     "ko":"장벽 구슬",         "en":"Barrier Orb"},
        "Q": {"tier":"B","type":"cc",       "ko":"둔화 구슬",         "en":"Slow Orb"},
        "E": {"tier":"C","type":"heal",     "ko":"회복 구슬",         "en":"Healing Orb"},
        "X": {"tier":"B","type":"revive",   "ko":"부활",              "en":"Resurrection"},
    },
    "Chamber": {
        "C": {"tier":"B","type":"trap",     "ko":"트레이드마크",      "en":"Trademark"},
        "Q": {"tier":"B","type":"zone",     "ko":"헤드헌터",          "en":"Headhunter"},
        "E": {"tier":"S","type":"mobility", "ko":"랑데부",            "en":"Rendezvous"},
        "X": {"tier":"A","type":"zone",     "ko":"역작",              "en":"Tour De Force"},
    },
    "Deadlock": {
        "C": {"tier":"B","type":"trap",     "ko":"장벽망",            "en":"Barrier Mesh"},
        "Q": {"tier":"C","type":"trap",     "ko":"음향 센서",         "en":"Sonic Sensor"},
        "E": {"tier":"A","type":"cc",       "ko":"중력그물",          "en":"GravNet"},
        "X": {"tier":"A","type":"cc",       "ko":"소멸",              "en":"Annihilation"},
    },
    "Vyse": {
        "C": {"tier":"B","type":"zone",     "ko":"면도날 덩굴",       "en":"Razorvine"},
        "Q": {"tier":"A","type":"trap",     "ko":"가지치기",          "en":"Shear"},
        "E": {"tier":"A","type":"trap",     "ko":"아크 장미",         "en":"Arc Rose"},
        "X": {"tier":"S","type":"cc",       "ko":"강철 정원",         "en":"Steel Garden"},
    },
    # ── 신규 요원 (2026) ──────────────────────────────────────────────────────
    "Veto": {
        "C": {"tier":"C","type":"mobility", "ko":"지름길",            "en":"Shortcut"},
        "Q": {"tier":"B","type":"trap",     "ko":"목조르기",          "en":"Stranglehold"},
        "E": {"tier":"A","type":"trap",     "ko":"요격기",            "en":"Interceptor"},
        "X": {"tier":"A","type":"selfbuff", "ko":"진화",              "en":"Evolution"},
    },
    "Miks": {
        "C": {"tier":"A","type":"cc",       "secondary_type":"heal",  "geo_ceiling":"S",
              "ko":"M-파동",               "en":"M-Wave"},
        "Q": {"tier":"C","type":"selfbuff", "ko":"화음",              "en":"Harmony"},
        "E": {"tier":"A","type":"smoke",    "ko":"웨이브폼",          "en":"Waveform"},
        "X": {"tier":"B","type":"cc",       "ko":"요동치는 베이스",   "en":"Bass Drop"},
    },
}
_DEFAULT_KIT = {k: {"tier":"B","type":"zone"} for k in ("Q","E","C","X")}


def compute_kit_score(agent: str) -> float:
    """스킬 등급 가중 평균 → 0~4 사이 값. 높을수록 고가치 킷"""
    kit = AGENT_KIT.get(agent, _DEFAULT_KIT)
    scores = [SKILL_TIER_SCORE.get(v["tier"], 2) for v in kit.values()]
    return round(sum(scores) / len(scores), 3)


def get_kit_flags(agent: str) -> dict:
    """has_smoke / has_cc / has_info / has_mobility / has_heal / has_revive / has_flash / has_blind 불리언"""
    kit = AGENT_KIT.get(agent, _DEFAULT_KIT)
    types = set()
    for v in kit.values():
        types.add(v["type"])
        if "secondary_type" in v:
            types.add(v["secondary_type"])
    s_types = {v["type"] for v in kit.values() if v["tier"] == "S"}
    return {
        "has_smoke":        "smoke"    in types,
        "has_cc":           "cc"       in types,
        "has_info":         "info"     in types,
        "has_mobility":     "mobility" in types,
        "has_heal":         "heal"     in types,
        "has_revive":       "revive"   in types,
        "has_flash":        "flash"    in types,
        "has_blind":        "blind"    in types,
        "high_value_smoke": "smoke"    in s_types,
        "high_value_cc":    "cc"       in s_types,
    }


# ─── 요원 설계 의도 ───────────────────────────────────────────────────────────

AGENT_DESIGN = {
    # ── 타격대 ──
    "Reyna": {
        "design_audience": "rank", "team_synergy": 0.0, "complexity": 0.2,
        "replaceability": 0.7, "role_niche": "solo_carry",
        "unique_value": "킬 후 리셋으로 1인 눈덩이 교전 지배. 팀 유틸 전무.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 8,
    },
    "Jett": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.8,
        "replaceability": 0.8, "role_niche": "mobility_duelist",
        "unique_value": "초이동성 + 킬 리셋 돌진. 메타 이동기 캐리.",
        "agent_tier": "B", "op_synergy": True, "geo_synergy": "medium",
        "skill_ceiling": 5,
    },
    "Raze": {
        "design_audience": "both", "team_synergy": 0.2, "complexity": 0.5,
        "replaceability": 0.6, "role_niche": "explosive_duelist",
        "unique_value": "폭발 광역피해 + 폭발팩 이동기. 클러치 교전 지배.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 8,
    },
    "Neon": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.7,
        "replaceability": 0.5, "role_niche": "speed_utility_duelist",
        "unique_value": "추월차선 + 릴레이볼트(CC) + 고속기어(이동) 조합. 타격대 중 유틸 자급 능력 최상위.",
        "agent_tier": "S", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 9,
    },
    "Phoenix": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.4,
        "replaceability": 0.8, "role_niche": "fire_duelist",
        "unique_value": "자가힐 섬광 + 리스폰 울트. 팀 유틸 희박.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 5,
    },
    "Iso": {
        "design_audience": "rank", "team_synergy": 0.1, "complexity": 0.5,
        "replaceability": 0.7, "role_niche": "solo_carry",
        "unique_value": "1v1 결투장 + 실드. 솔로 특화 설계, 팀 기여 최소.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 4,
    },
    "Yoru": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.9,
        "replaceability": 0.5, "role_niche": "deception_flanker",
        "unique_value": "텔포+분신 기만 전술. 감시자 설치물을 구조적으로 무력화.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 9,
    },
    "Waylay": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.6,
        "replaceability": 0.5, "role_niche": "mobility_duelist",
        "unique_value": "소닉 이동기 + 시야교란. 제트 니치를 팀 기여 포함으로 대체.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 7,
    },
    # ── 전략가 ──
    "Omen": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.5,
        "replaceability": 0.5, "role_niche": "smoke_teleport",
        "unique_value": "S급 연막 + 이동기 콤보. 맵 전체 이동 울트.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 5,
    },
    "Viper": {
        "design_audience": "pro",  "team_synergy": 0.9, "complexity": 0.9,
        "replaceability": 0.3, "role_niche": "zone_control_smoke",
        "unique_value": "맵 구역 완전 봉쇄. 독 데미지+연막 이중 압박. 팀 조율 없이 가치 없음.",
        "agent_tier": "S", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 7,
    },
    "Brimstone": {
        "design_audience": "both", "team_synergy": 0.7, "complexity": 0.4,
        "replaceability": 0.6, "role_niche": "smoke_support",
        "unique_value": "원격 연막 3개 + 자극제 버프. 직관적 전략가.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 3,
    },
    "Astra": {
        "design_audience": "pro",  "team_synergy": 1.0, "complexity": 1.0,
        "replaceability": 0.4, "role_niche": "global_cc_smoke",
        "unique_value": "맵 전체 CC + 연막 배치. 팀 조율 극대화 시 최강. 솔로 가치 없음.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 10,
    },
    "Clove": {
        "design_audience": "both", "team_synergy": 0.5, "complexity": 0.4,
        "replaceability": 0.5, "role_niche": "smoke_revive",
        "unique_value": "사망 후 행동 가능한 연막 운용. 독특한 생존 메커니즘.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 2,
    },
    "Harbor": {
        "design_audience": "both", "team_synergy": 0.8, "complexity": 0.6,
        "replaceability": 0.7, "role_niche": "water_smoke",
        "unique_value": "물 연막 + 광역 기절. 하지만 연막 경쟁에서 바이퍼/오멘에 열세.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 3,
    },
    # ── 척후대 ──
    "Sova": {
        "design_audience": "pro",  "team_synergy": 0.8, "complexity": 0.9,
        "replaceability": 0.2, "role_niche": "global_info",
        "unique_value": "맵 전체 정보 획득. 드론+화살 조합 반복 가능. 대체 불가 정보원.",
        "agent_tier": "S", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 9,
    },
    "Skye": {
        "design_audience": "pro",  "team_synergy": 0.9, "complexity": 0.7,
        "replaceability": 0.4, "role_niche": "info_heal",
        "unique_value": "정보 + 팀 힐 + 섬광 삼박자. 팀 지속력 핵심.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 6,
    },
    "Fade": {
        "design_audience": "both", "team_synergy": 0.7, "complexity": 0.6,
        "replaceability": 0.5, "role_niche": "info_cc",
        "unique_value": "정보 + CC 콤보. 까마귀 정보 + 야경 광역 CC.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 4,
    },
    "Breach": {
        "design_audience": "pro",  "team_synergy": 1.0, "complexity": 0.8,
        "replaceability": 0.3, "role_niche": "wall_cc",
        "unique_value": "벽 통과 S급 CC 3개. 팀 조율 시 가장 강력한 교전 개시.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 5,
    },
    "KAYO": {
        "design_audience": "both", "team_synergy": 0.8, "complexity": 0.5,
        "replaceability": 0.5, "role_niche": "suppress_initiator",
        "unique_value": "적 스킬 무력화 + 섬광 + 팀 소생. 구성 파괴 전문.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 6,
    },
    "Gekko": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.3,
        "replaceability": 0.5, "role_niche": "cc_initiator",
        "unique_value": "스킬 회수+재사용 CC 삼총사. 설치 보조 내장. 팀 기여 높음.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 3,
    },
    "Tejo": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.5,
        "replaceability": 0.5, "role_niche": "info_bombardment",
        "unique_value": "정밀 드론 + 광역 정밀 폭격. 정보와 피해 동시 제공.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 3,
    },
    # ── 감시자 ──
    "Cypher": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.7,
        "replaceability": 0.6, "role_niche": "info_sentinel",
        "unique_value": "지역 정보 독점. 하지만 요루 텔포에 설치물 전체 무력화.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 4,
    },
    "Killjoy": {
        "design_audience": "both", "team_synergy": 0.5, "complexity": 0.5,
        "replaceability": 0.7, "role_niche": "area_denial_sentinel",
        "unique_value": "사이트 지역 지배 설치물 세트. Q/E/C 모두 B급으로 킷 가치 낮음.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 3,
    },
    "Sage": {
        "design_audience": "both", "team_synergy": 0.9, "complexity": 0.3,
        "replaceability": 0.8, "role_niche": "heal_revive",
        "unique_value": "팀힐 + 부활. C급 스킬 위주 킷 → 수치 조정만으론 메타 진입 어려움.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 1,
    },
    "Chamber": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.7,
        "replaceability": 0.6, "role_niche": "anchor_sniper",
        "unique_value": "텔포 앵커 + 저격 특화. 너프 이후 생존력 저하로 고전.",
        "agent_tier": "B", "op_synergy": True, "geo_synergy": "medium",
        "skill_ceiling": 8,
    },
    "Deadlock": {
        "design_audience": "pro",  "team_synergy": 0.7, "complexity": 0.7,
        "replaceability": 0.5, "role_niche": "cc_sentinel",
        "unique_value": "CC 중심 감시자. 팀 조율 시 봉쇄력 높음.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 2,
    },
    "Vyse": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.6,
        "replaceability": 0.4, "role_niche": "cc_sentinel",
        "unique_value": "S급 광역 CC 울트 + 식물 설치물. 특정 맵에서 킬조이 완벽 대체.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 5,
    },
    # ── 신규 요원 (2026) ──
    "Veto": {
        "design_audience": "pro",  "team_synergy": 0.7, "complexity": 0.7,
        "replaceability": 0.4, "role_niche": "counter_sentinel",
        "unique_value": "투사체 파괴 + 팀 이동경로 생성. 적 스킬 차단에 특화된 감시자.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 7,
    },
    "Miks": {
        "design_audience": "both", "team_synergy": 0.7, "complexity": 0.6,
        "replaceability": 0.5, "role_niche": "support_initiator",
        "unique_value": "음파 CC + 팀 버프 + 음파 연막. 지원형 척후대.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 6,
    },
}
_DEFAULT_DESIGN = {
    "design_audience": "both", "team_synergy": 0.5, "complexity": 0.5,
    "replaceability": 0.5, "role_niche": "unknown", "unique_value": "",
}

# ─── 요원 관계 그래프 (V26A2 메타 스냅샷) ────────────────────────────────────

AGENT_RELATIONS = {
    "Killjoy": {
        "suppressed_by": [
            {"agent":"Yoru",    "type":"counter",  "reason":"요루 텔포가 나노스웜·알람봇·포탑 전체를 무시하고 진입 가능 → 설치물 전략 가치 0"},
            {"agent":"Vyse",    "type":"replaces", "reason":"킬조이 주요 맵(헤이븐·스플릿)에서 바이스가 CC+설치물 모두 우위 → 구조적 상위호환"},
            {"agent":"Tejo",    "type":"counter",  "reason":"테호 정밀 폭격이 설치물을 안전 거리에서 제거 가능"},
        ],
    },
    "Cypher": {
        "suppressed_by": [
            {"agent":"Yoru",    "type":"counter",  "reason":"요루 텔포가 트랩 와이어·스파이캠을 무시하고 진입 → 정보망 전체 붕괴"},
            {"agent":"Tejo",    "type":"counter",  "reason":"정밀 폭격으로 카메라·와이어 제거 가능"},
        ],
    },
    "Jett": {
        "suppressed_by": [
            {"agent":"Waylay",  "type":"replaces", "reason":"웨이레이가 이동기+시야교란+팀 기여를 동시에 제공 → 제트의 이동기 니치 완전 대체"},
            {"agent":"Neon",    "type":"replaces", "reason":"네온이 S급 연막+CC+이동기 삼박자 → 제트보다 팀 유틸 기여 훨씬 높음"},
        ],
    },
    "Sova": {
        "suppressed_by": [
            {"agent":"Tejo",    "type":"competes", "reason":"테호가 정보+광역피해를 동시에 제공 → 소바의 정보 역할을 일부 대체. 단 소바는 '대체 불가' 레벨"},
        ],
        "resilience_note": "정보 획득 자체는 대체 불가 → 픽률 바닥 존재. 완전 대체 아님.",
    },
    "Sage": {"structural_weakness": "힐(C급)+부활(C급) 위주 킷 → 수치 조정만으론 메타 진입 한계. 리워크 없이는 구조적 저픽."},
    "Phoenix": {
        "structural_weakness": "팀 유틸 전무 + 자가힐 의존 설계. 메타가 팀 조율 중심으로 이동할수록 가치 하락.",
        "suppressed_by": [
            {"agent":"Iso",   "type":"competes", "reason":"아이소가 더 강한 생존기+방어막으로 2선 타격대 슬롯 경쟁"},
            {"agent":"Reyna", "type":"competes", "reason":"레이나의 체력 회복+처치 보상 루프가 피닉스의 자가힐보다 효율적"},
            {"agent":"Yoru",  "type":"competes", "reason":"요루의 기만 이동기가 피닉스보다 독창적인 교전 창출"},
        ],
    },
    "Harbor": {
        "suppressed_by": [
            {"agent":"Viper",   "type":"competes", "reason":"연막 전략가 슬롯에서 바이퍼의 독 압박+맵 구역 봉쇄가 하버보다 우위"},
            {"agent":"Omen",    "type":"competes", "reason":"오멘이 연막+이동기 콤보로 더 높은 범용성 제공"},
        ],
    },
    "Chamber": {
        "suppressed_by": [
            {"agent":"Deadlock","type":"competes", "reason":"데드록이 CC 중심 감시자로 더 높은 팀 기여 제공"},
            {"agent":"Vyse",    "type":"competes", "reason":"바이스가 CC+S급 울트로 감시자 슬롯 경쟁"},
        ],
        "structural_weakness": "너프 이후 생존력 저하 → 저격 특화 가치만 남음.",
    },
    "Neon":   {"dominance_note": "추월차선 + 릴레이볼트(CC) + 고속기어(이동) = 타격대 중 유틸 자급력 1위. 랭크/대회 모두 고픽 → 너프 압박."},
    "Breach":  {"dominance_note": "S급 CC 3개 보유. 팀 조율 시 최강 개전 요원. 프로 메타 핵심."},
    "Yoru":    {"meta_impact": "텔포가 감시자 전체 설치물 무력화 → 감시자 픽률 억압 주원인."},
    "Gekko":   {"buff_note": "팀 기여 높고 설치 보조 내장. 랭크/대회 픽률 모두 낮음 → 버프 필요. 스킬 재사용 고유 메커니즘 잠재력 미발휘."},
    "Veto": {
        "meta_impact": "투사체 파괴(요격기)로 소바·테호·브리치 등 투사체 의존 요원 유틸 차단. 지름길로 팀 진입 경로 창출.",
        "suppressed_by": [
            {"agent":"Sova",    "type":"competes", "reason":"정보 획득 측면에서 소바와 척후대 슬롯 경쟁"},
        ],
    },
    "Miks": {
        "meta_impact": "음파 연막 + CC + 팀 버프 복합 킷. 척후대+전략가 혼합 역할. 신규 요원으로 메타 데이터 부족.",
        "suppressed_by": [
            {"agent":"Breach",  "type":"competes", "reason":"CC 척후대 슬롯에서 브리치의 S급 CC 3개와 경쟁"},
        ],
    },
}
