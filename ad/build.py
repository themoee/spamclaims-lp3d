"""Build the Reel: composite the frames, mix the audio, encode to Instagram's spec.

python ad/build.py [name=spamclaims-reel-15s] [skip_capture=1]
  1. node ad/capture.cjs          -> ad/out/frames/NNNN.png (render + captions + end card), unless skip_capture=1
  2. python ad/sfx.py             -> ad/audio/sfx.wav
  3. mix: voice (ad/audio/vo.wav, if present) on top, music bed (ad/audio/music.wav, if present) ducked under it
  4. ffmpeg: H.264 high, 1080x1920, 30 fps, yuv420p, AAC 192k 48 kHz, faststart -> ad/out/<name>.mp4
"""
import os
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
NAME = args.get("name", "spamclaims-reel-15s")


def read(path, channels=2):
    if not os.path.exists(path):
        return None
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        c = w.getnchannels()
    x = x.reshape(-1, c)
    if c == 1 and channels == 2:
        x = np.repeat(x, 2, axis=1)
    return x


def fit(x, n):
    if x is None:
        return np.zeros((n, 2), dtype=np.float32)
    if len(x) >= n:
        return x[:n]
    return np.concatenate([x, np.zeros((n - len(x), x.shape[1]), dtype=x.dtype)])


def envelope(x, win=0.12):
    """Smoothed loudness of a track (for ducking)."""
    m = np.abs(x).mean(axis=1)
    k = int(win * SR)
    return np.convolve(m, np.ones(k) / k, mode="same")


def main():
    if args.get("skip_capture") != "1":
        subprocess.run(["node", os.path.join(HERE, "capture.cjs")], check=True, cwd=ROOT)
    subprocess.run([sys.executable, os.path.join(HERE, "sfx.py")], check=True)

    sfx = read(os.path.join(AUDIO, "sfx.wav"))
    n = len(sfx)
    vo = fit(read(os.path.join(AUDIO, "vo.wav")), n)
    music = read(os.path.join(AUDIO, "music.wav"))
    music = fit(music, n)
    e = envelope(vo)
    talk = np.clip(e / (np.max(e) + 1e-9) * 6, 0, 1)[:, None]       # 1 while the voice is speaking
    mix = (1.0 * vo
           + 0.62 * sfx * (1 - 0.35 * talk)
           + 0.30 * music * (1 - 0.65 * talk))
    peak = np.max(np.abs(mix))
    mix *= 0.89 / (peak + 1e-9)                                        # -1 dBFS peak
    mixed = os.path.join(AUDIO, "mix.wav")
    with wave.open(mixed, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())

    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, f"{NAME}.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-framerate", "30", "-i", os.path.join(OUT, "frames", "%04d.png"),
        "-i", mixed,
        "-c:v", "libx264", "-profile:v", "high", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
        "-r", "30", "-g", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", dst,
    ], check=True)
    print("wrote", dst, f"{os.path.getsize(dst) / 1e6:.1f} MB",
          "| voice:", "yes" if np.max(np.abs(vo)) > 0 else "no", "| music:", "yes" if np.max(np.abs(music)) > 0 else "no")


if __name__ == "__main__":
    main()
