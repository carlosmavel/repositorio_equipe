// static/js/main.js

document.addEventListener("DOMContentLoaded", function() {
  const READ_KEY = "readNotifications";

  // 1) Inicializa tooltips do Bootstrap
  Array.from(document.querySelectorAll('[title]')).forEach(el =>
    new bootstrap.Tooltip(el)
  );

  // 2) Fade-out das flash messages
  const flashContainer = document.getElementById("flash-container");
  if (flashContainer) {
    flashContainer.querySelectorAll(".alert").forEach(flash => {
      setTimeout(() => {
        flash.style.transition = "opacity 0.5s";
        flash.style.opacity = "0";
        setTimeout(() => flash.remove(), 500);
      }, 3000);
    });
  }

  // 3) Carrega IDs já lidos
  let readIds = JSON.parse(localStorage.getItem(READ_KEY) || "[]");

  // 4) Seleciona badge e links de notificação
  const badge = document.getElementById("notificationBadge");
  const dropdownToggle = document.getElementById("notificationDropdown"); // botão que abre o menu
  let links = [];

  function refreshLinks() {
    links = Array.from(document.querySelectorAll(".notification-link"));
  }

  // 5) Atualiza o estilo dos links (remove negrito nos já lidos)
  function styleLinks() {
    links.forEach(link => {
      const id = link.dataset.id;
      if (readIds.includes(id)) {
        link.classList.remove("fw-bold");
      } else {
        link.classList.add("fw-bold");
      }
    });
  }

  // 6) Recalcula e exibe o badge
  function updateBadge() {
    if (!badge) return;
    const unread = links.reduce((acc, link) =>
      acc + (readIds.includes(link.dataset.id) ? 0 : 1), 0
    );
    if (unread <= 0) {
      badge.style.display = "none";
    } else {
      badge.style.display = "inline-block";
      badge.textContent = unread;
    }
  }

  // 7) Marca link como lido ao clicar
  function attachClickListeners() {
    links.forEach(link => {
      link.addEventListener("click", event => {
        event.preventDefault();
        const id = link.dataset.id;
        if (!readIds.includes(id)) {
          readIds.push(id);
          localStorage.setItem(READ_KEY, JSON.stringify(readIds));
        }
        link.classList.remove("fw-bold");
        updateBadge();
        // redireciona após breve delay para permitir animação
        setTimeout(() => {
          window.location.href = link.href;
        }, 150);
      });
    });
  }

  // 8) Quando o dropdown abre, garante que o badge e estilos estejam atualizados
  if (dropdownToggle) {
    dropdownToggle.addEventListener("show.bs.dropdown", () => {
      refreshLinks();
      styleLinks();
      updateBadge();
      attachClickListeners();
    });
  } else {
    // fallback: se não houver dropdown BS, inicializa logo
    refreshLinks();
    styleLinks();
    updateBadge();
    attachClickListeners();
  }
});