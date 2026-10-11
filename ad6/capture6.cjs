// node ad6/capture6.cjs [--out ad6/out/frames] [--only 0,240] [--step 1] [--from 0] [--to 995]
// Composites every frame of ad 6 (ad6.html: the 3D shots, the live iOS kit screens, stickers, captions, end card).
// puppeteer-core comes from the iOS kit's install; Chrome is the system one.
const path = require('path');
const fs = require('fs');
const puppeteer = require('C:/Users/moise/Projects/ios-ui-kit/node_modules/puppeteer-core');

const arg = (k, d) => {
  const i = process.argv.indexOf(`--${k}`);
  return i > 0 ? process.argv[i + 1] : d;
};
const HERE = __dirname;
const out = path.resolve(HERE, '..', arg('out', 'ad6/out/frames'));
const step = Number(arg('step', '1'));
const only = arg('only', '') ? arg('only').split(',').map(Number) : null;

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const edit = JSON.parse(fs.readFileSync(path.join(HERE, 'edit.json'), 'utf8'));
  const from = Number(arg('from', '0')), to = Number(arg('to', String(edit.frames - 1)));
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--allow-file-access-from-files', '--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE', m.text()); });
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  await page.goto('file:///' + path.join(HERE, 'ad6.html').replace(/\\/g, '/'), { waitUntil: 'load' });
  await page.evaluate(() => window.ready);
  const list = only || [...Array(edit.frames).keys()].filter((i) => i >= from && i <= to && (i - from) % step === 0);
  const t0 = Date.now();
  for (const i of list) {
    await page.evaluate((i) => window.renderFrame(i), i);
    await page.screenshot({ path: path.join(out, `${String(i).padStart(4, '0')}.png`), type: 'png' });
  }
  console.log(`captured ${list.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s -> ${out}`);
  await browser.close();
})();
