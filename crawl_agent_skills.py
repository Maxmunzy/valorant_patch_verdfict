"""
crawl_agent_skills.py
Fandom Wiki에서 전체 요원의 현재 스킬 스탯을 수집하여 agent_skills.json 생성
"""
import urllib.request, json, re, time
from pathlib import Path

OUT_PATH = Path("data/agent_skills.json")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

AGENTS = [
    "Astra", "Breach", "Brimstone", "Chamber", "Clove",
    "Cypher", "Deadlock", "Fade", "Gekko", "Harbor",
    "Iso", "Jett", "KAYO", "Killjoy", "Miks",
    "Neon", "Omen", "Phoenix", "Raze", "Reyna",
    "Sage", "Skye", "Sova", "Tejo", "Veto",
    "Viper", "Vyse", "Waylay", "Yoru",
]

WIKI_PAGE = {}  # KAYO wiki page is "KAYO" (no slash)

# 스킬 슬롯 수동 오버라이드 (특수 키 구조 요원)
SLOT_OVERRIDES = {
    "Astra": {
        "Gravity Well":      "C",
        "Nova Pulse":        "Q",
        "Nebula/Dissipate":  "E",
        "Stars":             "E",   # Signature = E slot; Nebula/Dissipate는 Stars의 사용 방식
        "Cosmic Divide":     "X",
        "Astral Form":       "P",
    },
    "Tejo": {
        "Stealth Drone":     "C",
        "Special Delivery":  "Q",
        "Guided Salvo":      "E",
        "Armageddon":        "X",   # Ultimate
    },
}


def api_get(params):
    base = "https://valorant.fandom.com/api.php"
    qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
    url = f"{base}?{qs}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def get_abilities_wikitext(agent):
    wiki_page = WIKI_PAGE.get(agent, agent)
    sec_data = api_get({"action": "parse", "page": wiki_page, "prop": "sections", "format": "json"})
    if "parse" not in sec_data:
        return None
    sections = sec_data["parse"]["sections"]
    abi = next((s for s in sections if s["line"].strip().lower() == "abilities"), None)
    if not abi:
        return None
    wt_data = api_get({"action": "parse", "page": wiki_page, "prop": "wikitext",
                       "section": abi["index"], "format": "json"})
    if "parse" not in wt_data:
        return None
    return wt_data["parse"]["wikitext"]["*"]


def extract_ability_names(wt):
    # 두 가지 형식 처리: {{abi_info|...}} (밑줄) 또는 {{abi info|...}} (공백)
    return re.findall(r'\{\{abi[\s_]info\|([^}]+)\}\}', wt)


def fetch_ability_page(ability_name):
    # 슬래시가 포함된 이름은 여러 대안 시도 (FRAG/ment -> FRAG-ment 등)
    candidates = [ability_name]
    if "/" in ability_name:
        candidates.append(ability_name.replace("/", "-"))
        candidates.append(ability_name.replace("/", " / "))
    for name in candidates:
        wt_data = api_get({"action": "parse", "page": name, "prop": "wikitext", "format": "json"})
        if "parse" in wt_data:
            return wt_data["parse"]["wikitext"]["*"]
    return None


def parse_stat_value(raw_val):
    val = re.sub(r'\[\[.*?\]\]', '', raw_val)
    val = re.sub(r'\{\{.*?\}\}', '', val)
    val = re.sub(r'<[^>]+>', '', val)
    val = val.strip().split('\n')[0].strip()
    val = val.split('<br')[0].strip()
    val = val.split('(')[0].strip()
    num_m = re.match(r'^(-?\d+(?:\.\d+)?)\s*(.*)', val)
    if num_m:
        num = float(num_m.group(1))
        unit = num_m.group(2).strip().rstrip('.')
        return {"value": num, "unit": unit, "raw": raw_val.strip()}
    return {"value": None, "unit": "", "raw": raw_val.strip()}


def clean_stat_name(raw_name):
    name = re.sub(r'\[\[File:[^\]]*\]\]\s*', '', raw_name)
    name = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', name)
    name = re.sub(r'\{\{.*?\}\}', '', name)
    name = re.sub(r"'{2,}", '', name)
    return name.strip()


