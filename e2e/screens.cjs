// Screenshot every main page (desktop + phone) for a visual review.
// Needs the demo data:  python -m scripts.seed_demo
// Usage: BASE_URL=http://localhost:8077 OUT_DIR=e2e/out/ui node e2e/screens.cjs
const { chromium, devices } = require("playwright");
const fs = require("fs");
const path = require("path");
const BASE = process.env.BASE_URL || "http://localhost:8077";
const OUT = process.env.OUT_DIR || path.join(__dirname, "out", "ui");
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const shots = async (ctx, tag, pages) => {
    const p = await ctx.newPage();
    p.on("pageerror", (e) => errors.push(`${tag}: ${e.message}`));
    p.on("console", (m) => { if (m.type() === "error") errors.push(`${tag}: ${m.text()}`); });
    for (const [name, url, wait] of pages) {
      await p.goto(BASE + url);
      if (wait) await p.waitForSelector(wait);
      await p.waitForTimeout(300);
      await p.screenshot({ path: path.join(OUT, `${tag}-${name}.png`), fullPage: true });
    }
    return p;
  };
  const desk = await browser.newContext({ viewport: { width: 1280, height: 860 } });
  const phone = await browser.newContext({ ...devices["iPhone 13"] });
  await shots(desk, "d", [["home", "/"], ["login", "/login"]]);
  await shots(phone, "m", [["home", "/"]]);
  const p = await desk.newPage();
  await p.goto(BASE + "/login");
  await p.fill("#email", "demo@example.com");
  await p.fill("#password", "demo12345");
  await p.click("button[type=submit]");
  await p.waitForURL(BASE + "/app");
  await phone.addCookies(await desk.cookies());
  const room = await (await p.request.get(BASE + "/api/classrooms/1")).json();
  const form = new URL(room.student_link).pathname;
  const teacher = [
    ["dashboard", "/app", ".room-card"],
    ["classroom", "/app/classrooms/1", "#subs-body tr"],
    ["evaluate", "/app/classrooms/1/submissions/2/evaluate", 'input[name="r-d1_1"]'],
    ["summary", "/app/classrooms/1/summary", "#sum-body tr"],
    ["submission", "/app/classrooms/1/submissions/2", "h1"],
    ["profile", "/app/profile", "form"],
  ];
  await shots(desk, "d", teacher);
  await shots(phone, "m", teacher);
  const student = await browser.newContext({ ...devices["iPhone 13"] });
  const sp = await shots(student, "m", [["student-form", form, "#sform"]]);
  await sp.click("#next").catch(() => {});
  await sp.fill("#f-no", "30"); await sp.fill("#f-name", "นายทดสอบ ระบบ");
  await sp.click("#next"); await sp.waitForTimeout(200);
  await sp.screenshot({ path: path.join(OUT, "m-student-step2.png"), fullPage: true });
  await browser.close();
  if (errors.length) { console.error(errors.join("\n")); process.exit(1); }
  console.log("screens OK ->", OUT);
})();
