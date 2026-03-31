"""Stage C native-grounding evaluation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from tv.common.config import get_repo_root, resolve_path
from tv.common.io import read_jsonl, write_json, write_jsonl
from tv.common.manifests import create_manifest, save_manifest
from tv.common.tinker_runtime import (
    create_sampling_client,
    create_service_client,
    get_renderer,
    get_sampling_params,
    require_tinker_api_key,
)
from tv.training.stage_c.pipeline import _extract_entities, _extract_numbers, _normalize_text, guess_language

logger = logging.getLogger(__name__)


DEFAULTS: dict[str, Any] = {
    "model_name": "openai/gpt-oss-120b",
    "model_path": None,
    "eval_manifest": "data/finetune/stage_c_eval/manifest.jsonl",
    "output_dir": "eval/stage_c_native/results",
    "max_tokens": 768,
    "temperature": 0.0,
    "eval_limit": None,
    "dry_run": False,
}


def _token_overlap(a: str, b: str) -> float:
    a_tokens = {token.lower() for token in _normalize_text(a).split() if token}
    b_tokens = {token.lower() for token in _normalize_text(b).split() if token}
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens)


def _entity_preservation(prediction: str, reference: str) -> float:
    ref_entities = set(_extract_entities(reference))
    ref_numbers = set(_extract_numbers(reference))
    required = ref_entities | ref_numbers
    if not required:
        return 1.0
    pred_text = _normalize_text(prediction)
    kept = sum(1 for item in required if item and item in pred_text)
    return kept / len(required)


def _style_proxy(task_family: str, prediction: str) -> float:
    text = _normalize_text(prediction)
    if not text:
        return 0.0
    if task_family == "headline_generation":
        return 1.0 if len(text.split()) <= 16 else 0.3
    if task_family == "entity_extraction":
        return 1.0 if "\n" in text or text.startswith("-") else 0.4
    if task_family in {"summary_short", "summary_medium"}:
        sentences = sum(text.count(mark) for mark in ".!?")
        return 1.0 if sentences <= 4 else 0.5
    return 0.8


def _extract_prompt_and_reference(example: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    return (
        [
            {"role": "system", "content": "Stay faithful to the source."},
            {"role": "user", "content": example["prompt"]},
        ],
        example["reference_answer"],
    )


def _generate_predictions(
    *,
    examples: list[dict[str, Any]],
    model_name: str,
    model_path: str | None,
    max_tokens: int,
    temperature: float,
) -> list[dict[str, Any]]:
    require_tinker_api_key()
    service = create_service_client()
    _tokenizer, renderer, _renderer_name = get_renderer(model_name)
    sampling_params = get_sampling_params(
        renderer,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    sampling_client = create_sampling_client(
        service,
        model_path=model_path,
        base_model=None if model_path else model_name,
    )

    predictions: list[dict[str, Any]] = []
    for index, example in enumerate(examples, start=1):
        prompt_messages, reference = _extract_prompt_and_reference(example)
        try:
            prompt = renderer.build_generation_prompt(prompt_messages)
            result = sampling_client.sample(
                prompt,
                sampling_params=sampling_params,
                num_samples=1,
            ).result()
            tokens = result.sequences[0].tokens
            response_message, _ok = renderer.parse_response(tokens)
            if isinstance(response_message, dict):
                prediction = str(response_message.get("content", ""))
            else:
                prediction = str(response_message)
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            logger.warning("Stage C eval generation failed for %s: %s", example.get("id"), exc)
            prediction = ""
        predictions.append(
            {
                "id": example["id"],
                "task_family": example["task_family"],
                "prompt": example["prompt"],
                "reference": reference,
                "prediction": prediction,
                "source_segments_text": example.get("source_segments_text", []),
            }
        )
        if index % 20 == 0:
            logger.info("Generated %d / %d Stage C eval predictions", index, len(examples))
    return predictions


def _score_prediction(example: dict[str, Any], prediction: str) -> dict[str, Any]:
    reference = example["reference_answer"]
    source_text = "\n\n".join(example.get("source_segments_text", []))
    adequacy = _token_overlap(reference, prediction)
    language_expected = "en" if example["task_family"] in {"translation_to_english", "explain_in_english"} else "tvl"
    language_actual = guess_language(prediction, source_path=example.get("metadata", {}).get("source_path"))
    language_score = 1.0 if (language_expected == "tvl" and language_actual in {"tvl", "mixed"}) or language_actual == language_expected else 0.0
    entity_score = _entity_preservation(prediction, reference)
    style_score = _style_proxy(example["task_family"], prediction)
    source_support = _token_overlap(prediction, source_text or reference)
    return {
        "adequacy": adequacy,
        "in_language_fidelity": language_score,
        "entity_preservation": entity_score,
        "style_fit": style_score,
        "source_support": source_support,
        "language_detected": language_actual,
    }


def main(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    if config:
        cfg.update(config)

    repo_root = get_repo_root()
    eval_manifest = resolve_path(cfg["eval_manifest"], repo_root)
    output_dir = resolve_path(cfg["output_dir"], repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    examples = read_jsonl(eval_manifest)
    if cfg.get("eval_limit"):
        examples = examples[: int(cfg["eval_limit"])]

    if cfg["dry_run"]:
        predictions = [
            {
                "id": example["id"],
                "task_family": example["task_family"],
                "prompt": example["prompt"],
                "reference": example["reference_answer"],
                "prediction": example["reference_answer"],
                "source_segments_text": example.get("source_segments_text", []),
            }
            for example in examples
        ]
    else:
        predictions = _generate_predictions(
            examples=examples,
            model_name=cfg["model_name"],
            model_path=cfg.get("model_path"),
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
        )

    scored_rows: list[dict[str, Any]] = []
    for example, pred in zip(examples, predictions, strict=False):
        metrics = _score_prediction(example, pred["prediction"])
        scored_rows.append({**pred, **metrics})

    aggregate = {
        "count": len(scored_rows),
        "by_slice": {},
        "means": {},
    }
    if scored_rows:
        for key in ("adequacy", "in_language_fidelity", "entity_preservation", "style_fit", "source_support"):
            aggregate["means"][key] = sum(row[key] for row in scored_rows) / len(scored_rows)
        slices = sorted({example["slice"] for example in examples})
        for slice_name in slices:
            subset = [row for row, example in zip(scored_rows, examples, strict=False) if example["slice"] == slice_name]
            if not subset:
                continue
            aggregate["by_slice"][slice_name] = {
                key: sum(row[key] for row in subset) / len(subset)
                for key in ("adequacy", "in_language_fidelity", "entity_preservation", "style_fit", "source_support")
            }

    write_jsonl(output_dir / "predictions.jsonl", scored_rows)
    write_json(output_dir / "report.json", aggregate)
    write_jsonl(output_dir / "human_review_pack.jsonl", scored_rows[: min(32, len(scored_rows))])

    manifest = create_manifest(
        stage="stage_c_native_eval",
        config=cfg,
        extra={
            "eval_manifest": str(eval_manifest),
            "output_dir": str(output_dir),
            "count": len(scored_rows),
            "dry_run": bool(cfg["dry_run"]),
        },
    )
    save_manifest(manifest, output_dir / "manifest.json")
    return aggregate

