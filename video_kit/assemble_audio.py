"""Trim each TTS line, lay them on one track with gaps, write vo.wav + timeline.json."""
import json, os, numpy as np, soundfile as sf
L = json.load(open("lines.json", encoding="utf-8"))
LEAD, GAP_IN, GAP_CH, TAIL = 0.4, 0.28, 0.65, 1.6
parts, tl, t, prev_ch, sr = [], [], LEAD, None, None
for l in L:
    x, sr = sf.read(f"{os.environ.get('VO', 'vo')}/{l['id']}.wav", dtype="float32")
    env = np.abs(x) > 0.01
    i0 = max(0, np.argmax(env) - int(0.03 * sr)); i1 = min(len(x), len(x) - np.argmax(env[::-1]) + int(0.06 * sr))
    x = x[i0:i1]
    if prev_ch is not None: t += GAP_CH if l["ch"] != prev_ch else GAP_IN
    tl.append({**l, "start": round(t, 3), "end": round(t + len(x) / sr, 3)})
    parts.append((t, x)); t += len(x) / sr; prev_ch = l["ch"]
total = t + TAIL
y = np.zeros(int(total * sr) + 1, dtype="float32")
for s, x in parts: i = int(round(s * sr)); y[i:i + len(x)] += x
y = y / max(1e-6, np.abs(y).max()) * 0.89
sf.write("vo.wav", y, sr, subtype="PCM_16")
json.dump({"duration": round(total, 3), "lines": tl}, open("timeline.json", "w"), ensure_ascii=False, indent=1)
print("total", round(total, 2))
for c in sorted(set(l["ch"] for l in tl)):
    a = [l for l in tl if l["ch"] == c]; print(c, a[0]["start"], a[-1]["end"])
