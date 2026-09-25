export const DIAGRAM_SAVED_EVENT = 'orquetask:diagram-saved';
export const DIAGRAM_PREVIEW_STATE_EVENT = 'orquetask:diagram-preview-state';

export function announceDiagramPreviewState(uuid, preview_state, preview_message = null) {
  if (!uuid) return;
  window.dispatchEvent(new CustomEvent(DIAGRAM_PREVIEW_STATE_EVENT, {
    detail: { uuid, preview_state, preview_message },
  }));
}

/** Add or replace the deterministic preview cache key without changing its route. */
export function versionDiagramPreviewUrl(url, version) {
  if (!url || version === undefined || version === null) return url || null;
  const parsed = new URL(url, window.location.href);
  parsed.searchParams.set('v', String(version));
  return `${parsed.pathname}${parsed.search}${parsed.hash}`;
}

export function announceDiagramSaved(saved) {
  const uuid = saved?.uuid || saved?.id;
  if (!uuid) return;
  window.dispatchEvent(new CustomEvent(DIAGRAM_SAVED_EVENT, {
    detail: {
      uuid,
      current_version: saved.current_version,
      lock_version: saved.lock_version,
      preview_state: saved.preview_state,
      preview_url: saved.preview_url || null,
      preview_token: saved.preview_token || saved.cache_token || saved.current_version,
      title: saved.title,
    },
  }));
}
