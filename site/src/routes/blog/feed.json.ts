import { getAllPosts, getPostBySlug } from "~/lib/blog-data";
import { absoluteImageUrl, absoluteUrl, SITE_META } from "~/lib/site";

export async function GET() {
  const posts = getAllPosts();

  const feed = {
    version: "https://jsonfeed.org/version/1.1",
    title: SITE_META.publicationName,
    home_page_url: absoluteUrl("/blog"),
    feed_url: absoluteUrl("/blog/feed.json"),
    description: SITE_META.publicationDescription,
    favicon: absoluteUrl("/icons/icon-192.png"),
    icon: absoluteUrl("/icons/icon-512.png"),
    language: "en-US",
    authors: [
      {
        name: SITE_META.publicationShortName,
        url: absoluteUrl("/demo"),
      },
    ],
    items: posts.map((summary) => {
      const post = getPostBySlug(summary.slug);
      return {
        id: absoluteUrl(`/blog/${summary.slug}`),
        url: absoluteUrl(`/blog/${summary.slug}`),
        title: summary.title,
        summary: summary.description,
        content_html: post?.html,
        image: absoluteImageUrl(summary.socialImage || summary.image),
        date_published: summary.publishedAt,
        date_modified: summary.updatedAt || summary.publishedAt,
        tags: summary.tags,
        authors: summary.authors.map((author) => ({
          name: author.name,
          url: author.href,
        })),
      };
    }),
  };

  return new Response(JSON.stringify(feed, null, 2), {
    status: 200,
    headers: {
      "Content-Type": "application/feed+json; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
