import Link from "next/link";
import AgentCard from "@/components/AgentCard";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { notFound } from "next/navigation";

export const revalidate = 300;

const CATEGORY_CONFIG = {
  nerf: {
    label:       "너프 위험군",
    labelEn:     "NERF TARGETS",
    desc:        "과도한 성능으로 패치 조정이 예상되는 요원",
    accentColor: "#FF4655",
    filter:      (a: AgentPrediction) => a.verdict.includes("nerf"),
    sort:        (a: AgentPrediction) => -a.p_nerf,
  },
  buff: {
    label:       "버프 기대군",
    labelEn:     "BUFF CANDIDATES",
    desc:        "성능이 낮거나 과너프 복구가 필요한 요원",
    accentColor: "#4FC3F7",
    filter:      (a: AgentPrediction) => a.verdict.includes("buff"),
    sort:        (a: AgentPrediction) => -a.p_buff,
  },
  stable: {
    label:       "스테이블",
    labelEn:     "STABLE AGENTS",
    desc:        "현재 패치 신호가 없는 안정적인 요원",
    accentColor: "#64748B",
    filter:      (a: AgentPrediction) => a.verdict === "stable",
    sort:        (a: AgentPrediction) => -a.p_patch,
  },
  rework: {
    label:       "리워크",
    labelEn:     "REWORK FLAGGED",
    desc:        "수치 조정 범위를 넘어 설계 변경이 필요한 요원",
    accentColor: "#A78BFA",
    filter:      (a: AgentPrediction) => a.verdict === "rework",
    sort:        (a: AgentPrediction) => -a.p_patch,
  },
} as const;

type CategoryType = keyof typeof CATEGORY_CONFIG;

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ type: string }>;
}) {
  const { type } = await params;
  if (!(type in CATEGORY_CONFIG)) notFound();

  const cfg = CATEGORY_CONFIG[type as CategoryType];

  let agents: AgentPrediction[] = [];
  try {
    const all = await getAllPredictions();
    agents = all.filter(cfg.filter).sort((a, b) => cfg.sort(a) - cfg.sort(b));
  } catch {
    /* empty */
  }

  return (
    <div className="space-y-8 pt-8">

      {/* Back link */}
      <Link
        href="/"
        className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-widest transition-colors"
        style={{ color: "rgba(71,85,105,0.7)" }}
      >
        ← BACK TO OVERVIEW
      </Link>

      {/* ── PAGE HEADER ──────────────────────────────── */}
      <div
        className="pl-4"
        style={{ borderLeft: `2px solid ${cfg.accentColor}` }}
      >
        <div
          className="text-[9px] font-valo uppercase tracking-[0.25em] mb-0.5"
          style={{ color: "rgba(71,85,105,0.7)" }}
        >
          {cfg.labelEn} // ANALYSIS
        </div>
        <h1 className="text-3xl font-valo font-black" style={{ color: cfg.accentColor }}>
          {cfg.label}
        </h1>
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          <p className="text-[11px]" style={{ color: "rgba(71,85,105,0.8)" }}>
            {cfg.desc}
          </p>
          <span
            className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wider"
            style={{
              color:       cfg.accentColor,
              border:      `1px solid ${cfg.accentColor}40`,
              background:  `${cfg.accentColor}10`,
            }}
          >
            {agents.length} AGENTS
          </span>
        </div>
      </div>

      {/* ── EMPTY STATE ──────────────────────────────── */}
      {agents.length === 0 && (
        <div
          className="p-12 text-center"
          style={{ border: `1px solid ${cfg.accentColor}18`, background: "#0d1220" }}
        >
          <div
            className="text-[9px] uppercase tracking-widest"
            style={{ color: "rgba(51,65,85,0.7)" }}
          >
            — NO DATA —
          </div>
          <p
            className="text-xs mt-1"
            style={{ color: "rgba(51,65,85,0.7)" }}
          >
            현재 이 카테고리에 해당하는 요원이 없습니다
          </p>
        </div>
      )}

      {/* ── NERF / BUFF: Top 3 highlighted ─────────── */}
      {agents.length > 0 && (type === "nerf" || type === "buff") && (
        <>
          {agents.length >= 1 && (
            <div>
              <div
                className="text-[9px] uppercase tracking-widest mb-3 flex items-center gap-2"
                style={{ color: "rgba(71,85,105,0.6)" }}
              >
                <div className="w-3 h-px" style={{ background: cfg.accentColor }} />
                TOP PRIORITY
              </div>
              <div
                className={`grid gap-2 items-start ${
                  agents.length >= 3
                    ? "grid-cols-3"
                    : agents.length === 2
                    ? "grid-cols-2"
                    : "grid-cols-1"
                }`}
              >
                {agents.slice(0, Math.min(3, agents.length)).map((a) => (
                  <AgentCard key={a.agent} agent={a} size="lg" />
                ))}
              </div>
            </div>
          )}

          {agents.length > 3 && (
            <div>
              <div
                className="text-[9px] uppercase tracking-widest mb-3 flex items-center gap-2"
                style={{ color: "rgba(71,85,105,0.5)" }}
              >
                <div className="w-3 h-px" style={{ background: "rgba(51,65,85,0.8)" }} />
                REMAINING
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start">
                {agents.slice(3).map((a) => (
                  <AgentCard key={a.agent} agent={a} />
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── STABLE / REWORK: uniform grid ────────── */}
      {agents.length > 0 && (type === "stable" || type === "rework") && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start">
          {agents.map((a) => (
            <AgentCard key={a.agent} agent={a} />
          ))}
        </div>
      )}

      {/* Hint */}
      {agents.length > 0 && (
        <div
          className="text-center text-[9px] uppercase tracking-widest pt-4"
          style={{ color: "rgba(51,65,85,0.6)" }}
        >
          // 카드 클릭 시 상세 분석 페이지로 이동 //
        </div>
      )}
    </div>
  );
}
