"""
maxmunzy/valorant-agent-stats 전처리 스크립트
GitHub: https://github.com/maxmunzy/valorant-agent-stats

수행 내용:
  - E2A1 ~ E9A3 전 액트 CSV를 GitHub Raw에서 다운로드
  - diamond1~3 + immortal1~3 + radiant 필터 → 다이아+ 합산
  - 에이전트별 액트별: 가중평균 승률, 합산 매치, 재계산 픽률
  - 저장: maxmunzy_diamond_plus.csv

실행: python preprocess_maxmunzy.py
"""

import io
import time
import requests
import pandas as pd

# ─── 상수 ──────────────────────────────────────────────────────────────────

BASE_RAW = "https://raw.githubusercontent.com/maxmunzy/valorant-agent-stats/main/csvs/{filename}"

# 액트 파일 목록 (파일명 → 액트명 매핑)
ACTS = [
    ("e2act1.csv", "E2A1"), ("e2act2.csv", "E2A2"), ("e2act3.csv", "E2A3"),
    ("e3act1.csv", "E3A1"), ("e3act2.csv", "E3A2"), ("e3act3.csv", "E3A3"),
    ("e4act1.csv", "E4A1"), ("e4act2.csv", "E4A2"), ("e4act3.csv", "E4A3"),
    ("e5act1.csv", "E5A1"), ("e5act2.csv", "E5A2"),
    ("e6act1.csv", "E6A1"), ("e6act2.csv", "E6A2"), ("e6act3.csv", "E6A3"),
    ("e7act1.csv", "E7A1"), ("e7act2.csv", "E7A2"), ("e7act3.csv", "E7A3"),
    ("e8act1.csv", "E8A1"), ("e8act2.csv", "E8A2"), ("e8act3.csv", "E8A3"),
    ("e9act1.csv", "E9A1"), ("e9act2.csv", "E9A2"), ("e9act3.csv", "E9A3"),
]

# 다이아+ 기준 placement 값
DIAMOND_PLUS = {
    "diamond1", "diamond2", "diamond3",
    "immortal1", "immortal2", "immortal3",
    "radiant",
}

# vstats.gg 데이터 시작 액트 (이후는 중복이지만 교차검증용으로 보존)
VSTATS_START = "E6A3"


# ─── 수집 ──────────────────────────────────────────────────────────────────

def fetch_act(filename: str, act_name: str) -> pd.DataFrame | None:
    url = BASE_RAW.format(filename=filename)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df["act_name"] = act_name
        return df
    except Exception as e:
        print(f"  ⚠  {act_name} 다운로드 실패: {e}")
        return None


def download_all() -> pd.DataFrame:
    frames = []
    for filename, act_name in ACTS:
        print(f"  다운로드: {act_name} ({filename})", end=" ... ", flush=True)
        df = fetch_act(filename, act_name)
        if df is not None:
            frames.append(df)
            print(f"OK ({len(df)}행)")
        time.sleep(0.3)

    if not frames:
        raise RuntimeError("다운로드된 데이터 없음")

    return pd.concat(frames, ignore_index=True)


# ─── 전처리 ────────────────────────────────────────────────────────────────

