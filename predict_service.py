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

# ─── 요원 메타 데이터 ─────────────────────────────────────────────────────────
from agent_data import AGENT_DESIGN, _DEFAULT_DESIGN, AGENT_RELATIONS
from feature_builder import compute_kit_score, get_kit_flags

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

from agent_data import AGENT_NAME_KO, AGENT_ROLE_KO

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

        # 설명 생성기 (explanation_service.py로 분리)
        from explanation_service import ExplanationGenerator
        self._explainer = ExplanationGenerator(cache_path)

        # 패치노트에서 요원별 마지막 패치 버전 조회용 룩업 구성
        # (agent, act_name) → 마지막 패치 버전 문자열
        self._last_patch_ver: dict[str, str] = {}
        try:
            import re as _re
            from agent_data import PATCH_TO_ACT
            _pn = pd.read_csv("patch_notes_classified.csv")
            _pn["_act"] = _pn["patch"].astype(str).map(PATCH_TO_ACT)
            # 크로스패치 인트로 텍스트 감지용 정규식
            # 예: "Patch Notes 12.03 Modes updates, Gekko changes..." 이 12.06 행에 붙어있으면 노이즈
            _xpatch_re = _re.compile(r"Patch Notes\s+(\d+\.\d+)", _re.IGNORECASE)
            def _norm_patch(p: str) -> str:
                try:
                    _a, _b = str(p).split(".")
                    return f"{int(_a)}.{int(_b)}"
                except Exception:
                    return str(p)
            for _, _r in _pn.iterrows():
                _ag  = str(_r.get("agent", ""))
                _act = str(_r.get("_act", ""))
                _p   = str(_r.get("patch", ""))
                _ct  = str(_r.get("change_type", "")).strip().lower()
                _dir = str(_r.get("direction", "")).strip().lower()
                _hb  = int(_r.get("has_bugfix", 0) or 0)
                _desc = str(_r.get("description", ""))
                # 노이즈 필터 ── 실제 밸런스 패치만 last_patch로 인정
                #   · change_type=rework: 다른 패치의 인트로 텍스트가 파서 오염된 행
                #   · has_bugfix=1 & direction=neutral: VFX/SFX/UI 버그픽스 (밸런스 영향 없음)
                #   · description이 다른 패치 번호를 참조: 인트로 블러브가 잘못 섞인 크로스패치 노이즈
                if _ct == "rework":
                    continue
                if _hb == 1 and _dir == "neutral":
                    continue
                _m = _xpatch_re.search(_desc)
                if _m and _norm_patch(_m.group(1)) != _norm_patch(_p):
                    continue
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

            # 현재 액트부터 역순으로 walk → 진짜 마지막 밸런스 패치 탐색.
            # (acts_since 기반 patch_act_name은 예전 필터링 이전 데이터로 계산된 경우가 있어
            #  낡은 액트를 가리킬 수 있음 → backward walk를 1순위로 사용)
            last_patch_ver: str | None = None
            if cur_act_idx >= 0:
                for _idx in range(cur_act_idx, -1, -1):
                    _act = IDX_ACT.get(_idx)
                    if not _act:
                        continue
                    _cand = self._last_patch_ver.get(f"{agent_name}|{_act}")
                    if _cand:
                        last_patch_ver = _cand
                        patch_act_name = _act  # UI 라벨용으로 실제 액트 반영
                        break
            # Fallback: 혹시 walk로 못 찾았을 때만 acts_since 기반 조회
            if not last_patch_ver and patch_act_name:
                last_patch_ver = self._last_patch_ver.get(f"{agent_name}|{patch_act_name}")

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
        result["explanation"] = self._explainer.get(r)
        return result

    def reload(self):
        """데이터/모델 재로드 (핫 리로드용)."""
        import importlib, predict_service as _self_mod
        importlib.reload(_self_mod)
