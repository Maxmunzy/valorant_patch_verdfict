"""
parse_patch_text.py
Liquipedia / Fandom get_page_text 결과를 파싱해 JSON으로 저장
Usage: python parse_patch_text.py <agent_name> <input_txt_file>
"""
import re, json, sys
from pathlib import Path

OUTPUT_DIR = Path("data/patch_history")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 단위 패턴 (단어 경계 포함 - 다음 단어 첫 글자를 잘못 캡처하지 않도록)
UNIT_PAT = r'(?:HP\/s(?:ec)?|seconds?|degrees?|credits?|points?|HP|%|m|x|\/s(?:ec)?|s)(?![a-zA-Z])'


def normalize_arrows(text: str) -> str:
    """Fandom의 → 화살표를 >>> 로 통일"""
    # → (U+2192) 및 → (HTML entity 형태 변환 후) 모두 처리
    text = text.replace('→', '>>>')
    text = text.replace('->', '>>>')
    return text


def parse_version_section(full_text: str) -> list[dict]:
    """'Version Balance Changes' 또는 'Update History' 섹션 파싱 (Liquipedia + Fandom 공용)"""
    # Fandom: "Update History" / Liquipedia: "Version Balance Changes"
    m = re.search(
        r'(?:Version\s+Balance\s+Changes|Update\s+History)\s*(?:\[\s*(?:edit|보기|편집)\s*\])?\s*\n?(.*?)'
        r'(?:Notable Players|External Links|References|Navigation|See also|\Z)',
        full_text, re.DOTALL | re.IGNORECASE)
    if not m:
        return []

    section = normalize_arrows(m.group(1).strip())

    # >>> 앞뒤 숫자(스탯 값)가 버전으로 오인되지 않도록 "금지 구간" 수집
    # 주의: >>> 이후 값(after)과 주변 문맥까지 금지 구간에 포함
    arrow_re = re.compile(r'([\d.]+)\s*([a-zA-Z%/]*)\s*>>>\s*([\d.]+)')
    forbidden = set()
    for am in arrow_re.finditer(section):
        # before 값
        for i in range(am.start(1), am.end(1)): forbidden.add(i)
        # after 값 + after 이후 2자리까지 (단위 숫자가 이어질 경우 대비)
        for i in range(am.start(3), am.end(3) + 2): forbidden.add(i)

    # 슬래시로 구분된 다중 값 (예: 0.75/0.6) 에서 파생된 숫자도 금지 구간에 추가
    slash_re = re.compile(r'([\d.]+)\s*/\s*([\d.]+)')
    for sm in slash_re.finditer(section):
        for i in range(sm.start(1), sm.end(1)): forbidden.add(i)
        for i in range(sm.start(2), sm.end(2)): forbidden.add(i)

    # 슬래시 값이 >>> 앞(before)에 있는 경우: after 값도 금지 구간에 추가
    # 예: "0.75/0.6 (Primary/Scoped) >>> 0.7" 에서 0.7 을 금지
    slash_before_arrow_re = re.compile(
        r'([\d.]+)\s*/\s*[\d.]+[^>]{0,40}>>>\s*([\d.]+)'
    )
    for sm in slash_before_arrow_re.finditer(section):
        for i in range(sm.start(1), sm.end(1)): forbidden.add(i)
        for i in range(sm.start(2), sm.end(2) + 2): forbidden.add(i)

    # 버전 번호 후보 찾기
    # - 금지 구간 제외
    # - "to X.XXs", "from X.XXs", "over X.XXs" 같은 문장 중간 숫자 제외
    # - Fandom 형식: v11.08 → 11.08 (v 접두사 허용)
    # - Liquipedia: 공백 앞뒤 위치 (단일 라인)
    # [a-z]? suffix: 버전 suffix 는 b (예: 11.07b) 정도만 허용; s, m 같은 단위는 제외
    ver_re = re.compile(r'(?<![.\d])v?(\d+\.\d+b?)\s')
    # 전치사/부사 뒤에 오는 숫자는 버전이 아님
    preposition_re = re.compile(r'\b(?:to|from|over|at|in|of|per|by)\s+$', re.IGNORECASE)

    # 버전 번호 뒤에 단위가 오면 수치값 (버전 아님)
    unit_suffix_re = re.compile(
        r'^(?:s(?:econds?)?|HP(?:/s)?|%|m(?:eters?)?|credits?|points?|orbs?|x|units?)\b',
        re.IGNORECASE
    )

    ver_positions = []
    for vm in ver_re.finditer(section):
        if vm.start(1) in forbidden:
            continue
        # 앞 20자에 전치사가 있으면 스킵
        prefix = section[max(0, vm.start(1)-20):vm.start(1)]
        if preposition_re.search(prefix):
            continue
        # 뒤에 단위(s, HP, %, m 등)가 오면 수치값 → 스킵
        # ver_re 의 마지막 \s 뒤부터 시작하는 텍스트
        suffix = section[vm.end():].lstrip()
        if unit_suffix_re.match(suffix):
            continue
        ver_positions.append((vm.start(1), vm.end(), vm.group(1)))

    # 위치 기반으로 패치 슬라이스
    patches = []
    for idx, (start, end, ver) in enumerate(ver_positions):
        next_start = ver_positions[idx + 1][0] if idx + 1 < len(ver_positions) else len(section)
        change_text = section[end:next_start].strip().replace('\n', ' ').replace('  ', ' ')

        all_changes = extract_all_changes(change_text)

        is_bugfix = bool(re.search(r'\bfixed\b|\bbug\b|\bexploit\b', change_text, re.IGNORECASE))
        is_qol = bool(re.search(r'\bquality\b|\bui\b|\bvisual\b|\banimation\b|\badjust', change_text, re.IGNORECASE))

        numeric_changes = [c for c in all_changes if c["change_type"] == "numeric"]

        patches.append({
            "patch": ver,
            "raw": change_text[:800],
            "is_bugfix": is_bugfix,
            "is_qol": is_qol,
            "numeric_changes": numeric_changes,
            "all_changes": all_changes,
        })

    return patches


