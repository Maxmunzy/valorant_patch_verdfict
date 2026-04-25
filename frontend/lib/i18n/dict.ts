/**
 * 다국어 사전. 한국어를 마스터로 두고 영어 미러를 함께 둔다.
 *
 * 컨벤션:
 *  - 페이지/주요 컴포넌트별로 네임스페이스 분리
 *  - 키는 영어 camelCase
 *  - 동적 값은 함수 또는 placeholder ({n}) 사용
 */

export type Locale = "ko" | "en";

const dictKo = {
  common: {
    backHome: "메인으로",
    loadFailed: "데이터를 불러오지 못했습니다.",
    tryAgainLater: "잠시 후 다시 시도해주세요.",
  },
  role: {
    "타격대": "타격대",
    "감시자": "감시자",
    "척후대": "척후대",
    "전략가": "전략가",
  } as Record<string, string>,
  badges: {
    "VCT 지배": "VCT 지배",
    "VCT 주력": "VCT 주력",
    "급등 신호": "급등 신호",
    "너프 MISS": "너프 MISS",
    "버프 MISS": "버프 MISS",
    "과보정": "과보정",
    "복구 조정": "복구 조정",
    "장기 하락": "장기 하락",
    "고점 에이전트": "고점 에이전트",
    "표본 부족": "표본 부족",
  } as Record<string, string>,
  verdictLabel: {
    stable: "안정",
    mild_buff: "약한 버프",
    strong_buff: "강한 버프",
    mild_nerf: "약한 너프",
    strong_nerf: "강한 너프",
    rework: "리워크",
  } as Record<string, string>,
  agentsPage: {
    title: "요원 분석 // PATCH VERDICT",
    description: "너프·버프 후보 Top 3과 전체 요원 탐색",
    heroTagline: "FULL ROSTER // NERF · BUFF · EXPLORE",
    heroLine1: "ALL",
    heroLine2: "AGENTS",
    heroIntro:
      "너프·버프 우선순위부터 전체 로스터 탐색까지. 카드를 클릭하면 요원별 상세 분석으로 이동합니다.",
    sectionNerfTagEn: "NF // NERF TARGETS",
    sectionNerfLabel: "너프 우선순위",
    sectionBuffTagEn: "BF // BUFF CANDIDATES",
    sectionBuffLabel: "버프 후보",
    analyzedSummary: (n: number) => `// ${n} agents analyzed // click a card for details //`,
    noData: "데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.",
  },
  agentExplorer: {
    sectionTagEn: "AF // AGENT FINDER",
    sectionLabel: "모든 요원 탐색",
    searchPlaceholder: "요원 이름 검색 (제트 / Jett)",
    searchAria: "요원 이름 검색",
    clearSearch: "검색어 지우기",
    sortAria: "정렬 기준",
    filterAll: "전체",
    sortLabels: {
      urgency: "위험도순",
      rank_pr: "랭크 픽률순",
      vct_pr: "VCT 픽률순",
      recent_patch: "최근 패치순",
    },
    sortHints: {
      urgency: "패치 가능성이 높은 순 (너프·버프 큰 쪽)",
      rank_pr: "랭크 게임 등장률 높은 순",
      vct_pr: "프로씬 등장률 높은 순",
      recent_patch: "마지막 밸런스 조정이 가까운 순",
    },
    noMatches: "조건에 맞는 요원이 없습니다.",
  },
  categoryPage: {
    analysisSuffix: "// ANALYSIS",
    agentsCount: "AGENTS",
    noData: "— NO DATA —",
    empty: "현재 이 카테고리에 해당하는 요원이 없습니다",
    topPriority: "TOP PRIORITY",
    remaining: "REMAINING",
    hint: "// 카드 클릭 시 상세 분석 페이지로 이동 //",
    categories: {
      nerf: {
        label: "너프 위험군",
        labelEn: "NERF TARGETS",
        desc: "과도한 성능으로 패치 조정이 예상되는 요원",
      },
      buff: {
        label: "버프 기대군",
        labelEn: "BUFF CANDIDATES",
        desc: "성능이 낮거나 과너프 복구가 필요한 요원",
      },
      stable: {
        label: "스테이블",
        labelEn: "STABLE AGENTS",
        desc: "현재 패치 신호가 없는 안정적인 요원",
      },
      rework: {
        label: "리워크",
        labelEn: "REWORK FLAGGED",
        desc: "수치 조정 범위를 넘어 설계 변경이 필요한 요원",
      },
    },
  },
  backtestPage: {
    title: "백테스트 리포트 // PATCH VERDICT",
    description: "워크포워드 방식으로 검증한 모델 정확도",
    loadFailed: "백테스트 데이터를 불러오지 못했습니다.",
    headerKicker: "시간순 재현 백테스트 · 과거 예측 성적표",
    headerTitleA: "예측",
    headerTitleAccent: "정확도",
    headerTitleB: "리포트",
    headerIntro:
      '각 액트마다 **그 시점까지 쌓인 데이터로만** 모델을 처음부터 다시 학습시킨 뒤 해당 액트를 예측하게 했습니다. 즉, 그때 실제로 모델을 돌렸다면 내렸을 예측만 평가에 포함됩니다. 미래 정보를 보고 과거를 맞히는 "치트"가 끼지 않아요.',
    tldrLabel: "한 줄 요약 · TL;DR",
    hero: {
      hitDir: "방향 적중률",
      hitDirSub: (n: number) => `전체 ${n}건 예측 중 너프/버프/안정 방향을 맞힌 비율`,
      hitDirBaseline: (lift: number, majPct: number, vsMaj: number) =>
        `랜덤 33% 대비 +${lift}pp · 항상 stable(${majPct}%) 대비 ${vsMaj >= 0 ? "+" : ""}${vsMaj}pp`,
      strongNerf: "강한 너프 신호 정밀도",
      strongNerfSub: "p_nerf 0.60 이상으로 찍은 예측 중 실제 너프로 이어진 비율",
      coverage: "검증 범위",
      coverageSub: (range: string, n: number) => `${range} · 총 ${n}건 예측`,
    },
    chipsTemplate: (n: number, range: string, acts: number) => [
      `예측 샘플 ${n}건`,
      `기간: ${range}`,
      `${acts}개 액트 폴드`,
      "방식: 시간순 재현 (Walk-forward)",
    ],
    sections: {
      overall: { en: "전체 지표", ko: "클래스별 성능" },
      topAgents: { en: "요원별 성적", ko: "잘 맞힌 요원 · 잘 못 맞힌 요원" },
      confusion: { en: "혼동 행렬", ko: "예측한 것 vs 실제 결과" },
      threshold: { en: "확신도 검증", ko: "확률이 높을 때 실제로도 맞는가" },
      leadHits: { en: "선행 예측", ko: "한 액트 먼저 짚어낸 케이스" },
      bigHits: { en: "대표 적중", ko: "높은 확률로 정확히 맞힌 예측" },
      bigMisses: { en: "대표 오답", ko: "높은 확률로 예측했지만 빗나간 케이스" },
      perAct: { en: "액트별 추이", ko: "각 액트별 예측 적중률" },
      predictionTable: (n: number) => ({ en: "전체 예측 목록", ko: `${n}건 원본 기록` }),
      methodology: { en: "측정 방식" },
    },
    blurbs: {
      topAgents: "한 요원을 여러 액트에 걸쳐 예측해온 누적 적중률입니다. 3건 이상 예측된 요원만 집계했어요.",
      threshold:
        "모델이 높은 확률로 찍을수록 실제 너프/버프가 일어날 비율도 같이 높아져야 정상입니다. 아래는 각 임계값 이상으로 예측한 샘플 가운데 실제 방향이 맞았던 비율이에요.",
      leadHits:
        "아직 너프가 내려오지 않았을 때 모델이 먼저 너프 신호를 올렸고, 실제로 **바로 다음 액트**에서 너프가 확정된 경우입니다.",
      leadHitNarrative: (predAct: string, hitAct: string) =>
        `${predAct} 당시엔 너프가 없는 안정 상태였지만 모델은 이미 너프 신호를 읽었고, 한 액트 뒤 ${hitAct}에서 실제 너프로 이어졌습니다.`,
      bigHits: "모델이 강한 확률로 너프/버프를 예측했고 실제로도 그 방향으로 이어진 케이스예요.",
      bigMisses: "모델이 강한 확률로 너프/버프를 예측했지만 실제는 반대로 흘러간 케이스입니다.",
      perAct:
        "액트가 늘수록 학습 데이터가 쌓입니다. 시간이 가면서 적중률이 안정권에 들어오는지 아래 그래프로 확인할 수 있어요.",
    },
    metrics: {
      hitDir: { label: "방향 적중률", hint: (n: number) => `전체 ${n}건 기준` },
      balAcc: { label: "Balanced Accuracy", hint: "클래스 불균형을 보정한 점수" },
      hit5: { label: "세부 적중률", hint: "약/강 세기까지 맞힌 비율" },
      top3: { label: "액트당 너프 TOP3", hint: "각 액트 너프 확률 상위 3명 중 실제 너프 비율" },
    },
    confusion: {
      colHeader: "예측 (predicted)",
      rowPrefix: "실제",
      caption: '대각선 칸이 "정확히 맞힌 예측". 초록이 짙을수록 잘 맞혔다는 뜻이에요.',
    },
    threshold: {
      colThreshold: "임계값",
      colSamples: "샘플",
      colPrecision: "정밀도",
      tableTitleNerf: "NERF 예측",
      tableTitleBuff: "BUFF 예측",
    },
    perAct: {
      legend3: "방향 적중률 (너프/버프/안정)",
      legend5: "세부 적중률 (약/강까지)",
      legendAvg: (avg: number) => `전체 평균 ${avg}%`,
      footer: (avg: number) =>
        `얇은 세로선은 전체 평균 (${avg}%) 위치 · 5c는 약/강 세기까지 맞힌 세부 적중률이에요.`,
    },
    story: {
      predictedLabel: "예측",
      truthLabel: "실제",
      predictedAtLabel: "예측 시점",
      hitAtLabel: "적중 시점",
    },
    methodology: {
      walkforward: {
        title: "시간순 재현 (Walk-forward)",
        body: '각 폴드에서 `act_idx < T`에 해당하는 과거 데이터로만 학습한 뒤 `act_idx == T`를 예측합니다. 미래 정보가 과거 평가에 새어 들어가지 않는 구조예요.',
      },
      twoStage: {
        title: "2단 구조",
        body:
          '1단(XGBoost)에서 "이 요원이 다음 패치에 조정될지 vs 안정될지"를 판별하고, 조정된다고 판단된 경우에만 2단(Logistic Regression)에서 "너프인지 버프인지"를 가립니다. 최종적으로 5단계 판정(강/약 너프 · 안정 · 강/약 버프)으로 합쳐져요.',
      },
      groundTruth: {
        title: "정답 레이블",
        body: "각 액트 이후 실제로 있었던 너프/버프 이력을 기준으로 매겼습니다. 미니 패치, 리워크, 핫픽스까지 모두 반영했어요.",
      },
      scope: {
        title: "평가 범위",
        body: "결과가 확정된 과거 액트만 대상으로 했습니다 (현재 진행 중인 V26A2는 제외).",
      },
      generated: "생성 시각",
    },
  },
  modelBlurb: {
    operatorTag: "운영자 해설",
    subtitle: "숫자 보기 전에 먼저 읽는 모델 성격",
    glossaryHeader: "용어 풀이",
    glossaryBody:
      '<b>정밀도</b>는 "모델이 너프라고 찍은 것 중 실제 너프였던 비율", <b>재현율</b>은 "실제 너프 중 모델이 미리 잡아낸 비율"입니다. 둘 다 100%로 올리는 건 불가능해서 균형 싸움이에요.',
    classNames: {
      stable: "안정 판정",
      nerf: "너프 탐지",
      buff: "버프 탐지",
    },
    sentences: {
      strongest: (name: string, f1: string, p: number, r: number) =>
        `가장 자신 있게 맞히는 쪽은 **${name}**이에요 — F1 ${f1}, 정밀도 ${p}% · 재현율 ${r}%.`,
      nerfRecallLow: (recallPct: number, missedPct: number, precPct: number) =>
        `**너프는 꽤 신중하게 집습니다** — 실제 너프 중 ${recallPct}%만 미리 잡아내고 나머지 ${missedPct}%는 놓치는 편입니다 (정밀도 ${precPct}%).`,
      weakest: (name: string, f1: string, p: number, r: number) =>
        `가장 까다로운 영역은 **${name}**입니다 — F1 ${f1}, 정밀도 ${p}% · 재현율 ${r}%.`,
      calibrated: (precPct: number, n: number) =>
        `대신 **확률이 높게 찍힐수록 신뢰할 만합니다** — p_nerf 0.70 이상으로 찍은 예측은 ${precPct}% 적중했어요 (n=${n}).`,
      overallFallback: (hitPct: number, balAcc: string) =>
        `전체 방향 적중률은 **${hitPct}%** 수준입니다 (Balanced Accuracy ${balAcc}).`,
    },
  },
  predictionTable: {
    agentSearchLabel: "요원 검색",
    actLabel: "ACT",
    predLabel: "예측",
    hitLabel: "적중",
    filterAll: "전체",
    filterHit: "맞춤",
    filterMiss: "틀림",
    sortToggle: "p_nerf ↓",
    resetFilter: "필터 초기화",
    rowsLabel: "rows",
    columns: {
      act: "Act",
      agent: "요원",
      truth: "실제",
      predicted: "예측",
      hit: "적중",
    },
    emptyRows: "조건에 맞는 행이 없습니다. 필터를 조정해 보세요.",
    expandLabel: (n: number) => `▼ 전체 ${n}개 보기`,
    collapseLabel: (initial: number) => `▲ 접기 (상위 ${initial}개만 보기)`,
    hitTooltip: "방향성 적중",
    missTooltip: "오답",
  },
  simulator: {
    metaTitle: "PATCH SIMULATOR // Valorant",
    headerKicker: "SIM // PATCH SIMULATOR",
    headerTitle: "패치 시뮬레이터",
    headerSub: "요원의 스킬 수치를 변경하고 메타에 미치는 영향을 예측합니다",
    loadingStream: "SIM DATA STREAM // 스킬 데이터 초기화 중...",
    guide: {
      tag: "GUIDE",
      title: "처음이신가요? 3단계로 끝납니다",
      step1Label: "요원 선택",
      step1Hint: "아래에서 조정하고 싶은 요원 클릭",
      step2Label: "수치 변경",
      step2Hint: "C/Q/E/X 스킬 값을 원하는 대로 수정",
      step3Label: "시뮬 실행",
      step3Hint: "메타 변화 + AI 분석 결과 확인",
      presetTitle: "⚡ 샘플 시나리오 · 클릭해서 바로 체험",
    },
    presets: [
      {
        title: "네온 궁극기 너프",
        tag: "너프",
        desc: "오버드라이브 연사 속도 20 → 15 (DPS 25% 감소)",
      },
      {
        title: "케이오 Q 플래시 가격 인하",
        tag: "버프",
        desc: "플래시/드라이브 250 → 150크레딧 (라운드 경제 완화)",
      },
      {
        title: "오멘 연막 지속시간 너프",
        tag: "너프",
        desc: "어둠의 장막 15s → 10s (VCT 고정픽 견제)",
      },
    ],
    pickerLabel: "요원 선택",
    changesHeader: (n: number) => `변경사항 (${n}개)`,
    nerfTag: "너프",
    buffTag: "버프",
    runButton: "시뮬레이션 실행",
    runningButton: "시뮬레이션 중...",
    confirmButton: "확인",
    editHint: "수정",
    noStats: "수치 데이터 없음",
    slotLabels: { C: "C", Q: "Q", E: "E · 시그니처", X: "X · 궁극기" },
    units: {
      seconds: "초",
      meters: "m",
      "meters/second": "m/s",
      meter: "m",
      "meter length": "m",
      charges: "개",
      creds: "크레딧",
      ult_points: "포인트",
    } as Record<string, string>,
    results: {
      title: "시뮬레이션 결과",
      aiTag: "AI 분석",
      aiGenerating: "분석 생성 중...",
      aiUnavailable: "AI 분석을 불러올 수 없습니다",
      directImpact: "직접 영향",
      confidenceLabel: "신뢰도",
      confHigh: "높음",
      confMid: "보통",
      confLow: "낮음",
      similarPatches: "유사 패치 사례",
      ripple: (n: number) => `리플 효과 (${n}명 영향)`,
      ranking: "패치 후 전체 순위",
    },
    summary: {
      stateLabel: (rankPr: string, rankWr: string, vctPr: number, verdict: string, pn: number, pb: number) =>
        `현재 상태: 랭크 픽률 ${rankPr}%, 랭크 승률 ${rankWr}%, VCT 픽률 ${vctPr}%, 현재 판정 ${verdict}(너프${pn}%/버프${pb}%)`,
      warnSampleLow: (vctPr: number, vctWr: number) =>
        `⚠ VCT 픽률 ${vctPr}%로 표본 부족 — VCT 승률 ${vctWr}%는 신뢰 불가`,
      warnDataLag: (lag: number) =>
        `⚠ VCT 데이터 ${lag}액트 전 — 최근 VCT 경기에서 거의 안 쓰임`,
      simResult: (prSign: string, pr: string, wrSign: string, wr: string) =>
        `시뮬 결과: 예상 PR변화 ${prSign}${pr}%p, WR변화 ${wrSign}${wr}%p`,
      verdictChange: (before: string, after: string, pn: number, pb: number) =>
        `판정 변화: ${before} → ${after}(너프${pn}%/버프${pb}%)`,
      ripplePrefix: "리플 효과",
    },
  },
};

