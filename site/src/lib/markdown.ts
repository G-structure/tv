import { Marked } from "marked";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";

hljs.registerLanguage("python", python);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const marked = new Marked({
  renderer: {
    // Block raw HTML from untrusted input — escape instead of rendering
    html({ text }: { text: string }) {
      return escapeHtml(text);
    },
    code({ text, lang }: { text: string; lang?: string }) {
      const language = lang && hljs.getLanguage(lang) ? lang : "plaintext";
      const highlighted = language !== "plaintext"
        ? hljs.highlight(text, { language }).value
        : escapeHtml(text);
      return `<div class="code-block group relative my-3">
        <div class="code-header flex items-center justify-between px-4 py-2 text-xs text-gray-400 bg-[#1e1e2e] rounded-t-lg border-b border-[#2a2a3e]">
          <span>${escapeHtml(language)}</span>
          <button type="button" class="chat-copy-btn hover:text-white transition-colors px-2 py-0.5 rounded hover:bg-white/10" aria-label="Copy code">Copy</button>
        </div>
        <pre class="bg-[#1e1e2e] rounded-b-lg p-4 overflow-x-auto"><code class="hljs language-${escapeHtml(language)} text-sm">${highlighted}</code></pre>
      </div>`;
    },
    codespan({ text }: { text: string }) {
      return `<code class="bg-[#1e1e2e] px-1.5 py-0.5 rounded text-[#e2b86b] text-sm">${escapeHtml(text)}</code>`;
    },
  },
});

export function renderMarkdown(text: string): string {
  return marked.parse(text) as string;
}

/**
 * Wire up delegated click handlers for copy buttons rendered by renderMarkdown.
 * Call once after mounting the chat message container.
 */
export function initCopyButtons(root: HTMLElement) {
  root.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLButtonElement>(".chat-copy-btn");
    if (!btn) return;
    const pre = btn.closest(".code-block")?.querySelector("pre code");
    if (!pre) return;
    navigator.clipboard.writeText(pre.textContent || "").then(() => {
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = "Copy"; }, 2000);
    });
  });
}
