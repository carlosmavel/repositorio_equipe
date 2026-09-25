import { diagramTitleForm, titleFromForm } from '../diagram-ui/title-form.js';

const dialog = document.querySelector('#create-diagram-dialog');
const openers = document.querySelectorAll('[data-create-diagram]');

if (dialog && openers.length) {
  const panel = dialog.querySelector('[data-title-form]');

  const render = () => {
    panel.innerHTML = diagramTitleForm({
      inputId: 'standalone-diagram-title',
      submitLabel: 'Criar e editar',
      cancelLabel: 'Cancelar',
    });
    const form = panel.querySelector('form');
    form.querySelector('[data-action="cancel-title"]').onclick = () => dialog.close();
    form.onsubmit = async event => {
      event.preventDefault();
      const title = titleFromForm(form);
      if (!title) return;
      const submit = form.querySelector('[type="submit"]');
      const feedback = form.querySelector('.diagram-picker__feedback');
      submit.disabled = true;
      feedback.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Criando diagrama…';
      try {
        const response = await fetch('/api/diagramas', {
          method: 'POST',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify({ title }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || 'Não foi possível criar o diagrama.');
        window.location.assign(payload.editor_url || `/diagramas/${payload.id}`);
      } catch (error) {
        feedback.textContent = error.message;
        feedback.classList.add('text-danger');
        submit.disabled = false;
        form.elements.title.focus();
      }
    };
  };

  openers.forEach(button => button.addEventListener('click', () => {
    render();
    dialog.showModal();
    panel.querySelector('input').focus();
  }));
  dialog.addEventListener('cancel', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
}
