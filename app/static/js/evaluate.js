// Assess one student on the 16 items, with their answers alongside.
// Student answers: open beside the form on wide screens, folded above it on phones.
{
  const side = document.getElementById("eval-side");
  const wide = window.matchMedia("(min-width: 960px)");
  const sync = () => { if (wide.matches) side.open = true; };
  sync();
  wide.addEventListener("change", sync);
}
(async function () {
  const { classroomId, submissionId } = document.body.dataset;
  const base = `/api/classrooms/${classroomId}/submissions/${submissionId}`;
  const $ = (id) => document.getElementById(id);
  const form = $("eval-form");
  const LABELS = { good: "ดี", fair: "ปานกลาง", improve: "ปรับปรุง" };
  const GROUPS = { high: "มีความพร้อมสูงทุกด้าน", medium: "มีความพร้อมปานกลาง", low: "ไม่มีความพร้อม", disability: "บกพร่องทางการเรียนรู้" };
  let codes = [];
  let dirty = false;

  function renderItems(domains) {
    codes = [];
    $("items").innerHTML = domains.map((d) => `
      <div class="domain-head">${d.domain_no}. ${API.esc(d.domain_name)}</div>
      ${d.items.map((it) => {
        codes.push(it.code);
        return `<div class="item-row" data-code="${it.code}">
          <div id="lbl-${it.code}">${API.esc(it.label)}</div>
          <div class="seg" role="radiogroup" aria-labelledby="lbl-${it.code}">
            ${["good", "fair", "improve"].map((r) => `<label><input type="radio" name="r-${it.code}" value="${r}"><span>${LABELS[r]}</span></label>`).join("")}
          </div>
          <input class="note" name="n-${it.code}" maxlength="200" placeholder="สิ่งที่ควรปรับปรุง / แก้ไข (ไม่บังคับ)" aria-label="สิ่งที่ควรปรับปรุงของ ${API.esc(it.label)}">
        </div>`;
      }).join("")}`).join("");
  }

  function ratings() {
    return codes.map((c) => (form.querySelector(`input[name="r-${c}"]:checked`) || {}).value).filter(Boolean);
  }

  let previewTimer = null;
  function updateProgress() {
    const done = ratings().length;
    $("progress-text").textContent = `ประเมินแล้ว ${done} / ${codes.length} ข้อ`;
    clearTimeout(previewTimer);
    if (done < codes.length) { $("auto-group").textContent = "ประเมินครบทุกข้อแล้วจะแสดง"; return; }
    previewTimer = setTimeout(async () => {
      try {
        const r = await API.get(`/api/classrooms/${classroomId}/auto-group-preview?ratings=${ratings().join(",")}`);
        $("auto-group").textContent = GROUPS[r.group];
      } catch (e) { /* preview only */ }
    }, 150);
  }

  function fillForm(ev) {
    renderItems(ev.domains);
    for (const [code, s] of Object.entries(ev.scores)) {
      const radio = form.querySelector(`input[name="r-${code}"][value="${s.rating}"]`);
      if (radio) radio.checked = true;
      form.querySelector(`input[name="n-${code}"]`).value = s.note || "";
    }
    form.last_grade.value = ev.last_grade || "";
    form.teacher_comment.value = ev.teacher_comment || "";
    form.group_override.value = ev.group_override || "";
    $("e-title").textContent = `${ev.home_class ? ev.home_class + " " : ""}เลขที่ ${ev.student_no} ${ev.full_name}${ev.nickname ? " (" + ev.nickname + ")" : ""}`;
    $("e-status").textContent = ev.evaluated ? "ประเมินแล้ว แก้ไขได้" : "ยังไม่ได้ประเมิน";
    const nav = (el, id) => {
      el.classList.toggle("hidden", !id);
      if (id) el.href = `/app/classrooms/${classroomId}/submissions/${id}/evaluate`;
    };
    nav($("e-prev"), ev.prev_id);
    nav($("e-next"), ev.next_id);
    form.dataset.nextPending = ev.next_pending_id || "";
    dirty = false;
    updateProgress();
  }

  async function loadAnswers() {
    const s = await API.get(base);
    const p = s.personal_info || {};
    const empty = !Object.keys(p).length && !Object.keys(s.open_answers || {}).length && !s.learning_prefs.length;
    $("no-form").classList.toggle("hidden", !empty);
    $("answers").classList.toggle("hidden", empty);
    const join = (...xs) => xs.filter((x) => x !== undefined && x !== "").join(" / ") || "-";
    $("a-basic").textContent = join(p.age !== undefined ? `${p.age} ปี` : "", p.prev_gpa !== undefined ? `GPA ${p.prev_gpa}` : "");
    $("a-family").textContent = join(p.lives_with, p.parent_status === "อื่นๆ" ? p.parent_status_other : p.parent_status);
    $("a-health").textContent = join(p.weight_kg ? `${p.weight_kg} กก.` : "", p.height_cm ? `${p.height_cm} ซม.` : "", p.chronic_disease);
    document.querySelectorAll("[data-q]").forEach((el) => { el.textContent = s.open_answers[el.dataset.q] || "-"; });
    $("a-prefs").textContent = s.learning_prefs.slice(0, 3).map((x, i) => `${i + 1}. ${x.label}`).join("  ") || "-";
    $("a-full").href = `/app/classrooms/${classroomId}/submissions/${submissionId}`;
  }

  form.addEventListener("change", () => { dirty = true; updateProgress(); });
  form.addEventListener("click", (ev) => {
    const btn = ev.target.closest("[data-fill]");
    if (!btn) return;
    codes.forEach((c) => { form.querySelector(`input[name="r-${c}"][value="${btn.dataset.fill}"]`).checked = true; });
    dirty = true;
    updateProgress();
  });
  window.addEventListener("beforeunload", (ev) => { if (dirty) { ev.preventDefault(); ev.returnValue = ""; } });

  let then = "stay";
  form.querySelectorAll("button[type=submit]").forEach((b) => b.addEventListener("click", () => { then = b.dataset.then; }));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = $("eval-error");
    API.hide(err);
    form.querySelectorAll(".item-row").forEach((row) => row.classList.remove("missing"));
    const scores = {};
    const missing = [];
    for (const c of codes) {
      const r = form.querySelector(`input[name="r-${c}"]:checked`);
      if (!r) { missing.push(c); continue; }
      scores[c] = { rating: r.value, note: form.querySelector(`input[name="n-${c}"]`).value };
    }
    if (missing.length) {
      missing.forEach((c) => form.querySelector(`.item-row[data-code="${c}"]`).classList.add("missing"));
      form.querySelector(`.item-row[data-code="${missing[0]}"]`).scrollIntoView({ behavior: "smooth", block: "center" });
      return API.showError(err, `ยังไม่ได้เลือกระดับ ${missing.length} ข้อ (ขอบสีแดง)`);
    }
    try {
      const saved = await API.put(`${base}/evaluation`, {
        scores,
        last_grade: form.last_grade.value,
        teacher_comment: form.teacher_comment.value,
        group_override: form.group_override.value || null,
      });
      dirty = false;
      if (then === "next") {
        if (saved.next_pending_id) {
          location.href = `/app/classrooms/${classroomId}/submissions/${saved.next_pending_id}/evaluate`;
        } else {
          location.href = `/app/classrooms/${classroomId}/summary`;
        }
        return;
      }
      fillForm(saved);
      API.toast("บันทึกแล้ว");
    } catch (e) { API.showError(err, e.message); }
  });

  try {
    await API.loadMe();
    const [ev] = await Promise.all([API.get(`${base}/evaluation`), loadAnswers()]);
    fillForm(ev);
  } catch (e) { API.toast(e.message); }
})();
