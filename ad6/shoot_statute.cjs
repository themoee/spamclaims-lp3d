// node ad6/shoot_statute.cjs -> ad6/assets/statute.png (the federal law card, 2x) + statute.json (the card size and
// the rectangles of the highlighted words, line by line, in card CSS px) for the compositor's marker sweep.
const path = require('path');
const fs = require('fs');
const puppeteer = require('C:/Users/moise/Projects/ios-ui-kit/node_modules/puppeteer-core');

(async () => {
  const out = path.join(__dirname, 'assets');
  fs.mkdirSync(out, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
    args: ['--allow-file-access-from-files', '--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1000, height: 1200, deviceScaleFactor: 2 });
  await page.goto('file:///' + path.join(__dirname, 'statute.html').replace(/\\/g, '/'), { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const info = await page.evaluate(() => {
    const card = document.getElementById('card').getBoundingClientRect();
    const rects = [...document.getElementById('hl').getClientRects()].map((r) => ({ x: r.x - card.x, y: r.y - card.y, w: r.width, h: r.height }));
    return { w: card.width, h: card.height, hl: rects };
  });
  const el = await page.$('#card');
  await el.screenshot({ path: path.join(out, 'statute.png'), omitBackground: true });
  fs.writeFileSync(path.join(out, 'statute.json'), JSON.stringify(info, null, 1));
  console.log(JSON.stringify(info));
  await browser.close();
})();
