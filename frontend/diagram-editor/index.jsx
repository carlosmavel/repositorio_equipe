import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Excalidraw,
  exportToBlob,
} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';

const STATUS = {
  clean: '✓ Salvo',
  dirty: 'Alterações não salvas',
  loading: 'Carregando...',
  saving: 'Salvando...',
};

function versionedPreviewUrl(url, version) {
  if (!url || version === undefined || version === null) return url || null;
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}v=${encodeURIComponent(version)}`;
}

/**
 * Editor reutilizável de diagramas. Toda informação da montagem é recebida
 * por props, para que instâncias fullscreen, standalone e embutidas sejam isoladas.
 */
export function DiagramWorkspace({
  mode = 'edit',
  canEdit = true,
  title = '',
  lockVersion: initialLockVersion,
  sceneUrl,
  saveUrl,
  previewUrl,
  excalidrawVersion,
  loadScene,
  saveScene,
  transport = globalThis.OrquetaskDiagramSave,
  onSaved,
  onDirtyChange,
  onStatusChange,
  onReady,
  onRequestClose,
}) {
  const apiRef = useRef(null);
  const filesRef = useRef({});
  const initializedRef = useRef(false);
  const savedFingerprintRef = useRef(null);
  const latestFingerprintRef = useRef(null);
  const savingRef = useRef(false);
  const callbacksRef = useRef({ onSaved, onDirtyChange, onStatusChange, onReady });
  callbacksRef.current = { onSaved, onDirtyChange, onStatusChange, onReady };

  const [initialData, setInitialData] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [status, setStatusValue] = useState(STATUS.loading);
  const [isSaving, setIsSaving] = useState(false);
  const [lockVersion, setLockVersion] = useState(initialLockVersion);
  const editable = mode === 'edit' && canEdit;

  const setStatus = useCallback((value) => {
    setStatusValue(value);
    callbacksRef.current.onStatusChange?.(value);
  }, []);

  const reportDirty = useCallback((dirty) => {
    callbacksRef.current.onDirtyChange?.(dirty);
  }, []);

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
    setStatus(STATUS.loading);
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
      if (!editable) setStatus('');
    }).catch((error) => {
      if (!active) return;
      const message = error.message || 'Não foi possível carregar o diagrama.';
      setLoadError(message);
      setStatus(`Falha ao carregar: ${message}`);
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
      setStatus(STATUS.clean);
      return;
    }
    const dirty = fingerprint !== savedFingerprintRef.current;
    reportDirty(dirty);
    if (!savingRef.current) setStatus(dirty ? STATUS.dirty : STATUS.clean);
  }, [reportDirty, setStatus, transport]);

  const save = useCallback(async () => {
    const api = apiRef.current;
    if (!editable || !api || savingRef.current) return;
    savingRef.current = true;
    setIsSaving(true);
    setStatus('Salvando...');
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
      setStatus(dirty ? STATUS.dirty : STATUS.clean);
      const saved = {
        ...result,
        uuid: result.uuid || result.id,
        current_version: result.current_version,
        lock_version: result.lock_version,
        preview_token: result.preview_token || result.previewToken || null,
        preview_url: result.preview_url || versionedPreviewUrl(previewUrl, result.current_version),
      };
      callbacksRef.current.onSaved?.(saved);
    } catch (error) {
      setStatus(`Falha ao salvar: ${error.message || 'Não foi possível salvar o diagrama.'} Alterações não salvas.`);
      reportDirty(true);
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  }, [editable, excalidrawVersion, lockVersion, previewUrl, reportDirty, saveScene,
    saveUrl, setStatus, title, transport]);

  return (
    <div className="diagram-workspace" data-mode={editable ? 'edit' : 'view'}>
      <div className="d-flex align-items-center gap-3 mb-2">
        {editable && <button className="btn btn-primary" type="button" onClick={save} disabled={isSaving}>Salvar diagrama</button>}
        {onRequestClose && <button className="btn btn-outline-secondary" type="button" onClick={onRequestClose}>Fechar</button>}
        <span role="status" aria-live="polite">{status}</span>
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
            onChange={editable ? onChange : undefined}
            viewModeEnabled={!editable}
          />
        </div>
      ) : null}
    </div>
  );
}

export default DiagramWorkspace;
