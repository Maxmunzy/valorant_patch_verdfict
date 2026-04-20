/**
 * 데이터 출처/갱신 시점/확률 의미를 간단히 표시하는 신뢰 블록.
 * 홈 상단 히어로 아래에 배치해 "이 수치가 어디서 오는지"를 먼저 알려줌.
 */
export default function TrustBlock() {
  const items: { label: string; value: string; hint?: string }[] = [
    {
      label: "DATA SOURCE",
      value: "랭크 (다이아+) · VCT 공식 경기",
      hint: "라이엇 공식 통계 + 리퀴피디아 VCT",
    },
    {
      label: "UPDATED",
      value: "매주 자동 갱신",
      hint: "패치 / VCT 액트 단위로 재학습",
    },
    {
      label: "PROBABILITY",
      value: "패치 가능성 스코어",
      hint: "실제 확률이 아닌 상대적 위험도 — 높을수록 조정 대상에 가까움",
    },
  ];

  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-slate-800/70"
      style={{ border: "1px solid rgba(51,65,85,0.6)", background: "rgba(13,18,32,0.6)" }}
    >
      {items.map((it) => (
        <div key={it.label} className="p-3.5 sm:p-4">
          <div
            className="text-[9px] uppercase tracking-[0.25em] mb-1.5"
            style={{ color: "rgba(148,163,184,0.55)" }}
          >
            {it.label}
          </div>
          <div className="text-[13px] font-semibold leading-snug" style={{ color: "#e2e8f0" }}>
            {it.value}
          </div>
          {it.hint && (
            <div className="text-[11px] leading-snug mt-1" style={{ color: "rgba(100,116,139,0.85)" }}>
              {it.hint}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
