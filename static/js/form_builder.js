// static/js/form_builder.js
// Simple form builder interface similar to Microsoft Forms

document.addEventListener('DOMContentLoaded', () => {
  const fieldsContainer = document.getElementById('fieldsContainer');
  const addFieldBtn = document.getElementById('addField');
  const estruturaInput = document.getElementById('estrutura');
  const form = document.getElementById('formBuilderForm');

  function updateJSON() {
    const fields = [];
    fieldsContainer.querySelectorAll('.field').forEach((fieldEl, idx) => {
      const tipo = fieldEl.querySelector('.field-tipo').value;
      const label = fieldEl.querySelector('.field-label').value.trim();
      const obrigatorio = fieldEl.querySelector('.field-obrigatorio').checked;
      const opcoes = fieldEl.querySelector('.field-opcoes').value
        .split(',')
        .map(o => o.trim())
        .filter(o => o);
      fields.push({ tipo, label, obrigatorio, ordem: idx, opcoes });
    });
    estruturaInput.value = JSON.stringify(fields);
  }

  function addField(data = {}) {
    const div = document.createElement('div');
    div.className = 'field card mb-3';
    div.innerHTML = `
      <div class="card-body">
        <div class="mb-2">
          <label class="form-label">Tipo</label>
          <select class="form-select field-tipo">
            <option value="text">Texto</option>
            <option value="textarea">Parágrafo</option>
            <option value="select">Escolha</option>
          </select>
        </div>
        <div class="mb-2">
          <label class="form-label">Label</label>
          <input type="text" class="form-control field-label">
        </div>
        <div class="mb-2 field-opcoes-wrapper d-none">
          <label class="form-label">Opções (separadas por vírgula)</label>
          <input type="text" class="form-control field-opcoes">
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
    const opcoesInput = div.querySelector('.field-opcoes');

    tipoSelect.addEventListener('change', () => {
      if (tipoSelect.value === 'select') {
        opcoesWrapper.classList.remove('d-none');
      } else {
        opcoesWrapper.classList.add('d-none');
      }
      updateJSON();
    });

    div.querySelector('.remove-field').addEventListener('click', () => {
      div.remove();
      updateJSON();
    });

    div.querySelectorAll('input, select').forEach(el => {
      el.addEventListener('input', updateJSON);
      el.addEventListener('change', updateJSON);
    });

    // Prefill data if editing existing structure
    tipoSelect.value = data.tipo || 'text';
    div.querySelector('.field-label').value = data.label || '';
    div.querySelector('.field-obrigatorio').checked = data.obrigatorio || false;
    if (data.tipo === 'select') {
      opcoesWrapper.classList.remove('d-none');
      opcoesInput.value = (data.opcoes || []).join(', ');
    }

    updateJSON();
  }

  addFieldBtn.addEventListener('click', () => addField());

  // Load existing structure if present
  if (estruturaInput.value) {
    try {
      const parsed = JSON.parse(estruturaInput.value);
      parsed.forEach(f => addField(f));
    } catch (e) {
      console.error('Erro ao carregar estrutura existente', e);
    }
  }

  form.addEventListener('submit', () => {
    updateJSON();
  });
});

