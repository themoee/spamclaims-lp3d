"""Ad 6 ("Storytime") timeline: when every voice line plays, which shot is on screen, every beat (cued off a word),
the group chat bubbles, and the TikTok-style captions (word by word). Writes ad6/edit.json.

python ad6/edit6.py
Never re-run after a render without checking the shots: patch fields instead (the 3D shots render from these times).
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 24
L = json.load(open(os.path.join(HERE, "audio", "fast.json"), encoding="utf-8"))

AT = {"V1": 0.12}
AT["V2"] = AT["V1"] + L["V1"]["dur"] + 0.10
AT["V3"] = AT["V2"] + L["V2"]["dur"] + 0.12
AT["V4"] = AT["V3"] + L["V3"]["dur"] + 0.30
AT["V5"] = AT["V4"] + L["V4"]["dur"] + 0.10
AT["F1"] = AT["V5"] + L["V5"]["dur"] - 0.07
AT["F2"] = AT["F1"] + 1.80
AT["F3"] = AT["F2"] + 1.40
AT["V6"] = AT["F3"] + L["F3"]["dur"] + 0.02
AT["V7"] = AT["V6"] + L["V6"]["dur"] + 0.15
AT["V8"] = AT["V7"] + L["V7"]["dur"] + 0.13
AT["V9"] = AT["V8"] + L["V8"]["dur"] + 0.19
END = AT["V9"] + L["V9"]["dur"] + 1.85
FRAMES = int(math.ceil(END * FPS))


def w(line, word, which="s", k=0):
    """Global time of a word in a line (k-th match)."""
    hits = [x for x in L[line]["words"] if x["w"].strip(".,?!").lower() == word.lower()]
    return round(AT[line] + hits[k][which], 3)


EV = {
    "buzz": [0.05, w("V1", "My") - 0.05],
    "boltup": w("V1", "five") - 0.25,                     # he bolts upright in bed
    "each": w("V1", "EACH"),
    "thread": AT["V2"],
    "stop": w("V2", "STOP"),
    "unsub": w("V2", "STOP") + 0.3,                       # the opt-out confirmation
    "after": [w("V2", "They") + 0.02, w("V2", "They") + 0.2, w("V2", "They") + 0.38],   # texts after STOP (2D)
    "thread_end": w("V2", "They") + 0.47,                 # the 2D thread hands over to the annoyed 3D shot
    "annoyed": w("V2", "kept", k=1) + 0.1,               # 3D: Dre stares, phone buzzing in his hand
    "twoam": AT["V3"],
    "clock": w("V3", "two"),
    "search": w("V3", "look") - 0.2,                      # the search UI, typing
    "statute": w("V4", "real") - 0.06,                    # the federal law card
    "federal": w("V4", "federal"),
    "sweep": w("V4", "Every"),                            # highlight sweep on "up to $500 ... each such violation"
    "money": w("V4", "five") - 0.04,                      # the $500 explosion
    "shock": AT["V4"] + L["V4"]["dur"] - 0.62,            # 3D: Dre shocked
    "skeptic": AT["V5"],                                  # 3D: "obviously I thought it was a scam"
    "scratch": AT["V5"] + 0.06,
    "scam": w("V5", "scam"),
    "chat": w("V5", "group") - 0.12,                      # whoosh into the group chat
    "real3d": AT["V6"] - 0.05,                            # 3D: "100% real, 100% legal, fr fr"
    "real": w("V6", "real"),
    "legal": w("V6", "legal"),
    "frfr": w("V6", "For"),
    "catch": AT["V7"],
    "c1": w("V7", "STOP"),                                # what can count: after STOP ...
    "c2": w("V7", "never"),                               # ... texts you never agreed to ...
    "c3": w("V7", "nine"),                                # ... texts after 9 PM (or before 8 AM)
    "mine": w("V7", "mine"),                              # "like mine": his 2:06 AM text
    "vary1": w("V7", "Not", k=1),                        # "Not every text qualifies" (the 2nd "not" in the line)
    "vary2": w("V7", "results"),
    "cta": AT["V8"],
    "shot": w("V8", "screenshot") + 0.12,
    "web": w("V8", "check") - 0.05,
    "close": AT["V9"] - 0.1,                              # 3D: "They ignored your STOP. The law didn't."
    "law": w("V9", "The"),
    "end": w("V9", "didn't") + 0.45,
}
CHAT = {   # the group chat: (time, sender, kind, text); Dre is "me" (blue); others have names and avatars
    "start": EV["chat"],
    "items": [
        (EV["chat"] + 0.10, "me", "text", "yo every spam text a company sends after u say STOP could be worth up to $500"),
        (w("F1", "Bro"), "Marcus", "text", "bro thats a scam 💀"),
        (w("F1", "that's") + 0.06, "Jay", "text", "no shot"),
        (w("F1", "scam") - 0.18, "me", "image", "statute"),
        (w("F1", "scam") + 0.1, "me", "text", "its literally federal law"),
        (w("F2", "Wait") - 0.03, "Jay", "text", "WAIT its actually real??"),
        (w("F2", "real") + 0.12, "Marcus", "text", "i have like 40 of those 😭"),
        (w("F3", "OH") - 0.02, "Ava", "text", "OH MY GOD"),
        (w("F3", "GOD") + 0.42, "Ava", "text", "checking mine rn"),
    ],
    "tapback": (w("F3", "OH") + 0.1, 4, "!!"),      # Ava hits "its literally federal law" with "!!"
}
SHOTS3D = [   # (name, start, end) in the ad timeline; rendered by blender/ad6_scene.py
    ("hook", 0.0, AT["V2"]),
    ("annoyed", EV["annoyed"], AT["V3"]),
    ("twoam", AT["V3"], EV["search"]),
    ("shock", EV["shock"], AT["V5"]),
    ("skeptic", AT["V5"], EV["chat"] + 0.05),
    ("real", EV["real3d"], AT["V7"]),
    ("close", EV["close"], END),
]

EMPH = {"$500", "500", "EACH", "STOP", "STOP?", "STOP.", "federal", "law.", "scam.", "real.", "legal.", "free", "SpamClaims",
        "two", "dollars.", "bucks.", "hundred", "five", "didn't."}
SKIP_CAPS = {"F1", "F2", "F3"}
captions = []
for line in ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9"]:
    ws = L[line]["words"]
    page = []
    for i, x in enumerate(ws):
        page.append(x)
        end_sentence = x["w"][-1:] in ".?!,"
        if len(page) >= 3 or end_sentence or i == len(ws) - 1:
            captions.append({"line": line, "at": round(AT[line] + page[0]["s"] - 0.04, 3),
                             "words": [{"w": y["w"], "s": round(AT[line] + y["s"], 3), "e": round(AT[line] + y["e"], 3),
                                        "hl": y["w"].strip(",") in EMPH} for y in page]})
            page = []
for i, c in enumerate(captions):
    nxt = captions[i + 1]["at"] if i + 1 < len(captions) else END
    c["until"] = round(min(nxt, c["words"][-1]["e"] + 0.5), 3)

FINE = ("*Up to $500 per qualifying text is the statutory damages amount under the federal TCPA (47 U.S.C. § 227); "
        "not a guarantee. Not every text qualifies; results vary. Dramatization: characters and messages are fictional. "
        "SpamClaims is not a law firm and does not provide legal advice.")
out = {
    "fps": FPS, "frames": FRAMES, "duration": round(END, 3),
    "voice": [{"line": k, "at": round(v, 3), "dur": L[k]["dur"]} for k, v in AT.items()],
    "events": EV, "chat": CHAT, "shots3d": [{"name": n, "start": round(a, 3), "end": round(b, 3)} for n, a, b in SHOTS3D],
    "captions": captions, "fine_print": FINE,
    "words": {k: [{"w": x["w"], "s": round(AT[k] + x["s"], 3), "e": round(AT[k] + x["e"], 3)} for x in L[k]["words"]] for k in AT},
    "chars": {k: [[c, round(AT[k] + s, 3), round(AT[k] + e, 3)] for c, s, e in L[k]["chars"]] for k in AT},
}
json.dump(out, open(os.path.join(HERE, "edit.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"duration {END:.2f}s, {FRAMES} frames")
for k, v in AT.items():
    print(f"  {k} at {v:6.2f} .. {v + L[k]['dur']:6.2f}")
for n, a, b in SHOTS3D:
    print(f"  3D {n:8} {a:6.2f} .. {b:6.2f}  ({int(round((b - a) * FPS))} frames)")
