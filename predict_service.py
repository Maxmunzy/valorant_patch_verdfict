"""
predict_service.py
PatchPredictor — FastAPI 서비스용 예측 래퍼

predict_report.py의 로직을 클래스로 캡슐화.
- step2_pipeline.pkl (model_a / model_b / feat_cols_a / feat_cols_b / label_b_cats)
- step2_training_data.csv
- Claude Haiku API (설명 생성, 지연 로드 + 인메모리 캐시)
"""

from __future__ import annotations

import os
import json
import warnings
warnings.filterwarnings("ignore")

# .env 자동 로드 (ANTHROPIC_API_KEY 등)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _key = _k.strip()
                if not os.environ.get(_key):   # 없거나 빈 값이면 덮어씀
                    os.environ[_key] = _v.strip()

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import OrdinalEncoder
from anthropic import Anthropic

# ─── 요원 메타 데이터 ─────────────────────────────────────────────────────────
from agent_data import AGENT_DESIGN, _DEFAULT_DESIGN, AGENT_RELATIONS
from feature_builder import compute_kit_score, get_kit_flags

# ─── 상수 ────────────────────────────────────────────────────────────────────

BUFF_CLASSES = {"buff_followup", "buff_pro", "buff_rank", "correction_buff"}
NERF_CLASSES = {"nerf_followup", "nerf_pro", "nerf_rank", "correction_nerf"}

PATCH_TYPE_EN = {
    "buff_rank":        "Buff (Rank)",
    "buff_pro":         "Buff (Pro)",
    "buff_followup":    "Buff (Follow-up)",
    "correction_buff":  "Buff (Over-nerf Recovery)",
    "nerf_rank":        "Nerf (Rank)",
    "nerf_pro":         "Nerf (Pro)",
    "nerf_followup":    "Nerf (Follow-up)",
    "correction_nerf":  "Nerf (Over-buff Correction)",
    "rework":           "Rework",
    "stable":           "Stable",
}

PATCH_TYPE_KO = {
    "buff_rank":        "버프 (랭크)",
    "buff_pro":         "버프 (대회)",
    "buff_followup":    "버프 (추가)",
    "correction_buff":  "버프 (과너프 복구)",
    "nerf_rank":        "너프 (랭크)",
    "nerf_pro":         "너프 (대회)",
    "nerf_followup":    "너프 (추가)",
    "correction_nerf":  "너프 (과버프 조정)",
    "rework":           "리워크",
    "stable":           "안정",
}

AGENT_NAME_KO = {
    # 타격대
    "Jett":      "제트",
    "Reyna":     "레이나",
    "Raze":      "레이즈",
    "Neon":      "네온",
    "Phoenix":   "피닉스",
    "Iso":       "아이소",
    "Yoru":      "요루",
    "Waylay":    "웨이레이",
    # 전략가
    "Brimstone": "브림스톤",
    "Viper":     "바이퍼",
    "Omen":      "오멘",
    "Astra":     "아스트라",
    "Clove":     "클로브",
    "Harbor":    "하버",
    "Miks":      "믹스",
    # 감시자
    "Killjoy":   "킬조이",
    "Cypher":    "사이퍼",
    "Sage":      "세이지",
    "Chamber":   "챔버",
    "Deadlock":  "데드락",
    "Vyse":      "바이스",
    "Veto":      "베토",
    # 척후대
    "Sova":      "소바",
    "Skye":      "스카이",
    "Fade":      "페이드",
    "Breach":    "브리치",
    "KAYO":      "케이오",
    "KAY/O":     "케이오",
    "Gekko":     "게코",
    "Tejo":      "테호",
}

AGENT_ROLE_KO = {
    "Brimstone": "전략가", "Viper": "전략가", "Omen": "전략가",
    "Astra": "전략가", "Harbor": "전략가", "Clove": "전략가",
    "Killjoy": "감시자", "Cypher": "감시자", "Sage": "감시자",
    "Chamber": "감시자", "Deadlock": "감시자", "Vyse": "감시자",
    "Sova": "척후대", "Fade": "척후대", "Gekko": "척후대",
    "Breach": "척후대", "Skye": "척후대", "KAYO": "척후대",
    "KAY/O": "척후대", "Tejo": "척후대",
    "Phoenix": "타격대", "Reyna": "타격대", "Raze": "타격대",
    "Jett": "타격대", "Neon": "타격대", "Yoru": "타격대",
    "Iso": "타격대", "Waylay": "타격대",
    "Veto": "감시자", "Miks": "전략가",
}

def _vct_wr_safe(row, default: float = 50.0) -> float:
    """vct_wr_last는 0.0이 유효한 값 — `or` 패턴 금지, None 체크로 처리"""
    v = row.get("vct_wr_last", None)
    return float(v) if v is not None else default


CAT_COLS = [
    "vct_profile", "last_direction", "last_combined",
    "last_rank_verdict", "last_vct_verdict", "patch_streak_direction",
    "last_trigger_type",
]

PIPELINE_PATH  = "step2_pipeline.pkl"
DATA_PATH      = "step2_training_data.csv"
EXPLANATION_CACHE_PATH = "explanation_cache.json"

# ─── 맵 풀 & 요원 스킬 한국 공식명 ──────────────────────────────────────────
CURRENT_MAP_POOL = ["바인드", "브리즈", "프랙처", "헤이번", "로터스", "펄", "스플릿"]

