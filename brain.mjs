// Brain for nothing-agent (subscription version).
//
// Runs on the PC. Turns a spoken rojak command (text) into {intent, query}.
// Uses the Claude subscription (claude.ai OAuth) through the Agent SDK, so it
// spends your Pro usage, not API credits. Locked down on purpose: no tools, one
// turn, token-guarded. This is why the PC belongs in the loop (it holds the
// authenticated session; the phone cannot).
//
// Fail-soft: any error returns a safe {intent: unknown} so the phone always
// gets a valid answer.

import { createServer } from "node:http";
import { readFileSync, writeFileSync, copyFileSync, existsSync } from "node:fs";
import { query } from "@anthropic-ai/claude-agent-sdk";

const PORT = 8080;
const MODEL = "claude-opus-4-8";             // proven on the subscription; swap for a faster one later
const TOKEN = process.env.BRAIN_TOKEN || ""; // shared secret the phone must send as x-token

// Use the subscription, not API credits (same trick Grawn uses).
delete process.env.ANTHROPIC_API_KEY;
delete process.env.ANTHROPIC_AUTH_TOKEN;

const INTENTS = ["play_music", "navigate", "media", "volume", "unknown"];
const MAX_ACTIONS = 5;

const SYSTEM =
  "You turn a Malaysian rojak voice command (mixed Mandarin, English and Malay, " +
  "with local slang, often starting with the wake word 'nothing') into actions. " +
  "One command may hold several actions; keep them in the spoken order. " +
  'Reply with ONLY compact JSON: {"actions":[{"intent": <one of ' + JSON.stringify(INTENTS) +
  '>, "query": <the cleaned target>}, ...]}. Use "unknown" if nothing fits. Clean the ' +
  "query into its standard form (the real song, artist or place name), not the raw " +
  'speech. Going home is always the query "home". ' +
  'For "media" the query is exactly one of "pause", "play", "next", "previous". ' +
  'For "volume" the query is a signed step count like "-2" or "+2"; "小声一点"/"大声一点" ' +
  'without a number means 2 steps. Examples: "nothing帮我开下周杰伦的搁浅" -> ' +
  '{"actions":[{"intent":"play_music","query":"搁浅 周杰伦"}]}; ' +
  '"nothing去map search下回家的路" -> {"actions":[{"intent":"navigate","query":"home"}]}; ' +
  '"nothing go KLCC then play some Jay Chou" -> {"actions":[{"intent":"navigate","query":"KLCC"},' +
  '{"intent":"play_music","query":"周杰伦"}]}; "eh nothing小声一点" -> ' +
  '{"actions":[{"intent":"volume","query":"-2"}]}; "nothing next song lah" -> ' +
  '{"actions":[{"intent":"media","query":"next"}]}.';

function saved_names() {
  // Read per request so edits to places.txt apply without a restart.
  try {
    return readFileSync(new URL("./places.txt", import.meta.url), "utf8").split("\n")
      .filter((l) => l.trim() && !l.trim().startsWith("#") && l.includes("="))
      .map((l) => l.split("=")[0].trim());
  } catch { return []; }
}

function system_prompt() {
  const names = saved_names();
  return names.length
    ? SYSTEM + " The user's saved places are " + JSON.stringify(names) + ". If a navigate " +
      "target means one of them (any script, language or nickname), the query must be that exact name."
    : SYSTEM;
}

function coerce(out, text) {
  // Model output is untrusted. Keep only valid {intent, query} items, else one unknown.
  const actions = (Array.isArray(out?.actions) ? out.actions : [])
    .filter((a) => a && INTENTS.includes(a.intent) && typeof a.query === "string")
    .map((a) => ({ intent: a.intent, query: a.query }))
    .slice(0, MAX_ACTIONS); // safe stop: a runaway reply cannot queue a long chain of phone actions
  return { actions: actions.length ? actions : [{ intent: "unknown", query: text.trim() }] };
}

async function parse(text) {
  try {
    const q = query({
      prompt: text,
      options: {
        systemPrompt: system_prompt(),
        allowedTools: [],   // locked: the brain cannot run bash or touch files
        maxTurns: 1,
        model: MODEL,
        effort: "low",
      },
    });
    let raw = "";
    for await (const msg of q) {
      if (msg.type === "result" && msg.subtype === "success" && !msg.is_error) raw = msg.result;
    }
    return coerce(JSON.parse(raw.trim()), text);
  } catch (e) {
    return { actions: [{ intent: "unknown", query: text.trim() }], error: String(e?.message || e) };
  }
}

// Config files the phone page may read and write. Nothing else on disk is reachable.
const EDITABLE = ["places.txt"];
const MAX_BODY = 64 * 1024;
const here = (name) => new URL("./" + name, import.meta.url);

function read_body(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (c) => {
      body += c;
      if (body.length > MAX_BODY) { req.destroy(); reject(new Error("body too large")); }
    });
    req.on("end", () => resolve(body));
    req.on("error", reject);
  });
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://local");
  const send = (code, body, type = "text/plain; charset=utf-8") => {
    res.writeHead(code, { "content-type": type }); res.end(body);
  };
  // The page itself holds no data; everything below needs the token.
  if (req.method === "GET" && url.pathname === "/") return send(200, readFileSync(here("editor.html")), "text/html; charset=utf-8");
  if (TOKEN && req.headers["x-token"] !== TOKEN) return send(401, "bad token");
  try {
    if (req.method === "POST" && url.pathname === "/parse") {
      const text = JSON.parse(await read_body(req)).text;
      if (typeof text !== "string") return send(400, 'expected {"text": "..."}');
      return send(200, JSON.stringify(await parse(text)), "application/json");
    }
    if (req.method === "GET" && url.pathname === "/files") return send(200, JSON.stringify(EDITABLE), "application/json");
    if (url.pathname === "/file") {
      const name = url.searchParams.get("name");
      if (!EDITABLE.includes(name)) return send(404, "not editable");
      if (req.method === "GET") return send(200, existsSync(here(name)) ? readFileSync(here(name)) : "");
      if (req.method === "PUT") {
        const body = await read_body(req);
        if (existsSync(here(name))) copyFileSync(here(name), here(name + ".bak")); // one-step undo
        writeFileSync(here(name), body);
        return send(200, "saved");
      }
    }
    send(404, "");
  } catch (e) {
    send(400, String(e?.message || e));
  }
});

// Default 127.0.0.1. To reach it from the phone set BRAIN_HOST (LAN or Tailscale IP); never without a token.
const HOST = process.env.BRAIN_HOST || "127.0.0.1";
if (HOST !== "127.0.0.1" && !TOKEN) {
  console.error(`refusing to listen on ${HOST} without BRAIN_TOKEN`);
  process.exit(1);
}
server.listen(PORT, HOST, () =>
  console.log(`brain (subscription) on ${HOST}:${PORT}  model=${MODEL}  token=${TOKEN ? "on" : "OFF (set BRAIN_TOKEN!)"}`));
