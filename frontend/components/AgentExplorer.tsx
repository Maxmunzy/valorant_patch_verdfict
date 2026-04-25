"use client";

import { useMemo, useState } from "react";
import AgentCard from "./AgentCard";
import { AgentPrediction } from "@/lib/api";
import { matchesQuery, ROLE_ORDER } from "@/lib/agents";
import type { Locale } from "@/lib/i18n/dict";
import { getDict, tRole } from "@/lib/i18n/dict";

type SortKey = "urgency" | "rank_pr" | "vct_pr" | "recent_patch";

const SORT_KEYS: SortKey[] = ["urgency", "rank_pr", "vct_pr", "recent_patch"];

/**
 * 모든 요원을 검색 / 역할 필터 / 정렬 토글로 탐색하는 섹션.
 *
 * Top 3 카드가 헤더의 "큐레이션" 역할이라면, 이 컴포넌트는 사용자가
 * "내 주캐 / 궁금한 요원"을 빠르게 찾기 위한 도구.
 */
export default function AgentExplorer({
  agents,
  locale = "ko",
}: {
  agents: AgentPrediction[];
  locale?: Locale;
}) {
  const t = getDict(locale).agentExplorer;
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<string>("__ALL__");
  const [sort, setSort] = useState<SortKey>("urgency");

  const view = useMemo(() => {
    let list = agents;

    if (role !== "__ALL__") {
      list = list.filter((a) => a.role === role);
    }
    if (query.trim()) {
      list = list.filter((a) => matchesQuery(a.agent, query));
    }

    const sorted = [...list];
    switch (sort) {
      case "urgency":
        sorted.sort((a, b) => (b.urgency_score ?? 0) - (a.urgency_score ?? 0));
        break;
      case "rank_pr":
        sorted.sort((a, b) => (b.rank_pr ?? 0) - (a.rank_pr ?? 0));
        break;
      case "vct_pr":
        sorted.sort((a, b) => (b.vct_pr ?? 0) - (a.vct_pr ?? 0));
        break;
      case "recent_patch":
        // days_since_patch 오름차순 (최근이 앞). null은 뒤로 밀기.
        sorted.sort((a, b) => {
          const da = a.days_since_patch ?? Number.MAX_SAFE_INTEGER;
          const db = b.days_since_patch ?? Number.MAX_SAFE_INTEGER;
          return da - db;
        });
        break;
    }
    return sorted;
  }, [agents, query, role, sort]);

  const totalCount = agents.length;

  return (
    <section className="space-y-4">
      {/* 섹션 라벨 */}
      <div className="flex items-center gap-3">
        <div style={{ width: "2px", height: "28px", background: "#A78BFA" }} className="shrink-0" />
        <div>
          <div className="text-[9px] font-valo tracking-[0.25em]" style={{ color: "rgba(167,139,250,0.8)" }}>
            {t.sectionTagEn}
          </div>
          <div className="text-xl font-valo font-bold leading-tight" style={{ color: "#A78BFA" }}>
            {t.sectionLabel}
          </div>
        </div>
        <span
          className="text-[9px] font-bold px-1.5 py-0.5 uppercase tracking-wider ml-1"
          style={{ color: "#A78BFA", border: "1px solid rgba(167,139,250,0.4)", background: "rgba(167,139,250,0.08)" }}
        >
          {view.length} / {totalCount}
        </span>
      </div>

      {/* 컨트롤 바 */}
      <div
        className="flex flex-col sm:flex-row gap-2 sm:gap-3 items-stretch sm:items-center p-3"
        style={{ border: "1px solid rgba(51,65,85,0.55)", background: "rgba(13,18,32,0.55)" }}
      >
        {/* 검색 입력 */}
        <div className="relative flex-1 min-w-0">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.searchPlaceholder}
            aria-label={t.searchAria}
            className="w-full text-sm px-3 py-2 outline-none transition-colors"
            style={{
              border: "1px solid rgba(51,65,85,0.7)",
              background: "rgba(8,12,20,0.7)",
              color: "#e2e8f0",
            }}
            onFocus={(e) => ((e.target as HTMLInputElement).style.borderColor = "rgba(167,139,250,0.6)")}
            onBlur={(e) => ((e.target as HTMLInputElement).style.borderColor = "rgba(51,65,85,0.7)")}
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs px-1.5 py-0.5 transition-colors"
              style={{ color: "rgba(148,163,184,0.7)" }}
              aria-label={t.clearSearch}
            >
              ✕
            </button>
          )}
        </div>

        {/* 역할 필터 */}
        <div className="flex gap-1 flex-wrap shrink-0">
          {[
            { value: "__ALL__", label: t.filterAll },
            ...ROLE_ORDER.map((r) => ({ value: r, label: tRole(locale, r) })),
          ].map((opt) => {
            const active = role === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setRole(opt.value)}
                className="text-[11px] font-semibold px-2.5 py-1.5 uppercase tracking-wider transition-all"
                style={{
                  border: active ? "1px solid #A78BFA" : "1px solid rgba(51,65,85,0.6)",
                  color: active ? "#A78BFA" : "rgba(148,163,184,0.85)",
                  background: active ? "rgba(167,139,250,0.08)" : "rgba(8,12,20,0.5)",
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>

        {/* 정렬 드롭다운 */}
        <div className="relative shrink-0">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label={t.sortAria}
            className="text-[11px] font-semibold uppercase tracking-wider px-2.5 py-1.5 pr-7 appearance-none cursor-pointer"
            style={{
              border: "1px solid rgba(167,139,250,0.45)",
              color: "#A78BFA",
              background: "rgba(167,139,250,0.06)",
            }}
            title={t.sortHints[sort]}
          >
            {SORT_KEYS.map((key) => (
              <option key={key} value={key} style={{ background: "#0d1220", color: "#e2e8f0" }}>
                {t.sortLabels[key]}
              </option>
            ))}
          </select>
          <span
            className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-[9px]"
            style={{ color: "#A78BFA" }}
          >
            ▼
          </span>
        </div>
      </div>

      {/* 결과 그리드 */}
      {view.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 items-start pt-1">
          {view.map((a) => (
            <AgentCard key={a.agent} agent={a} size="sm" locale={locale} />
          ))}
        </div>
      ) : (
        <div
          className="text-center py-10 text-sm"
          style={{
            color: "rgba(148,163,184,0.7)",
            border: "1px dashed rgba(51,65,85,0.55)",
            background: "rgba(13,18,32,0.3)",
          }}
        >
          {t.noMatches}
          {query && (
            <>
              {" "}
              <button
                type="button"
                onClick={() => setQuery("")}
                className="underline decoration-dotted"
                style={{ color: "#A78BFA" }}
              >
                {t.clearSearch}
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}
