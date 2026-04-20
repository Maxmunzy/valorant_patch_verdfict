"""
clean_agent_skills.py
agent_skills.json 후처리 정제 스크립트

crawl_agent_skills.py 실행 후 자동 또는 수동 실행.
1. 스탯명 정규화 (rowspan/HTML/위키마크업 제거)
2. value=None인 raw에서 숫자 재파싱
3. 유닛 통일 (seconds, meters 등)
4. 의미 없는 메타 스탯(패치 버전 마커, 빈 값) 제거
5. P(패시브) 슬롯 제거 (시뮬레이터에서 사용 안 함)
6. 결과를 agent_skills.json에 덮어쓰기

실행:
  python clean_agent_skills.py
  python clean_agent_skills.py --dry-run   # 변경 미리보기만
"""

import json
import re
import sys
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "agent_skills.json"

# ─── 스탯명 정규화 맵 ─────────────────────────────────────────────────────────
# 자주 등장하는 rowspan/HTML 오염 패턴 → 정제된 이름으로 매핑
# 없는 건 자동 정규화 로직이 처리
STAT_NAME_NORMALIZE: dict[str, str] = {
    # rowspan 접두어 제거
    # (자동 처리되지만 수동 오버라이드가 필요한 특수 케이스)
}

# 완전 삭제할 스탯 (value도 없고 의미도 없는 메타 마커)
STAT_BLACKLIST_PATTERNS = [
    r"^\{\{",               # {{Tick}}, {{patchv|...}} 등 위키 템플릿
    r"^x[\d.]+\s+multiplier",  # x0.5 multiplier to objects
    r"^Total\s+\d+.*tick",  # Total 76-79 ticks (중복 요약)
]

# ─── 유닛 정규화 ─────────────────────────────────────────────────────────────
UNIT_NORMALIZE = {
    "second": "seconds",
    "sec": "seconds",
    "secs": "seconds",
    "meter": "meters",
    "m": "meters",
    "credits": "credits",
    "credit": "credits",
    "HP": "HP",
    "hp": "HP",
    "HP/s": "HP/s",
    "hp/s": "HP/s",
    "per second": "/s",
    "meters/second": "m/s",
    "meters / second": "m/s",
    "blades": "blades",
    "degrees": "degrees",
}


def clean_stat_name(raw: str) -> str | None:
    """스탯 이름에서 HTML/위키 마크업 제거 후 정규화된 이름 반환. None이면 삭제 대상."""
    name = raw.strip()

    # 블랙리스트 체크
    for pat in STAT_BLACKLIST_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return None

    # rowspan="N"|실제이름  or  rowspan=N|실제이름
    m = re.match(r'rowspan\s*=\s*"?\d+"?\s*\|?\s*(.+)', name)
    if m:
        name = m.group(1).strip()

    # <!--...--> 제거
    name = re.sub(r'<!--.*?-->', '', name).strip()

    # <u>, <small>, <br>, <sup/> 등 HTML 태그 제거
    name = re.sub(r'<[^>]+>', ' ', name).strip()

    # {{...}} 위키 템플릿 제거
    name = re.sub(r'\{\{[^}]*\}\}', '', name).strip()

    # [[...]] 위키 링크 → 텍스트만
    name = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', name).strip()

    # '' 등 위키 볼드/이탤릭
    name = re.sub(r"'{2,}", '', name).strip()

    # 연속 공백 정리
    name = re.sub(r'\s+', ' ', name).strip()

    # 빈 문자열이면 삭제
    if not name or name == "|":
        return None

    # 수동 오버라이드 확인
    if name in STAT_NAME_NORMALIZE:
        return STAT_NAME_NORMALIZE[name]

    return name


def reparse_value(raw: str) -> tuple[float | None, str]:
    """raw 문자열에서 숫자+단위 재파싱 시도."""
    # HTML/위키 태그 제거
    cleaned = re.sub(r'<[^>]+>', ' ', raw)
    cleaned = re.sub(r'\{\{[^}]*\}\}', '', cleaned)
    cleaned = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', cleaned)
    cleaned = cleaned.strip()

    # 첫 줄만
    first_line = cleaned.split('\n')[0].strip()

    # "Total X seconds" 또는 "Total duration: X seconds" 패턴 (가장 흔한 null 원인)
    total_m = re.search(r'Total\s+(?:duration:\s*)?(\d+(?:\.\d+)?)\s*(\w+)', first_line)
    if total_m:
        return float(total_m.group(1)), normalize_unit(total_m.group(2))

    # "Within X seconds" 패턴
    within_m = re.match(r'Within\s+(\d+(?:\.\d+)?)\s*(\w+)', first_line)
    if within_m:
        return float(within_m.group(1)), normalize_unit(within_m.group(2))

    # "Minimum: X seconds" / "Maximum: X seconds" 패턴
    minmax_m = re.match(r'(?:Minimum|Maximum):\s*(\d+(?:\.\d+)?)\s*(.*)', first_line)
    if minmax_m:
        val = float(minmax_m.group(1))
        unit = minmax_m.group(2).strip().rstrip('.')
        return val, normalize_unit(unit)

    # <nowiki/>+15% 같은 패턴
    pct_m = re.match(r'[+\-]?\s*(\d+(?:\.\d+)?)\s*%', first_line)
    if pct_m:
        return float(pct_m.group(1)), "%"

    # "Agent/Bot/Trap detecting ...: X meters" 패턴
    detect_m = re.search(r':\s*(\d+(?:\.\d+)?)\s*meters', first_line)
    if detect_m:
        return float(detect_m.group(1)), "meters"

    # "Inner: X meters" 패턴 (첫 번째 값 사용)
    inner_m = re.search(r'(?:Inner|Min|Minimum)[^:]*:\s*(\d+(?:\.\d+)?)\s*meters', first_line)
    if inner_m:
        return float(inner_m.group(1)), "meters"

    # 일반 숫자 + 단위
    num_m = re.match(r'([+\-]?\d+(?:\.\d+)?)\s*(.*)', first_line)
    if num_m:
        val = float(num_m.group(1))
        unit = num_m.group(2).strip().rstrip('.').strip()
        # 괄호 이후 제거
        unit = re.split(r'[(<]', unit)[0].strip()
        return val, normalize_unit(unit)

    return None, ""


