import { MetaProvider, Link } from "@solidjs/meta";
import { Router } from "@solidjs/router";
import { FileRoutes } from "@solidjs/start/router";
import { Suspense, onMount } from "solid-js";
import { isServer } from "solid-js/web";
import Header from "~/components/Header";
import IslandSelector from "~/components/IslandSelector";
import FateleTeaser from "~/components/FateleTeaser";
import { registerServiceWorker } from "~/lib/register-sw";
import "./app.css";

export default function App() {
  onMount(() => {
    if (!isServer) registerServiceWorker();
  });

  return (
    <Router
      root={(props) => (
        <MetaProvider>
          <Link rel="alternate" type="application/rss+xml" title="TALAFUTIPOLO RSS" href="/feed.xml" />
          <div class="min-h-screen pb-12">
            <Header />
            <Suspense
              fallback={
                <div class="max-w-3xl mx-auto p-4 text-center text-gray-400">
                  Loading...
                </div>
              }
            >
              {props.children}
            </Suspense>
            <FateleTeaser />
            <IslandSelector />
          </div>
        </MetaProvider>
      )}
    >
      <FileRoutes />
    </Router>
  );
}
