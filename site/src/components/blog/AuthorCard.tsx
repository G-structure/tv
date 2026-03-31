import { A } from "@solidjs/router";
import { For, Show } from "solid-js";
import type { BlogAuthor } from "~/lib/blog-authors";

export default function AuthorCard(props: { author: BlogAuthor }) {
  return (
    <section class="blog-author-card">
      <div class="blog-author-card__mark">{props.author.initials}</div>
      <div class="blog-author-card__body">
        <div class="blog-author-card__eyebrow">Published by</div>
        <h2 class="blog-author-card__name">
          <A href={`/blog/author/${props.author.slug}`}>{props.author.name}</A>
        </h2>
        <p class="blog-author-card__role">{props.author.role}</p>
        <p class="blog-author-card__bio">{props.author.bio}</p>

        <Show when={props.author.links?.length}>
          <div class="blog-author-card__links">
            <For each={props.author.links}>
              {(link) => (
                <a href={link.href} target="_blank" rel="noreferrer noopener">
                  {link.label}
                </a>
              )}
            </For>
          </div>
        </Show>
      </div>
    </section>
  );
}
