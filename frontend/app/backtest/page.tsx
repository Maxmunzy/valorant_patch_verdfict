import BacktestContent from "@/components/BacktestContent";
import { getDict } from "@/lib/i18n/dict";

export const revalidate = 3600;

const t = getDict("ko").backtestPage;

export const metadata = {
  title: t.title,
  description: t.description,
};

export default function BacktestPage() {
  return <BacktestContent locale="ko" />;
}
