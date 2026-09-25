import React from 'react';
import { createRoot } from 'react-dom/client';
import { DiagramWorkspace } from './index.jsx';

const rootElement = document.getElementById('diagram-editor');
const configElement = document.getElementById('diagram-editor-config');

if (rootElement && configElement) {
  const config = JSON.parse(configElement.textContent);
  createRoot(rootElement).render(<DiagramWorkspace {...config} />);
}
