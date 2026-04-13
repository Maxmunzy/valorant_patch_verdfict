# Valorant Patch Verdict

## 개요

> **다음 패치 대상 요원을 예측하고, 패치가 메타에 미치는 영향을 시뮬레이션합니다.**

랭크 픽률/승률, VCT 대회 데이터, 패치 이력, 요원 설계 특성을 활용하여 발로란트 요원의 패치 압박을 예측하는 머신러닝 시스템입니다.

현재 메타 데이터를 입력하면, 29개 전 요원에 대해 너프/버프/안정 확률을 출력합니다.

---

## 작동 원리

### 2단계 계층 분류

```
입력: 요원 + 액트 피처 (랭크 통계, VCT 통계, 패치 이력, 설계 특성)
                    |
           [Stage A: XGBoost]  (50개 피처)
           안정 vs 패치 대상?
                /         \
            안정          패치 대상
                            |
                   [Stage B: XGBoost]  (51개 피처)
                   버프 vs 너프?
                    /         \
                 버프          너프
                    |           |
              경미 / 강한    경미 / 강한
```

**Stage A**는 해당 요원에게 패치 압박이 있는지 판별합니다.
**Stage B**는 패치 방향(버프 또는 너프)을 결정합니다.
각 스테이지는 독립적으로 최적화된 피처셋을 사용합니다.
강도(경미/강한)는 패치 맥락(후속 조정 여부)과 스킬 중요도(E/X)로 결정됩니다.

### 현재 성능 (2026-04-13)

| 지표 | 값 |
|---|---|
| Stage A balanced accuracy | 0.6614 |
| Stage B balanced accuracy | 0.7779 |
| 학습 데이터 | 659행 / 29 요원 / E2A1 ~ V26A2 |
| Stage A 피처 수 | 50 |
| Stage B 피처 수 | 51 |

---

## 최신 예측 (V26A2)

### 너프 순위

| # | 요원 | p_nerf | 랭크 픽률 | VCT 픽률 |
|---|---|---|---|---|
| 1 | Neon | 76.1% | 22.2% | 77.2% |
| 2 | Waylay | 75.0% | 37.0% | 44.2% |
| 3 | Omen | 67.3% | 16.9% | 46.5% |
| 4 | Viper | 64.1% | 6.4% | 50.4% |
| 5 | Sova | 53.2% | 32.4% | 24.4% |

### 버프 순위

| # | 요원 | p_buff | 랭크 픽률 | VCT 픽률 |
|---|---|---|---|---|
| 1 | KAYO | 78.6% | 4.6% | 7.0% |
| 2 | Gekko | 66.8% | 4.9% | 1.2% |
| 3 | Miks | 64.0% | 5.3% | 1.7% |
| 4 | Yoru | 63.6% | 3.1% | 1.8% |
| 5 | Vyse | 54.6% | 5.1% | 7.0% |

---

## 데이터 출처

| 출처 | 데이터 | 기간 |
|---|---|---|
| vstats.gg | 액트별 픽률, 승률, 매치 수 (다이아+, 전 리전) | E6A3~ |
| maxmunzy/valorant-agent-stats | 다이아+ 픽률, 승률, KD | E2A1~E9A3 |
| vlr.gg | VCT 대회 픽률, 승률 | E6A3~ |
| playvalorant.com | 공식 패치노트 | E2A1~ |

- **티어**: 다이아몬드+ (하위 랭크는 선호도 기반이라 노이즈가 큼)
- **리전**: 전 리전 통합 (발로란트는 글로벌 패치, 요원 풀이 작아 리전 간 차이 제한적)
- **데이터 병합**: vstats.gg 우선, maxmunzy가 E2A1~E6A2 구간 보완

---

## 모델 아키텍처

### 피처 엔지니어링: 2D 사분면 시스템

핵심 인사이트: 라이엇의 패치 결정은 **2D 평면 (픽률 × 승률)** 위에서 이루어지며, 1D 지표를 독립적으로 보면 핵심 신호를 놓칩니다.

