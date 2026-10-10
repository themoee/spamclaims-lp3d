# SpamClaims Reel 4 ("The Swarm"): what to paste into Ads Manager

`ad4/out/spamclaims-reel-swarm.mp4`: 26 s, 1080x1920, 24 fps (cinematic). Cover: `ad4/out/cover-swarm.jpg`.

The story is one continuous Blender camera move, about 18,000 3D objects rendered in Cycles:
1. "It starts with one text." One text bubble floats over a night city of 3,000 lit buildings.
2. "Then... it never stops." A river of 9,000 spam texts pours out of the sky, roars past the camera and funnels into one apartment window.
3. "You told them STOP." The phone on the desk sends STOP as a shockwave dome. Everything freezes, and the camera orbits the phone through a wall of frozen texts (bullet time).
4. "They kept texting." The dome shatters, and 4,500 texts flood the room and bury the desk.
5. "But every text after your STOP... may be a violation of federal law." The pile turns orange from the phone outward. The camera pulls back out of the window as the whole city's windows turn orange in a wave.
6. 4,000 orange texts rise from the city like lanterns and form the SpamClaims shield in the sky.
7. "See if your texts may qualify. Free, at SpamClaims dot com." End card over the shield.

## Primary text

You told them STOP. They kept texting.

Every marketing text sent after your STOP may be a violation of federal law. See if yours may qualify: upload your screenshots. Free to check, no sign-up.

SpamClaims is not a law firm. Not legal advice. Not every text qualifies; time limits apply.

## Headline

You said STOP. They kept texting.

## Description

Free to check · No sign-up

## Call to action button

Learn More

## Website URL

`https://spamclaims.com/lp/stop?vv=reel-swarm&utm_source=instagram&utm_medium=paid_social&utm_campaign=reel_stop&utm_content=reel-swarm`

## How to use it next to ad 3

- **Different jobs.** Ad 4 is the scroll-stopper: spectacle, emotion, brand. Ad 3 is the converter: it teaches the 10-second check and pre-qualifies.
- **Test both.** Run ad 4 alongside ad 3 (cut A) in the same campaign with equal budgets. Watch hook rate (3-second views per impression) and cost per qualified claimant.
- **Retargeting.** If ad 4 wins on hook rate but loses on qualified uploads, keep it at the top of the funnel and retarget its 50%+ viewers with ad 3.
- **Same setup as ad 3:** Advantage+ creative enhancements off, link straight to spamclaims.com, and the counsel check on geography (see `ad3/COPY.md`).

## Wording rules this follows

- No dollar amount (Meta rejected a partner ad that put "$500" in the creative).
- "May be a violation", "may qualify". The brands and numbers in the bubbles are invented (555 numbers are fictional).
- No cash visuals or government seals. The fine print is on the end card and in the primary text.

## How it was made, and how to change it

1. **Voice:** `python ad4/voice4.py` (Adam, `eleven_multilingual_v2`). Each line is checked by speech-to-text; `audition=1` compares four narrators.
2. **Timeline:** `python ad4/edit4.py` writes `ad4/edit.json` at 24 fps. Every beat is cued off a spoken word. Re-running it retimes the Blender render, so patch the fields instead once frames exist.
3. **Picture:** `blender -b --factory-startup -P blender/ad4_scene.py` writes `blender/frames/ad4`. `preview=1` renders a fast 270x480 pass; `only=` and `step=` pick frames.
   - Modules: `ad4_city.py` (buildings with procedural windows and the orange wave, rooftop gear, beacons, street lights, traffic, river, bridges, hills, night sky, aerial haze inside the materials), `ad4_room.py` (the hero tower's curtain wall and the apartment), `ad4_swarm.py` (the bubble mesh, the 48-text atlas material, path and rotation helpers), `ad4_atlas.py` (the atlas and the STOP bubble).
   - Cycles on CUDA with motion blur (shutter 0.1). About 13 s a frame over the city and 25-30 s in the room.
4. **Sound:** `python ad4/sound4.py`. ElevenLabs effects plus two Eleven Music cues; `build4.py` edits the cues so their hits land on "Then...", the STOP, the shatter and the shield.
5. **Build:** `python ad4/build4.py`. `capture4.cjs` composites `ad4.html` (the titles and the end card); the build mixes to -15 LUFS and encodes H.264 at CRF 17.
