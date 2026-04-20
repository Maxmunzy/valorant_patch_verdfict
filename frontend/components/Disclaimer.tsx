/**
 * 페이지 하단에 표시되는 비공식 안내 / 문의 / 업데이트 로그 블록.
 * 비공식 예측 도구임을 명시해 사용자 기대치를 정렬.
 *
 * 홈('/'): 전체 블록 표시 — 신규 방문자 컨텍스트 제공
 * 그 외 (상세 페이지 등): 축약 한 줄만 노출 — 여러 요원 연속 탐색 시 방해 최소화
 */
"use client";

import { usePathname } from "next/navigation";

const UPDATES: { date: string; note: string }[] = [
  { date: "2026.04.20", note: "홈 카드 배지 / 표본 신뢰도 Tier / 크로스패치 노이즈 필터" },
  { date: "2026.04.20", note: "확률 해석 경고 · 홈 정보 밀도 축소 · 시뮬레이터 샘플 시나리오" },
  { date: "2026.04.20", note: "AI 분석 라벨 용어 정돈 · stable 폴백 문구 개선" },
  { date: "2026.04.18", note: "커스텀 도메인 whosnxt.app 연결 · 프로덕션 배포" },
];

export default function Disclaimer() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  // ── 홈 외 페이지: 축약 1줄 푸터 ─────────────────────────────────
  if (!isHome) {
    return (
      <footer
        className="mt-12 pt-5 pb-8 border-t"
        style={{ borderColor: "rgba(30,41,59,0.6)" }}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div
            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] uppercase tracking-widest"
            style={{ color: "rgba(71,85,105,0.9)" }}
          >
            <span style={{ color: "rgba(148,163,184,0.7)" }}>UNOFFICIAL FAN PROJECT</span>
            <span>·</span>
            <span>NOT AFFILIATED WITH RIOT GAMES</span>
            <span>·</span>
            <a
              href="mailto:ashley920913@gmail.com"
              className="transition-colors hover:text-slate-300"
              style={{ color: "rgba(167,139,250,0.7)" }}
            >
              CONTACT
            </a>
            <span>·</span>
            <span>© 2026 WHOS&apos;NEXT</span>
          </div>
        </div>
      </footer>
    );
  }

  // ── 홈: 전체 신뢰 블록 ──────────────────────────────────────────
  return (
    <footer
      className="mt-16 pt-8 pb-12 border-t"
      style={{ borderColor: "rgba(30,41,59,0.8)" }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-6">
        {/* 한 줄 헤드라인 */}
        <div className="flex items-start gap-3">
          <div
            className="shrink-0 mt-1 w-1.5 h-1.5 rotate-45"
            style={{ background: "rgba(148,163,184,0.4)" }}
          />
          <p className="text-[12px] leading-relaxed" style={{ color: "rgba(148,163,184,0.75)" }}>
            <span className="font-bold" style={{ color: "#cbd5e1" }}>비공식 예측 도구</span>
            입니다. 라이엇 게임즈와 무관하며, 실제 패치 결과와 다를 수 있습니다.
            데이터 기반의 통계적 추정치로만 참고해 주세요.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* 문의 */}
          <div
            className="p-4"
            style={{ border: "1px solid rgba(30,41,59,0.7)", background: "rgba(13,18,32,0.5)" }}
          >
            <div
              className="text-[9px] uppercase tracking-[0.25em] mb-2"
              style={{ color: "rgba(100,116,139,0.85)" }}
            >
              CONTACT // 문의
            </div>
            <div className="text-[12px] leading-relaxed" style={{ color: "#cbd5e1" }}>
              피드백 · 버그 제보 · 제휴 문의
            </div>
            <a
              href="mailto:ashley920913@gmail.com"
              className="text-[13px] font-mono mt-1 inline-block transition-colors hover:text-white"
              style={{ color: "#A78BFA" }}
            >
              ashley920913@gmail.com
            </a>
          </div>

          {/* 업데이트 로그 */}
          <div
            className="p-4"
            style={{ border: "1px solid rgba(30,41,59,0.7)", background: "rgba(13,18,32,0.5)" }}
          >
            <div
              className="text-[9px] uppercase tracking-[0.25em] mb-2"
              style={{ color: "rgba(100,116,139,0.85)" }}
            >
              CHANGELOG // 최근 업데이트
            </div>
            <ul className="space-y-1.5">
              {UPDATES.map((u) => (
                <li key={u.date} className="flex gap-3 text-[12px] leading-snug">
                  <span
                    className="font-mono shrink-0"
                    style={{ color: "rgba(100,116,139,0.9)" }}
                  >
                    {u.date}
                  </span>
                  <span style={{ color: "#cbd5e1" }}>{u.note}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div
          className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] uppercase tracking-widest pt-2"
          style={{ color: "rgba(71,85,105,0.9)" }}
        >
          <span>© 2026 WHOS&apos;NEXT</span>
          <span>·</span>
          <span>UNOFFICIAL FAN PROJECT</span>
          <span>·</span>
          <span>NOT AFFILIATED WITH RIOT GAMES</span>
        </div>
      </div>
    </footer>
  );
}
