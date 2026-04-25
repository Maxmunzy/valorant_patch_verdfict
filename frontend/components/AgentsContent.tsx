import AgentCard from "@/components/AgentCard";
import AgentExplorer from "@/components/AgentExplorer";
import BackToHome from "@/components/BackToHome";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import type { Locale } from "@/lib/i18n/dict";
import { getDict } from "@/lib/i18n/dict";

/**
 * /agents (KO) · /en/agents (EN) 가 공유하는 본문 렌더링.
 * 데이터 페치는 한 번만, locale 만 다르게.
 */
export default async function AgentsContent({ locale }: { locale: Locale }) {
  const t = getDict(locale).agentsPage;
  const agents: AgentPrediction[] = await getAllPredictions().catch(() => []);

  const nerfAll = agents.filter((agent) => agent.verdict.includes("nerf"));
  const buffAll = agents.filter((agent) => agent.verdict.includes("buff"));
  const nerfTop3 = nerfAll.slice(0, 3);
  const buffTop3 = buffAll.slice(0, 3);

  return (
    <div className="py-10 space-y-12">
      {/* 페이지 헤더 + 메인으로 돌아가기 */}
      <div className="space-y-4">
        <BackToHome locale={locale} />
        <div className="flex items-start gap-4">
          <div
            className="shrink-0 mt-2"
            style={{
              width: "2px",
              height: "52px",
              background: "linear-gradient(to bottom, #FF4655, #FF465530)",
            }}
          />
          <div>
            <div className="text-[9px] tracking-[0.3em] mb-2" style={{ color: "rgba(148,163,184,0.7)" }}>
              {t.heroTagline}
            </div>
            <h1 className="text-4xl sm:text-5xl font-black tracking-wide leading-[0.95] text-white">
              {t.heroLine1} <span style={{ color: "#FF4655" }}>{t.heroLine2}</span>
            </h1>
            <p className="text-sm mt-3 max-w-[680px] leading-relaxed" style={{ color: "rgba(148,163,184,0.85)" }}>
              {t.heroIntro}
            </p>
          </div>
        </div>
      </div>

      {nerfTop3.length > 0 && (
        <section className="space-y-4">
          <SectionLabel
            label={t.sectionNerfLabel}
            labelEn={t.sectionNerfTagEn}
            accentColor="#FF4655"
            count={nerfTop3.length}
          />
          <div
            className={`grid gap-3 items-start ${
              nerfTop3.length >= 3 ? "grid-cols-3" : nerfTop3.length === 2 ? "grid-cols-2" : "grid-cols-1"
            }`}
          >
            {nerfTop3.map((agent, index) => (
              <AgentCard key={agent.agent} agent={agent} size="lg" rank={index + 1} locale={locale} />
            ))}
          </div>
        </section>
      )}

      {buffTop3.length > 0 && (
        <section className="space-y-4">
          <SectionLabel
            label={t.sectionBuffLabel}
            labelEn={t.sectionBuffTagEn}
            accentColor="#4FC3F7"
            count={buffTop3.length}
          />
          <div
            className={`grid gap-3 items-start ${
              buffTop3.length >= 3 ? "grid-cols-3" : buffTop3.length === 2 ? "grid-cols-2" : "grid-cols-1"
            }`}
          >
            {buffTop3.map((agent, index) => (
              <AgentCard key={agent.agent} agent={agent} size="lg" rank={index + 1} locale={locale} />
            ))}
          </div>
        </section>
      )}

      {agents.length > 0 && <AgentExplorer agents={agents} locale={locale} />}

      {agents.length > 0 && (
        <div className="text-center text-[13px] uppercase tracking-widest" style={{ color: "rgb(255, 255, 255)" }}>
          {t.analyzedSummary(agents.length)}
        </div>
      )}

      {agents.length === 0 && (
        <div
          className="text-center py-16 text-[12px] uppercase tracking-[0.25em]"
          style={{ color: "rgba(148,163,184,0.6)" }}
        >
          {t.noData}
        </div>
      )}
    </div>
  );
}

function SectionLabel({
  label,
  labelEn,
  accentColor,
  count,
}: {
  label: string;
  labelEn: string;
  accentColor: string;
  count: number;
}) {
  return (
    <div className="flex items-center gap-3">
      <div style={{ width: "2px", height: "28px", background: accentColor }} className="shrink-0" />
      <div>
        <div className="text-[9px] tracking-[0.25em]" style={{ color: `${accentColor}CC` }}>
          {labelEn}
        </div>
        <div className="text-xl font-bold leading-tight" style={{ color: accentColor }}>
          {label}
        </div>
      </div>
      <span
        className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wider ml-1"
        style={{ color: accentColor, border: `1px solid ${accentColor}40`, background: `${accentColor}10` }}
      >
        TOP {count}
      </span>
    </div>
  );
}
