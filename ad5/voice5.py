"""Ad 5 ("2:13 AM"): the narration, line by line, checked by ElevenLabs speech-to-text.

python ad5/voice5.py [only=V4] [voice=<id>] -> ad5/audio/lines/<id>.wav + ad5/audio/lines.json
Order follows the compliance research: the situation, then the criteria, then the statute-anchored $500 with the
qualifier spoken, then the call to action ("free" kept out of the money line).
"""
import base64
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ad"))
_argv = sys.argv[1:]
sys.argv = [sys.argv[0]]
import voice  # noqa: E402

import numpy as np  # noqa: E402

args = dict(a.split("=", 1) for a in _argv if "=" in a)
AUDIO = os.path.join(HERE, "audio")
OUT = os.path.join(AUDIO, "lines")
os.makedirs(OUT, exist_ok=True)
VOICE = args.get("voice", "CwhRBWXzGAHq8TQ4Fs17")     # Roger - Laid-Back, Casual, Resonant
MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.46, "similarity_boost": 0.86, "style": 0.3, "use_speaker_boost": True}
LINES = [
    ("V1", "You told them STOP."),
    ("V2", "They kept texting."),
    ("V3", "A real company. Two or more texts, weeks after your STOP?"),
    ("V4", "Federal law says each one can mean up to five hundred dollars in damages."),
    ("V5", "Results vary, and not every text qualifies."),
    ("V6", "Screenshot your texts, and check them free at SpamClaims dot com."),
]


def tts(text):
    d = json.loads(voice.call(f"/v1/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_128",
                              {"text": text, "model_id": MODEL, "voice_settings": SETTINGS}))
    x = voice.mp3_to_np(base64.b64decode(d["audio_base64"]))
    al = d.get("alignment") or {}
    words, cur, s0, e0 = [], "", 0.0, 0.0
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append((cur, s0, e0))
            cur = ""
            continue
        if not cur:
            s0 = s
        cur += ch
        e0 = e
    if cur:
        words.append((cur, s0, e0))
    idx = np.where(np.abs(x) > 0.012)[0]
    a = max(0, idx[0] - int(0.015 * voice.SR)) if len(idx) else 0
    b = min(len(x), idx[-1] + int(0.08 * voice.SR)) if len(idx) else len(x)
    off = a / voice.SR
    return x[a:b], [{"w": w, "s": round(max(0.0, s - off), 3), "e": round(max(0.0, e - off), 3)} for w, s, e in words]


def transcribe(path):
    out = subprocess.run(["curl", "-s", "-m", "90", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text",
                          "-H", f"xi-api-key: {voice.KEY}", "-F", "model_id=scribe_v1", "-F", f"file=@{path}"],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out).get("text", "")
    except Exception:
        return "?"


meta_path = os.path.join(AUDIO, "lines.json")
meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
only = set(args["only"].split(",")) if args.get("only") else None
for lid, text in LINES:
    if only and lid not in only:
        continue
    x, words = tts(text)
    p = os.path.join(OUT, f"{lid}.wav")
    voice.write_wav(p, x)
    heard = transcribe(p)
    meta[lid] = {"dur": round(len(x) / voice.SR, 3), "words": words, "heard": heard, "voice": VOICE}
    print(f"{lid}: {len(x) / voice.SR:5.2f}s  heard: {heard}")
json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
