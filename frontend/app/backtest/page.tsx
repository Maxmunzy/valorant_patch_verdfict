import Link from "next/link";
import { getBacktestSummary } from "@/lib/backtest";
import type { BacktestAgentRow } from "@/lib/backtest";
import BacktestPredictionTable from "@/components/backtest/BacktestPredictionTable";
import ModelCharacterBlurb from "@/components/backtest/ModelCharacterBlurb";

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
      <div className="space-y-5">
        <Link
          href="/"
          className="inline-block text-[12px] uppercase tracking-widest transition-colors hover:text-white"
          style={{ color: "rgba(148,163,184,0.8)" }}
        >
          ← 홈으로
        </Link>

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
              시간순 재현 백테스트 · 과거 예측 성적표
            </div>
            <h1 className="font-valo text-4xl sm:text-5xl font-bold tracking-wide leading-[0.95] text-white">
              모델은 과거에 <span style={{ color: "#4ADE80" }}>얼마나</span> 맞췄나
            </h1>
          </div>
        </div>

        <p className="text-[13px] leading-relaxed max-w-3xl pl-2" style={{ color: "rgba(203,213,225,0.9)" }}>
          각 액트마다 <span className="font-bold text-white">그 시점까지 쌓인 데이터로만</span> 모델을
          처음부터 다시 학습시킨 뒤 해당 액트를 예측하게 했습니다. 즉, 그때 실제로 모델을 돌렸다면
          내렸을 예측만 평가에 포함됩니다. 미래 정보를 보고 과거를 맞히는 "치트"가 끼지 않아요.
        </p>
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
          한 줄 요약 · TL;DR
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8">
          <HeroStat
            label="방향 적중률"
            value={`${Math.round(o.hitRate3 * 100)}%`}
            sub={`전체 ${data.totalRows}건 예측 중 너프/버프/안정 방향을 맞힌 비율`}
            accent="#4ADE80"
          />
          <HeroStat
            label="확신 있는 너프의 적중률"
            value={`${Math.round((data.highConf.nerf.find((r) => Math.abs(r.threshold - 0.6) < 0.01)?.precision ?? 0) * 100)}%`}
            sub={`p_nerf 0.60 이상으로 찍은 예측 중 실제 너프로 이어진 비율`}
            accent="#FF4655"
          />
          <HeroStat
            label="검증 범위"
            value={`${data.acts.length} ACT`}
            sub={`${data.actRange.first} → ${data.actRange.last} · 총 ${data.totalRows}건 예측`}
            accent="#7DD3FC"
          />
        </div>
        <div
          className="flex flex-wrap gap-2 mt-6 pt-5"
          style={{ borderTop: "1px solid rgba(51,65,85,0.5)" }}
        >
          {[
            `예측 샘플 ${data.totalRows}건`,
            `기간: ${data.actRange.first} → ${data.actRange.last}`,
            `${data.acts.length}개 액트 폴드`,
            "방식: 시간순 재현 (Walk-forward)",
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

      {/* ── 모델 성격 해설 (비전문 사용자용 친절 블록) ───────────── */}
      <ModelCharacterBlurb data={data} />

      {/* ── 전체 메트릭 ──────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader en="전체 지표" ko="클래스별 성능" accent="#4ADE80" />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            label="방향 적중률"
            value={`${Math.round(o.hitRate3 * 100)}%`}
            hint={`전체 ${data.totalRows}건 기준`}
            accent="#4ADE80"
          />
          <MetricCard
            label="Balanced Accuracy"
            value={o.balancedAccuracy.toFixed(3)}
            hint="클래스 불균형을 보정한 점수"
            accent="#A78BFA"
          />
          <MetricCard
            label="세부 적중률"
            value={`${Math.round(o.hitRate5 * 100)}%`}
            hint="약/강 세기까지 맞힌 비율"
            accent="#7DD3FC"
          />
          <MetricCard
            label="액트당 너프 TOP3"
            value={`${Math.round(data.topK.nerfPrecisionTop3PerAct * 100)}%`}
            hint="각 액트 너프 확률 상위 3명 중 실제 너프 비율"
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
                  <span className="text-[12px] font-mono" style={{ color: "rgba(148,163,184,0.85)" }}>
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

      {/* ── 요원별 적중 Top / Worst ──────────────────────────────────── */}
      {data.topAgents && (data.topAgents.hits.length > 0 || data.topAgents.misses.length > 0) && (
        <section className="space-y-5">
          <SectionHeader en="요원별 성적" ko="잘 맞힌 요원 · 잘 못 맞힌 요원" accent="#FBBF24" />
          <p className="text-[13px] leading-relaxed max-w-2xl" style={{ color: "rgba(203,213,225,0.9)" }}>
            한 요원을 여러 액트에 걸쳐 예측해온 누적 적중률입니다. 3건 이상 예측된 요원만 집계했어요.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <TopAgentsCard
              title="가장 잘 맞힌 요원 TOP 5"
              rows={data.topAgents.hits}
              accent="#4ADE80"
              positive
            />
            <TopAgentsCard
              title="가장 자주 빗나간 요원 TOP 5"
              rows={data.topAgents.misses}
              accent="#FF4655"
              positive={false}
            />
          </div>
        </section>
      )}

      {/* ── Confusion Matrix ─────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="혼동 행렬" ko="예측한 것 vs 실제 결과" accent="#A78BFA" />
        <ConfusionMatrix matrix={o.confusionMatrix} labels={o.confusionLabels} />
      </section>

      {/* ── 고확신 임계값 ────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader en="확신도 검증" ko="확률이 높을 때 실제로도 맞는가" accent="#7DD3FC" />
        <p className="text-[13px] leading-relaxed max-w-2xl" style={{ color: "rgba(203,213,225,0.9)" }}>
          모델이 높은 확률로 찍을수록 실제 너프/버프가 일어날 비율도 같이 높아져야 정상입니다.
          아래는 각 임계값 이상으로 예측한 샘플 가운데 실제 방향이 맞았던 비율이에요.
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
        <section className="space-y-5">
          <SectionHeader en="선행 예측" ko="한 액트 먼저 짚어낸 케이스" accent="#4ADE80" />
          <p className="text-[13px] leading-relaxed max-w-2xl" style={{ color: "rgba(203,213,225,0.9)" }}>
            아직 너프가 내려오지 않았을 때 모델이 먼저 너프 신호를 올렸고,
            실제로 <span className="font-bold text-white">바로 다음 액트</span>에서 너프가 확정된 경우입니다.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.stories.leadHits.map((s, i) => (
              <div
                key={i}
                className="p-5 space-y-3"
                style={{ border: "1px solid rgba(74,222,128,0.35)", background: "rgba(16,185,129,0.06)" }}
              >
                <div className="flex items-baseline justify-between">
                  <span className="font-valo uppercase tracking-wider text-2xl" style={{ color: "#e2e8f0" }}>
                    {s.agent}
                  </span>
                  <span className="text-[12px] font-mono font-bold" style={{ color: "rgba(74,222,128,0.95)" }}>
                    p_nerf {(s.pNerf * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[14px]" style={{ color: "rgba(203,213,225,0.9)" }}>
                  <span className="flex flex-col gap-0.5">
                    <span className="font-mono font-bold text-white">{s.predictedAt}</span>
                    <span className="text-[11px] uppercase tracking-wider" style={{ color: DIR_COLOR.stable }}>
                      {LABEL_KO[s.truthAtPred] ?? s.truthAtPred}
                    </span>
                  </span>
                  <span className="text-2xl" style={{ color: "#4ADE80" }}>→</span>
                  <span className="flex flex-col gap-0.5">
                    <span className="font-mono font-bold text-white">{s.hitAt}</span>
                    <span className="text-[11px] uppercase tracking-wider" style={{ color: DIR_COLOR.nerf }}>
                      {LABEL_KO[s.truthAtHit] ?? s.truthAtHit}
                    </span>
                  </span>
                </div>
                <div className="text-[12px] leading-snug" style={{ color: "rgba(148,163,184,0.9)" }}>
                  {s.predictedAt} 당시엔 너프가 없는 안정 상태였지만 모델은 이미 너프 신호를 읽었고,
                  한 액트 뒤 {s.hitAt}에서 실제 너프로 이어졌습니다.
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── 큰 적중 / 큰 오답 ────────────────────────────────────────── */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <StoryBlock
          en="대표 적중"
          ko="자신 있게 질렀는데 맞은 예측"
          accent="#4ADE80"
          rows={data.stories.bigHits}
          blurb="모델이 강하게 확신했고 실제로도 그 방향으로 움직인 케이스예요."
        />
        <StoryBlock
          en="대표 오답"
          ko="자신 있게 질렀는데 빗나간 예측"
          accent="#FF4655"
          rows={data.stories.bigMisses}
          blurb="너프/버프라고 강하게 찍었지만 실제로는 반대로 흘러간 케이스입니다."
        />
      </section>

      {/* ── 액트별 적중률 추이 ───────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="액트별 추이" ko="액트가 지날수록 모델은 나아졌나" accent="#FBBF24" />
        <p className="text-[13px] leading-relaxed max-w-2xl" style={{ color: "rgba(203,213,225,0.9)" }}>
          액트가 늘수록 학습 데이터가 쌓입니다. 시간이 가면서 적중률이 안정권에 들어오는지 아래 그래프로 확인할 수 있어요.
        </p>
        <PerActLineChart perAct={data.perAct} />
        <PerActChart perAct={data.perAct} />
      </section>

      {/* ── 전체 예측 테이블 ─────────────────────────────────────────── */}
      <section className="space-y-4">
        <SectionHeader en="전체 예측 목록" ko={`${data.totalRows}건 원본 기록`} accent="#CBD5E1" />
        <BacktestPredictionTable rows={data.predictions} acts={data.acts} />
      </section>

      {/* ── 메서돌로지 ────────────────────────────────────────────────── */}
      <section className="space-y-5">
        <SectionHeader en="측정 방식" ko="어떻게 평가했나" accent="#94A3B8" />
        <div
          className="p-6 text-[13px] leading-relaxed space-y-4"
          style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)", color: "rgba(226,232,240,0.92)" }}
        >
          <Bullet>
            <strong>시간순 재현 (Walk-forward)</strong> — 각 폴드에서
            <code className="font-mono text-white mx-1">act_idx &lt; T</code>에 해당하는 과거 데이터로만 학습한 뒤
            <code className="font-mono text-white mx-1">act_idx == T</code>를 예측합니다.
            미래 정보가 과거 평가에 새어 들어가지 않는 구조예요.
          </Bullet>
          <Bullet>
            <strong>2단 구조</strong> — 1단(XGBoost)에서 "이 요원이 다음 패치에 조정될지 vs 안정될지"를 판별하고,
            조정된다고 판단된 경우에만 2단(Logistic Regression)에서 "너프인지 버프인지"를 가립니다.
            최종적으로 5단계 판정(강/약 너프 · 안정 · 강/약 버프)으로 합쳐져요.
          </Bullet>
          <Bullet>
            <strong>정답 레이블</strong> — 각 액트 이후 실제로 있었던 너프/버프 이력을 기준으로 매겼습니다.
            미니 패치, 리워크, 핫픽스까지 모두 반영했어요.
          </Bullet>
          <Bullet>
            <strong>평가 범위</strong> — 결과가 확정된 과거 액트만 대상으로 했습니다 (현재 진행 중인 V26A2는 제외).
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
    <div className="flex items-baseline gap-3 flex-wrap">
      <div style={{ width: "3px", height: "30px", background: accent }} />
      <span
        className="text-[12px] font-valo tracking-[0.25em]"
        style={{ color: `${accent}CC` }}
      >
        {en}
      </span>
      <span className="font-valo font-bold text-xl sm:text-2xl" style={{ color: accent }}>
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
      className="p-5"
      style={{
        border: `1px solid ${accent}44`,
        background: `${accent}08`,
      }}
    >
      <div className="text-[12px] uppercase tracking-[0.2em] mb-2" style={{ color: "rgba(148,163,184,0.85)" }}>
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
      <div className="text-[11px] uppercase tracking-widest mb-1" style={{ color: "rgba(148,163,184,0.75)" }}>
        {label}
      </div>
      <div className="text-xl font-num font-bold tabular-nums" style={{ color: "#e2e8f0" }}>
        {value.toFixed(2)}
      </div>
    </div>
  );
}

