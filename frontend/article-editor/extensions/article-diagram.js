import { Node, mergeAttributes } from 'https://esm.sh/@tiptap/core@3';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export const ArticleDiagram = Node.create({
  name: 'articleDiagram',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,

  addOptions() {
    return { metadataUrl: diagramId => `/api/diagramas/${diagramId}/metadados` };
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
    return ({ node }) => {
      const dom = document.createElement('figure');
      dom.dataset.articleDiagram = 'true';
      dom.dataset.diagramId = node.attrs.diagramId;
      dom.className = 'article-diagram article-diagram--loading';
      dom.setAttribute('aria-label', 'Carregando diagrama');

      // O NodeView nunca busca o documento editável: apenas este recurso de
      // metadados, que também entrega a URL autorizada do preview.
      fetch(this.options.metadataUrl(node.attrs.diagramId), { headers: { Accept: 'application/json' } })
        .then(response => {
          if (!response.ok) throw new Error('Diagrama indisponível');
          return response.json();
        })
        .then(metadata => {
          const image = document.createElement('img');
          image.src = metadata.preview_url;
          image.alt = metadata.title || 'Diagrama';
          image.loading = 'lazy';
          dom.replaceChildren(image);
          dom.classList.remove('article-diagram--loading');
          dom.setAttribute('aria-label', metadata.title || 'Diagrama');
        })
        .catch(() => {
          dom.classList.remove('article-diagram--loading');
          dom.classList.add('article-diagram--unavailable');
          dom.textContent = 'Diagrama indisponível';
        });

      return { dom };
    };
  }
});

export default ArticleDiagram;
