import AgentCard from "@/components/AgentCard";
import BackToHome from "@/components/BackToHome";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import type { Locale } from "@/lib/i18n/dict";
import { getDict } from "@/lib/i18n/dict";
import { notFound } from "next/navigation";

const CATEGORY_BEHAVIOR = {
  nerf: {
    accentColor: "#FF4655",
    filter: (a: AgentPrediction) => a.verdict.includes("nerf"),
    sort: (a: AgentPrediction) => -a.p_nerf,
  },
  buff: {
    accentColor: "#4FC3F7",
    filter: (a: AgentPrediction) => a.verdict.includes("buff"),
    sort: (a: AgentPrediction) => -a.p_buff,
  },
  stable: {
    accentColor: "#64748B",
    filter: (a: AgentPrediction) => a.verdict === "stable",
    sort: (a: AgentPrediction) => -a.p_patch,
  },
  rework: {
    accentColor: "#A78BFA",
    filter: (a: AgentPrediction) => a.verdict === "rework",
    sort: (a: AgentPrediction) => -a.p_patch,
  },
} as const;

export type CategoryType = keyof typeof CATEGORY_BEHAVIOR;

export function isCategoryType(type: string): type is CategoryType {
  return type in CATEGORY_BEHAVIOR;
}

export default async function CategoryContent({
  type,
  locale,
}: {
  type: string;
  locale: Locale;
}) {
  if (!isCategoryType(type)) notFound();

  const behavior = CATEGORY_BEHAVIOR[type];
  const t = getDict(locale).categoryPage;
  const cat = t.categories[type];

  let agents: AgentPrediction[] = [];
  try {
    const all = await getAllPredictions();
    agents = all.filter(behavior.filter).sort((a, b) => behavior.sort(a) - behavior.sort(b));
  } catch {
    /* empty */
  }

  return (
    <div className="space-y-8 pt-8">
      <BackToHome locale={locale} />

      {/* ── PAGE HEADER ──────────────────────────────── */}
      <div className="pl-4" style={{ borderLeft: `2px solid ${behavior.accentColor}` }}>
        <div
          className="text-[9px] font-valo uppercase tracking-[0.25em] mb-0.5"
          style={{ color: "rgba(71,85,105,0.7)" }}
        >
          {cat.labelEn} {t.analysisSuffix}
        </div>
        <h1 className="text-3xl font-valo font-black" style={{ color: behavior.accentColor }}>
          {cat.label}
        </h1>
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          <p className="text-[11px]" style={{ color: "rgba(71,85,105,0.8)" }}>
            {cat.desc}
          </p>
          <span
            className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wider"
            style={{
              color: behavior.accentColor,
              border: `1px solid ${behavior.accentColor}40`,
              background: `${behavior.accentColor}10`,
            }}
          >
            {agents.length} {t.agentsCount}
          </span>
        </div>
      </div>

      {/* ── EMPTY STATE ──────────────────────────────── */}
      {agents.length === 0 && (
        <div
          className="p-12 text-center"
          style={{ border: `1px solid ${behavior.accentColor}18`, background: "#0d1220" }}
        >
          <div className="text-[9px] uppercase tracking-widest" style={{ color: "rgba(51,65,85,0.7)" }}>
            {t.noData}
          </div>
          <p className="text-xs mt-1" style={{ color: "rgba(51,65,85,0.7)" }}>
            {t.empty}
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
                <div className="w-3 h-px" style={{ background: behavior.accentColor }} />
                {t.topPriority}
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
                  <AgentCard key={a.agent} agent={a} size="lg" locale={locale} />
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
                {t.remaining}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start">
                {agents.slice(3).map((a) => (
                  <AgentCard key={a.agent} agent={a} locale={locale} />
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
            <AgentCard key={a.agent} agent={a} locale={locale} />
          ))}
        </div>
      )}

      {/* Hint */}
      {agents.length > 0 && (
        <div
          className="text-center text-[9px] uppercase tracking-widest pt-4"
          style={{ color: "rgba(51,65,85,0.6)" }}
        >
          {t.hint}
        </div>
      )}
    </div>
  );
}
