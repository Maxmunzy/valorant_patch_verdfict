"use client";

import { useState, useEffect, useCallback } from "react";
import Image from "next/image";
import {
  getAgentSkills,
  runSimulation,
  getSimAnalysis,
  AgentSkills,
  SkillSlot,
  SimStatChange,
  SimResult,
} from "@/lib/api";
import { agentIcon, AGENT_UUID } from "@/lib/agents";
import { AGENT_ROLE_KO } from "@/lib/constants";
import BackToHome from "@/components/BackToHome";

const SLOT_COLOR: Record<string, string> = { C: "#66BB6A", Q: "#42A5F5", E: "#FFA726", X: "#EF5350" };
const SLOT_LABEL: Record<string, string> = { C: "C", Q: "Q", E: "E · 시그니처", X: "X · 궁극기" };

const ROLE_ORDER = ["타격대", "척후대", "전략가", "감시자"];
const ROLE_COLOR: Record<string, string> = { "타격대": "#FF4655", "척후대": "#4FC3F7", "전략가": "#66BB6A", "감시자": "#FFA726" };

// 한국어 스킬 이름은 /agent-skills API 응답의 name_ko 필드에서 가져옴

// ─── 한국어 스탯 이름 ────────────────────────────────────────────────────────────
const STAT_NAME_KO: Record<string, string> = {
  // ── 메타 스탯 ──
  charges: "충전 수", creds: "가격", ult_points: "궁극기 포인트",
  // ── 시간 계열 (빈도순) ──
  "Unequip time": "해제 시간", "Equip time": "장착 시간",
  "Windup time": "시전 시간", "Duration": "지속 시간",
  "Deploy time": "배치 시간", "Windup": "시전 시간",
  "Concuss duration": "기절 시간", "Slow duration": "둔화 시간",
  "Teleport duration": "텔레포트 시간", "Nearsight duration": "근시 시간",
  "Deactivation time": "비활성화 시간", "Buff duration": "버프 시간",
  "Vulnerable duration": "취약 시간", "Revive duration": "부활 시간",
  "Max blind duration": "최대 실명 시간", "Max flash duration": "최대 섬광 시간",
  "Max duration": "최대 지속 시간", "Search duration": "탐색 시간",
  "Debuff duration": "디버프 시간", "Channel time": "채널링 시간",
  "Cast time": "시전 시간", "Deployment time": "배치 시간",
  "Reequip time": "재장착 시간", "Quick equip time": "빠른 장착",
  "Recall duration": "회수 시간", "Recall time": "회수 시간",
  "Reactivation time": "재활성화 시간", "Activation windup": "활성화 시전",
  "Activation windup time": "활성화 시전 시간", "Detain duration": "구속 시간",
  "Suppression duration": "억제 시간", "Suppress duration": "억제 시간",
  "Resurrection timer": "부활 타이머", "Initial windup time": "초기 시전 시간",
  "Initial summon time": "초기 소환 시간", "Maximum air time": "최대 체공 시간",
  "Empowered Duration": "강화 지속 시간", "Empowered duration": "강화 지속 시간",
  "Dash Duration": "대시 시간", "Dash duration": "대시 시간",
  "Healing duration": "회복 지속 시간", "Activation duration": "활성화 시간",
  "Cocoon duration": "고치 시간", "Eye duration": "눈 지속 시간",
  "Trail duration": "궤적 시간", "Tether Duration": "속박 시간",
  "Zone Duration": "구역 시간", "Wall Dissolve Duration": "벽 소멸 시간",
  "Slide duration": "슬라이드 시간", "Stabilization duration": "안정화 시간",
  "Overloaded Duration": "과부하 시간", "Downed Duration": "다운 시간",
  "Round Start windup time": "라운드 시작 시전",
  "Activation animation duration": "활성화 애니메이션",
  "Windup times": "시전 시간", "Windup time on bounce": "반사 시전 시간",
  "Max windup time": "최대 시전 시간", "Windup time per charge": "차지별 시전 시간",
  "Flash windup time": "섬광 시전 시간", "Flash activation windup time": "섬광 활성화 시전",
  "Flash max duration windup time": "섬광 최대 시전", "Telegraph windup time": "예고 시전",
  "Blind windup on target acquisition": "대상 포착 실명 시전",
  "Explosion windup time": "폭발 시전 시간",
  "Activation delay (without Empress)": "활성화 지연 (여제 제외)",
  "Activation window upon eligible takedown": "킬 후 활성화 창",
  "Overheal duration (without Empress)": "과회복 시간 (여제 제외)",
  "Shield windup": "방어막 시전", "Shield deactivation time": "방어막 해제",
  "Shield unequip time": "방어막 해제 시간", "Smoke deactivation time": "연막 해제",
  "Smoke unequip time": "연막 해제 시간",
  "Re-arm time": "재장전 시간", "Re-stealth timer": "은신 복귀",
  "Reload time": "재장전 시간", "Dart cooldown": "다트 쿨다운",
  "Dart removal channel time": "다트 제거 시간", "Net removal channel time": "그물 제거 시간",
  "Placement deploy time": "설치 시간", "Beacon duration": "신호기 시간",
  "1st reveal windup time": "1차 공개 시전", "2nd reveal windup time": "2차 공개 시전",
  "Triggered Slow duration": "트리거 둔화 시간", "Delay between successive segment detonations": "연쇄 폭발 간격",
  "Time taken to fully form": "완전 형성 시간", "Time required to fully charge": "완전 충전 시간",
  "Time taken to fortify": "강화 시간", "Time needed to arm": "무장 시간",
  "Fake decal duration": "가짜 자국 시간", "Maximum image duration": "최대 분신 시간",
  "Unequip time (out of ammo)": "탄약 소진 해제 시간",
  "Unequip times (out of ammo)": "탄약 소진 해제 시간",
  "Unequip/Return time": "해제/회수 시간", "Uneuqip time": "해제 시간",
  "Self-blind duration on arrival": "도착 시 자체 실명",
  "Duration while applying nearsight": "근시 적용 지속 시간",
  "Duration (if stopped)": "중단 시 지속 시간",
  "Contingency duration": "대비책 지속 시간", "Time until exit on kill": "킬 후 퇴장 시간",
  "Transportation duration to and from arena": "아레나 이동 시간",
  "Arena creation duration": "아레나 생성 시간", "Max duel duration": "최대 결투 시간",
  "Plasma blind duration": "플라즈마 실명 시간",
  "Flow state duration": "플로우 지속 시간", "Energy orb duration": "에너지 구 지속 시간",
  "Vision restoration duration": "시야 복구 시간",
  "Activation cooldowns": "활성화 쿨다운",
  "Max duration allowed for damaging assist to enable ability activation": "킬 어시 인정 시간",
  // ── 거리/범위 ──
  "Radius": "반경", "Radii": "반경", "Area size": "범위 크기",
  "Max deploy distance": "최대 배치 거리", "Max deploy length": "최대 배치 길이",
  "Max deploy height": "최대 배치 높이", "Detection radius": "탐지 반경",
  "Detection distance": "탐지 거리", "Detection radii": "탐지 반경",
  "Detection cone angle": "탐지 원뿔 각도", "Max detection cone distance": "최대 탐지 거리",
  "Max detection distance": "최대 탐지 거리",
  "Max cast distance": "최대 시전 거리", "Max cast range": "최대 시전 범위",
  "Max cast length": "최대 시전 길이", "Max cast radius": "최대 시전 반경",
  "Max cast radius for cloud's center": "구름 중심 최대 반경",
  "Travel distance": "이동 거리", "Base dash distance": "기본 대시 거리",
  "Dash distance": "대시 거리", "Slide distance": "슬라이드 거리",
  "Lunge distance": "돌진 거리", "Lunge radius": "돌진 반경",
  "Jump distance": "점프 거리", "Displacement Distance": "밀어내기 거리",
  "Knockback distance": "넉백 거리", "Self-knockback distance": "자체 넉백 거리",
  "Proximity radius to remain active": "활성 유지 근접 반경",
  "Proximity to target needed to explode": "폭발 근접 거리",
  "Proximity to target needed to activate blast": "폭발 활성화 거리",
  "Proximity needed to target to nearsight": "근시 적용 거리",
  "Distance between Iso and wall on cast": "시전 시 아이소-벽 거리",
  "Distance between Breach and AoE": "브리치-범위 거리",
  "Distance between Waylay and AoE": "웨이레이-범위 거리",
  "Distance between walls": "벽 간 거리", "Distance required to move away when affected": "영향 탈출 거리",
  "Audio cue radius": "소리 반경", "Arrival audio cue radius": "도착 소리 반경",
  "Teleport audio cue radius": "텔레포트 소리 반경",
  "Tether audio cue radius": "속박 소리 반경",
  "Anchor radius": "앵커 반경", "Search radius": "탐색 반경",
  "Slow radius": "둔화 반경", "Zone radius": "구역 반경",
  "Pulse radius": "펄스 반경", "Pulse radius at path end": "경로 끝 펄스 반경",
  "Maximum pulse travel distance": "최대 펄스 거리",
  "Explosion radius": "폭발 반경", "Detonation radius": "폭파 반경",
  "Plasma explosion radius on target": "플라즈마 폭발 반경",
  "Max wall penetration": "최대 벽 관통", "Max wall penetration depth": "최대 벽 관통 깊이",
  "Max wire length": "최대 와이어 길이", "Max recall distance": "최대 회수 거리",
  "Max projectile duration": "최대 투사체 시간", "Max lifespan": "최대 수명",
  "Max targeting distance": "최대 조준 거리",
  "Max vision radius": "최대 시야 반경", "Max vision radius while nearsighted": "근시 중 시야 반경",
  "Nearsight vision radius": "근시 시야 반경", "Nearsighted vision radius": "근시 시야 반경",
  "Vision radius": "시야 반경", "Vision cone angle": "시야 원뿔 각도",
  "Maximum radius": "최대 반경", "Cylinder size": "실린더 크기", "Cylinder radius": "실린더 반경",
  "Column area": "영역 크기", "Area": "범위", "Size": "크기",
  "Length": "길이", "Barrier lengths": "장벽 길이", "Maximum bend": "최대 곡률",
  "Wall Height": "벽 높이", "Wall Dimensions": "벽 크기",
  "Effective distance between Harbor and wave": "하버-파도 유효 거리",
  "Maximum rise": "최대 상승", "Maximum drop": "최대 하강",
  "Initial distance between agents on Arena spawn": "아레나 스폰 거리",
  "Buy Phase pickup range": "구매 단계 픽업 거리",
  "Deployment distance": "배치 거리", "Deployment duration": "배치 시간",
  "Effective active duration": "유효 활동 시간",
  "Pickup distance (Buy phase only)": "픽업 거리 (구매만)",
  "Vortex radius": "소용돌이 반경", "Flight altitude": "비행 고도",
  // ── 피해/회복 ──
  "Damage": "피해량", "Damage per distance": "거리당 피해",
  "Healing": "회복량", "Healing pool": "회복 풀",
  "Heal-over-time": "지속 회복", "Pulse heal": "펄스 회복",
  "Maximum Overheal": "최대 과회복", "Maximum decayed health": "최대 부식 체력",
  "Decay duration": "부식 시간", "Decay stats": "부식 수치", "Decay Stats": "부식 수치",
  "Downed Health": "다운 체력", "Debuff": "디버프",
  "Integrity duration": "내구 시간", "Integrity regeneration rate": "내구 재생률",
  // ── 속도/이동 ──
  "Velocity": "속도", "Speed": "속도", "Orb velocity": "구체 속도",
  "Sphere Velocity": "구체 속도", "Pulse velocity": "펄스 속도", "Pulse speed": "펄스 속도",
  "Run speed": "이동 속도", "Movement speed increase": "이동 속도 증가",
  "Bonus movement speed": "추가 이동 속도", "Travel speeds": "이동 속도",
  "Travel duration": "이동 시간",
  "Bullet tagging slow": "피격 둔화", "Slow potency": "둔화 강도",
  "Slow Duration": "둔화 시간", "Slow amount": "둔화량",
  "Lunge duration": "돌진 시간",
  // ── 기타 ──
  "Fire rate": "연사 속도", "'Single Fire' fire rate": "단발 연사 속도",
  "Ammunition": "탄약 수", "Angle": "각도", "Flash angle": "섬광 각도",
  "Ticks/Tick Rate": "틱 수/틱 속도", "Ticks/Tick rate": "틱 수/틱 속도",
  "Tick/Tick rate": "틱 수/틱 속도", "Detonation Ticks/Tick Rate per segment": "구간별 폭파 틱",
  "Buffs": "버프 효과", "Jammed duration": "방해 시간", "Hinder duration": "방해 시간",
  "Shield width": "방어막 너비",
  "Reveal stats": "공개 수치", "Reveal duration": "공개 시간",
  "Reveal ticks/tick Rate": "공개 틱", "Sonar pulses": "소나 펄스",
  "Pulse rate": "펄스 속도", "Windup to first pulse": "첫 펄스 시전",
  "Reload speed increase": "재장전 속도 증가",
  "Maximum intangibility duration": "최대 무적 시간",
  "Targeting delay": "조준 지연",
  "Damage multipliers": "피해 배수",
  "Capture windup": "포획 시전", "Reactivation windup": "재활성화 시전",
  "Maximum travel time in air": "최대 체공 이동 시간",
  "Max travel time in air": "최대 체공 이동 시간",
  // ── 추가 누락 스탯 ──
  "ADS Zoom": "조준경 배율", "Blast delay": "폭발 지연", "Blast windup": "폭발 시전",
  "Cast delay": "시전 지연", "Deactivation duration": "비활성화 시간",
  "Decay rates": "부식 수치", "Fire mode": "발사 모드",
  "Max Concuss duration": "최대 기절 시간", "Max Duration": "최대 지속 시간",
  "Movement penalties": "이동 패널티", "Overhealing rates": "과회복 수치",
  "Pull duration": "끌어당기기 시간", "Wall penetration": "벽 관통",
  "Wall dimensions": "벽 크기",
};

