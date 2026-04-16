"""
patch_simulator.py
패치 시뮬레이터 — 가상 패치 적용 후 전체 메타 변화 예측

사용법:
  # CLI
  python patch_simulator.py --agent Neon --skill E --stat "cooldown" --old 6 --new 8
  python patch_simulator.py --agent 네온 --skill E --stat "cooldown" --old 6 --new 8
  python patch_simulator.py --interactive

  # API (main.py에서 POST /simulate)
  {
    "changes": [
      {"agent": "Neon", "skill": "E", "stat": "cooldown", "old_value": 6, "new_value": 8}
    ]
  }

핵심 로직:
  1. 스탯 변경 → 방향(nerf/buff) + 크기(small/medium/large) + identity(E/X) 추론
  2. impact_lookup.json에서 경험적 PR/WR 변화량 범위(p25~p75) 조회
  3. 유사 패치 사례 검색 (같은 요원/역할/변경유형에서 실제 결과 참조)
  4. 신뢰도 기반 보수적 댐핑 (표본 부족 시 효과 축소)
  5. 수정된 피처로 2D 사분면 + 파생 피처 재계산 → 모델 재실행
"""

from __future__ import annotations

import sys
import json
import argparse
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import OrdinalEncoder

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ─── 데이터 로드 ────────────────────────────────────────────────────────────────

_BASE = Path(__file__).parent
IMPACT_LOOKUP: dict = {}
_lookup_path = _BASE / "impact_lookup.json"
if _lookup_path.exists():
    IMPACT_LOOKUP = json.loads(_lookup_path.read_text(encoding="utf-8"))

# 낮을수록 버프인 스탯 키워드 (skill_simulator.py에서 차용)
_LOWER_IS_BUFF = (
    "cooldown", "windup", "cost", "cred", "unequip", "equip",
    "deploy", "recharge", "restock", "charge time", "cast time",
    "recovery", "reload", "reactivation",
)

from agent_data import KO_TO_EN, normalize_agent as _normalize_agent, AGENT_PR_BASELINE, AGENT_ROLE

# ─── 유사 패치 사례 DB ─────────────────────────────────────────────────────────
_PATCH_NOTES_PATH = _BASE / "patch_notes_classified.csv"
_SIMILAR_CASES_DB: pd.DataFrame | None = None


def _load_similar_db() -> pd.DataFrame | None:
    """patch_notes_classified.csv에서 유사 사례 검색용 DB를 로드."""
    global _SIMILAR_CASES_DB
    if _SIMILAR_CASES_DB is not None:
        return _SIMILAR_CASES_DB
    if not _PATCH_NOTES_PATH.exists():
        return None
    try:
        df = pd.read_csv(_PATCH_NOTES_PATH)
        # 유효한 skill_key가 있고 direction이 buff/nerf인 행만
        df = df[
            (df["skill_key"] != "?") &
            (df["direction"].isin(["buff", "nerf"])) &
            (df["change_type"].isin(["cooldown", "duration", "damage", "charges", "cost", "range", "mechanic"]))
        ].copy()
        _SIMILAR_CASES_DB = df
        return df
    except Exception:
        return None


def _find_similar_cases(
    agent: str, skill: str, change_type: str, direction: str, max_results: int = 5
) -> list[dict]:
    """유사 패치 사례를 검색한다. 구체적→일반적 순서로 매칭.

    매칭 우선순위:
      1. 같은 요원 + 같은 스킬 + 같은 방향
      2. 같은 요원 + 같은 방향
      3. 같은 역할 + 같은 변경유형 + 같은 방향
      4. 같은 변경유형 + 같은 방향 (전체)
    """
    db = _load_similar_db()
    if db is None or db.empty:
        return []

    role = AGENT_ROLE.get(agent, "")
    results = []

    # Tier 1: 같은 요원 + 같은 스킬 + 같은 방향
    t1 = db[(db["agent"] == agent) & (db["skill_key"] == skill) & (db["direction"] == direction)]
    for _, row in t1.iterrows():
        results.append(_case_dict(row, "exact"))

    # Tier 2: 같은 요원 + 같은 방향
    t2 = db[(db["agent"] == agent) & (db["direction"] == direction) & ~db.index.isin(t1.index)]
    for _, row in t2.head(3).iterrows():
        results.append(_case_dict(row, "same_agent"))

    # Tier 3: 같은 역할 + 같은 변경유형 + 같은 방향
    if len(results) < max_results and role:
        role_agents = [a for a, r in AGENT_ROLE.items() if r == role and a != agent]
        t3 = db[
            (db["agent"].isin(role_agents)) &
            (db["change_type"] == change_type) &
            (db["direction"] == direction)
        ]
        for _, row in t3.head(max_results - len(results)).iterrows():
            results.append(_case_dict(row, "same_role"))

    # Tier 4: 전체 같은 변경유형 + 같은 방향
    if len(results) < max_results:
        t4 = db[
            (db["change_type"] == change_type) &
            (db["direction"] == direction) &
            ~db.index.isin(t1.index) & ~db.index.isin(t2.index)
        ]
        for _, row in t4.head(max_results - len(results)).iterrows():
            results.append(_case_dict(row, "similar_type"))

    return results[:max_results]


