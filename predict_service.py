"""
predict_service.py
PatchPredictor — FastAPI 서비스용 예측 래퍼

predict_report.py의 로직을 클래스로 캡슐화.
- step2_pipeline.pkl (model / feat_cols / label_cats)
  label_cats: mild_buff / mild_nerf / stable / strong_buff / strong_nerf
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
from feature_builder import compute_kit_score, get_kit_flags, AGENT_PR_BASELINE

# ─── 상수 ────────────────────────────────────────────────────────────────────

BUFF_CLASSES = {"buff_followup", "buff_rank", "correction_buff", "mild_buff", "strong_buff"}
NERF_CLASSES = {"nerf_followup", "nerf_rank", "correction_nerf", "mild_nerf", "strong_nerf"}

PATCH_TYPE_EN = {
    "buff_rank":        "Buff (Rank)",
    "buff_followup":    "Buff (Follow-up)",
    "correction_buff":  "Buff (Over-nerf Recovery)",
    "nerf_rank":        "Nerf (Rank)",
    "nerf_followup":    "Nerf (Follow-up)",
    "correction_nerf":  "Nerf (Over-buff Correction)",
    "rework":           "Rework",
    "mild_buff":        "Buff (Mild)",
    "strong_buff":      "Buff (Strong)",
    "mild_nerf":        "Nerf (Mild)",
    "strong_nerf":      "Nerf (Strong)",
    "stable":           "Stable",
}

PATCH_TYPE_KO = {
    "buff_rank":        "버프 (랭크)",
    "buff_followup":    "버프 (추가)",
    "correction_buff":  "버프 (과너프 복구)",
    "nerf_rank":        "너프 (랭크)",
    "nerf_followup":    "너프 (추가)",
    "correction_nerf":  "너프 (과버프 조정)",
    "rework":           "리워크",
    "mild_buff":        "버프 (소폭)",
    "strong_buff":      "버프 (강력)",
    "mild_nerf":        "너프 (소폭)",
    "strong_nerf":      "너프 (강력)",
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
    "Chamber":   "체임버",
    "Deadlock":  "데드록",
    "Vyse":      "바이스",
    "Veto":      "비토",
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
    "Jett":      {"C": "연막 폭발", "Q": "상승기류", "E": "순풍", "X": "칼날 폭풍"},
    "Viper":     {"C": "뱀 이빨", "E": "독성 장막", "Q": "독성 연기", "X": "독사의 구덩이"},
    "Neon":      {"C": "추월 차선", "Q": "릴레이 볼트", "E": "고속 기어", "X": "오버드라이브"},
    "Sova":      {"C": "올빼미 드론", "Q": "충격 화살", "E": "정찰용 화살", "X": "사냥꾼의 분노"},
    "Reyna":     {"C": "눈총", "Q": "포식", "E": "무시", "X": "여제"},
    "Raze":      {"C": "폭발 봇", "Q": "폭발 팩", "E": "페인트 탄", "X": "대미 장식"},
    "Chamber":   {"C": "트레이드마크", "Q": "헤드헌터", "E": "랑데부", "X": "역작"},
    "Killjoy":   {"C": "나노스웜", "Q": "알람봇", "E": "포탑", "X": "봉쇄"},
    "Sage":      {"C": "장벽 구슬", "Q": "둔화 구슬", "E": "회복 구슬", "X": "부활"},
    "Omen":      {"C": "어둠의 발자국", "Q": "피해망상", "E": "어둠의 장막", "X": "그림자 습격"},
    "Skye":      {"C": "재생", "Q": "정찰자", "E": "인도하는 빛", "X": "추적자"},
    "Fade":      {"C": "추적귀", "Q": "포박", "E": "귀체", "X": "황혼"},
    "Breach":    {"C": "여진", "Q": "섬광 폭발", "E": "균열", "X": "지진 강타"},
    "KAYO":      {"C": "파편/탄", "Q": "플래시/드라이브", "E": "제로/포인트", "X": "무력화/명령"},
    "Gekko":     {"C": "폭파봇 지옥", "Q": "지원봇", "E": "기절봇", "X": "요동봇"},
    "Astra":     {"C": "중력의 샘", "Q": "신성 파동", "E": "성운", "X": "우주 장벽"},
    "Brimstone": {"C": "자극제 신호기", "Q": "소이탄", "E": "공중 연막", "X": "궤도 일격"},
    "Harbor":    {"C": "폭풍 쇄도", "Q": "만조", "E": "해만", "X": "심판"},
    "Clove":     {"C": "활력 회복", "Q": "간섭", "E": "계략", "X": "아직 안 죽었어"},
    "Tejo":      {"C": "잠입 드론", "Q": "특별 배송", "E": "유도 일제 사격", "X": "아마겟돈"},
    "Iso":       {"C": "대비책", "Q": "약화", "E": "구슬 보호막", "X": "청부 계약"},
    "Deadlock":  {"C": "장벽망", "Q": "음향 센서", "E": "중력그물", "X": "소멸"},
    "Vyse":      {"C": "면도날 덩굴", "Q": "가지치기", "E": "아크 장미", "X": "강철 정원"},
    "Cypher":    {"C": "함정", "Q": "사이버 감옥", "E": "스파이캠", "X": "신경 절도"},
    "Phoenix":   {"C": "불길", "Q": "뜨거운 손", "E": "커브볼", "X": "역습"},
    "Waylay":    {"C": "포화", "Q": "광속", "E": "굴절", "X": "초점 교차"},
    "Yoru":      {"C": "기만", "Q": "기습", "E": "관문 충돌", "X": "차원 표류"},
    "Miks":      {"C": "M-파동", "Q": "화음", "E": "웨이브폼", "X": "요동치는 베이스"},
    "Veto":      {"C": "지름길", "Q": "목조르기", "E": "요격기", "X": "진화"},
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
            f"랭크 픽률 {rank_pr_pct:.1f}%, VCT 픽률 {vct_pr:.1f}%로 저픽 지속. "
            f"버프 필요성이 누적되는 상태.",
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
    elif "nerf" in verdict:
        signals.append(_sig(
            "analysis", "너프 신호",
            f"랭크 픽률 {rank_pr_pct:.1f}%, VCT 픽률 {vct_pr:.1f}%로 상위 티어 선점 중.",
            "danger"
        ))
    elif "buff" in verdict:
        if buff_hit:
            signals.append(_sig("analysis", "버프 효과 확인", "최근 버프가 지표에 반영됨. 방향은 맞지만 추가 조정 여부를 지켜봐야 함.", "positive"))
        elif atype == "pro_anchor" and vct_pr >= 15:
            signals.append(_sig(
                "analysis", "유틸 앵커 부진",
                f"VCT {vct_pr:.1f}% 픽이지만 랭크에서는 존재감 부족. 프로 전용 유틸리티 요원 특성상 버프 요구가 쌓이는 중.",
                "warning"
            ))
        elif map_explains > 2 and not top_map_in:
            signals.append(_sig("analysis", "맵 풀 영향", "주력 맵이 현 대회 풀에 미포함 — 픽률 하락이 밸런스 문제가 아닐 수 있음.", "neutral"))
        else:
            signals.append(_sig(
                "analysis", "버프 신호",
                f"랭크 픽률 {rank_pr_pct:.1f}%, VCT 픽률 {vct_pr:.1f}%로 현재 메타에서 외면받는 중.",
                "warning"
            ))

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
    if unique:
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

        pipe = joblib.load(pipeline_path)

        # 2-Stage 파이프라인 (Stage A: stable vs patched / Stage B: buff vs nerf)
        self.model_a      = pipe["model_a"]
        self.model_b      = pipe["model_b"]
        self.feat_cols_a  = pipe["feat_cols_a"]
        self.feat_cols_b  = pipe["feat_cols_b"]
        self.label_b_cats = pipe["label_b_cats"]  # ['buff', 'nerf']

        self.buff_b_idx = self.label_b_cats.index("buff")
        self.nerf_b_idx = self.label_b_cats.index("nerf")

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

        # patch_dates.json 로드 (크롤러가 자동 갱신)
        self._patch_dates: dict[str, str] = {}
        try:
            import json as _json
            with open("patch_dates.json", encoding="utf-8") as _f:
                self._patch_dates = _json.load(_f)
        except Exception:
            pass

        # 데이터 로드 및 전처리
        raw_df = pd.read_csv(data_path)
        self._run_pipeline(raw_df)

    def _run_pipeline(self, raw_df: pd.DataFrame):
        from agent_data import IDX_ACT

        df = raw_df.copy()

        # ── 원본값 보존 (인코딩 전) ───────────────────────────────────────────
        raw_cols = ["last_direction", "acts_since_patch"]
        df_raw = df[["agent", "act_idx"] + [c for c in raw_cols if c in df.columns]].copy()

        # vct_wr_last: VCT 데이터 없을 때 NaN → 50%으로 대체 (train_step2.prepare()와 동일)
        if "vct_wr_last" in df.columns:
            df["vct_wr_last"] = df["vct_wr_last"].fillna(50.0)

        # ── 카테고리 인코딩 ───────────────────────────────────────────────────
        oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        for col in CAT_COLS:
            if col in df.columns:
                df[col] = oe.fit_transform(df[[col]])

        # ── 요원별 최신 액트만 추출 ───────────────────────────────────────────
        latest = df.loc[df.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
        latest_raw = df_raw.loc[df_raw.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
        latest = latest.merge(
            latest_raw.rename(columns={c: f"_raw_{c}" for c in raw_cols if c in df_raw.columns}),
            on=["agent", "act_idx"], how="left",
        ).reset_index(drop=True)  # merge 후 index 재정렬 보장

        # ── 모델 추론 (2-Stage) ───────────────────────────────────────────────
        X_a = latest[self.feat_cols_a].values.astype(np.float32)
        X_b = latest[self.feat_cols_b].values.astype(np.float32)

        # Stage A: stable(0) vs patched(1)
        prob_a = self.model_a.predict_proba(X_a)  # (N, 2)
        # Stage B: buff vs nerf  (patched 행 조건부)
        prob_b = self.model_b.predict_proba(X_b)  # (N, 2)

        results = []
        for idx in range(len(latest)):
            row = latest.iloc[idx]

            # ── 패치 이력 원본값 파싱 ─────────────────────────────────────────
            _acts_raw = row.get("_raw_acts_since_patch", None)
            acts_since = (
                int(float(_acts_raw))
                if _acts_raw is not None
                else int(float(row.get("acts_since_patch", 99) or 99))
            )
            _ld_raw = row.get("_raw_last_direction", None)
            last_dir = str(_ld_raw).lower() if _ld_raw is not None else "none"
            if last_dir in ("0", "0.0", "nan", "none", ""):
                last_dir = "none"

            # ── 2-Stage 합성 확률 ─────────────────────────────────────────────
            # P(nerf) = P(patched) × P(nerf|patched)
            # P(buff) = P(patched) × P(buff|patched)
            p_patched  = float(prob_a[idx, 1])
            p_buff_dir = p_patched * float(prob_b[idx, self.buff_b_idx])
            p_nerf_dir = p_patched * float(prob_b[idx, self.nerf_b_idx])
            _p_stable  = float(prob_a[idx, 0])

            # 패치 직후 7일 이내: 지표 충분히 안 쌓임 → 50% 쪽으로 수축
            # patch_dates.json에 실제 배포일 있으면 날짜 기반, 없으면 acts_since=0 fallback
            _days_since_patch = 999
            _early_agent_name = str(row.get("agent", ""))
            _early_act_name   = str(row.get("act", ""))
            _early_patch_ver  = (
                self._last_patch_ver.get(f"{_early_agent_name}|{_early_act_name}")
                or None
            )
            if _early_patch_ver and _early_patch_ver in self._patch_dates:
                from datetime import date as _date
                try:
                    _pd = _date.fromisoformat(self._patch_dates[_early_patch_ver])
                    _days_since_patch = (_date.today() - _pd).days
                except ValueError:
                    pass
            elif acts_since == 0:
                # 날짜 정보 없음 → acts_since=0이면 보수적으로 수축
                _days_since_patch = 0

            if _days_since_patch <= 7:
                p_nerf_dir = 0.5 + (p_nerf_dir - 0.5) * 0.25
                p_buff_dir = 1.0 - p_nerf_dir

            # 표시용 (0~100)  ─ 모델 원본 확률 그대로 표시
            p_nerf = round(p_nerf_dir * 100, 1)
            p_buff = round(p_buff_dir * 100, 1)
            # p_patch = 방향 확신도 (50%에서 얼마나 멀어졌는지)
            p_patch = round(max(p_nerf_dir, p_buff_dir) * 100, 1)

            # ── Verdict 결정 (2-stage 임계값 기반) ───────────────────────────
            if _p_stable > max(p_nerf_dir, p_buff_dir):
                verdict = "stable"
            elif p_nerf_dir >= p_buff_dir:
                verdict = "strong_nerf" if p_nerf_dir > 0.40 else "mild_nerf"
            else:
                verdict = "strong_buff" if p_buff_dir > 0.25 else "mild_buff"

            # ── 도메인 오버라이드 ──────────────────────────────────────────────
            buff_miss = float(row.get("buff_miss_flag", 0) or 0)
            nerf_miss = float(row.get("nerf_miss_flag", 0) or 0)

            # 버프 미스 플래그: 모델이 너프라 해도, VCT가 확인 안 되면 여전히 버프 필요
            if buff_miss and "nerf" in verdict and "correction" not in verdict:
                vpr = float(row.get("vct_pr_last", 0) or 0)
                vwr = _vct_wr_safe(row)
                if not (vpr >= 25.0 and vwr >= 48.0):
                    verdict = "mild_buff"

            # 너프 미스 플래그: 모델이 버프라 해도, 버프 확신이 낮으면 너프 쪽으로
            if nerf_miss and "buff" in verdict and "correction" not in verdict:
                if p_buff <= 65.0:
                    rw = float(row.get("rank_wr_vs50", 0) or 0)
                    vw = _vct_wr_safe(row)
                    if rw < 0 and vw < 48.0:
                        verdict = "correction_buff"   # 과너프됐음
                    else:
                        verdict = "mild_nerf"

            # ── rework 방향 일치 가드 ────────────────────────────────────────────
            # rework는 방향이 명확한 경우(p_buff or p_nerf > 70%) 서브타입으로 보정
            if verdict == "rework":
                if p_buff_dir >= 0.7:
                    verdict = "mild_buff"
                elif p_nerf_dir >= 0.7:
                    verdict = "mild_nerf"

            # ── 신규 요원 가드 ─────────────────────────────────────────────────
            # acts_since=99: 출시 이후 한 번도 패치된 적 없는 신규 요원
            # 데이터 부족 → 모델 예측 신뢰도 낮음, 낮은 픽률≠버프 필요
            # → 방향 무관하게 stable 처리, 순위 최하단 배치
            if acts_since >= 90:
                verdict = "stable"

            # ── VCT 메타 조회 ──────────────────────────────────────────────────
            _raw_vct_last    = row.get("vct_last_act_idx", None)
            _vct_last_act_idx = int(float(_raw_vct_last)) if _raw_vct_last is not None else -1
            _vct_act          = row.get("vct_last_event_name") or IDX_ACT.get(_vct_last_act_idx, None)
            _raw_lag          = row.get("vct_data_lag", None)
            _vct_data_lag     = int(float(_raw_lag)) if _raw_lag is not None else 99

            # ── 마지막 패치 버전 조회 ─────────────────────────────────────────
            agent_name    = str(row["agent"])

            # 정렬용 스코어: 모델 확률 그대로 사용 (도메인 룰 없음)
            # 신규 요원은 최하단 배치
            if acts_since >= 90:
                urgency_score = 0.0
            else:
                urgency_score = max(p_nerf_dir, p_buff_dir)
            cur_act_name  = str(row.get("act", ""))
            cur_act_idx   = int(float(row.get("act_idx", -1) or -1))
            patch_act_idx = cur_act_idx - acts_since if acts_since < 99 else None
            patch_act_name = IDX_ACT.get(patch_act_idx) if patch_act_idx is not None else None

            last_patch_ver: str | None = None
            if patch_act_name:
                last_patch_ver = self._last_patch_ver.get(f"{agent_name}|{patch_act_name}")
            if not last_patch_ver:
                last_patch_ver = self._last_patch_ver.get(f"{agent_name}|{cur_act_name}")

            _vct_pr_post_val = row.get("vct_pr_post", None)
            _vct_pr_display = float(_vct_pr_post_val) if _vct_pr_post_val is not None else float(row.get("vct_pr_last", 0) or 0)

            results.append({
                "agent":              agent_name,
                "act":                cur_act_name,
                "role":               AGENT_ROLE_KO.get(agent_name, "알 수 없음"),
                "rank_pr":            round(float(row.get("rank_pr", 0) or 0) * 5, 1),
                "vct_pr":             round(_vct_pr_display, 1),
                "rank_wr":            round(float(row.get("rank_wr_vs50", 0) or 0), 2),
                "vct_wr":             round(float(row.get("vct_wr_post") or _vct_wr_safe(row)), 1),
                "vct_act":            _vct_act,
                "vct_data_lag":       _vct_data_lag,
                "last_patch_version": last_patch_ver,
                "last_patch_act":     patch_act_name,
                "p_patch":            p_patch,
                "p_buff":             p_buff,
                "p_nerf":             p_nerf,
                "urgency_score":      round(urgency_score, 4),
                "acts_since_patch":   acts_since,
                "days_since_patch":   _days_since_patch if _days_since_patch < 999 else None,
                "last_direction":     last_dir,
                "verdict":            verdict,
                "verdict_ko":         PATCH_TYPE_KO.get(verdict, verdict),
                "verdict_en":         PATCH_TYPE_EN.get(verdict, verdict),
                "signals":            extract_signals(row, verdict, last_patch_ver=last_patch_ver),
                "_row":               row,
            })

        self._results: list[dict] = results
        self._by_agent: dict[str, dict] = {r["agent"]: r for r in results}

    # ── Public API ────────────────────────────────────────────────────────────

    def get_all(self) -> list[dict]:
        """urgency_score(= max(p_nerf, p_buff)) 내림차순으로 모든 요원 반환.

        표시값과 정렬 기준이 동일 — 높은 확률 = 높은 순위.
        동 방향 내 순위는 VCT 초과 × 랭크 승률 기반 긴급도로 결정.
        """
        out = []
        for r in sorted(self._results, key=lambda x: x["urgency_score"], reverse=True):
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
        # act + 핵심 지표 반올림을 키에 포함 → 액트 변경 또는 데이터 변화 시 자동 무효화
        act          = r.get("act", "")
        rank_pr_r    = round(r.get("rank_pr", 0), 1)
        vct_pr_r     = round(r.get("vct_pr", 0), 1)
        cache_key = f"{agent}::{verdict}::{act}::{rank_pr_r}::{vct_pr_r}"

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

        # 신규 요원: 패치 이력 없음 → 모델 예측 신뢰도 낮음
        acts_since_r = int(r.get("acts_since_patch", 0) or 0)
        if acts_since_r >= 90:
            agent_ko_r = AGENT_NAME_KO.get(r["agent"], r["agent"])
            return (
                f"출시 이후 패치 이력이 없어 예측 신뢰도가 낮습니다. "
                f"데이터가 충분히 쌓이면 {agent_ko_r}에 대한 정밀 분석이 가능해집니다."
            )

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

        direction    = "버프" if "buff" in verdict else "너프"
        dir_pct      = p_buff if "buff" in verdict else p_nerf
        counter_pct  = p_nerf if "buff" in verdict else p_buff

        # 신호 강도: 방향 확률 기반 타이밍 힌트
        if dir_pct >= 60:
            signal_strength = "강함 — 이번 패치 조정 가능성 높음"
        elif dir_pct >= 35:
            signal_strength = "중간 — 이번 혹은 다음 패치 내 조정 예상"
        else:
            signal_strength = "약함 — 신호 누적 중, 당장보다 중장기적 조정 가능"

        # 데이터 해석 힌트: 어떤 수치가 어느 방향을 지지하는지
        rank_wr_actual = 50 + rank_wr
        nerf_evidence = []
        buff_evidence = []
        if rank_pr >= 40:  nerf_evidence.append(f"랭크 픽률 {rank_pr:.1f}%로 높음")
        if rank_wr > 1.5:  nerf_evidence.append(f"랭크 승률 {rank_wr_actual:.1f}%로 평균 이상")
        if vct_pr >= 25:   nerf_evidence.append(f"프로 대회 픽률 {vct_pr:.1f}%로 메타 핵심")
        if vct_wr >= 52:   nerf_evidence.append(f"프로 승률 {vct_wr:.1f}%로 높음")
        if rank_pr < 20:   buff_evidence.append(f"랭크 픽률 {rank_pr:.1f}%로 낮음")
        if rank_wr < -1.5: buff_evidence.append(f"랭크 승률 {rank_wr_actual:.1f}%로 평균 이하")
        if vct_pr < 8:     buff_evidence.append(f"프로 대회 픽률 {vct_pr:.1f}%로 낮음")
        if vct_wr <= 47:   buff_evidence.append(f"프로 승률 {vct_wr:.1f}%로 낮음")

        if direction == "너프":
            dir_evidence = "、".join(nerf_evidence) or f"프로 대회 픽률 {vct_pr:.1f}%"
            cnt_evidence = "、".join(buff_evidence) or f"랭크 승률 {rank_wr_actual:.1f}%"
        else:
            dir_evidence = "、".join(buff_evidence) or f"랭크 픽률 {rank_pr:.1f}%"
            cnt_evidence = "、".join(nerf_evidence) or f"프로 픽률 {vct_pr:.1f}%"

        # 맵 친화도
        map_affinity = AGENT_MAP_AFFINITY.get(agent, [])
        map_line = f"- 현재 맵 풀 ({', '.join(CURRENT_MAP_POOL)}) 중 특화 맵: {', '.join(map_affinity)}" if map_affinity else f"- 현재 맵 풀: {', '.join(CURRENT_MAP_POOL)} (특화 맵 없음)"

        # 스킬 이름 힌트
        skills = AGENT_SKILLS_KO.get(agent, {})
        skill_line = f"- {agent_ko}의 한국어 공식 스킬 이름: {', '.join(skills.values())}" if skills else ""

        # 맵 친화도: 특화 맵 없는 경우 맵 언급 생략
        map_line_prompt = (
            f"- 현재 맵 풀 특화 맵: {', '.join(map_affinity)} (분석에 자연스럽게 녹여도 됨)"
            if map_affinity else ""
        )

        prompt = f"""발로란트 프로씬 분석가 입장에서 {agent_ko}의 다음 패치 전망을 써주세요.

