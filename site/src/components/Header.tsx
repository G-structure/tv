import { A } from "@solidjs/router";
import LanguageToggle from "./LanguageToggle";
import type { LanguageMode } from "./LanguageToggle";

interface HeaderProps {
  langMode?: LanguageMode;
  onLangChange?: (mode: LanguageMode) => void;
}

export default function Header(props: HeaderProps) {
  return (
    <header class="bg-[#1a1a2e] text-white">
      <div class="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
        <A href="/" class="text-xl font-bold tracking-wide no-underline text-white">
          TALAFUTIPOLO
        </A>
        <div class="flex items-center gap-3">
          <span class="text-xs text-gray-400 hidden sm:inline">
            Tuvaluan Football News
          </span>
          {props.langMode && props.onLangChange && (
            <LanguageToggle mode={props.langMode} onChange={props.onLangChange} />
          )}
        </div>
      </div>
    </header>
  );
}
