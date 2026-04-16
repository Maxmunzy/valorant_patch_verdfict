"""
explanation_service.py
AI 기반 요원별 패치 전망 설명 생성 서비스

predict_service.py에서 분리 — 설명/프롬프트/캐시 로직만 담당.
핵심 예측 로직과 설명 레이어를 분리하여 유지보수성 향상.
"""

import os
import re
import json
import logging
from typing import Optional
from anthropic import Anthropic

from agent_data import AGENT_NAME_KO, AGENT_KIT, CURRENT_MAP_POOL

logger = logging.getLogger(__name__)

# ─── 스킬 한국어 공식 이름 (agent_data.AGENT_KIT에서 자동 생성) ─────────────
AGENT_SKILLS_KO: dict[str, dict[str, str]] = {
    agent: {slot: info["ko"] for slot, info in kit.items()}
    for agent, kit in AGENT_KIT.items()
}

# all_agents_map_stats.csv V26A2 기반 사전 계산 값 (map_pr >= 1.3 × 전체 평균)
AGENT_MAP_AFFINITY: dict[str, list[str]] = {
    "Breach":    ["프랙처", "로터스"],
    "Brimstone": ["프랙처", "바인드"],
    "Chamber":   ["브리즈"],
    "Cypher":    ["스플릿", "바인드"],
    "Fade":      ["펄", "로터스"],
    "Killjoy":   ["헤이븐", "프랙처", "펄"],
    "Omen":      ["헤이븐", "로터스", "스플릿"],
    "Phoenix":   ["헤이븐", "펄"],
    "Raze":      ["바인드", "로터스", "스플릿"],
    "Sage":      ["스플릿"],
    "Skye":      ["바인드", "스플릿"],
    "Sova":      ["브리즈", "헤이븐"],
    "Viper":     ["브리즈"],
}


