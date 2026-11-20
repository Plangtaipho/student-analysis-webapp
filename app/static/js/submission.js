// Read-only view of one student's answers.
(async function () {
  const { classroomId, submissionId } = document.body.dataset;
  const url = `/api/classrooms/${classroomId}/submissions/${submissionId}`;
  try {
    await API.loadMe();
    const s = await API.get(url);
    document.getElementById("s-title").textContent = `เลขที่ ${s.student_no} ${s.full_name}${s.nickname ? " (" + s.nickname + ")" : ""}`;
    document.getElementById("s-time").textContent = "ส่งเมื่อ " + API.thaiDateTime(s.submitted_at);
    document.querySelectorAll("[data-p]").forEach((el) => {
      let v = s.personal_info[el.dataset.p];
      if (el.dataset.p === "parent_status" && s.personal_info.parent_status_other) v += ` (${s.personal_info.parent_status_other})`;
      el.textContent = v === undefined || v === "" ? "-" : v;
    });
    document.querySelectorAll("[data-q]").forEach((el) => {
      el.textContent = s.open_answers[el.dataset.q] || "-";
    });
    document.getElementById("prefs").innerHTML = s.learning_prefs.map((p) => `<li>${API.esc(p.label)}</li>`).join("");
    document.getElementById("pdf-one").href = `${url}/pdf`;
    document.getElementById("eval-link").href = `/app/classrooms/${classroomId}/submissions/${submissionId}/evaluate`;
  } catch (e) {
    API.toast(e.message);
  }
})();
