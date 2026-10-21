"""timeline.json -> one y3_whiteboard clip spec per chapter (vertical 1080x1920).
Cues are anchored to a keyword inside a spoken line: at = line.start + dur*idx/len + DELAY (writing trails speech ~0.3–0.5s).
"""
import json, os
TL = json.load(open("timeline.json", encoding="utf-8"))
LN = {l["id"]: l for l in TL["lines"]}
DELAY, PRE = 0.3, 0.2          # write lag after keyword; cut happens PRE s before a chapter's first line

def at(sid, kw=None, shift=0.0):
    l = LN[sid]; s = l["sub"]; d = l["end"] - l["start"]
    i = 0 if kw is None else len(s) if kw == "END" else s.index(kw)
    return l["start"] + d * i / len(s) + (0 if kw in (None, "END") else DELAY) + shift

T = lambda *a, **k: ("title", at(*a, **k))
P = lambda *a, **k: ("point", at(*a, **k))
D = lambda *a, **k: ("draw", at(*a, **k))
H = lambda *a, **k: ("highlight", at(*a, **k))

CH = {
 1: [(T("s01"), "AI助理，非得花钱订？", None),
     (P("s01", "GitHub"), "GitHub 已有平替", None),
     (D("s01", "开源平替"), "开源 · 代码免费", "stack"),
     (P("s02", "三个"), "今天讲 3 个", None),
     (P("s02", "一人公司"), "一人公司·老板必看", None),
     (H("s02", "值得"), None, {"index": 0})],
 2: [(T("s03"), "Personal Agent？", None),
     (P("s03", "可不只是"), "不只是陪你聊天", None),
     (D("s03", "聊天"), "聊天只是入口", "chat"),
     (P("s04", "自己的电脑"), "它有自己的电脑", None),
     (D("s04", "浏览器"), "浏览器·命令·文件", "screen"),
     (P("s05"), "你下班它还在干活", None),
     (D("s05", "还在干活"), "一直在线", "clock"),
     (H("s05", "END", 0.15), None, {"index": 2})],
 3: [(T("s06", "团队型"), "团队型 Rakazo", None),
     (P("s06", "对标"), "对标 Grok Bot", None),
     (P("s07", "好几个"), "多个机器人分工", None),
     (D("s07", "一个查资料"), "查资料 → 写稿", "network"),
     (P("s07", "互相转交"), "活儿能互相转交", None),
     (P("s08"), "手机电脑随时指挥", None),
     (D("s08", "服务器"), "放在服务器上", "screen"),
     (P("s08", "24小时"), "24 小时不下班", None),
     (H("s08", "不下班"), None, {"index": 4, "style": "underline"})],
 4: [(T("s09", "管家型"), "管家型 OpenMuse", None),
     (P("s09", "对标"), "对标 Meta 的 Muse", None),
     (P("s10"), "查资料 · 邮件 · PDF", None),
     (P("s10", "任务进度"), "任务进度一目了然", None),
     (D("s10", "一目了然"), "进度可见", "chart"),
     (P("s11", "帮你"), "帮你盯网页", None),
     (D("s11", "价格到线"), "到线就提醒", "target"),
     (H("s11", "马上提醒"), None, {"index": 3})],
 5: [(T("s12", "工作室型"), "工作室型 OpenDots", None),
     (P("s12", "对标"), "对标 OpenAI 的 Dots", None),
     (P("s13", "工作室"), "一间 AI 工作室", None),
     (D("s13", "研究助手"), "研究 / 写作助手", "person"),
     (P("s13", "各管各"), "各管各的权限", None),
     (D("s13", "权限"), "按需授权", "gear"),
     (P("s14"), "先交草稿再审核", None),
     (D("s14", "审核通过"), "你说了算", "check"),
     (P("s14", "Slack"), "还能接进 Slack", None),
     (H("s14", "END", 0.1), None, {"index": 3})],
 6: [(T("s15"), "提醒一句", None),
     (P("s15", "早期"), "大多还在早期", None),
     (P("s15", "部署"), "要自己部署接模型", None),
     (D("s15", "接模型"), "要动手配置", "gear"),
     (P("s15b", "服务器"), "服务器模型费自理", None),
     (P("s16"), "适合有技术同事", None),
     (D("s16", "技术同事"), "或者你自己", "person"),
     (P("s16", "愿意折腾"), "或爱折腾的老板", None),
     (H("s15b", "还得"), None, {"index": 2})],
 7: [(T("s17"), "你先招哪个AI员工？", None),
     (P("s18", "团队型"), "扣1 → Rakazo", None),
     (P("s18", "管家型"), "扣2 → OpenMuse", None),
     (P("s18", "工作室型"), "扣3 → OpenDots", None),
     (H("s18", "END", 0.05), None, {"target": "title", "style": "underline"}),
     (P("s19"), "地址见评论区置顶", None),
],
}

os.makedirs("specs", exist_ok=True)
chs = sorted(CH); bounds = []
for k, c in enumerate(chs):
    first = [l for l in TL["lines"] if l["ch"] == c][0]
    t0 = 0 if k == 0 else first["start"] - PRE
    t1 = TL["duration"] if k == len(chs) - 1 else [l for l in TL["lines"] if l["ch"] == chs[k + 1]][0]["start"] - PRE
    bounds.append((c, round(t0, 3), round(t1, 3)))
    cues = []
    for (kind, a), text, extra in CH[c]:
        q = {"at": round(max(0.0, a - t0), 3), "kind": kind}
        if text: q["text"] = text
        if kind == "draw": q["data"] = {"icon": extra}
        if kind == "highlight": q["data"] = extra
        cues.append(q)
    spec = {"grammar": "y3_whiteboard", "duration": round(t1 - t0, 3), "fps": 30, "width": 1080, "height": 1920,
            "safe": {"top": 200, "bottom": 540, "fill": "#FBFBFB"}, "cues": cues}
    json.dump(spec, open(f"specs/ch{c}.json", "w"), ensure_ascii=False, indent=1)
json.dump(bounds, open("specs/bounds.json", "w"))
for b in bounds: print(b)
