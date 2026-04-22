import Link from "next/link";
import Image from "next/image";
import TrustBlock from "@/components/TrustBlock";
import TldrHero from "@/components/TldrHero";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { getBacktestSummary } from "@/lib/backtest";
import { agentPortrait } from "@/lib/agents";

export const revalidate = 60;

// 요원별 초상화 크롭 위치 미세조정 — 기본값 22%
// 공식 CDN 이미지마다 얼굴·몸통 위치가 조금씩 다르기 때문
const PORTRAIT_Y_OVERRIDE: Record<string, string> = {
  KAYO: "15%",
};
function portraitOffsetY(agent?: string | null): string {
  const y = (agent && PORTRAIT_Y_OVERRIDE[agent]) ?? "22%";
  return `center ${y}`;
}

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

function NavButton({
  href,
  tag,
  title,
  sub,
  color,
  agentName,
}: {
  href: string;
  tag: string;
  title: string;
  sub: string;
  color: string;
  agentName?: string | null;
}) {
  const portrait = agentName ? agentPortrait(agentName) : null;
  return (
    <Link
      href={href}
      className="group relative block overflow-hidden transition-all hover:brightness-110"
      style={{
        border: `1px solid ${color}40`,
        background: `linear-gradient(90deg, ${color}12 0%, rgba(13,18,32,0.65) 55%, ${color}06 100%)`,
      }}
    >
      {/* 요원 초상화 — 우측 배경 */}
      {portrait && (
        <div
          className="absolute top-0 bottom-0 right-0 pointer-events-none"
          style={{ width: "45%", zIndex: 0 }}
        >
          <Image
            src={portrait}
            alt=""
            fill
            className="object-cover opacity-30 group-hover:opacity-45 transition-opacity duration-300"
            style={{ objectPosition: portraitOffsetY(agentName) }}
            sizes="500px"
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to right, rgba(13,18,32,0.95) 0%, rgba(13,18,32,0.5) 40%, rgba(13,18,32,0.15) 75%, transparent 100%)",
            }}
          />
        </div>
      )}

      {/* corner brackets */}
      <span
        className="absolute top-0 left-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderTop: `2px solid ${color}`, borderLeft: `2px solid ${color}` }}
      />
      <span
        className="absolute top-0 right-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderTop: `2px solid ${color}80`, borderRight: `2px solid ${color}80` }}
      />
      <span
        className="absolute bottom-0 left-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderBottom: `2px solid ${color}`, borderLeft: `2px solid ${color}` }}
      />
      <span
        className="absolute bottom-0 right-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderBottom: `2px solid ${color}80`, borderRight: `2px solid ${color}80` }}
      />

      <div className="relative flex items-center justify-between gap-4 px-5 sm:px-7 py-3.5 sm:py-4" style={{ zIndex: 10 }}>
        <div className="flex items-center gap-4 sm:gap-5 min-w-0">
          <span
            className="hidden sm:block shrink-0"
            style={{
              width: "2px",
              height: "32px",
              background: `linear-gradient(to bottom, ${color}, ${color}30)`,
            }}
          />
          <div className="min-w-0">
            <div className="text-[9px] tracking-[0.35em] mb-1" style={{ color: `${color}cc` }}>
              {tag}
            </div>
            <div className="text-xl sm:text-2xl font-black tracking-tight text-white leading-none">
              {title}
            </div>
            <div
              className="text-[11px] mt-1.5 tracking-wide truncate"
              style={{ color: "rgba(148,163,184,0.85)" }}
            >
              {sub}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <span
            className="hidden sm:inline text-[10px] font-bold tracking-[0.3em]"
            style={{ color: `${color}bf` }}
          >
            ENTER
          </span>
          <span
            className="text-xl sm:text-3xl font-black leading-none transition-transform group-hover:translate-x-1"
            style={{ color, textShadow: `0 0 14px ${color}66` }}
          >
            ▶
          </span>
        </div>
      </div>
    </Link>
  );
}
