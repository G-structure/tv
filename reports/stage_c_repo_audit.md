# Stage C Repo Audit

## Current Entrypoints

- `scripts/build_stage_a_mt_data.py` -> `tv/training/stage_a_mt/build_data.py`.
- `scripts/train_stage_a_translation.py` and `scripts/eval_stage_a_translation.py` remain the Stage A train/eval entrypoints.
- `scripts/build_stage_b_sources.py`, `scripts/generate_stage_b_synthetic_tvl.py`, and `scripts/build_stage_b_mix.py` are the live Stage B data builders.
- `scripts/train_stage_b_agent.py` and `scripts/eval_stage_b_agent.py` are the live Stage B train/eval entrypoints.

## Observed Active Dataset Usage

- Latest `stage_a_mt` manifest exists at `data/finetune/stage_a_mt/manifest.json` with `182713` accepted rows.
- Latest `stage_b_mix` manifest anchors against `data/finetune/stage_a_mt/train_balanced.jsonl`.
- Current Stage B training therefore uses `stage_a_mt`, not `stage_a_mt_v2`, as its anchor path.
- `data/finetune/stage_a_mt_v2/` exists, but current checked-in Stage B configs still point to `data/finetune/stage_a_mt/train_balanced.jsonl`.

## Unstructured Builders

- `scripts/run_unstructured_datamining.py` orchestrates OCR/seed generation.
- `scripts/ocr_scanned_pdfs.py` produces page-level OCR artifacts in `data/external/ocr_scans/`.
- `scripts/build_unstructured_seed.py` converts unstructured assets into `data/external/stage_a_seed/` and `data/external/stage_b_seed/`.
- `tv/corpus/render.py` is the current path that merges the unstructured seed into `data/finetune/stage_a_mt_v2/`.

## Minimal Safe Stage C Integration Points

- Reuse repo-relative JSONL + manifest conventions from `tv/common/io.py` and `tv/common/manifests.py`.
- Keep Stage C source recovery separate from training-ready renders under `data/external/stage_c_seed/` and `data/finetune/stage_c_*`.
- Plug Stage C SFT datasets into the existing `scripts/train_stage_b_agent.py` flow through config-level data-path changes instead of altering the trainer core.
- Add a Stage C-native eval script rather than forcing the Stage B translation eval to judge native grounding.

## Execution Order Chosen

1. Build repo audit and raw source manifest.
2. Reuse existing Stage A seed and OCR artifacts, then add direct extraction for raw-only PDFs and images.
3. Recover OCR-heavy native news into article-level bundles where feasible and register every usable document with provenance.
4. Generate grounded SFT, news-article tasks, mirrors, terminology tasks, preferences, and held-out eval items.
5. Assemble Stage C train/val/DPO/eval renders and arm-specific prompt-mixture ablation files.
6. Wire training/eval through new Stage C configs, run dataset smoke validation, and update canonical docs/reports.
