import Link from "next/link";
import type { Locale } from "@/lib/i18n/dict";
import { getDict } from "@/lib/i18n/dict";

/**
 * 모든 서브 페이지 공통 "메인으로" 뒤로가기 버튼.
 * locale 에 따라 EN 페이지에선 "Back to home" + /en 으로 향함.
 */
export default function BackToHome({
  className = "",
  locale = "ko",
}: {
  className?: string;
  locale?: Locale;
}) {
  const t = getDict(locale).common;
  const href = locale === "en" ? "/en" : "/";
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 px-3.5 py-2 text-[12px] font-bold uppercase tracking-[0.22em] transition-all hover:brightness-125 hover:border-white/30 ${className}`}
      style={{
        color: "#CBD5E1",
        border: "1px solid rgba(100,116,139,0.55)",
        background: "rgba(13,18,32,0.7)",
      }}
    >
      <span style={{ color: "#FF4655", fontSize: "15px", lineHeight: 1 }}>←</span>
      {t.backHome}
    </Link>
  );
}
