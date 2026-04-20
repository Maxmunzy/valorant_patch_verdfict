import Image from "next/image";
import Link from "next/link";
import AgentCard from "@/components/AgentCard";
import TrustBlock from "@/components/TrustBlock";
import CollapseSection from "@/components/CollapseSection";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { agentPortrait } from "@/lib/agents";

// 60초 ISR — 배포/데이터 변경 후 체감 반영 시간 단축
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
        <div className="text-[9px] font-valo tracking-[0.25em]" style={{ color: `${accentColor}CC` }}>
          {labelEn}
        </div>
        <div className="text-xl font-valo font-bold leading-tight" style={{ color: accentColor }}>
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
  let agents: AgentPrediction[] = [];
  try {
    agents = await getAllPredictions();
  } catch {
    /* fallback empty */
  }

  // API 응답 순서 유지 (p_nerf/p_buff 내림차순)
  const nerfAll   = agents.filter((a) => a.verdict.includes("nerf"));
  const buffAll   = agents.filter((a) => a.verdict.includes("buff"));
  const stableAll = agents.filter((a) => a.verdict === "stable");

  const nerfTop3  = nerfAll.slice(0, 3);
  const buffTop3  = buffAll.slice(0, 3);
  const nerfRest  = nerfAll.slice(3);
  const buffRest  = buffAll.slice(3);

  return (
    <div className="min-h-[80vh] flex flex-col py-12 space-y-12">

      {/* ── HEADER ──────────────────────────────────── */}
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
            <div
              className="text-[9px] font-valo tracking-[0.3em] mb-2"
              style={{ color: "rgba(148,163,184,0.7)" }}
            >
              TACTICAL ANALYSIS // VALORANT PATCH PREDICTOR // XGBoost 2-Stage
            </div>
            <h1 className="font-valo text-5xl sm:text-6xl font-bold tracking-wide leading-[0.9] text-white">
              WHO&apos;S{" "}
              <span style={{ color: "#FF4655" }}>NEXT</span>
              <span style={{ color: "rgba(51,65,85,0.8)" }}>?</span>
            </h1>
          </div>
        </div>

        <p
          className="text-sm leading-relaxed max-w-none pl-2"
          style={{ color: "rgba(148,163,184,0.85)" }}
        >
          랭크·VCT 성적과 패치 이력을 ML 모델로 분석해 다음 패치 너프/버프 가능성을 예측합니다.
        </p>

        <div className="flex flex-wrap gap-2 pl-6">
          {[
            "SRC: RANK (DIAMOND+) // 패치 이후 평균",
            "SRC: VCT // 패치 이후 누적",
            "MDL: XGBoost 2-Stage",
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
              border: "1px solid rgba(167,139,250,0.5)",
              color: "#A78BFA",
              background: "rgba(167,139,250,0.08)",
            }}
          >
            <span style={{ fontSize: "16px" }}>&#9881;</span>
            패치 시뮬레이터
            <span className="text-[9px] font-normal tracking-normal" style={{ color: "rgba(167,139,250,0.6)" }}>
              스킬 수치를 바꿔보고 메타 변화를 예측
            </span>
          </Link>
        </div>

        {/* ── 데이터 출처 / 갱신 / 확률 의미 신뢰 블록 ───────── */}
        <TrustBlock />
      </div>

      {/* ── NERF TOP 3 ──────────────────────────────── */}
      {nerfTop3.length > 0 && (
        <section className="space-y-4">
          <SectionLabel
            label="너프 위험군"
            labelEn="NF // NERF TARGETS"
            accentColor="#FF4655"
            count={nerfTop3.length}
          />
          <div
            className={`grid gap-3 items-start ${
              nerfTop3.length >= 3 ? "grid-cols-3" :
              nerfTop3.length === 2 ? "grid-cols-2" : "grid-cols-1"
            }`}
          >
            {nerfTop3.map((a, i) => (
              <AgentCard key={a.agent} agent={a} size="lg" rank={i + 1} />
            ))}
          </div>
        </section>
      )}

      {/* ── BUFF TOP 3 ──────────────────────────────── */}
      {buffTop3.length > 0 && (
        <section className="space-y-4">
          <SectionLabel
            label="버프 기대군"
            labelEn="BF // BUFF CANDIDATES"
            accentColor="#4FC3F7"
            count={buffTop3.length}
          />
          <div
            className={`grid gap-3 items-start ${
              buffTop3.length >= 3 ? "grid-cols-3" :
              buffTop3.length === 2 ? "grid-cols-2" : "grid-cols-1"
            }`}
          >
            {buffTop3.map((a, i) => (
              <AgentCard key={a.agent} agent={a} size="lg" rank={i + 1} />
            ))}
          </div>
        </section>
      )}

      {/* ── NERF REST (기본 접힘) ──────────────────────── */}
      {nerfRest.length > 0 && (
        <section>
          <CollapseSection
            defaultOpen={false}
            storageKey="home:nerf-rest"
            header={
              <div
                className="text-[9px] uppercase tracking-[0.25em] flex items-center gap-2"
                style={{ color: "rgba(100,116,139,0.9)" }}
              >
                <div className="w-4 h-px" style={{ background: "rgba(255,70,85,0.6)" }} />
                NERF TARGETS · REMAINING
                <span style={{ color: "rgba(71,85,105,0.9)" }}>({nerfRest.length})</span>
                <div className="flex-1 h-px" style={{ background: "rgba(30,41,59,0.6)" }} />
              </div>
            }
          >
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start pt-3">
              {nerfRest.map((a) => (
                <AgentCard key={a.agent} agent={a} size="sm" />
              ))}
            </div>
          </CollapseSection>
        </section>
      )}

      {/* ── BUFF REST (기본 접힘) ──────────────────────── */}
      {buffRest.length > 0 && (
        <section>
          <CollapseSection
            defaultOpen={false}
            storageKey="home:buff-rest"
            header={
              <div
                className="text-[9px] uppercase tracking-[0.25em] flex items-center gap-2"
                style={{ color: "rgba(100,116,139,0.9)" }}
              >
                <div className="w-4 h-px" style={{ background: "rgba(79,195,247,0.6)" }} />
                BUFF CANDIDATES · REMAINING
                <span style={{ color: "rgba(71,85,105,0.9)" }}>({buffRest.length})</span>
                <div className="flex-1 h-px" style={{ background: "rgba(30,41,59,0.6)" }} />
              </div>
            }
          >
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start pt-3">
              {buffRest.map((a) => (
                <AgentCard key={a.agent} agent={a} size="sm" />
              ))}
            </div>
          </CollapseSection>
        </section>
      )}

      {/* ── STABLE (기본 접힘) ──────────────────────────── */}
      {stableAll.length > 0 && (
        <section>
          <CollapseSection
            defaultOpen={false}
            storageKey="home:stable"
            header={
              <SectionLabel
                label="STABLE"
                labelEn="ST // STABLE"
                accentColor="#64748B"
                count={stableAll.length}
              />
            }
          >
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start pt-4">
              {stableAll.map((a) => (
                <AgentCard key={a.agent} agent={a} size="sm" />
              ))}
            </div>
          </CollapseSection>
        </section>
      )}

      {agents.length > 0 && (
        <div
          className="text-center text-[13px] uppercase tracking-widest"
          style={{ color: "rgb(255, 255, 255)" }}
        >
          // {agents.length} AGENTS ANALYZED · 카드 클릭 시 상세 분석 //
        </div>
      )}
    </div>
  );
}
