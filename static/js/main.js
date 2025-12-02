// static/js/main.js

document.addEventListener("DOMContentLoaded", function () {
  /* ------------------------------------------------------------------
   * 0) A chave agora é por usuário: readNotifications_<username>
   * ------------------------------------------------------------------ */
  const currentUser = document.body.dataset.currentUser || "anon";
  const READ_KEY = `readNotifications_${currentUser}`;
  /* ------------------------------------------------------------------ */

  const THEME_KEY = "theme";

  function applyTheme(theme) {
    if (theme === "dark") {
      document.documentElement.setAttribute("data-bs-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-bs-theme");
    }
  }

  function toggleTheme() {
    const newTheme = localStorage.getItem(THEME_KEY) === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_KEY, newTheme);
    applyTheme(newTheme);
    window.dispatchEvent(new Event("themeChange"));
  }

  document.getElementById("themeToggle")?.addEventListener("click", function (e) {
    e.preventDefault();
    toggleTheme();
  });

  window.toggleTheme = toggleTheme;
  applyTheme(localStorage.getItem(THEME_KEY));

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

  function syncReadIdsFromDom() {
    links.forEach((link) => {
      if (link.dataset.lido === "true") {
        const id = link.dataset.id;
        if (id && !readIds.includes(id)) {
          readIds.push(id);
        }
      }
    });
    localStorage.setItem(READ_KEY, JSON.stringify(readIds));
  }

  function refreshLinks() {
    links = Array.from(document.querySelectorAll(".notification-link"));
    syncReadIdsFromDom();
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

    const serverCount = parseInt(badge.dataset.serverCount || '0', 10);

    const domCount = links.reduce(
      (acc, link) => acc + (readIds.includes(link.dataset.id) ? 0 : 1),
      0
    );
    const unread = Math.max(serverCount, domCount);
    badge.style.display = unread > 0 ? "inline-block" : "none";
    badge.textContent = unread;
  }

  // Função auxiliar para marcar uma notificação como lida (interna ao main.js)
  function _markNotificationAsReadLogic(notificationId, linkElement) {
    if (!readIds.includes(notificationId)) {
      readIds.push(notificationId);
      localStorage.setItem(READ_KEY, JSON.stringify(readIds));
      if (badge && badge.dataset.serverCount) {

        const c = parseInt(badge.dataset.serverCount, 10);
        if (c > 0) {
          badge.dataset.serverCount = String(c - 1);
        }
      }
      // Persiste no servidor
      fetch(`/api/notifications/${notificationId}/read`, { method: 'POST' });

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

    const menu = document.getElementById("notificationMenu");
    if (menu) {
      let offset = menu.querySelectorAll(".notification-link").length;
      const limit = 10;
      let loading = false;
      let endReached = false;

      function appendNotifications(items) {
        if (items.length === 0) {
          endReached = true;
          return;
        }
        for (const n of items) {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = n.url;
          a.textContent = n.message;
          const isRead = n.lido || readIds.includes(String(n.id));
          a.className = `dropdown-item notification-link ${isRead ? "" : "fw-bold"}`;
          a.dataset.id = n.id;
          a.dataset.lido = n.lido ? "true" : "false";
          li.appendChild(a);
          li.classList.add("is-new");
          li.addEventListener(
            "animationend",
            () => li.classList.remove("is-new"),
            { once: true }
          );
          menu.appendChild(li);
        }
        refreshLinks();
        styleLinks();
        attachClickListeners();
      }

      function loadMore() {
        if (loading || endReached) return;
        loading = true;
        fetch(`/api/notifications?offset=${offset}&limit=${limit}`)
          .then((r) => r.json())
          .then((data) => {
            appendNotifications(data);
            offset += data.length;
            updateBadge();
          })
          .finally(() => {
            loading = false;
          });
      }

      menu.addEventListener("scroll", () => {
        if (
          menu.scrollTop + menu.clientHeight >= menu.scrollHeight - 5
        ) {
          loadMore();
        }
      });
    }
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

  // Torna linhas de tabela com a classe .clickable-row navegáveis
  document.querySelectorAll('.clickable-row').forEach((row) => {
    row.addEventListener('click', (e) => {
      if (e.target.tagName !== 'A' && !e.target.closest('a') &&
          e.target.tagName !== 'BUTTON' && !e.target.closest('button')) {
        const href = row.dataset.href;
        if (href) {
          window.location.href = href;
        }
      }
    });
  });

  document.querySelectorAll('.copy-link-icon').forEach((icon) => {
    icon.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const url = icon.dataset.url;
      if (url && navigator.clipboard) {
        navigator.clipboard.writeText(url);
      }
    });
  });

  // --------------------------------------------------------------
  // Auxiliar: permite apenas um estabelecimento selecionado
  document.querySelectorAll('input[name="estabelecimento_id"]').forEach((chk) => {
    chk.addEventListener('change', () => {
      if (chk.checked) {
        document.querySelectorAll('input[name="estabelecimento_id"]').forEach((o) => {
          if (o !== chk) o.checked = false;
        });
      }
    });
  });


  const cargoDefaults = window.cargoDefaults || {};

  function setCargoFuncoesDisabled(prefix, cargoId) {
    const defs = cargoDefaults[cargoId] || { funcoes: [] };
    document.querySelectorAll(`input[id^='${prefix}func']`).forEach((chk) => {
      chk.disabled = defs.funcoes.includes(parseInt(chk.value));
    });
  }

  function applyCargoDefaults(prefix, cargoId) {
    const defs = cargoDefaults[cargoId] || { setores: [], celulas: [], funcoes: [] };
    document.querySelectorAll(`input[id^='${prefix}setor']`).forEach((chk) => {
      chk.checked = defs.setores.includes(parseInt(chk.value));
    });
    document.querySelectorAll(`input[id^='${prefix}celula']`).forEach((chk) => {
      chk.checked = defs.celulas.includes(parseInt(chk.value));
    });
    document.querySelectorAll(`input[id^='${prefix}func']`).forEach((chk) => {
      const isDefault = defs.funcoes.includes(parseInt(chk.value));
      chk.checked = isDefault;
      chk.disabled = isDefault;
    });
  }

  document.getElementById('cargo_id')?.addEventListener('change', (e) => {
    applyCargoDefaults('', e.target.value);
  });
  document.getElementById('edit_cargo_id')?.addEventListener('change', (e) => {
    applyCargoDefaults('edit_', e.target.value);
  });

  // Expose helper for inline scripts
  window.setCargoFuncoesDisabled = setCargoFuncoesDisabled;

  // Mostra o campo de especificar apenas quando a opção "Outra" estiver selecionada
  document.querySelectorAll('select[data-outra-select]').forEach((select) => {
    const especificar = select.parentElement.querySelector('.outra-especifique');
    if (!especificar) return;
    const toggle = () => {
      especificar.classList.toggle('d-none', select.value !== 'outra');
    };
    toggle();
    select.addEventListener('change', toggle);
  });

  document.querySelectorAll('.outra-option').forEach((outra) => {
    const container = outra.closest('.mb-3');
    if (!container || container.dataset.outraBound) return;
    container.dataset.outraBound = 'true';
    const inputs = container.querySelectorAll('input[type="radio"], input[type="checkbox"]');
    const especificar = container.querySelector('.outra-especifique');
    if (!especificar) return;
    const toggle = () => {
      const show = Array.from(inputs).some((inp) => inp.value === 'outra' && inp.checked);
      especificar.classList.toggle('d-none', !show);
    };
    toggle();
    inputs.forEach((inp) => inp.addEventListener('change', toggle));
  });

});
