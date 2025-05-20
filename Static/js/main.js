// static/js/main.js

document.addEventListener("DOMContentLoaded", function() {
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

  // 3) Lê do localStorage os IDs já lidos
  const READ_KEY = "readNotifications";
  let readIds = JSON.parse(localStorage.getItem(READ_KEY) || "[]");

  // 4) Obtém todos os links de notificação na página
  const links = Array.from(document.querySelectorAll(".notification-link"));
  const total = links.length;
  const badge = document.getElementById("notificationBadge");

  // 5) Marca como “não em negrito” os que já estão em readIds
  links.forEach(link => {
    const id = link.dataset.id;
    if (readIds.includes(id)) {
      link.classList.remove("fw-bold");
    }
  });

  // 6) Função que recalcula e exibe o badge
  function updateBadge() {
    if (!badge) return;
    // conta quantos links NÃO estão em readIds
    const unread = links.reduce((acc, link) => {
      return acc + (readIds.includes(link.dataset.id) ? 0 : 1);
    }, 0);

    if (unread <= 0) {
      badge.style.display = "none";
    } else {
      badge.style.display = "inline-block";
      badge.textContent = unread;
    }
  }

  // mostra o badge na carga inicial
  updateBadge();

  // 7) No clique em cada link:
  links.forEach(link => {
    link.addEventListener("click", event => {
      event.preventDefault();
      const id = link.dataset.id;

      // só adiciona se ainda não estava lido
      if (!readIds.includes(id)) {
        readIds.push(id);
        localStorage.setItem(READ_KEY, JSON.stringify(readIds));
      }

      // retira o negrito e atualiza badge
      link.classList.remove("fw-bold");
      updateBadge();

      // navega após 150ms
      setTimeout(() => {
        window.location.href = link.href;
      }, 150);
    });
  });
});