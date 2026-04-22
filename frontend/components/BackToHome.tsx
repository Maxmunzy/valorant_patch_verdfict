import Link from "next/link";

/**
 * 모든 서브 페이지 공통 "메인으로" 뒤로가기 버튼.
 * - 텍스트/색상 통일 ("메인으로")
 * - 작은 링크가 아닌 "버튼" 느낌으로 대비 확보
 */
export default function BackToHome({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`inline-flex items-center gap-2 px-3.5 py-2 text-[12px] font-bold uppercase tracking-[0.22em] transition-all hover:brightness-125 hover:border-white/30 ${className}`}
      style={{
        color: "#CBD5E1",
        border: "1px solid rgba(100,116,139,0.55)",
        background: "rgba(13,18,32,0.7)",
      }}
    >
      <span style={{ color: "#FF4655", fontSize: "15px", lineHeight: 1 }}>←</span>
      메인으로
    </Link>
  );
}
