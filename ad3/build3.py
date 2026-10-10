"""Build Reel ad 3 ("The 10-second check"), both cuts: composite the frames, mix the sound, encode for Instagram.

python ad3/build3.py [cut=a|b|ab] [skip_capture=1] [mix_only=1] [lufs=-15]
  1. node ad3/capture3.cjs --edit edit_<cut>.json -> ad3/out/frames_<cut>/NNNN.png
  2. the mix: the creator voice (ad3/audio/fast), phone sounds on every on-screen action, the tutorial beat (the groove
     section of ad3/audio/music.wav looped on bar lines, so it has energy from the first frame), ducked under the voice
  3. loudness: -15 LUFS integrated, -1 dBFS ceiling (ffmpeg ebur128 + alimiter)
  4. ffmpeg: H.264 high, 1080x1920, 30 fps, yuv420p, AAC 192k 48 kHz, faststart -> ad3/out/spamclaims-reel-check-<cut>.mp4
"""
import json
import os
import re
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AUDIO = os.path.join(HERE, "audio")
OUT = os.path.join(HERE, "out")
SR = 48000
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
LUFS = float(args.get("lufs", "-15"))
GROOVE_FROM, BAR = 10.45, 60 / 92 * 4          # where the beat comes in, and one bar at 92 bpm


def db(v):
    return 10 ** (v / 20)


def read(path, peak=None):
    with wave.open(path) as w:
        assert w.getframerate() == SR, path
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    if peak is not None:
        x = x * (peak / (np.max(np.abs(x)) + 1e-9))
    return x