function ConfusionMatrix({ matrix, labels }: { matrix: number[][]; labels: string[] }) {
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
            <th className="px-3 py-2 text-[12px] uppercase tracking-widest" colSpan={labels.length} style={{ color: "rgba(148,163,184,0.85)" }}>
              예측 (predicted)
            </th>
          </tr>
          <tr>
            <th className="px-3 py-2"></th>
            {labels.map((l) => (
              <th key={l} className="px-4 py-2 uppercase tracking-widest text-[13px] font-bold" style={{ color: DIR_COLOR[l as keyof typeof DIR_COLOR] ?? "#94A3B8" }}>
                {l}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <th className="pl-3 pr-4 py-3 text-left uppercase tracking-widest text-[13px] font-bold" style={{ color: DIR_COLOR[labels[i] as keyof typeof DIR_COLOR] ?? "#94A3B8" }}>
                <span style={{ color: "rgba(148,163,184,0.7)" }} className="mr-1.5 text-[11px]">실제</span>
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
      <div className="text-[13px] text-center mt-4" style={{ color: "rgba(148,163,184,0.85)" }}>
        대각선 칸이 "정확히 맞힌 예측". 초록이 짙을수록 잘 맞혔다는 뜻이에요.
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
      <table className="w-full text-[14px] font-num tabular-nums">
        <thead>
          <tr className="text-[11px] uppercase tracking-widest" style={{ color: "rgba(148,163,184,0.8)" }}>
            <th className="px-5 py-3 text-left">임계값</th>
            <th className="px-5 py-3 text-right">샘플</th>
            <th className="px-5 py-3 text-right">정밀도</th>
            <th className="px-5 py-3 w-1/2">  </th>
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
    <div className="space-y-4">
      <SectionHeader en={en} ko={ko} accent={accent} />
      <p className="text-[13px] leading-relaxed max-w-lg" style={{ color: "rgba(203,213,225,0.9)" }}>
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
                  <span className="font-valo uppercase tracking-wider text-xl" style={{ color: "#e2e8f0" }}>
                    {s.agent}
                  </span>
                  <span className="text-[12px] font-mono font-bold" style={{ color: "rgba(148,163,184,0.9)" }}>
                    {s.act}
                  </span>
                </div>
                <div className="text-[13px] mt-1.5" style={{ color: "rgba(203,213,225,0.9)" }}>
                  예측 <span className="font-bold" style={{ color: accent }}>
                    {LABEL_KO[s.predicted] ?? s.predicted}
                  </span>{" "}
                  · 실제 <span className="font-bold text-white">
                    {LABEL_KO[s.truth] ?? s.truth}
                  </span>
                </div>
              </div>
              <div
                className="text-right font-num font-bold text-xl tabular-nums shrink-0"
                style={{ color: accent }}
              >
                {Math.round(p * 100)}%
                <div className="text-[10px] uppercase tracking-widest font-normal mt-0.5" style={{ color: "rgba(148,163,184,0.75)" }}>
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
}: {
  perAct: { act: string; act_idx: number; n: number; hit_dir: number; hit_5: number }[];
}) {
  const avg = perAct.reduce((s, r) => s + r.hit_dir, 0) / Math.max(perAct.length, 1);

  return (
    <div
      className="p-6 space-y-3 overflow-x-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      {perAct.map((r) => {
        const pct3 = Math.round(r.hit_dir * 100);
        const pct5 = Math.round(r.hit_5   * 100);
        return (
          <div key={r.act} className="grid grid-cols-[88px_1fr_150px] items-center gap-4 text-[14px]">
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
                style={{ left: `${Math.round(avg * 100)}%`, width: "2px", background: "rgba(148,163,184,0.6)" }}
                title={`평균 ${Math.round(avg * 100)}%`}
              />
            </div>
            <div className="text-right font-num tabular-nums" style={{ color: "#e2e8f0" }}>
              <span className="font-bold text-base">{pct3}%</span>{" "}
              <span className="text-[12px]" style={{ color: "rgba(100,116,139,0.85)" }}>· 5c {pct5}%</span>
            </div>
          </div>
        );
      })}
      <div className="text-[12px] pt-3" style={{ color: "rgba(100,116,139,0.9)" }}>
        얇은 세로선은 전체 평균 ({Math.round(avg * 100)}%) 위치 · 5c는 약/강 세기까지 맞힌 세부 적중률이에요.
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

// ─── HERO 빅 숫자 카드 ──────────────────────────────────────────────────────
function HeroStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub: string;
  accent: string;
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
    </div>
  );
}

