import { Node, mergeAttributes } from '@tiptap/core';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const ArticleDiagram = Node.create({
  name: 'articleDiagram',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,

  addOptions() {
    return {
      metadataUrl: diagramId => `/api/diagramas/${diagramId}/metadados`,
      onOpenDiagram: null
    };
  },

  addAttributes() {
    return {
      diagramId: {
        default: null,
        parseHTML: element => element.getAttribute('data-diagram-id'),
        renderHTML: attributes => ({ 'data-diagram-id': attributes.diagramId })
      }
    };
  },

  parseHTML() {
    return [{ tag: 'figure[data-article-diagram][data-diagram-id]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return ['figure', mergeAttributes(HTMLAttributes, { 'data-article-diagram': 'true' })];
  },

  addCommands() {
    return {
      insertArticleDiagram: ({ diagramId, position } = {}) => ({ commands }) => {
        if (!UUID_PATTERN.test(diagramId || '')) return false;
        const node = { type: this.name, attrs: { diagramId } };
        return Number.isInteger(position)
          ? commands.insertContentAt(position, node)
          : commands.insertContent(node);
      }
    };
  },

  addNodeView() {
    return ({ node, editor, getPos }) => {
      const dom = document.createElement('figure');
      dom.dataset.articleDiagram = 'true';
      dom.dataset.diagramId = node.attrs.diagramId;
      dom.className = 'article-diagram article-diagram--loading';
      dom.setAttribute('aria-busy', 'true');

      const title = document.createElement('figcaption');
      title.className = 'article-diagram__title placeholder-glow';
      title.innerHTML = '<span class="placeholder col-6">Carregando diagrama</span>';
      const viewport = document.createElement('div');
      viewport.className = 'article-diagram__viewport';
      viewport.innerHTML = '<span class="article-diagram__state" role="status">Carregando preview…</span>';
      const actions = document.createElement('div');
      actions.className = 'article-diagram__actions';
      dom.replaceChildren(title, viewport, actions);

      const stopEditorEvent = event => event.stopPropagation();
      const selectAndOpen = (trigger, mode = 'view') => {
        const position = getPos();
        if (Number.isInteger(position)) editor.commands.setNodeSelection(position);
        trigger.focus({ preventScroll: true });
        this.options.onOpenDiagram?.(node.attrs.diagramId, trigger, { mode });
      };
      const makeAction = (label, style, mode) => {
        const action = document.createElement('button');
        action.type = 'button';
        action.className = `btn btn-sm ${style} article-diagram__action`;
        action.textContent = label;
        action.addEventListener('pointerdown', stopEditorEvent);
        action.addEventListener('click', event => {
          stopEditorEvent(event);
          selectAndOpen(action, mode);
        });
        return action;
      };

      // O NodeView busca apenas metadados e a URL autorizada do preview.
      fetch(this.options.metadataUrl(node.attrs.diagramId), {
        credentials: 'same-origin', headers: { Accept: 'application/json' }
      }).then(response => {
        if (!response.ok) throw new Error('Diagrama indisponível');
        return response.json();
      }).then(metadata => {
        const diagramTitle = metadata.title || 'Diagrama sem título';
        title.className = 'article-diagram__title';
        title.textContent = diagramTitle;
        actions.replaceChildren();

        if (metadata.can_view && this.options.onOpenDiagram) {
          const view = makeAction('Visualizar diagrama', 'btn-outline-primary', 'view');
          view.setAttribute('aria-label', `Visualizar diagrama: ${diagramTitle}`);
          actions.append(view);
          if (metadata.can_edit) {
            const edit = makeAction('Editar', 'btn-primary', 'edit');
            edit.setAttribute('aria-label', `Editar diagrama: ${diagramTitle}`);
            actions.append(edit);
          }
        }

        if (metadata.preview_state === 'missing' || !metadata.preview_url) {
          viewport.innerHTML = '<span class="article-diagram__state" role="status">Preview ainda não disponível</span>';
        } else {
          const preview = document.createElement('button');
          preview.type = 'button';
          preview.className = 'article-diagram__preview';
          preview.setAttribute('aria-label', `Visualizar diagrama: ${diagramTitle}`);
          const image = document.createElement('img');
          image.src = metadata.preview_url;
          image.alt = `Preview do diagrama ${diagramTitle}`;
          image.loading = 'lazy';
          image.addEventListener('error', () => {
            viewport.classList.add('article-diagram__viewport--error');
            viewport.innerHTML = '<span class="article-diagram__state" role="alert">Falha ao carregar o preview</span>';
          }, { once: true });
          preview.append(image);
          preview.addEventListener('pointerdown', stopEditorEvent);
          preview.addEventListener('click', event => {
            stopEditorEvent(event);
            selectAndOpen(preview, 'view');
          });
          viewport.replaceChildren(preview);
        }
        dom.classList.remove('article-diagram--loading');
        dom.removeAttribute('aria-busy');
      }).catch(() => {
        dom.classList.remove('article-diagram--loading');
        dom.classList.add('article-diagram--unavailable');
        dom.removeAttribute('aria-busy');
        title.className = 'article-diagram__title';
        title.textContent = 'Diagrama';
        viewport.innerHTML = '<span class="article-diagram__state" role="alert">Diagrama indisponível</span>';
        actions.replaceChildren();
      });

      return {
        dom,
        // Ações não movem a seleção nem iniciam o drag; o restante do card
        // continua selecionável e arrastável pelo Tiptap.
        stopEvent: event => Boolean(event.target.closest?.('.article-diagram__actions, .article-diagram__preview')),
      };
    };
  }
});

export default ArticleDiagram;
