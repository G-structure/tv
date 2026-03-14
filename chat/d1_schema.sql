-- Training metrics (one row per logged metric point)
CREATE TABLE IF NOT EXISTS training_metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL DEFAULT 'stage_b_llama8b',
  step INTEGER NOT NULL,
  metric_type TEXT NOT NULL,  -- 'train_nll', 'val_nll', 'gen_eval'
  value_json TEXT NOT NULL,   -- JSON blob of all metrics at this step
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_metrics_run_step ON training_metrics(run_id, step);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON training_metrics(run_id, metric_type);

-- Training config / mix stats (key-value store for static config)
CREATE TABLE IF NOT EXISTS training_config (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Benchmark eval runs (one row per model per run)
CREATE TABLE IF NOT EXISTS eval_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,        -- e.g. '2026-03-14_tiny' or '2026-03-14_full'
  model_key TEXT NOT NULL,     -- e.g. 'tvl', 'gpt-4o', 'google-translate'
  budget TEXT NOT NULL,        -- 'tiny' or 'full'
  results_json TEXT NOT NULL,  -- full results dict for this model
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_run ON eval_runs(run_id);

-- Individual eval predictions (for drill-down and example display)
CREATE TABLE IF NOT EXISTS eval_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  model_key TEXT NOT NULL,
  task TEXT NOT NULL,           -- e.g. 'translation_en_to_tvl'
  example_id TEXT NOT NULL,
  prediction TEXT NOT NULL,
  reference TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_eval_preds_run_model ON eval_predictions(run_id, model_key);
CREATE INDEX IF NOT EXISTS idx_eval_preds_task ON eval_predictions(run_id, task);
