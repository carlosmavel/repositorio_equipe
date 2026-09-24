import { Editor, Node } from 'https://esm.sh/@tiptap/core@3';
import StarterKit from 'https://esm.sh/@tiptap/starter-kit@3';
import { Image } from 'https://esm.sh/@tiptap/extension-image@3';
import { Link } from 'https://esm.sh/@tiptap/extension-link@3';
import { Subscript } from 'https://esm.sh/@tiptap/extension-subscript@3';
import { Superscript } from 'https://esm.sh/@tiptap/extension-superscript@3';
import { TextStyle, Color } from 'https://esm.sh/@tiptap/extension-text-style@3';
import { Underline } from 'https://esm.sh/@tiptap/extension-underline@3';
import { Table, TableRow, TableCell, TableHeader } from 'https://esm.sh/@tiptap/extension-table@3';
import { TaskList, TaskItem } from 'https://esm.sh/@tiptap/extension-list@3';
import { Placeholder } from 'https://esm.sh/@tiptap/extensions@3';
import { TextAlign } from 'https://esm.sh/@tiptap/extension-text-align@3';
import { Highlight } from 'https://esm.sh/@tiptap/extension-highlight@3';
import { FileHandler } from 'https://esm.sh/@tiptap/extension-file-handler@3';
import ArticleDiagram from './extensions/article-diagram.js';

const configElement = document.getElementById('article-editor-config');
const config = configElement ? JSON.parse(configElement.textContent) : {};

// This is deliberately the single registry used by both create and edit pages.
export const ARTICLE_EDITOR_NODE_NAMES = [
  'starterKit', 'image', 'articleVideo', 'link', 'subscript', 'superscript',
  'textStyle', 'color', 'underline', 'table', 'tableRow', 'tableCell',
  'tableHeader', 'taskList', 'taskItem', 'placeholder', 'textAlign',
  'highlight', 'fileHandler', 'articleDiagram'
];

