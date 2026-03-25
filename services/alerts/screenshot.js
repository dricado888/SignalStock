const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 740, height: 900 });
  const htmlPath = path.resolve(__dirname, 'preview.html');
  await page.goto(`file://${htmlPath}`);
  await page.waitForTimeout(300);
  await page.screenshot({
    path: path.resolve(__dirname, 'email_preview.png'),
    fullPage: true,
  });
  await browser.close();
  console.log('Saved: email_preview.png');
})();