def extract_all_changes(text: str) -> list[dict]:
    """모든 종류의 변경사항 추출"""
    changes = []

    # 1) 수치 변경: 숫자 >>> 숫자
    # 단위 패턴에 단어 경계 추가로 다음 단어 첫 글자 오캡처 방지
    re_numeric = re.compile(
        r'([A-Za-z][A-Za-z0-9\s\/\(\)\-\.\:]{2,80}?)\s*:?\s+'
        r'([\d.]+)\s*(' + UNIT_PAT + r')?\s*'
        r'>>>\s*([\d.]+)\s*(' + UNIT_PAT + r')?',
        re.IGNORECASE
    )

    numeric_spans = []
    for m in re_numeric.finditer(text):
        label = m.group(1).strip().rstrip(':').strip()
        before = float(m.group(2).rstrip('.'))
        before_unit = (m.group(3) or '').lower().strip()
        after = float(m.group(4).rstrip('.'))
        after_unit = (m.group(5) or m.group(3) or '').lower().strip()

        if before == after:
            continue

        stat_name = infer_stat(label)
        cost_stats = {"cost", "ult_cost", "cooldown", "delay"}
        direction = ("nerf" if after > before else "buff") if stat_name in cost_stats \
                    else ("nerf" if after < before else "buff")

        changes.append({
            "change_type": "numeric",
            "ability_slot": infer_slot(label),
            "context_label": label[-80:],
            "stat": stat_name,
            "before": before,
            "before_unit": before_unit,
            "after": after,
            "after_unit": after_unit,
            "direction": direction,
        })
        numeric_spans.append((m.start(), m.end()))

    # 2) Free >>> N 코스트 변경 (Free = 0 으로 간주)
    re_free = re.compile(
        r'([A-Za-z][A-Za-z0-9\s\/\(\)\-\.\:]{2,60}?)\s*:?\s+'
        r'Free\s*>>>\s*([\d.]+)\s*(' + UNIT_PAT + r')?',
        re.IGNORECASE
    )
    for m in re_free.finditer(text):
        label = m.group(1).strip().rstrip(':').strip()
        after = float(m.group(2))
        after_unit = (m.group(3) or '').lower().strip()
        changes.append({
            "change_type": "numeric",
            "ability_slot": infer_slot(label),
            "context_label": label[-80:],
            "stat": "cost",
            "before": 0,
            "before_unit": "free",
            "after": after,
            "after_unit": after_unit,
            "direction": "nerf",  # 무료에서 유료로 = nerf
        })
        numeric_spans.append((m.start(), m.end()))

    # 3) 비수치 >>> 변경
    re_nonnumeric = re.compile(
        r'([A-Za-z][A-Za-z0-9\s\/\(\)\-\.]{2,60}?)\s+'
        r'([A-Za-z][A-Za-z0-9\s\-\.\/]{1,40}?)\s*>>>\s*([A-Za-z][A-Za-z0-9\s\-\.\/]{1,40})',
        re.IGNORECASE
    )
    for m in re_nonnumeric.finditer(text):
        if any(s <= m.start() <= e for s, e in numeric_spans):
            continue
        before_val = m.group(2).strip()
        after_val = m.group(3).strip()
        if re.fullmatch(r'[\d.]+', before_val) or re.fullmatch(r'[\d.]+', after_val):
            continue
        label = m.group(1).strip()
        changes.append({
            "change_type": "non_numeric",
            "ability_slot": infer_slot(label + ' ' + before_val),
            "context_label": label[-60:],
            "stat": "mechanic",
            "before": before_val,
            "after": after_val,
            "direction": "change",
        })

    # 4) 효과 추가: Now/Will now/Added/Can now/Grants
    re_added = re.compile(
        r'(?:(?:Will\s+)?Now\s+(?:immune|deals|applies|heals|slows|reveals|also|gains|grants|always|properly)|'
        r'Added|Can now|Grants|New\s+(?:effect|mechanic)|Now\s+has|Will\s+now\s+(?:quick|auto|always))'
        r'[^\.]{5,120}',
        re.IGNORECASE
    )
    for m in re_added.finditer(text):
        snippet = m.group(0).strip()
        slot = infer_slot(text[max(0, m.start()-60):m.start()+60])
        changes.append({
            "change_type": "effect_added",
            "ability_slot": slot,
            "context_label": snippet[:100],
            "stat": "effect",
            "description": snippet[:100],
            "direction": "buff",
        })

    # 5) 효과 제거
    re_removed = re.compile(
        r'(?:No longer|Removed|Can no longer|Will no longer)'
        r'[^\.]{5,120}',
        re.IGNORECASE
    )
    for m in re_removed.finditer(text):
        snippet = m.group(0).strip()
        slot = infer_slot(text[max(0, m.start()-60):m.start()+60])
        changes.append({
            "change_type": "effect_removed",
            "ability_slot": slot,
            "context_label": snippet[:100],
            "stat": "effect",
            "description": snippet[:100],
            "direction": "nerf",
        })

    # 6) 리워크
    re_rework = re.compile(
        r'(?:Changed to|Redesigned|Reworked|Replaced|Switched to|Converted to)'
        r'[^\.]{3,120}',
        re.IGNORECASE
    )
    for m in re_rework.finditer(text):
        snippet = m.group(0).strip()
        slot = infer_slot(text[max(0, m.start()-60):m.start()+60])
        changes.append({
            "change_type": "rework",
            "ability_slot": slot,
            "context_label": snippet[:100],
            "stat": "mechanic",
            "description": snippet[:100],
            "direction": "change",
        })

    return changes


