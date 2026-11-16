// Student self-analysis form: step by step on a phone, draft kept in this tab only.
(function () {
  const root = document.getElementById("student-app");
  if (!root) return;
  const token = root.dataset.token;
  const minRanked = Number(root.dataset.minRanked);
  const api = `/api/f/${token}`;
  const draftKey = `draft:${token}`;
  const form = document.getElementById("sform");
  const steps = Array.from(form.querySelectorAll(".step"));
  const dots = document.getElementById("steps");
  const err = document.getElementById("form-error");
  let current = 0;
  let ranked = []; // learning-method keys in order
  let editCode = null; // set when editing earlier answers

  // ---- step navigation ---------------------------------------------------------
  dots.innerHTML = steps.map(() => "<span></span>").join("");

  function show(i) {
    current = i;
    steps.forEach((s, n) => s.classList.toggle("hidden", n !== i));
    Array.from(dots.children).forEach((d, n) => d.classList.toggle("on", n <= i));
    document.getElementById("step-count").textContent = `ขั้นตอนที่ ${i + 1} จาก ${steps.length}`;
    document.getElementById("prev").classList.toggle("hidden", i === 0);
    document.getElementById("next").classList.toggle("hidden", i === steps.length - 1);
    document.getElementById("submit").classList.toggle("hidden", i !== steps.length - 1);
    API.hide(err);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function stepValid(i) {
    const step = steps[i];
    for (const el of step.querySelectorAll("input, select, textarea")) {
      if (!el.checkValidity()) {
        el.reportValidity();
        return false;
      }
    }
    if (step.dataset.kind === "methods" && ranked.length < minRanked) {
      API.showError(err, `กรุณาเลือกวิธีการเรียนที่ชอบอย่างน้อย ${minRanked} อันดับ`);
      return false;
    }
    return true;
  }

  document.getElementById("next").addEventListener("click", () => {
    if (stepValid(current)) { saveDraft(); show(current + 1); }
  });
  document.getElementById("prev").addEventListener("click", () => show(current - 1));

  // ---- learning-method ranking: tap in order of preference -------------------------
  const methodButtons = Array.from(form.querySelectorAll(".method"));
  function renderRanks() {
    methodButtons.forEach((b) => {
      const pos = ranked.indexOf(b.dataset.key);
      b.classList.toggle("on", pos >= 0);
      b.setAttribute("aria-pressed", pos >= 0 ? "true" : "false");
      b.querySelector(".rank").textContent = pos >= 0 ? pos + 1 : "";
    });
    document.getElementById("rank-count").textContent = ranked.length;
  }
  methodButtons.forEach((b) =>
    b.addEventListener("click", () => {
      const k = b.dataset.key;
      ranked = ranked.includes(k) ? ranked.filter((x) => x !== k) : [...ranked, k];
      renderRanks();
    })
  );
  document.getElementById("rank-reset").addEventListener("click", () => { ranked = []; renderRanks(); });

  // ---- collect / fill -------------------------------------------------------------------
  function collect() {
    const personal = {};
    form.querySelectorAll("[data-personal]").forEach((el) => { if (el.value !== "") personal[el.name] = el.value; });
    const answers = {};
    form.querySelectorAll("[data-question]").forEach((el) => { if (el.value.trim()) answers[el.name] = el.value; });
    return {
      student_no: Number(form.student_no.value),
      full_name: form.full_name.value,
      nickname: form.nickname.value,
      personal_info: personal,
      open_answers: answers,
      learning_prefs: ranked,
      consent: form.consent.checked,
      edit_code: editCode,
    };
  }

  function fill(d) {
    form.student_no.value = d.student_no ?? "";
    form.full_name.value = d.full_name ?? "";
    form.nickname.value = d.nickname ?? "";
    form.querySelectorAll("[data-personal]").forEach((el) => { el.value = (d.personal_info || {})[el.name] ?? ""; });
    form.querySelectorAll("[data-question]").forEach((el) => { el.value = (d.open_answers || {})[el.name] ?? ""; });
    ranked = (d.learning_prefs || []).filter((k) => methodButtons.some((b) => b.dataset.key === k));
    renderRanks();
    toggleOther();
  }

  function saveDraft() {
    if (editCode) return; // never keep someone's loaded answers around
    try { sessionStorage.setItem(draftKey, JSON.stringify(collect())); } catch (e) { /* storage blocked */ }
  }
  function clearDraft() { try { sessionStorage.removeItem(draftKey); } catch (e) { /* ignore */ } }
  try {
    const d = JSON.parse(sessionStorage.getItem(draftKey) || "null");
    if (d) fill(d);
  } catch (e) { /* ignore */ }
  form.addEventListener("change", saveDraft);

  // "อื่นๆ" for parent status shows the text box.
  function toggleOther() {
    const sel = form.querySelector("[name=parent_status]");
    const other = form.querySelector("[name=parent_status_other]");
    if (!sel || !other) return;
    other.closest(".field").classList.toggle("hidden", sel.value !== "อื่นๆ");
  }
  form.querySelector("[name=parent_status]")?.addEventListener("change", toggleOther);
  toggleOther();

  // ---- submit -------------------------------------------------------------------------------
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!stepValid(current)) return;
    const btn = document.getElementById("submit");
    btn.disabled = true;
    API.hide(err);
    try {
      const res = await API.post(`${api}/submissions`, collect());
      clearDraft();
      form.classList.add("hidden");
      document.getElementById("edit-entry").classList.add("hidden");
      const done = document.getElementById("done");
      done.classList.remove("hidden");
      document.getElementById("done-name").textContent = `เลขที่ ${res.student_no} ${res.full_name}`;
      document.getElementById("done-new").classList.toggle("hidden", !res.edit_code);
      document.getElementById("done-updated").classList.toggle("hidden", !res.updated);
      if (res.edit_code) document.getElementById("done-code").textContent = res.edit_code;
      window.scrollTo({ top: 0 });
    } catch (e) {
      API.showError(err, e.message);
      btn.disabled = false;
    }
  });

  // ---- edit earlier answers ---------------------------------------------------------------
  const lookup = document.getElementById("lookup-form");
  document.getElementById("edit-open").addEventListener("click", () => lookup.classList.toggle("hidden"));
  lookup.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const lerr = document.getElementById("lookup-error");
    API.hide(lerr);
    const code = lookup.edit_code.value.trim();
    try {
      const d = await API.post(`${api}/lookup`, { student_no: Number(lookup.student_no.value), edit_code: code });
      editCode = code;
      clearDraft();
      fill(d);
      form.consent.checked = false;
      lookup.classList.add("hidden");
      document.getElementById("edit-banner").classList.remove("hidden");
      form.student_no.readOnly = true;
      show(0);
    } catch (e) { API.showError(lerr, e.message); }
  });

  renderRanks();
  show(0);
})();
