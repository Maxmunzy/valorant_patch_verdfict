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