def infer_stat(label: str) -> str:
    ll = label.lower()
    # multiplier 먼저 (ult_cost보다 우선)
    if any(w in ll for w in ["multiplier", "multi", "mult"]):
        return "multiplier"
    if any(w in ll for w in ["duration", "time", "window", "active", "uptime"]):
        return "duration"
    # "ultimate cost" / "ult cost" 는 ult_cost로 먼저 처리
    if any(w in ll for w in ["ult cost", "ultimate cost"]):
        return "ult_cost"
    if any(w in ll for w in ["cost", "credit", "price"]):
        return "cost"
    if "charge" in ll:
        return "charges"
    if any(w in ll for w in ["damage", "dmg", "dps", "tick"]):
        return "damage"
    if any(w in ll for w in ["health", "hp", "heal"]):
        return "health"
    if "cooldown" in ll:
        return "cooldown"
    if any(w in ll for w in ["range", "radius", "distance", "size", "diameter", "length", "width", "height", "killzone", "zone"]):
        return "range"
    if any(w in ll for w in ["ult", "ultimate", "point"]) and "cost" not in ll:
        return "ult_cost"
    if any(w in ll for w in ["speed", "velocity"]):
        return "speed"
    if "delay" in ll:
        return "delay"
    if "fortif" in ll:
        return "fortify_delay"
    if "degree" in ll or "vision" in ll or "angle" in ll:
        return "range"
    return "other"