제공 데이터 (이 수치만 사용, 없는 통계 절대 언급 금지):
- 예측 방향: {direction}
- 신호 강도: {signal_strength}
- 주요 근거: {dir_evidence}
- 참고 맥락 (뉘앙스 보정용, 방향 바뀌지 않음): {cnt_evidence}
- 기타 신호: {signal_text}
- 마지막 패치: {patch_ref}
{map_line_prompt}
{skill_line}

글쓰기 지침:
- 정확히 2~3문장. 초과 금지.
- 발로란트 프로씬 현업 용어를 자연스럽게 섞어 쓸 것
  (픽률/승률, 메타 픽, 유틸 효율, 인포 수집, 교전 개시, 사이드 밸런스,
   랭겜/프로씬, 티어, 포스트플랜트, 로테이션 압박, 구성 강제, 팀파이트 기여, 임팩트 등)
- 신호 강도에 맞게 타이밍 표현 조절:
  · 강함 → "이번 패치에 조정이 들어올 것으로 보입니다" 류
  · 중간 → "가까운 시일 내", "이번 혹은 다음 패치" 류
  · 약함 → "당장은 아니더라도 중장기적으로 조정이 예상됩니다" 류
- 숫자 나열로 시작하지 말 것 — 가장 인상적인 포인트로 자연스럽게 열 것
- 분석가가 의견을 내는 톤 — 보고서 투 금지, 팬심 투 금지
- 전체 흐름이 "{direction}" 방향과 일치해야 함 (방향 의심 표현 절대 금지)
- 결론을 두 번 쓰지 말 것 — 마지막 문장이 방향을 담은 결론
- 스킬 언급 시 위에 제공된 한국어 공식 스킬 이름만 사용 (영어명·설명형 표현 금지)
- 스킬 이름이 제공되지 않은 경우 스킬 이름 직접 언급 금지
- 맵 이름(브리즈·헤이번·어센트·바인드 등) 절대 언급 금지. 단, 위 데이터에 맵 특화 정보가 명시된 경우에만 허용.
- 패치 언급 시 반드시 "{patch_ref}" 표현 사용. VxxAx·ExxAx 형식 액트 코드명 절대 금지
- 요원 이름은 한국어 공식 이름만 사용 (영어 이름 금지):
  제트·레이나·레이즈·네온·피닉스·아이소·요루·웨이레이·브림스톤·바이퍼·오멘·아스트라·하버·클로브
  소바·페이드·스카이·브리치·케이오·게코·킬조이·사이퍼·데드락·바이스·세이지·테호·베토·믹스·체임버
