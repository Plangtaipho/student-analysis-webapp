// Login and sign-up forms (email + password, or finishing a Google sign-up).
(function () {
  const params = new URLSearchParams(location.search);
  const next = params.get("next");
  const target = next && next.startsWith("/app") && !next.startsWith("//") ? next : "/app";
  const GOOGLE_ERRORS = {
    failed: "เข้าสู่ระบบด้วย Google ไม่สำเร็จ กรุณาลองใหม่",
    inactive: "บัญชีนี้ถูกปิดการใช้งาน กรุณาติดต่อผู้ดูแลระบบ",
  };
  const gErr = document.getElementById("google-error");
  if (gErr && GOOGLE_ERRORS[params.get("google")]) API.showError(gErr, GOOGLE_ERRORS[params.get("google")]);

  // Google sign-up: email comes from Google, so hide the email/password fields.
  let googleMode = false;
  const regForm = document.getElementById("register-form");
  if (regForm && params.get("google") === "1") {
    googleMode = true;
    regForm.querySelectorAll(".pw-only").forEach((el) => {
      el.classList.add("hidden");
      el.querySelectorAll("input").forEach((i) => { i.required = false; i.disabled = true; });
    });
    const start = document.getElementById("google-start");
    if (start) start.classList.add("hidden");
    API.get("/api/auth/google/pending")
      .then((p) => {
        document.getElementById("google-email").textContent = p.email;
        document.getElementById("google-note").classList.remove("hidden");
      })
      .catch((e) => { location.href = "/register"; });
  }

  function bind(formId, url, build) {
    const form = document.getElementById(formId);
    if (!form) return;
    const err = document.getElementById("form-error");
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      API.hide(err);
      const btn = form.querySelector("button[type=submit]");
      btn.disabled = true;
      try {
        await API.post(url(), build(new FormData(form)));
        location.href = target;
      } catch (e) {
        API.showError(err, e.message);
        btn.disabled = false;
      }
    });
  }

  bind("login-form", () => "/api/auth/login", (f) => ({ email: f.get("email"), password: f.get("password") }));
  bind("register-form", () => (googleMode ? "/api/auth/google/register" : "/api/auth/register"), (f) => {
    const body = {
      full_name: f.get("full_name"),
      position: f.get("position"),
      department: f.get("department"),
      learning_area: f.get("learning_area"),
      school_name: f.get("school_name"),
      accept_terms: f.get("accept_terms") === "on",
    };
    if (googleMode) return body;
    if (f.get("password") !== f.get("password2")) throw new Error("รหัสผ่านทั้งสองช่องไม่ตรงกัน");
    return { ...body, email: f.get("email"), password: f.get("password") };
  });
})();
