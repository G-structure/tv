"""One-time migration: unescape HTML entities in existing football DB rows.

Fixes raw `&#x27;`, `&amp;`, etc. in title_en, body_en, og_description_en
(articles table) and title_tvl, body_tvl (translations table).

Usage:
    uv run python scripts/migrate_unescape_entities.py
"""

import html
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "football" / "football.db"


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    # Fix articles table
    article_cols = ["title_en", "body_en", "og_description_en"]
    for col in article_cols:
        rows = conn.execute(
            f"SELECT id, {col} FROM articles WHERE {col} LIKE '%&#%' OR {col} LIKE '%&amp;%'"
        ).fetchall()
        for row_id, value in rows:
            conn.execute(
                f"UPDATE articles SET {col} = ? WHERE id = ?",
                (html.unescape(value), row_id),
            )
        if rows:
            print(f"  Fixed {len(rows)} rows in articles.{col}")

    # Fix translations table
    trans_cols = ["title_tvl", "body_tvl"]
    for col in trans_cols:
        rows = conn.execute(
            f"SELECT id, {col} FROM translations WHERE {col} LIKE '%&#%' OR {col} LIKE '%&amp;%'"
        ).fetchall()
        for row_id, value in rows:
            conn.execute(
                f"UPDATE translations SET {col} = ? WHERE id = ?",
                (html.unescape(value), row_id),
            )
        if rows:
            print(f"  Fixed {len(rows)} rows in translations.{col}")

    conn.commit()

    # Verify
    remaining = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE title_en LIKE '%&#%' OR body_en LIKE '%&#%' OR og_description_en LIKE '%&#%'"
    ).fetchone()[0]
    print(f"\nRemaining articles with HTML entities: {remaining}")

    remaining_t = conn.execute(
        "SELECT COUNT(*) FROM translations WHERE title_tvl LIKE '%&#%' OR body_tvl LIKE '%&#%'"
    ).fetchone()[0]
    print(f"Remaining translations with HTML entities: {remaining_t}")

    conn.close()


if __name__ == "__main__":
    migrate()
