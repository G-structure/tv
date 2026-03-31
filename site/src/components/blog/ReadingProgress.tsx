import { createSignal, onCleanup, onMount } from "solid-js";

export default function ReadingProgress() {
  const [progress, setProgress] = createSignal(0);

  onMount(() => {
    const update = () => {
      const scrollTop = window.scrollY;
      const height = document.documentElement.scrollHeight - window.innerHeight;
      const next = height > 0 ? Math.min(100, Math.max(0, (scrollTop / height) * 100)) : 0;
      setProgress(next);
    };

    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);

    onCleanup(() => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    });
  });

  return (
    <div class="blog-progress" aria-hidden="true">
      <div class="blog-progress__bar" style={{ width: `${progress()}%` }} />
    </div>
  );
}
