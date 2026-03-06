export interface Article {
  id: string;
  source_id: string;
  url: string;
  title_en: string;
  body_en: string;
  author: string | null;
  published_at: string;
  category: string | null;
  tags: string | null;
  image_url: string | null;
  image_alt: string | null;
  image_width: number | null;
  image_height: number | null;
  og_description_en: string | null;
  word_count: number | null;
  // From translations join
  title_tvl?: string | null;
  body_tvl?: string | null;
  og_description_tvl?: string | null;
}

export interface Category {
  slug: string;
  count: number;
}
