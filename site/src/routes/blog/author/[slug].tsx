import { A, createAsync, cache, useParams } from "@solidjs/router";
import { For, Show } from "solid-js";
import { HttpStatusCode } from "@solidjs/start";
import AuthorCard from "~/components/blog/AuthorCard";
import PostCard from "~/components/blog/PostCard";
import OGMeta from "~/components/OGMeta";
import StructuredData from "~/components/StructuredData";
import { getAuthorBySlug, getPostsByAuthor } from "~/lib/blog-data";
import { absoluteUrl, SITE_META } from "~/lib/site";

const loadAuthorPage = cache(async (slug: string) => {
  "use server";
  const author = getAuthorBySlug(slug);
  const posts = getPostsByAuthor(slug);
  if (!author || posts.length === 0) return null;
  return { author, posts };
}, "blog-author-page");

export const route = {
  load: ({ params }: { params: { slug: string } }) => loadAuthorPage(params.slug),
};

export default function BlogAuthorPage() {
  const params = useParams<{ slug: string }>();
  const data = createAsync(() => loadAuthorPage(params.slug));

  return (
    <Show when={data()} fallback={<AuthorNotFound />}>
      {(page) => (
        <main class="blog-page blog-page--taxonomy">
          <OGMeta
            title={`${page().author.name} — ${SITE_META.publicationName}`}
            description={page().author.bio}
            url={absoluteUrl(`/blog/author/${page().author.slug}`)}
            image={SITE_META.defaultOgImage}
            imageWidth={SITE_META.defaultOgImageWidth}
            imageHeight={SITE_META.defaultOgImageHeight}
            imageAlt={SITE_META.defaultOgImageAlt}
            siteName={SITE_META.publicationShortName}
            titleSuffix={SITE_META.publicationShortName}
            authorNames={[page().author.name]}
          />
          <StructuredData
            data={{
              "@context": "https://schema.org",
              "@type": "ProfilePage",
              name: page().author.name,
              url: absoluteUrl(`/blog/author/${page().author.slug}`),
            }}
          />

          <div class="blog-shell blog-shell--wide">
            <section class="blog-taxonomy-hero">
              <p class="blog-kicker">Author</p>
              <AuthorCard author={page().author} />
            </section>

            <section class="blog-post-list blog-post-list--spacious">
              <For each={page().posts}>
                {(post) => <PostCard post={post} variant="list" />}
              </For>
            </section>
          </div>
        </main>
      )}
    </Show>
  );
}

function AuthorNotFound() {
  return (
    <main class="blog-page blog-page--taxonomy">
      <HttpStatusCode code={404} />
      <div class="blog-shell blog-shell--narrow blog-empty-state">
        <p class="blog-kicker">Language Lab Journal</p>
        <h1 class="blog-section-title">Author not found.</h1>
        <A href="/blog" class="blog-button blog-button--primary">
          Back to the blog
        </A>
      </div>
    </main>
  );
}