# 한국 공식 스킬명: {에이전트: {슬롯: "한국어 이름"}} (주요 스킬만 기재)
AGENT_SKILLS_KO: dict[str, dict[str, str]] = {
    "Jett":      {"C": "구름 파열", "Q": "상승기류", "E": "돌풍", "X": "폭풍: 소환"},
    "Viper":     {"C": "포이즌 클라우드", "E": "톡식 스크린", "Q": "스네이크 바이트", "X": "바이퍼스 핏"},
    "Neon":      {"C": "빠른 차선", "Q": "릴레이 볼트", "E": "고속 기어", "X": "추월"},
    "Sova":      {"C": "정찰 드론", "Q": "충격 볼트", "E": "정찰 볼트", "X": "사냥꾼의 분노"},
    "Reyna":     {"C": "라르나카", "Q": "데보아/디스미스", "X": "황홀경"},
    "Raze":      {"C": "페인트 쉘", "Q": "블래스트 팩", "E": "붐봇", "X": "쇼스토퍼"},
    "Chamber":   {"C": "트레이드마크", "Q": "헤드헌터", "E": "랑데부", "X": "투어드포스"},
    "Killjoy":   {"C": "나노스웜", "Q": "알람봇", "E": "포탑", "X": "봉쇄 명령"},
    "Sage":      {"C": "슬로우 오브", "Q": "힐링 오브", "E": "방어막 오브", "X": "부활"},
    "Omen":      {"C": "어두운 장막", "Q": "편집증", "E": "수상한 이동", "X": "차원 이동"},
    "Skye":      {"C": "망설임", "Q": "치료의 불꽃", "E": "인도자", "X": "추적자"},
    "Fade":      {"C": "봉인", "Q": "침식", "E": "도청", "X": "야경"},
    "Breach":    {"C": "애프터쇼크", "Q": "플래시포인트", "E": "스틸포인트", "X": "롤링 썬더"},
    "KAYO":      {"C": "프래그먼트", "Q": "플래시/드라이브", "E": "제로/포인트", "X": "널/커맨드"},
    "Gekko":     {"C": "디플로", "Q": "윙맨", "E": "딕키", "X": "매그붐"},
    "Astra":     {"C": "성운", "Q": "동화", "E": "분열", "X": "우주의 형태"},
    "Brimstone": {"C": "인화성 연막", "Q": "자극성 연막", "E": "소이 연막", "X": "오비탈 타격"},
    "Harbor":    {"C": "캐스케이드", "Q": "코브", "E": "하이 타이드", "X": "렉트레스"},
    "Clove":     {"C": "피크-어-부", "Q": "메두들", "E": "노트 역자", "X": "역전"},
    "Tejo":      {"C": "스마트 와이어", "Q": "수직 타격기", "E": "강습 팩", "X": "정밀 폭격"},
    "Iso":       {"C": "언더커버", "Q": "더블 탭", "E": "킬 컨트랙트 준비", "X": "킬 컨트랙트"},
    "Deadlock":  {"C": "그래비넷", "Q": "소닉 센서", "E": "배리어 메시", "X": "앤나이얼레이션"},
    "Vyse":      {"C": "스테이시스 트랩", "Q": "아크 로즈", "E": "탐식하는 넝쿨", "X": "강철 정원"},
    "Cypher":    {"C": "사이버 케이지", "Q": "신경 절도", "E": "함정 선", "X": "신경 절도 (울트)"},
    "Phoenix":   {"C": "블레이즈", "Q": "커브볼", "E": "핫 핸즈", "X": "런 잇 백"},
    "Waylay":    {"C": "스냅 캐스트", "Q": "환영 달리기", "E": "차선 이탈", "X": "돌풍 운동"},
    "Yoru":      {"C": "갈 곳이 없다", "Q": "맹목", "E": "잠행", "X": "차원 관찰자"},
    "Miks":      {"C": "M-파동", "Q": "화음", "E": "웨이브폼", "X": "요동치는 베이스"},
}

# 현재 맵 풀에서 요원별 특화 맵 (map_pr >= 1.3 × 전체 평균)
# all_agents_map_stats.csv V26A2 기반 사전 계산 값
AGENT_MAP_AFFINITY: dict[str, list[str]] = {
    "Breach":    ["프랙처", "로터스"],
    "Brimstone": ["프랙처", "바인드"],
    "Chamber":   ["브리즈"],
    "Cypher":    ["스플릿", "바인드"],
    "Fade":      ["펄", "로터스"],
    "Killjoy":   ["헤이번", "프랙처", "펄"],
    "Omen":      ["헤이번", "로터스", "스플릿"],
    "Phoenix":   ["헤이번", "펄"],
    "Raze":      ["바인드", "로터스", "스플릿"],
    "Sage":      ["스플릿"],
    "Skye":      ["바인드", "스플릿"],
    "Sova":      ["브리즈", "헤이번"],
    "Viper":     ["브리즈"],
    "Yoru":      ["브리즈"],
}

# ─── 도메인 규칙 ──────────────────────────────────────────────────────────────

def _agent_type(rank_pr: float, vct_pr: float) -> str:
    """
    요원 유형 분류 (픽률 기반):
      pro_anchor  — VCT 고픽(≥15%) + 랭크 저픽(<5%): 유틸리티 앵커, 프로 전용
      both_active — 양쪽 모두 활성(rank≥5%, vct≥10%)
      rank_only   — 랭크 중심(rank≥5%, vct<5%)
      both_weak   — 양쪽 저픽
    """
    if vct_pr >= 15.0 and rank_pr < 5.0:
        return "pro_anchor"
    if rank_pr >= 5.0 and vct_pr >= 10.0:
        return "both_active"
    if rank_pr >= 5.0 and vct_pr < 5.0:
        return "rank_only"
    return "both_weak"


def apply_domain_rules(row: dict | pd.Series, p_patch: float,
                       p_buff_raw: float, p_nerf_raw: float):
    _acts_raw  = row.get("_raw_acts_since_patch", None)
    acts_since = int(_acts_raw) if _acts_raw is not None else int(row.get("acts_since_patch", 99) or 99)

    # 패치 직후 (acts_since=0): 랭크/VCT 결과가 아직 없는 상태 → 거의 강제 stable
    suppress = 0.15 if acts_since == 0 else 1.0
    p_patch_new = min(1.0, p_patch * suppress)

    # 방향은 모델 원본 출력 그대로 정규화
    total = p_buff_raw + p_nerf_raw
    if total > 0:
        p_buff_norm = p_buff_raw / total
        p_nerf_norm = p_nerf_raw / total
    else:
        p_buff_norm = p_nerf_norm = 0.5

    return p_patch_new, p_buff_norm, p_nerf_norm


# ─── 신호 추출 ────────────────────────────────────────────────────────────────

def _sig(type_: str, label: str, text: str, tag: str = "neutral") -> dict:
    return {"type": type_, "label": label, "text": text, "tag": tag}


