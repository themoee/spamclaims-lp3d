// @ts-check
import { defineConfig } from 'astro/config';

// Deployed to GitHub Pages at https://themoee.github.io/spamclaims-lp3d/
// Every asset/link in the page is prefixed with import.meta.env.BASE_URL.
export default defineConfig({
  site: 'https://themoee.github.io',
  base: '/spamclaims-lp3d',
  output: 'static',
  trailingSlash: 'ignore',
  compressHTML: true,
  build: {
    // Critical CSS: the page's only stylesheet is inlined into the HTML.
    inlineStylesheets: 'always',
    assets: '_assets',
  },
  vite: {
    build: {
      // three.js is loaded via a dynamic import after first paint; keep it in its own chunk.
      chunkSizeWarningLimit: 900,
    },
  },
});
