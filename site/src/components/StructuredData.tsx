export default function StructuredData(props: { data: Record<string, unknown> | Array<Record<string, unknown>> }) {
  return (
    <script
      type="application/ld+json"
      innerHTML={JSON.stringify(props.data)}
    />
  );
}
