import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { randomBytes } from "node:crypto";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";

let mf;
before(async () => {
  mf = new Miniflare(convertV4MiniflareOptions({ cf: false, workers: [{
    modules: true, scriptPath: ".test-build/index.js",
    // Latest published local workerd is 2026-09-03. Production uses 2026-09-05.
    compatibilityDate: "2026-09-03", compatibilityFlags: ["nodejs_compat"],
    d1Databases: ["DB"],
    ratelimits: {
      READ_LIMITER: { namespace_id: "1400001", simple: { limit: 120, period: 60 } },
      WRITE_LIMITER: { namespace_id: "1400002", simple: { limit: 30, period: 60 } },
    },
  }] }));
  const db = await mf.getD1Database("DB");
  const migration = await readFile("migrations/0001_leaderboard.sql", "utf8");
  const statements = migration.match(/CREATE TRIGGER[\s\S]*?END;|CREATE (?:TABLE|INDEX)[\s\S]*?;/g);
  await db.batch(statements.map(sql => db.prepare(sql)));
});
after(async () => { await mf?.dispose(); });

const token = () => randomBytes(32).toString("base64url");
const event = (score = 100) => ({event_id: randomBytes(16).toString("hex"), score,
  lines: score / 100, pieces: Math.max(1, score / 100 * 3), duration_ms: 60000});
async function request(path, {key, body, country = "CN", method, headers = {}} = {}) {
  return mf.dispatchFetch("https://leaderboard.test" + path, {
    method: method || (body === undefined ? "GET" : "POST"),
    headers: {"CF-Connecting-IP": "192.0.2." + (key?.charCodeAt(0) || 1),
      ...(key ? {Authorization: "Bearer " + key} : {}), "Content-Type": "application/json", ...headers},
    ...(body === undefined ? {} : {body: JSON.stringify(body)}), cf: {country},
  });
}

test("automatic identity, trusted country, idempotent best score and five-place ranking", async () => {
  const key = token();
  let r = await request("/v1/player", {key, body: {}});
  assert.equal(r.status, 200);
  const original = (await r.json()).player;
  assert.match(original.nickname, /^[A-Za-z]+-[0-9a-f]{8}$/);
  assert.equal(original.country, "CN");
  r = await request("/v1/player", {key, body: {}, country: "US"});
  assert.equal((await r.json()).player.nickname, original.nickname);
  const score = event(1000);
  for (let i = 0; i < 2; i++) {
    r = await request("/v1/scores", {key, body: score});
    assert.equal(r.status, 200);
    assert.equal((await r.json()).player.games_played, 1);
  }
  r = await request("/v1/scores", {key, body: event(100), country: "US"});
  assert.equal((await r.json()).player.score, 1000);
  for (let i = 1; i <= 6; i++) {
    r = await request("/v1/scores", {key: token(), body: event(i * 100), country: "DE"});
    assert.equal(r.status, 200);
  }
  const ranked = (await (await request("/v1/leaderboard")).json()).players;
  assert.deepEqual(ranked.map(x => x.score), [1000, 600, 500, 400, 300]);
  assert.equal(ranked[0].country, "CN"); // country of personal best, not later lower score
  assert.deepEqual(Object.keys(ranked[0]).sort(), ["country", "nickname", "score"]);
});

test("reject forged country/nickname, invalid inputs and missing credentials", async () => {
  for (const body of [ {...event(), country: "US"}, {...event(), nickname: "admin"},
    {...event(), score: -100}, {...event(), score: true}, {...event(), lines: 0},
    {...event(), score: 1.5}, {...event(), pieces: 0}, {...event(), event_id: "' OR 1=1--"} ]) {
    assert.equal((await request("/v1/scores", {key: token(), body})).status, 400);
  }
  assert.equal((await request("/v1/scores", {body: event()})).status, 401);
  assert.equal((await request("/v1/player", {key: token(), body: {country: "US"}})).status, 400);
  assert.equal((await request("/v1/player", {key: token(), body: {junk: "x".repeat(3000)}})).status, 413);
  const key = token();
  const r = await request("/v1/player", {key, body: {}, country: "T1", headers: {"CF-IPCountry": "US"}});
  assert.equal((await r.json()).player.country, "XX");
});

test("delete own data only; score events cascade; rate limiter responds 429", async () => {
  const key = token();
  const result = await (await request("/v1/scores", {key, body: event(0)})).json();
  assert.equal(result.player.games_played, 1);
  assert.equal((await request("/v1/player", {key, method: "DELETE"})).status, 200);
  const db = await mf.getD1Database("DB");
  assert.equal((await db.prepare("SELECT COUNT(*) AS n FROM players WHERE nickname=?")
    .bind(result.player.nickname).first()).n, 0);
  let limited = false;
  const readKey = token();
  for (let i = 0; i < 125; i++) {
    const r = await request("/v1/leaderboard", {key: readKey});
    if (r.status === 429) { limited = true; assert.equal(r.headers.get("Retry-After"), "60"); break; }
    await r.arrayBuffer();
  }
  assert.equal(limited, true);
});
