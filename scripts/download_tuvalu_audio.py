"""Download Tuvaluan audio recordings from tuvalu.aa-ken.jp.

Downloads word audio from the main site and expression audio from the webapp.
Audio is stored for potential future use (not used in Stage A training).

Uses Docker curl-impersonate for fetching (browser-like TLS fingerprint).

Usage:
    uv run python scripts/download_tuvalu_audio.py
    uv run python scripts/download_tuvalu_audio.py --words-only
    uv run python scripts/download_tuvalu_audio.py --expressions-only
    uv run python scripts/download_tuvalu_audio.py --dry-run
"""

import json
import subprocess
import sys
import time
from pathlib import Path

from tqdm import tqdm

DOCKER_IMAGE = "lwthiker/curl-impersonate:0.6-ff"
DOCKER_WRAPPER = "curl_ff117"

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
AUDIO_DIR = DATA_DIR / "audio" / "tuvalu_app"
WORD_AUDIO_DIR = AUDIO_DIR / "words"
EXPR_AUDIO_DIR = AUDIO_DIR / "expressions"

# Main site audio
WORD_AUDIO_URL = "https://tuvalu.aa-ken.jp/sound/words/{id}.mp3"
# Webapp expression audio
EXPR_AUDIO_URL = "https://tuvalu.aa-ken.jp/webapp/assets/sounds/tuvalu_sound/expressions/{name}.mp3"

DELAY = 0.5  # seconds between downloads (lighter than page scraping)
_last_request_time = 0.0


def download_file(url: str, output_path: Path, timeout: int = 30) -> bool:
    """Download a file using Docker curl-impersonate. Returns True on success."""
    global _last_request_time

    if output_path.exists() and output_path.stat().st_size > 0:
        return True  # Already downloaded

    elapsed = time.time() - _last_request_time
    if elapsed < DELAY:
        time.sleep(DELAY - elapsed)

    try:
        # Write to a temp file, then move on success
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{output_path.parent}:/output",
                DOCKER_IMAGE,
                DOCKER_WRAPPER,
                "-s", "-L",
                "--max-time", str(timeout),
                "-o", f"/output/{output_path.name}",
                "-w", "%{http_code}",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=timeout + 10,
        )
        _last_request_time = time.time()

        http_code = result.stdout.strip()
        if http_code == "200" and output_path.exists() and output_path.stat().st_size > 0:
            return True
        else:
            # Clean up failed download
            if output_path.exists():
                output_path.unlink()
            return False

    except (subprocess.TimeoutExpired, Exception) as e:
        if output_path.exists():
            output_path.unlink()
        return False


def collect_word_audio_ids() -> list[str]:
    """Collect all audio IDs from scraped dictionary and webapp data."""
    audio_ids = set()

    # From the full dictionary scrape
    dict_file = DATA_DIR / "aligned" / "tuvalu_dictionary.jsonl"
    if dict_file.exists():
        for line in open(dict_file):
            record = json.loads(line)
            aid = record.get("audio_id")
            if aid:
                audio_ids.add(str(aid))

    # From the webapp scrape
    app_file = DATA_DIR / "aligned" / "tuvalu_app.jsonl"
    if app_file.exists():
        for line in open(app_file):
            record = json.loads(line)
            aid = record.get("audio_id")
            if aid:
                audio_ids.add(str(aid))

    # From raw webapp JSON files (they have audio arrays)
    raw_dir = DATA_DIR / "raw" / "tuvalu_app"
    if raw_dir.exists():
        for json_file in raw_dir.glob("*.json"):
            if json_file.name == "expressions.json":
                continue
            try:
                data = json.loads(json_file.read_text())
                for word in data.get("words", []):
                    for audio_file in word.get("audio", []):
                        # Strip .mp3 extension
                        aid = audio_file.replace(".mp3", "")
                        audio_ids.add(aid)
            except (json.JSONDecodeError, KeyError):
                pass

    return sorted(audio_ids)


