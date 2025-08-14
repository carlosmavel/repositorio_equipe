// static/js/cargo_graph.js

// Inicializa e controla o grafo de cargos na tela de administração

document.addEventListener('DOMContentLoaded', function () {
  const graphContainer = document.getElementById('cargoGraph');
  if (!graphContainer) return;

  let cy;

  function cssVar(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
  }

  function buildStyle() {
    const text = cssVar('--bs-body-color') || '#333';
    const bg2 = cssVar('--bs-secondary-bg') || '#ddd';
    return [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'text-valign': 'center',
          'text-halign': 'center',
          color: text,
          'background-color': 'data(color)',
          shape: 'data(shape)',
          'font-size': 12,
          width: 'label',
          padding: '6px'
        }
      },
      {
        selector: 'node[type!="cargo"]',
        style: {
          'background-color': bg2,
          shape: 'round-rectangle'
        }
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'target-arrow-shape': 'triangle',
          'line-color': text,
          'target-arrow-color': text,
          width: 2
        }
      },
      {
        selector: 'edge[rel="gestao"]',
        style: {
          'line-style': 'dashed',
          label: 'data(label)',
          'font-size': 10
        }
      }
    ];
  }

  function applyTheme() {
    if (cy) {
      cy.style(buildStyle());
    }
  }

  window.addEventListener('themeChange', applyTheme);

  function initGraph() {
    if (cy) return;
    const elements = window.cargoGraphElements || [];
    cy = cytoscape({
      container: graphContainer,
      elements: elements,
      layout: { name: 'cose', fit: true },
      style: buildStyle()
    });

    cy.on('tap', 'node[type="cargo"]', function (evt) {
      const data = evt.target.data();
      const modalEl = document.getElementById('cargoModal');
      const iframe = document.getElementById('cargoModalFrame');
      const title = document.getElementById('cargoModalLabel');
      if (modalEl && iframe && title) {
        iframe.src = data.url;
        title.textContent = data.label;
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
      }
    });

    cy.on('tap', 'node[type!="cargo"]', function (evt) {
      const node = evt.target;
      const collapsed = node.data('collapsed');
      const descendants = node.successors();
      descendants.style('display', collapsed ? 'element' : 'none');
      node.data('collapsed', !collapsed);
    });
  }

  document.getElementById('toggleGraph')?.addEventListener('click', () => {
    document.getElementById('cargoContainer').classList.add('d-none');
    document.getElementById('graphContainer').classList.remove('d-none');
    document.getElementById('toggleGraph').classList.add('d-none');
    document.getElementById('toggleTree').classList.remove('d-none');
    initGraph();
  });

  document.getElementById('toggleTree')?.addEventListener('click', () => {
    document.getElementById('graphContainer').classList.add('d-none');
    document.getElementById('cargoContainer').classList.remove('d-none');
    document.getElementById('toggleTree').classList.add('d-none');
    document.getElementById('toggleGraph').classList.remove('d-none');
  });

  const searchInput = document.getElementById('cargoSearch');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      if (!cy) return;
      const term = this.value.toLowerCase();
      cy.nodes('[type="cargo"]').forEach((n) => {
        const match = n.data('label').toLowerCase().includes(term);
        n.style('display', match ? 'element' : 'none');
      });
    });
  }
});
