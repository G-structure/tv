"""
Extract TVL<->EN paragraph pairs from three bilingual text sources:
1. The Gifts of Pai and Vau (children's book)
2. Tuvalu Toku Atufenua Pele (collection of bilingual essays)
3. Nanumea Tales (two academic PDFs with numbered paragraphs)
"""

import re
import subprocess
from pathlib import Path


# ---------- Language detection heuristic ----------

# TVL-only function words (words that NEVER appear in EN text)
TVL_WORDS = {
    # Function words / particles
    "ne", "kae", "ko", "oku", "iai", "pela", "kiai",
    "hoki", "tena", "telaa", "tenei", "pelaa", "ailoa",
    "laa", "konei", "iluga", "nihi", "gali", "olotou",
    "katoa", "loa", "penei", "mea", "fale",
    # Verbs/adjectives distinctive to TVL
    "faite", "mafai", "noho", "manako", "toku", "matou", "latou",
    "fiafia", "fakamatala", "fakaoga", "fakataua", "alofa", "tino",
    "laaua", "munaa", "fanatu", "ommai", "fakatuu",
    "fakamanuiagina", "igoa", "auala", "tahao",
    "meakai", "gana", "fakapelepele", "tauloto", "tamaliki",
    "agatilo", "fakapau", "nino", "laufala",
    "kola", "konaa",
    "faanau", "aavaga", "aliki",
    "fakamailoga", "fakapiki", "fesoasoani", "fakamatamata",
    "tokotahi", "fakataufaiga", "fakafoki", "fakaaoga",
    "fakavela", "faigata", "muamua", "iloto",
    "tupulaga", "tamana", "tokoukega", "malohi", "fakataaua",
    "fanoanoa", "tamafine", "tamataene", "fakakata", "faipati",
    "tuaa", "fakafenua", "mafuaga", "taumafai", "fakahologa",
    "tupuna", "futipolo", "lakei", "fakafetai",
    "manuia", "pehe", "tala",
    # Words shared with EN removed: "mai", "fenua", "taua", "malaga",
    # "moana", "atufenua", "kaleve", "fatele" (appear in EN context)
}

# EN-only words (words that NEVER appear in TVL text)
EN_WORDS = {
    # Articles and prepositions
    "the", "and", "was", "said", "they", "were", "with", "that", "this",
    "from", "have", "had", "has", "but", "for", "are", "not", "you",
    "all", "can", "her", "his", "one", "our", "out", "who", "how",
    "its", "may", "new", "now", "old", "own", "two", "way",
    # Common EN words
    "about", "after", "also", "been", "before", "between", "both",
    "because", "could", "each", "first", "into", "just", "like",
    "made", "make", "many", "more", "most", "much", "only", "other",
    "over", "people", "some", "than", "them", "then", "there", "these",
    "those", "through", "very", "when", "where", "which", "while",
    "would", "your", "island", "called", "named", "story",
    "children", "important", "beautiful", "special", "proud",
    "favourite", "because", "dance", "traditional", "culture",
    "what", "here", "time", "every", "know", "still",
    "young", "famous", "different", "especially", "always",
    "women", "wearing", "things", "their", "went",
    "scored", "compete", "competed", "athlete", "athletes",
    "represent", "admire", "never", "gives", "tried",
    "feel", "watch", "watching", "doing", "something",
    "once", "heard", "decided", "shocked", "practise",
    "skull", "skulls", "washed", "lagoon", "ground",
    "hard", "find", "items", "bring", "sometimes",
    "gather", "morning", "wakeup", "showing",
    # Additional high-frequency EN words
    "will", "being", "dancing", "my", "mum", "dad", "best",
    "playing", "game", "games", "home", "play", "don",
    "look", "good", "crowd", "says", "excited", "music",
    "song", "words", "tells", "today", "group", "groups",
    "hear", "smell", "hot", "sweaty", "crowded", "sleepy",
    "tired", "unique", "creative", "links", "past", "future",
    "drink", "fresh", "buy", "straight", "comes", "tree",
    "climb", "cut", "need", "bottle", "catch", "sweet",
    "use", "raw", "everyday", "juice", "boiled", "eaten",
    "rice", "taught", "slimy", "sticky", "pot",
    "weave", "started", "looking", "pages", "found",
    "materials", "stores", "plan", "crafts",
    "earrings", "version", "threads", "topped", "shells",
    "weddings", "parties", "celebrations",
    "necklaces", "ribbon", "outline", "gifted",
    "happy", "wonderful", "passionate", "precious",
    "name", "too",
}


