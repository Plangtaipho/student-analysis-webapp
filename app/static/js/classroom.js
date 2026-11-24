// One classroom: student link + QR, open/close, class list, and who has sent the form.
(async function () {
  const id = document.body.dataset.classroomId;
  const base = `/api/classrooms/${id}`;
  const $ = (s) => document.getElementById(s);
  let room = null;

  function renderRoom() {
    $("room-title").textContent = room.subject_name;
    $("room-sub").textContent = `${room.grade_label}  ภาคเรียนที่ ${room.semester}/${room.academic_year}${room.subject_code ? "  รหัสวิชา " + room.subject_code : ""}`;
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
    const base = room.roster_count || room.submitted_count;
    $("eval-progress").value = base ? Math.round((room.evaluated_count / base) * 100) : 0;
    $("pdf-all").classList.toggle("hidden", room.submitted_count === 0);
    $("locked-alert").classList.toggle("hidden", room.is_active);
    const trial = $("trial-alert");
    if (room.student_limit) {
      const full = room.submitted_count >= room.student_limit;
      trial.className = "alert " + (full ? "alert-warn" : "alert-info");
      trial.innerHTML = `ห้องทดลองใช้ฟรี รับนักเรียนได้ ${room.student_limit} คน (ส่งแล้ว ${room.submitted_count}/${room.student_limit} คน)` +
        `${full ? " ครบแล้ว" : ""} <a href="/app/billing">ชำระค่าบริการภาคเรียนนี้</a> เพื่อรับนักเรียนได้ไม่จำกัด`;
    } else {
      trial.classList.add("hidden");
    }
    const pa = $("purge-alert");
    pa.textContent = `ภาคเรียนนี้จบแล้ว ระบบจะลบห้องนี้และคำตอบของนักเรียนทั้งหมดในวันที่ ${API.thaiDate(room.purge_on)} กรุณาดาวน์โหลดรายงาน PDF เก็บไว้ก่อน`;
    pa.classList.toggle("hidden", !room.term_ended);
    $("summary-link").href = `/app/classrooms/${id}/summary`;
  }

  const STATUS = {
    missing: ['badge-missing', "ยังไม่ส่ง"],
    submitted: ['badge-submitted', "รอประเมิน"],
    evaluated: ['badge-evaluated', "ประเมินแล้ว"],
  };

  async function loadSubmissions() {
    const rows = await API.get(`${base}/submissions`);
    const firstPending = rows.find((r) => r.id && r.status === "submitted");
    $("eval-start").classList.toggle("hidden", !firstPending);
    if (firstPending) $("eval-start").href = `/app/classrooms/${id}/submissions/${firstPending.id}/evaluate`;
    const body = $("subs-body");
    $("subs-empty").classList.toggle("hidden", rows.length > 0);
    body.innerHTML = rows.map((r) => {
      const [cls, label] = STATUS[r.status];
      const name = API.esc(r.full_name) + (r.nickname ? ` <span class="muted">(${API.esc(r.nickname)})</span>` : "");
      const warn = r.in_roster === false ? ' <span class="badge badge-trial" title="เลขที่นี้ไม่อยู่ในรายชื่อที่ใส่ไว้">ไม่อยู่ในรายชื่อ</span>' : "";
      const evalBtn = r.id
        ? `<a class="btn btn-sm ${r.status === "evaluated" ? "" : "btn-primary"}" href="/app/classrooms/${id}/submissions/${r.id}/evaluate">${r.status === "evaluated" ? "แก้ผลประเมิน" : "ประเมิน"}</a>`
        : "";
      const actions = r.id
        ? `${evalBtn}
           ${r.by_teacher ? "" : `<a class="btn btn-sm" href="/app/classrooms/${id}/submissions/${r.id}">ดูคำตอบ</a>`}
           <details class="row-menu"><summary class="btn btn-sm" aria-label="ตัวเลือกเพิ่มเติมของเลขที่ ${r.student_no}">อื่นๆ</summary><div class="menu-pop">
             <a class="btn btn-sm" href="/app/classrooms/${id}/submissions/${r.id}?edit=1">แก้ไขเลขที่ ชื่อ หรือคำตอบ</a>
             ${r.by_teacher ? "" : `<button class="btn btn-sm" data-code="${r.id}" data-no="${r.student_no}">ออกรหัสแก้ไขใหม่</button>`}
             <button class="btn btn-sm btn-danger" data-del="${r.id}" data-no="${r.student_no}">ลบคำตอบนี้</button>
           </div></details>`
        : `<button class="btn btn-sm" data-manual="${r.student_no}" data-name="${API.esc(r.full_name)}">ครูประเมินเอง</button>
           <button class="btn btn-sm" data-unlist="${r.student_no}" data-name="${API.esc(r.full_name)}" title="นักเรียนย้ายออก หรือไม่มีตัวตนในห้องนี้">ย้ายออก/ไม่มีตัวตน</button>`;
      const byTeacher = r.by_teacher ? ' <span class="badge badge-missing">ครูเพิ่มเอง</span>' : "";
      return `<tr>
        <td class="num">${r.student_no}</td>
        <td class="who">${name}${warn}${byTeacher}${r.submitted_at ? `<span class="when">ส่งเมื่อ ${API.thaiDateTime(r.submitted_at)}</span>` : ""}</td>
        <td><span class="badge ${cls}">${label}</span></td>
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
    const manual = ev.target.closest("[data-manual]");
    if (manual) {
      try {
        const r = await API.post(`${base}/submissions/manual`, { student_no: Number(manual.dataset.manual), full_name: manual.dataset.name });
        location.href = `/app/classrooms/${id}/submissions/${r.id}/evaluate`;
      } catch (e) { API.toast(e.message); }
      return;
    }
    const unlist = ev.target.closest("[data-unlist]");
    if (unlist) {
      const no = unlist.dataset.unlist;
      if (!confirm(`เอาเลขที่ ${no} ${unlist.dataset.name} ออกจากรายชื่อห้อง?\nใช้กับนักเรียนที่ย้ายออกหรือไม่มีตัวตน ห้องจะนับว่าส่งครบโดยไม่รวมคนนี้ และจะไม่อยู่ในรายงาน`)) return;
      try {
        await API.del(`${base}/roster/${no}`);
        API.toast(`เอาเลขที่ ${no} ออกจากรายชื่อแล้ว`);
        await Promise.all([loadRoom(), loadSubmissions(), loadRoster()]);
      } catch (e) { API.toast(e.message); }
      return;
    }
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

  $("manual-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = $("manual-error");
    API.hide(err);
    const f = new FormData(ev.target);
    try {
      const r = await API.post(`${base}/submissions/manual`, { student_no: Number(f.get("student_no")), full_name: f.get("full_name") });
      location.href = `/app/classrooms/${id}/submissions/${r.id}/evaluate`;
    } catch (e) { API.showError(err, e.message); }
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
