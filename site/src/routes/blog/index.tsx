import { A, createAsync, cache } from "@solidjs/router";
import { For, Show } from "solid-js";
import PostCard from "~/components/blog/PostCard";
import OGMeta from "~/components/OGMeta";
import StructuredData from "~/components/StructuredData";
import {
  getAllPosts,
  getAllTags,
  getArchiveGroups,
  getFeaturedPost,
  getRecentPosts,
  type BlogArchiveGroup,
  type BlogTagIndex,
} from "~/lib/blog-data";
import type { BlogPost } from "~/lib/blog";
import { absoluteUrl, SITE_META } from "~/lib/site";

const loadBlogHome = cache(async (): Promise<{
  posts: BlogPost[];
  featured: BlogPost | null;
  latest: BlogPost[];
  tags: BlogTagIndex[];
  archive: BlogArchiveGroup[];
}> => {
  "use server";
  const posts = getAllPosts();
  return {
    posts,
    featured: getFeaturedPost(),
    latest: getRecentPosts(6),
    tags: getAllTags(),
    archive: getArchiveGroups(),
  };
}, "blog-home");

export const route = {
  load: () => loadBlogHome(),
};

export default function BlogIndex() {
  const data = createAsync(() => loadBlogHome());

  return (
    <Show when={data()}>
      {(blog) => {
        const secondaryPosts = blog().latest.filter(
          (post) => post.slug !== blog().featured?.slug
        );

        const collectionStructuredData = {
          "@context": "https://schema.org",
          "@type": "CollectionPage",
          name: SITE_META.publicationName,
          description: SITE_META.publicationDescription,
          url: absoluteUrl("/blog"),
          isPartOf: {
            "@type": "WebSite",
            name: SITE_META.publicationShortName,
            url: absoluteUrl("/"),
          },
          mainEntity: {
            "@type": "Blog",
            name: SITE_META.publicationName,
            url: absoluteUrl("/blog"),
            blogPost: blog().posts.map((post) => ({
              "@type": "BlogPosting",
              headline: post.title,
              url: absoluteUrl(`/blog/${post.slug}`),
              datePublished: post.publishedAt,
              description: post.description,
            })),
          },
        };

        return (
          <main class="blog-page blog-page--index">
            <OGMeta
              title={SITE_META.publicationName}
              description={SITE_META.publicationDescription}
              url={absoluteUrl("/blog")}
              image={SITE_META.defaultOgImage}
              imageWidth={SITE_META.defaultOgImageWidth}
              imageHeight={SITE_META.defaultOgImageHeight}
              imageAlt={SITE_META.defaultOgImageAlt}
              siteName={SITE_META.publicationShortName}
              titleSuffix={SITE_META.publicationShortName}
              keywords={blog().tags.map((tag) => tag.name)}
              alternateLinks={[
                {
                  href: SITE_META.feeds.blogRss,
                  title: `${SITE_META.publicationName} RSS`,
                  type: "application/rss+xml",
                },
                {
                  href: SITE_META.feeds.blogJson,
                  title: `${SITE_META.publicationName} JSON Feed`,
                  type: "application/feed+json",
                },
              ]}
            />
            <StructuredData data={collectionStructuredData} />

            <section class="blog-hero">
              <div class="blog-shell blog-shell--wide blog-hero__grid">
                <div class="blog-hero__copy">
                  <p class="blog-kicker">Language Lab Journal</p>
                  <h1 class="blog-hero__title">
                    Serious publishing for serious language technology.
                  </h1>
                  <p class="blog-hero__lede">
                    Research notes, launch posts, field reports, and open-source
                    writing from the team building AI infrastructure for endangered
                    languages.
                  </p>
                  <div class="blog-hero__actions">
                    <A href="/demo" class="blog-button blog-button--primary">
                      Explore the lab
                    </A>
                    <a href={SITE_META.feeds.blogRss} class="blog-button blog-button--ghost">
                      RSS
                    </a>
                    <a href={SITE_META.feeds.blogJson} class="blog-button blog-button--ghost">
                      JSON Feed
                    </a>
                  </div>
                </div>

                <div class="blog-hero__meta">
                  <div class="blog-stat-card">
                    <span class="blog-stat-card__label">Posts</span>
                    <strong class="blog-stat-card__value">{blog().posts.length}</strong>
                    <p class="blog-stat-card__detail">Editorial artifacts, not markdown dumps.</p>
                  </div>
                  <div class="blog-stat-card">
                    <span class="blog-stat-card__label">Topics</span>
                    <strong class="blog-stat-card__value">{blog().tags.length}</strong>
                    <p class="blog-stat-card__detail">Training, evaluation, launches, and open source.</p>
                  </div>
                  <div class="blog-stat-card">
                    <span class="blog-stat-card__label">Workflow</span>
                    <strong class="blog-stat-card__value">Markdown</strong>
                    <p class="blog-stat-card__detail">Edit one file, publish one post, keep the stack lean.</p>
                  </div>
                </div>
              </div>
            </section>

            <div class="blog-shell blog-shell--wide blog-home">
              <Show when={blog().featured}>
                {(featured) => (
                  <section class="blog-home__feature">
                    <div class="blog-home__section-head">
                      <div>
                        <p class="blog-section-kicker">Featured</p>
                        <h2 class="blog-section-title">Flagship story</h2>
                      </div>
                      <A href="/blog/archive" class="blog-text-link">
                        Full archive
                      </A>
                    </div>
                    <PostCard post={featured()} variant="feature" />
                  </section>
                )}
              </Show>

              <div class="blog-home__layout">
                <section class="blog-home__primary">
                  <Show
                    when={secondaryPosts.length > 0}
                    fallback={
                      <section class="blog-panel">
                        <p class="blog-panel__eyebrow">Issue zero</p>
                        <h2 class="blog-panel__title">The publication stack is ready for volume.</h2>
                        <p class="blog-panel__text">
                          New markdown documents become real posts with feeds, tags,
                          archive pages, structured metadata, and the long-form article
                          treatment already wired in.
                        </p>
                      </section>
                    }
                  >
                    <div class="blog-home__section-head">
                      <div>
                        <p class="blog-section-kicker">Latest</p>
                        <h2 class="blog-section-title">New from the publication</h2>
                      </div>
                    </div>

                    <div class="blog-post-list">
                      <For each={secondaryPosts}>
                        {(post) => <PostCard post={post} variant="list" />}
                      </For>
                    </div>
                  </Show>
                </section>

                <aside class="blog-home__sidebar">
                  <section class="blog-panel">
                    <p class="blog-panel__eyebrow">What we publish</p>
                    <h2 class="blog-panel__title">One publication, multiple modes.</h2>
                    <ul class="blog-panel__list">
                      <li>Technical deep dives with benchmarks, code, and failure cases.</li>
                      <li>Research updates that explain what changed and why it matters.</li>
                      <li>Launch posts for product, data, models, and open-source releases.</li>
                      <li>Field notes from building and deploying in public.</li>
                    </ul>
                  </section>

                  <section class="blog-panel">
                    <div class="blog-home__section-head blog-home__section-head--tight">
                      <div>
                        <p class="blog-panel__eyebrow">Topics</p>
                        <h2 class="blog-panel__title">Browse by beat</h2>
                      </div>
                    </div>
                    <div class="blog-tag-cloud">
                      <For each={blog().tags}>
                        {(tag) => (
                          <A href={`/blog/tag/${tag.slug}`} class="blog-topic-chip">
                            <span>{tag.name}</span>
                            <span>{tag.count}</span>
                          </A>
                        )}
                      </For>
                    </div>
                  </section>

                  <section class="blog-panel">
                    <div class="blog-home__section-head blog-home__section-head--tight">
                      <div>
                        <p class="blog-panel__eyebrow">Archive</p>
                        <h2 class="blog-panel__title">Publication history</h2>
                      </div>
                    </div>
                    <div class="blog-archive-list">
                      <For each={blog().archive}>
                        {(group) => (
                          <div class="blog-archive-list__item">
                            <span>{group.label}</span>
                            <span>{group.posts.length}</span>
                          </div>
                        )}
                      </For>
                    </div>
                  </section>

                  <section class="blog-panel blog-panel--cta">
                    <p class="blog-panel__eyebrow">Follow the loop</p>
                    <h2 class="blog-panel__title">Turn reading into deeper engagement.</h2>
                    <p class="blog-panel__text">
                      Try the live model, inspect the benchmarks, watch the project in
                      public, and subscribe through the publication feeds.
                    </p>
                    <div class="blog-panel__actions">
                      <A href="/chat" class="blog-button blog-button--primary">
                        Try the model
                      </A>
                      <A href="/chat/eval" class="blog-button blog-button--ghost">
                        View evals
                      </A>
                    </div>
                  </section>
                </aside>
              </div>
            </div>
          </main>
        );
      }}
    </Show>
  );
}
