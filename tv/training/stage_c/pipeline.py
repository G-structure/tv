"""Stage C native-document grounding pipeline.

This module builds the Stage C source manifest, extraction pool, grounded SFT
rows, preferences, held-out eval data, and training-ready renders.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import statistics
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tv.common.config import get_repo_root, resolve_path
from tv.common.io import read_json, read_jsonl, write_json, write_jsonl
from tv.common.manifests import create_manifest, hash_file, save_manifest


UTC_NOW = datetime.now(timezone.utc).isoformat()

SYSTEM_PROMPT_TVL = (
    "You are a careful Tuvaluan writer. Stay faithful to the source document. "
    "Do not add unsupported facts."
)
SYSTEM_PROMPT_EN = (
    "You are a careful bilingual assistant. Stay faithful to the source "
    "document and preserve names, dates, numbers, and quotations."
)

TVL_HINTS = {
    "te",
    "kae",
    "ko",
    "ki",
    "mai",
    "atu",
    "faka",
    "tuvalu",
    "malo",
    "fenua",
    "tala",
    "tenei",
    "tena",
    "konei",
    "konea",
    "fakatoka",
    "fakamau",
    "fakaaoga",
    "fakailoa",
    "faiga",
    "tagata",
    "manako",
    "fakafetai",
    "mote",
    "galuega",
    "atufenua",
    "matagaluega",
    "ola",
    "lei",
    "fakamatalaga",
}
TVL_EXTRA_CHARS = {"ā", "ē", "ī", "ō", "ū", "‵", "ʻ", "’"}
EN_HINTS = {
    "a",
    "an",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "education",
    "guidance",
    "in",
    "is",
    "it",
    "its",
    "learning",
    "learners",
    "of",
    "on",
    "or",
    "our",
    "should",
    "support",
    "teacher",
    "teachers",
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "these",
    "those",
    "their",
    "they",
    "to",
    "will",
    "would",
    "shall",
    "we",
    "working",
    "together",
    "your",
    "you",
    "house",
    "government",
    "report",
    "committee",
    "health",
    "budget",
    "ministry",
    "conference",
    "island",
}
ISLAND_HINTS = {
    "funafuti",
    "nanumea",
    "nanumaga",
    "nui",
    "nukufetau",
    "nukulaelae",
    "niutao",
    "niulakita",
    "vaitupu",
    "tuvalu",
    "nanumean",
}
ENTITY_STOPWORDS = {
    "Tuvalu",
    "Page",
    "The",
    "A",
    "An",
    "Of",
    "For",
    "And",
    "No",
    "TVL",
    "EN",
    "PDF",
}

NOISY_LINE_RE = re.compile(r"^[\W_]{2,}$")
WORD_RE = re.compile(r"[A-Za-zĀĒĪŌŪāēīōūʻ’'`-]+")
ENTITY_RE = re.compile(
    r"\b(?:[A-ZĀĒĪŌŪ][A-Za-zĀĒĪŌŪāēīōūʻ’'`-]+"
    r"(?:\s+[A-ZĀĒĪŌŪ][A-Za-zĀĒĪŌŪāēīōūʻ’'`-]+){0,5})\b"
)
DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+[A-Z][a-z]{2,9}\s+\d{4}"
    r"|\d{4}"
    r"|(?:Ianuali|Fepuali|Mati|Apelila|Mee|Iuni|Iulai|Aokuso|Setema|Oketopa|Novema|Tesema)\b)\b"
)
NUMBER_RE = re.compile(r"\b(?:\$?\d[\d,]*(?:\.\d+)?%?)\b")
QUOTE_RE = re.compile(r"[\"“”']([^\"“”']{12,300})[\"“”']")


DEFAULTS: dict[str, Any] = {
    "asset_dir": "unstruct_lang_data",
    "stage_a_seed_dir": "data/external/stage_a_seed",
    "ocr_dir": "data/external/ocr_scans",
    "ocr_fast_dir": "data/external/ocr_scans_fast",
    "output_dir": "data/external/stage_c_seed",
    "sft_output_dir": "data/finetune/stage_c_sft",
    "dpo_output_dir": "data/finetune/stage_c_dpo",
    "eval_output_dir": "data/finetune/stage_c_eval",
    "eval_dir": "eval/stage_c_native",
    "reports_dir": "reports",
    "default_arm": "native_plus_english",
    "val_fraction": 0.08,
    "holdout_fraction": 0.18,
    "max_news_articles_per_source": 64,
    "min_doc_chars": 180,
    "min_segment_chars": 80,
    "max_summary_sentences_short": 1,
    "max_summary_sentences_medium": 2,
    "max_fact_bullets": 4,
    "ocr_missing_small_pdfs": False,
}


@dataclass(slots=True)
class ExtractedSegment:
    """Internal segment representation used while building Stage C."""

    source_path: str
    segment_id: str
    text: str
    normalized_text: str
    likely_language: str
    page_or_image: str
    extraction_method: str
    support_type: str
    paired_en_text: str | None = None
    confidence_flags: list[str] | None = None


def _read_jsonl_safe(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return read_jsonl(path)


def _canonical_rel_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace(os.sep, "/")
    except ValueError:
        return str(path).replace(os.sep, "/")


def _canonical_stem(value: str) -> str:
    stem = Path(value).stem
    stem = re.sub(r"-p\d+-\d+$", "", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()
    return stem


def _slugify(value: str, *, fallback: str = "item") -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return value or fallback


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_hash(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


def _choose_variant(options: list[str], key: str) -> str:
    if not options:
        return ""
    return options[_stable_hash(key) % len(options)]


def _normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _split_sentences(text: str) -> list[str]:
    cleaned = _normalize_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZĀĒĪŌŪ0-9])", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _first_nonempty_lines(text: str, limit: int = 4) -> list[str]:
    return [line for line in text.splitlines() if line.strip()][:limit]


def _language_scores(text: str) -> tuple[int, int]:
    tokens = [token.lower() for token in WORD_RE.findall(text)]
    tvl = sum(token in TVL_HINTS for token in tokens)
    tvl += sum(token in ISLAND_HINTS for token in tokens)
    tvl += sum(char in TVL_EXTRA_CHARS for char in text)
    en = sum(token in EN_HINTS for token in tokens)
    return tvl, en


def guess_language(text: str, *, source_path: str | None = None) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return "unknown"
    tvl_score, en_score = _language_scores(normalized)
    if source_path:
        lower = source_path.lower()
        if "tuvaluan" in lower or "tuv_" in lower or lower.endswith("_tvl.pdf"):
            tvl_score += 2
        if lower.endswith("_en.pdf") or "english" in lower:
            en_score += 2
    if tvl_score == 0 and en_score == 0:
        return "unknown"
    if tvl_score >= en_score * 2 and tvl_score >= 2:
        return "tvl"
    if en_score >= tvl_score * 2 and en_score >= 2:
        return "en"
    return "mixed"


def _tvl_ratio(text: str) -> float:
    tvl_score, en_score = _language_scores(text)
    total = tvl_score + en_score
    if total == 0:
        return 0.0
    return tvl_score / total


def _extract_entities(text: str) -> list[str]:
    entities: list[str] = []
    seen: set[str] = set()
    for match in ENTITY_RE.findall(text):
        if match in ENTITY_STOPWORDS:
            continue
        if len(match) < 3:
            continue
        if match in seen:
            continue
        seen.add(match)
        entities.append(match)
    for island in sorted(ISLAND_HINTS):
        island_title = island.title()
        if island in text.lower() and island_title not in seen:
            entities.append(island_title)
            seen.add(island_title)
    return entities


def _extract_numbers(text: str) -> list[str]:
    seen: set[str] = set()
    numbers: list[str] = []
    for match in NUMBER_RE.findall(text):
        if match not in seen:
            numbers.append(match)
            seen.add(match)
    return numbers


def _extract_dates(text: str) -> list[str]:
    seen: set[str] = set()
    dates: list[str] = []
    for match in DATE_RE.findall(text):
        if match not in seen:
            dates.append(match)
            seen.add(match)
    return dates


def _fact_bullets(text: str, *, limit: int) -> list[str]:
    bullets: list[str] = []
    seen: set[str] = set()
    for sentence in _split_sentences(text):
        if len(sentence) < 18:
            continue
        if sentence in seen:
            continue
        if _extract_entities(sentence) or _extract_numbers(sentence) or _extract_dates(sentence):
            bullets.append(sentence)
            seen.add(sentence)
        if len(bullets) >= limit:
            break
    if not bullets:
        for sentence in _split_sentences(text)[:limit]:
            if sentence not in seen:
                bullets.append(sentence)
                seen.add(sentence)
    return bullets[:limit]


def _headline_from_text(text: str, *, fallback: str) -> str:
    lines = _first_nonempty_lines(text, limit=6)
    for line in lines:
        words = WORD_RE.findall(line)
        if 3 <= len(words) <= 14:
            upper_ratio = sum(char.isupper() for char in line if char.isalpha()) / max(
                sum(char.isalpha() for char in line), 1
            )
            if upper_ratio >= 0.35 or len(line) <= 90:
                return line.strip()
    sentences = _split_sentences(text)
    if sentences:
        words = sentences[0].split()
        if len(words) > 14:
            return " ".join(words[:14]).rstrip(",;:")
        return sentences[0]
    return fallback


def _summary_from_text(text: str, *, max_sentences: int) -> str:
    sentences = _split_sentences(text)
    if sentences:
        return " ".join(sentences[:max_sentences]).strip()
    return text.strip()


def _lead_from_text(text: str) -> str:
    sentences = _split_sentences(text)
    if sentences:
        return sentences[0].strip()
    return _normalize_text(text)


def _quote_from_text(text: str) -> str | None:
    match = QUOTE_RE.search(text)
    if match:
        return match.group(1).strip()
    return None


def _as_iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cmd_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _run_capture(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def _pdf_page_count(pdf_path: Path) -> int:
    output = _run_capture(["pdfinfo", str(pdf_path)])
    match = re.search(r"Pages:\s+(\d+)", output)
    return int(match.group(1)) if match else 0


def _pdftotext_pages(pdf_path: Path) -> list[str]:
    text = _run_capture(["pdftotext", "-layout", str(pdf_path), "-"])
    if not text:
        return []
    pages = [page.strip() for page in text.split("\f")]
    while pages and not pages[-1]:
        pages.pop()
    return pages


def _ocr_image_text(image_path: Path) -> str:
    if not _cmd_exists("tesseract"):
        return ""
    output = _run_capture(["tesseract", str(image_path), "stdout", "--psm", "6"])
    return _normalize_text(output)


def _broad_domain(source_family: str, source_path: str) -> list[str]:
    lower = source_path.lower()
    if "news" in source_family or "news" in lower:
        return ["news"]
    if "finance" in lower or "budget" in lower:
        return ["finance", "civic"]
    if "health" in lower or "medicare" in lower or "measles" in lower or "diabetes" in lower:
        return ["health", "civic"]
    if "education" in lower or "activity" in lower:
        return ["education", "civic"]
    if "nanumea" in lower or "childrens" in lower or "book" in lower:
        return ["culture", "narrative"]
    if "nature" in lower or "biorap" in lower:
        return ["biodiversity", "civic"]
    if "dictionary" in lower or "tatoeba" in lower or "corpus" in lower:
        return ["lexical"]
    return ["civic"]


def _source_family_for_path(source_path: str) -> str:
    lower = source_path.lower()
    if "don_t use yet" in lower:
        return "quarantine_pdf"
    if lower.endswith((".mp4", ".webm", ".mp3", ".wav")) or "/audio/" in lower:
        return "audio_video_asset"
    if "historic archives" in lower or "news_sheets" in lower:
        return "historic_news_scan"
    if "childrens books" in lower or "magical_garlands" in lower or "matua fakamoe" in lower or "am i small" in lower:
        return "children_book"
    if "/documents/nanumea/" in lower:
        return "oral_traditional_material"
    if "medicare" in lower or "steps report" in lower or "diabetes" in lower or "measles" in lower or "bcg" in lower:
        return "health_pdf"
    if "education" in lower or "te papa" in lower or "activity_book" in lower:
        return "education_pdf"
    if "finance" in lower or "budget" in lower:
        return "finance_pdf"
    if "/documents/" in lower:
        return "government_pdf"
    if "/nature/" in lower:
        return "biodiversity_reference"
    if "dictionary" in lower or "tatoeba" in lower or "corpus" in lower or "language_cards" in lower:
        return "lexical_reference"
    if "misc copies" in lower or "full_listing" in lower or lower.endswith((".zip", ".docx", ".csv", ".tsv", ".json")):
        return "duplicate_reference"
    return "other_source"


def _status_guess_for_source(
    source_path: str,
    *,
    already_has_extracted_counterpart: bool,
    has_ocr_counterpart: bool,
) -> str:
    family = _source_family_for_path(source_path)
    lower = source_path.lower()
    if family == "duplicate_reference":
        return "Duplicate/reference"
    if family == "audio_video_asset":
        return "Media-only"
    if family == "quarantine_pdf":
        return "Raw-only"
    if "news_sheets" in lower or "magical_garlands" in lower:
        return "Term-only" if has_ocr_counterpart else "Raw-only"
    if already_has_extracted_counterpart:
        return "Merged"
    return "Raw-only"


def _recommended_use_for_source(source_path: str, source_family: str) -> str:
    lower = source_path.lower()
    if source_family == "duplicate_reference":
        return "reference_only"
    if source_family == "audio_video_asset":
        return "subtitle_or_transcript_recovery"
    if source_family == "quarantine_pdf":
        return "quarantine_until_cleaned"
    if source_family == "historic_news_scan":
        return "promote_to_article_level_grounding"
    if source_family == "children_book":
        return "narrative_grounding"
    if source_family in {"government_pdf", "health_pdf", "finance_pdf", "education_pdf"}:
        return "grounded_civic_tasks"
    if source_family == "oral_traditional_material":
        return "cultural_grounding"
    if source_family == "lexical_reference":
        if "dictionary" in lower or "tatoeba" in lower or "corpus" in lower:
            return "lexical_support_only"
        return "support_only"
    if source_family == "biodiversity_reference":
        return "terminology_support_and_grounded_factual_tasks"
    return "support_only"


def _task_value_for_source(source_family: str, status_guess: str) -> str:
    if status_guess == "Duplicate/reference":
        return "low"
    if source_family in {"historic_news_scan", "health_pdf", "finance_pdf", "education_pdf", "oral_traditional_material"}:
        return "high"
    if source_family in {"children_book", "government_pdf", "biodiversity_reference"}:
        return "medium"
    if source_family in {"audio_video_asset", "lexical_reference"}:
        return "support_only"
    return "medium"


def _cleanup_cost_for_source(source_family: str, status_guess: str) -> str:
    if status_guess == "Duplicate/reference":
        return "none"
    if source_family in {"historic_news_scan", "children_book", "audio_video_asset"}:
        return "high"
    if source_family in {"health_pdf", "finance_pdf", "education_pdf", "government_pdf"}:
        return "medium"
    if source_family == "lexical_reference":
        return "low"
    return "medium"


def _holdout_candidate_for_source(source_family: str, status_guess: str) -> bool:
    if status_guess in {"Duplicate/reference", "Media-only"}:
        return False
    return source_family in {
        "historic_news_scan",
        "government_pdf",
        "health_pdf",
        "finance_pdf",
        "education_pdf",
        "children_book",
        "oral_traditional_material",
    }


def _copyright_status(source_family: str, source_path: str) -> str:
    lower = source_path.lower()
    if source_family in {"government_pdf", "health_pdf", "finance_pdf", "education_pdf"}:
        return "public_or_public_facing_document"
    if source_family in {"children_book", "oral_traditional_material", "historic_news_scan"}:
        return "third_party_research_only"
    if "dictionary" in lower or "grammar" in lower:
        return "reference_only"
    return "research_only"


def _ingest_status(source_family: str, status_guess: str, segment_count: int) -> str:
    if status_guess == "Duplicate/reference":
        return "excluded_duplicate"
    if source_family == "quarantine_pdf":
        return "quarantined"
    if segment_count == 0:
        return "candidate_only"
    if source_family in {"lexical_reference", "biodiversity_reference"}:
        return "support_only"
    return "ready"


def _content_kind(source_family: str) -> str:
    if source_family == "historic_news_scan":
        return "article"
    if source_family in {"children_book", "oral_traditional_material"}:
        return "narrative"
    if source_family in {"finance_pdf", "government_pdf", "health_pdf", "education_pdf"}:
        return "report_or_notice"
    if source_family == "lexical_reference":
        return "lexical_reference"
    if source_family == "audio_video_asset":
        return "media_asset"
    return "document"


def _title_from_source(source_path: str, text: str) -> str:
    headline = _headline_from_text(text, fallback=Path(source_path).stem.replace("_", " "))
    if headline:
        return headline
    return Path(source_path).stem.replace("_", " ")


def _build_source_manifest(
    *,
    repo_root: Path,
    asset_dir: Path,
    stage_a_sources: dict[str, list[dict[str, Any]]],
    ocr_groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(asset_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = _canonical_rel_path(path, repo_root)
        if rel_path.endswith("/.DS_Store") or rel_path == ".DS_Store":
            continue
        source_family = _source_family_for_path(rel_path)
        stem = _canonical_stem(rel_path)
        already_has_extracted_counterpart = rel_path in stage_a_sources or stem in ocr_groups
        status_guess = _status_guess_for_source(
            rel_path,
            already_has_extracted_counterpart=already_has_extracted_counterpart,
            has_ocr_counterpart=stem in ocr_groups,
        )
        row = {
            "source_path": rel_path,
            "source_family": source_family,
            "status_guess": status_guess,
            "likely_language": "tvl" if "tuvaluan" in rel_path.lower() else "mixed",
            "likely_task_value": _task_value_for_source(source_family, status_guess),
            "estimated_cleanup_cost": _cleanup_cost_for_source(source_family, status_guess),
            "recommended_use": _recommended_use_for_source(rel_path, source_family),
            "already_has_extracted_counterpart": already_has_extracted_counterpart,
            "duplicate_or_reference_flag": source_family == "duplicate_reference",
            "holdout_candidate": _holdout_candidate_for_source(source_family, status_guess),
            "notes": "",
        }
        if "don_t use yet" in rel_path.lower():
            row["notes"] = "Quarantine until pairing and source-role cleanup are done."
        elif source_family == "historic_news_scan":
            row["notes"] = "Historic OCR-heavy news source; prefer article recovery over page dumps."
        elif source_family == "audio_video_asset":
            row["notes"] = "Keep out of default SFT until subtitles or transcripts exist."
        elif source_family == "duplicate_reference":
            row["notes"] = "Reference-only or duplicate helper asset."
        rows.append(row)
    return rows


def _load_stage_a_seed_sources(stage_a_seed_dir: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(stage_a_seed_dir.glob("*.jsonl")):
        if path.name == "rejected.jsonl":
            continue
        for row in _read_jsonl_safe(path):
            source = row.get("source_url_tvl") or row.get("metadata", {}).get("source_file")
            if not source:
                continue
            grouped[str(source)].append({"seed_file": path.name, **row})
    return grouped


def _extract_ocr_confidence(row: dict[str, Any]) -> float:
    value = row.get("conf_mean")
    if value is None:
        value = row.get("confidence_mean")
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_ocr_groups(*dirs: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for directory in dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.jsonl")):
            stem = _canonical_stem(path.name)
            for row in _read_jsonl_safe(path):
                grouped[stem].append({"ocr_file": path.name, **row})
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row.get("page") or 0))
    return grouped


def _stage_a_segments_from_rows(
    source_path: str,
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[ExtractedSegment]]:
    extracted_rows: list[dict[str, Any]] = []
    segments: list[ExtractedSegment] = []
    for index, row in enumerate(rows, start=1):
        raw_text = str(row.get("tvl") or "").strip()
        normalized = _normalize_text(raw_text)
        if not normalized:
            continue
        segment_id = f"{_slugify(Path(source_path).stem)}-seed-{index:04d}"
        flags = [
            "seed_aligned",
            f"alignment_confidence:{row.get('alignment_confidence', 'unknown')}",
        ]
        likely_language = guess_language(normalized, source_path=source_path)
        extracted_rows.append(
            {
                "source_id": f"source:{_slugify(_canonical_stem(source_path))}",
                "source_path": source_path,
                "page_or_image": str(
                    row.get("metadata", {}).get("source_page")
                    or row.get("metadata", {}).get("pair_index")
                    or index
                ),
                "raw_text": raw_text,
                "normalized_text": normalized,
                "extraction_method": "existing_stage_a_seed",
                "confidence_or_quality_flags": flags,
                "likely_language": likely_language,
                "checksum": _sha256_text(normalized),
                "provenance": {
                    "seed_file": row.get("seed_file"),
                    "seed_row_id": row.get("id"),
                    "content_type": row.get("content_type"),
                    "domain": row.get("domain"),
                    "paired_en_text": row.get("en"),
                    "source_url_en": row.get("source_url_en"),
                },
            }
        )
        segments.append(
            ExtractedSegment(
                source_path=source_path,
                segment_id=segment_id,
                text=raw_text,
                normalized_text=normalized,
                likely_language=likely_language,
                page_or_image=str(index),
                extraction_method="existing_stage_a_seed",
                support_type="direct_support",
                paired_en_text=str(row.get("en") or "") or None,
                confidence_flags=flags,
            )
        )
    return extracted_rows, segments


def _page_rows_from_ocr(
    source_path: str,
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[ExtractedSegment]]:
    extracted_rows: list[dict[str, Any]] = []
    segments: list[ExtractedSegment] = []
    for row in rows:
        raw_text = str(row.get("text") or "").strip()
        normalized = _normalize_text(raw_text)
        if not normalized:
            continue
        page = str(row.get("page") or row.get("page_number") or "0")
        confidence = _extract_ocr_confidence(row)
        flags = [
            "existing_ocr_page",
            f"ocr_confidence:{confidence:.1f}",
        ]
        likely_language = guess_language(normalized, source_path=source_path)
        extracted_rows.append(
            {
                "source_id": f"source:{_slugify(_canonical_stem(source_path))}",
                "source_path": source_path,
                "page_or_image": page,
                "raw_text": raw_text,
                "normalized_text": normalized,
                "extraction_method": "existing_ocr_jsonl",
                "confidence_or_quality_flags": flags,
                "likely_language": likely_language,
                "checksum": _sha256_text(normalized),
                "provenance": {
                    "ocr_file": row.get("ocr_file"),
                    "ocr_engine": row.get("engine") or "tesseract",
                    "ocr_psm": row.get("psm"),
                },
            }
        )
        segments.append(
            ExtractedSegment(
                source_path=source_path,
                segment_id=f"{_slugify(Path(source_path).stem)}-ocr-page-{int(page):04d}",
                text=raw_text,
                normalized_text=normalized,
                likely_language=likely_language,
                page_or_image=page,
                extraction_method="existing_ocr_jsonl",
                support_type="direct_support",
                confidence_flags=flags,
            )
        )
    return extracted_rows, segments


def _page_rows_from_pdftotext(source_path: str, pdf_path: Path) -> tuple[list[dict[str, Any]], list[ExtractedSegment]]:
    extracted_rows: list[dict[str, Any]] = []
    segments: list[ExtractedSegment] = []
    for page_num, page_text in enumerate(_pdftotext_pages(pdf_path), start=1):
        normalized = _normalize_text(page_text)
        if not normalized:
            continue
        flags = ["pdftotext_layout"]
        if len(normalized) < 80:
            flags.append("low_text_density")
        likely_language = guess_language(normalized, source_path=source_path)
        extracted_rows.append(
            {
                "source_id": f"source:{_slugify(_canonical_stem(source_path))}",
                "source_path": source_path,
                "page_or_image": str(page_num),
                "raw_text": page_text,
                "normalized_text": normalized,
                "extraction_method": "pdftotext_layout",
                "confidence_or_quality_flags": flags,
                "likely_language": likely_language,
                "checksum": _sha256_text(normalized),
                "provenance": {
                    "page_number": page_num,
                    "page_count": _pdf_page_count(pdf_path),
                },
            }
        )
        segments.append(
            ExtractedSegment(
                source_path=source_path,
                segment_id=f"{_slugify(Path(source_path).stem)}-page-{page_num:04d}",
                text=page_text,
                normalized_text=normalized,
                likely_language=likely_language,
                page_or_image=str(page_num),
                extraction_method="pdftotext_layout",
                support_type="direct_support",
                confidence_flags=flags,
            )
        )
    return extracted_rows, segments


def _image_rows_from_tesseract(source_path: str, image_path: Path) -> tuple[list[dict[str, Any]], list[ExtractedSegment]]:
    raw_text = _ocr_image_text(image_path)
    if not raw_text:
        return [], []
    normalized = _normalize_text(raw_text)
    if not normalized:
        return [], []
    likely_language = guess_language(normalized, source_path=source_path)
    page_or_image = image_path.name
    flags = ["tesseract_image_ocr", "ocr_confidence:unknown"]
    extracted = {
        "source_id": f"source:{_slugify(_canonical_stem(source_path))}",
        "source_path": source_path,
        "page_or_image": page_or_image,
        "raw_text": raw_text,
        "normalized_text": normalized,
        "extraction_method": "tesseract_image_ocr",
        "confidence_or_quality_flags": flags,
        "likely_language": likely_language,
        "checksum": _sha256_text(normalized),
        "provenance": {
            "image_name": image_path.name,
        },
    }
    segment = ExtractedSegment(
        source_path=source_path,
        segment_id=f"{_slugify(Path(source_path).stem)}-{_slugify(image_path.name)}",
        text=raw_text,
        normalized_text=normalized,
        likely_language=likely_language,
        page_or_image=page_or_image,
        extraction_method="tesseract_image_ocr",
        support_type="direct_support",
        confidence_flags=flags,
    )
    return [extracted], [segment]


def _segments_from_page_rows(
    source_path: str,
    page_rows: list[ExtractedSegment],
    *,
    min_segment_chars: int,
) -> list[ExtractedSegment]:
    segments: list[ExtractedSegment] = []
    for row in page_rows:
        parts = [
            _normalize_text(part)
            for part in re.split(r"\n\s*\n", row.text)
            if _normalize_text(part)
        ]
        if not parts:
            parts = [_normalize_text(row.text)]
        for part_index, part in enumerate(parts, start=1):
            if len(part) < min_segment_chars:
                continue
            segments.append(
                ExtractedSegment(
                    source_path=source_path,
                    segment_id=f"{row.segment_id}-seg-{part_index:02d}",
                    text=part,
                    normalized_text=part,
                    likely_language=guess_language(part, source_path=source_path),
                    page_or_image=row.page_or_image,
                    extraction_method=row.extraction_method,
                    support_type=row.support_type,
                    confidence_flags=row.confidence_flags,
                )
            )
    return segments


def _clean_ocr_line(line: str) -> str:
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    line = line.strip("-=~_ ")
    return line


def _is_heading_line(line: str) -> bool:
    words = WORD_RE.findall(line)
    if not (3 <= len(words) <= 18):
        return False
    letters = [char for char in line if char.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(char.isupper() for char in letters) / len(letters)
    return upper_ratio >= 0.45 or line == line.upper()


def _recover_news_articles(
    source_path: str,
    page_rows: list[ExtractedSegment],
    *,
    max_articles: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    articles: list[dict[str, Any]] = []
    recovered_segments: list[dict[str, Any]] = []
    current_blocks: list[tuple[int, str]] = []
    current_title: str | None = None
    article_index = 0

    def flush_article() -> None:
        nonlocal current_blocks, current_title, article_index
        if not current_blocks:
            return
        article_index += 1
        if article_index > max_articles:
            current_blocks = []
            current_title = None
            return
        page_range = [current_blocks[0][0], current_blocks[-1][0]]
        tvl_parts: list[str] = []
        en_parts: list[str] = []
        segments: list[dict[str, Any]] = []
        for seg_index, (page_num, block_text) in enumerate(current_blocks, start=1):
            lang = guess_language(block_text, source_path=source_path)
            if lang == "tvl" or (lang == "mixed" and _tvl_ratio(block_text) >= 0.5):
                tvl_parts.append(block_text)
            elif lang == "en":
                en_parts.append(block_text)
            else:
                if _tvl_ratio(block_text) >= 0.4:
                    tvl_parts.append(block_text)
                else:
                    en_parts.append(block_text)
            segment_id = f"{_slugify(Path(source_path).stem)}-art-{article_index:03d}-seg-{seg_index:02d}"
            segments.append({"segment_id": segment_id, "text": block_text})
            recovered_segments.append(
                {
                    "segment_id": segment_id,
                    "article_id": f"ocr_news:{_canonical_stem(source_path)}:{article_index:03d}",
                    "source_path": source_path,
                    "page_or_image": str(page_num),
                    "raw_text": block_text,
                    "normalized_text": _normalize_text(block_text),
                    "extraction_method": "article_recovery_v1",
                    "confidence_or_quality_flags": ["auto_recovered_article"],
                    "likely_language": guess_language(block_text, source_path=source_path),
                    "checksum": _sha256_text(block_text),
                    "provenance": {"page_number": page_num},
                }
            )
        tvl_text = _normalize_text("\n\n".join(tvl_parts))
        en_text = _normalize_text("\n\n".join(en_parts))
        if len(tvl_text) < 100:
            current_blocks = []
            current_title = None
            return
        layout_type = "bilingual_mixed_page" if en_text else "single_language_page"
        article_id = f"ocr_news:{_canonical_stem(source_path)}:{article_index:03d}"
        title = current_title or _headline_from_text(tvl_text, fallback=Path(source_path).stem)
        articles.append(
            {
                "article_id": article_id,
                "source_scan": source_path,
                "page_range": page_range,
                "layout_type": layout_type,
                "language_profile": "tvl_primary" if not en_text else "mixed_with_tvl_primary",
                "tvl_text": tvl_text,
                "en_text": en_text,
                "segments": segments,
                "ocr_confidence": "medium",
                "recovery_method": "heading_and_language_block_recovery_v1",
                "qa_status": "auto_recovered",
                "title": title,
                "metadata": {
                    "created_at": _as_iso_timestamp(),
                    "source_path": source_path,
                },
            }
        )
        current_blocks = []
        current_title = None

    for page_row in page_rows:
        page_num = int(page_row.page_or_image)
        lines = [_clean_ocr_line(line) for line in page_row.text.splitlines()]
        lines = [line for line in lines if line and not NOISY_LINE_RE.match(line)]
        if not lines:
            continue
        current_block: list[str] = []
        for line in lines:
            if _is_heading_line(line):
                if current_block:
                    current_blocks.append((page_num, " ".join(current_block).strip()))
                    current_block = []
                if current_blocks:
                    flush_article()
                current_title = line
                continue
            if line.lower().startswith("page "):
                if current_block:
                    current_blocks.append((page_num, " ".join(current_block).strip()))
                    current_block = []
                continue
            current_block.append(line)
            if line.endswith((".", "!", "?")) and len(" ".join(current_block)) >= 220:
                current_blocks.append((page_num, " ".join(current_block).strip()))
                current_block = []
        if current_block:
            current_blocks.append((page_num, " ".join(current_block).strip()))
        if current_blocks and current_title:
            flush_article()
        elif current_blocks and len(current_blocks) >= 2:
            flush_article()
    flush_article()
    return articles, recovered_segments


def _bundle_from_segments(
    *,
    doc_id: str,
    source_path: str,
    source_family: str,
    segments: list[ExtractedSegment],
    title: str | None = None,
    grounding_level: str = "direct_text",
) -> dict[str, Any]:
    usable = [segment for segment in segments if len(segment.normalized_text) >= 40]
    if not usable:
        return {}
    joined_text = "\n\n".join(segment.normalized_text for segment in usable)
    return {
        "doc_id": doc_id,
        "source_path": source_path,
        "source_family": source_family,
        "title": title or _title_from_source(source_path, joined_text),
        "segments": usable,
        "text": joined_text,
        "language_profile": "tvl_primary" if _tvl_ratio(joined_text) >= 0.55 else "mixed",
        "domains": _broad_domain(source_family, source_path),
        "content_kind": _content_kind(source_family),
        "grounding_level": grounding_level,
    }


def _bundle_tvl_segments(bundle: dict[str, Any]) -> list[ExtractedSegment]:
    """Return the TVL-rich segment subset used for default Stage C grounding."""
    tvl_segments: list[ExtractedSegment] = []
    source_hint = bundle["source_path"].lower()
    force_tvl_bias = any(token in source_hint for token in ("tuvaluan", "_tvl", "tuv_", "nanumea", "childrens books"))
    for segment in bundle["segments"]:
        language = guess_language(segment.normalized_text, source_path=bundle["source_path"])
        ratio = _tvl_ratio(segment.normalized_text)
        if language == "tvl":
            tvl_segments.append(segment)
            continue
        if language == "mixed" and ratio >= 0.55:
            tvl_segments.append(segment)
            continue
        if force_tvl_bias and language != "en" and ratio >= 0.25:
            tvl_segments.append(segment)
    return tvl_segments


def _bundle_tvl_text(bundle: dict[str, Any]) -> str:
    return _normalize_text("\n\n".join(segment.normalized_text for segment in _bundle_tvl_segments(bundle)))


def _build_doc_bundles(
    *,
    source_manifest: list[dict[str, Any]],
    stage_a_segments: dict[str, list[ExtractedSegment]],
    ocr_page_segments: dict[str, list[ExtractedSegment]],
    raw_page_segments: dict[str, list[ExtractedSegment]],
    ocr_articles: list[dict[str, Any]],
    min_segment_chars: int,
) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    manifest_lookup = {row["source_path"]: row for row in source_manifest}

    for article in ocr_articles:
        source_path = str(article["source_scan"])
        segments = [
            ExtractedSegment(
                source_path=source_path,
                segment_id=segment["segment_id"],
                text=segment["text"],
                normalized_text=_normalize_text(segment["text"]),
                likely_language=guess_language(segment["text"], source_path=source_path),
                page_or_image=str(article["page_range"][0]),
                extraction_method="article_recovery_v1",
                support_type="direct_support",
                confidence_flags=["auto_recovered_article"],
            )
            for segment in article["segments"]
            if guess_language(segment["text"], source_path=source_path) != "en"
            or _tvl_ratio(segment["text"]) >= 0.45
        ]
        bundle = _bundle_from_segments(
            doc_id=f"native_doc:{_canonical_stem(source_path)}:{article['article_id'].split(':')[-1]}",
            source_path=source_path,
            source_family="historic_news_scan",
            segments=segments,
            title=article.get("title"),
            grounding_level="ocr_recovered_article",
        )
        if bundle:
            bundle["page_range"] = article["page_range"]
            bundle["paired_en_text"] = article.get("en_text") or None
            bundles.append(bundle)

    used_sources = {bundle["source_path"] for bundle in bundles if bundle.get("grounding_level") == "ocr_recovered_article"}

    for source_path, segments in stage_a_segments.items():
        family = manifest_lookup.get(source_path, {}).get("source_family", _source_family_for_path(source_path))
        bundle = _bundle_from_segments(
            doc_id=f"native_doc:{_canonical_stem(source_path)}",
            source_path=source_path,
            source_family=family,
            segments=segments,
            grounding_level="seed_aligned_segments",
        )
        if bundle:
            bundles.append(bundle)

    for source_path, page_segments in raw_page_segments.items():
        if source_path in stage_a_segments or source_path in used_sources:
            continue
        family = manifest_lookup.get(source_path, {}).get("source_family", _source_family_for_path(source_path))
        segments = _segments_from_page_rows(
            source_path,
            page_segments,
            min_segment_chars=min_segment_chars,
        )
        bundle = _bundle_from_segments(
            doc_id=f"native_doc:{_canonical_stem(source_path)}",
            source_path=source_path,
            source_family=family,
            segments=segments,
            grounding_level="direct_text_pages",
        )
        if bundle:
            bundles.append(bundle)

    for source_path, page_segments in ocr_page_segments.items():
        if source_path in stage_a_segments or source_path in used_sources or source_path in raw_page_segments:
            continue
        family = manifest_lookup.get(source_path, {}).get("source_family", _source_family_for_path(source_path))
        segments = _segments_from_page_rows(
            source_path,
            page_segments,
            min_segment_chars=min_segment_chars,
        )
        bundle = _bundle_from_segments(
            doc_id=f"native_doc:{_canonical_stem(source_path)}",
            source_path=source_path,
            source_family=family,
            segments=segments,
            grounding_level="ocr_page_segments",
        )
        if bundle:
            bundles.append(bundle)

    bundles.sort(key=lambda bundle: bundle["doc_id"])
    return bundles


def _build_doc_registry(
    *,
    repo_root: Path,
    source_manifest: list[dict[str, Any]],
    doc_bundles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest_lookup = {row["source_path"]: row for row in source_manifest}
    registry: list[dict[str, Any]] = []

    for bundle in doc_bundles:
        source_path = bundle["source_path"]
        source_file = repo_root / source_path
        manifest_row = manifest_lookup.get(source_path, {})
        text = bundle["text"]
        tvl_text = _bundle_tvl_text(bundle)
        ocr_quality = "medium" if "ocr" in bundle["grounding_level"] else "high"
        ingest_status = _ingest_status(
            bundle["source_family"],
            manifest_row.get("status_guess", "Raw-only"),
            len(bundle["segments"]),
        )
        if tvl_text and guess_language(tvl_text, source_path=source_path) == "en":
            ingest_status = "support_only"
        if not tvl_text:
            ingest_status = "candidate_only"
        registry.append(
            {
                "doc_id": bundle["doc_id"],
                "source_path": source_path,
                "source_family": bundle["source_family"],
                "title": bundle["title"],
                "language_profile": bundle["language_profile"],
                "domains": bundle["domains"],
                "content_kind": bundle["content_kind"],
                "text_quality": {
                    "ocr_quality": ocr_quality,
                    "normalization_status": "normalized_v1",
                    "language_confidence": guess_language(text, source_path=source_path),
                },
                "grounding_level": bundle["grounding_level"],
                "copyright_status": _copyright_status(bundle["source_family"], source_path),
                "ingest_status": ingest_status,
                "segment_count": len(bundle["segments"]),
                "holdout_eligible": bool(manifest_row.get("holdout_candidate", True) and tvl_text),
                "notes": manifest_row.get("notes", ""),
                "metadata": {
                    "page_start": min(int(seg.page_or_image.split("-")[0]) for seg in bundle["segments"] if str(seg.page_or_image).isdigit()) if any(str(seg.page_or_image).isdigit() for seg in bundle["segments"]) else None,
                    "page_end": max(int(seg.page_or_image.split("-")[0]) for seg in bundle["segments"] if str(seg.page_or_image).isdigit()) if any(str(seg.page_or_image).isdigit() for seg in bundle["segments"]) else None,
                    "source_hash": f"sha256:{hash_file(source_file)}" if source_file.exists() else None,
                    "created_at": _as_iso_timestamp(),
                    "source_size_bytes": source_file.stat().st_size if source_file.exists() else None,
                },
            }
        )
    registry.sort(key=lambda row: row["doc_id"])
    return registry


def _doc_holdout_slice(bundle: dict[str, Any]) -> str:
    source_family = bundle["source_family"]
    if "ocr" in bundle["grounding_level"]:
        return "ocr_noisy_after_cleanup"
    if source_family == "historic_news_scan":
        return "news"
    if source_family in {"government_pdf", "health_pdf", "finance_pdf", "education_pdf"}:
        return "government_civic"
    if source_family in {"children_book", "oral_traditional_material"}:
        return "cultural_narrative"
    if bundle["domains"] == ["lexical"]:
        return "terminology_entity_preservation"
    return "mixed_prompt_requests"


def _select_holdout_doc_ids(
    bundles: list[dict[str, Any]],
    *,
    holdout_fraction: float,
) -> set[str]:
    eligible = [
        bundle
        for bundle in bundles
        if bundle.get("content_kind") != "media_asset" and _bundle_tvl_text(bundle)
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for bundle in eligible:
        grouped[_doc_holdout_slice(bundle)].append(bundle)
    selected: set[str] = set()
    for slice_name, items in grouped.items():
        items = sorted(items, key=lambda bundle: _stable_hash(bundle["doc_id"]))
        quota = max(1, round(len(items) * holdout_fraction))
        for bundle in items[:quota]:
            selected.add(bundle["doc_id"])
    return selected


def _prompt_text(
    *,
    task_family: str,
    prompt_origin: str,
    title: str,
    facts: list[str],
) -> tuple[str, str]:
    tvl_native = {
        "native_request_article": "Tuku mai te tala tenei i te Tuvaluan.",
        "english_request_tvl_answer": "Respond in Tuvaluan with the full article text from the source.",
        "mixed_request_tvl_answer": "Tuku mai te article tenei in Tuvaluan, kae stay faithful ki te source.",
        "fact_sheet_to_article": "Fakaaoga a manatu konei kae tuku mai te tala i te Tuvaluan:\n\n" + "\n".join(f"- {fact}" for fact in facts),
        "headline_generation": "Tuku mai se ulutala puupuu mo tonu mo te tala tenei.",
        "lead_generation": "Tuku mai te opening paragraph muamua o te tala tenei.",
        "summary_short": "Fakatoetoefaka faiga puupuu te tala tenei i te Tuvaluan.",
        "summary_medium": "Fakatoetoefaka te tala tenei i te Tuvaluan i se aotelega malama.",
        "qa_grounded": f"Se a te ulutala tonu o te tala tenei e uiga ki {title}?",
        "entity_extraction": "Lisi mai igoa, koga, aso, mo aofaki tāua mai i te mataupu tenei.",
        "quote_preservation": "Toe tuku mai te pati tonu telā e fakasino ki te puna lenei.",
        "radio_rewrite": "Fakatuu te tala tenei e pelā me se fakasalalauga leitio i te Tuvaluan.",
        "formal_rewrite": "Toe tuku mai te mataupu tenei i se aga aloaia i te Tuvaluan.",
        "plain_language_rewrite": "Fakamatalaga faigofie te mataupu tenei i te Tuvaluan faigofie.",
        "translation_to_english": "Translate this Tuvaluan source faithfully into English.",
        "explain_in_english": "Explain the key point of this Tuvaluan source in English.",
    }
    english = {
        "native_request_article": "Write the full article in Tuvaluan, using the source text faithfully.",
        "english_request_tvl_answer": "Give the grounded answer in Tuvaluan and stay faithful to the source.",
        "mixed_request_tvl_answer": "Answer in Tuvaluan, but keep the source facts exact.",
        "fact_sheet_to_article": "Turn these fact bullets into the source-faithful Tuvaluan article:\n\n" + "\n".join(f"- {fact}" for fact in facts),
        "headline_generation": "Provide the source-faithful Tuvaluan headline only.",
        "lead_generation": "Provide only the opening lead paragraph in Tuvaluan.",
        "summary_short": "Give a short Tuvaluan summary grounded in the source.",
        "summary_medium": "Give a medium-length Tuvaluan summary grounded in the source.",
        "qa_grounded": f"What is the exact source-grounded answer about {title}? Answer in Tuvaluan.",
        "entity_extraction": "List the important names, places, dates, and amounts from the source.",
        "quote_preservation": "Return the quoted line exactly as it appears in the source.",
        "radio_rewrite": "Rewrite this for radio in natural Tuvaluan while staying source-faithful.",
        "formal_rewrite": "Rewrite this in formal Tuvaluan while preserving all entities and facts.",
        "plain_language_rewrite": "Rewrite this in plain Tuvaluan for a general reader.",
        "translation_to_english": "Translate the grounded Tuvaluan source into English.",
        "explain_in_english": "Explain the Tuvaluan source in English for a non-Tuvaluan reader.",
    }
    mixed = {
        "native_request_article": "Tuku mai te full article in Tuvaluan, kae keep the source exact.",
        "english_request_tvl_answer": "Answer in Tuvaluan, kae preserve names mo dates from the source.",
        "mixed_request_tvl_answer": "Tuku mai te grounded answer in Tuvaluan.",
        "fact_sheet_to_article": "Fakaaoga a fact bullets konei and write the Tuvaluan article:\n\n" + "\n".join(f"- {fact}" for fact in facts),
        "headline_generation": "Tuku mai te headline only, i te Tuvaluan.",
        "lead_generation": "Tuku mai te lead paragraph first, i te Tuvaluan.",
        "summary_short": "Fakatoetoefaka short te source nei i te Tuvaluan.",
        "summary_medium": "Fakatoetoefaka medium te source nei i te Tuvaluan.",
        "qa_grounded": f"Se a te exact answer e uiga ki {title}? Answer in Tuvaluan.",
        "entity_extraction": "Lisi mai entities tāua from the source.",
        "quote_preservation": "Toe tuku mai te quote tonu from the source.",
        "radio_rewrite": "Fakatuu te source nei mo radio i te Tuvaluan.",
        "formal_rewrite": "Toe tusi te source nei i se register formal Tuvaluan.",
        "plain_language_rewrite": "Fakamatalaga faigofie te source nei i te Tuvaluan.",
        "translation_to_english": "Translate te grounded Tuvaluan source into English.",
        "explain_in_english": "Explain te main point of te Tuvaluan source in English.",
    }
    stage_b_translated = {
        "native_request_article": "Tuku mai te article katoa i te Tuvaluan, kae tumau ki mea tonu mai te source.",
        "english_request_tvl_answer": "Tuku mai te tali i te Tuvaluan kae tausi tonu igoa, aso mo fuainumela.",
        "mixed_request_tvl_answer": "Fai te tali i te Tuvaluan, kae aua e toe fakafou ni mea seki i te source.",
        "fact_sheet_to_article": "Mai i manatu konei, tusi te article i te Tuvaluan i se auala tumau ki te source:\n\n" + "\n".join(f"- {fact}" for fact in facts),
        "headline_generation": "Tuku mai fua te ulutala i te Tuvaluan.",
        "lead_generation": "Tuku mai fua te lead paragraph muamua i te Tuvaluan.",
        "summary_short": "Tuku mai se aotelega puupuu i te Tuvaluan e tumau ki te source.",
        "summary_medium": "Tuku mai se aotelega malama i te Tuvaluan e tumau ki te source.",
        "qa_grounded": f"Tuku mai te tali tonu mai te source e uiga ki {title}.",
        "entity_extraction": "Lisi mai igoa, koga, aso mo aofaki tāua.",
        "quote_preservation": "Toe tuku mai te quote tonu e maua i te source.",
        "radio_rewrite": "Fakatuu te source tenei e pelā me se tala leitio i te Tuvaluan.",
        "formal_rewrite": "Toe tusi te source tenei i se uiga aloaia i te Tuvaluan.",
        "plain_language_rewrite": "Fakamatalaga faigofie te source tenei i te Tuvaluan faigofie.",
        "translation_to_english": "Fuli faka-Peretania te source Tuvaluan tenei.",
        "explain_in_english": "Fakamatala i te English te manatu tāua o te source Tuvaluan tenei.",
    }
    prompt_sets = {
        "native": tvl_native,
        "english": english,
        "mixed": mixed,
        "stage_b_translated": stage_b_translated,
    }
    prompt_map = prompt_sets[prompt_origin]
    prompt_lang = {
        "native": "tvl",
        "english": "en",
        "mixed": "mixed",
        "stage_b_translated": "tvl",
    }[prompt_origin]
    return prompt_map[task_family], prompt_lang


def _build_grounded_example(
    *,
    bundle: dict[str, Any],
    task_family: str,
    prompt_origin: str,
    answer: str,
    source_segments: list[ExtractedSegment],
    answer_origin: str,
    support_type: str,
    assistant_lang: str,
    user_text: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prompt_mode = {
        "native": "native_tvl_user",
        "english": "english_user_tvl_answer",
        "mixed": "mixed_user_tvl_answer",
        "stage_b_translated": "stage_b_translated_tvl_mirror",
    }[prompt_origin]
    system_prompt = SYSTEM_PROMPT_TVL if assistant_lang == "tvl" else SYSTEM_PROMPT_EN
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": answer},
    ]
    return {
        "id": f"grounded_sft:{bundle['doc_id']}:{task_family}:{prompt_mode}:{_slugify(source_segments[0].segment_id)}",
        "source_doc_id": bundle["doc_id"],
        "task_family": task_family,
        "prompt_mode": prompt_mode,
        "prompt_lang": {
            "native": "tvl",
            "english": "en",
            "mixed": "mixed",
            "stage_b_translated": "tvl",
        }[prompt_origin],
        "prompt_origin": prompt_origin,
        "assistant_lang": assistant_lang,
        "source_segments": [segment.segment_id for segment in source_segments],
        "source_spans": [segment.page_or_image for segment in source_segments],
        "support_type": support_type,
        "answer_origin": answer_origin,
        "messages": messages,
        "user": user_text,
        "assistant": answer,
        "provenance": {
            "source_path": bundle["source_path"],
            "source_family": bundle["source_family"],
            "domains": bundle["domains"],
            "grounding_level": bundle["grounding_level"],
            **(metadata or {}),
        },
    }


def _build_grounded_tasks_for_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    segments = _bundle_tvl_segments(bundle)
    if not segments:
        return tasks
    text = _bundle_tvl_text(bundle)
    if not text:
        return tasks
    if guess_language(text, source_path=bundle["source_path"]) == "en":
        return tasks
    title = bundle["title"]
    assistant_lang = "tvl"
    full_answer = text
    headline = _headline_from_text(text, fallback=title)
    lead = _lead_from_text(text)
    summary_short = _summary_from_text(text, max_sentences=1)
    summary_medium = _summary_from_text(text, max_sentences=2)
    facts = _fact_bullets(text, limit=4)
    fact_answer = "\n".join(f"- {fact}" for fact in facts)
    entity_list = _extract_entities(text)
    if not entity_list:
        entity_list = _extract_numbers(text)[:4]
    entities_answer = "\n".join(f"- {item}" for item in entity_list[:8]) if entity_list else ""
    quote_answer = _quote_from_text(text)
    en_support = bundle.get("paired_en_text")
    if not en_support:
        paired_bits = [segment.paired_en_text for segment in segments if segment.paired_en_text]
        if paired_bits:
            en_support = _normalize_text("\n\n".join(paired_bits))

    for prompt_origin in ("native", "english", "mixed", "stage_b_translated"):
        for task_family, answer, answer_origin, support_type in [
            ("native_request_article", full_answer, "source_span", "direct_support"),
            ("english_request_tvl_answer", full_answer, "source_span", "direct_support"),
            ("mixed_request_tvl_answer", full_answer, "source_span", "direct_support"),
            ("fact_sheet_to_article", full_answer, "fact_to_source_article", "fact_compilation"),
            ("headline_generation", headline, "extractive_headline", "light_transform"),
            ("lead_generation", lead, "extractive_lead", "light_transform"),
            ("summary_short", summary_short, "extractive_summary_short", "light_transform"),
            ("summary_medium", summary_medium, "extractive_summary_medium", "light_transform"),
            ("qa_grounded", headline, "extractive_answer", "direct_support"),
            ("entity_extraction", entities_answer, "entity_list", "fact_compilation"),
            ("radio_rewrite", summary_medium, "broadcast_extract", "light_transform"),
            ("formal_rewrite", full_answer if bundle["source_family"] in {"government_pdf", "health_pdf", "finance_pdf", "education_pdf"} else summary_medium, "formal_source_preserving", "light_transform"),
            ("plain_language_rewrite", fact_answer or summary_short, "plain_language_extract", "light_transform"),
        ]:
            if not answer:
                continue
            user_text, _prompt_lang = _prompt_text(
                task_family=task_family,
                prompt_origin=prompt_origin,
                title=title,
                facts=facts,
            )
            tasks.append(
                _build_grounded_example(
                    bundle=bundle,
                    task_family=task_family,
                    prompt_origin=prompt_origin,
                    answer=answer,
                    source_segments=segments[: min(4, len(segments))],
                    answer_origin=answer_origin,
                    support_type=support_type,
                    assistant_lang=assistant_lang,
                    user_text=user_text,
                    metadata={"register": bundle["content_kind"]},
                )
            )

        if quote_answer:
            user_text, _ = _prompt_text(
                task_family="quote_preservation",
                prompt_origin=prompt_origin,
                title=title,
                facts=facts,
            )
            tasks.append(
                _build_grounded_example(
                    bundle=bundle,
                    task_family="quote_preservation",
                    prompt_origin=prompt_origin,
                    answer=quote_answer,
                    source_segments=segments[: min(4, len(segments))],
                    answer_origin="quote_exact",
                    support_type="direct_support",
                    assistant_lang="tvl" if guess_language(quote_answer, source_path=bundle["source_path"]) != "en" else "en",
                    user_text=user_text,
                    metadata={"quote_preserved": True},
                )
            )

        if en_support:
            for task_family, answer_origin in [
                ("translation_to_english", "paired_english_support"),
                ("explain_in_english", "paired_english_explanation"),
            ]:
                user_text, _ = _prompt_text(
                    task_family=task_family,
                    prompt_origin=prompt_origin,
                    title=title,
                    facts=facts,
                )
                answer = _summary_from_text(en_support, max_sentences=2) if task_family == "explain_in_english" else en_support
                tasks.append(
                    _build_grounded_example(
                        bundle=bundle,
                        task_family=task_family,
                        prompt_origin=prompt_origin,
                        answer=answer,
                        source_segments=segments[: min(4, len(segments))],
                        answer_origin=answer_origin,
                        support_type="fact_compilation",
                        assistant_lang="en",
                        user_text=user_text,
                        metadata={"paired_english_available": True},
                    )
                )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for task in tasks:
        key = (
            task["task_family"],
            _normalize_text(task["user"]).lower(),
            _normalize_text(task["assistant"]).lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(task)
    return deduped


def _build_news_article_tasks(bundles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for bundle in bundles:
        if bundle["source_family"] != "historic_news_scan":
            continue
        tasks = _build_grounded_tasks_for_bundle(bundle)
        for task in tasks:
            if task["task_family"] in {
                "native_request_article",
                "english_request_tvl_answer",
                "mixed_request_tvl_answer",
                "headline_generation",
                "lead_generation",
                "summary_short",
                "summary_medium",
                "fact_sheet_to_article",
                "entity_extraction",
            }:
                row = dict(task)
                row["id"] = row["id"].replace("grounded_sft:", "news_article_task:")
                rows.append(row)
    rows.sort(key=lambda row: row["id"])
    return rows


def _build_prompt_mirrors(grounded_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mirrors: list[dict[str, Any]] = []
    seen_prompts: set[tuple[str, str, str]] = set()
    for row in grounded_rows:
        if row["assistant_lang"] != "tvl":
            continue
        source_doc_id = row["source_doc_id"]
        for prompt_origin in ("native", "english", "mixed", "stage_b_translated"):
            if row.get("prompt_origin") == prompt_origin:
                continue
            facts = _fact_bullets(row["assistant"], limit=3)
            user_text, prompt_lang = _prompt_text(
                task_family=row["task_family"],
                prompt_origin=prompt_origin,
                title=row["provenance"].get("source_path", source_doc_id),
                facts=facts,
            )
            normalized_prompt = _normalize_text(user_text).lower()
            if len(normalized_prompt) < 12:
                continue
            key = (source_doc_id, row["task_family"], normalized_prompt)
            if key in seen_prompts:
                continue
            seen_prompts.add(key)
            mirror = dict(row)
            mirror["id"] = row["id"].replace("grounded_sft:", "grounded_mirror:")
            mirror["id"] += f":{prompt_origin}"
            mirror["prompt_mode"] = {
                "native": "native_tvl_user",
                "english": "english_user_tvl_answer",
                "mixed": "mixed_user_tvl_answer",
                "stage_b_translated": "stage_b_translated_tvl_mirror",
            }[prompt_origin]
            mirror["prompt_lang"] = prompt_lang
            mirror["prompt_origin"] = prompt_origin
            mirror["messages"] = [
                dict(row["messages"][0]),
                {"role": "user", "content": user_text},
                dict(row["messages"][-1]),
            ]
            mirror["user"] = user_text
            mirror["provenance"] = {
                **row["provenance"],
                "mirror_of": row["id"],
                "mirror_filter_status": "accepted",
            }
            mirrors.append(mirror)
    mirrors.sort(key=lambda row: row["id"])
    return mirrors


def _build_entity_rows(bundles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    entities: list[dict[str, Any]] = []
    glossary: list[dict[str, Any]] = []
    constrained_tasks: list[dict[str, Any]] = []
    variant_clusters: dict[str, set[str]] = defaultdict(set)

    for bundle in bundles:
        text = bundle["text"]
        segment_ids = [segment.segment_id for segment in bundle["segments"][:4]]
        entity_candidates = _extract_entities(text)
        date_candidates = _extract_dates(text)
        number_candidates = _extract_numbers(text)

        for entity in entity_candidates[:24]:
            normalized = re.sub(r"[^A-Za-zĀĒĪŌŪāēīōū]+", "", entity).lower()
            variant_clusters[normalized].add(entity)
            entity_type = "place" if entity.lower() in ISLAND_HINTS else "named_entity"
            if "ministry" in entity.lower() or "matagaluega" in entity.lower():
                entity_type = "institution"
            entities.append(
                {
                    "id": f"entity:{bundle['doc_id']}:{_slugify(entity)}",
                    "source_doc_id": bundle["doc_id"],
                    "source_path": bundle["source_path"],
                    "entity": entity,
                    "entity_type": entity_type,
                    "domains": bundle["domains"],
                    "orthographic_variant_key": normalized,
                    "evidence_segments": segment_ids,
                    "likely_language": guess_language(entity, source_path=bundle["source_path"]),
                }
            )

        for date_value in date_candidates[:12]:
            glossary.append(
                {
                    "id": f"glossary:{bundle['doc_id']}:{_slugify(date_value)}",
                    "source_doc_id": bundle["doc_id"],
                    "candidate": date_value,
                    "candidate_type": "date",
                    "domains": bundle["domains"],
                    "evidence_segments": segment_ids,
                    "notes": "Date or year span preserved from source.",
                }
            )
        for number_value in number_candidates[:12]:
            glossary.append(
                {
                    "id": f"glossary:{bundle['doc_id']}:{_slugify(number_value)}",
                    "source_doc_id": bundle["doc_id"],
                    "candidate": number_value,
                    "candidate_type": "amount_or_number",
                    "domains": bundle["domains"],
                    "evidence_segments": segment_ids,
                    "notes": "Numeric value preserved from source.",
                }
            )

        if entity_candidates:
            answer = "\n".join(f"- {entity}" for entity in entity_candidates[:8])
            constrained_tasks.append(
                {
                    "id": f"constrained:{bundle['doc_id']}:span_tagging",
                    "source_doc_id": bundle["doc_id"],
                    "task_family": "span_tagging",
                    "constraint_type": "entity_preserving_rewrite",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_TVL},
                        {"role": "user", "content": "Lisi mai igoa mo koga tāua mai i te source nei kae aua e sui."},
                        {"role": "assistant", "content": answer},
                    ],
                    "assistant": answer,
                    "user": "Lisi mai igoa mo koga tāua mai i te source nei kae aua e sui.",
                    "provenance": {
                        "source_path": bundle["source_path"],
                        "source_segments": segment_ids,
                    },
                }
            )

        if date_candidates or number_candidates:
            answer = "\n".join(f"- {item}" for item in (date_candidates[:4] + number_candidates[:4]))
            constrained_tasks.append(
                {
                    "id": f"constrained:{bundle['doc_id']}:amount_date_preservation",
                    "source_doc_id": bundle["doc_id"],
                    "task_family": "amount_date_preservation",
                    "constraint_type": "amount_date_preservation",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_TVL},
                        {"role": "user", "content": "Toe tuku mai aso mo aofaki kolā e se mafai o sui."},
                        {"role": "assistant", "content": answer},
                    ],
                    "assistant": answer,
                    "user": "Toe tuku mai aso mo aofaki kolā e se mafai o sui.",
                    "provenance": {
                        "source_path": bundle["source_path"],
                        "source_segments": segment_ids,
                    },
                }
            )

        quote_value = _quote_from_text(text)
        if quote_value:
            constrained_tasks.append(
                {
                    "id": f"constrained:{bundle['doc_id']}:quote_preservation",
                    "source_doc_id": bundle["doc_id"],
                    "task_family": "quote_preservation",
                    "constraint_type": "quote_completion",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT_TVL},
                        {"role": "user", "content": "Toe tuku mai te quote tonu mai te source nei."},
                        {"role": "assistant", "content": quote_value},
                    ],
                    "assistant": quote_value,
                    "user": "Toe tuku mai te quote tonu mai te source nei.",
                    "provenance": {
                        "source_path": bundle["source_path"],
                        "source_segments": segment_ids,
                    },
                }
            )

    for key, variants in sorted(variant_clusters.items()):
        if len(variants) < 2:
            continue
        glossary.append(
            {
                "id": f"glossary:variants:{key}",
                "source_doc_id": None,
                "candidate": sorted(variants)[0],
                "candidate_type": "orthographic_variant_cluster",
                "domains": ["lexical"],
                "evidence_segments": [],
                "notes": "Orthographic variants clustered for terminology control.",
                "variants": sorted(variants),
            }
        )

    entities.sort(key=lambda row: row["id"])
    glossary.sort(key=lambda row: row["id"])
    constrained_tasks.sort(key=lambda row: row["id"])
    return entities, glossary, constrained_tasks


def _make_preference_negative(
    row: dict[str, Any],
    *,
    paired_english: str | None,
) -> tuple[str, list[str]]:
    chosen = row["assistant"]
    tags: list[str] = []
    negative = chosen

    entities = _extract_entities(chosen)
    numbers = _extract_numbers(chosen)

    if paired_english:
        negative = _summary_from_text(paired_english, max_sentences=2)
        tags.append("wrong_language")
        tags.append("translationese")
    elif entities:
        entity = entities[0]
        negative = negative.replace(entity, "", 1).strip()
        tags.append("entity_drop")
    if numbers:
        negative = re.sub(NUMBER_RE, "", negative, count=1).strip()
        tags.append("dropped_numbers_dates")
    if negative == chosen:
        negative = chosen + " This extra sentence is not in the source."
        tags.append("unsupported_hallucination")
    if all(ord(char) < 128 for char in negative) and guess_language(negative, source_path=row["provenance"]["source_path"]) == "en":
        if "wrong_language" not in tags:
            tags.append("wrong_language")
    if "wrong_language" not in tags and paired_english is None:
        negative = negative + " Please note the original report."
        tags.append("english_leakage")
    return negative, tags


def _build_preferences(grounded_rows: list[dict[str, Any]], bundles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    preferences: list[dict[str, Any]] = []
    for row in grounded_rows:
        if row["assistant_lang"] != "tvl":
            continue
        if row["task_family"] not in {
            "summary_short",
            "summary_medium",
            "headline_generation",
            "radio_rewrite",
            "formal_rewrite",
            "plain_language_rewrite",
            "native_request_article",
        }:
            continue
        bundle = bundles.get(row["source_doc_id"])
        paired_english = None
        if bundle:
            paired_english = bundle.get("paired_en_text")
            if not paired_english:
                paired_bits = [
                    segment.paired_en_text
                    for segment in bundle["segments"]
                    if segment.paired_en_text
                ]
                if paired_bits:
                    paired_english = _normalize_text("\n\n".join(bit for bit in paired_bits if bit))
        rejected, tags = _make_preference_negative(row, paired_english=paired_english)
        if not rejected or rejected == row["assistant"]:
            continue
        preferences.append(
            {
                "id": f"pref:{row['source_doc_id']}:{row['task_family']}:{row['prompt_mode']}",
                "task_family": row["task_family"],
                "prompt_mode": row["prompt_mode"],
                "messages": row["messages"][:-1],
                "chosen": row["assistant"],
                "rejected": rejected,
                "preference_reason_tags": tags,
                "source_doc_id": row["source_doc_id"],
                "source_segments": row["source_segments"],
                "metadata": {
                    "pair_source": "controlled_negative_v1",
                    "source_path": row["provenance"]["source_path"],
                    "prompt_origin": row.get("prompt_origin"),
                },
            }
        )
    preferences.sort(key=lambda row: row["id"])
    return preferences


def _build_eval_items(
    *,
    bundles: list[dict[str, Any]],
    holdout_doc_ids: set[str],
) -> list[dict[str, Any]]:
    eval_rows: list[dict[str, Any]] = []
    for bundle in bundles:
        if bundle["doc_id"] not in holdout_doc_ids:
            continue
        text = _bundle_tvl_text(bundle)
        if not text:
            continue
        segments = _bundle_tvl_segments(bundle)
        facts = _fact_bullets(text, limit=3)
        for task_family, answer, slice_name in [
            ("summary_medium", _summary_from_text(text, max_sentences=2), _doc_holdout_slice(bundle)),
            ("headline_generation", _headline_from_text(text, fallback=bundle["title"]), _doc_holdout_slice(bundle)),
            ("entity_extraction", "\n".join(f"- {entity}" for entity in _extract_entities(text)[:6]), "terminology_entity_preservation"),
            ("radio_rewrite", _summary_from_text(text, max_sentences=2), "mixed_prompt_requests"),
        ]:
            if not answer:
                continue
            prompt, _lang = _prompt_text(
                task_family=task_family,
                prompt_origin="native",
                title=bundle["title"],
                facts=facts,
            )
            eval_rows.append(
                {
                    "id": f"eval:{bundle['doc_id']}:{task_family}",
                    "split": "held_out",
                    "slice": slice_name,
                    "task_family": task_family,
                    "prompt": prompt,
                    "reference_answer": answer,
                    "source_doc_id": bundle["doc_id"],
                    "source_segments": [segment.segment_id for segment in segments[:4]],
                    "source_segments_text": [segment.normalized_text for segment in segments[:4]],
                    "scoring_axes": [
                        "adequacy",
                        "in_language_fidelity",
                        "entity_preservation",
                        "style_fit",
                        "source_support",
                    ],
                    "metadata": {
                        "human_verified": False,
                        "source_path": bundle["source_path"],
                    },
                }
            )
    eval_rows.sort(key=lambda row: row["id"])
    return eval_rows


def _prompt_origin_allowed(row: dict[str, Any], arm: str) -> bool:
    prompt_origin = row.get("prompt_origin")
    if arm == "native_only":
        return prompt_origin == "native"
    if arm == "native_plus_english":
        return prompt_origin in {"native", "english"}
    if arm == "native_plus_stage_b_translated":
        return prompt_origin in {"native", "stage_b_translated"}
    if arm == "native_plus_bilingual":
        return prompt_origin in {"native", "english", "mixed", "stage_b_translated"}
    raise ValueError(f"Unknown Stage C arm: {arm}")


def _build_split_rows(
    rows: list[dict[str, Any]],
    *,
    holdout_doc_ids: set[str],
    val_fraction: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    val: list[dict[str, Any]] = []
    for row in rows:
        doc_id = row["source_doc_id"]
        if doc_id in holdout_doc_ids:
            continue
        bucket = _stable_hash(doc_id) % 10000
        if bucket < int(val_fraction * 10000):
            val.append(row)
        else:
            train.append(row)
    train.sort(key=lambda row: row["id"])
    val.sort(key=lambda row: row["id"])
    return train, val


def _full_pair_signature(row: dict[str, Any]) -> str:
    user_text = ""
    assistant_text = ""
    if row.get("messages"):
        user_text = "\n".join(msg["content"] for msg in row["messages"] if msg.get("role") == "user")
        assistant_text = "\n".join(msg["content"] for msg in row["messages"] if msg.get("role") == "assistant")
    else:
        user_text = row.get("user", "")
        assistant_text = row.get("assistant", row.get("chosen", ""))
    return _sha256_text(_normalize_text(user_text).lower() + "||" + _normalize_text(assistant_text).lower())


def _load_existing_signatures(*paths: Path) -> set[str]:
    signatures: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                signatures.add(_full_pair_signature(row))
    return signatures


def _dedupe_rows(rows: list[dict[str, Any]], *, existing_signatures: set[str]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen = set(existing_signatures)
    for row in rows:
        signature = _full_pair_signature(row)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(row)
    return deduped


def _count_by(rows: Iterable[dict[str, Any]], key_fn: Any) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        counter[str(key_fn(row))] += 1
    return dict(sorted(counter.items()))


def _write_markdown_report(path: Path, title: str, sections: list[tuple[str, list[str]]]) -> None:
    lines = [f"# {title}", ""]
    for heading, body_lines in sections:
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(body_lines)
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _build_repo_audit_report(
    *,
    repo_root: Path,
    reports_dir: Path,
) -> None:
    stage_b_manifest = read_json(repo_root / "data/finetune/stage_b_mix/manifest.json")
    stage_a_manifest = read_json(repo_root / "data/finetune/stage_a_mt/manifest.json")
    active_anchor = stage_b_manifest.get("config", {}).get("anchor_path")
    active_stage_a = "stage_a_mt_v2" if active_anchor and "stage_a_mt_v2" in str(active_anchor) else "stage_a_mt"
    sections = [
        (
            "Current Entrypoints",
            [
                "- `scripts/build_stage_a_mt_data.py` -> `tv/training/stage_a_mt/build_data.py`.",
                "- `scripts/train_stage_a_translation.py` and `scripts/eval_stage_a_translation.py` remain the Stage A train/eval entrypoints.",
                "- `scripts/build_stage_b_sources.py`, `scripts/generate_stage_b_synthetic_tvl.py`, and `scripts/build_stage_b_mix.py` are the live Stage B data builders.",
                "- `scripts/train_stage_b_agent.py` and `scripts/eval_stage_b_agent.py` are the live Stage B train/eval entrypoints.",
            ],
        ),
        (
            "Observed Active Dataset Usage",
            [
                f"- Latest `stage_a_mt` manifest exists at `data/finetune/stage_a_mt/manifest.json` with `{stage_a_manifest.get('accepted_rows', 'unknown')}` accepted rows.",
                f"- Latest `stage_b_mix` manifest anchors against `{active_anchor}`.",
                f"- Current Stage B training therefore uses `{active_stage_a}`, not `stage_a_mt_v2`, as its anchor path.",
                "- `data/finetune/stage_a_mt_v2/` exists, but current checked-in Stage B configs still point to `data/finetune/stage_a_mt/train_balanced.jsonl`.",
            ],
        ),
        (
            "Unstructured Builders",
            [
                "- `scripts/run_unstructured_datamining.py` orchestrates OCR/seed generation.",
                "- `scripts/ocr_scanned_pdfs.py` produces page-level OCR artifacts in `data/external/ocr_scans/`.",
                "- `scripts/build_unstructured_seed.py` converts unstructured assets into `data/external/stage_a_seed/` and `data/external/stage_b_seed/`.",
                "- `tv/corpus/render.py` is the current path that merges the unstructured seed into `data/finetune/stage_a_mt_v2/`.",
            ],
        ),
        (
            "Minimal Safe Stage C Integration Points",
            [
                "- Reuse repo-relative JSONL + manifest conventions from `tv/common/io.py` and `tv/common/manifests.py`.",
                "- Keep Stage C source recovery separate from training-ready renders under `data/external/stage_c_seed/` and `data/finetune/stage_c_*`.",
                "- Plug Stage C SFT datasets into the existing `scripts/train_stage_b_agent.py` flow through config-level data-path changes instead of altering the trainer core.",
                "- Add a Stage C-native eval script rather than forcing the Stage B translation eval to judge native grounding.",
            ],
        ),
        (
            "Execution Order Chosen",
            [
                "1. Build repo audit and raw source manifest.",
                "2. Reuse existing Stage A seed and OCR artifacts, then add direct extraction for raw-only PDFs and images.",
                "3. Recover OCR-heavy native news into article-level bundles where feasible and register every usable document with provenance.",
                "4. Generate grounded SFT, news-article tasks, mirrors, terminology tasks, preferences, and held-out eval items.",
                "5. Assemble Stage C train/val/DPO/eval renders and arm-specific prompt-mixture ablation files.",
                "6. Wire training/eval through new Stage C configs, run dataset smoke validation, and update canonical docs/reports.",
            ],
        ),
    ]
    _write_markdown_report(reports_dir / "stage_c_repo_audit.md", "Stage C Repo Audit", sections)


def _build_raw_source_report(reports_dir: Path, manifest_rows: list[dict[str, Any]]) -> None:
    by_family = Counter(row["source_family"] for row in manifest_rows)
    by_status = Counter(row["status_guess"] for row in manifest_rows)
    sections = [
        (
            "Snapshot",
            [
                f"- Total sources scanned: `{len(manifest_rows)}`.",
                "- Manifest path: `data/external/stage_c_seed/raw_source_manifest.jsonl`.",
            ],
        ),
        (
            "By Source Family",
            [f"- `{family}`: `{count}`" for family, count in sorted(by_family.items())],
        ),
        (
            "By Status Guess",
            [f"- `{status}`: `{count}`" for status, count in sorted(by_status.items())],
        ),
        (
            "Priority Notes",
            [
                "- Historic news scans and raw-only civic PDFs are marked for promotion into grounded Stage C tasks.",
                "- Duplicate/reference assets and `REAL ONES ONLY/Documents/Don_t use yet/` are kept visible in the manifest but excluded from the default SFT pool.",
                "- Audio/video files remain manifest entries with transcript-path notes rather than direct text-training inputs.",
            ],
        ),
    ]
    _write_markdown_report(reports_dir / "stage_c_raw_source_manifest.md", "Stage C Raw Source Manifest", sections)


def _build_dataset_report(
    *,
    reports_dir: Path,
    grounded_rows: list[dict[str, Any]],
    mirror_rows: list[dict[str, Any]],
    news_rows: list[dict[str, Any]],
    constrained_rows: list[dict[str, Any]],
    preference_rows: list[dict[str, Any]],
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    default_arm: str,
) -> None:
    sections = [
        (
            "Build Outputs",
            [
                f"- Default Stage C arm: `{default_arm}`.",
                f"- Grounded SFT seed rows: `{len(grounded_rows)}`.",
                f"- Prompt mirrors: `{len(mirror_rows)}`.",
                f"- News article tasks: `{len(news_rows)}`.",
                f"- Terminology/constrained tasks: `{len(constrained_rows)}`.",
                f"- Preference rows: `{len(preference_rows)}`.",
                f"- Final Stage C SFT train/val: `{len(train_rows)}` / `{len(val_rows)}`.",
                f"- Held-out Stage C eval rows: `{len(eval_rows)}`.",
            ],
        ),
        (
            "Counts By Task Family",
            [f"- `{key}`: `{value}`" for key, value in _count_by(train_rows + val_rows, lambda row: row.get("task_family", "unknown")).items()],
        ),
        (
            "Counts By Prompt Language",
            [f"- `{key}`: `{value}`" for key, value in _count_by(train_rows + val_rows, lambda row: row.get("prompt_lang", "unknown")).items()],
        ),
        (
            "Counts By Assistant Language",
            [f"- `{key}`: `{value}`" for key, value in _count_by(train_rows + val_rows, lambda row: row.get("assistant_lang", "unknown")).items()],
        ),
        (
            "Counts By Source Family",
            [f"- `{key}`: `{value}`" for key, value in _count_by(train_rows + val_rows, lambda row: row.get("provenance", {}).get("source_family", "unknown")).items()],
        ),
        (
            "Reproduction Commands",
            [
                "- `uv run python scripts/build_stage_c_pipeline.py --config configs/stage_c_pipeline_default.json`",
                "- `uv run python scripts/eval_stage_c_native.py --config configs/stage_c_eval_native_oss120b.json --dry-run`",
                "- `uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_english.json --pilot`",
            ],
        ),
    ]
    _write_markdown_report(reports_dir / "stage_c_dataset_report.md", "Stage C Dataset Report", sections)


def _build_eval_files(
    *,
    eval_dir: Path,
    eval_rows: list[dict[str, Any]],
) -> None:
    write_jsonl(eval_dir / "manifest.jsonl", eval_rows)
    write_jsonl(eval_dir / "human_check_subset.jsonl", eval_rows[: min(24, len(eval_rows))])
    rubric = [
        "# Stage C Native Eval Rubric",
        "",
        "Score each item on these axes from 1-5:",
        "",
        "- adequacy: Does the answer satisfy the task?",
        "- in_language_fidelity: Does the answer stay in the requested language and avoid English leakage?",
        "- entity_preservation: Are names, places, dates, and numbers preserved?",
        "- style_fit: Does the answer fit the requested style or register?",
        "- source_support: Can each important claim be traced back to the provided source snippet?",
    ]
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "rubric.md").write_text("\n".join(rubric) + "\n", encoding="utf-8")


def build_stage_c_package(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    if config:
        cfg.update(config)

    repo_root = get_repo_root()
    asset_dir = resolve_path(cfg["asset_dir"], repo_root)
    stage_a_seed_dir = resolve_path(cfg["stage_a_seed_dir"], repo_root)
    ocr_dir = resolve_path(cfg["ocr_dir"], repo_root)
    ocr_fast_dir = resolve_path(cfg["ocr_fast_dir"], repo_root)
    output_dir = resolve_path(cfg["output_dir"], repo_root)
    sft_output_dir = resolve_path(cfg["sft_output_dir"], repo_root)
    dpo_output_dir = resolve_path(cfg["dpo_output_dir"], repo_root)
    eval_output_dir = resolve_path(cfg["eval_output_dir"], repo_root)
    eval_dir = resolve_path(cfg["eval_dir"], repo_root)
    reports_dir = resolve_path(cfg["reports_dir"], repo_root)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "extracted_text").mkdir(parents=True, exist_ok=True)
    (output_dir / "ocr_recovered").mkdir(parents=True, exist_ok=True)
    (output_dir / "terms").mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    _build_repo_audit_report(repo_root=repo_root, reports_dir=reports_dir)

    stage_a_sources = _load_stage_a_seed_sources(stage_a_seed_dir)
    ocr_groups = _load_ocr_groups(ocr_dir, ocr_fast_dir)

    source_manifest = _build_source_manifest(
        repo_root=repo_root,
        asset_dir=asset_dir,
        stage_a_sources=stage_a_sources,
        ocr_groups=ocr_groups,
    )
    write_jsonl(output_dir / "raw_source_manifest.jsonl", source_manifest)
    _build_raw_source_report(reports_dir, source_manifest)

    extracted_rows: list[dict[str, Any]] = []
    stage_a_segments: dict[str, list[ExtractedSegment]] = defaultdict(list)
    ocr_page_segments: dict[str, list[ExtractedSegment]] = defaultdict(list)
    raw_page_segments: dict[str, list[ExtractedSegment]] = defaultdict(list)

    for source_path, rows in stage_a_sources.items():
        seed_extracted, seed_segments = _stage_a_segments_from_rows(source_path, rows)
        extracted_rows.extend(seed_extracted)
        stage_a_segments[source_path].extend(seed_segments)

    source_manifest_lookup = {row["source_path"]: row for row in source_manifest}
    for source_path, manifest_row in source_manifest_lookup.items():
        source_file = repo_root / source_path
        if not source_file.exists():
            continue
        stem = _canonical_stem(source_path)
        if stem in ocr_groups:
            ocr_extracted, ocr_segments = _page_rows_from_ocr(source_path, ocr_groups[stem])
            extracted_rows.extend(ocr_extracted)
            ocr_page_segments[source_path].extend(ocr_segments)
            continue
        if source_path in stage_a_sources:
            continue
        if source_file.suffix.lower() == ".pdf":
            pdf_extracted, pdf_segments = _page_rows_from_pdftotext(source_path, source_file)
            if pdf_segments:
                extracted_rows.extend(pdf_extracted)
                raw_page_segments[source_path].extend(pdf_segments)
        elif source_file.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            image_extracted, image_segments = _image_rows_from_tesseract(source_path, source_file)
            if image_segments:
                extracted_rows.extend(image_extracted)
                raw_page_segments[source_path].extend(image_segments)

    extracted_rows.sort(key=lambda row: (row["source_path"], str(row["page_or_image"])))
    write_jsonl(output_dir / "extracted_text" / "page_text.jsonl", extracted_rows)

    ocr_articles: list[dict[str, Any]] = []
    recovered_segment_rows: list[dict[str, Any]] = []
    for source_path, page_segments in ocr_page_segments.items():
        if _source_family_for_path(source_path) != "historic_news_scan":
            continue
        articles, segments = _recover_news_articles(
            source_path,
            page_segments,
            max_articles=cfg["max_news_articles_per_source"],
        )
        ocr_articles.extend(articles)
        recovered_segment_rows.extend(segments)

    ocr_articles.sort(key=lambda row: row["article_id"])
    recovered_segment_rows.sort(key=lambda row: row["segment_id"])
    write_jsonl(output_dir / "ocr_recovered" / "native_news_articles.jsonl", ocr_articles)
    write_jsonl(output_dir / "ocr_recovered" / "recovered_segments.jsonl", recovered_segment_rows)

    doc_bundles = _build_doc_bundles(
        source_manifest=source_manifest,
        stage_a_segments=stage_a_segments,
        ocr_page_segments=ocr_page_segments,
        raw_page_segments=raw_page_segments,
        ocr_articles=ocr_articles,
        min_segment_chars=cfg["min_segment_chars"],
    )
    bundle_lookup = {bundle["doc_id"]: bundle for bundle in doc_bundles}

    registry = _build_doc_registry(
        repo_root=repo_root,
        source_manifest=source_manifest,
        doc_bundles=doc_bundles,
    )
    write_jsonl(output_dir / "native_doc_registry.jsonl", registry)

    grounded_rows: list[dict[str, Any]] = []
    for bundle in doc_bundles:
        if len(bundle["text"]) < cfg["min_doc_chars"]:
            continue
        if bundle["source_family"] in {"duplicate_reference", "audio_video_asset", "quarantine_pdf", "lexical_reference"}:
            continue
        grounded_rows.extend(_build_grounded_tasks_for_bundle(bundle))
    grounded_rows.sort(key=lambda row: row["id"])
    write_jsonl(output_dir / "grounded_sft.jsonl", grounded_rows)

    news_rows = _build_news_article_tasks(doc_bundles)
    write_jsonl(output_dir / "news_article_tasks.jsonl", news_rows)

    mirror_rows = _build_prompt_mirrors(grounded_rows)
    write_jsonl(output_dir / "grounded_sft_mirrors.jsonl", mirror_rows)

    entity_rows, glossary_rows, constrained_rows = _build_entity_rows(doc_bundles)
    write_jsonl(output_dir / "terms" / "entities.jsonl", entity_rows)
    write_jsonl(output_dir / "terms" / "glossary_candidates.jsonl", glossary_rows)
    write_jsonl(output_dir / "terms" / "constrained_tasks.jsonl", constrained_rows)

    preference_rows = _build_preferences(grounded_rows, bundle_lookup)
    write_jsonl(output_dir / "preferences.jsonl", preference_rows)

    holdout_doc_ids = _select_holdout_doc_ids(
        doc_bundles,
        holdout_fraction=cfg["holdout_fraction"],
    )
    eval_rows = _build_eval_items(
        bundles=doc_bundles,
        holdout_doc_ids=holdout_doc_ids,
    )
    eval_output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(eval_output_dir / "manifest.jsonl", eval_rows)
    write_jsonl(eval_output_dir / "held_out_native.jsonl", eval_rows)
    _build_eval_files(eval_dir=eval_dir, eval_rows=eval_rows)

    sft_candidates = grounded_rows + news_rows + mirror_rows + constrained_rows
    existing_signatures = _load_existing_signatures(
        repo_root / "data/finetune/stage_a_mt/train_balanced.jsonl",
        repo_root / "data/finetune/stage_a_mt_v2/train_balanced.jsonl",
    )
    sft_candidates = _dedupe_rows(sft_candidates, existing_signatures=existing_signatures)
    train_rows, val_rows = _build_split_rows(
        sft_candidates,
        holdout_doc_ids=holdout_doc_ids,
        val_fraction=cfg["val_fraction"],
    )

    arms_dir = sft_output_dir / "arms"
    arms_dir.mkdir(parents=True, exist_ok=True)
    arm_stats: dict[str, dict[str, int]] = {}
    arm_rows: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
    for arm in (
        "native_only",
        "native_plus_english",
        "native_plus_stage_b_translated",
        "native_plus_bilingual",
    ):
        arm_train = [row for row in train_rows if _prompt_origin_allowed(row, arm)]
        arm_val = [row for row in val_rows if _prompt_origin_allowed(row, arm)]
        write_jsonl(arms_dir / f"{arm}_train.jsonl", arm_train)
        write_jsonl(arms_dir / f"{arm}_val.jsonl", arm_val)
        arm_stats[arm] = {"train": len(arm_train), "val": len(arm_val)}
        arm_rows[arm] = (arm_train, arm_val)

    default_arm = cfg["default_arm"]
    default_train, default_val = arm_rows[default_arm]
    sft_output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(sft_output_dir / "train.jsonl", default_train)
    write_jsonl(sft_output_dir / "val.jsonl", default_val)

    dpo_output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(dpo_output_dir / "train.jsonl", preference_rows)
    write_jsonl(dpo_output_dir / "val.jsonl", preference_rows[: max(1, len(preference_rows) // 10)])

    dataset_manifest = create_manifest(
        stage="stage_c_dataset_build",
        config=cfg,
        extra={
            "source_manifest_count": len(source_manifest),
            "extracted_rows": len(extracted_rows),
            "ocr_articles": len(ocr_articles),
            "doc_registry_count": len(registry),
            "grounded_sft_count": len(grounded_rows),
            "news_article_tasks_count": len(news_rows),
            "mirror_count": len(mirror_rows),
            "constrained_tasks_count": len(constrained_rows),
            "preference_count": len(preference_rows),
            "eval_count": len(eval_rows),
            "train_count": len(default_train),
            "val_count": len(default_val),
            "candidate_train_count": len(train_rows),
            "candidate_val_count": len(val_rows),
            "arm_stats": arm_stats,
        },
    )
    save_manifest(dataset_manifest, output_dir / "build_manifest.json")

    _build_dataset_report(
        reports_dir=reports_dir,
        grounded_rows=grounded_rows,
        mirror_rows=mirror_rows,
        news_rows=news_rows,
        constrained_rows=constrained_rows,
        preference_rows=preference_rows,
        train_rows=default_train,
        val_rows=default_val,
        eval_rows=eval_rows,
        default_arm=default_arm,
    )

    return {
        "source_manifest_count": len(source_manifest),
        "extracted_rows": len(extracted_rows),
        "ocr_articles": len(ocr_articles),
        "doc_registry_count": len(registry),
        "grounded_sft_count": len(grounded_rows),
        "news_article_tasks_count": len(news_rows),
        "mirror_count": len(mirror_rows),
        "entity_count": len(entity_rows),
        "glossary_count": len(glossary_rows),
        "constrained_tasks_count": len(constrained_rows),
        "preference_count": len(preference_rows),
        "eval_count": len(eval_rows),
        "train_count": len(default_train),
        "val_count": len(default_val),
        "candidate_train_count": len(train_rows),
        "candidate_val_count": len(val_rows),
        "arm_stats": arm_stats,
    }