def infer_slot(label: str) -> str | None:
    ll = label.lower()
    # 명시적 슬롯 표기: 라벨 뒤쪽(가장 관련성 높은) 매칭 우선
    matches = list(re.finditer(r'\(([QECX])\)', label))
    if matches:
        return matches[-1].group(1)  # 마지막(가장 가까운) 슬롯
    matches = list(re.finditer(r'\b([QECX])\b', label))
    if matches:
        return matches[-1].group(1)
    slot_keywords = {
        "Q": ["slow orb", "updraft", "flashpoint", "incendiary", "nova pulse", "shock dart",
              "shock bolt", "trailblazer", "boom bot", "leer", "blindside", "curveball",
              "recon bolt", "headhunter", "wingman", "flash/drive", "nanoswarm", "paranoia",
              "relay bolt", "blast pack", "cascade", "sonic sensor", "meddle", "prowler",
              "special delivery", "undercut", "hot hands", "devour", "stealth drone",
              "frag/ment"],
        "E": ["barrier orb", "tailwind", "fault line", "sky smoke", "spycam",
              "guiding light", "gatecrash", "blaze", "rendezvous", "high tide", "high gear",
              "dark cover", "barrier mesh", "ruse", "seize", "double tap",
              "turret", "toxic screen", "razorvine", "waveform", "interceptor", "refract",
              "zero/point", "guided salvo", "gravnet"],
        "C": ["cloudburst", "aftershock", "stim beacon", "trapwire", "cyber cage", "owl drone",
              "paint shells", "fakeout", "trademark", "fast lane", "shrouded step",
              "haunt", "mosh pit", "cove", "pick-me-up", "alarmbot",
              "snake bite", "shear", "contingency", "dismiss", "crosscut",
              "harmonize", "m-pulse"],
        "X": ["bladestorm", "blade storm", "rolling thunder", "orbital strike", "neural theft",
              "hunter's fury", "seekers", "dimensional drift", "run it back", "tour de force",
              "showstopper", "empress", "lockdown", "overdrive", "reckoning", "annihilation",
              "not dead yet", "nightfall", "thrash", "steel garden", "kill contract",
              "null/cmd", "viper's pit", "armageddon", "resurrection", "bassquake",
              "evolution", "convergent paths", "from the shadows"],
    }
    for slot, keywords in slot_keywords.items():
        if any(kw in ll for kw in keywords):
            return slot
    return None


def parse_current_stats(full_text: str) -> dict:
    stats = {}
    patterns = [
        (r'Duration:\s*([\d.]+)', 'duration', 's'),
        (r'Cost:\s*([\d.]+)', 'cost', 'credits'),
        (r'Max Charges:\s*([\d.]+)', 'charges', 'count'),
        (r'Ultimate Cost:\s*([\d.]+)', 'ult_cost', 'points'),
        (r'Cooldown:\s*([\d.]+)', 'cooldown', 's'),
        (r'Health:\s*([\d.]+)\s*HP', 'health', 'hp'),
    ]
    for pattern, key, unit in patterns:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if m:
            stats[key] = {"value": float(m.group(1)), "unit": unit}
    return stats


def detect_source(raw_text: str) -> str:
    if "fandom.com" in raw_text or "Update History" in raw_text:
        return "valorant.fandom.com"
    return "liquipedia.net/valorant"


def process(agent_name: str, raw_text: str) -> dict:
    patch_history = parse_version_section(raw_text)
    current_stats = parse_current_stats(raw_text)

    numeric_count = sum(len(p["numeric_changes"]) for p in patch_history)
    all_change_count = sum(len(p["all_changes"]) for p in patch_history)
    balance_patches = [p for p in patch_history if not p["is_bugfix"] and not p["is_qol"]]

    return {
        "agent": agent_name,
        "source": detect_source(raw_text),
        "stats": {
            "total_patches": len(patch_history),
            "balance_patches": len(balance_patches),
            "numeric_changes": numeric_count,
            "all_changes": all_change_count,
        },
        "current_stats": current_stats,
        "patch_history": patch_history,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python parse_patch_text.py <AgentName> <raw_text_file>")
        sys.exit(1)

    agent_name = sys.argv[1]
    txt_file = Path(sys.argv[2])
    raw_text = txt_file.read_text(encoding="utf-8")

    result = process(agent_name, raw_text)
    out_path = OUTPUT_DIR / f"{agent_name}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    n = result["stats"]["total_patches"]
    nc = result["stats"]["numeric_changes"]
    ac = result["stats"]["all_changes"]
    print(f"{agent_name}: {n} patches, {nc} numeric + {ac - nc} qualitative = {ac} total changes → {out_path}")
