# Samoan ↔ English JW Content: URL Patterns & Mapping Guide

## 0. Confidence keys (please use these everywhere)

- **CONFIRMED**: I saw this pattern or root directly on an official JW page or through official sitemap/robots evidence.
- **LIKELY**: The pattern is consistent with JW's visible URL conventions, but I haven't seen this exact Samoan + English pairing live.
- **UNCERTAIN**: Needs confirmation (either through the sitemap, hreflang alternates, or a live language switch).

---

## 1. Canonical language markers

### JW.org language path (CONFIRMED)

- Samoan: `/sm/…` → root: `https://www.jw.org/sm/`
- English: `/en/…` → root: `https://www.jw.org/en/`

### WOL language path (CONFIRMED)

- Samoan: `https://wol.jw.org/sm/…`
- English: `https://wol.jw.org/en/…`

### WOL language/region tokens (stable pairing anchors) (CONFIRMED)

These are the "swap bundle" used mechanically when mapping Samoan WOL → English WOL:

| Property | Samoan | English |
|---|---|---|
| Language path | `sm` | `en` |
| Region code | `r173` | `r1` |
| Language-pack code | `lp-sm` | `lp-e` |
| `wtlocale` (finder) | `SM` | `E` |
| `wtlocale` (open) | `SM` | `E` |

**Notes:**
- WOL's `finder` entry for Samoan is confirmed with `wtlocale=SM` and direct Samoan doc IDs in public finder URLs.
- `open?wtlocale=SM` is **confirmed** — returns 302 to the correct Samoan page.
- Samoan language is called "Faa-Samoa" in JW's internal naming.
- WOL Samoan library spans 1971–2026 (`Lomiga Faa-Samoa (1971-2026)`).

### Stable publication/issue/section tokens (shared across languages) (CONFIRMED/LIKELY)

**Confirmed anchors:**
- WOL publication codes (visible on WOL browse pages, e.g., `bt`, `lv`, `T-31`, etc.)
- WOL Bible module tokens: `nwt` (New World Translation), `bi12` (1969/2001 Bible)
- JW issue codes: `wYYYYMMDD`, `gYYYYMMDD`, `wpYYYYMMDD`, `kmYYYYMM`, `mwbYYYYMM` patterns are language-independent anchors.
- JW robots file advertises the sitemap index URL: `https://www.jw.org/sitemap.xml`

**Likely**
- Full publication code set is larger than what's publicly obvious in one listing; treat any `wol/publication/.../{pubCode}` as stable across languages.

---

## 2. Seed URLs

- **JW robots/sitemap index (CONFIRMED):** `https://www.jw.org/robots.txt` (contains `Sitemap: https://www.jw.org/sitemap.xml`)
- **Samoan sitemap (CONFIRMED):** `https://www.jw.org/sm/sitemap.xml` — fetched successfully (2.7MB response, 16,061 URLs)
- **Samoan JW.org home (CONFIRMED):** `https://www.jw.org/sm/`
- **WOL Samoan home-style entry (CONFIRMED):** `wol.jw.org/sm/wol/h/r173/lp-sm/{yyyy}/{m}/{d}`
- **WOL English home-style entry (CONFIRMED):** `https://wol.jw.org/en/wol/h/r1/lp-e/{date}`

---

## 3. Confirmed official roots (Samoan and English)

### Samoan roots (CONFIRMED)

