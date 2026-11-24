// Record the home-page demo clip: QR -> student fills on a phone -> teacher assesses -> full PDF.
// 1. DATABASE_URL=sqlite:///./demo.db TRIAL_STUDENT_LIMIT=100 python -m e2e.demo_video.seed
// 2. PUBLIC_BASE_URL=https://kruflow-student-analysis.up.railway.app DATABASE_URL=sqlite:///./demo.db TRIAL_STUDENT_LIMIT=100 SECRET_KEY=demo uvicorn app.main:app --port 8079
// 3. BASE_URL=http://localhost:8079 node e2e/demo_video/record.cjs   (then run build.sh)
// Writes raw scene videos and timing to e2e/demo_video/out/.
const { chromium, devices } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE_URL || "http://localhost:8079";
const OUT = path.join(__dirname, "out");
const ROOM = process.env.ROOM_ID || "1";
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Caption bar and a visible pointer, drawn inside the page (videos do not show the real cursor).
const OVERLAY = () => {
  const add = () => {
    if (document.getElementById("__cur")) return;
    const st = document.createElement("style");
    st.textContent = `
      #__cur{position:fixed;z-index:2147483647;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;
        background:rgba(234,88,12,.35);border:2px solid #ea580c;pointer-events:none;transition:transform .12s;left:-50px;top:-50px}
      #__cur.down{transform:scale(1.8);background:rgba(234,88,12,.55)}
      #__cap{position:fixed;z-index:2147483646;left:50%;bottom:22px;transform:translateX(-50%);display:flex;gap:14px;align-items:center;
        background:#15315b;color:#fff;padding:12px 26px 12px 14px;border-radius:999px;font:600 24px/1.3 "IBM Plex Sans Thai Looped",sans-serif;
        box-shadow:0 10px 30px rgba(0,0,0,.25);white-space:nowrap}
      #__cap b{display:inline-grid;place-items:center;width:40px;height:40px;border-radius:50%;background:#f59e0b;color:#15315b;font-size:22px}
      #__cap:empty{display:none}`;
    document.head.appendChild(st);
    const c = document.createElement("div"); c.id = "__cur"; document.body.appendChild(c);
    const cap = document.createElement("div"); cap.id = "__cap"; document.body.appendChild(cap);
    addEventListener("mousemove", (e) => { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; }, true);
    addEventListener("mousedown", () => c.classList.add("down"), true);
    addEventListener("mouseup", () => setTimeout(() => c.classList.remove("down"), 120), true);
    window.__setCap = (n, t) => { cap.innerHTML = n ? `<b>${n}</b><span>${t}</span>` : ""; };
    if (window.__pendingCap) window.__setCap(...window.__pendingCap);
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", add); else add();
};

async function caption(page, n, text) {
  await page.evaluate(([n, t]) => { window.__pendingCap = [n, t]; if (window.__setCap) window.__setCap(n, t); }, [n, text]);
}

async function tap(page, sel, opts = {}) {
  const el = page.locator(sel).first();
  await el.scrollIntoViewIfNeeded();
  const b = await el.boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: opts.steps || 12 });
  await sleep(opts.pause ?? 180);
  await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
}

async function type(page, sel, text, delay = 55) {
  await tap(page, sel, { pause: 80 });
  await page.keyboard.type(text, { delay });
}

const timing = {};
async function scene(browser, name, ctxOpts, fn) {
  const size = ctxOpts.viewport;
  const ctx = await browser.newContext({ ...ctxOpts, bypassCSP: true, recordVideo: { dir: OUT, size } });
  await ctx.addInitScript(OVERLAY);
  const page = await ctx.newPage();
  const t0 = Date.now();
  const mark = { start: 0 };
  await fn(page, () => { mark.start = (Date.now() - t0) / 1000; });
  mark.end = (Date.now() - t0) / 1000;
  await ctx.close();
  fs.renameSync(await page.video().path(), path.join(OUT, `${name}.webm`));
  timing[name] = mark;
}

