// static/js/main.js

document.addEventListener("DOMContentLoaded", function () {
  /* ------------------------------------------------------------------
   * 0) A chave agora é por usuário: readNotifications_<username>
   * ------------------------------------------------------------------ */
  const currentUser = document.body.dataset.currentUser || "anon";
  const READ_KEY = `readNotifications_${currentUser}`;
  /* ------------------------------------------------------------------ */

  // 1) Inicializa apenas os tooltips marcados, com offset para centralizar
  Array.from(document.querySelectorAll('[data-bs-toggle="tooltip"]')).forEach((el) =>
    new bootstrap.Tooltip(el, {
      offset: [0, 6], // [x-deslocamento, y-deslocamento]
    })
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
  const dropdownToggle = document.getElementById("notificationDropdown"); // Deve corresponder ao ID no base.html
  let links = []; // será populado por refreshLinks

  function refreshLinks() {
    links = Array.from(document.querySelectorAll(".notification-link"));
  }

  function styleLinks() {
    links.forEach((link) => {
      const id = link.dataset.id; // Pega o ID da notificação do data attribute
      link.classList.toggle("fw-bold", !readIds.includes(id));
    });
  }

  function updateBadge() {
    if (!badge) return;
    // Não precisa chamar refreshLinks() aqui se já foi chamado antes de styleLinks e updateBadge
    const unread = links.reduce(
      (acc, link) => acc + (readIds.includes(link.dataset.id) ? 0 : 1),
      0
    );
    badge.style.display = unread > 0 ? "inline-block" : "none";
    badge.textContent = unread;
  }

  // Função auxiliar para marcar uma notificação como lida (interna ao main.js)
  function _markNotificationAsReadLogic(notificationId, linkElement) {
    if (!readIds.includes(notificationId)) {
      readIds.push(notificationId);
      localStorage.setItem(READ_KEY, JSON.stringify(readIds));
    }
    if (linkElement) {
      linkElement.classList.remove("fw-bold");
    } else {
      // Se o elemento não foi passado, tenta encontrá-lo para atualizar o estilo
      const linkToStyle = links.find(l => l.dataset.id === notificationId);
      if (linkToStyle) {
        linkToStyle.classList.remove("fw-bold");
      }
    }
    updateBadge(); // Atualiza o contador do badge
  }

  function attachClickListeners() {
    links.forEach((link) => {
      if (link.dataset.listenerAttached === "true") return;
      link.addEventListener("click", (event) => {
        event.preventDefault();
        const id = link.dataset.id;
        _markNotificationAsReadLogic(id, link); // Usa a função auxiliar
        setTimeout(() => (window.location.href = link.href), 150);
      });
      link.dataset.listenerAttached = "true";
    });
  }

  // --- LÓGICA DE INICIALIZAÇÃO NA CARGA DA PÁGINA ---
  // Garante que o estado inicial das notificações (badge e estilos) esteja correto no load.
  refreshLinks();
  styleLinks();
  updateBadge();
  attachClickListeners();

  if (dropdownToggle) {
    dropdownToggle.addEventListener("show.bs.dropdown", () => {
      // Quando o dropdown é aberto, re-sincroniza para garantir que está tudo atualizado.
      refreshLinks();
      styleLinks();
      updateBadge();
      // Re-atachar listeners aqui é uma precaução, caso os links sejam
      // alterados dinamicamente (o que não é o caso agora, mas não prejudica).
      attachClickListeners();
    });
  }

  // --- NOVA FUNÇÃO GLOBAL PARA MARCAR NOTIFICAÇÃO PELA URL ---
  // Esta função ficará disponível globalmente para ser chamada de outros scripts (ex: inline nos templates)
  window.markNotificationAsReadMatchingUrl = function(targetPageUrl) {
    refreshLinks(); // Garante que 'links' está atualizado com os elementos do DOM
    
    // Normaliza a targetPageUrl para absoluta, caso seja relativa
    const currentAbsoluteUrl = new URL(targetPageUrl, window.location.origin).href;

    links.forEach(link => {
        // Normaliza a URL da notificação para absoluta também
        const notificationUrl = new URL(link.href, window.location.origin).href;
        const notificationId = link.dataset.id;

        if (notificationUrl === currentAbsoluteUrl && !readIds.includes(notificationId)) {
            _markNotificationAsReadLogic(notificationId, link);
            // console.log(`Notificação ${notificationId} marcada como lida para URL: ${targetPageUrl}`);
        }
    });
  }
  // --- FIM DA NOVA FUNÇÃO GLOBAL ---
});