"""
auto_update.py
자동 데이터 갱신 파이프라인

사용법:
  python auto_update.py                # 전체 갱신 (랭크 + VCT + 패치 감지 + 빌드 + reload)
  python auto_update.py --rank-only    # 랭크 데이터만
  python auto_update.py --vct-only     # VCT 데이터만
  python auto_update.py --check-patch  # 새 패치 감지만
  python auto_update.py --dry-run      # 실제 크롤 없이 무엇을 할지 출력

스케줄러 등록:
  Windows 작업 스케줄러: 매일 09:00 → python auto_update.py
  Linux cron: 0 9 * * * cd /path/to/valrorant_agent && python auto_update.py
"""

import subprocess
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# ─── 설정 ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

API_RELOAD_URL = "http://localhost:8000/reload"
PATCH_DATES_PATH = BASE_DIR / "patch_dates.json"
PATCH_NOTES_RAW = BASE_DIR / "patch_notes_raw.csv"
PATCH_NOTES_CLASSIFIED = BASE_DIR / "patch_notes_classified.csv"

# playvalorant.com 패치 노트 URL 패턴
PATCH_NOTES_URL = "https://playvalorant.com/en-us/news/game-updates/{slug}/"

# ─── 로깅 ──────────────────────────────────────────────────────────────────────
log_file = LOG_DIR / f"auto_update_{datetime.now():%Y%m%d_%H%M}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─── 유틸 ──────────────────────────────────────────────────────────────────────
def run_script(script: str, args: list[str] | None = None, timeout: int = 600) -> bool:
    """서브프로세스로 Python 스크립트 실행. 성공 여부 반환."""
    cmd = [sys.executable, str(BASE_DIR / script)] + (args or [])
    log.info(f"실행: {' '.join(cmd)}")

    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(BASE_DIR),
            env=env,
        )
        if result.returncode == 0:
            log.info(f"  ✓ {script} 성공")
            if result.stdout:
                # 마지막 5줄만 로그
                for line in result.stdout.strip().split("\n")[-5:]:
                    log.info(f"    {line}")
            return True
        else:
            log.error(f"  ✗ {script} 실패 (exit={result.returncode})")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-10:]:
                    log.error(f"    {line}")
            return False
    except subprocess.TimeoutExpired:
        log.error(f"  ✗ {script} 타임아웃 ({timeout}초)")
        return False


