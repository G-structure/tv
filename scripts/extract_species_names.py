"""
Extract Tuvaluan-English species name pairs from biodiversity PDFs.

Document 1: Thaman 2015 — Fishes of Tuvalu (Appendix III columnar table)
Document 2: Thaman 2016 — Flora of Tuvalu (annotated systematic listing)
"""

import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Atoll / source codes to strip from Tuvaluan names
_ATOLL_PAREN = re.compile(
    r"\s*\([^)]*\b(?:Ff|Nm|Nt|Nui|Vt|Nf|Nl|Ng|Tv|At|TvD|Tvd|TvFP|NB|Nb)\b[^)]*\)"
)
# Size / stage markers in fish names
_SIZE_MARKER = re.compile(r"\s*[–-]\s*(?:sm\.|lg\.|v\.lg\.|juv\.|adult|young|postlarvae|post-?\s*larvae)")
# Question marks
_QMARK = re.compile(r"\s*\?")
# Parenthesized source citations like (Seluka 1997), (Maiden 1904), (Koch 2002), (Woodroffe 1991)
_SOURCE_CITE = re.compile(r"\s*\([^)]*\b(?:Seluka|Maiden|Koch|Woodroffe|TvD|Tvd|TvFP)\b[^)]*\)")
# Parenthesized descriptors like ("Christmas tree"), ("pine tree")
_PAREN_DESC = re.compile(r'\s*\("[^"]*"\s*(?:;\s*[^)]+)?\)')
# Parenthesized qualifiers like (plant), (fronds), (edible; Ff), (name of...)
_PAREN_QUAL = re.compile(r"\s*\((?:plant|fronds|edible|name\s+of)[^)]*\)")
# Generic leftover parentheticals (atoll codes etc)
_PAREN_GENERIC = re.compile(r"\s*\([^)]*\)")


