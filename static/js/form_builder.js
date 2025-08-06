// static/js/form_builder.js
// Interface de construção de formulários com ordenação de perguntas

document.addEventListener('DOMContentLoaded', () => {
  const fieldsContainer = document.getElementById('fieldsContainer');
  const estruturaInput = document.getElementById('estrutura');
  const form = document.getElementById('formBuilderForm');

  async function uploadImage(file) {
    const fd = new FormData();
    fd.append('imagem', file);
    const resp = await fetch('/ordem-servico/formularios/upload-imagem', {
      method: 'POST',
      body: fd,
    });
    if (resp.ok) {
      const data = await resp.json();
      return data.url;
    }
    return '';
  }

  function parseYouTube(url) {
    const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([\w-]{11})/);
    return match ? `https://www.youtube.com/embed/${match[1]}` : '';
  }

  function updateNumbers() {
    let pergunta = 0;
    let secao = 0;
    fieldsContainer.querySelectorAll('.field').forEach(el => {
      const numero = el.querySelector('.question-number');
      const tipoEl = el.querySelector('.field-tipo');
      if (tipoEl && tipoEl.value === 'section') {
        secao += 1;
        if (numero) numero.textContent = `Seção ${secao}`;
      } else {
        pergunta += 1;
        if (numero) numero.textContent = `Pergunta ${pergunta}`;
      }
    });
  }

  function updateQuestionTitle(fieldEl) {
    const titulo = fieldEl.querySelector('.field-label').value.trim();
    const tipo = fieldEl.querySelector('.field-tipo').value;
    const titleSpan = fieldEl.querySelector('.question-title');
    if (!titleSpan) return;
    if (tipo === 'section') {
      titleSpan.textContent = titulo || 'Seção';
    } else {
      titleSpan.textContent = titulo || 'Pergunta';
    }
  }

  function updateJSON() {
    const fields = [];
    let currentSection = null;
    fieldsContainer.querySelectorAll('.field').forEach((fieldEl, idx) => {
      const tipo = fieldEl.querySelector('.field-tipo').value;
      const id = fieldEl.dataset.id;

      if (tipo === 'section') {
        const titulo = fieldEl.querySelector('.field-label').value.trim();
        const subtitulo = fieldEl.querySelector('.field-subtitulo')?.value.trim() || '';
        const imagem = fieldEl.querySelector('.field-midia')?.value.trim() || '';
        const video = fieldEl.querySelector('.field-video')?.value.trim() || '';
        currentSection = { id, tipo, titulo, subtitulo, imagem_url: imagem, video_url: video, ordem: idx, campos: [] };
        fields.push(currentSection);
        return;
      }

      const label = fieldEl.querySelector('.field-label').value.trim();
      const subtitulo = fieldEl.querySelector('.field-subtitulo')?.value.trim() || '';
      const imagem = fieldEl.querySelector('.field-midia')?.value.trim() || '';
      const video = fieldEl.querySelector('.field-video')?.value.trim() || '';
      const obrigatoria = fieldEl.querySelector('.field-obrigatoria').checked;
      const fieldData = {
        id,
        tipo,
        label,
        subtitulo,
        midia_url: imagem,
        video_url: video,
        obrigatoria,
        ordem: idx,
        secao_id: currentSection ? currentSection.id : null,
      };

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
      } else if (tipo === 'option') {
        const opcoes = fieldEl
          .querySelector('.field-opcoes')
          .value.split(',')
          .map(o => o.trim())
          .filter(o => o);
        fieldData.opcoes = opcoes;
        fieldData.temOpcaoOutra = fieldEl.querySelector('.field-outra').checked;
        fieldData.permiteMultiplaEscolha = fieldEl.querySelector('.field-multipla').checked;
        fieldData.usarMenuSuspenso = fieldEl.querySelector('.field-menu-suspenso').checked;
        fieldData.embaralharOpcoes = fieldEl.querySelector('.field-embaralhar').checked;
        let ramificacoes = [];
        const ramText = fieldEl.querySelector('.field-ramificacoes').value.trim();
        if (ramText) {
          try {
            ramificacoes = JSON.parse(ramText);
          } catch (e) {
            console.warn('Ramificações inválidas para a pergunta', e);
          }
        }
        fieldData.ramificacoes = ramificacoes;
      } else {
        const opcoes = fieldEl
          .querySelector('.field-opcoes')
          .value.split(',')
          .map(o => o.trim())
          .filter(o => o);
        fieldData.opcoes = opcoes;
      }

      if (currentSection) {
        currentSection.campos.push(fieldData);
      } else {
        fields.push(fieldData);
      }
    });
    estruturaInput.value = JSON.stringify(fields);
  }

  function addField(tipo, data = {}) {
    const div = document.createElement('div');
    div.className = 'field card mb-3';
    div.dataset.id = data.id || Date.now();
    const unique = Date.now();
    div.innerHTML = `
      <div class="card-header d-flex align-items-center">
        <button type="button" class="btn btn-light btn-sm drag-handle me-2"><i class="bi bi-grip-vertical"></i></button>
        <span class="question-number me-2"></span>
        <span class="question-title flex-grow-1">${data.label || ''}</span>
        <div class="btn-group ms-auto">
          <button type="button" class="btn btn-light btn-sm add-image" title="Adicionar imagem">🖼️</button>
          <button type="button" class="btn btn-light btn-sm add-video" title="Adicionar vídeo">🎥</button>
          <button type="button" class="btn btn-light btn-sm duplicate-field" title="Duplicar"><i class="bi bi-files"></i></button>
          <button type="button" class="btn btn-light btn-sm move-up-field" title="Mover para cima"><i class="bi bi-arrow-up"></i></button>
          <button type="button" class="btn btn-light btn-sm move-down-field" title="Mover para baixo"><i class="bi bi-arrow-down"></i></button>
          <button type="button" class="btn btn-light btn-sm remove-field" title="Excluir"><i class="bi bi-trash"></i></button>
        </div>
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
        <div class="mb-2 field-subtitulo-wrapper">
          <label class="form-label">Subtítulo</label>
          <input type="text" class="form-control field-subtitulo" placeholder="Subtítulo da Pergunta">
        </div>
        <input type="hidden" class="field-midia">
        <input type="hidden" class="field-video">
        <div class="media-preview text-end mb-2">
          <div class="image-holder"></div>
          <div class="video-holder mt-2"></div>
        </div>
        <div class="mb-2 field-section-subtitulo-wrapper d-none">
          <label class="form-label">Subtítulo</label>
          <input type="text" class="form-control field-subtitulo" placeholder="Insira um subtítulo">
        </div>
        <div class="mb-2 field-opcoes-wrapper d-none">
          <label class="form-label">Opções (separadas por vírgula)</label>
          <input type="text" class="form-control field-opcoes">
        </div>
        <div class="form-check mb-2 field-outra-wrapper d-none">
          <input class="form-check-input field-outra" type="checkbox" id="field-outra-${unique}">
          <label class="form-check-label" for="field-outra-${unique}">Opção "Outra"</label>
        </div>
        <div class="form-check mb-2 field-multipla-wrapper d-none">
          <input class="form-check-input field-multipla" type="checkbox" id="field-multipla-${unique}">
          <label class="form-check-label" for="field-multipla-${unique}">Várias respostas</label>
        </div>
        <div class="form-check mb-2 field-menu-suspenso-wrapper d-none">
          <input class="form-check-input field-menu-suspenso" type="checkbox" id="field-menu-${unique}">
          <label class="form-check-label" for="field-menu-${unique}">Menu suspenso</label>
        </div>
        <div class="form-check mb-2 field-embaralhar-wrapper d-none">
          <input class="form-check-input field-embaralhar" type="checkbox" id="field-embaralhar-${unique}">
          <label class="form-check-label" for="field-embaralhar-${unique}">Ordenar aleatoriamente</label>
        </div>
        <div class="mb-2 field-ramificacoes-wrapper d-none">
          <label class="form-label">Ramificações (JSON)</label>
          <input type="text" class="form-control field-ramificacoes" placeholder='{"Opção": "Destino"}'>
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
        <div class="form-check mb-2 field-obrigatoria-wrapper">
          <input class="form-check-input field-obrigatoria" type="checkbox" id="field-obrig-${unique}">
          <label class="form-check-label" for="field-obrig-${unique}">Obrigatória</label>
        </div>
      </div>
      <div class="modal fade" id="imageModal-${unique}" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Adicionar imagem</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <input type="file" class="form-control image-input">
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-primary save-image">Salvar</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal fade" id="videoModal-${unique}" tabindex="-1">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Adicionar vídeo</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <input type="text" class="form-control video-url" placeholder="URL do vídeo">
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-primary save-video">Salvar</button>
            </div>
          </div>
        </div>
      </div>`;

    fieldsContainer.appendChild(div);

    const tipoSelect = div.querySelector('.field-tipo');
    const opcoesWrapper = div.querySelector('.field-opcoes-wrapper');
    const likertWrapper = div.querySelector('.field-likert-wrapper');
    const tableWrapper = div.querySelector('.field-table-wrapper');
    const obrigatoriaWrapper = div.querySelector('.field-obrigatoria-wrapper');
    const sectionSubtitleWrapper = div.querySelector('.field-section-subtitulo-wrapper');
    const subtituloWrapper = div.querySelector('.field-subtitulo-wrapper');
    const midiaHidden = div.querySelector('.field-midia');
    const videoHidden = div.querySelector('.field-video');
    const imageHolder = div.querySelector('.media-preview .image-holder');
    const videoHolder = div.querySelector('.media-preview .video-holder');
    const outraWrapper = div.querySelector('.field-outra-wrapper');
    const multiplaWrapper = div.querySelector('.field-multipla-wrapper');
    const menuSuspensoWrapper = div.querySelector('.field-menu-suspenso-wrapper');
    const embaralharWrapper = div.querySelector('.field-embaralhar-wrapper');
    const ramificacoesWrapper = div.querySelector('.field-ramificacoes-wrapper');
    const labelInput = div.querySelector('.field-label');
    const imgBtn = div.querySelector('.add-image');
    const vidBtn = div.querySelector('.add-video');
    const imageModalEl = div.querySelector(`#imageModal-${unique}`);
    const videoModalEl = div.querySelector(`#videoModal-${unique}`);

    tipoSelect.addEventListener('change', () => {
      const tipoVal = tipoSelect.value;
      if (tipoVal === 'option') {
        opcoesWrapper.classList.remove('d-none');
        outraWrapper.classList.remove('d-none');
        multiplaWrapper.classList.remove('d-none');
        menuSuspensoWrapper.classList.remove('d-none');
        embaralharWrapper.classList.remove('d-none');
        ramificacoesWrapper.classList.remove('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.add('d-none');
        sectionSubtitleWrapper.classList.add('d-none');
        subtituloWrapper.classList.remove('d-none');
        obrigatoriaWrapper.classList.remove('d-none');
        labelInput.placeholder = 'Título da Pergunta';
      } else if (tipoVal === 'select') {
        opcoesWrapper.classList.remove('d-none');
        outraWrapper.classList.add('d-none');
        multiplaWrapper.classList.add('d-none');
        menuSuspensoWrapper.classList.add('d-none');
        embaralharWrapper.classList.add('d-none');
        ramificacoesWrapper.classList.add('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.add('d-none');
        sectionSubtitleWrapper.classList.add('d-none');
        subtituloWrapper.classList.remove('d-none');
        obrigatoriaWrapper.classList.remove('d-none');
        labelInput.placeholder = 'Título da Pergunta';
      } else if (tipoVal === 'likert') {
        opcoesWrapper.classList.add('d-none');
        outraWrapper.classList.add('d-none');
        multiplaWrapper.classList.add('d-none');
        menuSuspensoWrapper.classList.add('d-none');
        embaralharWrapper.classList.add('d-none');
        ramificacoesWrapper.classList.add('d-none');
        likertWrapper.classList.remove('d-none');
        tableWrapper.classList.add('d-none');
        sectionSubtitleWrapper.classList.add('d-none');
        subtituloWrapper.classList.remove('d-none');
        obrigatoriaWrapper.classList.remove('d-none');
        labelInput.placeholder = 'Título da Pergunta';
      } else if (tipoVal === 'table') {
        opcoesWrapper.classList.add('d-none');
        outraWrapper.classList.add('d-none');
        multiplaWrapper.classList.add('d-none');
        menuSuspensoWrapper.classList.add('d-none');
        embaralharWrapper.classList.add('d-none');
        ramificacoesWrapper.classList.add('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.remove('d-none');
        sectionSubtitleWrapper.classList.add('d-none');
        subtituloWrapper.classList.remove('d-none');
        obrigatoriaWrapper.classList.remove('d-none');
        labelInput.placeholder = 'Título da Pergunta';
      } else if (tipoVal === 'section') {
        opcoesWrapper.classList.add('d-none');
        outraWrapper.classList.add('d-none');
        multiplaWrapper.classList.add('d-none');
        menuSuspensoWrapper.classList.add('d-none');
        embaralharWrapper.classList.add('d-none');
        ramificacoesWrapper.classList.add('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.add('d-none');
        obrigatoriaWrapper.classList.add('d-none');
        subtituloWrapper.classList.add('d-none');
        sectionSubtitleWrapper.classList.remove('d-none');
        labelInput.placeholder = 'Insira o seu título aqui';
      } else {
        opcoesWrapper.classList.add('d-none');
        outraWrapper.classList.add('d-none');
        multiplaWrapper.classList.add('d-none');
        menuSuspensoWrapper.classList.add('d-none');
        embaralharWrapper.classList.add('d-none');
        ramificacoesWrapper.classList.add('d-none');
        likertWrapper.classList.add('d-none');
        tableWrapper.classList.add('d-none');
        sectionSubtitleWrapper.classList.add('d-none');
        subtituloWrapper.classList.remove('d-none');
        obrigatoriaWrapper.classList.remove('d-none');
        labelInput.placeholder = 'Título da Pergunta';
      }
      if (tipoVal === 'section') {
        div.classList.add('section-card');
      } else {
        div.classList.remove('section-card');
      }
      updateNumbers();
      updateQuestionTitle(div);
      updateJSON();
    });

    div.querySelector('.remove-field').addEventListener('click', () => {
      div.remove();
      updateNumbers();
      updateJSON();
    });

    div.querySelector('.duplicate-field').addEventListener('click', () => {
      updateJSON();
      const parsed = JSON.parse(estruturaInput.value || '[]');
      const idx = Array.from(fieldsContainer.children).indexOf(div);
      const dataClone = parsed[idx];
      addField(dataClone.tipo, dataClone);
    });

    div.querySelector('.move-up-field').addEventListener('click', () => {
      const prev = div.previousElementSibling;
      if (prev) {
        fieldsContainer.insertBefore(div, prev);
        updateNumbers();
        updateJSON();
      }
    });

    div.querySelector('.move-down-field').addEventListener('click', () => {
      const next = div.nextElementSibling;
      if (next) {
        fieldsContainer.insertBefore(next, div);
        updateNumbers();
        updateJSON();
      }
    });

    div.querySelectorAll('input:not(.image-input):not(.video-url), select, textarea').forEach(el => {
      el.addEventListener('input', () => {
        updateQuestionTitle(div);
        updateJSON();
      });
      el.addEventListener('change', updateJSON);
    });

    if (imgBtn) {
      const imageModal = new bootstrap.Modal(imageModalEl);
      const imageInput = imageModalEl.querySelector('.image-input');
      imageModalEl.querySelector('.save-image').addEventListener('click', async () => {
        if (imageInput.files[0]) {
          const url = await uploadImage(imageInput.files[0]);
          midiaHidden.value = url;
          imageHolder.innerHTML = url ? `<img src="${url}" class="img-fluid" style="max-width:200px;">` : '';
          updateJSON();
        }
        imageModal.hide();
      });
      imgBtn.addEventListener('click', () => imageModal.show());
    }

    if (vidBtn) {
      const videoModal = new bootstrap.Modal(videoModalEl);
      const videoInput = videoModalEl.querySelector('.video-url');
      videoModalEl.querySelector('.save-video').addEventListener('click', () => {
        const embed = parseYouTube(videoInput.value.trim());
        if (embed) {
          videoHidden.value = embed;
          videoHolder.innerHTML = `<div class="position-relative"><iframe width="250" height="140" src="${embed}" allowfullscreen></iframe><button type="button" class="btn btn-link p-0 mt-1 expand-video">Expandir</button></div>`;
          updateJSON();
          const expandBtn = videoHolder.querySelector('.expand-video');
          expandBtn.addEventListener('click', () => {
            const expandModalEl = document.createElement('div');
            expandModalEl.className = 'modal fade';
            expandModalEl.innerHTML = `<div class=\"modal-dialog modal-lg\"><div class=\"modal-content\"><div class=\"modal-body p-0\"><iframe width=\"100%\" height=\"400\" src=\"${embed}\" allowfullscreen></iframe></div></div></div>`;
            document.body.appendChild(expandModalEl);
            const expandModal = new bootstrap.Modal(expandModalEl);
            expandModal.show();
            expandModalEl.addEventListener('hidden.bs.modal', () => expandModalEl.remove());
          });
        }
        videoModal.hide();
      });
      vidBtn.addEventListener('click', () => videoModal.show());
    }

    // Prefill data if editing existing structure
    tipoSelect.value = data.tipo || tipo || 'text';
    labelInput.value = data.label || data.titulo || '';
    div.querySelector('.field-obrigatoria').checked = data.obrigatoria || data.obrigatorio || false;
    div.querySelector('.field-subtitulo').value = data.subtitulo || '';
    midiaHidden.value = data.midia_url || '';
    if (data.midia_url) {
      imageHolder.innerHTML = `<img src="${data.midia_url}" class="img-fluid" style="max-width:200px;">`;
    }
    videoHidden.value = data.video_url || '';
    if (data.video_url) {
      videoHolder.innerHTML = `<div class="position-relative"><iframe width="250" height="140" src="${data.video_url}" allowfullscreen></iframe><button type="button" class="btn btn-link p-0 mt-1 expand-video">Expandir</button></div>`;
      const expandBtn = videoHolder.querySelector('.expand-video');
      expandBtn.addEventListener('click', () => {
        const expandModalEl = document.createElement('div');
        expandModalEl.className = 'modal fade';
        expandModalEl.innerHTML = `<div class=\"modal-dialog modal-lg\"><div class=\"modal-content\"><div class=\"modal-body p-0\"><iframe width=\"100%\" height=\"400\" src=\"${data.video_url}\" allowfullscreen></iframe></div></div></div>`;
        document.body.appendChild(expandModalEl);
        const expandModal = new bootstrap.Modal(expandModalEl);
        expandModal.show();
        expandModalEl.addEventListener('hidden.bs.modal', () => expandModalEl.remove());
      });
    }
    div.querySelector('.field-outra').checked = data.temOpcaoOutra || false;
    div.querySelector('.field-multipla').checked = data.permiteMultiplaEscolha || false;
    div.querySelector('.field-menu-suspenso').checked = data.usarMenuSuspenso || false;
    div.querySelector('.field-embaralhar').checked = data.embaralharOpcoes || false;
    div.querySelector('.field-ramificacoes').value = data.ramificacoes ? JSON.stringify(data.ramificacoes) : '';
    if (['select', 'option'].includes(tipoSelect.value)) {
      opcoesWrapper.classList.remove('d-none');
      div.querySelector('.field-opcoes').value = (data.opcoes || []).join(', ');
      if (tipoSelect.value === 'option') {
        outraWrapper.classList.remove('d-none');
        multiplaWrapper.classList.remove('d-none');
        menuSuspensoWrapper.classList.remove('d-none');
        embaralharWrapper.classList.remove('d-none');
        ramificacoesWrapper.classList.remove('d-none');
      }
    }
    if (tipoSelect.value === 'likert') {
      likertWrapper.classList.remove('d-none');
      div.querySelector('.field-likert-linhas').value = (data.linhas || []).join(', ');
      div.querySelector('.field-likert-colunas').value = (data.colunas || []).join(', ');
    } else if (tipoSelect.value === 'table') {
      tableWrapper.classList.remove('d-none');
      div.querySelector('.field-table-rows').value = data.linhas || 1;
      div.querySelector('.field-table-cabecalhos').value = (data.opcoes || []).join(', ');
    } else if (tipoSelect.value === 'section') {
      obrigatoriaWrapper.classList.add('d-none');
      subtituloWrapper.classList.add('d-none');
      sectionSubtitleWrapper.classList.remove('d-none');
      labelInput.placeholder = 'Insira o seu título aqui';
      div.querySelector('.field-subtitulo').value = data.subtitulo || '';
      div.classList.add('section-card');
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
      parsed.forEach(f => {
        if (f.tipo === 'section') {
          const secData = { ...f };
          delete secData.campos;
          addField('section', secData);
          (f.campos || []).forEach(c => addField(c.tipo, c));
        } else {
          addField(f.tipo, f);
        }
      });
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