def normalize_unit(unit: str) -> str:
    """유닛 문자열 통일."""
    u = unit.strip().lower()

    # 오염된 유닛 클린업 (예: "-0.75 seconds", "per tickTotal 160")
    # 숫자로 시작하면 유닛 아님
    if re.match(r'^[\-+]?\d', u):
        # "per tickTotal 160" 같은 건 빈 문자열
        return ""

    u = UNIT_NORMALIZE.get(u, unit.strip())

    # "seconds at full size..." 같은 건 "seconds"로
    if u.startswith("seconds"):
        return "seconds"
    if u.startswith("meters"):
        return "meters"

    return u


def is_meta_marker(stat_name: str, stat_val: dict) -> bool:
    """패치 버전 마커, 빈 raw 등 의미 없는 항목 판별."""
    raw = stat_val.get("raw", "")

    # {{Tick}}{{patchv|...}} 패턴 — 패치 버전 마커
    if "{{patchv" in raw or "{{Tick}}" in raw:
        return True

    # raw가 완전히 비었거나 "v" 하나 등
    if len(raw.strip()) <= 2:
        return True

    # 숫자 접두사 스탯명이면서 value=None → 보통 메타 주석
    if stat_val.get("value") is None and re.match(r'^[\d.]', stat_name):
        return True

    return False


def clean_agent_skills(data: dict, verbose: bool = False) -> dict:
    """전체 agent_skills 데이터 정제."""
    cleaned = {}
    stats_removed = 0
    stats_renamed = 0
    stats_reparsed = 0
    stats_total = 0

    for agent in sorted(data.keys()):
        slots = data[agent]
        agent_clean = {}

        for slot_key in sorted(slots.keys()):
            # P(패시브) 슬롯 제거
            if slot_key == "P":
                continue

            slot_data = slots[slot_key]
            if not isinstance(slot_data, dict):
                continue

            # stats 이외 필드 복사
            new_slot = {k: v for k, v in slot_data.items() if k != "stats"}
            new_stats = {}

            for stat_name, stat_val in slot_data.get("stats", {}).items():
                stats_total += 1

                # 1. 메타 마커 제거
                if is_meta_marker(stat_name, stat_val):
                    stats_removed += 1
                    if verbose:
                        print(f"  DEL  {agent}/{slot_key}: {stat_name}")
                    continue

                # 2. 스탯명 정규화
                new_name = clean_stat_name(stat_name)
                if new_name is None:
                    stats_removed += 1
                    if verbose:
                        print(f"  DEL  {agent}/{slot_key}: {stat_name}")
                    continue

                if new_name != stat_name:
                    stats_renamed += 1
                    if verbose:
                        print(f"  REN  {agent}/{slot_key}: {stat_name!r} -> {new_name!r}")

                # 3. value=None인 항목 재파싱
                new_val = dict(stat_val)  # shallow copy
                if new_val.get("value") is None:
                    reparsed_val, reparsed_unit = reparse_value(new_val.get("raw", ""))
                    if reparsed_val is not None:
                        new_val["value"] = reparsed_val
                        new_val["unit"] = reparsed_unit
                        stats_reparsed += 1
                        if verbose:
                            print(f"  FIX  {agent}/{slot_key}: {new_name} = {reparsed_val} {reparsed_unit}")

                # 4. 유닛 정규화
                if new_val.get("unit"):
                    new_val["unit"] = normalize_unit(new_val["unit"])

                # 5. 중복 이름 처리 (같은 슬롯에 같은 이름 → 첫 번째 유지)
                if new_name in new_stats:
                    if verbose:
                        print(f"  DUP  {agent}/{slot_key}: {new_name} (skipped)")
                    continue

                new_stats[new_name] = new_val

            new_slot["stats"] = new_stats
            agent_clean[slot_key] = new_slot

        cleaned[agent] = agent_clean

    print(f"\n정제 완료:")
    print(f"  전체 스탯: {stats_total}")
    print(f"  삭제: {stats_removed}")
    print(f"  이름 변경: {stats_renamed}")
    print(f"  값 재파싱: {stats_reparsed}")
    print(f"  최종 스탯: {stats_total - stats_removed}")

    return cleaned


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv or dry_run

    if not DATA_PATH.exists():
        print(f"ERROR: {DATA_PATH} 없음. crawl_agent_skills.py를 먼저 실행하세요.")
        sys.exit(1)

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    print(f"입력: {len(data)}개 요원")

    cleaned = clean_agent_skills(data, verbose=verbose)

    if dry_run:
        print("\n[DRY RUN] 파일 변경 없음.")
    else:
        DATA_PATH.write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n저장: {DATA_PATH}")


if __name__ == "__main__":
    main()
