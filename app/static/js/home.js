// Home page: hide the floating "ติดต่อเรา" button where the contact section already shows.
(function () {
  const fab = document.querySelector(".contact-fab");
  if (!fab || !("IntersectionObserver" in window)) return;
  const seen = new Set();
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) e.isIntersecting ? seen.add(e.target) : seen.delete(e.target);
    fab.classList.toggle("is-hidden", seen.size > 0);
  });
  document.querySelectorAll("#contact, .lp-footer").forEach((el) => io.observe(el));
})();
