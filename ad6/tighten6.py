"""Ad 6: TikTok pacing for the voice lines. Silences inside a line are cut down (jump-cut style: short inside a
sentence, a beat after a full stop), then Dre's lines are sped up slightly (pitch kept). Word and character timings are
mapped through the same edits, so captions and the lip sync stay on the words.

python ad6/tighten6.py [tempo=1.08]
  ad6/audio/lines/<id>.wav + lines.json -> ad6/audio/fast/<id>.wav + ad6/audio/fast.json
"""
import json
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio")
SRC, DST = os.path.join(AUDIO, "lines"), os.path.join(AUDIO, "fast")
os.makedirs(DST, exist_ok=True)
args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
TEMPO = float(args.get("tempo", "1.08"))
SR = 48000
KEEP_TEMPO = {"V3", "V9", "F1", "F2", "F3"}     # the 2 AM line and the closing line keep their pace; friends too
SPECIAL = {"V9": 0.42}                         # the closing line keeps a dramatic beat
IN_SENTENCE, AFTER_STOP = 0.07, 0.15           # target pause lengths (s)


def read(p):
    with wave.open(p) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1)


def write(p, x):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def silences(x, min_len=0.14):
    h = int(0.01 * SR)
    n = len(x) // h
    rms = np.sqrt((x[: n * h].reshape(n, h) ** 2).mean(axis=1) + 1e-12)
    thr = max(np.percentile(rms, 95) * 0.06, 10 ** (-48 / 20))
    quiet = rms < thr
    out, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.01 >= min_len and i > 0 and j < n:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


def main():
    meta = json.load(open(os.path.join(AUDIO, "lines.json"), encoding="utf-8"))
    res = {}
    for lid, m in meta.items():
        x = read(os.path.join(SRC, f"{lid}.wav"))
        ends = [w["e"] for w in m["words"] if w["w"][-1:] in ".?!"]
        cuts = []                                   # (start, end, new_len)
        for a, b in silences(x):
            stop = any(abs(e - a) < 0.25 for e in ends)
            tgt = SPECIAL.get(lid, AFTER_STOP if stop else IN_SENTENCE)
            if b - a > tgt + 0.02:
                cuts.append((a, b, tgt))
        # rebuild with 8 ms crossfades at every join, recording a time map
        pieces, tmap, t_new, cur = [], [(0.0, 0.0)], 0.0, 0.0
        fade = int(0.008 * SR)
        for a, b, tgt in cuts:
            keep_end = a + tgt / 2
            resume = b - tgt / 2
            seg = x[int(cur * SR): int(keep_end * SR)].copy()
            pieces.append(seg)
            t_new += len(seg) / SR
            tmap.append((keep_end, t_new))
            tmap.append((resume, t_new))
            cur = resume
        pieces.append(x[int(cur * SR):].copy())
        t_new += len(pieces[-1]) / SR
        tmap.append((len(x) / SR, t_new))
        y = pieces[0]
        for p in pieces[1:]:
            k = min(fade, len(y), len(p))
            r = np.linspace(0, 1, k, dtype=np.float32)
            y = np.concatenate([y[:-k], y[-k:] * (1 - r) + p[:k] * r, p[k:]]) if k else np.concatenate([y, p])
        tempo = 1.0 if lid in KEEP_TEMPO else TEMPO
        tmp = os.path.join(DST, f"_{lid}.wav")
        out = os.path.join(DST, f"{lid}.wav")
        write(tmp, y)
        if tempo != 1.0:
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-af", f"atempo={tempo}", "-ar", str(SR), out], check=True)
            os.remove(tmp)
        else:
            os.replace(tmp, out)
        ot, nt = np.array([p[0] for p in tmap]), np.array([p[1] for p in tmap])

        def mp(t):
            return round(float(np.interp(t, ot, nt)) / tempo, 3)

        words = [{"w": w["w"], "s": mp(w["s"]), "e": mp(w["e"])} for w in m["words"]]
        chars = [[c, mp(s), mp(e)] for c, s, e in m.get("chars", [])]
        dur = len(read(out)) / SR
        res[lid] = {"dur": round(dur, 3), "words": words, "chars": chars, "heard": m.get("heard"), "voice": m.get("voice"),
                    "cut": round(len(x) / SR - len(y) / SR, 2), "tempo": tempo}
        print(f"{lid}: {m['dur']:5.2f}s -> {dur:5.2f}s  ({len(cuts)} pauses cut, tempo {tempo})")
    json.dump(res, open(os.path.join(AUDIO, "fast.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
