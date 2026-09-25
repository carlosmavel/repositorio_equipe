import React, { useCallback, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Excalidraw,
  exportToBlob,
} from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';

const rootElement = document.getElementById('diagram-editor');
const config = rootElement
  ? JSON.parse(document.getElementById('diagram-editor-config').textContent)
  : null;

function DiagramEditor() {
  const apiRef = useRef(null);
  const filesRef = useRef({});
  const initializedRef = useRef(false);
  const savedFingerprintRef = useRef(null);
  const latestFingerprintRef = useRef(null);
  const savingRef = useRef(false);
  const [status, setStatus] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [lockVersion, setLockVersion] = useState(config.lockVersion);

  const initialDataRef = useRef(fetch(config.sceneUrl, {
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  }).then(async (response) => {
    if (!response.ok) throw new Error('Não foi possível carregar o diagrama.');
    const scene = await response.json();
    filesRef.current = scene.files || {};
    return {
      elements: scene.elements || [],
      appState: scene.appState || {},
      files: scene.files || {},
      scrollToContent: true,
    };
  }));

  const onChange = useCallback((elements, appState, files) => {
    filesRef.current = files;
    const fingerprint = window.OrquetaskDiagramSave.sceneFingerprint({ elements, appState, files });
    latestFingerprintRef.current = fingerprint;
    // Excalidraw emits onChange while applying initialData. That notification is
    // the baseline, not a user edit.
    if (!initializedRef.current) {
      initializedRef.current = true;
      savedFingerprintRef.current = fingerprint;
      return;
    }
    if (!savingRef.current) {
      setStatus(fingerprint === savedFingerprintRef.current ? '✓ Salvo' : 'Alterações não salvas');
    }
  }, []);

  const save = useCallback(async () => {
    const api = apiRef.current;
    if (!api || savingRef.current) return;
    savingRef.current = true;
    setIsSaving(true);
    setStatus('Salvando...');
    try {
      const elements = api.getSceneElements();
      const appState = api.getAppState();
      const files = filesRef.current;
      const savedFingerprint = window.OrquetaskDiagramSave.sceneFingerprint({ elements, appState, files });
      const preview = await exportToBlob({
        elements,
        appState: { ...appState, exportBackground: true },
        files,
        mimeType: 'image/png',
      });
      const request = await window.OrquetaskDiagramSave.buildRequest(
        { elements, appState, files },
        { title: config.title, lockVersion, excalidrawVersion: config.excalidrawVersion },
        preview,
      );
      const response = await fetch(config.saveUrl, {
        method: 'PUT', body: request, credentials: 'same-origin',
        headers: { Accept: 'application/json' },
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Não foi possível salvar o diagrama.');
      setLockVersion(result.lock_version);
      savedFingerprintRef.current = savedFingerprint;
      setStatus(latestFingerprintRef.current === savedFingerprint
        ? '✓ Salvo'
        : 'Alterações não salvas');
    } catch (error) {
      setStatus(`Falha ao salvar: ${error.message || 'Não foi possível salvar o diagrama.'} Alterações não salvas.`);
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  }, [config, lockVersion]);

  return (
    <div className="diagram-workspace">
      <div className="d-flex align-items-center gap-3 mb-2">
        {config.canEdit && <button className="btn btn-primary" type="button" onClick={save} disabled={isSaving}>Salvar diagrama</button>}
        <span role="status" aria-live="polite">{status}</span>
      </div>
      <div className="diagram-canvas">
        <Excalidraw
          excalidrawAPI={(api) => { apiRef.current = api; }}
          initialData={initialDataRef.current}
          onChange={config.canEdit ? onChange : undefined}
          viewModeEnabled={!config.canEdit}
        />
      </div>
    </div>
  );
}

if (rootElement) createRoot(rootElement).render(<DiagramEditor />);
