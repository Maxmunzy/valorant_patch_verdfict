import Link from "next/link";
import Image from "next/image";
import type { AgentPrediction } from "@/lib/api";
import { agentPortrait } from "@/lib/agents";
import { buildShareHeadline, type Locale } from "@/lib/headline";
import { tRole } from "@/lib/i18n/dict";

interface Props {
  topNerf: AgentPrediction | null;
  topBuff: AgentPrediction | null;
  locale?: Locale;
}

export default function TldrHero({ topNerf, topBuff, locale = "ko" }: Props) {
  if (!topNerf && !topBuff) return null;

  const t =
    locale === "en"
      ? {
          kicker: "TL;DR // this act's key moves",
          title: "Top-ranked patch candidates at a glance",
          detail: "View full analysis",
        }
      : {
          kicker: "TL;DR // 이번 액트 핵심",
          title: "한눈에 보는 최상위 패치 후보",
          detail: "상세 분석 보기",
        };

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3">
        <div
          className="shrink-0"
          style={{
            width: "2px",
            height: "28px",
            background: "linear-gradient(to bottom, #FBBF24, #FBBF2420)",
          }}
        />
        <div>
          <div className="text-[10px] tracking-[0.3em]" style={{ color: "rgba(251,191,36,0.8)" }}>
            {t.kicker}
          </div>
          <div className="text-base font-bold text-white leading-tight">{t.title}</div>
        </div>
      </div>

      <div className={`grid gap-3 ${topNerf && topBuff ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"}`}>
        {topNerf && <HeroCard agent={topNerf} rank="#1 NERF" accent="#FF4655" locale={locale} detailLabel={t.detail} />}
        {topBuff && <HeroCard agent={topBuff} rank="#1 BUFF" accent="#4FC3F7" locale={locale} detailLabel={t.detail} />}
      </div>
    </section>
  );
}

function HeroCard({
  agent,
  rank,
  accent,
  locale,
  detailLabel,
}: {
  agent: AgentPrediction;
  rank: string;
  accent: string;
  locale: Locale;
  detailLabel: string;
}) {
  const portrait = agentPortrait(agent.agent);
  const headline = buildShareHeadline(agent, locale);
  const pct = agent.verdict.includes("nerf")
    ? agent.p_nerf
    : agent.verdict.includes("buff")
      ? agent.p_buff
      : agent.p_patch;
  const href = `/agent/${encodeURIComponent(agent.agent)}`;

  return (
    <Link
      href={href}
      className="group relative overflow-hidden block"
      style={{
        border: `1px solid ${accent}50`,
        background: `linear-gradient(135deg, ${accent}10, rgba(13,18,32,0.85) 65%)`,
        minHeight: "200px",
      }}
    >
      {portrait && (
        <div className="absolute right-0 top-0 bottom-0 pointer-events-none" style={{ width: "58%", zIndex: 0 }}>
          <Image
            src={portrait}
            alt={agent.agent}
            fill
            className="object-cover object-top opacity-55 group-hover:opacity-75 transition-opacity duration-300"
            sizes="400px"
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to right, rgba(13,18,32,0.92) 0%, rgba(13,18,32,0.35) 45%, transparent 85%)",
            }}
          />
        </div>
      )}

      <div
        className="absolute top-0 left-0 right-0 h-px pointer-events-none"
        style={{ zIndex: 5, background: `linear-gradient(90deg, ${accent}, ${accent}50, transparent)` }}
      />

      <div className="absolute top-3 left-3 w-4 h-4 pointer-events-none" style={{ zIndex: 5, borderTop: `1px solid ${accent}70`, borderLeft: `1px solid ${accent}70` }} />
      <div className="absolute bottom-3 right-3 w-4 h-4 pointer-events-none" style={{ zIndex: 5, borderBottom: `1px solid ${accent}50`, borderRight: `1px solid ${accent}50` }} />

      <div className="relative p-5 sm:p-6 flex flex-col justify-between h-full space-y-4" style={{ zIndex: 10 }}>
        <div className="flex items-start justify-between gap-3">
          <span
            className="text-[11px] font-black px-2 py-1 uppercase tracking-widest leading-none"
            style={{ color: accent, border: `1px solid ${accent}70`, background: `${accent}14` }}
          >
            {rank}
          </span>
          <span className="text-[10px] uppercase tracking-widest" style={{ color: "rgba(148,163,184,0.75)" }}>
            {tRole(locale, agent.role)}
          </span>
        </div>

        <div className="space-y-2">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span className="font-black tabular-nums leading-none" style={{ color: accent, fontSize: "clamp(52px, 8vw, 72px)" }}>
              {pct.toFixed(0)}%
            </span>
            <span className="text-3xl sm:text-4xl font-bold tracking-tight text-white leading-none">{agent.agent}</span>
          </div>

          <p className="text-[13px] sm:text-sm leading-snug pt-2 max-w-prose" style={{ color: "rgba(226,232,240,0.92)" }}>
            {headline}
          </p>
        </div>

        <div
          className="flex items-center justify-between text-[10px] uppercase tracking-widest pt-2"
          style={{ borderTop: `1px solid ${accent}22`, color: "rgba(148,163,184,0.85)" }}
        >
          <span>{detailLabel}</span>
          <span className="font-bold group-hover:translate-x-1 transition-transform" style={{ color: accent }}>
            &gt;
          </span>
        </div>
      </div>
    </Link>
  );
}
