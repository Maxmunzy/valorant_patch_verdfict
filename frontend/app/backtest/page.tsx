import Link from "next/link";
import { getBacktestSummary } from "@/lib/backtest";
import BacktestPredictionTable from "@/components/backtest/BacktestPredictionTable";

// 백테스트 요약은 정적 JSON — 1시간마다 재검증
export const revalidate = 3600;

// ─── 색상/라벨 유틸 ────────────────────────────────────────────────────────
const DIR_COLOR = { stable: "#94A3B8", buff: "#4FC3F7", nerf: "#FF4655" } as const;
const LABEL_KO: Record<string, string> = {
  stable:      "안정",
  mild_buff:   "약한 버프",
  strong_buff: "강한 버프",
  mild_nerf:   "약한 너프",
  strong_nerf: "강한 너프",
};

// ─── 메인 ──────────────────────────────────────────────────────────────────
export default async function BacktestPage() {
  const data = await getBacktestSummary();

  if (!data) {
    return (
      <div className="py-20 text-center">
        <div className="text-sm" style={{ color: "rgba(148,163,184,0.8)" }}>
          백테스트 데이터를 불러오지 못했습니다.
        </div>
        <Link href="/" className="inline-block mt-4 text-[11px] underline" style={{ color: "#A78BFA" }}>
          ← 홈으로
        </Link>
      </div>
    );
  }

  const o = data.overall;

  return (
    <div className="py-10 space-y-10">
      {/* ── 헤더 ─────────────────────────────────────────────────────── */}
      <div className="space-y-4">
        <Link
          href="/"
          className="inline-block text-[10px] uppercase tracking-widest transition-colors hover:text-white"
          style={{ color: "rgba(148,163,184,0.7)" }}
        >
          ← HOME
        </Link>

        <div className="flex items-start gap-4">
          <div
            className="shrink-0 mt-2"
            style={{
              width: "2px",
              height: "60px",
              background: "linear-gradient(to bottom, #4ADE80, #4ADE8030)",
            }}
          />
          <div>
            <div
              className="text-[9px] font-valo tracking-[0.3em] mb-2"
              style={{ color: "rgba(148,163,184,0.7)" }}
            >
              MODEL VALIDATION // WALK-FORWARD BACKTEST
            </div>
            <h1 className="font-valo text-4xl sm:text-5xl font-bold tracking-wide leading-[0.95] text-white">
              과거 예측 <span style={{ color: "#4ADE80" }}>vs</span> 실제
            </h1>
          </div>
        </div>

        <p className="text-sm leading-relaxed max-w-3xl pl-2" style={{ color: "rgba(148,163,184,0.85)" }}>
          각 액트에 대해 <span className="font-bold text-white">그 시점까지의 데이터만</span> 사용해
          모델을 재학습하고 해당 액트의 결과를 예측했습니다.
          실전 서빙 전 모델이 실제로 내렸을 예측만 평가합니다.
        </p>

        <div className="flex flex-wrap gap-2 pl-6">
          {[
            `SAMPLE: ${data.totalRows} predictions`,
            `SPAN: ${data.actRange.first} → ${data.actRange.last}`,
            `FOLDS: ${data.acts.length} acts`,
            "CV: walk-forward temporal",
          ].map((t) => (
            <span
              key={t}
              className="text-[9px] px-2 py-1 uppercase tracking-wider"
              style={{
                border: "1px solid rgba(51,65,85,0.55)",
                color: "rgba(148,163,184,0.55)",
                background: "rgba(13,18,32,0.4)",
              }}
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* ── 전체 메트릭 ──────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="OVERALL // 3-CLASS" ko="전체 방향성 적중" accent="#4ADE80" />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="방향성 적중률"
            value={`${Math.round(o.hitRate3 * 100)}%`}
            hint={`n=${data.totalRows}`}
            accent="#4ADE80"
          />
          <MetricCard
            label="Balanced Accuracy"
            value={o.balancedAccuracy.toFixed(3)}
            hint="클래스 불균형 보정"
            accent="#A78BFA"
          />
          <MetricCard
            label="5-class 적중률"
            value={`${Math.round(o.hitRate5 * 100)}%`}
            hint="mild/strong 구분까지"
            accent="#7DD3FC"
          />
          <MetricCard
            label="Top-3/액트 NERF"
            value={`${Math.round(data.topK.nerfPrecisionTop3PerAct * 100)}%`}
            hint="각 액트 p_nerf 상위 3명 중 실제 너프 비율"
            accent="#FF4655"
          />
        </div>

        {/* 클래스별 P/R */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {(["stable", "buff", "nerf"] as const).map((c) => {
            const m = o.classes[c];
            const color = DIR_COLOR[c];
            return (
              <div
                key={c}
                className="p-4"
                style={{ border: `1px solid ${color}44`, background: `${color}0A` }}
              >
                <div className="flex items-center justify-between mb-3">
                  <span
                    className="text-[10px] uppercase tracking-[0.25em] font-valo font-bold"
                    style={{ color }}
                  >
                    {c}
                  </span>
                  <span className="text-[10px]" style={{ color: "rgba(100,116,139,0.8)" }}>
                    n={m.support}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <Stat label="Precision" value={m.precision} />
                  <Stat label="Recall"    value={m.recall} />
                  <Stat label="F1"        value={m.f1} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Confusion Matrix ─────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="CONFUSION MATRIX" ko="혼동 행렬" accent="#A78BFA" />
        <ConfusionMatrix matrix={o.confusionMatrix} labels={o.confusionLabels} />
      </section>

      {/* ── 고확신 임계값 ────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="CONFIDENCE CALIBRATION" ko="확신 구간 정밀도" accent="#7DD3FC" />
        <p className="text-[11px] leading-relaxed max-w-2xl" style={{ color: "rgba(148,163,184,0.8)" }}>
          확률이 높을수록 실제 너프/버프로 이어질 가능성이 커야 정상.
          아래 곡선은 임계값 이상 예측한 샘플 중 실제로 방향이 맞은 비율입니다.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <ThresholdTable
            title="NERF 예측"
            rows={data.highConf.nerf}
            accent="#FF4655"
          />
          <ThresholdTable
            title="BUFF 예측"
            rows={data.highConf.buff}
            accent="#4FC3F7"
          />
        </div>
      </section>

      {/* ── 스토리: 선행 적중 ────────────────────────────────────────── */}
      {data.stories.leadHits.length > 0 && (
        <section className="space-y-4">
          <SectionHeader en="LEAD HITS" ko="한 액트 선행 예측" accent="#4ADE80" />
          <p className="text-[11px] leading-relaxed max-w-2xl" style={{ color: "rgba(148,163,184,0.8)" }}>
            해당 액트에는 아직 너프 안 됐지만 모델이 먼저 경고를 올렸고,
            실제로 <span className="font-bold text-white">바로 다음 액트에</span> 너프가 이어진 경우.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.stories.leadHits.map((s, i) => (
              <div
                key={i}
                className="p-4 space-y-2"
                style={{ border: "1px solid rgba(74,222,128,0.35)", background: "rgba(16,185,129,0.06)" }}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-valo uppercase tracking-wider text-lg" style={{ color: "#e2e8f0" }}>
                    {s.agent}
                  </span>
                  <span className="text-[10px] font-mono" style={{ color: "rgba(74,222,128,0.85)" }}>
                    p_nerf {(s.pNerf * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[11px]" style={{ color: "rgba(148,163,184,0.9)" }}>
                  <span>
                    <span className="font-mono font-bold text-white">{s.predictedAt}</span>
                    <span className="text-[9px] ml-1 uppercase tracking-wider" style={{ color: DIR_COLOR.stable }}>
                      {LABEL_KO[s.truthAtPred] ?? s.truthAtPred}
                    </span>
                  </span>
                  <span style={{ color: "#4ADE80" }}>→</span>
                  <span>
                    <span className="font-mono font-bold text-white">{s.hitAt}</span>
                    <span className="text-[9px] ml-1 uppercase tracking-wider" style={{ color: DIR_COLOR.nerf }}>
                      {LABEL_KO[s.truthAtHit] ?? s.truthAtHit}
                    </span>
                  </span>
                </div>
                <div className="text-[10px] leading-snug" style={{ color: "rgba(100,116,139,0.85)" }}>
                  {s.predictedAt} 시점엔 stable. 그러나 모델은 너프 신호를 감지했고,
                  {s.hitAt} 에 실제 너프 발생.
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 큰 적중 / 큰 오답 ────────────────────────────────────────── */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StoryBlock
          en="NOTABLE HITS"
          ko="대표 적중"
          accent="#4ADE80"
          rows={data.stories.bigHits}
          blurb="확신 있게 예측 → 실제로 방향 맞음."
        />
        <StoryBlock
          en="NOTABLE MISSES"
          ko="대표 오답"
          accent="#FF4655"
          rows={data.stories.bigMisses}
          blurb="모델이 강하게 너프/버프라 했지만 실제로는 빗나간 케이스."
        />
      </section>

      {/* ── 액트별 적중률 ────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="PER-ACT ACCURACY" ko="액트별 적중률" accent="#FBBF24" />
        <PerActChart perAct={data.perAct} />
      </section>

      {/* ── 전체 예측 테이블 ─────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="ALL PREDICTIONS" ko="전체 예측 목록" accent="#CBD5E1" />
        <BacktestPredictionTable rows={data.predictions} acts={data.acts} />
      </section>

      {/* ── 메서돌로지 ────────────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="METHODOLOGY" ko="측정 방식" accent="#94A3B8" />
        <div
          className="p-5 text-[12px] leading-relaxed space-y-3"
          style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)", color: "rgba(203,213,225,0.9)" }}
        >
          <Bullet>
            <strong>Walk-forward CV</strong> — 각 폴드에서 <code className="font-mono text-white">act_idx &lt; T</code> 데이터로만
            모델을 학습한 뒤 <code className="font-mono text-white">act_idx == T</code> 를 예측.
            미래 데이터가 과거 평가에 누출되지 않습니다.
          </Bullet>
          <Bullet>
            <strong>2-Stage</strong> — Stage A: stable vs patched (XGBoost · train-only 언더샘플링),
            Stage B: buff vs nerf (Logistic Regression). 결합해 5-class verdict 산출.
          </Bullet>
          <Bullet>
            <strong>레이블</strong> — 각 액트 이후 실제 너프/버프 이력에 따라 부여.
            미니 패치 / rework / 핫픽스 포함.
          </Bullet>
          <Bullet>
            <strong>평가 대상</strong> — 레이블 확정된 과거 액트만 (현재 진행 중 V26A2 제외).
          </Bullet>
          <Bullet>
            <strong>생성 시각</strong>{" "}
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

// ─── Sub-components ────────────────────────────────────────────────────────

function SectionHeader({
  en,
  ko,
  accent,
}: {
  en: string;
  ko: string;
  accent: string;
}) {
  return (
    <div className="flex items-baseline gap-3">
      <div style={{ width: "2px", height: "22px", background: accent }} />
      <span
        className="text-[9px] font-valo tracking-[0.25em]"
        style={{ color: `${accent}CC` }}
      >
        {en}
      </span>
      <span className="font-valo font-bold text-lg" style={{ color: accent }}>
        {ko}
      </span>
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
    <div
      className="p-4"
      style={{
        border: `1px solid ${accent}44`,
        background: `${accent}08`,
      }}
    >
      <div className="text-[9px] uppercase tracking-[0.2em] mb-1" style={{ color: "rgba(148,163,184,0.75)" }}>
        {label}
      </div>
      <div className="text-3xl font-num font-bold tabular-nums" style={{ color: accent }}>
        {value}
      </div>
      {hint && (
        <div className="text-[10px] mt-1" style={{ color: "rgba(100,116,139,0.85)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-[9px] uppercase tracking-widest mb-0.5" style={{ color: "rgba(100,116,139,0.85)" }}>
        {label}
      </div>
      <div className="text-lg font-num font-bold tabular-nums" style={{ color: "#e2e8f0" }}>
        {value.toFixed(2)}
      </div>
    </div>
  );
}

function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
  const max = Math.max(...matrix.flat(), 1);

  return (
    <div
      className="p-4 overflow-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      <table className="text-[11px] font-num tabular-nums mx-auto">
        <thead>
          <tr>
            <th className="px-2 py-1"></th>
            <th className="px-2 py-1 text-[9px] uppercase tracking-widest" colSpan={labels.length} style={{ color: "rgba(148,163,184,0.75)" }}>
              예측 (predicted)
            </th>
          </tr>
          <tr>
            <th className="px-2 py-1"></th>
            {labels.map((l) => (
              <th key={l} className="px-3 py-1 uppercase tracking-widest text-[9px]" style={{ color: DIR_COLOR[l as keyof typeof DIR_COLOR] ?? "#94A3B8" }}>
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <th className="pl-2 pr-3 py-1 text-left uppercase tracking-widest text-[9px]" style={{ color: DIR_COLOR[labels[i] as keyof typeof DIR_COLOR] ?? "#94A3B8" }}>
                <span style={{ color: "rgba(148,163,184,0.6)" }} className="mr-1">실제</span>
                {labels[i]}
              </th>
              {row.map((v, j) => {
                const intensity = v / max;
                const isDiag = i === j;
                const bgBase = isDiag ? "74,222,128" : "148,163,184";
                return (
                  <td
                    key={j}
                    className="px-3 py-2 text-center font-bold"
                    style={{
                      background: `rgba(${bgBase},${0.05 + intensity * 0.35})`,
                      color: isDiag ? "#4ADE80" : "#e2e8f0",
                      border: "1px solid rgba(30,41,59,0.6)",
                      minWidth: "70px",
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
      <div className="text-[10px] text-center mt-3" style={{ color: "rgba(100,116,139,0.85)" }}>
        대각선 = 정답. 초록색 짙을수록 좋음.
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
        className="px-4 py-2 text-[10px] uppercase tracking-[0.25em] font-bold"
        style={{ color: accent, borderBottom: `1px solid ${accent}33` }}
      >
        {title}
      </div>
      <table className="w-full text-[11px] font-num tabular-nums">
        <thead>
          <tr className="text-[9px] uppercase tracking-widest" style={{ color: "rgba(148,163,184,0.7)" }}>
            <th className="px-4 py-2 text-left">임계값</th>
            <th className="px-4 py-2 text-right">샘플</th>
            <th className="px-4 py-2 text-right">정밀도</th>
            <th className="px-4 py-2 w-1/2">  </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const pct = Math.round(r.precision * 100);
            return (
              <tr key={r.threshold} style={{ borderTop: "1px solid rgba(30,41,59,0.4)" }}>
                <td className="px-4 py-2" style={{ color: "#cbd5e1" }}>
                  ≥ {r.threshold.toFixed(2)}
                </td>
                <td className="px-4 py-2 text-right" style={{ color: "rgba(148,163,184,0.9)" }}>
                  {r.n}
                </td>
                <td className="px-4 py-2 text-right font-bold" style={{ color: accent }}>
                  {pct}%
                </td>
                <td className="px-4 py-2">
                  <div style={{ background: `${accent}22`, height: "8px" }}>
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

function StoryBlock({
  en,
  ko,
  accent,
  rows,
  blurb,
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
}) {
  if (rows.length === 0) return null;
  return (
    <div className="space-y-3">
      <SectionHeader en={en} ko={ko} accent={accent} />
      <p className="text-[11px] leading-relaxed max-w-lg" style={{ color: "rgba(148,163,184,0.8)" }}>
        {blurb}
      </p>
      <div className="space-y-2">
        {rows.map((s, i) => {
          const p = s.pNerf ?? s.pBuff ?? 0;
          const pLabel = s.pNerf !== undefined ? "p_nerf" : "p_buff";
          return (
            <div
              key={i}
              className="p-3 flex items-center justify-between gap-3"
              style={{ border: `1px solid ${accent}33`, background: `${accent}06` }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-valo uppercase tracking-wider" style={{ color: "#e2e8f0" }}>
                    {s.agent}
                  </span>
                  <span className="text-[10px] font-mono" style={{ color: "rgba(100,116,139,0.85)" }}>
                    {s.act}
                  </span>
                </div>
                <div className="text-[10px] mt-0.5" style={{ color: "rgba(148,163,184,0.8)" }}>
                  예측 <span className="font-bold" style={{ color: accent }}>
                    {LABEL_KO[s.predicted] ?? s.predicted}
                  </span>{" "}
                  · 실제 <span className="font-bold" style={{ color: "#cbd5e1" }}>
                    {LABEL_KO[s.truth] ?? s.truth}
                  </span>
                </div>
              </div>
              <div
                className="text-right font-num font-bold text-sm tabular-nums shrink-0"
                style={{ color: accent }}
              >
                {pLabel} {Math.round(p * 100)}%
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
}: {
  perAct: { act: string; act_idx: number; n: number; hit_dir: number; hit_5: number }[];
}) {
  const avg = perAct.reduce((s, r) => s + r.hit_dir, 0) / Math.max(perAct.length, 1);

  return (
    <div
      className="p-4 space-y-2 overflow-x-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      {perAct.map((r) => {
        const pct3 = Math.round(r.hit_dir * 100);
        const pct5 = Math.round(r.hit_5   * 100);
        return (
          <div key={r.act} className="grid grid-cols-[64px_1fr_88px] items-center gap-3 text-[11px]">
            <div className="font-mono font-bold" style={{ color: "#cbd5e1" }}>
              {r.act}
            </div>
            <div style={{ background: "rgba(30,41,59,0.5)", height: "16px", position: "relative" }}>
              <div
                style={{
                  background: "#4ADE80",
                  height: "100%",
                  width: `${pct3}%`,
                  transition: "width 0.3s",
                }}
              />
              <div
                className="absolute top-0 bottom-0 w-px"
                style={{ left: `${Math.round(avg * 100)}%`, background: "rgba(148,163,184,0.5)" }}
                title={`평균 ${Math.round(avg * 100)}%`}
              />
            </div>
            <div className="text-right font-num tabular-nums" style={{ color: "rgba(148,163,184,0.9)" }}>
              {pct3}%{" "}
              <span style={{ color: "rgba(100,116,139,0.7)" }}>· 5c {pct5}%</span>
            </div>
          </div>
        );
      })}
      <div className="text-[10px] pt-2" style={{ color: "rgba(100,116,139,0.75)" }}>
        얇은 세로선 = 전체 평균 ({Math.round(avg * 100)}%). · 5c = 5-class 세부 적중률
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