def extract_signals(row: dict | pd.Series, verdict: str, last_patch_ver: str | None = None) -> list[dict]:
    """verdict에 대한 근거 신호 목록을 반환. label/text/tag 구조."""
    from agent_data import IDX_ACT
    agent        = row.get("agent", "")
    rank_pr      = float(row.get("rank_pr", 0) or 0)
    rank_pr_rel_meta = float(row.get("rank_pr_rel_meta", 1.0) or 1.0)
    # 표시용: % of games (rank_pr는 "전체 픽 슬롯 점유율"이므로 ×5 = 게임당 등장 비율)
    rank_pr_pct  = round(rank_pr * 5, 1)
    # 표시용: 패치 이후 누적 집계 우선, 없으면 최근 대회
    vct_pr       = float(row.get("vct_pr_post") or row.get("vct_pr_last", 0) or 0)
    rank_wr      = float(row.get("rank_wr_vs50", 0) or 0)
    rank_pr_peak = float(row.get("rank_pr_peak", 0) or 0)
    rank_pr_peak_pct = round(rank_pr_peak * 5, 1)
    rank_vs_peak = float(row.get("rank_pr_vs_peak", 1) or 1)
    buff_miss    = float(row.get("buff_miss_flag", 0) or 0)
    nerf_miss    = float(row.get("nerf_miss_flag", 0) or 0)
    buff_hit     = float(row.get("buff_hit_flag", 0) or 0)
    nerf_hit     = float(row.get("nerf_hit_flag", 0) or 0)
    both_weak    = float(row.get("both_weak_signal", 0) or 0)
    skill_ceil   = float(row.get("skill_ceiling_score", 0.5) or 0.5)
    # 표시용 승률도 누적 우선
    _vct_wr_post = row.get("vct_wr_post", None)
    vct_wr       = float(_vct_wr_post) if _vct_wr_post is not None else _vct_wr_safe(row)
    map_explains = float(row.get("map_explains_vct_drop", 0) or 0)
    top_map_in   = int(row.get("top_map_in_rotation", 1) or 1)
    recent_dmiss = int(row.get("recent_dual_miss_count", 0) or 0)
    rank_low_unexp = float(row.get("rank_low_unexpected", 0) or 0)

    # VCT 데이터 출처 액트
    _raw_vct_last     = row.get("vct_last_act_idx", None)
    _vct_last_act_idx = int(float(_raw_vct_last)) if _raw_vct_last is not None else -1
    _vct_act_name     = row.get("vct_last_event_name") or IDX_ACT.get(_vct_last_act_idx, None)
    _raw_lag          = row.get("vct_data_lag", None)
    _vct_data_lag     = int(float(_raw_lag)) if _raw_lag is not None else 99
    # 현재 예측 액트
    _raw_cur          = row.get("act_idx", None)
    _cur_act_idx      = int(float(_raw_cur)) if _raw_cur is not None else -1
    _cur_act_name     = IDX_ACT.get(_cur_act_idx, "")

    # 원본 패치 이력값 (인코딩 이전)
    acts_raw   = row.get("_raw_acts_since_patch", None)
    acts_since = int(float(acts_raw)) if acts_raw is not None else int(float(row.get("acts_since_patch", 99) or 99))
    ld_raw     = row.get("_raw_last_direction", None)
    last_dir   = str(ld_raw).lower() if ld_raw is not None else "none"
    if last_dir in ("0", "0.0", "nan", "none", ""):
        last_dir = "none"

    atype = _agent_type(rank_pr, vct_pr)
    rank_wr_actual = 50 + rank_wr

    signals: list[dict] = []

    # ── 1. 패치 이력 ─────────────────────────────────────────────────
    # 마지막 패치 액트 이름 계산
    _patch_act_name = IDX_ACT.get(_cur_act_idx - acts_since, None) if acts_since < 99 else None

    if last_dir in ("buff", "nerf") and acts_since <= 4:
        dir_ko   = "너프" if last_dir == "nerf" else "버프"
        if acts_since == 0:
            acts_str = "이번 액트"
        elif _patch_act_name:
            acts_str = f"{_patch_act_name} {dir_ko}"
        else:
            acts_str = f"{acts_since} 액트 전"
        label = f"패치 이력 — {acts_str}"

        if buff_hit or nerf_hit:
            text = f"{dir_ko} 효과 확인 (HIT). 지표가 원하는 방향으로 정착 중."
            tag  = "positive"
        elif buff_miss or nerf_miss:
            text = f"{dir_ko} 효과 미달 (MISS). 수치가 기대만큼 변화하지 않아 추가 조정이 필요한 상태."
            tag  = "warning"
        else:
            wr_actual = 50 + rank_wr
            if rank_wr > 1.0:
                wr_desc = f"랭크 승률 {wr_actual:.1f}%로 아직 높게 유지 중"
            elif rank_wr < -1.5:
                wr_desc = f"랭크 승률 {wr_actual:.1f}%로 이미 하락 중"
            else:
                wr_desc = f"랭크 승률 {wr_actual:.1f}%로 현재 평균 수준"
            text = (
                f"{dir_ko} 직후 — 아직 효과 판정 전. "
                f"{wr_desc}. 데이터가 더 쌓여야 HIT/MISS 결론을 낼 수 있음."
            )
            tag = "neutral"
        signals.append(_sig("patch", label, text, tag))

    elif acts_since >= 5 and acts_since < 99:
        signals.append(_sig(
            "patch", f"패치 이력 — {acts_since} 액트 무패치",
            "오랫동안 패치가 없었음. 현재 상태를 라이엇이 수용하고 있거나, 개선이 누적되는 중.",
            "neutral"
        ))
    elif acts_since >= 99:
        signals.append(_sig(
            "patch", "패치 이력 — 기록 없음",
            "패치 이력이 없거나 출시 이후 한 번도 조정되지 않은 상태.",
            "neutral"
        ))

    # ── 2. 랭크 현황 (마지막 패치 이후 평균) ────────────────────────────
    if _patch_act_name and last_patch_ver:
        rank_label = f"랭크 현황 — {_patch_act_name} · {last_patch_ver} 이후 평균"
    elif _patch_act_name:
        rank_label = f"랭크 현황 — {_patch_act_name} 이후 평균"
    elif last_patch_ver:
        rank_label = f"랭크 현황 — {last_patch_ver} 패치 이후 평균"
    elif _cur_act_name:
        rank_label = f"랭크 현황 — {_cur_act_name} 기준"
    else:
        rank_label = "랭크 현황"
    if rank_wr > 2.5:
        r_tag  = "danger"
        r_note = f"승률 {rank_wr_actual:.1f}% — 평균 대비 +{rank_wr:.1f}%p 초과"
    elif rank_wr < -2.5:
        r_tag  = "warning"
        r_note = f"승률 {rank_wr_actual:.1f}% — 평균 대비 {rank_wr:.1f}%p 미달"
    elif rank_pr_rel_meta > 3.0:
        r_tag  = "danger"
        r_note = f"승률 {rank_wr_actual:.1f}% — 픽률 집중도가 매우 높음"
    else:
        r_tag  = "neutral"
        r_note = f"승률 {rank_wr_actual:.1f}%"
    signals.append(_sig(
        "rank", rank_label,
        f"픽률 {rank_pr_pct:.1f}% / {r_note}",
        r_tag
    ))

    # ── 3. VCT 현황 (패치 이후 누적) ────────────────────────────────────
    if vct_pr >= 2.0:
        if _patch_act_name and last_patch_ver:
            vct_label = f"VCT 현황 — {_patch_act_name} · {last_patch_ver} 이후 누적"
            if _vct_act_name:
                vct_label += f" (최근: {_vct_act_name})"
        elif last_patch_ver:
            vct_label = f"VCT 현황 — {last_patch_ver} 이후 누적"
            if _vct_act_name:
                vct_label += f" (최근: {_vct_act_name})"
        elif _vct_act_name:
            vct_label = f"VCT 현황 — {_vct_act_name} 기준"
        else:
            vct_label = "VCT 현황"

        if vct_pr >= 35:   pr_desc = "메타 핵심"
        elif vct_pr >= 20: pr_desc = "프로 다수 기용"
        elif vct_pr >= 8:  pr_desc = "일부 팀 활용"
        else:              pr_desc = "소수 팀만 기용"

        # 픽률 < 5%는 샘플 부족 → 승률 신뢰 불가
        if vct_pr < 5.0:
            v_tag  = "neutral"
            v_note = "승률 집계 불가 (샘플 부족)"
        elif vct_wr >= 55:
            v_tag  = "danger"
            v_note = f"승률 {vct_wr:.1f}% — 쓰는 팀은 압도적으로 이김"
        elif vct_wr >= 52:
            v_tag  = "warning"
            v_note = f"승률 {vct_wr:.1f}% — 기용 시 우위"
        elif vct_wr < 45:
            v_tag  = "warning"
            v_note = f"승률 {vct_wr:.1f}% — 기용 시 패배 빈번"
        else:
            v_tag  = "neutral"
            v_note = f"승률 {vct_wr:.1f}% — 평균 수준"

        # VCT 데이터가 현재보다 오래됐으면 tag에 lag 경고 추가
        lag_note = f" (현재보다 {_vct_data_lag}액트 이전 데이터)" if _vct_data_lag > 0 else ""
        signals.append(_sig(
            "vct", vct_label,
            f"픽률 {vct_pr:.1f}% ({pr_desc}) / {v_note}{lag_note}",
            v_tag
        ))

    # ── 4. 판단 근거 ─────────────────────────────────────────────────
    if "correction_buff" in verdict:
        signals.append(_sig(
            "analysis", "과너프 판정",
            f"너프 이후 랭크 승률 {rank_wr_actual:.1f}%, VCT 승률 {vct_wr:.1f}%로 양쪽 모두 하락. "
            f"너프 효과가 의도 이상으로 작용 — 복구 조정 필요.",
            "warning"
        ))
    elif "correction_nerf" in verdict:
        signals.append(_sig(
            "analysis", "과버프 판정",
            f"버프 이후 지표가 과도하게 상승. 재조정이 필요한 상태.",
            "danger"
        ))
    elif "buff_rank" in verdict:
        signals.append(_sig(
            "analysis", "조용한 부진",
            f"별도 패치 플래그 없이도 랭크 픽률 {rank_pr_pct:.1f}%, VCT 픽률 {vct_pr:.1f}%로 "
            f"{acts_since}액트 이상 저픽 지속. 버프 필요성이 누적되는 상태.",
            "warning"
        ))
    elif buff_miss:
        dmiss_note = f" {recent_dmiss}회 연속 DUAL_MISS." if recent_dmiss >= 2 else ""
        signals.append(_sig(
            "analysis", "버프 효과 미달",
            f"이전 버프 이후 픽률·승률이 기대 수준에 도달하지 못함.{dmiss_note}",
            "warning"
        ))
    elif nerf_miss:
        signals.append(_sig(
            "analysis", "너프 효과 미달",
            f"이전 너프 이후에도 지표가 높은 수준 유지. 추가 조정 필요.",
            "danger"
        ))
    elif verdict == "stable":
        if buff_hit:
            signals.append(_sig("analysis", "버프 효과 확인", "최근 버프가 지표에 반영됨. 추가 조정 없이 안정 가능성 높음.", "positive"))
        elif nerf_hit:
            signals.append(_sig("analysis", "너프 효과 확인", "최근 너프 이후 지표가 안정 범위로 진입. 현 상태 수용 중.", "positive"))
        elif atype == "pro_anchor" and vct_pr >= 15:
            signals.append(_sig(
                "analysis", "유틸 앵커",
                f"VCT {vct_pr:.1f}% 픽이지만 승리 기여보다 팀 구성 필수 요소로 기용. "
                f"픽률 높아도 너프 근거로 보기 어려움.",
                "neutral"
            ))
        elif map_explains > 2 and not top_map_in:
            signals.append(_sig("analysis", "맵 풀 영향", "주력 맵이 현 대회 풀에 미포함 — 픽률 하락이 밸런스 문제가 아닐 수 있음.", "neutral"))
        else:
            signals.append(_sig("analysis", "패치 신호 미약", "현재 지표가 패치를 유발할 임계치에 도달하지 않음.", "neutral"))

    # ── 5. 추가 컨텍스트 ─────────────────────────────────────────────
    if skill_ceil >= 0.7:
        if "nerf" in verdict:
            signals.append(_sig(
                "identity", "고점 요원",
                f"스킬 천장이 높아 장인 운용 시 통계 이상의 실제 영향력이 있음. "
                f"VCT 픽률 {vct_pr:.1f}%는 이를 반영.",
                "warning"
            ))
        elif "buff" in verdict and rank_pr_rel_meta < 1.2:
            signals.append(_sig(
                "identity", "고점 요원",
                f"다루기 어려운 요원이라 랭크 픽률 {rank_pr_pct:.1f}%로 억눌려 있지만, "
                f"숙련자 기준 실제 강도는 통계보다 높음.",
                "neutral"
            ))

    if rank_vs_peak < 0.4 and rank_pr_peak_pct > 15 and "buff" in verdict:
        signals.append(_sig(
            "trend", "픽률 장기 하락",
            f"전성기 랭크 픽률 {rank_pr_peak_pct:.1f}% 대비 현재 {rank_pr_pct:.1f}% ({rank_vs_peak*100:.0f}% 수준). "
            f"꾸준한 하향세.",
            "warning"
        ))

    if rank_low_unexp and rank_pr_rel_meta < 0.6 and "buff" in verdict:
        signals.append(_sig(
            "trend", "비정상적 저픽",
            f"랭크 픽률 {rank_pr_pct:.1f}% — 설계 의도 대비 낮음.",
            "warning"
        ))

    # ── 6. 설계 정체성 ───────────────────────────────────────────────
    design = AGENT_DESIGN.get(agent, _DEFAULT_DESIGN)
    unique = design.get("unique_value", "")
    if unique and verdict != "stable":
        signals.append(_sig("identity", "설계 특성", unique, "neutral"))

    replaceability = float(design.get("replaceability", 0.5) or 0.5)
    niche = design.get("role_niche", "")
    if replaceability >= 0.7 and rank_pr_rel_meta < 0.7:
        signals.append(_sig("identity", "높은 대체 가능성", "메타 이탈 시 픽률이 급격히 떨어지는 구조.", "neutral"))
    elif replaceability <= 0.3 and niche:
        signals.append(_sig("identity", "독보적 역할", f"{niche} — 대체 불가 구조로 픽률 바닥이 존재.", "neutral"))

    # ── 7. 인과 관계 ─────────────────────────────────────────────────
    rel = AGENT_RELATIONS.get(agent, {})
    for item in rel.get("suppressed_by", []):
        type_ko = {"counter": "카운터", "replaces": "대체", "competes": "경쟁"}.get(item["type"], item["type"])
        signals.append(_sig("causal", f"{item['agent']} — {type_ko}", item["reason"], "neutral"))

    struct_note = (
        rel.get("structural_weakness") or rel.get("dominance_note") or
        rel.get("buff_note") or rel.get("resilience_note") or rel.get("meta_impact") or ""
    )
    if struct_note:
        signals.append(_sig("structural", "구조적 특성", struct_note, "neutral"))

    return signals


