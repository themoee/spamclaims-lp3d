"""Ad 3 ("The 10-second check"): the timeline for both cuts, from the voice performances.

python ad3/edit3.py  ->  ad3/audio/fast/<id>.wav (the lines 8 % brisker, pitch kept) and ad3/edit_a.json, ad3/edit_b.json

Every scene is cued off a spoken word (word timings from the TTS alignment, scaled by the tempo), so the picture
always moves with the voice:
  hook      L1  the STOP is sent, the brand confirms the opt-out, then four more promos arrive ("kept texting")
  search    L2  back to the Messages list, the search field, S-T-O-P typed, the matching threads
  count     L3  tap the brand, the thread opens on the STOP, the texts after it get numbered (1-4)
  rules     4   the checklist (2+ texts, weeks after the STOP, a real company, last 4 years); cut B adds the
                statute card with the qualifier on screen
  upload    5   screenshot flash, the thumbnail flies to spamclaims.com (the landing page the ad links to)
  end       6   the end card: the landing page headline, free to check, the URL, the fine print
"""
import json
import os
import subprocess
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio")
FAST = os.path.join(AUDIO, "fast")
os.makedirs(FAST, exist_ok=True)
L = json.load(open(os.path.join(AUDIO, "lines.json"), encoding="utf-8"))
TEMPO = 1.08
FPS = 30
GAP = 0.14            # breath between lines
LEAD = 0.30           # the first frame already shows the thread; the voice comes in a beat later
TAIL = 1.35           # end card hold after the last word

CUTS = {"a": ["L1", "L2", "L3", "A4", "A5", "A6"], "b": ["L1", "L2", "L3", "B4", "B5", "A6"]}


def stretch(lid):
    src, dst = os.path.join(AUDIO, "lines", f"{lid}.wav"), os.path.join(FAST, f"{lid}.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", f"atempo={TEMPO}", "-ar", "48000", "-ac", "1", dst],
                   check=True)
    with wave.open(dst) as w:
        return w.getnframes() / w.getframerate()


def word(lid, at, key, nth=0):
    """Absolute time of the nth word starting with `key` (case-insensitive) in line `lid` placed at `at`."""
    hits = [w for w in L[lid]["words"] if w["w"].lower().strip(".,?!:").startswith(key.lower())]
    if not hits:
        raise KeyError(f"{key} not in {lid}")
    return round(at + hits[min(nth, len(hits) - 1)]["s"] / TEMPO, 3)


