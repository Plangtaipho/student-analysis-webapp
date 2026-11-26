// Teacher profile (printed on reports) and password change.
(async function () {
  const pf = document.getElementById("profile-form");
  const pw = document.getElementById("password-form");
  const me = (await API.loadMe()).user;
  for (const k of ["position", "department", "learning_area", "school_name", "school_location", "area_office"]) pf[k].value = me[k] || "";
  NamePrefix.set("full_name", me.full_name);
  pf.area_office.dispatchEvent(new Event("change"));
  document.getElementById("email").textContent = me.email;
  if (!me.has_password) {
    // Google-only account: setting a first password needs no current one.
    const cur = document.getElementById("current-password-field");
    cur.classList.add("hidden");
    cur.querySelector("input").required = false;
    document.getElementById("password-title").textContent = "ตั้งรหัสผ่าน";
    document.getElementById("google-only-note").classList.remove("hidden");
  }

  pf.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = document.getElementById("profile-error");
    API.hide(err);
    const f = new FormData(pf);
    try {
      await API.put("/api/auth/profile", Object.fromEntries(f.entries()));
      API.toast("บันทึกข้อมูลแล้ว");
    } catch (e) { API.showError(err, e.message); }
  });

  // Signature printed on the reports.
  const sigImg = document.getElementById("sig-img");
  const sigErr = document.getElementById("sig-error");
  const sigFile = document.getElementById("sig-file");
  const sigUpload = document.getElementById("sig-upload");
  const showSig = (on) => {
    sigImg.classList.toggle("hidden", !on);
    document.getElementById("sig-empty").classList.toggle("hidden", on);
    document.getElementById("sig-delete").classList.toggle("hidden", !on);
    sigUpload.textContent = on ? "เปลี่ยนลายเซ็น" : "อัปโหลดลายเซ็น";
  };
  const loadSig = () => { sigImg.src = `/api/auth/signature?t=${Date.now()}`; };
  sigImg.addEventListener("load", () => showSig(true));
  sigImg.addEventListener("error", () => showSig(false));
  loadSig();
  sigUpload.addEventListener("click", async () => {
    API.hide(sigErr);
    const file = sigFile.files[0];
    if (!file) { sigFile.click(); return; }
    if (file.size > 8 * 1024 * 1024) return API.showError(sigErr, "ไฟล์ใหญ่เกิน 8 MB");
    const fd = new FormData();
    fd.append("file", file);
    sigUpload.disabled = true;
    try {
      await API.put("/api/auth/signature", fd);
      sigFile.value = "";
      loadSig();
      API.toast("บันทึกลายเซ็นแล้ว ตรวจดูภาพตัวอย่างด้านบน");
    } catch (e) { API.showError(sigErr, e.message); }
    finally { sigUpload.disabled = false; }
  });
  sigFile.addEventListener("change", () => { if (sigFile.files[0]) sigUpload.click(); });
  document.getElementById("sig-delete").addEventListener("click", async () => {
    API.hide(sigErr);
    try {
      await API.del("/api/auth/signature");
      showSig(false);
      API.toast("ลบลายเซ็นแล้ว");
    } catch (e) { API.showError(sigErr, e.message); }
  });

  pw.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = document.getElementById("password-error");
    API.hide(err);
    const f = new FormData(pw);
    if (f.get("password") !== f.get("password2")) return API.showError(err, "รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน");
    try {
      await API.put("/api/auth/password", { current_password: f.get("current_password"), password: f.get("password") });
      pw.reset();
      API.toast("บันทึกรหัสผ่านแล้ว");
      if (!me.has_password) location.reload();
    } catch (e) { API.showError(err, e.message); }
  });
})();
