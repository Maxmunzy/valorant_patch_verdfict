"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * 헤더용 언어 토글.
 * - 현재 경로가 /en 으로 시작하면 KO 링크는 /en 을 벗긴 경로로.
 * - 그 외에는 EN 링크는 /en + 현재 경로.
 * - 영문 버전이 없는 경로는 안전하게 /en 루트로 폴백.
 */

// 정확히 일치해야 하는 정적 경로
const EN_SUPPORTED_EXACT: string[] = ["/", "/backtest", "/agents"];
// prefix 매칭 — dynamic 세그먼트가 있는 경로
const EN_SUPPORTED_PREFIX: string[] = ["/category/"];

function hasEnEquivalent(koPath: string): boolean {
  if (EN_SUPPORTED_EXACT.includes(koPath)) return true;
  return EN_SUPPORTED_PREFIX.some((p) => koPath.startsWith(p));
}

export default function LangToggle() {
  const pathname = usePathname() || "/";
  const isEn = pathname === "/en" || pathname.startsWith("/en/");

  // KO 경로 계산
  const koPath = isEn
    ? pathname === "/en"
      ? "/"
      : pathname.replace(/^\/en/, "") || "/"
    : pathname;

  // EN 경로 계산 — 지원되지 않는 경로면 /en 루트로
  const strippedForEn = isEn ? koPath : pathname;
  const enPath = hasEnEquivalent(strippedForEn)
    ? strippedForEn === "/"
      ? "/en"
      : `/en${strippedForEn}`
    : "/en";

  return (
    <div
      className="inline-flex items-center text-[10px] font-bold tracking-[0.2em] select-none"
      style={{ border: "1px solid rgba(30,41,59,0.8)", background: "rgba(13,18,32,0.6)" }}
    >
      <Link
        href={koPath}
        aria-label="한국어"
        className="px-2 py-0.5 transition-colors"
        style={{
          background: !isEn ? "#FF4655" : "transparent",
          color: !isEn ? "#fff" : "rgba(148,163,184,0.7)",
        }}
      >
        KO
      </Link>
      <span style={{ color: "rgba(51,65,85,0.8)" }}>|</span>
      <Link
        href={enPath}
        aria-label="English"
        className="px-2 py-0.5 transition-colors"
        style={{
          background: isEn ? "#FF4655" : "transparent",
          color: isEn ? "#fff" : "rgba(148,163,184,0.7)",
        }}
      >
        EN
      </Link>
    </div>
  );
}
