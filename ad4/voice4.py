"""Ad 4 ("The Swarm"): the trailer narration, line by line, checked by ElevenLabs speech-to-text.

python ad4/voice4.py [audition=1] [only=V2,V3] [voice=<id>] [model=eleven_multilingual_v2]
  audition=1  two lines in each candidate voice -> ad4/audio/audition_<name>.wav
  otherwise   every line -> ad4/audio/lines/<id>.wav (48 kHz mono, trimmed) + ad4/audio/lines.json
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
CANDIDATES = {
    "chuck": "dCMXwKsfIwcA9jIgihJc",    # Chuck - confident, advertisement
    "bill": "pqHfZKP75CvOlQylNhV4",     # Bill - wise, mature, crisp
    "adam": "pNInz6obpgDQGcFmaJgB",     # Adam - dominant, firm
    "brian": "nPczCjzI2devNBz1zQrb",    # Brian - deep, resonant (ad 2's narrator)
}
VOICE = args.get("voice", CANDIDATES["chuck"])
MODEL = args.get("model", "eleven_multilingual_v2")
SETTINGS = {
    "eleven_multilingual_v2": {"stability": 0.38, "similarity_boost": 0.85, "style": 0.45, "use_speaker_boost": True},
    "eleven_v3": {"stability": 0.5},
}
LINES = [  # (id, text) - situation first, no dollar amounts (the research: the money line is what gets rejected)
    ("V1", "It starts with one text. Then... it never stops."),
    ("V2", "You told them STOP."),
    ("V3", "They kept texting."),
    ("V4", "But every text after your STOP..."),
    ("V5", "may be a violation of federal law."),
    ("V6", "See if your texts may qualify. Free, at SpamClaims dot com."),
]


def tts(voice_id, text, model=MODEL):
    vs = dict(SETTINGS[model])
    d = json.loads(voice.call(f"/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
                              {"text": text, "model_id": model, "voice_settings": vs}))
    x = voice.mp3_to_np(base64.b64decode(d["audio_base64"]))
    al = d.get("alignment") or {}
    words, cur, s0, e0 = [], "", 0.0, 0.0
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                        al.get("character_end_times_seconds", [])):
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


def pitch_stats(x):
    """Rough median pitch (Hz) of voiced 40 ms frames: a deep trailer voice sits low."""
    sr, n = voice.SR, int(0.04 * voice.SR)
    f0 = []
    for i in range(0, len(x) - n, n):
        fr = x[i:i + n] - np.mean(x[i:i + n])
        if np.sqrt(np.mean(fr ** 2)) < 0.03:
            continue
        ac = np.correlate(fr, fr, "full")[n - 1:]
        lo, hi = int(sr / 300), int(sr / 60)
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.3 * ac[0]:
            f0.append(sr / k)
    return float(np.median(f0)) if f0 else 0.0


def audition():
    for name, vid in CANDIDATES.items():
        x, words = tts(vid, LINES[1][1] + " " + LINES[2][1] + " " + LINES[3][1])
        p = os.path.join(AUDIO, f"audition_{name}.wav")
        voice.write_wav(p, x)
        print(f"{name:6} {len(x) / voice.SR:5.2f}s  pitch ~{pitch_stats(x):5.0f} Hz  heard: {transcribe(p)}")


def main():
    meta_path = os.path.join(AUDIO, "lines.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    only = set(args["only"].split(",")) if args.get("only") else None
    for lid, text in LINES:
        if only and lid not in only:
            continue
        x, words = tts(VOICE, text)
        p = os.path.join(OUT, f"{lid}.wav")
        voice.write_wav(p, x)
        heard = transcribe(p)
        meta[lid] = {"dur": round(len(x) / voice.SR, 3), "words": words, "heard": heard, "voice": VOICE, "model": MODEL}
        print(f"{lid}: {len(x) / voice.SR:5.2f}s  heard: {heard}")
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if args.get("audition") == "1":
    audition()
else:
    main()
