# Stage C Ship Report

## What Changed

- Added a full Stage C builder at `scripts/build_stage_c_pipeline.py` and `tv/training/stage_c/pipeline.py`.
- Added a Stage C held-out native eval path at `scripts/eval_stage_c_native.py` and `tv/training/stage_c/eval.py`.
- Added optional OpenAI-backed offline job tooling at `scripts/stage_c_openai_jobs.py` and `tv/training/stage_c/openai_jobs.py`.
- Added Stage C configs for pipeline build, held-out eval, and four ablation arms under `configs/`.
- Wired Stage C training into the existing Stage B trainer by config-level dataset swaps rather than trainer-core changes.
- Added Stage C CLI/config smoke coverage in `tests/test_cli_smoke.py` and `tests/test_config.py`.
- Updated the repo-facing Stage C docs to match the shipped paths and commands.

## Artifacts Built

- `data/external/stage_c_seed/raw_source_manifest.jsonl`
- `data/external/stage_c_seed/extracted_text/page_text.jsonl`
- `data/external/stage_c_seed/ocr_recovered/native_news_articles.jsonl`
- `data/external/stage_c_seed/ocr_recovered/recovered_segments.jsonl`
- `data/external/stage_c_seed/native_doc_registry.jsonl`
- `data/external/stage_c_seed/grounded_sft.jsonl`
- `data/external/stage_c_seed/news_article_tasks.jsonl`
- `data/external/stage_c_seed/grounded_sft_mirrors.jsonl`
- `data/external/stage_c_seed/terms/entities.jsonl`
- `data/external/stage_c_seed/terms/glossary_candidates.jsonl`
- `data/external/stage_c_seed/terms/constrained_tasks.jsonl`
- `data/external/stage_c_seed/preferences.jsonl`
- `data/external/stage_c_seed/build_manifest.json`
- `data/finetune/stage_c_sft/train.jsonl`
- `data/finetune/stage_c_sft/val.jsonl`
- `data/finetune/stage_c_sft/arms/*.jsonl`
- `data/finetune/stage_c_dpo/train.jsonl`
- `data/finetune/stage_c_dpo/val.jsonl`
- `data/finetune/stage_c_eval/manifest.jsonl`
- `data/finetune/stage_c_eval/held_out_native.jsonl`
- `eval/stage_c_native/manifest.jsonl`
- `eval/stage_c_native/human_check_subset.jsonl`
- `eval/stage_c_native/rubric.md`
- `reports/stage_c_repo_audit.md`
- `reports/stage_c_raw_source_manifest.md`
- `reports/stage_c_dataset_report.md`

## Counts And Quality Notes

- Raw files under `unstruct_lang_data/`: `182`
- Manifested primary files: `181`
- Extracted text rows: `31793`
- OCR-recovered native news articles: `41`
- Native document registry rows: `124`
- Grounded SFT candidates: `3468`
- Prompt mirrors: `3172`
- News article tasks: `936`
- Entity rows: `2285`
- Glossary candidates: `1185`
- Constrained terminology tasks: `281`
- Preference pairs: `1680`
- Final default Stage C SFT: train `1148`, val `130`
- Final Stage C DPO: train `1680`, val `168`
- Held-out native eval rows: `56`
- Default Stage C assistant language mix: `1170` TVL, `108` EN
- Default Stage C prompt language mix: `639` TVL, `639` EN
- Default Stage C provenance mix: `718` seed-aligned, `210` direct-text pages, `32` OCR page segments, `318` OCR-recovered articles
- Contamination check: train/val/eval doc overlap `0`

Quality gates that are now enforced by default:

- hold out by `source_doc_id`
- exclude duplicate/reference and quarantine sources from default SFT
- gate English-dominant bundles out of the default grounded TVL pool
- keep support type and provenance on every trainable Stage C example
- keep preference data separate from grounded SFT

## Validation Commands Run

These commands were run successfully in this checkout:

```bash
python scripts/build_stage_c_pipeline.py --config configs/stage_c_pipeline_default.json
python scripts/eval_stage_c_native.py --config configs/stage_c_eval_native_oss120b.json --dry-run
python scripts/stage_c_openai_jobs.py --job-type prompt_synthesis --input-path data/external/stage_c_seed/grounded_sft_mirrors.jsonl --output-dir data/external/stage_c_seed/openai_jobs/prompt_synthesis --max-rows 10
pytest tests/test_cli_smoke.py tests/test_config.py -q
python - <<'PY'
import datasets
from tv.common.config import load_config
from scripts.train_stage_b_agent import _translate_config
cfg = _translate_config(load_config('configs/stage_c_agent_oss120b_native_plus_english.json'), pilot=False)
train = datasets.load_dataset('json', data_files={'train': cfg['train_data']})['train']
val = datasets.load_dataset('json', data_files={'validation': cfg['validation_data']})['validation']
print({'train_rows': len(train), 'val_rows': len(val), 'sample_id': train[0]['id'], 'sample_task': train[0]['task_family']})
PY
```

## Smoke-Test Status

Fully executed:

- Stage C build
- Stage C eval dry-run
- Stage C OpenAI request-manifest dry-run
- Stage C config and CLI smoke tests
- Stage C dataset loading through the existing Stage B trainer config translation
- doc-level contamination check

Not fully executed in this environment:

- full LoRA training run for any Stage C arm
- full native eval against a trained Stage C checkpoint
- live OpenAI Batch or sync execution with `--execute`
- speech/transcript recovery for the media-only asset pool

## Remaining Blockers

- The media collection is still manifest-only until subtitle extraction or ASR is added.
- The OpenAI offline path is implemented and dry-run tested, but no live job was executed here.
- Full Stage C training and ablation comparison are still compute-bound follow-up runs.

The OpenAI loader now bridges repo `.env` keys to `OPENAI_API_KEY` using `OPENAI_KEY` first and `OPEN_AI` as a fallback, without hard-coding secrets.

## Exact Next Commands

```bash
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_english.json
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_only.json
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_stage_b_translated.json
uv run python scripts/train_stage_b_agent.py --config configs/stage_c_agent_oss120b_native_plus_bilingual.json
uv run python scripts/eval_stage_c_native.py --config configs/stage_c_eval_native_oss120b.json --model-path <stage_c_checkpoint_or_adapter>
uv run python scripts/stage_c_openai_jobs.py --job-type ocr_cleanup --input-path data/external/stage_c_seed/extracted_text/page_text.jsonl --output-dir data/external/stage_c_seed/openai_jobs/ocr_cleanup --max-rows 200 --execute
```
