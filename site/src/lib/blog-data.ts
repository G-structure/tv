import { getAllAuthors, resolveBlogAuthor } from "./blog-authors";
import { parseBlogMeta, parseBlogPost, slugify, type BlogPost, type BlogPostFull } from "./blog";

const postFiles = import.meta.glob("../content/blog/*.md", {
  query: "?raw",
  eager: true,
  import: "default",
}) as Record<string, string>;

export interface BlogTagIndex {
  name: string;
  slug: string;
  count: number;
}

export interface BlogArchiveGroup {
  year: string;
  label: string;
  posts: BlogPost[];
}

function slugFromPath(path: string): string {
  return path.replace(/^.*\//, "").replace(/\.md$/, "");
}

function compareDatesDesc(a?: string, b?: string): number {
  return (b || "").localeCompare(a || "");
}

let postsCache: BlogPost[] | null = null;

export function getAllPosts(): BlogPost[] {
  if (postsCache) return postsCache;

  const posts = Object.entries(postFiles)
    .map(([path, raw]) => parseBlogMeta(slugFromPath(path), raw))
    .sort((left, right) => {
      if (left.featured !== right.featured) {
        return left.featured ? -1 : 1;
      }
      return compareDatesDesc(left.publishedAt, right.publishedAt);
    });

  postsCache = posts;
  return posts;
}

export function getRecentPosts(limit = 6): BlogPost[] {
  return getAllPosts().slice(0, limit);
}

export function getFeaturedPost(): BlogPost | null {
  return getAllPosts().find((post) => post.featured) || getAllPosts()[0] || null;
}

export function getPostBySlug(slug: string): BlogPostFull | null {
  for (const [path, raw] of Object.entries(postFiles)) {
    if (slugFromPath(path) === slug) {
      return parseBlogPost(slug, raw);
    }
  }
  return null;
}

export function getRelatedPosts(slug: string, limit = 3): BlogPost[] {
  const source = getAllPosts().find((post) => post.slug === slug);
  if (!source) return getRecentPosts(limit);

  return getAllPosts()
    .filter((post) => post.slug !== slug)
    .map((post) => {
      const sharedTags = post.tagSlugs.filter((tag) => source.tagSlugs.includes(tag)).length;
      return { post, sharedTags };
    })
    .sort((left, right) => {
      if (left.sharedTags !== right.sharedTags) return right.sharedTags - left.sharedTags;
      return compareDatesDesc(left.post.publishedAt, right.post.publishedAt);
    })
    .map((entry) => entry.post)
    .slice(0, limit);
}

export function getAdjacentPosts(slug: string): {
  newer: BlogPost | null;
  older: BlogPost | null;
} {
  const ordered = [...getAllPosts()].sort((left, right) =>
    compareDatesDesc(left.publishedAt, right.publishedAt)
  );
  const index = ordered.findIndex((post) => post.slug === slug);
  if (index === -1) {
    return { newer: null, older: null };
  }

  return {
    newer: ordered[index - 1] || null,
    older: ordered[index + 1] || null,
  };
}

export function getAllTags(): BlogTagIndex[] {
  const counts = new Map<string, BlogTagIndex>();

  for (const post of getAllPosts()) {
    post.tags.forEach((tag, index) => {
      const key = post.tagSlugs[index] || slugify(tag);
      const current = counts.get(key);
      if (current) {
        current.count += 1;
      } else {
        counts.set(key, { name: tag, slug: key, count: 1 });
      }
    });
  }

  return Array.from(counts.values()).sort((left, right) => {
    if (left.count !== right.count) return right.count - left.count;
    return left.name.localeCompare(right.name);
  });
}

export function getPostsByTag(tagSlug: string): BlogPost[] {
  return getAllPosts().filter((post) => post.tagSlugs.includes(tagSlug));
}

export function getArchiveGroups(): BlogArchiveGroup[] {
  const buckets = new Map<string, BlogPost[]>();

  for (const post of getAllPosts()) {
    const year = post.publishedAt.slice(0, 4) || "Unknown";
    const items = buckets.get(year) || [];
    items.push(post);
    buckets.set(year, items);
  }

  return Array.from(buckets.entries())
    .sort((left, right) => right[0].localeCompare(left[0]))
    .map(([year, posts]) => ({
      year,
      label: year,
      posts: posts.sort((left, right) => compareDatesDesc(left.publishedAt, right.publishedAt)),
    }));
}

export function getPostsByAuthor(authorSlug: string): BlogPost[] {
  return getAllPosts().filter((post) => post.authors.some((author) => author.slug === authorSlug));
}

export function getAuthorBySlug(authorSlug: string) {
  return getAllAuthors().find((author) => author.slug === authorSlug) || resolveBlogAuthor(authorSlug);
}
