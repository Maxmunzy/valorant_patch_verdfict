# Reddit launch kit — WHOSNXT.APP

> 작성일: 2026-04-22 · 기준 백테스트: `V26A1` (20/28 = 71.4%, 전체 3-class 60.5%, n=453)

## 포스팅 순서

1. **r/ValorantCompetitive** 먼저. 데이터/메타 얘기가 환영받는 서브. 톤은 "겸손한 빌더".
2. r/ValorantCompetitive 에서 긍정 반응 / 조용한 반응이면 **r/VALORANT** 로 크로스포스트 (24h 뒤).
3. 대형 패치 발표 직후 24-48시간 창이 타이밍.
4. **절대 하지 말 것:** self-promotion 태그 없이 여러 서브 동시 폭격. 스팸으로 차임.

## 플레어 / 규정 체크리스트

- r/ValorantCompetitive: `Discussion` 또는 `Analysis` 플레어 선택.
- 제목에 **[OC]** (original content) 태그. 스크린샷 재활용 아니라는 시그널.
- 모더레이터가 자기홍보 10% 룰 관리하는 서브라면, 댓글 활동/ dm 대응 충실하게.

---

## 제목 후보 (A/B)

### 후보 A (최강 훅 — 숫자 앞세우기)

> I built an ML model that predicts which Valorant agents get nerfed/buffed next patch — 71% on last patch, 60% overall across 30 acts [OC]

### 후보 B (정직 앞세우기 — 더 겸손)

> I trained an ML model on 30 acts of Valorant patch data to predict next-patch nerfs. Backtest: 71% last act, 60% overall. Breaking down what it got right (and what it still gets wrong) [OC]

### 후보 C (짧고 호기심 유발)

> 30 acts of Valorant patch data vs. an XGBoost model — here's the backtest scorecard [OC]

**추천: A** — r/ValorantCompetitive 에서 숫자+OC 조합이 역사적으로 잘 먹힘. B는 rVALORANT 크로스포스트용.

---

## 본문 (마크다운 · 그대로 붙여넣기)

```
Hey r/ValorantCompetitive —

I'm a solo dev who got tired of guessing which agents would get nerfed next patch, so I built a model to do it for me. Site is live at https://whosnxt.app/en and I wanted to share how it's actually performing before anyone else asked.

### What it does

For every playable agent, it outputs three probabilities:
- **p_nerf** — how likely they get nerfed next patch
- **p_buff** — how likely they get buffed
- **p_stable** — how likely they stay untouched

Features are pulled from Diamond+ ranked pick/win rates, VCT pick rates, VCT trend (this event vs. last), days since last touched, and a hand-coded patch history going back to Episode 6 Act 2.

### Backtest (this is the part I care about)

Methodology: walk-forward. For each act, the model retrains **only on data that was available before that act**, then predicts that act. Nothing about the future leaks into past scoring — the only predictions counted are ones the model could realistically have made in real time.

Results across 30 acts, 453 predictions:

| Metric | Score | Baseline |
|---|---|---|
| 3-class direction hit rate | **60.5%** | random 33% · always-"stable" 55% |
| Last patch (V26A1) | **20/28 = 71.4%** | — |
| Balanced accuracy | 0.541 | — |
| Top-3 nerf / act | 50% | — |
| High-conf nerf (p ≥ 0.70) | 60% precision (n=15) | — |

Full per-act chart + per-class F1 + confusion matrix + threshold calibration here: https://whosnxt.app/en/backtest

### Where it fails (being honest)

- **Nerf class is the weakest.** F1 0.40. It over-predicts nerfs on agents the community obviously hates but Riot leaves alone. Balanced accuracy 0.54 means it's clearly better than random, not magic.
- **Buff calls are shakier than nerf calls at low confidence.** Buff precision only crosses 50% when p_buff ≥ 0.50 (n=86). Below that it's closer to coin-flipping with a slight lean.
- **VCT lag.** Tournament balance lags the live patch by 1–3 weeks, so VCT pick rate for a just-nerfed agent still looks strong for a while. There's a banner on the homepage calling this out.
- **One outlier act hurt the numbers.** Around V25A5 there was a patch where Riot touched several agents the model didn't flag high — you can see the dip in the per-act chart.
- **Reworks are hard.** The model has a separate rework signal but the class is small (n low) so it's noisy.

### How the model works

Two-stage:
1. **Stage A** — XGBoost classifier: "will this agent be touched next patch, or stay stable?" (BA ≈ 0.66)
2. **Stage B** — only runs if Stage A says "touched". Logistic regression splits it into nerf vs. buff. (BA ≈ 0.78)

Final output is 5-class (strong/mild nerf · stable · mild/strong buff) by combining the two stages. I went with 2-stage because the "touched vs. stable" cut is structurally cleaner than a single 3-way.

Ground truth comes from actually reading every patch note E6A2 → V26A1 and labelling each agent change. Hotfixes and mid-patch reworks included.

### What's next

- Automating the label ingestion so I don't hand-code patch notes anymore.
- A "patch simulator" already on the site — you can inject a hypothetical change and see how the meta might shift. It's a toy right now, more of a data-exploration tool than a predictor.
- Better nerf-class recall. The current model is too conservative. Likely needs a cost-sensitive loss or a separate "under pressure" feature.

### Not selling anything

No ads, no account, no login. Just a hobby project. If you click around and something looks wrong, tell me — I'll fix it. If you have a prediction for the next patch, post it in the comments and we can compare what my model thinks.

Site: https://whosnxt.app/en
Backtest report: https://whosnxt.app/en/backtest

Happy to answer questions about features, methodology, or whatever.
```

