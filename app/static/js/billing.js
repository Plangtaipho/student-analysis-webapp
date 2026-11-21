// Teacher payments: status per semester, PromptPay QR, slip upload.
(async function () {
  const $ = (s) => document.getElementById(s);
  const BADGE = { none: "badge-closed", pending: "badge-trial", approved: "badge-open", rejected: "badge-danger" };
  let data = null;

  function render() {
    $("price-inline").textContent = data.price;
    $("price-big").textContent = data.price;
    $("pp-name").textContent = data.promptpay_name ? `ชื่อบัญชี: ${data.promptpay_name}` : "";
    if (data.promptpay_ready) {
      $("qr").src = "/api/billing/qr.svg";
      $("qr").classList.remove("hidden");
    } else {
      $("qr-missing").classList.remove("hidden");
    }
    $("terms-body").innerHTML = data.terms.map((t) => `
      <tr>
        <td>${t.semester}/${t.academic_year}</td>
        <td>${t.rooms ? t.rooms + " ห้อง" : '<span class="muted">-</span>'}</td>
        <td><span class="badge ${BADGE[t.status]}">${API.esc(t.status_text)}</span>
          ${t.reject_reason ? `<div class="small stamp-text">เหตุผล: ${API.esc(t.reject_reason)}</div>` : ""}
          ${t.submitted_at ? `<div class="muted small">ส่งเมื่อ ${API.thaiDateTime(t.submitted_at)}</div>` : ""}</td>
        <td>${t.has_slip ? `<a class="small" href="/api/billing/slips/${t.subscription_id}" target="_blank" rel="noopener">ดูสลิป</a>` : ""}</td>
      </tr>`).join("");
    const payable = data.terms.filter((t) => t.status !== "approved");
    $("term").innerHTML = payable
      .map((t) => `<option value="${t.academic_year}-${t.semester}">ภาคเรียนที่ ${t.semester}/${t.academic_year}${t.rooms ? ` (${t.rooms} ห้อง)` : ""}</option>`)
      .join("");
    $("pay-form").classList.toggle("hidden", payable.length === 0);
  }

  async function load() {
    data = await API.get("/api/billing");
    render();
  }

  $("pay-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    API.hide($("pay-error"));
    const file = $("slip").files[0];
    if (!file) { API.showError($("pay-error"), "กรุณาเลือกรูปสลิป"); return; }
    if (file.size > 8 * 1024 * 1024) { API.showError($("pay-error"), "ไฟล์ใหญ่เกิน 8 MB"); return; }
    const [year, sem] = $("term").value.split("-");
    const fd = new FormData();
    fd.append("academic_year", year);
    fd.append("semester", sem);
    fd.append("file", file);
    const btn = $("pay-submit");
    btn.disabled = true;
    try {
      await API.post("/api/billing/slip", fd);
      API.toast("ส่งสลิปแล้ว ห้องของภาคเรียนนี้ใช้งานได้ทันที");
      $("slip").value = "";
      await load();
    } catch (e) {
      API.showError($("pay-error"), e.message);
    } finally {
      btn.disabled = false;
    }
  });

  try {
    await API.loadMe();
    await load();
  } catch (e) { API.toast(e.message); }
})();
