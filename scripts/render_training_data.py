#!/usr/bin/env python3
"""Render decontaminated splits + optional unstructured seed into training-ready chat JSONL.

Reads raw pair data from data/splits/ (output of build_splits.py) and renders
each pair into both translation directions using the same chat format as
training/stage_a_mt/build_data.py.

Optionally merges unstructured seed data (already in chat format from
build_stage_a_mt_data.py) into the training set.

Usage:
    uv run python scripts/render_training_data.py
    uv run python scripts/render_training_data.py --include-unstructured
    uv run python scripts/render_training_data.py --bible-max-train-share 0.5
    uv run python scripts/render_training_data.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SPLITS_DIR = DATA_DIR / "splits"
UNSTRUCT_DIR = DATA_DIR / "finetune" / "stage_a_mt" / "unstructured_seed"
OUTPUT_DIR = DATA_DIR / "finetune" / "stage_a_mt_v2"

SYSTEM_PROMPT = (
    "You are a careful translator between Tuvaluan and English. "
    "Translate faithfully. Preserve names, numbers, punctuation, line breaks, "
    "and structure when possible. Output only the translation."
)

TVL_TO_EN_TEMPLATES = [
    "Translate from Tuvaluan to English:\n\n{source}",
    "Translate the following Tuvaluan text into English. Preserve formatting and do not add commentary.\n\n{source}",
    "Convert this Tuvaluan text to natural English while keeping the original structure when possible.\n\n{source}",
]

EN_TO_TVL_TEMPLATES = [
    "Translate from English to Tuvaluan:\n\n{source}",
    "Translate the following English text into Tuvaluan. Preserve formatting and do not add commentary.\n\n{source}",
    "Convert this English text to Tuvaluan while keeping the original structure when possible.\n\n{source}",
]


def _stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


def _normalize_preserve_structure(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def _choose_template(row_id: str, direction: str) -> tuple[str, int]:
    if direction == "tvl_to_en":
        templates = TVL_TO_EN_TEMPLATES
    else:
        templates = EN_TO_TVL_TEMPLATES
    idx = _stable_hash(f"{row_id}::{direction}") % len(templates)
    return templates[idx], idx


def render_example(row: dict[str, Any], direction: str) -> dict[str, Any]:
    """Convert a raw pair into a chat-formatted training example."""
    if direction == "tvl_to_en":
        src = _normalize_preserve_structure(str(row["tvl"]))
        tgt = _normalize_preserve_structure(str(row["en"]))
        src_lang, tgt_lang = "tvl", "en"
    else:
        src = _normalize_preserve_structure(str(row["en"]))
        tgt = _normalize_preserve_structure(str(row["tvl"]))
        src_lang, tgt_lang = "en", "tvl"

    template, template_idx = _choose_template(str(row["id"]), direction)
    metadata = dict(row)
    metadata.update({
        "direction": direction,
        "source_lang": src_lang,
        "target_lang": tgt_lang,
        "template_idx": template_idx,
    })
    return {
        "id": f"{row['id']}::{direction}",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": template.format(source=src)},
            {"role": "assistant", "content": tgt},
        ],
        "metadata": metadata,
    }


def _downsample_bible(
    examples: list[dict[str, Any]], *, bible_max_share: float
) -> list[dict[str, Any]]:
    if not 0 < bible_max_share < 1:
        return examples

    bible = [x for x in examples if x["metadata"].get("content_type") == "bible_verse"]
    non_bible = [x for x in examples if x["metadata"].get("content_type") != "bible_verse"]
    if not bible or not non_bible:
        return examples

    max_bible = math.floor((bible_max_share / (1.0 - bible_max_share)) * len(non_bible))
    if len(bible) <= max_bible:
        return examples

    bible_sorted = sorted(bible, key=lambda x: _stable_hash(x["id"]))
    return sorted(non_bible + bible_sorted[:max_bible], key=lambda x: _stable_hash(x["id"]))


def _summarize(examples: list[dict[str, Any]]) -> dict[str, Any]:
    if not examples:
        return {"examples": 0}
    by_dir = Counter(x["metadata"]["direction"] for x in examples)
    by_ct = Counter(x["metadata"].get("content_type", "unknown") for x in examples)
    by_domain = Counter(x["metadata"].get("domain", "unknown") for x in examples)
    return {
        "examples": len(examples),
        "by_direction": dict(by_dir),
        "by_content_type": dict(by_ct),
        "by_domain": dict(by_domain),
        "target_chars_mean": round(
            statistics.mean(len(x["messages"][-1]["content"]) for x in examples), 1
        ),
    }


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render decontaminated splits into training-ready chat JSONL"
    )
    parser.add_argument("--splits-dir", type=Path, default=SPLITS_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--include-unstructured", action="store_true",
                        help="Merge unstructured seed into training data")
    parser.add_argument("--unstruct-dir", type=Path, default=UNSTRUCT_DIR)
    parser.add_argument("--bible-max-train-share", type=float, default=0.70)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Phase 1: Read decontaminated splits
    print(f"Reading splits from {args.splits_dir} ...")
    train_raw = read_jsonl(args.splits_dir / "train.jsonl")
    val_raw = read_jsonl(args.splits_dir / "validation.jsonl")
    test_raw = read_jsonl(args.splits_dir / "test.jsonl")
    print(f"  train: {len(train_raw)}, val: {len(val_raw)}, test: {len(test_raw)}")

    # Phase 2: Render to chat format (both directions)
    print("Rendering to chat format ...")
    train_examples: list[dict[str, Any]] = []
    val_examples: list[dict[str, Any]] = []
    test_examples: list[dict[str, Any]] = []

    for raw, target in [(train_raw, train_examples), (val_raw, val_examples), (test_raw, test_examples)]:
        for row in raw:
            target.append(render_example(row, "tvl_to_en"))
            target.append(render_example(row, "en_to_tvl"))

    print(f"  Rendered: train={len(train_examples)}, val={len(val_examples)}, test={len(test_examples)}")

    # Phase 3: Optionally merge unstructured seed
    if args.include_unstructured:
        unstruct_path = args.unstruct_dir / "train_balanced.jsonl"
        if unstruct_path.exists():
            unstruct = read_jsonl(unstruct_path)
            print(f"  Merging {len(unstruct)} unstructured examples into train")
            train_examples.extend(unstruct)
        else:
            print(f"  WARNING: {unstruct_path} not found, skipping unstructured")

    # Phase 4: Bible downsampling + deterministic sort
    train_full = sorted(train_examples, key=lambda x: _stable_hash(x["id"]))
    train_balanced = _downsample_bible(
        train_full, bible_max_share=args.bible_max_train_share
    )
    val_sorted = sorted(val_examples, key=lambda x: _stable_hash(x["id"]))
    test_sorted = sorted(test_examples, key=lambda x: _stable_hash(x["id"]))

    # Summary
    print(f"\n-- Final dataset --")
    print(f"  train_full:     {len(train_full):>7,}")
    print(f"  train_balanced: {len(train_balanced):>7,}")
    print(f"  validation:     {len(val_sorted):>7,}")
    print(f"  test:           {len(test_sorted):>7,}")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
        return

    # Phase 5: Write outputs
    print(f"\nWriting to {args.output_dir} ...")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(args.output_dir / "train_full.jsonl", train_full)
    write_jsonl(args.output_dir / "train_balanced.jsonl", train_balanced)
    write_jsonl(args.output_dir / "validation.jsonl", val_sorted)
    write_jsonl(args.output_dir / "test.jsonl", test_sorted)

    stats = {
        "source": {
            "splits_dir": str(args.splits_dir),
            "include_unstructured": args.include_unstructured,
            "bible_max_train_share": args.bible_max_train_share,
        },
        "train_full": _summarize(train_full),
        "train_balanced": _summarize(train_balanced),
        "validation": _summarize(val_sorted),
        "test": _summarize(test_sorted),
    }
    write_json(args.output_dir / "stats.json", stats)
    print("  Done.")


if __name__ == "__main__":
    main()
