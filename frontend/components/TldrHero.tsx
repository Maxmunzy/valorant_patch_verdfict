/**
 * 홈 최상단에 박히는 "이번 액트 1순위 너프/버프" 대형 헤드라인.
 *
 * 설계 의도 — 첫 5초 안에 "지금 가장 위험한 한 명 / 가장 유망한 한 명"이
 * 스캔될 것. Top3 카드보다 한 단계 앞선 위계.
 *
 * 렌더 규칙:
 *  - 너프 1순위가 있으면 왼쪽, 없으면 스킵
 *  - 버프 1순위가 있으면 오른쪽, 없으면 스킵
 *  - 둘 다 있을 때 큰 포트레이트 + 확률 + 한 줄 근거 (buildShareHeadline)
 *  - 클릭 시 해당 요원 상세로 이동
 *
 * 서버 컴포넌트 — portrait 경로와 헤드라인 문장 모두 SSR에 포함되어
 * OG 크롤러/스크린샷 봇이 읽을 수 있음.
 */

import Link from "next/link";
import Image from "next/image";
import type { AgentPrediction } from "@/lib/api";
import { agentPortrait } from "@/lib/agents";
import { buildShareHeadline } from "@/lib/headline";

interface Props {
  topNerf: AgentPrediction | null;
  topBuff: AgentPrediction | null;
}

export default function TldrHero({ topNerf, topBuff }: Props) {
  if (!topNerf && !topBuff) return null;

  return (
    <section className="space-y-3">
      {/* 한 줄 섹션 라벨 */}
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
          <div
            className="text-[10px] font-valo tracking-[0.3em]"
            style={{ color: "rgba(251,191,36,0.8)" }}
          >
            TL;DR // 이번 액트 1순위
          </div>
          <div className="text-base font-valo font-bold text-white leading-tight">
            한 줄로 보는 메타 변화 예보
          </div>
        </div>
      </div>

      <div
        className={`grid gap-3 ${
          topNerf && topBuff ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"
        }`}
      >
        {topNerf && (
          <HeroCard
            agent={topNerf}
            rank="#1 NERF"
            accent="#FF4655"
            rankColor="#FF4655"
          />
        )}
        {topBuff && (
          <HeroCard
            agent={topBuff}
            rank="#1 BUFF"
            accent="#4FC3F7"
            rankColor="#4FC3F7"
          />
        )}
      </div>
    </section>
  );
}

function HeroCard({
  agent: a,
  rank,
  accent,
  rankColor,
}: {
  agent: AgentPrediction;
  rank: string;
  accent: string;
  rankColor: string;
}) {
  const portrait = agentPortrait(a.agent);
  const headline = buildShareHeadline(a);
  const pct = a.verdict.includes("nerf") ? a.p_nerf : a.verdict.includes("buff") ? a.p_buff : a.p_patch;
  const href = `/agent/${encodeURIComponent(a.agent)}`;

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
      {/* 거대 포트레이트 — 오른쪽에서 좌측으로 페이드 */}
      {portrait && (
        <div
          className="absolute right-0 top-0 bottom-0 pointer-events-none"
          style={{ width: "58%", zIndex: 0 }}
        >
          <Image
            src={portrait}
            alt={a.agent}
            fill
            className="object-cover object-top opacity-35 group-hover:opacity-55 transition-opacity duration-300"
            sizes="400px"
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to right, #0d1220 10%, rgba(13,18,32,0.85) 40%, transparent 85%)",
            }}
          />
        </div>
      )}

      {/* 상단 글로우 라인 */}
      <div
        className="absolute top-0 left-0 right-0 h-px pointer-events-none"
        style={{
          zIndex: 5,
          background: `linear-gradient(90deg, ${accent}, ${accent}50, transparent)`,
        }}
      />

      {/* 코너 브래킷 */}
      <div
        className="absolute top-3 left-3 w-4 h-4 pointer-events-none"
        style={{
          zIndex: 5,
          borderTop: `1px solid ${accent}70`,
          borderLeft: `1px solid ${accent}70`,
        }}
      />
      <div
        className="absolute bottom-3 right-3 w-4 h-4 pointer-events-none"
        style={{
          zIndex: 5,
          borderBottom: `1px solid ${accent}50`,
          borderRight: `1px solid ${accent}50`,
        }}
      />

      {/* 내용 */}
      <div className="relative p-5 sm:p-6 flex flex-col justify-between h-full space-y-4" style={{ zIndex: 10 }}>
        <div className="flex items-start justify-between gap-3">
          <span
            className="text-[11px] font-valo font-black px-2 py-1 uppercase tracking-widest leading-none"
            style={{
              color: rankColor,
              border: `1px solid ${rankColor}70`,
              background: `${rankColor}14`,
            }}
          >
            {rank}
          </span>
          <span
            className="text-[10px] uppercase tracking-widest"
            style={{ color: "rgba(148,163,184,0.75)" }}
          >
            {a.role}
          </span>
        </div>

        <div className="space-y-2">
          <div className="flex items-baseline gap-3 flex-wrap">
            <span
              className="font-valo font-black tabular-nums leading-none"
              style={{ color: accent, fontSize: "clamp(52px, 8vw, 72px)" }}
            >
              {pct.toFixed(0)}%
            </span>
            <span
              className="text-3xl sm:text-4xl font-valo font-bold tracking-tight text-white leading-none"
            >
              {a.agent}
            </span>
          </div>

          {/* 한 줄 근거 — 공유 문장 */}
          <p
            className="text-[13px] sm:text-sm leading-snug pt-2 max-w-prose"
            style={{ color: "rgba(226,232,240,0.92)" }}
          >
            {headline}
          </p>
        </div>

        <div
          className="flex items-center justify-between text-[10px] uppercase tracking-widest pt-2"
          style={{ borderTop: `1px solid ${accent}22`, color: "rgba(148,163,184,0.85)" }}
        >
          <span>상세 분석 보기</span>
          <span
            className="font-bold group-hover:translate-x-1 transition-transform"
            style={{ color: accent }}
          >
            →
          </span>
        </div>
      </div>
    </Link>
  );
}