type DictShape = typeof dictKo;

const dictEn: DictShape = {
  common: {
    backHome: "Back to home",
    loadFailed: "Could not load data.",
    tryAgainLater: "Please try again later.",
  },
  role: {
    "타격대": "Duelist",
    "감시자": "Sentinel",
    "척후대": "Initiator",
    "전략가": "Controller",
  },
  badges: {
    "VCT 지배": "VCT dominant",
    "VCT 주력": "VCT regular",
    "급등 신호": "Surging",
    "너프 MISS": "Nerf miss",
    "버프 MISS": "Buff miss",
    "과보정": "Overcorrected",
    "복구 조정": "Recovery adjust",
    "장기 하락": "Long decline",
    "고점 에이전트": "Peak agent",
    "표본 부족": "Low sample",
  },
  verdictLabel: {
    stable: "stable",
    mild_buff: "mild buff",
    strong_buff: "strong buff",
    mild_nerf: "mild nerf",
    strong_nerf: "strong nerf",
    rework: "rework",
  },
  agentsPage: {
    title: "Agents // PATCH VERDICT",
    description: "Top 3 nerf/buff candidates and full roster",
    heroTagline: "FULL ROSTER // NERF · BUFF · EXPLORE",
    heroLine1: "ALL",
    heroLine2: "AGENTS",
    heroIntro:
      "From nerf/buff priority to full roster exploration. Click a card to view per-agent analysis.",
    sectionNerfTagEn: "NF // NERF TARGETS",
    sectionNerfLabel: "Nerf priority",
    sectionBuffTagEn: "BF // BUFF CANDIDATES",
    sectionBuffLabel: "Buff candidates",
    analyzedSummary: (n: number) => `// ${n} agents analyzed // click a card for details //`,
    noData: "Could not load data. Please try again later.",
  },
  agentExplorer: {
    sectionTagEn: "AF // AGENT FINDER",
    sectionLabel: "Browse all agents",
    searchPlaceholder: "Search agent (e.g. Jett)",
    searchAria: "Search agent name",
    clearSearch: "Clear",
    sortAria: "Sort by",
    filterAll: "All",
    sortLabels: {
      urgency: "Urgency",
      rank_pr: "Rank pick rate",
      vct_pr: "VCT pick rate",
      recent_patch: "Recently patched",
    },
    sortHints: {
      urgency: "Highest patch likelihood first",
      rank_pr: "Most-picked agents in ranked",
      vct_pr: "Most-picked agents in pro play",
      recent_patch: "Most recent balance change first",
    },
    noMatches: "No agents match the filter.",
  },
  categoryPage: {
    analysisSuffix: "// ANALYSIS",
    agentsCount: "AGENTS",
    noData: "— NO DATA —",
    empty: "No agents currently match this category.",
    topPriority: "TOP PRIORITY",
    remaining: "REMAINING",
    hint: "// click a card to see full analysis //",
    categories: {
      nerf: {
        label: "Nerf targets",
        labelEn: "NERF TARGETS",
        desc: "Agents performing too well — patch adjustments expected.",
      },
      buff: {
        label: "Buff candidates",
        labelEn: "BUFF CANDIDATES",
        desc: "Underperforming agents or post-nerf recovery candidates.",
      },
      stable: {
        label: "Stable",
        labelEn: "STABLE AGENTS",
        desc: "No patch signal — currently in a steady state.",
      },
      rework: {
        label: "Rework flagged",
        labelEn: "REWORK FLAGGED",
        desc: "Beyond numerical tuning — design changes likely needed.",
      },
    },
  },
  backtestPage: {
    title: "Backtest report // PATCH VERDICT",
    description: "Walk-forward validated model accuracy",
    loadFailed: "Could not load backtest data.",
    headerKicker: "WALK-FORWARD BACKTEST · HISTORICAL SCORECARD",
    headerTitleA: "Prediction",
    headerTitleAccent: "Accuracy",
    headerTitleB: "Report",
    headerIntro:
      'For every act, the model is retrained **from scratch using only data available at that point**, then asked to predict that act. No future information leaks into past evaluation — only predictions the model could realistically have made in real time are scored.',
    tldrLabel: "TL;DR",
    hero: {
      hitDir: "Direction hit rate",
      hitDirSub: (n: number) => `Share of ${n} predictions where nerf/buff/stable direction was correct.`,
      hitDirBaseline: (lift: number, majPct: number, vsMaj: number) =>
        `Random baseline 33% · Always-stable baseline ${majPct}%. Lift: +${lift}pp / ${vsMaj >= 0 ? "+" : ""}${vsMaj}pp.`,
      strongNerf: "High-conf nerf precision",
      strongNerfSub: "Of predictions made at p_nerf ≥ 0.60, how many turned into actual nerfs.",
      coverage: "Evaluation coverage",
      coverageSub: (range: string, n: number) => `${range} · ${n} predictions total.`,
    },
    chipsTemplate: (n: number, range: string, acts: number) => [
      `${n} prediction samples`,
      `Range: ${range}`,
      `${acts} act folds`,
      "Method: walk-forward",
    ],
    sections: {
      overall: { en: "Overall metrics", ko: "Per-class performance" },
      topAgents: { en: "Per-agent scoreboard", ko: "Best hits · biggest misses" },
      confusion: { en: "Confusion matrix", ko: "Predicted vs actual" },
      threshold: { en: "Confidence calibration", ko: "Does higher probability mean higher hit rate?" },
      leadHits: { en: "Lead predictions", ko: "Caught one act ahead of the patch" },
      bigHits: { en: "Notable hits", ko: "High-confidence predictions that landed" },
      bigMisses: { en: "Notable misses", ko: "High-confidence predictions that didn't" },
      perAct: { en: "Per-act trend", ko: "Hit rate over time" },
      predictionTable: (n: number) => ({ en: "All predictions", ko: `${n} raw rows` }),
      methodology: { en: "Methodology" },
    },
    blurbs: {
      topAgents:
        "Cumulative hit rate per agent across all evaluated acts. Only agents with at least 3 predictions are listed.",
      threshold:
        "When the model fires a higher probability, the real-world hit rate should rise too. Each row: share of predictions at that threshold that matched reality.",
      leadHits:
        "The model raised a nerf signal before any nerf had landed, and the **next act** confirmed it.",
      leadHitNarrative: (predAct: string, hitAct: string) =>
        `At ${predAct} the agent was still untouched, but the model already saw the nerf coming — confirmed one act later at ${hitAct}.`,
      bigHits: "Cases where the model fired a strong probability and reality went the same direction.",
      bigMisses: "Cases where the model fired a strong probability and reality went the opposite way.",
      perAct:
        "As more acts accumulate, training data grows. The chart below checks whether hit rate stabilizes over time — a sanity check against early overfitting.",
    },
    metrics: {
      hitDir: { label: "Direction hit rate", hint: (n: number) => `Across ${n} predictions.` },
      balAcc: { label: "Balanced accuracy", hint: "Class-imbalance corrected." },
      hit5: { label: "5-class hit rate", hint: "Mild/strong intensity also correct." },
      top3: { label: "Top-3 nerf / act", hint: "Actual nerfs among top-3 nerf picks per act." },
    },
    confusion: {
      colHeader: "Predicted",
      rowPrefix: "Actual",
      caption: "Diagonal cells = exact matches. Greener = better.",
    },
    threshold: {
      colThreshold: "Threshold",
      colSamples: "n",
      colPrecision: "Precision",
      tableTitleNerf: "Nerf predictions",
      tableTitleBuff: "Buff predictions",
    },
    perAct: {
      legend3: "Direction hit rate",
      legend5: "5-class hit rate",
      legendAvg: (avg: number) => `Avg ${avg}%`,
      footer: (avg: number) =>
        `Dashed line = overall average (${avg}%) · 5c = hit rate including mild/strong intensity.`,
    },
    story: {
      predictedLabel: "predicted",
      truthLabel: "actual",
      predictedAtLabel: "predicted at",
      hitAtLabel: "confirmed at",
    },
    methodology: {
      walkforward: {
        title: "Walk-forward",
        body:
          'Each fold trains on `act_idx < T` and predicts `act_idx == T`. Future information never leaks into past evaluation.',
      },
      twoStage: {
        title: "Two-stage model",
        body:
          'Stage A (XGBoost) classifies *touched next patch vs. stable*. Stage B (Logistic Regression) splits touched into nerf vs. buff. Final output: 5 classes (strong/mild nerf · stable · mild/strong buff).',
      },
      groundTruth: {
        title: "Ground truth",
        body:
          "Labels come from actual post-patch nerf/buff history, including mid-patch hotfixes and reworks.",
      },
      scope: {
        title: "Evaluation scope",
        body: "Only acts with confirmed patch outcomes are evaluated (current in-flight act V26A2 excluded).",
      },
      generated: "Generated at",
    },
  },
  modelBlurb: {
    operatorTag: "OPERATOR NOTE",
    subtitle: "Read this before staring at the numbers.",
    glossaryHeader: "Glossary",
    glossaryBody:
      '<b>Precision</b> = "of predictions the model called nerf, share that were actual nerfs". <b>Recall</b> = "of actual nerfs, share that the model caught in advance". You can\'t push both to 100% — it\'s a balancing act.',
    classNames: {
      stable: "Stable calls",
      nerf: "Nerf detection",
      buff: "Buff detection",
    },
    sentences: {
      strongest: (name: string, f1: string, p: number, r: number) =>
        `The model is most confident at **${name}** — F1 ${f1}, precision ${p}%, recall ${r}%.`,
      nerfRecallLow: (recallPct: number, missedPct: number, precPct: number) =>
        `**Nerf calls are conservative** — only ${recallPct}% of real nerfs are caught in advance, the other ${missedPct}% slip through (precision ${precPct}%).`,
      weakest: (name: string, f1: string, p: number, r: number) =>
        `The toughest area is **${name}** — F1 ${f1}, precision ${p}%, recall ${r}%.`,
      calibrated: (precPct: number, n: number) =>
        `**Confidence does carry signal** — predictions made at p_nerf ≥ 0.70 hit ${precPct}% of the time (n=${n}).`,
      overallFallback: (hitPct: number, balAcc: string) =>
        `Overall direction hit rate sits at **${hitPct}%** (balanced accuracy ${balAcc}).`,
    },
  },
  predictionTable: {
    agentSearchLabel: "Search agent",
    actLabel: "ACT",
    predLabel: "Predicted",
    hitLabel: "Hit",
    filterAll: "All",
    filterHit: "Hit",
    filterMiss: "Miss",
    sortToggle: "p_nerf ↓",
    resetFilter: "Reset",
    rowsLabel: "rows",
    columns: {
      act: "Act",
      agent: "Agent",
      truth: "Actual",
      predicted: "Predicted",
      hit: "Hit",
    },
    emptyRows: "No rows match. Adjust the filter.",
    expandLabel: (n: number) => `▼ Show all ${n}`,
    collapseLabel: (initial: number) => `▲ Collapse (top ${initial} only)`,
    hitTooltip: "Direction hit",
    missTooltip: "Miss",
  },
  simulator: {
    metaTitle: "PATCH SIMULATOR // Valorant",
    headerKicker: "SIM // PATCH SIMULATOR",
    headerTitle: "Patch simulator",
    headerSub: "Tweak an agent's ability stats and project the meta impact.",
    loadingStream: "SIM DATA STREAM // initializing skill data...",
    guide: {
      tag: "GUIDE",
      title: "First time? It only takes 3 steps.",
      step1Label: "Pick an agent",
      step1Hint: "Click the agent you want to adjust below.",
      step2Label: "Edit a stat",
      step2Hint: "Modify any C/Q/E/X stat value.",
      step3Label: "Run sim",
      step3Hint: "See the meta shift + AI commentary.",
      presetTitle: "⚡ Sample scenarios · click to try one.",
    },
    presets: [
      {
        title: "Neon ult nerf",
        tag: "Nerf",
        desc: "Overdrive fire rate 20 → 15 (DPS −25%)",
      },
      {
        title: "KAYO Q flash discount",
        tag: "Buff",
        desc: "Flash/drive 250 → 150 creds (round-economy ease)",
      },
      {
        title: "Omen smoke duration nerf",
        tag: "Nerf",
        desc: "Dark Cover 15s → 10s (counter-VCT pick)",
      },
    ],
    pickerLabel: "Pick an agent",
    changesHeader: (n: number) => `Changes (${n})`,
    nerfTag: "Nerf",
    buffTag: "Buff",
    runButton: "Run simulation",
    runningButton: "Simulating...",
    confirmButton: "OK",
    editHint: "edit",
    noStats: "No tunable stats.",
    slotLabels: { C: "C", Q: "Q", E: "E · Signature", X: "X · Ultimate" },
    units: {
      seconds: "s",
      meters: "m",
      "meters/second": "m/s",
      meter: "m",
      "meter length": "m",
      charges: "ct",
      creds: "creds",
      ult_points: "pts",
    },
    results: {
      title: "Simulation result",
      aiTag: "AI commentary",
      aiGenerating: "Generating commentary...",
      aiUnavailable: "AI commentary unavailable.",
      directImpact: "Direct impact",
      confidenceLabel: "Confidence",
      confHigh: "high",
      confMid: "med",
      confLow: "low",
      similarPatches: "Similar past patches",
      ripple: (n: number) => `Ripple effects (${n} agents)`,
      ranking: "Post-patch ranking",
    },
    summary: {
      stateLabel: (rankPr: string, rankWr: string, vctPr: number, verdict: string, pn: number, pb: number) =>
        `Current: rank PR ${rankPr}%, rank WR ${rankWr}%, VCT PR ${vctPr}%, verdict ${verdict} (nerf ${pn}% / buff ${pb}%)`,
      warnSampleLow: (vctPr: number, vctWr: number) =>
        `⚠ VCT PR ${vctPr}% is below the sample threshold — VCT WR ${vctWr}% is unreliable`,
      warnDataLag: (lag: number) =>
        `⚠ VCT data is ${lag} acts behind — barely picked in recent VCT play`,
      simResult: (prSign: string, pr: string, wrSign: string, wr: string) =>
        `Sim: projected PR change ${prSign}${pr}pp, WR change ${wrSign}${wr}pp`,
      verdictChange: (before: string, after: string, pn: number, pb: number) =>
        `Verdict: ${before} → ${after} (nerf ${pn}% / buff ${pb}%)`,
      ripplePrefix: "Ripple",
    },
  },
};

export const dict = { ko: dictKo, en: dictEn };

export function getDict(locale: Locale = "ko") {
  return dict[locale];
}

/** 한글 역할 라벨을 현재 locale 로 변환. 매칭 실패 시 원본 반환. */
export function tRole(locale: Locale, role?: string | null): string {
  if (!role) return "";
  return dict[locale].role[role] ?? role;
}

/** 한글 뱃지 라벨을 현재 locale 로 변환. 매칭 실패 시 원본 반환. */
export function tBadge(locale: Locale, badge: string): string {
  return dict[locale].badges[badge] ?? badge;
}
