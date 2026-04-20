// valorant-api.com UUID → 공식 agent 이미지 CDN 사용
// UUIDs from crawl_all_agents.py AGENTS list (Riot 공식 UUID)
export const AGENT_UUID: Record<string, string> = {
  Astra:     "41fb69c1-4189-7b37-f117-bcaf1e96f1bf",
  Breach:    "5f8d3a7f-467b-97f3-062c-13acf203c006",
  Brimstone: "9f0d8ba9-4140-b941-57d3-a7ad57c6b417",
  Chamber:   "22697a3d-45bf-8dd7-4fec-84a9e28c69d7",
  Clove:     "1dbf2edd-4729-0984-3115-daa5eed44993",
  Cypher:    "117ed9e3-49f3-6512-3ccf-0cada7e3823b",
  Deadlock:  "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235",
  Fade:      "dade69b4-4f5a-8528-247b-219e5a1facd6",
  Gekko:     "e370fa57-4757-3604-3648-499e1f642d3f",
  Harbor:    "95b78ed7-4637-86d9-7e41-71ba8c293152",
  Iso:       "0e38b510-41a8-5780-5e8f-568b2a4f2d6c",
  Jett:      "add6443a-41bd-e414-f6ad-e58d267f4e95",
  KAYO:      "601dbbe7-43ce-be57-2a40-4abd24953621",
  Killjoy:   "1e58de9c-4950-5125-93e9-a0aee9f98746",
  Neon:      "bb2a4828-46eb-8cd1-e765-15848195d751",
  Omen:      "8e253930-4c05-31dd-1b6c-968525494517",
  Phoenix:   "eb93336a-449b-9c1b-0a54-a891f7921d69",
  Raze:      "f94c3b30-42be-e959-889c-5aa313dba261",
  Reyna:     "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc",
  Sage:      "569fdd95-4d10-43ab-ca70-79becc718b46",
  Skye:      "6f2a04ca-43e0-be17-7f36-b3908627744d",
  Sova:      "320b2a48-4d9b-a075-30f1-1f93a9b638fa",
  Tejo:      "b444168c-4e35-8076-db47-ef9bf368f384",
  Viper:     "707eab51-4836-f488-046a-cda6bf494859",
  Vyse:      "efba5359-4016-a1e5-7626-b1ae76895940",
  Waylay:    "df1cb487-4902-002e-5c17-d28e83e78588",
  Miks:      "7c8a4701-4de6-9355-b254-e09bc2a34b72",
  Veto:      "92eeef5d-43b5-1d4a-8d03-b3927a09034b",
  Yoru:      "7f94d92c-4234-0a36-9646-3a87eb8b5c89",
};

export function agentPortrait(name: string): string {
  const uuid = AGENT_UUID[name];
  if (!uuid) return "";
  return `https://media.valorant-api.com/agents/${uuid}/fullportrait.png`;
}

export function agentIcon(name: string): string {
  const uuid = AGENT_UUID[name];
  if (!uuid) return "";
  return `https://media.valorant-api.com/agents/${uuid}/displayicon.png`;
}

// 요원 검색시 한영 입력 모두 허용하기 위한 한글명 매핑
export const AGENT_NAME_KO: Record<string, string> = {
  Jett: "제트", Reyna: "레이나", Raze: "레이즈", Neon: "네온",
  Phoenix: "피닉스", Iso: "아이소", Yoru: "요루", Waylay: "웨이레이",
  Brimstone: "브림스톤", Viper: "바이퍼", Omen: "오멘", Astra: "아스트라",
  Clove: "클로브", Harbor: "하버", Miks: "믹스",
  Killjoy: "킬조이", Cypher: "사이퍼", Sage: "세이지", Chamber: "체임버",
  Deadlock: "데드록", Vyse: "바이스", Veto: "비토",
  Sova: "소바", Skye: "스카이", Fade: "페이드", Breach: "브리치",
  KAYO: "케이오", Gekko: "게코", Tejo: "테호",
};

// 역할 검색/필터용 고정 순서
export const ROLE_ORDER: string[] = ["타격대", "감시자", "척후대", "전략가"];

/** 검색 매칭 — 영문/한글/대소문자 무관 */
export function matchesQuery(agent: string, query: string): boolean {
  if (!query) return true;
  const q = query.trim().toLowerCase();
  if (!q) return true;
  if (agent.toLowerCase().includes(q)) return true;
  const ko = AGENT_NAME_KO[agent];
  if (ko && ko.includes(query.trim())) return true;
  return false;
}
