"""Full football pipeline: scrape all sources + translate new articles.

Convenience script that runs all scrapers then translates any untranslated articles.

Usage:
    uv run python scripts/pipeline_football.py                  # scrape + translate all new
    uv run python scripts/pipeline_football.py --scrape-limit 5 # limit scraping per source
    uv run python scripts/pipeline_football.py --translate-only  # skip scraping, just translate
    uv run python scripts/pipeline_football.py --scrape-only     # skip translation
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def run(cmd: list[str], label: str) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, cwd=SCRIPTS_DIR.parent)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Football scrape + translate pipeline")
    parser.add_argument("--scrape-limit", type=int, help="Limit articles per scraper")
    parser.add_argument("--translate-limit", type=int, help="Limit articles to translate")
    parser.add_argument("--scrape-only", action="store_true", help="Only scrape, skip translation")
    parser.add_argument("--translate-only", action="store_true", help="Only translate, skip scraping")
    args = parser.parse_args()

    python = sys.executable

    if not args.translate_only:
        # Scrape all three sources
        limit_args = ["--limit", str(args.scrape_limit)] if args.scrape_limit else []

        run(
            [python, str(SCRIPTS_DIR / "scrape_football_goal.py")] + limit_args,
            "Scraping Goal.com",
        )
        run(
            [python, str(SCRIPTS_DIR / "scrape_football_fifa.py")] + limit_args,
            "Scraping FIFA.com",
        )
        run(
            [python, str(SCRIPTS_DIR / "scrape_football_sky.py")] + limit_args,
            "Scraping Sky Sports",
        )

    if not args.scrape_only:
        # Translate untranslated articles
        translate_args = (
            ["--limit", str(args.translate_limit)] if args.translate_limit else []
        )
        run(
            [python, str(SCRIPTS_DIR / "translate_football.py")] + translate_args,
            "Translating articles to Tuvaluan",
        )

    print(f"\n{'='*60}")
    print("  Pipeline complete!")
    print(f"{'='*60}\n")

    # Print DB stats
    subprocess.run(
        [
            python,
            "-c",
            """
import sqlite3
conn = sqlite3.connect('data/football/football.db')
for row in conn.execute('SELECT source_id, COUNT(*) FROM articles GROUP BY source_id'):
    print(f'  {row[0]:6s}: {row[1]:4d} articles')
total = conn.execute('SELECT COUNT(*) FROM articles').fetchone()[0]
translated = conn.execute('SELECT COUNT(*) FROM translations').fetchone()[0]
print(f'  {"total":6s}: {total:4d} articles, {translated} translated')
""",
        ],
        cwd=SCRIPTS_DIR.parent,
    )


if __name__ == "__main__":
    main()
