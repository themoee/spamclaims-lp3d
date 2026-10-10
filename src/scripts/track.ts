// Anonymous product analytics for this page, sent to the same PostHog project as the SpamClaims app.
// Same posture as the app: no cookies (a random id in localStorage), no PII, no session replay.
// Properties are this page's own attribution params (utm_*, vv, aff, sub1...) plus what the visitor did here:
// how far into the story they got and which CTA they used. Skipped on localhost and with ?notrack=1.

const KEY = 'phc_nBMxYsXiVaZNcU2VXo68LcZvfLsAKp9LfbNuDaXi2H6M';
const HOST = 'https://us.i.posthog.com';
const PARAMS = /^(utm_[a-z]+|vv|aff|affiliate|sub[1-5]|src|source|campaign|adset|ad)$/;
const CLICK_IDS = ['fbclid', 'ttclid', 'gclid', 'rtkcid', 'cmpid'];

const off = (() => {
  try {
    return /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname) || /[?&]notrack=1/.test(location.search);
  } catch {
    return true;
  }
})();

function distinctId(): string {
  try {
    let v = localStorage.getItem('sc_lp3d_id');
    if (!v) {
      v = crypto.randomUUID();
      localStorage.setItem('sc_lp3d_id', v);
    }
    return v;
  } catch {
    return 'anon';
  }
}

function attribution(): Record<string, string | boolean> {
  const out: Record<string, string | boolean> = {};
  try {
    const q = new URLSearchParams(location.search);
    q.forEach((v, k) => {
      if (PARAMS.test(k)) out[k] = v.slice(0, 120);
    });
    for (const k of CLICK_IDS) if (q.has(k)) out[`has_${k}`] = true;
  } catch {}
  return out;
}

export function track(event: string, props: Record<string, unknown> = {}) {
  if (off) return;
  const body = JSON.stringify({
    api_key: KEY,
    event,
    distinct_id: distinctId(),
    timestamp: new Date().toISOString(),
    properties: {
      ...attribution(),
      ...props,
      lp: '3d',
      $current_url: location.origin + location.pathname,
      $pathname: location.pathname,
      $referrer: document.referrer ? new URL(document.referrer).origin : '$direct',
      $screen_width: screen.width,
      $screen_height: screen.height,
      $lib: 'spamclaims-lp3d',
    },
  });
  try {
    fetch(`${HOST}/i/v0/e/`, { method: 'POST', body, keepalive: true, headers: { 'Content-Type': 'text/plain' } }).catch(
      () => {},
    );
  } catch {}
}
