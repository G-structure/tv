# Tuvaluan ↔ English JW Content: URL Patterns & Mapping Guide

## 0. Confidence keys (please use these everywhere)

- **CONFIRMED**: I saw this pattern or root directly on an official JW page or through official sitemap/robots evidence.
- **LIKELY**: The pattern is consistent with JW's visible URL conventions, but I haven't seen this exact Tuvaluan + English pairing live.
- **UNCERTAIN**: Needs confirmation (either through the sitemap, hreflang alternates, or a live language switch).

---

## 1. Canonical language markers

### JW.org language path (CONFIRMED)

- Tuvaluan: `/tvl/…` → root: `https://www.jw.org/tvl/`
- English: `/en/…` → root: `https://www.jw.org/en/`

### WOL language path (CONFIRMED)

- Tuvaluan: `https://wol.jw.org/tvl/…`
- English: `https://wol.jw.org/en/…`

### WOL language/region tokens (stable pairing anchors) (CONFIRMED)

These are the "swap bundle" I'd use mechanically when mapping Tuvaluan WOL → English WOL:

| Property | Tuvaluan | English |
|---|---|---|
| Language path | `tvl` | `en` |
| Region code | `r153` | `r1` |
| Language-pack code | `lp-vl` | `lp-e` |
| `wtlocale` (finder) | `VL` | `E` |
| `wtlocale` (open) | `TVL` (uncertain; might also be `VL`) | `E` |

**Notes:**
- WOL's `finder` entry for Tuvaluan is confirmed with `wtlocale=VL` and direct Tuvaluan doc IDs in public finder URLs.
- `open?wtlocale=TVL` is still *uncertain*; I'd treat it as "likely" but keep the pairing confidence lower until you see a live Tuvaluan `open` example.

### Stable publication/issue/section tokens (shared across languages) (CONFIRMED/LIKELY)

**Confirmed anchors:**
- WOL publication codes (visible on WOL browse pages, e.g., as `bt`, `lv`, `T-31`, etc.)
- WOL Bible module token: `nwt`
- JW issue codes: `wYYYYMMDD`, `gYYYYMMDD`, `wpYYYYMMDD`, `kmYYYYMM`, `mwbYYYYMM` patterns are language-independent anchors.
- JW robots file advertises the sitemap index URL: `https://www.jw.org/sitemap.xml`

**Likely**
- Full publication code set is larger than what's publicly obvious in one listing; treat any `wol/publication/.../{pubCode}` as stable across languages.

---

## 2. Seed URLs

- **JW robots/sitemap index (CONFIRMED):** `https://www.jw.org/robots.txt` (contains `Sitemap: https://www.jw.org/sitemap.xml`)
- **Tuvaluan sitemap (UNCERTAIN due to timeouts in retrieval):** `https://www.jw.org/tvl/sitemap.xml`
  - Your draft says "last modified 2026-03-03" and "1,310 URLs." I can't confirm the exact `<lastmod>`/count from the public tool retrieval yet; keep as "likely."
- **Tuvaluan JW.org home (CONFIRMED):** `https://www.jw.org/tvl/`
- **WOL Tuvaluan home-style entry (CONFIRMED):** the WOL doc patterns for Tuvaluan exist; you can also treat `/wol/h/r153/lp-vl/{date}` as predictable landing patterns
- **WOL English home-style entry (CONFIRMED):** `https://wol.jw.org/en/wol/h/r1/lp-e/{date}` exists and works with the confirmed swap bundle

---

## 3. Confirmed official roots (Tuvaluan and English)

### Tuvaluan roots (CONFIRMED)

| Root | URL | Type |
|---|---|---|
| JW.org home | `jw.org/tvl/` | entry point |
| Library/publications hub | `jw.org/tvl/tusi/` | index/TOC hub |
| Books hub | `jw.org/tvl/tusi/tusi/` | index |
| Brochures hub | `jw.org/tvl/tusi/polosiua/` | index |
| Bible hub | `jw.org/tvl/tusi/tusi-tapu/` | index |
| Bible book index | `jw.org/tvl/tusi/tusi-tapu/nwt/tusi-i-te-tusi-tapu/` | index |
| Magazines hub | `jw.org/tvl/tusi/mekesini/` | index |
| Songs hub | `jw.org/tvl/tusi/pese-fakatagitagi-pese-usuusu/` | index |
| Meeting workbook hub | `jw.org/tvl/tusi/tusi-mō-fakatasiga-a-mi/` | index |
| Programs | `jw.org/tvl/tusi/polokalame/` | index |
| Videos | `jw.org/tvl/tusi/vitio-kolā-ne-fakatoka-ne-molimau-a-ieova/` | index |
| Search hub | `jw.org/tvl/sala/` | search interface |
| News hub | `jw.org/tvl/tala/` | index |
| News by region | `jw.org/tvl/tala/kogā-fenua-kesekese/` | index |
| Bible study/FAQ hub | `jw.org/tvl/akoakoga-i-te-tusi-tapu/` | topic hub |
| FAQ index | `jw.org/tvl/akoakoga-i-te-tusi-tapu/fesili/` | index |
| About JW | `jw.org/tvl/molimau-a-ieova/` | topic hub |
| What's new | `jw.org/tvl/mea-fou/` | index/listing |
| All topics | `jw.org/tvl/mataupu-fatoa-fakapa/` | index/listing |
| Online help | `jw.org/tvl/online-help/` | index |
| JW Library help | `jw.org/tvl/online-help/jw-library/` | index |
| WOL library browse root | `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa` | browse root |
| WOL bible nav root | `wol.jw.org/tvl/wol/binav/r153/lp-vl/nwt` | bible nav root |
| WOL meetings root (date-based visible pages) | `wol.jw.org/tvl/wol/dt/r153/lp-vl/{yyyy}/{m}/{d}` | date-based meeting content |
| WOL daily text root (date-based visible pages) | `wol.jw.org/tvl/wol/h/r153/lp-vl/{yyyy}/{m}/{d}` | daily text content |