const VERDICT_KO: Record<string, string> = {
  strong_nerf: "강력 너프", mild_nerf: "소폭 너프",
  strong_buff: "강력 버프", mild_buff: "소폭 버프",
  stable: "안정",
};

function getSortedAgents(skills: AgentSkills | null): string[] {
  const agents = skills ? Object.keys(skills) : Object.keys(AGENT_UUID);
  return agents.sort((a, b) => {
    const roleA = skills?.[a]?._meta?.role_ko ?? AGENT_ROLE_KO[a] ?? "";
    const roleB = skills?.[b]?._meta?.role_ko ?? AGENT_ROLE_KO[b] ?? "";
    const ra = ROLE_ORDER.indexOf(roleA);
    const rb = ROLE_ORDER.indexOf(roleB);
    if (ra !== rb) return ra - rb;
    return a.localeCompare(b);
  });
}

interface PendingChange {
  agent: string;
  skill: string;
  stat: string;
  statLabel: string;
  old_value: number;
  new_value: number;
}

// ─── 프리셋 ────────────────────────────────────────────────────────────────────
// 대표적인 너프/버프 케이스를 원클릭으로 체험할 수 있게 미리 만들어둔 시나리오.
// 모두 agent_skills.json의 실제 스탯 값을 기준으로 한다.
const PRESETS: {
  title: string;
  tag: "너프" | "버프";
  color: string;
  desc: string;
  changes: PendingChange[];
}[] = [
  {
    title: "네온 궁극기 너프",
    tag: "너프",
    color: "#FF4655",
    desc: "오버드라이브 연사 속도 20 → 15 (DPS 25% 감소)",
    changes: [{
      agent: "Neon", skill: "X", stat: "Fire rate", statLabel: "Fire rate",
      old_value: 20, new_value: 15,
    }],
  },
  {
    title: "케이오 Q 플래시 가격 인하",
    tag: "버프",
    color: "#4FC3F7",
    desc: "플래시/드라이브 250 → 150크레딧 (라운드 경제 완화)",
    changes: [{
      agent: "KAYO", skill: "Q", stat: "creds", statLabel: "creds",
      old_value: 250, new_value: 150,
    }],
  },
  {
    title: "오멘 연막 지속시간 너프",
    tag: "너프",
    color: "#FF4655",
    desc: "어둠의 장막 15s → 10s (VCT 고정픽 견제)",
    changes: [{
      agent: "Omen", skill: "E", stat: "Duration", statLabel: "Duration",
      old_value: 15, new_value: 10,
    }],
  },
];

