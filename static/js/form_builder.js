// static/js/form_builder.js
// Interface de construção de formulários com ordenação de perguntas

document.addEventListener('DOMContentLoaded', () => {
  const fieldsContainer = document.getElementById('fieldsContainer');
  const estruturaInput = document.getElementById('estrutura');
  const form = document.getElementById('formBuilderForm');

  function updateNumbers() {
    fieldsContainer.querySelectorAll('.field').forEach((el, idx) => {
      const numero = el.querySelector('.question-number');
      if (numero) numero.textContent = `Pergunta ${idx + 1}`;
    });
  }

  function updateQuestionTitle(fieldEl) {
    const titulo = fieldEl.querySelector('.field-label').value.trim();
    const titleSpan = fieldEl.querySelector('.question-title');
    if (titleSpan) titleSpan.textContent = titulo || 'Pergunta';
  }

  function updateJSON() {
    const fields = [];
    fieldsContainer.querySelectorAll('.field').forEach((fieldEl, idx) => {
      const tipo = fieldEl.querySelector('.field-tipo').value;
      const label = fieldEl.querySelector('.field-label').value.trim();
      const obrigatorio = fieldEl.querySelector('.field-obrigatorio').checked;
      const id = fieldEl.dataset.id;
      const fieldData = { id, tipo, label, obrigatorio, ordem: idx };

      if (tipo === 'likert') {
        const linhas = fieldEl
          .querySelector('.field-likert-linhas')
          .value.split(',')
          .map(o => o.trim())
          .filter(o => o);
        const colunas = fieldEl
          .querySelector('.field-likert-colunas')
          .value.split(',')
          .map(o => o.trim())
          .filter(o => o);
        fieldData.linhas = linhas;
        fieldData.colunas = colunas;
      } else if (tipo === 'table') {
        const linhas = parseInt(fieldEl.querySelector('.field-table-rows').value, 10) || 0;
        const colunas = fieldEl
          .querySelector('.field-table-cabecalhos')
          .value.split(',')
          .map(o => o.trim())
          .filter(o => o);
        fieldData.linhas = linhas;
        fieldData.opcoes = colunas;
      } else {
        const opcoes = fieldEl
          .querySelector('.field-opcoes')
          .value.split(',')
          .map(o => o.trim())
          .filter(o => o);
        fieldData.opcoes = opcoes;
      }

      fields.push(fieldData);
    });
    estruturaInput.value = JSON.stringify(fields);
  }

  function addField(tipo, data = {}) {
    const div = document.createElement('div');
    div.className = 'field card mb-3';
    div.dataset.id = data.id || Date.now();
    div.innerHTML = `
      <div class="card-header d-flex align-items-center">
        <button type="button" class="btn btn-light btn-sm drag-handle me-2"><i class="bi bi-grip-vertical"></i></button>
        <span class="question-number me-2"></span>
        <span class="question-title flex-grow-1">${data.label || ''}</span>
      </div>
      <div class="card-body">
        <div class="mb-2">
          <label class="form-label">Tipo</label>
          <select class="form-select field-tipo">
            <option value="text">Texto</option>
            <option value="textarea">Parágrafo</option>
            <option value="select">Escolha</option>
            <option value="option">Opção</option>
            <option value="rating">Classificação</option>
            <option value="date">Data</option>
            <option value="likert">Likert</option>
            <option value="file">Carregar Arquivo</option>
            <option value="nps">Net Promoter Score®</option>
            <option value="section">Seção</option>
            <option value="table">Tabelas</option>
          </select>
        </div>
        <div class="mb-2">
          <label class="form-label">Título</label>
          <input type="text" class="form-control field-label" placeholder="Título da Pergunta">
        </div>
        <div class="mb-2 field-opcoes-wrapper d-none">
          <label class="form-label">Opções (separadas por vírgula)</label>
          <input type="text" class="form-control field-opcoes">
        </div>
        <div class="mb-2 field-likert-wrapper d-none">
          <label class="form-label">Linhas (separadas por vírgula)</label>
          <input type="text" class="form-control field-likert-linhas">
          <label class="form-label mt-2">Colunas (separadas por vírgula)</label>
          <input type="text" class="form-control field-likert-colunas">
        </div>
        <div class="mb-2 field-table-wrapper d-none">
          <label class="form-label">Número de linhas</label>
          <input type="number" min="1" class="form-control field-table-rows" value="1">
          <label class="form-label mt-2">Cabeçalhos (separados por vírgula)</label>
          <input type="text" class="form-control field-table-cabecalhos">
        </div>
        <div class="form-check mb-2">
          <input class="form-check-input field-obrigatorio" type="checkbox" id="field-obrig-${Date.now()}">
          <label class="form-check-label" for="field-obrig-${Date.now()}">Obrigatório</label>
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger remove-field">Remover</button>
      </div>`;

    fieldsContainer.appendChild(div);

    const tipoSelect = div.querySelector('.field-tipo');
    const opcoesWrapper = div.querySelector('.field-opcoes-wrapper');
    const likertWrapper = div.querySelector('.field-likert-wrapper');
    const tableWrapper = div.querySelector('.field-table-wrapper');

    tipoSelect.addEventListener('change', () => {
      if (['select', 'option'].includes(tipoSelect.value)) {
        opcoesWrapper.classList.remove('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.add('d-none');
      } else if (tipoSelect.value === 'likert') {
        opcoesWrapper.classList.add('d-none');
        likertWrapper.classList.remove('d-none');
        tableWrapper.classList.add('d-none');
      } else if (tipoSelect.value === 'table') {
        opcoesWrapper.classList.add('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.remove('d-none');
      } else {
        opcoesWrapper.classList.add('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.add('d-none');
      }
      updateJSON();
    });

    div.querySelector('.remove-field').addEventListener('click', () => {
      div.remove();
      updateNumbers();
      updateJSON();
    });

    div.querySelectorAll('input, select').forEach(el => {
      el.addEventListener('input', () => {
        updateQuestionTitle(div);
        updateJSON();
      });
      el.addEventListener('change', updateJSON);
    });

    // Prefill data if editing existing structure
    tipoSelect.value = data.tipo || tipo || 'text';
    div.querySelector('.field-label').value = data.label || '';
    div.querySelector('.field-obrigatorio').checked = data.obrigatorio || false;
    if (['select', 'option'].includes(data.tipo)) {
      opcoesWrapper.classList.remove('d-none');
      div.querySelector('.field-opcoes').value = (data.opcoes || []).join(', ');
    } else if (data.tipo === 'likert') {
      likertWrapper.classList.remove('d-none');
      div.querySelector('.field-likert-linhas').value = (data.linhas || []).join(', ');
      div.querySelector('.field-likert-colunas').value = (data.colunas || []).join(', ');
    } else if (data.tipo === 'table') {
      tableWrapper.classList.remove('d-none');
      div.querySelector('.field-table-rows').value = data.linhas || 1;
      div.querySelector('.field-table-cabecalhos').value = (data.opcoes || []).join(', ');
    }

    updateQuestionTitle(div);
    updateNumbers();
    updateJSON();
  }

  window.addField = addField;

  new Sortable(fieldsContainer, {
    handle: '.drag-handle',
    animation: 150,
    ghostClass: 'sortable-ghost',
    chosenClass: 'sortable-chosen',
    onStart: () => {
      fieldsContainer.classList.add('sorting');
    },
    onEnd: () => {
      fieldsContainer.classList.remove('sorting');
      updateNumbers();
      updateJSON();
      const ids = Array.from(fieldsContainer.querySelectorAll('.field'))
        .map(el => el.dataset.id)
        .filter(id => !!id);
      if (ids.length) {
        fetch('/formulario/reordenar_perguntas', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids })
        }).then(r => {
          if (r.ok) showToast('Ordem atualizada!');
        });
      }
    }
  });

  // Load existing structure if present
  if (estruturaInput.value) {
    try {
      const parsed = JSON.parse(estruturaInput.value);
      parsed.forEach(f => addField(f.tipo, f));
    } catch (e) {
      console.error('Erro ao carregar estrutura existente', e);
    }
  }

  form.addEventListener('submit', () => {
    updateJSON();
  });

  function showToast(message) {
    const container = document.createElement('div');
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = 1080;
    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-bg-success border-0';
    toastEl.role = 'alert';
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>`;
    container.appendChild(toastEl);
    document.body.appendChild(container);
    const bsToast = new bootstrap.Toast(toastEl);
    bsToast.show();
    toastEl.addEventListener('hidden.bs.toast', () => container.remove());
  }
});

