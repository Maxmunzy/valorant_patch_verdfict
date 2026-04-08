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
| vstats.gg | 액트별 픽률·승률·매치 수 (다이아+, 전 지역 합산) | E6A3~ |
| maxmunzy/valorant-agent-stats | 다이아+ 픽률·승률·KD | E2A1~E9A3 |
| vlr.gg | VCT 대회별 픽률·승률 | E6A3~ |
| playvalorant.com | 공식 패치 노트 | E2A1~ |

- **티어 기준**: 다이아몬드+ (그 이하는 메타 이해도보다 선호도 픽이 많아 노이즈 큼). vstats.gg와 maxmunzy 둘 다 동일 기준
- **서버**: 전 지역 합산 (발로란트는 전 서버 동시 패치, 요원 풀이 작아 지역 편차 제한적)
- **데이터 병합**: vstats.gg 우선, 빈 구간(E2A1~E6A2)은 maxmunzy 보완

---

## 모델 구조

### Stage A — 패치 여부 예측 (이진 분류)

> "이 요원이 이번 액트에 패치를 받을까?"

- **입력**: 피처 (랭크/VCT 픽률·승률 추세, 패치 이력, 요원 설계 특성, 역할군·유틸 상대 픽률, 맵 다양성)
- **출력**: `stable` / `patched` 확률
- **임계값**: 0.28
- **학습 데이터**: horizon=1 행만 (단기 판정 일관성 유지)

### Stage B — 패치 유형 분류 (5분류)

> "어떤 종류의 패치인가?"

- **입력**: Stage B 전용 피처 (patched 케이스만, 타이밍 노이즈 피처 제거)
- **출력**: 아래 5개 클래스
- **학습 데이터**: horizon=1,2,3 전부 (방향 데이터 최대화)

| 클래스 | 설명 |
|---|---|
| `nerf_rank` | 랭크/VCT 지표 기반 너프 |
| `nerf_followup` | 이전 너프 효과 미달, 추가 너프 |
| `buff_rank` | 랭크/VCT 지표 기반 버프 |
| `buff_followup` | 이전 버프 효과 미달, 추가 버프 |
| `rework` | 수치 조정으로 해결 불가, 구조 변경 |

---

## 레이블 생성 전략 (`classify_stable_state`)

> 매 액트마다 현재 수치만으로 독립 판정. acts_since/last_direction 같은 이력 조건 없음.
> 액트 = 약 2개월 단위이므로 매 액트 독립 재판정이 적합.

### nerf_followup 조건 (OR)

| 신호 | 조건 | 설명 |
|---|---|---|
| 랭크 지배 | `rank_pr_pct >= 20% AND rank_wr_vs50 >= 0%` | 픽률 높고 승률 평균 이상 |
| 승률 극단 | `rank_wr_vs50 >= 2.5%` | 픽률 무관 비정상 고승률 |
| VCT 지배 + 맵 비종속 | `vct_pr >= 40% AND map_hhi <= 0.15 AND rank_wr_vs50 >= -1%` | pro_dom 패턴 포착 (체임버·스카이·바이퍼형) |

`map_hhi <= 0.15` 조건: 맵 로테이션과 무관하게 모든 맵에서 고르게 나오는 요원만 적용.
맵 특화 요원(바이퍼 현재 map_hhi=0.46)은 VCT 픽률이 높아도 맵 로테 효과로 처리.

### buff_followup 조건 (OR)

| 신호 | 조건 | 설명 |
|---|---|---|
| 랭크 부진 | `rank_pr_pct <= 12% AND rank_wr_vs50 <= -1.5%` | 픽률·승률 동시 낮음 |
| 승률 극단 | `rank_wr_vs50 <= -4%` | 픽률 무관 비정상 저승률 |
| 존재감 없음 | `rank_pr_pct <= 5%` | 사실상 픽 없음 |

### 버그픽스 패치 처리

