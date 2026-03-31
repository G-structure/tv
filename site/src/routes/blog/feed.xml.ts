import { getAllPosts, getPostBySlug } from "~/lib/blog-data";
import { absoluteImageUrl, absoluteUrl, SITE_META } from "~/lib/site";

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  const posts = getAllPosts();
  const items = posts
    .map((summary) => {
      const post = getPostBySlug(summary.slug);
      const link = absoluteUrl(`/blog/${summary.slug}`);
      const description = escapeXml(summary.description);
      const content = post?.html || "";
      return `    <item>
      <title>${escapeXml(summary.title)}</title>
      <link>${escapeXml(link)}</link>
      <guid isPermaLink="true">${escapeXml(link)}</guid>
      <description>${description}</description>
      <pubDate>${new Date(summary.publishedAt).toUTCString()}</pubDate>
      <enclosure url="${escapeXml(absoluteImageUrl(summary.socialImage || summary.image))}" type="image/jpeg" />
      <content:encoded><![CDATA[${content}]]></content:encoded>
    </item>`;
    })
    .join("\n");

  const latest = posts[0]?.publishedAt
    ? new Date(posts[0].publishedAt).toUTCString()
    : new Date().toUTCString();

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>${SITE_META.publicationName}</title>
    <link>${absoluteUrl("/blog")}</link>
    <description>${escapeXml(SITE_META.publicationDescription)}</description>
    <language>en-US</language>
    <lastBuildDate>${latest}</lastBuildDate>
    <atom:link href="${absoluteUrl("/blog/feed.xml")}" rel="self" type="application/rss+xml"/>
${items}
  </channel>
</rss>`;

  return new Response(xml, {
    status: 200,
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
