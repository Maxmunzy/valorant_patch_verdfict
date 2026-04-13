export type Verdict =
  | "nerf_rank"
  | "nerf_followup"
  | "nerf_pro"
  | "correction_nerf"
  | "buff_rank"
  | "buff_followup"
  | "buff_pro"
  | "correction_buff"
  | "rework";

export const PRED_STYLES: Record<
  string,
  { border: string; badge: string; bar: string; glow: string }
> = {
  nerf_rank:       { border: "border-red-500",    badge: "bg-red-500/20 text-red-300",      bar: "bg-red-500",    glow: "shadow-red-500/20" },
  nerf_followup:   { border: "border-red-400",    badge: "bg-red-400/20 text-red-300",      bar: "bg-red-400",    glow: "shadow-red-400/20" },
  nerf_pro:        { border: "border-red-600",    badge: "bg-red-600/20 text-red-300",      bar: "bg-red-600",    glow: "shadow-red-600/20" },
  correction_nerf: { border: "border-orange-400", badge: "bg-orange-400/20 text-orange-300", bar: "bg-orange-400", glow: "shadow-orange-400/20" },
  buff_rank:       { border: "border-blue-400",   badge: "bg-blue-400/20 text-blue-300",    bar: "bg-blue-400",   glow: "shadow-blue-400/20" },
  buff_followup:   { border: "border-blue-500",   badge: "bg-blue-500/20 text-blue-300",    bar: "bg-blue-500",   glow: "shadow-blue-500/20" },
  buff_pro:        { border: "border-cyan-400",   badge: "bg-cyan-400/20 text-cyan-300",    bar: "bg-cyan-400",   glow: "shadow-cyan-400/20" },
  correction_buff: { border: "border-indigo-400", badge: "bg-indigo-400/20 text-indigo-300", bar: "bg-indigo-400", glow: "shadow-indigo-400/20" },
  rework:          { border: "border-purple-400", badge: "bg-purple-400/20 text-purple-300", bar: "bg-purple-400", glow: "shadow-purple-400/20" },
};

export const DEFAULT_STYLE = PRED_STYLES["buff_followup"];

export const PRED_LABELS: Record<string, { ko: string; en: string; icon: string }> = {
  nerf_rank:       { ko: "너프 (랭크)",        en: "Nerf (Rank)",             icon: "🔻" },
  nerf_followup:   { ko: "너프 (추가)",        en: "Nerf (Follow-up)",        icon: "🔻" },
  nerf_pro:        { ko: "너프 (대회)",        en: "Nerf (Pro)",              icon: "🔻" },
  correction_nerf: { ko: "너프 (과버프 조정)", en: "Nerf (Over-buff Fix)",    icon: "⚠️" },
  buff_rank:       { ko: "버프 (랭크)",        en: "Buff (Rank)",             icon: "🔺" },
  buff_followup:   { ko: "버프 (추가)",        en: "Buff (Follow-up)",        icon: "🔺" },
  buff_pro:        { ko: "버프 (대회)",        en: "Buff (Pro)",              icon: "🔺" },
  correction_buff: { ko: "버프 (과너프 복구)", en: "Buff (Over-nerf Fix)",    icon: "⚠️" },
  rework:          { ko: "리워크",             en: "Rework",                  icon: "⚙️" },
};

export const AGENT_ROLE_KO: Record<string, string> = {
  Brimstone: "전략가", Viper: "전략가", Omen: "전략가",
  Astra: "전략가", Harbor: "전략가", Clove: "전략가",
  Killjoy: "감시자", Cypher: "감시자", Sage: "감시자",
  Chamber: "감시자", Deadlock: "감시자", Vyse: "감시자", Veto: "감시자",
  Miks: "전략가",
  Sova: "척후대", Fade: "척후대", Gekko: "척후대",
  Breach: "척후대", Skye: "척후대", "KAY/O": "척후대", KAYO: "척후대",
  Tejo: "척후대",
  Phoenix: "타격대", Reyna: "타격대", Raze: "타격대",
  Jett: "타격대", Neon: "타격대", Yoru: "타격대",
  Iso: "타격대", Waylay: "타격대",
};

// tag → accent color (border + text)
export const SIGNAL_TAG_COLORS: Record<string, { border: string; dot: string; label: string }> = {
  danger:   { border: "border-red-500/40",    dot: "bg-red-500",    label: "text-red-400"    },
  warning:  { border: "border-amber-500/40",  dot: "bg-amber-400",  label: "text-amber-400"  },
  positive: { border: "border-emerald-500/40",dot: "bg-emerald-400",label: "text-emerald-400"},
  neutral:  { border: "border-slate-600/60",  dot: "bg-slate-500",  label: "text-slate-300"  },
};

// type → icon character (no emoji)
export const SIGNAL_TYPE_ICON: Record<string, string> = {
  patch:      "P",
  rank:       "R",
  vct:        "V",
  analysis:   "A",
  trend:      "T",
  identity:   "I",
  causal:     "C",
  structural: "S",
};

export const SIGNAL_TYPE_COLORS: Record<string, string> = {
  patch:     "text-blue-400",
  rank:      "text-slate-300",
  vct:       "text-cyan-400",
  analysis:  "text-amber-400",
  trend:     "text-orange-400",
  identity:  "text-slate-400",
  causal:    "text-pink-400",
  structural:"text-slate-500",
};

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";
