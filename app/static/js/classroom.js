// One classroom: student link + QR, open/close, class list, and who has sent the form.
(async function () {
  const id = document.body.dataset.classroomId;
  const base = `/api/classrooms/${id}`;
  const $ = (s) => document.getElementById(s);
  let room = null;

  function renderRoom() {
    $("room-title").textContent = room.subject_name;
    $("room-sub").textContent = `${room.grade_label} · ภาคเรียนที่ ${room.semester}/${room.academic_year}${room.subject_code ? " · " + room.subject_code : ""}`;
    $("room-link").value = room.student_link;
    $("room-open-link").href = room.student_link;
    const st = $("room-status");
    st.textContent = room.is_open ? "เปิดรับคำตอบ" : "ปิดรับแล้ว";
    st.className = "badge " + (room.is_open ? "badge-open" : "badge-closed");
    $("toggle-open").textContent = room.is_open ? "ปิดรับคำตอบ" : "เปิดรับคำตอบอีกครั้ง";
    $("trial-badge").classList.toggle("hidden", !room.is_trial);
    $("stat-submitted").textContent = room.submitted_count;
    $("stat-roster").textContent = room.roster_count || "-";
    $("stat-evaluated").textContent = room.evaluated_count;
    $("pdf-all").classList.toggle("hidden", room.submitted_count === 0);
  }

  const STATUS = {
    missing: ['badge-missing', "ยังไม่ส่ง"],
    submitted: ['badge-submitted', "รอประเมิน"],
    evaluated: ['badge-evaluated', "ประเมินแล้ว"],
  };

  async function loadSubmissions() {
    const rows = await API.get(`${base}/submissions`);
    const body = $("subs-body");
    $("subs-empty").classList.toggle("hidden", rows.length > 0);
    body.innerHTML = rows.map((r) => {
      const [cls, label] = STATUS[r.status];
      const name = API.esc(r.full_name) + (r.nickname ? ` <span class="muted">(${API.esc(r.nickname)})</span>` : "");
      const warn = r.in_roster === false ? ' <span class="badge badge-trial" title="เลขที่นี้ไม่อยู่ในรายชื่อที่ใส่ไว้">ไม่อยู่ในรายชื่อ</span>' : "";
      const actions = r.id
        ? `<a class="btn btn-sm" href="/app/classrooms/${id}/submissions/${r.id}">ดูคำตอบ</a>
           <button class="btn btn-sm" data-code="${r.id}" data-no="${r.student_no}">รหัสแก้ไขใหม่</button>
           <button class="btn btn-sm btn-danger" data-del="${r.id}" data-no="${r.student_no}">ลบ</button>`
        : "";
      return `<tr>
        <td class="num">${r.student_no}</td>
        <td>${name}${warn}</td>
        <td><span class="badge ${cls}">${label}</span></td>
        <td class="small muted">${r.submitted_at ? API.thaiDateTime(r.submitted_at) : ""}</td>
        <td><div class="row">${actions}</div></td>
      </tr>`;
    }).join("");
  }

  async function loadRoom() {
    room = await API.get(base);
    renderRoom();
  }

  async function loadRoster() {
    const rows = await API.get(`${base}/roster`);
    $("roster-text").value = rows.map((r) => `${r.student_no}\t${r.full_name}`).join("\n");
  }

  $("copy-link").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(room.student_link); API.toast("คัดลอกลิงก์แล้ว"); }
    catch (e) { $("room-link").select(); API.toast("กด Ctrl+C เพื่อคัดลอก"); }
  });

  $("toggle-open").addEventListener("click", async () => {
    room = await API.patch(base, { is_open: !room.is_open });
    renderRoom();
    API.toast(room.is_open ? "เปิดรับคำตอบแล้ว" : "ปิดรับคำตอบแล้ว");
  });

  $("delete-room").addEventListener("click", async () => {
    const ok = confirm(`ลบห้อง "${room.subject_name} ${room.grade_label}" และคำตอบของนักเรียนทั้งหมด?\nลบแล้วกู้คืนไม่ได้`);
    if (!ok) return;
    await API.del(base);
    location.href = "/app";
  });

  $("roster-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = $("roster-error");
    API.hide(err);
    try {
      const rows = await API.put(`${base}/roster`, { text: $("roster-text").value });
      $("roster-text").value = rows.map((r) => `${r.student_no}\t${r.full_name}`).join("\n");
      API.toast(rows.length ? `บันทึกรายชื่อ ${rows.length} คนแล้ว` : "ลบรายชื่อแล้ว");
      await Promise.all([loadRoom(), loadSubmissions()]);
    } catch (e) { API.showError(err, e.message); }
  });

  $("subs-body").addEventListener("click", async (ev) => {
    const del = ev.target.closest("[data-del]");
    const code = ev.target.closest("[data-code]");
    try {
      if (del) {
        if (!confirm(`ลบคำตอบของเลขที่ ${del.dataset.no}? นักเรียนจะต้องส่งใหม่`)) return;
        await API.del(`${base}/submissions/${del.dataset.del}`);
        API.toast("ลบคำตอบแล้ว");
        await Promise.all([loadRoom(), loadSubmissions()]);
      } else if (code) {
        if (!confirm(`ออกรหัสแก้ไขใหม่ให้เลขที่ ${code.dataset.no}? รหัสเดิมจะใช้ไม่ได้`)) return;
        const r = await API.post(`${base}/submissions/${code.dataset.code}/edit-code`);
        alert(`รหัสแก้ไขใหม่ของเลขที่ ${code.dataset.no}: ${r.edit_code}\nแจ้งนักเรียนให้ใช้รหัสนี้ที่ปุ่ม "แก้ไขคำตอบเดิม"`);
      }
    } catch (e) { API.toast(e.message); }
  });

  try {
    await API.loadMe();
    $("qr-img").src = `${base}/qr.svg`;
    $("pdf-all").href = `${base}/pdf/individual`;
    await Promise.all([loadRoom(), loadSubmissions(), loadRoster()]);
  } catch (e) {
    API.toast(e.message);
    if (e.status === 404) setTimeout(() => (location.href = "/app"), 1500);
  }
})();
