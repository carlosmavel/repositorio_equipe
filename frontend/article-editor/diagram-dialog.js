import { diagramTitleForm, titleFromForm } from '../diagram-ui/title-form.js';

const jsonHeaders = { Accept: 'application/json', 'Content-Type': 'application/json' };

async function requestJson(url, options = {}) {
  const response = await fetch(url, { headers: { Accept: 'application/json', ...(options.headers || {}) }, ...options });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || 'Não foi possível concluir a operação.');
  return payload;
}

/** Fluxo modal autocontido para inserir diagramas no editor de artigos. */
export class DiagramInsertionDialog {
  constructor({ onInsert }) {
    this.onInsert = onInsert;
    this.page = 1;
    this.mode = null;
    this.selected = null;
    this.insertionPosition = null;
    this.dialog = this.build();
    document.body.appendChild(this.dialog);
  }

  build() {
    const dialog = document.createElement('dialog');
    dialog.className = 'diagram-picker';
    dialog.setAttribute('aria-labelledby', 'diagram-picker-title');
    dialog.innerHTML = `
      <div class="diagram-picker__shell">
        <header class="diagram-picker__header">
          <div><h2 id="diagram-picker-title" class="h5 mb-1">Inserir diagrama</h2><p class="text-body-secondary mb-0">Crie, vincule ou reutilize um modelo.</p></div>
          <button type="button" class="btn-close" data-action="close" aria-label="Fechar"></button>
        </header>
        <div class="diagram-picker__body">
          <div class="diagram-picker__options" role="list" aria-label="Opções de inserção"></div>
          <section class="diagram-picker__panel" aria-live="polite"></section>
        </div>
      </div>`;
    dialog.addEventListener('cancel', () => this.close());
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog || event.target.closest('[data-action="close"]')) this.close();
    });
    return dialog;
  }

  async open(position) {
    this.insertionPosition = position;
    this.mode = null;
    this.selected = null;
    this.dialog.showModal();
    this.renderOptions(null, true);
    try {
      this.capabilities = await requestJson('/api/diagramas/capabilities');
      this.renderOptions();
      this.dialog.querySelector('[data-mode]:not(:disabled)')?.focus();
    } catch (error) {
      this.renderOptions(error);
    }
  }

  close() {
    this.dialog.close();
    this.insertionPosition = null;
  }

  renderOptions(error = null, loading = false) {
    const region = this.dialog.querySelector('.diagram-picker__options');
    if (loading) {
      region.innerHTML = '<p class="diagram-picker__status" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Carregando opções…</p>';
      return;
    }
    if (error) {
      region.innerHTML = `<div class="alert alert-danger mb-0" role="alert"><p class="mb-2">${this.escape(error.message)}</p><button type="button" class="btn btn-sm btn-outline-danger" data-retry-options>Tentar novamente</button></div>`;
      region.querySelector('[data-retry-options]').onclick = () => this.openCapabilities();
      return;
    }
    const options = [
      ['new', 'Criar novo', 'Comece com um diagrama em branco.', this.capabilities.can_create, this.capabilities.create_reason],
      ['existing', 'Vincular existente', 'Pesquise diagramas comuns acessíveis.', this.capabilities.can_link, this.capabilities.link_reason],
      ['template', 'Criar a partir de modelo', 'Visualize um modelo e crie uma cópia.', this.capabilities.can_copy_template, this.capabilities.copy_reason]
    ];
    region.innerHTML = options.map(([mode, title, description, enabled, reason]) => `
      <button type="button" class="diagram-picker__option" data-mode="${mode}" ${enabled ? '' : 'disabled'} aria-describedby="diagram-option-${mode}-help">
        <strong>${title}</strong><span id="diagram-option-${mode}-help">${enabled ? description : this.escape(reason || 'Opção indisponível para seu perfil.')}</span>
      </button>`).join('');
    region.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => this.selectMode(button.dataset.mode)));
  }

  async openCapabilities() {
    this.renderOptions(null, true);
    try { this.capabilities = await requestJson('/api/diagramas/capabilities'); this.renderOptions(); }
    catch (error) { this.renderOptions(error); }
  }

  selectMode(mode) {
    this.mode = mode;
    this.selected = null;
    if (mode === 'new') this.renderTitleForm('Título do novo diagrama', 'Criar e inserir', (title) => this.create(title));
    else { this.page = 1; this.renderBrowser(); }
  }

  renderTitleForm(label, submitLabel, submit, initial = '') {
    const panel = this.dialog.querySelector('.diagram-picker__panel');
    panel.innerHTML = diagramTitleForm({ inputId: 'diagram-picker-name', label, submitLabel, initial, cancelLabel: 'Voltar' });
    panel.querySelector('[data-action="cancel-title"]').onclick = () => { this.selected = null; this.renderOptions(); panel.innerHTML = ''; };
    panel.querySelector('form').onsubmit = async (event) => {
      event.preventDefault();
      const title = titleFromForm(event.currentTarget);
      if (!title) return;
      await this.withSubmission(event.currentTarget, () => submit(title));
    };
    panel.querySelector('input').focus();
  }

  async withSubmission(form, operation) {
    const submit = form.querySelector('[type="submit"]');
    const feedback = form.querySelector('.diagram-picker__feedback');
    submit.disabled = true;
    feedback.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Processando…';
    try { await operation(); }
    catch (error) { feedback.textContent = error.message; feedback.classList.add('text-danger'); submit.disabled = false; }
  }

  async create(title) {
    const diagram = await requestJson('/api/diagramas', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ title }) });
    this.complete(diagram);
  }

  async renderBrowser() {
    const panel = this.dialog.querySelector('.diagram-picker__panel');
    panel.innerHTML = `<form class="diagram-picker__search" role="search"><label class="visually-hidden" for="diagram-picker-search">Buscar por nome</label><input id="diagram-picker-search" class="form-control" type="search" placeholder="Buscar por nome"><button class="btn btn-outline-primary" type="submit">Buscar</button></form><div class="diagram-picker__results" aria-live="polite"></div>`;
    panel.querySelector('form').onsubmit = (event) => { event.preventDefault(); this.page = 1; this.loadList(); };
    await this.loadList();
  }

  async loadList() {
    const results = this.dialog.querySelector('.diagram-picker__results');
    const query = this.dialog.querySelector('#diagram-picker-search')?.value.trim() || '';
    results.innerHTML = '<p class="diagram-picker__status" role="status"><span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Carregando…</p>';
    const type = this.mode === 'template' ? 'modelo' : 'diagrama';
    try {
      const data = await requestJson(`/api/diagramas/metadados?tipo=${type}&q=${encodeURIComponent(query)}&page=${this.page}&per_page=8`);
      if (!data.items.length) {
        results.innerHTML = `<div class="diagram-picker__empty"><p>Nenhum ${type} encontrado.</p><button class="btn btn-sm btn-outline-primary" data-retry-list>Tentar novamente</button></div>`;
      } else {
        results.innerHTML = `<div class="diagram-picker__grid">${data.items.map(item => this.card(item)).join('')}</div>${this.pagination(data)}`;
      }
      results.querySelector('[data-retry-list]')?.addEventListener('click', () => this.loadList());
      results.querySelectorAll('[data-diagram-id]').forEach(button => button.onclick = () => this.choose(data.items.find(item => item.id === button.dataset.diagramId)));
      results.querySelectorAll('[data-page]').forEach(button => button.onclick = () => { this.page = Number(button.dataset.page); this.loadList(); });
    } catch (error) {
      results.innerHTML = `<div class="alert alert-danger" role="alert"><p>${this.escape(error.message)}</p><button class="btn btn-sm btn-outline-danger" data-retry-list>Tentar novamente</button></div>`;
      results.querySelector('[data-retry-list]').onclick = () => this.loadList();
    }
  }

  card(item) {
    return `<button type="button" class="diagram-picker__card" data-diagram-id="${item.id}"><span class="diagram-picker__thumb">${item.preview_url ? `<img src="${this.escape(item.preview_url)}" alt="Preview de ${this.escape(item.title)}" loading="lazy">` : '<span>Sem preview</span>'}</span><strong>${this.escape(item.title)}</strong></button>`;
  }

  pagination(data) {
    if (data.pages < 2) return '';
    return `<nav class="diagram-picker__pagination" aria-label="Paginação dos diagramas"><button class="btn btn-sm btn-outline-secondary" data-page="${data.page - 1}" ${data.page <= 1 ? 'disabled' : ''}>Anterior</button><span>Página ${data.page} de ${data.pages}</span><button class="btn btn-sm btn-outline-secondary" data-page="${data.page + 1}" ${data.page >= data.pages ? 'disabled' : ''}>Próxima</button></nav>`;
  }

  choose(item) {
    this.selected = item;
    if (this.mode === 'existing') return this.complete(item);
    this.renderTitleForm('Título da cópia', 'Copiar e inserir', (title) => this.copy(title), item.title);
  }

  async copy(title) {
    const diagram = await requestJson(`/api/diagramas/${this.selected.id}/copiar`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ title }) });
    this.complete(diagram);
  }

  complete(diagram) {
    this.onInsert(diagram.id, this.insertionPosition);
    const panel = this.dialog.querySelector('.diagram-picker__panel');
    const editAction = diagram.editor_url
      ? `<a class="btn btn-primary" href="${this.escape(diagram.editor_url)}" target="_blank" rel="noopener">Editar agora</a>`
      : '';
    panel.innerHTML = `<div class="alert alert-success mb-0" role="status"><h3 class="h6">Diagrama inserido</h3><p>A referência foi adicionada ao artigo.</p><div class="d-flex gap-2">${editAction}<button type="button" class="btn btn-outline-secondary" data-action="close">Continuar no artigo</button></div></div>`;
  }

  escape(value) {
    const node = document.createElement('span');
    node.textContent = String(value ?? '');
    return node.innerHTML;
  }
}
