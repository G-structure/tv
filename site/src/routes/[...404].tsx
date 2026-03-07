import { A } from "@solidjs/router";
import OGMeta from "~/components/OGMeta";

export default function NotFound() {
  return (
    <main class="max-w-3xl mx-auto p-4 text-center">
      <OGMeta title="Seki kitea | TALAFUTIPOLO" description="Page not found" />
      <div class="mt-16">
        <h1 class="text-4xl font-bold text-gray-900">Seki kitea</h1>
        <p class="mt-4 text-lg text-gray-500">
          Te peesi tenei e seki kitea. The page you're looking for doesn't exist.
        </p>
        <A
          href="/"
          class="inline-block mt-8 px-6 py-3 bg-[#1a1a2e] text-white text-sm font-medium rounded-lg no-underline hover:bg-[#2a2a4e] transition-colors"
        >
          &larr; Foki ki te kamata
        </A>
      </div>
    </main>
  );
}
