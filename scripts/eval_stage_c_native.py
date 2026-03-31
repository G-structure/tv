#!/usr/bin/env python3
"""CLI: evaluate held-out Stage C native grounding data."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tv.common.cli import load_optional_config, merge_cli_overrides


def _translate_config(raw: dict) -> dict:
    cfg: dict = {}
    model = raw.get("model", {})
    if "name" in model:
        cfg["model_name"] = model["name"]

    data = raw.get("data", {})
    if "eval_manifest" in data:
        cfg["eval_manifest"] = data["eval_manifest"]

    eval_section = raw.get("eval", {})
    if "out_dir" in eval_section:
        cfg["output_dir"] = eval_section["out_dir"]
    if "max_tokens" in eval_section:
        cfg["max_tokens"] = eval_section["max_tokens"]
    if "temperature" in eval_section:
        cfg["temperature"] = eval_section["temperature"]
    if "eval_limit" in eval_section:
        cfg["eval_limit"] = eval_section["eval_limit"]

    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Stage C held-out native grounding data")
    parser.add_argument("--config", type=str, default=None, help="Optional Stage C eval config JSON")
    parser.add_argument("--model-path", type=str, default=None, help="Optional LoRA/model path to evaluate")
    parser.add_argument("--dry-run", action="store_true", help="Skip remote generation and score reference answers")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    raw = load_optional_config(args.config)
    config = _translate_config(raw)
    config = merge_cli_overrides(
        config,
        {
            "model_path": args.model_path,
            "dry_run": args.dry_run,
        },
    )

    from tv.training.stage_c.eval import main as eval_main

    report = eval_main(config)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

