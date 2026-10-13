# huashu-voice

用我本人的豆包声音复刻音色合成口播，给 Claude（huashu-art-motion 等配音流程）自动调用。

**工作方式**：Claude 往 `jobs/` 推一个任务文件 → GitHub Actions 用仓库 Secrets 里的凭证调用火山引擎合成 → 把 WAV 提交回 `outputs/<任务id>/` → Claude `git pull` 取回。凭证只存在 GitHub 加密 Secrets 里，不进聊天、不进代码。

## 一次性设置（仓库主人做）

Settings → Secrets and variables → Actions → **New repository secret**：

| Secret | 填什么 |
|---|---|
| `VOLC_API_KEY` | 新版控制台「API Key 管理」里的 Key（用新版控制台就只填这个） |
| `VOLC_APP_ID` / `VOLC_ACCESS_TOKEN` | 旧版控制台的 APP ID 和 Access Token（没有 API Key 时用这两个代替） |
| `VOLC_SPEAKER_ID` | 声音复刻里的音色 ID，`S_` 开头 |

可选 Variable：`VOLC_TTS_RESOURCE_ID`（默认 `seed-icl-2.0`，声音复刻 2.0 合成）。

## 用法（Claude 在工作区里）

```sh
python3 client.py check                                  # 验凭证 + 音色状态，顺带合成一句试听
python3 client.py say --lines lines.json --out vo/       # 批量合成，lines.json: [{"id":"s01","tts":"..."}]
python3 client.py text "一句话" --out vo/
```

`--rate` 语速 -50…100（0 正常，100 = 2 倍速）。单句超过 280 字会自动切分。每次合成大约 1–2 分钟（含 Actions 排队）。

## 注意

- 仓库保持 **私有**：任务文件里有口播原文，`outputs/` 里有你的声音。
- `outputs/` 会越积越大，隔段时间可以删掉旧目录。
- 合成按火山引擎计费；失败原因写在 `outputs/<id>/status.json`（不含凭证）。
