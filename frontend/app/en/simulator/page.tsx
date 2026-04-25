import SimulatorClient from "@/app/simulator/SimulatorClient";
import { getAgentSkills, AgentSkills } from "@/lib/api";
import { getDict } from "@/lib/i18n/dict";

const t = getDict("en").simulator;

export const metadata = {
  title: t.metaTitle,
};

export const revalidate = 3600;

export default async function SimulatorPageEn() {
  let initialSkills: AgentSkills | null = null;
  try {
    initialSkills = await getAgentSkills();
  } catch {
    initialSkills = null;
  }
  return <SimulatorClient initialSkills={initialSkills} locale="en" />;
}
