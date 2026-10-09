# SpamClaims 3D landing page

A standalone, static marketing page for [SpamClaims](https://spamclaims.com): a floating phone, a swarm of spam
bubbles, and a 3D STOP sign that slams in as you scroll. Built with Astro + vanilla three.js; the meshes are made in
Blender (headless) and shipped as a single GLB.

Live: https://themoee.github.io/spamclaims-lp3d/

## Stack

- Astro (static output) + TypeScript, plain CSS (inlined as critical CSS at build time)
- three.js (`three`), code-split and loaded after first paint; GLTFLoader, no Draco
- Blender 5.2 LTS, run headless by `tools/build_assets.py`, exports `public/models/scene.glb`
- GitHub Pages via GitHub Actions (`.github/workflows/deploy.yml`, `withastro/action`)

## Commands

```sh
npm install
npm run dev        # http://localhost:4321/spamclaims-lp3d/
npm run build      # -> dist/
npm run preview    # serve dist/
```

### Rebuild the 3D assets (Blender)

Install Blender (`winget install --id BlenderFoundation.Blender -e`), then from the repo root:

```sh
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P tools/build_assets.py
# optional preview render of the parts:
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P tools/build_assets.py -- --render tools/preview.png
```

The script builds the phone (rounded slab, bevelled, inset screen plane, camera bump), the STOP sign (bevelled
octagon, yellow rim, white inner ring, extruded Impact "STOP" text converted to mesh) and three rounded speech bubbles,
applies modifiers, triangulates and exports the GLB (about 20k triangles, ~0.5 MB). The screen's texture (the text
thread) is drawn on a canvas at runtime in `src/scripts/hero3d.ts`. If the GLB is missing, the page falls back to
procedural three.js geometry with the same look.

### Regenerate the poster / OG image

With the preview server running (`npm run preview`):

```sh
node tools/make-poster.mjs http://127.0.0.1:4321/spamclaims-lp3d/
```

Uses headless Chrome to screenshot the hero (`?poster=1` renders the "after the slam" frame with the text hidden,
`?og=1` keeps the headline) and writes `public/poster.webp` (WebGL-off fallback) and `public/og.jpg` (Open Graph).

## How the CTA links work

Every CTA is `https://spamclaims.com/lp/stop`. A tiny inline script forwards every query parameter present on this
page's URL (utm_*, fbclid, gclid, ttclid, sub1..sub8, aff, ref, clickid, ...) and adds `lp=3d` (and `vv=3d` only if
`vv` is absent). Without JavaScript the links still carry `lp=3d`.

## Performance notes

- Headline is real HTML (LCP), display font is self-hosted and preloaded, body fonts come from Google Fonts with swap.
- three.js chunk: ~165 KB gzipped, loaded on idle after `load`. DPR capped at 1.5 (1.25 on mobile).
- Render loop pauses when the tab is hidden or the hero is scrolled out of view; `prefers-reduced-motion` renders one
  static frame; no WebGL shows `poster.webp`.