**랭크 2D 사분면** (요원 자신의 역대 평균을 중심으로):
```
                  승률이 요원 평균 이상
                        |
    Q2 니치 OP          |         Q1 너프 대상
    (저픽률, 고승률)     |   (고픽률, 고승률)
                         |
   ──────────────────────┼──────────────── 픽률이 베이스라인 이상
                         |
    Q3 버프 대상          |         Q4 팬덤
    (저픽률, 저승률)      |   (고픽률, 저승률)
                         |
                  승률이 요원 평균 이하
```

**VCT 피처**:
- `vct_must_nerf`: 절대 지배 임계값 (VCT 픽률 > 35%)
- `pro_only_nerf`: VCT 지배 + 랭크 비인기 (Viper/Omen 타입)

**스테이지별 전용 피처**:
- Stage A 전용: `map_hhi`, `kit_score`, `recent_dual_miss_count`, `vct_pr_avg`
- Stage B 전용: `vct_data_lag`, `geo_synergy`, `n_nerf_patches`, `n_total_patches`, `vct_pr_peak_all`

### 레이블링 시스템

5-class 레이블에 두 가지 핵심 혁신을 적용:

**1. VCT 절대 임계값**
VCT 픽률 35% 이상인 요원은 역대 평균과 무관하게 `mild_nerf` 레이블을 부여합니다.
항상 VCT에서 높은 Viper 같은 요원은 상대 지표로 감지할 수 없기 때문입니다.

**2. 신호 캐리오버**
액트 N에서 `mild_nerf` 레이블이었던 요원은, 지표가 정상화되지 않는 한 액트 N+1에서도 레이블이 유지됩니다.
지속적인 패치 압박 하의 요원이 stable/nerf 사이를 왔다 갔다 하는 것을 방지합니다.

| 레이블 | 설명 |
|---|---|
| `stable` | 지표가 베이스라인 근처, 패치 압박 없음 |
| `mild_nerf` | 너프 신호 존재 (랭크 초과 또는 VCT 지배) |
| `strong_nerf` | 실제 패치: 후속 조정/수정 또는 핵심 스킬(E/X) 너프 |
| `mild_buff` | 버프 신호 존재 (베이스라인 미달 + 패배 중) |
| `strong_buff` | 실제 패치: 후속 조정/수정, 핵심 스킬 버프 또는 리워크 |

### 학습 파이프라인

- **Stage A**: Walk-forward 시계열 CV, train-only 1:1 언더샘플링 (stable 다수 클래스를 patched 수에 맞춤)
- **Stage B**: Walk-forward 시계열 CV, SMOTE 오버샘플링 (buff 소수 클래스)
- **HPO**: Optuna TPE Sampler (스테이지당 60 trials)
- **피처 선택**: Stage A/B 각각 SHAP 중요도 기반 독립 피처셋 최적화
- **도메인 규칙 없음**: 모델 출력을 후처리 보정 없이 그대로 사용

### 주요 SHAP 피처

**Stage A (안정 vs 패치 대상) — 50개 피처:**

| 순위 | 피처 | SHAP | 설명 |
|---|---|---|---|
| 1 | rank_pr_excess | 0.163 | 요원 베이스라인 대비 픽률 초과 |
| 2 | vct_pr_last | 0.155 | 최근 VCT 픽률 |
| 3 | wr_buff_signal | 0.133 | 승률 버프 신호 |
| 4 | strength_vs_direction | 0.123 | 현재 강도 vs 마지막 패치 방향 |
| 5 | tier_gap | 0.122 | kit_score - agent_tier_score |
| 6 | rank_pr_slope | 0.119 | 픽률 추세 기울기 |
| 7 | last_pr_pre | 0.103 | 마지막 패치 직전 픽률 |
| 8 | rank_wr | 0.098 | 현재 랭크 승률 |
| 9 | kit_x_rank_pr | 0.089 | 킷 등급 × 픽률 교차 |
| 10 | kit_score | 0.080 | 스킬 등급 가중 평균 |

**Stage B (버프 vs 너프) — 51개 피처:**