- 확률 수치 금지, 마침표로 끝낼 것. 마크다운 금지(#, *, ** 등 일절 사용 금지).
- 금지 표현: 킷 / 키트 / 특성상 / 구조적 / 근본적인 / 개편 / 설계 의도 / 오버튠드 / 언더튠드
- 제공된 데이터에 없는 과거 통계·역사적 수치·타 시즌 비교 절대 언급 금지
- 스킬 메커니즘 설명(사이클·쿨다운·작동 방식 등) 금지 — 스킬 이름만 언급"""

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
        agent_ko = AGENT_NAME_KO.get(r["agent"], r["agent"])
        verdict  = r["verdict"]
        rank_pr  = r["rank_pr"]
        vct_pr   = r["vct_pr"]

        if "nerf" in verdict:
            return (
                f"{agent_ko}은(는) 현재 랭크 픽률 {rank_pr:.1f}%, VCT 픽률 {vct_pr:.1f}%로 "
                f"메타 상단을 점유 중입니다. 너프 조정이 예상됩니다."
            )
        elif "buff" in verdict:
            return (
                f"{agent_ko}의 랭크 픽률 {rank_pr:.1f}%, VCT 픽률 {vct_pr:.1f}%로 "
                f"현재 메타에서 외면받고 있습니다. 버프 조정이 필요한 상황입니다."
            )
        else:  # rework
            return (
                f"{agent_ko}은(는) 랭크·VCT 양쪽에서 모두 저픽 상태가 지속되고 있습니다. "
                f"수치 조정만으로는 한계가 있어 리워크 가능성이 있습니다."
            )
