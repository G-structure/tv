"""
Extract Tuvaluan-English example pairs from Besnier's Tuvaluan grammar PDF.

Usage:
    uv run scripts/extract_grammar_pairs.py

Requires: pdftotext (from poppler-utils)
"""

import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# Grammar abbreviations used in interlinear gloss lines.
# ---------------------------------------------------------------------------
GLOSS_ABBREVS = frozenset({
    "Anp", "Ben", "Cmp", "Cnt", "Cst", "Dxs", "Erg", "Foc", "Fut",
    "Inc", "Irr", "Itj", "Neg", "Nps", "Nrg", "Num", "Opt", "Prc",
    "Prf", "Pst", "Rcp", "Rdp", "Sbj", "Spc", "Tag", "Trn", "Voc",
})

# Section/chapter headers that appear on their own line (page headers/footers)
_SECTION_NAMES = {"Syntax", "Morphology", "Phonology", "Lexicon", "Introduction"}


# ---------------------------------------------------------------------------
# Line classification helpers
# ---------------------------------------------------------------------------

def _count_gloss_abbrevs(line: str) -> int:
    """Count how many gloss abbreviation tokens appear on the line."""
    count = 0
    for tok in line.split():
        # Tokens can be joined by +  e.g. "Foc+who?" or "Cst+Rdp+angry"
        parts = tok.replace('+', ' ').split()
        for part in parts:
            clean = part.rstrip('?.,;:!').lstrip('(')
            if clean in GLOSS_ABBREVS:
                count += 1
    return count


def _is_gloss_line(line: str, prev_tvl_line: str | None = None) -> bool:
    """Return True if the line looks like an interlinear gloss line.

    If prev_tvl_line is provided, also checks for word-count alignment with
    all-English gloss lines that lack standard abbreviation tokens.
    """
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in GLOSS_ABBREVS:
        return True
    if _count_gloss_abbrevs(stripped) >= 2:
        return True

    # If we have a previous TVL line, check for word-count aligned glosses.
    # A gloss line without abbreviations will be all-lowercase English words
    # with the same (or very close) word count as the TVL line.
    if prev_tvl_line:
        tvl_words = prev_tvl_line.strip().split()
        gloss_words = stripped.split()
        # Word counts should be close (within 2, because of multi-word glosses)
        if abs(len(tvl_words) - len(gloss_words)) <= 2 and len(gloss_words) >= 2:
            # Check if most gloss words are lowercase English
            lowercase_count = sum(
                1 for w in gloss_words
                if w[0].islower() or w.rstrip('?.,;:!') in GLOSS_ABBREVS
            )
            if lowercase_count / len(gloss_words) >= 0.6:
                # Verify at least some words look like English glosses
                eng_gloss_words = {
                    'word', 'of', 'who', 'the', 'what', 'person', 'thing',
                    'man', 'woman', 'child', 'say', 'do', 'go', 'come',
                    'make', 'give', 'take', 'see', 'hear', 'know', 'eat',
                    'sit', 'stand', 'walk', 'run', 'live', 'die', 'kill',
                    'beautiful', 'good', 'bad', 'big', 'small', 'old', 'new',
                    'laugh', 'cry', 'angry', 'happy', 'afraid', 'name',
                    'that', 'this', 'his', 'her', 'my', 'your', 'our',
                    'their', 'he', 'she', 'it', 'we', 'they', 'you',
                    'from', 'to', 'at', 'in', 'on', 'with', 'for',
                    'story', 'tune', 'year', 'day', 'night', 'time',
                    'price', 'matter', 'spouse', 'order', 'law', 'eye',
                    'different', 'custom', 'colour', 'white', 'date',
                    'month', 'island', 'land', 'house', 'canoe',
                    'sand-bank', 'boundary-stone', 'garden', 'top',
                    'bottom', 'fire', 'water', 'fish', 'bird', 'tree',
                    'coconut-tree', 'breadfruit-tree', 'large', 'short',
                    'just', 'then', 'thus', 'indeed', 'also', 'back',
                    'still', 'too', 'very', 'how?', 'where?', 'who?',
                    'what?', 'when?', 'which?', 'how-many?',
                    'constantly', 'tired', 'difficult-to', 'hard-working',
                    'drink', 'liquor', 'argue', 'fight', 'work',
                    'grandparent', 'grandchild', 'father', 'mother',
                    'brother', 'sister', 'sibling', 'ancestor',
                    'sand', 'bank', 'indeed', 'become', 'long', 'because',
                    'some', 'no', 'not', 'nor', 'if', 'but', 'and',
                    'or', 'so', 'yet', 'already', 'enough',
                }
                eng_count = sum(
                    1 for w in gloss_words
                    if w.lower().rstrip('?.,;:!') in eng_gloss_words
                    or w.rstrip('?.,;:!') in GLOSS_ABBREVS
                )
                if eng_count / len(gloss_words) >= 0.4:
                    return True

    return False