| Root | URL | Type |
|---|---|---|
| JW.org home | `jw.org/sm/` | entry point |
| Library/publications hub | `jw.org/sm/lomiga-ma-isi-mea/` | index/TOC hub |
| Books hub | `jw.org/sm/lomiga-ma-isi-mea/tusi/` | index |
| Brochures hub | `jw.org/sm/lomiga-ma-isi-mea/polosiua/` | index |
| Bible hub | `jw.org/sm/lomiga-ma-isi-mea/tusi-paia/` | index |
| Bible NWT root | `jw.org/sm/lomiga-ma-isi-mea/tusi-paia/nwt/` | index |
| Bible BI12 root | `jw.org/sm/lomiga-ma-isi-mea/tusi-paia/bi12/` | index |
| Magazines hub | `jw.org/sm/lomiga-ma-isi-mea/mekasini/` | index |
| Songs hub | `jw.org/sm/lomiga-ma-isi-mea/musika-pese/` | index |
| Meeting workbook hub | `jw.org/sm/lomiga-ma-isi-mea/jw-polokalame-mo-le-sauniga/` | index |
| Kingdom ministry hub | `jw.org/sm/lomiga-ma-isi-mea/faiva-o-le-malo/` | index |
| Programs | `jw.org/sm/lomiga-ma-isi-mea/polokalame/` | index |
| Series | `jw.org/sm/lomiga-ma-isi-mea/faasologa/` | index |
| Tracts hub | `jw.org/sm/lomiga-ma-isi-mea/sāvali/` | index |
| Videos | `jw.org/sm/lomiga-ma-isi-mea/vitiō/` | index |
| Glossary | `jw.org/sm/lomiga-ma-isi-mea/faasino-upu/` | index |
| Guides | `jw.org/sm/lomiga-ma-isi-mea/taʻiala/` | index |
| Audio stories | `jw.org/sm/lomiga-ma-isi-mea/tala-faalogologo-faale-tusi-paia/` | index |
| Search hub | `jw.org/sm/suʻe/` | search interface |
| News hub | `jw.org/sm/mea-tutupu/` | index |
| Bible study/FAQ hub | `jw.org/sm/aʻoaʻoga-a-le-tusi-paia/` | topic hub |
| FAQ index | `jw.org/sm/aʻoaʻoga-a-le-tusi-paia/o-fesili/` | index |
| About JW | `jw.org/sm/molimau-a-ieova/` | topic hub |
| What's new | `jw.org/sm/mea-fou/` | index/listing |
| Legal matters | `jw.org/sm/mataupu-tau-tulafono/` | index |
| Help | `jw.org/sm/fesoasoani/` | index |
| WOL library browse root | `wol.jw.org/sm/wol/library/r173/lp-sm/lomiga-uma` | browse root |
| WOL bible nav root | `wol.jw.org/sm/wol/binav/r173/lp-sm/nwt` | bible nav root |
| WOL meetings root (date-based) | `wol.jw.org/sm/wol/dt/r173/lp-sm/{yyyy}/{m}/{d}` | date-based meeting content |
| WOL daily text root (date-based) | `wol.jw.org/sm/wol/h/r173/lp-sm/{yyyy}/{m}/{d}` | daily text content |

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
- Caveat: the path immediately after `/sm/` uses Samoan labels, while English uses English labels.

