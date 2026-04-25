import AgentsContent from "@/components/AgentsContent";
import { getDict } from "@/lib/i18n/dict";

export const revalidate = 60;

const t = getDict("en").agentsPage;

export const metadata = {
  title: t.title,
  description: t.description,
};

export default function AgentsPageEn() {
  return <AgentsContent locale="en" />;
}
