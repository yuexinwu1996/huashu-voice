"""timeline.json -> subs.ass (1080x1920). Lines split at punctuation into <=15-char chunks, timed by char share."""
import json, re
TL = json.load(open("timeline.json", encoding="utf-8"))
HOT = ["Rakazo", "OpenMuse", "OpenDots", "Personal Agent", "扣1", "扣2", "扣3", "GitHub"]
MAXC = 15

def wlen(s):  # latin letters count half
    return sum(0.55 if ord(ch) < 128 else 1 for ch in s)

PUN = set("，。：、？！；")

def cw(seg):  # display width: trailing punctuation is dropped on screen
    return wlen(seg.rstrip("".join(PUN)))

def chunks(text):
    """Min-cost split: each chunk <= MAXC wide; prefer breaks after punctuation, never inside a latin word."""
    cs = list(text); n = len(cs); best = {n: (0.0, [])}
    for i in range(n - 1, -1, -1):
        cand = None
        for j in range(i + 1, n + 1):
            seg = "".join(cs[i:j])
            if cw(seg) > MAXC: break
            if j not in best or best[j] is None: continue
            pen = 10
            if j < n:
                if cs[j - 1] in PUN: pen += 0
                elif cs[j] in PUN: continue
                elif cs[j - 1].isascii() and cs[j].isascii() and (cs[j - 1].isalnum() or cs[j].isalnum()): pen += 100
                else: pen += 25
                if cw(seg) < 4: pen += 8
            c = (best[j][0] + pen, [j] + best[j][1])
            if cand is None or c[0] < cand[0]: cand = c
        best[i] = cand
    cuts = [0] + best[0][1]
    return ["".join(cs[a:b]) for a, b in zip(cuts, cuts[1:])]

def ts(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02d}:{s:05.2f}"

def style(s):
    s = re.sub(r"[，。、；：]$", "", s).strip().replace("，", "  ")
    for h in HOT: s = s.replace(h, r"{\c&H2672EF&}" + h + r"{\c&H1A1A1A&}")
    return s

ev, raw = [], []
for l in TL["lines"]:
    cs = chunks(l["sub"]); tot = sum(wlen(c) for c in cs); t = l["start"]; d = l["end"] - l["start"]
    for i, c in enumerate(cs):
        t1 = t + d * wlen(c) / tot
        end = t1 + (0.25 if i == len(cs) - 1 else 0)
        raw.append([max(0, t - 0.05), end, style(c)])
        t = t1
for i in range(len(raw) - 1): raw[i][1] = min(raw[i][1], raw[i + 1][0] - 0.02)
ev = [f"Dialogue: 0,{ts(a)},{ts(b)},Sub,,0,0,0,,{c}" for a, b, c in raw]
TAGS = {3: "01 · 团队型 Rakazo", 4: "02 · 管家型 OpenMuse", 5: "03 · 工作室型 OpenDots"}
B = json.load(open("specs/bounds.json"))
for c, t0, t1 in B:
    if c in TAGS: ev.append(f"Dialogue: 1,{ts(t0 + 2.2)},{ts(t1)},Tag,,0,0,0,,{{\\fad(250,0)}}{TAGS[c]}")
head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Tag,LXGW WenKai Medium,58,&H002672EF,&H002672EF,&H00FBFBFB,&H00FBFBFB,0,0,0,0,100,100,1,0,1,0,0,7,72,72,118,1
Style: Sub,Noto Sans CJK SC,84,&H001A1A1A,&H001A1A1A,&H00FBFBFB,&H64000000,1,0,0,0,100,100,1,0,1,7,0,2,40,40,380,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
open("subs.ass", "w", encoding="utf-8").write(head + "\n".join(ev) + "\n")
print(len(ev), "events")
