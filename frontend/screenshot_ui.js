// Quick UI screenshot for design review
const { chromium } = require('playwright');
const path = require('path');
const fs   = require('fs');

// Inline the built HTML as a preview with mock data
const html = fs.readFileSync(path.join(__dirname, 'dist/index.html'), 'utf8')
  .replace('</head>', `
  <style>
    /* Force the login page to render standalone */
  </style>
  </head>`);

(async () => {
  const browser = await chromium.launch();
  const page    = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });

  // Screenshot the built login page directly from dist
  await page.goto(`file://${path.join(__dirname, 'dist/index.html')}`);
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'ui_preview_login.png', fullPage: false });

  console.log('Saved: ui_preview_login.png');
  await browser.close();
})();
