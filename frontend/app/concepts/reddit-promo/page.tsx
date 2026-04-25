import Image from "next/image";
import { getAllPredictions, AgentPrediction } from "@/lib/api";
import { getBacktestSummary } from "@/lib/backtest";
import { agentPortrait } from "@/lib/agents";
import { buildShareHeadline } from "@/lib/headline";

const ROLE_EN: Record<string, string> = {
  "타격대": "DUELIST",
  "감시자": "SENTINEL",
  "척후대": "INITIATOR",
  "전략가": "CONTROLLER",
};

/**
 * 레딧/트위터 공유용 합성 스크린샷 페이지.
 *
 * 스샷 가이드:
 *  - 브라우저 크기: 1280x900 권장 (16:10). 풀스크린 스샷 그대로 레딧 프리뷰에 박기 좋음.
 *  - `.shot` 컨테이너만 크롭해도 됨 (16:10 비율 유지).
 *  - URL 워터마크 whosnxt.app 좌하단, 패치 태그 우하단.
 *
 * 내용:
 *  - 상단: 브랜드 + 한 줄 요약 (BACKTEST HIT RATE / LAST ACT)
 *  - 중단 좌: Top Nerf 큰 포트레이트 + %
 *  - 중단 우: Top Buff 큰 포트레이트 + %
 *  - 하단: per-act 라인 차트 (마지막 액트 하이라이트)
 */

export const revalidate = 60;

export const metadata = {
  title: "Reddit promo frame",
  robots: { index: false },
};

export default async function RedditPromo() {
  const [agents, backtest] = await Promise.all([
    getAllPredictions().catch(() => [] as AgentPrediction[]),
    getBacktestSummary().catch(() => null),
  ]);

  const topNerf = agents.find((a) => a.verdict.includes("nerf")) ?? null;
  const topBuff = agents.find((a) => a.verdict.includes("buff")) ?? null;

  const last = backtest?.perAct?.[backtest.perAct.length - 1] ?? null;
  const lastHit = last ? Math.round(last.hit_dir * 100) : null;
  const lastN = last ? last.n : null;
  const lastHitCount = last ? Math.round(last.hit_dir * last.n) : null;
  const hit3 = backtest ? Math.round(backtest.overall.hitRate3 * 100) : null;

  return (
    <div
      style={{
        background: "#05080f",
        minHeight: "100vh",
        padding: "40px 0",
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        className="shot"
        style={{
          width: 1280,
          height: 800,
          position: "relative",
          background:
            "radial-gradient(circle at 18% 20%, rgba(255,70,85,0.12) 0%, transparent 45%), radial-gradient(circle at 82% 80%, rgba(79,195,247,0.1) 0%, transparent 45%), #0a0e18",
          border: "1px solid rgba(71,85,105,0.55)",
          color: "#e2e8f0",
          overflow: "hidden",
          fontFamily: "ui-sans-serif, system-ui, sans-serif",
        }}
      >
        {/* top color strip */}
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: 4,
            background: "linear-gradient(90deg, #FF4655 0%, #FBBF24 50%, #4FC3F7 100%)",
          }}
        />

        {/* header band */}
        <div
          style={{
            padding: "36px 56px 16px",
            borderBottom: "1px solid rgba(71,85,105,0.35)",
          }}
        >
          <div
            style={{
              fontSize: 13,
              letterSpacing: 6,
              color: "rgba(148,163,184,0.75)",
              fontWeight: 800,
              marginBottom: 10,
            }}
          >
            WHOSNXT.APP · VALORANT PATCH PREDICTOR · XGBOOST 2-STAGE
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 22, flexWrap: "wrap" }}>
            <div
              style={{
                fontSize: 60,
                fontWeight: 900,
                letterSpacing: -1,
                color: "#fff",
                lineHeight: 0.95,
              }}
            >
              Who gets <span style={{ color: "#FF4655" }}>nerfed</span> next?
            </div>
            {lastHit !== null && (
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "baseline",
                  gap: 10,
                  padding: "10px 16px",
                  border: "1px solid rgba(74,222,128,0.5)",
                  background: "rgba(74,222,128,0.09)",
                }}
              >
                <span
                  style={{
                    fontSize: 10,
                    letterSpacing: 4,
                    color: "rgba(74,222,128,0.9)",
                    fontWeight: 800,
                  }}
                >
                  LAST PATCH HIT
                </span>
                <span
                  style={{
                    fontSize: 34,
                    fontWeight: 900,
                    color: "#4ADE80",
                    fontVariantNumeric: "tabular-nums",
                    lineHeight: 1,
                  }}
                >
                  {lastHitCount}/{lastN}
                </span>
                <span
                  style={{
                    fontSize: 16,
                    fontWeight: 800,
                    color: "#4ADE80",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  ({lastHit}%)
                </span>
              </div>
            )}
          </div>
        </div>

        {/* main — 2 hero cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 16,
            padding: "20px 56px",
          }}
        >
          {topNerf && <PromoCard agent={topNerf} rank="#1 NERF" accent="#FF4655" kind="nerf" />}
          {topBuff && <PromoCard agent={topBuff} rank="#1 BUFF" accent="#4FC3F7" kind="buff" />}
        </div>

        {/* per-act chart strip */}
        {backtest && backtest.perAct.length >= 2 && (
          <div style={{ padding: "0 56px 16px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "baseline",
                justifyContent: "space-between",
                marginBottom: 6,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: 4,
                  fontWeight: 800,
                  color: "rgba(251,191,36,0.9)",
                }}
              >
                PER-ACT HIT RATE · WALK-FORWARD BACKTEST
              </div>
              <div style={{ fontSize: 11, color: "rgba(148,163,184,0.7)", letterSpacing: 2 }}>
                overall 3-class {hit3}% · random 33% baseline
              </div>
            </div>
            <PerActChart perAct={backtest.perAct} />
          </div>
        )}

        {/* footer */}
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            padding: "14px 56px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderTop: "1px solid rgba(71,85,105,0.35)",
            background: "rgba(5,8,15,0.85)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 10,
                height: 10,
                background: "#FF4655",
                transform: "rotate(45deg)",
                boxShadow: "0 0 10px 2px rgba(255,70,85,0.5)",
              }}
            />
            <span style={{ fontSize: 14, fontWeight: 900, letterSpacing: 3, color: "#fff" }}>
              WHOSNXT.APP
            </span>
            <span style={{ fontSize: 11, color: "rgba(148,163,184,0.7)", letterSpacing: 2 }}>
              data: Diamond+ ranked · VCT · patch notes
            </span>
          </div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: 3,
              color: "rgba(74,222,128,0.85)",
              padding: "4px 10px",
              border: "1px solid rgba(74,222,128,0.4)",
              background: "rgba(74,222,128,0.06)",
            }}
          >
            LIVE · V26A2
          </div>
        </div>

        {/* corner brackets */}
        <Corner pos="tl" />
        <Corner pos="tr" />
        <Corner pos="bl" />
        <Corner pos="br" />
      </div>
    </div>
  );
}

