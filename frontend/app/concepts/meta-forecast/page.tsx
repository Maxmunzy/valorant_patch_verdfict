import BackToHome from "@/components/BackToHome";

// "한 줄로 보는 메타 변화 예보" — 5 design variants
// All variants share: single horizontal strip, tactical Valorant aesthetic,
// dark navy ground, sharp geometric edges, uppercase tracking-wide micro-labels.

export const metadata = {
  title: "META FORECAST // concepts",
};

const demo = {
  nerfAgent: "웨이레이",
  nerfPct: 79,
  buffAgent: "네온",
  buffPct: 64,
  context: "VCT 픽률 44.8% · 상위권 지배 중",
  countdown: 14, // days to next patch
  patchId: "V25A7",
};

export default function MetaForecastConcepts() {
  return (
    <div className="min-h-screen py-10 space-y-12" style={{ background: "#0a0e18" }}>
      <style>{`
        @keyframes pulse-dot { 0%,100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.35; transform: scale(0.85); } }
        @keyframes radar-sweep { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes ticker-scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        @keyframes signal-bar { 0%,100% { transform: scaleY(0.55); } 50% { transform: scaleY(1); } }
        @keyframes blink { 0%,49% { opacity: 1; } 50%,100% { opacity: 0; } }
        @keyframes caret { 0%,49% { opacity: 1; } 50%,100% { opacity: 0; } }
        @keyframes fade-sweep { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
        .meta-ticker-track { animation: ticker-scroll 26s linear infinite; }
        .meta-pulse { animation: pulse-dot 1.4s ease-in-out infinite; }
        .meta-blink { animation: blink 1.2s steps(1) infinite; }
        .meta-sweep::before {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(90deg, transparent 0%, rgba(255,70,85,0.12) 50%, transparent 100%);
          animation: fade-sweep 6s ease-in-out infinite;
          pointer-events: none;
        }
        .bar-anim > span { transform-origin: bottom; animation: signal-bar 1.1s ease-in-out infinite; }
        .bar-anim > span:nth-child(2) { animation-delay: 0.15s; }
        .bar-anim > span:nth-child(3) { animation-delay: 0.30s; }
        .bar-anim > span:nth-child(4) { animation-delay: 0.45s; }
        .bar-anim > span:nth-child(5) { animation-delay: 0.60s; }
        .caret::after { content: "▌"; margin-left: 4px; animation: caret 0.9s steps(1) infinite; color: #4ADE80; }
      `}</style>

      <header className="max-w-5xl mx-auto px-6 space-y-5">
        <BackToHome />
        <div className="flex items-start gap-4 pt-3">
          <div style={{ width: 2, height: 54, background: "linear-gradient(to bottom,#FF4655,#FF465510)" }} />
          <div>
            <div className="text-[10px] tracking-[0.35em]" style={{ color: "rgba(251,191,36,0.8)" }}>
              CONCEPT REVIEW // META FORECAST STRIP
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white leading-[1.05]">
              한 줄로 보는 메타 변화 예보
            </h1>
            <p className="text-[13px] mt-2" style={{ color: "rgba(148,163,184,0.8)" }}>
              5가지 스타일 · 모두 동일 데이터 사용 · 한 줄 스트립 제약 준수
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 space-y-14">
        <Labeled label="VARIANT 01" title="SPLIT VS — 너프 vs 버프 정면 대결">
          <SplitVs />
        </Labeled>

        <Labeled label="VARIANT 02" title="ALERT TICKER — 라이브 전광판">
          <AlertTicker />
        </Labeled>

        <Labeled label="VARIANT 03" title="RADAR SIGNAL — 레이더 교신">
          <RadarSignal />
        </Labeled>

        <Labeled label="VARIANT 04" title="TERMINAL READOUT — 데이터 스트림">
          <TerminalReadout />
        </Labeled>

        <Labeled label="VARIANT 05" title="THREAT LEVEL — 위협 평가 배너">
          <ThreatLevel />
        </Labeled>
      </main>

      <footer className="max-w-5xl mx-auto px-6 pt-8 pb-16 text-[11px] tracking-widest uppercase" style={{ color: "rgba(148,163,184,0.55)" }}>
        // END OF CONCEPT SHEET
      </footer>
    </div>
  );
}

