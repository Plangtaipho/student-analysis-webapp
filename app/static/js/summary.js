// Class summary: counts / percentages per item, learner groups, full-report download.
(async function () {
  const id = document.body.dataset.classroomId;
  const $ = (s) => document.getElementById(s);
  const fmt = (n, p) => (n ? [n, p.toFixed(2)] : ["-", "-"]);

  try {
    await API.loadMe();
    const [room, s] = await Promise.all([API.get(`/api/classrooms/${id}`), API.get(`/api/classrooms/${id}/summary`)]);
    $("sum-sub").textContent = `${room.subject_name} · ${room.grade_label} · ภาคเรียนที่ ${room.semester}/${room.academic_year}`;
    $("st-size").textContent = s.class_size;
    $("st-submitted").textContent = s.submitted;
    $("st-evaluated").textContent = s.evaluated;
    const pending = s.class_size - s.evaluated;
    if (!s.evaluated) {
      $("sum-warn").textContent = "ยังไม่มีนักเรียนที่ประเมินแล้ว ตัวเลขจะขึ้นเมื่อประเมินอย่างน้อย 1 คน";
      $("sum-warn").classList.remove("hidden");
      $("pdf-full").disabled = true;
    } else if (pending > 0) {
      $("sum-warn").textContent = `ยังประเมินไม่ครบ อีก ${pending} คน ตัวเลขด้านล่างนับเฉพาะ ${s.evaluated} คนที่ประเมินแล้ว`;
      $("sum-warn").classList.remove("hidden");
    }
    $("sum-body").innerHTML = s.domains.map((d) => `
      <tr class="domain"><td colspan="7">${d.domain_no}. ${API.esc(d.domain_name)}</td></tr>
      ${d.items.map((it) => {
        const cells = ["good", "fair", "improve"].flatMap((k) => fmt(it[k], it[k + "_pct"]));
        return `<tr><td>${API.esc(it.label)}</td>${cells.map((c) => `<td class="n">${c}</td>`).join("")}</tr>`;
      }).join("")}`).join("");
    $("groups").innerHTML = s.groups.map((g) => `
      <div><h3>${API.esc(g.label)} <span class="badge badge-submitted">${g.students.length}</span></h3>
      ${g.students.length ? `<ol>${g.students.map((st) => `<li>${API.esc(st.full_name)} <span class="muted small">(เลขที่ ${st.student_no})</span></li>`).join("")}</ol>` : '<p class="muted small">-</p>'}
      </div>`).join("");
  } catch (e) { API.toast(e.message); }

  $("memo-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const q = new URLSearchParams();
    for (const [k, v] of new FormData(ev.target).entries()) if (String(v).trim()) q.set(k, String(v).trim());
    window.open(`/api/classrooms/${id}/pdf/full?${q.toString()}`, "_blank", "noopener");
  });
})();
