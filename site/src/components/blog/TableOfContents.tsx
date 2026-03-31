import { For } from "solid-js";
import type { BlogHeading } from "~/lib/blog";

export default function TableOfContents(props: {
  headings: BlogHeading[];
  title?: string;
}) {
  return (
    <nav class="blog-toc" aria-label="Table of contents">
      <p class="blog-toc__label">{props.title || "On this page"}</p>
      <ol class="blog-toc__list">
        <For each={props.headings}>
          {(heading) => (
            <li class={`blog-toc__item blog-toc__item--depth-${heading.depth}`}>
              <a href={`#${heading.id}`} class="blog-toc__link">
                {heading.text}
              </a>
            </li>
          )}
        </For>
      </ol>
    </nav>
  );
}