def _clean_tvl_name(raw: str) -> str:
    """Strip atoll codes, size markers, question marks, source citations from a TVL name."""
    s = raw.strip()
    s = _SIZE_MARKER.sub("", s)
    s = _QMARK.sub("", s)
    s = _SOURCE_CITE.sub("", s)
    s = _PAREN_DESC.sub("", s)
    s = _PAREN_QUAL.sub("", s)
    s = _ATOLL_PAREN.sub("", s)
    # Strip any remaining parenthetical atoll/source codes
    s = _PAREN_GENERIC.sub("", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    # Remove trailing commas, semicolons, hyphens
    s = s.strip(" ,;-–")
    return s


# Known atoll abbreviations that can appear as stray tokens after paren stripping
_ATOLL_CODES = {"Ff", "Nm", "Nt", "Nui", "Vt", "Nf", "Nl", "Ng", "Tv", "At", "NB", "Nb"}
_ATOLL_CODES_LOWER = {c.lower() for c in _ATOLL_CODES}


def _strip_balanced_parens(text: str) -> str:
    """Remove all balanced (...) content from text, handling nested parens."""
    result = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            result.append(ch)
    return "".join(result)


def _strip_all_parens(text: str) -> str:
    """Remove all parenthetical content, size markers, and question marks from text."""
    s = text
    s = _SIZE_MARKER.sub("", s)
    s = _QMARK.sub("", s)
    # Use balanced paren stripping to handle commas inside parens
    s = _strip_balanced_parens(s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


def _is_valid_tvl_name(name: str) -> bool:
    """Check if a cleaned name is a valid Tuvaluan name (not an atoll code, marker, etc.)."""
    if not name or len(name) <= 1:
        return False
    # Skip atoll codes
    if name in _ATOLL_CODES or name.lower() in _ATOLL_CODES_LOWER:
        return False
    # Skip no-name markers
    if name in ("Np", "Nn", "Fn", "nn", "np"):
        return False
    # Skip if it starts with Nn/Np and is short (like "Nn – IP")
    if re.match(r"^(?:Nn|Np|Fn)\b", name):
        return False
    # Skip size/stage qualifiers that leaked through
    if re.match(r"^(?:sm|lg|juv|adult|young|IP|TP)\.?$", name, re.IGNORECASE):
        return False
    return True


def _split_names(text: str, sep: str = ",") -> list[str]:
    """Strip parentheticals first, then split on separator, return non-empty unique names."""
    cleaned = _strip_all_parens(text)
    parts = cleaned.split(sep)
    seen = set()
    result = []
    for p in parts:
        name = p.strip().strip(" ,;-–")
        if _is_valid_tvl_name(name) and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


# ---------------------------------------------------------------------------
# Fish extraction
# ---------------------------------------------------------------------------

# Families end in -idae
_FAMILY_RE = re.compile(r"\b[A-Z][a-z]+idae\b")
# "No name" markers
_NO_NAME = {"Np", "Nn", "Fn"}


def extract_fish_pairs(text: str) -> list[tuple[str, str]]:
    """Extract (tvl_name, en_common_name) pairs from fish PDF layout text.

    The Appendix III table has columns separated by whitespace:
    Tuvaluan name | Tokelauan name | Scientific name | Family | Common name | Sources

    Strategy:
    1. Find lines containing a Family name (ending in -idae).
    2. Parse columns by finding Family position and working backwards/forwards.
    3. Join multi-line continuations (lines without a Family name that follow a data line).
    """
    lines = text.split("\n")

    # Find start of Appendix III
    start_idx = 0
    for i, line in enumerate(lines):
        if "Appendix III" in line and "Complete listing" in line:
            start_idx = i
            break

    pairs = []
    # Track lines from start_idx onward
    data_lines = lines[start_idx:]

    # First pass: identify rows. Each row has a Family name somewhere.
    # Multi-line entries continue on the next line(s) without a Family.
    rows: list[str] = []
    in_data = False

    for line in data_lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip header lines
        if stripped.startswith("Tuvaluan name") and "Tokelauan" in stripped:
            in_data = True
            continue
        if stripped == "Finfish" or stripped == "Sharks" or stripped == "Rays" or stripped == "Eels":
            continue
        # Skip page numbers (standalone numbers)
        if re.match(r"^\d+$", stripped):
            continue

        if not in_data:
            continue

        # Check if this line has a Family name
        if _FAMILY_RE.search(line):
            rows.append(line)
        elif rows:
            # Continuation of previous row
            rows[-1] = rows[-1] + " " + stripped

    # Second pass: parse each row into columns
    for row in rows:
        # Find the Family name and its position
        fam_match = _FAMILY_RE.search(row)
        if not fam_match:
            continue

        family = fam_match.group()
        fam_start = fam_match.start()
        fam_end = fam_match.end()

        # Everything after family is: Common name + Sources
        after_family = row[fam_end:].strip()

        # Sources are at the end, typically abbreviated codes separated by commas
        # Common name is everything before the last cluster of source abbreviations
        # Source codes pattern: uppercase letter sequences, often with &
        # Split: find where the common name ends and sources begin
        # Sources are separated from common name by multiple spaces or we can use
        # the fact that sources contain patterns like "Tvd, TkD, NB, ..." etc.

        # Find common name: text between family and sources
        # Sources typically start after significant whitespace gap
        common_name = ""
        # Try splitting on double-space or more
        parts = re.split(r"\s{2,}", after_family, maxsplit=1)
        if parts:
            common_name = parts[0].strip()

        # If common name looks like source codes, skip
        if not common_name or re.match(r"^[A-Z][a-z]*[,&]", common_name) and len(common_name) < 20:
            continue

        # Clean common name: remove trailing source codes
        # Source codes pattern at end
        common_name = re.sub(r"\s+[A-Z][A-Za-z&]*(?:,\s*[A-Za-z&]+)*\s*$", "", common_name).strip()

        # Before family: contains Tuvaluan name | Tokelauan name | Scientific name
        before_family = row[:fam_start].strip()

        # Scientific name is right before the family — it's in italics (Latin binomial)
        # Pattern: Genus species (or Genus sp. or Genus spp.)
        sci_match = re.search(
            r"((?:Cf\.\s+)?[A-Z][a-z]+\s+(?:[a-z]+(?:\s*/[a-z]+)?|sp\.?|spp\.?)(?:\s*\?)?)\s*$",
            before_family,
        )
        if sci_match:
            before_sci = before_family[: sci_match.start()].strip()
        else:
            before_sci = before_family

        # before_sci has: Tuvaluan name | Tokelauan name (separated by large whitespace gaps)
        # Split on large whitespace (3+ spaces)
        name_parts = re.split(r"\s{3,}", before_sci)

        tvl_raw = name_parts[0].strip() if name_parts else ""

        # Skip entries with no Tuvaluan name
        if not tvl_raw:
            continue

        # Check for "no name" markers
        tvl_check = tvl_raw.split(",")[0].split("(")[0].strip()
        if tvl_check in _NO_NAME:
            # Check if there's more after the Np/Nn
            # e.g., "Nn (Ff, Nm), tifitifi laufou" — the second part IS a name
            remaining = tvl_raw
            # Remove the Np/Nn prefix
            remaining = re.sub(r"^(?:Np|Nn|Fn)\s*(?:\([^)]*\))?\s*,?\s*", "", remaining).strip()
            if not remaining or remaining.split(",")[0].split("(")[0].strip() in _NO_NAME:
                continue
            tvl_raw = remaining

        # Handle "Nn or manoko" patterns — extract the actual name part
        nn_or_match = re.match(r"^(?:Nn|Np|Fn)\s+or\s+(.+)", tvl_raw)
        if nn_or_match:
            tvl_raw = nn_or_match.group(1).strip()

        if not common_name:
            continue

        # Split Tuvaluan names on comma (variant names)
        tvl_names = _split_names(tvl_raw, ",")

        for name in tvl_names:
            if name and len(name) > 1:
                pairs.append((name, common_name))

    return pairs


# ---------------------------------------------------------------------------
# Flora extraction
# ---------------------------------------------------------------------------


def extract_flora_pairs(text: str) -> list[tuple[str, str]]:
    """Extract (tvl_name, en_common_name) pairs from flora PDF text.

    Entries follow the pattern:
        Scientific Name
        Common Name(s): ...
        Tuvaluan Name(s): ...
        Status: ...

    Some entries have no Tuvaluan name. Some have no Common Name.
    """
    lines = text.split("\n")
    pairs = []

    # Find the start of the annotated listing
    start_idx = 0
    for i, line in enumerate(lines):
        if "PTERIDOPHYTA" in line:
            start_idx = i
            break

    # Process lines looking for Common Name / Tuvaluan Name pairs
    current_common: list[str] = []
    current_tvl: list[str] = []
    in_common = False
    in_tvl = False

    for i in range(start_idx, len(lines)):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            in_common = False
            in_tvl = False
            continue

        # Detect Common Name line
        common_match = re.match(r"^Common\s+Names?\s*:\s*(.+)", stripped)
        if common_match:
            # If we had a previous TVL+Common pair buffered, flush it
            if current_tvl and current_common:
                _flush_flora_pairs(current_tvl, current_common, pairs)

            current_common = [common_match.group(1).strip()]
            current_tvl = []
            in_common = True
            in_tvl = False
            continue

        # Detect Tuvaluan Name line
        tvl_match = re.match(r"^Tuvaluan\s+Names?\s*:\s*(.+)", stripped)
        if tvl_match:
            current_tvl = [tvl_match.group(1).strip()]
            in_common = False
            in_tvl = True
            continue

        # Detect Status/Abundance/Remarks/Recorded/Voucher — these end a block
        if re.match(r"^(?:Status|Abundance|Remarks|Recorded|Voucher|Synonym)", stripped):
            if current_tvl and current_common:
                _flush_flora_pairs(current_tvl, current_common, pairs)
                current_tvl = []
            in_common = False
            in_tvl = False
            continue

        # Detect new scientific name or family header — flush
        if re.match(r"^[A-Z][A-Z]+(?:\s|$)", stripped):  # ALL CAPS = family or section header
            if current_tvl and current_common:
                _flush_flora_pairs(current_tvl, current_common, pairs)
                current_tvl = []
                current_common = []
            in_common = False
            in_tvl = False
            continue

        # Detect new scientific name (Genus species pattern at start of line)
        if re.match(r"^[A-Z][a-z]+\s+[a-z]", stripped) and not in_tvl and not in_common:
            if current_tvl and current_common:
                _flush_flora_pairs(current_tvl, current_common, pairs)
                current_tvl = []
            in_common = False
            in_tvl = False
            continue

        # Continuation lines
        if in_common:
            current_common.append(stripped)
        elif in_tvl:
            current_tvl.append(stripped)

    # Final flush
    if current_tvl and current_common:
        _flush_flora_pairs(current_tvl, current_common, pairs)

    return pairs


def _flush_flora_pairs(
    tvl_lines: list[str], common_lines: list[str], pairs: list[tuple[str, str]]
):
    """Parse buffered TVL and Common name lines into pairs."""
    tvl_text = " ".join(tvl_lines)
    common_text = " ".join(common_lines)

    # Clean common names — just take the text, split on comma/semicolon for variants
    common_names = []
    for part in re.split(r"[,;]", common_text):
        cn = part.strip().strip(".,;")
        if cn and len(cn) > 1:
            common_names.append(cn)

    if not common_names:
        return

    # Use first common name as the primary English name
    en_name = common_names[0]

    # Clean TVL names: strip all parenthetical content first, then split
    tvl_cleaned = _strip_all_parens(tvl_text)

    # Now split on semicolons and commas
    tvl_names = []
    seen = set()
    for part in re.split(r"[;,]", tvl_cleaned):
        name = part.strip().strip(" ,;-–")
        # Remove any stray quotes
        name = name.strip('"\'')
        if not _is_valid_tvl_name(name):
            continue
        if name.lower() in seen:
            continue
        # Skip if it looks like a description rather than a name
        if any(
            kw in name.lower()
            for kw in ["name of", "cooked as", "edible", "when", "thorns that"]
        ):
            continue
        # Skip page numbers
        if re.match(r"^\d+$", name):
            continue
        seen.add(name.lower())
        tvl_names.append(name)

    for tvl in tvl_names:
        pairs.append((tvl, en_name))


# ---------------------------------------------------------------------------
# Main: run both extractors against the actual PDFs
# ---------------------------------------------------------------------------


def main():
    fish_pdf = "/Users/cuboniks/Projects/tv/unstruct_lang_data/REAL ONES ONLY/Nature/Fauna/Thaman_2015_Fishes_Tuvalu_Tokelau.PDF.pdf"
    flora_pdf = "/Users/cuboniks/Projects/tv/unstruct_lang_data/REAL ONES ONLY/Nature/Thaman 2016.pdf"

    # Extract text from PDFs
    print("=== Extracting text from fish PDF (layout mode) ===")
    fish_result = subprocess.run(
        ["pdftotext", "-layout", fish_pdf, "-"],
        capture_output=True,
        text=True,
    )
    fish_text = fish_result.stdout

    print("=== Extracting text from flora PDF ===")
    flora_result = subprocess.run(
        ["pdftotext", flora_pdf, "-"],
        capture_output=True,
        text=True,
    )
    flora_text = flora_result.stdout

    # Run extractors
    fish_pairs = extract_fish_pairs(fish_text)
    flora_pairs = extract_flora_pairs(flora_text)

    # Report results
    def _report(label: str, pairs: list[tuple[str, str]]):
        print(f"\n{'='*60}")
        print(f"{label}: {len(pairs)} total pairs")
        print(f"{'='*60}")

        unique_tvl = set(t.lower() for t, _ in pairs)
        unique_en = set(e.lower() for _, e in pairs)
        multi_word = [(t, e) for t, e in pairs if " " in t]
        print(f"  Unique TVL names: {len(unique_tvl)}")
        print(f"  Unique EN names:  {len(unique_en)}")
        print(f"  Multi-word TVL:   {len(multi_word)}")

        print("\nFirst 10 pairs:")
        for i, (tvl, en) in enumerate(pairs[:10]):
            print(f"  {i+1:3d}. {tvl:<35s} -> {en}")

        print(f"\nLast 5 pairs:")
        for i, (tvl, en) in enumerate(pairs[-5:]):
            print(f"  {len(pairs)-4+i:3d}. {tvl:<35s} -> {en}")

        print("\nEdge cases handled:")
        stray_parens = [(t, e) for t, e in pairs if "(" in t or ")" in t]
        nn_markers = [(t, e) for t, e in pairs if t.lower().startswith(("nn", "np", "fn"))]
        src_in_en = [(t, e) for t, e in pairs if any(c in e for c in ["Tvd", "TkD", "RAS", "JER"])]
        print(f"  Stray parentheses in TVL names: {len(stray_parens)}")
        print(f"  No-name markers leaked:         {len(nn_markers)}")
        print(f"  Source codes in EN names:        {len(src_in_en)}")

        # Sample multi-word names
        print(f"\nSample multi-word TVL names:")
        for tvl, en in multi_word[:5]:
            print(f"  {tvl:<35s} -> {en}")

    _report("FISH", fish_pairs)
    _report("FLORA", flora_pairs)

    # Combined stats
    all_tvl = set(t.lower() for t, _ in fish_pairs + flora_pairs)
    print(f"\n{'='*60}")
    print(f"COMBINED: {len(fish_pairs) + len(flora_pairs)} total pairs")
    print(f"  Unique TVL names across both: {len(all_tvl)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
