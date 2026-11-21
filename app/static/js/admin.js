// Admin: review payment slips, list teachers.
(async function () {
  const $ = (s) => document.getElementById(s);
  const BADGE = { pending: "badge-trial", approved: "badge-open", rejected: "badge-danger" };

  function slipCard(s) {
    return `
      <article class="slip-card" data-id="${s.id}">
        <a href="/api/admin/subscriptions/${s.id}/slip" target="_blank" rel="noopener" class="slip-thumb">
          <img src="/api/admin/subscriptions/${s.id}/slip" alt="สลิปของ ${API.esc(s.teacher.full_name)}" loading="lazy">
        </a>
        <div class="slip-info">
          <h3>${API.esc(s.teacher.full_name)}</h3>
          <div class="muted small">${API.esc(s.teacher.school_name)}<br>${API.esc(s.teacher.email)}</div>
          <div class="mt-2">ภาคเรียนที่ ${s.semester}/${s.academic_year} · ${s.amount} บาท</div>
          <div class="muted small">${s.submitted_at ? "ส่งเมื่อ " + API.thaiDateTime(s.submitted_at) : ""}</div>
          <span class="badge ${BADGE[s.status]} mt-2">${API.esc(s.status_text)}</span>
          ${s.reject_reason ? `<div class="small stamp-text">เหตุผล: ${API.esc(s.reject_reason)}</div>` : ""}
          <div class="row mt-3">
            ${s.status !== "approved" ? `<button class="btn btn-primary btn-sm" data-act="approve">อนุมัติ</button>` : ""}
            ${s.status !== "rejected" ? `<button class="btn btn-sm" data-act="reject">ปฏิเสธ</button>` : ""}
          </div>
          <form class="reject-form hidden mt-2">
            <input name="reason" required minlength="2" maxlength="200" placeholder="เหตุผล เช่น ยอดเงินไม่ตรง / สลิปไม่ชัด" aria-label="เหตุผลที่ปฏิเสธ">
            <button class="btn btn-sm btn-danger" type="submit">ยืนยันปฏิเสธ</button>
          </form>
        </div>
      </article>`;
  }

  async function loadSubs() {
    const list = await API.get(`/api/admin/subscriptions?status_filter=${$("sub-filter").value}`);
    $("subs").innerHTML = list.map(slipCard).join("");
    $("subs-empty").classList.toggle("hidden", list.length > 0);
  }

  async function loadTeachers() {
    const list = await API.get("/api/admin/teachers");
    $("teacher-count").textContent = `(${list.length} คน)`;
    $("teachers-body").innerHTML = list.map((t) => `
      <tr><td class="who">${API.esc(t.full_name)}<span class="when">${API.esc(t.email)}</span></td>
      <td>${API.esc(t.school_name)}</td><td>${t.rooms}</td><td>${t.paid_terms}</td>
      <td class="small">${API.thaiDateTime(t.created_at)}</td></tr>`).join("");
  }

  $("sub-filter").addEventListener("change", loadSubs);

  $("subs").addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-act]");
    if (!btn) return;
    const card = btn.closest(".slip-card");
    if (btn.dataset.act === "reject") {
      card.querySelector(".reject-form").classList.toggle("hidden");
      return;
    }
    btn.disabled = true;
    try {
      await API.post(`/api/admin/subscriptions/${card.dataset.id}/approve`);
      API.toast("อนุมัติแล้ว");
      await Promise.all([loadSubs(), loadTeachers()]);
    } catch (e) { API.toast(e.message); btn.disabled = false; }
  });

  $("subs").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const card = ev.target.closest(".slip-card");
    try {
      await API.post(`/api/admin/subscriptions/${card.dataset.id}/reject`, { reason: ev.target.reason.value });
      API.toast("ปฏิเสธแล้ว ครูจะเห็นเหตุผลในหน้าชำระเงิน");
      await loadSubs();
    } catch (e) { API.toast(e.message); }
  });

  try {
    await API.loadMe();
    await Promise.all([loadSubs(), loadTeachers()]);
  } catch (e) { API.toast(e.message); }
})();
