import { openDiagramOverlay } from '../diagram-ui/overlay.jsx';

async function metadataFor(figure) {
  if (figure._diagramMetadata) return figure._diagramMetadata;
  const response = await fetch(figure.dataset.diagramMetadataUrl, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) throw new Error('Não foi possível carregar o diagrama.');
  figure._diagramMetadata = await response.json();
  return figure._diagramMetadata;
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-diagram-metadata-url]').forEach((figure) => {
    const open = async (trigger) => {
      trigger.disabled = true;
      try {
        const metadata = await metadataFor(figure);
        openDiagramOverlay(metadata.id, trigger, {
          metadataUrl: figure.dataset.diagramMetadataUrl,
          initialMetadata: metadata,
        });
      } catch (error) {
        const image = figure.querySelector('img');
        // O preview já autorizado continua útil mesmo se o contrato/scene falhar.
        if (image?.src) {
          openDiagramOverlay(figure.dataset.diagramId, trigger, { initialMetadata: {
            title: image.alt || 'Diagrama', preview_url: image.src,
            can_view: true, can_edit: false, can_open_scene: false,
          }});
        }
      } finally {
        trigger.disabled = false;
      }
    };
    figure.querySelectorAll('.article-diagram__preview, .article-diagram__action').forEach((trigger) => {
      trigger.addEventListener('click', () => open(trigger));
    });
  });
});