def parse_infobox(wt):
    info = {}
    # = 양쪽 공백 허용
    key_m = re.search(r'\|key\s*=\s*\{\{DKB\|([^}]+)\}\}', wt)
    if key_m:
        info["slot"] = key_m.group(1).strip()
    type_m = re.search(r'\|type\s*=\s*\[\[Abilities#([^\|\]]+)', wt)
    if not type_m:
        type_m = re.search(r'\|type\s*=\s*([^\n\|{]+)', wt)
    if type_m:
        info["type"] = type_m.group(1).strip().rstrip(']').strip()
    creds_m = re.search(r'\|creds\s*=\s*([^\n\|{]+)', wt)
    if creds_m:
        c = creds_m.group(1).strip()
        try:
            info["creds"] = int(c)
        except ValueError:
            info["creds"] = 0
    uses_m = re.search(r'\|uses\s*=\s*\{\{uses\|([^}]+)\}\}', wt)
    if uses_m:
        try:
            info["charges"] = int(uses_m.group(1).strip())
        except (ValueError, TypeError):
            info["charges"] = 1
    ult_m = re.search(r'\|ult_points\s*=\s*(\d+)', wt)
    if ult_m:
        info["ult_points"] = int(ult_m.group(1))
    func_m = re.search(r'\|function\s*=\s*(.+?)(?=\n\||\Z)', wt, re.DOTALL)
    if func_m:
        func = func_m.group(1).strip()
        # [[Category#Sub|Text]] -> Text 또는 [[Category#Sub]] -> Sub
        func = re.sub(r'\[\[(?:[^\]|#]*[#/])?([^\]|#]+)(?:\|[^\]]+)?\]\]', r'\1', func)
        # 남은 [[ ]] 제거
        func = re.sub(r'\[\[|\]\]', '', func)
        # <br> 등 HTML 제거
        func = re.sub(r'<[^>]+>', '', func)
        info["function"] = func.strip()
    return info


def parse_stats_table(wt):
    stats = {}
    idx = wt.find("==Stats==")
    if idx < 0:
        return stats
    table_start = wt.find("{|", idx)
    if table_start < 0:
        return stats
    table_end = wt.find("|}", table_start)
    if table_end < 0:
        table_end = len(wt)
    table = wt[table_start:table_end]
    rows = re.split(r'^\|-', table, flags=re.MULTILINE)
    for row in rows[1:]:
        lines = [l.strip() for l in row.strip().split("\n") if l.strip().startswith("|")]
        if len(lines) < 2:
            continue
        stat_raw = lines[0].lstrip("|").strip()
        val_raw = lines[1].lstrip("|").strip()
        stat_name = clean_stat_name(stat_raw)
        if not stat_name or stat_name in ("Stat", "Value"):
            continue
        stats[stat_name] = parse_stat_value(val_raw)
    return stats


def parse_ability_page(ability_name, wt):
    result = {"name": ability_name}
    info = parse_infobox(wt)
    result.update(info)
    result["stats"] = parse_stats_table(wt)
    return result


def crawl_agent(agent):
    wt = get_abilities_wikitext(agent)
    if not wt:
        print("FAIL (Abilities 섹션 없음)")
        return None
    ability_names = extract_ability_names(wt)
    if not ability_names:
        print("FAIL (스킬 이름 없음)")
        return None
    print(f"스킬 {len(ability_names)}개: {ability_names}")
    agent_skills = {}
    for abi_name in ability_names:
        time.sleep(0.25)
        try:
            abi_wt = fetch_ability_page(abi_name)
        except Exception as e:
            print(f"    [{abi_name}] 오류: {e}")
            continue
        if not abi_wt:
            print(f"    [{abi_name}] 페이지 없음")
            continue
        parsed = parse_ability_page(abi_name, abi_wt)
        # 수동 오버라이드 우선 적용
        override_map = SLOT_OVERRIDES.get(agent, {})
        if abi_name in override_map:
            slot = override_map[abi_name]
            parsed["slot"] = slot
        else:
            slot = parsed.get("slot", "P")
            if not parsed.get("slot"):
                parsed["slot"] = "P"
        stat_count = len(parsed.get("stats", {}))
        print(f"    [{abi_name}] slot={slot}, creds={parsed.get('creds','?')}, stats={stat_count}개")
        # 같은 슬롯이 이미 있으면 stats 병합 (Astra Stars/Nebula 모두 E)
        if slot in agent_skills:
            agent_skills[slot]["stats"].update(parsed.get("stats", {}))
            agent_skills[slot]["name"] += f" / {abi_name}"
        else:
            agent_skills[slot] = parsed
    return agent_skills


def main():
    print("=" * 60)
    print("요원별 스킬 스탯 수집기 (Fandom Wiki)")
    print("=" * 60 + "\n")
    result = {}
    failed = []
    for agent in AGENTS:
        print(f"\n[{agent}]", end=" ", flush=True)
        try:
            skills = crawl_agent(agent)
            if skills:
                result[agent] = skills
            else:
                failed.append(agent)
        except Exception as e:
            print(f"  ERROR: {e}")
            failed.append(agent)
        time.sleep(0.3)
    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n\nOK 저장: {OUT_PATH} ({len(result)}개 요원)")
    if failed:
        print(f"FAIL: {failed}")
    print("\n--- 요원별 스킬 수 ---")
    for agent, skills in result.items():
        slots = list(skills.keys())
        stat_counts = {s: len(skills[s].get("stats", {})) for s in slots}
        print(f"  {agent}: {slots}  stats={stat_counts}")


if __name__ == "__main__":
    main()
