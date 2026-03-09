import { A, useLocation } from "@solidjs/router";
import { For } from "solid-js";
import type { Category } from "~/lib/types";

interface CategoryPillsProps {
  categories: Category[];
}

export default function CategoryPills(props: CategoryPillsProps) {
  const location = useLocation();

  const isActive = (slug: string) => {
    return location.pathname === `/category/${slug}`;
  };

  const isAll = () => {
    return location.pathname === "/";
  };

  return (
    <div class="category-scroll flex gap-2 overflow-x-auto py-3 px-4">
      <A
        href="/"
        class={`shrink-0 px-4 py-2 rounded-full text-sm font-medium no-underline transition-colors ${
          isAll()
            ? "bg-[var(--gold)] text-[var(--ocean-deep)] font-bold"
            : "bg-white text-[var(--ocean-deep)] hover:bg-[var(--sky-dark)]"
        }`}
      >
        All
      </A>
      <For each={props.categories}>
        {(cat) => (
          <A
            href={`/category/${cat.slug}`}
            class={`shrink-0 px-4 py-2 rounded-full text-sm font-medium no-underline transition-colors capitalize ${
              isActive(cat.slug)
                ? "bg-[var(--gold)] text-[var(--ocean-deep)] font-bold"
                : "bg-white text-[var(--ocean-deep)] hover:bg-[var(--sky-dark)]"
            }`}
          >
            {cat.slug.replace(/-/g, " ")}
          </A>
        )}
      </For>
    </div>
  );
}
