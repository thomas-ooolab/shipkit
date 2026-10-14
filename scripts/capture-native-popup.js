#!/usr/bin/env node
// capture-native-popup.js — screenshot a page state the browser draws OUTSIDE the page (a native <select>
// popup, a date picker…), which Playwright headless and screenshot tools cannot capture. macOS only.
//
//   usage: node capture-native-popup.js --fe <dir with node_modules/playwright> --setup <setup.js>
//                                       --click <css selector> --out <result.png>
//
// <setup.js> is yours: `module.exports = async (page) => { …log in with the seeded test user, goto the page… }`.
// Then this opens a visible Chromium (headless:false) at 60,60, clicks the element — Playwright's click opens
// the native popup (an extension's click does not) — and, ~1.5s later, finds Chromium's windows via
// CoreGraphics (popup-tools.swift): the main window is layer 0, the popup a small onscreen layer-101 window.
// The main window is captured with `screencapture -l <id>` (never the popup that way: it returns the parent
// window too); the popup with `screencapture -R` on ITS OWN rectangle — the one allowed -R, because a layer-101
// popup is on top, so only its pixels land in the image — and it is pasted onto the main image.
// A <select> target also prints its options (put them in the evidence .txt). Open the PNG before attaching it.
//
// Needs Screen Recording permission for the terminal, and the Chromium window on the visible Space/display.
// exit 0 saved · 2 no main window · 3 no popup window (saved <out>-nopopup.png) · 64 usage · 1 other error

const { execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');
const arg = n => { const i = process.argv.indexOf('--' + n); return i > 0 ? process.argv[i + 1] : undefined; };
const [FE, SETUP, CLICK, OUT] = ['fe', 'setup', 'click', 'out'].map(arg);
if (!FE || !SETUP || !CLICK || !OUT) {
  console.error('usage: node capture-native-popup.js --fe <dir> --setup <setup.js> --click <css> --out <png>');
  process.exit(64);
}
const { chromium } = require(require.resolve('playwright', { paths: [path.resolve(FE)] }));
const swift = (...a) => execFileSync('swift', [path.join(__dirname, 'popup-tools.swift'), ...a.map(String)]).toString().trim();
const mainPng = OUT + '.main.tmp.png', popPng = OUT + '.popup.tmp.png';

(async () => {
  const browser = await chromium.launch({ headless: false, args: ['--window-position=60,60', '--window-size=1280,900'] });
  try {
    const ctx = await browser.newContext({ viewport: null });
    const page = await ctx.newPage();
    await require(path.resolve(SETUP))(page);
    const el = page.locator(CLICK).first();
    await el.scrollIntoViewIfNeeded();
    if (await el.evaluate(e => e.tagName) === 'SELECT')
      console.log('options:', JSON.stringify(await el.evaluate(s => [...s.options].map(o => o.textContent))));
    // a window opened on another display/Space makes `screencapture -l` fail: pull it onto the main screen
    const cdp = await ctx.newCDPSession(page);
    const { windowId } = await cdp.send('Browser.getWindowForTarget');
    await cdp.send('Browser.setWindowBounds', { windowId, bounds: { left: 60, top: 60, width: 1280, height: 900, windowState: 'normal' } });
    try { execFileSync('osascript', ['-e', `tell application "System Events" to set frontmost of (first process whose unix id is ${browser.process().pid}) to true`]); } catch {}
    await page.waitForTimeout(2000);
    await page.bringToFront();
    await el.click();
    await page.waitForTimeout(1500);

    const wins = JSON.parse(swift('list')).filter(w => w.onscreen);
    const main = wins.filter(w => w.layer === 0).sort((a, b) => b.w * b.h - a.w * a.h)[0];
    if (!main) { console.log('NO MAIN WINDOW'); process.exitCode = 2; return; }
    execFileSync('screencapture', ['-x', '-o', '-l', main.id, mainPng]);
    const pop = wins.find(w => w.layer === 101);
    if (!pop) { fs.renameSync(mainPng, OUT.replace(/\.png$/, '') + '-nopopup.png'); console.log('NO POPUP WINDOW; saved main only'); process.exitCode = 3; return; }
    execFileSync('screencapture', ['-x', '-R', `${pop.x},${pop.y},${pop.w},${pop.h}`, popPng]);
    console.log(swift('compose', mainPng, popPng, OUT, main.x, main.y, pop.x, pop.y, main.w), OUT);
  } finally {
    await browser.close();
    for (const f of [mainPng, popPng]) fs.rmSync(f, { force: true });
  }
})().catch(e => { console.error('ERROR', e.message); process.exit(1); });
