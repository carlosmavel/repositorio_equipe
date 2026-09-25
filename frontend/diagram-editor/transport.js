const SCHEMA_VERSION = 1;
const EPHEMERAL_APP_STATE = new Set([
  'collaborators', 'contextMenu', 'cursorButton', 'draggingElement',
  'editingElement', 'editingGroupId', 'editingLinearElement', 'errorMessage',
  'isLoading', 'openDialog', 'openMenu', 'pasteDialog',
  'previousSelectedElementIds', 'resizingElement', 'selectedElementIds',
  'selectedGroupIds', 'selectionElement', 'suggestedBindings', 'toast',
  'userToFollow', 'zenModeEnabled',
]);

function durableAppState(appState) {
  return Object.fromEntries(Object.entries(appState || {})
    .filter(([key]) => !EPHEMERAL_APP_STATE.has(key)));
}

function sceneFingerprint({ elements, appState, files } = {}) {
  const fileData = Object.fromEntries(Object.entries(files || {})
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([id, file]) => [id, {
      dataURL: file.dataURL || null,
      mimeType: file.mimeType || null,
    }]));
  return JSON.stringify({
    elements: elements || [],
    appState: durableAppState(appState),
    files: fileData,
  });
}

async function dataUrlToBlob(dataURL) {
  const response = await fetch(dataURL);
  return response.blob();
}

async function buildRequest({ elements, appState, files }, { title, lockVersion,
  excalidrawVersion } = {}, preview = null) {
  const form = new FormData();
  const manifest = {};
  for (const [id, file] of Object.entries(files || {})) {
    if (!file.dataURL) continue;
    const blob = await dataUrlToBlob(file.dataURL);
    manifest[id] = { mimeType: file.mimeType || blob.type };
    form.append(id, blob, `${id}`);
  }
  if (preview) form.append('preview', preview, 'preview.png');
  form.append('payload', JSON.stringify({
    schemaVersion: SCHEMA_VERSION,
    elements: elements || [],
    appState: durableAppState(appState),
    files: manifest,
    metadata: { editor: 'excalidraw', excalidrawVersion: excalidrawVersion || null },
    lockVersion,
    title,
  }));
  return form;
}

export const diagramTransport = { SCHEMA_VERSION, durableAppState, sceneFingerprint, buildRequest };
export default diagramTransport;
