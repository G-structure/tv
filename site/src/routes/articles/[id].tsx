import { createAsync, cache, useParams, A } from "@solidjs/router";
import { createSignal, For, Show } from "solid-js";
import { getArticle } from "~/lib/db";
import type { Article } from "~/lib/types";
import { formatDate } from "~/lib/time";
import OGMeta from "~/components/OGMeta";
import type { LanguageMode } from "~/components/LanguageToggle";
import LanguageToggle from "~/components/LanguageToggle";

const loadArticle = cache(async (id: string) => {
  "use server";
  return getArticle(id) || null;
}, "article");

export const route = {
  load: ({ params }: { params: { id: string } }) => loadArticle(params.id),
};

function splitParagraphs(body: string): string[] {
  if (body.includes("<p")) {
    const matches = body.match(/<p[^>]*>([\s\S]*?)<\/p>/gi);
    if (matches) {
      return matches
        .map((m) => m.replace(/<[^>]+>/g, "").trim())
        .filter((p) => p.length > 0);
    }
  }
  return body
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}

function SourceName(props: { sourceId: string }) {
  const map: Record<string, string> = {
    goal: "Goal.com",
    fifa: "FIFA.com",
    sky: "Sky Sports",
  };
  return <>{map[props.sourceId] || props.sourceId}</>;
}

function BilingualParagraph(props: {
  tvl: string;
  en: string;
  mode: LanguageMode;
  index: number;
}) {
  const [showEn, setShowEn] = createSignal(false);

  return (
    <div class="mb-5">
      <Show when={props.mode === "tv" || props.mode === "tv+en"}>
        <p class="text-base leading-relaxed text-gray-900">{props.tvl}</p>
      </Show>

      <Show when={props.mode === "tv"}>
        <button
          onClick={() => setShowEn(!showEn())}
          class="mt-1.5 text-xs text-blue-600 hover:text-blue-800 cursor-pointer bg-transparent border-none p-0 min-h-0"
        >
          {showEn() ? "Funa te English" : "Fakakite English"}
        </button>
        <Show when={showEn()}>
          <p class="mt-1.5 pl-3 text-sm leading-relaxed text-gray-400 italic border-l-2 border-gray-200">
            {props.en}
          </p>
        </Show>
      </Show>

      <Show when={props.mode === "tv+en"}>
        <p class="mt-2 pl-3 text-sm leading-relaxed text-gray-400 italic border-l-2 border-gray-200">
          {props.en}
        </p>
      </Show>

      <Show when={props.mode === "en"}>
        <p class="text-base leading-relaxed text-gray-900">{props.en}</p>
      </Show>
    </div>
  );
}

export default function ArticlePage() {
  const params = useParams();
  const article = createAsync(() => loadArticle(params.id));
  const [langMode, setLangMode] = createSignal<LanguageMode>("tv");

  return (
    <Show
      when={article()}
      fallback={
        <main class="max-w-3xl mx-auto p-4 text-center">
          <h1 class="text-xl font-bold text-gray-900 mt-8">
            Article not found
          </h1>
          <p class="mt-2 text-gray-500">
            This article may have been removed or the ID is invalid.
          </p>
        </main>
      }
    >
      {(a) => {
        const title = () =>
          langMode() === "en"
            ? a().title_en
            : a().title_tvl || a().title_en;
        const description = () =>
          a().og_description_tvl || a().og_description_en || "";
        const enParagraphs = () => splitParagraphs(a().body_en);
        const tvlParagraphs = () =>
          a().body_tvl ? splitParagraphs(a().body_tvl!) : [];
        const hasTvl = () => tvlParagraphs().length > 0;
        const effectiveMode = () => (hasTvl() ? langMode() : "en");

        return (
          <main class="max-w-3xl mx-auto pb-12">
            <OGMeta
              title={a().title_tvl || a().title_en}
              description={description() || undefined}
              image={a().image_url}
              imageWidth={a().image_width}
              imageHeight={a().image_height}
              publishedAt={a().published_at}
              category={a().category || undefined}
              type="article"
            />

            {/* Top bar with back + language toggle */}
            <div class="flex items-center justify-between px-4 py-2">
              <A
                href="/"
                class="text-sm text-gray-500 hover:text-gray-700 no-underline min-h-[36px]"
              >
                &larr; Foki
              </A>
              <Show when={hasTvl()}>
                <LanguageToggle
                  mode={langMode()}
                  onChange={setLangMode}
                />
              </Show>
            </div>

            {/* Hero image */}
            <Show when={a().image_url}>
              <img
                src={a().image_url!}
                alt={a().image_alt || title()}
                class="w-full h-56 sm:h-72 object-cover"
              />
            </Show>

            <article class="px-4 pt-4">
              {/* Title — TVL first */}
              <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight">
                {title()}
              </h1>

              {/* EN subtitle when showing TVL title */}
              <Show
                when={
                  hasTvl() &&
                  effectiveMode() !== "en" &&
                  a().title_en !== a().title_tvl
                }
              >
                <p class="mt-1 text-base text-gray-400 italic">
                  {a().title_en}
                </p>
              </Show>

              {/* TVL subtitle when showing EN title */}
              <Show
                when={
                  hasTvl() &&
                  effectiveMode() === "en" &&
                  a().title_tvl
                }
              >
                <p class="mt-1 text-base text-gray-400 italic">
                  {a().title_tvl}
                </p>
              </Show>

              {/* Meta line */}
              <div class="mt-3 flex flex-wrap items-center gap-2 text-sm text-gray-500">
                <span>{formatDate(a().published_at)}</span>
                <span>&middot;</span>
                <SourceName sourceId={a().source_id} />
                <Show when={a().author}>
                  <>
                    <span>&middot;</span>
                    <span>{a().author}</span>
                  </>
                </Show>
                <Show when={a().category}>
                  <>
                    <span>&middot;</span>
                    <span class="capitalize">
                      {a().category!.replace(/-/g, " ")}
                    </span>
                  </>
                </Show>
              </div>

              {/* Body */}
              <div class="mt-6">
                <Show
                  when={hasTvl()}
                  fallback={
                    /* English only — no translation available */
                    <For each={enParagraphs()}>
                      {(p) => (
                        <p class="mb-4 text-base leading-relaxed text-gray-900">
                          {p}
                        </p>
                      )}
                    </For>
                  }
                >
                  {/* Bilingual paragraphs */}
                  <For each={tvlParagraphs()}>
                    {(tvlP, i) => (
                      <BilingualParagraph
                        tvl={tvlP}
                        en={enParagraphs()[i()] || ""}
                        mode={effectiveMode()}
                        index={i()}
                      />
                    )}
                  </For>
                </Show>
              </div>

              {/* Source attribution + share */}
              <div class="mt-8 pt-4 border-t border-gray-200 flex items-center justify-between">
                <a
                  href={a().url}
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-blue-600 hover:text-blue-800 no-underline"
                >
                  Read original at <SourceName sourceId={a().source_id} />
                </a>
                <button
                  onClick={() => {
                    if (navigator.share) {
                      navigator.share({
                        title: a().title_tvl || a().title_en,
                        text:
                          a().og_description_tvl ||
                          a().og_description_en ||
                          undefined,
                        url: window.location.href,
                      });
                    } else {
                      navigator.clipboard.writeText(window.location.href);
                    }
                  }}
                  class="px-4 py-2 bg-[#1a1a2e] text-white text-sm rounded-lg cursor-pointer border-none"
                  aria-label="Fakasoa (Share)"
                >
                  Fakasoa
                </button>
              </div>
            </article>
          </main>
        );
      }}
    </Show>
  );
}
