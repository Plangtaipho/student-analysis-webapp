// End-to-end check of the week-2 flow (teacher evaluation, class summary, full PDF).
// Prepare data first on an empty database (the demo room must be room 1):
//   DATABASE_URL=... python -m scripts.seed_demo   (19 students, 17 assessed)
// Usage: BASE_URL=http://localhost:8077 node e2e/week2_flow.cjs
const { chromium, devices } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE_URL || "http://localhost:8077";
const OUT = process.env.OUT_DIR || path.join(__dirname, "out");
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const t = await ctx.newPage();
  t.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
  t.on("pageerror", (e) => errors.push(e.message));

  await t.goto(`${BASE}/login`);
  await t.fill("#email", "demo@example.com");
  await t.fill("#password", "demo12345");
  await t.click("button[type=submit]");
  await t.waitForURL(`${BASE}/app`);
  await t.goto(`${BASE}/app/classrooms/1`);
  await t.waitForSelector("#eval-start");
  await t.screenshot({ path: path.join(OUT, "w2-classroom.png"), fullPage: true });

  // Evaluate the next student who has not been assessed yet.
  await t.click("#eval-start");
  await t.waitForURL(/\/evaluate$/);
  await t.waitForSelector('input[name="r-d1_1"]');
  await t.click('button[data-fill="fair"]');
  await t.click('input[name="r-d1_1"][value="good"] + span');
  await t.click('input[name="r-d3_3"][value="improve"] + span');
  await t.fill('input[name="n-d3_3"]', "ส่งงานช้า");
  await t.fill("#last_grade", "3");
  await t.fill("#teacher_comment", "ควรติดตามการส่งงาน");
  await t.waitForFunction(() => !/ประเมินครบ/.test(document.querySelector("#auto-group").textContent));
  const autoGroup = await t.textContent("#auto-group");
  await t.screenshot({ path: path.join(OUT, "w2-evaluate.png"), fullPage: true });
  await t.click('button[data-then="next"]');
  await t.waitForURL((u) => !u.pathname.endsWith(`/submissions/18/evaluate`));
  console.log("after save ->", t.url(), "| auto group:", autoGroup.trim());

  // Mobile view of the evaluation page.
  const m = await browser.newContext({ ...devices["iPhone 13"] });
  const mp = await m.newPage();
  mp.on("pageerror", (e) => errors.push("mobile: " + e.message));
  await mp.context().addCookies(await ctx.cookies());
  await mp.goto(`${BASE}/app/classrooms/1/submissions/19/evaluate`);
  await mp.waitForSelector('input[name="r-d1_1"]');
  await mp.screenshot({ path: path.join(OUT, "w2-evaluate-mobile.png"), fullPage: false });

  // Summary page + full PDF.
  await t.goto(`${BASE}/app/classrooms/1/summary`);
  await t.waitForFunction(() => document.querySelector("#st-evaluated").textContent !== "-");
  const evaluated = await t.textContent("#st-evaluated");
  await t.screenshot({ path: path.join(OUT, "w2-summary.png"), fullPage: true });
  await t.fill("#doc_no", "๔๑๗/๒๕๖๙");
  const [resp] = await Promise.all([
    ctx.waitForEvent("response", { predicate: (r) => r.url().includes("/pdf/full"), timeout: 60000 }),
    t.click("#pdf-full"),
  ]);
  const pdfOk = resp.status() === 200 && (resp.headers()["content-type"] || "").includes("pdf");
  console.log("evaluated:", evaluated, "| full pdf:", pdfOk);
  await browser.close();
  if (errors.length) { console.error("Console errors:\n" + errors.join("\n")); process.exit(1); }
  if (evaluated.trim() !== "18" || !pdfOk) process.exit(1);
  console.log("WEEK2 E2E OK");
})();