# ─── 메인 클래스 ──────────────────────────────────────────────────────────────

class PatchPredictor:
    def __init__(self,
                 pipeline_path: str = PIPELINE_PATH,
                 data_path: str = DATA_PATH,
                 cache_path: str = EXPLANATION_CACHE_PATH):

        pipe           = joblib.load(pipeline_path)
        self.model_a   = pipe["model_a"]
        self.model_b   = pipe["model_b"]
        self.feat_cols_a = pipe["feat_cols_a"]
        self.feat_cols_b = pipe["feat_cols_b"]
        self.label_b_cats = pipe["label_b_cats"]

        self.buff_idx   = [i for i, l in enumerate(self.label_b_cats) if l in BUFF_CLASSES]
        self.nerf_idx   = [i for i, l in enumerate(self.label_b_cats) if l in NERF_CLASSES]
        self.rework_idx = [i for i, l in enumerate(self.label_b_cats) if l == "rework"]

        # 설명 캐시 로드
        self._cache_path = cache_path
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                self._explanation_cache: dict[str, str] = json.load(f)
        else:
            self._explanation_cache = {}

        self._anthropic: Anthropic | None = None

        # 패치노트에서 요원별 마지막 패치 버전 조회용 룩업 구성
        # (agent, act_name) → 마지막 패치 버전 문자열
        self._last_patch_ver: dict[str, str] = {}
        try:
            from agent_data import PATCH_TO_ACT
            _pn = pd.read_csv("patch_notes_classified.csv")
            _pn["_act"] = _pn["patch"].astype(str).map(PATCH_TO_ACT)
            for _, _r in _pn.iterrows():
                _ag = str(_r.get("agent", ""))
                _act = str(_r.get("_act", ""))
                _p   = str(_r.get("patch", ""))
                if _ag and _act and _p and _act != "nan" and _p != "nan":
                    key = f"{_ag}|{_act}"
                    # 같은 액트 내 최신 패치 버전 보존 (버전 비교 대신 덮어쓰기; CSV가 시간순 정렬됨)
                    self._last_patch_ver[key] = _p
        except Exception:
            pass

        # 데이터 로드 및 전처리
        raw_df = pd.read_csv(data_path)
        self._run_pipeline(raw_df)

    def _run_pipeline(self, raw_df: pd.DataFrame):
        df = raw_df.copy()

        # 원본 컬럼 보존 (도메인 규칙용)
        raw_cols = ["last_direction", "acts_since_patch"]
        df_raw = df[["agent", "act_idx"] + [c for c in raw_cols if c in df.columns]].copy()

        # OrdinalEncoder
        oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        for col in CAT_COLS:
            if col in df.columns:
                df[col] = oe.fit_transform(df[[col]])

        # 요원별 최신 액트
        latest = df.loc[df.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
        latest_raw = df_raw.loc[df_raw.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
        latest = latest.merge(
            latest_raw.rename(columns={c: f"_raw_{c}" for c in raw_cols if c in df_raw.columns}),
            on=["agent", "act_idx"], how="left",
        )

        X_a = latest[self.feat_cols_a].values.astype(np.float32)
        X_b = latest[self.feat_cols_b].values.astype(np.float32)

        prob_patch = self.model_a.predict_proba(X_a)[:, 1].copy()
        prob_b_all = self.model_b.predict_proba(X_b)

        results = []
        for i, row in latest.iterrows():
            p_raw      = float(prob_patch[i])
            p_buff_raw = float(prob_b_all[i, self.buff_idx].sum())
            p_nerf_raw = float(prob_b_all[i, self.nerf_idx].sum())
            p_rework   = float(prob_b_all[i, self.rework_idx].sum()) if self.rework_idx else 0.0

            p_adj, p_buff_norm, p_nerf_norm = apply_domain_rules(row, p_raw, p_buff_raw, p_nerf_raw)

            p_stable = 1.0 - p_adj
            p_buff   = p_adj * p_buff_norm
            p_nerf   = p_adj * p_nerf_norm

            # 방향 선택: p_patch 임계값 0.28 기준 (stable 과잉 예측 보정)
            if p_adj < 0.28:
                verdict = "stable"
            elif p_rework * p_adj > 0.28 and p_rework * p_adj > p_buff and p_rework * p_adj > p_nerf:
                verdict = "rework"
            elif p_buff >= p_nerf:
                best_buff = max(self.buff_idx, key=lambda x: prob_b_all[i, x])
                verdict = self.label_b_cats[best_buff]
            else:
                best_nerf = max(self.nerf_idx, key=lambda x: prob_b_all[i, x])
                verdict = self.label_b_cats[best_nerf]

            # 패치 이력 없는 신규 요원: 방향 마진 작으면 stable 강제 (Veto류 노이즈 방지)
            _a_check = row.get("_raw_acts_since_patch", None)
            _a_check = int(float(_a_check)) if _a_check is not None else int(float(row.get("acts_since_patch", 99) or 99))
            if _a_check >= 99 and verdict != "stable":
                if abs(p_buff - p_nerf) / max(p_adj, 0.01) < 0.12:
                    verdict = "stable"

            # 방향 혼동 보정
            buff_miss_f = float(row.get("buff_miss_flag", 0) or 0)
            nerf_miss_f = float(row.get("nerf_miss_flag", 0) or 0)
            if buff_miss_f and "nerf" in verdict and "correction" not in verdict:
                _vpr = float(row.get("vct_pr_last", 0) or 0)
                _vwr = _vct_wr_safe(row)
                if not (_vpr >= 25.0 and _vwr >= 48.0):  # 고픽 안정 요원은 버프 강제 안 함
                    verdict = "buff_followup"
            if nerf_miss_f and "buff" in verdict and "correction" not in verdict:
                _rw = float(row.get("rank_wr_vs50", 0) or 0)
                _vw = _vct_wr_safe(row)
                overnerfed = _rw < 0 and _vw < 48.0
                if overnerfed:
                    verdict = "correction_buff"
                else:
                    verdict = "nerf_followup"

            # 패치 이력 원본값 노출
            _acts_r = row.get("_raw_acts_since_patch", None)
            _acts   = int(float(_acts_r)) if _acts_r is not None else int(float(row.get("acts_since_patch", 99) or 99))
            _ld_r   = row.get("_raw_last_direction", None)
            _ld     = str(_ld_r).lower() if _ld_r is not None else "none"
            if _ld in ("0", "0.0", "nan", "none", ""):
                _ld = "none"

            # VCT 데이터가 어느 액트 기준인지
            from agent_data import IDX_ACT
            _raw_vct_last = row.get("vct_last_act_idx", None)
            _vct_last_act_idx = int(float(_raw_vct_last)) if _raw_vct_last is not None else -1
            _vct_act = row.get("vct_last_event_name") or IDX_ACT.get(_vct_last_act_idx, None)
            _raw_lag = row.get("vct_data_lag", None)
            _vct_data_lag = int(float(_raw_lag)) if _raw_lag is not None else 99

            # 요원별 마지막 패치 버전 조회
            # acts_since=0 → 현재 액트, acts_since=N → N액트 전 액트
            _agent_name = str(row["agent"])
            _cur_act_name_r = str(row.get("act", ""))
            _cur_act_idx_r  = int(float(row.get("act_idx", -1) or -1))
            _patch_act_idx_r = _cur_act_idx_r - _acts if _acts < 99 else None
            _patch_act_name_r = IDX_ACT.get(_patch_act_idx_r, None) if _patch_act_idx_r is not None else None
            _last_patch_ver: str | None = None
            if _patch_act_name_r:
                _last_patch_ver = self._last_patch_ver.get(f"{_agent_name}|{_patch_act_name_r}")
            # 폴백: 현재 액트에서 패치 기록 조회
            if not _last_patch_ver:
                _last_patch_ver = self._last_patch_ver.get(f"{_agent_name}|{_cur_act_name_r}")

            results.append({
                "agent":              row["agent"],
                "act":                row["act"],
                "role":               AGENT_ROLE_KO.get(row["agent"], "알 수 없음"),
                "rank_pr":            round(float(row.get("rank_pr", 0) or 0) * 5, 1),
                "vct_pr":             round(float(row.get("vct_pr_post") or row.get("vct_pr_last", 0) or 0), 1),
                "rank_wr":            round(float(row.get("rank_wr_vs50", 0) or 0), 2),
                "vct_wr":             round(float(row.get("vct_wr_post") or _vct_wr_safe(row)), 1),
                "vct_act":            _vct_act,
                "vct_data_lag":       _vct_data_lag,
                "last_patch_version": _last_patch_ver,
                "last_patch_act":     _patch_act_name_r,
                "p_patch":            round(p_adj * 100, 1),
                "p_buff":             round(p_buff * 100, 1),
                "p_nerf":             round(p_nerf * 100, 1),
                "p_stable":           round(p_stable * 100, 1),
                "acts_since_patch":   _acts,
                "last_direction":     _ld,
                "verdict":            verdict,
                "verdict_ko":         PATCH_TYPE_KO.get(verdict, verdict),
                "verdict_en":         PATCH_TYPE_EN.get(verdict, verdict),
                "signals":            extract_signals(row, verdict, last_patch_ver=_last_patch_ver),
                "_row":               row,
            })

        self._results: list[dict] = results
        self._by_agent: dict[str, dict] = {r["agent"]: r for r in results}

    # ── Public API ────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        """p_patch 내림차순으로 모든 요원 예측 반환 (프론트용 경량 포맷)."""
        out = []
        for r in sorted(self._results, key=lambda x: x["p_patch"], reverse=True):
            out.append({k: v for k, v in r.items() if k != "_row"})
        return out

    def get_agent(self, agent: str) -> dict | None:
        """특정 요원의 상세 예측 반환. 설명 포함 (lazy 생성)."""
        r = self._by_agent.get(agent)
        if r is None:
            return None
        result = {k: v for k, v in r.items() if k != "_row"}
        result["explanation"] = self._get_explanation(r)
        return result

    def reload(self):
        """데이터/모델 재로드 (핫 리로드용)."""
        import importlib, predict_service as _self_mod
        importlib.reload(_self_mod)

    # ── 설명 생성 ─────────────────────────────────────────────────────────────

    def _get_explanation(self, r: dict) -> str:
        agent   = r["agent"]
        verdict = r["verdict"]
        cache_key = f"{agent}::{verdict}"

        if cache_key in self._explanation_cache:
            return self._explanation_cache[cache_key]

        explanation = self._generate_explanation(r)
        self._explanation_cache[cache_key] = explanation
        try:
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self._explanation_cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return explanation

    def _generate_explanation(self, r: dict) -> str:
        """Claude Haiku로 양면 분석 스타일의 설명 생성. 실패 시 템플릿 폴백."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._template_explanation(r)

        if self._anthropic is None:
            self._anthropic = Anthropic(api_key=api_key)

        agent        = r["agent"]
        agent_ko     = AGENT_NAME_KO.get(agent, agent)
        verdict      = r["verdict"]
        p_patch      = r["p_patch"]
        p_buff       = r["p_buff"]
        p_nerf       = r["p_nerf"]
        rank_pr      = r["rank_pr"]
        vct_pr       = r["vct_pr"]
        rank_wr      = r["rank_wr"]
        vct_wr       = r["vct_wr"]
        signals      = r.get("signals", [])
        patch_ver    = r.get("last_patch_version") or ""
        patch_ref    = f"{patch_ver} 패치" if patch_ver else "최근 패치"

        import re as _re
        def _strip_act_codes(s: str) -> str:
            # VxxAx / ExxAx 패턴 제거 (예: V26A1, E9A3)
            return _re.sub(r'\b[VE]\d+A\d+\b', '', s).strip()
        signal_text = "\n".join(
            f"- {_strip_act_codes(s['label'])}: {_strip_act_codes(s['text'])}"
            for s in signals[:6]
        ) or "- 특별한 신호 없음"

        direction    = "버프" if "buff" in verdict else "너프" if "nerf" in verdict else "안정"
        counter      = "너프" if direction == "버프" else "버프" if direction == "너프" else "패치"
        dir_pct      = p_buff if "buff" in verdict else p_nerf if "nerf" in verdict else (100 - p_patch)
        counter_pct  = p_nerf if "buff" in verdict else p_buff if "nerf" in verdict else p_patch

        # 데이터 해석 힌트: 어떤 수치가 어느 방향을 지지하는지
        rank_wr_actual = 50 + rank_wr
        nerf_evidence = []
        buff_evidence = []
        # 너프 근거: 높은 픽률, 높은 승률 (rank_pr는 이미 ×5 변환된 "게임 등장 %" 기준)
        if rank_pr >= 40:  nerf_evidence.append(f"랭크 픽률 {rank_pr:.1f}%로 높음")
        if rank_wr > 1.5:  nerf_evidence.append(f"랭크 승률 {rank_wr_actual:.1f}%로 평균 이상")
        if vct_pr >= 25:   nerf_evidence.append(f"프로 대회 픽률 {vct_pr:.1f}%로 메타 핵심")
        if vct_wr >= 52:   nerf_evidence.append(f"프로 승률 {vct_wr:.1f}%로 높음")
        # 버프 근거: 낮은 픽률, 낮은 승률
        if rank_pr < 20:   buff_evidence.append(f"랭크 픽률 {rank_pr:.1f}%로 낮음")
        if rank_wr < -1.5: buff_evidence.append(f"랭크 승률 {rank_wr_actual:.1f}%로 평균 이하")
        if vct_pr < 8:     buff_evidence.append(f"프로 대회 픽률 {vct_pr:.1f}%로 낮음")
        if vct_wr <= 47:   buff_evidence.append(f"프로 승률 {vct_wr:.1f}%로 낮음")

        if direction == "너프":
            dir_evidence  = "、".join(nerf_evidence) or f"프로 대회 픽률 {vct_pr:.1f}%"
            cnt_evidence  = "、".join(buff_evidence) or f"랭크 승률 {rank_wr_actual:.1f}%"
            stable_note   = ""
        elif direction == "버프":
            dir_evidence  = "、".join(buff_evidence) or f"랭크 픽률 {rank_pr:.1f}%"
            cnt_evidence  = "、".join(nerf_evidence) or f"프로 픽률 {vct_pr:.1f}%"
            stable_note   = ""
        else:
            # 안정 판정: 수치 + 패치가 없는 이유(stable_reason)를 함께 전달
            stable_facts = []
            if rank_pr < 15:   stable_facts.append(f"랭크 픽률 {rank_pr:.1f}%")
            elif rank_pr >= 40: stable_facts.append(f"랭크 픽률 {rank_pr:.1f}% (높음)")
            else:              stable_facts.append(f"랭크 픽률 {rank_pr:.1f}%")
            stable_facts.append(f"랭크 승률 {rank_wr_actual:.1f}%")
            if vct_pr >= 10:   stable_facts.append(f"프로 픽률 {vct_pr:.1f}%")
            elif vct_pr < 3:   stable_facts.append(f"프로 픽률 {vct_pr:.1f}%")

            # 안정 이유: 수치 약점이 아닌 "왜 패치가 없는지"를 명시
            if rank_pr < 5 and vct_pr < 5:
                stable_reason = "랭크·대회 픽률이 모두 너무 낮아 개발진 레이더 밖 상태"
            elif rank_pr < 15 and vct_pr < 8:
                stable_reason = "메타 존재감이 미미해 패치 우선순위에서 벗어남"
            elif rank_pr >= 35 or vct_pr >= 25:
                stable_reason = "수치가 높지만 패치 기준 임계치에는 미달"
            else:
                stable_reason = "랭크·대회 수치 모두 패치 기준 임계치에 미달"

            dir_evidence  = "、".join(stable_facts) + f" / 안정 이유: {stable_reason}"
            cnt_evidence  = "패치 압박 신호 없음"  # buff_evidence/nerf_evidence 금지 — AI 방향 혼동 유발
            # 안정 판정 세부 유형: 픽률 낮음 vs 수치 균형
            if rank_pr < 15 and vct_pr < 5:
                stable_note = "\n- 안정 판정 이유: 픽률이 너무 낮아 개발진 레이더에 없는 상태 — '밸런스가 좋다', '조정 필요성이 낮다', '추가 조정이 필요한 상태' 같은 표현 쓰지 말 것"
            elif buff_evidence:
                stable_note = "\n- 안정 판정 이유: 수치는 낮지만 지금 당장 패치 압박은 없는 상태 — '버프가 필요하다', '추가 조정이 필요한 상태', '개선이 필요', '추가 조정이 필요했던 상황이지만', '조정이 필요한 상황이지만' 같은 표현 절대 금지. 수치가 낮다는 사실을 언급하되 패치 압박이 없다는 결론까지 자연스럽게 이어지게 쓸 것"
            else:
                stable_note = "\n- 안정 판정 이유: 수치가 패치 임계치에 도달하지 않아 안정적인 상태 — '추가 조정이 필요한 상태지만', '조정 압박이 있지만', '추가 조정이 필요했던 상황이지만', '패치 필요성이 없어 보입니다' 같은 표현 금지. 반드시 '당분간 패치 없을 것으로 보입니다' 류로 마무리"

        # 맵 친화도
        map_affinity = AGENT_MAP_AFFINITY.get(agent, [])
        map_line = f"- 현재 맵 풀 ({', '.join(CURRENT_MAP_POOL)}) 중 특화 맵: {', '.join(map_affinity)}" if map_affinity else f"- 현재 맵 풀: {', '.join(CURRENT_MAP_POOL)} (특화 맵 없음)"

        # 스킬 이름 힌트
        skills = AGENT_SKILLS_KO.get(agent, {})
        skill_line = f"- {agent_ko}의 한국어 공식 스킬 이름: {', '.join(skills.values())}" if skills else ""

        prompt = f"""아래 데이터를 보고 {agent_ko}의 다음 패치 전망을 짧게 써주세요.

데이터:
- 예측 방향: {direction}
- 주요 근거: {dir_evidence}
- 참고 맥락 (방향은 바뀌지 않음, 뉘앙스 보정용): {cnt_evidence}
- 기타 신호: {signal_text}
- 마지막 패치: {patch_ref}
{map_line}
{skill_line}

규칙:
- 요원 이름은 "{agent_ko}"로만 표기, 영어 이름 금지
- 2~3문장 (3문장 초과 금지), 자연스러운 구어체 — 논문·보고서 투 금지
- 전체 글이 "예측 방향"과 일관된 방향으로 흘러야 함
- 너프/버프 판정일 때 방향을 의심하는 표현 절대 금지: "명확하지 않습니다", "확신하기 어렵습니다", "필요성이 낮습니다", "압박이 크지 않습니다" 등
- 안정 판정일 때 "추가 조정이 필요한 상태지만", "개선이 필요하지만" 같은 역접 표현 절대 금지{stable_note}
- 안정 판정 = 버프도 너프도 모두 없다는 예측
- 안정 판정 첫 문장 규칙: 반드시 "현재 상태가 균형 잡혀 있다 / 패치 압박이 없다 / 수치가 안정적이다" 방향으로 시작할 것. 너프·버프 신호처럼 읽힐 수 있는 수치(픽률 높음, 승률 낮음 등)를 첫 문장에 언급하는 것 금지
- 안정 판정 글의 논리 흐름 필수: [현재 상태가 안정적임] → [패치 기준에 미달인 이유] → [조정 없을 것]. 이 순서를 지킬 것
- "수치가 낮다 / 버프가 효과 없었다 / 대체 가능성이 높다" 같은 문장은 독립적으로 끝나면 안 됨. 반드시 "그래도 패치 기준엔 미달"이라는 이유로 자연스럽게 연결되어야 함
- 안정 판정에서 약점 나열 후 바로 "패치 없을 것"으로 끝내는 구조 절대 금지 — 논리적 비약
- 결론을 두 번 쓰지 말 것 — 마지막 문장 자체가 결론
- 마지막 문장 필수 형식:
  · 너프 → "너프될 가능성이 높습니다" / "조정이 들어올 것으로 보입니다" 류
  · 버프 → "버프가 필요해 보입니다" / "버프가 들어올 것으로 보입니다" 류
  · 안정 → "당분간 버프·너프 모두 없을 것으로 보입니다" / "조정 없이 현 상태가 유지될 것으로 보입니다" 류 (단순히 "패치 없을 것"만 쓰지 말 것)
- 스킬 언급 시 반드시 위에 제공된 한국어 공식 스킬 이름 사용 (영어 스킬명 절대 금지)
- 스킬 이름이 제공되지 않은 경우 스킬 이름을 직접 언급하지 말 것
- 맵 특화 정보가 있으면 분석에 자연스럽게 녹여 쓸 것 (강요하지 말 것, 억지로 끼워 넣지 말 것)
- 아래 표현 절대 금지:
  × "킷" / "키트" / "특성상" / "구조적 우위·특성" / "근본적인" / "개편"
  × 영어 스킬명 (예: Curtain Call, Neural Radiance, drone affinity 등)
  × 마크다운(#, *, ** 등)
- 패치 언급 시 반드시 "{patch_ref}" 표현 사용. V25A5·V25A6·V26A1·V26A2 같은 VxxAx·ExxAx 형식 액트 코드명 절대 금지
- 확률 수치 금지, 마침표로 끝낼 것
- 다른 요원 이름은 반드시 한국어 공식 이름 사용:
  제트·레이나·레이즈·네온·피닉스·아이소·요루·웨이레이·브림스톤·바이퍼·오멘·아스트라·하버·클로브
  소바·페이드·스카이·브리치·케이오·게코·킬조이·사이퍼·데드락·바이스·세이지·테호·베토·믹스·체임버"""

        try:
            resp = self._anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception:
            return self._template_explanation(r)

    def _template_explanation(self, r: dict) -> str:
        agent   = r["agent"]
        verdict = r["verdict"]
        p_patch = r["p_patch"]
        rank_pr = r["rank_pr"]
        vct_pr  = r["vct_pr"]

        if "nerf" in verdict:
            return (
                f"{agent}는 현재 랭크 픽률 {rank_pr:.1f}%, VCT 픽률 {vct_pr:.1f}%로 "
                f"메타를 압도하고 있습니다. 패치 확률 {p_patch:.0f}%로 너프가 예상됩니다."
            )
        elif "buff" in verdict:
            return (
                f"{agent}의 랭크 픽률은 {rank_pr:.1f}%, VCT 픽률은 {vct_pr:.1f}%에 불과합니다. "
                f"패치 확률 {p_patch:.0f}%로 버프가 필요한 상황입니다."
            )
        elif verdict == "rework":
            return (
                f"{agent}는 랭크와 VCT 양쪽에서 모두 저픽 상태가 지속되고 있습니다. "
                f"수치 조정만으로는 한계가 있어 리워크 가능성이 {p_patch:.0f}%로 예측됩니다."
            )
        else:
            return (
                f"{agent}는 현재 밸런스가 잘 잡혀 있습니다. "
                f"랭크 픽률 {rank_pr:.1f}%, VCT 픽률 {vct_pr:.1f}%로 패치 필요성이 낮습니다."
            )
