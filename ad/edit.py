"""The Reel / Story ad: a 15 s, 9:16 edit of the Blender story (blender/story.py), timed for sound-off viewing.

python ad/edit.py  ->  ad/edit.json  (per-frame story t for Blender, captions, sound cues, voiceover lines)

Copy rules (same as the landing pages): "may" wording, no dollar amounts, no promises, no attorney names.
Safe zones (Instagram 1080x1920): nothing important in the top 250 px or the bottom 600 px (Reels UI).
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 15.0

# (ad start s, ad end s, story t start, story t end, easing): one shot each; a jump in t between shots is a cut
SHOTS = [
    (0.00, 1.00, 0.000, 0.092, "out"),     # hook: the Cosmic Orange back spins around to a lock screen
    (1.00, 3.00, 0.092, 0.180, "lin"),     # four more spam notifications land, one every half second
    (3.00, 3.60, 0.180, 0.226, "inout"),   # it opens to the conversation
    (3.60, 5.70, 0.226, 0.315, "lin"),     # STOP, the ripple, every text freezes
    (5.70, 6.70, 0.315, 0.352, "lin"),     # "you have been unsubscribed"
    (6.70, 9.40, 0.388, 0.505, "lin"),     # Today 9:12 AM: they texted again, the storm
    (9.40, 12.00, 0.742, 0.868, "lin"),    # screenshot flash, the scan, the evidence boxes
    (12.00, 15.00, 0.870, 1.000, "out"),   # it folds into the shield
]

CAPTIONS = [  # (in s, out s, lines, style)
    (0.15, 3.00, ["Still getting spam texts", "after you said STOP?"], "hook"),
    (3.70, 5.62, ["You replied STOP."], "beat"),
    (5.62, 6.68, ["They said you were", "unsubscribed."], "beat"),
    (6.82, 9.36, ["17 days later,", "they texted again."], "beat"),
    # the money line: federal law sets statutory damages of up to $500 per violating text (47 U.S.C. 227), so it
    # is said as "could be worth up to", with the asterisk and the fine print on the end card; never "you'll get"
    (9.48, 11.98, ["Each text after STOP", "could be worth", "up to $500*"], "money"),
    (12.15, 15.00, ["See if your texts", "may qualify."], "end"),
]
FINE_PRINT = "*Statutory damages under the TCPA, per violating text. Not a guarantee; results vary. Not legal advice."

VOICE = [  # (target start s, max length s, line) -- the voiceover, fitted to the picture
    (0.20, 2.75, "Still getting spam texts... after you said stop?"),
    (3.70, 2.95, "You replied stop. They said you were unsubscribed."),
    (6.85, 2.45, "Seventeen days later... they texted again."),
    (9.50, 2.60, "Each one could be worth up to five hundred dollars."),
    (12.25, 2.65, "See if yours qualify. Free, at SpamClaims dot com."),
]

# variant B, for the hook test: the money in the first three seconds, the law at the scan (same picture and sound)
import sys  # noqa: E402

VARIANT = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a).get("variant", "a")
if VARIANT == "b":
    CAPTIONS = [
        (0.15, 3.00, ["Got texts after STOP?", "Each one could be worth", "up to $500*"], "money", {"cascade": 0.34}),
        (3.70, 5.62, ["You replied STOP."], "beat"),
        (5.62, 6.68, ["They said you were", "unsubscribed."], "beat"),
        (6.82, 9.36, ["17 days later,", "they texted again."], "beat"),
        (9.48, 11.98, ["Texts after STOP may", "violate federal law."], "beat"),
        (12.15, 15.00, ["See if your texts", "may qualify."], "end"),
    ]
    VOICE = [
        (0.20, 3.40, "Got texts after you said stop? Each one could be worth up to five hundred dollars."),
        (3.70, 2.95, "You replied stop. They said you were unsubscribed."),
        (6.85, 2.45, "Seventeen days later... they texted again."),
        (9.55, 2.35, "Texts after you opt out may violate federal law."),
        (12.25, 2.65, "See if yours qualify. Free, at SpamClaims dot com."),
    ]


def ease(s, kind):
    if kind == "out":
        return 1 - (1 - s) ** 2
    if kind == "inout":
        return s * s * (3 - 2 * s)
    return s


def story_t(sec):
    for a, b, t0, t1, k in SHOTS:
        if a <= sec < b or (sec >= b and (a, b) == SHOTS[-1][:2]):
            s = min(1.0, max(0.0, (sec - a) / (b - a)))
            return t0 + (t1 - t0) * ease(s, k)
    return SHOTS[-1][3]


def ad_time(t):
    """The ad second at which story moment t is on screen (first shot containing it)."""
    for a, b, t0, t1, k in SHOTS:
        if t0 <= t <= t1:
            lo, hi = 0.0, 1.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if t0 + (t1 - t0) * ease(mid, k) < t:
                    lo = mid
                else:
                    hi = mid
            return a + (b - a) * (lo + hi) / 2
    return None


# story beats -> sound cues (seconds), from blender/story.py: notifications, STOP, freeze, the new text, flash, scan
BEATS = {
    "ding": [0.080, 0.100, 0.120, 0.140, 0.160],
    "send": [0.252],
    "freeze": [0.264],
    "ding_again": [0.424],
    "shutter": [0.746],
    "scan": [0.808],
    "tick": [0.829, 0.838, 0.842],
    "merge": [0.884],
    "pop": [0.920],
}
cues = []
for kind, ts in BEATS.items():
    for t in ts:
        sec = ad_time(t)
        if sec is not None:
            cues.append({"kind": kind, "at": round(sec, 3)})
cues += [{"kind": "storm", "at": round(ad_time(0.430), 3), "until": 9.40},
         {"kind": "cut", "at": 9.40}, {"kind": "cut", "at": 6.70}]
cues.sort(key=lambda c: c["at"])

frames = int(round(DUR * FPS))
t = [round(story_t(i / FPS), 6) for i in range(frames)]
out = {
    "fps": FPS, "duration": DUR, "size": [1080, 1920], "t": t,
    "shots": [dict(zip(("a", "b", "t0", "t1", "ease"), s)) for s in SHOTS],
    "captions": [dict({"in": c[0], "out": c[1], "lines": c[2], "style": c[3]}, **(c[4] if len(c) > 4 else {}))
                 for c in CAPTIONS],
    "fine_print": FINE_PRINT,
    "voice": [{"at": a, "max": m, "text": x} for a, m, x in VOICE],
    "cues": cues,
}
out["variant"] = VARIANT
json.dump(out, open(os.path.join(HERE, "edit.json" if VARIANT == "a" else f"edit_{VARIANT}.json"), "w",
                    encoding="utf-8"), indent=1)
print(f"{frames} frames, {len(cues)} sound cues")
for c in cues:
    print(f"  {c['at']:6.2f}s {c['kind']}")
