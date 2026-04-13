# 발로란트 패치 예측 모델 — 피처 및 학습 전략

> 기준일: 2026-04-13
> 학습 데이터: `step2_training_data.csv` (659행 / 29 요원 / E2A1 ~ V25A5)
> V26A2(현재 진행 중)는 학습 제외 — 레이블 미확정
> 모델: 2-Stage Hierarchical Classification (양쪽 모두 XGBoost)
> Stage A: stable vs patched — 50 피처 / train-only 1:1 undersampling
> Stage B: buff vs nerf — 51 피처 / SMOTE oversampling

---

## 모델 구조 요약

| Stage | 목적 | 모델 | 피처 수 | 출력 |
|-------|------|------|---------|------|
| A | 이번 액트에 패치가 올까? | XGBoost | 50 | stable / patched 확률 |
| B | 너프인가 버프인가? | XGBoost | 51 | buff / nerf 확률 |

- Stage A에서 patched로 판정된 요원만 Stage B로 진입
- 최종 출력: p_nerf, p_buff, p_stable (3-class 확률)
- Severity (mild/strong)는 패치 컨텍스트(followup/correction) 및 스킬 중요도(E/X)로 결정
- **도메인 규칙 없음** — 모델 출력 확률을 그대로 사용 (정규화만 적용)

---

## 검증 결과 (2026-04-13)

| Metric | Value |
|---|---|
| Stage A balanced accuracy | **0.6614** |
| Stage B balanced accuracy | **0.7779** |

Stage B 모델 비교:
- XGBoost: **0.7779** (채택)
- LR: 0.7711

---

## 피처셋 분리 구조

Stage A와 Stage B는 **독립된 피처셋**을 사용. 공통 드롭 목록(DROP_COLS_COMMON) 외에 각 스테이지 전용 드롭 목록이 존재.

```
DROP_COLS_COMMON  →  양쪽에서 모두 제거
DROP_COLS_A_ONLY  →  Stage A에서만 제거 (Stage B에서는 활성)
DROP_COLS_B_ONLY  →  Stage B에서만 제거 (Stage A에서는 활성)
```

| 구분 | Stage A 전용 드롭 | Stage B 전용 드롭 |
|------|---|---|
| 피처 | `vct_data_lag` (A=0.000) | `vct_pr_avg` (B=0.000) |
|      | `geo_synergy` (A=0.006) | `kit_score` (B=0.000) |
|      | `vct_pr_peak_all` (A=0.005) | `recent_dual_miss_count` (B=0.000) |
|      | `n_nerf_patches` (A=0.010) | `map_hhi` (B=0.000) |
|      | `n_total_patches` (A=0.012) | |

결과:
- Stage A: 46 공통 + 4 A전용 = **50 피처**
- Stage B: 46 공통 + 5 B전용 = **51 피처**

