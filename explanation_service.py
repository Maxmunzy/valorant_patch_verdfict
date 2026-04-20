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
        """캐시 확인 후 설명 반환. 캐시 미스 시 생성.

        중요: 템플릿 폴백(API 실패)은 캐시에 저장하지 않는다.
        폴백을 캐시하면 한 번 실패한 뒤 계속 폴백이 유지되는 문제가 발생한다.
        """
        agent   = r["agent"]
        verdict = r["verdict"]
        act     = r.get("act", "")
        rank_pr_r = round(r.get("rank_pr", 0), 1)
        vct_pr_r  = round(r.get("vct_pr", 0), 1)
        # v3: 템플릿 폴백이 캐시에 박힌 이전 상태를 무효화
        cache_key = f"v3::{agent}::{verdict}::{act}::{rank_pr_r}::{vct_pr_r}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        explanation, from_api = self._generate(r)
        # API 성공 결과만 캐시. 폴백은 매 요청마다 재시도해서 API 복구되면 즉시 반영
        if from_api:
            self._cache[cache_key] = explanation
            try:
                with open(self._cache_path, "w", encoding="utf-8") as f:
                    json.dump(self._cache, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return explanation

    def _generate(self, r: dict) -> tuple[str, bool]:
        """Claude Haiku로 양면 분석 스타일의 설명 생성.

        Returns:
            (text, from_api): text는 생성된 설명, from_api는 Claude API 성공 여부.
            from_api=False면 템플릿 폴백이 반환된 것.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("[explanation] ANTHROPIC_API_KEY 미설정 — 템플릿 폴백")
            return self._template(r), False

        # 신규 요원: 패치 이력 없음 → 모델 예측 신뢰도 낮음
        # 이 응답은 결정론적이므로 from_api=True 로 취급해도 캐시 부작용 없음
        acts_since_r = int(r.get("acts_since_patch", 0) or 0)
        if acts_since_r >= 90:
            agent_ko_r = AGENT_NAME_KO.get(r["agent"], r["agent"])
            return (
                f"출시 이후 패치 이력이 없어 예측 신뢰도가 낮습니다. "
                f"데이터가 충분히 쌓이면 {agent_ko_r}에 대한 정밀 분석이 가능해집니다."
            ), True

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

        # ── VCT 패치 적용 지연 맥락 (웨이레이 등 최근 너프 요원용) ──
        vct_lag_note = ""
        if agent == "Waylay":
            vct_lag_note = (
                "\nVCT 패치 적용 지연 (반드시 반영):\n"
                "- 현재 날짜: 2026년 4월 17일, 최신 클라이언트 패치: 12.07 (밸런스 변경 없음)\n"
                "- 12.06 패치의 웨이레이 너프는 VCT 대회에 2026년 4월 24일부터 적용 예정\n"
                "- 따라서 현재 VCT 픽률은 너프 전 기준이며, 프로씬에는 아직 12.06이 반영되지 않음\n"
                "- 금지 표현: \"12.06 패치 이후에도 프로씬에서 우위\", \"너프 후에도 VCT에서 지배적\" 류\n"
                "- 대신 \"12.06 너프가 VCT에 4월 24일부터 적용되면 실제 영향 확인 가능\" 식으로 서술"
            )

        prompt = f"""발로란트 프로씬 분석가 입장에서 {agent_ko}의 다음 패치 전망을 써주세요.
{vct_lag_note}
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
- Riot Games는 반드시 "라이엇"으로 표기. "라이옷", "라이웃", "라이어트" 등 변형 표기 절대 금지
- 금지 표현: 킷 / 키트 / 특성상 / 구조적 / 근본적인 / 개편 / 설계 의도 / 오버튠드 / 언더튠드 / 랭겜 / 라이옷 / 라이웃
- 제공된 데이터에 없는 과거 통계·역사적 수치·타 시즌 비교 절대 언급 금지
- 스킬 메커니즘 설명(사이클·쿨다운·작동 방식 등) 금지 — 스킬 이름만 언급
- 모델 라벨 노출 금지: "strong_nerf", "nerf", "buff", "strong_buff" 같은 영어 라벨은 우리 XGBoost 모델의 내부 라벨이며, 라이엇의 판정이 아니다. 이 단어를 그대로 쓰지 말고 "너프 대상", "상향 필요", "모델상 강한 너프 분류" 등 한국어로 풀어서 서술할 것. 주어는 "우리 모델" 또는 "예측 모델" — "라이엇의 판정" 식 표현 절대 금지."""

        try:
            resp = self._anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip(), True
        except Exception as e:
            logger.exception(f"[explanation] Anthropic API 실패 (agent={agent}): {e}")
            return self._template(r), False

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
            # stable: 픽률 기반 세분화
            if vct_pr >= 20 or rank_pr >= 25:
                return (
                    f"{agent_ko}은(는) 랭크 {rank_pr:.1f}% · VCT {vct_pr:.1f}% 픽률로 "
                    f"메타 상위권에 안착한 상태입니다. 당장 큰 조정은 없을 전망이지만 신호는 누적 중입니다."
                )
            elif vct_pr >= 8 or rank_pr >= 10:
                return (
                    f"{agent_ko}은(는) 랭크 {rank_pr:.1f}% · VCT {vct_pr:.1f}% 픽률로 "
                    f"균형 잡힌 구간에 있습니다. 이번 패치에서 큰 조정은 없을 것으로 보입니다."
                )
            else:
                return (
                    f"{agent_ko}은(는) 랭크·VCT 양쪽에서 저픽 상태가 지속되고 있습니다. "
                    f"수치 조정만으로는 한계가 있어 중장기적 리워크 가능성도 있습니다."
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

VCT 패치 적용 지연 (중요):
- 현재 날짜: 2026년 4월 17일
- 최신 클라이언트 패치: 12.07 (밸런스 변경 없음)
- 12.06 패치 (웨이레이 너프 포함)는 VCT 대회에 2026년 4월 24일부터 적용 예정
- 따라서 현재 VCT 경기에서 웨이레이는 아직 너프 전 버전으로 플레이 중
- "12.06 패치 이후 프로씬에서도..." 같은 표현 금지 (프로씬엔 아직 미적용)
- 웨이레이 VCT 픽률이 높은 건 12.06 너프가 반영되지 않은 상태 기준임을 반드시 명시

모델 예측 라벨 표기 (반드시 준수):
- "strong_nerf", "nerf", "buff", "strong_buff"는 우리 XGBoost 모델이 출력하는 내부 라벨이며, 라이엇의 판정이 아니다.
- 이 영어 라벨을 절대 그대로 노출하지 말 것. "라이엇의 strong_nerf 판정" 같은 표현 금지.
- 한국어로 풀어서 서술할 것:
  · strong_nerf → "우리 모델상 강한 너프 대상으로 분류" / "너프 필요도 매우 높음"
  · nerf → "너프 대상으로 분류" / "조정 압력이 있음"
  · buff → "버프 대상으로 분류" / "상향이 필요한 상태"
  · strong_buff → "강한 버프가 필요한 상태" / "대규모 상향 대상"
- 신뢰도 수치는 "모델 신뢰도 N%" 또는 "N% 확률로" 식으로 표현.
- 주어는 반드시 "우리 모델", "예측 모델", "모델상" 등으로 명시 — "라이엇이 판정" 식 표현 절대 금지.

요원 이름은 한국어 공식명만 사용. "라이엇"으로 표기."""

    prompt = f"""아래 가상 패치의 메타 영향을 분석해줘.

변경사항:
{changes_desc}

모델 예측 결과:
{result_summary}

작성 규칙:
- 3~4문장. 간결하게.
- "현재 상태" 수치를 반드시 확인하고 분석의 출발점으로 삼을 것
- **픽률 해석 기준 (엄수)**:
  · 랭크 픽률: 30%↑ = 메타 상단 고픽 / 15~30% = 상위권 / 8~15% = 중위권 / 3~8% = 저픽·외면 / 3% 미만 = 사실상 미채용
  · VCT 픽률: 30%↑ = 프로씬 메타 핵심 / 15~30% = 주요 픽 / 8~15% = 준수·대안 픽 / 3~8% = 저픽·외면 / 3% 미만 = 사실상 미채용
  · "준수한 픽률", "탄탄한 입지", "꾸준한 기용" 같은 긍정 표현은 랭크 15% 이상 또는 VCT 15% 이상일 때만 사용
  · 랭크 8% 미만 + VCT 10% 미만 = "외면받는 상황", "입지 약함", "버프가 필요한 상태"로 서술
- 버프 변경이 강한 요원(고픽)에게 적용되면 "더 강해진다", 약한 요원(저픽)에게 적용되면 "회복·재진입 시도" 식으로 서술
- 해당 요원의 위상 변화 + 같은 세부 역할군 내 경쟁 구도 변화 분석
- 프로씬 용어 자연스럽게 사용 (픽률, 승률, 메타 픽, 유틸 효율, 구성 강제력 등)
- 다른 역할군 요원과 비교 금지 (위 시스템 프롬프트의 분류표 엄수)
- **표본 크기 주의**: VCT 픽률이 5% 미만이면 표본이 작아 VCT 승률은 신뢰할 수 없다. 이 경우 "프로씬에서 N% 승률" 같은 표현 절대 금지. 대신 "프로씬 외면", "표본 부족으로 의미 없음", "사실상 미채용" 등으로 표현
- **데이터 지연 주의**: 요약에 "VCT 데이터 N액트 전" 표시가 있으면 "최근 VCT에서 거의 안 쓰임" 으로 해석
- **웨이레이 전용 규칙**: 웨이레이 분석 시 반드시 "12.06 너프가 VCT에 4월 24일부터 적용 예정이라 현재 44.8% 픽률은 너프 전 기준" 이라는 맥락을 명시할 것. 현재 VCT 픽률을 "현재 메타를 지배 중"으로 해석하지 말 것 — 너프 후 실제 픽률은 하락이 예상됨
- 마크다운 금지, 마침표로 끝낼 것"""

    try:
        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=700,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        err = str(e)
        if "credit" in err.lower() or "balance" in err.lower() or "billing" in err.lower():
            return "AI 분석 크레딧이 부족합니다. Anthropic 콘솔에서 크레딧을 충전해주세요."
        return f"AI 분석 생성 실패: {err}"