| 순위 | 피처 | SHAP | 설명 |
|---|---|---|---|
| 1 | rank_pr_avg3 | 0.383 | 최근 3액트 평균 픽률 |
| 2 | pr_pct_of_peak | 0.346 | 역대 피크 대비 현재 위치 |
| 3 | skill_ceiling_x_vct_pr | 0.342 | 실력 천장 × VCT 픽률 교차 |
| 4 | vct_pr_last | 0.291 | 최근 VCT 픽률 |
| 5 | last_pr_pre | 0.280 | 마지막 패치 직전 픽률 |
| 6 | vct_wr_last | 0.280 | 최근 VCT 승률 |
| 7 | rank_pr | 0.277 | 현재 랭크 픽률 |
| 8 | acts_since_patch | 0.251 | 마지막 패치 이후 경과 액트 수 |
| 9 | vct_rel_pos | 0.236 | VCT 상대 포지션 |
| 10 | rank_pr_vs_peak | 0.212 | 현재 / 역대 최고 비율 |

---

## 프로젝트 구조

```
valorant_patch_verdict/
  build_step2_data.py      # 학습 데이터 빌더
  label_builder.py         # 5-class 레이블링 로직
  feature_builder.py       # 피처 엔지니어링 (2D 사분면, 시그널)
  train_step2.py           # 모델 학습 파이프라인 (HPO, CV, SHAP)
  predict_service.py       # 예측 API 래퍼
  predict_report.py        # CLI 예측 리포트
  main.py                  # FastAPI 서버
  crawl_patch_notes.py     # 패치노트 크롤러
  agent_data.py            # 요원 설계 데이터, 스킬 가중치
  data/                    # 원본 데이터 (랭크 통계, VCT, 패치노트)
  frontend/                # Next.js + Tailwind CSS 프론트엔드
  step2_training_data.csv  # 빌드된 학습 데이터
  step2_pipeline.pkl       # 학습된 모델 아티팩트
```

---

## 실행

```bash
# 학습 데이터 빌드
python build_step2_data.py

# 모델 학습 (전체 HPO)
python train_step2.py

# 빠른 모드 (저장된 하이퍼파라미터 재사용)
python train_step2.py --fast

# HPO 강제 재실행
python train_step2.py --hpo

# 패치노트 크롤링 + patch_dates.json 갱신
python crawl_patch_notes.py

# 서버 시작
python main.py
```

---

## 로드맵

### Phase 1 — 스킬 스탯 DB (완료)
- `agent_skills.json`: 29 요원, 851개 스탯 (스킬별 초기값)
- `patch_history.json`: E2A1 이후 모든 스탯 변경 이력, 현재값 계산

### Phase 2 — 패치 임팩트 모델 (다음)
- 회귀 모델: 패치(스킬, 변경 유형, 크기)가 주어지면 픽률/승률 변화량 예측
- 136건의 실제 패치 케이스로 학습
- 입력: `[스킬_가중치, 변경_유형, 크기, 패치전_랭크_픽률, 패치전_랭크_승률, VCT_픽률]`
- 출력: `[랭크_픽률_변화, 랭크_승률_변화]`

### Phase 3 — 패치 시뮬레이터
- 사용자가 가상 패치 입력 (예: "제트 E 쿨타임 12초 → 8초")
- 시스템이 입력을 파싱하고 크기를 계산한 뒤 임팩트 모델 실행
- 예측된 변화량을 현재 메타에 적용하고 패치 압박 모델 재실행
- 출력: 새 너프/버프 순위 + AI 해석

### Phase 4 — 모델 고도화
- 요원 현재 스킬 스탯을 절대 강도 피처로 활용
- 유사 과거 패치 사례 검색
- 데이터셋 확장으로 strong 클래스 재현율 개선

---

## 기술 스택

| 구성 요소 | 기술 |
|---|---|
| 데이터 수집 | Python (Playwright, BeautifulSoup) |
| 패치노트 파싱 | Claude API |
| 데이터 처리 | pandas, numpy |
| ML | XGBoost, scikit-learn |
| HPO | Optuna (TPE Sampler) |
| 피처 중요도 | SHAP |
| AI 분석 | Claude Haiku (claude-haiku-4-5-20251001) |
| 프론트엔드 | Next.js, Tailwind CSS |
| API | FastAPI |