/* ----------------------------- shared wrapper ---------------------------- */

function Labeled({ label, title, children }: { label: string; title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <div className="flex items-baseline gap-3">
        <span
          className="text-[10px] px-2 py-0.5 tracking-[0.3em] font-bold"
          style={{ color: "#FBBF24", border: "1px solid rgba(251,191,36,0.45)", background: "rgba(251,191,36,0.05)" }}
        >
          {label}
        </span>
        <span className="text-[13px] font-bold tracking-wide" style={{ color: "rgba(226,232,240,0.9)" }}>
          {title}
        </span>
      </div>
      {children}
    </section>
  );
}

/* ----------------------------- VARIANT 01 --------------------------------- */

function SplitVs() {
  const { nerfAgent, nerfPct, buffAgent, buffPct, patchId } = demo;
  return (
    <div
      className="relative overflow-hidden"
      style={{
        height: 84,
        border: "1px solid rgba(71,85,105,0.55)",
        background: "#0d1220",
      }}
    >
      <div
        className="absolute inset-y-0 left-0 flex items-center pl-5 pr-14"
        style={{
          width: "50%",
          background:
            "linear-gradient(90deg, rgba(255,70,85,0.28) 0%, rgba(255,70,85,0.12) 60%, rgba(255,70,85,0) 100%)",
          clipPath: "polygon(0 0, 100% 0, calc(100% - 26px) 100%, 0 100%)",
        }}
      >
        <div className="flex items-baseline gap-3 whitespace-nowrap">
          <span className="text-[9px] font-bold tracking-[0.35em]" style={{ color: "#FF4655" }}>
            ▼ NERF
          </span>
          <span className="text-2xl font-black text-white tracking-tight">{nerfAgent}</span>
          <span className="text-[34px] font-black tabular-nums leading-none" style={{ color: "#FF4655" }}>
            {nerfPct}
            <span className="text-base">%</span>
          </span>
        </div>
      </div>

      <div
        className="absolute inset-y-0 right-0 flex items-center justify-end pr-5 pl-14"
        style={{
          width: "50%",
          background:
            "linear-gradient(270deg, rgba(79,195,247,0.28) 0%, rgba(79,195,247,0.12) 60%, rgba(79,195,247,0) 100%)",
          clipPath: "polygon(26px 0, 100% 0, 100% 100%, 0 100%)",
        }}
      >
        <div className="flex items-baseline gap-3 whitespace-nowrap">
          <span className="text-[34px] font-black tabular-nums leading-none" style={{ color: "#4FC3F7" }}>
            {buffPct}
            <span className="text-base">%</span>
          </span>
          <span className="text-2xl font-black text-white tracking-tight">{buffAgent}</span>
          <span className="text-[9px] font-bold tracking-[0.35em]" style={{ color: "#4FC3F7" }}>
            BUFF ▲
          </span>
        </div>
      </div>

      <div
        className="absolute top-1/2 left-1/2 flex items-center justify-center"
        style={{
          width: 52,
          height: 52,
          transform: "translate(-50%, -50%) rotate(45deg)",
          background: "#0a0e18",
          border: "1px solid rgba(251,191,36,0.7)",
          boxShadow: "0 0 0 3px #0a0e18, 0 0 24px rgba(251,191,36,0.2)",
        }}
      >
        <span
          className="text-[13px] font-black tracking-[0.2em]"
          style={{ color: "#FBBF24", transform: "rotate(-45deg)" }}
        >
          VS
        </span>
      </div>

      <div
        className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[8px] tracking-[0.4em]"
        style={{ color: "rgba(251,191,36,0.55)" }}
      >
        NEXT PATCH · {patchId}
      </div>

      <Bracket pos="tl" color="#FF4655" />
      <Bracket pos="tr" color="#4FC3F7" />
      <Bracket pos="bl" color="#FF465580" />
      <Bracket pos="br" color="#4FC3F780" />
    </div>
  );
}

/* ----------------------------- VARIANT 02 --------------------------------- */

