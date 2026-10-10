"""Ad 2 ("Did you mean START?"): the edit, timed to the voice performances in ad2/audio/lines.json.

python ad2/edit2.py  ->  ad2/edit.json: beats (when each message lands, who says it), screen states, stickers,
sound cues, the reveal, the end card. blender/ad2_scene.py and ad2/ad2.html both read it.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
L = json.load(open(os.path.join(HERE, "audio", "lines.json"), encoding="utf-8"))
READ = 0.9               # seconds to read a brand text before "me" answers (that pause is the joke's rhythm)

t = 0.30
beats = []               # (time, kind, state index, label, voice line id)


def say(lid):
    global t
    start = t
    t = start + L[lid]["dur"]
    return start


# 1. the first spam lands with the phone; the brand voice reads it
b1 = say("B1")
beats.append(dict(at=0.0, kind="state", state=0))
beats.append(dict(at=b1, kind="voice", line="B1"))
t += 0.05
script = [  # (me line, state when I answer, brand state after, sticker for me, sticker for them)
    ("M1", 1, 2, "Me, politely:", "Them:"),
    ("M2", 3, 4, "Me, again:", "Them:"),
    ("M3", 5, 6, "Me, louder:", "Them:"),
    ("M4", 7, 8, "Me, begging:", "Them, at 2 AM:"),
    ("M5", 9, 10, "Me, unwell:", "Them, unbothered:"),
]
stickers = [dict(at=0.12, text="POV: you replied STOP to a cookie company", style="pov")]
for k, (me, s_me, s_them, lab_me, lab_them) in enumerate(script):
    s = say(me)
    beats.append(dict(at=s, kind="state", state=s_me, who="me", level=k))
    beats.append(dict(at=s, kind="voice", line=me))
    stickers.append(dict(at=s - 0.04, text=lab_me, style="me"))
    t += 0.05
    if s_them == 10:                        # the punchline is spoken by the brand
        b2 = say("B2")
        beats.append(dict(at=b2, kind="state", state=10, who="them", level=k))
        beats.append(dict(at=b2, kind="voice", line="B2"))
        stickers.append(dict(at=b2 - 0.04, text=lab_them, style="them"))
        t += 0.03
    else:
        beats.append(dict(at=t, kind="state", state=s_them, who="them", level=k))
        stickers.append(dict(at=t - 0.04, text=lab_them, style="them"))
        t += READ + (0.15 if s_them == 8 else 0.0)

scratch = t
t += 0.38                                     # the record scratch: everything freezes
n1 = say("N1")
t += 0.10
n2 = say("N2")
end = t + 0.45

# the reveal, from the narrator's word timings
w = {x["w"].strip(".,:").lower(): x["s"] for x in L["N1"]["words"]}
twist_at = n1
first_stop_at = n1 + w.get("first", 1.6)
five_at = n1 + w.get("five", 3.0)
reveal = dict(spin=(n1 + 0.05, n1 + 0.80), flash=n1 + 0.85, boxes_from=n1 + w.get("every", 0.9) + 0.25,
              boxes_to=first_stop_at + 0.55, money_at=five_at - 0.12, scratch=scratch,
              lines_at=[n1 + w.get("every", 0.9) - 0.05, first_stop_at - 0.05])   # the money card's rows, as spoken
endcard = dict(at=n2 - 0.12, phone_out=(n2 - 0.25, n2 + 0.45), shield=(n2 + 0.05, n2 + 0.75), jingle=n2 + 1.05)

cues = [dict(kind="drop", at=0.02), dict(kind="land", at=0.52)]
for b in beats:
    if b["kind"] == "state" and b.get("who") == "them":
        cues.append(dict(kind="incoming", at=b["at"]))
    if b["kind"] == "state" and b.get("who") == "me":
        cues.append(dict(kind="sent", at=b["at"] + 0.02, level=b["level"]))
cues += [dict(kind="scratch", at=scratch), dict(kind="whoosh_spin", at=reveal["spin"][0]),
         dict(kind="shutter", at=reveal["flash"]), dict(kind="pop_money", at=reveal["money_at"]),
         dict(kind="whoosh_out", at=endcard["phone_out"][0]), dict(kind="jingle", at=endcard["jingle"])]

out = dict(fps=FPS, duration=round(end, 3), frames=int(round(end * FPS)), beats=beats, stickers=stickers,
           reveal=reveal, endcard=endcard, cues=sorted(cues, key=lambda c: c["at"]),
           voice=[dict(line=b["line"], at=round(b["at"], 3)) for b in beats if b["kind"] == "voice"]
           + [dict(line="N1", at=round(n1, 3)), dict(line="N2", at=round(n2, 3))],
           money_lines=["Every text after your", "first STOP could be worth", "up to $500*"],
           end_lines=["Your spam could", "finally pay off."],
           fine_print="*Statutory damages under the TCPA, per violating text. Not a guarantee; results vary. Not legal advice.")
json.dump(out, open(os.path.join(HERE, "edit.json"), "w", encoding="utf-8"), indent=1)
print(f"duration {end:.2f} s, {out['frames']} frames")
for b in beats:
    print(f"  {b['at']:6.2f}  {b['kind']:5}  {b.get('state', b.get('line', ''))!s:4} {b.get('who', '')}")
print(f"  {scratch:6.2f}  scratch | N1 {n1:.2f} (five at {five_at:.2f}) | N2 {n2:.2f} | end {end:.2f}")
