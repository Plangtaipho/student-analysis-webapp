// Name with a chosen title (คำนำหน้า): a <select data-prefix>, a text box for the rest of the name,
// and a hidden input that holds the joined name the forms send, e.g. "นางสาว" + "ใจดี ตั้งใจสอน".
// Markup: <div data-name-group><select data-prefix>…</select><input data-name-rest><input type="hidden" id="…"></div>
// "อื่นๆ" has value "-": the person types the whole name with their own title.
window.NamePrefix = (function () {
  function parts(g) {
    return { sel: g.querySelector("[data-prefix]"), rest: g.querySelector("[data-name-rest]"), hidden: g.querySelector("input[type=hidden]") };
  }
  function sync(g) {
    const { sel, rest, hidden } = parts(g);
    const p = sel.value === "-" ? "" : sel.value;
    hidden.value = (p + rest.value.trim()).trim();
  }
  function set(hiddenId, full) {
    const hidden = document.getElementById(hiddenId);
    const g = hidden && hidden.closest("[data-name-group]");
    if (!g) return;
    const { sel, rest } = parts(g);
    full = (full || "").trim();
    // Longest title first so "นางสาว" wins over "นาง".
    const titles = [...sel.options].map((o) => o.value).filter((v) => v && v !== "-").sort((a, b) => b.length - a.length);
    const t = titles.find((x) => full.startsWith(x));
    sel.value = t || (full ? "-" : "");
    rest.value = t ? full.slice(t.length).trim() : full;
    sync(g);
  }
  document.querySelectorAll("[data-name-group]").forEach((g) => {
    const { sel, rest } = parts(g);
    sel.addEventListener("change", () => sync(g));
    rest.addEventListener("input", () => sync(g));
    // Someone who types a title anyway ("นาย...") gets it moved into the menu.
    rest.addEventListener("blur", () => { const h = parts(g).hidden; if (sel.value === "" || sel.value === "-") set(h.id, rest.value); });
  });
  return { set, sync };
})();
