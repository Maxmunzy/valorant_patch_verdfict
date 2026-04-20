"use client";

import { useState, ReactNode } from "react";

/**
 * 클릭해서 펼치고 접을 수 있는 섹션 래퍼.
 * stable 리스트처럼 정보 밀도를 줄이고 싶은 영역에 사용.
 */
export default function CollapseSection({
  defaultOpen = false,
  header,
  children,
}: {
  defaultOpen?: boolean;
  header: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left flex items-center gap-2 group cursor-pointer"
        aria-expanded={open}
      >
        <div className="flex-1">{header}</div>
        <span
          className="text-[10px] font-valo tracking-widest px-2 py-1 transition-colors"
          style={{
            border: "1px solid rgba(100,116,139,0.4)",
            color: open ? "#cbd5e1" : "rgba(148,163,184,0.75)",
            background: "rgba(13,18,32,0.6)",
          }}
        >
          {open ? "▲ HIDE" : "▼ SHOW"}
        </span>
      </button>
      {open && <div>{children}</div>}
    </div>
  );
}
