export type Verdict =
  | "mild_nerf"
  | "strong_nerf"
  | "mild_buff"
  | "strong_buff"
  | "stable"
  | "rework";

export const PRED_STYLES: Record<
  string,
  { border: string; badge: string; bar: string; glow: string }
> = {
  mild_nerf:   { border: "border-red-400", badge: "bg-red-400/15 text-red-300", bar: "bg-red-400", glow: "shadow-red-400/20" },
  strong_nerf: { border: "border-red-500", badge: "bg-red-500/20 text-red-200", bar: "bg-red-500", glow: "shadow-red-500/25" },
  mild_buff:   { border: "border-sky-400", badge: "bg-sky-400/15 text-sky-300", bar: "bg-sky-400", glow: "shadow-sky-400/20" },
  strong_buff: { border: "border-cyan-400", badge: "bg-cyan-400/20 text-cyan-200", bar: "bg-cyan-400", glow: "shadow-cyan-400/25" },
  stable:      { border: "border-slate-500", badge: "bg-slate-500/15 text-slate-300", bar: "bg-slate-500", glow: "shadow-slate-500/20" },
  rework:      { border: "border-violet-400", badge: "bg-violet-400/20 text-violet-200", bar: "bg-violet-400", glow: "shadow-violet-400/25" },
};

export const DEFAULT_STYLE = PRED_STYLES.stable;

export const PRED_LABELS: Record<string, { ko: string; en: string; icon: string }> = {
  mild_nerf:   { ko: "너프 신호", en: "Mild Nerf", icon: "N" },
  strong_nerf: { ko: "강한 너프", en: "Strong Nerf", icon: "N+" },
  mild_buff:   { ko: "버프 신호", en: "Mild Buff", icon: "B" },
  strong_buff: { ko: "강한 버프", en: "Strong Buff", icon: "B+" },
  stable:      { ko: "안정", en: "Stable", icon: "S" },
  rework:      { ko: "리워크", en: "Rework", icon: "R" },
};

export const AGENT_ROLE_KO: Record<string, string> = {
  Brimstone: "전략가",
  Viper: "전략가",
  Omen: "전략가",
  Astra: "전략가",
  Harbor: "전략가",
  Clove: "전략가",
  Killjoy: "감시자",
  Cypher: "감시자",
  Sage: "감시자",
  Chamber: "감시자",
  Deadlock: "감시자",
  Vyse: "감시자",
  Veto: "감시자",
  Miks: "전략가",
  Sova: "척후대",
  Fade: "척후대",
  Gekko: "척후대",
  Breach: "척후대",
  Skye: "척후대",
  "KAY/O": "척후대",
  KAYO: "척후대",
  Tejo: "척후대",
  Phoenix: "타격대",
  Reyna: "타격대",
  Raze: "타격대",
  Jett: "타격대",
  Neon: "타격대",
  Yoru: "타격대",
  Iso: "타격대",
  Waylay: "타격대",
};

export const SIGNAL_TAG_COLORS: Record<string, { border: string; dot: string; label: string }> = {
  danger: { border: "border-red-500/40", dot: "bg-red-500", label: "text-red-400" },
  warning: { border: "border-amber-500/40", dot: "bg-amber-400", label: "text-amber-400" },
  positive: { border: "border-emerald-500/40", dot: "bg-emerald-400", label: "text-emerald-400" },
  neutral: { border: "border-slate-600/60", dot: "bg-slate-500", label: "text-slate-300" },
};

export const SIGNAL_TYPE_ICON: Record<string, string> = {
  patch: "P",
  rank: "R",
  vct: "V",
  analysis: "A",
  trend: "T",
  identity: "I",
  causal: "C",
  structural: "S",
};

export const SIGNAL_TYPE_COLORS: Record<string, string> = {
  patch: "text-blue-400",
  rank: "text-slate-300",
  vct: "text-cyan-400",
  analysis: "text-amber-400",
  trend: "text-orange-400",
  identity: "text-slate-400",
  causal: "text-pink-400",
  structural: "text-slate-500",
};

export const API_BASE =
  typeof window === "undefined"
    ? (process.env.BACKEND_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_BASE ?? "/api");