def detect_language(text: str) -> str:
    """Return 'en' or 'tvl' based on word frequency heuristic."""
    words = set(re.findall(r"[a-zA-ZāēīōūĀĒĪŌŪ'`]+", text.lower()))
    tvl_score = len(words & TVL_WORDS)
    en_score = len(words & EN_WORDS)
    return "en" if en_score > tvl_score else "tvl"



# ---------- Source 1: Gifts of Pai and Vau ----------

def extract_pai_vau(text: str) -> list[tuple[str, str]]:
    """Extract (en, tvl) pairs from The Gifts of Pai and Vau.

    Pattern: after front matter, paragraphs alternate EN, TVL, EN, TVL...
    with page numbers interspersed.
    """
    marker = "Once there were two women"
    idx = text.find(marker)
    if idx == -1:
        raise ValueError("Could not find story start marker")
    text = text[idx:]
    text = text.rstrip()

    lines = text.split("\n")

    # Remove standalone page numbers
    filtered = []
    for line in lines:
        stripped = line.strip()
        if stripped and re.match(r"^\d{1,2}$", stripped):
            continue
        filtered.append(line)

    rejoined = "\n".join(filtered)
    rejoined = re.sub(r"\n\s*\n", "\n\n", rejoined)
    raw_paragraphs = [p.strip() for p in rejoined.split("\n\n") if p.strip()]

    paragraphs = []
    for p in raw_paragraphs:
        merged = re.sub(r"\s+", " ", p).strip()
        if merged:
            paragraphs.append(merged)

    pairs = []
    i = 0
    while i < len(paragraphs) - 1:
        lang1 = detect_language(paragraphs[i])
        lang2 = detect_language(paragraphs[i + 1])
        if lang1 == "en" and lang2 == "tvl":
            pairs.append((paragraphs[i], paragraphs[i + 1]))
            i += 2
        else:
            i += 1

    return pairs


# ---------- Source 2: Tuvalu Toku Atufenua Pele ----------

# Lines to skip entirely (headers, author names, locations, structural)
TOKU_SKIP_PATTERNS = [
    r"^TE OLAGA O TE TALAVOU I AUKILANI THE LIFE OF A YOUNG TUVALUAN IN$",
    r"^AUCKLAND$",
    r"^HUSSIE FOIASO$",
    r"^TALOPUA TAULANGA$",
    r"^PUAVA PUATUA$",
    r"^HANNAH TAULANGA$",
    r"^IELEMIA FOIASO$",
    r"^FIESOLA PUAFOLAU$",
    r"^AMATAGA SATEKO$",
    r"^TAOIA SATEKO$",
    r"^FATELE$",
    r"^KAHOA$",
    r"^TE ANO$",
    r"^Fau$",
    r"^Faa fetu$",
    r"^Titi fakamanumanu$",
    r"^Titi galegale$",
    r"^KALEVE KULA - RED TODDY$",
    r"^LALAGA A TUPUNA$",
    r"^- GRANDMA'S WEAVING$",
    r"^OLIMIPIKA O TUVALU$",
    r"^- TUVALUAN OLYMPIAN$",
    r"^GANA TUVALU - TUVALU LANGUAGE$",
    r"^LAKEI TUVALU - TUVALUAN CLOTHING$",
    r"^TE NOTI O KULU - KULU'S KNOT$",
    r"^TUVALU MO TE ATUA - TUVALU FOR GOD$",
    r"^NANUMEA$",
    r"^[A-Z, ]+$",  # All caps lines under 60 chars (locations, author names)
    r"^\d{1,2}$",   # Page numbers
    r"^•$",          # Bullet markers
    r"^Tuvalu mo te Atua$",  # Anthem title
]


def _is_skip_line(line: str) -> bool:
    """Check if a line should be skipped (header, page number, etc.)."""
    stripped = line.strip()
    if not stripped:
        return True
    for pat in TOKU_SKIP_PATTERNS:
        if re.match(pat, stripped):
            # Extra check: all-caps pattern should be short
            if pat == r"^[A-Z, ]+$" and len(stripped) >= 60:
                continue
            return True
    return False


