# Stage C Raw Source Manifest

## Snapshot

- Raw files under `unstruct_lang_data/`: `182`.
- Manifest rows emitted: `181`.
- Ignored helper file: `unstruct_lang_data/REAL ONES ONLY/.DS_Store`.
- Manifest path: `data/external/stage_c_seed/raw_source_manifest.jsonl`.

## By Source Family

- `audio_video_asset`: `67`
- `biodiversity_reference`: `5`
- `children_book`: `30`
- `duplicate_reference`: `6`
- `education_pdf`: `4`
- `finance_pdf`: `4`
- `government_pdf`: `25`
- `health_pdf`: `10`
- `historic_news_scan`: `5`
- `lexical_reference`: `15`
- `oral_traditional_material`: `2`
- `other_source`: `1`
- `quarantine_pdf`: `7`

## By Status Guess

- `Duplicate/reference`: `6`
- `Media-only`: `67`
- `Merged`: `30`
- `Raw-only`: `75`
- `Term-only`: `3`

## Priority Notes

- Historic news scans and raw-only civic PDFs are marked for promotion into grounded Stage C tasks.
- Duplicate/reference assets and `REAL ONES ONLY/Documents/Don_t use yet/` are kept visible in the manifest but excluded from the default SFT pool.
- Audio/video files remain manifest entries with transcript-path notes rather than direct text-training inputs.
