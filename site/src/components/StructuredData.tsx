export default function StructuredData(props: { data: Record<string, unknown> | Array<Record<string, unknown>> }) {
  // Escape closing script tags to prevent XSS via JSON-LD injection
  const safeJson = () => JSON.stringify(props.data).replace(/<\/script/gi, "<\\/script");
  return (
    <script
      type="application/ld+json"
      innerHTML={safeJson()}
    />
  );
}
