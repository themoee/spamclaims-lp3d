/**
 * SpamClaims 3D hero.
 *
 * A floating phone (screen textured at runtime with a text thread), dozens of
 * spam bubbles drifting toward it, and a big STOP sign that slams in as the
 * visitor scrolls the first screen (or after a short idle), scattering them.
 *
 * Loaded via a dynamic import after first paint. Meshes come from
 * public/models/scene.glb (built with Blender, see tools/build_assets.py);
 * if the GLB is missing we fall back to procedural geometry with the same look.
 */
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

export interface HeroOptions {
  base: string;            // import.meta.env.BASE_URL without trailing slash
  reducedMotion: boolean;  // prefers-reduced-motion: render one static frame
  isMobile: boolean;       // coarse pointer / narrow: cap DPR, auto-rotate instead of parallax
  hero: HTMLElement;       // the sticky 100svh hero (visibility -> pause)
  wrap: HTMLElement;       // the taller wrapper whose scroll drives the slam
  poster: boolean;         // ?poster=1 -> deterministic "after the slam" frame
}

type Parts = Record<string, THREE.Object3D | undefined>;

interface Bubble {
  p: THREE.Vector3;
  v: THREE.Vector3;
  r: THREE.Euler;
  rv: THREE.Vector3;
  s: number;
  phase: number;
  life: number;
  mode: 'drift' | 'scatter';
}

const PALETTE = {
  bg: 0x140c28,
  primary: 0x7b5cff,
  accent: 0xff5ca8,
  highlight: 0xffe066,
  success: 0x37e59b,
};

// Tiny seeded RNG so the poster frame is reproducible.
function makeRng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13; s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5; s >>>= 0;
    return (s >>> 0) / 4294967296;
  };
}

// ----------------------------------------------------------------- textures
function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(' ');
  const lines: string[] = [];
  let line = '';
  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = w;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** The phone screen: an iMessage-style thread (marketing text, STOP, more marketing). */
