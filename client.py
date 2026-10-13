"""Run from Claude's workspace inside a clone of this repo. Talks to GitHub only (git push / git pull).

  python3 client.py check                                   # verify credentials + cloned voice status
  python3 client.py say  --lines lines.json --out vo/ [--rate 0] [--timeout 900]
  python3 client.py text "一句话" --out vo/                  # quick single line -> vo/l01.wav

lines.json: [{"id": "s01", "tts": "..."}]   (also accepts "text"; huashu/koubo line files work as-is)
Writes <out>/<id>.wav for every line plus <out>/manifest.json [{id, dur, sr}].
"""
import argparse, datetime, json, pathlib, secrets, shutil, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent
MAX_CHARS = 280  # Volcengine recommends < 300 chars per request


def git(*a, check=True):
    return subprocess.run(["git", "-C", str(ROOT), *a], check=check, capture_output=True, text=True)


def split_long(lines):
    out = []
    for ln in lines:
        text = ln.get("tts") or ln.get("text") or ""
        if len(text) <= MAX_CHARS:
            out.append({"id": ln["id"], "text": text}); continue
        parts, buf = [], ""
        for ch in text:
            buf += ch
            if ch in "。！？；" and len(buf) > MAX_CHARS * 0.6:
                parts.append(buf); buf = ""
        if buf: parts.append(buf)
        out += [{"id": f"{ln['id']}_{k+1:02d}", "text": p} for k, p in enumerate(parts)]
    return out


def submit(job):
    path = ROOT / "jobs" / f"{job['id']}.json"
    path.parent.mkdir(exist_ok=True)
    json.dump(job, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    git("pull", "--rebase", "-q", "origin", "main", check=False)
    git("add", str(path))
    git("commit", "-q", "-m", f"tts job {job['id']}")
    r = git("push", "-q", "origin", "HEAD:main", check=False)
    if r.returncode:
        sys.exit(f"git push failed: {r.stderr.strip()}")
    print(f"submitted job {job['id']} ({len(job.get('lines', []))} lines); waiting for GitHub Actions…", flush=True)


def wait(job_id, timeout):
    status = ROOT / "outputs" / job_id / "status.json"
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(10)
        git("pull", "--rebase", "-q", "origin", "main", check=False)
        if status.exists():
            return json.load(open(status, encoding="utf-8"))
        print(f"  …{int(time.time() - t0)}s", flush=True)
    sys.exit(f"timed out after {timeout}s — check the repo's Actions tab for job {job_id}")


def new_id(kind):
    return f"{datetime.datetime.now(datetime.timezone.utc):%Y%m%d-%H%M%S}-{kind}-{secrets.token_hex(2)}"


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    s = sub.add_parser("say"); s.add_argument("--lines", required=True); s.add_argument("--out", required=True)
    t = sub.add_parser("text"); t.add_argument("text"); t.add_argument("--out", required=True)
    for p in (s, t):
        p.add_argument("--rate", type=int, default=0, help="speech_rate -50..100 (0 = normal, 100 = 2x)")
        p.add_argument("--speaker", default="", help="override VOLC_SPEAKER_ID")
        p.add_argument("--model", default="seed-tts-2.0-expressive")
        p.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()

    if a.cmd == "check":
        job = {"id": new_id("check"), "kind": "check", "lines": [{"id": "probe", "text": "你好，这是一段声音复刻测试。"}]}
        submit(job); st = wait(job["id"], 600)
        print(json.dumps(st, ensure_ascii=False, indent=1))
        probe = ROOT / "outputs" / job["id"] / "probe.wav"
        if probe.exists(): print("probe audio:", probe)
        sys.exit(0 if st.get("ok") else 1)

    lines = [{"id": "l01", "text": a.text}] if a.cmd == "text" else json.load(open(a.lines, encoding="utf-8"))
    job = {"id": new_id("say"), "kind": "say", "speaker": a.speaker, "model": a.model, "speech_rate": a.rate,
           "sample_rate": 48000, "tone_fidelity": True, "lines": split_long(lines)}
    submit(job); st = wait(job["id"], a.timeout)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    man, bad = [], []
    for it in st.get("lines", []):
        if not it.get("ok"): bad.append(it); continue
        shutil.copy(ROOT / "outputs" / job["id"] / f"{it['id']}.wav", out / f"{it['id']}.wav")
        man.append({"id": it["id"], "dur": it["dur"], "sr": it["sr"]})
    json.dump(man, open(out / "manifest.json", "w"), ensure_ascii=False, indent=1)
    print(f"{len(man)} lines -> {out}")
    if st.get("error") or bad:
        print("FAILED:", json.dumps({"error": st.get("error"), "lines": bad}, ensure_ascii=False, indent=1))
        sys.exit(1)


if __name__ == "__main__":
    main()
