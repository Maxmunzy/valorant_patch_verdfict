"use client";

import { usePathname } from "next/navigation";

const UPDATES: { date: string; note: string }[] = [
  { date: "2026.04.25", note: "영문 페이지(/en)와 KO/EN 토글 추가, 12.06 라이브 반영해 VCT 시차 배너 제거" },
  { date: "2026.04.22", note: "직전 패치 적중률 카드, walk-forward baseline 비교, 에이전트 OG 이미지 추가" },
  { date: "2026.04.21", note: "백테스트 요약 공개와 카드형 VCT 시각화 추가" },
  { date: "2026.04.20", note: "에이전트 상세 페이지와 설명 품질 개선" },
  { date: "2026.04.20", note: "시뮬레이터 흐름과 경고 문구 보강" },
  { date: "2026.04.18", note: "whosnxt.app 프로덕션 배포 정리" },
];

const GITHUB_URL = "https://github.com/Maxmunzy/valorant_patch_verdict";

export default function Disclaimer() {
  const pathname = usePathname();
  const isHome = pathname === "/";

  if (!isHome) {
    return (
      <footer className="mt-12 pt-5 pb-8 border-t" style={{ borderColor: "rgba(30,41,59,0.6)" }}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div
            className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] uppercase tracking-widest"
            style={{ color: "rgba(71,85,105,0.9)" }}
          >
            <span style={{ color: "rgba(148,163,184,0.7)" }}>UNOFFICIAL FAN PROJECT</span>
            <span>·</span>
            <span>NOT AFFILIATED WITH RIOT GAMES</span>
            <span>·</span>
            <a href="/agents" className="transition-colors hover:text-white" style={{ color: "rgba(255,70,85,0.8)" }}>
              AGENTS
            </a>
            <span>·</span>
            <a href="/backtest" className="transition-colors hover:text-white" style={{ color: "rgba(74,222,128,0.8)" }}>
              BACKTEST
            </a>
            <span>·</span>
            <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="transition-colors hover:text-white" style={{ color: "rgba(148,163,184,0.7)" }}>
              GITHUB
            </a>
            <span>·</span>
            <a href="mailto:ashley920913@gmail.com" className="transition-colors hover:text-slate-300" style={{ color: "rgba(167,139,250,0.7)" }}>
              CONTACT
            </a>
            <span>·</span>
            <span>© 2026 WHOS&apos;NEXT</span>
          </div>
        </div>
      </footer>
    );
  }

  return (
    <footer className="mt-16 pt-8 pb-12 border-t" style={{ borderColor: "rgba(30,41,59,0.8)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-6">
        <div className="flex items-start gap-3">
          <div className="shrink-0 mt-1 w-1.5 h-1.5 rotate-45" style={{ background: "rgba(148,163,184,0.4)" }} />
          <p className="text-[12px] leading-relaxed" style={{ color: "rgba(148,163,184,0.75)" }}>
            <span className="font-bold" style={{ color: "#cbd5e1" }}>비공식 분석 프로젝트</span>
            입니다. 실제 패치 결과와 다를 수 있으며, 데이터 기반 참고 자료로 보는 것이 가장 적절합니다.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="p-4" style={{ border: "1px solid rgba(30,41,59,0.7)", background: "rgba(13,18,32,0.5)" }}>
            <div className="text-[9px] uppercase tracking-[0.25em] mb-2" style={{ color: "rgba(100,116,139,0.85)" }}>
              CONTACT
            </div>
            <div className="text-[12px] leading-relaxed" style={{ color: "#cbd5e1" }}>
              피드백, 버그 제보, 데이터 관련 문의
            </div>
            <a href="mailto:ashley920913@gmail.com" className="text-[13px] font-mono mt-1 inline-block transition-colors hover:text-white" style={{ color: "#A78BFA" }}>
              ashley920913@gmail.com
            </a>
          </div>

          <div className="p-4" style={{ border: "1px solid rgba(30,41,59,0.7)", background: "rgba(13,18,32,0.5)" }}>
            <div className="text-[9px] uppercase tracking-[0.25em] mb-2" style={{ color: "rgba(100,116,139,0.85)" }}>
              CHANGELOG
            </div>
            <ul className="space-y-1.5">
              {UPDATES.map((update) => (
                <li key={update.date} className="flex gap-3 text-[12px] leading-snug">
                  <span className="font-mono shrink-0" style={{ color: "rgba(100,116,139,0.9)" }}>
                    {update.date}
                  </span>
                  <span style={{ color: "#cbd5e1" }}>{update.note}</span>
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
          <span>·</span>
          <a href="/agents" className="transition-colors hover:text-white" style={{ color: "rgba(255,70,85,0.85)" }}>
            AGENTS
          </a>
          <span>·</span>
          <a href="/backtest" className="transition-colors hover:text-white" style={{ color: "rgba(74,222,128,0.85)" }}>
            BACKTEST
          </a>
          <span>·</span>
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="transition-colors hover:text-slate-300" style={{ color: "rgba(148,163,184,0.85)" }}>
            GITHUB
          </a>
        </div>
      </div>
    </footer>
  );
}
