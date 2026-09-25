import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { DiagramWorkspace } from '../diagram-editor/index.jsx';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
let activeOverlay = null;

class SceneErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() { return { failed: true }; }

  componentDidCatch(error) { this.props.onError?.(error); }

  render() { return this.state.failed ? null : this.props.children; }
}

export function RasterDiagramViewer({ src, title, onStatusChange }) {
  const viewportRef = useRef(null);
  const imageRef = useRef(null);
  const dragRef = useRef(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [loaded, setLoaded] = useState(false);

  const fit = useCallback(() => {
    const viewport = viewportRef.current;
    const image = imageRef.current;
    if (!viewport || !image?.naturalWidth || !image?.naturalHeight) return;
    const next = Math.min(
      viewport.clientWidth / image.naturalWidth,
      viewport.clientHeight / image.naturalHeight,
      1,
    ) * .94;
    setScale(Math.max(next, .05));
    setOffset({ x: 0, y: 0 });
    onStatusChange?.(`Ajustado à tela: ${Math.round(Math.max(next, .05) * 100)}%`);
  }, [onStatusChange]);

  const zoom = useCallback((factor) => {
    setScale(value => Math.min(8, Math.max(.05, value * factor)));
  }, []);

  useEffect(() => {
    if (!loaded) return undefined;
    fit();
    const observer = new ResizeObserver(fit);
    observer.observe(viewportRef.current);
    return () => observer.disconnect();
  }, [fit, loaded]);

  const onKeyDown = (event) => {
    if (event.key === '+' || event.key === '=') { event.preventDefault(); zoom(1.2); }
    if (event.key === '-') { event.preventDefault(); zoom(1 / 1.2); }
    if (event.key === '0') { event.preventDefault(); fit(); }
    const step = event.shiftKey ? 80 : 30;
    const movement = { ArrowLeft: [step, 0], ArrowRight: [-step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[event.key];
    if (movement) {
      event.preventDefault();
      setOffset(value => ({ x: value.x + movement[0], y: value.y + movement[1] }));
    }
  };

  return <div className="diagram-raster" data-testid="diagram-raster-viewer">
    <div className="diagram-raster__controls" role="toolbar" aria-label="Controles do diagrama">
      <button type="button" className="btn btn-outline-secondary" onClick={() => zoom(1 / 1.2)} aria-label="Diminuir zoom">−</button>
      <output aria-live="polite">{Math.round(scale * 100)}%</output>
      <button type="button" className="btn btn-outline-secondary" onClick={() => zoom(1.2)} aria-label="Aumentar zoom">+</button>
      <button type="button" className="btn btn-outline-secondary" onClick={fit}>Ajustar à tela</button>
    </div>
    <div ref={viewportRef} className="diagram-raster__viewport" tabIndex="0" onKeyDown={onKeyDown}
      aria-label="Diagrama. Use roda ou mais e menos para zoom; arraste ou use as setas para deslocar."
      onWheel={(event) => { event.preventDefault(); zoom(event.deltaY < 0 ? 1.12 : 1 / 1.12); }}
      onPointerDown={(event) => {
        event.currentTarget.setPointerCapture(event.pointerId);
        dragRef.current = { x: event.clientX, y: event.clientY, offset };
      }}
      onPointerMove={(event) => {
        if (!dragRef.current) return;
        setOffset({ x: dragRef.current.offset.x + event.clientX - dragRef.current.x, y: dragRef.current.offset.y + event.clientY - dragRef.current.y });
      }}
      onPointerUp={(event) => { dragRef.current = null; event.currentTarget.releasePointerCapture(event.pointerId); }}>
      <img ref={imageRef} src={src} alt={title || 'Diagrama'} draggable="false"
        onLoad={() => { setLoaded(true); onStatusChange?.('Preview carregado'); }}
        style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }} />
    </div>
  </div>;
}

function DiagramOverlay({ metadata, onClosed }) {
  const dialogRef = useRef(null);
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState(metadata.can_edit ? 'Carregando...' : '');
  const [confirmClose, setConfirmClose] = useState(false);
  const [useRaster, setUseRaster] = useState(!metadata.can_open_scene || !metadata.scene_url);
  const titleId = useId();
  const descriptionId = useId();

  const requestClose = useCallback(() => {
    if (dirty) {
      setConfirmClose(true);
      return;
    }
    onClosed();
  }, [dirty, onClosed]);

  useEffect(() => {
    dialogRef.current?.querySelector('[data-diagram-overlay-close]')?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        if (confirmClose) setConfirmClose(false);
        else requestClose();
        return;
      }
      const dialog = dialogRef.current;
      if (event.key !== 'Tab' || !dialog) return;
      const focusScope = confirmClose ? dialog.querySelector('.diagram-overlay__confirm') : dialog;
      const items = Array.from(focusScope.querySelectorAll(FOCUSABLE)).filter((item) => item.getClientRects().length);
      if (!items.length) {
        event.preventDefault();
        focusScope.focus();
      } else if (event.shiftKey && document.activeElement === items[0]) {
        event.preventDefault();
        items.at(-1).focus();
      } else if (!event.shiftKey && document.activeElement === items.at(-1)) {
        event.preventDefault();
        items[0].focus();
      }
    };
    document.addEventListener('keydown', onKeyDown, true);
    return () => document.removeEventListener('keydown', onKeyDown, true);
  }, [confirmClose, requestClose]);

  return (
    <div className="diagram-overlay" role="presentation">
      <section ref={dialogRef} className="diagram-overlay__dialog" role="dialog" aria-modal="true"
        aria-labelledby={titleId} aria-describedby={descriptionId} tabIndex="-1">
        <header className="diagram-overlay__header">
          <div className="diagram-overlay__heading">
            <h1 id={titleId} className="diagram-overlay__title">{metadata.title || 'Diagrama'}</h1>
            <p id={descriptionId} className="visually-hidden">
              {metadata.can_edit ? 'Editor de diagrama em tela cheia.' : 'Visualizador de diagrama em tela cheia.'}
            </p>
            <span className="diagram-overlay__state" role="status" aria-live="polite">{status}</span>
          </div>
          <div className="diagram-overlay__actions">
            <span className="badge text-bg-secondary">{metadata.can_edit ? 'Edição' : 'Somente leitura'}</span>
            <button type="button" className="btn btn-outline-secondary" data-diagram-overlay-close onClick={requestClose}
              aria-label={`Fechar ${metadata.title || 'diagrama'}`}>
              <i className="bi bi-x-lg" aria-hidden="true" /> <span className="d-none d-sm-inline">Fechar</span>
            </button>
          </div>
        </header>
        <main className="diagram-overlay__body">
          {useRaster ? <RasterDiagramViewer src={metadata.preview_url} title={metadata.title} onStatusChange={setStatus} /> : <SceneErrorBoundary onError={() => setUseRaster(true)}><DiagramWorkspace
            mode={metadata.can_edit ? 'edit' : 'view'} canEdit={metadata.can_edit}
            title={metadata.title} lockVersion={metadata.lock_version}
            sceneUrl={metadata.scene_url} saveUrl={metadata.save_url}
            previewUrl={metadata.preview_url} excalidrawVersion="0.18.0"
            onDirtyChange={setDirty} onStatusChange={setStatus}
            onLoadError={() => setUseRaster(true)}
          /></SceneErrorBoundary>}
        </main>
        {confirmClose && (
          <div className="diagram-overlay__confirm" role="alertdialog" aria-modal="true"
            aria-labelledby={`${titleId}-confirm`} aria-describedby={`${descriptionId}-confirm`}>
            <div className="diagram-overlay__confirm-card shadow-lg">
              <h2 id={`${titleId}-confirm`} className="h5">Descartar alterações?</h2>
              <p id={`${descriptionId}-confirm`}>O diagrama possui alterações que ainda não foram salvas.</p>
              <div className="d-flex flex-wrap justify-content-end gap-2">
                <button type="button" className="btn btn-secondary" autoFocus onClick={() => setConfirmClose(false)}>Continuar editando</button>
                <button type="button" className="btn btn-danger" onClick={onClosed}>Descartar e fechar</button>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

/** Monta uma única instância efêmera sem desmontar ou alterar o editor do artigo. */
export function openDiagramOverlay(metadata, trigger = document.activeElement) {
  activeOverlay?.close();
  const host = document.createElement('div');
  host.dataset.diagramOverlayRoot = '';
  document.body.appendChild(host);
  const root = createRoot(host);
  const scrollX = window.scrollX;
  const scrollY = window.scrollY;
  const previousFocus = trigger instanceof HTMLElement ? trigger : document.activeElement;
  const bodyStyle = document.body.getAttribute('style');
  const background = Array.from(document.body.children).filter((element) => element !== host).map((element) => ({
    element, inert: element.inert, ariaHidden: element.getAttribute('aria-hidden'),
  }));
  background.forEach(({ element }) => {
    element.inert = true;
    element.setAttribute('aria-hidden', 'true');
  });
  document.body.style.position = 'fixed';
  document.body.style.inset = `${-scrollY}px 0 0 ${-scrollX}px`;
  document.body.style.width = '100%';
  document.body.classList.add('diagram-overlay-open');

  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    root.unmount();
    host.remove();
    background.forEach(({ element, inert, ariaHidden }) => {
      element.inert = inert;
      if (ariaHidden === null) element.removeAttribute('aria-hidden');
      else element.setAttribute('aria-hidden', ariaHidden);
    });
    document.body.classList.remove('diagram-overlay-open');
    if (bodyStyle === null) document.body.removeAttribute('style');
    else document.body.setAttribute('style', bodyStyle);
    window.scrollTo(scrollX, scrollY);
    if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
    if (activeOverlay?.close === close) activeOverlay = null;
  };
  activeOverlay = { close };
  root.render(<DiagramOverlay metadata={metadata} onClosed={close} />);
  return close;
}