def _case_dict(row: pd.Series, match_tier: str) -> dict:
    """패치 사례를 dict로 변환."""
    desc = str(row.get("description", ""))
    return {
        "patch": str(row.get("patch", "")),
        "agent": str(row.get("agent", "")),
        "skill": str(row.get("skill_key", "")),
        "change_type": str(row.get("change_type", "")),
        "direction": str(row.get("direction", "")),
        "description": desc[:120] + ("..." if len(desc) > 120 else ""),
        "match_tier": match_tier,
    }


def _infer_change_type(stat_name: str) -> str:
    """스탯 이름에서 패치 변경유형을 추론."""
    s = stat_name.lower()
    if any(k in s for k in ("cooldown", "recharge", "reactivation")):
        return "cooldown"
    if any(k in s for k in ("damage", "heal")):
        return "damage"
    if any(k in s for k in ("duration", "time", "windup")):
        return "duration"
    if any(k in s for k in ("cost", "cred", "price")):
        return "cost"
    if any(k in s for k in ("range", "radius", "distance")):
        return "range"
    if any(k in s for k in ("charge",)):
        return "charges"
    return "mechanic"


# ─── 데이터 클래스 ──────────────────────────────────────────────────────────────

@dataclass
class StatChange:
    """단일 스탯 변경"""
    agent: str           # 영문명 (e.g. "Neon")
    skill: str           # "Q" | "E" | "C" | "X"
    stat_name: str       # "cooldown", "damage", "duration" 등
    old_value: float
    new_value: float

    @property
    def direction(self) -> str:
        """nerf / buff 자동 추론"""
        diff = self.new_value - self.old_value
        is_lower_buff = any(kw in self.stat_name.lower() for kw in _LOWER_IS_BUFF)
        if diff == 0:
            return "none"
        if is_lower_buff:
            return "buff" if diff < 0 else "nerf"
        else:
            return "buff" if diff > 0 else "nerf"

    @property
    def magnitude(self) -> str:
        """small / medium / large 크기 분류"""
        if self.old_value == 0:
            return "large"
        ratio = abs(self.new_value - self.old_value) / abs(self.old_value)
        if ratio <= 0.15:
            return "small"
        elif ratio <= 0.35:
            return "medium"
        else:
            return "large"

    @property
    def is_identity_skill(self) -> bool:
        """E(시그니처) 또는 X(궁극기) = identity skill"""
        return self.skill in ("E", "X")


@dataclass
class AgentPrediction:
    """요원 1명의 예측 결과"""
    agent: str
    p_nerf: float
    p_buff: float
    p_stable: float
    verdict: str
    rank_pr: float = 0.0   # 랭크 픽률 (÷5 스케일)
    rank_wr: float = 50.0   # 랭크 승률
    vct_pr: float = 0.0    # VCT 픽률


