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

interface Props {
  data: BacktestSummary;
}

export default function ModelCharacterBlurb({ data }: Props) {
  const o = data.overall;
  const s = o.classes.stable;
  const n = o.classes.nerf;
  const b = o.classes.buff;

  // ── 클레임 1: 가장 강한 클래스 ──────────────────────────────
  const classes = [
    { name: "안정 판정", key: "stable", f1: s.f1, p: s.precision, r: s.recall },
    { name: "너프 탐지", key: "nerf",   f1: n.f1, p: n.precision, r: n.recall },
    { name: "버프 탐지", key: "buff",   f1: b.f1, p: b.precision, r: b.recall },
  ].sort((x, y) => y.f1 - x.f1);
  const strongest = classes[0];
  const weakest   = classes[classes.length - 1];

  // ── 클레임 2: 너프 리콜이 낮으면 "보수적" 해설 ──────────────
  // (ChatGPT가 정확히 지적한 포인트 — 우리 모델의 약점)
  const nerfRecallLow  = n.recall < 0.5;
  const nerfMissedPct  = Math.round((1 - n.recall) * 100);

  // ── 클레임 3: 고확신 보정 ──────────────────────────────────
  const highNerfRow = data.highConf.nerf.find((r) => Math.abs(r.threshold - 0.7) < 0.01);
  const calibrated  = highNerfRow && highNerfRow.n >= 10 && highNerfRow.precision >= 0.55;

  // ── 문장 조립 ──────────────────────────────────────────────
  const sentences: { text: string; accent?: string }[] = [];

  sentences.push({
    text: `가장 자신 있게 맞히는 쪽은 **${strongest.name}**이에요 — F1 ${strongest.f1.toFixed(2)}, 정밀도 ${Math.round(strongest.p * 100)}% · 재현율 ${Math.round(strongest.r * 100)}%.`,
    accent: "#4ADE80",
  });

  if (nerfRecallLow) {
    sentences.push({
      text: `**너프는 꽤 신중하게 집습니다** — 실제 너프 중 ${Math.round(n.recall * 100)}%만 미리 잡아내고 나머지 ${nerfMissedPct}%는 놓치는 편입니다 (정밀도 ${Math.round(n.precision * 100)}%).`,
      accent: "#FF4655",
    });
  } else {
    sentences.push({
      text: `가장 까다로운 영역은 **${weakest.name}**입니다 — F1 ${weakest.f1.toFixed(2)}, 정밀도 ${Math.round(weakest.p * 100)}% · 재현율 ${Math.round(weakest.r * 100)}%.`,
      accent: "#F59E0B",
    });
  }

  if (calibrated && highNerfRow) {
    sentences.push({
      text: `대신 **확률이 높게 찍힐수록 신뢰할 만합니다** — p_nerf 0.70 이상으로 찍은 예측은 ${Math.round(highNerfRow.precision * 100)}% 적중했어요 (n=${highNerfRow.n}).`,
      accent: "#7DD3FC",
    });
  } else {
    sentences.push({
      text: `전체 방향 적중률은 **${Math.round(o.hitRate3 * 100)}%** 수준입니다 (Balanced Accuracy ${o.balancedAccuracy.toFixed(2)}).`,
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
          운영자 해설
        </span>
        <span
          className="text-[11px] uppercase tracking-widest"
          style={{ color: "rgba(148,163,184,0.8)" }}
        >
          숫자 보기 전에 먼저 읽는 모델 성격
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
        <strong style={{ color: "#cbd5e1" }}>용어 풀이</strong> · <b>정밀도</b>는 "모델이 너프라고 찍은 것 중 실제 너프였던 비율",
        <b>재현율</b>은 "실제 너프 중 모델이 미리 잡아낸 비율"입니다. 둘 다 100%로 올리는 건 불가능해서 균형 싸움이에요.
      </div>
    </div>
  );
}
