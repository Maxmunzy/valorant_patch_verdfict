import Link from "next/link";
import { getBacktestSummary } from "@/lib/backtest";
import BackToHome from "@/components/BackToHome";

// 영문 축약 백테스트 리포트 — Reddit/트위터 유입용.
// 전체 요원별 예측 테이블/스토리는 /backtest (한국어) 로 연결.
export const revalidate = 3600;

export const metadata = {
  title: "Backtest Report // WHO'S NEXT?",
  description:
    "Walk-forward backtest of a Valorant patch-prediction model. Transparent methodology, per-act accuracy, high-confidence threshold calibration.",
};

const DIR_COLOR = { stable: "#94A3B8", buff: "#4FC3F7", nerf: "#FF4655" } as const;

export default async function BacktestEn() {
  const data = await getBacktestSummary();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <div className="text-sm" style={{ color: "rgba(148,163,184,0.8)" }}>
          Could not load backtest data.
        </div>
        <div className="inline-block mt-4">
          <BackToHome locale="en" />
        </div>
      </div>
    );
  }

  const o = data.overall;
  const totalSupport = Object.values(o.classes).reduce((a, c) => a + c.support, 0) || 1;
  const majorityClass = (Object.entries(o.classes) as [string, { support: number }][]).reduce(
    (best, cur) => (cur[1].support > best[1].support ? cur : best),
  );
  const majorityPct = Math.round((majorityClass[1].support / totalSupport) * 100);
  const hitPct = Math.round(o.hitRate3 * 100);
  const liftVsRandom = hitPct - 33;
  const liftVsMajority = hitPct - majorityPct;

  const highConfNerf60 =
    data.highConf.nerf.find((r) => Math.abs(r.threshold - 0.6) < 0.01)?.precision ?? 0;
  const highConfBuff60 =
    data.highConf.buff.find((r) => Math.abs(r.threshold - 0.6) < 0.01)?.precision ?? 0;

  return (
    <div className="py-10 space-y-10">
      {/* ── header ──────────────────────────────────────────── */}
      <div className="space-y-5">
        <BackToHome />

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
              className="text-[11px] tracking-[0.3em] mb-2"
              style={{ color: "rgba(148,163,184,0.75)" }}
            >
              WALK-FORWARD BACKTEST · HISTORICAL SCORECARD
            </div>
            <h1 className="text-4xl sm:text-5xl font-black tracking-wide leading-[0.95] text-white">
              Prediction <span style={{ color: "#4ADE80" }}>Accuracy</span> Report
            </h1>
          </div>
        </div>

        <p className="text-[13px] leading-relaxed max-w-3xl pl-2" style={{ color: "rgba(203,213,225,0.9)" }}>
          For every act, the model is retrained{" "}
          <span className="font-bold text-white">from scratch using only data available at that point</span>,
          then asked to predict that act. No future information leaks into past evaluation — only predictions
          the model could realistically have made in real time are scored.
        </p>
      </div>

      {/* ── Hero stats ─────────────────────────────────────────── */}
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
          TL;DR
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8">
          <HeroStat
            label="Direction hit rate"
            value={`${hitPct}%`}
            sub={`Share of ${data.totalRows} predictions where nerf/buff/stable direction was correct.`}
            accent="#4ADE80"
            baseline={`Random baseline 33% · Always-stable baseline ${majorityPct}%. Lift: +${liftVsRandom}pp / ${liftVsMajority >= 0 ? "+" : ""}${liftVsMajority}pp.`}
          />
          <HeroStat
            label="High-conf nerf precision"
            value={`${Math.round(highConfNerf60 * 100)}%`}
            sub="Of predictions made at p_nerf ≥ 0.60, how many turned into actual nerfs."
            accent="#FF4655"
          />
          <HeroStat
            label="Evaluation coverage"
            value={`${data.acts.length} ACTS`}
            sub={`${data.actRange.first} → ${data.actRange.last} · ${data.totalRows} predictions total.`}
            accent="#7DD3FC"
          />
        </div>
        <div
          className="flex flex-wrap gap-2 mt-6 pt-5"
          style={{ borderTop: "1px solid rgba(51,65,85,0.5)" }}
        >
          {[
            `${data.totalRows} prediction samples`,
            `Range: ${data.actRange.first} → ${data.actRange.last}`,
            `${data.acts.length} act folds`,
            "Method: walk-forward",
          ].map((t) => (
            <span
              key={t}
              className="text-[11px] px-2.5 py-1.5 uppercase tracking-wider font-mono"
              style={{
                border: "1px solid rgba(51,65,85,0.55)",
                color: "rgba(148,163,184,0.85)",
                background: "rgba(13,18,32,0.4)",
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </section>

      {/* ── Overall metrics ────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader title="Overall metrics" accent="#4ADE80" />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="Direction hit rate"
            value={`${Math.round(o.hitRate3 * 100)}%`}
            hint={`Across ${data.totalRows} predictions.`}
            accent="#4ADE80"
          />
          <MetricCard
            label="Balanced accuracy"
            value={o.balancedAccuracy.toFixed(3)}
            hint="Class-imbalance corrected."
            accent="#A78BFA"
          />
          <MetricCard
            label="5-class hit rate"
            value={`${Math.round(o.hitRate5 * 100)}%`}
            hint="Mild/strong intensity also correct."
            accent="#7DD3FC"
          />
          <MetricCard
            label="Top-3 nerf / act"
            value={`${Math.round(data.topK.nerfPrecisionTop3PerAct * 100)}%`}
            hint="Actual nerfs among top-3 nerf picks per act."
            accent="#FF4655"
          />
        </div>

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
                    className="text-[13px] uppercase tracking-[0.25em] font-bold"
                    style={{ color }}
                  >
                    {c}
                  </span>
                  <span className="text-[12px] font-mono" style={{ color: "rgba(148,163,184,0.85)" }}>
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

      {/* ── Per-act line chart ────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader title="Per-act accuracy trend" accent="#FBBF24" />
        <p className="text-[13px] leading-relaxed max-w-2xl" style={{ color: "rgba(203,213,225,0.9)" }}>
          As more acts accumulate, training data grows. The chart below checks whether hit rate stabilizes
          over time — a sanity check against early overfitting.
        </p>
        <PerActLineChart perAct={data.perAct} />
      </section>

      {/* ── Threshold tables ──────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader title="Confidence calibration" accent="#7DD3FC" />
        <p className="text-[13px] leading-relaxed max-w-2xl" style={{ color: "rgba(203,213,225,0.9)" }}>
          Higher probability outputs should correlate with higher real-world hit rate. Each row: share of
          predictions at that probability threshold that matched reality.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ThresholdTable title="Nerf predictions" rows={data.highConf.nerf} accent="#FF4655" />
          <ThresholdTable title="Buff predictions" rows={data.highConf.buff} accent="#4FC3F7" />
        </div>
        <p className="text-[11.5px] pt-1" style={{ color: "rgba(148,163,184,0.7)" }}>
          Buff precision at p ≥ 0.60: {Math.round(highConfBuff60 * 100)}%.
        </p>
      </section>

      {/* ── Methodology ───────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader title="Methodology" accent="#94A3B8" />
        <div
          className="p-6 text-[13px] leading-relaxed space-y-4"
          style={{
            border: "1px solid rgba(51,65,85,0.6)",
            background: "rgba(13,18,32,0.5)",
            color: "rgba(226,232,240,0.92)",
          }}
        >
          <Bullet>
            <strong>Walk-forward</strong> — each fold trains on{" "}
            <code className="font-mono text-white mx-1">act_idx &lt; T</code> and predicts{" "}
            <code className="font-mono text-white mx-1">act_idx == T</code>. Future information never leaks
            into past evaluation.
          </Bullet>
          <Bullet>
            <strong>Two-stage model</strong> — Stage A (XGBoost) classifies{" "}
            <em>touched next patch vs. stable</em>. Stage B (Logistic Regression) splits touched → nerf vs.
            buff. Final output: 5 classes (strong/mild nerf · stable · mild/strong buff).
          </Bullet>
          <Bullet>
            <strong>Ground truth</strong> — labels come from actual post-patch nerf/buff history, including
            mid-patch hotfixes and reworks.
          </Bullet>
          <Bullet>
            <strong>Evaluation scope</strong> — only acts with confirmed patch outcomes (current in-flight
            act V26A2 is excluded).
          </Bullet>
          <Bullet>
            <strong>Generated at</strong>{" "}
            <span className="font-mono text-white">
              {new Date(data.generatedAt).toISOString().slice(0, 19).replace("T", " ")}
            </span>{" "}
            (UTC).
          </Bullet>
        </div>
      </section>

      {/* ── Links ─────────────────────────────────────────────── */}
      <section className="flex flex-wrap gap-3 pt-4">
        <Link
          href="/en"
          className="text-[12px] font-bold tracking-[0.25em] uppercase px-4 py-2.5"
          style={{
            border: "1px solid rgba(74,222,128,0.5)",
            color: "#4ADE80",
            background: "rgba(74,222,128,0.06)",
          }}
        >
          ← Back to home
        </Link>
        <Link
          href="/backtest"
          className="text-[12px] font-bold tracking-[0.25em] uppercase px-4 py-2.5"
          style={{
            border: "1px solid rgba(148,163,184,0.5)",
            color: "#cbd5e1",
            background: "rgba(51,65,85,0.25)",
          }}
        >
          Full report (KO) · per-agent tables ▸
        </Link>
      </section>
    </div>
  );
}

/* ------------------------- sub components ------------------------- */

function SectionHeader({ title, accent }: { title: string; accent: string }) {
  return (
    <div className="flex items-baseline gap-3 flex-wrap">
      <div style={{ width: "3px", height: "30px", background: accent }} />
      <span className="font-bold text-xl sm:text-2xl tracking-wide" style={{ color: accent }}>
        {title}
      </span>
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
        className="font-bold tabular-nums leading-none"
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
      <div className="text-[12px] uppercase tracking-[0.2em] mb-2" style={{ color: "rgba(148,163,184,0.85)" }}>
        {label}
      </div>
      <div className="text-4xl font-bold tabular-nums leading-none" style={{ color: accent }}>
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
      <div className="text-[11px] uppercase tracking-widest mb-1" style={{ color: "rgba(148,163,184,0.75)" }}>
        {label}
      </div>
      <div className="text-xl font-bold tabular-nums" style={{ color: "#e2e8f0" }}>
        {value.toFixed(2)}
      </div>
    </div>
  );
}

function ThresholdTable({
  title,
  rows,
  accent,
}: {
  title: string;
  rows: { threshold: number; n: number; precision: number }[];
  accent: string;
}) {
  return (
    <div style={{ border: `1px solid ${accent}44`, background: `${accent}08` }}>
      <div
        className="px-5 py-3 text-[14px] uppercase tracking-[0.25em] font-bold"
        style={{ color: accent, borderBottom: `1px solid ${accent}33` }}
      >
        {title}
      </div>
      <table className="w-full text-[14px] tabular-nums">
        <thead>
          <tr className="text-[11px] uppercase tracking-widest" style={{ color: "rgba(148,163,184,0.8)" }}>
            <th className="px-5 py-3 text-left">Threshold</th>
            <th className="px-5 py-3 text-right">n</th>
            <th className="px-5 py-3 text-right">Precision</th>
            <th className="px-5 py-3 w-1/2"></th>
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
                      style={{ background: accent, height: "100%", width: `${pct}%`, transition: "width 0.3s" }}
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

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <span style={{ color: "#A78BFA" }}>▸</span>
      <div className="flex-1">{children}</div>
    </div>
  );
}

function PerActLineChart({
  perAct,
}: {
  perAct: { act: string; act_idx: number; n: number; hit_dir: number; hit_5: number }[];
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
          <span style={{ color: "#e2e8f0" }}>Direction hit rate</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5" style={{ background: "#7DD3FC" }} />
          <span style={{ color: "rgba(203,213,225,0.9)" }}>5-class hit rate</span>
        </span>
        <span className="flex items-center gap-2">
          <span
            className="inline-block w-4 h-px border-t border-dashed"
            style={{ borderColor: "rgba(148,163,184,0.7)" }}
          />
          <span style={{ color: "rgba(148,163,184,0.85)" }}>Avg {Math.round(avg * 100)}%</span>
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
