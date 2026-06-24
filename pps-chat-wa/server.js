/**
 * pps-chat-wa — isolated per-user WhatsApp link service for the bitumen dashboard.
 *
 * COMPLETELY SEPARATE from the bulk `whatsapp-server` (/opt/whatsapp-dashboard):
 * own dir, own pm2 app, own port, own sessions, own node_modules. It never imports
 * or touches the bulk system.
 *
 * Each dashboard user links THEIR OWN WhatsApp via QR. The service:
 *   - serves the QR + connection status (the dashboard shows it)
 *   - writes every inbound 1:1 customer message to /opt/pps-bitumen/wa_inbound.jsonl
 *     (the dashboard drains it into chat_messages)
 *   - sends approved replies from that user's linked number
 *
 * Bound to 127.0.0.1 only + shared-secret token → only the local dashboard can call it.
 */
const fs = require("fs");
const path = require("path");
const express = require("express");
const qrcode = require("qrcode");
const { Client, LocalAuth } = require("whatsapp-web.js");

const PORT = parseInt(process.env.PORT || "8530", 10);
const SESSIONS_DIR = path.join(__dirname, ".sessions");
const INBOUND = process.env.PPS_INBOUND || "/opt/pps-bitumen/wa_inbound.jsonl";
const TOKEN_FILE = path.join(__dirname, ".token");

function readToken() {
  try { return fs.readFileSync(TOKEN_FILE, "utf8").trim(); } catch (_) { return process.env.PPS_CHATWA_TOKEN || ""; }
}
const TOKEN = readToken();

if (!fs.existsSync(SESSIONS_DIR)) fs.mkdirSync(SESSIONS_DIR, { recursive: true });

// user -> { client, status, number, qr }
const clients = new Map();

function appendInbound(obj) {
  try { fs.appendFileSync(INBOUND, JSON.stringify(obj) + "\n"); }
  catch (e) { console.error("[inbound] append failed:", e.message); }
}

function onMessage(user, msg) {
  try {
    if (!msg || msg.fromMe) return;
    const from = msg.from || "";
    if (!from.endsWith("@c.us")) return;            // 1:1 only — skip groups (@g.us) / status
    appendInbound({
      user,
      phone: from.replace("@c.us", ""),
      name: (msg._data && msg._data.notifyName) || "",
      text: msg.body || "",
      ts: new Date().toISOString(),
    });
  } catch (e) { console.error("[onMessage]", e.message); }
}

function makeClient(user) {
  const st = { client: null, status: "init", number: null, qr: null };
  const client = new Client({
    authStrategy: new LocalAuth({ clientId: user, dataPath: SESSIONS_DIR }),
    puppeteer: {
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    },
  });
  st.client = client;
  client.on("qr", async (qr) => { try { st.qr = await qrcode.toDataURL(qr); st.status = "qr"; } catch (e) { console.error(e.message); } });
  client.on("authenticated", () => { st.status = "authenticated"; st.qr = null; });
  client.on("auth_failure", (m) => { st.status = "auth_failure"; console.error("[auth_failure]", user, m); });
  client.on("ready", () => {
    st.status = "connected"; st.qr = null;
    try { st.number = (client.info && client.info.wid && client.info.wid.user) || null; } catch (_) {}
    console.log(`[ready] ${user} -> ${st.number}`);
  });
  client.on("disconnected", (r) => { st.status = "disconnected"; st.number = null; console.log(`[disconnected] ${user}: ${r}`); });
  client.on("message", (msg) => onMessage(user, msg));
  client.initialize().catch((e) => { st.status = "error"; console.error("[init]", user, e.message); });
  clients.set(user, st);
  return st;
}

function publicState(st) {
  if (!st) return { status: "idle" };
  return { status: st.status, number: st.number, qr: st.qr };
}

// Re-link users that already have a saved session (no QR needed on restart).
function autoInit() {
  try {
    for (const d of fs.readdirSync(SESSIONS_DIR)) {
      const m = d.match(/^session-(.+)$/);     // LocalAuth dirs are session-<clientId>
      if (m && !clients.has(m[1])) { console.log("[autoInit]", m[1]); makeClient(m[1]); }
    }
  } catch (e) { console.error("[autoInit]", e.message); }
}

// ── HTTP API (localhost + token only) ──
const app = express();
app.use(express.json({ limit: "256kb" }));
app.use((req, res, next) => {
  if (req.path === "/health") return next();
  if ((req.headers["x-token"] || "") !== TOKEN) return res.status(401).json({ ok: false, error: "unauthorized" });
  next();
});

app.get("/health", (_req, res) => res.json({ ok: true, users: clients.size }));

app.get("/status", (req, res) => {
  const user = String(req.query.user || "");
  if (!user) return res.status(400).json({ ok: false, error: "user required" });
  res.json({ ok: true, ...publicState(clients.get(user)) });
});

app.post("/link/start", (req, res) => {
  const user = String((req.body && req.body.user) || "");
  if (!user) return res.status(400).json({ ok: false, error: "user required" });
  let st = clients.get(user);
  if (!st) st = makeClient(user);
  res.json({ ok: true, ...publicState(st) });
});

app.post("/unlink", async (req, res) => {
  const user = String((req.body && req.body.user) || "");
  const st = clients.get(user);
  if (st && st.client) { try { await st.client.logout(); } catch (_) {} try { await st.client.destroy(); } catch (_) {} }
  clients.delete(user);
  try { fs.rmSync(path.join(SESSIONS_DIR, `session-${user}`), { recursive: true, force: true }); } catch (_) {}
  res.json({ ok: true, status: "idle" });
});

app.post("/send", async (req, res) => {
  const { user, phone, text } = req.body || {};
  const st = clients.get(String(user || ""));
  if (!st || st.status !== "connected" || !st.client) return res.status(409).json({ ok: false, error: "not connected" });
  try {
    const chatId = String(phone).replace(/\D/g, "") + "@c.us";
    await st.client.sendMessage(chatId, String(text || ""));
    res.json({ ok: true, number: st.number });
  } catch (e) { res.status(500).json({ ok: false, error: e.message }); }
});

app.listen(PORT, "127.0.0.1", () => {
  console.log(`pps-chat-wa listening on 127.0.0.1:${PORT} (inbound -> ${INBOUND})`);
  autoInit();
});
