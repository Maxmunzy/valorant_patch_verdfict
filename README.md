# valorant_patch_verdict

## 프로젝트 개요

> **발로란트 패치 예측 시스템**
> "다음에 너프/버프받을 요원이 누구인지 데이터로 예측한다."

랭크 픽률·승률, VCT 픽률·승률, 패치 이력, 요원 설계 특성을 조합해
**현재 액트 기준으로 각 요원의 패치 가능성과 방향을 예측**하는 2단계 XGBoost 모델.

---

## 아이디어 배경

발로란트에서 너프/버프가 날 때마다 커뮤니티는 "이거 맞냐 틀리냐"로 감정적 논쟁이 벌어진다.
기존 tracker.gg, blitz.gg, vlr.gg는 현재 픽률·승률만 보여줄 뿐, **패치 전후 비교**나 **다음 패치 예측**은 해주지 않는다.

이 프로젝트는 그 공백을 채운다. 감정이 아닌 **데이터**로 판단한다.

---

## 데이터 소스

| 출처 | 데이터 종류 | 구간 |
|---|---|---|
| vstats.gg | 액트별 픽률·승률·매치 수 (전 지역 합산) | E6A3~ |
| maxmunzy/valorant-agent-stats | 다이아+ 픽률·승률·KD (티어별) | E2A1~E8A2 |
| vlr.gg | VCT 대회별 픽률·승률 | E6A3~ |
| playvalorant.com | 공식 패치 노트 | E2A1~ |

- **티어 기준**: 다이아몬드+ (그 이하는 메타 이해도보다 선호도 픽이 많아 노이즈 큼)
- **서버**: 전 지역 합산 (발로란트는 전 서버 동시 패치, 요원 풀이 작아 지역 편차 제한적)

---

## 모델 구조

### Stage A — 패치 여부 예측 (이진 분류)

> "이 요원이 이번 액트에 패치를 받을까?"

- **입력**: 57개 피처 (랭크/VCT 픽률·승률 추세, 패치 이력, 요원 설계 특성, 킷 정보)
- **출력**: `stable` / `patched` 확률
- **임계값**: 0.35 (패치 누락보다 과감지를 허용)

### Stage B — 패치 유형 분류 (9분류)

> "어떤 종류의 패치인가?"

- **입력**: Stage A와 동일한 57개 피처 (patched 케이스만)
- **출력**: 아래 9개 클래스

| 클래스 | 설명 |
|---|---|
| `nerf_rank` | 랭크 지표 기반 너프 |
| `nerf_pro` | VCT 프로씬 지배 기반 너프 |
| `nerf_followup` | 이전 너프 효과 미달, 추가 너프 |
| `buff_rank` | 랭크 지표 기반 버프 |
| `buff_pro` | VCT 저픽 기반 버프 |
| `buff_followup` | 이전 버프 효과 미달, 추가 버프 |
| `correction_nerf` | 과버프 수정 너프 |
| `correction_buff` | 과너프 수정 버프 |
| `rework` | 수치 조정으로 해결 불가, 구조 변경 |

---

## 피처 설계 원칙

1. **시계열 정보 우선**: 단발 수치보다 slope, avg3, vs_peak 등 추세 피처가 더 중요
2. **정적 플래그 단독 사용 금지**: `has_smoke=1` 같은 요원별 상수는 시간 변동이 없어 SHAP=0. `kit_x_rank_pr`처럼 픽률 흐름과 교차해야 신호가 됨
3. **요원 정체성 직접 인코딩 금지**: 요원 ID 대신 역할 특성(team_synergy, replaceability 등)으로 일반화
4. **고정 분류 지양**: "이 요원은 랭크 전용" 같은 고정 분류를 모델 피처로 쓰면 메타 변화에 대응 불가 → DROP. 레이블 생성에만 활용
5. **시계열 누출 방지**: Walk-forward temporal split, KFold shuffle 사용 안 함

---

## 주요 피처 (SHAP 평균 중요도 상위)

