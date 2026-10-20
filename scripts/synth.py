"""Runs inside GitHub Actions. Processes every jobs/*.json that has no outputs/<id>/status.json yet.

Job file (written by client.py):
{
  "id": "20261009-0019-ab12",
  "kind": "say" | "check",
  "speaker": "S_xxx"            # optional, defaults to secret VOLC_SPEAKER_ID
  "model": "seed-tts-2.0-expressive",
  "speech_rate": 0,             # [-50, 100], 0 = normal; lives in audio_params (top level is silently ignored)
  "sample_rate": 48000,
  "tone_fidelity": true,
  "lines": [{"id": "s01", "text": "..."}]
}
Outputs: outputs/<id>/<line_id>.wav (mono 16-bit PCM WAV), outputs/<id>/status.json
Credentials come only from env (GitHub Secrets): VOLC_API_KEY  or  VOLC_APP_ID + VOLC_ACCESS_TOKEN.
"""
import base64, glob, json, os, pathlib, sys, time, uuid, wave
import requests

HOST = "https://openspeech.bytedance.com"
API_KEY = os.getenv("VOLC_API_KEY", "").strip()
APP_ID = os.getenv("VOLC_APP_ID", "").strip()
TOKEN = os.getenv("VOLC_ACCESS_TOKEN", "").strip()
DEFAULT_SPEAKER = os.getenv("VOLC_SPEAKER_ID", "").strip()
TTS_RESOURCE = os.getenv("VOLC_TTS_RESOURCE_ID", "").strip() or "seed-icl-2.0"
CLONE_RESOURCE = "volc.megatts.voiceclone"


AUTH = {"mode": "api_key" if API_KEY else "app_token"}


def key_shape(k):
    """Describe a credential without revealing it: length, charset, known prefixes."""
    import re
    if not k: return "empty"
    kind = ("uuid" if re.fullmatch(r"[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}", k)
            else "iam_access_key_id(AKLT…)" if k.startswith("AKLT") else "other")
    return {"len": len(k), "kind": kind, "has_space": any(c.isspace() for c in k),
            "non_ascii": any(ord(c) > 127 for c in k), "quoted": k[:1] in "'\"" or k[-1:] in "'\""}


def headers(resource):
    h = {"X-Api-Resource-Id": resource, "X-Api-Request-Id": str(uuid.uuid4()), "Content-Type": "application/json"}
    if AUTH["mode"] == "api_key" and API_KEY:
        h["X-Api-Key"] = API_KEY
    elif APP_ID and TOKEN:
        h["X-Api-App-Id"] = APP_ID
        h["X-Api-Access-Key"] = TOKEN
    else:
        raise RuntimeError("no credentials: set secret VOLC_API_KEY, or VOLC_APP_ID + VOLC_ACCESS_TOKEN")
    return h


def check_voice(speaker):
    r = requests.post(f"{HOST}/api/v3/tts/get_voice", headers=headers(CLONE_RESOURCE),
                      json={"speaker_id": speaker}, timeout=30)
    try:
        body = r.json()
    except ValueError:
        body = {"raw": r.text[:500]}
    return {"http": r.status_code, "body": body}


def synth(text, speaker, job):
    sr = int(job.get("sample_rate", 48000))
    payload = {
        "user": {"uid": "huashu-voice"},
        "req_params": {
            "text": text,
            "speaker": speaker,
            "model": job.get("model", "seed-tts-2.0-expressive"),
            "tone_fidelity": bool(job.get("tone_fidelity", True)),
            "audio_params": {"format": "pcm", "sample_rate": sr, "speech_rate": int(job.get("speech_rate", 0))},
        },
    }
    last_err = None
    for attempt in range(3):
        try:
            r = requests.post(f"{HOST}/api/v3/tts/unidirectional", headers=headers(TTS_RESOURCE),
                              json=payload, stream=True, timeout=120)
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
            pcm, codes = bytearray(), []
            for line in r.iter_lines():
                if not line:
                    continue
                msg = json.loads(line)
                code = msg.get("code", 0)
                if msg.get("data"):
                    pcm += base64.b64decode(msg["data"])
                if code not in (0, 20000000):
                    raise RuntimeError(f"api code {code}: {msg.get('message')}")
                codes.append(code)
            if not pcm:
                raise RuntimeError(f"empty audio (codes={codes[-3:]})")
            return bytes(pcm), sr
        except Exception as e:  # noqa: BLE001 — report every failure in status.json
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last_err))


def write_wav(path, pcm, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)


def run(job_path):
    job = json.load(open(job_path, encoding="utf-8"))
    out = pathlib.Path("outputs") / job["id"]
    out.mkdir(parents=True, exist_ok=True)
    speaker = job.get("speaker") or DEFAULT_SPEAKER
    status = {"id": job["id"], "kind": job.get("kind", "say"), "speaker_set": bool(speaker), "lines": [], "ok": True}
    try:
        if not speaker:
            raise RuntimeError("no speaker: set secret VOLC_SPEAKER_ID (S_xxx) or pass speaker in the job")
        if job.get("kind") == "check":
            status["creds"] = {"VOLC_API_KEY": key_shape(API_KEY), "VOLC_APP_ID": key_shape(APP_ID),
                               "VOLC_ACCESS_TOKEN": key_shape(TOKEN), "VOLC_SPEAKER_ID": key_shape(speaker)}
            status["voice"] = check_voice(speaker)
            if status["voice"]["http"] == 401 and API_KEY and APP_ID and TOKEN:
                AUTH["mode"] = "app_token"; status["voice_app_token"] = check_voice(speaker)
            status["auth_mode"] = AUTH["mode"]
            status["ok"] = status["voice"]["http"] == 200 or status.get("voice_app_token", {}).get("http") == 200
        elif API_KEY and APP_ID and TOKEN and check_voice(speaker)["http"] == 401:
            AUTH["mode"] = "app_token"
        for ln in job.get("lines", []):
            item = {"id": ln["id"]}
            try:
                pcm, sr = synth(ln["text"], speaker, job)
                write_wav(out / f"{ln['id']}.wav", pcm, sr)
                item.update(ok=True, dur=round(len(pcm) / 2 / sr, 3), sr=sr)
            except Exception as e:  # noqa: BLE001
                item.update(ok=False, error=str(e)); status["ok"] = False
            status["lines"].append(item)
            print(job["id"], item, flush=True)
    except Exception as e:  # noqa: BLE001
        status.update(ok=False, error=str(e))
    json.dump(status, open(out / "status.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return status["ok"]


if __name__ == "__main__":
    pending = [p for p in sorted(glob.glob("jobs/*.json"))
               if not (pathlib.Path("outputs") / pathlib.Path(p).stem / "status.json").exists()]
    print("pending jobs:", pending)
    results = [run(p) for p in pending]
    sys.exit(0 if all(results) else 0)  # failures are reported in status.json, never hidden behind a red run
