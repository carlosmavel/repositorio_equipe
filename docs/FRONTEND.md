# Frontend local (Vite)

Flask/Jinja continua responsável pelo HTML e inclui uma entrada Vite somente nas
páginas de edição que precisam dela. Rode `npm ci` e `npm run build`; o segundo
comando grava bundles com hash e `static/dist/.vite/manifest.json`, que é lido
por `core/vite.py`.

## Contrato validado do Excalidraw

A integração foi fixada em `@excalidraw/excalidraw` 0.18.0 e React/ReactDOM
18.3.1. Antes da fixação foram conferidas as páginas oficiais de
[instalação](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/installation),
[props](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/props/),
[API imperativa](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/props/excalidraw-api)
e [utilitários de exportação](https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export).

O contrato usado pelo adaptador é:

* `initialData` aceita um objeto ou `Promise` com `elements`, `appState`,
  `files` (`BinaryFiles`) e `scrollToContent`;
* `onChange(elements, appState, files)` fornece o snapshot e os arquivos atuais;
* a API recebida em `excalidrawAPI` expõe `getSceneElements()` e `getAppState()`;
* `exportToBlob`, `exportToCanvas` e `exportToSvg` são as funções oficiais de
  exportação; o preview usa `exportToBlob` com `files`;
* o pacote exige React e ReactDOM como peers e o CSS público
  `@excalidraw/excalidraw/index.css` deve ser importado. A linha 0.18 declara
  compatibilidade com React 17/18; por isso não foi adotado React 19.

Todos os pacotes Tiptap importados pelo editor usam exatamente a mesma versão
3.4.2. Eles são resolvidos em um único grafo pelo Vite, em vez de URLs `esm.sh`,
evitando registries duplicados de Tiptap/ProseMirror na página.
