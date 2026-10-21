"""Transcribe wavs with offline paraformer (16k) and report median F0 — used to vet TTS voices.
usage: python3 asr.py a.wav [b.wav ...]
"""
import sys, numpy as np, soundfile as sf, sherpa_onnx
D = "/home/claude/tts/sherpa-onnx-paraformer-zh-2024-03-09"
rec = sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=f"{D}/model.int8.onnx", tokens=f"{D}/tokens.txt", num_threads=4)

def f0(x, sr):
    fr, hop, vals = int(sr * 0.04), int(sr * 0.02), []
    for i in range(0, len(x) - fr, hop):
        w = x[i:i + fr]
        if np.sqrt((w ** 2).mean()) < 0.02: continue
        ac = np.correlate(w, w, "full")[fr - 1:]
        lo, hi = int(sr / 400), int(sr / 70)
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]: vals.append(sr / k)
    return float(np.median(vals)) if vals else 0

for p in sys.argv[1:]:
    x, sr = sf.read(p, dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    if sr != 16000:
        n = int(len(x) * 16000 / sr); x16 = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype("float32")
    else: x16 = x
    s = rec.create_stream(); s.accept_waveform(16000, x16); rec.decode_stream(s)
    print(f"{p}\tF0={f0(x, sr):.0f}Hz\t{s.result.text}")