function AlertTicker() {
  const { nerfAgent, nerfPct, buffAgent, buffPct, context, countdown, patchId } = demo;
  const tickerItems = [
    { tag: "NERF", agent: nerfAgent, pct: nerfPct, color: "#FF4655" },
    { tag: "BUFF", agent: buffAgent, pct: buffPct, color: "#4FC3F7" },
    { tag: "WATCH", agent: "레이즈", pct: 52, color: "#FBBF24" },
    { tag: "SIGNAL", agent: "바이퍼", pct: 48, color: "#A78BFA" },
    { tag: "STABLE", agent: "요루", pct: 31, color: "#64748B" },
  ];
  const track = [...tickerItems, ...tickerItems];

  return (
    <div
      className="relative overflow-hidden meta-sweep"
      style={{
        height: 68,
        border: "1px solid rgba(255,70,85,0.55)",
        background:
          "linear-gradient(180deg, rgba(255,70,85,0.08) 0%, rgba(13,18,32,0.95) 50%, rgba(13,18,32,1) 100%)",
      }}
    >
      <div
        className="absolute inset-y-0 left-0 flex items-center gap-2.5 px-4 z-10"
        style={{
          background: "linear-gradient(90deg, #FF4655 0%, #B91C1C 100%)",
          clipPath: "polygon(0 0, 100% 0, calc(100% - 14px) 100%, 0 100%)",
          minWidth: 128,
        }}
      >
        <span
          className="meta-pulse w-2 h-2 inline-block"
          style={{ background: "#fff", boxShadow: "0 0 8px #fff" }}
        />
        <div className="text-white leading-none">
          <div className="text-[8px] tracking-[0.3em] opacity-80">LIVE SIGNAL</div>
          <div className="text-[15px] font-black tracking-wider">ON AIR</div>
        </div>
      </div>

      <div className="absolute inset-y-0 left-[128px] right-[152px] overflow-hidden flex items-center">
        <div className="meta-ticker-track flex items-center gap-8 whitespace-nowrap pl-8">
          {track.map((item, i) => (
            <span key={i} className="flex items-baseline gap-2.5">
              <span
                className="text-[9px] font-bold tracking-[0.3em]"
                style={{ color: item.color }}
              >
                ● {item.tag}
              </span>
              <span className="text-[15px] font-bold text-white tracking-tight">
                {item.agent}
              </span>
              <span
                className="text-[15px] font-black tabular-nums"
                style={{ color: item.color }}
              >
                {item.pct}%
              </span>
              <span className="text-[11px]" style={{ color: "rgba(148,163,184,0.55)" }}>
                ──
              </span>
            </span>
          ))}
        </div>
        <div
          className="absolute inset-y-0 left-0 w-10 pointer-events-none"
          style={{ background: "linear-gradient(90deg, #0d1220, transparent)" }}
        />
        <div
          className="absolute inset-y-0 right-0 w-10 pointer-events-none"
          style={{ background: "linear-gradient(-90deg, #0d1220, transparent)" }}
        />
        <div
          className="absolute bottom-1 left-8 text-[9px] tracking-[0.25em]"
          style={{ color: "rgba(148,163,184,0.5)" }}
        >
          {context}
        </div>
      </div>

      <div
        className="absolute inset-y-0 right-0 flex items-center gap-3 px-4 z-10"
        style={{
          background: "linear-gradient(90deg, transparent 0%, rgba(251,191,36,0.1) 40%, rgba(251,191,36,0.2) 100%)",
          borderLeft: "1px solid rgba(251,191,36,0.45)",
          minWidth: 152,
        }}
      >
        <div className="text-right">
          <div className="text-[8px] tracking-[0.3em]" style={{ color: "rgba(251,191,36,0.75)" }}>
            NEXT PATCH
          </div>
          <div className="text-[11px] tracking-widest font-bold text-white">{patchId}</div>
        </div>
        <div className="flex items-baseline gap-0.5 leading-none">
          <span
            className="text-[10px] font-bold tracking-[0.25em] self-start pt-0.5"
            style={{ color: "#FBBF24" }}
          >
            D-
          </span>
          <span className="text-[30px] font-black tabular-nums" style={{ color: "#FBBF24" }}>
            {countdown}
          </span>
        </div>
      </div>
    </div>
  );
}