function PromoCard({
  agent,
  rank,
  accent,
  kind,
}: {
  agent: AgentPrediction;
  rank: string;
  accent: string;
  kind: "nerf" | "buff";
}) {
  const portrait = agentPortrait(agent.agent);
  const headline = buildShareHeadline(agent, "en");
  const pct = kind === "nerf" ? agent.p_nerf : agent.p_buff;

  return (
    <div
      style={{
        position: "relative",
        height: 330,
        border: `1px solid ${accent}60`,
        background: `linear-gradient(135deg, ${accent}15, rgba(13,18,32,0.92) 70%)`,
        overflow: "hidden",
      }}
    >
      {portrait && (
        <div
          style={{
            position: "absolute",
            top: 0,
            bottom: 0,
            right: 0,
            width: "56%",
            zIndex: 0,
          }}
        >
          <Image
            src={portrait}
            alt={agent.agent}
            fill
            sizes="600px"
            style={{ objectFit: "cover", objectPosition: "center 22%", opacity: 0.62 }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "linear-gradient(to right, rgba(13,18,32,0.94) 0%, rgba(13,18,32,0.4) 45%, transparent 85%)",
            }}
          />
        </div>
      )}

      {/* top color line */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 2,
          background: `linear-gradient(90deg, ${accent}, ${accent}40, transparent)`,
          zIndex: 2,
        }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 3,
          height: "100%",
          padding: 28,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <span
            style={{
              fontSize: 11,
              letterSpacing: 5,
              fontWeight: 900,
              color: accent,
              border: `1px solid ${accent}70`,
              padding: "5px 10px",
              background: `${accent}14`,
            }}
          >
            {rank}
          </span>
          <span
            style={{
              fontSize: 10,
              letterSpacing: 4,
              color: "rgba(148,163,184,0.8)",
              fontWeight: 700,
              paddingTop: 6,
            }}
          >
            {ROLE_EN[agent.role ?? ""] ?? agent.role?.toUpperCase()}
          </span>
        </div>

        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, flexWrap: "wrap" }}>
            <span
              style={{
                fontSize: 96,
                fontWeight: 900,
                color: accent,
                lineHeight: 0.9,
                fontVariantNumeric: "tabular-nums",
                textShadow: `0 0 24px ${accent}66`,
              }}
            >
              {Math.round(pct)}%
            </span>
            <span
              style={{
                fontSize: 44,
                fontWeight: 900,
                color: "#fff",
                letterSpacing: -0.5,
                lineHeight: 1,
              }}
            >
              {agent.agent}
            </span>
          </div>
          <div
            style={{
              fontSize: 13,
              color: "rgba(226,232,240,0.9)",
              marginTop: 10,
              lineHeight: 1.4,
              maxWidth: "80%",
            }}
          >
            {headline}
          </div>
        </div>
      </div>

      {/* corner bracket */}
      <div
        style={{
          position: "absolute",
          top: 12,
          left: 12,
          width: 14,
          height: 14,
          borderTop: `2px solid ${accent}`,
          borderLeft: `2px solid ${accent}`,
          zIndex: 4,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 12,
          right: 12,
          width: 14,
          height: 14,
          borderBottom: `2px solid ${accent}80`,
          borderRight: `2px solid ${accent}80`,
          zIndex: 4,
        }}
      />
    </div>
  );
}

