// Scoreboard for the daily set. Runs on Cloudflare Pages Functions and stores totals in a D1 database
// connected to the project under the variable name DB (Settings > Bindings in the Cloudflare dashboard).
//
//   POST /api/score  {date:"2026-10-26", device:"<random id>", total:3450, pts:[900,700,...]}
//        records one finished daily set per device per day, then returns today's stats
//   GET  /api/stats?date=2026-10-26
//        returns today's stats without recording anything
//
// Stats: {n: players, avg: average total, slots: average points for each of the 5 globes,
//         hist: how many players scored 0-99, 100-199, ... 5000 (51 buckets)}
// Running totals are stored per day, plus each finished total on its own (just the number, never linked to the
// device code) so the results chart can place every dot exactly. The chart gets the latest 300 totals, which keeps
// reads small however many people play. Each finished game costs 4 row writes.

const DATE = /^\d{4}-\d{2}-\d{2}$/;
let ready = false;

async function setup(db) {
  if (ready) return;
  await db.batch([
    db.prepare("CREATE TABLE IF NOT EXISTS plays (date TEXT NOT NULL, device TEXT NOT NULL, PRIMARY KEY (date, device))"),
    db.prepare("CREATE TABLE IF NOT EXISTS daily (date TEXT PRIMARY KEY, n INTEGER NOT NULL, total INTEGER NOT NULL, s0 INTEGER NOT NULL, s1 INTEGER NOT NULL, s2 INTEGER NOT NULL, s3 INTEGER NOT NULL, s4 INTEGER NOT NULL)"),
    db.prepare("CREATE TABLE IF NOT EXISTS hist (date TEXT NOT NULL, bucket INTEGER NOT NULL, n INTEGER NOT NULL, PRIMARY KEY (date, bucket))"),
    db.prepare("CREATE TABLE IF NOT EXISTS scores (date TEXT NOT NULL, total INTEGER NOT NULL)"),
    db.prepare("CREATE INDEX IF NOT EXISTS scores_date ON scores (date)"),
  ]);
  ready = true;
}

async function stats(db, date) {
  const d = await db.prepare("SELECT n, total, s0, s1, s2, s3, s4 FROM daily WHERE date = ?").bind(date).first();
  const h = await db.prepare("SELECT bucket, n FROM hist WHERE date = ?").bind(date).all();
  const hist = new Array(51).fill(0);
  for (const r of h.results) hist[r.bucket] = r.n;
  const sc = await db.prepare("SELECT total FROM scores WHERE date = ? ORDER BY rowid DESC LIMIT 300").bind(date).all();
  const scores = sc.results.map(r => r.total);
  if (!d) return { n: 0, avg: 0, slots: [0, 0, 0, 0, 0], hist, scores };
  return { n: d.n, avg: Math.round(d.total / d.n), slots: [d.s0, d.s1, d.s2, d.s3, d.s4].map(x => Math.round(x / d.n)), hist, scores };
}

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

// players use their own local date, so allow anything within about a day and a half of now
function dateOk(date) {
  if (typeof date !== "string" || !DATE.test(date)) return false;
  const t = Date.parse(date + "T12:00:00Z");
  return Number.isFinite(t) && Math.abs(Date.now() - t) < 40 * 3600 * 1000;
}

export async function onRequest({ request, env, params }) {
  const db = env.DB;
  if (!db) return json({ error: "The scoreboard database is not connected. Add a D1 binding named DB." }, 503);
  await setup(db);
  const path = [].concat(params.path || []).join("/");

  if (path === "stats" && request.method === "GET") {
    const date = new URL(request.url).searchParams.get("date") || "";
    if (!DATE.test(date)) return json({ error: "bad date" }, 400);
    return json(await stats(db, date));
  }

  if (path === "score" && request.method === "POST") {
    let b;
    try { b = await request.json(); } catch (e) { return json({ error: "bad request" }, 400); }
    const { date, device, total, pts } = b || {};
    const valid = dateOk(date) && typeof device === "string" && device.length >= 8 && device.length <= 64 &&
      Array.isArray(pts) && pts.length === 5 && pts.every(p => Number.isInteger(p) && p >= 0 && p <= 1000) &&
      Number.isInteger(total) && pts.reduce((a, c) => a + c, 0) === total;
    if (!valid) return json({ error: "invalid score" }, 400);
    // one result per device per day; a repeat just returns the stats
    const ins = await db.prepare("INSERT OR IGNORE INTO plays (date, device) VALUES (?, ?)").bind(date, device).run();
    if (ins.meta.changes === 1) {
      await db.batch([
        db.prepare("INSERT INTO daily (date, n, total, s0, s1, s2, s3, s4) VALUES (?, 1, ?, ?, ?, ?, ?, ?) " +
          "ON CONFLICT(date) DO UPDATE SET n = n + 1, total = total + excluded.total, s0 = s0 + excluded.s0, s1 = s1 + excluded.s1, " +
          "s2 = s2 + excluded.s2, s3 = s3 + excluded.s3, s4 = s4 + excluded.s4").bind(date, total, ...pts),
        db.prepare("INSERT INTO hist (date, bucket, n) VALUES (?, ?, 1) ON CONFLICT(date, bucket) DO UPDATE SET n = n + 1")
          .bind(date, Math.min(50, Math.floor(total / 100))),
        db.prepare("INSERT INTO scores (date, total) VALUES (?, ?)").bind(date, total),
      ]);
    }
    return json(await stats(db, date));
  }

  return json({ error: "not found" }, 404);
}
