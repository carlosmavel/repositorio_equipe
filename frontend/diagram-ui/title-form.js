/** Formulário de título compartilhado pelos fluxos de criação de diagramas. */
export function diagramTitleForm({
  inputId = 'diagram-title',
  label = 'Título do novo diagrama',
  submitLabel = 'Criar diagrama',
  initial = '',
  cancelLabel = null,
} = {}) {
  const cancel = cancelLabel
    ? `<button type="button" class="btn btn-outline-secondary" data-action="cancel-title">${escapeHtml(cancelLabel)}</button>`
    : '';
  return `<form class="diagram-title-form" novalidate>
    <label class="form-label" for="${escapeHtml(inputId)}">${escapeHtml(label)}</label>
    <input id="${escapeHtml(inputId)}" class="form-control" name="title" maxlength="200" required autocomplete="off" value="${escapeHtml(initial)}" aria-describedby="${escapeHtml(inputId)}-help ${escapeHtml(inputId)}-feedback">
    <div id="${escapeHtml(inputId)}-help" class="form-text">O diagrama será privado e poderá ser vinculado a um artigo depois.</div>
    <div id="${escapeHtml(inputId)}-feedback" class="diagram-picker__feedback mt-2" aria-live="assertive"></div>
    <div class="d-flex flex-column-reverse flex-sm-row gap-2 justify-content-end mt-3">${cancel}<button class="btn btn-primary" type="submit">${escapeHtml(submitLabel)}</button></div>
  </form>`;
}

export function titleFromForm(form) {
  const input = form.elements.title;
  const title = input.value.trim();
  input.value = title;
  if (!title) {
    input.setCustomValidity('Informe um título para o diagrama.');
    input.reportValidity();
    input.focus();
    return null;
  }
  input.setCustomValidity('');
  return title;
}

export function escapeHtml(value) {
  const node = document.createElement('span');
  node.textContent = String(value ?? '');
  return node.innerHTML;
}
