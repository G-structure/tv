#!/usr/bin/env python3
"""CLI: optional OpenAI-backed Stage C job orchestration."""

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
    if "input_path" in paths:
        cfg["input_path"] = paths["input_path"]
    if "output_dir" in paths:
        cfg["output_dir"] = paths["output_dir"]

    job = raw.get("job", {})
    for key in (
        "job_type",
        "model",
        "max_rows",
        "execute",
        "use_batch",
        "poll_interval_seconds",
        "batch_completion_window",
    ):
        if key in job:
            cfg[key] = job[key]
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage C optional OpenAI job orchestration")
    parser.add_argument("--config", type=str, default=None, help="Optional config JSON")
    parser.add_argument("--input-path", type=str, default=None, help="Input JSONL path")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument(
        "--job-type",
        type=str,
        default=None,
        choices=("prompt_synthesis", "ocr_cleanup", "preferences", "transcription_cleanup"),
        help="OpenAI job type",
    )
    parser.add_argument("--model", type=str, default=None, help="OpenAI model")
    parser.add_argument("--max-rows", type=int, default=None, help="Max rows to include")
    parser.add_argument("--execute", action="store_true", help="Actually execute instead of dry-run")
    parser.add_argument("--sync", action="store_true", help="Use synchronous requests instead of Batch API")
    args = parser.parse_args()

    raw = load_optional_config(args.config)
    config = _translate_config(raw)
    config = merge_cli_overrides(
        config,
        {
            "input_path": args.input_path,
            "output_dir": args.output_dir,
            "job_type": args.job_type,
            "model": args.model,
            "max_rows": args.max_rows,
            "execute": args.execute or None,
            "use_batch": False if args.sync else None,
        },
    )

    from tv.training.stage_c.openai_jobs import main as jobs_main

    manifest = jobs_main(config)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