function PerActChart({
  perAct,
}: {
  perAct: { act: string; n: number; hit_dir: number }[];
}) {
  const W = 1168;
  const H = 160;
  const padL = 44;
  const padR = 20;
  const padT = 14;
  const padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const n = perAct.length;
  const avg = perAct.reduce((s, r) => s + r.hit_dir, 0) / Math.max(n, 1);
  const xOf = (i: number) => padL + (i * innerW) / Math.max(n - 1, 1);
  const yOf = (v: number) => padT + innerH - v * innerH;

  const path = perAct
    .map((r, i) => `${i === 0 ? "M" : "L"}${xOf(i).toFixed(1)},${yOf(r.hit_dir).toFixed(1)}`)
    .join(" ");

  const lastIdx = n - 1;
  const lastR = perAct[lastIdx];
  const labelStep = Math.max(1, Math.ceil(n / 10));

  return (
    <div
      style={{
        border: "1px solid rgba(51,65,85,0.55)",
        background: "rgba(13,18,32,0.55)",
        padding: "10px 14px 4px",
      }}
    >
      <svg width="100%" viewBox={`0 0 ${W} ${H}`}>
        {[0, 0.33, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line
              x1={padL}
              x2={W - padR}
              y1={yOf(v)}
              y2={yOf(v)}
              stroke={v === 0.33 ? "rgba(251,191,36,0.45)" : "rgba(51,65,85,0.35)"}
              strokeWidth={1}
              strokeDasharray={v === 0.33 ? "4 4" : undefined}
            />
            <text
              x={padL - 6}
              y={yOf(v)}
              fontSize="11"
              fill={v === 0.33 ? "rgba(251,191,36,0.8)" : "rgba(148,163,184,0.75)"}
              textAnchor="end"
              dominantBaseline="middle"
              fontFamily="ui-monospace, monospace"
            >
              {Math.round(v * 100)}%
            </text>
          </g>
        ))}

        {/* avg line */}
        <line
          x1={padL}
          x2={W - padR}
          y1={yOf(avg)}
          y2={yOf(avg)}
          stroke="rgba(148,163,184,0.55)"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        <path
          d={path}
          fill="none"
          stroke="#4ADE80"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ filter: "drop-shadow(0 0 3px #4ADE8066)" }}
        />

        {perAct.map((r, i) => {
          const isLast = i === lastIdx;
          return (
            <circle
              key={r.act}
              cx={xOf(i)}
              cy={yOf(r.hit_dir)}
              r={isLast ? 5 : 3}
              fill={isLast ? "#FBBF24" : "#4ADE80"}
              stroke={isLast ? "#FBBF24" : "none"}
              strokeWidth={isLast ? 2 : 0}
            />
          );
        })}

        {lastR && (
          <g>
            <text
              x={xOf(lastIdx) - 4}
              y={yOf(lastR.hit_dir) - 12}
              fontSize="12"
              fill="#FBBF24"
              textAnchor="end"
              fontWeight="900"
              fontFamily="ui-monospace, monospace"
            >
              {lastR.act} · {Math.round(lastR.hit_dir * 100)}%
            </text>
          </g>
        )}

        {perAct.map((r, i) => {
          if (i % labelStep !== 0 && i !== lastIdx) return null;
          return (
            <text
              key={r.act}
              x={xOf(i)}
              y={H - padB + 16}
              fontSize="10"
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

function Corner({ pos }: { pos: "tl" | "tr" | "bl" | "br" }) {
  const sz = 14;
  const color = "rgba(148,163,184,0.55)";
  const style: React.CSSProperties = { position: "absolute", width: sz, height: sz, pointerEvents: "none" };
  if (pos === "tl")
    return <div style={{ ...style, top: 6, left: 6, borderTop: `1px solid ${color}`, borderLeft: `1px solid ${color}` }} />;
  if (pos === "tr")
    return <div style={{ ...style, top: 6, right: 6, borderTop: `1px solid ${color}`, borderRight: `1px solid ${color}` }} />;
  if (pos === "bl")
    return <div style={{ ...style, bottom: 6, left: 6, borderBottom: `1px solid ${color}`, borderLeft: `1px solid ${color}` }} />;
  return <div style={{ ...style, bottom: 6, right: 6, borderBottom: `1px solid ${color}`, borderRight: `1px solid ${color}` }} />;
}
