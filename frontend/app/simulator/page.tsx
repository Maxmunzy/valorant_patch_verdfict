import SimulatorClient from "./SimulatorClient";
import { getAgentSkills, AgentSkills } from "@/lib/api";

export const metadata = {
  title: "PATCH SIMULATOR // Valorant",
};

// ISR: 1시간마다 재검증 (스킬 데이터는 거의 변하지 않음)
export const revalidate = 3600;

export default async function SimulatorPage() {
  let initialSkills: AgentSkills | null = null;
  try {
    initialSkills = await getAgentSkills();
  } catch {
    // fallback — 클라에서 다시 시도
    initialSkills = null;
  }
  return <SimulatorClient initialSkills={initialSkills} />;
}
