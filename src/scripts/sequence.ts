// Scroll-scrubbed frame sequence on a canvas (the product-page technique): the frames are prerendered in
// Blender (blender/story.py), this only loads, decodes and draws them. Built to never lag:
//
// - Two sets: 16:9 "desktop" and 9:16 "mobile", picked by the stage's shape.
// - Progressive loading that keeps going on its own: every 16th frame first, then 8th, 4th, 2nd, all; frames
//   near the playhead jump the queue. On data-saver or slow connections the mobile set loads every other frame.
// - Bounded memory: compressed blobs are kept, only a small window around the playhead is decoded to
//   ImageBitmaps (off the main thread), everything else is released.
// - Cheap drawing: at most two blits per frame (a quantized crossfade between the neighbours we have), nothing
//   at all when the image would not change.
// - No idle work: the loop sleeps when the playhead has settled, when the story is off screen and when the
//   tab is hidden; a scroll, a resize or a newly decoded frame wakes it.
// - Frame-rate independent easing (same feel at 60, 90 and 120 Hz), short enough to never trail the finger.

type Manifest = { n: number; w: number; h: number; frames: number[]; ext: string };
type SetName = 'desktop' | 'mobile';

export interface SequenceOptions {
  canvas: HTMLCanvasElement;
  base: string;
  target: () => number;
  onFrame?: (t: number) => void;
  onFirstDraw?: () => void;
  onReady?: (info: { set: SetName; ms: number; frames: number; lite: boolean }) => void;
  reducedMotion?: boolean;
  stills?: number[];
}

const ANCHOR: Record<SetName, [number, number]> = { desktop: [0.62, 0.5], mobile: [0.5, 0.56] };
const TAU = 0.07; // seconds: the playhead's easing time constant
const STEPS = 8; // crossfade quantization (fewer redraws while the playhead settles)

function liteNetwork(): boolean {
  const c = (navigator as any).connection;
  if (!c) return false;
  return !!c.saveData || /(^|-)(2g|3g)$/.test(String(c.effectiveType || ''));
}

class FrameSet {
  m!: Manifest;
  blobs: (Blob | null)[] = [];
  bmps: (ImageBitmap | null)[] = [];
  has: boolean[] = [];
  fetching = new Set<number>();
  decoding = new Set<number>();
  order: number[] = [];
  head = 0;
  done = 0;
  dead = false;
  center = 0;
  t0 = performance.now();
  win: number;
  lite = false;
  constructor(public name: SetName, public dir: string, private onChange: () => void, private onAll: () => void) {
    this.win = name === 'mobile' ? 5 : 8;
  }

  async init() {
    const r = await fetch(`${this.dir}/manifest.json`, { cache: 'no-cache' });
    this.m = await r.json();
    const n = this.m.n;
    this.blobs = new Array(n).fill(null);
    this.bmps = new Array(n).fill(null);
    this.has = new Array(n).fill(false);
    this.lite = this.name === 'mobile' && liteNetwork();
    for (const i of this.m.frames) this.has[i] = !this.lite || i % 2 === 0 || i === n - 1;
    const seen = new Set<number>();
    for (const stride of [16, 8, 4, 2, 1]) {
      for (let i = 0; i < n; i += stride) {
        const k = this.nearestExisting(i);
        if (k >= 0 && !seen.has(k)) {
          seen.add(k);
          this.order.push(k);
        }
      }
    }
    this.pump();
  }

  nearestExisting(i: number): number {
    for (let d = 0; d < this.m.n; d++) {
      if (i - d >= 0 && this.has[i - d]) return i - d;
      if (i + d < this.m.n && this.has[i + d]) return i + d;
    }
    return -1;
  }

  url(i: number) {
    return `${this.dir}/${String(i).padStart(4, '0')}.${this.m.ext}`;
  }

