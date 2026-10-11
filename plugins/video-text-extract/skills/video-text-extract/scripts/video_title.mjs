// Read title metadata using the existing cat-catch Playwright installation.
import { createRequire } from 'node:module';
import { readFile } from 'node:fs/promises';
const [cat, url, option, sessionFile] = process.argv.slice(2);
const { chromium } = createRequire(cat)('playwright');
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: option === '--storage-state' ? JSON.parse(await readFile(sessionFile, 'utf8')) : undefined,
  });
  if (option === '--cookies') await context.addCookies(JSON.parse(await readFile(sessionFile, 'utf8')));
  const page = await context.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1000);
  const title = await page.evaluate(() =>
    document.querySelector('meta[property="og:title"]')?.content?.trim()
    || document.querySelector('meta[name="twitter:title"]')?.content?.trim()
    || document.title.trim());
  // A navigation can return HTTP 200 with a challenge/error document.
  // Its boilerplate title is not evidence of the video's title.
  const unavailable = /^(出错啦|访问受限|访问验证|安全验证|验证码|access denied|just a moment|403 forbidden|404 not found|error\b)/i.test(title);
  console.log(JSON.stringify({ title: unavailable ? '' : title }));
} catch {
  console.error('Video title metadata unavailable');
  process.exitCode = 1;
} finally {
  await browser?.close();
}