def build(cut):
    t = LEAD
    lines = []
    for lid in CUTS[cut]:
        dur = stretch(lid)
        lines.append({"id": lid, "at": round(t, 3), "dur": round(dur, 3),
                      "words": [{"w": w["w"], "s": round(t + w["s"] / TEMPO, 3), "e": round(t + w["e"] / TEMPO, 3)}
                                for w in L[lid]["words"]]})
        t += dur + GAP
    end = t - GAP + TAIL
    at = {x["id"][-1] if x["id"][0] in "AB" else x["id"][1]: x["at"] for x in lines}     # "1".."6" -> start
    ids = {str(k + 1): lid for k, lid in enumerate(CUTS[cut])}
    l1, l2, l3, l4, l5, l6 = (at[str(k)] for k in range(1, 7))
    W = lambda n, key, nth=0: word(ids[str(n)], at[str(n)], key, nth)    # noqa: E731
    stop_said = W(1, "stop")
    kept = W(1, "kept")
    hook = {"stop_sent": round(stop_said - 0.05, 3), "confirm": round(stop_said + 0.55, 3),
            "arrivals": [round(kept + 0.02 + 0.27 * k, 3) for k in range(4)]}
    search = {"back": round(W(2, "open") - 0.12, 3), "focus": W(2, "search"),
              "typed": [round(W(2, "stop") - 0.30 + 0.11 * k, 3) for k in range(4)], "results": round(W(2, "stop") + 0.22, 3)}
    tap = W(3, "tap")
    count0 = W(3, "count")
    count = {"tap": round(tap + 0.05, 3), "open": round(tap + 0.22, 3), "ring": round(W(3, "stop") - 0.05, 3),
             "badges": [round(count0 + 0.05 + 0.3 * k, 3) for k in range(4)]}
    rules = {"in": round(l4 - 0.05, 3), "items": [W(4, "two"), W(4, "weeks"), W(4, "federal" if cut == "a" else "under"),
                                                    round(l6 - 0.1, 3)],
             "each": W(4, "each") if cut == "a" else None,
             "statute": W(4, "under") if cut == "b" else None, "dollars": W(4, "five") if cut == "b" else None,
             "vary": W(4, "results") if cut == "b" else None}
    upload = {"shot": round(W(5, "screenshot") - 0.06, 3), "web": round(W(5, "check") - 0.12, 3),
              "url": W(5, "spamclaims"), "tapcta": round(W(5, "spamclaims") + 0.55, 3)}
    endcard = {"at": round(l6 - 0.22, 3), "years": W(6, "four")}
    captions = caption_track(lines, cut)
    out = {"cut": cut, "fps": FPS, "duration": round(end, 3), "frames": int(round(end * FPS)), "tempo": TEMPO,
           "lines": lines, "hook": hook, "search": search, "count": count, "rules": rules, "upload": upload,
           "endcard": endcard, "captions": captions}
    json.dump(out, open(os.path.join(HERE, f"edit_{cut}.json"), "w", encoding="utf-8"), indent=1)
    print(f"cut {cut}: {end:.2f} s, {out['frames']} frames; lines at " + ", ".join(f"{x['id']} {x['at']:.2f}" for x in lines))


# Captions: short phrases (2-5 words) shown as they are spoken, the key word highlighted. The phrase boundaries are
# chosen by hand per line so they read naturally; each phrase starts at its first word and holds until the next.
PHRASES = {
    "L1": [("You said STOP.", "stop", "STOP"), ("They kept texting.", "kept", "texting")],
    "L2": [("10-second check:", "here", "10-second"), ("Open Messages,", "open", "Messages"), ("search STOP", "search", "STOP")],
    "L3": [("Tap a company", "tap", "Tap"), ("you texted STOP to", "you", "STOP"), ("Count what came after", "count", "after")],
    "A4": [("2+ texts?", "two", "2+"), ("Weeks after STOP?", "weeks", "Weeks"), ("Federal law may", "federal", "Federal law"),
           ("entitle you to damages", "entitle", "damages"), ("for each one", "for", "each one")],
    "B4": [("2+ texts?", "two", "2+"), ("Weeks after STOP?", "weeks", "Weeks"), ("Under federal law,", "under", "federal law"),
           ("up to $500 per text*", "up", "$500"), ("Results vary", "results", "vary")],
    "A5": [("Screenshot the STOP", "screenshot", "Screenshot"), ("+ the texts after it", "and", "texts after"),
           ("Check free at", "check", "free"), ("SpamClaims.com", "spamclaims", "SpamClaims.com")],
    "B5": [("Screenshot the STOP", "screenshot", "Screenshot"), ("+ the texts after it", "and", "texts after"),
           ("Check them at", "check", "Check"), ("SpamClaims.com", "spamclaims", "SpamClaims.com")],
    "A6": [("Texts from the last 4 years", "texts", "4 years"), ("can count", "can", "count")],
}


def caption_track(lines, cut):
    caps = []
    for ln in lines:
        words = ln["words"]
        for text, key, hl in PHRASES[ln["id"]]:
            hits = [w for w in words if w["w"].lower().strip(".,?!:").startswith(key)]
            caps.append({"at": round(hits[0]["s"] - 0.04, 3) if hits else ln["at"], "text": text, "hl": hl, "line": ln["id"]})
    caps.sort(key=lambda c: c["at"])
    for k, c in enumerate(caps):
        nxt = caps[k + 1]["at"] if k + 1 < len(caps) else c["at"] + 1.6
        c["until"] = round(nxt, 3)
    return caps


for c in CUTS:
    build(c)
