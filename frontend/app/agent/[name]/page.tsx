import { getAgentPrediction } from "@/lib/api";
import { notFound } from "next/navigation";
import AgentDetailClient, { AgentDetailData } from "@/components/AgentDetailClient";

// 60초 ISR — 배포/데이터 변경 후 체감 반영 시간 단축.
// (backend에 explanation_cache가 있어 비용 증가는 미미)
export const revalidate = 60;

export default async function AgentDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const agentName = decodeURIComponent(name);

  let data: AgentDetailData;

  try {
    // The API returns more fields than the base AgentPrediction type
    data = (await getAgentPrediction(agentName)) as unknown as AgentDetailData;
  } catch {
    notFound();
  }

  return <AgentDetailClient data={data} />;
}