  /** Keeps up to 6 requests in flight until every frame is in; each completion schedules the next. */
  pump() {
    if (this.dead || !this.m) return;
    while (this.fetching.size < 6) {
      const k = this.nextFetch();
      if (k < 0) break;
      this.fetching.add(k);
      fetch(this.url(k))
        .then((r) => (r.ok ? r.blob() : null))
        .catch(() => null)
        .then((b) => {
          this.fetching.delete(k);
          if (this.dead) return;
          this.blobs[k] = b;
          if (!b) this.has[k] = false;
          this.done++;
          if (this.done === this.order.length) this.onAll();
          if (Math.abs(k - this.center) <= this.win) this.onChange();
          this.pump();
        });
    }
  }

  nextFetch(): number {
    const c = this.center;
    for (let d = 0; d <= this.win; d++) {
      for (const k of [c + d, c - d]) {
        if (k >= 0 && k < this.m.n && this.has[k] && !this.blobs[k] && !this.fetching.has(k)) return k;
      }
    }
    while (this.head < this.order.length) {
      const k = this.order[this.head];
      if (!this.blobs[k] && !this.fetching.has(k) && this.has[k]) return k;
      this.head++;
    }
    return -1;
  }

  /** Decode the window around the playhead (max 2 at a time), release what is far away. */
  want(center: number) {
    if (center !== this.center) {
      this.center = center;
      this.pump();
    }
    for (let d = 0; d <= this.win && this.decoding.size < 2; d++) {
      for (const k of d ? [center + d, center - d] : [center]) {
        if (k < 0 || k >= this.m.n || this.decoding.size >= 2) continue;
        const b = this.blobs[k];
        if (!b || this.bmps[k] || this.decoding.has(k)) continue;
        this.decoding.add(k);
        createImageBitmap(b)
          .then((bmp) => {
            this.decoding.delete(k);
            if (this.dead || Math.abs(k - this.center) > this.win + 3) return bmp.close();
            this.bmps[k] = bmp;
            this.onChange();
          })
          .catch(() => this.decoding.delete(k));
      }
    }
    const keep = this.win + 3;
    for (let k = 0; k < this.bmps.length; k++) {
      const bmp = this.bmps[k];
      if (bmp && Math.abs(k - center) > keep) {
        bmp.close();
        this.bmps[k] = null;
      }
    }
  }

  below(i: number): number {
    for (let k = i; k >= Math.max(0, i - 24); k--) if (this.bmps[k]) return k;
    return -1;
  }

  above(i: number): number {
    for (let k = i; k <= Math.min(this.m.n - 1, i + 24); k++) if (this.bmps[k]) return k;
    return -1;
  }

  busy() {
    return this.decoding.size > 0;
  }

  dispose() {
    this.dead = true;
    for (const b of this.bmps) b?.close();
  }
}

