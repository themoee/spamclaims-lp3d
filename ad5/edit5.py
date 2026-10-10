"""Ad 5 ("2:13 AM"): the timeline, from the narration (ad5/audio/lines.json), 24 fps.

python ad5/edit5.py -> ad5/edit.json (read by blender/ad5_scene.py and ad5/ad5.html). After the render, patch fields.
  wake      the screen wakes at 2:13 AM with a text (buzz), two more follow (buzz, buzz)
  thread    the screen shows the conversation; the camera rises over the phone
  badges    "Two or more texts": the texts after the STOP get numbered, one by one
  evidence  "weeks after your STOP": the STOP outlined, the days since it under each number
  money     "five hundred dollars": the $500 overlay (statute-anchored, the qualifier spoken next)
  shot      the screenshot flash; "check them": spamclaims.com opens on the phone
  end       the end card
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, "audio", "lines.json"), encoding="utf-8"))
FPS = 24
AT = {"V1": 1.30, "V2": 3.05, "V3": 5.65, "V4": 9.25, "V5": 13.65, "V6": 16.75}


def w(lid, key, nth=0):
    hits = [x for x in L[lid]["words"] if x["w"].lower().strip(".,?!:").startswith(key.lower())]
    return round(AT[lid] + hits[min(nth, len(hits) - 1)]["s"], 3)


ev = {
    "wake": 0.55,
    "buzz": [0.55, 2.75, 4.05],
    "thread": 4.75,
    "badges": [w("V3", "two") + 0.05, w("V3", "more") + 0.12, w("V3", "texts") + 0.18],
    "evidence": w("V3", "weeks"),
    "money": w("V4", "five") - 0.08,
    "vary": w("V5", "results"),
    "shot": AT["V6"] - 0.25,
    "web": w("V6", "check") - 0.1,
    "end": AT["V6"] + L["V6"]["dur"] + 0.15,
}
end = ev["end"] + 3.3
out = {"fps": FPS, "duration": round(end, 3), "frames": int(round(end * FPS)), "events": ev,
       "voice": [{"line": k, "at": v, "dur": L[k]["dur"]} for k, v in AT.items()],
       "captions": [
           {"at": AT["V1"] - 0.05, "until": AT["V2"] - 0.05, "text": "You said STOP.", "hl": "STOP."},
           {"at": AT["V2"] - 0.05, "until": AT["V3"] - 0.1, "text": "They kept texting.", "hl": "texting."},
           {"at": AT["V3"] - 0.05, "until": w("V3", "two") - 0.05, "text": "A real company?", "hl": "real"},
           {"at": w("V3", "two") - 0.05, "until": w("V3", "weeks") - 0.05, "text": "2+ texts", "hl": "2+"},
           {"at": w("V3", "weeks") - 0.05, "until": AT["V4"] - 0.1, "text": "weeks after STOP?", "hl": "weeks"},
           {"at": AT["V4"] - 0.05, "until": ev["money"] - 0.05, "text": "Under federal law,", "hl": "federal law"},
       ],
       "fine_print": "*Statutory damages under the TCPA, 47 U.S.C. § 227, per violating text. Not a guarantee; results vary; "
                     "not every text qualifies. SpamClaims is not a law firm. Not legal advice."}
json.dump(out, open(os.path.join(HERE, "edit.json"), "w", encoding="utf-8"), indent=1)
print(f"{end:.2f} s, {out['frames']} frames")
for k, v in ev.items():
    print(f"  {k:9} {v}")
