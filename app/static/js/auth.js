// Login and sign-up forms.
(function () {
  const next = new URLSearchParams(location.search).get("next");
  const target = next && next.startsWith("/app") ? next : "/app";

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
        await API.post(url, build(new FormData(form)));
        location.href = target;
      } catch (e) {
        API.showError(err, e.message);
        btn.disabled = false;
      }
    });
  }

  bind("login-form", "/api/auth/login", (f) => ({ email: f.get("email"), password: f.get("password") }));
  bind("register-form", "/api/auth/register", (f) => {
    if (f.get("password") !== f.get("password2")) throw new Error("รหัสผ่านทั้งสองช่องไม่ตรงกัน");
    return {
      email: f.get("email"),
      password: f.get("password"),
      full_name: f.get("full_name"),
      school_name: f.get("school_name"),
      accept_terms: f.get("accept_terms") === "on",
    };
  });
})();
