#!/usr/bin/env python3
"""CLI: build the Stage C native-document grounding package."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tv.common.cli import load_optional_config, merge_cli_overrides


def _translate_config(raw: dict) -> dict:
    cfg: dict = {}
    paths = raw.get("paths", {})
    for key, value in {
        "asset_dir": paths.get("asset_dir"),
        "stage_a_seed_dir": paths.get("stage_a_seed_dir"),
        "ocr_dir": paths.get("ocr_dir"),
        "ocr_fast_dir": paths.get("ocr_fast_dir"),
        "output_dir": paths.get("output_dir"),
        "sft_output_dir": paths.get("sft_output_dir"),
        "dpo_output_dir": paths.get("dpo_output_dir"),
        "eval_output_dir": paths.get("eval_output_dir"),
        "eval_dir": paths.get("eval_dir"),
        "reports_dir": paths.get("reports_dir"),
    }.items():
        if value is not None:
            cfg[key] = value

    build = raw.get("build", {})
    for key in (
        "default_arm",
        "val_fraction",
        "holdout_fraction",
        "max_news_articles_per_source",
        "min_doc_chars",
        "min_segment_chars",
        "ocr_missing_small_pdfs",
    ):
        if key in build:
            cfg[key] = build[key]

    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Stage C native grounding dataset package")
    parser.add_argument("--config", type=str, default=None, help="Optional Stage C config JSON")
    parser.add_argument("--asset-dir", type=str, default=None, help="Override raw source asset directory")
    parser.add_argument("--output-dir", type=str, default=None, help="Override seed output directory")
    parser.add_argument("--reports-dir", type=str, default=None, help="Override reports directory")
    args = parser.parse_args()

    raw = load_optional_config(args.config)
    config = _translate_config(raw)
    config = merge_cli_overrides(
        config,
        {
            "asset_dir": args.asset_dir,
            "output_dir": args.output_dir,
            "reports_dir": args.reports_dir,
        },
    )

    from tv.training.stage_c.pipeline import build_stage_c_package

    stats = build_stage_c_package(config)
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