@dataclass
class SimulationResult:
    """시뮬레이션 결과"""
    changes: list[StatChange]
    before: list[AgentPrediction]
    after: list[AgentPrediction]
    deltas: dict[str, dict]  # agent → {pr_delta, wr_delta, ...}

    def to_dict(self) -> dict:
        """API 응답용 직렬화"""
        def _pred_list(preds: list[AgentPrediction]) -> list[dict]:
            return [
                {
                    "agent": p.agent,
                    "p_nerf": round(p.p_nerf, 1),
                    "p_buff": round(p.p_buff, 1),
                    "p_stable": round(p.p_stable, 1),
                    "verdict": p.verdict,
                }
                for p in sorted(preds, key=lambda x: max(x.p_nerf, x.p_buff), reverse=True)
            ]

        changed_agents = {c.agent for c in self.changes}
        impact = []
        for agent in changed_agents:
            before_p = next((p for p in self.before if p.agent == agent), None)
            after_p = next((p for p in self.after if p.agent == agent), None)
            d = self.deltas.get(agent, {})
            if before_p and after_p:
                impact.append({
                    "agent": agent,
                    "applied_pr_delta": round(d.get("pr_delta", 0), 3),
                    "applied_wr_delta": round(d.get("wr_delta", 0), 3),
                    "pr_range": [round(x, 3) for x in d.get("pr_range", [0, 0, 0])],
                    "wr_range": [round(x, 3) for x in d.get("wr_range", [0, 0, 0])],
                    "confidence": d.get("confidence", "low"),
                    "n_samples": d.get("n_samples", 0),
                    "similar_cases": d.get("similar_cases", [])[:5],
                    "before": {
                        "p_nerf": round(before_p.p_nerf, 1),
                        "p_buff": round(before_p.p_buff, 1),
                        "verdict": before_p.verdict,
                        "rank_pr": round(before_p.rank_pr, 1),
                        "rank_wr": round(before_p.rank_wr, 1),
                        "vct_pr": round(before_p.vct_pr, 1),
                    },
                    "after": {
                        "p_nerf": round(after_p.p_nerf, 1),
                        "p_buff": round(after_p.p_buff, 1),
                        "verdict": after_p.verdict,
                    },
                })

        # 비직접 변경 요원 중 verdict가 바뀐 것들
        ripple = []
        before_map = {p.agent: p for p in self.before}
        after_map = {p.agent: p for p in self.after}
        for agent, ap in after_map.items():
            if agent in changed_agents:
                continue
            bp = before_map.get(agent)
            if bp and bp.verdict != ap.verdict:
                ripple.append({
                    "agent": agent,
                    "before_verdict": bp.verdict,
                    "after_verdict": ap.verdict,
                    "before_p_nerf": round(bp.p_nerf, 1),
                    "after_p_nerf": round(ap.p_nerf, 1),
                    "before_p_buff": round(bp.p_buff, 1),
                    "after_p_buff": round(ap.p_buff, 1),
                })

        return {
            "changes": [
                {
                    "agent": c.agent,
                    "skill": c.skill,
                    "stat": c.stat_name,
                    "old": c.old_value,
                    "new": c.new_value,
                    "direction": c.direction,
                    "magnitude": c.magnitude,
                }
                for c in self.changes
            ],
            "impact": impact,
            "ripple_effects": ripple,
            "before_ranking": _pred_list(self.before),
            "after_ranking": _pred_list(self.after),
        }


# ─── 시뮬레이터 클래스 ──────────────────────────────────────────────────────────

CAT_COLS = [
    "vct_profile", "last_direction", "last_combined",
    "last_rank_verdict", "last_vct_verdict", "patch_streak_direction",
    "last_trigger_type",
]


