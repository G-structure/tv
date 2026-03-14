import { createResource, For, Show, createMemo, createSignal } from "solid-js";
import { isServer } from "solid-js/web";
import { Title } from "@solidjs/meta";

interface EvalRun {
  run_id: string;
  budget: string;
  created_at: string;
  models: Record<string, Record<string, TaskResult>>;
}

interface TaskResult {
  count: number;
  chrf_pp: number;
  bleu: number;
  exact_match: number;
}

interface EvalData {
  runs: EvalRun[];
}

async function fetchEvalData(): Promise<EvalData | undefined> {
  if (isServer) return undefined;
  const resp = await fetch("/api/eval-results");
  if (!resp.ok) throw new Error("Failed to fetch eval results");
  return resp.json();
}

const TASK_LABELS: Record<string, string> = {
  translation_en_to_tvl: "EN → TVL",
  translation_tvl_to_en: "TVL → EN",
  chat_tvl: "Chat (TVL)",
  qa_tvl: "QA (TVL)",
  summarization_tvl: "Summarization (TVL)",
};

const MODEL_LABELS: Record<string, string> = {
  tvl: "TVL Fine-tune",
  "gpt-4o": "GPT-4o",
  "claude-sonnet": "Claude Sonnet",
  "gemini-2.5-flash": "Gemini 2.5 Flash",
  "llama-4-scout": "Llama 4 Scout",
  "google-translate": "Google Translate",
};

