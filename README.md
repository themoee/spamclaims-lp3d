# SpamClaims 3D landing page

A standalone, static marketing page for [SpamClaims](https://spamclaims.com): one cinematic, scroll-driven story
rendered in Blender. A photoreal iPhone 17 Pro (Cosmic Orange) turns around to a lock screen full of spam, you reply
STOP, every floating text freezes mid-air, they text again 17 days later, three example threads, the screenshot gets
read, and the SpamClaims shield rises. Then the essentials (how it works, free to check, FAQ) and the CTA.

Live: https://themoee.github.io/spamclaims-lp3d/

## How it works

- **The story is a prerendered frame sequence**, scrubbed by scroll on a `<canvas>` (the Apple product-page
  technique). Two sets: 16:9 `desktop` (1600x900) and 9:16 `mobile` (864x1536), 300 frames each, WebP.
  `src/scripts/sequence.ts` loads them progressively (every 16th frame first), keeps only a window of decoded
  frames in memory, eases the playhead toward the scroll position and crossfades neighbouring frames.
- **The copy is HTML**, timed to the same scroll progress (`src/data/story.ts`). The numbers there match the beats in
  `blender/story.py`; change both together.
- **The phone screens are real UI**, rendered by the iOS kit (`C:\Users\moise\Projects\ios-ui-kit`) into
  `blender/textures/*.png` at 1206x2622 (iPhone 17 Pro, 402x874 pt @3x). All numbers are fictional 555 numbers,
  all brands invented, no Apple logo or names, Inter instead of SF.

## Commands

```sh
npm install
npm run dev        # http://127.0.0.1:4321/spamclaims-lp3d/
npm run build      # -> dist/
npm run preview    # serve dist/
```

### Re-render the story (Blender 5.2, Cycles on CUDA)

```sh
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd blender
"$B" -b --factory-startup -P story.py -- set=desktop preview=1 step=15   # quick 480x270 look at 20 frames
python contact.py frames/desktop_preview renders/_contact_desktop.png 4
"$B" -b --factory-startup -P story.py -- set=desktop                      # full: 300 frames, 1600x900
"$B" -b --factory-startup -P story.py -- set=mobile                       # full: 300 frames, 864x1536
cd ..
python tools/frames_to_webp.py desktop
python tools/frames_to_webp.py mobile
python tools/make_og.py frame=blender/frames/desktop/0054.png              # public/og.jpg
```

About 8 to 10 seconds a frame on the RTX 4060 laptop GPU at 96 samples. Existing frames are skipped unless
`force=1`. `only=0,80,160` renders specific frames. The scene is built in code: `iphone17pro.py` (the phone,
measured, see `docs/IPHONE17PRO_IOS_SPEC.md`), `emblem.py` (the shield from the real logo's outline),
`studio.py` (lights, world, camera helpers), `story.py` (the choreography and the render loop).

### The logo

`public/logo-reversed.png` is the dark-background version of `public/logo.png` (navy wordmark to white, the shield
keeps its navy with a white keyline): `python tools/make_logo_reversed.py`.

## How the CTA links work

Every CTA is `https://spamclaims.com/lp/stop`. A tiny inline script forwards every query parameter on this page's URL
(utm_*, fbclid, ttclid, sub1..., aff, vv, ...) and adds `lp=3d`. Without JavaScript the links still carry `lp=3d`.

## Analytics

Anonymous PostHog events to the SpamClaims project (no cookies, no PII, no replay; skipped on localhost and with
`?notrack=1`): `$pageview`, `lp3d_act` (the furthest act reached: stop, again, examples, how, finale),
`lp3d_story_complete`, `lp3d_cta_click` (`where`: header, hero, finale, sticky, final; `t`: story progress) and
`lp3d_frames_ready` (which set, how long the frames took).