def write(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def place(track, x, at, gain_db=0.0, pan=0.0):
    i = int(round(at * SR))
    if i < 0:
        x, i = x[-i:], 0
    x = x[: max(0, len(track) - i)]
    a = (pan + 1) * np.pi / 4
    g = db(gain_db) * np.sqrt(2)
    track[i:i + len(x), 0] += g * np.cos(a) * x
    track[i:i + len(x), 1] += g * np.sin(a) * x


def pitch(x, semitones):
    """Resample to shift pitch (a short pop gets a little shorter as it goes up; fine for UI sounds)."""
    r = 2 ** (semitones / 12)
    idx = np.arange(0, len(x) - 1, r)
    return np.interp(idx, np.arange(len(x)), x).astype(np.float32)


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    if fin:
        k = min(len(x), int(fin * SR))
        x[:k] *= np.linspace(0, 1, k)
    if fout:
        k = min(len(x), int(fout * SR))
        x[len(x) - k:] *= np.linspace(1, 0, k)
    return x


def follower(x, attack=0.03, release=0.30, rate=1000):
    h = SR // rate
    m = np.abs(x[: len(x) // h * h]).reshape(-1, h).max(axis=1)
    ca, cr = np.exp(-1 / (attack * rate)), np.exp(-1 / (release * rate))
    out = np.empty_like(m)
    y = 0.0
    for i, v in enumerate(m):
        c = ca if v > y else cr
        y = c * y + (1 - c) * v
        out[i] = y
    return np.interp(np.arange(len(x)) / h, np.arange(len(out)), out).astype(np.float32)


def ffmpeg(*a):
    return subprocess.run(["ffmpeg", "-y", "-hide_banner", *a], check=True, capture_output=True, text=True)


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))


def mix(E):
    N = int(round(E["frames"] / E["fps"] * SR))
    dur = N / SR
    vo = np.zeros((N, 2), dtype=np.float32)
    for ln in E["lines"]:
        place(vo, read(os.path.join(AUDIO, "fast", f"{ln['id']}.wav")), ln["at"], 0.0)
    raw, comp = os.path.join(AUDIO, "_vo_raw.wav"), os.path.join(AUDIO, "_vo_comp.wav")
    write(raw, vo * 0.5)
    ffmpeg("-i", raw, "-af", "acompressor=threshold=-24dB:ratio=2.5:attack=4:release=90:makeup=1", comp)
    with wave.open(comp) as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
    os.remove(raw)
    os.remove(comp)
    vo = np.zeros((N, 2), dtype=np.float32)
    vo[: min(N, len(y))] = y[:N] * 2.0

    fx = np.zeros((N, 2), dtype=np.float32)
    clip = {k: read(os.path.join(AUDIO, f"sfx_{k}.wav"), peak=1.0)
            for k in ["sent", "recv", "shutter", "chime", "key", "tap", "swipe", "pop", "tick", "drop"]}
    h, s, c, r, u, ec = E["hook"], E["search"], E["count"], E["rules"], E["upload"], E["endcard"]
    place(fx, clip["recv"], 0.02, -12)                                   # the first frame: a text lands
    place(fx, clip["sent"], h["stop_sent"], -14)
    place(fx, clip["recv"], h["confirm"], -15)
    for k, t in enumerate(h["arrivals"]):
        place(fx, pitch(clip["recv"], [0, 1, 2, 3][k]), t, -14 + k * 0.6, pan=[-0.15, 0.1, -0.05, 0.15][k])
    place(fx, clip["swipe"], s["back"], -19)
    place(fx, clip["tap"], s["focus"] - 0.03, -17)
    for k, t in enumerate(s["typed"]):
        place(fx, pitch(clip["key"], [0, 0.5, -0.5, 0.3][k]), t - 0.01, -16)
    place(fx, clip["tap"], c["tap"] - 0.02, -15)
    place(fx, clip["swipe"], c["open"] - 0.02, -19)
    place(fx, clip["tick"], c["ring"], -19)
    for k, t in enumerate(c["badges"]):
        place(fx, pitch(clip["pop"], [0, 2, 4, 7][k]), t - 0.01, -13, pan=0.25)
    place(fx, clip["swipe"], r["in"], -21)
    for k, t in enumerate(r["items"][:2] + [r["items"][2] + 0.55]):
        place(fx, pitch(clip["tick"], [0, 2, 4][k]), t, -15)
    if r.get("each"):
        for k in range(4):
            place(fx, pitch(clip["pop"], 7 + 2 * k), r["each"] + 0.12 * k, -21, pan=0.25)
    place(fx, clip["shutter"], u["shot"] - 0.01, -9)
    place(fx, clip["swipe"], u["web"] - 0.02, -18)
    place(fx, clip["drop"], u["web"] + 0.30, -15)
    place(fx, clip["tap"], u["tapcta"] - 0.02, -14)
    place(fx, clip["chime"], ec["at"] + 0.35, -11)

    # the beat: the groove section looped on bar lines (short crossfades), out over the last 1.2 s
    m = read(os.path.join(AUDIO, "music.wav"))
    g0, bar = int(GROOVE_FROM * SR), int(BAR * SR)
    bars = (len(m) - g0 - int(1.0 * SR)) // bar                          # whole bars available before the final chord
    groove = m[g0: g0 + bars * bar]
    bed = groove.copy()
    xf = int(0.012 * SR)
    while len(bed) < N:
        nxt = groove[2 * bar:]                                            # loop back two bars in (skip the entry)
        bed[-xf:] = bed[-xf:] * np.linspace(1, 0, xf) + nxt[:xf] * np.linspace(0, 1, xf)
        bed = np.concatenate([bed, nxt[xf:]])
    bed = fade(bed[:N], 0.02, 1.2)
    mu = np.zeros((N, 2), dtype=np.float32)
    place(mu, bed, 0.0, -9.0)

    talk = np.clip(follower(vo.mean(axis=1), 0.04, 0.32) / 0.05, 0, 1)[:, None]
    mixed = vo + fx * (1 - 0.25 * talk) + mu * (1 - 0.5 * talk)
    pre = os.path.join(AUDIO, f"_premix_{E['cut']}.wav")
    write(pre, mixed * 0.5)
    i, _ = loudness(pre)
    out = os.path.join(AUDIO, f"mix_{E['cut']}.wav")
    ffmpeg("-i", pre, "-af", f"volume={LUFS - i:.2f}dB,alimiter=limit=0.87:attack=3:release=60:level=disabled", "-ar", str(SR),
           "-c:a", "pcm_s16le", out)
    os.remove(pre)
    i2, pk = loudness(out)
    print(f"cut {E['cut']}: mix {i2:.1f} LUFS, peak {pk:.1f} dBFS, {dur:.2f} s")
    return out


def main():
    for cut in args.get("cut", "ab"):
        edit = f"edit_{cut}.json"
        E = json.load(open(os.path.join(HERE, edit), encoding="utf-8"))
        frames = os.path.join(OUT, f"frames_{cut}")
        if args.get("mix_only") != "1" and args.get("skip_capture") != "1":
            subprocess.run(["node", os.path.join(HERE, "capture3.cjs"), "--edit", edit, "--out", f"ad3/out/frames_{cut}"],
                           check=True, cwd=ROOT)
        audio = mix(E)
        if args.get("mix_only") == "1":
            continue
        dst = os.path.join(OUT, f"spamclaims-reel-check-{cut}.mp4")
        ffmpeg("-loglevel", "error", "-framerate", "30", "-i", os.path.join(frames, "%04d.png"), "-i", audio,
               "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
               "-r", "30", "-g", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", dst)
        print("wrote", dst, f"{os.path.getsize(dst) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