class PatchSimulator:
    """가상 패치를 적용하고 모델을 재실행하여 메타 변화를 예측한다."""

    def __init__(
        self,
        pipeline_path: str = "step2_pipeline.pkl",
        data_path: str = "step2_training_data.csv",
    ):
        pipe = joblib.load(pipeline_path)
        self.model_a = pipe["model_a"]
        self.model_b = pipe["model_b"]
        self.feat_cols_a = pipe["feat_cols_a"]
        self.feat_cols_b = pipe["feat_cols_b"]
        self.label_b_cats = pipe["label_b_cats"]  # ['buff', 'nerf']
        self.buff_b_idx = self.label_b_cats.index("buff")
        self.nerf_b_idx = self.label_b_cats.index("nerf")

        self.raw_df = pd.read_csv(data_path)

    # ── 공개 API ────────────────────────────────────────────────────────────────

    def simulate(self, changes: list[StatChange]) -> SimulationResult:
        """
        가상 패치를 적용하고 전 요원의 before/after 예측을 반환한다.

        1. 현재 데이터로 before 예측
        2. 변경 요원의 피처에 예상 PR/WR 델타 반영
        3. 2D 사분면 + 파생 피처 재계산
        4. after 예측 수행
        5. before/after 비교
        """
        # before: 현재 상태 그대로 예측
        df_before = self._prepare_latest(self.raw_df)
        before_preds = self._run_prediction(df_before)

        # 요원별 델타 집계 (같은 요원에 여러 변경 가능)
        agent_deltas: dict[str, dict] = {}
        for change in changes:
            d = self._estimate_deltas(change)
            if change.agent not in agent_deltas:
                agent_deltas[change.agent] = {
                    "pr_delta": 0.0, "wr_delta": 0.0,
                    "pr_range": [0.0, 0.0, 0.0], "wr_range": [0.0, 0.0, 0.0],
                    "confidence": "high", "n_samples": 0,
                    "similar_cases": [],
                }
            ad = agent_deltas[change.agent]
            ad["pr_delta"] += d["pr_delta"]
            ad["wr_delta"] += d["wr_delta"]
            # 범위는 누적 합산
            for i in range(3):
                ad["pr_range"][i] += d["pr_range"][i]
                ad["wr_range"][i] += d["wr_range"][i]
            # 신뢰도는 가장 낮은 것으로
            conf_order = {"low": 0, "medium": 1, "high": 2}
            if conf_order.get(d["confidence"], 0) < conf_order.get(ad["confidence"], 2):
                ad["confidence"] = d["confidence"]
            ad["n_samples"] = max(ad["n_samples"], d.get("n_samples", 0))
            ad["similar_cases"].extend(d.get("similar_cases", []))

        # after: 피처 수정 후 예측
        df_after = self._modify_features(df_before.copy(), agent_deltas)
        after_preds = self._run_prediction(df_after)

        return SimulationResult(
            changes=changes,
            before=before_preds,
            after=after_preds,
            deltas=agent_deltas,
        )

    # ── 델타 추정 ───────────────────────────────────────────────────────────────

    def _estimate_deltas(self, change: StatChange) -> dict:
        """impact_lookup.json에서 경험적 PR/WR 변화량 범위를 조회한다.

        반환:
          pr_delta, wr_delta: 모델 피처 수정에 사용할 대표값 (댐핑 적용)
          pr_range, wr_range: [low, mid, high] 불확실성 범위 (p25, median, p75)
          confidence: "high" | "medium" | "low" — 표본 수와 매칭 품질 기반
          similar_cases: 유사 패치 사례 목록
        """
        direction = change.direction
        if direction == "none":
            return {
                "pr_delta": 0.0, "wr_delta": 0.0,
                "pr_range": [0.0, 0.0, 0.0], "wr_range": [0.0, 0.0, 0.0],
                "confidence": "high", "similar_cases": [],
            }

        magnitude = change.magnitude
        identity = 1 if change.is_identity_skill else 0

        # 룩업 키 조합 시도 (구체적 → 일반적 순서)
        candidates = [
            (f"{direction}_id{identity}_{magnitude}", 1.0),     # 정확 매칭
            (f"{direction}_id{identity}_mechanic", 0.85),       # identity 매칭, magnitude 일반화
            (f"{direction}_id0_{magnitude}", 0.7),              # identity 무관
            (f"{direction}_id0_mechanic", 0.6),
            (f"_fallback_{direction}", 0.4),                    # 전체 방향 fallback
        ]

        entry = None
        match_quality = 0.4
        for key, quality in candidates:
            if key in IMPACT_LOOKUP:
                entry = IMPACT_LOOKUP[key]
                match_quality = quality
                break

        if entry is None:
            entry = IMPACT_LOOKUP.get("_overall", {})
            match_quality = 0.3

        pr_entry = entry.get("pr", {})
        wr_entry = entry.get("wr", {})
        n_samples = pr_entry.get("n", 0)

        # ── 신뢰도 계산 ──
        # 표본 수 + 매칭 품질 + 비핵심 스킬 페널티
        sample_conf = min(n_samples / 15.0, 1.0)  # 15개 이상이면 만점
        confidence_score = sample_conf * match_quality
        if not change.is_identity_skill:
            confidence_score *= 0.8  # 비핵심(C/Q) 스킬은 효과 불확실

        if confidence_score >= 0.6:
            confidence = "high"
        elif confidence_score >= 0.35:
            confidence = "medium"
        else:
            confidence = "low"

        # ── 범위 추출 (p25, median, p75) ──
        pr_range = [
            pr_entry.get("p25", 0.0),
            pr_entry.get("median", 0.0),
            pr_entry.get("p75", 0.0),
        ]
        wr_range = [
            wr_entry.get("p25", 0.0),
            wr_entry.get("median", 0.0),
            wr_entry.get("p75", 0.0),
        ]

        # ── 대표값 선택 (방향 일치 쪽) + 보수적 댐핑 ──
        pr_delta = self._pick_delta(pr_entry, direction)
        wr_delta = self._pick_delta(wr_entry, direction)

        # 댐핑: 신뢰도 낮을수록 0 쪽으로 축소
        damping = min(confidence_score / 0.6, 1.0)  # high이면 1.0, low이면 ~0.5
        pr_delta *= damping
        wr_delta *= damping

        # ── 유사 사례 검색 ──
        change_type = _infer_change_type(change.stat_name)
        similar = _find_similar_cases(change.agent, change.skill, change_type, direction)

        return {
            "pr_delta": pr_delta,
            "wr_delta": wr_delta,
            "pr_range": [round(x, 3) for x in pr_range],
            "wr_range": [round(x, 3) for x in wr_range],
            "confidence": confidence,
            "n_samples": n_samples,
            "similar_cases": similar,
        }

    @staticmethod
    def _pick_delta(stat_entry: dict, direction: str) -> float:
        """방향에 맞는 대표값을 선택한다.

        너프: p25 (PR/WR가 실제로 떨어진 케이스의 대표값)
        버프: p75 (PR/WR가 실제로 올라간 케이스의 대표값)

        median이 방향과 이미 일치하면 median 사용 (보수적).
        """
        median = stat_entry.get("median", 0.0)
        if direction == "nerf":
            p25 = stat_entry.get("p25", median)
            return min(median, p25)
        else:
            p75 = stat_entry.get("p75", median)
            return max(median, p75)

    # ── 피처 수정 ───────────────────────────────────────────────────────────────

    def _prepare_latest(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """raw_df에서 요원별 최신 액트 행만 추출 + 인코딩."""
        df = raw_df.copy()

        # vct_wr_last NaN → 50.0
        if "vct_wr_last" in df.columns:
            df["vct_wr_last"] = df["vct_wr_last"].fillna(50.0)

        # 카테고리 인코딩
        oe = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        for col in CAT_COLS:
            if col in df.columns:
                df[col] = oe.fit_transform(df[[col]])

        # 요원별 최신 행
        latest = df.loc[df.groupby("agent")["act_idx"].idxmax()].copy().reset_index(drop=True)
        return latest

    def _modify_features(self, df: pd.DataFrame, agent_deltas: dict) -> pd.DataFrame:
        """
        패치 대상 요원의 피처를 수정한다.

        수정 대상:
        - rank_pr: PR 델타 반영 (training data는 ÷5 스케일, impact_lookup은 raw %)
        - rank_wr / rank_wr_vs50: WR 델타 반영
        - vct_pr_last: VCT PR 델타 반영 (랭크 델타의 2배 민감도 가정)
        - 2D 사분면 피처 전체 재계산
        - excess / signal 피처 재계산
        """
        for agent, deltas in agent_deltas.items():
            mask = df["agent"] == agent
            if not mask.any():
                continue

            idx = df.index[mask][0]
            pr_delta_raw = deltas["pr_delta"]   # raw percentage points (e.g. -2.0)
            wr_delta = deltas["wr_delta"]        # raw percentage points (e.g. -0.5)

            # rank_pr는 training data에서 ÷5 스케일 (pick_rate_pct = % of total picks)
            # impact_lookup의 PR은 "게임 등장률 %" 기준 → ÷5로 변환
            pr_delta_scaled = pr_delta_raw / 5.0

            # 기본 피처 수정
            old_rank_pr = float(df.at[idx, "rank_pr"])
            new_rank_pr = max(old_rank_pr + pr_delta_scaled, 0.01)
            df.at[idx, "rank_pr"] = new_rank_pr

            old_rank_wr = float(df.at[idx, "rank_wr"])
            new_rank_wr = old_rank_wr + wr_delta
            df.at[idx, "rank_wr"] = new_rank_wr
            df.at[idx, "rank_wr_vs50"] = new_rank_wr - 50.0

            # VCT 픽률: 프로는 랭크보다 민감하게 반응 (×1.5 가정)
            old_vct_pr = float(df.at[idx, "vct_pr_last"])
            new_vct_pr = max(old_vct_pr + pr_delta_raw * 1.5, 0.0)
            df.at[idx, "vct_pr_last"] = new_vct_pr

            # rank_pr_avg3 도 비례 조정
            if "rank_pr_avg3" in df.columns:
                df.at[idx, "rank_pr_avg3"] = max(
                    float(df.at[idx, "rank_pr_avg3"]) + pr_delta_scaled, 0.01
                )

            # ── 2D 사분면 + 파생 피처 재계산 ──────────────────────────────────
            self._rederive_features(df, idx, agent)

        return df

    def _rederive_features(self, df: pd.DataFrame, idx: int, agent: str):
        """수정된 rank_pr/rank_wr/vct_pr로부터 파생 피처를 재계산한다."""

        _rank_pr_raw = float(df.at[idx, "rank_pr"])
        _baseline_pr = AGENT_PR_BASELINE.get(agent, 5.0)
        _rank_wr = float(df.at[idx, "rank_wr"])
        _rank_wr_avg = float(df.at[idx, "rank_wr_hist_mean"]) if "rank_wr_hist_mean" in df.columns else 50.0
        _vct_pr = float(df.at[idx, "vct_pr_last"])
        _vct_wr_col = df.at[idx, "vct_wr_last"] if "vct_wr_last" in df.columns else 50.0
        _vct_wr = float(_vct_wr_col) if not pd.isna(_vct_wr_col) else 50.0
        _vct_pr_avg = float(df.at[idx, "vct_pr_avg"]) if "vct_pr_avg" in df.columns else 0.0

        # 축 이탈량
        _pr_excess = _rank_pr_raw - _baseline_pr
        _wr_excess = _rank_wr - _rank_wr_avg
        _vct_excess = _vct_pr - _vct_pr_avg
        _vct_wr_excess = _vct_wr - 50.0
        _wr_vs50 = _rank_wr - 50.0

        # ── 2D 사분면 재계산 ──────────────────────────────────────────────
        def _set(col, val):
            if col in df.columns:
                df.at[idx, col] = val

        _set("rank_nerf_2d",   max(_pr_excess, 0) * max(_wr_excess, 0))
        _set("rank_buff_2d",   max(-_pr_excess, 0) * max(-_wr_excess, 0))
        _set("rank_fandom_2d", max(_pr_excess, 0) * max(-_wr_excess, 0))
        _set("rank_niche_2d",  max(-_pr_excess, 0) * max(_wr_excess, 0))

        _set("vct_nerf_2d",  max(_vct_excess, 0) * max(_vct_wr_excess, 0))
        _set("vct_buff_2d",  max(-_vct_excess, 0) * max(-_vct_wr_excess, 0))
        _set("vct_must_nerf", max(_vct_pr - 35.0, 0))

        _set("cross_nerf_2d",
             max(_pr_excess, 0) * max(_wr_excess, 0)
             + max(_vct_excess, 0) * max(_vct_wr_excess, 0))

        _set("pro_only_nerf",
             max(_vct_pr - 35.0, 0) * max(_baseline_pr * 2.0 - _rank_pr_raw, 0) / max(_baseline_pr * 2.0, 1.0))

        _set("rank_only_nerf",
             max(_pr_excess, 0) * max(_wr_excess, 0) * max(20.0 - _vct_pr, 0) / 20.0)

        _set("vct_pr_vs_agent_avg", _vct_pr / max(_vct_pr_avg, 2.0))

        # ── Excess 피처 ──────────────────────────────────────────────────
        _rank_pr_excess = max(_rank_pr_raw - _baseline_pr, 0.0)
        _vct_pr_excess = max(_vct_pr - _vct_pr_avg, 0.0)
        _set("rank_pr_excess", _rank_pr_excess)
        _set("rank_excess_x_wr", _rank_pr_excess * max(_wr_vs50, 0.0))
        _set("vct_pr_excess", _vct_pr_excess)
        _set("vct_excess_x_wr", _vct_pr_excess * max(_wr_vs50, 0.0))

        # ── 1D 방향 신호 ─────────────────────────────────────────────────
        _set("wr_nerf_signal", max(_wr_vs50, 0.0))
        _set("wr_buff_signal", max(-_wr_vs50, 0.0))
        _set("vct_buff_signal", max(_vct_pr_avg - _vct_pr, 0.0) if _vct_pr_avg > 0 else 0.0)
        _set("rank_wr_vs_agent_avg", _wr_excess)

        # ── 교차 피처 ────────────────────────────────────────────────────
        _rel_meta = float(df.at[idx, "rank_pr_rel_meta"]) if "rank_pr_rel_meta" in df.columns else 1.0
        _set("pro_rank_ratio", _vct_pr / max(_rank_pr_raw, 0.5))
        _set("rank_wr_vs50", _wr_vs50)

        # skill_ceiling_x_vct_pr
        _sc = float(df.at[idx, "skill_ceiling_score"]) if "skill_ceiling_score" in df.columns else 0.5
        _set("skill_ceiling_x_vct_pr", _sc * _vct_pr)

        # VCT 상대 위치 비율
        _set("vct_rel_pos", _vct_pr / max(_vct_pr_avg, 0.5) if _vct_pr_avg > 0 else 1.0)

        # pr_vs_baseline
        _set("pr_vs_baseline", _rank_pr_raw - _baseline_pr)
        _pr_excess_ratio = (_rank_pr_raw - _baseline_pr) / max(_baseline_pr, 0.5)
        _set("pr_wr_gap", _pr_excess_ratio - _wr_vs50 / 2.0)

        # pr_pct_of_peak
        _pr_peak = float(df.at[idx, "rank_pr_peak"]) if "rank_pr_peak" in df.columns else _rank_pr_raw
        _set("pr_pct_of_peak", _rank_pr_raw / max(_pr_peak, 0.01))

        # strength_vs_direction
        _ld = "none"
        # 시뮬레이션에서는 last_direction이 이미 인코딩된 상태이므로 그대로 유지

    # ── 모델 실행 ───────────────────────────────────────────────────────────────

    def _run_prediction(self, df: pd.DataFrame) -> list[AgentPrediction]:
        """DataFrame에 대해 2-Stage 예측을 수행하고 AgentPrediction 리스트를 반환한다."""
        X_a = df[self.feat_cols_a].values.astype(np.float32)
        X_b = df[self.feat_cols_b].values.astype(np.float32)

        prob_a = self.model_a.predict_proba(X_a)  # (N, 2): [stable, patched]
        prob_b = self.model_b.predict_proba(X_b)  # (N, 2): [buff, nerf]

        results = []
        for i in range(len(df)):
            agent = str(df.iloc[i]["agent"])
            p_stable = float(prob_a[i, 0])
            p_patched = float(prob_a[i, 1])
            p_buff_dir = p_patched * float(prob_b[i, self.buff_b_idx])
            p_nerf_dir = p_patched * float(prob_b[i, self.nerf_b_idx])

            # Verdict 결정 (predict_service.py와 동일 로직)
            if p_stable > max(p_nerf_dir, p_buff_dir):
                verdict = "stable"
            elif p_nerf_dir >= p_buff_dir:
                verdict = "strong_nerf" if p_nerf_dir > 0.40 else "mild_nerf"
            else:
                verdict = "strong_buff" if p_buff_dir > 0.25 else "mild_buff"

            # 현재 상태 수치 추출 (AI 분석 컨텍스트용)
            row = df.iloc[i]
            _rp = float(row["rank_pr"]) * 5.0 if "rank_pr" in df.columns and pd.notna(row.get("rank_pr")) else 0.0
            _rw = float(row["rank_wr"]) if "rank_wr" in df.columns and pd.notna(row.get("rank_wr")) else 50.0
            _vp = float(row["vct_pr_last"]) if "vct_pr_last" in df.columns and pd.notna(row.get("vct_pr_last")) else 0.0

            results.append(AgentPrediction(
                agent=agent,
                p_nerf=round(p_nerf_dir * 100, 1),
                p_buff=round(p_buff_dir * 100, 1),
                p_stable=round(p_stable * 100, 1),
                verdict=verdict,
                rank_pr=round(_rp, 1),
                rank_wr=round(_rw, 1),
                vct_pr=round(_vp, 1),
            ))
        return results


# ─── CLI 출력 ────────────────────────────────────────────────────────────────────

def _print_result(result: SimulationResult):
    """시뮬레이션 결과를 터미널에 출력한다."""
    print()
    print("=" * 70)
    print("  패치 시뮬레이션 결과")
    print("=" * 70)

    # 적용된 변경사항
    for c in result.changes:
        dir_ko = "너프" if c.direction == "nerf" else ("버프" if c.direction == "buff" else "변경없음")
        dir_arrow = "▼" if c.direction == "nerf" else ("▲" if c.direction == "buff" else "─")
        print(f"\n  {dir_arrow} {c.agent} [{c.skill}] {c.stat_name}: {c.old_value} → {c.new_value}  ({dir_ko}, {c.magnitude})")
        d = result.deltas.get(c.agent, {})
        print(f"    예상 변화: 랭크 PR {d.get('pr_delta', 0):+.2f}%p  /  WR {d.get('wr_delta', 0):+.2f}%p")

    # 직접 영향 요원
    changed_agents = {c.agent for c in result.changes}
    before_map = {p.agent: p for p in result.before}
    after_map = {p.agent: p for p in result.after}

    print("\n  ─── 패치 대상 요원 before / after ──────────────────────────────")
    print(f"  {'요원':<12} {'before':>20}  →  {'after':>20}")
    for agent in sorted(changed_agents):
        bp = before_map.get(agent)
        ap = after_map.get(agent)
        if bp and ap:
            b_str = f"N{bp.p_nerf:>5.1f}% B{bp.p_buff:>5.1f}% [{bp.verdict}]"
            a_str = f"N{ap.p_nerf:>5.1f}% B{ap.p_buff:>5.1f}% [{ap.verdict}]"
            print(f"  {agent:<12} {b_str}  →  {a_str}")

    # 리플 효과 (verdict 변경)
    ripple = []
    for agent, ap in after_map.items():
        if agent in changed_agents:
            continue
        bp = before_map.get(agent)
        if bp and bp.verdict != ap.verdict:
            ripple.append((agent, bp, ap))

    if ripple:
        print("\n  ─── 리플 효과 (verdict 변경) ────────────────────────────────")
        for agent, bp, ap in ripple:
            print(f"  {agent:<12} {bp.verdict:>14} → {ap.verdict:<14}  (N: {bp.p_nerf:.1f}→{ap.p_nerf:.1f}%  B: {bp.p_buff:.1f}→{ap.p_buff:.1f}%)")

    # 전체 너프/버프 순위 변동 (상위 5)
    print("\n  ─── After 전체 순위 (상위 10) ───────────────────────────────────")
    sorted_after = sorted(result.after, key=lambda x: max(x.p_nerf, x.p_buff), reverse=True)
    print(f"  {'#':<3} {'요원':<12} {'p_nerf':>8} {'p_buff':>8} {'verdict':>14}")
    for i, p in enumerate(sorted_after[:10], 1):
        marker = " ★" if p.agent in changed_agents else ""
        print(f"  {i:<3} {p.agent:<12} {p.p_nerf:>7.1f}% {p.p_buff:>7.1f}% {p.verdict:>14}{marker}")

    print()


# ─── CLI 엔트리포인트 ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Valorant 패치 시뮬레이터")
    parser.add_argument("--agent", type=str, help="요원 이름 (한/영)")
    parser.add_argument("--skill", type=str, choices=["Q", "E", "C", "X"], help="스킬 슬롯")
    parser.add_argument("--stat", type=str, help="변경할 스탯 (e.g. cooldown, damage)")
    parser.add_argument("--old", type=float, help="현재 값")
    parser.add_argument("--new", type=float, help="변경 후 값")
    parser.add_argument("--interactive", action="store_true", help="대화형 모드")

    args = parser.parse_args()

    print("모델 로딩 중...")
    sim = PatchSimulator()
    print("모델 로드 완료.\n")

    if args.interactive:
        _interactive_mode(sim)
    elif args.agent and args.skill and args.stat and args.old is not None and args.new is not None:
        agent = _normalize_agent(args.agent)
        change = StatChange(
            agent=agent,
            skill=args.skill,
            stat_name=args.stat,
            old_value=args.old,
            new_value=args.new,
        )
        result = sim.simulate([change])
        _print_result(result)
    else:
        parser.print_help()
        print("\n예시:")
        print("  python patch_simulator.py --agent Neon --skill E --stat cooldown --old 6 --new 8")
        print("  python patch_simulator.py --interactive")


def _interactive_mode(sim: PatchSimulator):
    """대화형 모드: 여러 변경을 누적 적용"""
    changes: list[StatChange] = []
    print("패치 시뮬레이터 대화형 모드")
    print("명령어: add(변경 추가) / run(시뮬레이션 실행) / clear(초기화) / quit(종료)")

    while True:
        cmd = input("\n> ").strip().lower()
        if cmd in ("quit", "q", "exit"):
            break
        elif cmd in ("clear", "c"):
            changes.clear()
            print("변경사항 초기화됨.")
        elif cmd in ("run", "r"):
            if not changes:
                print("변경사항이 없습니다. 'add'로 추가하세요.")
                continue
            print(f"\n{len(changes)}개 변경사항으로 시뮬레이션 실행 중...")
            result = sim.simulate(changes)
            _print_result(result)
        elif cmd in ("add", "a"):
            try:
                agent_input = input("  요원 (한/영): ").strip()
                agent = _normalize_agent(agent_input)
                skill = input("  스킬 (Q/E/C/X): ").strip().upper()
                if skill not in ("Q", "E", "C", "X"):
                    print("  잘못된 스킬 슬롯입니다.")
                    continue
                stat = input("  스탯 이름 (e.g. cooldown, damage, duration): ").strip()
                old_val = float(input("  현재 값: ").strip())
                new_val = float(input("  변경 후 값: ").strip())
                change = StatChange(agent=agent, skill=skill, stat_name=stat,
                                    old_value=old_val, new_value=new_val)
                changes.append(change)
                dir_ko = "너프" if change.direction == "nerf" else "버프"
                print(f"  ✓ {agent} [{skill}] {stat}: {old_val} → {new_val} ({dir_ko}, {change.magnitude}) 추가됨")
                print(f"  현재 {len(changes)}개 변경사항")
            except (ValueError, EOFError):
                print("  입력 오류. 다시 시도하세요.")
        elif cmd in ("list", "l"):
            if not changes:
                print("변경사항 없음")
            else:
                for i, c in enumerate(changes, 1):
                    dir_ko = "너프" if c.direction == "nerf" else "버프"
                    print(f"  {i}. {c.agent} [{c.skill}] {c.stat_name}: {c.old_value} → {c.new_value} ({dir_ko})")
        else:
            print("알 수 없는 명령어입니다. add / run / clear / list / quit")


if __name__ == "__main__":
    main()
