#!/usr/bin/env python3
"""Ingest new unstructured TVL-EN data sources into Stage A seed format.

Processes:
  1. corpus_v2 (tuvalu.aa-ken.jp word/expression pairs)
  2. Paired EN/TVL PDFs (government docs with parallel structure)
  3. Bilingual PDFs with TUVALUAN/ENGLISH headers
  4. Language cards (two-column TVL→EN from MPP)
  5. Te Papa activity book (vocabulary lists, bilingual phrases)
  6. Mormon prayer JPG pair (OCR)
  7. Grammar (Besnier interlinear examples)
  8. Fishes (Thaman 2015 columnar table)
  9. Flora (Thaman 2016 annotated listing)
  10. Pai & Vau (bilingual children's book)
  11. Toku Atufenua Pele (bilingual essays)
  12. Nanumea Tales (numbered paragraph alignment)

Output: data/external/stage_a_seed/unstruct_*.jsonl files
These integrate into the existing pipeline via:
  build_stage_a_mt_data.py → render_training_data.py --include-unstructured

Usage:
  uv run scripts/ingest_new_unstruct.py
  uv run scripts/ingest_new_unstruct.py --dry-run
  uv run scripts/ingest_new_unstruct.py --only corpus_v2
  uv run scripts/ingest_new_unstruct.py --only paired_pdfs
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
ASSET_DIR = REPO_ROOT / "unstruct_lang_data" / "REAL ONES ONLY"
OUTPUT_DIR = REPO_ROOT / "data" / "external" / "stage_a_seed"
EXTRACTOR_VERSION = "new-unstruct-ingest-v1"

# ── Helpers ──────────────────────────────────────────────────────────────────


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _make_seed_row(
    id_: str,
    tvl: str,
    en: str,
    *,
    domain: str,
    alignment_method: str,
    alignment_confidence: float,
    source_tvl: str,
    source_en: str,
    pub_code: str,
    content_type: str = "translation_phrase",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tvl = tvl.strip()
    en = en.strip()
    tvl_chars = len(tvl)
    en_chars = len(en)
    ratio = tvl_chars / en_chars if en_chars > 0 else 0.0
    return {
        "id": id_,
        "tvl": tvl,
        "en": en,
        "content_type": content_type,
        "domain": domain,
        "alignment_method": alignment_method,
        "alignment_confidence": alignment_confidence,
        "doc_id": None,
        "source_url_tvl": source_tvl,
        "source_url_en": source_en,
        "book_num": None,
        "chapter": None,
        "verse": None,
        "date": None,
        "pub_code": pub_code,
        "tvl_chars": tvl_chars,
        "en_chars": en_chars,
        "length_ratio": round(ratio, 4),
        "metadata": {
            "extractor_version": EXTRACTOR_VERSION,
            **(metadata or {}),
        },
    }


def _pdftotext_layout(path: Path) -> str:
    r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                       capture_output=True, text=True)
    return r.stdout or "" if r.returncode == 0 else ""


def _pdftotext_raw(path: Path) -> str:
    r = subprocess.run(["pdftotext", str(path), "-"],
                       capture_output=True, text=True)
    return r.stdout or "" if r.returncode == 0 else ""


def _ocr_image(path: Path, lang: str = "eng") -> str:
    r = subprocess.run(["tesseract", str(path), "stdout", "-l", lang, "--psm", "6"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [warn] tesseract failed on {path.name}: {r.stderr[:200]}", file=sys.stderr)
        return ""
    return (r.stdout or "").strip()


def _split_paragraphs(text: str, *, min_chars: int = 20) -> list[str]:
    text = re.sub(r"\f", "\n\n", text)
    raw = re.split(r"\n{2,}", text)
    paras = []
    for p in raw:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) >= min_chars:
            paras.append(p)
    return paras


def _clean_para(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^\d+\s*$", "", text)
    text = re.sub(r"PAGE \d+ OF \d+", "", text, flags=re.IGNORECASE)
    return text.strip()


def _is_boilerplate(text: str) -> bool:
    t = text.lower().strip()
    if len(t) < 15:
        return True
    if re.match(r"^(page\s+)?\d+(\s+of\s+\d+)?$", t):
        return True
    if t.startswith("www.") or t.startswith("http"):
        return True
    return False


# ── Post-processing cleanup ──────────────────────────────────────────────────

# Gloss abbreviations from Besnier grammar that should NOT appear in TVL text
_GLOSS_ABBREVS = {
    "Anp", "Ben", "Cmp", "Cnt", "Cst", "Dxs", "Erg", "Foc", "Fut",
    "Inc", "Irr", "Itj", "Neg", "Nps", "Nrg", "Num", "Opt", "Prc",
    "Prf", "Pst", "Rcp", "Rdp", "Sbj", "Spc", "Tag", "Trn", "Voc",
    "Agr", "Nom",
}

# Right single curly quote — used for BOTH translation delimiters AND English contractions
_CONTRACTION_RE = re.compile(r"\b(don|didn|doesn|won|wouldn|couldn|shouldn|isn|aren|wasn|weren|hasn|haven|hadn|ain|can|mustn|needn)$", re.IGNORECASE)


def _postprocess_rows(rows: list[dict[str, Any]], source_name: str) -> list[dict[str, Any]]:
    """Apply cross-source quality filters. Returns cleaned list."""
    cleaned: list[dict[str, Any]] = []
    removed = {"truncated_en": 0, "gloss_in_tvl": 0, "en_prose_in_tvl": 0,
               "garbled_text": 0, "extreme_ratio": 0, "duplicate": 0,
               "page_number_noise": 0, "speaker_label": 0, "pos_tag": 0,
               "stub_en": 0}
    seen: set[tuple[str, str]] = set()

    for row in rows:
        tvl = row["tvl"]
        en = row["en"]

        # ── Deduplicate ──
        key = (tvl.lower().strip(), en.lower().strip())
        if key in seen:
            removed["duplicate"] += 1
            continue
        seen.add(key)

        # ── Truncated EN at contraction (grammar-specific) ──
        # e.g., EN = "I don" or "Why didn" from curly-quote stripping
        if _CONTRACTION_RE.search(en.rstrip()):
            removed["truncated_en"] += 1
            continue

        # ── Stub EN: EN < 3 words when TVL > 5 words ──
        en_words = en.split()
        tvl_words = tvl.split()
        if len(en_words) <= 2 and len(tvl_words) >= 5:
            removed["stub_en"] += 1
            continue

        # ── Gloss abbreviations leaked into TVL field ──
        tvl_tokens = set(tvl.split())
        gloss_count = len(tvl_tokens & _GLOSS_ABBREVS)
        if gloss_count >= 2:
            removed["gloss_in_tvl"] += 1
            continue

        # ── English prose in TVL field ──
        # Check if TVL text is actually English (high English function word ratio)
        eng_func = {"the", "a", "an", "of", "in", "is", "are", "was", "were", "that",
                     "this", "which", "for", "with", "can", "may", "but", "also",
                     "however", "between", "from", "as", "be", "or", "and", "not"}
        tvl_lower = [w.lower() for w in tvl_words]
        if len(tvl_words) >= 6:
            eng_count = sum(1 for w in tvl_lower if w in eng_func)
            if eng_count / len(tvl_words) > 0.35:
                removed["en_prose_in_tvl"] += 1
                continue

        # ── Garbled spaced-out text (PDF extraction artifact) ──
        # Detect: most "words" are 1-2 chars (char-by-char spacing)
        if len(tvl_words) >= 10:
            short_count = sum(1 for w in tvl_words if len(w) <= 2)
            if short_count / len(tvl_words) > 0.6:
                removed["garbled_text"] += 1
                continue
        if len(en_words) >= 10:
            short_count = sum(1 for w in en_words if len(w) <= 2)
            if short_count / len(en_words) > 0.6:
                removed["garbled_text"] += 1
                continue

        # ── Strip speaker labels from TVL (grammar dialogues) ──
        tvl_stripped = re.sub(r"^[A-Z]:\s+", "", tvl)
        if tvl_stripped != tvl:
            row = {**row, "tvl": tvl_stripped}
            tvl = tvl_stripped

        # ── Strip POS tags from EN ──
        en_cleaned = re.sub(r"\[(?:N|V|Adj|Adv|Prep|Conj|Pron)\]\s*", "", en)
        if en_cleaned != en:
            removed["pos_tag"] += 1
            row = {**row, "en": en_cleaned.strip()}
            en = en_cleaned.strip()

        # ── Strip page numbers embedded in text ──
        # Pattern: standalone 2-3 digit numbers surrounded by spaces within text
        tvl_cleaned = re.sub(r"\s+\d{3}\s+", " ", tvl)
        en_cleaned2 = re.sub(r"\s+\d{3}\s+", " ", en)
        if tvl_cleaned != tvl or en_cleaned2 != en:
            removed["page_number_noise"] += 1
            row = {**row, "tvl": tvl_cleaned.strip(), "en": en_cleaned2.strip()}
            tvl = tvl_cleaned.strip()
            en = en_cleaned2.strip()

        # ── Strip zero morpheme markers (ø) from grammar ──
        if "ø" in tvl:
            tvl_cleaned = re.sub(r"\s*ø[ji/*]*\s*", " ", tvl)
            row = {**row, "tvl": re.sub(r"\s+", " ", tvl_cleaned).strip()}

        # ── Strip fullwidth characters ──
        tvl_fw = row["tvl"]
        en_fw = row["en"]
        # Common fullwidth → ASCII replacements
        fw_map = str.maketrans({
            "\uff1f": "?", "\uff0c": ",", "\uff0e": ".", "\uff08": "(",
            "\uff09": ")", "\uff1a": ":", "\uff1b": ";", "\uff57": "w",
        })
        tvl_fw = tvl_fw.translate(fw_map)
        en_fw = en_fw.translate(fw_map)
        if tvl_fw != row["tvl"] or en_fw != row["en"]:
            row = {**row, "tvl": tvl_fw, "en": en_fw}

        # ── Strip bell character and other control chars ──
        row = {**row,
               "tvl": re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", row["tvl"]),
               "en": re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", row["en"])}

        # ── Recalculate length stats ──
        tvl_chars = len(row["tvl"])
        en_chars = len(row["en"])
        ratio = tvl_chars / en_chars if en_chars > 0 else 0.0
        row = {**row, "tvl_chars": tvl_chars, "en_chars": en_chars,
               "length_ratio": round(ratio, 4)}

        # ── Skip if text became empty after cleaning ──
        if not row["tvl"].strip() or not row["en"].strip():
            continue

        cleaned.append(row)

    total_removed = sum(removed.values())
    if total_removed > 0:
        print(f"  [{source_name}] postprocess: removed {total_removed} rows "
              f"({', '.join(f'{k}={v}' for k, v in removed.items() if v > 0)})")

    return cleaned


# ── Source 1: corpus_v2 ──────────────────────────────────────────────────────


def process_corpus_v2() -> list[dict[str, Any]]:
    """Convert tuvalu_en_bilingual_corpus_v2 JSONL to seed format."""
    src = ASSET_DIR / "word pairings and data sets" / "tuvalu_en_bilingual_corpus_v2"
    jsonl_path = src / "pairs" / "corpus_pairs_dedup.jsonl"

    if not jsonl_path.exists():
        print(f"  [skip] {jsonl_path} not found")
        return []

    rows = []
    seen: set[tuple[str, str]] = set()
    with jsonl_path.open(encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            tvl = (obj.get("tuvalu_text") or "").strip()
            en = (obj.get("english_text") or "").strip()
            if not tvl or not en:
                continue
            # Clean up numbered variants like "mai 1" → "mai"
            tvl_clean = re.sub(r"\s+\d+$", "", tvl)
            # Clean up POS markers like "[N] where-?" → "where-?"
            en_clean = re.sub(r"^\[.*?\]\s*", "", en)
            # Strip numbered senses: "1. cook 2. cooked well" → "cook"
            en_clean = re.sub(r"^\d+\.\s*", "", en_clean)
            if re.match(r".*\s+\d+\.\s+", en_clean):
                # Take only the first sense
                en_clean = re.split(r"\s+\d+\.\s+", en_clean)[0].strip()
            # Strip academic citations: "(Jackson 2010)", "(Koch 1961)"
            en_clean = re.sub(r"\s*\([A-Z][a-z]+ \d{4}\)", "", en_clean)
            # Strip POS abbreviation prefixes: "n. female singer" → "female singer"
            en_clean = re.sub(r"^(?:n|v|adj|adv|prep|conj)\.\s+", "", en_clean, flags=re.IGNORECASE)
            if not tvl_clean or not en_clean:
                continue

            dedup_key = (tvl_clean.lower(), en_clean.lower())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            cats = obj.get("categories_en", "")
            if isinstance(cats, list):
                cats = "; ".join(cats)

            rows.append(_make_seed_row(
                id_=f"unstruct:corpus_v2:{i:05d}",
                tvl=tvl_clean, en=en_clean,
                domain="corpus_v2",
                alignment_method="corpus_pair",
                alignment_confidence=0.95,
                source_tvl="tuvalu.aa-ken.jp",
                source_en="tuvalu.aa-ken.jp",
                pub_code="unstruct_corpus_v2",
                content_type="translation_phrase",
                metadata={
                    "entry_type": obj.get("entry_type"),
                    "has_audio": obj.get("has_any_audio", False),
                    "categories": cats,
                    "source_file": str(jsonl_path.relative_to(REPO_ROOT)),
                    "source_row": i,
                },
            ))

    print(f"  corpus_v2: {len(rows)} pairs from {jsonl_path.name}")
    return rows


# ── Source 2: Paired EN/TVL PDFs ─────────────────────────────────────────────

PAIRED_PDFS: list[tuple[str, str, str, str]] = [
    ("BCG Vaccine", "healthed_bcg_aftercare_en_HE2226.pdf",
     "healthed_bcg_aftercare_tuvaluan_HE2233.pdf", "bcg_aftercare"),
    ("BCG Vaccine", "healthed_bcg_information_en_HE2205.pdf",
     "healthed_bcg_information_tuvaluan_HE2212.pdf", "bcg_info"),
    ("Citizen budget 2025", "eng_citizen_budget_2025_2026.pdf",
     "tuv_citizen_budget_2025_2026.pdf", "citizen_budget"),
    ("Climate children", "CC_Story_Eng_lr.pdf",
     "children-take-action-tuvalu.pdf", "climate_children"),
    ("Covid alert Levels", "COVID-19-alert-levels-summary.pdf",
     "Alert-Levels-Table_Govt-Tuvalu.pdf", "covid_alert"),
    ("Diabetes", "diabetes-type-2-brochure.pdf",
     "Type-2-diabetes-tuvaluan-brochure.pdf", "diabetes"),
    # finance_budget REMOVED — 100% duplicate of citizen_budget (same underlying PDFs)
    ("Health reform", "heallth-reform-white-paper-summary-apr21.pdf",
     "health-reform-white-paper-summary-tvl-may21.pdf", "health_reform"),
    ("Measles", "healthed_measles_en_HE5000.pdf",
     "healthed_measles_tuvaluan_HE8107.pdf", "measles"),
    (" Menincoccal (inconsistent format", "healthed_meningococcal_en_HE2395.pdf",
     "healthed_meningococcal_tuvaluan_HE2663.pdf", "meningococcal"),
    ("Pac education 2030", "Pacific-Education-Plan-2023-Summary.pdf",
     "Pacific-Education-Plan-2023-Summary-Tuvaluan.pdf", "pac_edu_2030"),
    ("Resilient emergency sheet",
     "resilient-religious-communities-emergency-preparedness-plan-appendix1.pdf",
     "resilient-religious-emergency-preparedness-plan-tuvaluan.pdf", "resilient_emergency"),
    ("Strategic Action Plan ", "NSAP Eng new web.pdf",
     "NSAP Tuvalu new.pdf", "nsap"),
    ("TCCP 2012", "TCCP Te Kaniva English final web new.PDF.pdf",
     "TCCP Te Kaniva Tuvalu final web new.PDF.pdf", "tccp_2012"),
    ("Traveller Factsheet", "Traveller factsheet - English.pdf",
     "Traveller factsheet - Tuvaluan.pdf", "traveller_factsheet"),
    ("biogass ", "biogass_publication_tuvalu_english_final.pdf",
     "biogass_publication_tuvalu_traslated.pdf", "biogas"),
    ("covid level 4", "COVID19-L4-Your-stay-at-home-plan-A4-ENGLISH.pdf",
     "COVID19-L4-Your-stay-at-home-plan-A4-TUVALUAN.pdf", "covid_level4"),
]


def _align_paragraphs(
    en_paras: list[str], tvl_paras: list[str], *, max_ratio_diff: float = 3.0
) -> list[tuple[str, str, float]]:
    """Align paragraph lists 1:1 with confidence scoring."""
    pairs: list[tuple[str, str, float]] = []
    if not en_paras or not tvl_paras:
        return pairs

    # If counts match exactly, do 1:1 alignment
    if len(en_paras) == len(tvl_paras):
        for ep, tp in zip(en_paras, tvl_paras):
            if not ep or not tp:
                continue
            ratio = len(tp) / len(ep)
            if ratio < 1 / max_ratio_diff or ratio > max_ratio_diff:
                continue
            conf = min(1.0, 0.5 + 0.5 * min(len(ep), len(tp)) / max(len(ep), len(tp)))
            pairs.append((ep, tp, round(conf, 3)))
        return pairs

    shorter = min(len(en_paras), len(tvl_paras))
    longer = max(len(en_paras), len(tvl_paras))

    # If counts differ by ≤40%, try 1:1 alignment on shorter list
    if shorter > 0 and (longer - shorter) / shorter <= 0.40:
        for ep, tp in zip(en_paras[:shorter], tvl_paras[:shorter]):
            if not ep or not tp:
                continue
            ratio = len(tp) / len(ep)
            if ratio < 1 / max_ratio_diff or ratio > max_ratio_diff:
                continue
            conf = min(0.7, 0.3 + 0.4 * min(len(ep), len(tp)) / max(len(ep), len(tp)))
            pairs.append((ep, tp, round(conf, 3)))
        return pairs

    # Paragraph counts differ a lot — try page-level alignment.
    # Group paragraphs into pages (split on form feeds in original) and
    # align pages 1:1, then join paragraphs within each page.
    # Fallback: full-document pair
    en_full = " ".join(en_paras)
    tvl_full = " ".join(tvl_paras)
    if len(en_full) >= 50 and len(tvl_full) >= 50:
        ratio = len(tvl_full) / len(en_full)
        if 1 / max_ratio_diff <= ratio <= max_ratio_diff:
            pairs.append((en_full, tvl_full, 0.4))

    return pairs


def _align_by_page(en_text: str, tvl_text: str, *, min_para_chars: int = 30) -> list[tuple[str, str, float]]:
    """Split on form feeds and align page-by-page, then paragraph-by-paragraph."""
    en_pages = [p.strip() for p in en_text.split("\f") if p.strip()]
    tvl_pages = [p.strip() for p in tvl_text.split("\f") if p.strip()]

    if not en_pages or not tvl_pages:
        return []

    pairs: list[tuple[str, str, float]] = []
    n = min(len(en_pages), len(tvl_pages))
    for ep, tp in zip(en_pages[:n], tvl_pages[:n]):
        en_paras = [_clean_para(p) for p in _split_paragraphs(ep, min_chars=min_para_chars)
                     if not _is_boilerplate(p)]
        tvl_paras = [_clean_para(p) for p in _split_paragraphs(tp, min_chars=min_para_chars)
                      if not _is_boilerplate(p)]
        page_pairs = _align_paragraphs(en_paras, tvl_paras)
        pairs.extend(page_pairs)

    return pairs


def process_paired_pdfs() -> list[dict[str, Any]]:
    """Extract and align parallel EN/TVL government documents."""
    base = ASSET_DIR / "Documents" / "En-TVL seperate"
    rows: list[dict[str, Any]] = []
    pair_idx = 0

    for folder, en_file, tvl_file, slug in PAIRED_PDFS:
        en_path = base / folder / en_file
        tvl_path = base / folder / tvl_file
        if not en_path.exists() or not tvl_path.exists():
            print(f"  [skip] missing file for {slug}")
            continue

        en_text = _pdftotext_raw(en_path)
        tvl_text = _pdftotext_raw(tvl_path)
        if not en_text.strip() or not tvl_text.strip():
            print(f"  [skip] empty text for {slug}")
            continue

        # Try paragraph-level alignment first
        en_paras = [_clean_para(p) for p in _split_paragraphs(en_text, min_chars=30)
                     if not _is_boilerplate(p)]
        tvl_paras = [_clean_para(p) for p in _split_paragraphs(tvl_text, min_chars=30)
                      if not _is_boilerplate(p)]
        aligned = _align_paragraphs(en_paras, tvl_paras)

        # If paragraph alignment failed badly (<3 pairs), try page-level
        if len(aligned) < 3:
            page_aligned = _align_by_page(en_text, tvl_text, min_para_chars=30)
            if len(page_aligned) > len(aligned):
                aligned = page_aligned

        for en, tvl, conf in aligned:
            if len(en) < 30 or len(tvl) < 30:
                continue
            pair_idx += 1
            rows.append(_make_seed_row(
                id_=f"unstruct:paired_doc:{pair_idx:05d}",
                tvl=tvl, en=en,
                domain="paired_doc",
                alignment_method="paragraph_align",
                alignment_confidence=conf,
                source_tvl=str(tvl_path.relative_to(REPO_ROOT)),
                source_en=str(en_path.relative_to(REPO_ROOT)),
                pub_code=f"unstruct_paired_{slug}",
                content_type="translation_paragraph",
                metadata={
                    "topic": slug, "en_file": en_file, "tvl_file": tvl_file,
                    "en_para_count": len(en_paras), "tvl_para_count": len(tvl_paras),
                },
            ))

        print(f"  {slug}: {len(aligned)} aligned pairs "
              f"(EN:{len(en_paras)} TVL:{len(tvl_paras)} paras)")

    print(f"  paired_pdfs total: {len(rows)} pairs")
    return rows


# ── Source 3: Bilingual PDFs with TUVALUAN/ENGLISH headers ───────────────────

BILINGUAL_PDFS: list[tuple[str, str]] = [
    ("BILINGUAL Family Tax Benefit - Tuvaluan.pdf", "family_tax"),
    ("Child Care Subsidy - Tuvaluan.pdf", "child_care"),
]


def _segment_bilingual(text: str) -> list[tuple[str, str]]:
    """Segment bilingual document with TUVALUAN/ENGLISH headers into pairs."""
    pages = text.split("\f")
    current_en: list[str] = []
    current_tvl: list[str] = []

    for page in pages:
        page = page.strip()
        if not page:
            continue

        has_tuvaluan = bool(re.search(r"^TUVALUAN\b", page, re.MULTILINE | re.IGNORECASE))
        has_english = bool(re.search(r"^ENGLISH\b", page, re.MULTILINE | re.IGNORECASE))

        if has_tuvaluan and not has_english:
            current_tvl.append(page)
        elif has_english and not has_tuvaluan:
            current_en.append(page)
        elif has_tuvaluan and has_english:
            parts = re.split(r"\n(?=TUVALUAN\b|ENGLISH\b)", page, flags=re.IGNORECASE)
            for part in parts:
                part = part.strip()
                if re.match(r"^TUVALUAN\b", part, re.IGNORECASE):
                    body = re.sub(r"^TUVALUAN\s*\n?", "", part, flags=re.IGNORECASE).strip()
                    if body:
                        current_tvl.append(body)
                elif re.match(r"^ENGLISH\b", part, re.IGNORECASE):
                    body = re.sub(r"^ENGLISH\s*\n?", "", part, flags=re.IGNORECASE).strip()
                    if body:
                        current_en.append(body)

    if current_en and current_tvl:
        en_text = "\n\n".join(current_en)
        tvl_text = "\n\n".join(current_tvl)
        en_paras = [_clean_para(p) for p in _split_paragraphs(en_text, min_chars=30)
                     if not _is_boilerplate(p)]
        tvl_paras = [_clean_para(p) for p in _split_paragraphs(tvl_text, min_chars=30)
                      if not _is_boilerplate(p)]
        aligned = _align_paragraphs(en_paras, tvl_paras)
        return [(en, tvl) for en, tvl, _ in aligned]
    return []


def process_bilingual_pdfs() -> list[dict[str, Any]]:
    """Extract pairs from bilingual PDFs with TUVALUAN/ENGLISH headers."""
    base = ASSET_DIR / "Documents" / "Eng-TVL together"
    rows: list[dict[str, Any]] = []
    pair_idx = 0

    for filename, slug in BILINGUAL_PDFS:
        path = base / filename
        if not path.exists():
            print(f"  [skip] not found: {path}")
            continue
        text = _pdftotext_raw(path)
        if not text.strip():
            print(f"  [skip] empty text: {filename}")
            continue
        pairs = _segment_bilingual(text)
        for en, tvl in pairs:
            if len(en) < 30 or len(tvl) < 30:
                continue
            pair_idx += 1
            rows.append(_make_seed_row(
                id_=f"unstruct:bilingual_doc:{pair_idx:05d}",
                tvl=tvl, en=en,
                domain="bilingual_doc",
                alignment_method="bilingual_segment",
                alignment_confidence=0.6,
                source_tvl=str(path.relative_to(REPO_ROOT)),
                source_en=str(path.relative_to(REPO_ROOT)),
                pub_code=f"unstruct_bilingual_{slug}",
                content_type="translation_paragraph",
                metadata={"source_file": filename, "topic": slug},
            ))
        print(f"  {slug}: {len(pairs)} bilingual pairs from {filename}")

    print(f"  bilingual_pdfs total: {len(rows)} pairs")
    return rows


# ── Source 4: Language cards (two-column TVL→EN) ─────────────────────────────


def process_language_cards() -> list[dict[str, Any]]:
    """Extract TVL/EN pairs from MPP language cards (two-column layout)."""
    path = ASSET_DIR / "Documents" / "Eng-TVL together" / "mpp_te_gana_tuvalu_language_cards_bilingual.pdf"
    if not path.exists():
        print(f"  [skip] language cards not found")
        return []

    text = _pdftotext_layout(path)
    if not text.strip():
        print(f"  [skip] empty text for language cards")
        return []

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    pair_idx = 0
    rel_path = str(path.relative_to(REPO_ROOT))

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < 5:
            continue

        # Two-column format: TVL left, EN right, separated by 2+ spaces
        # e.g. "Talofa                    Greetings / Hello"
        m = re.match(r"^(.+?)\s{3,}(.+)$", line)
        if not m:
            continue

        left = m.group(1).strip()
        right = m.group(2).strip()

        # Skip headers, pronunciation guides, credits
        if not left or not right:
            continue
        if len(left) < 2 or len(right) < 2:
            continue
        if left.startswith("•") or left.startswith("Pati Aoga"):
            continue
        # Skip phonetics lines like 'a sounded as "a" in "father"'
        if "sounded as" in right.lower() or "vowel" in right.lower():
            continue
        # Skip section headers
        if right.lower() in ("helpful words", "common phrases", "pleasantries",
                              "in conversation", "people", "prayer", "hymn"):
            continue
        if left.lower() in ("common phrases", "pleasantries", "in conversation",
                             "people", "consonants", "five vowels",
                             "reading and speaking"):
            continue
        # Skip vowel/consonant grid rows (e.g., "Aa → Ee Ii Oo Uu")
        # These are tabular layouts, not translation pairs
        if len(left) <= 3 and not any(c.isspace() for c in left):
            continue
        # Skip if the right side looks like more TVL tokens (no English words)
        # A valid EN side should have at least one 3+ letter English word
        en_words = [w for w in right.split() if len(w) >= 3 and w.isascii()]
        if not en_words:
            continue
        # Skip if right side has internal multi-column spacing (grid artifact)
        if re.search(r"\S\s{3,}\S", right):
            continue

        dedup_key = (left.lower(), right.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        pair_idx += 1
        rows.append(_make_seed_row(
            id_=f"unstruct:lang_cards:{pair_idx:05d}",
            tvl=left, en=right,
            domain="language_cards",
            alignment_method="two_column_layout",
            alignment_confidence=0.9,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_language_cards",
            content_type="translation_phrase",
            metadata={"source_file": path.name},
        ))

    print(f"  language_cards: {len(rows)} pairs")
    return rows


# ── Source 5: Te Papa activity book (vocabulary/phrase extraction) ────────────

# Hard-coded vocabulary lists from the activity book
TEPAPA_WORD_LISTS: list[tuple[str, str]] = [
    # Colors (page 5)
    ("felo", "yellow"),
    ("kakii", "grey"),
    ("kūla", "red"),
    ("lanu launiu", "green"),
    ("lanu moana", "dark blue"),
    ("ōlenisi", "orange"),
    ("piniki", "pink"),
    ("tea", "white"),
    ("uli", "black"),
    ("uli malie", "brown"),
    ("violeta", "purple"),
    # Numbers (page 8)
    ("tasi", "one"),
    ("lua", "two"),
    ("tolu", "three"),
    ("fā", "four"),
    ("lima", "five"),
    ("ono", "six"),
    ("fitu", "seven"),
    ("valu", "eight"),
    ("iva", "nine"),
    ("sefulu", "ten"),
    ("selau", "one hundred"),
    ("afe", "one thousand"),
    # Animals (page 9)
    ("ali", "flounder"),
    ("fonu", "green sea turtle"),
    ("gogo", "black noddy"),
    ("kaleva", "long-tailed cuckoo"),
    ("lasisi", "land snail"),
    ("tuna", "eel"),
    ("mago", "mako shark"),
    ("moko", "forest gecko"),
    # Body parts (page 12)
    ("fulufulu", "hair"),
    ("taliga", "ears"),
    ("ihu", "nose"),
    ("mata", "eyes"),
    ("kapakau", "arms"),
    ("lima", "hands"),
    ("pihu", "gut"),
    ("vae", "legs"),
    ("matikao", "fingers"),
    ("foitino", "body"),
    # Fatele costume (page 13)
    ("fau", "neck garland made from shells, leaves, puka tree seeds"),
    ("malele", "head garland made from flowers and leaves"),
    ("lakei", "arm bands made from leaves, paper, shells"),
    ("titi tao", "decorative overskirt made from dyed pandanus leaves"),
    ("togiga fatele", "top, for women, made from leaves"),
    ("titi lama", "dancing skirt made from pandanus leaves"),
    # Te Ano sport terms (page 14)
    ("ano", "ball"),
    ("malae", "field"),
    ("vaka", "team"),
    ("alovaka", "captain"),
    ("pukepuke", "catcher"),
    # Emotions (page 15)
    ("fiafia", "happy"),
    ("faanoanoa", "sad"),
    ("fiakai", "hungry"),
    ("alofa", "love"),
    ("logo'mae", "hurt"),
    ("fakapoi", "shocked"),
    # Page titles / phrases
    ("'Gana Tuvalu", "Tuvalu language"),
    ("Tusi galue", "Activity book"),
    ("E tu i fea Tuvalu?", "Where is Tuvalu?"),
    ("E fakaleo pefea?", "How does it sound?"),
    ("Sea te lanu tela?", "What colour is that?"),
    ("E foliga pefea a fenua?", "What do the islands look like?"),
    ("Sea te manu tela?", "What's that animal?"),
    ("I fea i toku foitino?", "Where on my body?"),
    ("Fatele: Pese, Saka a Tuvalu", "Fatele: Tuvaluan song and dance"),
    ("Te Ano: Tafaoga a Tuvalu", "Te Ano: Tuvalu's national sport"),
    ("Tofo tao mafaufau!", "Test your memory!"),
    ("Tauloto te lauga o fuainumela", "Learn how to count numbers"),
    # Key phrases
    ("fenua", "islands"),
    ("fetu", "stars"),
    ("vaueli", "vowels"),
    ("pati", "words"),
    ("galu", "waves"),
    ("manu", "animal"),
    ("lanu", "colour"),
    ("fuainumela", "numbers"),
    ("maneapa", "meeting house"),
    ("kolose", "Tuvalu crochet"),
    ("lalanga", "weaving with a needle"),
    ("fafetu", "star-shaped design"),
    ("Tuvalu mo te Atua", "Tuvalu for the Almighty"),
]


def process_tepapa_activity() -> list[dict[str, Any]]:
    """Extract vocabulary pairs from the Te Papa Tuvalu activity book."""
    path = ASSET_DIR / "Documents" / "Eng-TVL together" / "tepapa_tuvalu_activity_book_bilingual.pdf"
    rel_path = str(path.relative_to(REPO_ROOT)) if path.exists() else "tepapa_activity_book"

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for i, (tvl, en) in enumerate(TEPAPA_WORD_LISTS, 1):
        dedup_key = (tvl.lower(), en.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        rows.append(_make_seed_row(
            id_=f"unstruct:tepapa:{i:05d}",
            tvl=tvl, en=en,
            domain="tepapa_activity",
            alignment_method="manual_extraction",
            alignment_confidence=0.98,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_tepapa_activity",
            content_type="translation_phrase",
            metadata={"source_file": "tepapa_tuvalu_activity_book_bilingual.pdf"},
        ))

    print(f"  tepapa_activity: {len(rows)} pairs")
    return rows


# ── Source 6: Mormon Prayer JPGs ─────────────────────────────────────────────


def process_mormon_prayer() -> list[dict[str, Any]]:
    """OCR the Mormon prayer EN/TVL image pair."""
    base = ASSET_DIR / "Documents" / "En-TVL seperate" / "Mormon Prayer"
    en_path = base / "Mormon scrament eng.jpg"
    tvl_path = base / "Mormon sacrament tvl.jpg"

    if not en_path.exists() or not tvl_path.exists():
        print("  [skip] Mormon prayer images not found")
        return []

    en_text = _ocr_image(en_path)
    tvl_text = _ocr_image(tvl_path)
    if not en_text or not tvl_text:
        print("  [skip] OCR failed for Mormon prayer images")
        return []

    # Fix common OCR error: digit 0 → letter o in TVL text
    tvl_text = re.sub(r"\b0\b", "o", tvl_text)

    rows = [_make_seed_row(
        id_="unstruct:mormon_prayer:00001",
        tvl=tvl_text, en=en_text,
        domain="ocr_image_pair",
        alignment_method="paired_image_ocr",
        alignment_confidence=0.7,
        source_tvl=str(tvl_path.relative_to(REPO_ROOT)),
        source_en=str(en_path.relative_to(REPO_ROOT)),
        pub_code="unstruct_mormon_prayer",
        content_type="translation_paragraph",
        metadata={"ocr_engine": "tesseract"},
    )]

    print(f"  mormon_prayer: {len(rows)} pair")
    return rows


# ── Source 7: Besnier Grammar (interlinear examples) ─────────────────────────


def process_grammar() -> list[dict[str, Any]]:
    """Extract TVL/EN example pairs from Besnier's Tuvaluan grammar PDF."""
    from extract_grammar_pairs import extract_grammar_pairs

    pdf_path = (ASSET_DIR / "Linguistic Academic Guides"
                / "epdf.pub_tuvaluan-a-polynesian-language-of-the-central-pacific-"
                  "descriptive-grammars.pdf")
    if not pdf_path.exists():
        print(f"  [skip] grammar PDF not found: {pdf_path}")
        return []

    text = _pdftotext_raw(pdf_path)
    if not text.strip():
        print(f"  [skip] empty text for grammar PDF")
        return []

    pairs = extract_grammar_pairs(text)
    rows: list[dict[str, Any]] = []
    rel_path = str(pdf_path.relative_to(REPO_ROOT))

    for i, (tvl, en) in enumerate(pairs, 1):
        if not tvl.strip() or not en.strip():
            continue
        rows.append(_make_seed_row(
            id_=f"unstruct:grammar:{i:05d}",
            tvl=tvl, en=en,
            domain="grammar",
            alignment_method="interlinear_gloss",
            alignment_confidence=0.85,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_grammar_besnier",
            content_type="translation_phrase",
            metadata={"source_file": pdf_path.name, "pair_index": i},
        ))

    print(f"  grammar: {len(rows)} pairs from Besnier grammar")
    return rows


