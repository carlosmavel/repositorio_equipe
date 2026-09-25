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
  const [status, setStatus] = useState('');
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

  const onChange = useCallback((_elements, _appState, files) => {
    filesRef.current = files;
    setStatus('Alterações não salvas');
  }, []);

  const save = useCallback(async () => {
    const api = apiRef.current;
    if (!api) return;
    setStatus('Salvando…');
    try {
      const elements = api.getSceneElements();
      const appState = api.getAppState();
      const files = filesRef.current;
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
      setStatus('Salvo');
    } catch (error) {
      setStatus(error.message || 'Falha ao salvar');
    }
  }, [config, lockVersion]);

  return (
    <div className="diagram-workspace">
      <div className="d-flex align-items-center gap-3 mb-2">
        <button className="btn btn-primary" type="button" onClick={save}>Salvar diagrama</button>
        <span role="status" aria-live="polite">{status}</span>
      </div>
      <div className="diagram-canvas">
        <Excalidraw
          excalidrawAPI={(api) => { apiRef.current = api; }}
          initialData={initialDataRef.current}
          onChange={onChange}
        />
      </div>
    </div>
  );
}

if (rootElement) createRoot(rootElement).render(<DiagramEditor />);
