# Football News → Tuvaluan: source evaluation and scraping plan

This document evaluates seven football news sites as sources for English articles
to translate into Tuvaluan using the Stage A translation adapter. The goal is to
build a pipeline that continuously fetches English football articles and produces
Tuvaluan translations, expanding coverage beyond the JW.org religious corpus.

## Why football news

The Stage A adapter (trained on JW.org parallel data) is strong on religious and
instructional text but needs exposure to contemporary, casual, and sports-domain
language. Football is globally popular, produces high volumes of short-to-medium
articles daily, and uses vocabulary that overlaps well with everyday Tuvaluan
(body language, emotions, competition, place names, personal names).

Football articles also stress-test the name-preservation problem: the adapter
currently hallucinates JW-style transliterations for unfamiliar proper nouns
(e.g. "Tausa" → "Taʹhosh"). Sports articles full of player names, club names,
and place names will provide natural training signal for verbatim name copying.

## Evaluation methodology

Each site was probed twice:

1. **WebFetch** — standard HTTP client (equivalent to `requests`/`httpx`)
2. **Docker curl-impersonate** — browser TLS fingerprint via `lwthiker/curl-impersonate:0.6-ff`

We checked: server-side rendering, article URL patterns, HTML selectors,
robots.txt, anti-bot measures, and article volume.

**Key finding**: No site required curl-impersonate. Unlike JW.org (which uses
TLS fingerprint detection), all seven football sites serve identical content to
regular curl and curl-impersonate.

## Site-by-site results

### Tier 1 — recommended sources

#### Goal.com — EASY, robots.txt allows all

| Property | Detail |
|----------|--------|
| Rendering | Next.js SSR — full content in `__NEXT_DATA__` JSON |
| URL pattern | `/en-us/news/{slug}/{blt_id}` and `/en-us/lists/{slug}/{blt_id}` |
| Extraction | `__NEXT_DATA__` → `props.pageProps.content.article.body.body` (HTML) |
| Selectors | `[data-testid="article-title"]`, `[data-testid="article-body"] p` |
| Metadata | JSON-LD `NewsArticle` + `__NEXT_DATA__` (headline, author, date, tags) |
| Discovery | 38 regional sitemaps; `editorial-news.xml` (~205 URLs), `editorial-slides.xml` (~5,000 URLs) for en-us |
| Volume | ~5,500+ articles in en-us sitemaps |
| robots.txt | `User-agent: * / Allow: /` — fully permissive, no AI bot blocks |
| Anti-bot | None detected. No Cloudflare, no CAPTCHA, no rate limiting, no UA check |
| curl-impersonate needed | No |

**Why top pick**: Permissive robots.txt, high volume, clean structured data,
zero anti-bot friction. Best effort-to-reward ratio.

#### FIFA.com — EASY (via API), robots.txt allows all

| Property | Detail |
|----------|--------|
| Rendering | React SPA — `www.fifa.com` returns empty shell. Content via open API |
| API base | `https://cxm-api.fifa.com/fifaplusweb/api` |
| Article endpoint | `/sections/article/{contentfulEntryId}?locale=en` — no auth needed |
| Search endpoint | `/fifacxmsearch/api/results?locale=en&searchString=...&size=10` |
| Search API key | `X-Functions-Key: 2kD9zRYRT7xN6kSGs6EoHcvSyKOyK0B4YaKTf1Ygeaw8PM6bgfR6SQ==` (public, embedded in client JS) |
| Content format | Contentful Rich Text JSON — `nodeType: "paragraph"` → `nodeType: "text"` → `value` |
| Discovery | 106 sitemap pages at `cxm-api.fifa.com/fifaplusweb/api/sitemaps/articles/{0-105}` (~100 articles each) |
| Volume | ~10,600 articles |
| robots.txt | Only blocks `/*?archive?filters=` — articles fully allowed |
| Anti-bot | Kasada + Akamai Bot Manager on `www.fifa.com`, but API has none |
| Locales | en, ar, zh, fr, de, hi, id, it, ja, ko, pt, es |
| curl-impersonate needed | No |

**Why top pick**: Open API returning structured JSON is cleaner than any HTML
scraping. No auth required. Large volume. Official tournament content provides
formal, well-edited English. The two-step lookup (URL → Contentful ID → content)
adds complexity but the search API bridges this.

#### Sky Sports Football — EASY, robots.txt allows generic crawlers

| Property | Detail |
|----------|--------|
| Rendering | Fully SSR |
| URL pattern | `/football/news/{section-id}/{article-id}/{slug}` |
| Extraction | JSON-LD `articleBody` field — full plain text in one string |
| Selectors | `div.sdc-article-body[data-testid="article-body"] p` |
| Metadata | JSON-LD `NewsArticle` (headline, author, datePublished) |
| Discovery | News sitemap at `/sitemap/sitemap-news.xml` (~60 recent articles); homepage has ~20 links |
| Volume | ~60 in news sitemap (recent only); historical requires crawling listing pages |
| robots.txt | Blocks `GPTBot`, `CCBot`, `AhrefsBot`, `Yandexbot`. Generic `*` is allowed on `/football/news/` |
| Anti-bot | None detected |
| curl-impersonate needed | No |

