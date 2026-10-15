(() => {
  const menuButton = document.getElementById("mobile-menu-toggle");
  const nav = document.getElementById("main-nav");

  menuButton?.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
  });

  nav?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      nav.classList.remove("is-open");
      menuButton?.setAttribute("aria-expanded", "false");
      menuButton?.setAttribute("aria-label", "Open navigation");
    });
  });

  document.querySelectorAll(".open-harvey").forEach((button) => {
    button.addEventListener("click", () => document.getElementById("harvey-toggle")?.click());
  });

  document.querySelectorAll(".alert-dismiss").forEach((button) => {
    button.addEventListener("click", () => button.closest(".site-alert")?.remove());
  });
})();
