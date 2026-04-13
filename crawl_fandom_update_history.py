"""
crawl_fandom_update_history.py
Fandom VALORANT wiki Update History section crawler
Saves to data/tmp/{AgentName}_raw.txt
"""
import requests
import time
import re
import sys
from pathlib import Path

OUTPUT_DIR = Path("C:/valrorant_agent/data/tmp")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Agent URL path -> save file name
AGENTS = [
    ("Breach",   "Breach"),
    ("Brimstone","Brimstone"),
    ("Clove",    "Clove"),
    ("Cypher",   "Cypher"),
    ("Deadlock", "Deadlock"),
    ("Fade",     "Fade"),
    ("Gekko",    "Gekko"),
    ("Harbor",   "Harbor"),
    ("Iso",      "Iso"),
    ("Jett",     "Jett"),
    ("KAYO",     "KAYO"),
    ("Killjoy",  "Killjoy"),
    ("Miks",     "Miks"),
    ("Neon",     "Neon"),
    ("Omen",     "Omen"),
    ("Phoenix",  "Phoenix"),
    ("Raze",     "Raze"),
    ("Reyna",    "Reyna"),
    ("Sage",     "Sage"),
    ("Skye",     "Skye"),
    ("Sova",     "Sova"),
    ("Tejo",     "Tejo"),
    ("Veto",     "Veto"),
    ("Viper",    "Viper"),
    ("Vyse",     "Vyse"),
    ("Yoru",     "Yoru"),
]


def fetch_wikitext(url_agent: str) -> str | None:
    """Fetch page wikitext via Fandom API"""
    api_url = "https://valorant.fandom.com/api.php"
    params = {
        "action": "parse",
        "page": url_agent,
        "prop": "wikitext",
        "format": "json",
        "redirects": "1",
    }
    try:
        r = requests.get(api_url, params=params, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if "parse" in data:
                return data["parse"]["wikitext"]["*"]
        print(f"  API {r.status_code}")
    except Exception as e:
        print(f"  API error: {e}")
    return None


def extract_update_history_wikitext(wikitext: str) -> str:
    """Extract the {{Update history|update=...}} template content from wikitext"""
    # Find the {{Update history template
    idx = wikitext.find("{{Update history")
    if idx == -1:
        idx = wikitext.find("{{update history")
    if idx == -1:
        return ""

    # Find the content after |update=
    update_idx = wikitext.find("|update=", idx)
    if update_idx == -1:
        return ""

    content_start = update_idx + len("|update=")

    # Find matching closing }} by counting braces
    depth = 2  # We started inside {{Update history|update=
    pos = content_start
    while pos < len(wikitext) and depth > 0:
        if wikitext[pos:pos+2] == "{{":
            depth += 1
            pos += 2
        elif wikitext[pos:pos+2] == "}}":
            depth -= 1
            if depth == 0:
                break
            pos += 2
        else:
            pos += 1

    return wikitext[content_start:pos].strip()


def convert_wikitext_update_history(raw: str) -> str:
    """Convert wikitext Update History to plain text format for the parser"""
    lines = raw.split("\n")
    result_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Convert {{patchv|12.00}} -> v12.00
        line = re.sub(r'\{\{patchv\|([^}]+)\}\}', r'v\1', line)

        # Convert {{abi text|Flashpoint}} -> Flashpoint
        line = re.sub(r'\{\{abi text\|([^}]+)\}\}', r'\1', line)
        line = re.sub(r'\{\{abi\|([^}]+)\}\}', r'\1', line)

        # Convert {{ui|Buff}} / {{ui|Nerf}} etc -> (Buff) / (Nerf)
        line = re.sub(r'\{\{ui\|([^}]+)\}\}', r'[\1]', line)

        # Convert {{Buff}} / {{Nerf}} / {{Bugfix}} templates
        line = re.sub(r'\{\{(Buff|Nerf|Bugfix|Adjustment|Bugfix Buff|Bugfix Nerf)[^}]*\}\}', r'[\1]', line, flags=re.IGNORECASE)

        # Remove All Platforms / Console-only sub-headers keeping them as context
        line = re.sub(r'\{\{(?:All Platforms|Console-only|Platform)[^}]*\}\}', '', line)

        # Convert other simple templates like {{icon|...}} -> ''
        line = re.sub(r'\{\{icon\|[^}]+\}\}', '', line)

        # Remove remaining simple templates (single level only)
        # Be careful not to strip nested ones
        line = re.sub(r'\{\{[^{}]+\}\}', '', line)

        # Convert wiki links [[Link|Text]] -> Text, [[Link]] -> Link
        line = re.sub(r'\[\[(?:[^|\]]+\|)?([^\]]+)\]\]', r'\1', line)

        # Remove bold/italic markup
        line = re.sub(r"'''?", '', line)

        # Remove leading list markers (* # :) while preserving indentation context
        stripped = re.sub(r'^[*#:]+\s*', '', line)

        if stripped:
            result_lines.append(stripped)

    return "\n".join(result_lines)


def crawl_agent(url_name: str, file_name: str) -> tuple[bool, str]:
    """Crawl a single agent and return (success, plain_text_content)"""
    url_encoded = url_name.replace("/", "%2F")

    wikitext = fetch_wikitext(url_encoded)
    if not wikitext:
        return False, ""

    # Extract Update History section
    history_raw = extract_update_history_wikitext(wikitext)
    if not history_raw:
        print(f"  WARNING: No Update History template found for {file_name}")
        # Try to find any update history content
        idx = wikitext.lower().find("update history")
        if idx >= 0:
            history_raw = wikitext[idx:idx+10000]
        else:
            return False, ""

    # Convert wikitext to plain text
    plain = convert_wikitext_update_history(history_raw)
    return True, plain


def main():
    results = {}

    # Allow filtering specific agents via command line
    if len(sys.argv) > 1:
        filter_agents = set(sys.argv[1:])
        agents_to_process = [(u, f) for u, f in AGENTS if f in filter_agents]
    else:
        agents_to_process = AGENTS

    total = len(agents_to_process)

    for i, (url_name, file_name) in enumerate(agents_to_process, 1):
        out_path = OUTPUT_DIR / f"{file_name}_raw.txt"
        print(f"[{i:02d}/{total:02d}] Crawling {file_name}...", end=" ", flush=True)

        success, content = crawl_agent(url_name, file_name)

        if not success or not content.strip():
            print("FAILED - no content")
            results[file_name] = "FAILED"
            continue

        # Build file content
        file_content = f"{file_name} - valorant.fandom.com\nUpdate History[]\n{content}\n"

        # Write file
        out_path.write_text(file_content, encoding="utf-8")

        # Count versions
        ver_matches = re.findall(r'v(\d+\.\d+)', content)
        latest = ver_matches[0] if ver_matches else "unknown"
        count = len(ver_matches)

        print(f"OK - {count} patches, latest: v{latest}")
        results[file_name] = latest

        time.sleep(0.8)  # rate limit

    print("\n=== Done ===")
    ok_count = sum(1 for v in results.values() if v != 'FAILED')
    print(f"Success: {ok_count}/{total}")
    for name, latest in results.items():
        status = f"v{latest}" if latest != 'FAILED' and latest != 'unknown' else latest
        print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