nerf/buff 없는 패치(버그픽스, 수치 오기정 등)는 `stable` 고정이 아닌 **수치 기반 재판정**.
패치 전후 수치가 같으면 레이블도 같아 모델 학습 노이즈 없음.

---

## 멀티 호라이즌 (Stage B 데이터 확장)

| horizon | 사용 Stage | 설명 |
|---|---|---|
| 1 | A + B | 현재 액트 → 다음 1액트 후 패치 (기본) |
| 2 | B만 | 현재 액트 피처 → 2액트 후 실제 패치 방향 |
| 3 | B만 | 현재 액트 피처 → 3액트 후 실제 패치 방향 |

- Stage A는 horizon=1만 사용 (단기 판정 일관성 유지)
- Stage B는 전체 horizon 활용 → 655행 (이전 403행 대비 +63%)
- 지연 패치 케이스(라이엇이 2~3액트 후에 조정) 학습 가능

---

## 도메인 규칙 레이어

모델 출력 후 최소한의 하드 룰만 적용:

| 규칙 | 조건 | 효과 |
|---|---|---|
| acts_since=0 억제 | 이번 액트에 방금 패치됨 | p_patch × 0.15 |

이전에 있던 신규 요원 억제, 저픽 연속 억제, 스킬 천장 보정, VCT 승률 보정 등 모두 제거.
SHAP=0 규칙은 모델이 해당 신호를 피처에서 이미 학습하므로 불필요.

---

## 검증 결과 (2026-04-08 기준)

| 검증 방식 | Stage A | Stage B |
|---|---|---|
| Temporal OOF balanced accuracy | **0.8577** | **0.5468** |
| Leave-One-Agent-Out 평균 BA | **0.836** | **0.436** |

- Stage A 학습: 596행 (horizon=1) / Stage B 학습: 655행 (horizon=1,2,3)
- 전체 데이터: 939행 / 29요원 / E2A1 ~ V26A2
- stable:patched 비율 55:45 (이전 73:27 대비 균형 개선)

### BA 분해 (Stage A)
| 그룹 | 행 수 | BA |
|---|---|---|
| 수치기반 레이블 (classify_stable_state) | 470 | 0.905 |
| 실제 라이엇 패치 | 149 | **0.852** |

---

## 현재 예측 결과 (V26A2 기준, 주요 케이스)

| 요원 | 예측 | 근거 |
|---|---|---|
| 네온 | nerf_followup | VCT 77%, map_hhi 0.006 (맵 비종속 pro_dom) |
| 소바 | nerf_followup | 랭크 픽률 32.4%, 승률 +0.45% |
| 스카이 | nerf_followup | VCT 39.5%, map_hhi 0.053 (최근 버프 후 상승 중) |
| 페이드 | nerf_followup | 랭크 픽률 25.6%, VCT 29.8% |
| 요루 | buff_followup | 랭크 픽률 3.3% |

---

## 실행 방법

```bash
# 데이터 빌드 (horizon=1,2,3 포함)
python build_step2_data.py

# 모델 학습 (full HPO)
python train_step2.py

# 피처 실험 (저장된 파라미터 재사용, 빠름)
python train_step2.py --fast

# HPO 강제 재실행 + 파라미터 갱신
python train_step2.py --hpo
```

---

## 기술 스택

| 구분 | 사용 기술 |
|---|---|
| 데이터 수집 | Python (Playwright, BeautifulSoup) |
| 패치 노트 정형화 | Claude API |
| 데이터 전처리 | pandas, numpy |
| 머신러닝 | XGBoost, scikit-learn (LogisticRegression, SimpleImputer) |
| HPO | Optuna (TPE Sampler) |
| 피처 중요도 | SHAP |
| AI 분석 텍스트 | Claude Haiku (claude-haiku-4-5-20251001) |
| 프론트엔드 | Next.js, Tailwind CSS |

---

*Started from a random idea on the subway*