def _has_open_quote(text: str) -> bool:
    """Return True if text has an unclosed left-curly single quote."""
    depth = 0
    for ch in text:
        if ch == '\u2018':
            depth += 1
        elif ch == '\u2019':
            depth -= 1
    return depth > 0


def _is_translation_line(line: str) -> bool:
    """Return True if line contains or continues a translation in curly quotes."""
    return '\u2018' in line


def _is_example_start(line: str) -> tuple[bool, int | None]:
    """Check if line starts a new numbered example. Returns (is_start, number)."""
    # Only match numeric example numbers, not (a), (b), (c), etc.
    m = re.match(r'^\s*\((\d+)\)\s*$', line)
    if m:
        return True, int(m.group(1))
    m = re.match(r'^\s*\((\d+)\)\s+\S', line)
    if m:
        return True, int(m.group(1))
    return False, None


def _is_subsection_label(line: str) -> bool:
    """Return True if line is a subsection label like '(b) Modal verbs'.

    Must distinguish from TVL lines that start with optional elements in parens
    like '(Pe) e vau koe pe ikaai?' or '(Kee) oko ki ssuaa maasina'.
    Subsection labels have English academic words after the paren.
    """
    m = re.match(r'^\s*\([a-z]\)\s+(.+)', line)
    if not m:
        return False
    rest = m.group(1).strip()
    words = rest.lower().split()
    # Subsection labels contain English academic/grammatical terminology
    academic_words = {
        'modal', 'verbs', 'negative', 'adverbial', 'postposed', 'transitivizing',
        'demonstrative', 'approximative', 'additive', 'discourse', 'directly',
        'indirectly', 'quoted', 'transitions', 'factors', 'noun', 'possessive',
        'time', 'locative', 'causal', 'manner', 'comitative', 'expression',
        'neutral', 'leading', 'alternative', 'main', 'interrogative', 'speech',
        'subordinate', 'clauses', 'coordination', 'suffixation', 'conditionals',
        'conjuncts', 'knowledge', 'acquisition', 'achievement',
    }
    # If any of the first 3 words are academic terms, it's a subsection label
    return any(w in academic_words for w in words[:3])


def _is_section_header(line: str) -> bool:
    """Return True if line looks like a section/page header or page number."""
    stripped = line.strip()
    if re.match(r'^\d+$', stripped):
        return True
    if stripped in _SECTION_NAMES:
        return True
    if re.match(r'^\d+\s+(' + '|'.join(_SECTION_NAMES) + r')$', stripped):
        return True
    if re.match(r'^(' + '|'.join(_SECTION_NAMES) + r')\s+\d+$', stripped):
        return True
    # Sub-section numbers like "2.1.1.5.11." or "5.1.2.2.2."
    if re.match(r'^\d+(\.\d+){2,}\.?\s', stripped):
        return True
    return False


