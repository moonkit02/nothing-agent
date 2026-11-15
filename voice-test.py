"""Speaker-verification experiment: does a model tell my voice apart from others?

Usage: .venv/Scripts/python voice-test.py              compare all clips in voice-samples/
       .venv/Scripts/python voice-test.py <clip>       PASS/REJECT one new clip (3D-Speaker only)
  enrol-*  -> my voiceprints: one per style (enrol-soft-*, enrol-low-*, enrol-high-*; everything
              else is "normal"). A clip's score is its best match, so styles are not blurred together.
  me-*     -> should score HIGH against it
  other-*  -> should score LOW
Prints per-clip cosine scores for each model in models/, and whether one threshold separates them.
"""
import re
import sys
from pathlib import Path

import av
import numpy as np
import sherpa_onnx

HERE = Path(__file__).parent
SAMPLES = HERE / "voice-samples"
MODELS = sorted((HERE / "models").glob("*.onnx"))
CHECK_MODEL = HERE / "models" / "3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx"
THRESHOLD = 0.54  # from the 2026-11-14 run: me 0.619..0.768, brother 0.318..0.464
RATE = 16000


def load_audio(path):
    # Decode any format (the phone records .aac) to 16 kHz mono float32.
    # Skip broken packets (the recorder leaves some) instead of failing the whole clip.
    chunks, bad = [], 0
    with av.open(str(path)) as container:
        resampler = av.AudioResampler(format="flt", layout="mono", rate=RATE)
        for packet in container.demux(audio=0):
            try:
                frames = packet.decode()
            except av.error.InvalidDataError:
                bad += 1
                continue
            for frame in frames:
                chunks += [f.to_ndarray().reshape(-1) for f in resampler.resample(frame)]
        chunks += [f.to_ndarray().reshape(-1) for f in resampler.resample(None)]
    if bad:
        print(f"  {path.name}: skipped {bad} broken packet(s)")
    return np.concatenate(chunks)


def embed(extractor, samples):
    stream = extractor.create_stream()
    stream.accept_waveform(sample_rate=RATE, waveform=samples)
    stream.input_finished()
    v = np.array(extractor.compute(stream))
    return v / np.linalg.norm(v)


def style_of(name):
    # enrol-soft-1 -> soft; enrol-1 and enrol-long-me -> normal
    m = re.match(r"enrol-([a-z]+)-", name)
    return m.group(1) if m and m.group(1) != "long" else "normal"


def voiceprints(vecs):
    groups = {}
    for n, v in vecs.items():
        if n.startswith("enrol-"):
            groups.setdefault(style_of(n), []).append(v)
    return {s: (lambda m: m / np.linalg.norm(m))(np.mean(vs, axis=0)) for s, vs in groups.items()}


def best_match(vec, prints):
    # (score, style) of the closest voiceprint
    return max((float(vec @ p), s) for s, p in prints.items())


def check(clip):
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
        sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(CHECK_MODEL), num_threads=2))
    prints = voiceprints({p.name: embed(extractor, load_audio(p)) for p in sorted(SAMPLES.glob("enrol-*"))})
    samples = load_audio(clip)
    score, style = best_match(embed(extractor, samples), prints)
    verdict = "PASS (you)" if score >= THRESHOLD else "REJECT (not you)"
    print(f"{clip.name}  {len(samples) / RATE:.1f}s  score {score:.3f} ({style})  threshold {THRESHOLD}  -> {verdict}")


def main():
    if len(sys.argv) > 1:
        return check(Path(sys.argv[1]))
    clips = {p.name: load_audio(p) for p in sorted(SAMPLES.iterdir()) if p.is_file()}
    print(f"{len(clips)} clips: " + ", ".join(f"{n} {len(a) / RATE:.1f}s" for n, a in clips.items()))
    for model in MODELS:
        extractor = sherpa_onnx.SpeakerEmbeddingExtractor(
            sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(model), num_threads=2))
        vecs = {n: embed(extractor, a) for n, a in clips.items()}
        prints = voiceprints(vecs)

        print(f"\n=== {model.name}  voiceprints: {', '.join(sorted(prints))}")
        matches = {n: best_match(v, prints) for n, v in vecs.items() if not n.startswith("enrol-")}
        for n, (s, style) in sorted(matches.items(), key=lambda kv: -kv[1][0]):
            print(f"  {s:6.3f}  {'ME   ' if n.startswith('me-') else 'OTHER'}  {style:7}  {n}")
        me = [s for n, (s, _) in matches.items() if n.startswith("me-")]
        other = [s for n, (s, _) in matches.items() if n.startswith("other-")]
        gap = min(me) - max(other)
        print(f"  me: {min(me):.3f}..{max(me):.3f}   other: {min(other):.3f}..{max(other):.3f}   "
              f"gap: {gap:+.3f}  -> {'SEPARATED' if gap > 0 else 'OVERLAP'}")


if __name__ == "__main__":
    main()
