import { createAsync, cache, useParams } from "@solidjs/router";
import { For, Show } from "solid-js";
import { getArticles, getCategories } from "~/lib/db";
import type { Article, Category } from "~/lib/types";
import ArticleCard from "~/components/ArticleCard";
import CategoryPills from "~/components/CategoryPills";
import OGMeta from "~/components/OGMeta";

const loadCategory = cache(async (slug: string) => {
  "use server";
  const articles = getArticles(21, 0, slug);
  const categories = getCategories();
  return { articles, categories, slug };
}, "category");

export const route = {
  load: ({ params }: { params: { slug: string } }) =>
    loadCategory(params.slug),
};

export default function CategoryPage() {
  const params = useParams();
  const data = createAsync(() => loadCategory(params.slug));

  const displayName = () =>
    params.slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <main class="max-w-3xl mx-auto pb-8">
      <OGMeta
        title={`${displayName()} | TALAFUTIPOLO`}
        description={`${displayName()} football news in Tuvaluan and English`}
      />

      <Show when={data()}>
        {(d) => (
          <>
            {/* Category filter pills */}
            <CategoryPills categories={d().categories} />

            {/* Category heading */}
            <div class="px-4 pt-2 pb-2">
              <h1 class="text-xl font-bold text-gray-900 capitalize">
                {displayName()}
              </h1>
            </div>

            {/* Empty state */}
            <Show when={d().articles.length === 0}>
              <div class="p-8 text-center text-gray-400">
                <p class="text-lg font-medium">Seki isi tala</p>
                <p class="mt-1 text-sm">No articles in this category</p>
              </div>
            </Show>

            {/* Hero card for first article */}
            <Show when={d().articles.length > 0}>
              <div class="px-4">
                <ArticleCard article={d().articles[0]} hero />
              </div>
            </Show>

            {/* Remaining articles */}
            <Show when={d().articles.length > 1}>
              <div class="mt-4 divide-y divide-gray-100">
                <For each={d().articles.slice(1)}>
                  {(article) => <ArticleCard article={article} />}
                </For>
              </div>
            </Show>
          </>
        )}
      </Show>
    </main>
  );
}
