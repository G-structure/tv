import { createSignal } from "solid-js";

export type LanguageMode = "tv" | "en" | "tv+en";

const MODE_LABELS: Record<LanguageMode, string> = {
  tv: "TV",
  en: "EN",
  "tv+en": "TV+EN",
};

const MODE_CYCLE: LanguageMode[] = ["tv", "en", "tv+en"];

interface LanguageToggleProps {
  mode: LanguageMode;
  onChange: (mode: LanguageMode) => void;
}

export default function LanguageToggle(props: LanguageToggleProps) {
  const next = () => {
    const idx = MODE_CYCLE.indexOf(props.mode);
    return MODE_CYCLE[(idx + 1) % MODE_CYCLE.length];
  };

  return (
    <button
      onClick={() => props.onChange(next())}
      class="px-3 py-1.5 rounded-full text-xs font-semibold border border-[var(--ocean)] text-[var(--ocean-deep)] bg-white hover:bg-[var(--sky)] transition-colors cursor-pointer min-h-[36px]"
      aria-label={`Language: ${MODE_LABELS[props.mode]}. Tap to switch.`}
    >
      {MODE_LABELS[props.mode]}
    </button>
  );
}