# ── Source 8: Fishes (Thaman 2015) ──────────────────────────────────────────


def process_fishes() -> list[dict[str, Any]]:
    """Extract TVL fish name / EN common name pairs from Thaman 2015."""
    from extract_species_names import extract_fish_pairs

    pdf_path = (ASSET_DIR / "Nature" / "Fauna"
                / "Thaman_2015_Fishes_Tuvalu_Tokelau.PDF.pdf")
    if not pdf_path.exists():
        print(f"  [skip] fish PDF not found: {pdf_path}")
        return []

    text = _pdftotext_layout(pdf_path)
    if not text.strip():
        print(f"  [skip] empty text for fish PDF")
        return []

    pairs = extract_fish_pairs(text)
    rows: list[dict[str, Any]] = []
    rel_path = str(pdf_path.relative_to(REPO_ROOT))

    seen: set[tuple[str, str]] = set()
    idx = 0
    for tvl, en in pairs:
        tvl, en = tvl.strip(), en.strip()
        if not tvl or not en:
            continue
        dedup_key = (tvl.lower(), en.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        idx += 1
        rows.append(_make_seed_row(
            id_=f"unstruct:fishes:{idx:05d}",
            tvl=tvl, en=en,
            domain="biodiversity",
            alignment_method="columnar_table",
            alignment_confidence=0.9,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_fishes_thaman2015",
            content_type="translation_phrase",
            metadata={"source_file": pdf_path.name, "taxon_type": "fish"},
        ))

    print(f"  fishes: {len(rows)} pairs from Thaman 2015")
    return rows


# ── Source 9: Flora (Thaman 2016) ───────────────────────────────────────────


def process_flora() -> list[dict[str, Any]]:
    """Extract TVL plant name / EN common name pairs from Thaman 2016."""
    from extract_species_names import extract_flora_pairs

    pdf_path = ASSET_DIR / "Nature" / "Thaman 2016.pdf"
    if not pdf_path.exists():
        print(f"  [skip] flora PDF not found: {pdf_path}")
        return []

    text = _pdftotext_raw(pdf_path)
    if not text.strip():
        print(f"  [skip] empty text for flora PDF")
        return []

    pairs = extract_flora_pairs(text)
    rows: list[dict[str, Any]] = []
    rel_path = str(pdf_path.relative_to(REPO_ROOT))

    seen: set[tuple[str, str]] = set()
    idx = 0
    for tvl, en in pairs:
        tvl, en = tvl.strip(), en.strip()
        if not tvl or not en:
            continue
        dedup_key = (tvl.lower(), en.lower())
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        idx += 1
        rows.append(_make_seed_row(
            id_=f"unstruct:flora:{idx:05d}",
            tvl=tvl, en=en,
            domain="biodiversity",
            alignment_method="annotated_listing",
            alignment_confidence=0.85,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_flora_thaman2016",
            content_type="translation_phrase",
            metadata={"source_file": pdf_path.name, "taxon_type": "plant"},
        ))

    print(f"  flora: {len(rows)} pairs from Thaman 2016")
    return rows


# ── Source 10: Gifts of Pai and Vau (bilingual children's book) ─────────────


def process_pai_vau() -> list[dict[str, Any]]:
    """Extract EN/TVL paragraph pairs from The Gifts of Pai and Vau."""
    from extract_bilingual_pdfs import extract_pai_vau

    pdf_path = ASSET_DIR / "Childrens books" / "The gifts of Pai and Vau-spreads.pdf"
    if not pdf_path.exists():
        print(f"  [skip] Pai & Vau PDF not found: {pdf_path}")
        return []

    text = _pdftotext_raw(pdf_path)
    if not text.strip():
        print(f"  [skip] empty text for Pai & Vau")
        return []

    pairs = extract_pai_vau(text)
    rows: list[dict[str, Any]] = []
    rel_path = str(pdf_path.relative_to(REPO_ROOT))

    for i, (en, tvl) in enumerate(pairs, 1):
        if not en.strip() or not tvl.strip():
            continue
        rows.append(_make_seed_row(
            id_=f"unstruct:pai_vau:{i:05d}",
            tvl=tvl, en=en,
            domain="childrens_book",
            alignment_method="bilingual_alternation",
            alignment_confidence=0.8,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_pai_vau",
            content_type="translation_paragraph",
            metadata={"source_file": pdf_path.name, "pair_index": i},
        ))

    print(f"  pai_vau: {len(rows)} pairs from Gifts of Pai and Vau")
    return rows


# ── Source 11: Tuvalu Toku Atufenua Pele (bilingual essays) ────────────────


def process_toku_atufenua() -> list[dict[str, Any]]:
    """Extract EN/TVL paragraph pairs from Toku Atufenua Pele."""
    from extract_bilingual_pdfs import extract_toku_atufenua

    pdf_path = ASSET_DIR / "Childrens books" / "Tuvalu Toku Atufenua Pele.pdf"
    if not pdf_path.exists():
        print(f"  [skip] Toku Atufenua PDF not found: {pdf_path}")
        return []

    text = _pdftotext_raw(pdf_path)
    if not text.strip():
        print(f"  [skip] empty text for Toku Atufenua")
        return []

    pairs = extract_toku_atufenua(text)
    rows: list[dict[str, Any]] = []
    rel_path = str(pdf_path.relative_to(REPO_ROOT))

    for i, (en, tvl) in enumerate(pairs, 1):
        if not en.strip() or not tvl.strip():
            continue
        rows.append(_make_seed_row(
            id_=f"unstruct:toku_atufenua:{i:05d}",
            tvl=tvl, en=en,
            domain="childrens_book",
            alignment_method="language_detection",
            alignment_confidence=0.75,
            source_tvl=rel_path, source_en=rel_path,
            pub_code="unstruct_toku_atufenua",
            content_type="translation_paragraph",
            metadata={"source_file": pdf_path.name, "pair_index": i},
        ))

    print(f"  toku_atufenua: {len(rows)} pairs from Toku Atufenua Pele")
    return rows


# ── Source 12: Nanumea Tales (numbered paragraph alignment) ─────────────────


def process_nanumea_tales() -> list[dict[str, Any]]:
    """Extract EN/TVL paragraph pairs from Nanumea tales."""
    from extract_bilingual_pdfs import extract_nanumea_tales

    base = ASSET_DIR / "Documents" / "nanumea"
    tale_files = [
        ("Tefolaha tale 1 - Tepou, pp 292-307 from Heirs of Tefolaha.pdf", "tale1"),
        ("Tefolaha tale 2 - Sosemea & Takitua, pp 308-316 from Heirs of Tefolaha.pdf", "tale2"),
    ]

    rows: list[dict[str, Any]] = []
    idx = 0

    for filename, slug in tale_files:
        pdf_path = base / filename
        if not pdf_path.exists():
            print(f"  [skip] {filename} not found")
            continue

        text = _pdftotext_raw(pdf_path)
        if not text.strip():
            print(f"  [skip] empty text for {filename}")
            continue

        pairs = extract_nanumea_tales(text)
        rel_path = str(pdf_path.relative_to(REPO_ROOT))

        for en, tvl in pairs:
            if not en.strip() or not tvl.strip():
                continue
            idx += 1
            rows.append(_make_seed_row(
                id_=f"unstruct:nanumea:{idx:05d}",
                tvl=tvl, en=en,
                domain="oral_tradition",
                alignment_method="numbered_paragraph",
                alignment_confidence=0.9,
                source_tvl=rel_path, source_en=rel_path,
                pub_code=f"unstruct_nanumea_{slug}",
                content_type="translation_paragraph",
                metadata={"source_file": filename, "tale": slug, "pair_index": idx},
            ))

        print(f"  nanumea {slug}: {len(pairs)} pairs from {filename}")

    print(f"  nanumea_tales total: {len(rows)} pairs")
    return rows


# ── Main ─────────────────────────────────────────────────────────────────────

ALL_SOURCES = {
    "corpus_v2": process_corpus_v2,
    "paired_pdfs": process_paired_pdfs,
    "bilingual_pdfs": process_bilingual_pdfs,
    "language_cards": process_language_cards,
    "tepapa_activity": process_tepapa_activity,
    "mormon_prayer": process_mormon_prayer,
    "grammar": process_grammar,
    "fishes": process_fishes,
    "flora": process_flora,
    "pai_vau": process_pai_vau,
    "toku_atufenua": process_toku_atufenua,
    "nanumea_tales": process_nanumea_tales,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest new unstructured TVL-EN data into Stage A seed format."
    )
    parser.add_argument("--dry-run", action="store_true", help="Report without writing.")
    parser.add_argument("--only", nargs="+", choices=list(ALL_SOURCES.keys()),
                        help="Only process specific sources.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    sources = args.only or list(ALL_SOURCES.keys())
    args.output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    summary: dict[str, int] = {}

    for name in sources:
        print(f"\n── Processing: {name} ──")
        rows = ALL_SOURCES[name]()
        raw_count = len(rows)
        rows = _postprocess_rows(rows, name)
        summary[name] = len(rows)
        total += len(rows)

        if raw_count != len(rows):
            print(f"  {name}: {raw_count} raw → {len(rows)} after cleanup")

        if rows and not args.dry_run:
            out_path = args.output_dir / f"unstruct_{name}.jsonl"
            _write_jsonl(out_path, rows)
            print(f"  → wrote {len(rows)} rows to {out_path}")

    print(f"\n── Summary ──")
    for name, count in summary.items():
        print(f"  {name}: {count} pairs")
    print(f"  TOTAL: {total} new pairs")

    if args.dry_run:
        print("\n[DRY RUN] No files written.")
    else:
        print(f"\nOutput directory: {args.output_dir}")
        print("Next steps:")
        print("  1. uv run scripts/build_stage_a_mt_data.py  # convert to chat format")
        print("  2. uv run scripts/render_training_data.py --include-unstructured  # merge into training")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
