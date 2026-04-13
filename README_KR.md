# Valorant Patch Verdict

> **다음에 누가 패치 먹을지 예측하고, 가상 패치가 메타를 어떻게 바꿀지 시뮬레이션하는 모델이다.**

발로란트 랭크(다이아+) 픽률/승률, VCT 프로 대회 데이터, 패치 이력, 요원 킷 설계를 종합해서 29개 전 요원의 너프/버프/안정 확률을 뽑아내는 ML 시스템이다.

---

## 어떻게 동작하나

2단계로 나눠서 판단한다.

```
입력: 요원 + 액트별 피처 (랭크 통계, VCT 통계, 패치 이력, 킷 특성)
                    |
           [Stage A: XGBoost]  (50개 피처)
           이번 액트에 패치 받을까?
                /         \
            안정          패치 대상
                            |
                   [Stage B: XGBoost]  (51개 피처)
                   너프야 버프야?
                    /         \
                 버프          너프
                    |           |
              경미 / 강한    경미 / 강한
```

**Stage A**가 먼저 "이 요원한테 패치 압박이 있는가"를 판별하고, 패치 대상으로 분류되면 **Stage B**가 방향(너프/버프)을 잡는다. 각 스테이지는 서로 다른 피처셋을 쓴다. 강도(경미/강한)는 이전 패치가 효과 있었는지, 핵심 스킬(E/X)을 건드리는지 등으로 결정된다.

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

## 데이터

| 출처 | 뭘 가져오나 | 기간 |
|---|---|---|
| vstats.gg | 액트별 픽률, 승률, 매치 수 (다이아+, 전 리전) | E6A3~ |
| maxmunzy/valorant-agent-stats | 다이아+ 픽률, 승률, KD | E2A1~E9A3 |
| vlr.gg | VCT 대회 픽률, 승률 | E6A3~ |
| playvalorant.com | 공식 패치노트 | E2A1~ |

- **티어**: 다이아+ 기준. 하위 랭크는 "좋아하는 요원 고르기"라서 패치 신호로는 노이즈가 너무 크다.
- **리전**: 전 리전 통합. 발로란트는 글로벌 단일 패치고, 요원 수가 29개뿐이라 리전 간 차이가 유의미하지 않다.
- **병합**: vstats.gg를 기본으로 쓰되, E2A1~E6A2 빈 구간은 maxmunzy 데이터로 채운다.

---

## 핵심 설계

### 2D 사분면 피처

라이엇의 패치는 픽률과 승률을 **같이** 본다. 픽률만 높다고, 승률만 높다고 너프하지 않는다. 이걸 반영해서 피처를 2D 평면(픽률 × 승률) 위에서 설계했다.

```
                  승률이 요원 평균 이상
                        |
    Q2 니치 OP          |         Q1 너프 대상
    (안 쓰는데 이김)     |   (많이 쓰고 이김)
                         |
   ──────────────────────┼──────────── 픽률이 베이스라인 이상
                         |
    Q3 버프 대상          |         Q4 팬덤
    (안 쓰고 지고)        |   (많이 쓰는데 짐)
                         |
                  승률이 요원 평균 이하
```

중심점은 절대 기준(50%, 10%)이 아니라 **요원 자기 자신의 역대 평균**이다. 제트의 "정상" 픽률은 14%고 하버는 0.4%니까, 같은 잣대로 재면 안 된다.

### VCT 절대 지배 감지

VCT 픽률 35%를 넘는 요원은 역대 평균이 어떻든 너프 신호를 건다. 바이퍼나 오멘처럼 원래부터 VCT에서 항상 높은 요원은 상대 비교로는 절대 못 잡는다 — "원래 이 정도인데?"로 넘어가기 때문이다. 절대 기준이 이 맹점을 커버한다.

### 신호 캐리오버

이전 액트에서 너프/버프 신호가 잡혔는데 아직 패치를 안 받았으면, 수치가 정상화되지 않는 한 다음 액트에도 그 신호를 유지한다. 패치 압박이 계속되는 요원이 매 액트마다 stable/nerf를 왔다 갔다 하는 걸 막기 위해서다.

### 레이블 체계

| 레이블 | 의미 |
|---|---|
| `stable` | 수치가 베이스라인 근처. 패치 압박 없음 |
| `mild_nerf` | 너프 신호 있음 (랭크 초과 or VCT 지배) |
| `strong_nerf` | 실제 너프 패치: 후속 조정이거나 핵심 스킬(E/X) 너프 |
| `mild_buff` | 버프 신호 있음 (베이스라인 미달 + 승률도 낮음) |
| `strong_buff` | 실제 버프 패치: 후속 조정, 핵심 스킬 버프, 리워크 |

strong은 실제 패치가 나온 행에서만 붙는다. 패치 안 나온 액트는 아무리 수치가 나빠도 최대 mild까지만.

### Stage A/B 피처 분리

두 스테이지가 풀어야 하는 문제가 다르니까, 피처셋도 따로 최적화한다.

- Stage A 전용: `map_hhi`(맵 편중도), `kit_score`, `recent_dual_miss_count`, `vct_pr_avg`
- Stage B 전용: `vct_data_lag`(VCT 데이터 지연), `geo_synergy`, `n_nerf_patches`, `n_total_patches`, `vct_pr_peak_all`

