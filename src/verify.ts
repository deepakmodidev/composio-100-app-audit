import fs from "node:fs/promises";
import { chromium } from "playwright";
import { AppResearchSchema } from "./schema.js";
const rows = AppResearchSchema.array().parse(
  JSON.parse(
    await fs.readFile(
      new URL("../data/apps.final.json", import.meta.url),
      "utf8",
    ),
  ),
);
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
const results = [];
for (const app of rows) {
  for (const ev of app.evidence) {
    try {
      const res = await page.goto(ev.url, {
        waitUntil: "domcontentloaded",
        timeout: 30000,
      });
      const title = await page.title();
      results.push({
        appId: app.id,
        app: app.name,
        url: ev.url,
        status: res?.status() || 0,
        title,
        ok: !!res && res.status() < 400,
      });
    } catch (e) {
      results.push({
        appId: app.id,
        app: app.name,
        url: ev.url,
        status: 0,
        title: "",
        ok: false,
        error: String(e),
      });
    }
  }
}
await browser.close();
await fs.writeFile(
  new URL("../data/browser-check.json", import.meta.url),
  JSON.stringify(results, null, 2),
);
console.log(
  `${results.filter((x) => x.ok).length}/${results.length} evidence pages loaded`,
);
