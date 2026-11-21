// Small fetch wrapper shared by all pages. Teacher calls send the CSRF token.
(function () {
  let csrf = "";

  async function request(method, url, body) {
    const opts = { method, headers: {}, credentials: "same-origin" };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    if (csrf && method !== "GET") opts.headers["X-CSRF-Token"] = csrf;
    let res;
    try {
      res = await fetch(url, opts);
    } catch (e) {
      throw new Error("เชื่อมต่อไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่");
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { /* not JSON */ }
    if (!res.ok) {
      if (res.status === 401 && location.pathname.startsWith("/app")) {
        location.href = "/login?next=" + encodeURIComponent(location.pathname);
      }
      const err = new Error((data && data.detail) || "เกิดข้อผิดพลาด กรุณาลองใหม่");
      err.status = res.status;
      throw err;
    }
    if (data && data.csrf) csrf = data.csrf;
    return data;
  }

  function toast(msg) {
    const el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("role", "status");
    el.textContent = msg;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2600);
  }

  function showError(el, msg) {
    if (!el) return toast(msg);
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function hide(el) { if (el) el.classList.add("hidden"); }

  // Escape text before putting it into HTML.
  function esc(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function thaiDate(isoDay) {
    if (!isoDay) return "";
    const [y, m, d] = isoDay.split("-").map(Number);
    return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("th-TH", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
  }
  function thaiDateTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" });
  }

  async function loadMe() {
    return request("GET", "/api/auth/me");
  }

  // Logout button in the top bar (teacher pages).
  document.addEventListener("click", async (ev) => {
    const btn = ev.target.closest("[data-logout]");
    if (!btn) return;
    ev.preventDefault();
    try { await loadMe(); await request("POST", "/api/auth/logout"); } catch (e) { /* ignore */ }
    location.href = "/login";
  });

  window.API = {
    get: (u) => request("GET", u),
    post: (u, b) => request("POST", u, b ?? {}),
    put: (u, b) => request("PUT", u, b ?? {}),
    patch: (u, b) => request("PATCH", u, b ?? {}),
    del: (u) => request("DELETE", u),
    loadMe, toast, showError, hide, esc, thaiDate, thaiDateTime,
  };
})();
