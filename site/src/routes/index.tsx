import { createAsync, cache } from "@solidjs/router";
import { For, Show } from "solid-js";
import { getArticles, getCategories } from "~/lib/db";
import type { Article, Category } from "~/lib/types";
import ArticleCard from "~/components/ArticleCard";
import CategoryPills from "~/components/CategoryPills";
import OGMeta from "~/components/OGMeta";

const loadHome = cache(async () => {
  "use server";
  const articles = getArticles(21);
  const categories = getCategories();
  return { articles, categories };
}, "home");

export const route = {
  load: () => loadHome(),
};

export default function Home() {
  const data = createAsync(() => loadHome());

  return (
    <main class="max-w-3xl mx-auto pb-8">
      <OGMeta
        title="Talafutipolo Tuvalu — Tala Futipolo i te Gagana Tuvalu"
        description="Tala futipolo mai te lalolagi i te gagana Tuvalu. Football news from around the world in the Tuvaluan language."
      />

      <Show when={data()}>
        {(d) => (
          <>
            {/* Category filter pills */}
            <Show when={d().categories.length > 0}>
              <CategoryPills categories={d().categories} />
            </Show>

            {/* Empty state */}
            <Show when={d().articles.length === 0}>
              <div class="p-8 text-center text-gray-400">
                <p class="text-lg font-medium">Seki isi tala</p>
                <p class="mt-2 text-sm">No articles yet</p>
              </div>
            </Show>

            {/* Hero card for latest article */}
            <Show when={d().articles.length > 0}>
              <div class="px-4 pt-2">
                <ArticleCard article={d().articles[0]} hero />
              </div>
            </Show>

            {/* Remaining articles as thumbnail rows */}
            <Show when={d().articles.length > 1}>
              <div class="mt-4 divide-y divide-gray-100">
                <For each={d().articles.slice(1)}>
                  {(article) => <ArticleCard article={article} />}
                </For>
              </div>
            </Show>

            {/* Load more */}
            <Show when={d().articles.length >= 21}>
              <div class="px-4 mt-4">
                <a
                  href="/?page=2"
                  class="block w-full py-3 text-center text-sm font-medium text-gray-600 bg-gray-100 rounded-lg no-underline hover:bg-gray-200 transition-colors"
                >
                  Faitau atu &darr;
                </a>
              </div>
            </Show>
          </>
        )}
      </Show>
    </main>
  );
}
