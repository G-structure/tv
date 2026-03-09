#!/usr/bin/env python3
"""Standalone split validation — checks any set of split files for leakage.

Can be run independently as a CI check after build_splits.py or after
any manual modification to split files.

Usage:
    uv run python scripts/validate_splits.py
    uv run python scripts/validate_splits.py --splits-dir data/splits
    uv run python scripts/validate_splits.py --ngram-size 8
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_SPLITS_DIR = DATA_DIR / "splits"

DEFAULTS = {
    "ngram_size": 10,
    "min_test": 300,
    "min_val": 100,
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _tokenize(text: str) -> list[str]:
    return _normalize(text).split()


def _extract_ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _text_hash(text: str) -> str:
    return hashlib.sha256(_normalize(text).encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def validate(
    train: list[dict],
    val: list[dict],
    test: list[dict],
    ngram_size: int,
    min_test: int,
    min_val: int,
) -> tuple[list[str], list[str]]:
    """Run all validation checks.

    Returns (failures, warnings).
    """
    failures: list[str] = []
    warnings: list[str] = []
    heldout = test + val

    # ── 1. Doc-level integrity ────────────────────────────────────────────

    def _doc_ids(rows: list[dict]) -> set[str]:
        return {r["doc_id"] for r in rows if r.get("doc_id")}

    train_docs = _doc_ids(train)
    test_docs = _doc_ids(test)
    val_docs = _doc_ids(val)

    overlap_tt = train_docs & test_docs
    overlap_tv = train_docs & val_docs
    if overlap_tt:
        failures.append(f"doc_id overlap train<>test: {len(overlap_tt)} docs (sample: {list(overlap_tt)[:5]})")
    if overlap_tv:
        failures.append(f"doc_id overlap train<>val: {len(overlap_tv)} docs (sample: {list(overlap_tv)[:5]})")

    # ── 2. Bible book integrity ───────────────────────────────────────────

    def _book_nums(rows: list[dict]) -> set[int]:
        return {
            int(r["book_num"])
            for r in rows
            if r.get("content_type") == "bible_verse" and r.get("book_num")
        }

    train_books = _book_nums(train)
    test_books = _book_nums(test)
    val_books = _book_nums(val)

    if train_books & test_books:
        failures.append(f"Bible book overlap train<>test: {train_books & test_books}")
    if train_books & val_books:
        failures.append(f"Bible book overlap train<>val: {train_books & val_books}")
    if test_books & val_books:
        failures.append(f"Bible book overlap test<>val: {test_books & val_books}")

    # ── 3. Date integrity (daily text) ────────────────────────────────────

    def _dates(rows: list[dict]) -> set[str]:
        return {r["date"] for r in rows if r.get("date")}

    train_dates = _dates(train)
    test_dates = _dates(test)
    val_dates = _dates(val)

    if train_dates & test_dates:
        failures.append(f"Date overlap train<>test: {len(train_dates & test_dates)} dates")
    if train_dates & val_dates:
        failures.append(f"Date overlap train<>val: {len(train_dates & val_dates)} dates")

    # ── 4. Exact text overlap ─────────────────────────────────────────────

    train_hashes_tvl: set[str] = set()
    train_hashes_en: set[str] = set()
    for row in train:
        train_hashes_tvl.add(_text_hash(str(row.get("tvl", ""))))
        train_hashes_en.add(_text_hash(str(row.get("en", ""))))

    exact_tvl = 0
    exact_en = 0
    for row in heldout:
        if _text_hash(str(row.get("tvl", ""))) in train_hashes_tvl:
            exact_tvl += 1
        if _text_hash(str(row.get("en", ""))) in train_hashes_en:
            exact_en += 1

    if exact_tvl:
        failures.append(f"Exact TVL text overlap: {exact_tvl} held-out texts appear in train")
    if exact_en:
        failures.append(f"Exact EN text overlap: {exact_en} held-out texts appear in train")

    # ── 5. N-gram overlap (held-out Bible vs non-Bible train) ─────────────

    heldout_bible = [r for r in heldout if r.get("content_type") == "bible_verse"]
    heldout_ngrams: set[tuple[str, ...]] = set()
    for row in heldout_bible:
        for side in ("tvl", "en"):
            tokens = _tokenize(str(row.get(side, "")))
            heldout_ngrams.update(_extract_ngrams(tokens, ngram_size))

    non_bible_train = [r for r in train if r.get("content_type") != "bible_verse"]
    ngram_leak_count = 0
    ngram_leak_examples: list[str] = []
    for row in non_bible_train:
        leaked = False
        for side in ("tvl", "en"):
            tokens = _tokenize(str(row.get(side, "")))
            row_ngrams = _extract_ngrams(tokens, ngram_size)
            overlap = row_ngrams & heldout_ngrams
            if overlap:
                leaked = True
                break
        if leaked:
            ngram_leak_count += 1
            if len(ngram_leak_examples) < 5:
                ngram_leak_examples.append(row.get("id", "?"))

    if ngram_leak_count:
        failures.append(
            f"N-gram leak: {ngram_leak_count} non-Bible train examples share "
            f"{ngram_size}-grams with held-out Bible (samples: {ngram_leak_examples})"
        )

    # ── 6. Doc-level grouping consistency ─────────────────────────────────

    # Verify all paragraphs from same doc_id are in same split
    doc_split_map: dict[str, set[str]] = defaultdict(set)
    for split_name, rows in [("train", train), ("validation", val), ("test", test)]:
        for row in rows:
            if row.get("doc_id"):
                doc_split_map[row["doc_id"]].add(split_name)
    split_doc_ids = [did for did, splits_set in doc_split_map.items() if len(splits_set) > 1]
    if split_doc_ids:
        failures.append(
            f"Doc-level grouping violated: {len(split_doc_ids)} doc_ids span multiple splits "
            f"(sample: {split_doc_ids[:5]})"
        )

    # Verify all verses from same Bible book are in same split
    book_split_map: dict[int, set[str]] = defaultdict(set)
    for split_name, rows in [("train", train), ("validation", val), ("test", test)]:
        for row in rows:
            if row.get("content_type") == "bible_verse" and row.get("book_num"):
                book_split_map[int(row["book_num"])].add(split_name)
    split_books = [bn for bn, splits_set in book_split_map.items() if len(splits_set) > 1]
    if split_books:
        failures.append(f"Bible book grouping violated: books {split_books} span multiple splits")

    # Verify all daily texts from same date are in same split
    date_split_map: dict[str, set[str]] = defaultdict(set)
    for split_name, rows in [("train", train), ("validation", val), ("test", test)]:
        for row in rows:
            if row.get("date"):
                date_split_map[row["date"]].add(split_name)
    split_dates = [d for d, splits_set in date_split_map.items() if len(splits_set) > 1]
    if split_dates:
        failures.append(f"Date grouping violated: {len(split_dates)} dates span multiple splits")

    # ── 7. Minimum sizes ─────────────────────────────────────────────────

    if len(test) < min_test:
        warnings.append(f"Test set small: {len(test)} < {min_test} recommended")
    if len(val) < min_val:
        warnings.append(f"Validation set small: {len(val)} < {min_val} recommended")

    # ── 8. Per-domain representation ──────────────────────────────────────

    test_cts = Counter(r.get("content_type", "unknown") for r in test)
    val_cts = Counter(r.get("content_type", "unknown") for r in val)
    for required in ("bible_verse", "article_paragraph", "daily_text"):
        if test_cts.get(required, 0) == 0:
            warnings.append(f"Test set missing content_type: {required}")
        if val_cts.get(required, 0) == 0:
            warnings.append(f"Validation set missing content_type: {required}")

    # ── 9. Contamination residual ─────────────────────────────────────────

    if non_bible_train:
        residual_pct = 100.0 * ngram_leak_count / len(non_bible_train)
        if residual_pct > 0:
            warnings.append(f"Residual contamination: {residual_pct:.2f}% of non-Bible train")

    return failures, warnings


# Need defaultdict for doc/book/date grouping checks
from collections import defaultdict


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate split files for leakage")
    parser.add_argument("--splits-dir", type=Path, default=DEFAULT_SPLITS_DIR)
    parser.add_argument("--ngram-size", type=int, default=DEFAULTS["ngram_size"])
    parser.add_argument("--min-test", type=int, default=DEFAULTS["min_test"])
    parser.add_argument("--min-val", type=int, default=DEFAULTS["min_val"])
    args = parser.parse_args()

    splits_dir = args.splits_dir
    print(f"Validating splits in {splits_dir} ...")

    train = read_jsonl(splits_dir / "train.jsonl")
    val = read_jsonl(splits_dir / "validation.jsonl")
    test = read_jsonl(splits_dir / "test.jsonl")

    if not train:
        print("ERROR: train.jsonl is empty or missing")
        sys.exit(1)

    print(f"  train:      {len(train):>7,}")
    print(f"  validation: {len(val):>7,}")
    print(f"  test:       {len(test):>7,}")

    quarantined = read_jsonl(splits_dir / "quarantined.jsonl")
    if quarantined:
        print(f"  quarantined: {len(quarantined):>6,}")

    print(f"\nRunning checks (ngram_size={args.ngram_size}) ...")
    failures, warnings = validate(
        train, val, test,
        ngram_size=args.ngram_size,
        min_test=args.min_test,
        min_val=args.min_val,
    )

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    - {w}")

    if failures:
        print(f"\n  FAILURES ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        print(f"\nValidation FAILED with {len(failures)} failure(s).")
        sys.exit(1)
    else:
        print("\n  All checks PASSED.")


if __name__ == "__main__":
    main()
