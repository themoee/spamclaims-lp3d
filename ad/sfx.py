"""Original sound design for the Reel, synthesized from scratch (no Apple sounds, nothing licensed), placed on the
cues in ad/edit.json: notification dings, the STOP send, the freeze hit, the storm, shutter, scan, ticks, the logo.

python ad/sfx.py  ->  ad/audio/sfx.wav (48 kHz, stereo, 15 s)
If ad/audio/sfx_<kind>.wav files exist (e.g. from ElevenLabs sound effects), they replace the synthesized ones.
"""
import json
import os
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
edit = json.load(open(os.path.join(HERE, "edit.json"), encoding="utf-8"))
DUR = edit["duration"]
rng = np.random.default_rng(7)


def t_(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, attack=0.004, decay=0.25):
    t = np.arange(n) / SR
    return np.minimum(1.0, t / attack) * np.exp(-t / decay)


def lowpass(x, cutoff):
    """FFT brick-ish lowpass with a soft knee (fine for noise shaping)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1 / (1 + (lo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    return np.fft.irfft(X, len(x))


def ding(pitch=1.0, gain=1.0):
    t = t_(0.55)
    a = np.sin(2 * np.pi * 1568 * pitch * t) * env(len(t), 0.002, 0.13)
    b = 0.55 * np.sin(2 * np.pi * 2349 * pitch * t) * env(len(t), 0.002, 0.09)
    c = 0.25 * np.sin(2 * np.pi * 3136 * pitch * t) * env(len(t), 0.001, 0.05)
    return gain * 0.32 * (a + b + c)


def send():
    t = t_(0.28)
    n = rng.standard_normal(len(t))
    s = np.zeros_like(n)
    for k in range(6):                                    # a rising band: 6 slices, each a bit higher
        lo = 600 * (1.5 ** k)
        sl = slice(k * len(t) // 6, (k + 1) * len(t) // 6)
        s[sl] = bandpass(n, lo, lo * 2.2)[sl]
    return 0.22 * s * np.sin(np.pi * np.linspace(0, 1, len(t))) ** 1.5


def freeze():
    t = t_(1.6)
    boom = np.sin(2 * np.pi * (52 - 14 * t) * t) * env(len(t), 0.003, 0.35)
    shimmer = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6.28)) for f in (2093, 2637, 3136, 3951, 4699, 5274))
    shimmer *= env(len(t), 0.01, 0.55) * 0.09
    air = lowpass(rng.standard_normal(len(t)), 9000) * env(len(t), 0.002, 0.05) * 0.25
    return 0.55 * boom + shimmer + air


def storm(sec):
    t = t_(sec)
    brown = np.cumsum(rng.standard_normal(len(t)))
    brown = lowpass(brown - np.convolve(brown, np.ones(4800) / 4800, mode="same"), 900)
    brown /= np.max(np.abs(brown)) + 1e-9
    drone = np.sin(2 * np.pi * (55 + 40 * (t / sec) ** 2) * t) + 0.5 * np.sin(2 * np.pi * (110 + 80 * (t / sec) ** 2) * t)
    flutter = 0.5 + 0.5 * np.sin(2 * np.pi * (3 + 9 * t / sec) * t)
    ramp = (t / sec) ** 1.8
    return ramp * (0.42 * brown + 0.16 * drone * (0.6 + 0.4 * flutter))


def shutter():
    t = t_(0.18)
    n = rng.standard_normal(len(t))
    a = bandpass(n, 1500, 9000) * env(len(t), 0.0005, 0.012)
    b = np.zeros_like(n)
    k = int(0.045 * SR)
    b[k:] = (bandpass(n, 800, 6000) * env(len(t), 0.0005, 0.02))[: len(t) - k]
    return 0.5 * (a + 0.8 * b)


def scan(sec=1.15):
    t = t_(sec)
    f = 520 + 1300 * (t / sec)
    phase = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(phase) * (0.55 + 0.45 * np.sin(2 * np.pi * 28 * t))
    hiss = bandpass(rng.standard_normal(len(t)), 3000, 12000) * 0.35
    shape = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 0.7
    return 0.12 * (tone + hiss) * shape


def tick():
    t = t_(0.09)
    return 0.22 * np.sin(2 * np.pi * 2637 * t) * env(len(t), 0.001, 0.018)


def merge():
    t = t_(0.5)
    n = rng.standard_normal(len(t))
    s = np.concatenate([lowpass(n[i:i + 2400], 300 + 9000 * (i / len(t)) ** 2) for i in range(0, len(t), 2400)])[: len(t)]
    return 0.3 * s * (np.linspace(0, 1, len(t)) ** 2.5)


def pop():
    t = t_(2.2)
    thunk = np.sin(2 * np.pi * (90 - 30 * t) * t) * env(len(t), 0.002, 0.18)
    chord = sum(np.sin(2 * np.pi * f * t) * w for f, w in ((1047, 1.0), (1319, 0.8), (1568, 0.7), (2093, 0.35)))
    chord *= env(len(t), 0.006, 0.7) * 0.11
    return 0.6 * thunk + chord


def load_override(kind):
    p = os.path.join(HERE, "audio", f"sfx_{kind}.wav")
    if not os.path.exists(p):
        return None
    with wave.open(p) as w:
        assert w.getframerate() == SR, f"{p}: expected {SR} Hz"
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            x = x.reshape(-1, 2).mean(axis=1)
    return x


mix = np.zeros((int(DUR * SR) + SR, 2), dtype=np.float64)


def place(x, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    x = x[: max(0, len(mix) - i)]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    mix[i:i + len(x), 0] += gain * l * x
    mix[i:i + len(x), 1] += gain * r * x


OVR_GAIN = {"ding": 0.45, "ding_again": 0.6, "send": 0.6, "freeze": 0.62, "storm": 0.8, "shutter": 0.55, "scan": 0.32, "pop": 0.55, "jingle": 0.5}
dings = 0
for c in edit["cues"]:
    k, at = c["kind"], c["at"]
    custom = load_override("ding" if k == "ding_again" else k)
    if custom is not None:
        if k == "storm":                                     # fit the swell exactly into its window, hard cut at the edit
            n = int((c["until"] - at) * SR)
            custom = np.concatenate([custom, np.zeros(max(0, n - len(custom)))])[:n] * np.linspace(0.3, 1.0, n) ** 1.5
        place(custom, at, OVR_GAIN.get(k, 0.7))
        continue
    if k == "ding":
        place(ding(1.0 + 0.03 * dings), at, 0.9, pan=[-0.35, 0.3, -0.15, 0.4, 0.0][dings % 5])
        dings += 1
    elif k == "ding_again":
        place(ding(0.84, 1.25), at, 1.0)
    elif k == "send":
        place(send(), at - 0.05, 2.4, 0.2)
    elif k == "freeze":
        place(freeze(), at, 1.0)
    elif k == "storm":
        place(storm(c["until"] - at), at, 1.55)
    elif k == "shutter":
        place(shutter(), at, 1.9)
    elif k == "scan":
        place(scan(), at, 1.3)
    elif k == "tick":
        place(tick(), at, 2.0, 0.25)
    elif k == "merge":
        place(merge(), at - 0.35, 0.8)
    elif k == "pop":
        place(pop(), at, 1.0)
    elif k == "jingle":                                      # fallback if the ElevenLabs jingle is missing
        place(ding(1.25, 0.8), at, 0.7)

mix = mix[: int(DUR * SR)]
peak = np.max(np.abs(mix))
mix *= 0.7 / (peak + 1e-9)                                  # leave headroom for the voice and music
os.makedirs(os.path.join(HERE, "audio"), exist_ok=True)
out = os.path.join(HERE, "audio", "sfx.wav")
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote", out, f"{DUR:.1f} s, peak normalized to -3 dB")