def preprocess(raw: pd.DataFrame) -> pd.DataFrame:
    # 1. 다이아+ 필터
    dp = raw[raw["placement"].isin(DIAMOND_PLUS)].copy()
    print(f"\n다이아+ 필터: {len(raw)}행 → {len(dp)}행")

    # 2. win_rate: 0~1 비율 → % 변환
    dp["win_rate_pct"] = (dp["win_rate"] * 100).round(2)

    # 3. 액트별 전체 매치 합산 (픽률 분모)
    #    각 placement의 전체 에이전트 매치수 합산 → 다이아+ 전체 합산
    total_by_act = (
        dp.groupby("act_name")["matches"]
        .sum()
        .rename("total_matches_dp")
    )

    # 4. 에이전트 × 액트별 다이아+ 합산
    agg = (
        dp.groupby(["agent", "act_name"])
        .apply(lambda g: pd.Series({
            "matches":       g["matches"].sum(),
            # 가중평균 승률
            "win_rate_pct":  (
                (g["win_rate_pct"] * g["matches"]).sum() / g["matches"].sum()
                if g["matches"].sum() > 0 else None
            ),
            # 가중평균 KD
            "kd":            (
                (g["kd"] * g["matches"]).sum() / g["matches"].sum()
                if g["matches"].sum() > 0 else None
            ),
            "kills":         (
                (g["kills"] * g["matches"]).sum() / g["matches"].sum()
                if g["matches"].sum() > 0 else None
            ),
            "deaths":        (
                (g["deaths"] * g["matches"]).sum() / g["matches"].sum()
                if g["matches"].sum() > 0 else None
            ),
            "avg_score":     (
                (g["avg_score"] * g["matches"]).sum() / g["matches"].sum()
                if g["matches"].sum() > 0 else None
            ),
        }), include_groups=False)
        .reset_index()
    )

    # 5. 픽률 계산: 에이전트 매치 / 액트 전체 다이아+ 매치
    agg = agg.merge(total_by_act, on="act_name", how="left")
    agg["pick_rate_pct"] = (agg["matches"] / agg["total_matches_dp"] * 100).round(3)

    # 6. 정렬 & 반올림
    act_order = [a for _, a in ACTS]
    agg["act_idx"] = agg["act_name"].map({a: i for i, a in enumerate(act_order)})
    agg = agg.sort_values(["act_idx", "agent"]).reset_index(drop=True)

    agg["win_rate_pct"] = agg["win_rate_pct"].round(2)
    agg["kd"]           = agg["kd"].round(3)
    agg["kills"]        = agg["kills"].round(1)
    agg["deaths"]       = agg["deaths"].round(1)
    agg["avg_score"]    = agg["avg_score"].round(0)

    # 7. source 태그 (vstats 겹치는 구간 표시)
    agg["source"] = "maxmunzy"
    agg.loc[agg["act_name"] >= VSTATS_START, "overlap_vstats"] = True
    agg["overlap_vstats"] = agg["overlap_vstats"].fillna(False)

    cols = [
        "act_name", "act_idx", "agent",
        "win_rate_pct", "pick_rate_pct", "matches", "total_matches_dp",
        "kd", "kills", "deaths", "avg_score",
        "source", "overlap_vstats",
    ]
    return agg[cols]


# ─── 요약 출력 ─────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame):
    print("\n" + "=" * 65)
    print(f"총 {len(df)}행  |  액트 {df['act_name'].nunique()}개  |  에이전트 {df['agent'].nunique()}개")
    print(f"구간: {df['act_name'].iloc[0]} ~ {df['act_name'].iloc[-1]}")
    print()

    # 주요 케이스: Chamber(E5), Jett(E4), Skye(E7~), Yoru(E6~)
    key_agents = ["Chamber", "Jett", "Skye", "Yoru", "Neon", "Viper"]
    for agent in key_agents:
        sub = df[df["agent"] == agent][["act_name", "win_rate_pct", "pick_rate_pct", "matches"]]
        if sub.empty:
            continue
        print(f"[{agent}]")
        print(sub.to_string(index=False))
        print()

    print("=" * 65)


# ─── 메인 ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("maxmunzy/valorant-agent-stats 전처리")
    print("Diamond+ (diamond1~3 + immortal1~3 + radiant) 합산")
    print(f"구간: E2A1 ~ E9A3  ({len(ACTS)}개 액트)")
    print("=" * 65 + "\n")

    print("[1] 다운로드")
    raw = download_all()
    print(f"\n전체 다운로드: {len(raw)}행 / {raw['act_name'].nunique()}액트\n")

    print("[2] 전처리 (다이아+ 합산)")
    df = preprocess(raw)

    out = "maxmunzy_diamond_plus.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out}")

    print_summary(df)


if __name__ == "__main__":
    main()
