"""Optional OpenAI-backed Stage C batch/sync job tooling."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from tv.common.config import get_repo_root, resolve_path
from tv.common.io import read_jsonl, write_json, write_jsonl


DEFAULTS: dict[str, Any] = {
    "input_path": "data/external/stage_c_seed/grounded_sft_mirrors.jsonl",
    "output_dir": "data/external/stage_c_seed/openai_jobs",
    "job_type": "prompt_synthesis",
    "model": "gpt-5.4-mini",
    "max_rows": 200,
    "execute": False,
    "use_batch": True,
    "poll_interval_seconds": 10,
    "batch_completion_window": "24h",
}


def load_repo_env() -> dict[str, str]:
    """Load `.env` into the current process without overriding live env."""
    repo_root = get_repo_root()
    env_path = repo_root / ".env"
    loaded: dict[str, str] = {}
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
                loaded[key] = value
    if not os.environ.get("OPENAI_API_KEY"):
        bridge = os.environ.get("OPENAI_KEY") or os.environ.get("OPEN_AI")
        if bridge:
            os.environ["OPENAI_API_KEY"] = bridge
            loaded["OPENAI_API_KEY"] = bridge
    return loaded


def _prompt_for_row(job_type: str, row: dict[str, Any]) -> list[dict[str, str]]:
    if job_type == "prompt_synthesis":
        answer = row.get("assistant") or row.get("chosen") or ""
        task_family = row.get("task_family", "unknown")
        return [
            {
                "role": "system",
                "content": "Create compact prompt-side variants only. Do not change the answer facts. Return strict JSON.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task_family": task_family,
                        "answer": answer,
                        "source_doc_id": row.get("source_doc_id"),
                        "request": "Generate a native TVL prompt, an English prompt requesting a Tuvaluan answer, and a mixed TVL/EN prompt. Return JSON only.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    if job_type == "ocr_cleanup":
        return [
            {
                "role": "system",
                "content": "Repair OCR while staying source-faithful. Preserve line order, names, dates, amounts, and uncertain spans. Return strict JSON.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "source_path": row.get("source_path"),
                        "page_or_image": row.get("page_or_image"),
                        "raw_text": row.get("raw_text"),
                        "request": "Return {cleaned_text, quality_flags, unresolved_spans}.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    if job_type == "preferences":
        return [
            {
                "role": "system",
                "content": "Rank grounded answers for Tuvaluan language fidelity. Return strict JSON with chosen/rejected and tags.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "messages": row.get("messages"),
                        "chosen": row.get("chosen"),
                        "rejected": row.get("rejected"),
                        "request": "Verify the better answer and tag leakage, translationese, entity loss, and unsupported facts.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    if job_type == "transcription_cleanup":
        return [
            {
                "role": "system",
                "content": "Clean transcript text faithfully. Preserve timing identifiers and do not invent missing speech. Return strict JSON.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "source_path": row.get("source_path"),
                        "raw_text": row.get("raw_text"),
                        "request": "Return {cleaned_text, speaker_hints, unresolved_spans}.",
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    raise ValueError(f"Unknown Stage C OpenAI job type: {job_type}")


def _request_items(rows: list[dict[str, Any]], *, job_type: str, model: str) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        custom_id = f"stage_c:{job_type}:{index:05d}:{row.get('id', row.get('source_doc_id', 'row'))}"
        body = {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": _prompt_for_row(job_type, row),
        }
        requests.append(
            {
                "custom_id": custom_id,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": body,
                "input_row": row,
            }
        )
    return requests


def _batch_requests_to_jsonl(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for request in requests:
        output.append(
            {
                "custom_id": request["custom_id"],
                "method": request["method"],
                "url": request["url"],
                "body": request["body"],
            }
        )
    return output


def _api_client() -> httpx.Client:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY is not set. Use dry-run or configure .env.")
    return httpx.Client(
        base_url="https://api.openai.com",
        headers={
            "Authorization": f"Bearer {key}",
        },
        timeout=120,
    )


def _create_batch(client: httpx.Client, *, requests_path: Path, completion_window: str) -> dict[str, Any]:
    files = {
        "file": (requests_path.name, requests_path.read_bytes(), "application/jsonl"),
        "purpose": (None, "batch"),
    }
    file_response = client.post("/v1/files", files=files)
    file_response.raise_for_status()
    file_payload = file_response.json()
    batch_response = client.post(
        "/v1/batches",
        json={
            "input_file_id": file_payload["id"],
            "endpoint": "/v1/chat/completions",
            "completion_window": completion_window,
        },
    )
    batch_response.raise_for_status()
    return {
        "input_file": file_payload,
        "batch": batch_response.json(),
    }


def _poll_batch(client: httpx.Client, batch_id: str, *, poll_interval_seconds: int) -> dict[str, Any]:
    while True:
        response = client.get(f"/v1/batches/{batch_id}")
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status in {"completed", "failed", "expired", "cancelled"}:
            return payload
        time.sleep(poll_interval_seconds)


def _download_batch_output(client: httpx.Client, output_file_id: str, destination: Path) -> Path:
    response = client.get(f"/v1/files/{output_file_id}/content")
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def _execute_sync(client: httpx.Client, requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    for request in requests:
        response = client.post(request["url"], json=request["body"])
        response.raise_for_status()
        outputs.append(
            {
                "custom_id": request["custom_id"],
                "response": response.json(),
                "input_row": request["input_row"],
            }
        )
    return outputs


def main(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    if config:
        cfg.update(config)

    load_repo_env()

    repo_root = get_repo_root()
    input_path = resolve_path(cfg["input_path"], repo_root)
    output_dir = resolve_path(cfg["output_dir"], repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(input_path)
    if cfg.get("max_rows"):
        rows = rows[: int(cfg["max_rows"])]

    requests = _request_items(
        rows,
        job_type=cfg["job_type"],
        model=cfg["model"],
    )
    requests_jsonl = _batch_requests_to_jsonl(requests)
    requests_path = output_dir / f"{cfg['job_type']}_requests.jsonl"
    write_jsonl(requests_path, requests_jsonl)

    manifest: dict[str, Any] = {
        "job_type": cfg["job_type"],
        "model": cfg["model"],
        "input_path": str(input_path),
        "output_dir": str(output_dir),
        "request_count": len(requests_jsonl),
        "execute": bool(cfg["execute"]),
        "use_batch": bool(cfg["use_batch"]),
        "requests_path": str(requests_path),
    }

    if not cfg["execute"]:
        write_json(output_dir / f"{cfg['job_type']}_manifest.json", manifest)
        return manifest

    client = _api_client()
    if cfg["use_batch"]:
        created = _create_batch(
            client,
            requests_path=requests_path,
            completion_window=cfg["batch_completion_window"],
        )
        manifest["batch_create"] = created
        batch_id = created["batch"]["id"]
        batch_status = _poll_batch(
            client,
            batch_id,
            poll_interval_seconds=int(cfg["poll_interval_seconds"]),
        )
        manifest["batch_status"] = batch_status
        output_file_id = batch_status.get("output_file_id")
        if output_file_id:
            output_file = _download_batch_output(
                client,
                output_file_id,
                output_dir / f"{cfg['job_type']}_batch_output.jsonl",
            )
            manifest["batch_output_path"] = str(output_file)
    else:
        sync_outputs = _execute_sync(client, requests)
        sync_output_path = output_dir / f"{cfg['job_type']}_sync_output.jsonl"
        write_jsonl(sync_output_path, sync_outputs)
        manifest["sync_output_path"] = str(sync_output_path)

    write_json(output_dir / f"{cfg['job_type']}_manifest.json", manifest)
    return manifest

