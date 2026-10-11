"""Build Reel ad 6 ("Storytime"): composite the frames, mix, encode (24 fps).

python ad6/build6.py [skip_capture=1] [mix_only=1] [name=spamclaims-reel-storytime] [lufs=-15]
  1. node ad6/capture6.cjs: the 3D shots + the iOS screens, stickers, captions, end card -> ad6/out/frames
  2. the mix: Dre (narrator) and his friends (a light phone EQ, they are "in the story"); the trap score placed so its
     drop lands on the $500 slam (music_full.wav, offset measured with a downbeat analysis) and fading out under the last
     line; the effects on every beat (buzz, texts in and out, the STOP ring, keys, stamps, the riser + boom + sparkle,
     the record scratch, the group chat, the checklist ticks, the screenshot shutter, the chime); music ducked under voices
  3. ffmpeg: H.264 high, 1080x1920, 24 fps, yuv420p, AAC 192k, faststart -> ad6/out/<name>.mp4
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
NAME = args.get("name", "spamclaims-reel-storytime")
LUFS = float(args.get("lufs", "-15"))
MUSIC_OFFSET = float(args.get("music_offset", "6.93"))     # music time of video 0: the drop (23.02 s) -> the $500 slam
# after the drop the edit runs longer than the track: one 2-bar phrase (strong downbeats at both ends, measured) plays twice,
# so the score still fades out under the last line
LOOP = (29.595, 32.885)
E = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
EV = E["events"]
DUR = E["frames"] / E["fps"]
N = int(round(DUR * SR))
AT = {v["line"]: v["at"] for v in E["voice"]}


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


def processed(src, af):
    """Run a mono line through an ffmpeg filter chain, back as numpy."""
    a, b = os.path.join(AUDIO, "_in.wav"), os.path.join(AUDIO, "_out.wav")
    with wave.open(a, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(src, -1, 1) * 32767).astype(np.int16).tobytes())
    ffmpeg("-i", a, "-af", af, "-ar", str(SR), "-ac", "1", b)
    y = read(b)
    os.remove(a); os.remove(b)
    return y


def mix():
    # voices: Dre centred and compressed; the friends a little phone-y and spread
    vo = np.zeros((N, 2), dtype=np.float32)
    for line, at in AT.items():
        x = read(os.path.join(AUDIO, "fast", f"{line}.wav"))
        if line.startswith("F"):
            x = processed(x, "highpass=f=240,lowpass=f=6500,acompressor=threshold=-20dB:ratio=3:attack=5:release=100:makeup=2")
            place(vo, x, at, -2.0, pan={"F1": -0.35, "F2": 0.35, "F3": 0.0}[line])
        else:
            x = processed(x, "acompressor=threshold=-22dB:ratio=2.5:attack=5:release=120:makeup=1")
            place(vo, x, at, 0.0)

    fx = np.zeros((N, 2), dtype=np.float32)
    names = ["buzz", "tone", "sent", "recv", "key", "tap", "tick", "pop", "shutter", "swipe", "scratch", "whoosh", "boom",
             "chime", "room", "sparkle", "riser", "hit", "buzzer", "marker", "gasp"]
    c = {k: read(os.path.join(AUDIO, f"sfx_{k}.wav"), peak=1.0) for k in names}
    # the hook: the phone buzzing in bed, the bolt upright, "$500 EACH"
    for t in EV["buzz"]:
        place(fx, c["buzz"], t - 0.02, -12)
        place(fx, c["tone"], t + 0.03, -17)
    place(fx, c["pop"], 0.15, -16)
    place(fx, c["whoosh"], EV["boltup"] - 0.05, -13)
    place(fx, c["hit"], EV["each"] - 0.01, -9)
    place(fx, c["pop"], EV["each"], -14, pan=0.2)
    # the thread: STOP sent, the opt-out reply, the texts that kept coming
    place(fx, c["swipe"], EV["thread"] - 0.03, -17)
    place(fx, c["sent"], EV["stop"], -12)
    place(fx, c["marker"], EV["stop"] + 0.12, -18)
    place(fx, c["recv"], EV["unsub"], -14)
    for k, t in enumerate(EV["after"]):
        place(fx, c["recv"], t, -14 + k, pan=-0.15)
        place(fx, c["buzz"], t - 0.02, -13)
    for t in (EV["thread_end"] + 0.08, EV["thread_end"] + 0.62):     # still buzzing in his hand
        place(fx, c["buzz"], t, -12)
    # 2 AM: the room, typing, the tap on the result
    bed = c["room"]
    seg = np.concatenate([bed, bed])[: int((EV["statute"] - EV["twoam"] + 0.6) * SR)]
    place(fx, fade(seg, 0.3, 0.4), EV["twoam"] - 0.1, -24)
    place(fx, c["pop"], EV["clock"] - 0.05, -17)
    for k in range(12):
        place(fx, pitch(c["key"], [0, 1, -1, 2, 0, -2, 1, 0, 2, -1, 0, 1][k]), EV["search"] + 0.12 + k * 0.07, -20)
    place(fx, c["tap"], EV["statute"] - 0.22, -14)
    # the law: the card comes up, the stamp, the marker
    place(fx, c["whoosh"], EV["statute"] - 0.02, -16)
    place(fx, c["hit"], EV["federal"], -12)
    place(fx, c["marker"], EV["sweep"] + 0.1, -13)
    place(fx, c["marker"], EV["sweep"] + 0.65, -14)
    # the $500: riser into the slam, boom, sparkle
    r = c["riser"]
    place(fx, fade(r, 0.2, 0.0), EV["money"] - len(r) / SR, -11)
    place(fx, c["boom"], EV["money"] - 0.01, -3)
    place(fx, c["sparkle"], EV["money"] + 0.03, -9)
    place(fx, c["pop"], EV["shock"] + 0.1, -15)
    # skeptic: the record scratch, the red flags
    place(fx, c["scratch"], EV["scratch"], -8)
    place(fx, c["buzzer"], EV["scam"], -13)
    # the group chat
    place(fx, c["whoosh"], EV["chat"] - 0.04, -15)
    for t, who, kind, text in E["chat"]["items"]:
        place(fx, c["sent"] if who == "me" else c["recv"], t, -14, pan=0.25 if who == "me" else -0.25)
    place(fx, c["pop"], E["chat"]["tapback"][0], -13)
    place(fx, c["gasp"], AT["F3"] - 0.05, -20)
    # 100% real, 100% legal, fr fr
    place(fx, c["hit"], EV["real"] - 0.05, -11)
    place(fx, c["hit"], EV["legal"] - 0.05, -11)
    place(fx, c["hit"], EV["frfr"] + 0.05, -10)
    place(fx, c["sparkle"], EV["frfr"] + 0.08, -21)
    # the catch
    place(fx, c["swipe"], EV["catch"] - 0.02, -18)
    for k in ("c1", "c2", "c3"):
        place(fx, c["tick"], EV[k], -12)
    place(fx, c["pop"], EV["mine"] - 0.05, -13, pan=0.3)            # his 2:06 AM text, the receipt
    place(fx, c["marker"], EV["mine"] + 0.15, -16)
    place(fx, c["whoosh"], EV["vary1"] - 0.05, -24)
    # the call to action: screenshot, the landing page, the tap
    place(fx, c["swipe"], EV["cta"] - 0.02, -18)
    place(fx, c["shutter"], EV["shot"] - 0.01, -8)
    place(fx, c["swipe"], EV["web"] - 0.03, -17)
    place(fx, c["tap"], EV["web"] + 1.35, -13)
    # the close
    place(fx, c["hit"], EV["law"] - 0.03, -16)
    place(fx, c["chime"], EV["end"] + 0.1, -8)

    mu = np.zeros((N, 2), dtype=np.float32)
    m = read(os.path.join(AUDIO, "music_full.wav"))
    xf = int(0.02 * SR)
    a0, l0, l1 = int(MUSIC_OFFSET * SR), int(LOOP[0] * SR) - xf // 2, int(LOOP[1] * SR) - xf // 2
    parts = [m[a0:l1 + xf], m[l0:l1 + xf], m[l1:]]
    seg = parts[0]
    for p_ in parts[1:]:                                   # 20 ms crossfades, just ahead of the downbeats
        r = np.linspace(0, 1, xf, dtype=np.float32)
        seg = np.concatenate([seg[:-xf], seg[-xf:] * (1 - r) + p_[:xf] * r, p_[xf:]])
    seg = seg[:N]
    place(mu, fade(seg, 0.03, 0.5), 0.0, -7.0)

    talk = np.clip(follower(vo.mean(axis=1), 0.04, 0.35) / 0.05, 0, 1)[:, None]
    out = vo + fx * (1 - 0.2 * talk) + mu * (1 - 0.5 * talk)
    pre = os.path.join(AUDIO, "_premix.wav")
    write(pre, out * 0.5)
    i, _ = loudness(pre)
    mixed = os.path.join(AUDIO, "mix.wav")
    ffmpeg("-i", pre, "-af", f"volume={LUFS - i:.2f}dB,alimiter=limit=0.84:attack=3:release=80:level=disabled", "-ar", str(SR),
           "-c:a", "pcm_s16le", mixed)
    os.remove(pre)
    i2, pk = loudness(mixed)
    print(f"mix: {i2:.1f} LUFS, peak {pk:.1f} dBFS, {DUR:.2f} s")
    return mixed


def main():
    if args.get("mix_only") != "1" and args.get("skip_capture") != "1":
        subprocess.run(["node", os.path.join(HERE, "capture6.cjs")], check=True, cwd=ROOT)
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
