import Link from "next/link";
import Image from "next/image";
import { agentPortrait } from "@/lib/agents";

// 요원별 초상화 크롭 위치 미세조정 — 기본값 22%
// 공식 CDN 이미지마다 얼굴·몸통 위치가 조금씩 다르기 때문
const PORTRAIT_Y_OVERRIDE: Record<string, string> = {
  KAYO: "15%",
};

function portraitOffsetY(agent?: string | null): string {
  const y = (agent && PORTRAIT_Y_OVERRIDE[agent]) ?? "22%";
  return `center ${y}`;
}

interface Props {
  href: string;
  tag: string;
  title: string;
  sub: string;
  color: string;
  agentName?: string | null;
  enterLabel?: string;
}

export default function NavButton({
  href,
  tag,
  title,
  sub,
  color,
  agentName,
  enterLabel = "ENTER",
}: Props) {
  const portrait = agentName ? agentPortrait(agentName) : null;
  return (
    <Link
      href={href}
      className="group relative block overflow-hidden transition-all hover:brightness-110"
      style={{
        border: `1px solid ${color}40`,
        background: `linear-gradient(90deg, ${color}12 0%, rgba(13,18,32,0.65) 55%, ${color}06 100%)`,
      }}
    >
      {/* 요원 초상화 — 우측 배경 */}
      {portrait && (
        <div
          className="absolute top-0 bottom-0 right-0 pointer-events-none"
          style={{ width: "45%", zIndex: 0 }}
        >
          <Image
            src={portrait}
            alt=""
            fill
            className="object-cover opacity-30 group-hover:opacity-45 transition-opacity duration-300"
            style={{ objectPosition: portraitOffsetY(agentName) }}
            sizes="500px"
          />
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to right, rgba(13,18,32,0.95) 0%, rgba(13,18,32,0.5) 40%, rgba(13,18,32,0.15) 75%, transparent 100%)",
            }}
          />
        </div>
      )}

      {/* corner brackets */}
      <span
        className="absolute top-0 left-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderTop: `2px solid ${color}`, borderLeft: `2px solid ${color}` }}
      />
      <span
        className="absolute top-0 right-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderTop: `2px solid ${color}80`, borderRight: `2px solid ${color}80` }}
      />
      <span
        className="absolute bottom-0 left-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderBottom: `2px solid ${color}`, borderLeft: `2px solid ${color}` }}
      />
      <span
        className="absolute bottom-0 right-0 w-3 h-3 pointer-events-none"
        style={{ zIndex: 5, borderBottom: `2px solid ${color}80`, borderRight: `2px solid ${color}80` }}
      />

      <div className="relative flex items-center justify-between gap-4 px-5 sm:px-7 py-3.5 sm:py-4" style={{ zIndex: 10 }}>
        <div className="flex items-center gap-4 sm:gap-5 min-w-0">
          <span
            className="hidden sm:block shrink-0"
            style={{
              width: "2px",
              height: "32px",
              background: `linear-gradient(to bottom, ${color}, ${color}30)`,
            }}
          />
          <div className="min-w-0">
            <div className="text-[9px] tracking-[0.35em] mb-1" style={{ color: `${color}cc` }}>
              {tag}
            </div>
            <div className="text-xl sm:text-2xl font-black tracking-tight text-white leading-none">
              {title}
            </div>
            <div
              className="text-[11px] mt-1.5 tracking-wide truncate"
              style={{ color: "rgba(148,163,184,0.85)" }}
            >
              {sub}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <span
            className="hidden sm:inline text-[10px] font-bold tracking-[0.3em]"
            style={{ color: `${color}bf` }}
          >
            {enterLabel}
          </span>
          <span
            className="text-xl sm:text-3xl font-black leading-none transition-transform group-hover:translate-x-1"
            style={{ color, textShadow: `0 0 14px ${color}66` }}
          >
            ▶
          </span>
        </div>
      </div>
    </Link>
  );
}