function makeScreenTexture(): THREE.CanvasTexture {
  const W = 512, H = 1106;
  const c = document.createElement('canvas');
  c.width = W; c.height = H;
  const ctx = c.getContext('2d')!;
  const font = '-apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

  const bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#0d0a1f');
  bg.addColorStop(1, '#09071a');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // status bar
  ctx.fillStyle = '#ffffff';
  ctx.font = `600 26px ${font}`;
  ctx.textBaseline = 'middle';
  ctx.fillText('9:41', 40, 44);
  ctx.textAlign = 'right';
  ctx.fillText('100%', W - 40, 44);
  ctx.textAlign = 'left';

  // header
  ctx.fillStyle = '#1b1636';
  ctx.fillRect(0, 76, W, 118);
  ctx.beginPath();
  ctx.arc(W / 2, 118, 30, 0, Math.PI * 2);
  ctx.fillStyle = '#5a4bb3';
  ctx.fill();
  ctx.fillStyle = '#ffffff';
  ctx.font = `700 26px ${font}`;
  ctx.textAlign = 'center';
  ctx.fillText('?', W / 2, 120);
  ctx.font = `500 21px ${font}`;
  ctx.fillStyle = '#d9d3ff';
  ctx.fillText('+1 (833) 555-0147', W / 2, 170);
  ctx.textAlign = 'left';

  let y = 230;
  const pad = 24, maxW = 330, lineH = 32;

  const date = (label: string, strong = false) => {
    ctx.font = `${strong ? 700 : 500} 20px ${font}`;
    ctx.fillStyle = strong ? '#ffe066' : '#8d86b3';
    ctx.textAlign = 'center';
    ctx.fillText(label, W / 2, y + 12);
    ctx.textAlign = 'left';
    y += 44;
  };
  const bubble = (text: string, out: boolean) => {
    ctx.font = `500 24px ${font}`;
    const lines = wrapText(ctx, text, maxW);
    const w = Math.min(maxW, Math.max(...lines.map((l) => ctx.measureText(l).width))) + pad * 2;
    const h = lines.length * lineH + pad * 1.6;
    const x = out ? W - 32 - w : 32;
    ctx.fillStyle = out ? '#34c759' : '#2d2a45';
    roundRect(ctx, x, y, w, h, 26);
    ctx.fill();
    // tail
    ctx.beginPath();
    if (out) {
      ctx.moveTo(x + w - 10, y + h - 24);
      ctx.quadraticCurveTo(x + w + 2, y + h - 4, x + w + 12, y + h);
      ctx.quadraticCurveTo(x + w - 10, y + h + 2, x + w - 22, y + h - 10);
    } else {
      ctx.moveTo(x + 10, y + h - 24);
      ctx.quadraticCurveTo(x - 2, y + h - 4, x - 12, y + h);
      ctx.quadraticCurveTo(x + 10, y + h + 2, x + 22, y + h - 10);
    }
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    lines.forEach((l, i) => ctx.fillText(l, x + pad, y + pad * 0.8 + lineH / 2 + i * lineH));
    y += h + 18;
  };

  date('Mon, Mar 2 · 9:12 AM');
  bubble('BrightSmile Dental: FLASH SALE 🦷 40% off whitening this week only. Reply YES to claim!', false);
  bubble('STOP', true);
  ctx.font = `500 19px ${font}`;
  ctx.fillStyle = '#8d86b3';
  ctx.textAlign = 'right';
  ctx.fillText('Delivered', W - 40, y - 4);
  ctx.textAlign = 'left';
  y += 20;
  date('16 days later', true);
  date('Wed, Mar 18 · 6:04 PM');
  bubble('BrightSmile Dental: Last chance! Your 40% discount expires Friday. Reply YES to lock it in.', false);
  bubble('BrightSmile Dental: Did you forget? Book now and get a FREE exam.', false);

  // keyboard-ish bottom bar
  ctx.fillStyle = '#1b1636';
  roundRect(ctx, 24, H - 86, W - 48, 56, 28);
  ctx.fill();
  ctx.fillStyle = '#6f68a0';
  ctx.font = `500 22px ${font}`;
  ctx.fillText('Text Message', 48, H - 58);

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.flipY = false; // glTF UV convention (origin top-left)
  tex.anisotropy = 4;
  tex.needsUpdate = true;
  return tex;
}

function makeGlowTexture(hex: string): THREE.CanvasTexture {
  const S = 256;
  const c = document.createElement('canvas');
  c.width = S; c.height = S;
  const ctx = c.getContext('2d')!;
  const g = ctx.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  g.addColorStop(0, hex + 'ee');
  g.addColorStop(0.35, hex + '66');
  g.addColorStop(1, hex + '00');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, S, S);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function makeStopLabelTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = 512; c.height = 512;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#ffffff';
  ctx.font = '900 190px Impact, "Arial Black", Arial, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('STOP', 256, 268);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// ----------------------------------------------------------------- geometry
function octagonExtruded(radius: number, depth: number): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  for (let i = 0; i < 8; i++) {
    const a = Math.PI / 8 + (i * Math.PI) / 4;
    const x = radius * Math.cos(a), y = radius * Math.sin(a);
    if (i === 0) shape.moveTo(x, y); else shape.lineTo(x, y);
  }
  shape.closePath();
  const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
  g.translate(0, 0, -depth / 2);
  return g;
}

function roundedRectExtruded(w: number, h: number, r: number, depth: number): THREE.BufferGeometry {
  const shape = new THREE.Shape();
  const hw = w / 2, hh = h / 2;
  shape.moveTo(-hw + r, -hh);
  shape.lineTo(hw - r, -hh);
  shape.quadraticCurveTo(hw, -hh, hw, -hh + r);
  shape.lineTo(hw, hh - r);
  shape.quadraticCurveTo(hw, hh, hw - r, hh);
  shape.lineTo(-hw + r, hh);
  shape.quadraticCurveTo(-hw, hh, -hw, hh - r);
  shape.lineTo(-hw, -hh + r);
  shape.quadraticCurveTo(-hw, -hh, -hw + r, -hh);
  const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 2, curveSegments: 10 });
  g.translate(0, 0, -depth / 2);
  return g;
}

