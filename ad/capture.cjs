// node ad/capture.cjs [--frames ../blender/frames/ad] [--out ad/out/frames] [--step 1] [--only 0,90,180]
// Composites every ad frame (Blender render + captions + end card) in headless Chrome at exactly 1080x1920.
// puppeteer-core comes from the iOS kit's install; Chrome is the system one.
const path = require('path');
const fs = require('fs');
const puppeteer = require('C:/Users/moise/Projects/ios-ui-kit/node_modules/puppeteer-core');

const arg = (k, d) => {
  const i = process.argv.indexOf(`--${k}`);
  return i > 0 ? process.argv[i + 1] : d;
};
const HERE = __dirname;
const frames = arg('frames', '../blender/frames/ad');
const out = path.resolve(HERE, '..', arg('out', 'ad/out/frames'));
const step = Number(arg('step', '1'));
const only = arg('only', '') ? arg('only').split(',').map(Number) : null;
const editFile = arg('edit', 'edit.json');

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const edit = JSON.parse(fs.readFileSync(path.join(HERE, editFile), 'utf8'));
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
    args: ['--allow-file-access-from-files', '--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  const url = 'file:///' + path.join(HERE, 'ad.html').replace(/\\/g, '/') + `?frames=${encodeURIComponent(frames)}&edit=${encodeURIComponent(editFile)}`;
  await page.goto(url, { waitUntil: 'load' });
  await page.evaluate(() => window.ready);
  const list = only || [...Array(edit.t.length).keys()].filter((i) => i % step === 0);
  const srcDir = path.resolve(HERE, frames);
  const t0 = Date.now();
  for (const i of list) {
    const name = `${String(i).padStart(4, '0')}.png`;
    // a preview set may hold only some frames: show the nearest earlier render
    let src = i;
    while (src > 0 && !fs.existsSync(path.join(srcDir, `${String(src).padStart(4, '0')}.png`))) src--;
    await page.evaluate((i, src) => window.renderFrame(i, src), i, src);
    await page.screenshot({ path: path.join(out, name), type: 'png' });
  }
  console.log(`captured ${list.length} frames in ${((Date.now() - t0) / 1000).toFixed(1)} s -> ${out}`);
  await browser.close();
})();