// ─── 메인 ──────────────────────────────────────────────────────────────────────
export default function SimulatorClient({
  initialSkills = null,
}: {
  initialSkills?: AgentSkills | null;
}) {
  const [skills, setSkills] = useState<AgentSkills | null>(initialSkills);
  // 서버에서 미리 받아왔으면 로딩 불필요
  const [loading, setLoading] = useState(initialSkills === null);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [changes, setChanges] = useState<PendingChange[]>([]);
  const [simulating, setSimulating] = useState(false);
  const [result, setResult] = useState<SimResult | null>(null);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzingAI, setAnalyzingAI] = useState(false);

  useEffect(() => {
    if (skills !== null) return; // 서버 프리페치 성공 → 재요청 불필요
    getAgentSkills().then(setSkills).catch(console.error).finally(() => setLoading(false));
  }, [skills]);

  const addChange = useCallback(
    (agent: string, skill: string, stat: string, statLabel: string, oldVal: number, newVal: number) => {
      if (oldVal === newVal) return;
      setChanges((prev) => {
        const filtered = prev.filter((c) => !(c.agent === agent && c.skill === skill && c.stat === stat));
        return [...filtered, { agent, skill, stat, statLabel, old_value: oldVal, new_value: newVal }];
      });
    }, []
  );

  const removeChange = useCallback((idx: number) => {
    setChanges((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const runSim = async () => {
    if (changes.length === 0) return;
    setSimulating(true);
    setResult(null);
    setAnalysis(null);
    try {
      const payload: SimStatChange[] = changes.map((c) => ({
        agent: c.agent, skill: c.skill, stat: c.stat,
        old_value: c.old_value, new_value: c.new_value,
      }));
      const r = await runSimulation(payload);
      setResult(r);

      // AI 분석 비동기 요청
      setAnalyzingAI(true);
      const summary = buildResultSummary(r);
      getSimAnalysis(payload, summary)
        .then(setAnalysis)
        .catch(() => setAnalysis(null))
        .finally(() => setAnalyzingAI(false));
    } catch (e) {
      console.error(e);
    } finally {
      setSimulating(false);
    }
  };

  if (loading) {
    return (
      <div className="py-8 space-y-8 animate-pulse">
        {/* 헤더 스켈레톤 */}
        <div className="space-y-4">
          <div className="h-3 w-24 bg-slate-800/60" />
          <div className="pl-4" style={{ borderLeft: "2px solid rgba(167,139,250,0.35)" }}>
            <div className="h-2.5 w-40 bg-slate-800/60 mb-2" />
            <div className="h-8 w-48 bg-slate-800/80 mb-2" />
            <div className="h-3 w-72 bg-slate-800/50" />
          </div>
        </div>

        {/* 역할군 탭 스켈레톤 */}
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 w-20 bg-slate-800/50" />
          ))}
        </div>

        {/* 요원 그리드 스켈레톤 */}
        <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-9 gap-2">
          {Array.from({ length: 18 }).map((_, i) => (
            <div key={i} className="aspect-square bg-slate-800/40 border border-slate-800/60" />
          ))}
        </div>

        <div className="text-center text-[10px] uppercase tracking-widest text-slate-600">
          SIM DATA STREAM // 스킬 데이터 초기화 중...
        </div>
      </div>
    );
  }

  return (
    <div className="py-8 space-y-8">
      {/* ── 헤더 ─────────────────────────────────────── */}
      <div className="space-y-4">
        <BackToHome />
        <div className="pl-4" style={{ borderLeft: "2px solid #A78BFA" }}>
          <div className="text-[9px] font-valo tracking-[0.25em] mb-0.5" style={{ color: "rgba(167,139,250,0.6)" }}>
            SIM // PATCH SIMULATOR
          </div>
          <h1 className="font-valo text-3xl font-bold tracking-wide" style={{ color: "#A78BFA" }}>패치 시뮬레이터</h1>
          <p className="text-sm mt-1" style={{ color: "#94A3B8" }}>
            요원의 스킬 수치를 변경하고 메타에 미치는 영향을 예측합니다
          </p>
        </div>
      </div>

      {/* ── 사용 가이드 (3스텝) ─────────────────────── */}
      <div
        className="p-4 sm:p-5 space-y-3"
        style={{
          background: "rgba(167,139,250,0.04)",
          border: "1px solid rgba(167,139,250,0.18)",
        }}
      >
        <div className="flex items-center gap-2">
          <span
            className="text-[9px] font-black px-1.5 py-px uppercase tracking-widest"
            style={{ color: "#A78BFA", border: "1px solid rgba(167,139,250,0.4)", background: "rgba(167,139,250,0.08)" }}
          >
            GUIDE
          </span>
          <span className="text-xs uppercase tracking-widest" style={{ color: "rgba(167,139,250,0.75)" }}>
            처음이신가요? 3단계로 끝납니다
          </span>
        </div>
        <ol className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[12px]" style={{ color: "#cbd5e1" }}>
          {[
            { n: "1", label: "요원 선택", hint: "아래에서 조정하고 싶은 요원 클릭" },
            { n: "2", label: "수치 변경", hint: "C/Q/E/X 스킬 값을 원하는 대로 수정" },
            { n: "3", label: "시뮬 실행", hint: "메타 변화 + AI 분석 결과 확인" },
          ].map((s) => (
            <li
              key={s.n}
              className="flex items-start gap-2 p-2"
              style={{ background: "rgba(13,18,32,0.5)", border: "1px solid rgba(30,41,59,0.7)" }}
            >
              <span
                className="shrink-0 w-5 h-5 flex items-center justify-center text-[11px] font-num font-black"
                style={{
                  color: "#A78BFA",
                  border: "1px solid rgba(167,139,250,0.35)",
                  background: "rgba(167,139,250,0.08)",
                }}
              >
                {s.n}
              </span>
              <div className="min-w-0">
                <div className="font-semibold leading-tight" style={{ color: "#e2e8f0" }}>{s.label}</div>
                <div className="text-[11px] mt-0.5 leading-snug" style={{ color: "rgba(148,163,184,0.7)" }}>{s.hint}</div>
              </div>
            </li>
          ))}
        </ol>

        {/* 프리셋: 원클릭 체험용 */}
        <div className="pt-2">
          <div className="text-[10px] uppercase tracking-widest mb-2" style={{ color: "rgba(167,139,250,0.6)" }}>
            ⚡ 샘플 시나리오 · 클릭해서 바로 체험
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {PRESETS.map((p) => (
              <button
                key={p.title}
                type="button"
                onClick={() => {
                  // 프리셋 적용: 기존 changes 초기화하고 프리셋의 changes로 교체
                  setChanges(p.changes);
                  // 해당 요원을 자동 선택해서 편집기에 보여줌
                  setSelectedAgent(p.changes[0].agent);
                  // 이전 결과는 초기화
                  setResult(null);
                  setAnalysis(null);
                }}
                className="text-left p-3 group transition-all hover:brightness-110"
                style={{
                  background: "rgba(13,18,32,0.7)",
                  border: `1px solid ${p.color}30`,
                }}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span
                    className="text-[9px] font-black px-1.5 py-px uppercase tracking-wider"
                    style={{ color: p.color, border: `1px solid ${p.color}50`, background: `${p.color}10` }}
                  >
                    {p.tag}
                  </span>
                  <span className="text-[13px] font-bold" style={{ color: "#e2e8f0" }}>{p.title}</span>
                </div>
                <div className="text-[11px] leading-snug" style={{ color: "rgba(148,163,184,0.75)" }}>
                  {p.desc}
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 요원 선택 (역할군별) ────────────────────── */}
      <div className="space-y-5">
        <div className="text-[9px] uppercase tracking-widest flex items-center gap-2" style={{ color: "rgba(71,85,105,0.6)" }}>
          <div className="w-3 h-px" style={{ background: "#A78BFA" }} />
          요원 선택
        </div>
        {ROLE_ORDER.map((role) => {
          const roleColor = ROLE_COLOR[role] ?? "#64748B";
          const agentsInRole = getSortedAgents(skills).filter((a) => {
            const r = skills?.[a]?._meta?.role_ko ?? AGENT_ROLE_KO[a] ?? "";
            return r === role;
          });
          if (agentsInRole.length === 0) return null;
          return (
            <div key={role} className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rotate-45" style={{ background: roleColor, boxShadow: `0 0 6px ${roleColor}55` }} />
                <span className="text-xs font-valo font-bold tracking-widest" style={{ color: roleColor }}>{role}</span>
                <div className="flex-1 h-px" style={{ background: `${roleColor}20` }} />
              </div>
              <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 gap-3">
                {agentsInRole.map((agent) => {
                  const isSelected = selectedAgent === agent;
                  const hasChange = changes.some((c) => c.agent === agent);
                  return (
                    <button
                      key={agent}
                      onClick={() => setSelectedAgent(isSelected ? null : agent)}
                      className="relative group flex flex-col items-center gap-1.5 p-3 transition-all"
                      style={{
                        background: isSelected ? "rgba(167,139,250,0.15)" : hasChange ? "rgba(167,139,250,0.06)" : "rgba(13,18,32,0.6)",
                        border: isSelected ? "1px solid rgba(167,139,250,0.5)" : hasChange ? "1px solid rgba(167,139,250,0.25)" : "1px solid rgba(30,41,59,0.6)",
                      }}
                    >
                      {agentIcon(agent) && (
                        <Image src={agentIcon(agent)} alt={agent} width={64} height={64} className="rounded-full"
                          style={{ filter: isSelected ? "none" : "grayscale(0.4) brightness(0.8)", transition: "filter 0.2s" }}
                        />
                      )}
                      <span className="text-sm font-bold tracking-wide truncate w-full text-center" style={{ color: isSelected ? "#A78BFA" : "rgba(148,163,184,0.85)" }}>
                        {agent}
                      </span>
                      {hasChange && (
                        <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full"
                          style={{ background: "#A78BFA", boxShadow: "0 0 6px rgba(167,139,250,0.6)" }} />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* ── 스킬 에디터 ──────────────────────────────── */}
      {selectedAgent && skills && (
        <SkillEditor agent={selectedAgent} agentSkills={skills[selectedAgent] ?? {}} roleKo={skills[selectedAgent]?._meta?.role_ko ?? AGENT_ROLE_KO[selectedAgent] ?? ""} changes={changes} onAddChange={addChange} />
      )}

      {/* ── 변경사항 목록 ────────────────────────────── */}
      {changes.length > 0 && (
        <div className="space-y-3">
          <div className="text-[9px] uppercase tracking-widest flex items-center gap-2" style={{ color: "rgba(71,85,105,0.6)" }}>
            <div className="w-3 h-px" style={{ background: "#A78BFA" }} />
            변경사항 ({changes.length}개)
          </div>
          <div className="space-y-1.5">
            {changes.map((c, i) => {
              const diff = c.new_value - c.old_value;
              const lowerIsBuff = ["cooldown", "cost", "cred", "windup", "deploy", "recharge", "equip", "unequip", "time", "delay", "channel", "arm"].some((k) => c.stat.toLowerCase().includes(k));
              const isNerf = lowerIsBuff ? diff > 0 : diff < 0;
              const color = isNerf ? "#FF4655" : "#4FC3F7";
              const dirLabel = isNerf ? "너프" : "버프";
              return (
                <div key={`${c.agent}-${c.skill}-${c.stat}`} className="flex items-center gap-3 px-4 py-2.5 text-sm"
                  style={{ background: "rgba(13,18,32,0.6)", border: `1px solid ${color}30` }}>
                  <span className="font-bold text-white">{c.agent}</span>
                  <span className="font-num text-xs px-1.5 py-0.5" style={{ color: SLOT_COLOR[c.skill] ?? "#999", border: `1px solid ${SLOT_COLOR[c.skill] ?? "#999"}40` }}>
                    {c.skill}
                  </span>
                  <span className="text-slate-400 truncate flex-1">{c.statLabel}</span>
                  <span className="font-num text-slate-500">{c.old_value}</span>
                  <span style={{ color }}>→</span>
                  <span className="font-num font-bold" style={{ color }}>{c.new_value}</span>
                  <span className="text-xs px-1.5 py-0.5" style={{ color, border: `1px solid ${color}30` }}>{dirLabel}</span>
                  <button onClick={() => removeChange(i)} className="text-slate-600 hover:text-red-400 transition-colors ml-1 text-sm">✕</button>
                </div>
              );
            })}
          </div>
          <button onClick={runSim} disabled={simulating}
            className="w-full py-3 font-black text-sm uppercase tracking-widest transition-all"
            style={{
              background: simulating ? "rgba(167,139,250,0.1)" : "rgba(167,139,250,0.15)",
              border: "1px solid rgba(167,139,250,0.4)", color: "#A78BFA",
              cursor: simulating ? "wait" : "pointer",
            }}>
            {simulating ? "시뮬레이션 중..." : "시뮬레이션 실행"}
          </button>
        </div>
      )}

      {/* ── 결과 ─────────────────────────────────────── */}
      {result && <SimulationResults result={result} analysis={analysis} analyzingAI={analyzingAI} />}
    </div>
  );
}

// ─── 결과 요약 텍스트 생성 (AI 분석용) ─────────────────────────────────────────
function buildResultSummary(r: SimResult): string {
  const lines: string[] = [];
  for (const imp of r.impact) {
    const b = imp.before as Record<string, unknown>;
    const vctPr = Number(b.vct_pr ?? 0);
    const vctWr = Number(b.vct_wr ?? 50);
    const vctLag = Number(b.vct_data_lag ?? 0);

    // 표본 신뢰도 경고
    const warnings: string[] = [];
    if (vctPr < 5) warnings.push(`⚠ VCT 픽률 ${vctPr}%로 표본 부족 — VCT 승률 ${vctWr}%는 신뢰 불가`);
    if (vctLag >= 2) warnings.push(`⚠ VCT 데이터 ${vctLag}액트 전 — 최근 VCT 경기에서 거의 안 쓰임`);

    lines.push(`${imp.agent} 현재 상태: 랭크 픽률 ${b.rank_pr ?? "?"}%, 랭크 승률 ${b.rank_wr ?? "?"}%, VCT 픽률 ${vctPr}%, 현재 판정 ${imp.before.verdict}(너프${imp.before.p_nerf}%/버프${imp.before.p_buff}%)`);
    warnings.forEach((w) => lines.push(`  ${w}`));
    lines.push(`  시뮬 결과: 예상 PR변화 ${imp.applied_pr_delta >= 0 ? "+" : ""}${imp.applied_pr_delta.toFixed(2)}%p, WR변화 ${imp.applied_wr_delta >= 0 ? "+" : ""}${imp.applied_wr_delta.toFixed(2)}%p`);
    lines.push(`  판정 변화: ${imp.before.verdict} → ${imp.after.verdict}(너프${imp.after.p_nerf}%/버프${imp.after.p_buff}%)`);
  }
  if (r.ripple_effects.length > 0) {
    lines.push(`리플 효과: ${r.ripple_effects.map((e) => `${e.agent}(${e.before_verdict}→${e.after_verdict})`).join(", ")}`);
  }
  return lines.join("\n");
}

// ─── 스킬 에디터 ────────────────────────────────────────────────────────────────
function SkillEditor({
  agent, agentSkills, roleKo, changes, onAddChange,
}: {
  agent: string;
  agentSkills: Record<string, SkillSlot>;
  roleKo: string;
  changes: PendingChange[];
  onAddChange: (agent: string, skill: string, stat: string, statLabel: string, oldVal: number, newVal: number) => void;
}) {
  const slots = ["C", "Q", "E", "X"].filter((s) => agentSkills[s]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4">
        {agentIcon(agent) && <Image src={agentIcon(agent)} alt={agent} width={48} height={48} className="rounded-full" />}
        <div>
          <div className="text-2xl font-extrabold tracking-tight text-white">{agent}</div>
          <div className="text-xs uppercase tracking-widest" style={{ color: ROLE_COLOR[roleKo] ?? "#64748B" }}>
            {roleKo}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {slots.map((slot) => {
          const skill = agentSkills[slot];
          const color = SLOT_COLOR[slot] ?? "#999";

          // 메타 스탯 (charges, creds, ult_points)을 일반 스탯과 합침
          const allStats: { name: string; value: number; unit: string }[] = [];

          if (skill.charges !== undefined && skill.charges !== null) {
            allStats.push({ name: "charges", value: skill.charges, unit: "개" });
          }
          if (skill.creds !== undefined && skill.creds !== null && skill.creds > 0) {
            allStats.push({ name: "creds", value: skill.creds, unit: "크레딧" });
          }
          if (slot === "X" && skill.ult_points !== undefined && skill.ult_points !== null) {
            allStats.push({ name: "ult_points", value: skill.ult_points, unit: "포인트" });
          }

          for (const [statName, statVal] of Object.entries(skill.stats)) {
            if (statVal.value !== null && statVal.value !== undefined) {
              allStats.push({ name: statName, value: statVal.value, unit: statVal.unit });
            }
          }

          return (
            <div key={slot} className="p-4 space-y-3" style={{ background: "rgba(13,18,32,0.6)", border: `1px solid ${color}25` }}>
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-black px-2 py-1 tracking-wider"
                  style={{ color, border: `1px solid ${color}50`, background: `${color}10` }}>
                  {SLOT_LABEL[slot] ?? slot}
                </span>
                <span className="text-sm font-bold text-slate-300">{skill.name_ko ?? skill.name}</span>
              </div>

              {allStats.length === 0 ? (
                <div className="text-xs text-slate-700 italic">수치 데이터 없음</div>
              ) : (
                <div className="space-y-2">
                  {allStats.map((s) => {
                    const existing = changes.find((c) => c.agent === agent && c.skill === slot && c.stat === s.name);
                    return (
                      <StatRow key={s.name} agent={agent} skill={slot} statName={s.name} value={s.value} unit={s.unit}
                        color={color} currentNew={existing?.new_value}
                        onConfirm={(newVal) => onAddChange(agent, slot, s.name, s.name, s.value, newVal)} />
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── StatRow ────────────────────────────────────────────────────────────────────
function StatRow({
  agent, skill, statName, value, unit, color, currentNew, onConfirm,
}: {
  agent: string; skill: string; statName: string; value: number; unit: string;
  color: string; currentNew?: number; onConfirm: (newVal: number) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [inputVal, setInputVal] = useState(String(currentNew ?? value));

  const handleConfirm = () => {
    const parsed = parseFloat(inputVal);
    if (!isNaN(parsed) && parsed !== value) onConfirm(parsed);
    setEditing(false);
  };

  const isModified = currentNew !== undefined && currentNew !== value;
  const rawUnit = unit.split(/[<(]/)[0].trim().slice(0, 20);
  const UNIT_KO: Record<string, string> = {
    seconds: "초", meters: "m", "meters/second": "m/s", meter: "m",
    "meter length": "m",
  };
  // meter-length 계열 복합 단위 → "m" 로 축약
  const displayUnit = rawUnit.includes("meter") ? "m" : (UNIT_KO[rawUnit] ?? rawUnit);
  const isTimeStat = rawUnit === "seconds" || displayUnit === "초" || ["time", "duration", "windup", "delay", "channel"].some((k) => statName.toLowerCase().includes(k));
  const inputStep = isTimeStat ? "0.1" : "1";

  return (
    <div className="flex items-center gap-3 text-sm py-0.5">
      <span className="text-slate-400 truncate flex-1 min-w-0" title={statName}>{STAT_NAME_KO[statName] ?? statName}</span>
      {editing ? (
        <div className="flex items-center gap-2">
          <span className="text-slate-600 font-num">{value}</span>
          <span className="text-slate-700">&rarr;</span>
          <input type="number" step={inputStep} value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleConfirm(); if (e.key === "Escape") setEditing(false); }}
            autoFocus className="w-20 px-2 py-1 text-sm font-num text-right bg-transparent outline-none"
            style={{ border: `1px solid ${color}50`, color }} />
          <button onClick={handleConfirm} className="text-xs px-2 py-1 font-bold" style={{ color, border: `1px solid ${color}40` }}>
            확인
          </button>
        </div>
      ) : (
        <button onClick={() => { setInputVal(String(currentNew ?? value)); setEditing(true); }} className="flex items-center gap-1.5 group">
          <span className="font-num font-bold text-sm" style={{ color: isModified ? color : "rgba(226,232,240,0.9)" }}>
            {isModified ? (
              <><span className="text-slate-600 line-through">{value}</span><span className="mx-1" style={{ color }}>&rarr;</span>{currentNew}</>
            ) : value}
          </span>
          {displayUnit && <span className="text-slate-600 text-xs">{displayUnit}</span>}
          <span className="text-slate-700 group-hover:text-slate-400 transition-colors text-[10px] ml-1">수정</span>
        </button>
      )}
    </div>
  );
}

// ─── 결과 ────────────────────────────────────────────────────────────────────────
function SimulationResults({ result, analysis, analyzingAI }: { result: SimResult; analysis: string | null; analyzingAI: boolean }) {
  const changedAgents = new Set(result.changes.map((c) => c.agent));

  return (
    <div className="space-y-6">
      <div className="text-[9px] uppercase tracking-widest flex items-center gap-2" style={{ color: "rgba(71,85,105,0.6)" }}>
        <div className="w-3 h-px" style={{ background: "#A78BFA" }} />
        시뮬레이션 결과
      </div>

      {/* AI 분석 */}
      <div className="p-5" style={{ background: "rgba(167,139,250,0.05)", border: "1px solid rgba(167,139,250,0.2)" }}>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-widest" style={{ color: "#A78BFA" }}>AI 분석</span>
          {analyzingAI && <span className="text-xs text-slate-600 animate-pulse">분석 생성 중...</span>}
        </div>
        {analysis ? (
          <p className="text-sm leading-relaxed" style={{ color: "rgba(203,213,225,0.9)" }}>{analysis}</p>
        ) : !analyzingAI ? (
          <p className="text-sm text-slate-600 italic">AI 분석을 불러올 수 없습니다</p>
        ) : null}
      </div>

      {/* 직접 영향 */}
      {result.impact.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-wider text-slate-500 font-bold">직접 영향</div>
          {result.impact.map((imp) => {
            const verdictChanged = imp.before.verdict !== imp.after.verdict;
            const confColor = imp.confidence === "high" ? "#66BB6A" : imp.confidence === "medium" ? "#FFA726" : "#FF4655";
            const confLabel = imp.confidence === "high" ? "높음" : imp.confidence === "medium" ? "보통" : "낮음";
            return (
              <div key={imp.agent} className="p-4 space-y-3" style={{ background: "rgba(13,18,32,0.6)", border: "1px solid rgba(167,139,250,0.2)" }}>
                <div className="flex items-center gap-4">
                  {agentIcon(imp.agent) && <Image src={agentIcon(imp.agent)} alt={imp.agent} width={44} height={44} className="rounded-full" />}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-base font-extrabold tracking-tight text-white">{imp.agent}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5" style={{ color: confColor, border: `1px solid ${confColor}40` }}>
                        신뢰도 {confLabel}
                      </span>
                      <span className="text-[10px] text-slate-700">n={imp.n_samples}</span>
                    </div>
                    <div className="text-xs font-num text-slate-500 mt-1">
                      픽률 {imp.applied_pr_delta >= 0 ? "+" : ""}{imp.applied_pr_delta.toFixed(2)}%p
                      <span className="text-slate-600 ml-1">
                        ({imp.pr_range[0] >= 0 ? "+" : ""}{imp.pr_range[0].toFixed(1)} ~ {imp.pr_range[2] >= 0 ? "+" : ""}{imp.pr_range[2].toFixed(1)})
                      </span>
                      {" / "}
                      승률 {imp.applied_wr_delta >= 0 ? "+" : ""}{imp.applied_wr_delta.toFixed(2)}%p
                      <span className="text-slate-600 ml-1">
                        ({imp.wr_range[0] >= 0 ? "+" : ""}{imp.wr_range[0].toFixed(1)} ~ {imp.wr_range[2] >= 0 ? "+" : ""}{imp.wr_range[2].toFixed(1)})
                      </span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="flex items-center gap-2 text-sm">
                      <VerdictBadge verdict={imp.before.verdict} />
                      <span className="text-slate-600">&rarr;</span>
                      <VerdictBadge verdict={imp.after.verdict} highlight={verdictChanged} />
                    </div>
                    <div className="text-xs font-num text-slate-600 mt-1">
                      너프:{imp.before.p_nerf}&rarr;{imp.after.p_nerf}% 버프:{imp.before.p_buff}&rarr;{imp.after.p_buff}%
                    </div>
                  </div>
                </div>

                {/* 유사 패치 사례 */}
                {imp.similar_cases && imp.similar_cases.length > 0 && (
                  <div className="pt-3 border-t" style={{ borderColor: "rgba(30,41,59,0.6)" }}>
                    <div className="text-[10px] uppercase tracking-widest text-slate-600 mb-1.5">유사 패치 사례</div>
                    <div className="space-y-1">
                      {imp.similar_cases.slice(0, 3).map((sc, i) => {
                        const tierColor = sc.match_tier === "exact" ? "#A78BFA" : sc.match_tier === "same_agent" ? "#66BB6A" : "#475569";
                        return (
                          <div key={i} className="flex items-start gap-2 text-xs">
                            <span className="text-slate-600 font-num shrink-0">v{sc.patch}</span>
                            <span className="font-bold shrink-0" style={{ color: tierColor }}>{sc.agent}</span>
                            <span className="text-slate-500 font-num shrink-0">[{sc.skill}]</span>
                            <span className="text-slate-400 truncate">{sc.description}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 리플 효과 */}
      {result.ripple_effects.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-wider text-slate-500 font-bold">
            리플 효과 ({result.ripple_effects.length}명 영향)
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {result.ripple_effects.map((r) => (
              <div key={r.agent} className="flex items-center gap-3 px-4 py-2 text-sm"
                style={{ background: "rgba(13,18,32,0.6)", border: "1px solid rgba(30,41,59,0.6)" }}>
                <span className="font-bold text-white">{r.agent}</span>
                <VerdictBadge verdict={r.before_verdict} />
                <span className="text-slate-600">&rarr;</span>
                <VerdictBadge verdict={r.after_verdict} highlight />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 전체 순위 */}
      <div className="space-y-2">
        <div className="text-xs uppercase tracking-wider text-slate-500 font-bold">패치 후 전체 순위</div>
        <div className="space-y-0.5">
          {result.after_ranking.map((a, i) => {
            const before = result.before_ranking.find((b) => b.agent === a.agent);
            const isChanged = changedAgents.has(a.agent);
            const verdictChanged = before && before.verdict !== a.verdict;
            const dominant = Math.max(a.p_nerf, a.p_buff);
            const barColor = a.verdict.includes("nerf") ? "#FF4655" : a.verdict.includes("buff") ? "#4FC3F7" : "#475569";

            return (
              <div key={a.agent} className="flex items-center gap-3 px-4 py-1.5 text-xs"
                style={{
                  background: isChanged ? "rgba(167,139,250,0.06)" : "rgba(13,18,32,0.3)",
                  border: isChanged ? "1px solid rgba(167,139,250,0.15)" : "1px solid transparent",
                }}>
                <span className="w-6 text-right text-slate-600 font-num text-xs">{i + 1}</span>
                <span className={`w-24 truncate ${isChanged ? "text-purple-300 font-bold" : "text-slate-300"}`}>{a.agent}</span>
                <div className="flex-1 h-1.5 relative" style={{ background: "rgba(30,41,59,0.5)" }}>
                  <div className="absolute left-0 top-0 h-full transition-all" style={{ width: `${Math.min(dominant, 100)}%`, background: barColor, opacity: 0.7 }} />
                </div>
                <span className="w-14 text-right font-num font-bold" style={{ color: barColor }}>{dominant.toFixed(1)}%</span>
                <VerdictBadge verdict={a.verdict} highlight={!!verdictChanged} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── VerdictBadge ──────────────────────────────────────────────────────────────
function VerdictBadge({ verdict, highlight }: { verdict: string; highlight?: boolean }) {
  const isNerf = verdict.includes("nerf");
  const isBuff = verdict.includes("buff");
  const color = isNerf ? "#FF4655" : isBuff ? "#4FC3F7" : "#475569";
  const label = VERDICT_KO[verdict] ?? verdict.slice(0, 7);

  return (
    <span className="text-[10px] font-bold px-1.5 py-0.5 uppercase tracking-wider"
      style={{ color, border: `1px solid ${color}${highlight ? "60" : "30"}`, background: highlight ? `${color}15` : "transparent" }}>
      {label}
    </span>
  );
}