def reload_api() -> bool:
    """FastAPI /reload 엔드포인트 호출."""
    try:
        import urllib.request
        req = urllib.request.Request(
            API_RELOAD_URL,
            method="POST",
            headers={"Content-Type": "application/json"},
            data=b"{}",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            log.info(f"  API 재로드: {body}")
            return True
    except Exception as e:
        log.warning(f"  API 재로드 실패 (서버 꺼져 있으면 정상): {e}")
        return False


def clear_explanation_cache():
    """설명 캐시 삭제 — 데이터 변경 시 AI 설명도 갱신 필요."""
    cache = BASE_DIR / "explanation_cache.json"
    if cache.exists():
        cache.unlink()
        log.info("  explanation_cache.json 삭제")


# ─── 새 패치 감지 ──────────────────────────────────────────────────────────────
def detect_new_patches() -> list[str]:
    """playvalorant.com에서 새 패치 노트가 있는지 HEAD 요청으로 확인.

    patch_dates.json에 없는 패치 버전을 반환.
    """
    known = set()
    if PATCH_DATES_PATH.exists():
        with open(PATCH_DATES_PATH, encoding="utf-8") as f:
            known = set(json.load(f).keys())

    # 현재 최신 패치 번호에서 +1, +2까지 체크
    if known:
        versions = sorted(known, key=lambda v: [int(x) for x in v.split(".")])
        latest = versions[-1]
        major, minor = latest.split(".")
        candidates = [
            f"{major}.{int(minor) + 1:02d}",
            f"{major}.{int(minor) + 2:02d}",
        ]
    else:
        log.warning("patch_dates.json이 비어 있음 — 패치 감지 건너뜀")
        return []

    new_patches = []
    import urllib.request

    for ver in candidates:
        slug = f"valorant-patch-notes-{ver.replace('.', '-')}"
        url = PATCH_NOTES_URL.format(slug=slug)
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    log.info(f"  새 패치 발견: {ver}")
                    new_patches.append(ver)
        except Exception:
            pass  # 404 = 아직 없음

    return new_patches


def sync_classified_csv():
    """patch_notes_raw.csv → patch_notes_classified.csv 동기화.

    classified에 없는 새 행을 raw에서 가져와서 claude_confidence='' 로 추가.
    """
    if not PATCH_NOTES_RAW.exists():
        return

    import pandas as pd
    raw = pd.read_csv(PATCH_NOTES_RAW, encoding="utf-8-sig")

    if PATCH_NOTES_CLASSIFIED.exists():
        cls = pd.read_csv(PATCH_NOTES_CLASSIFIED, encoding="utf-8-sig")
        # raw에만 있는 패치 찾기
        existing_patches = set(cls["patch"].astype(str).unique())
        new_rows = raw[~raw["patch"].astype(str).isin(existing_patches)]
        if len(new_rows) > 0:
            new_rows = new_rows.copy()
            new_rows["claude_confidence"] = ""
            combined = pd.concat([cls, new_rows], ignore_index=True)
            combined.to_csv(PATCH_NOTES_CLASSIFIED, index=False, encoding="utf-8-sig")
            log.info(f"  classified에 {len(new_rows)}행 추가 (패치: {new_rows['patch'].unique().tolist()})")
        else:
            log.info("  classified 이미 최신")
    else:
        raw_copy = raw.copy()
        raw_copy["claude_confidence"] = ""
        raw_copy.to_csv(PATCH_NOTES_CLASSIFIED, index=False, encoding="utf-8-sig")
        log.info(f"  classified 새로 생성 ({len(raw_copy)}행)")


# ─── 메인 파이프라인 ────────────────────────────────────────────────────────────
def pipeline(
    do_rank: bool = True,
    do_vct: bool = True,
    do_patch_check: bool = True,
    dry_run: bool = False,
):
    log.info("=" * 60)
    log.info(f"  자동 갱신 시작 — {datetime.now():%Y-%m-%d %H:%M:%S}")
    log.info("=" * 60)

    data_changed = False
    steps_done = []

    # ── 1. 새 패치 감지 + 크롤 ──────────────────────────────────────────────
    if do_patch_check:
        log.info("\n[1/4] 새 패치 감지...")
        new_patches = detect_new_patches()

        if new_patches:
            for ver in new_patches:
                log.info(f"  패치 {ver} 크롤 시작")
                if not dry_run:
                    ok = run_script("crawl_patch_notes.py", ["--patch", ver], timeout=300)
                    if ok:
                        data_changed = True
                        steps_done.append(f"패치 {ver} 크롤")
                else:
                    log.info(f"  [DRY RUN] crawl_patch_notes.py --patch {ver}")

            # raw → classified 동기화
            if not dry_run:
                sync_classified_csv()
        else:
            log.info("  새 패치 없음")
    else:
        log.info("\n[1/4] 패치 감지 건너뜀")

    # ── 2. 랭크 데이터 크롤 ─────────────────────────────────────────────────
    if do_rank:
        log.info("\n[2/4] 랭크 데이터 크롤...")
        if not dry_run:
            ok = run_script("crawl_current_act.py", ["--no-build"], timeout=600)
            if ok:
                data_changed = True
                steps_done.append("랭크 크롤")
        else:
            log.info("  [DRY RUN] crawl_current_act.py --no-build")
    else:
        log.info("\n[2/4] 랭크 크롤 건너뜀")

    # ── 3. VCT 데이터 크롤 ──────────────────────────────────────────────────
    if do_vct:
        log.info("\n[3/4] VCT 데이터 크롤...")
        if not dry_run:
            ok = run_script("crawl_current_vct.py", ["--no-build"], timeout=600)
            if ok:
                data_changed = True
                steps_done.append("VCT 크롤")
        else:
            log.info("  [DRY RUN] crawl_current_vct.py --no-build")
    else:
        log.info("\n[3/4] VCT 크롤 건너뜀")

    # ── 4. 빌드 + 모델 재학습 + 재로드 ─────────────────────────────────────
    if data_changed:
        log.info("\n[4/5] Step2 데이터 빌드...")
        if not dry_run:
            build_ok = run_script("build_step2_data.py", timeout=120)
            if build_ok:
                steps_done.append("빌드")
        else:
            log.info("  [DRY RUN] build_step2_data.py")
            build_ok = True

        # ── 5. 모델 재학습 (저장된 HPO 재사용 → --fast) ─────────────────
        log.info("\n[5/5] 모델 재학습 (--fast) + API 재로드...")
        if not dry_run and build_ok:
            train_ok = run_script("train_step2.py", ["--fast"], timeout=1800)
            if train_ok:
                steps_done.append("모델 재학습")
                clear_explanation_cache()
                reload_api()
                steps_done.append("API 재로드")
        else:
            log.info("  [DRY RUN] train_step2.py --fast + /reload")
    else:
        log.info("\n[4-5] 데이터 변경 없음 — 빌드/학습 건너뜀")

    # ── 완료 ────────────────────────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    if steps_done:
        log.info(f"  완료: {' → '.join(steps_done)}")
    else:
        log.info("  변경 없음 (모든 데이터 최신)")
    log.info(f"  소요 시간: {datetime.now():%H:%M:%S}")
    log.info(f"  로그: {log_file}")
    log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="자동 데이터 갱신 파이프라인")
    parser.add_argument("--rank-only",   action="store_true", help="랭크 데이터만 갱신")
    parser.add_argument("--vct-only",    action="store_true", help="VCT 데이터만 갱신")
    parser.add_argument("--check-patch", action="store_true", help="새 패치 감지만")
    parser.add_argument("--dry-run",     action="store_true", help="실제 실행 없이 계획만 출력")
    args = parser.parse_args()

    if args.rank_only:
        pipeline(do_rank=True, do_vct=False, do_patch_check=False, dry_run=args.dry_run)
    elif args.vct_only:
        pipeline(do_rank=False, do_vct=True, do_patch_check=False, dry_run=args.dry_run)
    elif args.check_patch:
        pipeline(do_rank=False, do_vct=False, do_patch_check=True, dry_run=args.dry_run)
    else:
        pipeline(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
