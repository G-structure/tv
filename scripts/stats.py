"""Dataset statistics and quality reporting.

Usage:
    uv run python scripts/stats.py
"""

import json
import hashlib
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ALIGNED_DIR = DATA_DIR / "aligned"


def load_all_records() -> dict[str, list[dict]]:
    """Load all JSONL files from the aligned directory, keyed by filename."""
    records_by_file = {}
    for jsonl_path in sorted(ALIGNED_DIR.glob("*.jsonl")):
        records = []
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        records_by_file[jsonl_path.name] = records
    return records_by_file


def compute_stats(all_records: list[dict]) -> dict:
    """Compute aggregate statistics over all records."""
    if not all_records:
        return {}

    tvl_chars_list = [r.get("tvl_chars", 0) for r in all_records]
    en_chars_list = [r.get("en_chars", 0) for r in all_records]
    ratios = [r.get("length_ratio", 0) for r in all_records if r.get("length_ratio")]

    def median(values):
        if not values:
            return 0
        s = sorted(values)
        n = len(s)
        if n % 2 == 0:
            return (s[n // 2 - 1] + s[n // 2]) / 2
        return s[n // 2]

    def mean(values):
        if not values:
            return 0
        return sum(values) / len(values)

    return {
        "tvl_chars": {
            "min": min(tvl_chars_list) if tvl_chars_list else 0,
            "max": max(tvl_chars_list) if tvl_chars_list else 0,
            "mean": round(mean(tvl_chars_list), 1),
            "median": round(median(tvl_chars_list), 1),
        },
        "en_chars": {
            "min": min(en_chars_list) if en_chars_list else 0,
            "max": max(en_chars_list) if en_chars_list else 0,
            "mean": round(mean(en_chars_list), 1),
            "median": round(median(en_chars_list), 1),
        },
        "length_ratio": {
            "min": round(min(ratios), 3) if ratios else 0,
            "max": round(max(ratios), 3) if ratios else 0,
            "mean": round(mean(ratios), 3) if ratios else 0,
            "median": round(median(ratios), 3) if ratios else 0,
        },
    }


def compute_ratio_histogram(all_records: list[dict]) -> dict[str, int]:
    """Compute length ratio distribution buckets."""
    buckets = {
        "0.0-0.5": 0,
        "0.5-1.0": 0,
        "1.0-1.5": 0,
        "1.5-2.0": 0,
        "2.0-3.0": 0,
        ">3.0": 0,
    }
    for r in all_records:
        ratio = r.get("length_ratio", 0)
        if ratio is None or ratio == 0:
            continue
        if ratio < 0.5:
            buckets["0.0-0.5"] += 1
        elif ratio < 1.0:
            buckets["0.5-1.0"] += 1
        elif ratio < 1.5:
            buckets["1.0-1.5"] += 1
        elif ratio < 2.0:
            buckets["1.5-2.0"] += 1
        elif ratio < 3.0:
            buckets["2.0-3.0"] += 1
        else:
            buckets[">3.0"] += 1
    return buckets


def find_quality_issues(all_records: list[dict]) -> dict:
    """Identify quality issues in the dataset."""
    empty_text = []
    extreme_ratios = []
    very_short = []
    seen_hashes = Counter()

    for r in all_records:
        rid = r.get("id", "?")
        tvl = r.get("tvl", "")
        en = r.get("en", "")

        # Empty text
        if not tvl or not tvl.strip() or not en or not en.strip():
            empty_text.append(rid)

        # Extreme length ratios
        ratio = r.get("length_ratio", 0)
        if ratio and (ratio < 0.3 or ratio > 3.0):
            extreme_ratios.append((rid, ratio))

        # Very short pairs
        tvl_chars = r.get("tvl_chars", 0)
        en_chars = r.get("en_chars", 0)
        if (tvl_chars and tvl_chars < 10) or (en_chars and en_chars < 10):
            very_short.append((rid, tvl_chars, en_chars))

        # Duplicate detection
        text_hash = hashlib.md5(
            (tvl.strip() + "|||" + en.strip()).encode()
        ).hexdigest()
        seen_hashes[text_hash] += 1

    duplicates = {h: c for h, c in seen_hashes.items() if c > 1}
    total_duplicate_pairs = sum(c - 1 for c in duplicates.values())

    return {
        "empty_text": empty_text,
        "extreme_ratios": extreme_ratios,
        "very_short": very_short,
        "duplicate_count": total_duplicate_pairs,
        "duplicate_groups": len(duplicates),
    }


def print_separator(char="=", width=60):
    print(char * width)


def main():
    if not ALIGNED_DIR.exists():
        print(f"No aligned data directory found at {ALIGNED_DIR}")
        return

    records_by_file = load_all_records()

    if not records_by_file:
        print("No JSONL files found in aligned directory.")
        return

    all_records = []
    for records in records_by_file.values():
        all_records.extend(records)

    print_separator()
    print("DATASET STATISTICS")
    print_separator()

    # Total pairs
    print(f"\nTotal pairs: {len(all_records)}")

    # Pairs per file
    print("\nPairs per file:")
    for fname, records in sorted(records_by_file.items()):
        print(f"  {fname}: {len(records)}")

    # Pairs by content_type
    content_type_counts = Counter(r.get("content_type", "unknown") for r in all_records)
    print("\nPairs by content_type:")
    for ct, count in content_type_counts.most_common():
        print(f"  {ct}: {count}")

    # Pairs by domain
    domain_counts = Counter(r.get("domain", "unknown") for r in all_records)
    print("\nPairs by domain:")
    for dom, count in domain_counts.most_common():
        print(f"  {dom}: {count}")

    # Character count stats
    stats = compute_stats(all_records)
    if stats:
        print("\nCharacter count stats (tvl_chars):")
        s = stats["tvl_chars"]
        print(f"  min: {s['min']}, max: {s['max']}, mean: {s['mean']}, median: {s['median']}")

        print("\nCharacter count stats (en_chars):")
        s = stats["en_chars"]
        print(f"  min: {s['min']}, max: {s['max']}, mean: {s['mean']}, median: {s['median']}")

        print("\nLength ratio stats (tvl/en):")
        s = stats["length_ratio"]
        print(f"  min: {s['min']}, max: {s['max']}, mean: {s['mean']}, median: {s['median']}")

    # Length ratio histogram
    histogram = compute_ratio_histogram(all_records)
    print("\nLength ratio distribution:")
    for bucket, count in histogram.items():
        bar = "#" * min(count, 50)
        pct = (count / len(all_records) * 100) if all_records else 0
        print(f"  {bucket:>7s}: {count:>6d} ({pct:5.1f}%) {bar}")

    # Quality issues
    print_separator()
    print("QUALITY ISSUES")
    print_separator()

    issues = find_quality_issues(all_records)

    print(f"\nEmpty text (either side): {len(issues['empty_text'])}")
    if issues["empty_text"]:
        for rid in issues["empty_text"][:10]:
            print(f"  - {rid}")
        if len(issues["empty_text"]) > 10:
            print(f"  ... and {len(issues['empty_text']) - 10} more")

    print(f"\nExtreme length ratios (outside 0.3-3.0): {len(issues['extreme_ratios'])}")
    if issues["extreme_ratios"]:
        for rid, ratio in issues["extreme_ratios"][:10]:
            print(f"  - {rid}: {ratio:.3f}")
        if len(issues["extreme_ratios"]) > 10:
            print(f"  ... and {len(issues['extreme_ratios']) - 10} more")

    print(f"\nDuplicates (exact tvl+en hash): {issues['duplicate_count']} "
          f"duplicate pairs in {issues['duplicate_groups']} groups")

    print(f"\nVery short pairs (either side < 10 chars): {len(issues['very_short'])}")
    if issues["very_short"]:
        for rid, tc, ec in issues["very_short"][:10]:
            print(f"  - {rid}: tvl={tc} chars, en={ec} chars")
        if len(issues["very_short"]) > 10:
            print(f"  ... and {len(issues['very_short']) - 10} more")

    print_separator()
    print("END OF REPORT")
    print_separator()


if __name__ == "__main__":
    main()
