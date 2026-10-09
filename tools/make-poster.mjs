// Renders public/poster.webp (scene only, WebGL-off fallback) and public/og.jpg (hero with headline)
// by screenshotting the running site with headless Chrome (software WebGL via SwiftShader).
//
//   npm run preview            (in another terminal)
//   node tools/make-poster.mjs http://127.0.0.1:4321/spamclaims-lp3d/
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import sharp from 'sharp';

const url = process.argv[2] || 'http://127.0.0.1:4321/spamclaims-lp3d/';
const root = resolve(new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));

const chromeCandidates = [
  process.env.CHROME_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  join(process.env.LOCALAPPDATA || '', 'Google\\Chrome\\Application\\chrome.exe'),
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].filter(Boolean);
const chrome = chromeCandidates.find((p) => existsSync(p));
if (!chrome) {
  console.error('Chrome not found; set CHROME_PATH');
  process.exit(1);
}

function shot(pageUrl, w, h, out) {
  const profile = mkdtempSync(join(tmpdir(), 'lp3d-chrome-'));
  try {
    execFileSync(
      chrome,
      [
        '--headless=new',
        '--hide-scrollbars',
        '--no-first-run',
        '--disable-extensions',
        '--use-angle=swiftshader',
        '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist',
        `--user-data-dir=${profile}`,
        `--window-size=${w},${h}`,
        '--virtual-time-budget=20000',
        `--screenshot=${out}`,
        pageUrl,
      ],
      { stdio: 'inherit', timeout: 120000 },
    );
  } finally {
    try { rmSync(profile, { recursive: true, force: true }); } catch {}
  }
}

const sep = url.includes('?') ? '&' : '?';
const posterPng = join(tmpdir(), 'lp3d-poster.png');
const ogPng = join(tmpdir(), 'lp3d-og.png');

shot(`${url}${sep}poster=1`, 1600, 900, posterPng);
await sharp(posterPng).webp({ quality: 78 }).toFile(join(root, 'public', 'poster.webp'));

shot(`${url}${sep}og=1`, 1200, 630, ogPng);
await sharp(ogPng).jpeg({ quality: 84, mozjpeg: true }).toFile(join(root, 'public', 'og.jpg'));

for (const f of ['poster.webp', 'og.jpg']) {
  const meta = await sharp(join(root, 'public', f)).metadata();
  console.log(`${f}: ${meta.width}x${meta.height}`);
}
