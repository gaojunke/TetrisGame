// GPL-3.0-or-later. No account credentials are needed or shipped in the plugin.
const ADJECTIVES = ["Amber", "Arctic", "Azure", "Brave", "Calm", "Coral", "Golden", "Jade"];
const ANIMALS = ["Fox", "Owl", "Panda", "Otter", "Lynx", "Crane", "Finch", "Whale"];

class HttpError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

function json(data: unknown, status = 200): Response {
  return Response.json(data, { status, headers: {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    ...(status === 429 ? { "Retry-After": "60" } : {}),
  }});
}

async function digest(value: string): Promise<string> {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
}

async function playerId(request: Request): Promise<string> {
  const auth = request.headers.get("Authorization") || "";
  if (!/^Bearer [A-Za-z0-9_-]{43}$/.test(auth)) throw new HttpError(401, "invalid_player_token");
  // Only the digest is persisted; the random installation token stays on-device.
  return digest(auth.slice(7));
}

function countryOf(request: Request): string {
  // Only trusted Cloudflare ingress metadata; never a client-supplied country/IP.
  const country = request.cf?.country;
  return typeof country === "string" && /^[A-Z]{2}$/.test(country) ? country : "XX";
}

async function nicknameOf(id: string): Promise<string> {
  const seed = await digest("nickname-v1:" + id);
  return `${ADJECTIVES[parseInt(seed.slice(0, 2), 16) % 8]}${ANIMALS[parseInt(seed.slice(2, 4), 16) % 8]}-${seed.slice(4, 12)}`;
}

async function readBody(request: Request): Promise<Record<string, unknown>> {
  if (!(request.headers.get("Content-Type") || "").startsWith("application/json")) {
    throw new HttpError(415, "json_required");
  }
  if (!request.body) throw new HttpError(400, "missing_body");
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 2048) { await reader.cancel(); throw new HttpError(413, "body_too_large"); }
    chunks.push(value);
  }
  const buffer = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.byteLength; }
  let body: unknown;
  try { body = JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(buffer)); }
  catch { throw new HttpError(400, "invalid_json"); }
  if (!body || typeof body !== "object" || Array.isArray(body)) throw new HttpError(400, "invalid_body");
  return body as Record<string, unknown>;
}

function integer(value: unknown, min: number, max: number): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < min || value > max) {
    throw new HttpError(400, "invalid_score");
  }
  return value;
}

function validateScore(body: Record<string, unknown>): { event: string; score: number } {
  if (Object.keys(body).some(key => !["event_id", "score", "lines", "pieces", "duration_ms"].includes(key))) {
    throw new HttpError(400, "unexpected_field");
  }
  if (typeof body.event_id !== "string" || !/^[0-9a-f]{32}$/.test(body.event_id)) {
    throw new HttpError(400, "invalid_event");
  }
  const score = integer(body.score, 0, 10000000);
  const lines = integer(body.lines, 0, 100000);
  const pieces = integer(body.pieces, 1, 1000000);
  const duration = integer(body.duration_ms, 1, 30 * 86400000);
  if (score % 100 || score < lines * 100 || score > lines * 200 ||
      lines * 10 > pieces * 4 || pieces > duration / 20 + 10) {
    throw new HttpError(400, "inconsistent_score");
  }
  return { event: body.event_id, score };
}

async function ensurePlayer(env: Env, id: string, country: string): Promise<void> {
  await env.DB.prepare(
    "INSERT INTO players(player_id,nickname,country,created_at) VALUES(?,?,?,?) ON CONFLICT(player_id) DO NOTHING"
  ).bind(id, await nicknameOf(id), country, Date.now()).run();
}

async function profile(env: Env, id: string, country: string): Promise<unknown> {
  const row = await env.DB.prepare(
    "SELECT nickname, MAX(best_score,0) AS score, games_played FROM players WHERE player_id=?"
  ).bind(id).first();
  return { ...row, country };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    try {
      const url = new URL(request.url);
      if (url.protocol !== "https:") throw new HttpError(400, "https_required");
      const path = url.pathname;
      // Rate-limit IPs transiently; do not save IP addresses or request headers.
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const limiter = request.method === "GET" ? env.READ_LIMITER : env.WRITE_LIMITER;
      if (!(await limiter.limit({ key: ip })).success) throw new HttpError(429, "rate_limited");
      if (path === "/health" && request.method === "GET") {
        await env.DB.prepare("SELECT 1 FROM players LIMIT 1").first();
        return json({ status: "ok", version: "1.4.0" });
      }
      if (path === "/v1/leaderboard" && request.method === "GET") {
        const result = await env.DB.prepare(
          "SELECT nickname,best_score AS score,country FROM players WHERE best_score>=0 ORDER BY best_score DESC,best_at ASC,player_id ASC LIMIT 5"
        ).all();
        return json({ players: result.results });
      }
      if (!["/v1/player", "/v1/scores"].includes(path)) throw new HttpError(404, "not_found");
      if (request.method !== "POST" && !(path === "/v1/player" && request.method === "DELETE")) {
        throw new HttpError(405, "method_not_allowed");
      }
      const id = await playerId(request);
      const country = countryOf(request);
      if (request.method === "DELETE") {
        await env.DB.prepare("DELETE FROM players WHERE player_id=?").bind(id).run();
        return json({ deleted: true });
      }
      if (!(await env.WRITE_LIMITER.limit({ key: "player:" + id })).success) throw new HttpError(429, "rate_limited");
      if (path === "/v1/scores") {
        const { event, score } = validateScore(await readBody(request));
        await ensurePlayer(env, id, country);
        await env.DB.prepare(
          "INSERT INTO score_events(player_id,event_id,score,country,submitted_at) VALUES(?,?,?,?,?) ON CONFLICT(player_id,event_id) DO NOTHING"
        ).bind(id, event, score, country, Date.now()).run();
      } else {
        const body = await readBody(request);
        if (Object.keys(body).length) throw new HttpError(400, "unexpected_field");
        await ensurePlayer(env, id, country);
      }
      return json({ player: await profile(env, id, country) });
    } catch (error) {
      if (error instanceof HttpError) return json({ error: error.message }, error.status);
      // Never log tokens, IPs, bodies, SQL parameters, or arbitrary exception text.
      console.error(JSON.stringify({ event: "leaderboard_request_failed" }));
      return json({ error: "service_unavailable" }, 503);
    }
  },
} satisfies ExportedHandler<Env>;
