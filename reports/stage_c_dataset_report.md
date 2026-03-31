# Stage C Dataset Report

## Build Outputs

- Build manifest: `data/external/stage_c_seed/build_manifest.json`
- Build timestamp: `2026-03-31T07:18:45.811283+00:00`
- Default Stage C arm: `native_plus_english`
- Raw source manifest rows: `181` primary files (`182` on disk; `.DS_Store` ignored)
- Extracted text rows: `31793`
- OCR-recovered native news articles: `41`
- Native document registry rows: `124`
- Grounded SFT candidates: `3468`
- Prompt mirrors: `3172`
- News article tasks: `936`
- Entity rows: `2285`
- Glossary candidates: `1185`
- Constrained terminology tasks: `281`
- Preference rows: `1680`
- Candidate grounded split before arm filtering: train `2466`, val `290`
- Final Stage C SFT default arm: train `1148`, val `130`
- Final Stage C DPO: train `1680`, val `168`
- Held-out Stage C eval rows: `56`

## Split And Ablation Summary

- `native_only`: train `574`, val `65`
- `native_plus_english`: train `1148`, val `130`
- `native_plus_stage_b_translated`: train `1148`, val `130`
- `native_plus_bilingual`: train `2296`, val `260`
- Document contamination check: train docs `35`, val docs `4`, eval docs `14`, overlaps `0`

## Counts By Task Family

- `english_request_tvl_answer`: `78`
- `entity_extraction`: `78`
- `explain_in_english`: `54`
- `fact_sheet_to_article`: `134`
- `formal_rewrite`: `78`
- `headline_generation`: `78`
- `lead_generation`: `78`
- `mixed_request_tvl_answer`: `78`
- `native_request_article`: `78`
- `plain_language_rewrite`: `78`
- `qa_grounded`: `156`
- `quote_preservation`: `22`
- `radio_rewrite`: `78`
- `summary_medium`: `78`
- `summary_short`: `78`
- `translation_to_english`: `54`

## Counts By Prompt Language

- `en`: `639`
- `tvl`: `639`

## Counts By Assistant Language

- `en`: `108`
- `tvl`: `1170`

## Counts By Provenance

- Prompt origin `english`: `639`
- Prompt origin `native`: `639`
- Grounding level `seed_aligned_segments`: `718`
- Grounding level `direct_text_pages`: `210`
- Grounding level `ocr_page_segments`: `32`
- Grounding level `ocr_recovered_article`: `318`
- Support type `direct_support`: `412`
- Support type `fact_compilation`: `320`
- Support type `light_transform`: `546`

## Counts By Source Family

- `biodiversity_reference`: `96`
- `children_book`: `102`
- `education_pdf`: `62`
- `finance_pdf`: `34`
- `government_pdf`: `426`
- `health_pdf`: `132`
- `historic_news_scan`: `318`
- `oral_traditional_material`: `72`
- `other_source`: `36`

## Eval Slice Summary

- `government_civic`: `8`
- `cultural_narrative`: `2`
- `mixed_prompt_requests`: `20`
- `ocr_noisy_after_cleanup`: `10`
- `terminology_entity_preservation`: `16`

## Reproduction Commands

- `uv run python scripts/build_stage_c_pipeline.py --config configs/stage_c_pipeline_default.json`
- `uv run python scripts/eval_stage_c_native.py --config configs/stage_c_eval_native_oss120b.json --dry-run`
- `uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_english.json`
