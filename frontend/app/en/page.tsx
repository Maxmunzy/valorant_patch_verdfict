import TrustBlock from "@/components/TrustBlock";
import TldrHero from "@/components/TldrHero";
import NavButton from "@/components/NavButton";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { getBacktestSummary } from "@/lib/backtest";

export const revalidate = 60;

export const metadata = {
  title: "WHO'S NEXT? // Valorant Patch Predictor",
  description:
    "ML-powered predictions for which Valorant agents get nerfed or buffed next patch. Walk-forward backtest, transparent methodology.",
  openGraph: {
    title: "WHO'S NEXT? // Valorant Patch Predictor",
    description:
      "ML predictions for which Valorant agents get nerfed or buffed next patch. Walk-forward backtest, transparent methodology.",
    url: "/en",
  },
  twitter: {
    card: "summary_large_image" as const,
    title: "WHO'S NEXT? // Valorant Patch Predictor",
    description:
      "ML predictions for which Valorant agents get nerfed or buffed next patch.",
  },
};

export default async function HomeEn() {
  const [agents, backtest] = await Promise.all([
    getAllPredictions().catch(() => [] as AgentPrediction[]),
    getBacktestSummary().catch(() => null),
  ]);

  const nerfAll = agents.filter((agent) => agent.verdict.includes("nerf"));
  const buffAll = agents.filter((agent) => agent.verdict.includes("buff"));
  const hit3 = backtest ? Math.round(backtest.overall.hitRate3 * 100) : null;

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
          An ML project that combines Diamond+ ranked data, VCT pick/win rates, and patch history to estimate which
          agents are closest to being nerfed or buffed next patch.
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

        <TrustBlock backtest={backtest} locale="en" />
      </div>

      <TldrHero topNerf={nerfAll[0] ?? null} topBuff={buffAll[0] ?? null} locale="en" />

      {/* 3 unified CTAs — below TldrHero, vertical stack */}
      <div className="space-y-3">
        <NavButton
          href="/agents"
          tag="ROSTER // ALL"
          title="Full roster"
          sub={
            agents.length > 0
              ? `${nerfAll.length} nerf candidates · ${buffAll.length} buff candidates · ${agents.length} agents total`
              : "Top 3 nerf/buff + full roster"
          }
          color="#FF4655"
          agentName={nerfAll[0]?.agent ?? null}
          enterLabel="ENTER"
        />
        <NavButton
          href="/simulator"
          tag="TOOL // SIMULATE"
          title="Patch simulator"
          sub="Inject hypothetical changes and watch the meta shift."
          color="#4FC3F7"
          agentName={buffAll[0]?.agent ?? null}
          enterLabel="ENTER"
        />
        <NavButton
          href="/en/backtest"
          tag="PROOF // BACKTEST"
          title="Backtest report"
          sub={
            hit3 !== null
              ? `3-class hit rate ${hit3}% · walk-forward backtest details`
              : "Past predictions vs. reality · model credibility"
          }
          color="#4ADE80"
          agentName={nerfAll[1]?.agent ?? buffAll[1]?.agent ?? nerfAll[0]?.agent ?? null}
          enterLabel="ENTER"
        />
      </div>
    </div>
  );
}
