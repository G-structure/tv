import { Marked, Renderer } from "marked";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import javascript from "highlight.js/lib/languages/javascript";
import typescript from "highlight.js/lib/languages/typescript";
import bash from "highlight.js/lib/languages/bash";
import json from "highlight.js/lib/languages/json";
import { resolveBlogAuthor, type BlogAuthor } from "./blog-authors";
import { absoluteUrl } from "./site";

hljs.registerLanguage("python", python);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("bash", bash);
hljs.registerLanguage("json", json);

type FrontmatterValue = string | number | boolean | string[];

const KNOWN_IMAGE_DIMENSIONS: Record<string, [number, number]> = {
  "/blog/pai-vau-cover.webp": [800, 1048],
  "/blog/tinker-spend-march.webp": [1200, 758],
  "/social/language-lab-blog.jpg": [1200, 630],
  "/social/technical-deepdive-card.jpg": [1200, 630],
};

export interface BlogHeading {
  id: string;
  text: string;
  depth: number;
}

export interface BlogPost {
  slug: string;
  title: string;
  description: string;
  publishedAt: string;
  updatedAt?: string;
  image?: string;
  imageAlt?: string;
  socialImage?: string;
  socialImageAlt?: string;
  authors: BlogAuthor[];
  tags: string[];
  tagSlugs: string[];
  kind: string;
  featured: boolean;
  canonicalUrl: string;
  wordCount: number;
  readingTimeMinutes: number;
}

export interface BlogPostFull extends BlogPost {
  body: string;
  html: string;
  headings: BlogHeading[];
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-{2,}/g, "-");
}

function createSlugger(): (value: string) => string {
  const seen = new Map<string, number>();
  return (value: string) => {
    const base = slugify(value) || "section";
    const count = seen.get(base) || 0;
    seen.set(base, count + 1);
    return count === 0 ? base : `${base}-${count + 1}`;
  };
}