**Library hub (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/`
- EN: `jw.org/en/library/`
- Alignment: high structurally; second segment differs (`lomiga-ma-isi-mea` vs `library`)

**Search hub (CONFIRMED for SM entry)**
- SM: `jw.org/sm/suʻe/`
- EN: English search behavior is often via `finder` instead.
- Alignment strategy: use stable identifiers in search results (issue codes, docid-like tokens).

**What's new / All topics listings (CONFIRMED for SM and EN)**
- SM what's new: `jw.org/sm/mea-fou/`
- EN what's new: `jw.org/en/whats-new/`

---

### B. JW.org — Bible

**Bible landing (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/tusi-paia/`
- EN: `jw.org/en/library/bible/`

**Two Bible translations available in Samoan (CONFIRMED)**
- NWT (New World Translation): `…/tusi-paia/nwt/…` (1,317 URLs)
- BI12 (older translation): `…/tusi-paia/bi12/…` (1,191 URLs)

**Bible chapter leaf (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/tusi-paia/nwt/tusi/{book-slug}/{chapter}/`
- EN: `jw.org/en/library/bible/nwt/books/{book-slug}/{chapter}/`
- Alignment: very high when matched via stable bookNo + chapter.
- Example NWT: `…/nwt/tusi/kenese/1/` ↔ `…/nwt/books/genesis/1/`
- Example BI12: `…/bi12/tusi/kenese/1/` ↔ `…/bi12/books/genesis/1/`

---

### C. JW.org — magazines

**Magazine hub (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/mekasini/`
- EN: `jw.org/en/library/magazines/`

**Issue index (CONFIRMED pattern)**
- Pattern: `jw.org/{lang}/lomiga-ma-isi-mea/mekasini/{issue-code}/`
- Examples: `w20060401`, `g20040422`, `wp20150401`
- Alignment: **very high** — issue codes are language-independent.
- **7,720 magazine URLs** — the largest content category in Samoan.

---

### D. JW.org — books

**Books hub (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/tusi/`
- EN: `jw.org/en/library/books/`
- **1,479 book URLs** in Samoan sitemap.

---

### E. JW.org — brochures & booklets

**Brochures hub (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/polosiua/`
- EN: `jw.org/en/library/brochures/`
- **451 brochure URLs** in Samoan sitemap.

---

### F. JW.org — songs / music

**Songs hub (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/musika-pese/`
- **399 song URLs** in Samoan sitemap.
- Alignment: **very high** because song numbers are stable across languages.

---

### G. JW.org — videos

**Videos section (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/vitiō/`
- **265 video URLs** in Samoan sitemap.

---

### H. JW.org — meeting workbooks

**Workbook hub (CONFIRMED)**
- SM: `jw.org/sm/lomiga-ma-isi-mea/jw-polokalame-mo-le-sauniga/`
- **1,502 meeting program URLs** — a very large category in Samoan.

---

### I. JW.org — programs (CONFIRMED)
- SM: `jw.org/sm/lomiga-ma-isi-mea/polokalame/`
- **102 program URLs** in Samoan sitemap.

---

### J. JW.org — study / FAQ / Bible questions

**Study hub (CONFIRMED)**
- SM: `jw.org/sm/aʻoaʻoga-a-le-tusi-paia/`
- EN: `jw.org/en/bible-teachings/`

**Sub-categories (CONFIRMED):**
| Category | Samoan path | URLs |
|---|---|---|
| FAQ | `/sm/aʻoaʻoga-a-le-tusi-paia/o-fesili/` | 143 |
| Youth | `/sm/aʻoaʻoga-a-le-tusi-paia/talavou/` | 148 |
| Children | `/sm/aʻoaʻoga-a-le-tusi-paia/tamaiti/` | 9 |
| Science | `/sm/aʻoaʻoga-a-le-tusi-paia/faasaienisi/` | 19 |
| Family | `/sm/aʻoaʻoga-a-le-tusi-paia/aiga/` | 37 |
| Faith | `/sm/aʻoaʻoga-a-le-tusi-paia/faatuatua-i-le-atua/` | 8 |
| Peace & happiness | `/sm/aʻoaʻoga-a-le-tusi-paia/filemu-fiafia/` | 7 |
| History | `/sm/aʻoaʻoga-a-le-tusi-paia/talafaasolopito/` | 6 |
| Scripture meanings | `/sm/aʻoaʻoga-a-le-tusi-paia/mau-o-le-tusi-paia/` | 56 |
| Study tools | `/sm/aʻoaʻoga-a-le-tusi-paia/meafaigaluega-mo-suʻesuʻega-faale-tusi-paia/` | 5 |

---

### K. JW.org — news

**Samoan news (CONFIRMED)**
- Hub: `jw.org/sm/mea-tutupu/`
- EN: `jw.org/en/news/`
- **130 news URLs** in Samoan sitemap.

---

### L. JW.org — about JW

- SM: `jw.org/sm/molimau-a-ieova/`
- EN: `jw.org/en/jehovahs-witnesses/`
- **652 about-JW URLs** in Samoan sitemap.

---

### M. JW.org — help

- SM: `jw.org/sm/fesoasoani/`
- EN: `jw.org/en/online-help/`
- **3 help URLs** in Samoan sitemap.

---

### N. JW.org — kingdom ministry

- SM: `jw.org/sm/lomiga-ma-isi-mea/faiva-o-le-malo/`
- EN: `jw.org/en/library/kingdom-ministry/`
- **74 URLs** in Samoan sitemap.

---

### O. JW.org — tracts & invitations

- SM: `jw.org/sm/lomiga-ma-isi-mea/sāvali/`
- **72 URLs** in Samoan sitemap.

---

### P. JW.org — series / topic series

- SM: `jw.org/sm/lomiga-ma-isi-mea/faasologa/`
- **204 URLs** in Samoan sitemap.

---

## 5. JW.org resolver endpoints (important bilingual anchors)

### O. JW.org — `finder` resolver (CONFIRMED)
- Pattern: `https://www.jw.org/finder?…&wtlocale={locale}`
- Samoan: `wtlocale=SM`
- English: `wtlocale=E`
- Useful params:
  - `docid` (hard anchor)
  - `lank` (selection identifier)
  - `item` (publication/item codes)

**Key point:** `finder` is one of the strongest ways to "join" an otherwise unaligned slug, because `docid` is cross-language stable.

### P. JW.org — `open` resolver (CONFIRMED)
- Pattern: `https://www.jw.org/open?docid={docid}&wtlocale={locale}`
- English: confirmed with `wtlocale=E`
- Samoan: confirmed with `wtlocale=SM` (returns 302 to correct Samoan page)
- Verified: `open?wtlocale=SM&docid=1102008070` → `/sm/lomiga-ma-isi-mea/tusi/alofa-o-le-atua/faamamaluina-le-faaipoipoga/`

---

## 6. WOL URL families (docId + code-based — strongest pairing)

### Q. WOL — document pages (docId-based) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/d/{rCode}/{lpCode}/{docId}`
- Samoan example: `wol.jw.org/sm/wol/d/r173/lp-sm/1102008070`
- English swap bundle: `wol.jw.org/en/wol/d/r1/lp-e/1102008070`
- **docId stays the same across languages** (highest confidence in alignment)

### R. WOL — publication TOC pages (pub-code-based) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/publication/{rCode}/{lpCode}/{pub-code}`
- Samoan: `.../r173/lp-sm/{pub-code}`
- English: `.../r1/lp-e/{pub-code}`

### S. WOL — Bible chapter pages (bookNo + chapter) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/b/{rCode}/{lpCode}/nwt/{bookNo}/{chapter}`
- SM: `.../r173/lp-sm/nwt/1/1` (Genesis 1 — 31 verses confirmed)
- EN: `.../r1/lp-e/nwt/1/1`
- Alignment: very high because bookNo is numeric and stable across languages.
- **HTML structure confirmed:** `<span class="v" id="v{bookNo}-{ch}-{verse}-{part}">` — same as Tuvaluan.

### T. WOL — Bible navigation pages (CONFIRMED pattern)
- Root: `wol.jw.org/{lang}/wol/binav/{rCode}/{lpCode}/nwt`
- By book: `.../nwt/{bookNo}`

### U. WOL — Bible citations (bc) (LIKELY)
- Alignment rule: swap bundle + keep docId and anchor structure.

### V. WOL — footnote pages (fn) (CONFIRMED pattern)
- Pattern: `wol.jw.org/{lang}/wol/fn/{rCode}/{lpCode}/{docId}/{footnoteNo}`

### W. WOL — daily text (date-based, h-family) (CONFIRMED)
- Pattern: `wol.jw.org/{lang}/wol/h/{rCode}/{lpCode}/{yyyy}/{m}/{d}`
- SM: `.../r173/lp-sm/2025/3/1`
- EN: `.../r1/lp-e/2025/3/1`
- Alignment: **extremely high**; date is universal.
- **HTML structure confirmed:** `div.tabContent[data-date]` → `p.themeScrp` + `p.sb` (3 consecutive days per page).

### X. WOL — meetings/schedule (date-based, dt-family) (CONFIRMED pattern)
- Pattern: `wol.jw.org/{lang}/wol/dt/{rCode}/{lpCode}/{yyyy}/{m}/{d}`
- SM: `.../r173/lp-sm/2025/1/1`
- EN: `.../r1/lp-e/2025/1/1`
- Alignment: **very high**; date is universal.

### Y. WOL — library browse hubs (CONFIRMED)
- Samoan: `wol.jw.org/sm/wol/library/r173/lp-sm/lomiga-uma`
- English: `wol.jw.org/en/wol/library/r1/lp-e/all-publications`

**WOL Library categories (CONFIRMED):**
| Samoan slug | Samoan name | English equivalent |
|---|---|---|
| `lomiga-uma` | LOMIGA | All Publications |
| `lomiga-uma/tusi-paia` | Tusi Paia | Bible |
| `lomiga-uma/fesoasoani-mo-saʻiliʻiliga` | Fesoasoani mo Saʻiliʻiliga | Research Aids |
| `lomiga-uma/le-olomatamata` | Le Olomatamata | The Watchtower |
| `lomiga-uma/ala-mai` | Ala Mai! | Awake! |
| `lomiga-uma/tusi` | Tusi | Books |
| `lomiga-uma/polokalame-mo-le-sauniga` | Polokalame mo le Sauniga | Meeting Programs |
| `lomiga-uma/faiva-o-le-malo` | Faiva o le Malo | Kingdom Ministry |
| `lomiga-uma/polosiua-ma-tamaʻitusi` | Polosiua ma Tamaʻitusi | Brochures & Booklets |
| `lomiga-uma/sāvali` | Sāvali | Tracts |
| `lomiga-uma/polokalame` | Polokalame | Programs |
| `lomiga-uma/faasologa-o-mataupu` | Faasologa o Mataupu | Topic Series |
| `lomiga-uma/faatonuga-ma-taʻiala` | Faatonuga ma Taʻiala | Instructions & Guides |

### Z. WOL — search (s) pages (CONFIRMED pattern)
- Pattern: `wol.jw.org/{lang}/wol/s/{rCode}/{lpCode}?…`

---

## 7. Cross-language mapping heuristics (best → worst)

### Heuristic 1 (WOL docId swap) — **best**
- Extract `docId`
- Swap bundle: `sm/r173/lp-sm` → `en/r1/lp-e`
- Keep `docId`
- Confirmed: `open?wtlocale=SM&docid=1102008070` resolves correctly

### Heuristic 2 (WOL pub-code swap) — **very high**
- Extract `pub-code` from `/wol/publication/.../{pub-code}`
- Swap bundle; keep `pub-code`

### Heuristic 3 (WOL Bible numeric alignment) — **very high**
- Keep `{bookNo}/{chapter}` constant
- Swap bundle
- Works for both NWT and BI12

### Heuristic 4 (WOL date alignment) — **very high**
- Keep `{yyyy}/{m}/{d}` constant
- Swap bundle
- Keep family token constant (`dt`→`dt`, `h`→`h`)

### Heuristic 5 (JW sitemap/hreflang) — **best for JW**
- `sm/sitemap.xml` has 16,061 URLs
- Use `<xhtml:link rel="alternate">` as authoritative when available

### Heuristic 6 (Issue codes) — **high**
- Map magazine/workbook issues with `w...`, `g...`, `km...`, `mwb...`

### Heuristic 7 (Title slugs already in English) — **medium-high**
- Some Samoan book/brochure slugs use English titles

### Heuristic 8 (Song number) — **high**
- Song number stable across languages

### Heuristic 9 (Section-slug swap) — **medium**
- `/sm/lomiga-ma-isi-mea/…` ↔ `/en/library/…`
- `/sm/mea-tutupu/…` ↔ `/en/news/…`
- `/sm/aʻoaʻoga-a-le-tusi-paia/…` ↔ `/en/bible-teachings/…`
- `/sm/fesoasoani/…` ↔ `/en/online-help/…`
- `/sm/molimau-a-ieova/…` ↔ `/en/jehovahs-witnesses/…`

### Heuristic 10 (finder/open locale swap) — **high**
- Hard anchor: `docid`
- Swap locale: `SM` ↔ `E`

### Heuristic 11 (JW Bible via WOL) — **fallback**
- Book slugs localize (e.g., `kenese` vs `genesis`); use WOL bookNo + chapter

### Heuristic 12 (Language switcher UI) — **fallback**
- JW pages have a "change language" control

---

## 8. Pattern cheat sheet (compact)

| Site | Samoan pattern | English counterpart pattern | Confidence | Key |
|---|---|---|---|---|
| WOL doc | `.../wol/d/r173/lp-sm/{docId}` | `.../wol/d/r1/lp-e/{docId}` | Very high | docId shared |
| WOL pub toc | `.../wol/publication/r173/lp-sm/{pubCode}` | `.../wol/publication/r1/lp-e/{pubCode}` | Very high | pubCode shared |
| WOL Bible | `.../wol/b/r173/lp-sm/nwt/{book}/{ch}` | `.../wol/b/r1/lp-e/nwt/{book}/{ch}` | Very high | bookNo stable |
| WOL footnote | `.../wol/fn/r173/lp-sm/{docId}/{n}` | `.../wol/fn/r1/lp-e/{docId}/{n}` | Very high | docId shared |
| WOL daily | `.../wol/h/r173/lp-sm/{Y}/{M}/{D}` | `.../wol/h/r1/lp-e/{Y}/{M}/{D}` | Very high | date universal |
| WOL meetings | `.../wol/dt/r173/lp-sm/{Y}/{M}/{D}` | `.../wol/dt/r1/lp-e/{Y}/{M}/{D}` | Very high | date universal |
| WOL browse | `.../wol/library/r173/lp-sm/lomiga-uma/...` | `.../wol/library/r1/lp-e/all-publications/...` | Medium | taxonomy differs |
| JW magazines | `.../sm/lomiga-ma-isi-mea/mekasini/{issue}/` | `.../en/library/magazines/{issue}/` | High | issue stable |
| JW songs | `.../{songbook}/{num}-.../` | `.../{songbook}/{num}-.../` | High | song number stable |
| JW finder | `https://www.jw.org/finder?…&wtlocale=SM` | `https://www.jw.org/finder?…&wtlocale=E` | High | docid shared |
| JW open | `jw.org/open?docid={id}&wtlocale=SM` | `jw.org/open?docid={id}&wtlocale=E` | Very high | locale confirmed |

---

## 9. Content breakdown (16,061 sitemap URLs)

### By top-level category

| Category | Path prefix | URLs |
|---|---|---|
| Magazines | `/sm/lomiga-ma-isi-mea/mekasini/` | 7,720 |
| Bible chapters | `/sm/lomiga-ma-isi-mea/tusi-paia/.../tusi/{book}/{ch}/` | 2,378 |
| Meeting programs | `/sm/lomiga-ma-isi-mea/jw-polokalame-mo-le-sauniga/` | 1,502 |
| Books | `/sm/lomiga-ma-isi-mea/tusi/` | 1,479 |
| About JW | `/sm/molimau-a-ieova/` | 652 |
| Brochures | `/sm/lomiga-ma-isi-mea/polosiua/` | 451 |
| Songs | `/sm/lomiga-ma-isi-mea/musika-pese/` | 399 |
| Videos | `/sm/lomiga-ma-isi-mea/vitiō/` | 265 |
| Series | `/sm/lomiga-ma-isi-mea/faasologa/` | 204 |
| Youth | `/sm/aʻoaʻoga-a-le-tusi-paia/talavou/` | 148 |
| FAQ | `/sm/aʻoaʻoga-a-le-tusi-paia/o-fesili/` | 143 |
| News | `/sm/mea-tutupu/` | 130 |
| Programs | `/sm/lomiga-ma-isi-mea/polokalame/` | 102 |
| Kingdom ministry | `/sm/lomiga-ma-isi-mea/faiva-o-le-malo/` | 74 |
| Tracts | `/sm/lomiga-ma-isi-mea/sāvali/` | 72 |
| Bible indexes | `/sm/lomiga-ma-isi-mea/tusi-paia/` (non-chapter) | 131 |
| Scripture meanings | `/sm/aʻoaʻoga-a-le-tusi-paia/mau-o-le-tusi-paia/` | 56 |
| Family | `/sm/aʻoaʻoga-a-le-tusi-paia/aiga/` | 37 |
| Science | `/sm/aʻoaʻoga-a-le-tusi-paia/faasaienisi/` | 19 |
| What's new | `/sm/mea-fou/` | 15 |
| Legal | `/sm/mataupu-tau-tulafono/` | 14 |
| Audio stories | `/sm/lomiga-ma-isi-mea/tala-faalogologo-faale-tusi-paia/` | 14 |
| Children | `/sm/aʻoaʻoga-a-le-tusi-paia/tamaiti/` | 9 |
| Others | various | ~41 |

### Bible versions

| Version | Code | Chapter URLs | Book TOC URLs |
|---|---|---|---|
| New World Translation | `nwt` | ~1,189 | ~68 |
| 1969/2001 Bible | `bi12` | ~1,189 | ~68 |

### Comparison with Tuvaluan

| Metric | Samoan | Tuvaluan | Ratio |
|---|---|---|---|
| Total sitemap URLs | 16,061 | 7,103 | 2.3× |
| Bible chapters | 2,378 | 1,189 | 2.0× |
| Magazine URLs | 7,720 | 2,489 | 3.1× |
| Book URLs | 1,479 | 499 | 3.0× |
| Bible versions | 2 (nwt, bi12) | 1 (nwt) | — |

---

## 10. Regex / parsing rules

### JW.org URL classifiers

```regex
^https?://(www\.)?jw\.org/sm(/|$)
^https?://(www\.)?jw\.org/sm/lomiga-ma-isi-mea/
^https?://(www\.)?jw\.org/sm/lomiga-ma-isi-mea/tusi-paia/nwt/tusi/[^/]+/\d+/
^https?://(www\.)?jw\.org/sm/lomiga-ma-isi-mea/tusi-paia/bi12/tusi/[^/]+/\d+/
^https?://(www\.)?jw\.org/sm/lomiga-ma-isi-mea/mekasini/
^https?://(www\.)?jw\.org/sm/mea-tutupu/
^https?://(www\.)?jw\.org/sm/fesoasoani/
^https?://(www\.)?jw\.org/sm/a%CA%BBoa%CA%BBoga-a-le-tusi-paia/

^https?://(www\.)?jw\.org/en(/|$)
^https?://(www\.)?jw\.org/en/library/
^https?://(www\.)?jw\.org/en/library/bible/nwt/books/[^/]+/\d+/
^https?://(www\.)?jw\.org/en/library/magazines/
```

### WOL URL classifiers

```regex
^https?://wol\.jw\.org/sm/wol/d/r173/lp-sm/\d+
^https?://wol\.jw\.org/en/wol/d/r1/lp-e/\d+
^https?://wol\.jw\.org/(sm|en)/wol/publication/r(173|1)/lp-(sm|e)/[A-Za-z0-9-]+
^https?://wol\.jw\.org/(sm|en)/wol/b/r(173|1)/lp-(sm|e)/[a-z0-9]+/\d+/\d+
^https?://wol\.jw\.org/(sm|en)/wol/binav/r(173|1)/lp-(sm|e)(/nwt(/\d+)?)?$
^https?://wol\.jw\.org/(sm|en)/wol/h/r(173|1)/lp-(sm|e)/\d{4}/\d{1,2}/\d{1,2}
^https?://wol\.jw\.org/(sm|en)/wol/dt/r(173|1)/lp-(sm|e)/\d{4}/\d{1,2}/\d{1,2}
^https?://wol\.jw\.org/(sm|en)/wol/fn/r(173|1)/lp-(sm|e)/\d+/\d+
^https?://wol\.jw\.org/(sm|en)/wol/bc/r(173|1)/lp-(sm|e)/\d+/
^https?://wol\.jw\.org/(sm|en)/wol/s/r(173|1)/lp-(sm|e)\?
```

### Extractors

```regex
/wol/d/[^/]+/[^/]+/(?P<docId>\d+)
\?(?:^|.*&)docid=(?P<docId>\d+)(?:&|$)
\?(?:^|.*&)wtlocale=(?P<locale>[A-Z]+)(?:&|$)
/wol/publication/[^/]+/[^/]+/(?P<pubCode>[A-Za-z0-9-]+)
/wol/b/[^/]+/[^/]+/(?P<module>[a-z0-9]+)/(?P<bookNo>\d+)/(?P<chapter>\d+)
```

### Normalization rules

* Lowercase host and path
* Strip `#fragment` from comparisons
* For `open` and `finder`, keep query params because they are identity-bearing
* Define invariant triplets:
  * Samoan WOL bundle: `(sm, r173, lp-sm)`
  * English WOL bundle: `(en, r1, lp-e)`

---

## 11. High-priority discovery pages

1. Samoan JW root: `jw.org/sm/` (CONFIRMED)
2. Samoan publications hub: `jw.org/sm/lomiga-ma-isi-mea/` (CONFIRMED)
3. Samoan magazines hub: `jw.org/sm/lomiga-ma-isi-mea/mekasini/` (CONFIRMED)
4. Samoan books hub: `jw.org/sm/lomiga-ma-isi-mea/tusi/` (CONFIRMED)
5. Samoan brochure hub: `jw.org/sm/lomiga-ma-isi-mea/polosiua/` (CONFIRMED)
6. Samoan news hub: `jw.org/sm/mea-tutupu/` (CONFIRMED)
7. Samoan "what's new": `jw.org/sm/mea-fou/` (CONFIRMED)
8. WOL Samoan browse root: `wol.jw.org/sm/wol/library/r173/lp-sm/lomiga-uma` (CONFIRMED)
9. WOL Samoan publication TOCs via pubCode: `wol.jw.org/sm/wol/publication/r173/lp-sm/{pubCode}` (CONFIRMED family)
10. WOL Samoan doc pages: `wol.jw.org/sm/wol/d/r173/lp-sm/{docId}` (CONFIRMED)
11. WOL Samoan finder entry: `wol.jw.org/wol/finder?docid=...&wtlocale=SM` (CONFIRMED)

---

## 12. "Find-it-all" mechanism (sitemap-based)

1. **Fetch** `https://www.jw.org/robots.txt` — locate sitemap entry
2. **Fetch** `https://www.jw.org/sitemap.xml` — main sitemap index
3. **Locate** `<loc>https://www.jw.org/sm/sitemap.xml</loc>` in the index
4. **Parse** the Samoan sitemap — every `<loc>` is a Samoan page (16,061 total)
5. **Derive English counterparts:**
   - Replace `/sm/` → `/en/` (existence not guaranteed; HTTP HEAD to verify)
   - Use hreflang `<xhtml:link>` if present in sitemap entries
6. **For WOL content:**
   - Use library index at `wol.jw.org/sm/wol/library/r173/lp-sm/lomiga-uma`
   - Discover publication codes from `…/wol/publication/…` pages
   - Harvest docIds from `…/wol/d/…` pages
   - Map to English via `r173/lp-sm` → `r1/lp-e`
7. **Robots note:** JW.org's robots.txt disallows certain query-based URLs; stick to sitemap metadata and deterministic patterns

---

## 13. Discovery workflow (detailed)

1. **Start with JW.org robots** — fetch `robots.txt`, locate sitemap

2. **Enumerate sitemaps** — parse main sitemap index; discover `https://www.jw.org/sm/sitemap.xml`

3. **Favor "hard anchors" first:**
   - WOL docId mapping
   - WOL pubCode mapping
   - JW issue codes and song numbers

4. **Language-root traversal (JW + WOL)** — BFS crawl:
   - JW: `jw.org/sm/` down to first-level categories (`lomiga-ma-isi-mea`, `mea-tutupu`, `fesoasoani`, `aʻoaʻoga-a-le-tusi-paia`, `molimau-a-ieova`)
   - WOL: `wol.jw.org/sm/` plus section roots (`/wol/binav/…/nwt`, `/wol/publication/…`, `/wol/library/…`, `/wol/dt/…`)
   - Only collect link structure and URLs — no body extraction

5. **Category/section expansion** — for JW, capture:
   - Bible: `…/lomiga-ma-isi-mea/tusi-paia/nwt/…` and `…/bi12/…`
   - Magazines: `…/lomiga-ma-isi-mea/mekasini/…`
   - Books: `…/lomiga-ma-isi-mea/tusi/…`
   - Brochures: `…/lomiga-ma-isi-mea/polosiua/…`
   - Songs: `…/lomiga-ma-isi-mea/musika-pese/…`
   - Videos: `…/lomiga-ma-isi-mea/vitiō/…`
   - Meeting workbooks: `…/lomiga-ma-isi-mea/jw-polokalame-mo-le-sauniga/…`
   - Kingdom ministry: `…/lomiga-ma-isi-mea/faiva-o-le-malo/…`
   - Programs: `…/lomiga-ma-isi-mea/polokalame/…`
   - Series: `…/lomiga-ma-isi-mea/faasologa/…`
   - Tracts: `…/lomiga-ma-isi-mea/sāvali/…`
   - Study FAQ: `…/aʻoaʻoga-a-le-tusi-paia/o-fesili/…`
   - News: `…/mea-tutupu/…`
   - Help: `…/fesoasoani/…`

   For WOL, capture:
   - Publication codes from `…/wol/publication/…`
   - Bible book numbers from `…/wol/b/…/nwt/{bookNo}/…`
   - DocIds from `…/wol/d/…/{docId}`

6. **TOC and pagination traversal** — follow index/TOC pages; capture linked URLs only

7. **DocId harvesting (WOL)** — from `…/wol/d/…/{docId}`, record docId; from WOL index listings, record docIds in TOC links

8. **English-pair inference:**
   - WOL: mechanical swap using docId/pubCode/bookNo rules (section 7)
   - JW.org: use sitemap/hreflang first, then `sm`→`en` + section slug swap + stable issue codes
   - Record confidence on each inferred pairing

---

## 14. Coverage checklist (Samoan areas to enumerate)

* [ ] Bible NWT landing + index + chapters
* [ ] Bible BI12 landing + index + chapters
* [ ] Bible supplements (introductions, appendices)
* [ ] Magazines (issue index + articles) — **7,720 URLs, largest category**
* [ ] Books (TOCs + chapters) — **1,479 URLs**
* [ ] Brochures/booklets (TOCs + sections)
* [ ] Songs/music (TOC + numbered leaves)
* [ ] Videos (series + leaves)
* [ ] Meeting programs (issues + sections) — **1,502 URLs**
* [ ] Kingdom ministry (issues + sections)
* [ ] Programs (if any)
* [ ] Series / topic series
* [ ] Tracts & invitations
* [ ] Study aids/FAQ (talavou/tamaiti/faasaienisi/aiga, etc.)
* [ ] Scripture meanings / Bible verse explanations
* [ ] News
* [ ] About JW — **652 URLs**
* [ ] Help/support
* [ ] WOL daily text / meetings (date-based)
* [ ] WOL citations (bc), indexes (dx), footnotes (fn)
* [ ] Audio Bible stories
* [ ] Glossary / index terms
* [ ] WOL publication TOCs by pub-code
* [ ] Legal matters

---

## 15. Coverage gaps / open questions

* **Samoan has significantly more content than Tuvaluan** (16,061 vs 7,103 sitemap URLs = 2.3× more), especially in magazines (3.1×) and books (3.0×).
* **Two Bible versions** (NWT + BI12) — need to handle both in scraping. BI12 may have different verse structure.
* **BI12 Bible HTML structure** needs verification — may differ from NWT's `<span class="v">` pattern.
* **WOL publication codes** for Samoan need exhaustive enumeration from the library browse page.
* **Category slug mapping** between `jw.org/sm/lomiga-ma-isi-mea/…` and `jw.org/en/library/…` needs validation with sample pages.
* **Full WOL library browse hierarchy** (`lomiga-uma/…` vs `all-publications/…`) needs exhaustive enumeration.
* **Samoan Watchtower name**: "Le Olomatamata" (The Watchtower), "Ala Mai!" (Awake!).
* **Samoan daily text** confirmed working — same HTML structure as Tuvaluan (3-day pages, `p.themeScrp` + `p.sb`).
* **WOL `dt` vs `h` family token mismatch:** stick to the same family token when swapping languages.
* **Samoan Sign Language** (`sgn-WS`, `lp-sms`, `r555`) exists separately — do not confuse with Samoan (`sm`, `lp-sm`, `r173`).

---

## 16. Script adaptation notes (from Tuvaluan pipeline)

The existing scraping pipeline (`scripts/`) can be adapted for Samoan by changing the language bundles:

### Bundle constants to change

```python
# Tuvaluan (current)
TVL_BUNDLE = {"lang": "tvl", "rcode": "r153", "lpcode": "lp-vl"}

# Samoan (new)
SM_BUNDLE = {"lang": "sm", "rcode": "r173", "lpcode": "lp-sm"}

# English (unchanged)
EN_BUNDLE = {"lang": "en", "rcode": "r1", "lpcode": "lp-e"}
```

### scrape_sitemap.py adaptation
- Change `SITEMAP_URL` to `"https://www.jw.org/sm/sitemap.xml"`
- Update all classifiers to use `/sm/lomiga-ma-isi-mea/` paths instead of `/tvl/tusi/` paths
- Output to `data/raw/sitemap_sm.json`

### scrape_bible.py adaptation
- Replace `TVL_BUNDLE` with `SM_BUNDLE`
- Update raw file paths from `wol_tvl` to `wol_sm`
- Change output field from `"tvl"` to `"sm"` in pair records
- Add BI12 support: allow `--version bi12` flag in addition to NWT
- Output to separate `data/aligned/bible_verses_sm.jsonl`

### scrape_articles.py adaptation
- Replace `TVL_BUNDLE` with `SM_BUNDLE`
- Update `WOL_PUB_TOC_URL` to use `r173/lp-sm`
- Update `SECTION_RE` and `LIBRARY_RE` to match `r173/lp-sm`
- Update `harvest_all_library` category slugs to Samoan WOL categories:
  - `"le-olomatamata"` (Watchtower), `"ala-mai"` (Awake!), `"tusi"` (Books),
    `"polokalame-mo-le-sauniga"` (Meeting), `"faiva-o-le-malo"` (Ministry),
    `"polosiua-ma-tamaʻitusi"` (Brochures)
- Output to `data/aligned/articles_sm.jsonl`

### scrape_daily_text.py adaptation
- Replace `TVL_BUNDLE` with `SM_BUNDLE`
- Update raw file paths from `wol_tvl` to `wol_sm`
- Change output field from `"tvl"` to `"sm"` in pair records
- Output to `data/aligned/daily_text_sm.jsonl`

### HTML parsing (no changes expected)
- Bible: `<span class="v" id="v{bookNo}-{ch}-{verse}-{part}">` — **confirmed identical** in Samoan WOL
- Articles: `article#article` → `p[data-pid]` — same structure expected
- Daily text: `div.tabContent[data-date]` → `p.themeScrp` + `p.sb` — **confirmed identical** in Samoan WOL
