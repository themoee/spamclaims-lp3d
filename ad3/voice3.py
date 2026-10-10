"""Ad 3 ("The 10-second check"): the creator voice-over, line by line, checked by ElevenLabs speech-to-text.

python ad3/voice3.py [audition=1] [only=A5,B5] [voice=<voice id>]
  audition=1  the hook line in three candidate voices -> ad3/audio/audition_<name>.wav (pace, clarity)
  otherwise   every line -> ad3/audio/lines/<id>.wav (48 kHz mono, trimmed) + ad3/audio/lines.json
              (duration, word timings, what speech-to-text heard)

Lines 1-4 are shared by both cuts; cut A says no dollar amount (the control), cut B ties $500 to the statute and
says the qualifier out loud (the challenger), with "free" kept out of the money line.
"""
import base64
import json
import os
import re
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
    "laura": "FGY2WhTYpPnrIDTdsKH5",   # Laura - Enthusiast, Quirky Attitude (social media)
    "sarah": "EXAVITQu4vr4xnSDxMaL",   # Sarah - Mature, Reassuring, Confident
    "liam": "TX3LPaxmHKxFdv7VOQHJ",    # Liam - Energetic, Social Media Creator
}
VOICE = args.get("voice", CANDIDATES["sarah"])   # reassuring + confident: trust is the category weak spot
MODEL = "eleven_v3"
SETTINGS = {"stability": 0.5}            # v3 "natural"

LINES = [  # (id, text with v3 performance tags); A = no-$ control, B = statute-anchored $ challenger
    ("L1", "[fast-paced] You told a company STOP... and they kept texting you?"),
    ("L2", "[fast-paced] Here's a ten-second check. Open Messages and search the word STOP."),
    ("L3", "[fast-paced] Tap a company you texted STOP to, and count what they sent after."),
    ("A4", "[fast-paced] Two or more texts, weeks after your STOP? Federal law may entitle you to damages for each one."),
    ("A5", "[fast-paced] Screenshot your STOP and the texts after it, and check them free at SpamClaims dot com."),
    ("A6", "[fast-paced] Texts from the last four years can count."),
    ("B4", "[fast-paced] Two or more texts, weeks after your STOP? Under federal law, damages can be up to five "
           "hundred dollars per text. Results vary."),
    ("B5", "[fast-paced] Screenshot your STOP and the texts after it, and check them at SpamClaims dot com."),
    ("B6", "[fast-paced] It's free to check. Texts from the last four years can count."),
]


def tts(voice_id, text):
    d = json.loads(voice.call(f"/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
                              {"text": text, "model_id": MODEL, "voice_settings": SETTINGS}))
    x = voice.mp3_to_np(base64.b64decode(d["audio_base64"]))
    al = d.get("alignment") or {}
    words, cur, s0, e0, in_tag = [], "", 0.0, 0.0, False
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                        al.get("character_end_times_seconds", [])):
        if ch == "[":
            in_tag = True
        if in_tag:
            if ch == "]":
                in_tag = False
            continue
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
    b = min(len(x), idx[-1] + int(0.06 * voice.SR)) if len(idx) else len(x)
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


def audition():
    for name, vid in CANDIDATES.items():
        x, words = tts(vid, LINES[0][1] + " " + LINES[1][1] + " " + LINES[2][1])
        p = os.path.join(AUDIO, f"audition_{name}.wav")
        voice.write_wav(p, x)
        dur = len(x) / voice.SR
        print(f"{name:6} {dur:5.2f}s  {len(words) / dur:4.2f} words/s  heard: {transcribe(p)}")


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
        meta[lid] = {"dur": round(len(x) / voice.SR, 3), "words": words, "heard": heard, "voice": VOICE}
        print(f"{lid}: {len(x) / voice.SR:5.2f}s  heard: {heard}")
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if args.get("audition") == "1":
    audition()
else:
    main()
