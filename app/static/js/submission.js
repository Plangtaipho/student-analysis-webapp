// One student's answers. The teacher can correct them (wrong number, a classmate's name, wrong answers) or delete them.
(async function () {
  const { classroomId, submissionId } = document.body.dataset;
  const url = `/api/classrooms/${classroomId}/submissions/${submissionId}`;
  const $ = (id) => document.getElementById(id);
  const form = $("edit-form");
  let s = null;
  const who = (hc, no) => (hc ? `${hc} เลขที่ ${no}` : `เลขที่ ${no}`);

  function render() {
    $("s-title").textContent = `${who(s.home_class, s.student_no)} ${s.full_name}${s.nickname ? " (" + s.nickname + ")" : ""}`;
    $("s-time").textContent = (s.by_teacher ? "ครูเพิ่มเอง " : "ส่งเมื่อ ") + API.thaiDateTime(s.submitted_at);
    document.querySelectorAll("[data-p]").forEach((el) => {
      let v = s.personal_info[el.dataset.p];
      if (el.dataset.p === "parent_status" && s.personal_info.parent_status_other) v += ` (${s.personal_info.parent_status_other})`;
      el.textContent = v === undefined || v === "" ? "-" : v;
    });
    document.querySelectorAll("[data-q]").forEach((el) => {
      el.textContent = s.open_answers[el.dataset.q] || "-";
    });
    $("prefs").innerHTML = s.learning_prefs.map((p) => `<li>${API.esc(p.label)}</li>`).join("");
  }

  function fillForm() {
    $("e-hc-field").classList.toggle("hidden", !s.mixed_classes);
    $("e-hc").value = s.home_class || "";
    $("e-no").value = s.student_no;
    $("e-name").value = s.full_name;
    $("e-nick").value = s.nickname || "";
    form.querySelectorAll("[data-personal]").forEach((el) => { el.value = s.personal_info[el.name] ?? ""; });
    form.querySelectorAll("[data-q-in]").forEach((el) => { el.value = s.open_answers[el.dataset.qIn] || ""; });
    // A record the teacher added has no student answers to correct.
    $("edit-answers").classList.toggle("hidden", s.by_teacher);
  }

  function editing(on) {
    form.classList.toggle("hidden", !on);
    $("view").classList.toggle("hidden", on || s.by_teacher);
    $("edit-btn").classList.toggle("hidden", on);
    API.hide($("edit-error"));
    if (on) { fillForm(); $("e-no").focus(); }
  }

  // With a class list, the number decides the name (same rule as the student form).
  function fillRosterName() {
    const hc = s.mixed_classes ? $("e-hc").value.trim() : "";
    const name = s.roster[hc ? `${hc}|${$("e-no").value}` : $("e-no").value];
    if (name) $("e-name").value = name;
  }
  $("e-no").addEventListener("input", fillRosterName);
  $("e-hc").addEventListener("input", fillRosterName);

  $("edit-btn").addEventListener("click", () => editing(true));
  $("edit-cancel").addEventListener("click", () => editing(false));

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = $("edit-error");
    API.hide(err);
    const body = { home_class: $("e-hc").value, student_no: Number($("e-no").value), full_name: $("e-name").value, nickname: $("e-nick").value };
    if (!body.student_no || body.student_no < 1) { API.showError(err, "กรุณากรอกเลขที่"); return; }
    if (body.full_name.trim().length < 2) { API.showError(err, "กรุณากรอกชื่อ – สกุล"); return; }
    if (!s.by_teacher) {
      body.personal_info = {};
      form.querySelectorAll("[data-personal]").forEach((el) => { if (el.value !== "") body.personal_info[el.name] = el.value; });
      body.open_answers = {};
      form.querySelectorAll("[data-q-in]").forEach((el) => { body.open_answers[el.dataset.qIn] = el.value; });
    }
    try {
      s = await API.put(url, body);
      render();
      editing(false);
      API.toast("บันทึกการแก้ไขแล้ว");
    } catch (e) { API.showError(err, e.message); }
  });

  $("delete-btn").addEventListener("click", async () => {
    if (!confirm(`ลบคำตอบของเลขที่ ${s.student_no} ${s.full_name} รวมถึงผลประเมิน?\nลบแล้วกู้คืนไม่ได้ นักเรียนส่งใหม่ได้`)) return;
    try {
      await API.del(url);
      location.href = `/app/classrooms/${classroomId}`;
    } catch (e) { API.toast(e.message); }
  });

  try {
    await API.loadMe();
    s = await API.get(url);
    render();
    $("pdf-one").href = `${url}/pdf`;
    $("eval-link").href = `/app/classrooms/${classroomId}/submissions/${submissionId}/evaluate`;
    if (s.by_teacher) $("view").classList.add("hidden");
    if (new URLSearchParams(location.search).has("edit")) editing(true);
  } catch (e) {
    API.toast(e.message);
  }
})();
