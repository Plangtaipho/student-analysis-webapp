// One classroom: student link + QR, open/close, class list, and who has sent the form.
(async function () {
  const id = document.body.dataset.classroomId;
  const base = `/api/classrooms/${id}`;
  const $ = (s) => document.getElementById(s);
  let room = null;
  const who = (hc, no) => (hc ? `${hc} เลขที่ ${no}` : `เลขที่ ${no}`);
  const rosterLine = (r) => (room && room.mixed_classes ? `${r.home_class}\t${r.student_no}\t${r.full_name}` : `${r.student_no}\t${r.full_name}`);

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
    const mixed = room.mixed_classes;
    $("mixed-toggle").checked = mixed;
    $("no-head").textContent = mixed ? "ห้อง / เลขที่" : "เลขที่";
    $("manual-hc").classList.toggle("hidden", !mixed);
    $("manual-hc").required = mixed;
    $("roster-help").textContent = mixed
      ? "ห้องคละ: ใส่บรรทัดละ 1 คน เรียง ห้อง เลขที่ ชื่อ เช่น ม.3/2  5  ด.ช.ก้อง ใจดี คัดลอก 3 คอลัมน์จาก Excel มาวางได้เลย ระบบจะบอกได้ว่าใครยังไม่ส่ง และกันการกรอกห้องหรือเลขที่ผิด"
      : "ใส่รายชื่อแล้วระบบจะบอกได้ว่าใครยังไม่ส่ง และกันการกรอกเลขที่ผิด คัดลอกคอลัมน์เลขที่และชื่อจาก Excel มาวางได้เลย บรรทัดละ 1 คน";
    $("roster-text").placeholder = mixed
      ? "ม.3/1\t1\tนายนนทพัทธ์ ภูแซมโชติ\nม.3/2\t1\tนางสาวสุดธิดา ทองคำแสน"
      : "1\tนายนนทพัทธ์ ภูแซมโชติ\n2\tนางสาวสุดธิดา ทองคำแสน";
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
      const warn = r.in_roster === false ? ' <span class="badge badge-trial" title="${room && room.mixed_classes ? "ห้องและเลขที่นี้" : "เลขที่นี้"}ไม่อยู่ในรายชื่อที่ใส่ไว้">ไม่อยู่ในรายชื่อ</span>' : "";
      const evalBtn = r.id
        ? `<a class="btn btn-sm ${r.status === "evaluated" ? "" : "btn-primary"}" href="/app/classrooms/${id}/submissions/${r.id}/evaluate">${r.status === "evaluated" ? "แก้ผลประเมิน" : "ประเมิน"}</a>`
        : "";
      const actions = r.id
        ? `${evalBtn}
           ${r.by_teacher ? "" : `<a class="btn btn-sm" href="/app/classrooms/${id}/submissions/${r.id}">ดูคำตอบ</a>`}
           <details class="row-menu"><summary class="btn btn-sm" aria-label="ตัวเลือกเพิ่มเติมของ${who(r.home_class, r.student_no)}">อื่นๆ</summary><div class="menu-pop">
             <a class="btn btn-sm" href="/app/classrooms/${id}/submissions/${r.id}?edit=1">แก้ไข${room && room.mixed_classes ? "ห้อง " : ""}เลขที่ ชื่อ หรือคำตอบ</a>
             ${r.by_teacher ? "" : `<button class="btn btn-sm" data-code="${r.id}" data-no="${API.esc(who(r.home_class, r.student_no))}">ออกรหัสแก้ไขใหม่</button>`}
             <button class="btn btn-sm btn-danger" data-del="${r.id}" data-no="${API.esc(who(r.home_class, r.student_no))}">ลบคำตอบนี้</button>
           </div></details>`
        : `<button class="btn btn-sm" data-manual="${r.student_no}" data-hc="${API.esc(r.home_class || "")}" data-name="${API.esc(r.full_name)}">ครูประเมินเอง</button>
           <button class="btn btn-sm" data-unlist="${r.student_no}" data-hc="${API.esc(r.home_class || "")}" data-name="${API.esc(r.full_name)}" title="นักเรียนย้ายออก หรือไม่มีตัวตนในห้องนี้">ย้ายออก/ไม่มีตัวตน</button>`;
      const byTeacher = r.by_teacher ? ' <span class="badge badge-missing">ครูเพิ่มเอง</span>' : "";
      return `<tr>
        <td class="num">${r.home_class ? `<span class="hc">${API.esc(r.home_class)}</span> ` : ""}${r.student_no}</td>
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
    $("roster-text").value = rows.map(rosterLine).join("\n");
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
      $("roster-text").value = rows.map(rosterLine).join("\n");
      API.toast(rows.length ? `บันทึกรายชื่อ ${rows.length} คนแล้ว` : "ลบรายชื่อแล้ว");
      await Promise.all([loadRoom(), loadSubmissions()]);
    } catch (e) { API.showError(err, e.message); }
  });

  $("subs-body").addEventListener("click", async (ev) => {
    const manual = ev.target.closest("[data-manual]");
    if (manual) {
      try {
        const r = await API.post(`${base}/submissions/manual`, {
          home_class: manual.dataset.hc,
          student_no: Number(manual.dataset.manual),
          full_name: manual.dataset.name,
        });
        location.href = `/app/classrooms/${id}/submissions/${r.id}/evaluate`;
      } catch (e) { API.toast(e.message); }
      return;
    }
    const unlist = ev.target.closest("[data-unlist]");
    if (unlist) {
      const no = unlist.dataset.unlist;
      const hc = unlist.dataset.hc;
      if (!confirm(`เอา${who(hc, no)} ${unlist.dataset.name} ออกจากรายชื่อห้อง?\nใช้กับนักเรียนที่ย้ายออกหรือไม่มีตัวตน ห้องจะนับว่าส่งครบโดยไม่รวมคนนี้ และจะไม่อยู่ในรายงาน`)) return;
      try {
        await API.del(`${base}/roster/${no}${hc ? "?home_class=" + encodeURIComponent(hc) : ""}`);
        API.toast(`เอา${who(hc, no)} ออกจากรายชื่อแล้ว`);
        await Promise.all([loadRoom(), loadSubmissions(), loadRoster()]);
      } catch (e) { API.toast(e.message); }
      return;
    }
    const del = ev.target.closest("[data-del]");
    const code = ev.target.closest("[data-code]");
    try {
      if (del) {
        if (!confirm(`ลบคำตอบของ${del.dataset.no}? นักเรียนจะต้องส่งใหม่`)) return;
        await API.del(`${base}/submissions/${del.dataset.del}`);
        API.toast("ลบคำตอบแล้ว");
        await Promise.all([loadRoom(), loadSubmissions()]);
      } else if (code) {
        if (!confirm(`ออกรหัสแก้ไขใหม่ให้${code.dataset.no}? รหัสเดิมจะใช้ไม่ได้`)) return;
        const r = await API.post(`${base}/submissions/${code.dataset.code}/edit-code`);
        alert(`รหัสแก้ไขใหม่ของ${code.dataset.no}: ${r.edit_code}\nแจ้งนักเรียนให้ใช้รหัสนี้ที่ปุ่ม "แก้ไขคำตอบเดิม"`);
      }
    } catch (e) { API.toast(e.message); }
  });

  $("manual-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = $("manual-error");
    API.hide(err);
    const f = new FormData(ev.target);
    try {
      const r = await API.post(`${base}/submissions/manual`, {
        home_class: f.get("home_class") || "",
        student_no: Number(f.get("student_no")),
        full_name: f.get("full_name"),
      });
      location.href = `/app/classrooms/${id}/submissions/${r.id}/evaluate`;
    } catch (e) { API.showError(err, e.message); }
  });

  $("mixed-toggle").addEventListener("change", async (ev) => {
    const on = ev.target.checked;
    if (on && !confirm("เปลี่ยนเป็นห้องคละ? นักเรียนจะต้องกรอกห้องเดิมพร้อมเลขที่ ถ้ามีรายชื่อหรือคำตอบที่ส่งไว้แล้ว ให้ใส่ห้องเดิมเพิ่มทีหลัง")) {
      ev.target.checked = false;
      return;
    }
    try {
      room = await API.patch(base, { mixed_classes: on });
      renderRoom();
      API.toast(on ? "เปลี่ยนเป็นห้องคละแล้ว" : "เปลี่ยนเป็นห้องปกติแล้ว");
      await Promise.all([loadSubmissions(), loadRoster()]);
    } catch (e) {
      ev.target.checked = !on;
      API.toast(e.message);
    }
  });

  try {
    await API.loadMe();
    $("qr-img").src = `${base}/qr.svg`;
    $("pdf-all").href = `${base}/pdf/individual`;
    await loadRoom();
    await Promise.all([loadSubmissions(), loadRoster()]);
  } catch (e) {
    API.toast(e.message);
    if (e.status === 404) setTimeout(() => (location.href = "/app"), 1500);
  }
})();