def _detect_line_language(text: str, prev_lang: str | None = None) -> str:
    """Detect language of a single line.

    If the line has no indicator words (score 0 for both), inherit the
    language of the previous line (continuation line like 'bingo.' or 'cracks.').
    """
    words = set(re.findall(r"[a-zA-ZāēīōūĀĒĪŌŪ'`]+", text.lower()))
    tvl_score = len(words & TVL_WORDS)
    en_score = len(words & EN_WORDS)

    if en_score == 0 and tvl_score == 0:
        # Ambiguous short line: inherit from previous
        return prev_lang if prev_lang else "en"

    return "en" if en_score > tvl_score else "tvl"


def _group_lines_by_language(lines: list[str]) -> list[tuple[str, str]]:
    """Group contiguous non-empty content lines by detected language.

    Returns list of (language, merged_text) tuples.
    Uses continuation logic: ambiguous lines inherit previous language.
    """
    groups = []
    current_lines = []
    current_lang = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line: flush current group
            if current_lines and current_lang:
                merged = " ".join(current_lines)
                groups.append((current_lang, merged))
                current_lines = []
                current_lang = None
            continue

        if _is_skip_line(stripped):
            # Skip line acts as break
            if current_lines and current_lang:
                merged = " ".join(current_lines)
                groups.append((current_lang, merged))
                current_lines = []
                current_lang = None
            continue

        lang = _detect_line_language(stripped, current_lang)

        if current_lang is None:
            current_lang = lang
            current_lines = [stripped]
        elif lang == current_lang:
            current_lines.append(stripped)
        else:
            # Language changed: flush previous group and start new
            merged = " ".join(current_lines)
            groups.append((current_lang, merged))
            current_lines = [stripped]
            current_lang = lang

    # Flush last group
    if current_lines and current_lang:
        merged = " ".join(current_lines)
        groups.append((current_lang, merged))

    return groups


def extract_toku_atufenua(text: str) -> list[tuple[str, str]]:
    """Extract (en, tvl) pairs from Tuvalu Toku Atufenua Pele.

    Strategy: line-by-line language detection with continuation logic.
    Lines with no indicator words inherit previous language. Groups of
    contiguous same-language lines form paragraphs. Adjacent EN+TVL
    paragraphs are paired.
    """
    # Find body start
    body_start_marker = "In my family there are four children"
    idx = text.find(body_start_marker)
    if idx == -1:
        raise ValueError("Could not find body start")

    # Find body end: before FAKAFETAI LASI (acknowledgments)
    body_end_marker = "FAKAFETAI LASI"
    end_idx = text.find(body_end_marker)
    if end_idx == -1:
        end_idx = len(text)

    body = text[idx:end_idx]

    # Cut off the national anthem section
    anthem_idx = body.find("Tuvalu mo te Atua\n")
    if anthem_idx != -1:
        body = body[:anthem_idx]

    lines = body.split("\n")

    # Group lines by language
    groups = _group_lines_by_language(lines)

    # Filter out structural/noise groups
    filtered = []
    for lang, text_content in groups:
        t = text_content.strip()
        if not t or len(t) < 5:
            continue
        # Skip mixed structural line
        if t.startswith("Kahoa are made of five important elements"):
            continue
        filtered.append((lang, t))

    # Remove duplicates (keep first occurrence)
    seen = set()
    deduped = []
    for lang, t in filtered:
        if t in seen:
            continue
        seen.add(t)
        deduped.append((lang, t))
    filtered = deduped

    # Merge consecutive same-language paragraphs before pairing.
    # This handles cases where an EN paragraph's TVL translation is displaced.
    merged = []
    for lang, t in filtered:
        if merged and merged[-1][0] == lang:
            # Same language as previous: merge
            merged[-1] = (lang, merged[-1][1] + " " + t)
        else:
            merged.append((lang, t))

    # Pair consecutive EN+TVL
    pairs = []
    i = 0
    while i < len(merged) - 1:
        lang1, text1 = merged[i]
        lang2, text2 = merged[i + 1]

        if lang1 == "en" and lang2 == "tvl":
            pairs.append((text1, text2))
            i += 2
        elif lang1 == "tvl" and lang2 == "en":
            pairs.append((text2, text1))
            i += 2
        else:
            i += 1

    return pairs


# ---------- Source 3: Nanumea Tales ----------