/** Procedural stand-in for the Blender GLB (same names, same look). */
function proceduralParts(): Parts {
  const body = new THREE.MeshStandardMaterial({ color: 0x17122a, roughness: 0.35, metalness: 0.6 });
  const sign = new THREE.MeshStandardMaterial({ color: 0xed215c, roughness: 0.45 });
  const rim = new THREE.MeshStandardMaterial({ color: 0xffdb40, roughness: 0.4, metalness: 0.1 });
  const white = new THREE.MeshStandardMaterial({ color: 0xfafaff, roughness: 0.5 });

  const parts: Parts = {};
  parts.Phone = new THREE.Mesh(roundedRectExtruded(0.72, 1.5, 0.1, 0.08), body);
  parts.Phone.name = 'Phone';
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.655, 1.415), white);
  screen.position.z = 0.0415;
  screen.name = 'Screen';
  // PlaneGeometry UVs have v=1 at the top; the GLB screen uses glTF convention (v=0 at top).
  const uv = screen.geometry.attributes.uv as THREE.BufferAttribute;
  for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
  parts.Screen = screen;
  const bump = new THREE.Mesh(roundedRectExtruded(0.22, 0.22, 0.06, 0.022), body);
  bump.position.set(-0.21, 0.56, -0.05);
  bump.name = 'CameraBump';
  parts.CameraBump = bump;

  const s = new THREE.Mesh(octagonExtruded(1.0, 0.12), sign);
  s.name = 'StopSign';
  parts.StopSign = s;
  const r = new THREE.Mesh(octagonExtruded(1.08, 0.16), rim);
  r.position.z = -0.01;
  r.name = 'StopRim';
  parts.StopRim = r;
  const label = new THREE.Mesh(
    new THREE.PlaneGeometry(1.7, 1.7),
    new THREE.MeshBasicMaterial({ map: makeStopLabelTexture(), transparent: true, toneMapped: false }),
  );
  label.position.z = 0.075;
  label.name = 'StopText';
  parts.StopText = label;

  const bubbleMats = [
    new THREE.MeshStandardMaterial({ color: 0x9e99b8, roughness: 0.55 }),
    new THREE.MeshStandardMaterial({ color: 0xff5ca8, roughness: 0.5 }),
    new THREE.MeshStandardMaterial({ color: 0x8c73ff, roughness: 0.5 }),
  ];
  const dims: [number, number, number][] = [[0.62, 0.36, 0.17], [0.46, 0.42, 0.2], [0.78, 0.3, 0.15]];
  dims.forEach((d, i) => {
    const m = new THREE.Mesh(roundedRectExtruded(d[0], d[1], d[2], 0.14), bubbleMats[i]);
    m.name = `Bubble${i + 1}`;
    parts[m.name] = m;
  });
  return parts;
}

async function loadParts(base: string): Promise<{ parts: Parts; fromGlb: boolean }> {
  try {
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(`${base}/models/scene.glb`);
    const parts: Parts = {};
    for (const name of ['Phone', 'Screen', 'CameraBump', 'StopSign', 'StopRim', 'StopInner', 'StopText', 'Bubble1', 'Bubble2', 'Bubble3']) {
      const o = gltf.scene.getObjectByName(name);
      if (o) parts[name] = o;
    }
    if (!parts.Phone || !parts.Screen || !parts.StopSign || !parts.Bubble1) throw new Error('GLB missing parts');
    return { parts, fromGlb: true };
  } catch (err) {
    console.warn('[hero3d] GLB unavailable, using procedural geometry', err);
    return { parts: proceduralParts(), fromGlb: false };
  }
}

function firstMesh(o: THREE.Object3D): THREE.Mesh | null {
  let found: THREE.Mesh | null = null;
  o.traverse((c) => { if (!found && (c as THREE.Mesh).isMesh) found = c as THREE.Mesh; });
  return found;
}