Stage A 전용 활성 (B에서는 드롭):
- `kit_score` — 스킬 등급 가중 평균. Stage A SHAP 0.080 (#10)
- `map_hhi` — 맵 편중도. 맵 종속 요원 판별에 유효
- `recent_dual_miss_count` — 최근 랭크+VCT 모두 MISS. Stage A SHAP 0.074 (#13)
- `vct_pr_avg` — VCT 픽률 역대 평균. Stage A SHAP 0.026

Stage B 전용 활성 (A에서는 드롭):
- `vct_data_lag` — VCT 데이터 지연. Stage B SHAP 0.104 (#18)
- `geo_synergy` — 맵 지오메트리 시너지. Stage B SHAP 0.048
- `n_nerf_patches` — 누적 너프 횟수. Stage B SHAP 0.043
- `n_total_patches` — 전체 패치 횟수. Stage B SHAP 0.012
- `vct_pr_peak_all` — 역대 최고 VCT 픽률. Stage B SHAP 0.015

---

## 레이블 생성 원칙

### 5-class 레이블 체계

| Label | 설명 |
|---|---|
| `stable` | 지표가 베이스라인 근처, 패치 압박 없음 |
| `mild_nerf` | 비패치: 너프 신호 지속 중 / 패치: 첫 너프 + 보조 스킬 |
| `strong_nerf` | 패치: followup/correction 너프 OR 핵심 스킬(E/X) 너프 |
| `mild_buff` | 비패치: 버프 신호 지속 중 / 패치: 첫 버프 + 보조 스킬 |
| `strong_buff` | 패치: followup/correction 버프 OR 핵심 스킬 버프 OR rework |

핵심 원칙:
- **strong은 실제 패치 행에서만 부여** (비패치 행은 최대 mild)
- **요원별 베이스라인 기준**: 제트(13.93%) 같은 고픽 요원은 높은 기준, 하버(0.43%)는 낮은 기준
- **지속성 조건**: rank_pr_slope >= -0.8 (이미 급하락 중이면 stable 복귀)

### 레이블 분포

```
stable         347  (52.7%)
mild_buff      111  (16.8%)
mild_nerf      109  (16.5%)
strong_nerf     54  ( 8.2%)
strong_buff     38  ( 5.8%)
```

### classify_stable_state (비패치 행 레이블)

요원별 베이스라인 대비 초과/미달로 신호 판단 (원본 스케일 직접 비교):

```
너프 방향 (하나라도 해당):
  A) rank 신호: rank_pr_excess > 1.5  AND  rank_wr > 50%
  B) VCT 상대 신호: vct_pr_excess > 10.0 (역대 평균 대비)
  C) VCT 절대 지배: vct_pr > 35% (역대 평균 무관 — Viper/Omen 타입)

버프 방향 (하나라도 해당):
  A) rank 신호: rank_pr_excess < -0.5  AND  rank_wr < 49.5%
  B) 픽률 극단: rank_pr < 1.0
```

### VCT 절대 임계값 (35%)

VCT 픽률 35% 이상인 요원은 역대 평균과 무관하게 `mild_nerf` 부여.
Viper/Omen처럼 항상 VCT에서 높은 요원은 상대 지표(vct_pr_excess)로는 감지 불가능.

### 신호 캐리오버 (Signal Carryover)

이전 액트에서 mild_nerf/mild_buff였고, 지표가 아직 해소되지 않았으면 레이블 유지.
이전 트리거 조건이 하나라도 남아있으면 유지, 전부 해소되면 stable 복귀.

### build_patch_label (패치 행 레이블)

strong 기준:
- followup: 이전 패치가 MISS → 추가 조정
- correction: 이전 패치가 OVERSHOOT → 반대 방향 수정
- 핵심 스킬(E/X) 변경
- rework 필요 (rank + VCT 모두 극단적 저조)

---

## 피처 설계: 2D Quadrant System

### 핵심 인사이트

라이엇의 패치 결정은 **2D 평면 (픽률 × 승률)** 위에서 이루어짐.
1D 지표(픽률만, 승률만)를 독립적으로 보면 핵심 신호를 놓침.

### Rank 2D Quadrant (요원별 베이스라인 중심)

```
                   WR above agent avg
                        |
    Q2 Niche OP         |         Q1 Nerf target
    (low PR, high WR)   |   (high PR, high WR)
                        |
   ──────────────────────┼──────────── PR above baseline
                        |
    Q3 Buff target       |         Q4 Fandom
    (low PR, low WR)     |   (high PR, low WR)
                        |
                   WR below agent avg
```

- PR 축: 요원 자신의 역대 평균 픽률 (baseline)
- WR 축: 요원 자신의 역대 평균 승률 (절대 50%가 아님)

---

## SHAP 피처 중요도

### Stage A Top 15 (stable vs patched)

| Rank | Feature | SHAP | 설명 |
|---|---|---|---|
| 1 | rank_pr_excess | 0.163 | 요원 베이스라인 대비 픽률 초과 |
| 2 | vct_pr_last | 0.155 | 최근 VCT 픽률 |
| 3 | wr_buff_signal | 0.133 | 승률 버프 신호 |
| 4 | strength_vs_direction | 0.123 | 현재 강도 vs 마지막 패치 방향 |
| 5 | tier_gap | 0.122 | kit_score - agent_tier_score |
| 6 | rank_pr_slope | 0.119 | 픽률 추세 기울기 |
| 7 | last_pr_pre | 0.103 | 마지막 패치 직전 픽률 |
| 8 | rank_wr | 0.098 | 현재 랭크 승률 |
| 9 | kit_x_rank_pr | 0.089 | kit등급 × 픽률 교차 |
| 10 | kit_score | 0.080 | 스킬 등급 가중 평균 (A전용) |
| 11 | pr_pct_of_peak | 0.075 | 역대 피크 대비 현재 위치 |
| 12 | pr_slope_5act | 0.074 | 5액트 픽률 추세 |
| 13 | recent_dual_miss_count | 0.074 | 랭크+VCT 모두 MISS 횟수 (A전용) |
| 14 | vct_pr_slope | 0.072 | VCT 픽률 추세 |
| 15 | skill_ceiling_score | 0.068 | 실력 천장 프록시 |

### Stage A Bottom 10

| Rank | Feature | SHAP |
|---|---|---|
| 41 | vct_pr_avg | 0.026 |
| 42 | rank_pr_vs_peak | 0.026 |
| 43 | last_buff_acts_ago | 0.027 |
| 44 | rank_wr_hist_mean | 0.028 |
| 45 | pr_effect_ratio | 0.022 |
| 46 | vct_wr_last | 0.022 |
| 47 | vct_buff_signal | 0.018 |
| 48 | vct_pr_excess | 0.018 |
| 49 | agent_replaceability | 0.024 |
| 50 | rank_niche_2d | 0.010 |

### Stage B Top 15 (buff vs nerf)

| Rank | Feature | SHAP | 설명 |
|---|---|---|---|
| 1 | rank_pr_avg3 | 0.383 | 최근 3액트 평균 픽률 |
| 2 | pr_pct_of_peak | 0.346 | 역대 피크 대비 현재 |
| 3 | skill_ceiling_x_vct_pr | 0.342 | 실력천장 × VCT 픽률 교차 |
| 4 | vct_pr_last | 0.291 | 최근 VCT 픽률 |
| 5 | last_pr_pre | 0.280 | 마지막 패치 직전 픽률 |
| 6 | vct_wr_last | 0.280 | 최근 VCT 승률 |
| 7 | rank_pr | 0.277 | 현재 랭크 픽률 |
| 8 | acts_since_patch | 0.251 | 마지막 패치 이후 경과 액트 |
| 9 | vct_rel_pos | 0.236 | VCT 상대 포지션 |
| 10 | rank_pr_vs_peak | 0.212 | 현재 / 역대 최고 비율 |
| 11 | rank_niche_2d | 0.204 | Q2: 저픽 × 고승 (니치 OP) |
| 12 | rank_pr_delta | 0.183 | 최근 2액트 픽률 변화 |
| 13 | rank_pr_excess | 0.152 | 베이스라인 대비 초과 |
| 14 | vct_last_act_idx | 0.148 | VCT 마지막 이벤트 시점 |
| 15 | pr_slope_5act | 0.134 | 5액트 픽률 추세 |

### Stage B Bottom 10

| Rank | Feature | SHAP |
|---|---|---|
| 42 | n_total_patches | 0.012 |
| 43 | vct_pr_peak_all | 0.015 |
| 44 | vct_pr_excess | 0.019 |
| 45 | last_trigger_type | 0.020 |
| 46 | vct_pr_vs_agent_avg | 0.024 |
| 47 | rank_wr_vs_agent_avg | 0.028 |
| 48 | agent_replaceability | 0.012 |
| 49 | vct_must_nerf | 0.004 |
| 50 | pro_rank_ratio | 0.004 |
| 51 | skill_ceiling_score | 0.039 |

---

## 공통 드롭 피처 (DROP_COLS_COMMON)

양쪽 Stage에서 모두 제거된 피처. 주요 카테고리:

**메타/누출 컬럼**: agent, act, act_idx, label, horizon, label_direction 등
**미래 누수**: vct_pr_post, vct_wr_post, rank_pr_t+1, rank_wr_t+1
**요원별 고정 상수**: agent_pr_baseline, pr_vs_baseline, pr_wr_gap
**이진 스킬 보유 플래그**: has_smoke~has_blind, high_value_smoke/cc — 전부 SHAP=0
**util 상대 비율**: util_smoke_rank_pr_ratio ~ util_blind_rank_pr_ratio — has_*와 동일, SHAP=0
**v3 2D SHAP=0**: vct_nerf_2d, vct_buff_2d, rank_fandom_2d, cross_nerf_2d, rank_only_nerf, wr_nerf_signal 등
**기타 SHAP=0**: buff_hit_flag, nerf_hit_flag, vct_profile, buff_miss_flag, nerf_miss_flag, map_explains_vct_drop, top_map_in_rotation 등
**Leak 위험**: dir_verdict_code, last_direction, rank_wr_vs50

---

## 학습 전략

### Walk-forward Temporal CV
- 시계열 누출 방지: KFold shuffle 사용 안 함
- OOF 예측을 시간 순서대로 생성
- 3-fold walk-forward split (min_train_ratio=0.5)

### Stage A: Train-only 1:1 Undersampling
- stable이 다수 클래스 → patched 수에 맞춰 stable을 1:1 언더샘플링
- 검증 셋은 원본 분포 유지
- Class weight: balanced

### Stage B: SMOTE Oversampling + XGBoost
- buff가 소수 클래스 → SMOTE로 오버샘플링
- k_neighbors = min(3, minority_count - 1)
- 검증 셋은 원본 분포 유지
- XGBoost가 LR을 역전 (0.7779 > 0.7711) — 피처 분리 후 XGB가 Stage B 전용 피처를 더 잘 활용

### HPO: Optuna TPE Sampler
- 60 trials per stage
- Walk-forward temporal CV 기준 balanced accuracy 최적화
- `--fast`: 저장된 하이퍼파라미터 재사용
- `--hpo`: HPO 강제 재실행

### 피처 선택: SHAP Importance + Stage 분리
- 학습 후 SHAP importance 분석
- Stage A + Stage B 모두에서 SHAP < 0.02인 피처 → DROP_COLS_COMMON
- 한 Stage에서만 SHAP ≈ 0인 피처 → 해당 Stage 전용 드롭 (다른 Stage에서는 유지)
- 예: `vct_data_lag` Stage A SHAP=0.000이지만 Stage B SHAP=0.104 → A에서만 드롭

### 도메인 규칙
**전부 제거.** 이전에 6개 규칙(acts_since 억제, MISS 방향 재가중, both_weak 상향, skill_ceiling 너프 강화, VCT 승률 극단 보정 등)이 있었으나 모두 제거. 모델이 피처에서 직접 학습하므로 수동 보정 불필요.

---

## 스케일 메모

rank_pr은 **원본 스케일** (1~17 범위)로 사용. 이전 버전에서 `rank_pr * 5`로 %p 변환하던 것은 베이스라인과의 스케일 불일치를 유발하여 제거.
- 베이스라인도 원본 스케일 (예: Jett 13.93, Harbor 0.43)
- rank_pr_excess = rank_pr - baseline (직접 비교)
- 임계값도 원본 스케일 기준 (NERF_PR_THRESH=1.5 ≈ 7.5%p 초과)

---

## 피처 설계 원칙

1. **2D 사분면 설계**: 픽률·승률을 독립 1D가 아닌 2D 평면으로 교차
2. **요원별 베이스라인 중심**: 절대 기준 대신 요원 자신의 역대 평균을 중심점으로 사용
3. **VCT 절대 + 상대 이중 기준**: 상대 지표만으로는 Viper/Omen 타입 감지 불가 → 35% 절대 기준 병행
4. **Stage A/B 독립 피처셋**: 각 Stage의 SHAP 결과에 따라 독립적으로 피처 최적화
5. **정적 플래그 단독 사용 금지**: `has_smoke=1`은 SHAP=0. 반드시 픽률·승률과 교차
6. **시계열 누출 방지**: Walk-forward temporal split, label leak 피처 제거
7. **도메인 룰 전면 제거**: 모델이 직접 학습하도록 위임, 수동 보정 없음
8. **신호 캐리오버**: 비패치 레이블은 이전 액트 신호가 해소되지 않으면 유지