/* ----------------------------- VARIANT 03 --------------------------------- */

function RadarSignal() {
  const { nerfAgent, nerfPct, buffAgent, buffPct, countdown } = demo;
  return (
    <div
      className="relative overflow-hidden"
      style={{
        height: 96,
        border: "1px solid rgba(74,222,128,0.4)",
        background:
          "radial-gradient(circle at 8% 50%, rgba(74,222,128,0.1) 0%, transparent 35%), linear-gradient(180deg, #0d1220 0%, #080b14 100%)",
      }}
    >
      <div className="absolute left-4 top-1/2 -translate-y-1/2" style={{ width: 72, height: 72 }}>
        <div
          className="relative w-full h-full rounded-full"
          style={{
            border: "1px solid rgba(74,222,128,0.6)",
            boxShadow: "inset 0 0 18px rgba(74,222,128,0.15)",
          }}
        >
          <span
            className="absolute inset-[10px] rounded-full"
            style={{ border: "1px solid rgba(74,222,128,0.3)" }}
          />
          <span
            className="absolute inset-[22px] rounded-full"
            style={{ border: "1px solid rgba(74,222,128,0.2)" }}
          />
          <span
            className="absolute inset-y-0 left-1/2 w-px"
            style={{ background: "rgba(74,222,128,0.25)" }}
          />
          <span
            className="absolute inset-x-0 top-1/2 h-px"
            style={{ background: "rgba(74,222,128,0.25)" }}
          />
          <span
            className="absolute inset-0 rounded-full"
            style={{
              background:
                "conic-gradient(from 0deg, rgba(74,222,128,0.55) 0deg, transparent 60deg, transparent 360deg)",
              animation: "radar-sweep 3.2s linear infinite",
            }}
          />
          <span
            className="absolute meta-pulse"
            style={{
              left: "70%", top: "25%", width: 5, height: 5, borderRadius: "50%",
              background: "#FF4655", boxShadow: "0 0 8px #FF4655",
            }}
          />
          <span
            className="absolute meta-pulse"
            style={{
              left: "22%", top: "68%", width: 4, height: 4, borderRadius: "50%",
              background: "#4FC3F7", boxShadow: "0 0 8px #4FC3F7",
              animationDelay: "0.6s",
            }}
          />
        </div>
      </div>

      <div
        className="absolute top-1/2 -translate-y-1/2 left-[104px] right-[168px] flex flex-col justify-center gap-1.5"
      >
        <SignalRow tag="TGT-01" verdict="NERF LOCK" agent={nerfAgent} pct={nerfPct} color="#FF4655" />
        <div
          className="h-px"
          style={{ background: "linear-gradient(90deg, rgba(74,222,128,0.25), transparent)" }}
        />
        <SignalRow tag="TGT-02" verdict="BUFF RISE" agent={buffAgent} pct={buffPct} color="#4FC3F7" />
      </div>

      <div
        className="absolute inset-y-0 right-0 flex flex-col justify-center px-4"
        style={{
          minWidth: 168,
          borderLeft: "1px solid rgba(74,222,128,0.25)",
          background: "linear-gradient(270deg, rgba(74,222,128,0.08), transparent)",
        }}
      >
        <div className="text-[8px] tracking-[0.35em]" style={{ color: "rgba(74,222,128,0.8)" }}>
          INCOMING // ETA
        </div>
        <div className="flex items-baseline gap-1 mt-0.5">
          <span className="text-[24px] font-black tabular-nums text-white leading-none">
            T-{String(countdown).padStart(2, "0")}
          </span>
          <span className="text-[11px] tracking-wider" style={{ color: "rgba(148,163,184,0.65)" }}>
            DAYS
          </span>
        </div>
        <div className="text-[9px] mt-1 tracking-[0.25em]" style={{ color: "rgba(148,163,184,0.55)" }}>
          BEARING 217° · STRONG
        </div>
      </div>
    </div>
  );
}

