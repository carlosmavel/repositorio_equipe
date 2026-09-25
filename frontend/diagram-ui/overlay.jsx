import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { DiagramWorkspace } from '../diagram-editor/index.jsx';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';
let activeOverlay = null;

function DiagramOverlay({ metadata, onClosed }) {
  const dialogRef = useRef(null);
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState(metadata.can_edit ? 'Carregando...' : '');
  const [confirmClose, setConfirmClose] = useState(false);
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
          <DiagramWorkspace
            mode={metadata.can_edit ? 'edit' : 'view'} canEdit={metadata.can_edit}
            title={metadata.title} lockVersion={metadata.lock_version}
            sceneUrl={metadata.scene_url} saveUrl={metadata.save_url}
            previewUrl={metadata.preview_url} excalidrawVersion="0.18.0"
            onDirtyChange={setDirty} onStatusChange={setStatus}
          />
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