export function startSequence(o: SequenceOptions) {
  const ctx = o.canvas.getContext('2d', { alpha: false }) as CanvasRenderingContext2D;
  ctx.imageSmoothingQuality = 'high';
  // sized from the stage (100svh), not the window: the mobile toolbar collapsing must not resize the canvas
  let boxW = 1, boxH = 1;
  const measure = () => {
    const r = o.canvas.getBoundingClientRect();
    boxW = Math.max(1, r.width || window.innerWidth);
    boxH = Math.max(1, r.height || window.innerHeight);
  };
  measure();
  const portrait = () => boxW / boxH < 1;

  let set: FrameSet | null = null;
  let shown = o.target();
  let lastShown = -1;
  let lastKey = '';
  let dirty = true;
  let firstDrawn = false;
  let running = false;
  let onScreen = true;
  let still = 0;
  let last = performance.now();

  const kick = () => {
    if (running || !onScreen || document.hidden) return;
    running = true;
    still = 0;
    last = performance.now();
    requestAnimationFrame(tick);
  };

  const open = (name: SetName) => {
    set?.dispose();
    const fs = new FrameSet(
      name,
      `${o.base}/seq/${name}`,
      () => {
        dirty = true;
        kick();
      },
      () => o.onReady?.({ set: name, ms: Math.round(performance.now() - fs.t0), frames: fs.m.frames.length, lite: fs.lite }),
    );
    set = fs;
    fs.init().then(() => {
      size();
      kick();
    });
  };

  const size = () => {
    if (!set?.m) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cover = Math.max(boxW / set.m.w, boxH / set.m.h);
    const k = Math.min(dpr, 1 / cover); // never draw more pixels than the source has
    const w = Math.max(1, Math.round(boxW * k));
    const h = Math.max(1, Math.round(boxH * k));
    if (o.canvas.width !== w || o.canvas.height !== h) {
      o.canvas.width = w;
      o.canvas.height = h;
      ctx.imageSmoothingQuality = 'high';
    }
    dirty = true;
  };

  const blit = (bmp: ImageBitmap, alpha: number, anchor: [number, number]) => {
    const cw = o.canvas.width, ch = o.canvas.height;
    const s = Math.max(cw / bmp.width, ch / bmp.height);
    const dw = bmp.width * s, dh = bmp.height * s;
    ctx.globalAlpha = alpha;
    ctx.drawImage(bmp, (cw - dw) * anchor[0], (ch - dh) * anchor[1], dw, dh);
  };

  const snapStill = (t: number) => {
    const st = o.stills || [];
    let best = t, bd = 9;
    for (const s of st) if (Math.abs(s - t) < bd) (bd = Math.abs(s - t)), (best = s);
    return best;
  };

  function tick(now: number) {
    const fs = set;
    if (!fs?.m || !onScreen || document.hidden) {
      running = false;
      return;
    }
    const dt = Math.min(0.1, Math.max(0, (now - last) / 1000));
    last = now;
    let tgt = o.target();
    if (o.reducedMotion) tgt = snapStill(tgt);
    const a = 1 - Math.exp(-dt / (o.reducedMotion ? 0.12 : TAU));
    shown += (tgt - shown) * a;
    if (Math.abs(tgt - shown) < 0.00008) shown = tgt;

    const n = fs.m.n;
    const f = Math.min(n - 1, Math.max(0, shown * (n - 1)));
    const i0 = Math.floor(f);
    fs.want(i0);
    let ia = fs.below(i0);
    let ib = fs.above(i0 + 1 <= n - 1 ? i0 + 1 : i0);
    if (ia < 0 && ib < 0) {
      requestAnimationFrame(tick);
      return;
    }
    let mix = 0;
    if (ia < 0) (ia = ib), (ib = -1);
    else if (ib >= 0 && ib > ia && ib - ia <= 6) mix = Math.round(((f - ia) / (ib - ia)) * STEPS) / STEPS;
    else ib = -1;
    if (mix >= 1) (ia = ib), (ib = -1), (mix = 0);

    if (shown !== lastShown) {
      lastShown = shown;
      o.onFrame?.(shown);
    }
    const key = `${ia}:${mix > 0 ? ib : -1}:${mix}:${o.canvas.width}x${o.canvas.height}`;
    if (key !== lastKey || dirty) {
      lastKey = key;
      dirty = false;
      const anchor = ANCHOR[fs.name];
      blit(fs.bmps[ia]!, 1, anchor);
      if (mix > 0 && ib >= 0) blit(fs.bmps[ib]!, mix, anchor);
      ctx.globalAlpha = 1;
      if (!firstDrawn) {
        firstDrawn = true;
        o.onFirstDraw?.();
      }
      still = 0;
    } else if (shown === tgt && !fs.busy()) {
      still++;
    }
    if (still > 20) {
      running = false; // settled: sleep until a scroll, a resize or a new frame wakes us
      return;
    }
    requestAnimationFrame(tick);
  }

  open(portrait() ? 'mobile' : 'desktop');

  window.addEventListener('scroll', kick, { passive: true });
  document.addEventListener('visibilitychange', kick);
  new IntersectionObserver((es) => {
    onScreen = es[0].isIntersecting;
    kick();
  }).observe(o.canvas);
  let resizeT = 0;
  let lastBox = '';
  new ResizeObserver(() => {
    measure();
    const k = `${Math.round(boxW)}x${Math.round(boxH)}`;
    if (k === lastBox) return;
    lastBox = k;
    clearTimeout(resizeT);
    resizeT = window.setTimeout(() => {
      const want: SetName = portrait() ? 'mobile' : 'desktop';
      if (set && set.name !== want) open(want);
      else size();
      kick();
    }, 120);
  }).observe(o.canvas);
  return { kick, setName: () => set?.name };
}
