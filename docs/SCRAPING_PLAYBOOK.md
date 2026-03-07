# Scraping Playbook: Tuvaluan-English Parallel Corpus

A step-by-step guide to reproduce the full data collection pipeline. This playbook documents every script, command, and decision made to build the corpus from scratch.

## Prerequisites

### System requirements

- **macOS** (tested on Apple Silicon / Darwin 25.2.0) or Linux
- **Docker Desktop** (required for curl-impersonate)
- **Python 3.14+** (via Homebrew or system package manager)
- **uv** (Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Why Docker curl-impersonate?

Both `jw.org` and `wol.jw.org` perform TLS fingerprint detection. Standard HTTP clients all fail:

| Client | Result |
|---|---|
| `requests` | Timeout after 30s |
| `httpx` (HTTP/2) | Works once, then `StreamReset error_code:2` |
| `curl` (system) | Exit 92 / Exit 56 |
| **Docker curl-impersonate** | **200 OK** (reliable) |

The sites reject connections whose TLS handshake doesn't match a known browser fingerprint. `curl-impersonate` mimics Firefox 117's TLS/HTTP fingerprint.

### Bootstrap

```bash
# 1. Clone the repository
git clone <repo-url> tv && cd tv

# 2. Install Python dependencies
uv sync

# 3. Pull the curl-impersonate Docker image
docker pull lwthiker/curl-impersonate:0.6-ff

# 4. Verify Docker works
docker run --rm lwthiker/curl-impersonate:0.6-ff \
  curl_ff117 -s -o /dev/null -w "HTTP %{http_code}\n" \
  "https://www.jw.org/tvl/sitemap.xml"
# Expected output: HTTP 200

# 5. Verify Python + fetch works
uv run python -c "
from scripts.fetch import fetch
html = fetch('https://wol.jw.org/tvl/wol/b/r153/lp-vl/nwt/1/1')
print(f'Fetched {len(html)} chars' if html else 'FAILED')
"
```

> **Apple Silicon note**: The platform warning (`linux/amd64 does not match linux/arm64/v8`) is expected and harmless. The image runs under Rosetta.

---

## Phase 1: Sitemap Enumeration

**Script**: `scripts/scrape_sitemap.py`
**Output**: `data/raw/sitemap_tvl.xml`, `data/raw/sitemap_tvl.json`
**Time**: ~30 seconds

```bash
uv run python scripts/scrape_sitemap.py
```

This fetches `https://www.jw.org/tvl/sitemap.xml` (1.1MB), parses all `<loc>` entries, and classifies each URL by content type using regex patterns.

**Result**: 7,103 Tuvaluan URLs across 25 categories. Key finding: zero hreflang alternate links exist, so cross-language pairing must use WOL's internal alignment mechanisms (verse numbers, docIds, dates).

| Category | Count | Scrapeable? |
|---|---|---|
| magazine | 2,489 | Yes (via library crawl) |
| publication_index | 1,605 | Index pages only |
| bible_chapter | 1,189 | Yes (verse-aligned) |
| book | 499 | Yes (via pub code / library) |
| brochure | 257 | Yes (via pub code / library) |
| song | 227 | Lyrics only |
| video | 146 | No text content |
| Other (faq, news, etc.) | 590 | Minimal parallel text |

---

## Phase 2: Bible Scraping (Verse-Aligned)

**Script**: `scripts/scrape_bible.py`
**Output**: `data/aligned/bible_verses.jsonl`
**Time**: ~80 minutes for full Bible

### Pilot run (3 chapters)

```bash
uv run python scripts/scrape_bible.py --pilot
```

Scrapes Genesis 1, Psalm 19, and John 3 in both TVL and EN. Validates that verse-level alignment works (82/82 verses aligned, 100% match rate).

### Single book

```bash
uv run python scripts/scrape_bible.py --book 1    # Genesis (50 chapters)
uv run python scripts/scrape_bible.py --book 19   # Psalms (150 chapters)
```

### Full Bible (all 66 books, 1,189 chapters)

```bash
uv run python scripts/scrape_bible.py --full
```

**Result**: 30,838 verse pairs across all 66 books. 0 failures. The script is fully resumable -- if interrupted, restart with the same command and it picks up where it left off.

### How Bible alignment works

- **URL pattern**: `wol.jw.org/{lang}/wol/b/{rcode}/{lpcode}/nwt/{bookNo}/{chapter}`
  - TVL: `tvl/r153/lp-vl`, EN: `en/r1/lp-e`
  - `bookNo`: 1-66, `chapter`: varies by book
- **HTML selector**: `span.v` with `id="v{bookNo}-{ch}-{verse}-{part}"`
- **Cleanup**: Remove `a.fn` (footnotes), `a.b` (cross-refs), `sup` (superscripts)
- **Merge**: Verses split across paragraphs (part > 1) are concatenated
- **Alignment**: Match by verse number across languages -- always 1:1

---

## Phase 3: Article Scraping (Paragraph-Aligned)

**Script**: `scripts/scrape_articles.py`
**Output**: `data/aligned/articles.jsonl`
**Time**: Several hours for full library crawl

Article scraping happens in two stages: (1) discover docIds, then (2) fetch and align articles.

### Stage 1: DocId discovery

DocIds are WOL's internal document identifiers. The same docId points to the same content in both languages. There are three ways to discover them:

#### Method A: By publication code (direct)

```bash
uv run python scripts/scrape_articles.py --pub lv    # "Love" book
uv run python scripts/scrape_articles.py --pub bh    # "Bible Teach" book
uv run python scripts/scrape_articles.py --pub jy    # "Jesus" book
```

Known Tuvaluan publication codes: `bh`, `bhs`, `bm`, `bt`, `fg`, `gf`, `hf`, `jl`, `jy`, `kr`, `lff`, `lffi`, `lmd`, `lv`, `lvs`, `my`, `sjj`, `snnw`, `th`, `wt`, `yc`, `ypq`

#### Method B: Library category crawl (recursive)

This recursively crawls WOL library pages to discover ALL docIds in a category:

```bash
# Crawl a single category
uv run python scripts/scrape_articles.py --library-cat "faleleoleo-maluga"   # Watchtower
uv run python scripts/scrape_articles.py --library-cat "ala-mai"             # Awake!
uv run python scripts/scrape_articles.py --library-cat "tusi-mō-fakatasiga"  # Meeting workbooks
uv run python scripts/scrape_articles.py --library-cat "tusi"                # Books
uv run python scripts/scrape_articles.py --library-cat "te-tou-galuega-talai"  # Ministry
uv run python scripts/scrape_articles.py --library-cat "polosiua-ki-te-tamā-tusi"  # Brochures

# Or crawl ALL categories at once
uv run python scripts/scrape_articles.py --library
```

The library URL structure: `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa/{category-slug}`

The crawler follows `/wol/library/` and `/wol/publication/` links up to 5 levels deep, collecting all `/wol/d/` docId links found.

#### Method C: Specific docIds

```bash
uv run python scripts/scrape_articles.py --docids 1102008070 1102015820 1102008066
```

### Stage 2: Fetch and align

Once docIds are discovered, the script automatically:

1. Fetches the TVL page: `wol.jw.org/tvl/wol/d/r153/lp-vl/{docId}`
2. Fetches the EN page: `wol.jw.org/en/wol/d/r1/lp-e/{docId}`
3. Extracts paragraphs from `article#article` using `p[data-pid]`
4. Aligns by matching `data-pid` values between languages
5. Falls back to document-level alignment when paragraph counts diverge significantly

### The full scrape we ran

We ran all 6 library categories in parallel (3 at a time due to rate limiting):

```bash
# Run these in parallel (separate terminal sessions or background):
uv run python scripts/scrape_articles.py --library-cat "faleleoleo-maluga"  &
uv run python scripts/scrape_articles.py --library-cat "ala-mai"  &
uv run python scripts/scrape_articles.py --library-cat "tusi-mō-fakatasiga"  &
wait

# Then the remaining categories (most content already covered):
uv run python scripts/scrape_articles.py --library-cat "tusi"
uv run python scripts/scrape_articles.py --library-cat "te-tou-galuega-talai"
uv run python scripts/scrape_articles.py --library-cat "polosiua-ki-te-tamā-tusi"
```

We also scraped individual publication codes earlier in the project:

```bash
for pub in lv bh bt lff kr jy wt my bhs lvs sjj snnw; do
  uv run python scripts/scrape_articles.py --pub "$pub"
done

# Additional brochure codes discovered later
for pub in bm fg gf hf jl lmd th yc ypq; do
  uv run python scripts/scrape_articles.py --pub "$pub"
done
```

**Result**: 275,430 article paragraph pairs from 7,255 unique docIds. Many docIds exist only in English (no TVL translation), so the scraper skips those automatically.

### Quality filtering (built into the scraper)

The scraper filters out noise at extraction time:

- **Metadata paragraphs**: Chapter headers ("CHAPTER 7" / "MATAUPU E 7"), copyright lines, photo credits, TOC entries
- **Very short pairs**: Both sides < 20 characters
- **Extreme ratios**: TVL/EN character ratio outside 0.15-7.0
- **Document-level fallback**: When paragraph counts diverge > 20%, concatenate all paragraphs into a single pair with confidence 0.6

---

## Phase 4: Daily Text Scraping (Date-Aligned)

**Script**: `scripts/scrape_daily_text.py`
**Output**: `data/aligned/daily_text.jsonl`
**Time**: ~50 minutes for full range

### Date range discovery

Tuvaluan daily texts exist on WOL from **2017-01-01** onward. Earlier years return empty pages. We verified this boundary by testing pages for each year 2014-2021.

### Full scrape (2017-2025)

```bash
uv run python scripts/scrape_daily_text.py --range 2017-01-01 2025-12-31
```

### By year

```bash
uv run python scripts/scrape_daily_text.py --year 2025
```

### How daily text alignment works

- **URL pattern**: `wol.jw.org/{lang}/wol/h/{rcode}/{lpcode}/{yyyy}/{m}/{d}`
  - Note: month and day are NOT zero-padded (e.g., `/2025/3/5` not `/2025/03/05`)
- **HTML structure**: `div.tabContent[data-date]` contains `p.themeScrp` (theme scripture) and `p.sb` (commentary)
- **Optimization**: Each page returns ~3 consecutive days. The script extracts adjacent dates from the same fetch to reduce requests by ~60%.
- **Alignment**: Date-based (each date has exactly one TVL and one EN daily text)

**Result**: 3,432 daily text pairs covering 2017-01-01 through 2025-12-31. 3,287 unique dates (some dates produce pairs with slightly different structures yielding multiple records). 0 failures, 0 gaps.

---

## Phase 5: Quality Report

**Script**: `scripts/stats.py`

```bash
uv run python scripts/stats.py
```

This produces a comprehensive report of dataset statistics and quality issues.

---

## Resume and Idempotency

All scrapers are fully resumable and idempotent:

1. **Raw HTML caching**: `fetch_and_save()` checks if the raw HTML file exists before fetching. Interrupted runs don't re-download pages already on disk.
2. **Output deduplication**: Each scraper loads existing IDs from its output JSONL on startup and skips already-scraped items.
3. **Append-mode writing**: New pairs are appended to the JSONL file, so partial runs are safe.

To resume any interrupted scrape, simply re-run the same command. It will skip all completed work and continue from where it left off.

---

## Rate Limiting and Politeness

- **Delay**: 2 seconds between requests (enforced in `scripts/fetch.py`)
- **Retries**: 3 attempts with exponential backoff (2s, 4s, 8s) on failure
- **Caching**: Raw HTML saved to `data/raw/` -- never re-fetches a page already on disk
- **Docker overhead**: Each request spins up a new Docker container (~1s overhead), which naturally rate-limits to ~3s per request total

---

## Final Dataset Summary

After running all phases, the dataset contains:

| Source | Pairs | Unique items | Tokens (est.) |
|---|---|---|---|
| Bible verses | 30,838 | 1,189 chapters | ~2.4M |
| Articles | 275,430 | 7,255 docIds | ~36.7M |
| Daily text | 3,432 | 3,287 dates (2017-2025) | ~1.8M |
| **Total (raw)** | **309,700** | | **~40.9M** |

> **Note**: The raw article data contains ~129k duplicates from overlapping library crawls (the same docId can appear in multiple categories). These are removed during the dataset build step (`scripts/build_stage_a_mt_data.py`) which deduplicates by content hash.

### Post-deduplication estimates

After quality filtering (dedup, min length, ratio bounds):

| Metric | Value |
|---|---|
| Unique pairs | ~180k |
| Quality-filtered pairs | ~170k |
| Total tokens (both languages) | ~25M |

### WOL content coverage

| Library category | Scraped? | DocIds found |
|---|---|---|
| Watchtower (faleleoleo-maluga) | Yes | ~6,500 |
| Awake! (ala-mai) | Yes | ~3,850 |
| Meeting workbooks (tusi-mo-fakatasiga) | Yes | ~3,900 |
| Books (tusi) | Yes (via pub codes + library) | Covered above |
| Ministry (te-tou-galuega-talai) | Yes (all duplicates) | Covered above |
| Brochures (polosiua-ki-te-tama-tusi) | Yes (all duplicates) | Covered above |
| Bible (all 66 books) | Yes | 1,189 chapters |
| Daily text (2017-2025) | Yes, 0 gaps | 3,287 dates |

### What we didn't scrape (and why)

| Category | Count | Reason |
|---|---|---|
| Songs (pese) | 227 | Lyrics only; different text type that may confuse MT models |
| Videos | 146 | No parallel text content |
| FAQ | 49 | Minimal content, most already captured via docId overlap |
| News | 36 | Very small, many English-only |
| Help pages | 17 | UI/navigation text, not useful for MT |

---

## Troubleshooting

### Docker not running

```
Cannot connect to the Docker daemon
```

Start Docker Desktop. All fetching requires Docker for curl-impersonate.

### Exit code 6 / Exit code 56

Network timeout or TLS error. The script retries automatically (3 attempts). If persistent, check your internet connection or Docker memory limits.

### `ModuleNotFoundError: No module named 'bs4'`

You're running with raw `python3` instead of `uv run`. Always use:

```bash
uv run python scripts/scrape_bible.py --full
```

### Platform warning on Apple Silicon

```
WARNING: The requested image's platform (linux/amd64) does not match linux/arm64/v8
```

This is expected and harmless. The Docker image runs under Rosetta emulation.

### Scrape seems stuck

The library crawl phase can take several minutes to discover docIds before any pairs are written. Check for network activity:

```bash
# Check if raw HTML files are being created
ls -lt data/raw/wol_tvl/ | head -5

# Check if Docker containers are running
docker ps
```

### Running in the background

For long scrapes, use a terminal multiplexer (`tmux` or `screen`):

```bash
tmux new -s scrape
uv run python scripts/scrape_articles.py --library-cat "faleleoleo-maluga"
# Ctrl-B D to detach, `tmux attach -t scrape` to reattach
```

> **Warning**: `nohup` with `uv run` does not work reliably -- the subprocess can't find virtualenv dependencies. Use `tmux` or `screen` instead.

---

## File Reference

| File | Purpose |
|---|---|
| `scripts/fetch.py` | Shared HTTP fetcher (Docker curl-impersonate wrapper) |
| `scripts/scrape_sitemap.py` | Parse jw.org/tvl sitemap, classify URLs |
| `scripts/scrape_bible.py` | Scrape Bible chapters, verse-aligned |
| `scripts/scrape_articles.py` | Scrape WOL articles by docId, paragraph-aligned |
| `scripts/scrape_daily_text.py` | Scrape daily text pages, date-aligned |
| `scripts/stats.py` | Dataset statistics and quality report |
| `data/raw/wol_tvl/*.html` | Cached raw Tuvaluan HTML pages |
| `data/raw/wol_en/*.html` | Cached raw English HTML pages |
| `data/aligned/bible_verses.jsonl` | Aligned Bible verse pairs |
| `data/aligned/articles.jsonl` | Aligned article paragraph pairs |
| `data/aligned/daily_text.jsonl` | Aligned daily text pairs |

---

## Reproduction Checklist

- [ ] Docker Desktop installed and running
- [ ] `uv sync` completed
- [ ] `docker pull lwthiker/curl-impersonate:0.6-ff` completed
- [ ] Phase 1: `uv run python scripts/scrape_sitemap.py`
- [ ] Phase 2: `uv run python scripts/scrape_bible.py --full`
- [ ] Phase 3a: `uv run python scripts/scrape_articles.py --library-cat "faleleoleo-maluga"`
- [ ] Phase 3b: `uv run python scripts/scrape_articles.py --library-cat "ala-mai"`
- [ ] Phase 3c: `uv run python scripts/scrape_articles.py --library-cat "tusi-mō-fakatasiga"`
- [ ] Phase 4: `uv run python scripts/scrape_daily_text.py --range 2017-01-01 2025-12-31`
- [ ] Phase 5: `uv run python scripts/stats.py`
- [ ] Verify: ~309k raw pairs across 3 JSONL files
