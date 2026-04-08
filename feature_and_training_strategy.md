# 발로란트 패치 예측 모델 — 피처 및 학습 전략

> 기준일: 2026-04-08
> 학습 데이터: `step2_training_data.csv` (939행 / 29 요원 / E2A1 ~ V26A2)
> Stage A 학습: 596행 (horizon=1, stable_strong/weak 제외)
> Stage B 학습: 655행 (horizon=1,2,3, patched 케이스만)
> 모델: XGBoost 2-Stage (Stage A: stable vs patched / Stage B: 패치 유형 5분류)

---

## 모델 구조 요약

| Stage | 목적 | 학습 데이터 | 출력 |
|-------|------|------------|------|
| A | 이번 액트에 패치가 올까? | horizon=1 행 (596행) | stable / patched 확률 |
| B | 어떤 종류의 패치일까? | horizon=1,2,3 행 (655행) | nerf_rank / buff_rank / nerf_followup / buff_followup / rework |

- Stage A 임계값: **0.28**
- V26A2(현재 진행 중 액트)는 학습 제외 — 미래 레이블 미확정

---

## 레이블 생성 원칙

### classify_stable_state (패치 없는 액트 / 버그픽스 액트)

매 액트마다 현재 수치만으로 독립 재판정. 이력 조건 없음.

```
nerf_followup:
  - rank_pr_pct >= 20% AND rank_wr_vs50 >= 0%   (랭크 지배)
  - rank_wr_vs50 >= 2.5%                          (고승률 극단)
  - vct_pr >= 40% AND map_hhi <= 0.15 AND rank_wr_vs50 >= -1%  (pro_dom + 맵 비종속)

buff_followup:
  - rank_pr_pct <= 12% AND rank_wr_vs50 <= -1.5% (랭크 부진)
  - rank_wr_vs50 <= -4%                           (저승률 극단)
  - rank_pr_pct <= 5%                             (존재감 없음)
```

**pro_dom 조건의 map_hhi 제약**: 맵 로테이션 영향을 받는 맵 특화 요원(map_hhi > 0.15)은 VCT 픽률이 높아도 레이블에 반영하지 않음. 모델 피처(vct_pr_last)로는 계속 활용.

**버그픽스 처리**: nerf/buff 없는 패치는 `stable` 고정이 아닌 `classify_stable_state()` 수치 재판정.

---

## 멀티 호라이즌

```
horizon=1: (agent, t) 피처 → t+1 패치 레이블  ← Stage A + B
horizon=2: (agent, t) 피처 → t+2 실제 패치 레이블  ← Stage B만
horizon=3: (agent, t) 피처 → t+3 실제 패치 레이블  ← Stage B만
```

horizon=2,3은 실제 nerf/buff 패치가 있는 경우만 생성 (규칙 기반 레이블 제외).
같은 피처에 다른 레이블이 혼재하는 것을 방지하기 위해 Stage A는 horizon=1만 사용.

---

## 피처 목록 (SHAP 평균 중요도, 2026-04-08 기준)

> Stage A SHAP: stable vs patched 이진분류
> Stage B SHAP: 패치 유형 5분류

### 1. 랭크 승률 피처

| 피처 | 설명 |
|------|------|
| `rank_wr` | 현재 액트 랭크 승률 (%). Stage A SHAP 1위 |
| `rank_wr_vs50` | 랭크 승률 - 50%. 양수=과강, 음수=과약 신호 |

### 2. 패치 방향·결과 피처

| 피처 | 설명 |
|------|------|
| `last_wr_post` | 마지막 패치 후 승률. 패치 효과 측정 핵심 |
| `strength_vs_direction` | 현재 강도(승률·픽률) vs 마지막 패치 방향 일치도. 너프 후 여전히 강하면 추가 너프 신호 |
| `last_rank_verdict` | 마지막 패치 후 랭크 반응 (HIT/MISS/FAIL) 인코딩 |
| `last_vct_verdict` | 마지막 패치 후 VCT 반응 인코딩 |
| `nerf_miss_flag` | 너프했는데 여전히 강함 (MISS). Stage B 패치 유형 분류 핵심 신호 |
| `buff_miss_flag` | 버프했는데 여전히 약함 (MISS) |
| `recent_dual_miss_count` | 최근 랭크·VCT 둘 다 MISS 횟수. 누적 조정 실패 신호 |
| `dir_verdict_code` | 마지막 패치 방향 수치 인코딩 (-1/0/1) |

### 3. VCT(프로씬) 피처

| 피처 | 설명 |
|------|------|
| `vct_pr_last` | 최근 VCT 픽률 (%). NaN → 0 처리 |
| `vct_wr_last` | 최근 VCT 승률 (%). NaN → 50.0 처리 |
| `vct_pre_n` | 최근 VCT 이벤트 참여 횟수. 대회 노출도 |
| `vct_pr_avg` | 전체 VCT 픽률 평균 |
| `vct_pr_slope` | VCT 픽률 추세 |
| `vct_pr_delta` | 최근 2 VCT 이벤트 간 픽률 변화 (신규) |
| `vct_pr_peak_all` | 역대 최고 VCT 픽률 |
| `vct_profile` | VCT 픽률 프로파일 인코딩 |
| `pro_rank_ratio` | VCT 픽률 / 랭크 픽률. 프로 편향 요원 판별 |
| `vct_low_unexpected` | 설계 의도 대비 VCT 픽률이 낮은 경우 플래그 |