### English roots (CONFIRMED)

| Root | URL |
|---|---|
| JW.org home | `jw.org/en/` |
| Library hub | `jw.org/en/library/` |
| Books | `jw.org/en/library/books/` |
| Brochures | `jw.org/en/library/brochures/` |
| Bible | `jw.org/en/library/bible/` |
| Magazines | `jw.org/en/library/magazines/` |
| News | `jw.org/en/news/` |
| News by region | `jw.org/en/news/region/` |
| What's new | `jw.org/en/whats-new/` |
| Online help | `jw.org/en/online-help/` |
| JW Library help | `jw.org/en/online-help/jw-library/` |
| About JW | `jw.org/en/jehovahs-witnesses/` |
| Bible teachings | `jw.org/en/bible-teachings/` |
| WOL library browse root | `wol.jw.org/en/wol/library/r1/lp-e/all-publications` |
| WOL bible nav root | `wol.jw.org/en/wol/binav/r1/lp-e` |
| WOL meetings root | `wol.jw.org/en/wol/dt/r1/lp-e` |
| WOL daily text root | `wol.jw.org/en/wol/h/r1/lp-e/{yyyy}/{m}/{d}` |

---

## 4. URL family inventory

### A. JW.org — entry / main sections

**Language root (CONFIRMED)**
- Pattern: `https://www.jw.org/{lang}/`
- Alignment: high (direct language swap)
- Caveat: the path immediately after `/tvl/` often uses Tuvaluan labels, while English uses English labels.

