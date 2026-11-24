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
