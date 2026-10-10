"""Build Reel ad 4 ("The Swarm"): composite the Blender frames, mix the sound, encode for Instagram (24 fps).

python ad4/build4.py [skip_capture=1] [mix_only=1] [frames=../blender/frames/ad4] [name=spamclaims-reel-swarm] [lufs=-15]
Music edit (cue hits measured on the generated files):
  A1  cue_a, 5.7 % faster so its drum hit (5.38 s) lands on "Then..." (the swarm erupts) and its riser cuts (10.72 s)
      exactly on the STOP shockwave
  A2  cue_a's hit + drums (5.36-7.40 s) again on the dome shattering, driving the avalanche
  B   cue_b from 4.94 s on the orange turn, so its climax (12.95 s) lands as the shield forms
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
NAME = args.get("name", "spamclaims-reel-swarm")
LUFS = float(args.get("lufs", "-15"))
E = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
EV = E["events"]
DUR = E["frames"] / E["fps"]
N = int(round(DUR * SR))
STRETCH = (10.72 - 5.38) / (EV["stop"] - EV["erupt"])          # cue_a speed-up so both hits land


def db(v):
    return 10 ** (v / 20)


def read(path, peak=None):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        x = x.reshape(-1, w.getnchannels())
        sr = w.getframerate()
    x = x.mean(axis=1)
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


def seg(x, a, b=None):
    return x[int(a * SR): (int(b * SR) if b is not None else None)]


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
    ffmpeg("-i", raw, "-af", "acompressor=threshold=-22dB:ratio=3:attack=4:release=110:makeup=1,"
                             "aecho=0.8:0.5:60|140:0.12|0.07", comp)      # a touch of trailer room on the narrator
    with wave.open(comp) as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
    os.remove(raw); os.remove(comp)
    vo = np.zeros((N, 2), dtype=np.float32)
    vo[: min(N, len(y))] = y[:N] * 2.0

    # music
    mu = np.zeros((N, 2), dtype=np.float32)
    fast = os.path.join(AUDIO, "_cue_a_fast.wav")
    ffmpeg("-i", os.path.join(AUDIO, "cue_a.wav"), "-af", f"atempo={STRETCH:.5f}", "-ar", str(SR), "-ac", "1", fast)
    a_fast = read(fast)
    os.remove(fast)
    off = 5.38 / STRETCH - EV["erupt"]                           # the stretched cue's time at t = 0
    a1 = seg(a_fast, off, off + EV["stop"])
    place(mu, fade(a1, 0.8, 0.012), 0.0, -4.0)
    a = read(os.path.join(AUDIO, "cue_a.wav"))
    a2 = seg(a, 5.36, 7.40)
    place(mu, fade(a2, 0.004, 0.45), EV["shatter"] - 0.02, -5.0)
    b = read(os.path.join(AUDIO, "cue_b.wav"))
    b1 = seg(b, 4.94, 4.94 + (DUR - EV["orange"]))
    place(mu, fade(b1, 0.35, 0.8), EV["orange"], -3.0)

    # effects
    fx = np.zeros((N, 2), dtype=np.float32)
    clip = {k: read(os.path.join(AUDIO, f"sfx_{k}.wav"), peak=1.0) for k in
            ["wind", "ping", "swarm", "flyby", "dings", "buzz", "sent", "boom", "freeze", "shatter", "avalanche", "power",
             "cityboom", "lanterns", "triumph", "chime"]}
    place(fx, fade(seg(clip["wind"], 0, 6.3), 0.5, 1.2), 0.0, -17)
    place(fx, fade(seg(clip["wind"], 1.0, 7.5), 0.8, 1.5), 13.3, -19)
    place(fx, clip["ping"], EV["one"] - 0.05, -9)
    place(fx, clip["swarm"], EV["erupt"] + 0.25, -7, pan=-0.2)
    place(fx, clip["swarm"], EV["stream"] - 0.05, -10, pan=0.25)
    for t, g in ((4.05, -9), (5.45, -8), (13.25, -9)):
        place(fx, clip["flyby"], t, g)
    place(fx, clip["dings"], 6.15, -12)
    place(fx, clip["buzz"], 6.35, -15)
    place(fx, clip["sent"], EV["stop"] - 0.12, -10)
    place(fx, clip["boom"], EV["stop"] - 0.02, -2.5)
    place(fx, clip["freeze"], EV["freeze"] - 0.05, -8)
    place(fx, clip["shatter"], EV["shatter"] - 0.02, -6.0)
    place(fx, clip["avalanche"], EV["shatter"] + 0.17, -11)
    place(fx, clip["power"], EV["orange"] - 0.05, -8)
    place(fx, clip["cityboom"], EV["city"] - 0.1, -6)
    place(fx, clip["lanterns"], EV["lanterns"] + 0.1, -11)
    place(fx, clip["lanterns"], EV["lanterns"] + 2.2, -12, pan=0.2)
    place(fx, clip["triumph"], EV["shield"] - 0.05, -7)
    place(fx, clip["chime"], EV["end"] + 0.3, -8)

    talk = np.clip(follower(vo.mean(axis=1), 0.04, 0.35) / 0.05, 0, 1)[:, None]
    out = vo + fx * (1 - 0.55 * talk) + mu * (1 - 0.5 * talk)
    pre = os.path.join(AUDIO, "_premix.wav")
    write(pre, out * 0.5)
    i, _ = loudness(pre)
    mixed = os.path.join(AUDIO, "mix.wav")
    ffmpeg("-i", pre, "-af", f"volume={LUFS - i:.2f}dB,alimiter=limit=0.87:attack=3:release=80:level=disabled", "-ar", str(SR),
           "-c:a", "pcm_s16le", mixed)
    os.remove(pre)
    i2, pk = loudness(mixed)
    print(f"mix: {i2:.1f} LUFS, peak {pk:.1f} dBFS, {DUR:.2f} s (cue_a x{STRETCH:.4f})")
    return mixed


def main():
    frames = args.get("frames", "../blender/frames/ad4")
    out_frames = os.path.join(OUT, "frames")
    if args.get("mix_only") != "1" and args.get("skip_capture") != "1":
        subprocess.run(["node", os.path.join(HERE, "capture4.cjs"), "--frames", frames, "--out", "ad4/out/frames"], check=True, cwd=ROOT)
    mixed = mix()
    if args.get("mix_only") == "1":
        return
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f"{NAME}.mp4")
    ffmpeg("-loglevel", "error", "-framerate", str(E["fps"]), "-i", os.path.join(out_frames, "%04d.png"), "-i", mixed,
           "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-r", str(E["fps"]), "-g", str(E["fps"]), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
           "-shortest", dst)
    print("wrote", dst, f"{os.path.getsize(dst) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