document.addEventListener('DOMContentLoaded', () => {
    const editorElement = document.querySelector('#tiptap-editor');
    if (!editorElement || editorElement.dataset.tiptapInitialized === '1') {
      return;
    }
    editorElement.dataset.tiptapInitialized = '1';
    const initialContent = config.initialContent || '<p></p>';

    const pendingEditorImageUploads = new Set();
    const pendingEditorVideoUploads = new Set();
    const EDITOR_VIDEO_ALLOWED_TYPES = ['video/mp4', 'video/webm', 'video/x-msvideo', 'video/avi', 'application/x-troff-msvideo'];
    const EDITOR_VIDEO_MAX_BYTES = Number(config.videoMaxBytes) || 104857600;
    const VideoNode = Node.create({
      name: 'articleVideo', group: 'block', atom: true, draggable: true,
      addAttributes() { return { src: { default: null } }; },
      parseHTML() { return [{ tag: 'video[data-article-video]' }]; },
      renderHTML({ HTMLAttributes }) {
        return ['video', { ...HTMLAttributes, controls: 'controls', preload: 'metadata', playsinline: 'true', 'data-article-video': 'true' }];
      }
    });

    const activeEditorImageUploadKeys = new Set();
    const EDITOR_IMAGE_ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const EDITOR_IMAGE_UPLOAD_TIMEOUT_MS = 30000;
    const EDITOR_IMAGE_MAX_BYTES = Number(config.imageMaxBytes) || 2097152;

    function describeEditorImageFile(file) {
      return {
        name: file.name || 'imagem-colada',
        type: file.type || 'sem-mime',
        size: file.size || 0
      };
    }

    function validateEditorImageFile(file) {
      if (!EDITOR_IMAGE_ALLOWED_MIME_TYPES.includes(file.type)) {
        throw new Error('Tipo de imagem inválido. Envie apenas PNG, JPG/JPEG, GIF ou WebP.');
      }
      if (EDITOR_IMAGE_MAX_BYTES > 0 && file.size > EDITOR_IMAGE_MAX_BYTES) {
        const limitMb = (EDITOR_IMAGE_MAX_BYTES / 1024 / 1024).toFixed(1).replace('.0', '');
        throw new Error(`Imagem acima do limite permitido (${limitMb} MB). Reduza o print ou envie como anexo.`);
      }
    }

    function editorImageUploadKey(file) {
      return [file.name || 'imagem-colada', file.type || 'sem-mime', file.size || 0, file.lastModified || 0].join(':');
    }

    function editorImageFilename(file) {
      if (file.name) return file.name;
      const extensionsByMime = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'image/webp': 'webp'
      };
      return `imagem-colada.${extensionsByMime[file.type] || 'png'}`;
    }

    async function uploadEditorImage(file) {
      validateEditorImageFile(file);
      const uploadStartedAt = performance.now();
      const fileInfo = describeEditorImageFile(file);
      console.info('[editor-image-upload:start]', fileInfo);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), EDITOR_IMAGE_UPLOAD_TIMEOUT_MS);

      try {
        const formData = new FormData();
        formData.append('file', file, editorImageFilename(file));
        const response = await fetch('/artigos/editor-image-upload', {
          method: 'POST',
          body: formData,
          headers: { Accept: 'application/json' },
          signal: controller.signal
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (e) {
          // Mantém mensagem genérica quando a resposta não é JSON.
        }
        if (!response.ok || !payload?.url) {
          throw new Error(payload?.error || 'Não foi possível enviar a imagem colada.');
        }
        return payload.url;
      } catch (error) {
        if (error.name === 'AbortError') {
          throw new Error('Tempo esgotado ao enviar a imagem colada. Tente novamente com uma imagem menor ou use anexos.');
        }
        throw error;
      } finally {
        clearTimeout(timeoutId);
        console.info('[editor-image-upload:end]', {
          ...fileInfo,
          durationMs: Math.round(performance.now() - uploadStartedAt)
        });
      }
    }

    function trackEditorImageUpload(uploadPromise) {
      pendingEditorImageUploads.add(uploadPromise);
      uploadPromise.then(
        () => pendingEditorImageUploads.delete(uploadPromise),
        () => pendingEditorImageUploads.delete(uploadPromise)
      );
      return uploadPromise;
    }

    async function waitForEditorImageUploads() {
      if (!pendingEditorImageUploads.size) return;
      await Promise.all(Array.from(pendingEditorImageUploads));
    }

    const insertImageFiles = (editorInstance, files, pos = null) => {
      Array.from(files)
        .filter(file => file.type.startsWith('image/'))
        .forEach(file => {
          const uploadKey = editorImageUploadKey(file);
          if (activeEditorImageUploadKeys.has(uploadKey)) {
            return;
          }
          activeEditorImageUploadKeys.add(uploadKey);
          const uploadPromise = uploadEditorImage(file)
            .then((url) => {
              const image = { type: 'image', attrs: { src: url, alt: file.name } };
              if (typeof pos === 'number') {
                editorInstance.chain().focus().insertContentAt(pos, image).run();
                return;
              }
              editorInstance.chain().focus().insertContent(image).run();
            })
            .catch((error) => {
              console.error('Falha ao enviar imagem do editor', error);
              alert(error.message || 'Não foi possível enviar a imagem colada.');
              throw error;
            })
            .finally(() => activeEditorImageUploadKeys.delete(uploadKey));
          trackEditorImageUpload(uploadPromise);
        });
    };

    function validateEditorVideoFile(file) {
      const extension = (file.name.split('.').pop() || '').toLowerCase();
      if (!['mp4', 'webm', 'avi'].includes(extension) || !EDITOR_VIDEO_ALLOWED_TYPES.includes(file.type)) {
        throw new Error('Tipo de vídeo inválido. Envie apenas MP4, WebM ou AVI.');
      }
      if (EDITOR_VIDEO_MAX_BYTES > 0 && file.size > EDITOR_VIDEO_MAX_BYTES) {
        throw new Error(`Vídeo acima do limite permitido (${Math.round(EDITOR_VIDEO_MAX_BYTES / 1024 / 1024)} MB).`);
      }
    }

    async function uploadEditorVideo(file) {
      validateEditorVideoFile(file);
      const formData = new FormData();
      formData.append('file', file, file.name);
      const response = await fetch('/artigos/editor-video-upload', { method: 'POST', body: formData, headers: { Accept: 'application/json' } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.url) throw new Error(payload.error || 'Não foi possível enviar o vídeo.');
      return payload;
    }

    const editor = new Editor({
      element: editorElement,
      extensions: [
        StarterKit,
        Image.configure({ allowBase64: false }),
        VideoNode,
        ArticleDiagram,
        Link.configure({ openOnClick: false, defaultProtocol: 'https' }),
        Subscript,
        Superscript,
        TextStyle,
        Color,
        Underline,
        Table.configure({ resizable: true }),
        TableRow,
        TableCell,
        TableHeader,
        TaskList,
        TaskItem.configure({ nested: true }),
        Placeholder.configure({ placeholder: config.placeholder || 'Escreva o conteúdo do artigo...' }),
        TextAlign.configure({ types: ['heading', 'paragraph'] }),
        Highlight.configure({ multicolor: true }),
        FileHandler.configure({
          allowedMimeTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
          onPaste: (editorInstance, files) => insertImageFiles(editorInstance, files),
          onDrop: (editorInstance, files, pos) => insertImageFiles(editorInstance, files, pos)
        })
      ],
      content: initialContent,
      editorProps: {
        attributes: {
          class: 'tiptap-content',
          'aria-labelledby': 'tiptap-editor-label'
        }
      },
      onUpdate: () => saveDraft(),
      onSelectionUpdate: ({ editor }) => updateToolbarState(editor),
      onTransaction: ({ editor }) => updateToolbarState(editor)
    });

  const videoInput = document.querySelector('[data-editor-video-input]');
  let videoInsertionPosition = null;
  const selectAndUploadVideo = () => {
    videoInsertionPosition = editor.state.selection.anchor;
    videoInput.value = '';
    videoInput.click();
  };
  videoInput.addEventListener('change', () => {
    const file = videoInput.files?.[0];
    if (!file) return;
    const button = document.querySelector('[data-editor-command="insertVideo"]');
    button.disabled = true;
    const upload = uploadEditorVideo(file)
      .then((payload) => editor.chain().focus().insertContentAt(videoInsertionPosition, { type: 'articleVideo', attrs: { src: payload.url } }).run())
      .catch((error) => { console.error('Falha ao enviar vídeo', error); alert(error.message || 'Não foi possível enviar o vídeo.'); throw error; })
      .finally(() => { pendingEditorVideoUploads.delete(upload); button.disabled = false; });
    pendingEditorVideoUploads.add(upload);
  });

  const toolbarButtons = document.querySelectorAll('[data-editor-command]');
  const promptPositiveInteger = (message, defaultValue, min = 1, max = 20) => {
    const raw = prompt(message, String(defaultValue));
    if (raw === null) return null;
    const value = Number.parseInt(raw, 10);
    if (!Number.isInteger(value) || value < min || value > max) {
      alert(`Informe um número entre ${min} e ${max}.`);
      return null;
    }
    return value;
  };
  const normalizeUrl = (value) => {
    const trimmed = (value || '').trim();
    if (!trimmed) return '';
    if (/^(https?:|mailto:)/i.test(trimmed)) return trimmed;
    if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return `mailto:${trimmed}`;
    return `https://${trimmed}`;
  };
  const setLink = () => {
    const previousUrl = editor.getAttributes('link').href || '';
    const rawUrl = prompt('URL do link:', previousUrl);
    if (rawUrl === null) return;
    const href = normalizeUrl(rawUrl);
    if (!href) {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href }).run();
  };
  const setTextColor = () => {
    const color = prompt('Cor do texto em hexadecimal (ex.: #0d6efd):', editor.getAttributes('textStyle').color || '#0d6efd');
    if (color === null) return;
    if (!/^#[0-9a-f]{3}(?:[0-9a-f]{3})?$/i.test(color.trim())) {
      alert('Use uma cor hexadecimal válida, como #0d6efd.');
      return;
    }
    editor.chain().focus().setColor(color.trim()).run();
  };
  const insertConfiguredTable = () => {
    const rows = promptPositiveInteger('Quantas linhas a tabela deve ter?', 3, 1, 20);
    if (rows === null) return;
    const cols = promptPositiveInteger('Quantas colunas a tabela deve ter?', 3, 1, 10);
    if (cols === null) return;
    editor.chain().focus().insertTable({ rows, cols, withHeaderRow: true }).run();
  };
  const chooseDiagram = async (items, message) => {
    if (!items.length) {
      alert('Nenhum diagrama disponível.');
      return null;
    }
    const choices = items.map((item, index) => `${index + 1}. ${item.title}`).join('\n');
    const selected = prompt(`${message}\n\n${choices}`);
    if (selected === null) return null;
    const index = Number.parseInt(selected, 10) - 1;
    return items[index] || null;
  };

  const insertArticleDiagram = async () => {
    const option = prompt('Inserir diagrama:\n1. Criar novo\n2. Vincular existente\n3. Criar a partir de modelo', '1');
    if (option === null) return;
    let diagram = null;
    if (option === '1') {
      const title = prompt('Título do novo diagrama:');
      if (!title?.trim()) return;
      const response = await fetch('/api/diagramas', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ title: title.trim() })
      });
      diagram = await response.json();
      if (!response.ok) throw new Error(diagram.error || 'Não foi possível criar o diagrama.');
    } else {
      const metadataResponse = await fetch(`/api/diagramas/metadados${option === '3' ? '?tipo=modelo' : ''}`, { headers: { Accept: 'application/json' } });
      const items = await metadataResponse.json();
      if (!metadataResponse.ok) throw new Error(items.error || 'Não foi possível listar os diagramas.');
      const selected = await chooseDiagram(items, option === '3' ? 'Escolha um modelo:' : 'Escolha um diagrama:');
      if (!selected) return;
      if (option === '2') {
        diagram = selected;
      } else if (option === '3') {
        const title = prompt('Título da cópia:', selected.title);
        if (!title?.trim()) return;
        const copyResponse = await fetch(`/api/diagramas/${selected.id}/copiar`, {
          method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ title: title.trim() })
        });
        diagram = await copyResponse.json();
        if (!copyResponse.ok) throw new Error(diagram.error || 'Não foi possível copiar o modelo.');
      } else {
        alert('Escolha uma opção entre 1 e 3.');
        return;
      }
    }
    editor.chain().focus().insertArticleDiagram({ diagramId: diagram.id, position: editor.state.selection.anchor }).run();
  };

  const runEditorCommand = (command) => {
    const chain = editor.chain().focus();
    const commands = {
      bold: () => chain.toggleBold().run(),
      italic: () => chain.toggleItalic().run(),
      underline: () => chain.toggleUnderline().run(),
      strike: () => chain.toggleStrike().run(),
      code: () => chain.toggleCode().run(),
      subscript: () => chain.toggleSubscript().run(),
      superscript: () => chain.toggleSuperscript().run(),
      highlight: () => chain.toggleHighlight({ color: '#fff3cd' }).run(),
      textColor: () => setTextColor(),
      unsetColor: () => chain.unsetColor().run(),
      paragraph: () => chain.setParagraph().run(),
      heading1: () => chain.toggleHeading({ level: 1 }).run(),
      heading2: () => chain.toggleHeading({ level: 2 }).run(),
      heading3: () => chain.toggleHeading({ level: 3 }).run(),
      blockquote: () => chain.toggleBlockquote().run(),
      codeBlock: () => chain.toggleCodeBlock().run(),
      horizontalRule: () => chain.setHorizontalRule().run(),
      hardBreak: () => chain.setHardBreak().run(),
      bulletList: () => chain.toggleBulletList().run(),
      orderedList: () => chain.toggleOrderedList().run(),
      taskList: () => chain.toggleTaskList().run(),
      alignLeft: () => chain.setTextAlign('left').run(),
      alignCenter: () => chain.setTextAlign('center').run(),
      alignRight: () => chain.setTextAlign('right').run(),
      alignJustify: () => chain.setTextAlign('justify').run(),
      setLink: () => setLink(),
      unsetLink: () => chain.extendMarkRange('link').unsetLink().run(),
      clearFormat: () => chain.unsetAllMarks().clearNodes().run(),
      insertTable: () => insertConfiguredTable(),
      insertVideo: () => selectAndUploadVideo(),
      insertArticleDiagram: () => insertArticleDiagram().catch(error => alert(error.message || 'Não foi possível inserir o diagrama.')),
      addColumnBefore: () => chain.addColumnBefore().run(),
      addColumnAfter: () => chain.addColumnAfter().run(),
      deleteColumn: () => chain.deleteColumn().run(),
      addRowBefore: () => chain.addRowBefore().run(),
      addRowAfter: () => chain.addRowAfter().run(),
      deleteRow: () => chain.deleteRow().run(),
      mergeCells: () => chain.mergeCells().run(),
      splitCell: () => chain.splitCell().run(),
      toggleHeaderRow: () => chain.toggleHeaderRow().run(),
      toggleHeaderColumn: () => chain.toggleHeaderColumn().run(),
      deleteTable: () => chain.deleteTable().run(),
      undo: () => chain.undo().run(),
      redo: () => chain.redo().run()
    };
    commands[command]?.();
  };

  function updateToolbarState(editorInstance = editor) {
    const passiveCommands = [
      'paragraph', 'textColor', 'unsetColor', 'horizontalRule', 'hardBreak', 'setLink', 'unsetLink',
      'clearFormat', 'insertTable', 'insertVideo', 'insertArticleDiagram', 'addColumnBefore', 'addColumnAfter', 'deleteColumn', 'addRowBefore',
      'addRowAfter', 'deleteRow', 'mergeCells', 'splitCell', 'toggleHeaderRow', 'toggleHeaderColumn',
      'deleteTable', 'undo', 'redo'
    ];
    document.querySelectorAll('[data-editor-command]').forEach((button) => {
      const command = button.dataset.editorCommand;
      const active = (command === 'heading1' && editorInstance.isActive('heading', { level: 1 })) ||
        (command === 'heading2' && editorInstance.isActive('heading', { level: 2 })) ||
        (command === 'heading3' && editorInstance.isActive('heading', { level: 3 })) ||
        (command === 'alignLeft' && editorInstance.isActive({ textAlign: 'left' })) ||
        (command === 'alignCenter' && editorInstance.isActive({ textAlign: 'center' })) ||
        (command === 'alignRight' && editorInstance.isActive({ textAlign: 'right' })) ||
        (command === 'alignJustify' && editorInstance.isActive({ textAlign: 'justify' })) ||
        (!passiveCommands.includes(command) && editorInstance.isActive(command));
      button.classList.toggle('active', Boolean(active));
      button.setAttribute('aria-pressed', Boolean(active).toString());
    });
  }

  toolbarButtons.forEach((button) => {
    button.addEventListener('click', () => runEditorCommand(button.dataset.editorCommand));
  });
  updateToolbarState();

  // Visibilidade por checkboxes
  const visChecks = document.querySelectorAll('.vis-check');
  const visInput = document.getElementById('visibilityInput');
  const visDisplay = document.getElementById('visibilityDisplay');
  const STORAGE_KEY = config.autosaveKey;
  const ARTICLE_VIEW_PATH = config.articleViewPath || '';
  const DRASTIC_REDUCTION_MESSAGE = 'Esta alteração reduz significativamente o conteúdo do artigo. Confirme se deseja continuar.';
  const previousArticleCharCount = Number(config.previousCharCount) || 0;

  function normalizePlainTextForCount(text) {
    return (text || '').replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function plainTextFromHtmlForCount(html) {
    const holder = document.createElement('div');
    holder.innerHTML = html || '';
    return normalizePlainTextForCount(holder.textContent || holder.innerText || '');
  }

  function calculateReductionPercent(previousCount, newCount) {
    if (!previousCount || previousCount <= 0 || newCount >= previousCount) return 0;
    return ((previousCount - newCount) / previousCount) * 100;
  }

  function updateReductionFields({ confirmed = false } = {}) {
    const newText = normalizePlainTextForCount(editor.getText());
    const newCharCount = newText.length;
    const reductionPercent = calculateReductionPercent(previousArticleCharCount, newCharCount);
    document.getElementById('drastic-reduction-confirmed')?.setAttribute('value', confirmed ? 'true' : 'false');
    document.getElementById('previous-char-count')?.setAttribute('value', String(previousArticleCharCount));
    document.getElementById('new-char-count')?.setAttribute('value', String(newCharCount));
    document.getElementById('reduction-percent')?.setAttribute('value', reductionPercent.toFixed(2));
    return { newCharCount, reductionPercent };
  }
  function saveDraft() {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        titulo: document.querySelector('input[name="titulo"]').value,
        texto: editor.getHTML(),
        visibility: visInput.value,
        tipo_id: document.getElementById('tipo-id')?.value,
        area_id: document.getElementById('area-id')?.value,
        sistema_id: document.getElementById('sistema-id')?.value
      })
    );
  }
  function loadDraft() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
      const data = JSON.parse(raw);
      if (data.titulo) document.querySelector('input[name="titulo"]').value = data.titulo;
      if (data.texto) editor.commands.setContent(data.texto);
      ['tipo_id', 'area_id', 'sistema_id'].forEach((key) => {
        const input = document.getElementById(key.replace('_', '-'));
        if (input && typeof data[key] === 'string') input.value = data[key];
      });
      if (data.visibility) {
        visInput.value = data.visibility;
        const parts = data.visibility.split(',');
        visChecks.forEach(cb => cb.checked = parts.includes(cb.value));
        updateVisibility();
      }
    } catch (e) {
      console.warn('Falha ao carregar rascunho do artigo', e);
    }
  }
  function updateVisibility() {
    const opts = Array.from(visChecks).filter(c => c.checked);
    visInput.value = opts.map(o => o.value).join(',');
    visDisplay.innerHTML = opts.map(o => `<span class="badge bg-secondary me-1">${o.dataset.label}</span>`).join('');
  }
  visChecks.forEach(cb => cb.addEventListener('change', updateVisibility));
  updateVisibility();
  if (config.clearAutosave) localStorage.removeItem(STORAGE_KEY);
  else loadDraft();
  document.querySelector('input[name="titulo"]').addEventListener('input', saveDraft);
  ['tipo-id', 'area-id', 'sistema-id'].forEach((id) => document.getElementById(id)?.addEventListener('change', saveDraft));
  visChecks.forEach(cb => cb.addEventListener('change', saveDraft));

  const overlay = document.getElementById('fileLoadingOverlay');
  const overlayText = overlay?.querySelector('.file-loading-text');
  const overlayBar = overlay?.querySelector('.progress-bar');
  const progressMessages = overlay?.querySelector('.processing-messages');
  const progressIdInput = document.getElementById('progress-id');
  const seenMessages = new Set();
  let progressPoll = null;
  let overlaySimInterval = null;
  let overlaySimProgress = 0;

  const resetProgressMessages = () => {
    seenMessages.clear();
    if (progressMessages) {
      progressMessages.innerHTML = '';
    }
  };

  const appendMessages = (messages = []) => {
    if (!progressMessages) return;
    messages.forEach(msg => {
      if (!msg || seenMessages.has(msg)) return;
      seenMessages.add(msg);
      const line = document.createElement('div');
      line.className = 'message-line';
      line.textContent = msg;
      progressMessages.appendChild(line);
      progressMessages.scrollTop = progressMessages.scrollHeight;
    });
  };

  const startProgressPolling = (progressId) => {
    if (!progressId || progressPoll) return;
    progressPoll = setInterval(async () => {
      try {
        const resp = await fetch(`/upload-progress/${progressId}`);
        if (!resp.ok) return;
        const data = await resp.json();
        appendMessages(data.messages || []);
        const progressValue = typeof data.percent === 'number' ? data.percent : null;
        setOverlayState(overlayText?.textContent || 'Processando anexos...', progressValue);
        if (data.done) {
          completeBar();
          stopProgressPolling();
        }
      } catch (e) {
        console.warn('Falha ao consultar progresso', e);
      }
    }, 900);
  };

  const stopProgressPolling = () => {
    if (progressPoll) {
      clearInterval(progressPoll);
      progressPoll = null;
    }
  };

  const startSimulatedBar = () => {
    if (!overlayBar || overlaySimInterval) return;
    overlaySimProgress = 0;
    overlayBar.classList.add('progress-bar-striped', 'progress-bar-animated');
    overlayBar.style.width = '0%';
    overlayBar.setAttribute('aria-valuenow', 0);

    overlaySimInterval = setInterval(() => {
      overlaySimProgress = Math.min(95, overlaySimProgress + (Math.random() * 5 + 3));
      overlayBar.style.width = `${overlaySimProgress}%`;
      overlayBar.setAttribute('aria-valuenow', Math.round(overlaySimProgress));
    }, 550);
  };

  const stopSimulatedBar = () => {
    if (overlaySimInterval) {
      clearInterval(overlaySimInterval);
      overlaySimInterval = null;
    }
  };

  const completeBar = () => {
    stopSimulatedBar();
    if (!overlayBar) return;
    overlayBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
    overlayBar.style.width = '100%';
    overlayBar.setAttribute('aria-valuenow', 100);
  };

  const setOverlayState = (message, percent = null) => {
    if (!overlay) return;
    overlay.style.display = 'flex';
    if (overlayText) overlayText.textContent = message;

    if (!overlayBar) return;

    if (percent === null) {
      startSimulatedBar();
    } else {
      stopSimulatedBar();
      overlayBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
      const current = Number(overlayBar.getAttribute('aria-valuenow')) || 0;
      const value = Math.min(100, Math.max(current, percent));
      overlayBar.style.width = `${value}%`;
      overlayBar.setAttribute('aria-valuenow', value);
    }
  };
  const hasPendingAttachmentFiles = () => Boolean(document.getElementById('files')?.files?.length);

  const hideOverlay = () => {
    completeBar();
    if (overlay) overlay.style.display = 'none';
    if (overlayBar) {
      overlayBar.style.width = '0%';
      overlayBar.removeAttribute('aria-valuenow');
    }
    stopProgressPolling();
    resetProgressMessages();
  };

  function isArticleViewUrl(url, expectedPath = ARTICLE_VIEW_PATH) {
    if (!url) return false;
    try {
      const parsed = new URL(url, window.location.origin);
      return parsed.pathname === expectedPath;
    } catch (e) {
      return false;
    }
  }

  function hasArticleSaveSuccessMarker(html) {
    return typeof html === 'string' && (
      html.includes('data-artigo-save-success="true"') ||
      html.includes('id="artigo-save-success"') ||
      html.includes('artigo-save-success')
    );
  }

  async function resolveEditSubmitResult(response, expectedPath = ARTICLE_VIEW_PATH) {
    if (response.redirected) {
      return {
        shouldClearAutosave: isArticleViewUrl(response.url, expectedPath),
        redirectUrl: response.url,
        html: null
      };
    }

    if (!response.ok) {
      return { shouldClearAutosave: false, redirectUrl: null, html: null };
    }

    const contentType = response.headers?.get('content-type') || '';
    if (contentType.includes('application/json')) {
      let data = null;
      try {
        data = await response.json();
      } catch (e) {
        return { shouldClearAutosave: false, redirectUrl: null, html: null };
      }
      const success = data?.success === true || data?.ok === true || data?.status === 'success';
      return {
        shouldClearAutosave: success,
        redirectUrl: success ? (data.redirect_url || data.redirectUrl || null) : null,
        html: null
      };
    }

    const html = await response.text();
    return {
      shouldClearAutosave: hasArticleSaveSuccessMarker(html),
      redirectUrl: null,
      html
    };
  }

  // Sincroniza conteúdo no hidden antes de submeter
  const form = document.querySelector('form');
  let lastSubmitter = null;
  form?.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((button) => {
    button.addEventListener('click', () => { lastSubmitter = button; });
  });
  const setSubmitButtonsDisabled = (disabled) => {
    form?.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((button) => {
      button.disabled = disabled;
    });
  };
  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (pendingEditorImageUploads.size) {
        setOverlayState('Enviando imagens coladas no texto...', null);
        try {
          await waitForEditorImageUploads();
          await Promise.all(Array.from(pendingEditorVideoUploads));
        } catch (error) {
          hideOverlay();
          setSubmitButtonsDisabled(false);
          return;
        }
      }

      const hiddenTexto = document.getElementById('hidden-texto');
      if (hiddenTexto) {
        hiddenTexto.value = editor.getHTML();
      }
      const reductionMetrics = updateReductionFields();
      const hasDrasticReduction = config.mode === 'edit' && (reductionMetrics.reductionPercent > 70 || (previousArticleCharCount > 2000 && reductionMetrics.newCharCount < 300));
      if (hasDrasticReduction) {
        const confirmed = window.confirm(DRASTIC_REDUCTION_MESSAGE);
        if (!confirmed) return;
        updateReductionFields({ confirmed: true });
      }
      const progressId = progressIdInput?.value || (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()));
      if (progressIdInput) progressIdInput.value = progressId;
    resetProgressMessages();
      setOverlayState('Salvando artigo e anexos...', 0);
      if (hasPendingAttachmentFiles()) {
        startProgressPolling(progressId);
      }

      if (config.mode === 'create') {
        const submitActionInput = document.getElementById('submit-action');
        const submitter = event.submitter || lastSubmitter;
        if (submitActionInput) {
          submitActionInput.name = 'acao';
          submitActionInput.value = submitter?.name === 'acao' ? submitter.value : 'rascunho';
        }
        localStorage.removeItem(STORAGE_KEY);
        setSubmitButtonsDisabled(true);
        form.submit();
        return;
      }

      setSubmitButtonsDisabled(true);
      try {
        const formData = new FormData(form);
        const submitter = event.submitter;
        if (submitter?.name && !formData.has(submitter.name)) {
          formData.append(submitter.name, submitter.value);
        }
        const response = await fetch(form.action || window.location.href, {
          method: 'POST',
          body: formData
        });
        const submitResult = await resolveEditSubmitResult(response);

        if (submitResult.shouldClearAutosave) {
          localStorage.removeItem(STORAGE_KEY);
          completeBar();
          if (submitResult.redirectUrl) {
            window.location.href = submitResult.redirectUrl;
          } else {
            setTimeout(() => window.location.reload(), 400);
          }
          return;
        }

        if (submitResult.redirectUrl) {
          window.location.href = submitResult.redirectUrl;
          return;
        }

        if (submitResult.html) {
          document.open();
          document.write(submitResult.html);
          document.close();
          return;
        }
      } catch (err) {
        console.error('Falha ao salvar artigo', err);
      }

      hideOverlay();
      setSubmitButtonsDisabled(false);
    });
  }

  // Remoção imediata de arquivos existentes
  const existingContainer = document.getElementById('existing-preview');
  const deleteFields = document.getElementById('delete-fields');
  if (existingContainer && deleteFields) { // Verifica se os elementos existem
    existingContainer.addEventListener('click', e => {
      const removeButton = e.target.closest('.remove-existing');
      if (removeButton) {
        const wrapper = removeButton.closest('[data-filename]');
        if (wrapper) { // Verifica se o wrapper foi encontrado
          const filename = wrapper.getAttribute('data-filename');
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = 'delete_files';
          input.value = filename;
          deleteFields.appendChild(input);
          wrapper.remove();
        }
      }
    });
  }

    // Preview de novos uploads
    const resolveIcon = (filename) => {
      const ext = filename.split('.').pop().toLowerCase();
      if (ext === 'pdf') return config.icons.pdf;
      if (['xls', 'xlsx'].includes(ext)) return config.icons.excel;
      return config.icons.file;
    };

    const inputFile = document.getElementById('files');
    const preview = document.getElementById('preview');
    if (inputFile && preview) { // Verifica se os elementos existem
    const dt = new DataTransfer();
    inputFile.addEventListener('change', () => {
      const incomingFiles = Array.from(inputFile.files || []);
      if (!incomingFiles.length) {
        preview.innerHTML = '';
        hideOverlay();
        return;
      }
      setOverlayState('Preparando anexos...', 0);
      incomingFiles.forEach((file, index) => {
        if (!Array.from(dt.files).some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
          dt.items.add(file);
        }

        const percent = Math.round(((index + 1) / incomingFiles.length) * 100);
        const displayName = file.name.replace(/^[0-9a-f]{32}_/, '');
        setOverlayState(`Processando arquivo ${index + 1} de ${incomingFiles.length}: ${displayName}`, percent);
      });
      inputFile.files = dt.files;
      preview.innerHTML = '';
      Array.from(dt.files).forEach((file, idx) => {
        const url = URL.createObjectURL(file);
        const displayName = file.name.replace(/^[0-9a-f]{32}_/, '');
        const col = document.createElement('div');
        col.className = 'col-12 col-sm-6 col-md-4 col-lg-3 attachment-card';
        col.innerHTML = `
        <div class="card h-100 shadow-sm">
          <div class="attachment-preview" title="${displayName}">
                  <span class="attachment-filename-hover" aria-hidden="true"></span>
            ${file.type.startsWith('image/')
              ? `<img src="${url}" class="card-img-top attachment-thumb" alt="${displayName}">`
              : `<div class="attachment-thumb-wrapper"><img src="${resolveIcon(file.name)}" class="attachment-icon-vertical" alt="Arquivo"></div>`}
                      </div>
          <button type="button" class="attachment-delete-btn remove-btn" data-index="${idx}" aria-label="Remover">
            <i class="bi bi-trash"></i>
          </button>
          <div class="card-body p-2 attachment-meta">
            <div class="attachment-name" title="${displayName}">${displayName}</div>
                      </div>
        </div>`;
        preview.appendChild(col);
      });
      setOverlayState('Pré-visualização pronta!', 100);
      setTimeout(hideOverlay, 350);
    });

    preview.addEventListener('click', e => {
      const removeButton = e.target.closest('.remove-btn');
      if (!removeButton) return;
      const idx = Number(removeButton.dataset.index);
      dt.items.remove(idx);
      inputFile.files = dt.files;
      inputFile.dispatchEvent(new Event('change')); // Força o re-render do preview
    });
  }
});
