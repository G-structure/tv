import { MetaProvider } from "@solidjs/meta";
import { Router } from "@solidjs/router";
import { FileRoutes } from "@solidjs/start/router";
import { Suspense } from "solid-js";
import Header from "~/components/Header";
import IslandSelector from "~/components/IslandSelector";
import FateleTeaser from "~/components/FateleTeaser";
import "./app.css";

export default function App() {
  return (
    <Router
      root={(props) => (
        <MetaProvider>
          <div class="min-h-screen bg-gray-50 pb-12">
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
