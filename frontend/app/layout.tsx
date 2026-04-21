import type { Metadata } from "next";
import "./globals.css";
import Disclaimer from "@/components/Disclaimer";

export const metadata: Metadata = {
  title: "PATCH VERDICT // Valorant",
  description: "랭크와 VCT 데이터를 바탕으로 다음 패치 압력을 예측하는 Valorant 분석 서비스",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="antialiased">
      <body
        className="min-h-screen font-sans"
        style={{ background: "#080c14", color: "#e2e8f0" }}
      >
        <div
          className="fixed top-0 left-0 right-0 h-px z-50"
          style={{ background: "linear-gradient(90deg, #FF4655, #FF465530, transparent)" }}
        />

        <header
          className="sticky top-0 z-40 backdrop-blur-md border-b border-slate-800/70"
          style={{ background: "rgba(8,12,20,0.92)" }}
        >
          <div className="max-w-7xl mx-auto flex items-center justify-between h-11 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <div
                className="w-2 h-2 rotate-45 shrink-0"
                style={{ background: "#FF4655", boxShadow: "0 0 8px 2px rgba(255,70,85,0.55)" }}
              />
              <div className="flex items-center gap-1.5">
                <span className="text-[13px] font-black tracking-[0.15em]" style={{ color: "#FF4655" }}>
                  PATCH
                </span>
                <span className="text-slate-700 text-[13px]">/</span>
                <span className="text-[13px] font-black tracking-[0.15em] text-white">VERDICT</span>
              </div>
              <div
                className="hidden sm:flex items-center gap-1 px-1.5 py-0.5"
                style={{ border: "1px solid rgba(16,185,129,0.25)", background: "rgba(16,185,129,0.06)" }}
              >
                <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[9px] uppercase tracking-widest" style={{ color: "rgba(52,211,153,0.7)" }}>
                  LIVE
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-[9px] uppercase tracking-widest text-slate-700 hidden sm:block">SYS:ACT</span>
              <span
                className="text-[10px] font-bold text-slate-400 px-2 py-0.5"
                style={{ border: "1px solid rgba(30,41,59,0.8)", background: "rgba(13,18,32,0.6)" }}
              >
                V26A2
              </span>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 pb-8">{children}</main>
        <Disclaimer />
      </body>
    </html>
  );
}