function parseArrayLiteral(value: string): string[] {
  const inner = value.slice(1, -1).trim();
  if (!inner) return [];
  return inner
    .split(",")
    .map((item) => item.trim().replace(/^['"]|['"]$/g, ""))
    .filter(Boolean);
}

function parseScalar(value: string): FrontmatterValue {
  const trimmed = value.trim();
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return Number(trimmed);
  if (trimmed.startsWith("[") && trimmed.endsWith("]")) {
    return parseArrayLiteral(trimmed);
  }
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

/** Parse lightweight YAML frontmatter without introducing CMS-level complexity. */
function parseFrontmatter(raw: string): {
  meta: Record<string, FrontmatterValue>;
  body: string;
} {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) return { meta: {}, body: raw };

  const meta: Record<string, FrontmatterValue> = {};
  const lines = match[1].split(/\r?\n/);

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.trim()) continue;

    const keyMatch = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!keyMatch) continue;

    const [, key, rawValue] = keyMatch;
    if (rawValue.trim().length > 0) {
      meta[key] = parseScalar(rawValue);
      continue;
    }

    const listItems: string[] = [];
    while (index + 1 < lines.length && /^\s*-\s+/.test(lines[index + 1])) {
      index += 1;
      listItems.push(lines[index].replace(/^\s*-\s+/, "").trim().replace(/^['"]|['"]$/g, ""));
    }

    meta[key] = listItems;
  }

  return { meta, body: match[2] };
}

function toStringArray(value: FrontmatterValue | undefined): string[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean);
  return [String(value)].filter(Boolean);
}

function toStringValue(value: FrontmatterValue | undefined): string | undefined {
  if (value === undefined || value === null) return undefined;
  return String(value);
}

function toBooleanValue(value: FrontmatterValue | undefined): boolean {
  return value === true || value === "true";
}

function stripMarkdown(value: string): string {
  return value
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, " $1 ")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, " $1 ")
    .replace(/<\/?[^>]+>/g, " ")
    .replace(/^[#>*-]+\s*/gm, "")
    .replace(/\|/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function estimateReadingTimeMinutes(wordCount: number): number {
  return Math.max(1, Math.round(wordCount / 220));
}

function extractHeadings(body: string): BlogHeading[] {
  const lexer = new Marked();
  const tokens = lexer.lexer(body) as Array<any>;
  const nextHeadingId = createSlugger();

  const headings: BlogHeading[] = [];
  const visit = (tokenList: Array<any>) => {
    for (const token of tokenList) {
      if (token.type === "heading" && token.depth >= 2 && token.depth <= 3) {
        headings.push({
          id: nextHeadingId(token.text),
          text: stripMarkdown(token.text),
          depth: token.depth,
        });
      }

      if (Array.isArray(token.tokens)) visit(token.tokens);
      if (token.type === "list" && Array.isArray(token.items)) {
        for (const item of token.items) {
          if (Array.isArray(item.tokens)) visit(item.tokens);
        }
      }
    }
  };

  visit(tokens);
  return headings;
}

function createMarkedRenderer() {
  const renderer = new Renderer();
  const nextHeadingId = createSlugger();

  renderer.heading = function (this: any, token: any) {
    const text = this.parser.parseInline(token.tokens);
    const id = nextHeadingId(token.text);
    return `<h${token.depth} id="${id}" class="blog-heading blog-heading--${token.depth}">
      <a href="#${id}" class="blog-heading__anchor-link">
        <span>${text}</span>
        <span class="blog-heading__hash" aria-hidden="true">#</span>
      </a>
    </h${token.depth}>`;
  };

  renderer.code = function (token: any) {
    const rawLanguage = (token.lang || "").trim();
    const language = rawLanguage.split(/\s+/)[0];
    const supportedLanguage = language && hljs.getLanguage(language) ? language : "plaintext";
    const highlighted =
      supportedLanguage !== "plaintext"
        ? hljs.highlight(token.text, { language: supportedLanguage }).value
        : escapeHtml(token.text);
    const id = `code-${Math.random().toString(36).slice(2, 9)}`;

    return `<div class="blog-code">
      <div class="blog-code__header">
        <span class="blog-code__lang">${supportedLanguage}</span>
        <button type="button" onclick="navigator.clipboard.writeText(document.getElementById('${id}')?.textContent || '').then(()=>{this.textContent='Copied';setTimeout(()=>{this.textContent='Copy'},1800)})" class="blog-code__copy">Copy</button>
      </div>
      <pre class="blog-code__pre"><code id="${id}" class="hljs language-${supportedLanguage}">${highlighted}</code></pre>
    </div>`;
  };

  renderer.codespan = function (token: any) {
    return `<code class="blog-inline-code">${escapeHtml(token.text)}</code>`;
  };

  renderer.table = function (this: any, token: any) {
    const tableHtml = Renderer.prototype.table.call(this, token);
    return `<div class="blog-table-wrap">${tableHtml}</div>`;
  };

  renderer.image = function (token: any) {
    const href = token.href || "";
    const alt = token.text || "";
    const title = token.title || "";
    const [width, height] = KNOWN_IMAGE_DIMENSIONS[href] || [];
    const sizeAttributes = width ? ` width="${width}" height="${height}"` : "";
    const caption = title || alt;
    return `<figure class="blog-figure">
      <img src="${href}" alt="${escapeHtml(alt)}"${sizeAttributes} loading="lazy" decoding="async" />
      ${caption ? `<figcaption>${escapeHtml(caption)}</figcaption>` : ""}
    </figure>`;
  };

  renderer.link = function (this: any, token: any) {
    const href = token.href || "#";
    const titleAttr = token.title ? ` title="${escapeHtml(token.title)}"` : "";
    const isExternal = /^https?:\/\//i.test(href);
    const rel = isExternal ? ` rel="noreferrer noopener"` : "";
    const target = isExternal ? ` target="_blank"` : "";
    const text = this.parser.parseInline(token.tokens);
    return `<a href="${href}"${titleAttr}${rel}${target}>${text}</a>`;
  };

  return new Marked({
    gfm: true,
    breaks: false,
    renderer,
  });
}

function buildPostBase(slug: string, raw: string): Omit<BlogPostFull, "html" | "headings"> {
  const { meta, body } = parseFrontmatter(raw);
  const finalSlug = toStringValue(meta.slug) || slug;
  const title = toStringValue(meta.title) || slug;
  const description = toStringValue(meta.description) || "";
  const publishedAt = toStringValue(meta.publishedAt) || toStringValue(meta.published) || toStringValue(meta.date) || "";
  const updatedAt = toStringValue(meta.updatedAt) || toStringValue(meta.updated) || toStringValue(meta.modified);
  const image = toStringValue(meta.image);
  const socialImage = toStringValue(meta.socialImage) || toStringValue(meta.social_image) || image;
  const imageAlt = toStringValue(meta.imageAlt) || toStringValue(meta.image_alt) || title;
  const socialImageAlt = toStringValue(meta.socialImageAlt) || toStringValue(meta.social_image_alt) || imageAlt;
  const tags = [
    ...toStringArray(meta.tags),
    ...toStringArray(meta.topics),
  ].filter(Boolean);
  const authors = toStringArray(meta.authors).length > 0
    ? toStringArray(meta.authors)
    : toStringArray(meta.author).length > 0
      ? toStringArray(meta.author)
      : ["language-lab"];
  const authorProfiles = authors.map(resolveBlogAuthor);
  const wordCount = stripMarkdown(body).split(/\s+/).filter(Boolean).length;
  const readingTimeMinutes = estimateReadingTimeMinutes(wordCount);

  return {
    slug: finalSlug,
    title,
    description,
    publishedAt,
    updatedAt,
    image,
    imageAlt,
    socialImage,
    socialImageAlt,
    authors: authorProfiles,
    tags,
    tagSlugs: tags.map(slugify),
    kind: toStringValue(meta.kind) || toStringValue(meta.format) || "Research note",
    featured: toBooleanValue(meta.featured),
    canonicalUrl: toStringValue(meta.canonicalUrl) || toStringValue(meta.canonical_url) || absoluteUrl(`/blog/${finalSlug}`),
    wordCount,
    readingTimeMinutes,
    body,
  };
}

export function parseBlogPost(slug: string, raw: string): BlogPostFull {
  const post = buildPostBase(slug, raw);
  const marked = createMarkedRenderer();
  return {
    ...post,
    html: marked.parse(post.body) as string,
    headings: extractHeadings(post.body),
  };
}

export function parseBlogMeta(slug: string, raw: string): BlogPost {
  const post = buildPostBase(slug, raw);
  const { body: _body, ...meta } = post;
  return meta;
}