export default function Eval() {
  const [data] = createResource(fetchEvalData);
  const [selectedRun, setSelectedRun] = createSignal<string | null>(null);

  const latestRun = createMemo(() => {
    if (!data()?.runs?.length) return null;
    const id = selectedRun();
    if (id) return data()!.runs.find((r) => r.run_id === id) || data()!.runs[0];
    return data()!.runs[0];
  });

  const tasks = createMemo(() => {
    const run = latestRun();
    if (!run) return [];
    const allTasks = new Set<string>();
    for (const results of Object.values(run.models)) {
      for (const task of Object.keys(results)) allTasks.add(task);
    }
    return Array.from(allTasks).sort();
  });

  const models = createMemo(() => {
    const run = latestRun();
    if (!run) return [];
    return Object.keys(run.models).sort((a, b) => {
      if (a === "tvl") return -1;
      if (b === "tvl") return 1;
      return a.localeCompare(b);
    });
  });

  const overallScores = createMemo(() => {
    const run = latestRun();
    if (!run) return [];
    return models()
      .map((model) => {
        const results = run.models[model];
        const taskScores = Object.values(results)
          .filter((r: any) => r.count > 0)
          .map((r: any) => r.chrf_pp);
        const avg = taskScores.length ? taskScores.reduce((a, b) => a + b, 0) / taskScores.length : 0;
        return { model, avg, count: taskScores.length };
      })
      .sort((a, b) => b.avg - a.avg);
  });

  return (
    <>
      <Title>TVL Eval</Title>
      <div class="min-h-screen bg-[var(--color-bg)]">
        {/* Nav */}
        <nav class="flex items-center justify-between px-6 h-12 border-b border-[var(--color-border)]">
          <div class="flex items-center gap-3">
            <span class="text-[var(--color-accent)] text-[10px]">&#10038;</span>
            <div class="flex items-center gap-2 text-[13px] text-[var(--color-text-muted)]">
              <a href="/" class="hover:text-[var(--color-text-secondary)] transition-colors">TVL</a>
              <span>/</span>
              <span class="text-[var(--color-text)]">Eval</span>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <a href="/training" class="text-[12px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">Training</a>
            <a href="/" class="text-[12px] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">Chat</a>
          </div>
        </nav>

        <div class="max-w-5xl mx-auto px-6 py-8">
          <Show when={data.loading}>
            <div class="text-[var(--color-text-muted)] text-[13px]">Loading evaluation results...</div>
          </Show>

          <Show when={data.error}>
            <div class="text-[#f87171]/70 text-[13px]">Failed to load eval results</div>
          </Show>

          <Show when={latestRun()}>
            {/* Header */}
            <div class="mb-8">
              <h1 class="text-[20px] font-semibold text-[var(--color-text)] mb-1">
                Model Evaluation
              </h1>
              <p class="text-[13px] text-[var(--color-text-muted)]">
                Comparing TVL fine-tune against leading models on Tuvaluan language tasks
              </p>
              <div class="flex items-center gap-4 mt-3">
                <Show when={(data()?.runs?.length ?? 0) > 1}>
                  <select
                    class="text-[12px] bg-[var(--color-surface)] border border-[var(--color-border)] rounded px-2 py-1 text-[var(--color-text-secondary)]"
                    onChange={(e) => setSelectedRun(e.target.value)}
                  >
                    <For each={data()?.runs}>
                      {(run) => (
                        <option value={run.run_id}>
                          {run.run_id} ({run.budget})
                        </option>
                      )}
                    </For>
                  </select>
                </Show>
                <span class="text-[11px] text-[var(--color-text-muted)] tabular">
                  {latestRun()!.budget} · {latestRun()!.created_at?.slice(0, 16)}
                </span>
              </div>
            </div>

            {/* Overall ranking */}
            <div class="mb-8">
              <h2 class="text-[14px] font-medium text-[var(--color-text)] mb-3">Overall Ranking</h2>
              <div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden">
                <div class="grid grid-cols-[2fr_1fr_1fr] gap-px bg-[var(--color-border)]">
                  <div class="bg-[var(--color-surface-2)] px-4 py-2 text-[11px] text-[var(--color-text-muted)] uppercase tracking-wider">Model</div>
                  <div class="bg-[var(--color-surface-2)] px-4 py-2 text-[11px] text-[var(--color-text-muted)] uppercase tracking-wider text-right">Mean chrF++</div>
                  <div class="bg-[var(--color-surface-2)] px-4 py-2 text-[11px] text-[var(--color-text-muted)] uppercase tracking-wider text-right">Tasks</div>
                </div>
                <For each={overallScores()}>
                  {(item, i) => (
                    <div class={`grid grid-cols-[2fr_1fr_1fr] gap-px ${i() === 0 ? "bg-[var(--color-accent)]/5" : ""}`}>
                      <div class="bg-[var(--color-surface)] px-4 py-2.5 text-[13px]">
                        <span class={item.model === "tvl" ? "text-[var(--color-accent)] font-medium" : "text-[var(--color-text)]"}>
                          {MODEL_LABELS[item.model] || item.model}
                        </span>
                        <Show when={i() === 0}>
                          <span class="ml-2 text-[10px] text-[var(--color-accent)]">★</span>
                        </Show>
                      </div>
                      <div class="bg-[var(--color-surface)] px-4 py-2.5 text-[13px] text-[var(--color-text-secondary)] text-right tabular">{item.avg.toFixed(1)}</div>
                      <div class="bg-[var(--color-surface)] px-4 py-2.5 text-[13px] text-[var(--color-text-muted)] text-right tabular">{item.count}</div>
                    </div>
                  )}
                </For>
              </div>
            </div>

            {/* Per-task breakdown */}
            <h2 class="text-[14px] font-medium text-[var(--color-text)] mb-3">Per-Task Results</h2>
            <For each={tasks()}>
              {(task) => (
                <div class="mb-6">
                  <h3 class="text-[13px] text-[var(--color-text-secondary)] mb-2">
                    {TASK_LABELS[task] || task}
                  </h3>
                  <div class="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg overflow-hidden">
                    <div class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-px bg-[var(--color-border)]">
                      <div class="bg-[var(--color-surface-2)] px-3 py-1.5 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">Model</div>
                      <div class="bg-[var(--color-surface-2)] px-3 py-1.5 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider text-right">chrF++</div>
                      <div class="bg-[var(--color-surface-2)] px-3 py-1.5 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider text-right">BLEU</div>
                      <div class="bg-[var(--color-surface-2)] px-3 py-1.5 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider text-right">Exact</div>
                      <div class="bg-[var(--color-surface-2)] px-3 py-1.5 text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider text-right">n</div>
                    </div>
                    <For
                      each={models()
                        .filter((m) => latestRun()!.models[m]?.[task]?.count > 0)
                        .sort((a, b) => (latestRun()!.models[b]?.[task]?.chrf_pp ?? 0) - (latestRun()!.models[a]?.[task]?.chrf_pp ?? 0))}
                    >
                      {(model) => {
                        const r = () => latestRun()!.models[model][task];
                        return (
                          <div class="grid grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-px">
                            <div class="bg-[var(--color-surface)] px-3 py-2 text-[12px]">
                              <span class={model === "tvl" ? "text-[var(--color-accent)]" : "text-[var(--color-text)]"}>
                                {MODEL_LABELS[model] || model}
                              </span>
                            </div>
                            <div class="bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)] text-right tabular">
                              {r().chrf_pp?.toFixed(1) ?? "—"}
                            </div>
                            <div class="bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-secondary)] text-right tabular">
                              {r().bleu?.toFixed(1) ?? "—"}
                            </div>
                            <div class="bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-muted)] text-right tabular">
                              {r().exact_match != null ? (r().exact_match * 100).toFixed(0) + "%" : "—"}
                            </div>
                            <div class="bg-[var(--color-surface)] px-3 py-2 text-[12px] text-[var(--color-text-muted)] text-right tabular">
                              {r().count}
                            </div>
                          </div>
                        );
                      }}
                    </For>
                  </div>
                </div>
              )}
            </For>

            {/* Footer */}
            <div class="mt-12 pt-6 border-t border-[var(--color-border)]">
              <p class="text-[11px] text-[var(--color-text-muted)]">
                Metrics: chrF++ (word_order=2), BLEU (effective_order), exact match (whitespace-normalized).
                Evaluated on Stage B test set with balanced task sampling.
              </p>
            </div>
          </Show>
        </div>
      </div>
    </>
  );
}
