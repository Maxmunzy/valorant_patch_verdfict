"""
backtest_predictions.csv 를 프론트가 읽기 좋은 JSON 요약으로 변환.

출력: frontend/public/backtest-summary.json
구성:
  - overall: hit_rate, balanced_accuracy, per-class precision/recall
  - highConf: p_nerf/p_buff 임계값별 precision
  - perAct: 액트별 n / 3-class 적중률 / 5-class 적중률 / 최근 5 표시용
  - stories: 눈에 띄는 케이스 (정답/오답 각 3~5건)
  - predictions: 전체 목록 (agent, act, label_true, verdict, p_*, hit)

  - generatedAt: ISO timestamp
  - totalRows: 전체 예측 수
"""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import (balanced_accuracy_score, classification_report,
                             confusion_matrix)

IN_CSV  = "backtest_predictions.csv"
OUT_JSON = "frontend/public/backtest-summary.json"


def _round(x, n=3):
    try:
        return round(float(x), n)
    except Exception:
        return None


def main():
    df = pd.read_csv(IN_CSV)
    n = len(df)

    # ── Overall ──────────────────────────────────────────────────────────
    labels3 = ["stable", "buff", "nerf"]
    y_t, y_p = df["dir_true"].values, df["dir_pred"].values
    ba3     = balanced_accuracy_score(y_t, y_p)
    hit3    = float(df["hit_dir"].mean())
    hit5    = float(df["hit_5class"].mean())

    report3 = classification_report(y_t, y_p, labels=labels3,
                                    target_names=labels3,
                                    zero_division=0,
                                    output_dict=True)

    cm = confusion_matrix(y_t, y_p, labels=labels3).tolist()

    # ── 고확신 구간 ──────────────────────────────────────────────────────
    def prec_at(mask, col, target):
        sub = df[mask]
        if len(sub) == 0:
            return {"n": 0, "precision": 0.0}
        return {
            "n": int(len(sub)),
            "precision": _round((sub[col] == target).mean(), 3),
        }

    high_conf = {
        "nerf": [
            {"threshold": t, **prec_at(df["p_nerf_dir"] >= t, "dir_true", "nerf")}
            for t in [0.30, 0.40, 0.50, 0.60, 0.70]
        ],
        "buff": [
            {"threshold": t, **prec_at(df["p_buff_dir"] >= t, "dir_true", "buff")}
            for t in [0.15, 0.20, 0.25, 0.35, 0.50]
        ],
    }

    # ── Top-K per-act nerf precision ─────────────────────────────────────
    top_nerf = (df.sort_values(["act", "p_nerf_dir"], ascending=[True, False])
                  .groupby("act")
                  .head(3))
    top_nerf_prec = _round((top_nerf["dir_true"] == "nerf").mean(), 3)

    # ── 액트별 성과 ──────────────────────────────────────────────────────
    per_act = (df.groupby(["act", "act_idx"])
                 .agg(n=("agent", "size"),
                      hit_dir=("hit_dir", "mean"),
                      hit_5=("hit_5class", "mean"))
                 .reset_index()
                 .sort_values("act_idx")
                 .to_dict(orient="records"))

    per_act = [
        {
            "act": r["act"],
            "act_idx": int(r["act_idx"]),
            "n": int(r["n"]),
            "hit_dir": _round(r["hit_dir"]),
            "hit_5": _round(r["hit_5"]),
        }
        for r in per_act
    ]

    # ── 스토리: 한 액트 일찍 맞춘 케이스 ──────────────────────────────────
    # 직전 액트에서 nerf 예측했는데 "stable" 판정 났다가, 다음 액트에서 실제로 nerf된 케이스
    sorted_df = df.sort_values(["agent", "act_idx"]).reset_index(drop=True)
    lead_hits = []
    for agent, g in sorted_df.groupby("agent"):
        g = g.reset_index(drop=True)
        for i in range(len(g) - 1):
            cur, nxt = g.iloc[i], g.iloc[i + 1]
            if cur["dir_pred"] == "nerf" and cur["dir_true"] != "nerf" \
               and nxt["dir_true"] == "nerf":
                lead_hits.append({
                    "agent": agent,
                    "predictedAt": cur["act"],
                    "hitAt": nxt["act"],
                    "pNerf": _round(cur["p_nerf_dir"]),
                    "truthAtPred": cur["label_true"],
                    "truthAtHit":  nxt["label_true"],
                })
    # p_nerf 큰 순으로 상위 5개
    lead_hits = sorted(lead_hits, key=lambda x: x["pNerf"] or 0, reverse=True)[:5]

    # ── 큰 오답: p_nerf >= 0.6인데 실제는 nerf 아닌 것 / p_buff >= 0.35인데 buff 아님
    big_misses = []
    for _, row in df[(df["p_nerf_dir"] >= 0.6) & (df["dir_true"] != "nerf")].iterrows():
        big_misses.append({
            "agent": row["agent"],
            "act": row["act"],
            "predicted": row["verdict"],
            "truth": row["label_true"],
            "pNerf": _round(row["p_nerf_dir"]),
            "pBuff": _round(row["p_buff_dir"]),
            "kind": "nerf_false_positive",
        })
    for _, row in df[(df["p_buff_dir"] >= 0.35) & (df["dir_true"] != "buff")].iterrows():
        big_misses.append({
            "agent": row["agent"],
            "act": row["act"],
            "predicted": row["verdict"],
            "truth": row["label_true"],
            "pNerf": _round(row["p_nerf_dir"]),
            "pBuff": _round(row["p_buff_dir"]),
            "kind": "buff_false_positive",
        })
    # 상위 p로 정렬 + 5건
    big_misses.sort(
        key=lambda x: (x["pNerf"] if x["kind"].startswith("nerf") else x["pBuff"]) or 0,
        reverse=True,
    )
    big_misses = big_misses[:6]

    # ── 큰 적중: p_nerf >= 0.6 이고 실제 nerf / p_buff >= 0.3 이고 실제 buff
    big_hits = []
    for _, row in df[(df["p_nerf_dir"] >= 0.6) & (df["dir_true"] == "nerf")].iterrows():
        big_hits.append({
            "agent": row["agent"],
            "act": row["act"],
            "predicted": row["verdict"],
            "truth": row["label_true"],
            "pNerf": _round(row["p_nerf_dir"]),
            "kind": "nerf_hit",
        })
    for _, row in df[(df["p_buff_dir"] >= 0.30) & (df["dir_true"] == "buff")].iterrows():
        big_hits.append({
            "agent": row["agent"],
            "act": row["act"],
            "predicted": row["verdict"],
            "truth": row["label_true"],
            "pBuff": _round(row["p_buff_dir"]),
            "kind": "buff_hit",
        })
    big_hits.sort(
        key=lambda x: (x.get("pNerf") or 0) + (x.get("pBuff") or 0),
        reverse=True,
    )
    big_hits = big_hits[:6]

    # ── 요원별 적중률 Top / Worst ────────────────────────────────────────
    # 예측 n >= 3 요원만 대상 (통계 노이즈 방지)
    agent_agg = (df.groupby("agent")
                   .agg(n=("act", "size"),
                        hits=("hit_dir", "sum"),
                        hit_rate=("hit_dir", "mean"))
                   .reset_index())
    agent_agg = agent_agg[agent_agg["n"] >= 3]

    # 적중률 높은 순 (동률이면 n 많은 순)
    best = agent_agg.sort_values(["hit_rate", "n"], ascending=[False, False]).head(5)
    top_agents_hit = [
        {
            "agent":   r["agent"],
            "n":       int(r["n"]),
            "hits":    int(r["hits"]),
            "misses":  int(r["n"] - r["hits"]),
            "hitRate": _round(r["hit_rate"]),
        }
        for _, r in best.iterrows()
    ]

    # 적중률 낮은 순 (동률이면 n 많은 순 — 여러 번 틀린 쪽이 더 의미 있음)
    worst = agent_agg.sort_values(["hit_rate", "n"], ascending=[True, False]).head(5)
    top_agents_miss = [
        {
            "agent":   r["agent"],
            "n":       int(r["n"]),
            "hits":    int(r["hits"]),
            "misses":  int(r["n"] - r["hits"]),
            "hitRate": _round(r["hit_rate"]),
        }
        for _, r in worst.iterrows()
    ]

    # ── 전체 예측 목록 (프론트 테이블용) ─────────────────────────────────
    predictions = []
    for _, row in df.iterrows():
        predictions.append({
            "agent":     row["agent"],
            "act":       row["act"],
            "actIdx":    int(row["act_idx"]),
            "truth":     row["label_true"],
            "predicted": row["verdict"],
            "dirTruth":  row["dir_true"],
            "dirPred":   row["dir_pred"],
            "pStable":   _round(row["p_stable"]),
            "pBuffDir":  _round(row["p_buff_dir"]),
            "pNerfDir":  _round(row["p_nerf_dir"]),
            "hitDir":    bool(row["hit_dir"]),
            "hit5":      bool(row["hit_5class"]),
        })

    acts_sorted = sorted(df["act"].unique(), key=lambda a: df[df["act"] == a]["act_idx"].iloc[0])

    summary = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "totalRows":   n,
        "acts": acts_sorted,
        "actRange": {
            "first": acts_sorted[0] if acts_sorted else None,
            "last":  acts_sorted[-1] if acts_sorted else None,
        },
        "overall": {
            "hitRate3":         _round(hit3),
            "hitRate5":         _round(hit5),
            "balancedAccuracy": _round(ba3),
            "classes": {
                c: {
                    "precision": _round(report3[c]["precision"]),
                    "recall":    _round(report3[c]["recall"]),
                    "f1":        _round(report3[c]["f1-score"]),
                    "support":   int(report3[c]["support"]),
                }
                for c in labels3 if c in report3
            },
            "confusionMatrix": cm,
            "confusionLabels": labels3,
        },
        "highConf": high_conf,
        "topK": {
            "nerfPrecisionTop3PerAct": top_nerf_prec,
            "nerfTop3Sample": int(len(top_nerf)),
        },
        "perAct": per_act,
        "stories": {
            "leadHits":  lead_hits,
            "bigHits":   big_hits,
            "bigMisses": big_misses,
        },
        "topAgents": {
            "hits":   top_agents_hit,
            "misses": top_agents_miss,
        },
        "predictions": predictions,
    }

    out_path = pathlib.Path(OUT_JSON)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[OK] {OUT_JSON}")
    print(f"  rows: {n}  acts: {len(acts_sorted)} ({acts_sorted[0]} .. {acts_sorted[-1]})")
    print(f"  3-class hit: {hit3:.3f}  BA: {ba3:.3f}")
    print(f"  leadHits: {len(lead_hits)}  bigHits: {len(big_hits)}  bigMisses: {len(big_misses)}")


if __name__ == "__main__":
    main()
