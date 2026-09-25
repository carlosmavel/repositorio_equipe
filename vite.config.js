import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Flask exposes the build directory below /static/dist.  Without an explicit
  // base, URLs emitted from Excalidraw's CSS point at /assets and bypass it.
  base: '/static/dist/',
  plugins: [react()],
  build: {
    manifest: true,
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        'article-editor': 'frontend/article-editor/index.js',
        'diagram-editor': 'frontend/diagram-editor/standalone.jsx',
        'article-diagram-viewer': 'frontend/article-diagram-viewer/index.js',
        'diagram-library': 'frontend/diagram-library/create.js',
      },
    },
  },
});
