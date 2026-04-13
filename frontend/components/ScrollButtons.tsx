"use client";

const BUTTONS = [
  { label: "🔻 너프 예상 보기", target: "nerf", color: "border-red-500/50 text-red-400 hover:bg-red-500/10" },
  { label: "🔺 버프 예상 보기", target: "buff", color: "border-blue-500/50 text-blue-400 hover:bg-blue-500/10" },
  { label: "⚙️ 리워크", target: "rework", color: "border-purple-500/50 text-purple-400 hover:bg-purple-500/10" },
  { label: "✅ 안정", target: "stable", color: "border-slate-600 text-slate-400 hover:bg-slate-700/40" },
];

export default function ScrollButtons() {
  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="flex flex-wrap justify-center gap-3 pt-2">
      {BUTTONS.map(({ label, target, color }) => (
        <button
          key={target}
          onClick={() => scrollTo(target)}
          className={`rounded-lg border px-5 py-2.5 text-sm font-medium transition-colors cursor-pointer ${color}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
