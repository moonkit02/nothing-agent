"""Brain for nothing-agent.

Runs on the PC. Turns a spoken rojak command (already transcribed to text) into
a structured action {intent, query} using the Claude API.

Fail-soft on purpose: if the Anthropic SDK or credentials are missing, or the
model returns something unexpected, it degrades to a safe {intent: unknown}
instead of crashing. The phone always gets a valid JSON answer.

Binds to localhost: a tunnel (cloudflared/ngrok) forwards to 127.0.0.1, so the
port stays off the wider network.
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080
MODEL = "claude-opus-5-5"  # swap to "claude-haiku-5-5" for a faster, cheaper assistant

# Closed set of actions. REPLACE / extend with your real intents.
INTENTS = ["play_music", "navigate", "unknown"]

# Real rojak commands from the user. Double as the STT test set. Add more over time.
EXAMPLES = [
    {"text": "nothing帮我开下周杰伦的搁浅", "intent": "play_music",
     "query": "搁浅 周杰伦"},
    {"text": "nothing去map search下回家的路", "intent": "navigate",
     "query": "home"},
]

SYSTEM = (
    "You turn a Malaysian rojak voice command (mixed Mandarin, English and Malay, "
    "with local slang) into one action. Reply with ONLY compact JSON: "
    '{"intent": <one of %s>, "query": <the cleaned target>}. '
    "Use 'unknown' if nothing fits. Clean the query into its standard form (the "
    "real song, artist or place name), not the raw speech."
) % INTENTS

def _few_shot():
    # Prior turns that show the model the exact JSON shape we want back.
    turns = []
    for e in EXAMPLES:
        turns.append({"role": "user", "content": e["text"]})
        turns.append({"role": "assistant",
                      "content": json.dumps({"intent": e["intent"], "query": e["query"]})})
    return turns

def _stub(text):
    # Offline fallback when the SDK or a key is not available.
    return {"intent": "unknown", "query": text.strip()}

def _coerce(out, text):
    # Model output is untrusted. Keep only a valid intent + query, else unknown.
    if not isinstance(out, dict) or out.get("intent") not in INTENTS or "query" not in out:
        return {"intent": "unknown", "query": text.strip()}
    return {"intent": out["intent"], "query": out["query"]}

def parse(text):
    try:
        import anthropic
    except ImportError:
        return _stub(text)
    try:
        client = anthropic.Anthropic()  # key from env or `ant auth login` profile
        resp = client.messages.create(
            model=MODEL,
            max_tokens=256,
            output_config={"effort": "low"},  # small, fast classification
            system=SYSTEM,
            messages=_few_shot() + [{"role": "user", "content": text}],
        )
        raw = next((b.text for b in resp.content if b.type == "text"), "")
        return _coerce(json.loads(raw), text)
    except Exception as e:
        # Network, auth or bad JSON: fail soft so the phone still gets an answer.
        return {"intent": "unknown", "query": text.strip(), "error": str(e)}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/parse":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            text = json.loads(self.rfile.read(length))["text"]
        except (ValueError, KeyError):
            self.send_error(400, 'expected JSON {"text": "..."}')
            return
        body = json.dumps(parse(text)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass  # stay quiet

def _selfcheck():
    assert _stub("  hi ") == {"intent": "unknown", "query": "hi"}
    assert _coerce({"intent": "play_music", "query": "x"}, "raw") == {"intent": "play_music", "query": "x"}
    assert _coerce({"intent": "bogus", "query": "x"}, "raw text")["intent"] == "unknown"
    assert _coerce("not a dict", "fallback")["query"] == "fallback"
    assert len(_few_shot()) == 2 * len(EXAMPLES)
    print("ok")

if __name__ == "__main__":
    if "--check" in sys.argv:
        _selfcheck()
    else:
        # ponytail: --lan binds all interfaces for same-WiFi phone testing.
        # Default stays localhost-only (use a tunnel for the real path).
        host = "0.0.0.0" if "--lan" in sys.argv else "127.0.0.1"
        print(f'brain on {host}:{PORT}  model={MODEL}  (POST /parse {{"text": "..."}})')
        HTTPServer((host, PORT), Handler).serve_forever()
