"""Ad 6 ("Storytime"): Dre tells the story (a Gen Z creator voice), his group chat reacts out loud.
Every line is checked by ElevenLabs speech-to-text; character timings are kept for the lip sync.

python ad6/voice6.py [audition=1] [only=V1,F2] [voice=<voice id>]
  audition=1  the hook in the candidate narrator voices -> ad6/audio/audition_<name>.wav
  otherwise   every line -> ad6/audio/lines/<id>.wav (48 kHz mono, trimmed) + ad6/audio/lines.json
              (duration, word timings, character timings, what speech-to-text heard)

The money is always "could be worth up to", tied to federal law, and the catch and "results vary" are said out loud.
Nobody claims to have been paid: the story is about finding out the law is real, not a payout.
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

NARRATORS = {
    "liam": "TX3LPaxmHKxFdv7VOQHJ",     # Liam - Energetic, Social Media Creator (young, American)
    "will": "bIHbv24MWmeRgasZH58o",     # Will - Relaxed Optimist (young, American)
}
DRE = args.get("voice", NARRATORS["liam"])
JAY = "bIHbv24MWmeRgasZH58o"            # Will - Relaxed Optimist (young, American)
AVA = "FGY2WhTYpPnrIDTdsKH5"            # Laura - Enthusiast, Quirky Attitude (young, American)
MARCUS = "N2lVS1w4EtoT3dr4eOWO"         # Callum - Husky Trickster
MODEL = "eleven_v3"
SETTINGS = {"stability": 0.5}            # v3 "natural"

LINES = [  # (id, voice, text with v3 performance tags)
    ("V1", DRE, "[excited] [fast-paced] Okay, storytime. My spam texts? Could be worth up to five hundred bucks. EACH."),
    ("V2", DRE, "[fast-paced] So this one company kept texting me. I said STOP. [annoyed] They kept going."),
    ("V3", DRE, "[curious] So at like two A.M.... I look it up."),
    ("V4", DRE, "[excited] [fast-paced] And bro. It's a real federal law. Every text after you say STOP? Could be worth up to five "
                "hundred dollars."),
    ("V5", DRE, "[sarcastic] [fast-paced] Obviously, I thought it was a scam. [laughs] So did the group chat."),
    ("V6", DRE, "[confident] [fast-paced] It's a hundred percent real. A hundred percent legal. For real, for real."),
    ("V7", DRE, "[fast-paced] Oh, and it's not just STOP. Texts you never agreed to? Texts after nine PM, like mine? "
                "Those can count too. Not every text qualifies, and results vary."),
    ("V8", DRE, "[fast-paced] So screenshot your texts, and check them free at SpamClaims dot com."),
    ("V9", DRE, "They ignored your STOP. [pause] The law didn't."),
    ("F1", MARCUS, "[laughs] Bro, that's a scam."),
    ("F2", JAY, "[shocked] Wait... it's actually real?"),
    ("F3", AVA, "[shouting] OH MY GOD!"),
]


def tts(voice_id, text):
    d = json.loads(voice.call(f"/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
                              {"text": text, "model_id": MODEL, "voice_settings": SETTINGS}))
    x = voice.mp3_to_np(base64.b64decode(d["audio_base64"]))
    al = d.get("alignment") or {}
    chars, words, cur, s0, e0, in_tag = [], [], "", 0.0, 0.0, False
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                        al.get("character_end_times_seconds", [])):
        if ch == "[":
            in_tag = True
        if in_tag:
            if ch == "]":
                in_tag = False
            continue
        chars.append((ch, s, e))
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
    return (x[a:b], [{"w": w, "s": round(max(0.0, s - off), 3), "e": round(max(0.0, e - off), 3)} for w, s, e in words],
            [[c, round(max(0.0, s - off), 3), round(max(0.0, e - off), 3)] for c, s, e in chars])


def transcribe(path):
    out = subprocess.run(["curl", "-s", "-m", "90", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text",
                          "-H", f"xi-api-key: {voice.KEY}", "-F", "model_id=scribe_v1", "-F", f"file=@{path}"],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out).get("text", "")
    except Exception:
        return "?"


def audition():
    for name, vid in NARRATORS.items():
        x, words, _ = tts(vid, LINES[0][2] + " " + LINES[1][2])
        p = os.path.join(AUDIO, f"audition_{name}.wav")
        voice.write_wav(p, x)
        dur = len(x) / voice.SR
        print(f"{name:7} {dur:5.2f}s  {len(words) / dur:4.2f} words/s  heard: {transcribe(p)}")


def main():
    meta_path = os.path.join(AUDIO, "lines.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    only = set(args["only"].split(",")) if args.get("only") else None
    for lid, vid, text in LINES:
        if only and lid not in only:
            continue
        x, words, chars = tts(vid, text)
        p = os.path.join(OUT, f"{lid}.wav")
        voice.write_wav(p, x)
        heard = transcribe(p)
        meta[lid] = {"dur": round(len(x) / voice.SR, 3), "words": words, "chars": chars, "heard": heard, "voice": vid}
        print(f"{lid}: {len(x) / voice.SR:5.2f}s  heard: {heard}")
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    audition() if args.get("audition") == "1" else main()
