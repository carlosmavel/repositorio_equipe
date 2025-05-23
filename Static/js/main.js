// static/js/main.js
document.addEventListener("DOMContentLoaded", function () {
  /* ------------------------------------------------------------------
     0) A chave agora é por usuário: readNotifications_<username>      */
  const currentUser = document.body.dataset.currentUser || "anon";
  const READ_KEY    = `readNotifications_${currentUser}`;
  /* ------------------------------------------------------------------ */

  // 1) Inicializa tooltips do Bootstrap
  Array.from(document.querySelectorAll("[title]")).forEach((el) =>
    new bootstrap.Tooltip(el)
  );

  // 2) Fade-out das flash messages
  const flashContainer = document.getElementById("flash-container");
  if (flashContainer) {
    flashContainer.querySelectorAll(".alert").forEach((flash) => {
      setTimeout(() => {
        flash.style.transition = "opacity 0.5s";
        flash.style.opacity = "0";
        setTimeout(() => flash.remove(), 500);
      }, 3000);
    });
  }

  // 3) Carrega IDs já lidos para ESTE usuário
  let readIds = JSON.parse(localStorage.getItem(READ_KEY) || "[]");

  // 4) Seleciona badge e links de notificação
  const badge = document.getElementById("notificationBadge");
  const dropdownToggle = document.getElementById("notificationDropdown");
  let links = [];

  function refreshLinks() {
    links = Array.from(document.querySelectorAll(".notification-link"));
  }

  function styleLinks() {
    links.forEach((link) => {
      const id = link.dataset.id;
      link.classList.toggle("fw-bold", !readIds.includes(id));
    });
  }

  function updateBadge() {
    if (!badge) return;
    const unread = links.reduce(
      (acc, link) => acc + (readIds.includes(link.dataset.id) ? 0 : 1),
      0
    );
    badge.style.display = unread ? "inline-block" : "none";
    badge.textContent = unread;
  }

  function attachClickListeners() {
    links.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const id = link.dataset.id;
        if (!readIds.includes(id)) {
          readIds.push(id);
          localStorage.setItem(READ_KEY, JSON.stringify(readIds));
        }
        link.classList.remove("fw-bold");
        updateBadge();
        setTimeout(() => (window.location.href = link.href), 150);
      });
    });
  }

  // 8) Inicializa quando o dropdown abre
  if (dropdownToggle) {
    dropdownToggle.addEventListener("show.bs.dropdown", () => {
      refreshLinks();
      styleLinks();
      updateBadge();
      attachClickListeners();
    });
  } else {
    // fallback para casos sem dropdown BS
    refreshLinks();
    styleLinks();
    updateBadge();
    attachClickListeners();
  }
});