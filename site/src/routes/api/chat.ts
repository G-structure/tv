import type { APIEvent } from "@solidjs/start/server";

const MAX_MESSAGE_LENGTH = 4000;
const MAX_MESSAGES = 50;
const MAX_BODY_BYTES = 64 * 1024; // 64 KB

function getBackendUrl(event: APIEvent): string {
  const cfEnv = (event.context as any)?.cloudflare?.env;
  return cfEnv?.CHAT_BACKEND_URL || process.env.CHAT_BACKEND_URL || "http://localhost:8787";
}

function validateChatBody(body: unknown): { ok: true; payload: object } | { ok: false; error: string } {
  if (!body || typeof body !== "object") return { ok: false, error: "Invalid request body" };
  const b = body as Record<string, unknown>;

  if (!Array.isArray(b.messages)) return { ok: false, error: "messages must be an array" };
  if (b.messages.length === 0) return { ok: false, error: "messages must not be empty" };
  if (b.messages.length > MAX_MESSAGES) return { ok: false, error: `Too many messages (max ${MAX_MESSAGES})` };

  const validRoles = new Set(["user", "assistant", "system"]);
  for (const msg of b.messages) {
    if (!msg || typeof msg !== "object") return { ok: false, error: "Invalid message" };
    if (!validRoles.has((msg as any).role)) return { ok: false, error: "Invalid message role" };
    if (typeof (msg as any).content !== "string") return { ok: false, error: "Message content must be a string" };
    if ((msg as any).content.length > MAX_MESSAGE_LENGTH) return { ok: false, error: `Message too long (max ${MAX_MESSAGE_LENGTH} chars)` };
  }

  if (b.temperature !== undefined && (typeof b.temperature !== "number" || b.temperature < 0 || b.temperature > 2)) {
    return { ok: false, error: "temperature must be 0-2" };
  }
  if (b.max_tokens !== undefined && (typeof b.max_tokens !== "number" || b.max_tokens < 1 || b.max_tokens > 4096)) {
    return { ok: false, error: "max_tokens must be 1-4096" };
  }

  return {
    ok: true,
    payload: {
      messages: b.messages.map((m: any) => ({ role: m.role, content: m.content })),
      temperature: b.temperature ?? 0.3,
      max_tokens: b.max_tokens ?? 1024,
    },
  };
}

export async function POST(event: APIEvent) {
  const backendUrl = getBackendUrl(event);
  const targetUrl = `${backendUrl}/api/chat`;

  try {
    const contentLength = event.request.headers.get("content-length");
    if (contentLength && parseInt(contentLength, 10) > MAX_BODY_BYTES) {
      return new Response(JSON.stringify({ error: "Request too large" }), {
        status: 413,
        headers: { "Content-Type": "application/json" },
      });
    }

    const body = await event.request.json();
    const validation = validateChatBody(body);
    if (!validation.ok) {
      return new Response(JSON.stringify({ error: validation.error }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const resp = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(validation.payload),
    });

    if (!resp.ok) {
      const status = resp.status >= 500 ? 502 : resp.status;
      return new Response(JSON.stringify({ error: "Chat request failed" }), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(resp.body, {
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: "Chat service unavailable" }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  }
}
