// node ad3/shoot_lp.cjs [url] -> ad3/assets/lp_stop.png (402x874 CSS px at 3x, like an iPhone 17 Pro in Safari)
// The landing page the ad links to, captured headless with every analytics / database / pixel request blocked,
// so the capture is not a production visit.
const path = require('path');
const fs = require('fs');
const puppeteer = require('C:/Users/moise/Projects/ios-ui-kit/node_modules/puppeteer-core');

const url = process.argv[2] || 'https://spamclaims.com/lp/stop';
const BLOCK = /posthog|clarity\.ms|supabase\.co|facebook\.(com|net)|fbcdn|redtrack|cashedbackspam|googletagmanager|google-analytics|doubleclick|tiktok|hotjar|sentry/i;
(async () => {
  const out = path.join(__dirname, 'assets');
  fs.mkdirSync(out, { recursive: true });
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
    args: ['--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1');
  await page.setViewport({ width: 402, height: 874, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  await page.setRequestInterception(true);
  let blocked = 0;
  page.on('request', (r) => (BLOCK.test(r.url()) ? (blocked++, r.abort()) : r.continue()));
  await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  await new Promise((r) => setTimeout(r, 1800));       // let the hero animations settle
  await page.screenshot({ path: path.join(out, 'lp_stop.png') });
  const info = await page.evaluate(() => {
    const pick = (s) => { const e = document.querySelector(s); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, text: e.textContent.trim().slice(0, 80) }; };
    const buttons = [...document.querySelectorAll('button, a')].filter((e) => e.getBoundingClientRect().top < 874 && e.textContent.trim())
      .map((e) => { const r = e.getBoundingClientRect(); return { text: e.textContent.trim().slice(0, 50), x: r.x, y: r.y, w: r.width, h: r.height }; });
    return { h1: pick('h1'), buttons, bg: getComputedStyle(document.body).backgroundColor };
  });
  fs.writeFileSync(path.join(out, 'lp_stop.json'), JSON.stringify(info, null, 1));
  console.log('blocked', blocked, 'requests;', JSON.stringify(info).slice(0, 900));
  await browser.close();
})();