(async () => {
  const browser = await chromium.launch();
  // Log in once; every recorded scene reuses the cookies.
  const login = await browser.newContext();
  const lp = await login.newPage();
  await lp.goto(`${BASE}/login`);
  await lp.fill("#email", "sample@kruflow.example");
  await lp.fill("#password", "sample-report-1");
  await lp.click("button[type=submit]");
  await lp.waitForURL(`${BASE}/app`);
  const storageState = await login.storageState();
  await login.close();
  const desk = { viewport: { width: 1280, height: 720 }, storageState, deviceScaleFactor: 1 };

  let link;
  await scene(browser, "a", desk, async (p, ready) => {
    await p.goto(`${BASE}/app/classrooms/${ROOM}`);
    await p.waitForFunction(() => document.getElementById("qr-img").naturalWidth > 0);
    link = (await p.inputValue("#room-link")).replace(/^https?:\/\/[^/]+/, BASE);
    await p.locator("#qr-img").evaluate((e) => e.scrollIntoView({ block: "center" }));
    await caption(p, 1, "สร้างห้องรายวิชา ได้ลิงก์และ QR ส่งเข้ากลุ่มไลน์ห้อง");
    await p.mouse.move(640, 600);
    ready();
    const q = await p.locator("#qr-img").boundingBox();
    await p.mouse.move(q.x + q.width / 2, q.y + q.height / 2, { steps: 25 });
    await sleep(4200);
  });

  await scene(browser, "b", { ...devices["iPhone 13"], viewport: { width: 390, height: 700 } }, async (s, ready) => {
    await s.goto(link);
    await s.waitForSelector("#f-no");
    ready();
    await sleep(600);
    await type(s, "#f-no", "12");
    await sleep(300);
    if (!(await s.inputValue("#f-name"))) await type(s, "#f-name", "นางสาวพอใจ ตัวอย่างแก้ว", 25);
    await type(s, "#f-nick", "พอ");
    await sleep(300);
    await tap(s, "#next");
    await sleep(500);
    await type(s, "#f-age", "15");
    await s.selectOption("#f-blood_type", "O");
    await type(s, "#f-father_name", "นายสมชาย ตัวอย่างแก้ว", 25);
    await tap(s, "#next");
    await sleep(400);
    await tap(s, "#next");
    await sleep(400);
    await type(s, "#f-q1", "วาดรูป");
    await type(s, "#f-q2", "คณิตศาสตร์");
    await type(s, "#f-q10", "พยาบาล");
    await tap(s, "#next");
    await sleep(400);
    for (const k of ["experiment", "group", "mindmap"]) { await tap(s, `.method[data-key=${k}]`); await sleep(150); }
    await sleep(300);
    await tap(s, "#next");
    await sleep(400);
    await tap(s, "input[name=consent]");
    await tap(s, "#submit");
    await s.waitForSelector("#done:not(.hidden)");
    await sleep(2200);
  });

  await scene(browser, "c", desk, async (p, ready) => {
    await p.goto(`${BASE}/app/classrooms/${ROOM}`);
    await p.waitForSelector("#eval-start:not(.hidden)");
    await caption(p, 3, "ครูดูคำตอบ แล้วกดประเมิน 16 ข้อ ระบบจัดกลุ่มผู้เรียนให้");
    ready();
    await sleep(900);
    await tap(p, "#eval-start", { steps: 20 });
    await p.waitForSelector('input[name="r-d1_1"]');
    await caption(p, 3, "ครูดูคำตอบ แล้วกดประเมิน 16 ข้อ ระบบจัดกลุ่มผู้เรียนให้");
    await sleep(700);
    await tap(p, 'button[data-fill="good"]', { steps: 20 });
    await sleep(500);
    await tap(p, 'input[name="r-d3_3"][value="fair"] + span', { steps: 20 });
    await sleep(400);
    await tap(p, 'input[name="r-d4_2"][value="fair"] + span', { steps: 15 });
    await sleep(500);
    await tap(p, 'button[data-then="stay"]', { steps: 20 });
    await sleep(1500);
  });

  await scene(browser, "d", { ...desk, acceptDownloads: true }, async (p, ready) => {
    await p.goto(`${BASE}/app/classrooms/${ROOM}/summary`);
    await p.waitForFunction(() => document.querySelector("#st-evaluated").textContent !== "-");
    await caption(p, 4, "ร้อยละและตารางสรุปคิดให้ครบ กดดาวน์โหลดรายงานฉบับเต็ม");
    ready();
    await sleep(1800);
    await type(p, "#doc_no", "๑๒๓/๒๕๖๙", 70);
    await sleep(300);
    await Promise.all([
      p.context().waitForEvent("response", { predicate: (r) => r.url().includes("/pdf/full"), timeout: 60000 }),
      tap(p, "#pdf-full", { steps: 20 }),
    ]);
    await sleep(800);
  });

  await scene(browser, "e", desk, async (p, ready) => {
    const img = (n) => `${BASE}/static/sample/page-${n}.jpg`;
    await p.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>
      @font-face{font-family:Plex;src:url(${BASE}/static/fonts/IBMPlexSansThaiLooped-SemiBold.ttf)}
      body{margin:0;height:720px;background:#f4f1ea;font-family:Plex,sans-serif;overflow:hidden}
      .row{position:absolute;top:70px;left:0;right:0;display:flex;justify-content:center;gap:22px;align-items:flex-start}
      .row img{height:400px;box-shadow:0 12px 30px rgba(21,49,91,.18);border:1px solid #ddd;opacity:0;transform:translateY(30px);transition:all .6s}
      .row img.wide{height:283px;margin-top:58px}
      .row img.on{opacity:1;transform:none}
      h1{position:absolute;left:0;right:0;bottom:56px;text-align:center;color:#15315b;font-size:38px;margin:0;opacity:0;transition:opacity .6s}
      h1.on{opacity:1} h1 small{display:block;font-size:22px;color:#475569;margin-top:6px}
    </style></head><body><div class="row">
      <img src="${img(1)}"><img src="${img(2)}"><img class="wide" src="${img(3)}"><img src="${img(4)}"></div>
      <h1>ได้ PDF ไฟล์เดียวครบชุด พร้อมเซ็นส่งฝ่ายวิชาการ<small>บันทึกข้อความ · แบบสรุปผล · กลุ่มผู้เรียน · แบบบันทึกรายบุคคล</small></h1>
      </body></html>`);
    await p.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth));
    ready();
    const imgs = await p.$$("img");
    for (const i of imgs) { await i.evaluate((e) => e.classList.add("on")); await sleep(350); }
    await p.evaluate(() => document.querySelector("h1").classList.add("on"));
    await sleep(3500);
  });

  await browser.close();
  fs.writeFileSync(path.join(OUT, "timing.json"), JSON.stringify(timing, null, 2));
  console.log(JSON.stringify(timing));
})().catch((e) => { console.error(e); process.exit(1); });
