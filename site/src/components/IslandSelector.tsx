import { createSignal, onMount, Show } from "solid-js";
import { ISLANDS } from "~/lib/types";

function generateUUID(): string {
  return crypto.randomUUID();
}

export default function IslandSelector() {
  const [show, setShow] = createSignal(false);

  onMount(() => {
    if (!localStorage.getItem("talafutipolo_island_chosen")) {
      setShow(true);
    }
  });

  const selectIsland = (island: string) => {
    localStorage.setItem("talafutipolo_island", island);
    if (!localStorage.getItem("talafutipolo_session")) {
      localStorage.setItem("talafutipolo_session", generateUUID());
    }
    localStorage.setItem("talafutipolo_island_chosen", "true");
    setShow(false);
  };

  const skip = () => {
    if (!localStorage.getItem("talafutipolo_session")) {
      localStorage.setItem("talafutipolo_session", generateUUID());
    }
    localStorage.setItem("talafutipolo_island_chosen", "true");
    setShow(false);
  };

  return (
    <Show when={show()}>
      <div class="fixed inset-0 z-50 bg-[#1a1a2e] flex items-center justify-center p-6">
        <div class="w-full max-w-sm text-center">
          <h2 class="text-2xl font-bold text-white mb-2">Talofa!</h2>
          <p class="text-gray-300 mb-6 text-sm">
            Ko koe mai fea? Where are you from?
          </p>

          <div class="grid grid-cols-2 gap-3 mb-4">
            {ISLANDS.slice(0, 9).map((island) => (
              <button
                onClick={() => selectIsland(island)}
                class="py-3 px-4 bg-white/10 text-white rounded-lg text-sm font-medium hover:bg-white/20 transition-colors cursor-pointer border-none"
              >
                {island}
              </button>
            ))}
          </div>

          {/* I fafo (Diaspora) full width */}
          <button
            onClick={() => selectIsland("I fafo")}
            class="w-full py-3 px-4 bg-white/10 text-white rounded-lg text-sm font-medium hover:bg-white/20 transition-colors cursor-pointer border-none mb-4"
          >
            I fafo (Diaspora)
          </button>

          <button
            onClick={skip}
            class="text-gray-400 text-sm hover:text-gray-200 cursor-pointer bg-transparent border-none"
          >
            Fano &rarr;
          </button>
        </div>
      </div>
    </Show>
  );
}
