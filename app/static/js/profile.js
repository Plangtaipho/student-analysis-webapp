// Teacher profile (printed on reports) and password change.
(async function () {
  const pf = document.getElementById("profile-form");
  const pw = document.getElementById("password-form");
  const me = (await API.loadMe()).user;
  for (const k of ["full_name", "position", "department", "school_name", "school_location", "area_office"]) pf[k].value = me[k] || "";
  document.getElementById("email").textContent = me.email;

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

  pw.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const err = document.getElementById("password-error");
    API.hide(err);
    const f = new FormData(pw);
    if (f.get("password") !== f.get("password2")) return API.showError(err, "รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน");
    try {
      await API.put("/api/auth/password", { current_password: f.get("current_password"), password: f.get("password") });
      pw.reset();
      API.toast("เปลี่ยนรหัสผ่านแล้ว");
    } catch (e) { API.showError(err, e.message); }
  });
})();
