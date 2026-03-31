const SESSION_KEY = "talafutipolo_session";
const ISLAND_KEY = "talafutipolo_island";

function generateSessionId(): string {
  return crypto.randomUUID();
}

export function ensureCommunitySessionId(): string {
  if (typeof localStorage === "undefined") return "";
  const existing = localStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const next = generateSessionId();
  localStorage.setItem(SESSION_KEY, next);
  return next;
}

export function getKnownIsland(): string | null {
  if (typeof localStorage === "undefined") return null;
  const island = localStorage.getItem(ISLAND_KEY)?.trim();
  return island ? island : null;
}

export function setKnownIsland(island: string): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(ISLAND_KEY, island);
}
