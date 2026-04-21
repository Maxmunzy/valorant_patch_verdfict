import Link from "next/link";
import AgentCard from "@/components/AgentCard";
import AgentExplorer from "@/components/AgentExplorer";
import TrustBlock from "@/components/TrustBlock";
import ModelAccuracyBanner from "@/components/ModelAccuracyBanner";
import TldrHero from "@/components/TldrHero";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { getBacktestSummary } from "@/lib/backtest";

export const revalidate = 60;

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

export default async function Home() {
  const [agents, backtest] = await Promise.all([
    getAllPredictions().catch(() => [] as AgentPrediction[]),
    getBacktestSummary().catch(() => null),
  ]);

  const nerfAll = agents.filter((agent) => agent.verdict.includes("nerf"));
  const buffAll = agents.filter((agent) => agent.verdict.includes("buff"));
  const nerfTop3 = nerfAll.slice(0, 3);
  const buffTop3 = buffAll.slice(0, 3);

  return (
    <div className="min-h-[80vh] flex flex-col py-12 space-y-12">
      <div className="space-y-5">
        <div className="flex items-start gap-4">
          <div
            className="shrink-0 mt-2"
            style={{
              width: "2px",
              height: "60px",
              background: "linear-gradient(to bottom, #FF4655, #FF465530)",
            }}
          />
          <div>
            <div className="text-[9px] tracking-[0.3em] mb-2" style={{ color: "rgba(148,163,184,0.7)" }}>
              TACTICAL ANALYSIS // VALORANT PATCH PREDICTOR // XGBOOST 2-STAGE
            </div>
            <h1 className="text-5xl sm:text-6xl font-black tracking-wide leading-[0.9] text-white">
              WHO&apos;S <span style={{ color: "#FF4655" }}>NEXT</span>
              <span style={{ color: "rgba(51,65,85,0.8)" }}>?</span>
            </h1>
          </div>
        </div>

        <p className="text-sm leading-relaxed max-w-none pl-2" style={{ color: "rgba(148,163,184,0.85)" }}>
          랭크, VCT, 패치 이력을 함께 읽어서 다음 너프와 버프 가능성을 비교하는 데이터 프로젝트입니다.
        </p>

        <div className="flex flex-wrap gap-2 pl-6">
          {[
            "SRC: RANK (DIAMOND+)",
            "SRC: VCT",
            "SRC: PATCH NOTES",
            "MDL: XGBoost 2-STAGE",
          ].map((tag) => (
            <span
              key={tag}
              className="text-[9px] px-2 py-1 uppercase tracking-wider"
              style={{
                border: "1px solid rgba(51,65,85,0.55)",
                color: "rgba(148,163,184,0.55)",
                background: "rgba(13,18,32,0.4)",
              }}
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="pl-6 pt-2">
          <Link
            href="/simulator"
            className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-black uppercase tracking-widest transition-all hover:brightness-125"
            style={{
              border: "1px solid rgba(79,195,247,0.45)",
              color: "#4FC3F7",
              background: "rgba(79,195,247,0.08)",
            }}
          >
            <span style={{ fontSize: "16px" }}>&#9881;</span>
            Patch Simulator
            <span className="text-[9px] font-normal tracking-normal" style={{ color: "rgba(79,195,247,0.65)" }}>
              가상 변경을 넣고 메타 변화를 확인
            </span>
          </Link>
        </div>

        <TrustBlock backtest={backtest} />
        <ModelAccuracyBanner data={backtest} />
      </div>

      <TldrHero topNerf={nerfAll[0] ?? null} topBuff={buffAll[0] ?? null} />

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
    </div>
  );
}
