import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    manifest: true,
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        'article-editor': 'frontend/article-editor/index.js',
        'diagram-editor': 'frontend/diagram-editor/index.jsx',
      },
    },
  },
});
