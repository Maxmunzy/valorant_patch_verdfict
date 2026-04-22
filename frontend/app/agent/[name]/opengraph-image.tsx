import { ImageResponse } from "next/og";
import { getAgentPrediction } from "@/lib/api";
import { agentPortrait } from "@/lib/agents";

// Next.js 16 file convention — 이 파일이 존재하는 라우트의 OG 이미지를 동적 생성.
// /agent/[name] 링크를 공유하면 디스코드/트위터/슬랙 미리보기에 이 이미지가 박힘.

export const alt = "Valorant Patch Verdict — Agent";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// 동적 데이터에 의존 — 라우트 revalidate 정책(60초)을 따라간다.
export const revalidate = 60;

function pickVerdict(p_nerf: number, p_buff: number, p_stable: number) {
  const entries: [string, number, string][] = [
    ["NERF", p_nerf, "#FF4655"],
    ["BUFF", p_buff, "#4FC3F7"],
    ["STABLE", p_stable, "#94A3B8"],
  ];
  entries.sort((a, b) => b[1] - a[1]);
  const [label, prob, color] = entries[0];
  return { label, prob, color };
}

export default async function Image({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const agentName = decodeURIComponent(name);

  // 데이터 로딩 실패해도 OG 이미지는 fallback 으로 그려냄 (빌드 실패 방지).
  let verdict = "STABLE";
  let prob = 0;
  let color = "#94A3B8";
  let role = "";

  try {
    const data = await getAgentPrediction(agentName);
    const v = pickVerdict(data.p_nerf, data.p_buff, data.p_stable);
    verdict = v.label;
    prob = v.prob;
    color = v.color;
    role = data.role || "";
  } catch {
    // fallback 유지
  }

  const portrait = agentPortrait(agentName);
  const pct = Math.round(prob * 100);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#0a0e18",
          color: "#e2e8f0",
          fontFamily: "sans-serif",
          position: "relative",
        }}
      >
        {/* 왼쪽 포트레이트 영역 */}
        <div
          style={{
            width: "58%",
            height: "100%",
            position: "relative",
            display: "flex",
            background: "#0d1220",
          }}
        >
          {portrait && (
            <img
              src={portrait}
              alt=""
              width={696}
              height={630}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                objectPosition: "center 22%",
                opacity: 0.9,
              }}
            />
          )}
          {/* 왼쪽-오른쪽 페이드 — 인물에서 우측 텍스트 영역으로 자연스럽게 이어지도록 */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              background:
                "linear-gradient(to right, rgba(13,18,32,0.15) 0%, rgba(13,18,32,0.1) 55%, #0a0e18 95%, #0a0e18 100%)",
            }}
          />
          {/* 상단 컬러 스트립 */}
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 6,
              background: color,
              display: "flex",
            }}
          />
        </div>

        {/* 오른쪽 텍스트 영역 */}
        <div
          style={{
            width: "42%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            padding: "52px 56px",
            background: "#0a0e18",
            position: "relative",
          }}
        >
          {/* 상단: 브랜드 바 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                fontSize: 18,
                letterSpacing: 6,
                color: "#FF4655",
                fontWeight: 900,
              }}
            >
              <div
                style={{
                  width: 10,
                  height: 10,
                  transform: "rotate(45deg)",
                  background: "#FF4655",
                  display: "flex",
                }}
              />
              PATCH / VERDICT
            </div>
            <div
              style={{
                fontSize: 14,
                letterSpacing: 5,
                color: "rgba(148,163,184,0.75)",
                fontWeight: 700,
              }}
            >
              VALORANT · XGBOOST 2-STAGE
            </div>
          </div>

          {/* 중앙: 판정 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div
              style={{
                fontSize: 22,
                letterSpacing: 8,
                color: color,
                fontWeight: 900,
                display: "flex",
              }}
            >
              VERDICT · {verdict}
            </div>
            <div
              style={{
                fontSize: 220,
                lineHeight: 1,
                color: color,
                fontWeight: 900,
                fontVariantNumeric: "tabular-nums",
                letterSpacing: -6,
                display: "flex",
                textShadow: `0 0 40px ${color}80`,
              }}
            >
              {pct}%
            </div>
            <div
              style={{
                fontSize: 84,
                color: "#ffffff",
                fontWeight: 900,
                letterSpacing: -2,
                display: "flex",
                marginTop: 4,
              }}
            >
              {agentName.toUpperCase()}
            </div>
            {role && (
              <div
                style={{
                  fontSize: 18,
                  letterSpacing: 8,
                  color: "rgba(148,163,184,0.7)",
                  fontWeight: 700,
                  marginTop: 4,
                  display: "flex",
                }}
              >
                {role}
              </div>
            )}
          </div>

          {/* 하단: URL */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 16,
              letterSpacing: 5,
              color: "rgba(148,163,184,0.55)",
              fontWeight: 700,
              borderTop: "1px solid rgba(71,85,105,0.4)",
              paddingTop: 16,
            }}
          >
            <div style={{ display: "flex" }}>WHOSNXT.APP</div>
            <div style={{ display: "flex", color: `${color}cc` }}>▸ 상세 분석</div>
          </div>

          {/* 우측 상단 액센트 블럭 */}
          <div
            style={{
              position: "absolute",
              top: 52,
              right: 56,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 60,
              height: 60,
              transform: "rotate(45deg)",
              border: `2px solid ${color}`,
              background: `${color}15`,
            }}
          />
        </div>

        {/* 코너 브래킷 4개 */}
        <div
          style={{
            position: "absolute",
            top: 24,
            left: 24,
            width: 20,
            height: 20,
            borderTop: `3px solid ${color}`,
            borderLeft: `3px solid ${color}`,
            display: "flex",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 24,
            right: 24,
            width: 20,
            height: 20,
            borderTop: `3px solid ${color}`,
            borderRight: `3px solid ${color}`,
            display: "flex",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: 24,
            left: 24,
            width: 20,
            height: 20,
            borderBottom: `3px solid ${color}80`,
            borderLeft: `3px solid ${color}80`,
            display: "flex",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: 24,
            right: 24,
            width: 20,
            height: 20,
            borderBottom: `3px solid ${color}80`,
            borderRight: `3px solid ${color}80`,
            display: "flex",
          }}
        />
      </div>
    ),
    {
      ...size,
    },
  );
}