def _is_prose(line: str) -> bool:
    """
    Heuristic: return True if a line looks like running prose (not part of an example).

    Prose lines tend to be long English sentences that discuss the grammar.
    Example lines are either: TVL words, gloss abbreviations, or quoted translations.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Lines with translation quotes are never prose
    if '\u2018' in stripped:
        return False

    # Gloss lines are not prose
    if _is_gloss_line(stripped):
        return False

    # Short lines (< 45 chars) are likely TVL example text
    if len(stripped) < 45:
        return False

    # Detect English prose by checking for common English function words
    words = stripped.lower().split()
    eng_function_words = {
        'the', 'a', 'an', 'of', 'in', 'is', 'are', 'was', 'were', 'that',
        'this', 'which', 'when', 'where', 'how', 'what', 'their', 'its',
        'for', 'with', 'can', 'may', 'but', 'also', 'however', 'between',
        'from', 'used', 'as', 'be', 'or', 'and', 'not', 'if', 'than',
        'more', 'most', 'such', 'these', 'those', 'has', 'have', 'had',
        'do', 'does', 'did', 'by', 'on', 'at', 'to', 'it', 'they',
        'other', 'same', 'both', 'either', 'neither', 'only',
    }
    eng_count = sum(1 for w in words if w in eng_function_words)
    ratio = eng_count / max(len(words), 1)

    # If > 25% of words are English function words and line is long, it's prose
    if ratio > 0.25 and len(stripped) > 60:
        return True

    return False


def _extract_translations(text: str) -> str:
    """Extract text between outermost curly single quotes."""
    parts = []
    i = 0
    while i < len(text):
        start = text.find('\u2018', i)
        if start == -1:
            break
        # Find the matching closing quote (outermost)
        depth = 1
        j = start + 1
        while j < len(text) and depth > 0:
            if text[j] == '\u2018':
                depth += 1
            elif text[j] == '\u2019':
                depth -= 1
            j += 1
        end = j - 1
        parts.append(text[start + 1:end])
        i = end + 1
    return ' '.join(parts)


def _clean_tvl(text: str) -> str:
    """Clean TVL text: strip brackets, leftover number prefixes, extra whitespace."""
    # Remove leftover example number prefixes like "( 10)" at the start
    text = re.sub(r'^\s*\(\s*\d+\)\s*', '', text)
    # Remove square brackets but keep content
    text = re.sub(r'\[([^\]]*)\]', r'\1', text)
    # Remove stage-direction style brackets: [the quoted conversation...]
    # (already handled above by stripping brackets)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _clean_en(text: str) -> str:
    """Clean English translation text."""
    text = text.strip()
    text = text.strip('\u2018\u2019')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _starts_with_ungrammatical(text: str) -> bool:
    """Check if TVL text starts with * or ? (ungrammatical/marginal)."""
    stripped = text.strip()
    return stripped.startswith('*') or stripped.startswith('?')


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_grammar_pairs(text: str) -> list[tuple[str, str]]:
    """
    Extract Tuvaluan-English example pairs from pdftotext output of Besnier grammar.

    Returns list of (tvl, en) tuples.
    """
    lines = text.split('\n')

    # ---------- Pre-processing: merge split example numbers ----------
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == '(' and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            m = re.match(r'^(\d+)\)\s*$', nxt)
            if m:
                merged.append(f'({m.group(1)})')
                i += 2
                continue
            m = re.match(r'^(\d+)\)\s+(.+)$', nxt)
            if m:
                merged.append(f'({m.group(1)})  {m.group(2)}')
                i += 2
                continue
        merged.append(line)
        i += 1
    lines = merged

    # ---------- Parse example blocks ----------
    # Strategy: for each (NUMBER) marker, parse the structured block immediately
    # following it: TVL line(s) -> gloss line(s) -> translation line(s).
    # Stop as soon as we hit prose, another example, or the block structure breaks.

    pairs: list[tuple[str, str]] = []
    i = 0

    while i < len(lines):
        is_start, example_num = _is_example_start(lines[i])
        if not is_start:
            i += 1
            continue

        # Extract any TVL content on the same line as the number
        m = re.match(r'^\s*\(\d+\)\s*(.*)', lines[i])
        first_content = m.group(1).strip() if m else ''
        i += 1

        # Skip blank lines right after the number
        while i < len(lines) and not lines[i].strip():
            i += 1

        # Collect the structured block: TVL -> gloss -> translation
        # There may be multiple sub-examples within one numbered example
        # (e.g., dialogue turns: speaker T, speaker S)

        block_tvl: list[str] = []
        block_gloss: list[str] = []
        block_trans: list[str] = []

        if first_content:
            # Classify the first content
            if _is_gloss_line(first_content):
                block_gloss.append(first_content)
            elif _is_translation_line(first_content):
                block_trans.append(first_content)
            elif not _is_prose(first_content):
                block_tvl.append(first_content)
            else:
                # Prose on the same line as number — skip this "example"
                continue

        state = 'tvl'  # tvl -> gloss -> trans
        if block_gloss:
            state = 'gloss'
        if block_trans:
            state = 'trans'

        # Walk forward collecting lines that belong to this example
        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()

            # Stop at next example
            nxt_start, _ = _is_example_start(raw)
            if nxt_start:
                break

            # Skip section headers (page numbers, chapter names)
            if _is_section_header(raw):
                i += 1
                continue

            # Stop at subsection labels like "(b) Modal verbs"
            if _is_subsection_label(raw):
                break

            # Empty line
            if not stripped:
                # If we've already collected a translation, this empty line
                # might separate sub-examples within the same numbered example
                # or it might signal end of block.
                # Peek ahead to see if more example content follows.
                if state == 'trans' and block_trans:
                    # Check if next non-empty line is still part of this example
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines):
                        nxt_start2, _ = _is_example_start(lines[j])
                        nxt_stripped = lines[j].strip()
                        if (nxt_start2
                                or _is_prose(nxt_stripped)
                                or _is_section_header(lines[j])):
                            break
                        # It could be a new TVL line for a sub-example
                        # Emit current group and start a new one
                        _emit_pair(block_tvl, block_trans, pairs)
                        block_tvl = []
                        block_gloss = []
                        block_trans = []
                        state = 'tvl'
                    else:
                        break
                i += 1
                continue

            # Classify this line (pass previous TVL line for context-aware gloss detection)
            prev_tvl = block_tvl[-1] if block_tvl else None
            is_trans = _is_translation_line(stripped)
            is_gloss = _is_gloss_line(stripped, prev_tvl_line=prev_tvl)
            is_prose_line = _is_prose(stripped)

            # Handle based on current state
            if state == 'tvl':
                if is_trans:
                    block_trans.append(stripped)
                    state = 'trans'
                elif is_gloss:
                    block_gloss.append(stripped)
                    state = 'gloss'
                elif is_prose_line:
                    break
                else:
                    block_tvl.append(stripped)
            elif state == 'gloss':
                if is_trans:
                    block_trans.append(stripped)
                    state = 'trans'
                elif is_gloss:
                    block_gloss.append(stripped)
                elif is_prose_line:
                    break
                else:
                    # A non-gloss, non-trans line after gloss — could be
                    # multi-line gloss that wasn't detected, or a new TVL line.
                    # If we have no translation yet, treat as continued gloss.
                    # Otherwise break.
                    if not block_trans:
                        block_gloss.append(stripped)
                    else:
                        break
            elif state == 'trans':
                if is_trans:
                    block_trans.append(stripped)
                elif not is_trans and not is_gloss:
                    # Check if this is a continuation of an unclosed translation
                    full_trans = ' '.join(block_trans)
                    if _has_open_quote(full_trans):
                        block_trans.append(stripped)
                    elif stripped.rstrip().endswith('\u2019'):
                        block_trans.append(stripped)
                    else:
                        # Translation is done. Check if this is a new sub-example
                        # (TVL line) or prose.
                        if is_prose_line:
                            break
                        # Emit current and start new sub-example
                        _emit_pair(block_tvl, block_trans, pairs)
                        block_tvl = [stripped]
                        block_gloss = []
                        block_trans = []
                        state = 'tvl'
                elif is_gloss:
                    # Gloss after translation — new sub-example
                    _emit_pair(block_tvl, block_trans, pairs)
                    block_tvl = []
                    block_gloss = [stripped]
                    block_trans = []
                    state = 'gloss'

            i += 1

        # Emit whatever is left in the current block
        _emit_pair(block_tvl, block_trans, pairs)

    return pairs


def _emit_pair(
    tvl_lines: list[str],
    trans_lines: list[str],
    pairs: list[tuple[str, str]],
) -> None:
    """Validate and emit a (tvl, en) pair."""
    if not tvl_lines or not trans_lines:
        return

    tvl_text = ' '.join(tvl_lines)
    trans_text = ' '.join(trans_lines)

    en_text = _extract_translations(trans_text)
    if not en_text:
        return

    tvl_text = _clean_tvl(tvl_text)
    en_text = _clean_en(en_text)

    # Skip ungrammatical / marginal examples
    if _starts_with_ungrammatical(tvl_text):
        return

    if not tvl_text or not en_text:
        return

    # Skip single-word TVL (likely a gloss token or heading)
    if len(tvl_text.split()) < 2:
        return

    # Skip sub-section labels captured as TVL
    if re.match(r'^\([a-z]\)\s+[A-Z]', tvl_text):
        return

    # Skip sub-section labels like "(b) fakaaa" or "(b) i (te mea)"
    if re.match(r'^\([a-z]\)\s+', tvl_text):
        return

    # Skip if TVL starts with (cf. — a cross-reference
    if tvl_text.startswith('(cf.'):
        return

    # Skip paradigm/template lines like "(negator) (clitic pronoun)"
    # where the entire line is parenthesized words
    paren_count = tvl_text.count('(')
    if paren_count >= 3 and all(
        re.match(r'^\(', w) or w.startswith('(')
        for w in re.split(r'\s+', tvl_text)
        if w.strip()
    ):
        return

    # Skip lines that look like metalinguistic descriptions
    if re.match(r'^\(', tvl_text) and ')' in tvl_text[:20]:
        after_paren = re.sub(r'\([^)]*\)', '', tvl_text).strip()
        after_words = after_paren.lower().split()
        meta_words = {
            'verbs', 'nouns', 'modal', 'negative', 'adverbial', 'postposed',
            'transitivizing', 'suffixation', 'conditionals', 'demonstrative',
            'approximative', 'additive', 'discourse', 'conjuncts', 'negator',
            'clitic', 'pronoun',
        }
        if any(w in meta_words for w in after_words):
            return

    # Final sanity check: TVL should not look like English prose
    words = tvl_text.lower().split()
    eng_function_words = {
        'the', 'a', 'an', 'of', 'in', 'is', 'are', 'was', 'were', 'that',
        'this', 'which', 'when', 'where', 'how', 'what', 'their', 'for',
        'with', 'can', 'may', 'but', 'also', 'however', 'between', 'from',
        'as', 'be', 'or', 'and', 'not', 'if', 'than', 'by', 'on', 'it',
    }
    eng_count = sum(1 for w in words if w in eng_function_words)
    if len(words) > 6 and eng_count / len(words) > 0.40:
        return

    # Skip lexical list entries (from glossary/interjection sections) that
    # lack proper interlinear-gloss structure — they look like:
    # "word1 'def1' word2 'def2'" all on one line
    # Check: if TVL text itself contains curly quotes, it's a lexical list
    if '\u2018' in tvl_text or '\u2019' in tvl_text:
        return

    # Skip entries from the interjection/borrowing lists near the end of the book
    # These contain English metalanguage like "borrowed from Samoan"
    borrowing_markers = [
        'borrowed from', 'when beginning', 'jubilation after',
        'apology for', 'farewell', 'greeting',
        'is spotted', 'compound terms',
    ]
    if any(marker in tvl_text.lower() for marker in borrowing_markers):
        return

    # Skip section heading numbers that leaked through
    if re.match(r'^\d+(\.\d+){2,}', tvl_text):
        return

    # Skip dialect notes: "word (dialect1, dialect2...) or word (dialect3)"
    if re.search(r'\((?:Funafuti|Vaitupu|Nukufetau|Nukulaelae|Nanumea|Nui)\b', tvl_text):
        return

    # Skip long English prose lines that start with conjunctive adverbs
    prose_starters = [
        'However,', 'In contrast,', 'Furthermore,', 'Moreover,',
        'In addition,', 'Nevertheless,', 'Although ',
    ]
    if any(tvl_text.startswith(ps) for ps in prose_starters):
        return

    pairs.append((tvl_text, en_text))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    pdf_path = (
        "/Users/cuboniks/Projects/tv/unstruct_lang_data/REAL ONES ONLY/"
        "Linguistic Academic Guides/"
        "epdf.pub_tuvaluan-a-polynesian-language-of-the-central-pacific-"
        "descriptive-grammars.pdf"
    )

    result = subprocess.run(
        ["pdftotext", pdf_path, "-"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"pdftotext failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    text = result.stdout
    pairs = extract_grammar_pairs(text)

    print(f"Extracted {len(pairs)} pairs\n")
    for tvl, en in pairs[:10]:
        print(f"  TVL: {tvl}")
        print(f"  EN:  {en}")
        print()


if __name__ == "__main__":
    main()
