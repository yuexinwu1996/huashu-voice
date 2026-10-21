# video_kit — huashu-art-motion 竖屏白板口播片（本人声音）

上一支片子（Personal Agent 开源平替，2026-10）跑通的流程，下次直接复用。

1. 写口播 `lines.json`：`[{"id","ch"(章节),"sub"(字幕原文),"tts"(念法，数字写汉字/英文名加空格)}]`
2. 配音：`python3 ../client.py say --lines lines.json --out vo_clone`（走本人复刻音色）
3. `VO=vo_clone python3 assemble_audio.py` → `vo.wav` + `timeline.json`（句间 0.28s、章节间 0.65s）
4. 改 `example/build_specs.py` 里的 CH 表：每个 cue 挂到某句的关键词上（`P("s07","关键词")`），出 `specs/ch*.json`（1080×1920，safe top 200 / bottom 540）
5. 把 `y3_whiteboard.portrait.js` 覆盖到 huashu 工程的 `clips/y3_whiteboard.js`（竖屏大字号、单栏、平移不切字），`render.py --spec` 渲每章
6. 改 `subs_template.py` 的 HOT（橙色高亮词）和 TAGS（章节角标），生成 `subs.ass`；字体用霞鹜文楷 ttf（从 engine/lib/fonts 的 woff 转）
7. concat → ffmpeg 烧字幕 + loudnorm -16 LUFS → 成片；跑 `qa.py --spec` 和 `subzone_gate.py`，再派独立 agent 审片
8. `asr.py` 用于离线核对配音念没念错（英文名识别差，忽略）
