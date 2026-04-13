import { getAgentPrediction } from "@/lib/api";
import { notFound } from "next/navigation";
import AgentDetailClient, { AgentDetailData } from "@/components/AgentDetailClient";

export const revalidate = 300;

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
