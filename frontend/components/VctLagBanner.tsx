/**
 * VCT 지표 시차 경고 배너.
 *
 * 라이엇이 패치를 내놔도 VCT 공식 대회는 며칠~몇 주 뒤부터 적용된다.
 * 즉 사이트에 표시되는 VCT 픽률/승률은 가장 최근 패치의 밸런스를 반영하지 못한 상태.
 * 이 시차를 홈에 명시해, 프로씬 지표가 부풀려 보이는 걸 오해하지 않게 한다.
 *
 * 문구에 나오는 패치 번호와 날짜는 수동 관리.
 * (자동화는 현재 범위 초과 — VCT 일정 크롤러가 없음.)
 */

export default function VctLagBanner() {
  return (
    <div
      className="relative flex items-center gap-2.5 px-3.5 py-2 text-[11px] leading-snug"
      style={{
        border: "1px solid rgba(251,191,36,0.35)",
        background:
          "linear-gradient(90deg, rgba(251,191,36,0.08) 0%, rgba(13,18,32,0.4) 60%, rgba(13,18,32,0.0) 100%)",
      }}
    >
      <span
        className="shrink-0 inline-flex items-center justify-center text-[9px] font-black tracking-widest px-1.5 py-0.5"
        style={{
          color: "#FBBF24",
          border: "1px solid rgba(251,191,36,0.55)",
          background: "rgba(251,191,36,0.12)",
        }}
      >
        NOTE
      </span>
      <span style={{ color: "rgba(226,232,240,0.8)" }}>
        VCT 픽률·승률은 <span className="font-bold text-white">12.06 패치 이전 기준</span>입니다.
        대회 밸런스는 <span className="font-bold text-white">4월 24일</span>부터 반영되므로
        최근 너프된 요원이 VCT 지표에선 여전히 높아 보일 수 있습니다.
      </span>
    </div>
  );
}