function SignalRow({ tag, verdict, agent, pct, color }: { tag: string; verdict: string; agent: string; pct: number; color: string }) {
  return (
    <div className="flex items-center gap-3 whitespace-nowrap">
      <span
        className="text-[8.5px] px-1.5 py-0.5 font-bold tracking-[0.25em]"
        style={{ color, border: `1px solid ${color}55`, background: `${color}12` }}
      >
        {tag}
      </span>
      <span className="text-[10px] font-bold tracking-[0.3em]" style={{ color }}>
        {verdict}
      </span>
      <span className="text-[18px] font-black tracking-tight text-white">{agent}</span>
      <span className="text-[22px] font-black tabular-nums leading-none" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}

/* ----------------------------- VARIANT 04 --------------------------------- */

function TerminalReadout() {
  const { nerfAgent, nerfPct, buffAgent, buffPct, context, patchId } = demo;
  return (
    <div
      className="relative overflow-hidden"
      style={{
        height: 78,
        border: "1px solid rgba(74,222,128,0.35)",
        background: "#05080f",
        boxShadow: "inset 0 0 40px rgba(74,222,128,0.04)",
      }}
    >
      <div
        className="absolute top-0 left-0 right-0 flex items-center gap-2 px-3 py-1 text-[9px] tracking-[0.3em]"
        style={{
          background: "rgba(74,222,128,0.07)",
          borderBottom: "1px solid rgba(74,222,128,0.2)",
          color: "rgba(74,222,128,0.85)",
        }}
      >
        <span style={{ width: 6, height: 6, background: "#FF4655", borderRadius: "50%" }} />
        <span style={{ width: 6, height: 6, background: "#FBBF24", borderRadius: "50%" }} />
        <span style={{ width: 6, height: 6, background: "#4ADE80", borderRadius: "50%" }} />
        <span className="ml-2">META_FORECAST.SH · {patchId}</span>
        <span className="ml-auto" style={{ color: "rgba(148,163,184,0.55)" }}>
          LAST SYNC 02:14
        </span>
      </div>

      <div
        className="absolute inset-x-0 bottom-0 top-[22px] flex items-center px-4 text-[13px] whitespace-nowrap overflow-hidden"
        style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}
      >
        <div className="flex items-center gap-3 w-full">
          <span style={{ color: "#4ADE80" }}>▸</span>
          <span style={{ color: "rgba(148,163,184,0.5)" }}>diff</span>
          <span style={{ color: "#FF4655" }}>
            - {nerfAgent}
            <span className="opacity-70"> [nerf:{nerfPct}%]</span>
          </span>
          <span style={{ color: "rgba(148,163,184,0.4)" }}>·</span>
          <span style={{ color: "#4FC3F7" }}>
            + {buffAgent}
            <span className="opacity-70"> [buff:{buffPct}%]</span>
          </span>
          <span style={{ color: "rgba(148,163,184,0.4)" }}>·</span>
          <span style={{ color: "rgba(226,232,240,0.75)" }}>note=</span>
          <span style={{ color: "#FBBF24" }} className="truncate">
            &quot;{context}&quot;
          </span>
          <span className="caret ml-1" />
        </div>
      </div>

      <div
        className="absolute top-[22px] bottom-0 right-0 w-16 pointer-events-none"
        style={{ background: "linear-gradient(-90deg, #05080f, transparent)" }}
      />

      <div
        className="absolute inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent 0px, transparent 2px, rgba(74,222,128,0.04) 2px, rgba(74,222,128,0.04) 3px)",
        }}
      />
    </div>
  );
}

/* ----------------------------- VARIANT 05 --------------------------------- */

