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
  const cargoDefaults = window.cargoDefaults || {};

  function setCargoFuncoesDisabled(prefix, cargoId) {
    const defs = cargoDefaults[cargoId] || { funcoes: [] };
    document.querySelectorAll(`input[id^='${prefix}func']`).forEach((chk) => {
      chk.disabled = defs.funcoes.includes(parseInt(chk.value));
    });
  }

  function applyCargoDefaults(prefix, cargoId) {
    const defs = cargoDefaults[cargoId] || { estabelecimentos: [], setores: [], celulas: [], funcoes: [] };
    const form = prefix === 'edit_' ? document.getElementById('edit_cargo_id')?.closest('form') : document.getElementById('create-user-form');
    const hiddenEstabelecimento = document.getElementById(`${prefix}hidden_estabelecimento_id`);
    const hiddenSetorContainer = document.getElementById(`${prefix}hidden_setor_ids_container`);
    const hiddenCelulaContainer = document.getElementById(`${prefix}hidden_celula_ids_container`);

    const clearAndAppendMultiHidden = (container, name, values) => {
      if (!container) return;
      container.innerHTML = '';
      values.forEach((value) => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = name;
        input.value = value;
        container.appendChild(input);
      });
    };

    const estabelecimentoPadrao = defs.estabelecimentos?.length ? defs.estabelecimentos[0] : '';
    if (hiddenEstabelecimento) {
      hiddenEstabelecimento.value = estabelecimentoPadrao ? String(estabelecimentoPadrao) : '';
    }
    clearAndAppendMultiHidden(hiddenSetorContainer, 'setor_ids', defs.setores || []);
    clearAndAppendMultiHidden(hiddenCelulaContainer, 'celula_ids', defs.celulas || []);

    const instituicaoDisplay = form?.querySelector("input[name='instituicao_nome_herdada']");
    if (instituicaoDisplay) {
      const estabelecimentoMarcado = form?.querySelector(`input[id^='${prefix}est'][value='${estabelecimentoPadrao}']`);
      const instituicaoLabel = estabelecimentoMarcado?.closest('.form-check')?.querySelector('small')?.textContent || '';
      instituicaoDisplay.value = instituicaoLabel.replace('(Instituição:', '').replace(')', '').trim();
    }

    document.querySelectorAll(`input[id^='${prefix}est']`).forEach((chk) => {
      chk.checked = defs.estabelecimentos.includes(parseInt(chk.value));
    });
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

    if (prefix === '') {
      validateCreateUserForm();
    }
  }

  document.getElementById('cargo_id')?.addEventListener('change', (e) => {
    applyCargoDefaults('', e.target.value);
  });
  document.getElementById('edit_cargo_id')?.addEventListener('change', (e) => {
    applyCargoDefaults('edit_', e.target.value);
  });

  const selectedCargoCreate = document.getElementById('cargo_id')?.value;
  if (selectedCargoCreate) {
    applyCargoDefaults('', selectedCargoCreate);
  }
  const selectedCargoEdit = document.getElementById('edit_cargo_id')?.value;
  if (selectedCargoEdit) {
    applyCargoDefaults('edit_', selectedCargoEdit);
  }

  // Expose helper for inline scripts
  window.setCargoFuncoesDisabled = setCargoFuncoesDisabled;

  if (window.manterAbaCadastro) {
    const cadastroTabBtn = document.getElementById('cadastro-tab');
    if (cadastroTabBtn) {
      bootstrap.Tab.getOrCreateInstance(cadastroTabBtn).show();
    }
  }

  function initCargoHierarchySync() {
    const hierarchyForms = document.querySelectorAll('.js-cargo-hierarquia-form');
    if (!hierarchyForms.length) return;

    hierarchyForms.forEach((form) => {
      const celulaCheckboxes = Array.from(form.querySelectorAll("input[type='checkbox'][name='celula_ids'][data-setor-id][data-estabelecimento-id][data-instituicao-id]"));
      const setorCheckboxes = Array.from(form.querySelectorAll("input[type='checkbox'][name='setor_ids'][data-setor-id][data-estabelecimento-id][data-instituicao-id]"));
      const estabelecimentoCheckboxes = Array.from(form.querySelectorAll("input[type='checkbox'][name='estabelecimento_ids'][data-estabelecimento-id][data-instituicao-id]"));
      const instituicaoCheckboxes = Array.from(form.querySelectorAll("input[type='checkbox'][name='instituicao_ids'][data-instituicao-id]"));

      const getByData = (list, key, value) => list.filter((checkbox) => checkbox.dataset[key] === String(value));
      const anyChecked = (list) => list.some((checkbox) => checkbox.checked);
      const setChecked = (list, checked) => {
        list.forEach((checkbox) => {
          checkbox.checked = checked;
          checkbox.indeterminate = false;
        });
      };

      const syncSetorByDescendants = (setorId) => {
        const relatedSetores = getByData(setorCheckboxes, "setorId", setorId);
        if (!relatedSetores.length) return;
        const hasCheckedCelula = anyChecked(getByData(celulaCheckboxes, "setorId", setorId));
        if (hasCheckedCelula) {
          setChecked(relatedSetores, true);
        }
      };

      const syncEstabelecimentoByDescendants = (estabelecimentoId, { allowAutoUncheck = false } = {}) => {
        const relatedEstabelecimentos = getByData(estabelecimentoCheckboxes, "estabelecimentoId", estabelecimentoId);
        if (!relatedEstabelecimentos.length) return;
        const hasCheckedSetor = anyChecked(getByData(setorCheckboxes, "estabelecimentoId", estabelecimentoId));
        const hasCheckedCelula = anyChecked(getByData(celulaCheckboxes, "estabelecimentoId", estabelecimentoId));

        if (hasCheckedSetor || hasCheckedCelula) {
          setChecked(relatedEstabelecimentos, true);
          return;
        }

        if (allowAutoUncheck) {
          setChecked(relatedEstabelecimentos, false);
        }
      };

      const syncInstituicaoByDescendants = (instituicaoId, { allowAutoUncheck = false } = {}) => {
        const relatedInstituicoes = getByData(instituicaoCheckboxes, "instituicaoId", instituicaoId);
        if (!relatedInstituicoes.length) return;
        const hasCheckedEstabelecimento = anyChecked(getByData(estabelecimentoCheckboxes, "instituicaoId", instituicaoId));
        const hasCheckedSetor = anyChecked(getByData(setorCheckboxes, "instituicaoId", instituicaoId));
        const hasCheckedCelula = anyChecked(getByData(celulaCheckboxes, "instituicaoId", instituicaoId));

        if (hasCheckedEstabelecimento || hasCheckedSetor || hasCheckedCelula) {
          setChecked(relatedInstituicoes, true);
          return;
        }

        if (allowAutoUncheck) {
          setChecked(relatedInstituicoes, false);
        }
      };

      const syncAllParents = () => {
        const setorIds = new Set(celulaCheckboxes.map((checkbox) => checkbox.dataset.setorId));
        setorIds.forEach(syncSetorByDescendants);

        const estabelecimentoIds = new Set([
          ...celulaCheckboxes.map((checkbox) => checkbox.dataset.estabelecimentoId),
          ...setorCheckboxes.map((checkbox) => checkbox.dataset.estabelecimentoId),
        ]);
        estabelecimentoIds.forEach(syncEstabelecimentoByDescendants);

        const instituicaoIds = new Set([
          ...celulaCheckboxes.map((checkbox) => checkbox.dataset.instituicaoId),
          ...setorCheckboxes.map((checkbox) => checkbox.dataset.instituicaoId),
          ...estabelecimentoCheckboxes.map((checkbox) => checkbox.dataset.instituicaoId),
        ]);
        instituicaoIds.forEach(syncInstituicaoByDescendants);
      };

      celulaCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
          const { setorId, estabelecimentoId, instituicaoId } = checkbox.dataset;
          if (checkbox.checked) {
            setChecked(getByData(setorCheckboxes, "setorId", setorId), true);
            setChecked(getByData(estabelecimentoCheckboxes, "estabelecimentoId", estabelecimentoId), true);
            setChecked(getByData(instituicaoCheckboxes, "instituicaoId", instituicaoId), true);
            return;
          }

          syncSetorByDescendants(setorId);
          syncEstabelecimentoByDescendants(estabelecimentoId);
          syncInstituicaoByDescendants(instituicaoId);
        });
      });

      setorCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
          const { setorId, estabelecimentoId, instituicaoId } = checkbox.dataset;
          if (checkbox.checked) {
            setChecked(getByData(estabelecimentoCheckboxes, "estabelecimentoId", estabelecimentoId), true);
            setChecked(getByData(instituicaoCheckboxes, "instituicaoId", instituicaoId), true);
            return;
          }

          setChecked(getByData(celulaCheckboxes, "setorId", setorId), false);
          syncEstabelecimentoByDescendants(estabelecimentoId);
          syncInstituicaoByDescendants(instituicaoId);
        });
      });

      estabelecimentoCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
          const { estabelecimentoId, instituicaoId } = checkbox.dataset;
          if (checkbox.checked) {
            setChecked(getByData(instituicaoCheckboxes, "instituicaoId", instituicaoId), true);
            return;
          }

          setChecked(getByData(setorCheckboxes, "estabelecimentoId", estabelecimentoId), false);
          setChecked(getByData(celulaCheckboxes, "estabelecimentoId", estabelecimentoId), false);
          syncInstituicaoByDescendants(instituicaoId, { allowAutoUncheck: true });
        });
      });

      instituicaoCheckboxes.forEach((checkbox) => {
        checkbox.addEventListener("change", () => {
          if (checkbox.checked) return;
          const { instituicaoId } = checkbox.dataset;
          setChecked(getByData(estabelecimentoCheckboxes, "instituicaoId", instituicaoId), false);
          setChecked(getByData(setorCheckboxes, "instituicaoId", instituicaoId), false);
          setChecked(getByData(celulaCheckboxes, "instituicaoId", instituicaoId), false);
        });
      });

      form.addEventListener("submit", () => {
        syncAllParents();
      });

      syncAllParents();
    });
  }

  initCargoHierarchySync();

  function getFieldIdentifier(field) {
    return field?.name || field?.id || "(sem-name-id)";
  }

  function isFieldFilled(field) {
    if (!field) {
      return {
        filled: false,
        valueRead: null,
        reason: "campo inexistente",
        type: "missing",
      };
    }

    const tag = (field.tagName || "").toLowerCase();
    const type = (field.type || tag || "unknown").toLowerCase();
    const role = (field.getAttribute("role") || "").toLowerCase();
    const className = field.className || "";

    if (type === "checkbox" || type === "radio") {
      return {
        filled: field.checked,
        valueRead: field.checked,
        reason: field.checked ? "marcado" : "não marcado",
        type,
      };
    }

    if (field.multiple || type === "select-multiple") {
      const selectedValues = Array.from(field.selectedOptions || []).map((opt) => opt.value).filter(Boolean);
      return {
        filled: selectedValues.length > 0,
        valueRead: selectedValues,
        reason: selectedValues.length > 0 ? "possui opções selecionadas" : "nenhuma opção selecionada",
        type: "select-multiple",
      };
    }

    const rawValue = field.value;
    const textValue = typeof rawValue === "string" ? rawValue.trim() : rawValue;
    const hasValue = Boolean(textValue);

    let reason = hasValue ? "valor preenchido" : "valor vazio";
    if (!hasValue && role.includes("combobox")) {
      reason = "combobox sem valor";
    } else if (!hasValue && className.includes("select2")) {
      reason = "componente select2 sem valor";
    }

    return {
      filled: hasValue,
      valueRead: textValue,
      reason,
      type,
    };
  }

  function validateCreateUserForm() {
    const form = document.getElementById('create-user-form');
    const submitBtn = document.getElementById('submit-create-user');
    if (!form || !submitBtn) return;

    const username = document.getElementById('username');
    const email = document.getElementById('email');
    const cargo = document.getElementById('cargo_id');

    const selectedCargoId = cargo?.value || null;
    const cargoAdminFuncoes = selectedCargoId && cargoDefaults[selectedCargoId]
      ? cargoDefaults[selectedCargoId].funcoes || []
      : [];
    const adminFuncaoId = Number(window.adminFuncaoId);
    const hasAdminByCargo = Number.isInteger(adminFuncaoId)
      ? cargoAdminFuncoes.includes(adminFuncaoId)
      : false;
    const hasAdminMarcadoManual = Number.isInteger(adminFuncaoId)
      ? Array.from(document.querySelectorAll("input[name='funcao_ids']:checked"))
          .some((input) => Number(input.value) === adminFuncaoId)
      : false;

    const exigeHierarquia = !(hasAdminByCargo || hasAdminMarcadoManual);

    const requiredFields = [username, email, cargo];
    const requiredResults = requiredFields.map((field) => {
      const result = isFieldFilled(field);
      return {
        id: field?.id || null,
        name: field?.name || null,
        ...result,
      };
    });

    const selectedCargoDefaults = selectedCargoId && cargoDefaults[selectedCargoId]
      ? cargoDefaults[selectedCargoId]
      : { estabelecimentos: [], setores: [], celulas: [] };
    const cargoDefaultSetores = Array.isArray(selectedCargoDefaults.setores) ? selectedCargoDefaults.setores : [];
    const cargoDefaultCelulas = Array.isArray(selectedCargoDefaults.celulas) ? selectedCargoDefaults.celulas : [];
    const cargoDefaultEstabelecimentos = Array.isArray(selectedCargoDefaults.estabelecimentos) ? selectedCargoDefaults.estabelecimentos : [];

    const getNumericId = (input, prefix) => {
      const fromValue = Number(input?.value);
      if (Number.isInteger(fromValue) && fromValue > 0) return fromValue;
      const fromId = Number((input?.id || '').replace(prefix, ''));
      return Number.isInteger(fromId) && fromId > 0 ? fromId : null;
    };

    const allEstInputs = Array.from(form.querySelectorAll("input[id^='est']"));
    const allSetorInputs = Array.from(form.querySelectorAll("input[id^='setor']"));
    const allCelulaInputs = Array.from(form.querySelectorAll("input[id^='celula']"));

    const setorToEstMap = new Map();
    const celulaToSetorMap = new Map();
    const celulaToEstMap = new Map();

    allSetorInputs.forEach((setorInput) => {
      const setorId = getNumericId(setorInput, 'setor');
      if (!setorId) return;

      const estInput = setorInput
        .closest('.ms-4')
        ?.previousElementSibling
        ?.querySelector("input[id^='est']");
      const estId = getNumericId(estInput, 'est');
      if (estId) setorToEstMap.set(setorId, estId);
    });

    allCelulaInputs.forEach((celulaInput) => {
      const celulaId = getNumericId(celulaInput, 'celula');
      if (!celulaId) return;

      const setorInput = celulaInput
        .closest('.ms-4.mb-2')
        ?.previousElementSibling
        ?.querySelector("input[id^='setor']");
      const setorId = getNumericId(setorInput, 'setor');
      if (setorId) {
        celulaToSetorMap.set(celulaId, setorId);
        const estId = setorToEstMap.get(setorId);
        if (estId) celulaToEstMap.set(celulaId, estId);
      }
    });

    const checkedSetorIds = allSetorInputs
      .filter((input) => input.checked)
      .map((input) => getNumericId(input, 'setor'))
      .filter((value) => Number.isInteger(value));
    const checkedCelulaIds = allCelulaInputs
      .filter((input) => input.checked)
      .map((input) => getNumericId(input, 'celula'))
      .filter((value) => Number.isInteger(value));
    const checkedEstIds = allEstInputs
      .filter((input) => input.checked)
      .map((input) => getNumericId(input, 'est'))
      .filter((value) => Number.isInteger(value));

    const effectiveCelulaIds = new Set([...checkedCelulaIds, ...cargoDefaultCelulas.map(Number).filter(Number.isInteger)]);
    const effectiveSetorIds = new Set([...checkedSetorIds, ...cargoDefaultSetores.map(Number).filter(Number.isInteger)]);
    const effectiveEstabelecimentoIds = new Set([...checkedEstIds, ...cargoDefaultEstabelecimentos.map(Number).filter(Number.isInteger)]);

    effectiveCelulaIds.forEach((celulaId) => {
      const inferredSetorId = celulaToSetorMap.get(celulaId);
      if (inferredSetorId) effectiveSetorIds.add(inferredSetorId);
      const inferredEstId = celulaToEstMap.get(celulaId);
      if (inferredEstId) effectiveEstabelecimentoIds.add(inferredEstId);
    });

    effectiveSetorIds.forEach((setorId) => {
      const inferredEstId = setorToEstMap.get(setorId);
      if (inferredEstId) effectiveEstabelecimentoIds.add(inferredEstId);
    });

    const hiddenEstabelecimentoValue = Number(document.getElementById('hidden_estabelecimento_id')?.value);
    if (Number.isInteger(hiddenEstabelecimentoValue) && hiddenEstabelecimentoValue > 0) {
      effectiveEstabelecimentoIds.add(hiddenEstabelecimentoValue);
    }

    const hasSetor = effectiveSetorIds.size > 0;
    const hasCelula = effectiveCelulaIds.size > 0;
    const hasEstabelecimento = effectiveEstabelecimentoIds.size > 0;

    // Espelha a regra do backend:
    // - setor e célula são obrigatórios para não-admin;
    // - setor pode ser inferido a partir de célula selecionada/herdada;
    // - estabelecimento pode ser inferido a partir do setor/célula ou herdado do cargo.
    const hierarchyOk = !exigeHierarquia || (hasEstabelecimento && hasSetor && hasCelula);

    const requiredFieldsOk = requiredResults.every((fieldResult) => fieldResult.filled);
    const isValid = Boolean(requiredFieldsOk && hierarchyOk);

    submitBtn.disabled = !isValid;
    submitBtn.classList.toggle('disabled', !isValid);

    console.groupCollapsed('[create-user-form] validação botão "Adicionar Usuário"');
    requiredResults.forEach((fieldResult) => {
      console.log('Campo obrigatório', {
        id: fieldResult.id,
        name: fieldResult.name,
        identifier: getFieldIdentifier({ id: fieldResult.id, name: fieldResult.name }),
        type: fieldResult.type,
        valueRead: fieldResult.valueRead,
        filled: fieldResult.filled,
        reason: fieldResult.reason,
      });
    });
    console.log('Campo obrigatório (grupo)', {
      id: '(grupo-hierarquia)',
      name: 'setor_ids/celula_ids',
      type: 'checkbox-group',
      valueRead: {
        estabelecimento_ids_efetivos: Array.from(effectiveEstabelecimentoIds),
        setor_ids_efetivos: Array.from(effectiveSetorIds),
        celula_ids_efetivos: Array.from(effectiveCelulaIds),
        cargo_defaults: {
          estabelecimentos: cargoDefaultEstabelecimentos,
          setores: cargoDefaultSetores,
          celulas: cargoDefaultCelulas,
        },
      },
      filled: hierarchyOk,
      reason: !exigeHierarquia
        ? 'hierarquia dispensada para perfil admin'
        : hasEstabelecimento && hasSetor && hasCelula
          ? 'estabelecimento, setor e célula preenchidos (inclui herdados/inferidos)'
          : `faltando ${[
              !hasEstabelecimento ? 'estabelecimento_id' : null,
              !hasSetor ? 'setor_ids' : null,
              !hasCelula ? 'celula_ids' : null,
            ].filter(Boolean).join(' e ')}`,
    });
    console.log('Resumo validação', {
      exigeHierarquia,
      hasAdminByCargo,
      hasAdminMarcadoManual,
      selectedCargoId,
      requiredFieldsOk,
      hierarchyOk,
      isValid,
      submitDisabled: submitBtn.disabled,
    });
    console.groupEnd();
  }

  const createUserForm = document.getElementById('create-user-form');
  if (createUserForm) {
    createUserForm.addEventListener('input', validateCreateUserForm);
    createUserForm.addEventListener('change', validateCreateUserForm);
    validateCreateUserForm();
  }

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
