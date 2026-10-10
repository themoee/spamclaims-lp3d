"""Voiceover (and optional sound effects / music bed) from ElevenLabs, fitted to the picture in ad/edit.json.

python ad/voice.py [voice=<name or id>] [model=eleven_multilingual_v2] [sfx=1] [music=1] [list=1]
The key is read from %USERPROFILE%\\.elevenlabs_key (or ELEVENLABS_API_KEY); it is never printed or written anywhere.
Writes ad/audio/vo.wav (48 kHz mono, 15 s, each line at its slot), vo_lines/*.wav, and with sfx=1 / music=1 the
ElevenLabs sound effects (ad/audio/sfx_<kind>.wav, picked up by sfx.py) and a music bed (ad/audio/music.wav).
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio")
SR = 48000
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
API = "https://api.elevenlabs.io"


def key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    p = os.path.join(os.path.expanduser("~"), ".elevenlabs_key")
    if not k and os.path.exists(p):
        k = open(p, encoding="utf-8-sig").read().strip()
    if not k:
        sys.exit("no ElevenLabs key: save it to %USERPROFILE%\\.elevenlabs_key")
    return k


KEY = key()


class ApiError(Exception):
    pass


def call(path, body=None, method=None, accept="application/json"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method or ("POST" if data else "GET"))
    req.add_header("xi-api-key", KEY)
    req.add_header("Accept", accept)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:400]
        raise ApiError(f"ElevenLabs {path.split('?')[0]} -> HTTP {e.code}: {msg}")


def pcm_to_np(raw):
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def mp3_to_np(raw):
    """Every plan can return MP3; decode it to 48 kHz mono with ffmpeg."""
    src = os.path.join(AUDIO, "_tmp.mp3")
    open(src, "wb").write(raw)
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    os.remove(src)
    return pcm_to_np(out)


def write_wav(path, x, channels=1):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def trim(x, thresh=0.01):
    idx = np.where(np.abs(x) > thresh)[0]
    if not len(idx):
        return x
    a, b = max(0, idx[0] - int(0.02 * SR)), min(len(x), idx[-1] + int(0.08 * SR))
    return x[a:b]


def atempo(x, factor):
    """Time-stretch without changing pitch (ffmpeg atempo); used only for small fits (<= 1.15x)."""
    src, dst = os.path.join(AUDIO, "_tmp_in.wav"), os.path.join(AUDIO, "_tmp_out.wav")
    write_wav(src, x)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter:a", f"atempo={factor:.4f}", dst], check=True)
    with wave.open(dst) as w:
        y = pcm_to_np(w.readframes(w.getnframes()))
    os.remove(src)
    os.remove(dst)
    return y


def pick_voice():
    voices = json.loads(call("/v1/voices"))["voices"]
    if args.get("list") == "1":
        for v in voices:
            lab = v.get("labels", {})
            print(f"{v['voice_id']}  {v['name']:<24} {lab.get('gender', '')} {lab.get('accent', '')} {lab.get('age', '')} {lab.get('use_case', lab.get('description', ''))}")
        sys.exit(0)
    want = args.get("voice")
    if want:
        for v in voices:
            if want in (v["voice_id"], v["name"]) or v["name"].lower().startswith(want.lower()):
                return v
        sys.exit(f"voice {want!r} not found (run with list=1)")
    for name in ("Brian", "Chris", "Eric", "Sarah", "Jessica", "Adam", "Matilda"):   # natural, confident, American
        for v in voices:
            if v["name"].lower().startswith(name.lower()):
                return v
    return voices[0]


def tts(voice_id, text, speed=1.0):
    """One line, with word timings (from the character alignment), leading silence trimmed off both."""
    import base64

    body = {
        "text": text,
        "model_id": args.get("model", "eleven_multilingual_v2"),
        "voice_settings": {"stability": 0.42, "similarity_boost": 0.82, "style": 0.38, "use_speaker_boost": True, "speed": speed},
    }
    d = json.loads(call(f"/v1/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128", body))
    x = mp3_to_np(base64.b64decode(d["audio_base64"]))
    al = d.get("alignment") or d.get("normalized_alignment") or {}
    words, cur, start, end = [], "", 0.0, 0.0
    for ch, s, e in zip(al.get("characters", []), al.get("character_start_times_seconds", []),
                        al.get("character_end_times_seconds", [])):
        if ch.isspace():
            if cur:
                words.append((cur, start, end))
            cur = ""
            continue
        if not cur:
            start = s
        cur, end = cur + ch, e
    if cur:
        words.append((cur, start, end))
    idx = np.where(np.abs(x) > 0.01)[0]
    a = max(0, idx[0] - int(0.02 * SR)) if len(idx) else 0
    b = min(len(x), idx[-1] + int(0.08 * SR)) if len(idx) else len(x)
    off = a / SR
    return x[a:b], [(w, max(0.0, s - off), max(0.0, e - off)) for w, s, e in words]


def main():
    os.makedirs(os.path.join(AUDIO, "vo_lines"), exist_ok=True)
    edit = json.load(open(os.path.join(HERE, args.get("edit", "edit.json")), encoding="utf-8"))
    tag = "" if edit.get("variant", "a") == "a" else "_" + edit["variant"]
    v = pick_voice()
    print("voice:", v["name"], v["voice_id"])
    track = np.zeros(int(edit["duration"] * SR) + SR, dtype=np.float32)
    report = []
    for k, line in enumerate(edit["voice"]):
        x, words = tts(v["voice_id"], line["text"])
        dur = len(x) / SR
        if dur > line["max"]:                                 # ask for a slightly faster read first
            x, words = tts(v["voice_id"], line["text"], speed=min(1.15, dur / line["max"] * 1.02))
            dur = len(x) / SR
        if dur > line["max"]:                                 # then a gentle time-stretch (timings scale with it)
            f = min(1.15, dur / line["max"])
            x = atempo(x, f)
            words = [(w, s / f, e / f) for w, s, e in words]
            dur = len(x) / SR
        write_wav(os.path.join(AUDIO, "vo_lines", f"{k}{tag}.wav"), x)
        i = int(line["at"] * SR)
        track[i:i + len(x)] += x[: len(track) - i]
        report.append({"at": line["at"], "dur": round(dur, 3), "max": line["max"], "text": line["text"],
                       "words": [{"w": w, "s": round(line["at"] + s, 3), "e": round(line["at"] + e, 3)} for w, s, e in words]})
    track = track[: int(edit["duration"] * SR)]
    track *= 0.89 / (np.max(np.abs(track)) + 1e-9)
    write_wav(os.path.join(AUDIO, f"vo{tag}.wav"), track)
    json.dump({"voice": v["name"], "voice_id": v["voice_id"], "lines": report},
              open(os.path.join(AUDIO, f"vo{tag}.json"), "w"), indent=1)
    for r in report:
        print(f"  at {r['at']:5.2f}s  {r['dur']:4.2f}s (max {r['max']})  {r['text']}")

    if args.get("sfx") == "1":
        prompts = {
            "send": "a quick soft whoosh of a text message being sent, airy, short, modern",
            "ding": "a single soft modern phone notification ping, glassy, short, clean, no melody",
            "freeze": "a deep cinematic impact with an icy crystalline shimmer tail, time freezing, 1.5 seconds",
            "storm": "a tense low rumble swelling louder with fast fluttering whooshes, building anxiety, 2 seconds",
            "shutter": "a crisp digital camera shutter click, short",
            "scan": "a futuristic scanner sweep, smooth rising electronic tone with soft static, 1.2 seconds",
            "pop": "a satisfying deep logo reveal hit with a bright warm shimmer, 2 seconds",
        }
        lengths = {"send": 0.5, "ding": 0.6, "freeze": 1.6, "storm": 2.0, "shutter": 0.5, "scan": 1.2, "pop": 2.0}
        for kind, prompt in prompts.items():
            try:
                raw = call("/v1/sound-generation?output_format=mp3_44100_128",
                           {"text": prompt, "duration_seconds": lengths[kind], "prompt_influence": 0.55},
                           accept="audio/mpeg")
            except ApiError as e:
                print("  sfx", kind, "skipped:", e)
                continue
            write_wav(os.path.join(AUDIO, f"sfx_{kind}.wav"), trim(mp3_to_np(raw), 0.003))
            print("  sfx", kind)

    if args.get("music") == "1":
        try:
            raw = call("/v1/music?output_format=mp3_44100_128", {
                "prompt": "minimal tense modern electronic ad bed, soft pulsing synth bass and ticking hi-hats, "
                          "100 bpm, builds tension, no vocals, clean ending",
                "music_length_ms": int(edit["duration"] * 1000),
            }, accept="audio/mpeg")
            write_wav(os.path.join(AUDIO, "music.wav"), mp3_to_np(raw))
            print("  music bed")
        except ApiError as e:
            print("  music API unavailable, using a sound-effects bed instead:", str(e)[:120])
            try:
                raw = call("/v1/sound-generation?output_format=mp3_44100_128", {
                    "text": "tense minimal modern electronic pulse bed, soft synth bass throb and light ticking, dark, "
                            "building suspense, no melody, steady, 15 seconds",
                    "duration_seconds": min(22.0, edit["duration"]), "prompt_influence": 0.45}, accept="audio/mpeg")
                write_wav(os.path.join(AUDIO, "music.wav"), mp3_to_np(raw))
                print("  bed from sound effects")
            except ApiError as e2:
                print("  bed skipped:", e2)


if __name__ == "__main__":
    try:
        main()
    except ApiError as e:
        sys.exit(str(e))