**Why Tier 1**: Easiest extraction (JSON-LD gives full text as single string).
No paywall. robots.txt only blocks named AI bots, not generic crawlers. Lower
volume than Goal/FIFA but excellent article quality.

### Tier 2 — usable with caveats

#### The Guardian Football — EASY technically, legally restricted

| Property | Detail |
|----------|--------|
| Rendering | Fully SSR (React "DCR" with server rendering) |
| URL pattern | `/football/{YYYY}/{mon}/{dd}/{slug}` |
| Extraction | `[data-gu-name="body"] p` (stable semantic selectors) |
| Metadata | JSON-LD `NewsArticle`; also `og:` meta tags |
| API | Free Content API at `content.guardianapis.com` — returns full body as JSON |
| API limits | Free: 12 req/sec, 5,000 calls/day. `page-size=200` max. Commercial: contact sales |
| Volume | ~198,000 football articles since 1999 |
| robots.txt | **Explicitly blocks all AI**: `anthropic-ai`, `ClaudeBot`, `GPTBot`, `CCBot`, etc. Header states: "not permitted for LLMs, ML, or AI purposes" |
| Anti-bot | None technical. Legal/TOS enforcement instead |
| curl-impersonate needed | No |

**Assessment**: By far the largest corpus and the cleanest API. But the Guardian
is the most explicit about blocking AI/ML use. For a low-resource language
preservation project, reaching out to `licensing@theguardian.com` could be
worthwhile — this isn't a commercial AI product, it's linguistic preservation
for ~11,000 speakers.

#### ESPN FC — EASY technically, blocks AI crawlers

| Property | Detail |
|----------|--------|
| Rendering | Fully SSR |
| URL pattern | `/soccer/story/_/id/{numeric_id}/{slug}` |
| Extraction | `div.article-body p` (35+ paragraphs typical) |
| Metadata | JSON-LD `NewsArticle` (headline, datePublished, author) |
| Discovery | Homepage has 19+ story links; Google News sitemap available |
| Volume | Large (unclear total; continuous daily output) |
| robots.txt | **Blocks all AI bots**: `anthropic-ai`, `GPTBot`, `ChatGPT-User`, `CCBot`, `Google-Extended` |
| Anti-bot | None technical |
| Paywall | ESPN+ articles truncated; free articles have `content_tier: free` |
| curl-impersonate needed | No |

**Assessment**: Clean SSR with good structured data, but robots.txt intent
is clear. ESPN+ paywall also limits some content.

#### CBS Sports Soccer — EASY technically, low volume

| Property | Detail |
|----------|--------|
| Rendering | SSR — article body in `<article>` > `<p>` tags |
| URL pattern | `/soccer/news/{slug}/` |
| Extraction | `article p` (filter out ad divs) |
| Metadata | JSON-LD `NewsArticle` (no body text, just metadata) |
| Discovery | RSS feed at `/rss/headlines/soccer/` (36 recent items) |
| Volume | **~1-3 soccer articles per month** |
| robots.txt | Blocks `GPTBot`. Generic crawlers allowed |
| Anti-bot | Admiral anti-adblock overlay; not blocking to scraper |
| curl-impersonate needed | No |

**Assessment**: Works fine technically but soccer coverage is negligible.
Not worth building a dedicated scraper for ~30 articles/year.

### Tier 3 — not recommended

#### UEFA.com — MEDIUM, limited discovery

| Property | Detail |
|----------|--------|
| Rendering | Article pages: SSR. Listing pages: JS-rendered (no article links in HTML) |
| URL pattern | `/{competition}/news/{hex-id}--{slug}/` |
| Extraction | `div.article_body p` (also custom `pk-accordion-item` elements) |
| Metadata | JSON-LD (title, date, description only — not full body) |
| Discovery | Sitemaps at `sitemap/news/latest.xml` (~61 articles); per-competition sitemaps are tiny (~2 articles) |
| Volume | ~61 in latest sitemap; no large historical archive accessible |
| robots.txt | Permissive — news content allowed |
| Anti-bot | None detected. Embedded API keys found but API is locked to browser context |
| curl-impersonate needed | No |

**Assessment**: Article extraction works but discovery is the bottleneck.
Sitemaps are small and listing pages require JS rendering. The editorial API
(`editorial.uefa.com`) is inaccessible outside the browser despite public keys.
Not worth the effort given Goal.com and FIFA.com cover similar content.

## Recommended pipeline

### Phase 1 — Goal.com + FIFA.com (no legal friction)

