"""
Step 2 Training Data Builder
(요원, 액트) 쌍 → 다음 액트 패치 예측 레이블 생성

레이블 구조:
  stable                         ← 패치 없음
  nerf_{skill}_{trigger}         ← 일반 너프
  nerf_{skill}_{trigger}_followup← 1차 너프 효과 없어 추가 너프
  correction_nerf                ← 과버프 후 재조정
  buff_{skill}_{trigger}         ← 일반 버프
  buff_{skill}_{trigger}_followup← 1차 버프 효과 없어 추가 버프
  correction_buff                ← 과너프 후 복구
  rework                         ← 반복 DUAL_MISS → 수치 조정 한계
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

# ─── 상수 (feature_engineering.py 와 동일) ───────────────────────────────────

ALL_ACTS = [
    "E2A1","E2A2","E2A3",
    "E3A1","E3A2","E3A3",
    "E4A1","E4A2","E4A3",
    "E5A1","E5A2",
    "E6A1","E6A2","E6A3",
    "E7A1","E7A2","E7A3",
    "E8A1","E8A2","E8A3",
    "E9A1","E9A2","E9A3",
    "E10A1","E10A2","E10A3",
    "E11A1","E11A2","E11A3",
    "E12A1","V26A2",
]
ACT_IDX = {a: i for i, a in enumerate(ALL_ACTS)}
IDX_ACT = {i: a for a, i in ACT_IDX.items()}

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
    "9.03":"E10A1","9.04":"E10A1","9.05":"E10A1","9.07":"E10A1",
    "9.08":"E10A2","9.09":"E10A2","9.10":"E10A2",
    "9.11":"E10A3",
    "10.01":"E11A1","10.02":"E11A1","10.03":"E11A1","10.04":"E11A1",
    "10.05":"E11A1","10.06":"E11A1",
    "10.08":"E11A2","10.09":"E11A2","10.10":"E11A2","10.11":"E11A2",
    "11.01":"E11A3","11.02":"E11A3","11.04":"E11A3","11.05":"E11A3",
    "11.06":"E12A1","11.07":"E12A1","11.08":"E12A1","11.09":"E12A1",
    "11.10":"E12A1","11.11":"E12A1",
    "12.01":"V26A2","12.02":"V26A2","12.03":"V26A2","12.04":"V26A2",
    "12.05":"V26A2","12.06":"V26A2",
}

VCT_TO_ACT = {
    "Masters Reykjavik 2022":"E4A3","Masters Copenhagen 2022":"E5A1",
    "Champions 2022":"E6A1","VCT LOCK//IN 2023":"E7A1",
    "VCT Americas League 2023":"E7A2","VCT EMEA League 2023":"E7A2",
    "VCT Pacific League 2023":"E7A2","Masters Tokyo 2023":"E7A3",
    "Champions 2023":"E9A2",
    "VCT Americas Kickoff 2024":"E9A3","VCT EMEA Kickoff 2024":"E9A3",
    "VCT Pacific Kickoff 2024":"E9A3","VCT CN Kickoff 2024":"E9A3",
    "VCT Americas Stage 1 2024":"E10A1","VCT EMEA Stage 1 2024":"E10A1",
    "VCT Pacific Stage 1 2024":"E10A1","VCT CN Stage 1 2024":"E10A1",
    "Masters Madrid 2024":"E10A2",
    "VCT Americas Stage 2 2024":"E10A3","VCT EMEA Stage 2 2024":"E10A3",
    "VCT Pacific Stage 2 2024":"E10A3","VCT CN Stage 2 2024":"E10A3",
    "Masters Shanghai 2024":"E11A1","Champions 2024":"E11A2",
    "VCT Americas Kickoff 2025":"E11A3","VCT EMEA Kickoff 2025":"E11A3",
    "VCT Pacific Kickoff 2025":"E11A3","VCT CN Kickoff 2025":"E11A3",
    "VCT Americas Stage 1 2025":"E11A3","VCT EMEA Stage 1 2025":"E11A3",
    "VCT Pacific Stage 1 2025":"E11A3","VCT CN Stage 1 2025":"E11A3",
    "Masters Bangkok 2025":"E12A1",
    "VCT Americas Stage 2 2025":"E12A1","VCT EMEA Stage 2 2025":"E12A1",
    "VCT Pacific Stage 2 2025":"E12A1","VCT CN Stage 2 2025":"E12A1",
    "Champions 2025":"E12A1","Masters Santiago 2026":"E12A1",
    "VCT EMEA Stage 1 2026":"V26A2","VCT Pacific Stage 1 2026":"V26A2",
    "VCT Americas Stage 1 2026":"V26A2",
}
VCT_EVENT_ORDER = {v: i for i, v in enumerate(VCT_TO_ACT.keys())}

SKILL_WEIGHT = {"E": 3.0, "C": 2.0, "Q": 1.0, "X": 2.5}

# ─── 요원 이름 정규화 매핑 ────────────────────────────────────────────────────
# 소스마다 이름이 달라 정규화 필요 (예: KAY/O, Kayo → KAYO)
AGENT_NAME_MAP = {
    "KAY/O": "KAYO",
    "Kayo":  "KAYO",
    "kayo":  "KAYO",
}

def normalize_agent(name: str) -> str:
    return AGENT_NAME_MAP.get(name, name)

# ─── 스킬 등급 계층 ───────────────────────────────────────────────────────────
# S급(4): 연막(smoke), 광역CC/진탕 → 메타 핵심 유틸
# A급(3): 섬광/시야차단, 정보획득, 이동기, 국지CC → 높은 범용 가치
# B급(2): 장판피해, 감시트랩, 이동기보조 → 상황 의존적
# C급(1): 힐(자가), 부활, 자가버프 → 낮은 팀 기여
# "?": 사용자가 직접 정의 필요 (미정)
SKILL_TIER_SCORE = {"S": 4, "A": 3, "B": 2, "C": 1}
AGENT_TIER_SCORE = {"S": 4, "A": 3, "B": 2, "C": 1}  # 요원 전체 티어 (역할 수행도 반영)

# ─── 요원 스킬 구성 (나무위키 공식 스킬명 기준, 2026-04-03) ──────────────────
# tier: S/A/B/C/?   ← 사용자가 직접 정의 ("?" = 미정, compute_kit_score에서 B급(2)으로 처리)
# type: smoke(연막) / flash(섬광) / cc(군중제어) / info(정보) / mobility(이동기)
#        zone(장판·구역) / trap(감시트랩) / heal(회복) / revive(부활) / selfbuff(자가버프)
AGENT_KIT = {
    # ── Duelists ──────────────────────────────────────────────────────────────
    "Jett": {
        "C": {"tier":"B","type":"smoke",    "ko":"연막 폭발",         "en":"Cloudburst"},
        "Q": {"tier":"C","type":"mobility", "ko":"상승 기류",         "en":"Updraft"},
        "E": {"tier":"S","type":"mobility", "ko":"순풍",              "en":"Tailwind"},
        "X": {"tier":"B","type":"selfbuff", "ko":"칼날 폭풍",         "en":"Blade Storm"},
    },
    "Reyna": {
        "C": {"tier":"B","type":"flash",    "ko":"눈총",              "en":"Leer"},
        "Q": {"tier":"C","type":"heal",     "ko":"포식",              "en":"Devour"},
        "E": {"tier":"B","type":"mobility", "ko":"무시",              "en":"Dismiss"},
        "X": {"tier":"C","type":"selfbuff", "ko":"여제",              "en":"Empress"},
    },
    "Raze": {
        "C": {"tier":"B","type":"zone",     "ko":"폭발 봇",           "en":"Boom Bot"},
        "Q": {"tier":"A","type":"mobility", "ko":"폭발 팩",           "en":"Blast Pack"},
        "E": {"tier":"A","type":"zone",     "ko":"페인트 탄",         "en":"Paint Shells"},
        "X": {"tier":"B","type":"zone",     "ko":"대미 장식",         "en":"Showstopper"},
    },
    "Neon": {
        "C": {"tier":"A","type":"smoke",    "ko":"추월 차선",         "en":"Fast Lane"},
        "Q": {"tier":"B","type":"cc",       "ko":"릴레이 볼트",       "en":"Relay Bolt"},
        "E": {"tier":"S","type":"mobility", "ko":"고속 기어",         "en":"High Gear"},
        "X": {"tier":"C","type":"selfbuff", "ko":"오버드라이브",      "en":"Overdrive"},
    },
    "Phoenix": {
        "C": {"tier":"B","type":"zone",     "ko":"불길",              "en":"Blaze"},
        "Q": {"tier":"B","type":"zone",     "ko":"뜨거운 손",         "en":"Hot Hands"},
        "E": {"tier":"A","type":"flash",    "ko":"커브볼",            "en":"Curveball"},
        "X": {"tier":"C","type":"revive",   "ko":"역습",              "en":"Run it Back"},
    },
    "Iso": {
        "C": {"tier":"B","type":"zone",     "ko":"대비책",            "en":"Contingency"},
        "Q": {"tier":"B","type":"cc",       "ko":"약화",              "en":"Undercut"},
        "E": {"tier":"B","type":"selfbuff", "ko":"구슬 보호막",       "en":"Double Tap"},
        "X": {"tier":"C","type":"selfbuff", "ko":"청부 계약",         "en":"Kill Contract"},
    },
    "Yoru": {
        "C": {"tier":"B","type":"info",     "ko":"기만",              "en":"Fakeout"},
        "Q": {"tier":"A","type":"flash",    "ko":"기습",              "en":"Blindside"},
        "E": {"tier":"A","type":"mobility", "ko":"관문 충돌",         "en":"Gatecrash"},
        "X": {"tier":"A","type":"info",     "ko":"차원 표류",         "en":"Dimensional Drift"},
    },
    "Waylay": {
        "C": {"tier":"B","type":"cc",       "ko":"포화",              "en":"Barrage"},
        "Q": {"tier":"A","type":"mobility", "ko":"광속",              "en":"Lightspeed"},
        "E": {"tier":"A","type":"mobility", "ko":"굴절",              "en":"Refract"},
        "X": {"tier":"B","type":"cc",       "ko":"초점 교차",         "en":"Focal Point"},
    },
    # ── Controllers ───────────────────────────────────────────────────────────
    "Brimstone": {
        "C": {"tier":"B","type":"selfbuff", "ko":"자극제 신호기",     "en":"Stim Beacon"},
        "Q": {"tier":"B","type":"zone",     "ko":"소이탄",            "en":"Incendiary"},
        "E": {"tier":"S","type":"smoke",    "ko":"공중 연막",         "en":"Sky Smoke"},
        "X": {"tier":"B","type":"zone",     "ko":"궤도 일격",         "en":"Orbital Strike"},
    },
    "Viper": {
        "C": {"tier":"A","type":"zone",     "ko":"뱀 이빨",           "en":"Snake Bite"},
        "Q": {"tier":"S","type":"smoke",    "ko":"독성 연기",         "en":"Poison Cloud"},
        "E": {"tier":"S","type":"smoke",    "ko":"독성 장막",         "en":"Toxic Screen"},
        "X": {"tier":"S","type":"smoke",    "ko":"독사의 구덩이",     "en":"Viper's Pit"},
    },
    "Omen": {
        "C": {"tier":"B","type":"mobility", "ko":"어둠의 발자국",     "en":"Shrouded Step"},
        "Q": {"tier":"A","type":"flash",    "ko":"피해망상",          "en":"Paranoia"},
        "E": {"tier":"S","type":"smoke",    "ko":"어둠의 장막",       "en":"Dark Cover"},
        "X": {"tier":"B","type":"mobility", "ko":"그림자 습격",       "en":"From the Shadows"},
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
    # ── Initiators ────────────────────────────────────────────────────────────
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
        "C": {"tier":"A","type":"info",     "ko":"추적귀",            "en":"Haunt"},
        "Q": {"tier":"A","type":"cc",       "ko":"포박",              "en":"Seize"},
        "E": {"tier":"B","type":"info",     "ko":"귀체",              "en":"Prowler"},
        "X": {"tier":"S","type":"cc",       "ko":"황혼",              "en":"Nightfall"},
    },
    "Breach": {
        "C": {"tier":"S","type":"cc",       "ko":"여진",              "en":"Aftershock"},
        "Q": {"tier":"A","type":"flash",    "ko":"섬광 폭발",         "en":"Flashpoint"},
        "E": {"tier":"S","type":"cc",       "ko":"균열",              "en":"Fault Line"},
        "X": {"tier":"S","type":"cc",       "ko":"지진 강타",         "en":"Rolling Thunder"},
    },
    "KAYO": {
        "C": {"tier":"B","type":"zone",     "ko":"파편/탄",           "en":"FRAG/ment"},
        "Q": {"tier":"A","type":"flash",    "ko":"플래시/드라이브",   "en":"FLASH/drive"},
        "E": {"tier":"S","type":"info",     "ko":"제로/포인트",       "en":"ZERO/point"},
        "X": {"tier":"S","type":"cc",       "ko":"무력화/명령",       "en":"NULL/cmd"},
    },
    "Gekko": {
        "C": {"tier":"A","type":"zone",     "ko":"폭파봇 지옥",       "en":"Mosh Pit"},
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
    # ── Sentinels ─────────────────────────────────────────────────────────────
    "Cypher": {
        "C": {"tier":"A","type":"trap",     "ko":"함정",              "en":"Trapwire"},
        "Q": {"tier":"B","type":"zone",     "ko":"사이버 감옥",       "en":"Cyber Cage"},
        "E": {"tier":"A","type":"info",     "ko":"스파이캠",          "en":"Spycam"},
        "X": {"tier":"B","type":"info",     "ko":"신경 절도",         "en":"Neural Theft"},
    },
    "Killjoy": {
        "C": {"tier":"A","type":"zone",     "geo_ceiling":"S",        "ko":"나노스웜",          "en":"Nanoswarm"},
        "Q": {"tier":"A","type":"trap",     "ko":"알람봇",            "en":"Alarmbot"},
        "E": {"tier":"A","type":"trap",     "ko":"포탑",              "en":"Turret"},
        "X": {"tier":"S","type":"cc",       "ko":"봉쇄",              "en":"Lockdown"},
    },
    "Sage": {
        "C": {"tier":"A","type":"zone",     "ko":"장벽 구슬",         "en":"Barrier Orb"},
        "Q": {"tier":"A","type":"cc",       "ko":"둔화 구슬",         "en":"Slow Orb"},
        "E": {"tier":"C","type":"heal",     "ko":"회복 구슬",         "en":"Healing Orb"},
        "X": {"tier":"B","type":"revive",   "ko":"부활",              "en":"Resurrection"},
    },
    "Chamber": {
        "C": {"tier":"B","type":"trap",     "ko":"트레이드마크",      "en":"Trademark"},
        "Q": {"tier":"B","type":"zone",     "ko":"헤드헌터",          "en":"Headhunter"},
        "E": {"tier":"A","type":"mobility", "ko":"랑데부",            "en":"Rendezvous"},
        "X": {"tier":"B","type":"zone",     "ko":"역작",              "en":"Tour De Force"},
    },
    "Deadlock": {
        "C": {"tier":"A","type":"trap",     "ko":"장벽망",            "en":"Barrier Mesh"},
        "Q": {"tier":"B","type":"trap",     "ko":"음향 센서",         "en":"Sonic Sensor"},
        "E": {"tier":"A","type":"cc",       "ko":"중력그물",          "en":"GravNet"},
        "X": {"tier":"A","type":"cc",       "ko":"소멸",              "en":"Annihilation"},
    },
    "Vyse": {
        "C": {"tier":"B","type":"zone",     "ko":"면도날 덩굴",       "en":"Razorvine"},
        "Q": {"tier":"A","type":"trap",     "ko":"가지치기",          "en":"Shear"},
        "E": {"tier":"A","type":"trap",     "ko":"아크 장미",         "en":"Arc Rose"},
        "X": {"tier":"S","type":"cc",       "ko":"강철 정원",         "en":"Steel Garden"},
    },
    # ── New Agents (2026) ─────────────────────────────────────────────────────
    "Veto": {
        "C": {"tier":"B","type":"mobility", "ko":"지름길",            "en":"Shortcut"},
        "Q": {"tier":"B","type":"trap",     "ko":"목조르기",          "en":"Stranglehold"},
        "E": {"tier":"A","type":"trap",     "ko":"요격기",            "en":"Interceptor"},
        "X": {"tier":"B","type":"selfbuff", "ko":"진화",              "en":"Evolution"},
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
    """has_smoke / has_cc / has_info / has_mobility / has_heal / has_revive 불리언
    secondary_type(예: Miks M-파동 힐↔진탕 스위치)도 인식"""
    kit = AGENT_KIT.get(agent, _DEFAULT_KIT)
    types = set()
    for v in kit.values():
        types.add(v["type"])
        if "secondary_type" in v:
            types.add(v["secondary_type"])
    s_types = {v["type"] for v in kit.values() if v["tier"] == "S"}
    return {
        "has_smoke":    "smoke"    in types,
        "has_cc":       "cc"       in types,
        "has_info":     "info"     in types,
        "has_mobility": "mobility" in types,
        "has_heal":     "heal"     in types,
        "has_revive":   "revive"   in types,
        "high_value_smoke": "smoke" in s_types,   # S급 연막 보유
        "high_value_cc":    "cc"   in s_types,    # S급 CC 보유
    }

# ─── 요원 정체성 (설계 의도 기반) ─────────────────────────────────────────────
# design_audience:
#   "rank" → 팀 유틸리티 없는 솔로 캐리 설계 (레이나, 아이소)
#            VCT 저픽은 구조적으로 예측 가능, 랭크 저픽은 비정상
#   "pro"  → 팀 조율 필수 설계 (바이퍼, 아스트라, 브리치, 소바, 스카이, 데드록)
#            랭크 저픽은 구조적으로 예측 가능, VCT 저픽은 비정상
#   "both" → 랭크+대회 모두 의도된 설계 (나머지)
#            랭크 또는 VCT 저픽 모두 비정상 → 패치 신호
# team_synergy: 0.0(솔로 특화) ~ 1.0(팀 조율 필수)
# complexity:   0.0(낮은 진입장벽) ~ 1.0(매우 높은 숙련 요구)
# replaceability: 0.0(대체 불가) ~ 1.0(쉽게 대체됨)
#   → 낮을수록 픽률 바닥 존재 (소바), 높을수록 메타 이탈 시 픽률 0으로 수렴
# role_niche: 요원의 핵심 가치 한 줄 정의
AGENT_DESIGN = {
    # ── Duelists ──
    "Reyna": {
        "design_audience": "rank", "team_synergy": 0.0, "complexity": 0.2,
        "replaceability": 0.7,
        "role_niche": "solo_carry",
        "unique_value": "킬 후 리셋으로 1인 눈덩이 교전 지배. 팀 유틸 전무.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 8,  # 에임 특화 설계. 파일럿 에임 수준이 결과를 직접 결정
    },
    "Jett": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.8,
        "replaceability": 0.8,
        "role_niche": "mobility_duelist",
        "unique_value": "초이동성 + 킬 리셋 돌진. 메타 이동기 캐리.",
        "agent_tier": "B", "op_synergy": True, "geo_synergy": "medium",
        "skill_ceiling": 5,  # 대쉬 캔슬 있으나 에임 의존도 높고 스킬 자체 난이도는 중간
    },
    "Raze": {
        "design_audience": "both", "team_synergy": 0.2, "complexity": 0.5,
        "replaceability": 0.6,
        "role_niche": "explosive_duelist",
        "unique_value": "폭발 광역피해 + 폭발팩 이동기. 클러치 교전 지배.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 8,  # 폭발팩 이동기 + 에임 연계. 파일럿 실력이 효과를 직접 증폭
    },
    "Neon": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.7,
        "replaceability": 0.5,
        "role_niche": "speed_smoke_duelist",
        "unique_value": "S급 연막 + CC + 이동기 삼박자. 자체 유틸 완결형 타격대.",
        "agent_tier": "S", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 9,  # 스프린트 속도 제어·슬라이드 타이밍. 담비(농심) 같은 장인 효과 극대
    },
    "Phoenix": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.4,
        "replaceability": 0.8,
        "role_niche": "fire_duelist",
        "unique_value": "자가힐 섬광 + 리스폰 울트. 팀 유틸 희박.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 5,  # 커브볼 각도 + 에임 의존. 파일럿 실력 반영 중간
    },
    "Iso": {
        "design_audience": "rank", "team_synergy": 0.1, "complexity": 0.5,
        "replaceability": 0.7,
        "role_niche": "solo_carry",
        "unique_value": "1v1 결투장 + 실드. 솔로 특화 설계, 팀 기여 최소.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 4,  # 실드 타이밍 + 에임 의존. 에임 파일럿 효과 있으나 스킬 구조적 한계
    },
    "Yoru": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.9,
        "replaceability": 0.5,
        "role_niche": "deception_flanker",
        "unique_value": "텔포+분신 기만 전술. 감시자 설치물을 구조적으로 무력화.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 9,  # 기만 루트 설계·분신 페이크. 장인과 일반 픽 성과 격차 최대급
    },
    "Waylay": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.6,
        "replaceability": 0.5,
        "role_niche": "mobility_duelist",
        "unique_value": "소닉 이동기 + 시야교란. 제트 니치를 팀 기여 포함으로 대체.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 7,  # 소닉 이동기 타이밍 + 에임 연계. 파일럿 빨 크게 받는 구조
    },
    # ── Controllers ──
    "Omen": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.5,
        "replaceability": 0.5,
        "role_niche": "smoke_teleport",
        "unique_value": "S급 연막 + 이동기 콤보. 맵 전체 이동 울트.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 5,  # 텔포 포지션 창의성 있으나 연막 자체는 직관적. 장인 이점 중간
    },
    "Viper": {
        "design_audience": "pro",  "team_synergy": 0.9, "complexity": 0.9,
        "replaceability": 0.3,
        "role_niche": "zone_control_smoke",
        "unique_value": "맵 구역 완전 봉쇄. 독 데미지+연막 이중 압박. 팀 조율 없이 가치 없음.",
        "agent_tier": "S", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 7,  # 맵별 라인업 숙련 필수. 장인 격차 크지만 소바·요루보다는 낮음
    },
    "Brimstone": {
        "design_audience": "both", "team_synergy": 0.7, "complexity": 0.4,
        "replaceability": 0.6,
        "role_niche": "smoke_support",
        "unique_value": "원격 연막 3개 + 자극제 버프. 직관적 전략가.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 3,  # 연막 배치 직관적. 장인 이점 없음
    },
    "Astra": {
        "design_audience": "pro",  "team_synergy": 1.0, "complexity": 1.0,
        "replaceability": 0.4,
        "role_niche": "global_cc_smoke",
        "unique_value": "맵 전체 CC + 연막 배치. 팀 조율 극대화 시 최강. 솔로 가치 없음.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 10, # 별 배치·팀 타이밍·CC 연계. 게임 내 최고 복잡도. 장인 격차 최대
    },
    "Clove": {
        "design_audience": "both", "team_synergy": 0.5, "complexity": 0.4,
        "replaceability": 0.5,
        "role_niche": "smoke_revive",
        "unique_value": "사망 후 행동 가능한 연막 운용. 독특한 생존 메커니즘.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 2,  # 연막 배치 직관적 + 사망 후 행동 단순. 장인 이점 없음
    },
    "Harbor": {
        "design_audience": "both", "team_synergy": 0.8, "complexity": 0.6,
        "replaceability": 0.7,
        "role_niche": "water_smoke",
        "unique_value": "물 연막 + 광역 기절. 하지만 연막 경쟁에서 바이퍼/오멘에 열세.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 3,  # 물 연막 각도 창의성 있으나 장인 풀 작음
    },
    # ── Initiators ──
    "Sova": {
        "design_audience": "pro",  "team_synergy": 0.8, "complexity": 0.9,
        "replaceability": 0.2,
        "role_niche": "global_info",
        "unique_value": "맵 전체 정보 획득. 드론+화살 조합 반복 가능. 대체 불가 정보원.",
        "agent_tier": "S", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 9,  # 화살 라인업 수백 개. 소바 장인과 일반 픽 정보 격차 극대
    },
    "Skye": {
        "design_audience": "pro",  "team_synergy": 0.9, "complexity": 0.7,
        "replaceability": 0.4,
        "role_niche": "info_heal",
        "unique_value": "정보 + 팀 힐 + 섬광 삼박자. 팀 지속력 핵심.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 6,  # 정찰자 조종·섬광 각도. 장인 이점 있으나 소바·요루만큼 극단적이지 않음
    },
    "Fade": {
        "design_audience": "both", "team_synergy": 0.7, "complexity": 0.6,
        "replaceability": 0.5,
        "role_niche": "info_cc",
        "unique_value": "정보 + CC 콤보. 까마귀 정보 + 야경 광역 CC.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 4,  # 추적귀 경로 설계·야경 타이밍. 장인 이점 중하
    },
    "Breach": {
        "design_audience": "pro",  "team_synergy": 1.0, "complexity": 0.8,
        "replaceability": 0.3,
        "role_niche": "wall_cc",
        "unique_value": "벽 통과 S급 CC 3개. 팀 조율 시 가장 강력한 교전 개시.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 5,  # 벽 통과 각도 라인업 있으나 팀 조율 의존 → 개인 스킬 천장은 중간
    },
    "KAYO": {
        "design_audience": "both", "team_synergy": 0.8, "complexity": 0.5,
        "replaceability": 0.5,
        "role_niche": "suppress_initiator",
        "unique_value": "적 스킬 무력화 + 섬광 + 팀 소생. 구성 파괴 전문.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 6,  # 나이프 투척 각도 + 섬광 타이밍. 장인 이점 중간 (기존 유지)
    },
    "Gekko": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.3,
        "replaceability": 0.5,
        "role_niche": "cc_initiator",
        "unique_value": "스킬 회수+재사용 CC 삼총사. 설치 보조 내장. 팀 기여 높음.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 3,  # 진입 장벽 낮고 스킬 회수 루프 반복. 장인 이점 없음
    },
    "Tejo": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.5,
        "replaceability": 0.5,
        "role_niche": "info_bombardment",
        "unique_value": "정밀 드론 + 광역 정밀 폭격. 정보와 피해 동시 제공.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 3,  # 드론 조종 + 폭격 라인업 있으나 장인 이점 제한적
    },
    # ── Sentinels ──
    "Cypher": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.7,
        "replaceability": 0.6,
        "role_niche": "info_sentinel",
        "unique_value": "지역 정보 독점. 하지만 요루 텔포에 설치물 전체 무력화.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 4,  # 설치 위치 창의성. 메타 제약으로 장인 효과 발현 어려움
    },
    "Killjoy": {
        "design_audience": "both", "team_synergy": 0.5, "complexity": 0.5,
        "replaceability": 0.7,
        "role_niche": "area_denial_sentinel",
        "unique_value": "사이트 지역 지배 설치물 세트. Q/E/C 모두 B급으로 킷 가치 낮음.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 3,  # 나노스웜 숨김 위치 창의성 있으나 스킬 구조 단순. 장인 이점 낮음
    },
    "Sage": {
        "design_audience": "both", "team_synergy": 0.9, "complexity": 0.3,
        "replaceability": 0.8,
        "role_niche": "heal_revive",
        "unique_value": "팀힐 + 부활. C급 스킬 위주 킷 → 수치 조정만으론 메타 진입 어려움.",
        "agent_tier": "C", "op_synergy": False, "geo_synergy": "low",
        "skill_ceiling": 1,  # 장벽 배치·힐 우선순위. 장인 이점 전무
    },
    "Chamber": {
        "design_audience": "both", "team_synergy": 0.3, "complexity": 0.7,
        "replaceability": 0.6,
        "role_niche": "anchor_sniper",
        "unique_value": "텔포 앵커 + 저격 특화. 너프 이후 생존력 저하로 고전.",
        "agent_tier": "B", "op_synergy": True, "geo_synergy": "medium",
        "skill_ceiling": 8,  # 에임 특화 저격 설계. 파일럿 에임 수준이 결과를 직접 결정
    },
    "Deadlock": {
        "design_audience": "pro",  "team_synergy": 0.7, "complexity": 0.7,
        "replaceability": 0.5,
        "role_niche": "cc_sentinel",
        "unique_value": "CC 중심 감시자. 팀 조율 시 봉쇄력 높음.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 2,  # 장벽망+그물 설치 위치 단순. 장인 이점 낮음
    },
    "Vyse": {
        "design_audience": "both", "team_synergy": 0.6, "complexity": 0.6,
        "replaceability": 0.4,
        "role_niche": "cc_sentinel",
        "unique_value": "S급 광역 CC 울트 + 식물 설치물. 특정 맵에서 킬조이 완벽 대체.",
        "agent_tier": "A", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 5,  # 설치물 숨김 창의성. 장인 이점 중간 (기존 유지)
    },
    # ── New Agents (2026) ──
    "Veto": {
        "design_audience": "pro",  "team_synergy": 0.7, "complexity": 0.7,
        "replaceability": 0.4,
        "role_niche": "counter_sentinel",
        "unique_value": "투사체 파괴 + 팀 이동경로 생성. 적 스킬 차단에 특화된 감시자.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "medium",
        "skill_ceiling": 7,  # 투사체 파괴 타이밍 + 루트 생성 창의성. 파일럿 빨 크게 받음
    },
    "Miks": {
        "design_audience": "both", "team_synergy": 0.7, "complexity": 0.6,
        "replaceability": 0.5,
        "role_niche": "support_initiator",
        "unique_value": "음파 CC + 팀 버프 + 음파 연막. 지원형 척후대.",
        "agent_tier": "B", "op_synergy": False, "geo_synergy": "high",
        "skill_ceiling": 6,  # 음파 스위치 타이밍 + CC 연계. 장인 이점 중간
    },
}
_DEFAULT_DESIGN = {
    "design_audience": "both", "team_synergy": 0.5, "complexity": 0.5,
    "replaceability": 0.5, "role_niche": "unknown", "unique_value": "",
}

# ─── 요원 관계 그래프 (V26A2 메타 스냅샷) ────────────────────────────────────
# counter:  A가 B의 핵심 유틸을 구조적으로 무력화
# replaces: A가 B의 역할을 더 효율적으로 수행 (동일 슬롯 경쟁에서 우위)
# competes: 같은 팀 슬롯을 놓고 경쟁하는 요원 집합
# suppressed_by: 이 요원이 현재 메타에서 억압받는 원인들
AGENT_RELATIONS = {
    "Killjoy": {
        "suppressed_by": [
            {
                "agent": "Yoru",
                "type": "counter",
                "reason": "요루 텔포가 나노스웜·알람봇·포탑 전체를 무시하고 진입 가능 → 설치물 전략 가치 0",
            },
            {
                "agent": "Vyse",
                "type": "replaces",
                "reason": "킬조이 주요 맵(헤이븐·스플릿)에서 바이스가 CC+설치물 모두 우위 → 구조적 상위호환",
            },
            {
                "agent": "Tejo",
                "type": "counter",
                "reason": "테호 정밀 폭격이 설치물을 안전 거리에서 제거 가능",
            },
        ],
    },
    "Cypher": {
        "suppressed_by": [
            {
                "agent": "Yoru",
                "type": "counter",
                "reason": "요루 텔포가 트랩 와이어·스파이캠을 무시하고 진입 → 정보망 전체 붕괴",
            },
            {
                "agent": "Tejo",
                "type": "counter",
                "reason": "정밀 폭격으로 카메라·와이어 제거 가능",
            },
        ],
    },
    "Jett": {
        "suppressed_by": [
            {
                "agent": "Waylay",
                "type": "replaces",
                "reason": "웨이레이가 이동기+시야교란+팀 기여를 동시에 제공 → 제트의 이동기 니치 완전 대체",
            },
            {
                "agent": "Neon",
                "type": "replaces",
                "reason": "네온이 S급 연막+CC+이동기 삼박자 → 제트보다 팀 유틸 기여 훨씬 높음",
            },
        ],
    },
    "Sova": {
        "suppressed_by": [
            {
                "agent": "Tejo",
                "type": "competes",
                "reason": "테호가 정보+광역피해를 동시에 제공 → 소바의 정보 역할을 일부 대체. 단 소바는 '대체 불가' 레벨",
            },
        ],
        "resilience_note": "정보 획득 자체는 대체 불가 → 픽률 바닥 존재. 완전 대체 아님.",
    },
    "Sage": {
        "structural_weakness": "힐(C급)+부활(C급) 위주 킷 → 수치 조정만으론 메타 진입 한계. 리워크 없이는 구조적 저픽.",
    },
    "Phoenix": {
        "structural_weakness": "팀 유틸 전무 + 자가힐 의존 설계. 메타가 팀 조율 중심으로 이동할수록 가치 하락.",
        "suppressed_by": [
            {
                "agent": "Neon",
                "type": "replaces",
                "reason": "네온이 더 강한 이동기+연막+CC → 피닉스의 화염 장판은 B급 유틸로 경쟁 불가",
            },
        ],
    },
    "Harbor": {
        "suppressed_by": [
            {
                "agent": "Viper",
                "type": "competes",
                "reason": "연막 전략가 슬롯에서 바이퍼의 독 압박+맵 구역 봉쇄가 하버보다 우위",
            },
            {
                "agent": "Omen",
                "type": "competes",
                "reason": "오멘이 연막+이동기 콤보로 더 높은 범용성 제공",
            },
        ],
    },
    "Chamber": {
        "suppressed_by": [
            {
                "agent": "Deadlock",
                "type": "competes",
                "reason": "데드록이 CC 중심 감시자로 더 높은 팀 기여 제공",
            },
            {
                "agent": "Vyse",
                "type": "competes",
                "reason": "바이스가 CC+S급 울트로 감시자 슬롯 경쟁",
            },
        ],
        "structural_weakness": "너프 이후 생존력 저하 → 저격 특화 가치만 남음.",
    },
    "Neon": {
        "dominance_note": "S급 연막 + CC + 이동기 = 타격대 최고 킷 가치(3.25). 랭크/대회 모두 고픽 → 너프 압박.",
    },
    "Breach": {
        "dominance_note": "S급 CC 3개 보유. 팀 조율 시 최강 개전 요원. 프로 메타 핵심.",
    },
    "Yoru": {
        "meta_impact": "텔포가 감시자 전체 설치물 무력화 → 감시자 픽률 억압 주원인.",
    },
    "Gekko": {
        "buff_note": "팀 기여 높고 설치 보조 내장. 랭크/대회 픽률 모두 낮음 → 버프 필요. 스킬 재사용 고유 메커니즘 잠재력 미발휘.",
    },
    "Veto": {
        "meta_impact": "투사체 파괴(요격기)로 소바·테호·브리치 등 투사체 의존 요원 유틸 차단. 지름길로 팀 진입 경로 창출.",
        "suppressed_by": [
            {
                "agent": "Sova",
                "type": "competes",
                "reason": "정보 획득 측면에서 소바와 척후대 슬롯 경쟁",
            },
        ],
    },
    "Miks": {
        "meta_impact": "음파 연막 + CC + 팀 버프 복합 킷. 척후대+전략가 혼합 역할. 신규 요원으로 메타 데이터 부족.",
        "suppressed_by": [
            {
                "agent": "Breach",
                "type": "competes",
                "reason": "CC 척후대 슬롯에서 브리치의 S급 CC 3개와 경쟁",
            },
        ],
    },
}

# ─── 레이블 빌더 ──────────────────────────────────────────────────────────────

def dominant_skill(patch_rows):
    """패치에서 가장 중요한 스킬 키 반환"""
    nb = patch_rows[patch_rows["direction"].isin(["nerf","buff"])]
    if nb.empty:
        return "multi"
    weights = nb["skill_key"].map(lambda k: SKILL_WEIGHT.get(k, 1.0))
    best_idx = weights.idxmax()
    sk = nb.loc[best_idx, "skill_key"]
    return sk if sk in ("E","Q","C","X") else "multi"

def dominant_trigger(patch_rows):
    """패치에서 주된 trigger_type 반환"""
    nb = patch_rows[patch_rows["direction"].isin(["nerf","buff"])]
    if nb.empty:
        return "rank"
    nb = nb.dropna(subset=["trigger_type"])
    if nb.empty:
        return "rank"
    counts = nb["trigger_type"].value_counts()
    if counts.empty:
        return "rank"
    t = counts.index[0]
    # 단순화: pro_dominance / rank_stat / role_invasion / new_release
    if t == "pro_dominance":  return "pro_dom"
    if t == "role_invasion":  return "role_inv"
    if t == "skill_ceiling":  return "skill_ceil"
    return "rank"

def classify_stable_state(feat):
    """
    패치 없는 stable 케이스를 수치 기준으로 세분화
    → 모델이 "강한데 안 패치됨" / "약한데 안 패치됨" 을 노이즈로 학습하지 않도록
    """
    rank_pr      = float(feat.get("rank_pr", 0) or 0)
    vct_pr       = float(feat.get("vct_pr_last", 0) or 0)
    rank_wr_vs50 = float(feat.get("rank_wr_vs50", 0) or 0)
    vct_profile  = feat.get("vct_profile", "")

    # 강한 요원인데 아직 패치 안 됨
    if rank_pr > 12 or vct_pr > 35 or rank_wr_vs50 > 3.0:
        return "stable_strong"

    # 약한 요원 (양쪽 다 낮음)
    if rank_pr < 3.0 and vct_pr < 3.0 and vct_profile not in ("pro_absent", "pro_unknown"):
        return "stable_weak"

    return "stable_balanced"


def detect_context(agent, target_act_idx, step1_df):
    """
    과거 verdict 이력을 보고 패치 컨텍스트 결정
      correction: 이전 패치가 OVERSHOOT이었음
      followup:   이전 패치가 MISS/DUAL_MISS였음
      first:      이전 패치 없거나 HIT → 새 패치
    """
    hist = step1_df[
        (step1_df["agent"] == agent) &
        (step1_df["patch_act_idx"] < target_act_idx)
    ].sort_values("patch_act_idx")

    if hist.empty:
        return "first"

    last = hist.iloc[-1]
    cv = last.get("combined_verdict", "UNKNOWN")
    direction = last.get("direction", "")

    if "OVERSHOOT" in cv:
        return "correction"
    if "MISS" in cv and direction in ("buff", "nerf"):
        return "followup"
    return "first"

def check_rework_needed(feat):
    """
    랭크도 VCT도 안 나오는 요원 → 수치 조정 한계, rework 필요

    조건:
      rank_pr < 2%  AND  vct_pr < 2%
      AND 과거 평균(rank_pr_avg3)도 낮음  ← 원래부터 안 쓰였음
      AND 급격한 하락 중이 아님           ← 과너프 저점 제외
    """
    rank_pr      = float(feat.get("rank_pr")      or 0)
    vct_pr       = float(feat.get("vct_pr_last")  or 0)
    rank_pr_avg3 = float(feat.get("rank_pr_avg3") or rank_pr)
    rank_slope   = float(feat.get("rank_pr_slope") or 0)

    if rank_pr >= 2.0 or vct_pr >= 2.0:
        return False

    # 과거에 한 번이라도 인기 있었으면 → 과너프 후 일시적 저점 (테호 류)
    rank_pr_peak = float(feat.get("rank_pr_peak") or 0)
    if rank_pr_peak > 5.0:
        return False

    # 최근 3액트 평균이 높은데 현재만 낮음 → 너프 직후 저점
    if rank_pr_avg3 > 3.0 and rank_pr < rank_pr_avg3 * 0.5:
        return False

    # 급격한 하락세 → 너프 직후 저점
    if rank_slope < -1.5:
        return False

    return True

def build_patch_label(agent, target_act_idx, patch_rows, step1_df, feat):
    """
    단일 (요원, 다음 액트) 에 해당하는 패치 레이블 생성
    patch_rows: 해당 요원, 해당 액트의 실제 패치 행들
    feat: 현재 액트 기준 피처 (rework 판정에 사용)
    """
    nb = patch_rows[patch_rows["direction"].isin(["nerf","buff"])]
    if nb.empty:
        return "stable", {}

    direction = "nerf" if (nb["direction"] == "nerf").sum() >= (nb["direction"] == "buff").sum() else "buff"
    skill   = dominant_skill(nb)
    trigger = dominant_trigger(nb)
    context = detect_context(agent, target_act_idx, step1_df)

    # rework: 랭크도 VCT도 안 나오는 요원
    if check_rework_needed(feat):
        label = "rework"
    elif context == "correction":
        label = f"correction_{direction}"
    elif context == "followup":
        label = f"{direction}_{skill}_{trigger}_followup"
    else:
        label = f"{direction}_{skill}_{trigger}"

    meta = {
        "label_direction": direction,
        "label_skill":     skill,
        "label_trigger":   trigger,
        "label_context":   context,
    }
    return label, meta


# ─── 피처 빌더 ───────────────────────────────────────────────────────────────

def precompute_map_versatility(map_raw_df):
    """all_agents_map_stats 기반 맵 다양성 지표 사전 계산

    Returns dict: (act, agent) → {map_versatility, map_hhi, map_specialist}
    - map_versatility : 해당 액트에서 플레이한 맵 수
    - map_hhi         : 허핀달 집중도 0(균등분산)~1(한 맵 독점)
    - map_specialist  : 1개 맵이 전체 픽의 50%+ → 전문 맵 요원
    """
    result = {}
    df = map_raw_df[map_raw_df["map"] != "ALL"].copy()
    for (act, agent), grp in df.groupby(["act", "agent"]):
        total = grp["matches"].sum()
        if total == 0:
            continue
        n = len(grp)
        shares = grp["matches"] / total
        hhi_raw  = float((shares ** 2).sum())
        hhi_norm = (hhi_raw - 1/n) / (1 - 1/n) if n > 1 else 1.0
        result[(act, agent)] = {
            "map_versatility": n,
            "map_hhi":         round(hhi_norm, 4),
            "map_specialist":  float(shares.max() > 0.5),
        }
    return result

def compute_vct_profile(vct_pre_avg):
    if vct_pre_avg is None or (isinstance(vct_pre_avg, float) and np.isnan(vct_pre_avg)):
        return "pro_unknown"
    v = float(vct_pre_avg)
    if   v >= 15: return "pro_staple"
    elif v >= 5:  return "pro_viable"
    elif v >= 1:  return "pro_marginal"
    else:         return "pro_absent"

def build_features(agent, act_idx, rank_df, vct_df, step1_df, map_dep_df=None,
                   map_versatility_dict=None, pn_df=None):
    """
    (요원, 액트) 기준 현재 상태 피처 계산
    """
    feat = {}

    # ── 랭크 피처 (현재 액트 기준) ──
    ag_rank = rank_df[rank_df["agent"] == agent].sort_values("act_idx")
    all_hist = ag_rank[ag_rank["act_idx"] <= act_idx]
    cur_rank = all_hist.tail(3)
    if not cur_rank.empty:
        latest = cur_rank.iloc[-1]
        feat["rank_pr"]       = float(latest["pick_rate_pct"])
        feat["rank_wr"]       = float(latest["win_rate_pct"])
        feat["rank_wr_vs50"]  = float(latest["win_rate_pct"]) - 50.0
        if len(cur_rank) >= 2:
            pr_vals = cur_rank["pick_rate_pct"].values
            x = np.arange(len(pr_vals))
            feat["rank_pr_slope"] = float(np.polyfit(x, pr_vals, 1)[0])
        else:
            feat["rank_pr_slope"] = 0.0
        feat["rank_pr_avg3"] = float(cur_rank["pick_rate_pct"].mean())
        # 전체 이력 중 최고 픽률 (과너프 저점 구분용)
        feat["rank_pr_peak"] = float(all_hist["pick_rate_pct"].max())

    # ── VCT 피처 ──
    ag_vct = vct_df[vct_df["agent"] == agent].sort_values(["act_idx","event_order"])
    pre_vct = ag_vct[ag_vct["act_idx"] <= act_idx]
    if not pre_vct.empty:
        last_ev = pre_vct.iloc[-1]
        feat["vct_pr_last"]  = float(last_ev["pick_rate_pct"])
        feat["vct_wr_last"]  = float(last_ev["win_rate_pct"])
        feat["vct_pr_avg"]   = float(pre_vct.tail(3)["pick_rate_pct"].mean())
        feat["vct_pre_n"]    = len(pre_vct)
    else:
        feat["vct_pr_last"] = 0.0
        feat["vct_wr_last"] = np.nan
        feat["vct_pr_avg"]  = 0.0
        feat["vct_pre_n"]   = 0

    feat["vct_profile"] = compute_vct_profile(feat.get("vct_pr_avg"))

    # 역대 VCT 픽률 최고치: "솔로 캐리 설계(레이나 전구간 0~4%)" vs "너프/메타로 밀린 것(제트/레이즈 역대 60%+)" 구분용
    feat["vct_pr_peak_all"] = float(pre_vct["pick_rate_pct"].max()) if not pre_vct.empty else 0.0

    # VCT 트렌드 (최근 3이벤트 픽률 기울기)
    recent_vct = pre_vct.tail(3)
    if len(recent_vct) >= 2:
        vpr = recent_vct["pick_rate_pct"].values
        feat["vct_pr_slope"] = float(np.polyfit(np.arange(len(vpr)), vpr, 1)[0])
    else:
        feat["vct_pr_slope"] = 0.0

    # 랭크 vs VCT 갭 (프로 선호도 vs 일반)
    if "rank_pr" in feat and feat.get("vct_pr_avg", 0) > 0:
        feat["rank_vct_gap"] = feat["rank_pr"] - feat["vct_pr_avg"]
    else:
        feat["rank_vct_gap"] = np.nan

    # ── Step 1 이력 피처 ──
    hist = step1_df[
        (step1_df["agent"] == agent) &
        (step1_df["patch_act_idx"] <= act_idx)
    ].sort_values("patch_act_idx")

    feat["n_total_patches"]    = len(hist)
    feat["n_nerf_patches"]     = int((hist["direction"] == "nerf").sum())
    feat["n_buff_patches"]     = int((hist["direction"] == "buff").sum())

    if not hist.empty:
        feat["acts_since_patch"] = act_idx - int(hist["patch_act_idx"].max())
    elif pn_df is not None:
        # step1에 없는 요원(패치 이력 없음): patch_notes 직접 조회 (neutral 포함)
        pn_agent = pn_df[(pn_df["agent"] == agent) & (pn_df["act_idx"] <= act_idx)]
        feat["acts_since_patch"] = (act_idx - int(pn_agent["act_idx"].max())) if not pn_agent.empty else 99
    else:
        feat["acts_since_patch"] = 99

    if not hist.empty:
        last = hist.iloc[-1]
        feat["last_direction"]     = last.get("direction", "none")
        feat["last_combined"]      = last.get("combined_verdict", "UNKNOWN")
        feat["last_rank_verdict"]  = last.get("rank_verdict", "NO_DATA")
        feat["last_vct_verdict"]   = last.get("vct_verdict", "NO_DATA")
        feat["last_max_skill_w"]   = float(last.get("max_skill_weight", 2.0) or 2.0)
        # 마지막 패치의 trigger_type: 왜 패치했는지 원인
        # buff/nerf 행만 대상, neutral(버그픽스/UI) 제외
        last_act_idx = int(hist["patch_act_idx"].max())
        if pn_df is not None:
            pn_last = pn_df[
                (pn_df["agent"] == agent) &
                (pn_df["act_idx"] == last_act_idx) &
                (pn_df["direction"].isin(["nerf", "buff"]))
            ]
            feat["last_trigger_type"] = dominant_trigger(pn_last)
        else:
            feat["last_trigger_type"] = "rank"
    else:
        feat["last_direction"]     = "none"
        feat["last_combined"]      = "UNKNOWN"
        feat["last_rank_verdict"]  = "NO_DATA"
        feat["last_vct_verdict"]   = "NO_DATA"
        feat["last_max_skill_w"]   = 2.0
        feat["last_trigger_type"]  = "rank"

    # 최근 4액트 내 DUAL_MISS 누적 (rework 신호)
    recent4 = hist[hist["patch_act_idx"] >= act_idx - 4]
    feat["recent_dual_miss_count"] = int(
        recent4["combined_verdict"].isin(["DUAL_MISS","RANK_ONLY_MISS"]).sum()
    )
    feat["recent_buff_fail_count"] = int(
        (recent4["combined_verdict"].isin(["DUAL_MISS","RANK_ONLY_MISS"]) &
         (recent4["direction"] == "buff")).sum()
    )

    # 최근 연속 방향 (같은 방향이 반복되면 누적 압박)
    if not hist.empty:
        directions = hist["direction"].tolist()
        streak = 1
        for i in range(len(directions)-2, -1, -1):
            if directions[i] == directions[-1]:
                streak += 1
            else:
                break
        feat["patch_streak"]           = streak
        feat["patch_streak_direction"] = directions[-1]
    else:
        feat["patch_streak"]           = 0
        feat["patch_streak_direction"] = "none"

    # ── 맵 의존도 피처 ─────────────────────────────────────────────────────────
    # 맵풀에서 빠진 맵이 top_map이면 VCT 픽률 하락이 약해서가 아닐 수 있음
    # 단, VCT 픽률이 이미 높으면 (15%+) 맵풀 관계없이 요원이 강한 것이므로 제외
    if map_dep_df is not None:
        act_name = IDX_ACT.get(act_idx)
        row = map_dep_df[(map_dep_df["agent"] == agent) & (map_dep_df["act"] == act_name)]
        if not row.empty:
            r = row.iloc[0]
            feat["map_dep_score"]       = float(r["map_dep_score"])
            feat["top_map_in_rotation"] = int(r["in_rotation"])
            feat["effective_map_dep"]   = float(r["effective_map_dep"])
            # 맵풀 부재가 VCT 픽률 하락을 설명하는지 여부
            # top_map이 VCT 맵풀 밖이고 VCT 픽률 < 15%일 때만 의미 있음
            # (요루처럼 픽률이 이미 높으면 맵풀 관계없이 강한 요원임)
            vct_low = float(feat.get("vct_pr_last", 0) or 0) < 15.0
            feat["map_explains_vct_drop"] = float(r["map_dep_score"]) if (
                int(r["in_rotation"]) == 0 and vct_low
            ) else 0.0
        else:
            feat["map_dep_score"]         = 1.0
            feat["top_map_in_rotation"]   = 1
            feat["effective_map_dep"]     = 1.0
            feat["map_explains_vct_drop"] = 0.0
    else:
        feat["map_dep_score"]         = 1.0
        feat["top_map_in_rotation"]   = 1
        feat["effective_map_dep"]     = 1.0
        feat["map_explains_vct_drop"] = 0.0

    # ── 프로 vs 랭크 픽률 비율 & 구조적 불균형 피처 ──────────────────────────────
    # pro_rank_ratio: 높을수록 대회 편향(Viper/Breach), 낮을수록 랭크 편향(Reyna/Jett)
    vct_pr_last_ = float(feat.get("vct_pr_last", 0) or 0)
    rank_pr_      = float(feat.get("rank_pr", 0) or 0)
    feat["pro_rank_ratio"] = vct_pr_last_ / max(rank_pr_, 0.5)

    # ── 요원 정체성 피처 (AGENT_DESIGN 기반, 설계 의도 직접 인코딩) ──────────────
    # 통계로 역추정(vct_pr_peak_all 등)하는 것보다 명확하고 신규 요원에도 적용 가능
    design = AGENT_DESIGN.get(agent, _DEFAULT_DESIGN)
    audience = design["design_audience"]
    feat["agent_team_synergy"]  = design["team_synergy"]
    feat["agent_complexity"]    = design["complexity"]
    feat["agent_replaceability"]= design.get("replaceability", 0.5)
    # design_rank_only / design_pro_only: 레이블 생성(classify_stable_state)에만 사용
    # 모델 피처에서는 DROP_COLS로 제외 — 고정 분류가 메타 변화에 대응 못 하는 문제
    feat["design_rank_only"]    = 1.0 if audience == "rank" else 0.0  # 레이나, 아이소
    feat["design_pro_only"]     = 1.0 if audience == "pro"  else 0.0  # 바이퍼, 아스트라, 브리치, 소바, 스카이, 데드록
    # "both" 요원인데 도메인 저픽 → 설계 의도 대비 이상 → 패치 신호
    rank_low  = rank_pr_ < 3.0
    vct_low   = vct_pr_last_ < 5.0
    is_both   = (audience == "both")
    is_rank   = (audience == "rank")
    is_pro    = (audience == "pro")
    # 랭크 저픽이 설계로 설명 안 됨: pro-only도 rank-only도 아닌데 랭크도 낮음
    feat["rank_low_unexpected"] = float(rank_low and not is_pro and not is_rank)
    # VCT 저픽이 설계로 설명 안 됨: rank-only가 아닌데 VCT도 낮음
    feat["vct_low_unexpected"]  = float(vct_low and not is_rank)
    # 양쪽 다 낮은데 "both" 설계 → 가장 강한 버프 신호 (게코 류)
    feat["both_weak_signal"]    = float(rank_low and vct_low and is_both)

    # ── 킷 가치 피처 (AGENT_KIT 기반, 스킬 등급 S/A/B/C) ──────────────────────
    # kit_score: 스킬 등급 가중 평균 (1.75=세이지/레이나 ~ 3.75=브리치)
    # 낮은 kit_score + 낮은 픽률 → 수치 조정 한계, rework 가능성
    # 높은 kit_score + 높은 픽률 → 구조적 너프 압박
    feat["kit_score"] = compute_kit_score(agent)
    flags = get_kit_flags(agent)
    feat["has_smoke"]           = float(flags["has_smoke"])
    feat["has_cc"]              = float(flags["has_cc"])
    feat["has_info"]            = float(flags["has_info"])
    feat["has_mobility"]        = float(flags["has_mobility"])
    feat["has_heal"]            = float(flags["has_heal"])
    feat["has_revive"]          = float(flags["has_revive"])
    feat["high_value_smoke"]    = float(flags["high_value_smoke"])
    feat["high_value_cc"]       = float(flags["high_value_cc"])
    # 킷 가치 vs 현재 픽률 불일치:
    # 고가치 킷인데 픽률 낮음 → 메타 억압 가능성 (대체/카운터 당하는 중)
    # 저가치 킷인데 픽률 높음 → 구조적 OP, 수치 인플레 가능성
    feat["kit_pr_gap"] = feat["kit_score"] - (rank_pr_ / 5.0)  # 정규화된 픽률과의 차이
    # 대체 가능성 × 픽률: 대체 쉽고 픽률도 낮음 → 메타 이탈 신호
    feat["replaceable_low_pr"]  = float(design.get("replaceability", 0.5) > 0.6 and rank_low)
    # C급 스킬(힐/부활) 보유 + 저픽 → 구조적 한계, rework 필요 신호
    low_value_kit = feat["kit_score"] < 2.3
    feat["low_kit_weak_signal"] = float(low_value_kit and rank_low and vct_low)

    # ── 요원 종합 티어 (역할 수행도·실전 제약 반영) ─────────────────────────────
    feat["agent_tier_score"] = AGENT_TIER_SCORE.get(design.get("agent_tier", "B"), 2)
    # kit_score(이론치) vs agent_tier_score(실전치) 괴리
    # 양수: 이론 > 실전 (브리치형 - 선딜/조율 제약), 음수: 실전 > 이론 (메타 변수 존재)
    feat["tier_gap"] = round(feat["kit_score"] - feat["agent_tier_score"], 3)
    # 오퍼 시너지: 이동기로 오퍼 피크-탈출 가능 → 킷 밖 영역 지배력 보유
    feat["op_synergy"] = float(design.get("op_synergy", False))
    # 맵 지오메트리 시너지: 배치 각도/위치에 따라 스킬 실질 가치 증폭
    feat["geo_synergy"] = {"high": 2.0, "medium": 1.0, "low": 0.0}.get(
        design.get("geo_synergy", "medium"), 1.0
    )
    # geo_bonus: geo_ceiling > tier 인 스킬들의 잠재 추가 가치 합산
    _geo_bonus = 0
    for _slot, _sk in AGENT_KIT.get(agent, _DEFAULT_KIT).items():
        if "geo_ceiling" in _sk:
            _geo_bonus += SKILL_TIER_SCORE.get(_sk["geo_ceiling"], 2) - SKILL_TIER_SCORE.get(_sk["tier"], 2)
    feat["geo_bonus"] = float(_geo_bonus)

    # ── 킷 × 픽률 교차 피처 ─────────────────────────────────────────────────────
    # 정적 킷 플래그 단독으로는 SHAP 기여 없음 → 현재 픽률 흐름과 교차해야 패치 신호 포착
    #
    # [너프 신호]
    # S급 연막 + VCT 고픽 → 구조적 지배력, 너프 압박
    feat["smoke_vct_dom"] = float(flags["high_value_smoke"]) * min(vct_pr_last_ / 10.0, 3.0)
    # 이동기 + 랭크 고픽 → 솔로 캐리 이동기 OP, 너프 위험
    feat["mobility_rank_dom"] = float(flags["has_mobility"]) * min(rank_pr_ / 5.0, 3.0)
    # 킷 등급 × 랭크 픽률 연속값 → 높을수록 너프 압박
    feat["kit_x_rank_pr"] = round(feat["kit_score"] * min(rank_pr_ / 5.0, 3.0), 3)
    #
    # [버프/리워크 신호]
    # 힐 보유 + 랭크 저픽 → 킷 가치 있는데 안 쓰임 → 수치 문제
    feat["heal_low_rank"] = float(flags["has_heal"] and rank_pr_ < 3.0)
    # 부활 보유 + 랭크 저픽 → 세이지형 구조적 한계
    feat["revive_low_rank"] = float(flags["has_revive"] and rank_pr_ < 3.0)
    # 정보 요원 + VCT 저픽 (VCT 데이터 있을 때만) → 정보력 가치 없어진 메타
    feat["info_low_vct"] = float(flags["has_info"] and vct_pr_last_ < 5.0 and vct_pr_last_ > 0)
    # CC 요원 + 랭크 저픽 → 선딜/조율 구조적 한계, 수치 조정 필요
    feat["cc_low_rank"] = float(flags["has_cc"] and rank_pr_ < 2.0)
    # 연막 요원 + VCT 저픽 → 대체 연막에 밀린 상황, 버프 신호
    feat["smoke_low_vct"] = float(flags["has_smoke"] and vct_pr_last_ < 3.0)

    # rank_dominant_flag: design_rank_only 복사본. 둘 다 DROP_COLS에서 제외됨
    feat["rank_dominant_flag"] = feat["design_rank_only"]

    # 실력 천장 피처: 1~10 정수 → 0.0~1.0 정규화
    # 장인 효과가 큰 요원은 평균 랭크 통계가 실제 가치를 과소평가 → 너프 신호 완화에 사용
    _sc_raw = design.get("skill_ceiling", 5)
    feat["skill_ceiling_score"] = int(_sc_raw) / 10.0

    # 잠재적 대회 편향 요원: design_pro_only OR 역대 VCT 픽률 높음
    vct_peak_ = float(feat.get("vct_pr_peak_all", 0) or 0)
    feat["pro_dominant_flag"] = 1.0 if (
        is_pro or (vct_pr_last_ > 5.0 or vct_peak_ > 20.0) and rank_pr_ < 3.0
    ) else 0.0

    # ── 맵 다양성 피처 (all_agents_map_stats 기반) ─────────────────────────────
    # map_versatility : 플레이한 맵 수 (많을수록 범용 → 너프 압박 ↑)
    # map_hhi         : 허핀달 집중도 0(균등)~1(한맵 독점) (높을수록 전문 맵 요원)
    # map_specialist  : 1개 맵 의존도 50%+ → 전체 픽률로 버프/너프 판단 오류 방지
    # specialist_low_pr: 전문 맵 요원인데 픽률 낮음 → 맵풀 탓, 버프 신호 아님
    if map_versatility_dict is not None:
        act_name_mv = IDX_ACT.get(act_idx)
        mv = map_versatility_dict.get((act_name_mv, agent), {})
        feat["map_versatility"]   = float(mv.get("map_versatility", 5))
        feat["map_hhi"]           = float(mv.get("map_hhi", 0.3))
        feat["map_specialist"]    = float(mv.get("map_specialist", 0.0))
        feat["specialist_low_pr"] = float(mv.get("map_specialist", 0.0) == 1.0 and rank_low)
        # 범용성(1-hhi) × 픽률 연속값 → 전 맵에서 많이 나올수록 너프 압박
        # hhi 높음(맵 고착화) → 값 눌림 → 안정 신호 / hhi 낮음 + 픽률 높음 → 너프 신호
        feat["versatile_nerf_signal"] = round(
            (1.0 - float(mv.get("map_hhi", 0.3))) * min(rank_pr_ / 5.0, 3.0), 3
        )
    else:
        feat["map_versatility"]   = 5.0
        feat["map_hhi"]           = 0.3
        feat["map_specialist"]    = 0.0
        feat["specialist_low_pr"] = 0.0
        feat["versatile_high_pr"] = 0.0

    # ── 전성기 대비 현재 픽률 비율 ───────────────────────────────────────────────
    # 낮을수록 전성기 대비 많이 쇠퇴 → 과너프 피해자일 가능성
    rank_pr      = float(feat.get("rank_pr", 0) or 0)
    rank_pr_peak = float(feat.get("rank_pr_peak", 0) or 0)
    feat["rank_pr_vs_peak"] = rank_pr / rank_pr_peak if rank_pr_peak > 0 else 1.0

    # ── 상호작용 파생 피처 ─────────────────────────────────────────────────────
    # 방향 × 결과 코드: 모델이 "버프 후 MISS" vs "너프 후 MISS" 를 구분하도록
    # buff+HIT→+2, buff+MISS→+1, buff+FAIL→+0.5
    # nerf+HIT→-2, nerf+MISS→-1, nerf+FAIL→-0.5
    # none→0
    d = feat.get("last_direction", "none")
    c = feat.get("last_combined", "UNKNOWN")

    # 명시적 방향+결과 플래그 (Stage B 방향 혼동 방지)
    # last_combined="DUAL_MISS" 만으로는 버프 후인지 너프 후인지 모호 → dir_verdict_code로 보완
    # 이 플래그는 Stage B에서 nerf_followup vs buff_followup 구분의 핵심 신호
    feat["buff_miss_flag"] = 1.0 if (d == "buff" and c in ("DUAL_MISS","RANK_ONLY_MISS")) else 0.0
    feat["nerf_miss_flag"] = 1.0 if (d == "nerf" and c in ("DUAL_MISS","RANK_ONLY_MISS")) else 0.0
    feat["buff_hit_flag"]  = 1.0 if (d == "buff" and c in ("DUAL_HIT","RANK_ONLY_HIT"))  else 0.0
    feat["nerf_hit_flag"]  = 1.0 if (d == "nerf" and c in ("DUAL_HIT","RANK_ONLY_HIT"))  else 0.0
    hit_types  = ("DUAL_HIT", "RANK_ONLY_HIT")
    miss_types = ("DUAL_MISS", "RANK_ONLY_MISS")
    fail_types = ("PRO_FAIL", "RANK_FAIL", "MIXED")
    if d == "buff":
        if c in hit_types:  dir_verdict_code = +2.0
        elif c in miss_types: dir_verdict_code = +1.0
        elif c in fail_types: dir_verdict_code = +0.5
        else: dir_verdict_code = 0.0
    elif d == "nerf":
        if c in hit_types:  dir_verdict_code = -2.0
        elif c in miss_types: dir_verdict_code = -1.0
        elif c in fail_types: dir_verdict_code = -0.5
        else: dir_verdict_code = 0.0
    else:
        dir_verdict_code = 0.0
    feat["dir_verdict_code"] = dir_verdict_code

    # 현재 강도 vs 패치 방향 신호
    # 음수: 방향 대비 약함 (버프했는데 여전히 약함 → 추가 버프 필요)
    # 양수: 방향 대비 강함 (너프했는데 여전히 강함 → correction/추가 너프)
    wr_vs50 = float(feat.get("rank_wr_vs50", 0) or 0)
    if d == "buff":
        feat["strength_vs_direction"] = wr_vs50      # 낮을수록 여전히 약함
    elif d == "nerf":
        feat["strength_vs_direction"] = -wr_vs50     # 높을수록 여전히 강함
    else:
        feat["strength_vs_direction"] = 0.0

    return feat


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("Step 2 Training Data Builder")
    print("=" * 65 + "\n")

    # ── 데이터 로드 ──
    rank_v   = pd.read_csv("agent_act_history_all.csv")
    rank_m   = pd.read_csv("maxmunzy_diamond_plus.csv")
    vct_raw  = pd.read_csv("vct_summary.csv")
    pn       = pd.read_csv("patch_notes_classified.csv")
    step1    = pd.read_csv("training_data.csv")
    map_dep  = pd.read_csv("map_dependency_scores.csv")
    map_raw  = pd.read_csv("all_agents_map_stats.csv")
    map_v_dict = precompute_map_versatility(map_raw)

    # ── 요원 이름 정규화 ──
    rank_v["agent"]  = rank_v["agent"].map(normalize_agent)
    rank_m["agent"]  = rank_m["agent"].map(normalize_agent)
    vct_raw["agent"] = vct_raw["agent"].map(normalize_agent)
    if "agent" in pn.columns:
        pn["agent"] = pn["agent"].map(normalize_agent)
    if "agent" in step1.columns:
        step1["agent"] = step1["agent"].map(normalize_agent)

    # 랭크 통합
    rv = rank_v[rank_v["note"] == "ok"].copy()
    rv = rv.rename(columns={"act":"act_name","win_rate":"win_rate_pct"})
    rv["act_idx"] = rv["act_name"].map(ACT_IDX)
    rm = rank_m.copy()
    rm["act_idx"] = rm["act_name"].map(ACT_IDX)
    vstats_keys = set(zip(rv["agent"], rv["act_name"]))
    rm_excl = rm[~rm.apply(lambda r: (r["agent"],r["act_name"]) in vstats_keys, axis=1)]
    common = ["agent","act_name","act_idx","win_rate_pct","pick_rate_pct"]
    rank_df = pd.concat(
        [rv[[c for c in common if c in rv.columns]],
         rm_excl[[c for c in common if c in rm_excl.columns]]],
        ignore_index=True
    ).sort_values(["agent","act_idx"])

    # VCT 통합
    vct_df = vct_raw.copy()
    vct_df["act_name"]    = vct_df["event"].map(VCT_TO_ACT)
    vct_df["act_idx"]     = vct_df["act_name"].map(ACT_IDX)
    vct_df["event_order"] = vct_df["event"].map(VCT_EVENT_ORDER)
    vct_df = vct_df.dropna(subset=["act_idx"])

    # Step 1 이력 (patch_act_idx 추가)
    step1["patch_act_idx"] = step1["patch_act"].map(ACT_IDX)

    # 패치 노트에 act_idx 매핑
    pn["act"]     = pn["patch"].astype(str).map(PATCH_TO_ACT)
    pn["act_idx"] = pn["act"].map(ACT_IDX)
    pn = pn.dropna(subset=["act_idx"])
    pn["act_idx"] = pn["act_idx"].astype(int)

    print(f"  랭크: {len(rank_df)}행 / VCT: {len(vct_df)}행")
    print(f"  패치노트: {len(pn)}행 / Step1: {len(step1)}행")

    # ── (요원, 액트) 쌍 생성 ──
    # 랭크 데이터가 있는 요원-액트만
    agent_acts = rank_df[["agent","act_name","act_idx"]].drop_duplicates()
    print(f"\n  (요원, 액트) 후보: {len(agent_acts)}쌍")

    # ── 패치 룩업 테이블: (agent, act_idx) → 패치 행들 ──
    # 다음 액트에 패치가 있는지 확인하기 위해 next_act_idx 기준으로 매핑
    patch_lookup = {}
    for _, row in pn.iterrows():
        key = (row["agent"], int(row["act_idx"]))
        if key not in patch_lookup:
            patch_lookup[key] = []
        patch_lookup[key].append(row)

    # ── 레이블 & 피처 조립 ──
    rows = []
    for _, aa in agent_acts.iterrows():
        agent   = aa["agent"]
        act     = aa["act_name"]
        act_idx = int(aa["act_idx"])

        # 다음 액트에 패치가 있나?
        next_act_idx = act_idx + 1
        patch_rows_list = patch_lookup.get((agent, next_act_idx), [])

        feat = build_features(agent, act_idx, rank_df, vct_df, step1, map_dep,
                              map_versatility_dict=map_v_dict, pn_df=pn)

        if patch_rows_list:
            patch_rows_df = pd.DataFrame(patch_rows_list)
            label, meta = build_patch_label(agent, next_act_idx, patch_rows_df, step1, feat)
        else:
            label = classify_stable_state(feat)  # stable_balanced / stable_strong / stable_weak
            meta  = {
                "label_direction": "none",
                "label_skill": "none",
                "label_trigger": "none",
                "label_context": "none",
                "label_has_rework": 0,
            }

        feat["agent"]    = agent
        feat["act"]      = act
        feat["act_idx"]  = act_idx
        feat["label"]    = label
        feat.update(meta)

        rows.append(feat)

    df = pd.DataFrame(rows)
    print(f"\n  생성: {len(df)}행 / {df.shape[1]}컬럼")

    # ── 레이블 분포 ──
    print("\n[레이블 분포]")
    vc = df["label"].value_counts()
    print(vc.to_string())

    # ── 레이블 그룹 집계 ──
    print("\n[방향별 집계]")
    df["label_group"] = df["label"].apply(lambda x:
        "stable" if x == "stable" else
        "rework" if x == "rework" else
        x.split("_")[0]  # nerf / buff / correction
    )
    print(df["label_group"].value_counts().to_string())

    # ── 저장 ──
    df.to_csv("step2_training_data.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: step2_training_data.csv  ({len(df)}행 x {df.shape[1]}컬럼)")

    # ── 샘플 확인 ──
    print("\n[패치 케이스 샘플]")
    patched = df[df["label"] != "stable"].sort_values(["agent","act_idx"])
    sample_cols = ["agent","act","rank_pr","vct_pr_last","vct_profile",
                   "last_combined","label"]
    print(patched[sample_cols].head(25).to_string(index=False))

    return df


if __name__ == "__main__":
    df = main()
