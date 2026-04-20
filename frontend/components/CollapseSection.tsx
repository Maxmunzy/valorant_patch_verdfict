"use client";

import { useState, useEffect, ReactNode } from "react";

/**
 * 클릭해서 펼치고 접을 수 있는 섹션 래퍼.
 * stable 리스트처럼 정보 밀도를 줄이고 싶은 영역에 사용.
 *
 * storageKey 를 주면 sessionStorage 에 펼침/접힘 상태가 저장되어
 * 카드 클릭 → 상세 페이지 → 뒤로가기 왕복 시에도 펼쳐놨던 섹션이 유지된다.
 * (탭 닫으면 초기화)
 */
export default function CollapseSection({
  defaultOpen = false,
  storageKey,
  header,
  children,
}: {
  defaultOpen?: boolean;
  storageKey?: string;
  header: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  // SSR → CSR 하이드레이션 후 sessionStorage에서 복원
  useEffect(() => {
    if (!storageKey) return;
    try {
      const stored = sessionStorage.getItem(storageKey);
      if (stored === "1") setOpen(true);
      else if (stored === "0") setOpen(false);
    } catch {
      // sessionStorage 접근 실패시 무시 (프라이빗 모드 등)
    }
  }, [storageKey]);

  // 상태 변경시 저장
  useEffect(() => {
    if (!storageKey) return;
    try {
      sessionStorage.setItem(storageKey, open ? "1" : "0");
    } catch {
      // 무시
    }
  }, [open, storageKey]);

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
