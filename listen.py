"""Listen service: phone mic audio -> speaker check -> speech-to-text -> wake word -> brain -> act.sh.

Runs on the PC next to brain.mjs (which proxies POST /listen here). Localhost only.
Body: raw little-endian float32 mono PCM at 16 kHz (one utterance, cut by the page's VAD).

  BRAIN_TOKEN    same token as brain.mjs (used to call /parse)
  BRAIN_HOST     where brain.mjs listens (default 127.0.0.1)
  PHONE_SERIAL   adb serial for act.sh (e.g. 100.99.1.104:5555)
  SPEAKER_ENFORCE=1  reject commands that fail the voiceprint (default: shadow mode, score is logged only)

Every utterance is logged to voice-samples/listen-log.jsonl (gitignored: transcripts, scores).
"""
import importlib.util
import json
import os
import re
import subprocess
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import sherpa_onnx

HERE = Path(__file__).parent
PORT = 8081
MAX_BODY = 16000 * 4 * 15  # 15 s of float32 audio
# Speech-to-text spells "Apollo" many ways (seen: 啊菠萝, 啊，菠萝, 阿波路, "Apooos", "Abo set…").
# Needs the 啊/阿 start, so plain 菠萝 (pineapple) in normal talk does not wake it.
# "abo"/"apo" alone only counts at the very start of the utterance (where the wake word is said).
WAKE = re.compile(r"[啊阿哎][\s,，、.。!！]*[波菠播玻拨][罗萝路洛落啰羅蘿]|\bap+o+l+o+s?\b|\bapo{2,}s?\b"
                  r"|^\W*(hey\s*)?a[bp]+o+\b", re.I)
BASH = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else "bash"
SERIAL = os.environ.get("PHONE_SERIAL", "")
TOKEN = os.environ.get("BRAIN_TOKEN", "")
BRAIN = f"http://{os.environ.get('BRAIN_HOST', '127.0.0.1')}:8080/parse"
ENFORCE = os.environ.get("SPEAKER_ENFORCE") == "1"
LOG = HERE / "voice-samples" / "listen-log.jsonl"

# Reuse the voiceprint code from the experiment script (its file name has a dash, so load it by path).
_spec = importlib.util.spec_from_file_location("voice_test", HERE / "voice-test.py")
vt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vt)

SV = HERE / "models" / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
asr = sherpa_onnx.OfflineRecognizer.from_sense_voice(
    model=str(SV / "model.int8.onnx"), tokens=str(SV / "tokens.txt"), language="auto", use_itn=True, num_threads=4)
extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
    sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(vt.CHECK_MODEL), num_threads=2))
prints = vt.voiceprints({p.name: vt.embed(extractor, vt.load_audio(p)) for p in sorted(vt.SAMPLES.glob("enrol-*"))})
act_lock = threading.Lock()  # one phone, one action at a time


def transcribe(samples):
    stream = asr.create_stream()
    stream.accept_waveform(vt.RATE, samples)
    asr.decode_stream(stream)
    return stream.result.text.strip()


def parse(text):
    req = urllib.request.Request(BRAIN, data=json.dumps({"text": text}).encode(),
                                 headers={"x-token": TOKEN, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["actions"]


def act(intent, query):
    if intent == "unknown":
        return "skipped: unknown"
    with act_lock:
        r = subprocess.run([BASH, "act.sh", SERIAL, intent, query], cwd=HERE,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
    return (r.stdout or r.stderr).strip() + ("" if r.returncode == 0 else f" (exit {r.returncode})")


def handle(samples):
    t0 = time.time()
    out = {"seconds": round(len(samples) / vt.RATE, 1)}
    score, style = vt.best_match(vt.embed(extractor, samples), prints)
    out.update(score=round(score, 3), style=style, is_me=score >= vt.THRESHOLD)
    out["text"] = transcribe(samples)
    out["wake"] = bool(WAKE.search(out["text"]))
    if not out["wake"]:
        out["result"] = "ignored (no wake word)"
    elif ENFORCE and not out["is_me"]:
        out["result"] = "blocked: voice does not match"
    else:
        out["actions"] = parse(out["text"])
        out["done"] = [act(a["intent"], a["query"]) for a in out["actions"]]
        out["result"] = "done"
    out["ms"] = int((time.time() - t0) * 1000)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), **out}, ensure_ascii=False) + "\n")
    return out


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        if self.path != "/listen" or not 0 < n <= MAX_BODY or n % 4:
            return self.reply(400, {"error": "expected float32 PCM, up to 15 s"})
        try:
            self.reply(200, handle(np.frombuffer(self.rfile.read(n), dtype="<f4").copy()))
        except Exception as e:
            self.reply(500, {"error": str(e)})

    def reply(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"listen on 127.0.0.1:{PORT}  voiceprints={sorted(prints)}  "
          f"speaker={'ENFORCE' if ENFORCE else 'shadow'}  phone={SERIAL or 'NOT SET'}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
