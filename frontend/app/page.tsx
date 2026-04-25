import TrustBlock from "@/components/TrustBlock";
import TldrHero from "@/components/TldrHero";
import NavButton from "@/components/NavButton";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { getBacktestSummary } from "@/lib/backtest";

export const revalidate = 60;

export default async function Home() {
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

        <TrustBlock backtest={backtest} />
      </div>

      <TldrHero topNerf={nerfAll[0] ?? null} topBuff={buffAll[0] ?? null} />

      {/* 통일된 CTA 3개 — TldrHero 바로 아래, 세로 스택 */}
      <div className="space-y-3">
        <NavButton
          href="/agents"
          tag="ROSTER // ALL"
          title="다른 요원 보러가기"
          sub={
            agents.length > 0
              ? `너프 후보 ${nerfAll.length}명 · 버프 후보 ${buffAll.length}명 · 총 ${agents.length}명 분석`
              : "너프·버프 Top 3 + 전체 로스터"
          }
          color="#FF4655"
          agentName={nerfAll[0]?.agent ?? null}
        />
        <NavButton
          href="/simulator"
          tag="TOOL // SIMULATE"
          title="패치 시뮬레이터"
          sub="가상 변경을 넣고 메타가 어떻게 움직이는지 확인"
          color="#4FC3F7"
          agentName={buffAll[0]?.agent ?? null}
        />
        <NavButton
          href="/backtest"
          tag="PROOF // BACKTEST"
          title="백테스트 리포트"
          sub={
            hit3 !== null
              ? `3-class 적중률 ${hit3}% · walk-forward 백테스트 상세`
              : "과거 예측 vs 실제 · 모델 신뢰도 상세"
          }
          color="#4ADE80"
          agentName={nerfAll[1]?.agent ?? buffAll[1]?.agent ?? nerfAll[0]?.agent ?? null}
        />
      </div>
    </div>
  );
}
