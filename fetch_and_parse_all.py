"""
fetch_and_parse_all.py
Fandom API에서 모든 요원의 Update History를 가져와 raw 파일 저장 + 파싱
"""
import urllib.request, json, re, time, subprocess
from pathlib import Path

TMP_DIR = Path("data/tmp")
TMP_DIR.mkdir(parents=True, exist_ok=True)

AGENTS = [
    ("Breach",     "Breach"),
    ("Brimstone",  "Brimstone"),
    ("Clove",      "Clove"),
    ("Cypher",     "Cypher"),
    ("Deadlock",   "Deadlock"),
    ("Fade",       "Fade"),
    ("Gekko",      "Gekko"),
    ("Harbor",     "Harbor"),
    ("Iso",        "ISO"),
    ("Jett",       "Jett"),
    ("KAYO",       "KAY/O"),
    ("Killjoy",    "Killjoy"),
    ("Miks",       "Miks"),
    ("Neon",       "Neon"),
    ("Omen",       "Omen"),
    ("Phoenix",    "Phoenix"),
    ("Raze",       "Raze"),
    ("Reyna",      "Reyna"),
    ("Sage",       "Sage"),
    ("Skye",       "Skye"),
    ("Sova",       "Sova"),
    ("Tejo",       "Tejo"),
    ("Veto",       "Veto"),
    ("Viper",      "Viper"),
    ("Vyse",       "Vyse"),
    ("Yoru",       "Yoru"),
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}


def api_get(params: dict) -> dict:
    base = "https://valorant.fandom.com/api.php"
    qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
    url = f"{base}?{qs}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def get_update_history_wikitext(wiki_page: str) -> str | None:
    # 1. 섹션 목록에서 Update History 인덱스 찾기
    sec_data = api_get({"action": "parse", "page": wiki_page, "prop": "sections", "format": "json"})
    if "parse" not in sec_data:
        return None
    sections = sec_data["parse"]["sections"]
    uh = next((s for s in sections if "update" in s["line"].lower() and "history" in s["line"].lower()), None)
    if not uh:
        return None

    # 2. 해당 섹션 wikitext 가져오기
    wt_data = api_get({"action": "parse", "page": wiki_page, "prop": "wikitext", "section": uh["index"], "format": "json"})
    if "parse" not in wt_data:
        return None
    return wt_data["parse"]["wikitext"]["*"]


def convert_wikitext(wt: str) -> str:
    """wikitext → 파서가 읽을 수 있는 plain text"""
    lines = wt.split("\n")
    out = []
    in_block = False

    for line in lines:
        # 섹션 헤더
        m = re.match(r'^={2,4}\s*(.+?)\s*={2,4}$', line)
        if m:
            title = m.group(1).strip()
            if title != "Update History":
                out.append(f"\n{title}[]")
            in_block = False
            continue

        # Update history 템플릿 시작
        if line.startswith("{{Update history|update="):
            in_block = True
            continue

        # 템플릿 닫힘
        if line.strip() == "}}" and in_block:
            in_block = False
            continue

        if not in_block:
            continue

        # 버전 번호 줄: '''{{patchv|12.05}}
        if "'''" in line and "{{patchv" in line:
            ver = re.sub(r"\{\{patchv\|([^}]+)\}\}", r"v\1", line)
            ver = ver.replace("'''", "").strip()
            out.append(ver)
            continue

        # 일반 콘텐츠 처리
        l = line
        l = re.sub(r"\{\{abi text\|([^}]+)\}\}", r"\1", l)
        l = re.sub(r"\{\{ui\|[^}]+\}\}\s*", "", l)
        l = re.sub(r"\{\{patchv\|([^}]+)\}\}", r"v\1", l)
        l = re.sub(r"\{\{hp\|([^}]+)\}\}", r"\1 HP", l)
        l = re.sub(r"\{\{credit\|([^}]+)\}\}", r"\1 credits", l)
        l = re.sub(r"\{\{[^{}]*\}\}", "", l)  # 나머지 단순 템플릿
        # 중첩 템플릿 2회 더 제거
        for _ in range(2):
            l = re.sub(r"\{\{[^{}]*\}\}", "", l)
        l = l.replace("'''", "").replace("''", "")
        l = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", l)
        l = re.sub(r"\*+\s*", "", l, count=1)
        l = re.sub(r"<ref[^>]*>.*?</ref>", "", l, flags=re.DOTALL | re.IGNORECASE)
        l = re.sub(r"<ref[^>]*/>", "", l, flags=re.IGNORECASE)
        l = l.strip()
        if l:
            out.append(l)

    result = "\n".join(out)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def main():
    results = {}
    for file_name, wiki_page in AGENTS:
        print(f"Fetching {file_name} (wiki: {wiki_page})...", end=" ", flush=True)
        try:
            wt = get_update_history_wikitext(wiki_page)
            if wt is None:
                print("ERR No Update History section found")
                results[file_name] = None
                continue
            plain = convert_wikitext(wt)
            content = f"{file_name} - valorant.fandom.com\nUpdate History[]\n{plain}\n"
            out_path = TMP_DIR / f"{file_name}_raw.txt"
            out_path.write_text(content, encoding="utf-8")
            # 버전 수 확인
            vers = re.findall(r"v\d+\.\d+", plain)
            print(f"OK {len(vers)} patches, saved to {out_path}")
            results[file_name] = len(vers)
        except Exception as e:
            print(f"ERR: {e}")
            results[file_name] = None
        time.sleep(0.3)  # rate limit 방지

    print("\n--- 결과 요약 ---")
    for name, cnt in results.items():
        status = f"{cnt} patches" if cnt else "FAILED"
        print(f"  {name}: {status}")

    # 파싱 실행
    print("\n--- JSON 재파싱 시작 ---")
    success = 0
    for file_name, _ in AGENTS:
        raw_path = TMP_DIR / f"{file_name}_raw.txt"
        if not raw_path.exists():
            print(f"  {file_name}: raw 파일 없음 (스킵)")
            continue
        r = subprocess.run(
            ["python3", "parse_patch_text.py", file_name, str(raw_path)],
            capture_output=True, text=True, encoding="utf-8"
        )
        if r.returncode == 0:
            print(f"  {r.stdout.strip()}")
            success += 1
        else:
            print(f"  {file_name}: 파싱 오류 - {r.stderr.strip()[:100]}")

    print(f"\nOK 완료: {success}/{len(AGENTS)}개 파싱 성공")


if __name__ == "__main__":
    main()
