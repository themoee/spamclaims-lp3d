// Scroll-scrubbed frame sequence on a canvas (the product-page technique): the frames are prerendered in
// Blender (blender/story.py), this only loads, decodes and draws them.
//
// - Two sets: 16:9 "desktop" and 9:16 "mobile", picked by the viewport's shape.
// - Progressive loading: every 16th frame first, then 8th, 4th, 2nd, all; frames near the scroll position
//   jump the queue. Missing frames fall back to the nearest one loaded.
// - Memory stays bounded: compressed blobs are kept, but only a window of frames around the playhead is
//   decoded to ImageBitmaps (each 1600x900 bitmap is ~5.8 MB).
// - The playhead eases toward the scroll position and crossfades neighbouring frames, so a coarse wheel
//   or a fast flick still plays smoothly.

type Manifest = { n: number; w: number; h: number; frames: number[]; ext: string };
type SetName = 'desktop' | 'mobile';

export interface SequenceOptions {
  canvas: HTMLCanvasElement;
  base: string;
  target: () => number;
  onFrame?: (t: number) => void;
  onFirstDraw?: () => void;
  onReady?: (info: { set: SetName; ms: number; frames: number }) => void;
  reducedMotion?: boolean;
  stills?: number[];
}

const ANCHOR: Record<SetName, [number, number]> = { desktop: [0.62, 0.5], mobile: [0.5, 0.56] };

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
  t0 = performance.now();
  win: number;
  constructor(public name: SetName, public dir: string, private onChange: () => void, private onAll: () => void) {
    this.win = name === 'mobile' ? 6 : 9;
  }

  async init() {
    const r = await fetch(`${this.dir}/manifest.json`, { cache: 'no-cache' });
    this.m = await r.json();
    const n = this.m.n;
    this.blobs = new Array(n).fill(null);
    this.bmps = new Array(n).fill(null);
    this.has = new Array(n).fill(false);
    for (const i of this.m.frames) this.has[i] = true;
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

  pump(center: number) {
    if (this.dead) return;
    while (this.fetching.size < 6) {
      const k = this.nextFetch(center);
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
          this.onChange();
        });
    }
  }

  nextFetch(center: number): number {
    for (let d = 0; d <= this.win; d++) {
      for (const k of [center + d, center - d]) {
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

  want(center: number) {
    const lo = center - this.win, hi = center + this.win;
    for (let d = 0; d <= this.win && this.decoding.size < 3; d++) {
      for (const k of [center + d, center - d]) {
        if (k < lo || k > hi || k < 0 || k >= this.m.n) continue;
        const b = this.blobs[k];
        if (b && !this.bmps[k] && !this.decoding.has(k) && this.decoding.size < 3) {
          this.decoding.add(k);
          createImageBitmap(b)
            .then((bmp) => {
              this.decoding.delete(k);
              if (this.dead) return bmp.close();
              this.bmps[k] = bmp;
              this.onChange();
            })
            .catch(() => this.decoding.delete(k));
        }
      }
    }
    for (let k = 0; k < this.bmps.length; k++) {
      const bmp = this.bmps[k];
      if (bmp && Math.abs(k - center) > this.win * 2 + 2) {
        bmp.close();
        this.bmps[k] = null;
      }
    }
  }

  nearestBitmap(i: number): [ImageBitmap | null, number] {
    for (let d = 0; d < 60; d++) {
      const a = this.bmps[i - d];
      if (a) return [a, i - d];
      const b = this.bmps[i + d];
      if (b) return [b, i + d];
    }
    return [null, -1];
  }

  dispose() {
    this.dead = true;
    for (const b of this.bmps) b?.close();
  }
}

export function startSequence(o: SequenceOptions) {
  const ctx = o.canvas.getContext('2d', { alpha: false })!;
  // sized from the stage (100svh), not the window: the mobile toolbar collapsing must not resize the canvas
  const box = () => {
    const r = o.canvas.getBoundingClientRect();
    return { w: Math.max(1, r.width || window.innerWidth), h: Math.max(1, r.height || window.innerHeight) };
  };
  const portrait = () => {
    const b = box();
    return b.w / b.h < 1;
  };
  let set: FrameSet | null = null;
  let shown = o.target();
  let lastKey = '';
  let dirty = true;
  let firstDrawn = false;

  const open = (name: SetName) => {
    set?.dispose();
    const fs = new FrameSet(name, `${o.base}/seq/${name}`, () => (dirty = true), () =>
      o.onReady?.({ set: name, ms: Math.round(performance.now() - fs.t0), frames: fs.m.frames.length }),
    );
    set = fs;
    fs.init().then(() => {
      size();
      dirty = true;
    });
  };

  const size = () => {
    if (!set?.m) return;
    const { w: cssW, h: cssH } = box();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cover = Math.max(cssW / set.m.w, cssH / set.m.h);
    const k = Math.min(dpr, 1 / cover);           // never draw more pixels than the source has
    o.canvas.width = Math.max(1, Math.round(cssW * k));
    o.canvas.height = Math.max(1, Math.round(cssH * k));
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

  const tick = () => {
    requestAnimationFrame(tick);
    const fs = set;
    if (!fs?.m) return;
    let tgt = o.target();
    if (o.reducedMotion) tgt = snapStill(tgt);
    const ease = o.reducedMotion ? 0.25 : 0.14;
    shown += (tgt - shown) * ease;
    if (Math.abs(tgt - shown) < 0.00015) shown = tgt;
    const n = fs.m.n;
    const f = Math.min(n - 1, Math.max(0, shown * (n - 1)));
    const i0 = Math.floor(f);
    fs.pump(i0);
    fs.want(i0);
    const [a, ia] = fs.nearestBitmap(i0);
    if (!a) return;
    const b = ia === i0 ? fs.bmps[i0 + 1] : null;
    const mix = b ? f - i0 : 0;
    const key = `${ia}:${b ? i0 + 1 : -1}:${mix.toFixed(3)}:${o.canvas.width}x${o.canvas.height}`;
    o.onFrame?.(shown);
    if (key === lastKey && !dirty) return;
    lastKey = key;
    dirty = false;
    const anchor = ANCHOR[fs.name];
    blit(a, 1, anchor);
    if (b && mix > 0.004) blit(b, mix, anchor);
    ctx.globalAlpha = 1;
    if (!firstDrawn) {
      firstDrawn = true;
      o.onFirstDraw?.();
    }
  };

  open(portrait() ? 'mobile' : 'desktop');
  let resizeT = 0;
  let lastBox = '';
  new ResizeObserver(() => {
    const b = box();
    const k = `${Math.round(b.w)}x${Math.round(b.h)}`;
    if (k === lastBox) return;
    lastBox = k;
    clearTimeout(resizeT);
    resizeT = window.setTimeout(() => {
      const want: SetName = portrait() ? 'mobile' : 'desktop';
      if (set && set.name !== want) open(want);
      else size();
    }, 120);
  }).observe(o.canvas);
  requestAnimationFrame(tick);
  return { setName: () => set?.name };
}
