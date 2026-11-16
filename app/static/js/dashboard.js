// Teacher home: list of classrooms + "new classroom" form.
(async function () {
  const list = document.getElementById("rooms");
  const empty = document.getElementById("rooms-empty");
  const form = document.getElementById("new-room-form");
  const err = document.getElementById("new-room-error");
  const toggle = document.getElementById("new-room-toggle");

  function card(r) {
    const pct = r.submitted_count && r.roster_count ? Math.min(100, Math.round((r.submitted_count / r.roster_count) * 100)) : 0;
    return `
      <a class="card room-card" href="/app/classrooms/${r.id}">
        <div class="row">
          <h3>${API.esc(r.subject_name)}</h3>
          <span class="spacer"></span>
          ${r.is_trial ? '<span class="badge badge-trial">ห้องทดลองใช้</span>' : ""}
          <span class="badge ${r.is_open ? "badge-open" : "badge-closed"}">${r.is_open ? "เปิดรับคำตอบ" : "ปิดรับแล้ว"}</span>
        </div>
        <div class="muted">${API.esc(r.grade_label)} · ภาคเรียนที่ ${r.semester}/${r.academic_year}</div>
        <div class="stat mt-2">
          <div><b>${r.submitted_count}${r.roster_count ? `<span class="muted small"> / ${r.roster_count}</span>` : ""}</b><span class="muted small">ส่งแล้ว</span></div>
          <div><b>${r.evaluated_count}</b><span class="muted small">ประเมินแล้ว</span></div>
        </div>
        ${r.roster_count ? `<progress class="progress mt-2" max="100" value="${pct}" aria-label="ส่งแล้ว ${pct}%"></progress>` : ""}
      </a>`;
  }

  async function load() {
    const rooms = await API.get("/api/classrooms");
    list.innerHTML = rooms.map(card).join("");
    empty.classList.toggle("hidden", rooms.length > 0);
    if (!rooms.length) form.classList.remove("hidden");
  }

  toggle.addEventListener("click", () => form.classList.toggle("hidden"));

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    API.hide(err);
    const f = new FormData(form);
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      const room = await API.post("/api/classrooms", {
        subject_name: f.get("subject_name"),
        subject_code: f.get("subject_code"),
        grade_label: f.get("grade_label"),
        academic_year: Number(f.get("academic_year")),
        semester: Number(f.get("semester")),
      });
      location.href = `/app/classrooms/${room.id}`;
    } catch (e) {
      API.showError(err, e.message);
      btn.disabled = false;
    }
  });

  try {
    await API.loadMe();
    const term = await API.get("/api/classrooms/term-default");
    form.academic_year.value = term.academic_year;
    form.semester.value = String(term.semester);
    await load();
  } catch (e) {
    API.toast(e.message);
  }
})();
