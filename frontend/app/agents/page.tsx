import AgentCard from "@/components/AgentCard";
import AgentExplorer from "@/components/AgentExplorer";
import BackToHome from "@/components/BackToHome";
import { getAllPredictions, AgentPrediction } from "@/lib/api";

export const revalidate = 60;

export const metadata = {
  title: "요원 분석 // PATCH VERDICT",
  description: "너프·버프 후보 Top 3과 전체 요원 탐색",
};

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

export default async function AgentsPage() {
  const agents: AgentPrediction[] = await getAllPredictions().catch(() => []);

  const nerfAll = agents.filter((agent) => agent.verdict.includes("nerf"));
  const buffAll = agents.filter((agent) => agent.verdict.includes("buff"));
  const nerfTop3 = nerfAll.slice(0, 3);
  const buffTop3 = buffAll.slice(0, 3);

  return (
    <div className="py-10 space-y-12">
      {/* 페이지 헤더 + 메인으로 돌아가기 */}
      <div className="space-y-4">
        <BackToHome />
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
              FULL ROSTER // NERF · BUFF · EXPLORE
            </div>
            <h1 className="text-4xl sm:text-5xl font-black tracking-wide leading-[0.95] text-white">
              ALL <span style={{ color: "#FF4655" }}>AGENTS</span>
            </h1>
            <p className="text-sm mt-3 max-w-[680px] leading-relaxed" style={{ color: "rgba(148,163,184,0.85)" }}>
              너프·버프 우선순위부터 전체 로스터 탐색까지. 카드를 클릭하면 요원별 상세 분석으로 이동합니다.
            </p>
          </div>
        </div>
      </div>

      {nerfTop3.length > 0 && (
        <section className="space-y-4">
          <SectionLabel label="너프 우선순위" labelEn="NF // NERF TARGETS" accentColor="#FF4655" count={nerfTop3.length} />
          <div className={`grid gap-3 items-start ${nerfTop3.length >= 3 ? "grid-cols-3" : nerfTop3.length === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
            {nerfTop3.map((agent, index) => (
              <AgentCard key={agent.agent} agent={agent} size="lg" rank={index + 1} />
            ))}
          </div>
        </section>
      )}

      {buffTop3.length > 0 && (
        <section className="space-y-4">
          <SectionLabel label="버프 후보" labelEn="BF // BUFF CANDIDATES" accentColor="#4FC3F7" count={buffTop3.length} />
          <div className={`grid gap-3 items-start ${buffTop3.length >= 3 ? "grid-cols-3" : buffTop3.length === 2 ? "grid-cols-2" : "grid-cols-1"}`}>
            {buffTop3.map((agent, index) => (
              <AgentCard key={agent.agent} agent={agent} size="lg" rank={index + 1} />
            ))}
          </div>
        </section>
      )}

      {agents.length > 0 && <AgentExplorer agents={agents} />}

      {agents.length > 0 && (
        <div className="text-center text-[13px] uppercase tracking-widest" style={{ color: "rgb(255, 255, 255)" }}>
          // {agents.length} agents analyzed // click a card for details //
        </div>
      )}

      {agents.length === 0 && (
        <div
          className="text-center py-16 text-[12px] uppercase tracking-[0.25em]"
          style={{ color: "rgba(148,163,184,0.6)" }}
        >
          데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
        </div>
      )}
    </div>
  );
}
