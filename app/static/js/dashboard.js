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
        <span class="folder-tab">${API.esc(r.grade_label)}</span>

        <h3>${API.esc(r.subject_name)}</h3>
        <div class="muted small">${r.subject_code ? API.esc(r.subject_code) + ", " : ""}ภาคเรียนที่ ${r.semester}/${r.academic_year}</div>
        <div class="stamps">
          ${r.is_trial ? '<span class="badge badge-trial">ทดลองใช้</span>' : ""}
          ${r.is_active ? `<span class="badge ${r.is_open ? "badge-open" : "badge-closed"}">${r.is_open ? "เปิดรับ" : "ปิดรับแล้ว"}</span>` : '<span class="badge badge-danger">รอชำระเงิน</span>'}
        </div>
        <div class="counts">
          <div><b>${r.submitted_count}${r.roster_count ? `<small class="muted"> / ${r.roster_count}</small>` : ""}</b><span>ส่งแบบฟอร์มแล้ว</span></div>
          <div><b>${r.evaluated_count}</b><span>ครูประเมินแล้ว</span></div>
        </div>
        ${r.roster_count ? `<progress class="progress" max="100" value="${pct}" aria-label="ส่งแล้ว ${pct}%"></progress>` : ""}
        <div class="keep-note${r.term_ended ? " soon" : ""}">${r.term_ended ? "จบภาคเรียนแล้ว ข้อมูลจะถูกลบ" : "เก็บข้อมูลถึง"} ${API.thaiDate(r.purge_on)}</div>
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
