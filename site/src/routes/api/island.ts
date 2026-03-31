import type { APIEvent } from "@solidjs/start/server";
import { backfillIslandForSession } from "~/lib/db";
import { ISLANDS } from "~/lib/types";

const VALID_ISLANDS = new Set(ISLANDS);

export async function POST(event: APIEvent) {
  try {
    const body = await event.request.json();
    const island = typeof body.island === "string" ? body.island.trim() : "";
    const sessionId =
      typeof body.session_id === "string" ? body.session_id.trim() : "";

    if (!sessionId || sessionId.length > 200 || !VALID_ISLANDS.has(island as (typeof ISLANDS)[number])) {
      return new Response(JSON.stringify({ error: "Invalid island payload" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    await backfillIslandForSession(sessionId, island);

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("Island backfill API error:", e);
    return new Response(JSON.stringify({ error: "Server error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
