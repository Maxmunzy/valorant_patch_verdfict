import { getBacktestSummary } from "@/lib/backtest";
import type { BacktestAgentRow } from "@/lib/backtest";
import BacktestPredictionTable from "@/components/backtest/BacktestPredictionTable";
import ModelCharacterBlurb from "@/components/backtest/ModelCharacterBlurb";
import BackToHome from "@/components/BackToHome";
import type { Locale } from "@/lib/i18n/dict";
import { getDict } from "@/lib/i18n/dict";

const DIR_COLOR = { stable: "#94A3B8", buff: "#4FC3F7", nerf: "#FF4655" } as const;

export default async function BacktestContent({ locale }: { locale: Locale }) {
  const data = await getBacktestSummary();
  const t = getDict(locale).backtestPage;
  const verdictLabel = (k: string) => getDict(locale).verdictLabel[k] ?? k;

  if (!data) {
    return (
      <div className="py-20 text-center">
        <div className="text-sm" style={{ color: "rgba(148,163,184,0.8)" }}>
          {t.loadFailed}
        </div>
        <div className="inline-block mt-4">
          <BackToHome locale={locale} />
        </div>
      </div>
    );
  }

  const o = data.overall;

  // ─ baseline 계산 ────────────────────────────────────────────
  const totalSupport = Object.values(o.classes).reduce((a, c) => a + c.support, 0) || 1;
  const majorityClass = (Object.entries(o.classes) as [string, { support: number }][]).reduce(
    (best, cur) => (cur[1].support > best[1].support ? cur : best),
  );
  const majorityPct = Math.round((majorityClass[1].support / totalSupport) * 100);
  const hitPct = Math.round(o.hitRate3 * 100);
  const liftVsRandom = hitPct - 33;
  const liftVsMajority = hitPct - majorityPct;
  const range = `${data.actRange.first} → ${data.actRange.last}`;

  return (
    <div className="py-10 space-y-10">
      {/* ── 헤더 ─────────────────────────────────────────────────────── */}
      <div className="space-y-5">
        <BackToHome locale={locale} />

        <div className="flex items-start gap-4">
          <div
            className="shrink-0 mt-2"
            style={{
              width: "3px",
              height: "72px",
              background: "linear-gradient(to bottom, #4ADE80, #4ADE8030)",
            }}
          />
          <div>
            <div
              className="text-[11px] font-valo tracking-[0.3em] mb-2"
              style={{ color: "rgba(148,163,184,0.75)" }}
            >
              {t.headerKicker}
            </div>
            <h1 className="font-valo text-4xl sm:text-5xl font-bold tracking-wide leading-[0.95] text-white">
              {t.headerTitleA} <span style={{ color: "#4ADE80" }}>{t.headerTitleAccent}</span>{" "}
              {t.headerTitleB}
            </h1>
          </div>
        </div>

        <p
          className="text-[13px] leading-relaxed max-w-3xl pl-2"
          style={{ color: "rgba(203,213,225,0.9)" }}
          dangerouslySetInnerHTML={{
            __html: t.headerIntro.replace(
              /\*\*(.*?)\*\*/g,
              '<span class="font-bold text-white">$1</span>',
            ),
          }}
        />
      </div>

      {/* ── 빅 숫자 HERO 카드 ────────────────────────────────────────── */}
      <section
        className="p-6 sm:p-8"
        style={{
          border: "1px solid rgba(74,222,128,0.35)",
          background: "linear-gradient(135deg, rgba(74,222,128,0.08), rgba(13,18,32,0.6))",
        }}
      >
        <div
          className="text-[11px] sm:text-[12px] uppercase tracking-[0.3em] font-bold mb-5"
          style={{ color: "rgba(74,222,128,0.85)" }}
        >
          {t.tldrLabel}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8">
          <HeroStat
            label={t.hero.hitDir}
            value={`${hitPct}%`}
            sub={t.hero.hitDirSub(data.totalRows)}
            accent="#4ADE80"
            baseline={t.hero.hitDirBaseline(liftVsRandom, majorityPct, liftVsMajority)}
          />
          <HeroStat
            label={t.hero.strongNerf}
            value={`${Math.round(
              (data.highConf.nerf.find((r) => Math.abs(r.threshold - 0.6) < 0.01)?.precision ??
                0) * 100,
            )}%`}
            sub={t.hero.strongNerfSub}
            accent="#FF4655"
          />
          <HeroStat
            label={t.hero.coverage}
            value={`${data.acts.length} ACT`}
            sub={t.hero.coverageSub(range, data.totalRows)}
            accent="#7DD3FC"
          />
        </div>
        <div
          className="flex flex-wrap gap-2 mt-6 pt-5"
          style={{ borderTop: "1px solid rgba(51,65,85,0.5)" }}
        >
          {t.chipsTemplate(data.totalRows, range, data.acts.length).map((tag) => (
            <span
              key={tag}
              className="text-[11px] px-2.5 py-1.5 uppercase tracking-wider font-mono"
              style={{
                border: "1px solid rgba(51,65,85,0.55)",
                color: "rgba(148,163,184,0.85)",
                background: "rgba(13,18,32,0.4)",
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      </section>

      {/* ── 모델 성격 해설 ───────────── */}
      <ModelCharacterBlurb data={data} locale={locale} />

      {/* ── 전체 메트릭 ──────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader
          en={t.sections.overall.en}
          ko={t.sections.overall.ko}
          accent="#4ADE80"
        />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label={t.metrics.hitDir.label}
            value={`${Math.round(o.hitRate3 * 100)}%`}
            hint={t.metrics.hitDir.hint(data.totalRows)}
            accent="#4ADE80"
          />
          <MetricCard
            label={t.metrics.balAcc.label}
            value={o.balancedAccuracy.toFixed(3)}
            hint={t.metrics.balAcc.hint}
            accent="#A78BFA"
          />
          <MetricCard
            label={t.metrics.hit5.label}
            value={`${Math.round(o.hitRate5 * 100)}%`}
            hint={t.metrics.hit5.hint}
            accent="#7DD3FC"
          />
          <MetricCard
            label={t.metrics.top3.label}
            value={`${Math.round(data.topK.nerfPrecisionTop3PerAct * 100)}%`}
            hint={t.metrics.top3.hint}
            accent="#FF4655"
          />
        </div>

        {/* 클래스별 P/R */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(["stable", "buff", "nerf"] as const).map((c) => {
            const m = o.classes[c];
            const color = DIR_COLOR[c];
            return (
              <div
                key={c}
                className="p-5"
                style={{ border: `1px solid ${color}44`, background: `${color}0A` }}
              >
                <div className="flex items-center justify-between mb-4">
                  <span
                    className="text-[13px] uppercase tracking-[0.25em] font-valo font-bold"
                    style={{ color }}
                  >
                    {c}
                  </span>
                  <span
                    className="text-[12px] font-mono"
                    style={{ color: "rgba(148,163,184,0.85)" }}
                  >
                    n={m.support}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Stat label="Precision" value={m.precision} />
                  <Stat label="Recall" value={m.recall} />
                  <Stat label="F1" value={m.f1} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── 요원별 적중 Top / Worst ──────────────────────────────────── */}
      {data.topAgents && (data.topAgents.hits.length > 0 || data.topAgents.misses.length > 0) && (
        <section className="space-y-5">
          <SectionHeader
            en={t.sections.topAgents.en}
            ko={t.sections.topAgents.ko}
            accent="#FBBF24"
          />
          <p
            className="text-[13px] leading-relaxed max-w-2xl"
            style={{ color: "rgba(203,213,225,0.9)" }}
          >
            {t.blurbs.topAgents}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <TopAgentsCard
              title={locale === "en" ? "Top hits" : "가장 잘 맞힌 요원 TOP 5"}
              rows={data.topAgents.hits}
              accent="#4ADE80"
              positive
            />
            <TopAgentsCard
              title={locale === "en" ? "Top misses" : "가장 자주 빗나간 요원 TOP 5"}
              rows={data.topAgents.misses}
              accent="#FF4655"
              positive={false}
            />
          </div>
        </section>
      )}

      {/* ── Confusion Matrix ─────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader
          en={t.sections.confusion.en}
          ko={t.sections.confusion.ko}
          accent="#A78BFA"
        />
        <ConfusionMatrix
          matrix={o.confusionMatrix}
          labels={o.confusionLabels}
          colHeader={t.confusion.colHeader}
          rowPrefix={t.confusion.rowPrefix}
          caption={t.confusion.caption}
        />
      </section>

      {/* ── 고확신 임계값 ────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader
          en={t.sections.threshold.en}
          ko={t.sections.threshold.ko}
          accent="#7DD3FC"
        />
        <p
          className="text-[13px] leading-relaxed max-w-2xl"
          style={{ color: "rgba(203,213,225,0.9)" }}
        >
          {t.blurbs.threshold}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ThresholdTable
            title={t.threshold.tableTitleNerf}
            rows={data.highConf.nerf}
            accent="#FF4655"
            cols={t.threshold}
          />
          <ThresholdTable
            title={t.threshold.tableTitleBuff}
            rows={data.highConf.buff}
            accent="#4FC3F7"
            cols={t.threshold}
          />
        </div>
      </section>

      {/* ── 스토리: 선행 적중 ────────────────────────────────────────── */}
      {data.stories.leadHits.length > 0 && (
        <section className="space-y-5">
          <SectionHeader
            en={t.sections.leadHits.en}
            ko={t.sections.leadHits.ko}
            accent="#4ADE80"
          />
          <p
            className="text-[13px] leading-relaxed max-w-2xl"
            style={{ color: "rgba(203,213,225,0.9)" }}
            dangerouslySetInnerHTML={{
              __html: t.blurbs.leadHits.replace(
                /\*\*(.*?)\*\*/g,
                '<span class="font-bold text-white">$1</span>',
              ),
            }}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.stories.leadHits.map((s, i) => (
              <div
                key={i}
                className="p-5 space-y-3"
                style={{
                  border: "1px solid rgba(74,222,128,0.35)",
                  background: "rgba(16,185,129,0.06)",
                }}
              >
                <div className="flex items-baseline justify-between">
                  <span
                    className="text-2xl font-extrabold tracking-tight"
                    style={{ color: "#e2e8f0" }}
                  >
                    {s.agent}
                  </span>
                  <span
                    className="text-[12px] font-mono font-bold"
                    style={{ color: "rgba(74,222,128,0.95)" }}
                  >
                    p_nerf {(s.pNerf * 100).toFixed(1)}%
                  </span>
                </div>
                <div
                  className="flex items-center gap-2 text-[14px]"
                  style={{ color: "rgba(203,213,225,0.9)" }}
                >
                  <span className="flex flex-col gap-0.5">
                    <span className="font-mono font-bold text-white">{s.predictedAt}</span>
                    <span
                      className="text-[11px] uppercase tracking-wider"
                      style={{ color: DIR_COLOR.stable }}
                    >
                      {verdictLabel(s.truthAtPred)}
                    </span>
                  </span>
                  <span className="text-2xl" style={{ color: "#4ADE80" }}>
                    →
                  </span>
                  <span className="flex flex-col gap-0.5">
                    <span className="font-mono font-bold text-white">{s.hitAt}</span>
                    <span
                      className="text-[11px] uppercase tracking-wider"
                      style={{ color: DIR_COLOR.nerf }}
                    >
                      {verdictLabel(s.truthAtHit)}
                    </span>
                  </span>
                </div>
                <div
                  className="text-[12px] leading-snug"
                  style={{ color: "rgba(148,163,184,0.9)" }}
                >
                  {t.blurbs.leadHitNarrative(s.predictedAt, s.hitAt)}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 큰 적중 / 큰 오답 ────────────────────────────────────────── */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StoryBlock
          en={t.sections.bigHits.en}
          ko={t.sections.bigHits.ko}
          accent="#4ADE80"
          rows={data.stories.bigHits}
          blurb={t.blurbs.bigHits}
          predictedLabel={t.story.predictedLabel}
          truthLabel={t.story.truthLabel}
          verdictLabel={verdictLabel}
        />
        <StoryBlock
          en={t.sections.bigMisses.en}
          ko={t.sections.bigMisses.ko}
          accent="#FF4655"
          rows={data.stories.bigMisses}
          blurb={t.blurbs.bigMisses}
          predictedLabel={t.story.predictedLabel}
          truthLabel={t.story.truthLabel}
          verdictLabel={verdictLabel}
        />
      </section>

      {/* ── 액트별 적중률 추이 ───────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en={t.sections.perAct.en} ko={t.sections.perAct.ko} accent="#FBBF24" />
        <p
          className="text-[13px] leading-relaxed max-w-2xl"
          style={{ color: "rgba(203,213,225,0.9)" }}
        >
          {t.blurbs.perAct}
        </p>
        <PerActLineChart
          perAct={data.perAct}
          legend3={t.perAct.legend3}
          legend5={t.perAct.legend5}
          legendAvg={t.perAct.legendAvg}
        />
        <PerActChart perAct={data.perAct} footer={t.perAct.footer} />
      </section>

      {/* ── 전체 예측 테이블 ─────────────────────────────────────────── */}
      <section className="space-y-4">
        {(() => {
          const sec = t.sections.predictionTable(data.totalRows);
          return <SectionHeader en={sec.en} ko={sec.ko} accent="#CBD5E1" />;
        })()}
        <BacktestPredictionTable rows={data.predictions} acts={data.acts} locale={locale} />
      </section>

      {/* ── 메서돌로지 ────────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader en={t.sections.methodology.en} accent="#94A3B8" />
        <div
          className="p-6 text-[13px] leading-relaxed space-y-4"
          style={{
            border: "1px solid rgba(51,65,85,0.6)",
            background: "rgba(13,18,32,0.5)",
            color: "rgba(226,232,240,0.92)",
          }}
        >
          <Bullet>
            <strong>{t.methodology.walkforward.title}</strong>{" "}
            <span dangerouslySetInnerHTML={{ __html: renderInlineCode(t.methodology.walkforward.body) }} />
          </Bullet>
          <Bullet>
            <strong>{t.methodology.twoStage.title}</strong>{" "}
            <span dangerouslySetInnerHTML={{ __html: renderInlineCode(t.methodology.twoStage.body) }} />
          </Bullet>
          <Bullet>
            <strong>{t.methodology.groundTruth.title}</strong> {t.methodology.groundTruth.body}
          </Bullet>
          <Bullet>
            <strong>{t.methodology.scope.title}</strong> {t.methodology.scope.body}
          </Bullet>
          <Bullet>
            <strong>{t.methodology.generated}</strong>{" "}
            <span className="font-mono text-white">
              {new Date(data.generatedAt).toISOString().slice(0, 19).replace("T", " ")}
            </span>{" "}
            (UTC)
          </Bullet>
        </div>
      </section>
    </div>
  );
}

/** `code` markdown → <code> tag (안전한 단순 변환). */
function renderInlineCode(s: string): string {
  return s.replace(/`([^`]+)`/g, '<code class="font-mono text-white mx-1">$1</code>');
}

/* ─── Sub-components ──────────────────────────────────────────────── */

function SectionHeader({
  en,
  ko,
  accent,
}: {
  en: string;
  ko?: string;
  accent: string;
}) {
  return (
    <div className="flex items-baseline gap-3 flex-wrap">
      <div style={{ width: "3px", height: "30px", background: accent }} />
      {ko ? (
        <>
          <span
            className="text-[12px] font-valo tracking-[0.25em]"
            style={{ color: `${accent}CC` }}
          >
            {en}
          </span>
          <span className="font-valo font-bold text-xl sm:text-2xl" style={{ color: accent }}>
            {ko}
          </span>
        </>
      ) : (
        <span
          className="font-valo font-bold text-xl sm:text-2xl tracking-wide"
          style={{ color: accent }}
        >
          {en}
        </span>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  accent: string;
}) {
  return (
    <div className="p-5" style={{ border: `1px solid ${accent}44`, background: `${accent}08` }}>
      <div
        className="text-[12px] uppercase tracking-[0.2em] mb-2"
        style={{ color: "rgba(148,163,184,0.85)" }}
      >
        {label}
      </div>
      <div className="text-4xl font-num font-bold tabular-nums leading-none" style={{ color: accent }}>
        {value}
      </div>
      {hint && (
        <div className="text-[11px] mt-2" style={{ color: "rgba(148,163,184,0.75)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div
        className="text-[11px] uppercase tracking-widest mb-1"
        style={{ color: "rgba(148,163,184,0.75)" }}
      >
        {label}
      </div>
      <div className="text-xl font-num font-bold tabular-nums" style={{ color: "#e2e8f0" }}>
        {value.toFixed(2)}
      </div>
    </div>
  );
}

function ConfusionMatrix({
  matrix,
  labels,
  colHeader,
  rowPrefix,
  caption,
}: {
  matrix: number[][];
  labels: string[];
  colHeader: string;
  rowPrefix: string;
  caption: string;
}) {
  const max = Math.max(...matrix.flat(), 1);

  return (
    <div
      className="p-6 overflow-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      <table className="text-[14px] font-num tabular-nums mx-auto">
        <thead>
          <tr>
            <th className="px-3 py-2"></th>
            <th
              className="px-3 py-2 text-[12px] uppercase tracking-widest"
              colSpan={labels.length}
              style={{ color: "rgba(148,163,184,0.85)" }}
            >
              {colHeader}
            </th>
          </tr>
          <tr>
            <th className="px-3 py-2"></th>
            {labels.map((l) => (
              <th
                key={l}
                className="px-4 py-2 uppercase tracking-widest text-[13px] font-bold"
                style={{ color: DIR_COLOR[l as keyof typeof DIR_COLOR] ?? "#94A3B8" }}
              >
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <th
                className="pl-3 pr-4 py-3 text-left uppercase tracking-widest text-[13px] font-bold"
                style={{ color: DIR_COLOR[labels[i] as keyof typeof DIR_COLOR] ?? "#94A3B8" }}
              >
                <span style={{ color: "rgba(148,163,184,0.7)" }} className="mr-1.5 text-[11px]">
                  {rowPrefix}
                </span>
                {labels[i]}
              </th>
              {row.map((v, j) => {
                const intensity = v / max;
                const isDiag = i === j;
                const bgBase = isDiag ? "74,222,128" : "148,163,184";
                return (
                  <td
                    key={j}
                    className="px-5 py-3.5 text-center font-bold text-xl"
                    style={{
                      background: `rgba(${bgBase},${0.05 + intensity * 0.4})`,
                      color: isDiag ? "#4ADE80" : "#e2e8f0",
                      border: "1px solid rgba(30,41,59,0.6)",
                      minWidth: "88px",
                    }}
                  >
                    {v}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div
        className="text-[13px] text-center mt-4"
        style={{ color: "rgba(148,163,184,0.85)" }}
      >
        {caption}
      </div>
    </div>
  );
}

function ThresholdTable({
  title,
  rows,
  accent,
  cols,
}: {
  title: string;
  rows: { threshold: number; n: number; precision: number }[];
  accent: string;
  cols: { colThreshold: string; colSamples: string; colPrecision: string };
}) {
  return (
    <div style={{ border: `1px solid ${accent}44`, background: `${accent}08` }}>
      <div
        className="px-5 py-3 text-[14px] uppercase tracking-[0.25em] font-bold"
        style={{ color: accent, borderBottom: `1px solid ${accent}33` }}
      >
        {title}
      </div>
      <table className="w-full text-[14px] font-num tabular-nums">
        <thead>
          <tr
            className="text-[11px] uppercase tracking-widest"
            style={{ color: "rgba(148,163,184,0.8)" }}
          >
            <th className="px-5 py-3 text-left">{cols.colThreshold}</th>
            <th className="px-5 py-3 text-right">{cols.colSamples}</th>
            <th className="px-5 py-3 text-right">{cols.colPrecision}</th>
            <th className="px-5 py-3 w-1/2"> </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const pct = Math.round(r.precision * 100);
            return (
              <tr key={r.threshold} style={{ borderTop: "1px solid rgba(30,41,59,0.4)" }}>
                <td className="px-5 py-3 font-bold" style={{ color: "#e2e8f0" }}>
                  ≥ {r.threshold.toFixed(2)}
                </td>
                <td className="px-5 py-3 text-right" style={{ color: "rgba(203,213,225,0.9)" }}>
                  {r.n}
                </td>
                <td className="px-5 py-3 text-right font-bold text-lg" style={{ color: accent }}>
                  {pct}%
                </td>
                <td className="px-5 py-3">
                  <div style={{ background: `${accent}22`, height: "14px" }}>
                    <div
                      style={{
                        background: accent,
                        height: "100%",
                        width: `${pct}%`,
                        transition: "width 0.3s",
                      }}
                    />
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StoryBlock({
  en,
  ko,
  accent,
  rows,
  blurb,
  predictedLabel,
  truthLabel,
  verdictLabel,
}: {
  en: string;
  ko: string;
  accent: string;
  rows: {
    agent: string;
    act: string;
    predicted: string;
    truth: string;
    pNerf?: number;
    pBuff?: number;
  }[];
  blurb: string;
  predictedLabel: string;
  truthLabel: string;
  verdictLabel: (k: string) => string;
}) {
  if (rows.length === 0) return null;
  return (
    <div className="space-y-4">
      <SectionHeader en={en} ko={ko} accent={accent} />
      <p
        className="text-[13px] leading-relaxed max-w-lg"
        style={{ color: "rgba(203,213,225,0.9)" }}
      >
        {blurb}
      </p>
      <div className="space-y-3">
        {rows.map((s, i) => {
          const p = s.pNerf ?? s.pBuff ?? 0;
          const pLabel = s.pNerf !== undefined ? "p_nerf" : "p_buff";
          return (
            <div
              key={i}
              className="p-4 flex items-center justify-between gap-4"
              style={{ border: `1px solid ${accent}33`, background: `${accent}06` }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span
                    className="text-xl font-extrabold tracking-tight"
                    style={{ color: "#e2e8f0" }}
                  >
                    {s.agent}
                  </span>
                  <span
                    className="text-[12px] font-mono font-bold"
                    style={{ color: "rgba(148,163,184,0.9)" }}
                  >
                    {s.act}
                  </span>
                </div>
                <div className="text-[13px] mt-1.5" style={{ color: "rgba(203,213,225,0.9)" }}>
                  {predictedLabel}{" "}
                  <span className="font-bold" style={{ color: accent }}>
                    {verdictLabel(s.predicted)}
                  </span>{" "}
                  · {truthLabel}{" "}
                  <span className="font-bold text-white">{verdictLabel(s.truth)}</span>
                </div>
              </div>
              <div
                className="text-right font-num font-bold text-xl tabular-nums shrink-0"
                style={{ color: accent }}
              >
                {Math.round(p * 100)}%
                <div
                  className="text-[10px] uppercase tracking-widest font-normal mt-0.5"
                  style={{ color: "rgba(148,163,184,0.75)" }}
                >
                  {pLabel}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PerActChart({
  perAct,
  footer,
}: {
  perAct: { act: string; act_idx: number; n: number; hit_dir: number; hit_5: number }[];
  footer: (avg: number) => string;
}) {
  const avg = perAct.reduce((s, r) => s + r.hit_dir, 0) / Math.max(perAct.length, 1);

  return (
    <div
      className="p-6 space-y-3 overflow-x-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      {perAct.map((r) => {
        const pct3 = Math.round(r.hit_dir * 100);
        const pct5 = Math.round(r.hit_5 * 100);
        return (
          <div
            key={r.act}
            className="grid grid-cols-[88px_1fr_150px] items-center gap-4 text-[14px]"
          >
            <div className="font-mono font-bold text-[15px]" style={{ color: "#cbd5e1" }}>
              {r.act}
            </div>
            <div style={{ background: "rgba(30,41,59,0.5)", height: "26px", position: "relative" }}>
              <div
                style={{
                  background: "#4ADE80",
                  height: "100%",
                  width: `${pct3}%`,
                  transition: "width 0.3s",
                }}
              />
              <div
                className="absolute top-0 bottom-0"
                style={{
                  left: `${Math.round(avg * 100)}%`,
                  width: "2px",
                  background: "rgba(148,163,184,0.6)",
                }}
                title={`avg ${Math.round(avg * 100)}%`}
              />
            </div>
            <div className="text-right font-num tabular-nums" style={{ color: "#e2e8f0" }}>
              <span className="font-bold text-base">{pct3}%</span>{" "}
              <span className="text-[12px]" style={{ color: "rgba(100,116,139,0.85)" }}>
                · 5c {pct5}%
              </span>
            </div>
          </div>
        );
      })}
      <div className="text-[12px] pt-3" style={{ color: "rgba(100,116,139,0.9)" }}>
        {footer(Math.round(avg * 100))}
      </div>
    </div>
  );
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span style={{ color: "#A78BFA" }}>▸</span>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function HeroStat({
  label,
  value,
  sub,
  accent,
  baseline,
}: {
  label: string;
  value: string;
  sub: string;
  accent: string;
  baseline?: string;
}) {
  return (
    <div className="space-y-2">
      <div
        className="text-[11px] sm:text-[12px] uppercase tracking-[0.25em] font-bold"
        style={{ color: "rgba(148,163,184,0.9)" }}
      >
        {label}
      </div>
      <div
        className="font-num font-bold tabular-nums leading-none"
        style={{ color: accent, fontSize: "clamp(40px, 7vw, 64px)" }}
      >
        {value}
      </div>
      <div className="text-[12px] leading-snug" style={{ color: "rgba(203,213,225,0.9)" }}>
        {sub}
      </div>
      {baseline && (
        <div
          className="text-[10.5px] leading-snug tracking-wide pt-1"
          style={{ color: "rgba(148,163,184,0.7)", borderTop: "1px dashed rgba(71,85,105,0.5)" }}
        >
          {baseline}
        </div>
      )}
    </div>
  );
}

function TopAgentsCard({
  title,
  rows,
  accent,
  positive,
}: {
  title: string;
  rows: BacktestAgentRow[];
  accent: string;
  positive: boolean;
}) {
  if (!rows.length) return null;
  return (
    <div className="p-5 space-y-3" style={{ border: `1px solid ${accent}44`, background: `${accent}08` }}>
      <div
        className="text-[12px] uppercase tracking-[0.25em] font-bold pb-2"
        style={{ color: accent, borderBottom: `1px solid ${accent}33` }}
      >
        {title}
      </div>
      <div className="space-y-2">
        {rows.map((r, i) => {
          const pct = Math.round(r.hitRate * 100);
          return (
            <div
              key={r.agent}
              className="grid grid-cols-[24px_1fr_auto] items-center gap-3 py-1.5"
              style={{ borderTop: i === 0 ? "none" : "1px solid rgba(30,41,59,0.4)" }}
            >
              <span
                className="text-[13px] font-mono font-bold tabular-nums"
                style={{ color: "rgba(100,116,139,0.85)" }}
              >
                {i + 1}
              </span>
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="text-base font-extrabold tracking-tight truncate"
                  style={{ color: "#e2e8f0" }}
                >
                  {r.agent}
                </span>
                <span
                  className="text-[11px] font-mono"
                  style={{ color: "rgba(148,163,184,0.75)" }}
                >
                  {r.hits}/{r.n}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-24 sm:w-32" style={{ background: `${accent}15`, height: "8px" }}>
                  <div
                    style={{
                      background: accent,
                      height: "100%",
                      width: positive ? `${pct}%` : `${100 - pct}%`,
                      transition: "width 0.3s",
                    }}
                  />
                </div>
                <span
                  className="font-num font-bold tabular-nums text-base w-12 text-right"
                  style={{ color: accent }}
                >
                  {pct}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PerActLineChart({
  perAct,
  legend3,
  legend5,
  legendAvg,
}: {
  perAct: { act: string; act_idx: number; n: number; hit_dir: number; hit_5: number }[];
  legend3: string;
  legend5: string;
  legendAvg: (avg: number) => string;
}) {
  if (perAct.length < 2) return null;

  const W = 800;
  const H = 240;
  const padL = 52;
  const padR = 20;
  const padT = 20;
  const padB = 50;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const n = perAct.length;
  const avg = perAct.reduce((s, r) => s + r.hit_dir, 0) / n;

  const xOf = (i: number) => padL + (i * innerW) / Math.max(n - 1, 1);
  const yOf = (v: number) => padT + innerH - v * innerH;

  const buildPath = (key: "hit_dir" | "hit_5") =>
    perAct
      .map((r, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(r[key]).toFixed(1)}`)
      .join(" ");

  const d3 = buildPath("hit_dir");
  const d5 = buildPath("hit_5");
  const avgY = yOf(avg);
  const labelStep = Math.max(1, Math.ceil(n / 9));

  return (
    <div
      className="p-4 sm:p-6 overflow-x-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      <div className="flex flex-wrap items-center gap-4 mb-3 text-[12px] font-mono">
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5" style={{ background: "#4ADE80" }} />
          <span style={{ color: "#e2e8f0" }}>{legend3}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5" style={{ background: "#7DD3FC" }} />
          <span style={{ color: "rgba(203,213,225,0.9)" }}>{legend5}</span>
        </span>
        <span className="flex items-center gap-2">
          <span
            className="inline-block w-4 h-px border-t border-dashed"
            style={{ borderColor: "rgba(148,163,184,0.7)" }}
          />
          <span style={{ color: "rgba(148,163,184,0.85)" }}>
            {legendAvg(Math.round(avg * 100))}
          </span>
        </span>
      </div>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: "600px" }}>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={padL} x2={W - padR} y1={yOf(v)} y2={yOf(v)} stroke="rgba(51,65,85,0.35)" strokeWidth={1} />
            <text
              x={padL - 8}
              y={yOf(v)}
              fontSize="12"
              fill="rgba(148,163,184,0.8)"
              textAnchor="end"
              dominantBaseline="middle"
              fontFamily="ui-monospace, monospace"
            >
              {Math.round(v * 100)}%
            </text>
          </g>
        ))}

        <line
          x1={padL}
          x2={W - padR}
          y1={avgY}
          y2={avgY}
          stroke="rgba(148,163,184,0.7)"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        <path d={d5} fill="none" stroke="#7DD3FC" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" opacity={0.75} />
        <path
          d={d3}
          fill="none"
          stroke="#4ADE80"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: "drop-shadow(0 0 3px #4ADE8055)" }}
        />

        {perAct.map((r, i) => (
          <g key={r.act}>
            <circle cx={xOf(i)} cy={yOf(r.hit_dir)} r={3.5} fill="#4ADE80" />
            <title>{`${r.act}: ${Math.round(r.hit_dir * 100)}% (n=${r.n})`}</title>
          </g>
        ))}

        {perAct.map((r, i) => {
          if (i % labelStep !== 0 && i !== n - 1) return null;
          return (
            <text
              key={r.act}
              x={xOf(i)}
              y={H - padB + 18}
              fontSize="11"
              fill="rgba(148,163,184,0.85)"
              textAnchor="middle"
              fontFamily="ui-monospace, monospace"
            >
              {r.act}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