class ExplanationGenerator:
    """AI(Claude Haiku) 기반 요원 패치 전망 설명 생성기.

    캐시 관리, 프롬프트 구성, 템플릿 폴백을 담당.
    """

    def __init__(self, cache_path: str = "explanation_cache.json"):
        self._cache_path = cache_path
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                self._cache: dict[str, str] = json.load(f)
        else:
            self._cache = {}
        self._anthropic: Anthropic | None = None

    def get(self, r: dict) -> str:
        """캐시 확인 후 설명 반환. 캐시 미스 시 생성."""
        agent   = r["agent"]
        verdict = r["verdict"]
        act     = r.get("act", "")
        rank_pr_r = round(r.get("rank_pr", 0), 1)
        vct_pr_r  = round(r.get("vct_pr", 0), 1)
        cache_key = f"{agent}::{verdict}::{act}::{rank_pr_r}::{vct_pr_r}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        explanation = self._generate(r)
        self._cache[cache_key] = explanation
        try:
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return explanation

    def _generate(self, r: dict) -> str:
        """Claude Haiku로 양면 분석 스타일의 설명 생성. 실패 시 템플릿 폴백."""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return self._template(r)

        # 신규 요원: 패치 이력 없음 → 모델 예측 신뢰도 낮음
        acts_since_r = int(r.get("acts_since_patch", 0) or 0)
        if acts_since_r >= 90:
            agent_ko_r = AGENT_NAME_KO.get(r["agent"], r["agent"])
            return (
                f"출시 이후 패치 이력이 없어 예측 신뢰도가 낮습니다. "
                f"데이터가 충분히 쌓이면 {agent_ko_r}에 대한 정밀 분석이 가능해집니다."
            )

        if self._anthropic is None:
            self._anthropic = Anthropic(api_key=api_key)

        agent     = r["agent"]
        agent_ko  = AGENT_NAME_KO.get(agent, agent)
        verdict   = r["verdict"]
        p_buff    = r["p_buff"]
        p_nerf    = r["p_nerf"]
        rank_pr   = r["rank_pr"]
        vct_pr    = r["vct_pr"]
        rank_wr   = r["rank_wr"]
        vct_wr    = r["vct_wr"]
        signals   = r.get("signals", [])
        patch_ver = r.get("last_patch_version") or ""
        patch_ref = f"{patch_ver} 패치" if patch_ver else "최근 패치"

        def _strip_act_codes(s: str) -> str:
            return re.sub(r'\b[VE]\d+A\d+\b', '', s).strip()

        signal_text = "\n".join(
            f"- {_strip_act_codes(s['label'])}: {_strip_act_codes(s['text'])}"
            for s in signals[:6]
        ) or "- 특별한 신호 없음"

        direction   = "버프" if "buff" in verdict else "너프"
        dir_pct     = p_buff if "buff" in verdict else p_nerf
        counter_pct = p_nerf if "buff" in verdict else p_buff

        # 신호 강도
        if dir_pct >= 60:
            signal_strength = "강함 — 이번 패치 조정 가능성 높음"
        elif dir_pct >= 35:
            signal_strength = "중간 — 이번 혹은 다음 패치 내 조정 예상"
        else:
            signal_strength = "약함 — 신호 누적 중, 당장보다 중장기적 조정 가능"

        # 데이터 해석 힌트
        rank_wr_actual = 50 + rank_wr
        nerf_evidence = []
        buff_evidence = []
        if rank_pr >= 40:  nerf_evidence.append(f"랭크 픽률 {rank_pr:.1f}%로 높음")
        if rank_wr > 1.5:  nerf_evidence.append(f"랭크 승률 {rank_wr_actual:.1f}%로 평균 이상")
        if vct_pr >= 25:   nerf_evidence.append(f"프로 대회 픽률 {vct_pr:.1f}%로 메타 핵심")
        if vct_wr >= 52:   nerf_evidence.append(f"프로 승률 {vct_wr:.1f}%로 높음")
        if rank_pr < 20:   buff_evidence.append(f"랭크 픽률 {rank_pr:.1f}%로 낮음")
        if rank_wr < -1.5: buff_evidence.append(f"랭크 승률 {rank_wr_actual:.1f}%로 평균 이하")
        if vct_pr < 8:     buff_evidence.append(f"프로 대회 픽률 {vct_pr:.1f}%로 낮음")
        if vct_wr <= 47:   buff_evidence.append(f"프로 승률 {vct_wr:.1f}%로 낮음")

        if direction == "너프":
            dir_evidence = "、".join(nerf_evidence) or f"프로 대회 픽률 {vct_pr:.1f}%"
            cnt_evidence = "、".join(buff_evidence) or f"랭크 승률 {rank_wr_actual:.1f}%"
        else:
            dir_evidence = "、".join(buff_evidence) or f"랭크 픽률 {rank_pr:.1f}%"
            cnt_evidence = "、".join(nerf_evidence) or f"프로 픽률 {vct_pr:.1f}%"

        # 맵 친화도
        map_affinity = AGENT_MAP_AFFINITY.get(agent, [])
        map_line_prompt = (
            f"- 현재 맵 풀 특화 맵: {', '.join(map_affinity)} (분석에 자연스럽게 녹여도 됨)"
            if map_affinity else ""
        )

        # 스킬 이름 힌트
        skills = AGENT_SKILLS_KO.get(agent, {})
        skill_line = f"- {agent_ko}의 한국어 공식 스킬 이름: {', '.join(skills.values())}" if skills else ""

        prompt = f"""발로란트 프로씬 분석가 입장에서 {agent_ko}의 다음 패치 전망을 써주세요.

제공 데이터 (이 수치만 사용, 없는 통계 절대 언급 금지):
- 예측 방향: {direction}
- 신호 강도: {signal_strength}
- 주요 근거: {dir_evidence}
- 참고 맥락 (뉘앙스 보정용, 방향 바뀌지 않음): {cnt_evidence}
- 기타 신호: {signal_text}
- 마지막 패치: {patch_ref}
{map_line_prompt}
{skill_line}

글쓰기 지침:
- 정확히 2~3문장. 초과 금지.
- 발로란트 프로씬 현업 용어를 자연스럽게 섞어 쓸 것
  (픽률/승률, 메타 픽, 유틸 효율, 인포 수집, 교전 개시, 사이드 밸런스,
   랭크/프로씬, 티어, 포스트플랜트, 로테이션 압박, 구성 강제, 팀파이트 기여, 임팩트 등)
- 신호 강도에 맞게 타이밍 표현 조절:
  · 강함 → "이번 패치에 조정이 들어올 것으로 보입니다" 류
  · 중간 → "가까운 시일 내", "이번 혹은 다음 패치" 류
  · 약함 → "당장은 아니더라도 중장기적으로 조정이 예상됩니다" 류
- 숫자 나열로 시작하지 말 것 — 가장 인상적인 포인트로 자연스럽게 열 것
- 분석가가 의견을 내는 톤 — 보고서 투 금지, 팬심 투 금지
- 전체 흐름이 "{direction}" 방향과 일치해야 함 (방향 의심 표현 절대 금지)
- 패치 이력(최근 너프/버프)은 배경 맥락일 뿐 — 예측 방향과 모순되는 논조로 쓰지 말 것
  · 예: 버프 예측인데 "너프 영향이 아직 판정 안 됨" 식의 관망 톤 금지
  · 최근 너프 후 버프 예측이면 "너프가 과했다/부족했다" 식으로 방향에 녹일 것
- 결론을 두 번 쓰지 말 것 — 마지막 문장이 방향을 담은 결론
- 스킬 언급 시 위에 제공된 한국어 공식 스킬 이름을 절대 축약하지 말고 풀네임 그대로 사용 (예: "폭파봇 지옥"을 "지옥"으로 줄이면 안 됨, 영어명·설명형 표현도 금지)
- 스킬 이름이 제공되지 않은 경우 스킬 이름 직접 언급 금지
- 맵 이름(브리즈·헤이번·어센트·바인드 등) 절대 언급 금지. 단, 위 데이터에 맵 특화 정보가 명시된 경우에만 허용.
- 패치 언급 시 반드시 "{patch_ref}" 표현 사용. VxxAx·ExxAx 형식 액트 코드명 절대 금지
- 요원 이름은 한국어 공식 이름만 사용 (영어 이름 금지):
  제트·레이나·레이즈·네온·피닉스·아이소·요루·웨이레이·브림스톤·바이퍼·오멘·아스트라·하버·클로브
  소바·페이드·스카이·브리치·케이오·게코·킬조이·사이퍼·데드락·바이스·세이지·테호·베토·믹스·체임버
- 확률 수치 금지, 마침표로 끝낼 것. 마크다운 금지(#, *, ** 등 일절 사용 금지).
- "라이엇"은 반드시 "라이엇"으로 표기 (라이웃·라이엇이 아닌 라이엇)
- 금지 표현: 킷 / 키트 / 특성상 / 구조적 / 근본적인 / 개편 / 설계 의도 / 오버튠드 / 언더튠드 / 랭겜
- 제공된 데이터에 없는 과거 통계·역사적 수치·타 시즌 비교 절대 언급 금지
- 스킬 메커니즘 설명(사이클·쿨다운·작동 방식 등) 금지 — 스킬 이름만 언급"""

        try:
            resp = self._anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except Exception:
            return self._template(r)

    def _template(self, r: dict) -> str:
        """API 실패 시 사용하는 간단 템플릿 폴백."""
        agent_ko = AGENT_NAME_KO.get(r["agent"], r["agent"])
        verdict  = r["verdict"]
        rank_pr  = r["rank_pr"]
        vct_pr   = r["vct_pr"]

        if "nerf" in verdict:
            return (
                f"{agent_ko}은(는) 현재 랭크 픽률 {rank_pr:.1f}%, VCT 픽률 {vct_pr:.1f}%로 "
                f"메타 상단을 점유 중입니다. 너프 조정이 예상됩니다."
            )
        elif "buff" in verdict:
            return (
                f"{agent_ko}의 랭크 픽률 {rank_pr:.1f}%, VCT 픽률 {vct_pr:.1f}%로 "
                f"현재 메타에서 외면받고 있습니다. 버프 조정이 필요한 상황입니다."
            )
        else:
            return (
                f"{agent_ko}은(는) 랭크·VCT 양쪽에서 모두 저픽 상태가 지속되고 있습니다. "
                f"수치 조정만으로는 한계가 있어 리워크 가능성이 있습니다."
            )