// ─── 요원별 Top Hit / Top Miss 카드 ─────────────────────────────────────────
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
    <div
      className="p-5 space-y-3"
      style={{ border: `1px solid ${accent}44`, background: `${accent}08` }}
    >
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
                <span className="font-valo uppercase text-base font-bold truncate" style={{ color: "#e2e8f0" }}>
                  {r.agent}
                </span>
                <span className="text-[11px] font-mono" style={{ color: "rgba(148,163,184,0.75)" }}>
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

// ─── 액트별 적중률 라인 차트 ────────────────────────────────────────────────
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
  const yOf = (v: number) => padT + innerH - v * innerH; // v는 0~1

  const buildPath = (key: "hit_dir" | "hit_5") =>
    perAct
      .map((r, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(r[key]).toFixed(1)}`)
      .join(" ");

  const d3  = buildPath("hit_dir");
  const d5  = buildPath("hit_5");
  const avgY = yOf(avg);

  // x축 라벨 — 너무 많으면 띄엄띄엄
  const labelStep = Math.max(1, Math.ceil(n / 9));

  return (
    <div
      className="p-4 sm:p-6 overflow-x-auto"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.5)" }}
    >
      <div className="flex flex-wrap items-center gap-4 mb-3 text-[12px] font-mono">
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5" style={{ background: "#4ADE80" }} />
          <span style={{ color: "#e2e8f0" }}>방향 적중률 (너프/버프/안정)</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-0.5" style={{ background: "#7DD3FC" }} />
          <span style={{ color: "rgba(203,213,225,0.9)" }}>세부 적중률 (약/강까지)</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block w-4 h-px border-t border-dashed" style={{ borderColor: "rgba(148,163,184,0.7)" }} />
          <span style={{ color: "rgba(148,163,184,0.85)" }}>전체 평균 {Math.round(avg * 100)}%</span>
        </span>
      </div>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: "600px" }}>
        {/* y축 그리드 */}
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line
              x1={padL}
              x2={W - padR}
              y1={yOf(v)}
              y2={yOf(v)}
              stroke="rgba(51,65,85,0.35)"
              strokeWidth={1}
            />
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

        {/* 평균 라인 */}
        <line
          x1={padL}
          x2={W - padR}
          y1={avgY}
          y2={avgY}
          stroke="rgba(148,163,184,0.7)"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* 5-class 선 (더 얇게) */}
        <path
          d={d5}
          fill="none"
          stroke="#7DD3FC"
          strokeWidth={1.8}
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity={0.75}
        />

        {/* 3-class 선 (강조) */}
        <path
          d={d3}
          fill="none"
          stroke="#4ADE80"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: "drop-shadow(0 0 3px #4ADE8055)" }}
        />

        {/* 데이터 포인트 */}
        {perAct.map((r, i) => (
          <g key={r.act}>
            <circle cx={xOf(i)} cy={yOf(r.hit_dir)} r={3.5} fill="#4ADE80" />
            <title>{`${r.act}: ${Math.round(r.hit_dir * 100)}% (n=${r.n})`}</title>
          </g>
        ))}

        {/* x축 라벨 */}
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
