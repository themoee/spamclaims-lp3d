// node ad6/shoot_quick.cjs [base=http://localhost:8082] -> ad6/assets/quick_{intro,what,count}.png (402x874 CSS px at
// 3x, like an iPhone 17 Pro) + quick.json (where the intro's button is), from the quick funnel (/lp/quick).
// Every database / analytics / pixel host is blocked: the local dev server talks to production.
const path = require('path');
const fs = require('fs');
const puppeteer = require('C:/Users/moise/Projects/ios-ui-kit/node_modules/puppeteer-core');

const base = process.argv[2] || 'http://localhost:8082';
const BLOCK = /supabase\.co|posthog|clarity\.ms|facebook\.(com|net)|fbcdn|redtrack|cashedbackspam|googletagmanager|google-analytics|doubleclick|tiktok|hotjar|sentry/i;
const external = (u) => { try { const h = new URL(u).hostname; return h !== 'localhost' && BLOCK.test(h); } catch { return false; } };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const out = path.join(__dirname, 'assets');
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true,
    args: ['--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.setUserAgent('Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1');
  await page.setViewport({ width: 402, height: 874, deviceScaleFactor: 3, isMobile: true, hasTouch: true });
  await page.setRequestInterception(true);
  page.on('request', (r) => (external(r.url()) ? r.abort() : r.continue()));
  // no drifting background texts in the stills (they would freeze mid-flight)
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }]);
  await page.goto(`${base}/lp/quick`, { waitUntil: 'networkidle2', timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  await sleep(1500);
  const btn = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button')].find((x) => /check my texts/i.test(x.textContent));
    const r = b.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
  await page.screenshot({ path: path.join(out, 'quick_intro.png') });
  const click = (re) => page.evaluate((src) => {
    const rx = new RegExp(src, 'i');
    [...document.querySelectorAll('button')].find((x) => rx.test(x.textContent.trim()) && x.offsetParent !== null).click();
  }, re);
  await click('^check my texts'); await sleep(700);
  await click('kept texting after i said stop'); await click('texted me after 9 pm'); await sleep(600);
  await page.screenshot({ path: path.join(out, 'quick_what.png') });
  await click('^next'); await sleep(700);
  await click('^this month$'); await sleep(700);
  await click('^6–10$'); await sleep(900);
  await page.screenshot({ path: path.join(out, 'quick_count.png') });
  fs.writeFileSync(path.join(out, 'quick.json'), JSON.stringify({ cta: btn }, null, 1));
  console.log('cta', JSON.stringify(btn));
  await browser.close();
})();