### 4. 랭크 픽률 피처

| 피처 | 설명 |
|------|------|
| `rank_pr` | 현재 액트 랭크 픽률 (slots 단위, × 5 = %) |
| `rank_pr_avg3` | 최근 3액트 평균 랭크 픽률. 단발 노이즈 제거 |
| `rank_pr_slope` | 랭크 픽률 추세 기울기 |
| `rank_pr_delta` | 최근 2액트 간 픽률 변화 (신규) |
| `rank_pr_vs_peak` | 현재 픽률 / 역대 최고 픽률 비율 |
| `rank_pr_peak` | 역대 최고 랭크 픽률 |

### 5. 패치 이력 피처

| 피처 | 설명 |
|------|------|
| `n_total_patches` | 전체 패치 횟수 누적 |
| `n_nerf_patches` | 누적 너프 횟수 |
| `n_buff_patches` | 누적 버프 횟수 |
| `acts_since_patch` | 마지막 패치 이후 경과 액트 수 |
| `last_direction` | 마지막 패치 방향 인코딩 |
| `patch_streak` | 연속 패치 횟수 |
| `last_pr_pre` | 마지막 패치 직전 픽률 |

### 6. 요원 설계 피처

| 피처 | 설명 |
|------|------|
| `skill_ceiling_score` | 데이터 기반: 다이아+ 픽률 / 전체 픽률 비율 (E6A3-E9A3 구간, 0-1 정규화). 고랭크일수록 선호 = 실력 천장 높음 |
| `agent_team_synergy` | 팀 협력 필요도 0~1. 높을수록 랭크 저픽이 구조적 |
| `agent_replaceability` | 대체 가능성 0~1 |
| `agent_complexity` | 요원 운용 복잡도 0~1 |
| `pro_dominant_flag` | VCT 편향 요원 플래그 |
| `n_rank_acts` | 유효 랭크 데이터 액트 수. 신규 요원 신뢰도 보정 |

### 7. 킷(스킬 구성) 피처

| 피처 | 설명 |
|------|------|
| `kit_x_rank_pr` | kit_score × (rank_pr / 5). 킷 등급 높은 요원이 고픽일수록 너프 압박 |
| `kit_pr_gap` | kit_score - (rank_pr / 5). 킷 이론값 대비 실제 픽률 괴리 |
| `kit_score` | 스킬 등급 가중 평균 (S=4/A=3/B=2/C=1) |
| `tier_gap` | kit_score(이론치) - agent_tier_score(실전치) |
| `last_max_skill_w` | 마지막 패치에서 손댄 스킬 중 최고 등급 |
| `has_smoke`, `has_cc`, `has_info`, `has_mobility`, `has_heal`, `has_revive`, `has_flash`, `has_blind` | 스킬 보유 여부 (0/1) |
| `high_value_smoke`, `high_value_cc` | S급 연막/CC 보유 여부 |
| `mobility_rank_dom` | has_mobility × (rank_pr / 5). 이동기 요원의 랭크 고픽 교차 |
| `geo_synergy` | 맵 지오메트리 시너지 |

### 8. 역할군·유틸 상대 픽률 피처

> 같은 역할군/유틸 타입 내에서 이 요원이 얼마나 선택받는지 포착.

| 피처 | 설명 |
|------|------|
| `role_rank_pr_ratio` | 동일 역할군 내 랭크 픽률 상대 비율 |
| `util_smoke_rank_pr_ratio` | 연막 보유 요원 내 랭크 픽률 상대 비율 |
| `util_cc_rank_pr_ratio` | CC 보유 요원 내 랭크 픽률 상대 비율 |
| `util_info_rank_pr_ratio` | 정보 스킬 보유 요원 내 랭크 픽률 상대 비율 |
| `util_mobility_rank_pr_ratio` | 이동기 보유 요원 내 랭크 픽률 상대 비율 |
| `util_heal_rank_pr_ratio` | 힐 보유 요원 내 랭크 픽률 상대 비율 |
| `util_revive_rank_pr_ratio` | 부활 보유 요원 내 랭크 픽률 상대 비율 |
| `util_flash_rank_pr_ratio` | 플래시 보유 요원 내 랭크 픽률 상대 비율 |
| `util_blind_rank_pr_ratio` | 근시(blind) 보유 요원 내 랭크 픽률 상대 비율 |

### 9. 맵 관련 피처

| 피처 | 설명 |
|------|------|
| `map_hhi` | 맵 편중도 (허핀달 지수 0~1). 0에 가까울수록 맵 가리지 않고 고르게 등장. **레이블 조건(VCT pro_dom)에도 사용** |
| `map_explains_vct_drop` | 맵풀 변경이 VCT 픽률 하락을 설명하는 정도 |
| `top_map_in_rotation` | 주력 맵이 현재 대회 맵풀에 포함 여부 |
| `map_versatility` | 해당 액트에서 플레이된 맵 수 |