def collect_expression_audio_ids() -> list[str]:
    """Collect expression audio file names from the webapp data."""
    audio_names = []

    raw_path = DATA_DIR / "raw" / "tuvalu_app" / "expressions.json"
    if not raw_path.exists():
        print("  No expressions.json found in raw data", file=sys.stderr)
        return []

    data = json.loads(raw_path.read_text())
    for cat in data:
        name = cat.get("name", "")  # e.g. "e1"
        sound_index = cat.get("sound_index", [])
        for indices in sound_index:
            for idx in indices:
                # Format: e1-01, e1-02, etc.
                audio_names.append(f"{name}-{idx:02d}")

    return sorted(set(audio_names))


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Download Tuvaluan audio recordings from tuvalu.aa-ken.jp")
    parser.add_argument("--words-only", action="store_true",
                        help="Only download word audio")
    parser.add_argument("--expressions-only", action="store_true",
                        help="Only download expression audio")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count files to download without downloading")
    args = parser.parse_args()

    download_words = not args.expressions_only
    download_exprs = not args.words_only

    # Word audio
    if download_words:
        word_ids = collect_word_audio_ids()
        WORD_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        already = sum(1 for aid in word_ids
                      if (WORD_AUDIO_DIR / f"{aid}.mp3").exists())
        to_download = len(word_ids) - already

        print(f"Word audio: {len(word_ids)} IDs found, "
              f"{already} already downloaded, {to_download} to fetch")

        if args.dry_run:
            print("  [DRY RUN] Would download to", WORD_AUDIO_DIR)
        else:
            success = 0
            failed = 0
            for aid in tqdm(word_ids, desc="Downloading word audio"):
                output_path = WORD_AUDIO_DIR / f"{aid}.mp3"
                if output_path.exists() and output_path.stat().st_size > 0:
                    success += 1
                    continue

                url = WORD_AUDIO_URL.format(id=aid)
                if download_file(url, output_path):
                    success += 1
                else:
                    failed += 1

            print(f"  Word audio: {success} downloaded, {failed} failed")

    # Expression audio
    if download_exprs:
        expr_ids = collect_expression_audio_ids()
        EXPR_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

        already = sum(1 for eid in expr_ids
                      if (EXPR_AUDIO_DIR / f"{eid}.mp3").exists())
        to_download = len(expr_ids) - already

        print(f"\nExpression audio: {len(expr_ids)} IDs found, "
              f"{already} already downloaded, {to_download} to fetch")

        if args.dry_run:
            print("  [DRY RUN] Would download to", EXPR_AUDIO_DIR)
        else:
            success = 0
            failed = 0
            for eid in tqdm(expr_ids, desc="Downloading expression audio"):
                output_path = EXPR_AUDIO_DIR / f"{eid}.mp3"
                if output_path.exists() and output_path.stat().st_size > 0:
                    success += 1
                    continue

                url = EXPR_AUDIO_URL.format(name=eid)
                if download_file(url, output_path):
                    success += 1
                else:
                    failed += 1

            print(f"  Expression audio: {success} downloaded, {failed} failed")

    # Summary
    total_word = len(list(WORD_AUDIO_DIR.glob("*.mp3"))) if WORD_AUDIO_DIR.exists() else 0
    total_expr = len(list(EXPR_AUDIO_DIR.glob("*.mp3"))) if EXPR_AUDIO_DIR.exists() else 0
    total_size = sum(f.stat().st_size for f in WORD_AUDIO_DIR.glob("*.mp3")) if WORD_AUDIO_DIR.exists() else 0
    total_size += sum(f.stat().st_size for f in EXPR_AUDIO_DIR.glob("*.mp3")) if EXPR_AUDIO_DIR.exists() else 0

    print(f"\nTotal audio files: {total_word} words + {total_expr} expressions")
    print(f"Total size: {total_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
