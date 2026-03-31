import { A } from "@solidjs/router";
import { For, Show } from "solid-js";
import type { BlogPost } from "~/lib/blog";
import { formatShortDate } from "~/lib/site";

export default function PostCard(props: {
  post: BlogPost;
  variant?: "feature" | "list" | "compact";
}) {
  const variant = () => props.variant || "list";

  return (
    <A
      href={`/blog/${props.post.slug}`}
      class={`blog-card blog-card--${variant()}`}
    >
      <Show when={props.post.image}>
        <div class="blog-card__media">
          <img
            src={props.post.image}
            alt={props.post.imageAlt || props.post.title}
            class="blog-card__image"
            loading={variant() === "feature" ? "eager" : "lazy"}
            decoding="async"
          />
        </div>
      </Show>

      <div class="blog-card__content">
        <div class="blog-card__eyebrow-row">
          <span class="blog-card__kind">{props.post.kind}</span>
          <span class="blog-card__dot" aria-hidden="true" />
          <time class="blog-card__meta">{formatShortDate(props.post.publishedAt)}</time>
          <span class="blog-card__dot" aria-hidden="true" />
          <span class="blog-card__meta">{props.post.readingTimeMinutes} min read</span>
        </div>

        <h2 class="blog-card__title">{props.post.title}</h2>
        <p class="blog-card__description">{props.post.description}</p>

        <div class="blog-card__footer">
          <div class="blog-card__author">
            <span class="blog-card__author-mark">
              {props.post.authors[0]?.initials || "LL"}
            </span>
            <span>{props.post.authors.map((author) => author.name).join(", ")}</span>
          </div>

          <Show when={props.post.tags.length > 0}>
            <div class="blog-card__tags">
              <For each={props.post.tags.slice(0, variant() === "compact" ? 2 : 3)}>
                {(tag) => <span class="blog-card__tag">{tag}</span>}
              </For>
            </div>
          </Show>
        </div>
      </div>
    </A>
  );
}
