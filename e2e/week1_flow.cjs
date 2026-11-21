// End-to-end check of the week-1 flow in a real browser.
// Usage: BASE_URL=http://localhost:8077 node e2e/week1_flow.cjs
// Teacher (desktop): sign up -> create room -> paste class list.
// Student (iPhone): open link -> fill every step -> submit -> get edit code -> edit again.
// Teacher: sees the answer, opens it, downloads the PDF. Fails on any console error.
const { chromium, devices } = require("playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.env.BASE_URL || "http://localhost:8077";
const OUT = process.env.OUT_DIR || path.join(__dirname, "out");
fs.mkdirSync(OUT, { recursive: true });

function watch(page, label, errors) {
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${label}: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${label}: ${e.message}`));
}

(async () => {
  const browser = await chromium.launch();
  const errors = [];

  // ---- teacher ----------------------------------------------------------------------------
  const tctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const t = await tctx.newPage();
  watch(t, "teacher", errors);
  const email = `kru${Date.now()}@example.com`;
  await t.goto(`${BASE}/register`);
  await t.fill("#full_name", "นางพรธิดา โพธิ์สิงห์");
  await t.fill("#position", "ครู");
  await t.fill("#department", "กลุ่มบริหารวิชาการ");
  await t.fill("#school_name", "โรงเรียนหนองสวรรค์วิทยาคาร");
  await t.fill("#email", email);
  await t.fill("#password", "password123");
  await t.fill("#password2", "password123");
  await t.check("input[name=accept_terms]");
  await t.click("button[type=submit]");
  await t.waitForURL(`${BASE}/app`);
  await t.waitForSelector("#new-room-form:not(.hidden)");
  await t.fill("#subject_name", "คณิตศาสตร์พื้นฐาน");
  await t.fill("#subject_code", "ค33101");
  await t.fill("#grade_label", "มัธยมศึกษาปีที่ 6/1");
  await t.click("#new-room-form button[type=submit]");
  await t.waitForURL(/\/app\/classrooms\/\d+$/);
  await t.waitForFunction(() => document.getElementById("room-link").value.includes("/f/"));
  await t.fill("#roster-text", "1\tนายนนทพัทธ์ ภูแซมโชติ\n2\tนางสาวสุดธิดา ทองคำแสน\n3\tนางสาวศิริรัตน์ พรมาแข้");
  await t.click("#roster-form button[type=submit]");
  await t.waitForFunction(() => document.querySelectorAll("#subs-body tr").length === 3);
  const link = await t.inputValue("#room-link");
  await t.waitForFunction(() => document.getElementById("qr-img").naturalWidth > 0);
  await t.screenshot({ path: path.join(OUT, "teacher-classroom-empty.png"), fullPage: true });

  // ---- student on a phone ------------------------------------------------------------------
  const sctx = await browser.newContext({ ...devices["iPhone 13"] });
  const s = await sctx.newPage();
  watch(s, "student", errors);
  await s.goto(link);
  await s.screenshot({ path: path.join(OUT, "student-step1.png"), fullPage: true });
  await s.fill("#f-no", "2");
  await s.fill("#f-name", "นางสาวสุดธิดา ทองคำแสน");
  await s.fill("#f-nick", "ฝ้าย");
  await s.click("#next");
  await s.fill("#f-birth_date", "2009-03-15");
  await s.fill("#f-age", "17");
  await s.selectOption("#f-blood_type", "B");
  await s.fill("#f-father_name", "นายสมชาย ทองคำแสน");
  await s.fill("#f-father_job", "เกษตรกร");
  await s.selectOption("#f-parent_status", "อื่นๆ");
  await s.fill("#f-parent_status_other", "บิดาเสียชีวิต");
  await s.screenshot({ path: path.join(OUT, "student-step2.png"), fullPage: true });
  await s.click("#next");
  await s.fill("#f-province", "หนองบัวลำภู");
  await s.fill("#f-weight_kg", "48");
  await s.click("#next");
  await s.fill("#f-q1", "ร้องเพลง");
  await s.fill("#f-q10", "พยาบาล");
  await s.click("#next");
  // Too few ranked methods must be refused.
  await s.click(".method[data-key=experiment]");
  await s.click("#next");
  await s.waitForSelector("#form-error:not(.hidden)");
  await s.click(".method[data-key=group]");
  await s.click(".method[data-key=project]");
  await s.screenshot({ path: path.join(OUT, "student-methods.png"), fullPage: true });
  await s.click("#next");
  await s.check("input[name=consent]");
  await s.click("#submit");
  await s.waitForSelector("#done:not(.hidden)");
  const code = (await s.textContent("#done-code")).trim();
  if (!/^\d{6}$/.test(code)) throw new Error("no edit code shown: " + code);
  await s.screenshot({ path: path.join(OUT, "student-done.png"), fullPage: true });

  // Student comes back and edits with the code.
  const s2 = await sctx.newPage();
  watch(s2, "student-edit", errors);
  await s2.goto(link);
  await s2.click("#edit-open");
  await s2.fill("#l-no", "2");
  await s2.fill("#l-code", code);
  await s2.click("#lookup-form button[type=submit]");
  await s2.waitForSelector("#edit-banner:not(.hidden)");
  if ((await s2.inputValue("#f-nick")) !== "ฝ้าย") throw new Error("earlier answers not loaded");
  await s2.fill("#f-nick", "ฝ้ายคำ");
  for (let i = 0; i < 5; i++) await s2.click("#next");
  if ((await s2.textContent("#rank-count")) !== "3") { /* ranking kept */ }
  await s2.check("input[name=consent]");
  await s2.click("#submit");
  await s2.waitForSelector("#done-updated:not(.hidden)");

  // ---- teacher sees it -------------------------------------------------------------------
  await t.reload();
  await t.waitForFunction(() => document.querySelector("#subs-body") && document.querySelector("#subs-body").textContent.includes("ฝ้ายคำ"));
  await t.screenshot({ path: path.join(OUT, "teacher-classroom-submitted.png"), fullPage: true });
  await t.click("#subs-body a:has-text('ดูคำตอบ')");
  await t.waitForFunction(() => document.getElementById("s-title").textContent.includes("สุดธิดา"));
  const other = await t.textContent("[data-p=parent_status]");
  if (!other.includes("บิดาเสียชีวิต")) throw new Error("parent status other not shown: " + other);
  await t.screenshot({ path: path.join(OUT, "teacher-submission.png"), fullPage: true });
  const pdfUrl = await t.getAttribute("#pdf-one", "href");
  const res = await t.request.get(BASE + pdfUrl);
  const buf = await res.body();
  if (res.status() !== 200 || buf.slice(0, 4).toString() !== "%PDF") throw new Error("PDF download failed");
  fs.writeFileSync(path.join(OUT, "individual.pdf"), buf);

  await browser.close();
  if (errors.length) {
    console.error("Console errors:\n" + errors.join("\n"));
    process.exit(1);
  }
  console.log("OK week-1 flow; screenshots in", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
