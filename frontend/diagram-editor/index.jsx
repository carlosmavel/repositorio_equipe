import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import {
  Excalidraw,
  exportToBlob,
} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import diagramTransport from './transport.js';
import { announceDiagramPreviewState, versionDiagramPreviewUrl } from '../diagram-ui/events.js';

const SAVE_STATE = {
  clean: { label: 'Sem alterações', icon: 'bi-check-circle', buttonClass: 'btn-outline-secondary', disabled: true },
  dirty: { label: 'Salvar alterações', icon: 'bi-save', buttonClass: 'btn-primary', disabled: false },
  saving: { label: 'Salvando...', icon: 'bi-cloud-arrow-up', buttonClass: 'btn-primary', disabled: true },
  saved: { label: 'Salvo', icon: 'bi-check-circle-fill', buttonClass: 'btn-success', disabled: true },
  error: { label: 'Falha ao salvar — tentar novamente', icon: 'bi-exclamation-triangle-fill', buttonClass: 'btn-danger', disabled: false },
};

function currentDocumentTheme() {
  return document.documentElement.dataset.bsTheme === 'dark' ? 'dark' : 'light';
}

/**
 * Editor reutilizável de diagramas. Toda informação da montagem é recebida
 * por props, para que instâncias fullscreen, standalone e embutidas sejam isoladas.
 */