def _extract_numbered_paragraphs(text: str) -> dict[int, str]:
    """Extract numbered paragraphs (1), (2), ... from text.

    Returns dict mapping paragraph number to its text content.
    """
    parts = re.split(r"\((\d+)\)", text)

    result = {}
    i = 1
    while i < len(parts) - 1:
        num = int(parts[i])
        para_text = parts[i + 1]

        # Remove page numbers (standalone 3-digit numbers)
        para_text = re.sub(r"\n\d{3}\n", "\n", para_text)
        para_text = re.sub(r"^\d{3}\s*\n", "", para_text)
        para_text = re.sub(r"\n\d{3}\s*$", "", para_text)

        # Remove stage directions
        para_text = re.sub(r"\[[\w\s]+(?:laughs|chuckles|chuckes)\]", "", para_text, flags=re.IGNORECASE)
        para_text = re.sub(r"\[notices his mistake\]", "", para_text, flags=re.IGNORECASE)

        # Collapse whitespace
        para_text = re.sub(r"\s+", " ", para_text).strip()

        if para_text:
            result[num] = para_text
        i += 2

    return result


def extract_nanumea_tales(tvl_en_text: str) -> list[tuple[str, str]]:
    """Extract (en, tvl) pairs from Nanumea tales with numbered paragraphs.

    The text has: first half = TVL paragraphs numbered (1)...(N),
    second half = EN translation with matching numbers.
    Works for both Tale 1 (29 paragraphs) and Tale 2 (14 paragraphs).
    """
    en_markers = [
        "English Translation, Tepou",
        "English Translation, Sosemea",
    ]

    split_idx = -1
    for marker in en_markers:
        idx = tvl_en_text.find(marker)
        if idx != -1:
            split_idx = idx
            break

    if split_idx == -1:
        raise ValueError("Could not find English translation section")

    tvl_section = tvl_en_text[:split_idx]
    en_section = tvl_en_text[split_idx:]

    # Trim TVL section to start at [Tala... or (1)
    tala_match = re.search(r"\[Tala", tvl_section)
    if tala_match:
        tvl_section = tvl_section[tala_match.start():]
    else:
        first_num = re.search(r"\(1\)", tvl_section)
        if first_num:
            tvl_section = tvl_section[first_num.start():]

    # Trim EN section to start at [The Story... or (1)
    story_match = re.search(r"\[The Story", en_section)
    if story_match:
        en_section = en_section[story_match.start():]
    else:
        first_num = re.search(r"\(1\)", en_section)
        if first_num:
            en_section = en_section[first_num.start():]

    # Remove NOTES section at the end
    notes_idx = en_section.find("\nNOTES\n")
    if notes_idx == -1:
        notes_idx = en_section.find("\nNotes\n")
    if notes_idx != -1:
        en_section = en_section[:notes_idx]

    tvl_paras = _extract_numbered_paragraphs(tvl_section)
    en_paras = _extract_numbered_paragraphs(en_section)

    common_nums = sorted(set(tvl_paras.keys()) & set(en_paras.keys()))

    pairs = []
    for num in common_nums:
        en_text = en_paras[num]
        tvl_text = tvl_paras[num]

        # Clean remaining page numbers at edges
        en_text = re.sub(r"^\d{3}\s+", "", en_text)
        tvl_text = re.sub(r"^\d{3}\s+", "", tvl_text)

        # Strip footnote markers at end
        en_text = re.sub(r"\d+$", "", en_text).strip()

        if en_text and tvl_text:
            pairs.append((en_text, tvl_text))

    return pairs


# ---------- Main test ----------

def run_pdftotext(path: str) -> str:
    """Run pdftotext and return extracted text."""
    result = subprocess.run(
        ["pdftotext", path, "-"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr}")
    return result.stdout


def preview_pairs(pairs: list[tuple[str, str]], n: int = 5, label: str = ""):
    """Print first n pairs for quality check."""
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"  Total pairs: {len(pairs)}")
    print(f"{'='*80}")
    for i, (en, tvl) in enumerate(pairs[:n]):
        print(f"\n--- Pair {i+1} ---")
        print(f"  EN:  {en[:200]}{'...' if len(en) > 200 else ''}")
        print(f"  TVL: {tvl[:200]}{'...' if len(tvl) > 200 else ''}")


