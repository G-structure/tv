import Database from "better-sqlite3";
import { join, resolve } from "path";
import type { Article, Category } from "./types";

// process.cwd() is site/ in both dev and production
const DB_PATH = resolve(join(process.cwd(), "..", "data", "football", "football.db"));

let db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!db) {
    db = new Database(DB_PATH, { readonly: true });
    db.pragma("journal_mode = WAL");
  }
  return db;
}

const ARTICLE_SELECT = `
  SELECT
    a.id, a.source_id, a.url,
    a.title_en, a.body_en, a.author,
    a.published_at, a.category, a.tags,
    a.image_url, a.image_alt, a.image_width, a.image_height,
    a.og_description_en, a.word_count,
    t.title_tvl, t.body_tvl, t.og_description_tvl
  FROM articles a
  LEFT JOIN translations t ON t.article_id = a.id
`;

export function getArticles(
  limit = 20,
  offset = 0,
  category?: string
): Article[] {
  const conn = getDb();
  if (category) {
    const stmt = conn.prepare(
      `${ARTICLE_SELECT}
       WHERE a.category = ?
       ORDER BY a.published_at DESC
       LIMIT ? OFFSET ?`
    );
    return stmt.all(category, limit, offset) as Article[];
  }
  const stmt = conn.prepare(
    `${ARTICLE_SELECT}
     ORDER BY a.published_at DESC
     LIMIT ? OFFSET ?`
  );
  return stmt.all(limit, offset) as Article[];
}

export function getArticle(id: string): Article | undefined {
  const conn = getDb();
  const stmt = conn.prepare(`${ARTICLE_SELECT} WHERE a.id = ?`);
  return stmt.get(id) as Article | undefined;
}

export function getCategories(): Category[] {
  const conn = getDb();
  const stmt = conn.prepare(`
    SELECT category AS slug, COUNT(*) AS count
    FROM articles
    WHERE category IS NOT NULL AND category != ''
    GROUP BY category
    ORDER BY count DESC
  `);
  return stmt.all() as Category[];
}

export function getArticleCount(category?: string): number {
  const conn = getDb();
  if (category) {
    const stmt = conn.prepare(
      "SELECT COUNT(*) AS cnt FROM articles WHERE category = ?"
    );
    return (stmt.get(category) as { cnt: number }).cnt;
  }
  const stmt = conn.prepare("SELECT COUNT(*) AS cnt FROM articles");
  return (stmt.get() as { cnt: number }).cnt;
}