### 10. 기타 복합 피처

| 피처 | 설명 |
|------|------|
| `both_weak_signal` | 랭크·VCT 둘 다 낮은 플래그 |
| `agent_team_synergy` | 팀 협력 필요도 |
| `skill_ceiling_x_vct_pr` | skill_ceiling_score × vct_pr_last 교차 |
| `pr_vs_baseline` | 역할군 기대 픽률 대비 현재 픽률 편차 |
| `overshoot_flag` | 직전 패치가 과도했던 경우 플래그 |
| `correction_risk_flag` | 수정 패치 가능성 플래그 |

---

## 제거된 피처 (DROP_COLS)

| 피처 | 제거 이유 |
|------|-----------|
| `buff_hit_flag`, `nerf_hit_flag` | SHAP 0. hit(효과 확인)은 패치 예측에 무의미 |
| `map_specialist`, `specialist_low_pr` | SHAP 0 |
| `geo_bonus` | SHAP 0, 분산 없음 |
| `rank_dominant_flag` | `design_rank_only` 복사본, 둘 다 SHAP 0 |
| `low_kit_weak_signal` | 변동성 없음 |
| `op_synergy` | 해당 요원 너무 적음 |
| `replaceable_low_pr`, `versatile_high_pr` | 요원별 거의 상수 |
| `versatile_nerf_signal` | `(1-map_hhi) × rank_pr` — XGBoost가 원본 피처로 자동 포착, 중복 |
| `design_rank_only`, `design_pro_only` | "이 요원은 랭크 전용"으로 고정 분류 → 메타 변화 대응 불가 |
| `heal_low_rank`, `revive_low_rank` 등 | 이진 임계값 교차 → 요원별 상수화 |
| `rank_vct_gap` | NaN 30%+ |
| `map_dep_score`, `effective_map_dep` | 이중 인코딩 |
| `last_combined` | DUAL_MISS 플래그만으로 방향 판단 불가 |
| `rank_pr_rel_meta`, `rank_pr_zscore` | Stage B 성능 저하 확인 |
| `horizon` | 레이블 생성용 메타 컬럼, 피처 아님 |

---

## 도메인 규칙 레이어

**현재 유일한 규칙**: acts_since_patch = 0 (이번 액트에 방금 패치됨) → p_patch × 0.15

나머지 규칙 전부 제거. SHAP=0이었던 규칙들은 모델이 해당 신호를 피처에서 이미 직접 학습하므로 불필요.

---

## 학습 전략

### Walk-forward Temporal Split
- 시계열 누출 방지: KFold shuffle 사용 안 함
- OOF 예측을 시간 순서대로 생성

### horizon 분리
- Stage A: horizon=1만 (596행) — 단기 판정, 레이블 일관성 유지
- Stage B: horizon=1,2,3 전부 (655행) — 방향 데이터 최대화. 같은 피처에 horizon만 다른 행이 생기므로 Stage A에는 혼합 금지

### 데이터 품질 가중치 (sparse agent discount)
- 조건: `acts_since_patch >= 99` AND `n_rank_acts < 8`
- 가중치: `clip(n_rank_acts / 8.0, 0.2, 1.0)`

### stable_strong / stable_weak 제거
- Stage A 학습에서 제외: 명백한 극단 케이스는 경계 케이스 학습에 노이즈

### LR 파이프라인 (비교군)
```python
SkPipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler()),
    ("lr", LogisticRegression(...)),
])
```

---

## 검증 결과 요약 (2026-04-08)

| 검증 방식 | Stage A | Stage B |
|-----------|---------|---------|
| Temporal OOF balanced accuracy | **0.8577** | **0.5468** |
| Leave-One-Agent-Out 평균 BA | **0.836** | **0.436** |

### Stage A LOAO 요원별 (하위)
Jett 0.500 / Miks 0.500 / Reyna 0.500 / Deadlock 0.550 / Sage 0.609

### Stage B LOAO 요원별 (하위)
Iso 0.175 / Yoru 0.200 / Fade 0.250 / Veto 0.250 / Brimstone 0.298

Stage B 한계: 요원별 고유 패치 패턴이 강해 일반화 어려움. 데이터 누적 시 자연 개선.

---

## 피처 설계 원칙

1. **정적 플래그 단독 사용 금지**: `has_smoke=1`은 SHAP=0. 반드시 픽률·승률 흐름과 교차
2. **요원 정체성 인코딩 지양**: 요원 ID 대신 역할 특성으로 일반화
3. **시계열 누출 방지**: Walk-forward temporal split
4. **도메인 룰은 데이터 밖 예외만**: SHAP=0 룰은 모델이 이미 학습 → 제거
5. **레이블 조건과 피처 분리**: map_hhi는 레이블 조건(VCT pro_dom 판단)과 모델 피처 둘 다 사용 가능. 단 레이블에는 맵 비종속 요원만 적용해 맵 로테 노이즈 차단
6. **멀티 호라이즌 분리**: Stage A/B 용도가 다르므로 horizon 혼합 금지