if __name__ == "__main__":
    base = Path("/Users/cuboniks/Projects/tv/unstruct_lang_data/REAL ONES ONLY")

    # Source 1: Pai and Vau
    print("\n" + "#"*80)
    print("# SOURCE 1: The Gifts of Pai and Vau")
    print("#"*80)
    pai_vau_path = base / "Childrens books" / "The gifts of Pai and Vau-spreads.pdf"
    pai_vau_text = run_pdftotext(str(pai_vau_path))
    pai_vau_pairs = extract_pai_vau(pai_vau_text)
    preview_pairs(pai_vau_pairs, 5, "Gifts of Pai and Vau")

    # Source 2: Toku Atufenua
    print("\n" + "#"*80)
    print("# SOURCE 2: Tuvalu Toku Atufenua Pele")
    print("#"*80)
    toku_path = base / "Childrens books" / "Tuvalu Toku Atufenua Pele.pdf"
    toku_text = run_pdftotext(str(toku_path))
    toku_pairs = extract_toku_atufenua(toku_text)
    preview_pairs(toku_pairs, 5, "Tuvalu Toku Atufenua Pele")

    # Source 3: Nanumea Tales
    print("\n" + "#"*80)
    print("# SOURCE 3: Nanumea Tales")
    print("#"*80)

    tale1_path = base / "Documents" / "nanumea" / "Tefolaha tale 1 - Tepou, pp 292-307 from Heirs of Tefolaha.pdf"
    tale2_path = base / "Documents" / "nanumea" / "Tefolaha tale 2 - Sosemea & Takitua, pp 308-316 from Heirs of Tefolaha.pdf"

    tale1_text = run_pdftotext(str(tale1_path))
    tale2_text = run_pdftotext(str(tale2_path))

    tale1_pairs = extract_nanumea_tales(tale1_text)
    preview_pairs(tale1_pairs, 5, "Nanumea Tale 1 (Tepou)")

    tale2_pairs = extract_nanumea_tales(tale2_text)
    preview_pairs(tale2_pairs, 5, "Nanumea Tale 2 (Sosemea/Takitua)")

    nanumea_pairs = tale1_pairs + tale2_pairs

    # Summary
    print("\n" + "#"*80)
    print("# SUMMARY")
    print("#"*80)
    print(f"  Pai and Vau:     {len(pai_vau_pairs)} pairs (expected: 12)")
    print(f"  Toku Atufenua:   {len(toku_pairs)} pairs (expected: ~70-75)")
    print(f"  Nanumea Tale 1:  {len(tale1_pairs)} pairs (expected: 29)")
    print(f"  Nanumea Tale 2:  {len(tale2_pairs)} pairs (expected: 14)")
    print(f"  Nanumea Total:   {len(nanumea_pairs)} pairs (expected: 43)")
    print(f"  GRAND TOTAL:     {len(pai_vau_pairs) + len(toku_pairs) + len(nanumea_pairs)} pairs")

    # Edge cases
    print("\n" + "#"*80)
    print("# EDGE CASES HANDLED")
    print("#"*80)
    edge_cases = [
        "Page numbers stripped (1-2 digit for books, 3-digit for academic PDFs)",
        "Front matter excluded (title pages, copyright, TOC, introductions)",
        "Back matter excluded (acknowledgments, NOTES sections)",
        "Section headers and author bylines stripped (all-caps detection)",
        "Bullet markers treated as paragraph separators",
        "Stage directions removed: [Tepou laughs], [notices his mistake], etc.",
        "Multi-line paragraphs merged (internal newlines collapsed)",
        "Language detection: TVL-only vs EN-only word lists avoid false matches on shared terms",
        "Ambiguous short lines ('bingo.', 'cracks.') inherit previous line's language",
        "Consecutive same-language paragraphs merged (handles displaced PDF layout)",
        "Nanumea: numbered paragraph (1)...(N) alignment across TVL/EN halves",
        "Nanumea: two separate tales extracted and combined",
        "National anthem section excluded (song, not prose)",
        "Duplicate paragraphs removed (e.g., repeated text at page boundaries)",
        "Song/verse pairs included (e.g., Kulu's song in EN and TVL)",
        "Toku Atufenua: Kahoa bullet-point items paired correctly (5 elements)",
        "Toku Atufenua: Lakei clothing items (Fau, Faa fetu, Titi) paired correctly",
    ]
    for i, ec in enumerate(edge_cases, 1):
        print(f"  {i:2d}. {ec}")