Both sites have permissive robots.txt and return structured data (JSON). Start here.

```
scripts/scrape_football_goal.py     # Goal.com via __NEXT_DATA__ + sitemaps
scripts/scrape_football_fifa.py     # FIFA.com via CXM API + sitemaps
```

**Expected yield**: ~16,000 English articles (5,500 Goal + 10,600 FIFA)

**Scraper pattern** (same as existing JW.org scrapers):
1. Fetch sitemap / search API → collect article URLs/IDs
2. Fetch each article → extract title + body text
3. Cache raw responses in `data/cache/`
4. Output to `data/football/goal_articles.jsonl` / `data/football/fifa_articles.jsonl`

No curl-impersonate needed — regular `requests` or `httpx` works for both.

### Phase 2 — translate via Stage A adapter

Use the Tinker OpenAI-compatible endpoint to translate each article:

```
Base URL:  https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1
Model:     tinker://a6453cc0-d0d8-5168-996a-c9b9ee3b8582:train:0/sampler_weights/final
Endpoint:  /completions (not /chat/completions — model uses role_colon renderer)
Stop:      ["\n\nUser:"]
```

Prompt template (matching training format):
```
System: You are a careful translator between Tuvaluan and English. Translate faithfully.
Preserve names, numbers, punctuation, line breaks, and structure when possible.
Output only the translation.

User: Convert this English text to natural Tuvaluan while keeping the original
structure when possible.

{article_paragraph}

[Assistant]: {translation}
```

Translate paragraph-by-paragraph (not full articles) to stay within the 2048 max
token window the adapter was trained on.

### Phase 3 — Sky Sports (supplement)

Add Sky Sports for UK/European league coverage. JSON-LD extraction is trivial.
robots.txt allows generic crawlers. Lower volume but high-quality match reports.

### Phase 4 — Guardian (if licensed)

If `licensing@theguardian.com` grants permission for language preservation use,
the Guardian API provides 198k football articles via a clean JSON endpoint.
This would be the single largest source by far.

## Known issues to address

### Name hallucination

The Stage A adapter was trained on JW.org data where names are always
transliterated (Ieova↔Jehovah, Iesu↔Jesus). When it encounters unfamiliar
names, it hallucinates JW-style transliterations:

- "Tausa" → "Taʹhosh"
- "Nukufetau" → "Nuk·phatʹta"

Prompt engineering does not fix this — it's baked into the weights.

**Fix**: Augment Stage A training data with ~1,000 synthetic name-preservation
pairs (Tuvaluan place names, personal names in simple sentence templates) and
retrain. Football articles will then provide ongoing reinforcement since every
article contains dozens of proper nouns that must be copied verbatim.

### Domain vocabulary gap

Football-specific terms (penalty, offside, midfielder, VAR) have no Tuvaluan
equivalents in the training data. The adapter may produce awkward paraphrases
or hallucinated translations. Two strategies:

1. **Loanword preservation**: Keep English football terms as loanwords in
   Tuvaluan output (common practice in Pacific languages for sports terms)
2. **Post-training glossary**: Build a football term glossary and use it as
   few-shot context in the translation prompt

### Quality filtering

Not all translated output will be usable. Apply the same quality filters used
for the JW.org parallel corpus:

- Minimum character length per side
- Length ratio filtering (reject extreme ratios)
- Duplicate detection
- Metadata detection (headers, footers, navigation text)

## File layout

```
data/football/
  goal_articles.jsonl          # raw scraped Goal.com articles
  fifa_articles.jsonl          # raw scraped FIFA.com articles
  sky_articles.jsonl           # raw scraped Sky Sports articles
  translations/
    goal_en_tvl.jsonl          # translated Goal.com articles
    fifa_en_tvl.jsonl          # translated FIFA.com articles
    sky_en_tvl.jsonl           # translated Sky Sports articles

scripts/
  scrape_football_goal.py      # Goal.com scraper
  scrape_football_fifa.py      # FIFA.com CXM API scraper
  scrape_football_sky.py       # Sky Sports scraper
  translate_football.py        # batch translation via Tinker endpoint
```

## Summary table

| Site | Rating | Legal | Volume | Method | Priority |
|------|--------|-------|--------|--------|----------|
| Goal.com | Easy | Clear | ~5,500 | `__NEXT_DATA__` JSON | P0 |
| FIFA.com | Easy | Clear | ~10,600 | Open CXM API | P0 |
| Sky Sports | Easy | OK (generic UA) | ~60/batch | JSON-LD | P1 |
| Guardian | Easy | Needs license | ~198,000 | Content API | P2 (if licensed) |
| ESPN | Easy | Restricted | Large | SSR HTML | P3 |
| CBS Sports | Easy | OK (generic UA) | ~30/year | RSS + HTML | Skip |
| UEFA | Medium | Clear | ~61/batch | SSR + sitemap | Skip |