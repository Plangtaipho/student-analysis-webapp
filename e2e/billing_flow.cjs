// End-to-end check of payments: locked second room -> slip upload -> admin approves.
// Start the server with PROMPTPAY_ID / PROMPTPAY_NAME and INITIAL_ADMIN_EMAIL=admin@example.com,
// INITIAL_ADMIN_PASSWORD=admin12345 on a database prepared with `python -m scripts.seed_demo`.
// Usage: BASE_URL=http://localhost:8077 node e2e/billing_flow.cjs
const { chromium, devices } = require("playwright");
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const BASE = process.env.BASE_URL || "http://localhost:8077";
const OUT = process.env.OUT_DIR || path.join(__dirname, "out");
fs.mkdirSync(OUT, { recursive: true });

// A tiny valid PNG to use as the slip.
function png(w, h) {
  const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (b) => { let c = 0xffffffff; for (const x of b) c = crcTable[(c ^ x) & 0xff] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([len, td, c]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 2;
  const raw = Buffer.alloc((w * 3 + 1) * h, 0xdd); for (let y = 0; y < h; y++) raw[y * (w * 3 + 1)] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}

async function login(page, email, password) {
  await page.goto(`${BASE}/login`);
  await page.fill("#email", email);
  await page.fill("#password", password);
  await page.click("button[type=submit]");
  await page.waitForURL(/\/app|\/admin/);
}

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  const watch = (p) => { p.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); }); p.on("pageerror", (e) => errors.push(e.message)); };
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const t = await ctx.newPage(); watch(t);
  await login(t, "demo@example.com", "demo12345");

  // Second room: not the free trial, so it starts locked.
  await t.click("#new-room-toggle");
  await t.fill("#subject_name", "ภาษาไทย");
  await t.fill("#grade_label", "มัธยมศึกษาปีที่ 6/2");
  await t.click("#new-room-form button[type=submit]");
  await t.waitForURL(/\/app\/classrooms\/\d+$/);
  await t.waitForSelector("#locked-alert:not(.hidden)");
  await t.screenshot({ path: path.join(OUT, "b-classroom-locked.png") });

  await t.goto(`${BASE}/app/billing`);
  await t.waitForSelector("#qr:not(.hidden)");
  await t.screenshot({ path: path.join(OUT, "b-billing.png"), fullPage: true });
  await t.setInputFiles("#slip", { name: "slip.png", mimeType: "image/png", buffer: png(300, 500) });
  await t.click("#pay-submit");
  await t.waitForFunction(() => document.querySelector("#terms-body").textContent.includes("รอตรวจสอบ"));
  await t.screenshot({ path: path.join(OUT, "b-billing-sent.png"), fullPage: true });

  const m = await browser.newPage({ ...devices["iPhone 13"] }); watch(m);
  await m.context().addCookies(await ctx.cookies());
  await m.goto(`${BASE}/app/billing`);
  await m.waitForSelector("#terms-body tr");
  await m.screenshot({ path: path.join(OUT, "b-billing-mobile.png"), fullPage: true });

  const actx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const a = await actx.newPage(); watch(a);
  await login(a, "admin@example.com", "admin12345");
  await a.goto(`${BASE}/admin`);
  await a.waitForSelector(".slip-card");
  await a.screenshot({ path: path.join(OUT, "b-admin.png"), fullPage: true });
  await a.click('.slip-card button[data-act="approve"]');
  await a.waitForSelector("#subs-empty:not(.hidden)");

  await t.goto(`${BASE}/app/billing`);
  await t.waitForFunction(() => document.querySelector("#terms-body").textContent.includes("ชำระแล้ว"));
  console.log("billing flow: locked -> pending -> approved");
  await browser.close();
  if (errors.length) { console.error("Console errors:\n" + errors.join("\n")); process.exit(1); }
  console.log("BILLING E2E OK");
})().catch((e) => { console.error(e); process.exit(1); });
