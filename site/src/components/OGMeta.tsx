import { Meta, Title } from "@solidjs/meta";

interface OGMetaProps {
  title: string;
  description?: string;
  image?: string | null;
  imageWidth?: number | null;
  imageHeight?: number | null;
  url?: string;
  type?: string;
  publishedAt?: string;
  category?: string;
}

export default function OGMeta(props: OGMetaProps) {
  return (
    <>
      <Title>{props.title} — Talafutipolo</Title>
      <Meta name="description" content={props.description || props.title} />

      {/* OpenGraph */}
      <Meta property="og:title" content={props.title} />
      <Meta property="og:description" content={props.description || props.title} />
      <Meta property="og:type" content={props.type || "website"} />
      <Meta property="og:site_name" content="Talafutipolo Tuvalu" />
      <Meta property="og:locale" content="tvl" />
      <Meta property="og:locale:alternate" content="en" />
      {props.url && <Meta property="og:url" content={props.url} />}
      {props.image && <Meta property="og:image" content={props.image} />}
      {props.imageWidth && (
        <Meta property="og:image:width" content={String(props.imageWidth)} />
      )}
      {props.imageHeight && (
        <Meta property="og:image:height" content={String(props.imageHeight)} />
      )}
      {props.publishedAt && (
        <Meta property="article:published_time" content={props.publishedAt} />
      )}
      {props.category && (
        <Meta property="article:section" content={props.category} />
      )}

      {/* Twitter Card */}
      <Meta
        name="twitter:card"
        content={props.image ? "summary_large_image" : "summary"}
      />
      <Meta name="twitter:title" content={props.title} />
      <Meta
        name="twitter:description"
        content={props.description || props.title}
      />
      {props.image && <Meta name="twitter:image" content={props.image} />}
    </>
  );
}
