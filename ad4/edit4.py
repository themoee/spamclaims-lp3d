"""Ad 4 ("The Swarm"): the timeline, from the narration (ad4/audio/lines.json).

python ad4/edit4.py -> ad4/edit.json (24 fps). blender/ad4_scene.py and ad4/ad4.html both read it.
Re-running retimes everything; after the Blender render, patch fields instead.

Beats (each cued off a spoken word):
  one      "one text"       a single text bubble glides across the night sky
  erupt    "Then..."        the swarm erupts from behind downtown, thousands of bubbles
  stream   "never stops"    the swarm streams past, funnels into one window
  window   (visual)         the camera flies in through the window to the phone
  stop     "STOP."          the phone sends STOP: a shockwave dome
  freeze   (visual)         everything frozen: bullet-time orbit through the swarm
  shatter  "kept"           the dome shatters, the bubbles flood in, bury the desk
  orange   "every"          the texts after STOP light up orange, from the phone out
  exit     (visual)         the camera flies back out of the window
  city     "violation"      the whole city's windows turn orange in a wave
  lanterns (visual)         orange bubbles rise from the city like lanterns
  shield   (visual)         they form the SpamClaims shield in the sky
  end      "See if..."      the end card
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE, "audio", "lines.json"), encoding="utf-8"))
FPS = 24
AT = {"V1": 0.40, "V2": 7.30, "V3": 9.70, "V4": 11.60, "V5": 13.45, "V6": 20.30}


def w(lid, key, nth=0):
    hits = [x for x in L[lid]["words"] if x["w"].lower().strip(".,?!:").startswith(key.lower())]
    return round(AT[lid] + hits[min(nth, len(hits) - 1)]["s"], 3)


ev = {
    "one": w("V1", "one") - 0.25,
    "erupt": w("V1", "then") + 0.05,
    "stream": w("V1", "never"),
    "window": 6.10,
    "stop": w("V2", "stop") + 0.02,
    "freeze": w("V2", "stop") + 0.20,
    "shatter": w("V3", "kept") + 0.02,
    "orange": w("V4", "every") + 0.06,
    "orange_end": w("V4", "stop") + 0.25,
    "exit": 12.55,
    "city": w("V5", "violation") - 0.25,
    "lanterns": 15.25,
    "shield": 19.80,
    "end": w("V6", "see") + 0.70,
}
end = AT["V6"] + L["V6"]["dur"] + 1.05
out = {"fps": FPS, "duration": round(end, 3), "frames": int(round(end * FPS)), "events": ev,
       "voice": [{"line": k, "at": v, "dur": L[k]["dur"]} for k, v in AT.items()],
       "titles": [
           {"at": w("V2", "you") - 0.05, "until": ev["shatter"] - 0.05, "text": "You said STOP.", "hl": "STOP."},
           {"at": ev["shatter"], "until": w("V4", "but") - 0.1, "text": "They kept texting.", "hl": "texting."},
           {"at": w("V4", "every") - 0.05, "until": AT["V5"] + L["V5"]["dur"] + 0.3,
            "text": "Every text after STOP|may be a violation|of federal law.", "hl": "violation"},
       ],
       "fine_print": "SpamClaims is not a law firm and does not give legal advice. Not every text qualifies; "
                     "eligibility depends on facts and location. Time limits apply."}
json.dump(out, open(os.path.join(HERE, "edit.json"), "w", encoding="utf-8"), indent=1)
print(f"{end:.2f} s, {out['frames']} frames at {FPS} fps")
for k, v in ev.items():
    print(f"  {k:10} {v:6.2f}")
