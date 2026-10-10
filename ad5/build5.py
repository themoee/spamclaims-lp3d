"""Build Reel ad 5 ("2:13 AM"): film-look post pass, overlays, the mix, the encode (24 fps).

python ad5/build5.py [skip_post=1] [skip_capture=1] [mix_only=1] [name=spamclaims-reel-213am] [lufs=-15]
  1. python ad5/post5.py: bloom, chromatic aberration, vignette, grain -> ad5/out/post
  2. node ad5/capture5.cjs: captions, the $500 card, the end card -> ad5/out/frames
  3. the mix: Roger's narration; a quiet bedroom (room tone); the phone rattling on walnut with each text and a soft
     text tone; pops as the texts after STOP are numbered, a tick on the STOP outline; the screenshot shutter; swipes;
     the SpamClaims chime; the felt-piano score (its first note on the phone waking); music ducked under the voice
  4. ffmpeg: H.264 high, 1080x1920, 24 fps, yuv420p, AAC 192k, faststart -> ad5/out/<name>.mp4
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
NAME = args.get("name", "spamclaims-reel-213am")
LUFS = float(args.get("lufs", "-15"))
E = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
EV = E["events"]
DUR = E["frames"] / E["fps"]
N = int(round(DUR * SR))


def db(v):
    return 10 ** (v / 20)


def read(path, peak=None):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        x = x.reshape(-1, w.getnchannels()).mean(axis=1)
        sr = w.getframerate()
    if sr != SR:
        x = np.interp(np.arange(0, len(x), sr / SR), np.arange(len(x)), x).astype(np.float32)
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


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    if fin:
        k = min(len(x), int(fin * SR)); x[:k] *= np.linspace(0, 1, k)
    if fout:
        k = min(len(x), int(fout * SR)); x[len(x) - k:] *= np.linspace(1, 0, k)
    return x


def pitch(x, semitones):
    r = 2 ** (semitones / 12)
    return np.interp(np.arange(0, len(x) - 1, r), np.arange(len(x)), x).astype(np.float32)


def follower(x, attack=0.03, release=0.3, rate=1000):
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


def mix():
    vo = np.zeros((N, 2), dtype=np.float32)
    for v in E["voice"]:
        place(vo, read(os.path.join(AUDIO, "lines", f"{v['line']}.wav")), v["at"], 0.0)
    raw, comp = os.path.join(AUDIO, "_vo_raw.wav"), os.path.join(AUDIO, "_vo_comp.wav")
    write(raw, vo * 0.5)
    ffmpeg("-i", raw, "-af", "acompressor=threshold=-22dB:ratio=2.5:attack=5:release=120:makeup=1", comp)
    with wave.open(comp) as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
    os.remove(raw); os.remove(comp)
    vo = np.zeros((N, 2), dtype=np.float32)
    vo[: min(N, len(y))] = y[:N] * 2.0

    fx = np.zeros((N, 2), dtype=np.float32)
    c = {k: read(os.path.join(AUDIO, f"sfx_{k}.wav"), peak=1.0) for k in
         ["room", "buzz", "tone", "pop", "tick", "shutter", "chime", "swipe"]}
    room = c["room"]
    bed = np.concatenate([room, room[int(0.5 * SR):], room[int(1.0 * SR):]])[:N]   # long enough for the whole ad
    place(fx, fade(bed, 0.8, 1.5), 0.0, -24)
    for t in EV["buzz"]:
        place(fx, c["buzz"], t - 0.02, -8)
        place(fx, c["tone"], t + 0.03, -15)
    place(fx, c["swipe"], EV["thread"] - 0.03, -20)
    for k, t in enumerate(EV["badges"]):
        place(fx, pitch(c["pop"], [0, 2, 4][k]), t - 0.01, -15, pan=0.2)
    place(fx, c["tick"], EV["evidence"], -15)
    place(fx, c["shutter"], EV["shot"] - 0.01, -8)
    place(fx, c["swipe"], EV["web"] - 0.03, -19)
    place(fx, c["chime"], EV["end"] + 0.25, -9)

    mu = np.zeros((N, 2), dtype=np.float32)
    m = read(os.path.join(AUDIO, "music.wav"))
    seg = m[int(0.4 * SR): int(0.4 * SR) + N]
    place(mu, fade(seg, 0.5, 1.4), 0.0, -6.0)

    talk = np.clip(follower(vo.mean(axis=1), 0.04, 0.35) / 0.05, 0, 1)[:, None]
    out = vo + fx * (1 - 0.2 * talk) + mu * (1 - 0.45 * talk)
    pre = os.path.join(AUDIO, "_premix.wav")
    write(pre, out * 0.5)
    i, _ = loudness(pre)
    mixed = os.path.join(AUDIO, "mix.wav")
    ffmpeg("-i", pre, "-af", f"volume={LUFS - i:.2f}dB,alimiter=limit=0.87:attack=3:release=80:level=disabled", "-ar", str(SR),
           "-c:a", "pcm_s16le", mixed)
    os.remove(pre)
    i2, pk = loudness(mixed)
    print(f"mix: {i2:.1f} LUFS, peak {pk:.1f} dBFS, {DUR:.2f} s")
    return mixed


def main():
    if args.get("mix_only") != "1":
        if args.get("skip_post") != "1":
            subprocess.run([sys.executable, os.path.join(HERE, "post5.py")], check=True, cwd=ROOT)
        if args.get("skip_capture") != "1":
            subprocess.run(["node", os.path.join(HERE, "capture5.cjs")], check=True, cwd=ROOT)
    mixed = mix()
    if args.get("mix_only") == "1":
        return
    dst = os.path.join(OUT, f"{NAME}.mp4")
    ffmpeg("-loglevel", "error", "-framerate", str(E["fps"]), "-i", os.path.join(OUT, "frames", "%04d.png"), "-i", mixed,
           "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-r", str(E["fps"]), "-g", str(E["fps"]), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
           "-shortest", dst)
    print("wrote", dst, f"{os.path.getsize(dst) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