| 피처 | 설명 |
|---|---|
| `acts_since_patch` | 마지막 패치 후 경과 액트. 오래될수록 패치 압박 누적 |
| `strength_vs_direction` | 현재 강도 vs 마지막 패치 방향 일치도. 너프했는데 여전히 강하면 추가 너프 신호 |
| `rank_pr_avg3` | 최근 3액트 평균 랭크 픽률. 단발보다 노이즈 적음 |
| `rank_pr_slope` | 랭크 픽률 추세 (기울기) |
| `kit_x_rank_pr` | 킷 등급 × 랭크 픽률. 고가치 킷 요원이 많이 픽될수록 너프 압박 |
| `rank_wr` | 현재 랭크 승률 |
| `vct_pre_n` | 최근 VCT 이벤트 참여 수. 대회 노출도 |
| `map_hhi` | 맵 편중도. 높을수록 특정 맵 전문가 → 픽률 하락이 맵풀 탓일 수 있음 |
| `vct_wr_last` | 최근 VCT 승률. 낮은 픽률이어도 이기는 팀은 이김 (네온 케이스) |
| `pro_rank_ratio` | VCT 픽률 / 랭크 픽률. 프로 편향 요원 판별 |

자세한 피처 설명: [`feature_and_training_strategy.md`](feature_and_training_strategy.md)

---

## 도메인 규칙 레이어

ML 모델 출력 위에 하드 룰로 보정 (`predict_report.py`):

| 규칙 | 조건 | 효과 |
|---|---|---|
| 0 | 이번 액트 이미 패치됨 | 같은 방향 추가 패치 확률 억제 |
| 1 | 버프 후 MISS인데 nerf 예측 | buff 방향으로 재가중 |
| 2 | 너프 후 MISS인데 buff 예측 | nerf 방향으로 재가중 |
| 4 | 양쪽 도메인 모두 저픽 + 버프 방향 | p_patch 상향 |
| 5 | 실력 천장 높음 + VCT 픽률 6%+ | p_nerf × 1.25 |
| 6 | VCT 승률 65%+ + VCT 픽률 5%+ | p_nerf × 2.5 |

---

## 검증 결과 (2026-04-05 기준)

| 검증 방식 | Stage A | Stage B |
|---|---|---|
| Temporal OOF balanced accuracy | 0.4852 | 0.3610 |
| Leave-One-Agent-Out 평균 BA | 0.534 | 0.472 |

- LOAO >= Temporal → 특정 요원 패턴 암기 아닌 일반 패턴 학습 확인 (과적합 없음)
- Stage B 낮은 이유: 118행 / 9클래스. `correction_buff/nerf` 각 1행으로 사실상 학습 불가
- 12.05 VCT 데이터 추가 시 자연스럽게 개선 예정

---

## 현재 예측 결과 (V26A2 기준)

| 요원 | p_patch | 예측 유형 | 최종 예측 |
|---|---|---|---|
| 게코 | 76% | buff_followup | buff_followup |
| 요루 | 67% | correction_nerf | correction_nerf |
| 아이소 | 50% | nerf_rank | nerf_rank |
| 하버 | 48% | rework | rework |

---

## 주요 케이스

### 요루 — 패치 12.05 너프

- **트리거**: role_invasion + pro_dominance
- 관문 지속시간 30초 → 15초, 기습 충전 2개 → 1개
- 너프 후 랭크 픽률 급락 → correction_nerf 예측 (과너프 가능성)

### 네온 — 너프 예상

- VCT 승률 66.7% (VCT 픽률 낮아도 쓰는 팀은 압도적으로 이김)
- 도메인 룰 6 적용 → nerf 확률 상향

### 웨이레이 — 패치 12.06 너프

- **트리거**: role_invasion (감시자·척후대 역할까지 안전하게 수행)
- change_type: mechanic (즉시 사용 → 장착으로 메커니즘 변경)

---

## 너프 트리거 유형

| 유형 | 설명 |
|---|---|
| `rank_stat` | 랭크 픽률·승률 초과 |
| `pro_dominance` | VCT 필수픽화 |
| `role_invasion` | 타 포지션 입지 잠식 |
| `map_anchor` | 특정 맵 고착 |
| `skill_ceiling` | 고숙련 천장 과도 |

---

## 실행 방법

```bash
# 데이터 빌드
python build_step2_data.py

# 모델 학습 (full HPO)
python train_step2.py

# 피처 실험 (저장된 파라미터 재사용, 빠름)
python train_step2.py --fast

# HPO 강제 재실행 + 파라미터 갱신
python train_step2.py --hpo

# 예측 리포트 출력
python predict_report.py
```

---

## 기술 스택

| 구분 | 사용 기술 |
|---|---|
| 데이터 수집 | Python (Playwright, BeautifulSoup) |
| 패치 노트 정형화 | Claude API |
| 데이터 전처리 | pandas, numpy |
| 머신러닝 | XGBoost, scikit-learn (LogisticRegression) |
| HPO | Optuna (TPE Sampler) |
| 피처 중요도 | SHAP |
| 시각화 | matplotlib |

---

*Started from a random idea on the subway*