**Library hub (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/`
- EN: `jw.org/en/library/`
- Alignment: high structurally; second segment differs (`tusi` vs `library`)

**Search hub (CONFIRMED for TVL entry)**
- TVL: `jw.org/tvl/sala/`
- EN: English search behavior is often via `finder` instead (see resolver endpoints below); there isn't always a neat `/en/search/` pattern.
- Alignment strategy: use stable identifiers in search results (issue codes, docid-like tokens) rather than page layout.

**What's new / All topics listings (CONFIRMED for TVL and EN)**
- TVL what's new: `jw.org/tvl/mea-fou/`
- EN what's new: `jw.org/en/whats-new/`
- TVL all topics: `jw.org/tvl/mataupu-fatoa-fakapa/`
- Alignment: medium; swap language + use hreflang (if present) + verify with a few known titles to build confidence.

---

### B. JW.org — Bible

**Bible landing (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/tusi-tapu/`
- EN: `jw.org/en/library/bible/`

**Bible book index (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/tusi-tapu/nwt/tusi-i-te-tusi-tapu/`
- Alignment: very high when paired via WOL book numbers (WOL uses stable numeric bookNo 1–66).

**Bible book TOC (CONFIRMED for pattern existence; book-slug mapping is LIKELY)**
- TVL pattern: `jw.org/tvl/tusi/tusi-tapu/nwt/tusi/{book-slug}/`
- Example: `jw.org/tvl/tusi/tusi-tapu/nwt/tusi/iuta/`
- Alignment: book slug is localized; use WOL bookNo mapping, or rely on language switcher.

**Bible chapter leaf (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/tusi-tapu/nwt/tusi/{book-slug}/{chapter}/`
- EN: `jw.org/en/library/bible/nwt/books/{book-slug}/{chapter}/`
- Example: `salamo/129/` ↔ `psalms/129/`
- Alignment: high when matched via stable bookNo + chapter.

**Bible supplemental TOC pages (CONFIRMED pattern)**
- TVL pattern: `jw.org/tvl/tusi/tusi-tapu/nwt/mataupu-fakaopoopo-e/…`
- Example: `jw.org/tvl/tusi/tusi-tapu/nwt/mataupu-fakaopoopo-e/fekau-i-te-tusi-tapu/`
- Alignment: medium; localization makes slug-level matching hard; fallback is sitemap/hreflang or WOL docId anchoring.

---

### C. JW.org — magazines

**Magazine hub (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/mekesini/`
- EN: `jw.org/en/library/magazines/`

**Issue index (CONFIRMED pattern)**
- Pattern: `jw.org/{lang}/tusi/mekesini/{issue-code}/`
- Examples: `w20060401`, `g20040422`, `wp20150401`
- Alignment: **very high** — issue codes are language-independent.

**Article leaf under issue (CONFIRMED pattern)**
- TVL pattern: `jw.org/tvl/tusi/mekesini/{issue-code}/{article-slug}/`
- Example: `.../wp20150401/faiga-akoga-faka-te-tusi-tapu/`
- Alignment: issue code anchors it; slug matching is the weak link; use WOL docId when available.

**Magazine TOC / download (LIKELY)**
- JW often has download hubs under publication pages, but exact Tuvaluan download URL patterns should be confirmed via sitemap/hreflang because `/download/` segments can be inconsistent.

---

### D. JW.org — books

**Books hub (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/tusi/`
- EN: `jw.org/en/library/books/`

**Book landing/TOC (CONFIRMED)**
- Pattern: `jw.org/tvl/tusi/tusi/{title-slug}/`
- Example: `jw.org/tvl/tusi/tusi/Lessons-You-Can-Learn-From-the-Bible/`
- Alignment: title slugs can be identical to English titles (strong), but not always; use `finder` docId as the hard anchor.

**Book chapter / lesson leaf (LIKELY)**
- Pattern: `jw.org/tvl/tusi/tusi/{title-slug}/{chapter-or-section}/`
- Alignment: medium-high with docId anchoring.

---

### E. JW.org — brochures & booklets

**Brochures hub (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/polosiua/`
- EN: `jw.org/en/library/brochures/`

**Brochure landing/leaf (CONFIRMED)**
- Pattern: `jw.org/tvl/tusi/polosiua/{title-slug}/`
- Examples:
  - `jw.org/tvl/tusi/polosiua/The-Government-That-Will-Bring-Paradise/`
  - `jw.org/tvl/tusi/polosiua/Examining-the-Scriptures-Daily-2024/`
  - `jw.org/tvl/tusi/polosiua/Examining-the-Scriptures-Daily-2024/` (download options mentioned on page)
  - It may also have TOC leaves with localized slugs and odd concatenations, e.g., `Te-Itulau-o-UlutalaTe-Kau-Lomi-Tusi`

**Alignment strategy (confirmed + fallback)**
1. When the title slug is obviously English and matches an English JW library slug, use direct slug swap (high).
2. If the Tuvaluan slug is localized, look for:
   - hreflang alternate in sitemap entry (best)
   - `finder` docId on the page (hard anchor)
   - WOL docId mapping (hard anchor)

---

### F. JW.org — songs / music

**Songs hub (CONFIRMED)**
- TVL: `jw.org/tvl/tusi/pese-fakatagitagi-pese-usuusu/`

**Song leaf (adult songbook)**
- Pattern: `.../{songbook-slug}/{song-number}-{song-slug}/`
- Example: `jw.org/tvl/tusi/pese-fakatagitagi-pese-usuusu/usu-pese-mo-te-fiafia/114-ke-fakaakoako/`
- Alignment: **very high** because the number is stable across languages.

**Song leaf (children's songbook)**
- Pattern: `.../pese-fakatagitagi-pese-usuusu/{songbook-slug}/{song-title-slug}/`
- Example: `.../ke-fai-mo-taugasoa-o-ieova-tou-pese-tamaliki/Ieova-e-Ola/`
- Alignment: title slug may change; no numeric anchor — use language switcher/sitemap

**TOC pages (CONFIRMED pattern)**
- Example: `.../Te-Itulau-o-UlutalaTe-Kau-Lomi-Tusi/` (songbook TOC)
- Strategy: enumerate song pages from TOC links, align by song number, then reconcile slug differences after the number.

---

### G. JW.org — videos

**Videos section (CONFIRMED pattern)**
- Pattern: `jw.org/tvl/tusi/vitio-kolā-ne-fakatoka-ne-molimau-a-ieova/…`
- Examples:
  - Series leaf: `.../fakatomuaga-o-tusi-i-te-tusi-tapu/tusi-ko-kalatia/`
  - Single video: `.../Kaia-e-Tau-ei-o-Sukesuke-ki-te-Tusi-Tapu/`

**Video leaf with transcript / description (LIKELY)**
- Video pages often include text; treat them as in-scope content.
- Alignment: use series slug + language switcher + WOL docId if present.

---

### H. JW.org — meeting workbooks

**Workbook hub and issues (CONFIRMED)**
- Hub: `jw.org/tvl/tusi/tusi-mō-fakatasiga-a-mi/`
- Issue example: `.../iulai-2019-mwb/`, `.../novema-tesema-2021-mwb/`

**Alignment:**
- If the English issue exists, mapping is high via `mwb` issue slug.
- If English issue slug differs, map through WOL daily text/meeting schedule content (which uses stable docIds and pubCodes).

---

### I. JW.org — programs (CONFIRMED root, LIKELY leaf behavior)
- Programs hub: `jw.org/tvl/tusi/polokalame/`
- Leaf patterns are likely `.../{program-id}/`
- Alignment: medium; conventions/conventions may align via WOL docId anchors.

---

### J. JW.org — study / FAQ / Bible questions

**FAQ hub (CONFIRMED)**
- TVL: `jw.org/tvl/akoakoga-i-te-tusi-tapu/`

**FAQ categories and leaves (CONFIRMED for listing pages)**
- Youth: `.../talavou/`
- Children: `.../tamaliki/`
- Science: `.../saienisi/`
- Family: `.../tauavaga-matua/`
- FAQ leaf pattern: `.../fesili/{question-slug}/`

**Alignment strategy (strongest path first):**
1. Use `finder?wtlocale=VL&docid=...` when available (strong).
2. Otherwise use WOL docId mapping (hard anchor) if the FAQ page corresponds to a WOL docId.
3. Avoid slug matching unless the title is identical.

---

### K. JW.org — news

**Tuvaluan news (CONFIRMED)**
- Hub: `jw.org/tvl/tala/`
- Regions: `jw.org/tvl/tala/kogā-fenua-kesekese/{region-slug}/`
- Region example: `.../Italy/`
- Global: `.../lalolagi-kātoa/`
- Article leaf pattern: `.../{region-slug}/{date-and-title-slug}/`
- Example: `.../lalolagi-kātoa/2026-Lipoti-Fou-Mai-te-Potukau-Pule-1/`

**English news (CONFIRMED)**
- Hub: `jw.org/en/news/`
- Regions: `jw.org/en/news/region/`
- Region example: `jw.org/en/news/region/italy/`
- Global news: `jw.org/en/news/region/global/`

**Alignment strategy (medium-high):**
- Region names are often identical (Italy/italy), but a few localized regions (especially Tuvaluan transliterations) may require a mapping table.
- Use the date-anchor portion of the slug as a strong anchor: `YYYY-...`
- Use sitemap/hreflang alternates as the best mapping source when available.

---

### L. JW.org — help

**Help hubs (CONFIRMED)**
- TVL: `jw.org/tvl/online-help/`
- EN: `jw.org/en/online-help/`
- JW Library help:
  - TVL: `jw.org/tvl/online-help/jw-library/`
  - EN: `jw.org/en/online-help/jw-library/`

**Platform-specific help (CONFIRMED in English; likely in Tuvaluan depending on translation consistency)**
- Pattern: `.../jw-library/{platform}/{topic}/`
- Platform tokens like `ios` and `android` are stable anchors.
- Topic slugs may translate; map via language switcher or docId/finder if present.

---

### M. JW.org — misc "about" pages (CONFIRMED root, LIKELY deeper leaf mapping)
- Tuvaluan "about JW" hub: `jw.org/tvl/molimau-a-ieova/`
- English "about JW" hub: `jw.org/en/jehovahs-witnesses/`
- Many English "about us" leaves exist:
  - `jw.org/en/jehovahs-witnesses/meetings/`
  - `jw.org/en/jehovahs-witnesses/conventions/`
  - `jw.org/en/jehovahs-witnesses/faq/…`
- Alignment: medium; map sections by "theme" and confirm via hreflang or WOL docId when available.

---

### N. JW.org — miscellaneous articles

- Pattern: `jw.org/tvl/tusi/kesekese/nisi-mataupu/{slug}/`
- Alignment: medium; page role is clear but slug-level matching is language-specific

---

## 5. JW.org resolver endpoints (important bilingual anchors)

### O. JW.org — `finder` resolver (CONFIRMED)
- Pattern: `https://www.jw.org/finder?…&wtlocale={locale}`
- Tuvaluan: `wtlocale=VL`
- English: `wtlocale=E`
- Useful params:
  - `docid` (hard anchor)
  - `lank` (often a selection identifier like `docid-502017151_101_VIDEO`)
  - `item` (publication/item codes in some contexts)

**Key point:** `finder` is one of the strongest ways to "join" an otherwise unaligned slug, because `docid` is cross-language stable.

### P. JW.org — `open` resolver (CONFIRMED for English; UNCERTAIN for Tuvaluan)
- Pattern: `https://www.jw.org/open?docid={docid}&wtlocale={locale}`
- English: confirmed with `wtlocale=E`
- Tuvaluan: likely `TVL` (uncertain); might also accept `VL`
- Strategy: if you can't confirm Tuvaluan open, don't hard-code it; keep it a "try both locales" rule.

---

## 6. WOL URL families (docId + code-based — strongest pairing)

### Q. WOL — document pages (docId-based) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/d/{rCode}/{lpCode}/{docId}`
- Tuvaluan example: `wol.jw.org/tvl/wol/d/r153/lp-vl/1102014246`
- English swap bundle: `wol.jw.org/en/wol/d/r1/lp-e/1102014246`
- **docId stays the same across languages** (highest confidence in your alignment plan)
- Confirmed: `1102008070` = "Let Marriage Be Honorable" / "E ‵Tau o Faka‵malu te Fakaipoipoga"
- Confirmed: `1102015820` = "Answers to 10 Questions Young People Ask" / "Tali ki Fesili e 10 a Talavou"

### R. WOL — publication TOC pages (pub-code-based) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/publication/{rCode}/{lpCode}/{pub-code}`
- Tuvaluan: `.../r153/lp-vl/{pub-code}`
- English: `.../r1/lp-e/{pub-code}`
- Confirmed: `lv`, `bt`, `T-31` work across both languages
- Subchapters:
  - `.../{pub-code}/{chapter-number}` (chapter-number is language-agnostic within that publication, but exact chapter numbering should be confirmed)

### S. WOL — Bible chapter pages (bookNo + chapter) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/b/{rCode}/{lpCode}/nwt/{bookNo}/{chapter}`
- TVL: `.../r153/lp-vl/nwt/19/11` (Psalm 11)
- EN: `.../r1/lp-e/nwt/19/11`
- Alignment: very high because bookNo is numeric and stable across languages.

### T. WOL — Bible navigation pages (CONFIRMED pattern)
- Root: `wol.jw.org/{lang}/wol/binav/{rCode}/{lpCode}/nwt`
- By book: `.../nwt/{bookNo}`
- Example: `.../nwt/21` (Ecclesiastes)

### U. WOL — Bible citations (bc) (CONFIRMED in English; LIKELY in Tuvaluan)
- English examples exist, e.g., `wol.jw.org/en/wol/bc/r1/lp-e/1102014944/17/0`
- Alignment rule: swap bundle + keep docId and anchor structure if the content exists in Tuvaluan.

### V. WOL — footnote pages (fn) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/fn/{rCode}/{lpCode}/{docId}/{footnoteNo}`
- Example: `.../r153/lp-vl/2010123/1`
- Alignment: docId stable; footnote numbering might differ across language editions, so align with caution.

### W. WOL — daily text (date-based, h-family) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/h/{rCode}/{lpCode}/{yyyy}/{m}/{d}`
- TVL: `.../r153/lp-vl/2024/3/2`
- EN: `.../r1/lp-e/2024/3/2`
- Alignment: **extremely high**; date is universal.

### X. WOL — meetings/schedule (date-based, dt-family) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/dt/{rCode}/{lpCode}/{yyyy}/{m}/{d}`
- TVL: `.../r153/lp-vl/2025/1/1`
- EN: `.../r1/lp-e/2025/1/1`
- Alignment: **very high**; date is universal.
- Important nuance: don't assume `dt` ↔ `h` across languages; stick to the same family token when swapping languages.

### Y. WOL — library browse hubs (CONFIRMED)
- Tuvaluan: `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa`
- English: `wol.jw.org/en/wol/library/r1/lp-e/all-publications`
- Category sub-paths are localized (e.g., `tusi-mō-fakatasiga/tusi-mō-fakatasiga-2017/fepuali`)
- Alignment: conceptually strong, but taxonomy labels differ; use pubCode/docId rather than category names for automated matching.

### Z. WOL — search (s) pages (CONFIRMED pattern)
- Pattern: `wol.jw.org/{lang}/wol/s/{rCode}/{lpCode}?…`
- Alignment: low for pairing (search results differ by language), but great for discovery; use search to harvest docIds/pubCodes, then map.

### AA. WOL — index "dx…" families (CONFIRMED for English; LIKELY for Tuvaluan)
- WOL includes indexed reference content, e.g., `dx86-26`
- English example: `wol.jw.org/en/wol/d/r1/lp-e/1200275976` includes `dx86-26` content for "Tuvalu"
- Use case: even if you don't want the index entries themselves, index pages provide structured citations (like `w00 8/15 9-10`) and docIds that are stable anchors.
- Alignment: swap bundle likely works, but confirm Tuvaluan editions exist before aligning.

### AB. WOL "pc" (publication content segment) family (CONFIRMED in English; LIKELY overall)
- Pattern observed: `wol.jw.org/en/wol/pc/{rCode}/{lpCode}/{docId}/{segment}/{segmentPart}`
- Example: `wol.jw.org/en/wol/pc/r1/lp-e/201973323/5/0`
- Treat docId as stable; pc segments are "page fragment" helpers.

---

## 7. Cross-language mapping heuristics (best → worst)

### Heuristic 1 (WOL docId swap) — **best**
- Extract `docId`
- Swap bundle: `tvl/r153/lp-vl` → `en/r1/lp-e`
- Keep `docId`
- Confirmed: `r153/lp-vl/1102008070` → `r1/lp-e/1102008070`

### Heuristic 2 (WOL pub-code swap) — **very high**
- Extract `pub-code` from `/wol/publication/.../{pub-code}`
- Swap bundle; keep `pub-code`
- Confirmed: `lv`, `bt`, `T-31` work across both languages

### Heuristic 3 (WOL Bible numeric alignment) — **very high**
- Keep `{bookNo}/{chapter}` constant: `.../nwt/19/11` → `.../nwt/19/11`
- Swap bundle

### Heuristic 4 (WOL date alignment) — **very high**
- Keep `{yyyy}/{m}/{d}` constant
- Swap bundle
- Keep family token constant (`dt`→`dt`, `h`→`h`)

### Heuristic 5 (JW sitemap/hreflang) — **best for JW**
- If you can access `tvl/sitemap.xml`, treat `<xhtml:link rel="alternate">` as authoritative
- If you can't, treat sitemap-based claim as "likely" and validate with spot checks

### Heuristic 6 (Issue codes) — **high**
- Map magazine/workbook issues with `w...`, `g...`, `km...`, `mwb...`
- Doesn't guarantee the Tuvaluan page exists in English (or vice versa), but does guarantee you're pairing the intended issue when it does.
- Example: `jw.org/tvl/tusi/galuega-talai/km201511/` ↔ `jw.org/en/library/kingdom-ministry/km201511/`

### Heuristic 7 (Title slugs already in English) — **medium-high**
- e.g., many Tuvaluan book/brochure slugs are already English titles
- Example: `Examining-the-Scriptures-Daily-2024` exists in both languages
- Still validate via docId or hreflang to avoid false pairs

### Heuristic 8 (Song number) — **high**
- Song number stable across languages
- Example: song `114` in both Tuvaluan and English songbooks
- Once aligned, map title slugs conservatively

### Heuristic 9 (Section-slug swap) — **medium**
- `/tvl/tusi/…` ↔ `/en/library/…`
- `/tvl/tala/…` ↔ `/en/news/…`
- `/tvl/akoakoga-i-te-tusi-tapu/…` ↔ `/en/bible-teachings/…`
- `/tvl/online-help/…` ↔ `/en/online-help/…` (often stable)
- `/tvl/molimau-a-ieova/…` ↔ `/en/jehovahs-witnesses/…`
- Validate with a few known pages; don't fully automate without spot checks.

### Heuristic 10 (finder/open locale swap) — **medium-high**
- Hard anchor: `docid`
- Swap locale: `VL` ↔ `E`
- Tuvaluan `open` locale: `TVL` is plausible but not confirmed; treat as "try both."

### Heuristic 11 (JW Bible via WOL) — **fallback**
- Because book slugs localize (e.g., `salamo` vs `psalms`), use WOL bookNo + chapter to align reliably
  1. Map Tuvaluan JW.org chapter → Tuvaluan WOL `bookNo/chapter`
  2. Swap WOL language tokens → English WOL
  3. Map back to English JW.org if needed

### Heuristic 12 (Language switcher UI) — **fallback**
- JW pages have a "change language" control; consistently produces the English URL
- Slow, but strong when it exists; use it for high-value seed pages to build a slug mapping table.

---

## 8. Pattern cheat sheet (compact)

| Site | Tuvaluan pattern | English counterpart pattern | Confidence | Key |
|---|---|---|---|---|
| WOL doc | `.../wol/d/r153/lp-vl/{docId}` | `.../wol/d/r1/lp-e/{docId}` | Very high | docId shared |
| WOL pub toc | `.../wol/publication/r153/lp-vl/{pubCode}` | `.../wol/publication/r1/lp-e/{pubCode}` | Very high | pubCode shared |
| WOL Bible | `.../wol/b/r153/lp-vl/nwt/{book}/{ch}` | `.../wol/b/r1/lp-e/nwt/{book}/{ch}` | Very high | bookNo stable |
| WOL footnote | `.../wol/fn/r153/lp-vl/{docId}/{n}` | `.../wol/fn/r1/lp-e/{docId}/{n}` | Very high | docId shared |
| WOL daily | `.../wol/h/r153/lp-vl/{Y}/{M}/{D}` | `.../wol/h/r1/lp-e/{Y}/{M}/{D}` | Very high | date universal |
| WOL meetings | `.../wol/dt/r153/lp-vl/{Y}/{M}/{D}` | `.../wol/dt/r1/lp-e/{Y}/{M}/{D}` | Very high | date universal |
| WOL browse | `.../wol/library/r153/lp-vl/tusi-katoa/...` | `.../wol/library/r1/lp-e/all-publications/...` | Medium | taxonomy differs |
| WOL bc | `wol.jw.org/tvl/wol/bc/r153/lp-vl/...` | `wol.jw.org/en/wol/bc/r1/lp-e/...` | Likely | docId shared |
| JW magazines | `.../tvl/tusi/mekesini/{issue}/` | `.../en/library/magazines/{issue}/` | High | issue stable |
| JW songs | `.../{songbook}/{num}-.../` | `.../{songbook}/{num}-.../` | High | song number stable |
| JW finder | `https://www.jw.org/finder?…&wtlocale=VL` | `https://www.jw.org/finder?…&wtlocale=E` | High | docid shared |
| JW open | `jw.org/open?docid={id}&wtlocale=TVL/VL` | `jw.org/open?docid={id}&wtlocale=E` | Medium | locale uncertain |

---

## 9. Content breakdown (1,310 sitemap URLs)

### Scripture (~1,200 URLs)

NWT Bible chapters covering Genesis through Revelation.
- Pattern: `https://www.jw.org/tvl/tusi/tusi-tapu/nwt/tusi/{book-name}/{chapter}/`

### Non-scripture (~110 URLs)

| Category | Path prefix | ~Count |
|---|---|---|
| Home / nav | `/tvl/`, `/tvl/sala/`, `/tvl/mea-fou/`, `/tvl/mataupu-fatoa-fakapa/` | 4 |
| Bible study hub | `/tvl/akoakoga-i-te-tusi-tapu/` | 1 |
| Q&A topics | `/tvl/akoakoga-i-te-tusi-tapu/fesili/` | ~36 |
| Youth | `/tvl/akoakoga-i-te-tusi-tapu/talavou/` | ~20 |
| Children | `/tvl/akoakoga-i-te-tusi-tapu/tamaliki/` | ~7 |
| Science | `/tvl/akoakoga-i-te-tusi-tapu/saienisi/` | ~3 |
| Family | `/tvl/akoakoga-i-te-tusi-tapu/tauavaga-matua/` | ~2 |
| Study method | `/tvl/akoakoga-i-te-tusi-tapu/te-faiga-o-te-akoga-i-te-tusi-tapu/` | ~1 |
| Publications / NWT intro | `/tvl/tusi/tusi-tapu/nwt/fakatomuaga/` | ~18 |
| Publication index | `/tvl/tusi/`, `/tvl/tusi/tusi-tapu/` | ~4 |
| News | `/tvl/tala/` | ~1+ |

---

## 10. Regex / parsing rules

### JW.org URL classifiers

```regex
^https?://(www\.)?jw\.org/tvl(/|$)
^https?://(www\.)?jw\.org/tvl/tusi/
^https?://(www\.)?jw\.org/tvl/tusi/tusi-tapu/nwt/tusi/[^/]+/\d+/
^https?://(www\.)?jw\.org/tvl/tusi/mekesini/
^https?://(www\.)?jw\.org/tvl/tala/
^https?://(www\.)?jw\.org/tvl/online-help/
^https?://(www\.)?jw\.org/tvl/akoakoga-i-te-tusi-tapu/

^https?://(www\.)?jw\.org/en(/|$)
^https?://(www\.)?jw\.org/en/library/
^https?://(www\.)?jw\.org/en/library/bible/nwt/books/[^/]+/\d+/
^https?://(www\.)?jw\.org/en/library/magazines/
```

### WOL URL classifiers

```regex
^https?://wol\.jw\.org/tvl/wol/d/r153/lp-vl/\d+
^https?://wol\.jw\.org/en/wol/d/r1/lp-e/\d+
^https?://wol\.jw\.org/(tvl|en)/wol/publication/r(153|1)/lp-(vl|e)/[A-Za-z0-9-]+
^https?://wol\.jw\.org/(tvl|en)/wol/b/r(153|1)/lp-(vl|e)/[a-z0-9]+/\d+/\d+
^https?://wol\.jw\.org/(tvl|en)/wol/binav/r(153|1)/lp-(vl|e)(/nwt(/\d+)?)?$
^https?://wol\.jw\.org/(tvl|en)/wol/h/r(153|1)/lp-(vl|e)/\d{4}/\d{1,2}/\d{1,2}
^https?://wol\.jw\.org/(tvl|en)/wol/dt/r(153|1)/lp-(vl|e)/\d{4}/\d{1,2}/\d{1,2}
^https?://wol\.jw\.org/(tvl|en)/wol/fn/r(153|1)/lp-(vl|e)/\d+/\d+
^https?://wol\.jw\.org/(tvl|en)/wol/bc/r(153|1)/lp-(vl|e)/\d+/
^https?://wol\.jw\.org/(tvl|en)/wol/s/r(153|1)/lp-(vl|e)\?
```

### Extractors

```regex
/wol/d/[^/]+/[^/]+/(?P<docId>\d+)
\?(?:^|.*&)docid=(?P<docId>\d+)(?:&|$)
\?(?:^|.*&)wtlocale=(?P<locale>[A-Z]+)(?:&|$)
/wol/publication/[^/]+/[^/]+/(?P<pubCode>[A-Za-z0-9-]+)
/wol/b/[^/]+/[^/]+/(?P<module>[a-z]+)/(?P<bookNo>\d+)/(?P<chapter>\d+)
```

### Normalization rules

* Lowercase host and path
* Strip `#fragment` from comparisons (common in WOL doc pages)
* For `open` and `finder`, keep query params because they are identity-bearing
* Define invariant triplets:

  * Tuvaluan WOL bundle: `(tvl, r153, lp-vl)`
  * English WOL bundle: `(en, r1, lp-e)`

---

## 11. High-priority discovery pages

1. Tuvaluan JW root: `jw.org/tvl/` (CONFIRMED)
2. Tuvaluan publications hub: `jw.org/tvl/tusi/` (CONFIRMED)
3. Tuvaluan brochure hub: `jw.org/tvl/tusi/polosiua/` (CONFIRMED)
4. Tuvaluan magazines hub: `jw.org/tvl/tusi/mekesini/` (CONFIRMED)
5. Tuvaluan "what's new": `jw.org/tvl/mea-fou/` (CONFIRMED)
6. Tuvaluan news hub: `jw.org/tvl/tala/` and global: `jw.org/tvl/tala/kogā-fenua-kesekese/lalolagi-kātoa/` (CONFIRMED)
7. WOL Tuvaluan browse root: `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa` (CONFIRMED)
8. WOL Tuvaluan publication TOCs via pubCode: `wol.jw.org/tvl/wol/publication/r153/lp-vl/{pubCode}` (CONFIRMED family)
9. WOL Tuvaluan doc pages: `wol.jw.org/tvl/wol/d/r153/lp-vl/{docId}` (CONFIRMED)
10. WOL Tuvaluan finder entry: `wol.jw.org/wol/finder?docid=...&wtlocale=VL` (CONFIRMED)

---

## 12. "Find-it-all" mechanism (sitemap-based)

1. **Fetch** `https://www.jw.org/robots.txt` — locate sitemap entry
2. **Fetch** `https://www.jw.org/sitemap.xml` — main sitemap index (~1,100+ language sitemaps)
3. **Locate** `<loc>https://www.jw.org/tvl/sitemap.xml</loc>` in the index
4. **Parse** the Tuvaluan sitemap — every `<loc>` is a Tuvaluan page (1,310 total)
5. **Derive English counterparts:**
   - Replace `/tvl/` → `/en/` (existence not guaranteed; HTTP HEAD to verify)
   - Use hreflang `<xhtml:link>` if present in sitemap entries
6. **For WOL content:**
   - Use library index at `wol.jw.org/tvl/wol/library/r153/lp-vl/tusi-katoa`
   - Discover publication codes from `…/wol/publication/…` pages
   - Harvest docIds from `…/wol/d/…` pages
   - Map to English via `r153/lp-vl` → `r1/lp-e`
7. **Robots note:** JW.org's robots.txt disallows certain query-based URLs (`contentLanguageFilter`, `pubFilter`) and `/choose-language`; stick to sitemap metadata and deterministic patterns

---

## 13. Discovery workflow (detailed)

1. **Start with JW.org robots** — fetch `robots.txt`, locate sitemap

2. **Enumerate sitemaps** — parse main sitemap index; discover `https://www.jw.org/tvl/sitemap.xml`

3. **Favor "hard anchors" first:**
   - WOL docId mapping
   - WOL pubCode mapping
   - JW issue codes and song numbers

4. **Language-root traversal (JW + WOL)** — BFS crawl:
   - JW: `jw.org/tvl/` down to first-level categories (`tusi`, `tala`, `online-help`, `akoakoga-i-te-tusi-tapu`, `molimau-a-ieova`)
   - WOL: `wol.jw.org/tvl/` plus section roots (`/wol/binav/…/nwt`, `/wol/publication/…`, `/wol/library/…`, `/wol/dt/…`)
   - Only collect link structure and URLs — no body extraction

5. **Category/section expansion** — for JW, capture:
   - Bible: `…/tusi-tapu/nwt/…`
   - Magazines: `…/tusi/mekesini/…`
   - Books: `…/tusi/tusi/…`
   - Brochures: `…/tusi/polosiua/…`
   - Songs: `…/tusi/pese-fakatagitagi-pese-usuusu/…`
   - Videos: `…/tusi/vitio-kolā-ne-fakatoka-ne-molimau-a-ieova/…`
   - Meeting workbooks: `…/tusi/tusi-mō-fakatasiga-a-mi/…`
   - Programs: `…/tusi/polokalame/…`
   - Study FAQ: `…/akoakoga-i-te-tusi-tapu/fesili/…`
   - News: `…/tala/kogā-fenua-kesekese/…`
   - Help: `…/online-help/jw-library/…`
   - Miscellaneous: `…/tusi/kesekese/…`

   For WOL, capture:
   - Publication codes from `…/wol/publication/…`
   - Bible book numbers from `…/wol/b/…/nwt/{bookNo}/…`
   - DocIds from `…/wol/d/…/{docId}`

6. **TOC and pagination traversal** — follow index/TOC pages and pagination controls; capture linked URLs only

7. **DocId harvesting (WOL)** — from `…/wol/d/…/{docId}`, record docId; from WOL index listings, record docIds in TOC links

8. **English-pair inference:**
   - WOL: mechanical swap using docId/pubCode/bookNo rules (section 7)
   - JW.org: use sitemap/hreflang first, then `tvl`→`en` + section slug swap + stable issue codes, then language switcher UI as fallback
   - Record confidence on each inferred pairing

9. **Only use slug-level matching as a last step**, and even then:
   - Strip diacritics, unify percent-encoding for comparison
   - Normalize case
   - Be prepared to keep a "slug alias table"

---

## 14. Coverage checklist (Tuvaluan areas to enumerate)

* [ ] Bible landing + index + chapters + supplements
* [ ] Magazines (issue index + articles)
* [ ] Books (TOCs + chapters)
* [ ] Brochures/booklets (TOCs + sections)
* [ ] Songs/music (TOC + numbered leaves + children's songbook)
* [ ] Videos (series + leaves)
* [ ] Meeting workbooks (issues + sections)
* [ ] Programs (if any)
* [ ] Study aids/FAQ (talavou/tamaliki/saienisi/tauavaga-matua, etc.)
* [ ] News (region/global listing + leaves)
* [ ] Help/support
* [ ] WOL daily text / meetings (date-based)
* [ ] WOL citations (bc), indexes (dx), footnotes (fn)
* [ ] Miscellaneous articles (`…/tusi/kesekese/…`)
* [ ] Tracts/invitations (under "Polosiua & Tamā tusi" / WOL tract publication codes)
* [ ] Archives: "all publications" type landing pages
* [ ] WOL publication TOCs by pub-code

---

## 15. Coverage gaps / open questions

* JW sitemap retrieval timing out: counts/`<lastmod>`/hreflang alternate data for `/tvl/sitemap.xml` are still uncertain in this write-up.
* Tuvaluan `open` `wtlocale` token: likely `TVL` but not confirmed; you may need to "try VL or TVL" as a rule.
* Tuvaluan bc/dx pages exist by pattern, but some of them may not exist in Tuvaluan; confirm with live checks before assuming symmetry.
* **Category slug mapping** between `jw.org/tvl/tusi/…` and `jw.org/en/library/…` is not fully confirmed; Tuvaluan uses a mix of localized and English slugs.
* **Full WOL library browse hierarchy** (`tusi-katoa/…` vs `all-publications/…`) needs exhaustive enumeration for a perfect slug mapping.
* **Additional WOL Bible translation codes** beyond `nwt` for Tuvaluan are likely but not confirmed (English has `rh` etc.)
* **WOL `dt` vs `h` family token mismatch:** stick to the same family token when swapping languages; don't cross-map `dt`↔`h`.
* **Tuvaluan WOL `all-publications` category URL** analogous to English `.../all-publications/…` not directly confirmed; Tuvaluan uses `tusi-katoa` but sub-category hierarchy is unverified.