SHAP 중요도 기준으로 한쪽 스테이지에서만 신호가 없는 피처는 그쪽에서만 뺀다. 예를 들어 `vct_data_lag`은 Stage A에서 SHAP=0인데 Stage B에서는 최상위권이라, A에서만 빼고 B에서는 살려둔다.

---

## 주요 SHAP 피처

**Stage A (패치 대상 여부) — 상위 10:**

| # | 피처 | SHAP | 의미 |
|---|---|---|---|
| 1 | rank_pr_excess | 0.163 | 요원 베이스라인 대비 픽률 초과량 |
| 2 | vct_pr_last | 0.155 | 최근 VCT 픽률 |
| 3 | wr_buff_signal | 0.133 | 승률 버프 신호 |
| 4 | strength_vs_direction | 0.123 | 현재 강도 vs 마지막 패치 방향 |
| 5 | tier_gap | 0.122 | 이론 킷 등급 - 실전 등급 차이 |
| 6 | rank_pr_slope | 0.119 | 픽률 추세 기울기 |
| 7 | last_pr_pre | 0.103 | 마지막 패치 직전 픽률 |
| 8 | rank_wr | 0.098 | 현재 랭크 승률 |
| 9 | kit_x_rank_pr | 0.089 | 킷 등급 × 픽률 교차 |
| 10 | kit_score | 0.080 | 스킬 등급 가중 평균 |

**Stage B (너프/버프 방향) — 상위 10:**

| # | 피처 | SHAP | 의미 |
|---|---|---|---|
| 1 | rank_pr_avg3 | 0.383 | 최근 3액트 평균 픽률 |
| 2 | pr_pct_of_peak | 0.346 | 전성기 대비 현재 위치 |
| 3 | skill_ceiling_x_vct_pr | 0.342 | 실력 천장 × VCT 픽률 |
| 4 | vct_pr_last | 0.291 | 최근 VCT 픽률 |
| 5 | last_pr_pre | 0.280 | 마지막 패치 직전 픽률 |
| 6 | vct_wr_last | 0.280 | 최근 VCT 승률 |
| 7 | rank_pr | 0.277 | 현재 랭크 픽률 |
| 8 | acts_since_patch | 0.251 | 마지막 패치 후 경과 액트 수 |
| 9 | vct_rel_pos | 0.236 | VCT 상대 포지션 |
| 10 | rank_pr_vs_peak | 0.212 | 현재 / 역대 최고 비율 |

---

## 학습 파이프라인

- **Stage A**: Walk-forward 시계열 CV. stable이 다수이므로 train fold에서만 1:1 언더샘플링해서 균형을 맞추고, val은 원본 분포로 평가한다.
- **Stage B**: 마찬가지로 Walk-forward CV. buff가 소수이므로 SMOTE로 오버샘플링한다.
- **HPO**: Optuna TPE Sampler, 스테이지당 60 trials.
- **피처 선택**: SHAP 중요도 분석 후 양쪽에서 다 약한 피처는 공통 드롭, 한쪽에서만 약한 피처는 해당 스테이지에서만 드롭.
- **도메인 규칙**: 없다. 모델 출력을 후보정 없이 그대로 쓴다.

---

## 프로젝트 구조

```
valorant_patch_verdict/
  build_step2_data.py      # 학습 데이터 빌더
  label_builder.py         # 5-class 레이블링 로직
  feature_builder.py       # 피처 엔지니어링 (2D 사분면, 시그널)
  train_step2.py           # 모델 학습 (HPO, CV, SHAP)
  predict_service.py       # 예측 API 래퍼
  predict_report.py        # CLI 예측 리포트
  main.py                  # FastAPI 서버
  crawl_patch_notes.py     # 패치노트 크롤러
  agent_data.py            # 요원 설계 데이터, 스킬 가중치
  data/                    # 원본 데이터 (랭크, VCT, 패치노트)
  frontend/                # Next.js + Tailwind CSS 프론트엔드
  step2_training_data.csv  # 빌드된 학습 데이터
  step2_pipeline.pkl       # 학습된 모델
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
- `agent_skills.json`: 29요원 851개 스탯 (스킬별 초기값)
- `patch_history.json`: E2A1 이후 전체 스탯 변경 이력 + 현재값

### Phase 2 — 패치 임팩트 모델 (다음)
- 패치 내용(어떤 스킬, 어떤 변경, 얼마나)을 넣으면 픽률/승률이 얼마나 바뀔지 예측하는 회귀 모델
- 136건의 실제 패치 케이스로 학습

### Phase 3 — 패치 시뮬레이터
- "제트 E 쿨타임 12초 → 8초"처럼 가상 패치를 입력하면
- 임팩트 모델로 픽률/승률 변화를 예측하고
- 변화된 메타로 패치 압박 모델을 다시 돌려서
- 새 너프/버프 순위 + AI 해석을 출력

### Phase 4 — 모델 고도화
- 요원 현재 스킬 스탯을 절대 강도 피처로 활용
- 유사 과거 패치 사례 검색
- 데이터 확장으로 strong 클래스 재현율 개선

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