export function DiagramWorkspace({
  mode = 'edit',
  canEdit = true,
  title = '',
  diagramId,
  lockVersion: initialLockVersion,
  sceneUrl,
  saveUrl,
  previewUrl,
  excalidrawVersion,
  loadScene,
  saveScene,
  transport = diagramTransport,
  onSaved,
  onDirtyChange,
  onSavingChange,
  onStatusChange,
  onSaveStateChange,
  onReady,
  onRequestClose,
  onLoadError,
}) {
  const apiRef = useRef(null);
  const filesRef = useRef({});
  const initializedRef = useRef(false);
  const savedFingerprintRef = useRef(null);
  const latestFingerprintRef = useRef(null);
  const savingRef = useRef(false);
  const callbacksRef = useRef({ onSaved, onDirtyChange, onSavingChange, onStatusChange, onSaveStateChange, onReady, onLoadError });
  callbacksRef.current = { onSaved, onDirtyChange, onSavingChange, onStatusChange, onSaveStateChange, onReady, onLoadError };

  const [initialData, setInitialData] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [saveState, setSaveStateValue] = useState('clean');
  const [announcement, setAnnouncement] = useState('Carregando...');
  const [theme, setTheme] = useState(currentDocumentTheme);
  const [lockVersion, setLockVersion] = useState(initialLockVersion);
  const saveStatusId = useId();
  const editable = mode === 'edit' && canEdit;

  const setStatus = useCallback((value) => {
    setAnnouncement(value);
    callbacksRef.current.onStatusChange?.(value);
  }, []);

  const setSaveState = useCallback((value) => {
    setSaveStateValue(value);
    const label = SAVE_STATE[value].label;
    setStatus(label);
    callbacksRef.current.onSaveStateChange?.(value);
  }, [setStatus]);

  const reportDirty = useCallback((dirty) => {
    callbacksRef.current.onDirtyChange?.(dirty);
  }, []);

  useEffect(() => {
    const syncTheme = () => setTheme(currentDocumentTheme());
    // main.js applies the persisted global theme before this bundle is mounted.
    syncTheme();
    window.addEventListener('themeChange', syncTheme);
    return () => window.removeEventListener('themeChange', syncTheme);
  }, []);

  useEffect(() => {
    if (!editable) return undefined;
    const warnBeforeUnload = (event) => {
      if (saveState === 'clean' || saveState === 'saved') return;
      event.preventDefault();
      event.returnValue = '';
    };
    window.addEventListener('beforeunload', warnBeforeUnload);
    return () => window.removeEventListener('beforeunload', warnBeforeUnload);
  }, [editable, saveState]);

  useEffect(() => {
    let active = true;
    const requestScene = loadScene || (async () => {
      const response = await fetch(sceneUrl, {
        credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      if (!response.ok) throw new Error('Não foi possível carregar o diagrama.');
      return response.json();
    });

    setLoadError('');
    setStatus('Carregando...');
    Promise.resolve().then(requestScene).then((scene) => {
      if (!active) return;
      const data = {
        elements: scene.elements || [],
        appState: scene.appState || {},
        files: scene.files || {},
        scrollToContent: true,
      };
      filesRef.current = data.files;
      initializedRef.current = false;
      setInitialData(data);
      if (!editable) setStatus('Diagrama carregado');
    }).catch((error) => {
      if (!active) return;
      const message = error.message || 'Não foi possível carregar o diagrama.';
      setLoadError(message);
      setStatus(`Falha ao carregar: ${message}`);
      callbacksRef.current.onLoadError?.(error);
    });
    return () => { active = false; };
  }, [editable, loadScene, sceneUrl, setStatus]);

  const onChange = useCallback((elements, appState, files) => {
    filesRef.current = files || {};
    const fingerprint = transport.sceneFingerprint({ elements, appState, files });
    latestFingerprintRef.current = fingerprint;
    // O primeiro onChange é emitido pelo Excalidraw ao aplicar initialData.
    if (!initializedRef.current) {
      initializedRef.current = true;
      savedFingerprintRef.current = fingerprint;
      reportDirty(false);
      setSaveState('clean');
      return;
    }
    const dirty = fingerprint !== savedFingerprintRef.current;
    reportDirty(dirty);
    if (!savingRef.current) setSaveState(dirty ? 'dirty' : 'clean');
  }, [reportDirty, setSaveState, transport]);

  const save = useCallback(async () => {
    const api = apiRef.current;
    if (!editable || !api || savingRef.current) return;
    savingRef.current = true;
    callbacksRef.current.onSavingChange?.(true);
    setSaveState('saving');
    announceDiagramPreviewState(diagramId, 'generating');
    try {
      const elements = api.getSceneElements();
      const appState = api.getAppState();
      const files = filesRef.current;
      // Capture antes dos awaits: mudanças durante export/upload permanecem dirty.
      const savedFingerprint = transport.sceneFingerprint({ elements, appState, files });
      const preview = await exportToBlob({
        elements,
        appState: { ...appState, exportBackground: true },
        files,
        mimeType: 'image/png',
      });
      let result;
      if (saveScene) {
        result = await saveScene({ elements, appState, files }, {
          title, lockVersion, excalidrawVersion, preview,
        });
      } else {
        const request = await transport.buildRequest(
          { elements, appState, files },
          { title, lockVersion, excalidrawVersion },
          preview,
        );
        const response = await fetch(saveUrl, {
          method: 'PUT', body: request, credentials: 'same-origin',
          headers: { Accept: 'application/json' },
        });
        result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Não foi possível salvar o diagrama.');
      }

      setLockVersion(result.lock_version);
      savedFingerprintRef.current = savedFingerprint;
      const clean = latestFingerprintRef.current === savedFingerprint;
      const dirty = !clean;
      reportDirty(dirty);
      setSaveState(dirty ? 'dirty' : 'saved');
      const saved = {
        ...result,
        uuid: result.uuid || result.id,
        current_version: result.current_version,
        lock_version: result.lock_version,
        preview_token: result.preview_token || result.previewToken || null,
        preview_url: result.preview_url || versionDiagramPreviewUrl(previewUrl, result.current_version),
      };
      callbacksRef.current.onSaved?.(saved);
      announceDiagramPreviewState(saved.uuid || diagramId, saved.preview_state || 'ready');
    } catch (error) {
      setSaveState('error');
      reportDirty(true);
      announceDiagramPreviewState(diagramId, 'failed', 'Não foi possível gerar o preview. Tente novamente.');
    } finally {
      savingRef.current = false;
      callbacksRef.current.onSavingChange?.(false);
    }
  }, [diagramId, editable, excalidrawVersion, lockVersion, previewUrl, reportDirty, saveScene,
    saveUrl, setSaveState, title, transport]);

  const savePresentation = SAVE_STATE[saveState];

  return (
    <div className="diagram-workspace" data-mode={editable ? 'edit' : 'view'}>
      <div className="diagram-save-area d-flex align-items-center gap-3 mb-2" data-save-state={saveState}>
        {editable && <button className={`btn ${savePresentation.buttonClass}`} type="button" onClick={save}
          disabled={savePresentation.disabled} aria-describedby={saveStatusId}>
          <i className={`bi ${savePresentation.icon}`} aria-hidden="true" />{' '}{savePresentation.label}
        </button>}
        {onRequestClose && <button className="btn btn-outline-secondary" type="button" onClick={onRequestClose}>Fechar</button>}
        <span id={saveStatusId} className="diagram-save-status" role="status" aria-live="polite" aria-atomic="true">{announcement}</span>
      </div>
      {loadError ? (
        <div className="alert alert-danger" role="alert">{loadError}</div>
      ) : initialData ? (
        <div className="diagram-canvas">
          <Excalidraw
            excalidrawAPI={(api) => {
              apiRef.current = api;
              callbacksRef.current.onReady?.(api);
            }}
            initialData={initialData}
            theme={theme}
            onChange={editable ? onChange : undefined}
            viewModeEnabled={!editable}
          />
        </div>
      ) : null}
    </div>
  );
}

export default DiagramWorkspace;
