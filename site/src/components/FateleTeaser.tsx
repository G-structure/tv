import { createAsync, cache, A } from "@solidjs/router";
import { Show } from "solid-js";
import { getFateleStats } from "~/lib/db";

const loadTeaser = cache(async () => {
  "use server";
  const stats = getFateleStats();
  return stats.total_this_month;
}, "fatele-teaser");

export default function FateleTeaser() {
  const count = createAsync(() => loadTeaser());

  return (
    <div class="fixed bottom-0 left-0 right-0 z-40 bg-[#1a1a2e] text-white border-t border-gray-700">
      <A
        href="/fatele"
        class="block max-w-3xl mx-auto px-4 py-2.5 flex items-center justify-between no-underline text-white"
      >
        <span class="text-xs">
          Te Fatele
          <Show when={typeof count() === "number"}>
            {" "}&middot; {count()} i te masina nei
          </Show>
        </span>
        <span class="text-xs">&rarr;</span>
      </A>
    </div>
  );
}