function ThreatLevel() {
  const { nerfAgent, nerfPct, buffAgent, buffPct, context } = demo;
  return (
    <div
      className="relative overflow-hidden"
      style={{
        height: 92,
        border: "1px solid rgba(255,70,85,0.55)",
        background:
          "linear-gradient(90deg, rgba(255,70,85,0.12) 0%, rgba(13,18,32,0.9) 18%, rgba(13,18,32,0.9) 82%, rgba(79,195,247,0.1) 100%)",
      }}
    >
      <div
        className="absolute inset-y-0 left-0"
        style={{
          width: 14,
          backgroundImage:
            "repeating-linear-gradient(135deg, #FF4655 0 8px, #0d1220 8px 16px)",
          opacity: 0.85,
        }}
      />
      <div
        className="absolute inset-y-0 right-0"
        style={{
          width: 14,
          backgroundImage:
            "repeating-linear-gradient(135deg, #4FC3F7 0 8px, #0d1220 8px 16px)",
          opacity: 0.8,
        }}
      />

      <div className="absolute inset-y-0 left-[14px] right-[14px] flex items-center">
        <div
          className="flex items-center gap-3 pl-6 pr-5"
          style={{
            height: "100%",
            borderRight: "1px solid rgba(255,70,85,0.3)",
          }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" aria-hidden>
            <path d="M12 2 L22 20 L2 20 Z" fill="none" stroke="#FF4655" strokeWidth="2" />
            <path d="M12 9 V14" stroke="#FF4655" strokeWidth="2" strokeLinecap="square" />
            <path d="M12 16.5 V17.5" stroke="#FF4655" strokeWidth="2" strokeLinecap="square" />
          </svg>
          <div>
            <div className="text-[9px] tracking-[0.35em]" style={{ color: "rgba(255,70,85,0.85)" }}>
              THREAT ASSESSMENT
            </div>
            <div
              className="text-[22px] font-black tracking-[0.08em] leading-none meta-blink"
              style={{ color: "#FF4655", textShadow: "0 0 14px rgba(255,70,85,0.4)" }}
            >
              LEVEL 04
            </div>
          </div>
        </div>

        <div className="flex-1 flex items-center justify-between px-6 gap-4">
          <div>
            <div className="text-[9px] tracking-[0.35em]" style={{ color: "rgba(255,70,85,0.8)" }}>
              PRIMARY // NERF
            </div>
            <div className="flex items-baseline gap-2 leading-none">
              <span className="text-[22px] font-black text-white tracking-tight">{nerfAgent}</span>
              <span className="text-[24px] font-black tabular-nums" style={{ color: "#FF4655" }}>
                {nerfPct}%
              </span>
            </div>
            <div className="text-[10px] mt-1 tracking-[0.2em]" style={{ color: "rgba(148,163,184,0.65)" }}>
              {context}
            </div>
          </div>

          <div className="flex items-end gap-1.5 bar-anim" style={{ height: 46 }}>
            {[1, 2, 3, 4, 5].map((i) => {
              const active = i <= 4;
              const color = i <= 3 ? "#FF4655" : i === 4 ? "#FF4655" : "#334155";
              return (
                <span
                  key={i}
                  style={{
                    width: 7,
                    height: 12 + i * 7,
                    background: active ? color : "rgba(71,85,105,0.4)",
                    boxShadow: active ? `0 0 10px ${color}70` : "none",
                    display: "block",
                  }}
                />
              );
            })}
          </div>

          <div className="text-right">
            <div className="text-[9px] tracking-[0.35em]" style={{ color: "rgba(79,195,247,0.85)" }}>
              SECONDARY // BUFF
            </div>
            <div className="flex items-baseline gap-2 leading-none justify-end">
              <span className="text-[22px] font-black text-white tracking-tight">{buffAgent}</span>
              <span className="text-[24px] font-black tabular-nums" style={{ color: "#4FC3F7" }}>
                {buffPct}%
              </span>
            </div>
            <div className="text-[10px] mt-1 tracking-[0.2em]" style={{ color: "rgba(148,163,184,0.55)" }}>
              상승세 · 메타 재편 가능
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ----------------------------- shared bits -------------------------------- */

function Bracket({ pos, color }: { pos: "tl" | "tr" | "bl" | "br"; color: string }) {
  const common = "absolute w-3 h-3 pointer-events-none";
  if (pos === "tl")
    return <span className={`${common} top-0 left-0`} style={{ borderTop: `2px solid ${color}`, borderLeft: `2px solid ${color}` }} />;
  if (pos === "tr")
    return <span className={`${common} top-0 right-0`} style={{ borderTop: `2px solid ${color}`, borderRight: `2px solid ${color}` }} />;
  if (pos === "bl")
    return <span className={`${common} bottom-0 left-0`} style={{ borderBottom: `2px solid ${color}`, borderLeft: `2px solid ${color}` }} />;
  return <span className={`${common} bottom-0 right-0`} style={{ borderBottom: `2px solid ${color}`, borderRight: `2px solid ${color}` }} />;
}