# ─── 시뮬레이터 AI 분석 ──────────────────────────────────────────────────────

def generate_sim_analysis(changes_desc: str, result_summary: str) -> str:
    """패치 시뮬레이션 결과에 대한 AI 분석 생성. 크레딧 부족 등 에러 시 한국어 메시지 반환."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "API 키가 설정되지 않아 AI 분석을 생성할 수 없습니다."

    system = """너는 발로란트 프로씬 전문 분석가다. 역할군 분류를 정확히 지켜야 한다.

역할군별 요원 (절대 틀리면 안 됨):
- 1선 타격대: 제트, 레이즈, 네온, 웨이레이
- 2선 타격대: 레이나, 피닉스, 요루, 아이소
- 척후대: 소바, 페이드, 스카이, 브리치, 케이오, 게코, 테호
- 전략가: 브림스톤, 바이퍼, 오멘, 아스트라, 하버, 클로브, 믹스
- 감시자: 킬조이, 사이퍼, 데드락, 바이스, 세이지, 체임버

경쟁 요원은 반드시 같은 세부 역할군 내에서만 언급.
예: 아이소(2선 타격대)의 경쟁 상대 = 레이나, 피닉스, 요루. 절대 제트(1선)나 킬조이(감시자)가 아님.
예: 제트(1선 타격대)의 경쟁 상대 = 레이즈, 네온, 웨이레이. 절대 레이나(2선)가 아님.

요원 이름은 한국어 공식명만 사용. "라이엇"으로 표기."""

    prompt = f"""아래 가상 패치의 메타 영향을 분석해줘.

변경사항:
{changes_desc}

모델 예측 결과:
{result_summary}

작성 규칙:
- 3~4문장. 간결하게.
- "현재 상태" 수치를 반드시 확인하고 분석의 출발점으로 삼을 것 (랭크/VCT 픽률이 높으면 강한 요원, 낮으면 약한 요원)
- 버프 변경이 강한 요원에게 적용되면 "더 강해진다", 약한 요원에게 적용되면 "회복을 시도" 식으로 현재 상태에 맞게 분석
- 해당 요원의 위상 변화 + 같은 세부 역할군 내 경쟁 구도 변화 분석
- 프로씬 용어 자연스럽게 사용 (픽률, 승률, 메타 픽, 유틸 효율, 구성 강제력 등)
- 다른 역할군 요원과 비교 금지 (위 시스템 프롬프트의 분류표 엄수)
- 마크다운 금지, 마침표로 끝낼 것"""

    try:
        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        err = str(e)
        if "credit" in err.lower() or "balance" in err.lower() or "billing" in err.lower():
            return "AI 분석 크레딧이 부족합니다. Anthropic 콘솔에서 크레딧을 충전해주세요."
        return f"AI 분석 생성 실패: {err}"