---

## 이미지 (포스트에 첨부)

- **메인 프리뷰**: `/concepts/reddit-promo` 페이지를 `1280×800` 브라우저에서 풀스크린 스크린샷
- 썸네일 구성: Top Nerf · Top Buff 포트레이트 + `LAST PATCH HIT 20/28 (71%)` 배지 + 액트별 hit rate 라인 차트 (V26A1 하이라이트) + 좌하단 WHOSNXT.APP 워터마크
- 파일명: `whosnxt-reddit-preview.png`
- 필요시 두 번째 이미지로 `/en/backtest` 의 per-act 차트 영역만 크롭해 추가

## 스크린샷 캡처 절차

1. `cd frontend && npm run dev`
2. 브라우저 창을 **1280×900** (또는 16:10 비율) 로 맞춤
3. `http://localhost:3000/concepts/reddit-promo` 접속
4. Chrome DevTools → Device toolbar → `Responsive · 1280 × 800` 로 설정 → `⌘+Shift+P` → `Capture full size screenshot`
5. 결과물의 상단 여백(dev server 헤더)은 크롭으로 제거 — `.shot` 컨테이너만 남기기

## 댓글 대응 가이드

| 질문 유형 | 답변 톤 |
|---|---|
| "랜덤 찍어도 그 정도 아님?" | 랜덤 33%, always-stable baseline 55%, 우리 60.5% 수치 공개. +5pp 리프트는 작지만 유의미 |
| "왜 나는 이 요원이 너프 당할 거라 생각함" | 해당 에이전트 확률 직접 확인 가능한 URL 공유 + 모델이 왜 다르게 보는지 feature 얘기 |
| "데이터 어디서?" | Diamond+ 랭크 공개 집계 + VCT official bracket + 패치노트. 직접 스크래이핑 |
| "오픈소스 언제?" | "지금은 아님, 정리되면 공개 검토" (약속 금지) |
| "한국인임?" | 솔직하게 YES. 한국어 버전은 `/` (루트). 글로벌 프리뷰용으로 `/en` 만듬 |

## 체크리스트

- [ ] 로컬에서 `/en` `/en/backtest` `/concepts/reddit-promo` 다 렌더 확인
- [ ] `whosnxt.app/en` 프로덕션 배포 & 캐시 확인
- [ ] 스크린샷 촬영 & 파일로 저장
- [ ] Reddit 계정 karma ≥ 50 확인 (없으면 서브 차단 가능)
- [ ] r/ValorantCompetitive 규칙 재확인 (self-promo 비율, 플레어)
- [ ] 다음 Valorant 패치 발표 타이밍 확인 (Riot Dev Diaries / 공식 트위터)
- [ ] 포스팅 직후 2-3시간 댓글 실시간 응대