// ----------------------------------------------------------------- main
export async function initHero(canvas: HTMLCanvasElement, opts: HeroOptions) {
  const { base, hero, wrap } = opts;
  const rng = makeRng(opts.poster ? 1337 : (Date.now() & 0xffff) || 7);
  const rand = (a: number, b: number) => a + (b - a) * rng();

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, opts.isMobile ? 1.25 : 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.setClearColor(0x000000, 0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 80);
  camera.position.set(0, 0, 8);
  const CAM_Z = 8;

  // soft studio reflections for the PBR materials
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.35;
  pmrem.dispose();

  // lights: purple / pink key + fill, yellow rim behind the STOP
  scene.add(new THREE.AmbientLight(0x4b3a8a, 1.4));
  const key = new THREE.DirectionalLight(0xd6ccff, 1.7);
  key.position.set(-3, 5, 6);
  scene.add(key);
  const purple = new THREE.PointLight(PALETTE.primary, 90, 40, 2);
  purple.position.set(4.5, 3, 4);
  scene.add(purple);
  const pink = new THREE.PointLight(PALETTE.accent, 70, 40, 2);
  pink.position.set(-5, -3, 3);
  scene.add(pink);
  const rimLight = new THREE.PointLight(PALETTE.highlight, 120, 40, 2);
  rimLight.position.set(2.5, 5.5, -3.5);
  scene.add(rimLight);

  const { parts, fromGlb } = await loadParts(base);

  // --- phone
  const phone = new THREE.Group();
  const phoneInner = new THREE.Group(); // bob/tilt
  phone.add(phoneInner);
  phoneInner.add(parts.Phone!, parts.CameraBump ?? new THREE.Group(), parts.Screen!);
  const screenMesh = firstMesh(parts.Screen!)!;
  screenMesh.material = new THREE.MeshBasicMaterial({ map: makeScreenTexture(), toneMapped: false });
  // halo behind the phone
  const halo = new THREE.Mesh(
    new THREE.PlaneGeometry(3.2, 3.6),
    new THREE.MeshBasicMaterial({ map: makeGlowTexture('#7b5cff'), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.55, toneMapped: false }),
  );
  halo.position.z = -0.35;
  phoneInner.add(halo);
  scene.add(phone);

  // --- STOP sign
  const stop = new THREE.Group();
  const stopInner = new THREE.Group(); // squash on impact
  stop.add(stopInner);
  for (const n of ['StopRim', 'StopSign', 'StopInner', 'StopText']) if (parts[n]) stopInner.add(parts[n]!);
  // yellow edge glow sprite behind the sign
  const stopGlow = new THREE.Mesh(
    new THREE.PlaneGeometry(4.2, 4.2),
    new THREE.MeshBasicMaterial({ map: makeGlowTexture('#ffe066'), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.0, toneMapped: false }),
  );
  stopGlow.position.z = -0.2;
  stopInner.add(stopGlow);
  // impact shockwave ring
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.92, 1.0, 8, 1, Math.PI / 8),
    new THREE.MeshBasicMaterial({ color: PALETTE.highlight, transparent: true, opacity: 0, side: THREE.DoubleSide, toneMapped: false, depthWrite: false }),
  );
  ring.position.z = -0.1;
  stop.add(ring);
  scene.add(stop);

  // --- spam bubbles (instanced)
  const N_PER = opts.isMobile ? 10 : 16;
  const bubbleMeshes: THREE.InstancedMesh[] = [];
  const bubbles: Bubble[] = [];
  const dummy = new THREE.Object3D();
  for (const n of ['Bubble1', 'Bubble2', 'Bubble3']) {
    const src = parts[n] ? firstMesh(parts[n]!) : null;
    if (!src) continue;
    const im = new THREE.InstancedMesh(src.geometry, src.material as THREE.Material, N_PER);
    im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    im.frustumCulled = false;
    bubbleMeshes.push(im);
    scene.add(im);
    for (let i = 0; i < N_PER; i++) {
      bubbles.push({ p: new THREE.Vector3(), v: new THREE.Vector3(), r: new THREE.Euler(), rv: new THREE.Vector3(), s: 1, phase: rand(0, 6.28), life: 0, mode: 'drift' });
    }
  }

  // --- layout (responsive): computed from the visible frustum at z=0
  const L = {
    desktop: true,
    vh: 1, vw: 1,
    phoneScale: 1,
    phonePos: new THREE.Vector3(),
    stopScale: 1,
    stopStart: new THREE.Vector3(),
    stopEnd: new THREE.Vector3(),
    spawnR: 5,
  };
  function layout() {
    const w = Math.max(1, canvas.clientWidth), h = Math.max(1, canvas.clientHeight);
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    L.desktop = w >= 900;
    camera.fov = L.desktop ? 36 : 50;
    camera.updateProjectionMatrix();
    L.vh = 2 * CAM_Z * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    L.vw = L.vh * camera.aspect;
    L.phoneScale = (L.desktop ? 0.64 : 0.46) * L.vh / 1.5;
    if (L.desktop) L.phonePos.set(0.22 * L.vw, -0.05 * L.vh, 0);
    else L.phonePos.set(0.02 * L.vw, -0.215 * L.vh, 0);
    phone.scale.setScalar(L.phoneScale);
    phone.position.copy(L.phonePos);

    L.stopScale = (L.desktop ? 0.46 : 0.44) * L.phoneScale;
    stop.scale.setScalar(L.stopScale);
    // The sign sits in front of the phone (closer to the camera), so scale its x/y by the
    // perspective factor at that depth to keep it projected over the phone.
    const zEnd = 0.7 * L.phoneScale;
    const k = (CAM_Z - zEnd) / CAM_Z;
    L.stopEnd.set((L.phonePos.x + 0.06 * L.phoneScale) * k, (L.phonePos.y + 0.14 * L.phoneScale) * k, zEnd);
    L.stopStart.set(L.stopEnd.x + 0.04 * L.vw * k, (0.5 * L.vh + 0.2 * L.vh) * k + 1.2 * L.stopScale, zEnd);
    L.spawnR = Math.max(L.vw, L.vh) * 0.62;
  }
  layout();

  // --- bubbles behaviour
  const target = new THREE.Vector3();
  function spawn(b: Bubble, nearPhone = false) {
    const a = rand(0, Math.PI * 2);
    const el = rand(-0.45, 0.45);
    const R = nearPhone ? L.spawnR * rand(0.25, 0.75) : L.spawnR * rand(0.95, 1.3);
    b.p.set(L.phonePos.x + R * Math.cos(a) * Math.cos(el), L.phonePos.y + R * Math.sin(el) * 0.9, rand(-2.5, 1.2) * L.phoneScale * 0.45);
    target.copy(L.phonePos).add(new THREE.Vector3(rand(-0.2, 0.2), rand(-0.3, 0.3), 0.3).multiplyScalar(L.phoneScale));
    b.v.copy(target).sub(b.p).normalize().multiplyScalar(rand(0.22, 0.42) * L.phoneScale);
    b.r.set(rand(-0.4, 0.4), rand(-0.6, 0.6), rand(-0.3, 0.3));
    b.rv.set(rand(-1, 1), rand(-1, 1), rand(-1, 1)).multiplyScalar(0.5);
    b.s = rand(0.42, 0.8) * L.phoneScale;
    b.life = 0;
    b.mode = 'drift';
  }
  bubbles.forEach((b) => spawn(b, true));

  const tmpDir = new THREE.Vector3();
  function scatter() {
    for (const b of bubbles) {
      tmpDir.copy(b.p).sub(L.stopEnd);
      tmpDir.y += 0.3 * L.phoneScale;
      if (tmpDir.lengthSq() < 1e-4) tmpDir.set(rand(-1, 1), rand(-1, 1), 0.3);
      tmpDir.normalize();
      b.v.copy(tmpDir).multiplyScalar(rand(2.2, 4.2) * L.phoneScale);
      b.v.z += rand(-0.5, 0.8) * L.phoneScale;
      b.rv.set(rand(-1, 1), rand(-1, 1), rand(-1, 1)).multiplyScalar(5);
      b.mode = 'scatter';
      b.life = 0;
    }
  }

  function updateBubbles(dt: number, t: number) {
    let k = 0;
    for (const im of bubbleMeshes) {
      for (let i = 0; i < N_PER; i++, k++) {
        const b = bubbles[k];
        b.life += dt;
        if (b.mode === 'drift') {
          b.p.addScaledVector(b.v, dt);
          b.p.y += Math.sin(t * 1.6 + b.phase) * 0.0025 * L.phoneScale;
          b.p.x += Math.cos(t * 1.1 + b.phase) * 0.0018 * L.phoneScale;
          if (b.p.distanceTo(L.phonePos) < 0.62 * L.phoneScale) spawn(b);
        } else {
          b.p.addScaledVector(b.v, dt);
          b.v.multiplyScalar(Math.max(0, 1 - 0.9 * dt));
          if (b.life > 2.6 || b.p.distanceTo(L.phonePos) > L.spawnR * 1.5) spawn(b);
        }
        b.r.x += b.rv.x * dt;
        b.r.y += b.rv.y * dt;
        b.r.z += b.rv.z * dt;
        dummy.position.copy(b.p);
        dummy.rotation.copy(b.r);
        // pop in from the spawn point
        const grow = Math.min(1, b.life * 1.5);
        dummy.scale.setScalar(b.s * (0.2 + 0.8 * grow));
        dummy.updateMatrix();
        im.setMatrixAt(i, dummy.matrix);
      }
      im.instanceMatrix.needsUpdate = true;
    }
  }

  // --- slam progress: max(scroll progress, idle auto-play)
  let pScroll = 0;
  let pAuto = 0;
  let autoStarted = -1;
  let userScrolled = false;
  const IDLE_MS = 2600;
  const startedAt = performance.now();
  function readScroll() {
    const range = Math.max(1, wrap.offsetHeight - hero.offsetHeight);
    const top = wrap.getBoundingClientRect().top; // 0 at start, negative as we scroll
    pScroll = THREE.MathUtils.clamp(-top / range, 0, 1);
    if (pScroll > 0.02) userScrolled = true;
  }
  readScroll();

  let impacted = false;
  let impactT = 99;
  let shake = 0;
  const easeIn = (x: number) => x * x * x;

  function updateStop(dt: number, now: number) {
    if (!userScrolled && autoStarted < 0 && now - startedAt > IDLE_MS) autoStarted = now;
    if (autoStarted >= 0 && pAuto < 1) pAuto = Math.min(1, (now - autoStarted) / 1100);
    const p = Math.max(pScroll, pAuto);
    const e = easeIn(p);
    stop.position.lerpVectors(L.stopStart, L.stopEnd, e);
    stop.rotation.set(THREE.MathUtils.lerp(-0.95, 0.1, e), THREE.MathUtils.lerp(0.55, -0.14, e), THREE.MathUtils.lerp(0.5, -0.16, e));
    const near = p > 0.985;
    if (near && !impacted) {
      impacted = true;
      impactT = 0;
      shake = 1;
      scatter();
    }
    if (!near && impacted && p < 0.6) impacted = false;
    impactT += dt;
    // squash + wobble on impact
    const wob = impacted ? Math.exp(-impactT * 5) * Math.sin(impactT * 34) : 0;
    stopInner.scale.set(1 + 0.16 * wob, 1 - 0.14 * wob, 1 + 0.1 * wob);
    (stopGlow.material as THREE.MeshBasicMaterial).opacity = impacted ? 0.35 + 0.35 * Math.exp(-impactT * 2.5) : 0.1 * p;
    // shockwave ring
    const rm = ring.material as THREE.MeshBasicMaterial;
    if (impacted && impactT < 0.7) {
      const k = impactT / 0.7;
      ring.scale.setScalar(1 + k * 2.6);
      rm.opacity = (1 - k) * 0.9;
    } else {
      rm.opacity = 0;
    }
    // phone recoil
    phoneInner.position.z = impacted ? -0.18 * Math.exp(-impactT * 4) * Math.max(0, Math.sin(impactT * 18)) : 0;
    shake = Math.max(0, shake - dt * 2.2);
  }

  // --- pointer parallax (desktop) / auto rotation (mobile)
  let mx = 0, my = 0, tmx = 0, tmy = 0;
  const onPointer = (ev: PointerEvent) => {
    tmx = (ev.clientX / window.innerWidth - 0.5) * 2;
    tmy = (ev.clientY / window.innerHeight - 0.5) * 2;
  };
  if (!opts.isMobile) window.addEventListener('pointermove', onPointer, { passive: true });

  function updatePhone(dt: number, t: number) {
    mx += (tmx - mx) * Math.min(1, dt * 4);
    my += (tmy - my) * Math.min(1, dt * 4);
    phoneInner.position.y = Math.sin(t * 1.15) * 0.05;
    if (opts.isMobile) {
      phoneInner.rotation.set(Math.sin(t * 0.7) * 0.08 + 0.05, Math.sin(t * 0.45) * 0.42, Math.sin(t * 0.5) * 0.04);
    } else {
      phoneInner.rotation.set(-my * 0.22 + Math.sin(t * 0.9) * 0.05 + 0.04, -0.28 + mx * 0.4 + Math.sin(t * 0.7) * 0.07, Math.sin(t * 0.6) * 0.03 - 0.03);
    }
    camera.position.x = mx * 0.35 + (shake > 0 ? (rng() - 0.5) * 0.25 * shake : 0);
    camera.position.y = -my * 0.2 + (shake > 0 ? (rng() - 0.5) * 0.25 * shake : 0);
    camera.lookAt(0, 0, 0);
    halo.rotation.z = t * 0.05;
  }

  // --- loop with pause when hidden / off-screen
  let running = false;
  let raf = 0;
  let last = performance.now();
  let t = 0;
  function frame(now: number) {
    if (!running) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    t += dt;
    readScroll();
    updateStop(dt, now);
    updateBubbles(dt, t);
    updatePhone(dt, t);
    renderer.render(scene, camera);
    raf = requestAnimationFrame(frame);
  }
  function start() {
    if (running || opts.reducedMotion) return;
    running = true;
    last = performance.now();
    raf = requestAnimationFrame(frame);
  }
  function stopLoop() {
    running = false;
    cancelAnimationFrame(raf);
  }
  let heroVisible = true;
  const io = new IntersectionObserver((entries) => {
    heroVisible = entries[0]?.isIntersecting ?? true;
    if (heroVisible && document.visibilityState === 'visible') start(); else stopLoop();
  }, { threshold: 0.02 });
  io.observe(hero);
  const onVis = () => { if (document.visibilityState === 'visible' && heroVisible) start(); else stopLoop(); };
  document.addEventListener('visibilitychange', onVis);

  let resizeT = 0;
  const onResize = () => {
    cancelAnimationFrame(resizeT);
    resizeT = requestAnimationFrame(() => { layout(); if (opts.reducedMotion) renderStatic(); });
  };
  window.addEventListener('resize', onResize);

  // static frame: STOP already in place, bubbles scattered
  function renderStatic() {
    pAuto = 1;
    impacted = true;
    impactT = 2;
    stop.position.copy(L.stopEnd);
    stop.rotation.set(0.1, -0.14, -0.16);
    stopInner.scale.setScalar(1);
    (stopGlow.material as THREE.MeshBasicMaterial).opacity = 0.4;
    bubbles.forEach((b) => { spawn(b, true); b.life = 2; });
    updateBubbles(0, 0);
    phoneInner.rotation.set(0.04, opts.isMobile ? 0.25 : -0.28, -0.03);
    camera.position.set(0, 0, CAM_Z);
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
  }

  if (opts.reducedMotion || opts.poster) {
    renderStatic();
    if (opts.poster) {
      // a couple of settle frames so the bubbles read as "just scattered"
      for (let i = 0; i < 40; i++) updateBubbles(1 / 60, i / 60);
      renderer.render(scene, camera);
    }
  } else {
    // first frame immediately, then the loop
    renderer.render(scene, camera);
    start();
  }
  canvas.classList.add('is-ready');

  return {
    fromGlb,
    destroy() {
      stopLoop();
      io.disconnect();
      document.removeEventListener('visibilitychange', onVis);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('pointermove', onPointer);
      renderer.dispose();
    },
  };
}
