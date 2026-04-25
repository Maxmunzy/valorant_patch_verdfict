import Link from "next/link";
import type { BacktestSummary } from "@/lib/backtest";
import { AGENT_NAME_KO } from "@/lib/agents";
import type { Locale } from "@/lib/headline";

/**
 * 홈 최상단에 박는 소셜 프루프 카드.
 * "우리가 지난 패치에서 실제로 몇 개 맞혔냐" 를 한 줄로 보여줌.
 *
 * 데이터 출처: public/backtest-summary.json → perAct[마지막] + predictions 필터.
 * perAct 배열의 마지막 항목이 가장 최근에 검증 완료된 액트 (현재 액트 직전).
 */

interface Props {
  backtest: BacktestSummary | null;
  locale?: Locale;
}

export default function RecentPatchHitCard({ backtest, locale = "ko" }: Props) {
  if (!backtest || !backtest.perAct.length) return null;

  const last = backtest.perAct[backtest.perAct.length - 1];
  const hitRate = Math.round(last.hit_dir * 100);
  const hitCount = Math.round(last.hit_dir * last.n);
  const notable = backtest.stories.bigHits
    .filter((row) => row.act === last.act && (row.kind === "nerf_hit" || row.kind === "buff_hit"))
    .slice(0, 3)
    .map((row) => {
      const nameEn = row.agent;
      const nameKo = AGENT_NAME_KO[row.agent] ?? row.agent;
      return {
        agent: row.agent,
        display: locale === "en" ? nameEn : nameKo,
        direction:
          locale === "en"
            ? row.kind === "nerf_hit"
              ? "nerf hit"
              : "buff hit"
            : row.kind === "nerf_hit"
              ? "너프 적중"
              : "버프 적중",
        color: row.kind === "nerf_hit" ? "#FF4655" : "#4FC3F7",
      };
    });

  const t =
    locale === "en"
      ? {
          badge: `LAST PATCH · ${last.act}`,
          hitSuffix: `/ ${last.n} hits`,
          report: "Backtest report",
          href: "/en/backtest",
        }
      : {
          badge: `LAST PATCH · ${last.act}`,
          hitSuffix: `/ ${last.n} 적중`,
          report: "백테스트 리포트",
          href: "/backtest",
        };

  return (
    <Link
      href={t.href}
      className="group relative block overflow-hidden transition-all hover:brightness-110"
      style={{
        border: "1px solid rgba(74,222,128,0.45)",
        background:
          "linear-gradient(90deg, rgba(74,222,128,0.14) 0%, rgba(13,18,32,0.65) 50%, rgba(74,222,128,0.06) 100%)",
      }}
    >
      {/* corner brackets */}
      <span
        className="absolute top-0 left-0 w-3 h-3 pointer-events-none"
        style={{ borderTop: "2px solid #4ADE80", borderLeft: "2px solid #4ADE80" }}
      />
      <span
        className="absolute top-0 right-0 w-3 h-3 pointer-events-none"
        style={{ borderTop: "2px solid #4ADE8080", borderRight: "2px solid #4ADE8080" }}
      />
      <span
        className="absolute bottom-0 left-0 w-3 h-3 pointer-events-none"
        style={{ borderBottom: "2px solid #4ADE80", borderLeft: "2px solid #4ADE80" }}
      />
      <span
        className="absolute bottom-0 right-0 w-3 h-3 pointer-events-none"
        style={{ borderBottom: "2px solid #4ADE8080", borderRight: "2px solid #4ADE8080" }}
      />

      <div className="relative px-4 sm:px-5 py-3 sm:py-3.5 flex items-center gap-3 sm:gap-5">
        {/* 왼쪽: 라이브 인디케이터 + 배지 */}
        <div
          className="shrink-0 flex items-center gap-2 px-2.5 py-1"
          style={{
            border: "1px solid rgba(74,222,128,0.55)",
            background: "rgba(74,222,128,0.08)",
          }}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ background: "#4ADE80", boxShadow: "0 0 6px #4ADE80" }}
          />
          <span
            className="text-[9px] font-bold tracking-[0.3em]"
            style={{ color: "#4ADE80" }}
          >
            {t.badge}
          </span>
        </div>

        {/* 본문: 적중 수치 + 주요 히트 */}
        <div className="flex-1 min-w-0 flex items-baseline gap-3 flex-wrap">
          <div className="flex items-baseline gap-1.5 leading-none">
            <span className="text-[22px] sm:text-[26px] font-black tabular-nums" style={{ color: "#4ADE80" }}>
              {hitCount}
            </span>
            <span className="text-[13px] sm:text-[14px]" style={{ color: "rgba(148,163,184,0.8)" }}>
              {t.hitSuffix}
            </span>
            <span
              className="text-[12px] sm:text-[13px] font-bold tabular-nums ml-1"
              style={{ color: "#4ADE80" }}
            >
              {hitRate}%
            </span>
          </div>

          {notable.length > 0 && (
            <div className="hidden sm:flex items-center gap-2 min-w-0">
              <span className="text-[10px] tracking-[0.25em]" style={{ color: "rgba(148,163,184,0.45)" }}>
                ──
              </span>
              <div className="flex items-center gap-2 truncate">
                {notable.map((item, i) => (
                  <span key={item.agent} className="flex items-center gap-1 text-[11px] tracking-wide whitespace-nowrap">
                    {i > 0 && <span style={{ color: "rgba(148,163,184,0.35)" }}>·</span>}
                    <span className="font-bold" style={{ color: item.color }}>
                      {item.display}
                    </span>
                    <span style={{ color: "rgba(148,163,184,0.65)" }}>{item.direction}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 오른쪽: 리포트 링크 */}
        <div className="shrink-0 flex items-center gap-2">
          <span
            className="hidden sm:inline text-[10px] font-bold tracking-[0.3em]"
            style={{ color: "rgba(74,222,128,0.8)" }}
          >
            {t.report}
          </span>
          <span
            className="text-lg font-black transition-transform group-hover:translate-x-0.5"
            style={{ color: "#4ADE80", textShadow: "0 0 10px rgba(74,222,128,0.4)" }}
          >
            ▸
          </span>
        </div>
      </div>
    </Link>
  );
}
