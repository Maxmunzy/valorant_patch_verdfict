/**
 * 백테스트 HERO 아래 붙는 "모델 성격 해설" 블록.
 *
 * ChatGPT 피드백 (2026.04.21) — 숫자는 많지만 비전문 사용자가
 * precision/recall 차이를 바로 체감하기 어렵다. 운영자 해설 한 단락이
 * 숫자 위에서 성격을 먼저 잡아주면 훨씬 친절해진다.
 *
 * 설계 원칙:
 *  - JSON에서 값 읽어 템플릿으로 자동 생성 (하드코딩 금지 — 재학습하면 자동 갱신)
 *  - 3개 클레임으로 구성: 강점 · 약점 · 확신 보정
 *  - 각 클레임 뒤에 괄호로 근거 숫자 달아서 "왜 그렇게 주장하는지" 바로 확인 가능
 */

import type { BacktestSummary } from "@/lib/backtest";
import type { Locale } from "@/lib/i18n/dict";
import { getDict } from "@/lib/i18n/dict";

interface Props {
  data: BacktestSummary;
  locale?: Locale;
}

export default function ModelCharacterBlurb({ data, locale = "ko" }: Props) {
  const t = getDict(locale).modelBlurb;
  const o = data.overall;
  const s = o.classes.stable;
  const n = o.classes.nerf;
  const b = o.classes.buff;

  // ── 클레임 1: 가장 강한 클래스 ──────────────────────────────
  const classes = [
    { name: t.classNames.stable, key: "stable", f1: s.f1, p: s.precision, r: s.recall },
    { name: t.classNames.nerf, key: "nerf", f1: n.f1, p: n.precision, r: n.recall },
    { name: t.classNames.buff, key: "buff", f1: b.f1, p: b.precision, r: b.recall },
  ].sort((x, y) => y.f1 - x.f1);
  const strongest = classes[0];
  const weakest = classes[classes.length - 1];

  // ── 클레임 2: 너프 리콜이 낮으면 "보수적" 해설 ──────────────
  const nerfRecallLow = n.recall < 0.5;
  const nerfMissedPct = Math.round((1 - n.recall) * 100);

  // ── 클레임 3: 고확신 보정 ──────────────────────────────────
  const highNerfRow = data.highConf.nerf.find((r) => Math.abs(r.threshold - 0.7) < 0.01);
  const calibrated = highNerfRow && highNerfRow.n >= 10 && highNerfRow.precision >= 0.55;

  // ── 문장 조립 ──────────────────────────────────────────────
  const sentences: { text: string; accent?: string }[] = [];

  sentences.push({
    text: t.sentences.strongest(
      strongest.name,
      strongest.f1.toFixed(2),
      Math.round(strongest.p * 100),
      Math.round(strongest.r * 100),
    ),
    accent: "#4ADE80",
  });

  if (nerfRecallLow) {
    sentences.push({
      text: t.sentences.nerfRecallLow(
        Math.round(n.recall * 100),
        nerfMissedPct,
        Math.round(n.precision * 100),
      ),
      accent: "#FF4655",
    });
  } else {
    sentences.push({
      text: t.sentences.weakest(
        weakest.name,
        weakest.f1.toFixed(2),
        Math.round(weakest.p * 100),
        Math.round(weakest.r * 100),
      ),
      accent: "#F59E0B",
    });
  }

  if (calibrated && highNerfRow) {
    sentences.push({
      text: t.sentences.calibrated(Math.round(highNerfRow.precision * 100), highNerfRow.n),
      accent: "#7DD3FC",
    });
  } else {
    sentences.push({
      text: t.sentences.overallFallback(
        Math.round(o.hitRate3 * 100),
        o.balancedAccuracy.toFixed(2),
      ),
      accent: "#7DD3FC",
    });
  }

  return (
    <div
      className="p-5 sm:p-6 space-y-3"
      style={{
        border: "1px solid rgba(148,163,184,0.35)",
        background: "rgba(13,18,32,0.6)",
      }}
    >
      <div className="flex items-center gap-2">
        <span
          className="text-[10px] uppercase tracking-[0.3em] font-bold px-2 py-0.5"
          style={{
            color: "#FBBF24",
            border: "1px solid rgba(251,191,36,0.4)",
            background: "rgba(251,191,36,0.06)",
          }}
        >
          {t.operatorTag}
        </span>
        <span
          className="text-[11px] uppercase tracking-widest"
          style={{ color: "rgba(148,163,184,0.8)" }}
        >
          {t.subtitle}
        </span>
      </div>

      <ul className="space-y-2.5">
        {sentences.map((s, i) => (
          <li key={i} className="flex gap-3">
            <span
              className="shrink-0 mt-2 w-1.5 h-1.5 rotate-45"
              style={{ background: s.accent ?? "#94A3B8" }}
            />
            <p
              className="text-[13px] sm:text-[14px] leading-relaxed"
              style={{ color: "rgba(226,232,240,0.95)" }}
              dangerouslySetInnerHTML={{
                __html: s.text.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff;font-weight:700">$1</strong>'),
              }}
            />
          </li>
        ))}
      </ul>

      <div
        className="text-[11px] leading-snug pt-2"
        style={{ color: "rgba(148,163,184,0.7)", borderTop: "1px solid rgba(51,65,85,0.4)" }}
      >
        <strong style={{ color: "#cbd5e1" }}>{t.glossaryHeader}</strong>{" "}
        <span dangerouslySetInnerHTML={{ __html: t.glossaryBody }} />
      </div>
    </div>
  );
}
