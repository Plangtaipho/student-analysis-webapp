// Sign-up and profile: pick the education service area from the national list,
// then get the schools of that area as suggestions for the school box (any name can still be typed).
(function () {
  const area = document.getElementById("area_office");
  const school = document.getElementById("school_name");
  if (!area || !school) return;
  const areaList = document.getElementById("area-list");
  const schoolList = document.getElementById("school-list");
  let names = new Set();

  async function loadSchools() {
    schoolList.innerHTML = "";
    if (!names.has(area.value)) return;
    try {
      const res = await fetch("/api/edu/schools?area=" + encodeURIComponent(area.value));
      if (!res.ok) return;
      const list = await res.json();
      schoolList.innerHTML = list.map((s) => `<option value="${API.esc(s)}"></option>`).join("");
    } catch (e) { /* suggestions only */ }
  }

  (async function () {
    try {
      const res = await fetch("/api/edu/areas");
      const list = await res.json();
      names = new Set(list.map((a) => a.name));
      areaList.innerHTML = list.map((a) => `<option value="${API.esc(a.name)}">${API.esc(a.short)}</option>`).join("");
      loadSchools();
    } catch (e) { /* the box still accepts typing */ }
  })();
  area.addEventListener("change", loadSchools);
  area.addEventListener("input", () => { if (names.has(area.value)) loadSchools(); });
})();
