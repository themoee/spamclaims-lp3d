"""Build Reel ad 2 ("Did you mean START?"): composite the frames, mix the sound, encode for Instagram.

python ad2/build2.py [name=spamclaims-reel-start] [skip_capture=1] [mix_only=1] [lufs=-15]
  1. node ad2/capture2.cjs -> ad2/out/frames/NNNN.png (Blender phone + stickers + money card + end card)
  2. the mix: voice lines on their beats (the "me" lines shifted so the spoken STOP lands with its bubble), the comedy
     groove until the record scratch, a beat of silence, the payoff groove from the screenshot flash to its final chord,
     ElevenLabs effects on every cue; the music ducks under the voices
  3. loudness: -15 LUFS integrated, -1 dBFS ceiling (ffmpeg ebur128 + alimiter)
  4. ffmpeg: H.264 high, 1080x1920, 30 fps, yuv420p, AAC 192k 48 kHz, faststart -> ad2/out/<name>.mp4
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
NAME = args.get("name", "spamclaims-reel-start")
LUFS = float(args.get("lufs", "-15"))
E = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
L = json.load(open(os.path.join(AUDIO, "lines.json"), encoding="utf-8"))
DUR = E["frames"] / E["fps"]
N = int(round(DUR * SR))
R, END = E["reveal"], E["endcard"]

# per-line gain (dB): evens out the three voices, keeps the escalation (the shout stays loudest)
LINE_DB = {"B1": 0, "B2": 3, "M1": 0, "M2": 0, "M3": 0, "M4": 2, "M5": 3, "N1": 8, "N2": 7}
MUSIC_B_FROM = 2.045      # s into music_b2: just before a downbeat, so the groove drops in on the screenshot flash


def db(v):
    return 10 ** (v / 20)


def read(name, peak=None):
    with wave.open(os.path.join(AUDIO, name)) as w:
        assert w.getframerate() == SR, name
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
    """Mix mono clip x into the stereo track at `at` seconds (constant power pan, -1 left .. 1 right)."""
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
        k = min(len(x), int(fin * SR))
        x[:k] *= np.linspace(0, 1, k)
    if fout:
        k = min(len(x), int(fout * SR))
        x[len(x) - k:] *= np.linspace(1, 0, k)
    return x


def follower(x, attack=0.03, release=0.30, rate=1000):
    """Attack/release envelope of |x| (mono), computed at a 1 kHz control rate and returned at audio rate."""
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


def window(t0, t1, ramp=0.08):
    """1 inside [t0, t1], 0 outside, with linear ramps (a per-sample gain curve)."""
    t = np.arange(N) / SR
    return np.clip(np.minimum((t - t0) / ramp + 1, (t1 - t) / ramp + 1), 0, 1).astype(np.float32)


def ffmpeg(*a):
    return subprocess.run(["ffmpeg", "-y", "-hide_banner", *a], check=True, capture_output=True, text=True)


def loudness(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    tail = err[err.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", tail).group(1))
    pk = float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail).group(1))
    return i, pk


def onset(x, rel_db):
    """When a line's 5 ms RMS first comes within rel_db of its peak (speech-to-text word starts are too loose)."""
    h = SR // 200
    r = np.sqrt(np.mean(x[: len(x) // h * h].reshape(-1, h) ** 2, axis=1))
    return float(np.where(r > r.max() * db(rel_db))[0][0] * h / SR)


def voice_track():
    vo = np.zeros((N, 2), dtype=np.float32)
    beats = {b["line"]: b["at"] for b in E["voice"]}
    placed = []
    prev_end = 0.0
    for lid, at in sorted(beats.items(), key=lambda kv: kv[1]):
        x = read(f"lines/{lid}.wav")
        if lid.startswith("M"):
            at = at + 0.03 - onset(x, -6)            # the vowel of "Stop" lands with the sent bubble (not the s-hiss)
        elif lid == "B2":
            at = at + 0.13 - onset(x, -20)           # the brand reads its text as it arrives
        if at + onset(x, -30) < prev_end:
            print(f"  warning: {lid} overlaps the previous line by {prev_end - at:.2f} s")
        place(vo, x, at, LINE_DB[lid])
        placed.append((lid, at, at + len(x) / SR))
        prev_end = at + len(x) / SR - onset(x[::-1], -30)       # where the speech (not the clip) ends
    # gentle bus compression so the narrator and the shout sit in the same space
    raw = os.path.join(AUDIO, "_vo_raw.wav")
    comp = os.path.join(AUDIO, "_vo_comp.wav")
    write(raw, vo * 0.5)
    ffmpeg("-i", raw, "-af", "acompressor=threshold=-24dB:ratio=3:attack=4:release=90:makeup=1", comp)
    with wave.open(comp) as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32).reshape(-1, 2) / 32768
    os.remove(raw)
    os.remove(comp)
    out = np.zeros((N, 2), dtype=np.float32)
    out[: min(N, len(y))] = y[:N] * 2.0
    return out, placed


def sfx_track():
    fx = np.zeros((N, 2), dtype=np.float32)
    clip = {k: read(f"sfx_{k}.wav", peak=1.0) for k in
            ["drop", "land", "incoming", "ping", "sent", "scratch", "spin", "shutter", "chaching", "coin", "whoosh_out",
             "jingle", "crickets"]}
    for c in E["cues"]:
        k, at = c["kind"], c["at"]
        if k == "drop":
            place(fx, clip["drop"], at, -16)
        elif k == "land":
            place(fx, clip["land"], at, -13)
        elif k == "sent":
            place(fx, clip["sent"], at, -13 if c.get("level") == 2 else -17)
        elif k == "incoming":
            place(fx, clip["incoming"], at, -19)
            place(fx, clip["ping"], at + 0.01, -15)
        elif k == "scratch":
            place(fx, clip["scratch"], at - 0.02, -5)
        elif k == "whoosh_spin":
            place(fx, clip["spin"], at, -11)
        elif k == "shutter":
            place(fx, clip["shutter"], at - 0.01, -9)
        elif k == "pop_money":
            place(fx, clip["chaching"], at - 0.02, -8)
        elif k == "whoosh_out":
            place(fx, clip["whoosh_out"], at, -13)
        elif k == "jingle":
            place(fx, clip["jingle"], at, -9)
    # crickets: the 2 AM text arrives to an awkward silence
    two_am = next(b["at"] for b in E["beats"] if b["kind"] == "state" and b.get("who") == "them" and b.get("level") == 3)
    place(fx, fade(clip["crickets"][: int(0.95 * SR)], 0.05, 0.3), two_am + 0.16, -21, pan=0.25)
    # a coin clink as each text after STOP lights up, from where it sits on the screen (the left column)
    n = 3
    for k in range(n):
        t = R["boxes_from"] + k * (R["boxes_to"] - R["boxes_from"]) / (n - 1)
        place(fx, clip["coin"], t, -14, pan=-0.15 + 0.1 * k)
    for k, (dt, pan) in enumerate([(0.10, -0.5), (0.17, 0.45), (0.26, -0.25), (0.33, 0.3)]):
        place(fx, clip["coin"], R["money_at"] + dt, -19 - k, pan=pan)    # the coin shower after the cha-ching
    return fx, two_am


def music_track(two_am):
    m = np.zeros((N, 2), dtype=np.float32)
    a = read("music_a.wav")
    cut = int(R["scratch"] * SR)
    place(m, fade(a[:cut], 0.0, 0.012), 0.0, -7.5)                       # the comedy groove, stopped dead by the scratch
    b = read("music_b2.wav")
    i0 = int(MUSIC_B_FROM * SR)
    t_in = R["flash"] - 0.01
    seg = b[i0: i0 + int((DUR - t_in) * SR)]
    place(m, fade(seg, 0.006, 0.35), t_in, -5.5)                          # the payoff groove drops on the flash
    # the 2 AM crickets: the music holds its breath
    m *= (1 - 0.7 * window(two_am + 0.08, two_am + 0.85, 0.1))[:, None]
    return m


def main():
    if args.get("mix_only") != "1" and args.get("skip_capture") != "1":
        subprocess.run(["node", os.path.join(HERE, "capture2.cjs")], check=True, cwd=ROOT)
    vo, placed = voice_track()
    fx, two_am = sfx_track()
    mu = music_track(two_am)
    talk = np.clip(follower(vo.mean(axis=1), 0.04, 0.32) / 0.05, 0, 1)[:, None]      # 1 while someone is talking
    hero = np.clip(follower(fx.mean(axis=1), 0.01, 0.25) / 0.2, 0, 1)[:, None]       # loud effects (scratch, cha-ching)
    mix = vo + fx * (1 - 0.3 * talk) + mu * (1 - 0.55 * talk) * (1 - 0.35 * hero)
    pre = os.path.join(AUDIO, "_premix.wav")
    write(pre, mix * 0.5)
    i, _ = loudness(pre)
    gain = LUFS - i
    mixed = os.path.join(AUDIO, "mix.wav")
    ffmpeg("-i", pre, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.87:attack=3:release=60:level=disabled", "-ar", str(SR),
           "-c:a", "pcm_s16le", mixed)
    os.remove(pre)
    i2, pk = loudness(mixed)
    print(f"mix: {i2:.1f} LUFS, peak {pk:.1f} dBFS, {DUR:.2f} s")
    for lid, a, b in placed:
        print(f"  {lid}: {a:6.2f} -> {b:6.2f}")
    if args.get("mix_only") == "1":
        return
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f"{NAME}.mp4")
    ffmpeg("-loglevel", "error", "-framerate", "30", "-i", os.path.join(OUT, "frames", "%04d.png"), "-i", mixed,
           "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
           "-r", "30", "-g", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", dst)
    print("wrote", dst, f"{os.path.getsize(dst) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
