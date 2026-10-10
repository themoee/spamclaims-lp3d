"""Keep the tension part of ad/audio/music.wav (to the 9.4 s cut) and join a separately generated, sustained lift
for the money line and the end card, so the bed never dies before the last frame.

python ad/music_outro.py  ->  ad/audio/music.wav (15 s; the previous one is kept as music_tension_src.wav)
"""
import os
import shutil
import sys
import wave

import numpy as np

sys.argv = [sys.argv[0]]
import voice  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "audio")
SR = voice.SR
CUT, DUR = 9.40, 15.0

src = os.path.join(A, "music_tension_src.wav")
if not os.path.exists(src):
    shutil.copy(os.path.join(A, "music.wav"), src)
with wave.open(src) as w:
    tension = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

raw = voice.call("/v1/music?output_format=mp3_44100_128", {
    "prompt": "8 second confident uplifting modern electronic ad outro: warm synth chords, steady driving beat, "
              "hopeful and bold, sustained and continuous all the way through, full energy until the very last "
              "second, then one strong final hit. No vocals, no intro, no fade.",
    "music_length_ms": 8000}, accept="audio/mpeg")
lift = voice.mp3_to_np(raw)
print(f"lift {len(lift) / SR:.2f} s; rms per second:",
      " ".join(f"{float(np.sqrt(np.mean(lift[i * SR:(i + 1) * SR] ** 2))):.3f}" for i in range(int(len(lift) / SR))))

n_cut, n = int(CUT * SR), int(DUR * SR)
xf = int(0.08 * SR)
head = tension[:n_cut].copy()
tail = lift[: n - n_cut + xf].copy()
if len(tail) < n - n_cut + xf:
    tail = np.concatenate([tail, np.zeros(n - n_cut + xf - len(tail), dtype=np.float32)])
# level-match the lift to the tension part, then a short crossfade at the cut
r_head = np.sqrt(np.mean(head[-SR:] ** 2)) + 1e-9
r_tail = np.sqrt(np.mean(tail[: 2 * SR] ** 2)) + 1e-9
tail *= min(1.6, r_head / r_tail * 1.15)
ramp = np.linspace(0, 1, xf)
out = np.concatenate([head[:-xf], head[-xf:] * (1 - ramp) + tail[:xf] * ramp, tail[xf:]])[:n]
out[-int(0.35 * SR):] *= np.linspace(1, 0, int(0.35 * SR))       # land cleanly on the last frame
voice.write_wav(os.path.join(A, "music.wav"), out)
print("music.wav", f"{len(out) / SR:.2f} s; rms per second:",
      " ".join(f"{float(np.sqrt(np.mean(out[i * SR:(i + 1) * SR] ** 2))):.3f}" for i in range(15)))
