"""Ad 2 ("Did you mean START?"): the voice lines, generated one by one, then checked by ElevenLabs speech-to-text.

python ad2/voice2.py [only=M3,B2] [force=1]
Writes ad2/audio/lines/<id>.wav (48 kHz mono, trimmed) and ad2/audio/lines.json (duration, word timings and
what speech-to-text heard), so the edit can be timed to the performances.
"""
import base64
import json
import os
import re
import subprocess
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ad"))
_argv = sys.argv[1:]
sys.argv = [sys.argv[0]]
import voice  # noqa: E402

import numpy as np  # noqa: E402

args = dict(a.split("=", 1) for a in _argv if "=" in a)
OUT = os.path.join(HERE, "audio", "lines")
os.makedirs(OUT, exist_ok=True)

VOICES = {
    "ME": ("iP95p4xoKVk53GoZ742B", "eleven_v3"),          # Chris - Charming, Down-to-Earth: the person getting texted
    "BRAND": ("cgSgspJ2msm6clMCkdW9", "eleven_v3"),       # Jessica - Playful, Bright, Warm: the relentless brand
    "NARRATOR": ("nPczCjzI2devNBz1zQrb", "eleven_multilingual_v2"),   # Brian - Deep, Resonant: a trailer voice for the twist
}
LINES = [  # (id, speaker, text with v3 performance tags)
    ("B1", "BRAND", "[cheerfully] Your cookies miss you!"),
    ("M1", "ME", "[politely] Stop."),
    ("M2", "ME", "[annoyed] Stop."),
    ("M3", "ME", "[shouting] STOP!"),
    ("M4", "ME", "[desperately] Please... stop."),
    ("M5", "ME", "[calmly, slightly unhinged] I will throw my phone in a lake."),
    ("B2", "BRAND", "[sweetly] Did you mean... start?"),
    ("N1", "NARRATOR", "Plot twist: every text after your first stop could be worth up to five hundred dollars."),
    ("N2", "NARRATOR", "See if yours qualify. Free, at SpamClaims dot com."),
]
SETTINGS = {
    "eleven_v3": {"stability": 0.5},                                      # v3: "natural" (0.5) keeps tags expressive
    "eleven_multilingual_v2": {"stability": 0.42, "similarity_boost": 0.82, "style": 0.38, "use_speaker_boost": True},
}


SPEED = {"N1": 1.08, "N2": 1.05}                                          # the narrator reads a touch brisker
SLOT = {"N1": 4.30, "N2": 3.05}                                           # the slots the render was timed to


def tts(voice_id, model, text, speed=1.0):
    vs = dict(SETTINGS[model])
    if speed != 1.0:
        vs["speed"] = speed
    d = json.loads(voice.call(f"/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128",
                              {"text": text, "model_id": model, "voice_settings": vs}))
    raw = base64.b64decode(d["audio_base64"])
    x = voice.mp3_to_np(raw)
    al = d.get("alignment") or {}
    spoken = re.sub(r"\[[^\]]*\]\s*", "", text)               # tags are performed, not said: skip them for timing
    chars, starts, ends = al.get("characters", []), al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])
    words, cur, s0, e0, in_tag = [], "", 0.0, 0.0, False
    for ch, s, e in zip(chars, starts, ends):
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
        cur, e0 = cur + ch, e
    if cur:
        words.append((cur, s0, e0))
    idx = np.where(np.abs(x) > 0.012)[0]
    a = max(0, idx[0] - int(0.015 * voice.SR)) if len(idx) else 0
    b = min(len(x), idx[-1] + int(0.06 * voice.SR)) if len(idx) else len(x)
    off = a / voice.SR
    return x[a:b], [(w, round(max(0.0, s - off), 3), round(max(0.0, e - off), 3)) for w, s, e in words], spoken


def transcribe(path):
    k = voice.KEY
    out = subprocess.run(["curl", "-s", "-m", "90", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text",
                          "-H", f"xi-api-key: {k}", "-F", "model_id=scribe_v1", "-F", "tag_audio_events=true",
                          "-F", f"file=@{path}"], capture_output=True, text=True).stdout
    try:
        return json.loads(out).get("text", "")
    except Exception:
        return "?"


def main():
    meta_path = os.path.join(HERE, "audio", "lines.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    only = set(args["only"].split(",")) if args.get("only") else None
    for lid, spk, text in LINES:
        if only and lid not in only:
            continue
        if lid in meta and not only and args.get("force") != "1":
            continue
        vid, model = VOICES[spk]
        x, words, spoken = tts(vid, model, text, SPEED.get(lid, 1.0))
        slot = SLOT.get(lid)
        if slot and len(x) / voice.SR > slot:            # the picture is already rendered: fit the read to its slot
            sp = min(1.2, SPEED.get(lid, 1.0) * (len(x) / voice.SR) / slot * 1.02)
            x, words, spoken = tts(vid, model, text, sp)
            if len(x) / voice.SR > slot:
                f = (len(x) / voice.SR) / slot
                x = voice.atempo(x, f)
                words = [(w_, s_ / f, e_ / f) for w_, s_, e_ in words]
        wav = os.path.join(OUT, f"{lid}.wav")
        voice.write_wav(wav, x)
        heard = transcribe(wav)
        meta[lid] = {"speaker": spk, "text": text, "spoken": spoken, "dur": round(len(x) / voice.SR, 3),
                     "words": [{"w": w, "s": s, "e": e} for w, s, e in words], "heard": heard}
        print(f"{lid:3} {spk:8} {meta[lid]['dur']:5.2f}s  said: {spoken!r}\n{'':18}heard: {heard!r}")
        json.dump(meta, open(meta_path, "w"), indent=1)


if __name__ == "__main__":
    main()
