function createDefaultNotesState() {
  const notesState = window.DescribeItState?.notes;
  if (notesState && typeof notesState.createDefaultNotesState === 'function') {
    return notesState.createDefaultNotesState();
  }

  return {
    scope: 'project',
    includeArchived: false,
    projectItems: [],
    globalItems: [],
    selectedNoteId: null,
    editor: {
      id: null,
      title: '',
      content: '',
      format: 'markdown',
      tags: '',
      is_archived: false,
    },
    llm: {
      prompt: '',
      useSelectedImage: false,
      backend: '',
      model: '',
      outputFormat: 'markdown',
      title: '',
      tags: '',
      webSearch: false,
      webFetch: false,
      contextUrl: '',
      contextFile: '',
      includeProjectNotes: false,
      includeGlobalNotes: false,
      reasoningMode: 'off',
      reasoningVisibility: 'hidden',
    },
  };
}

function createDefaultCaptionBatchState() {
  const batchState = window.DescribeItState?.batch;
  if (batchState && typeof batchState.createDefaultCaptionBatchState === 'function') {
    return batchState.createDefaultCaptionBatchState();
  }

  return {
    query: {
      findText: '',
      replaceText: '',
      mode: 'plain',
      caseSensitive: false,
    },
    scope: {
      captionScope: 'active_only',
      imageScope: 'included_only',
      imageIdsText: '',
    },
    apply: {
      confirm: false,
      createUndoSnapshot: true,
    },
    preview: null,
    operations: [],
    historyLimit: 20,
    lastOperationId: '',
  };
}

function createDefaultCaptionTextEditJobState() {
  const batchState = window.DescribeItState?.batch;
  if (batchState && typeof batchState.createDefaultCaptionTextEditJobState === 'function') {
    return batchState.createDefaultCaptionTextEditJobState();
  }

  return {
    id: '',
    status: 'idle',
    total: 0,
    completed: 0,
    affected: 0,
    currentLabel: '',
    lastError: '',
    result: null,
    createdAt: '',
    updatedAt: '',
  };
}

function createDefaultCaptionTextEditState() {
  const batchState = window.DescribeItState?.batch;
  if (batchState && typeof batchState.createDefaultCaptionTextEditState === 'function') {
    return batchState.createDefaultCaptionTextEditState();
  }

  return {
    removeTagsPatternsText: '',
    addCommonCaptionText: '',
    addCommonScope: 'without_caption',
    historyLimit: 10,
    jobs: {
      deleteEmpty: createDefaultCaptionTextEditJobState(),
      removeTags: createDefaultCaptionTextEditJobState(),
      addCommon: createDefaultCaptionTextEditJobState(),
    },
    history: {
      deleteEmpty: [],
      removeTags: [],
      addCommon: [],
    },
  };
}

function createDefaultBatchState() {
  const batchState = window.DescribeItState?.batch;
  if (batchState && typeof batchState.createDefaultBatchState === 'function') {
    return batchState.createDefaultBatchState();
  }

  return {
    subTab: 'generate',
    target: 'included',
    excludeCaptioned: false,
    usePreset: true,
    presetPromptSuffix: '',
    outputMode: 'new_candidate',
    skipOnFailure: true,
    retryCount: 0,
    jobId: '',
    status: 'idle',
    total: 0,
    completed: 0,
    succeeded: 0,
    failed: 0,
    currentImageId: null,
    currentFilename: '',
    currentGeneratedText: '',
    lastError: '',
    history: [],
    historyStatusFilter: 'all',
    results: [],
  };
}

function createDefaultGridFilterState() {
  const gridState = window.DescribeItState?.grid;
  if (gridState && typeof gridState.createDefaultGridFilterState === 'function') {
    return gridState.createDefaultGridFilterState();
  }

  return {
    searchText: '',
    searchMode: 'both', // 'filename', 'caption', 'both'
    inclusionStatus: 'all', // 'all', 'included', 'excluded'
    captionStatus: 'all', // 'all', 'with_captions', 'blank_captions'
    sortBy: 'name', // 'name', 'status', 'caption_count'
    sortOrder: 'asc', // 'asc', 'desc'
    pageSize: 50, // Items per page: 25, 50, 100, all
    currentPage: 1, // Current page (1-based)
  };
}

function describeItApp() {
  return {
    healthLabel: 'checking',
    currentProject: null,
    metadataForm: {
      path: '',
      name: '',
      description: '',
      trigger_word: '',
      caption_mode: 'description',
      context_url: '',
      context_file_path: '',
    },
    recentProjects: [],
    createForm: {
      name: '',
      path: 'projects/my_first_project.db',
      description: '',
    },
    openForm: {
      path: '',
    },
    importForm: {
      source_folder: 'practice_dataset/sample_set',
      source_image: '',
      replace_existing: false,
      default_caption: '',
    },
    importProgress: {
      active: false,
      total: 0,
      current: 0,
      percent: 0,
      currentFilename: '',
      label: '',
    },
    exportForm: {
      output_folder: 'exports',
      included_only: true,
      apply_trigger_word: false,
      include_metadata: false,
      overwrite_existing: false,
      clean_output_folder: false,
      create_new_folder: false,
      new_folder_name: '',
      include_project_notes: true,
    },
    exportPreview: null,
    imageSummary: {
      count: 0,
      non_empty_caption_count: 0,
      blank_caption_count: 0,
      previews: [],
    },
    uiSection: 'workspace',
    settingsTab: 'general',
    colorMode: 'dark',
    images: [],
    bookmarkedImageIds: [],
    isCurrentImageBookmarked() {
      return this.selectedImage && this.bookmarkedImageIds.includes(this.selectedImage.id);
    },
    toggleBookmarkCurrentImage() {
      if (!this.selectedImage) return;
      const id = this.selectedImage.id;
      if (this.bookmarkedImageIds.includes(id)) {
        this.bookmarkedImageIds = this.bookmarkedImageIds.filter((x) => x !== id);
      } else {
        this.bookmarkedImageIds = [...this.bookmarkedImageIds, id];
      }
      this.saveBookmarks();
    },
    saveBookmarks() {
      try {
        localStorage.setItem('describeIt.bookmarkedImageIds', JSON.stringify(this.bookmarkedImageIds));
      } catch (e) {}
    },
    loadBookmarks() {
      try {
        const data = localStorage.getItem('describeIt.bookmarkedImageIds');
        if (data) {
          this.bookmarkedImageIds = JSON.parse(data);
        }
      } catch (e) {}
    },
    loadColorMode() {
      try {
        const saved = localStorage.getItem('describeIt.colorMode');
        if (saved && ['dark', 'light', 'system'].includes(saved)) {
          this.colorMode = saved;
        }
      } catch (e) {}
      this.applyColorMode(this.colorMode);
    },
    applyColorMode(mode) {
      document.documentElement.setAttribute('data-theme', mode);
    },
    setColorMode(mode) {
      this.colorMode = mode;
      this.applyColorMode(mode);
      try { localStorage.setItem('describeIt.colorMode', mode); } catch (e) {}
    },
    cycleColorMode() {
      const modes = ['dark', 'light', 'system'];
      const next = modes[(modes.indexOf(this.colorMode) + 1) % modes.length];
      this.setColorMode(next);
    },
    colorModeLabel() {
      return { dark: '🌙 Dark', light: '☀️ Light', system: '⚙ System' }[this.colorMode] || 'Dark';
    },
    goToBookmarkedImage(imageId) {
      if (!imageId) return;
      this.selectImage(imageId, true);
    },
    bookmarkedImages() {
      // Returns image objects for all bookmarks, in bookmark order
      const byId = new Map((this.images || []).map(img => [img.id, img]));
      return this.bookmarkedImageIds.map(id => byId.get(id)).filter(Boolean);
    },
    scratchpad: {
      input: '',
      items: [],
      dragIndex: null,
    },
    sidebarNotes: {
      pinnedProjectIds: [],
      pinnedGlobalIds: [],
      recentProjectIds: [],
      recentGlobalIds: [],
    },
    quickChat: {
      backend: '',
      model: '',
      includeSelectedImage: false,
      prompt: '',
      response: '',
      noteScope: 'project',
      noteTitle: '',
      noteTags: '',
      saveDialogOpen: false,
      history: [],
    },
    loadQuickChatHistory() {
      try {
        const data = localStorage.getItem('describeIt.quickChatHistory');
        if (!data) {
          return;
        }
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed)) {
          this.quickChat.history = parsed
            .filter((entry) => entry && typeof entry === 'object')
            .slice(0, 5);
        }
      } catch (e) {}
    },
    saveQuickChatHistory() {
      try {
        localStorage.setItem('describeIt.quickChatHistory', JSON.stringify(this.quickChat.history.slice(0, 5)));
      } catch (e) {}
    },
    addQuickChatHistoryEntry(entry) {
      if (!entry || typeof entry !== 'object') {
        return;
      }
      this.quickChat.history = [entry, ...this.quickChat.history].slice(0, 5);
      this.saveQuickChatHistory();
    },
    useQuickChatHistoryEntry(entry) {
      if (!entry || typeof entry !== 'object') {
        return;
      }
      this.quickChat.backend = entry.backend || this.quickChat.backend;
      this.quickChat.model = entry.model || this.quickChat.model;
      this.quickChat.includeSelectedImage = entry.includeSelectedImage === true;
      this.quickChat.prompt = entry.prompt || '';
      this.quickChat.response = entry.response || '';
      this.syncQuickChatSelection();
    },
    loadScratchpad() {
      try {
        const data = localStorage.getItem('describeIt.scratchpadItems');
        if (!data) {
          return;
        }
        const parsed = JSON.parse(data);
        if (Array.isArray(parsed)) {
          this.scratchpad.items = parsed
            .map((item) => String(item || '').trim())
            .filter((item) => item.length > 0);
        }
      } catch (e) {}
    },
    saveScratchpad() {
      try {
        localStorage.setItem('describeIt.scratchpadItems', JSON.stringify(this.scratchpad.items));
      } catch (e) {}
    },
    addScratchpadItem() {
      const text = String(this.scratchpad.input || '').trim();
      if (!text) {
        return;
      }
      this.scratchpad.items = [text, ...this.scratchpad.items];
      this.scratchpad.input = '';
      this.saveScratchpad();
    },
    removeScratchpadItem(index) {
      if (!Number.isInteger(index) || index < 0 || index >= this.scratchpad.items.length) {
        return;
      }
      this.scratchpad.items = this.scratchpad.items.filter((_, i) => i !== index);
      this.saveScratchpad();
    },
    startScratchpadDrag(index) {
      if (!Number.isInteger(index) || index < 0 || index >= this.scratchpad.items.length) {
        return;
      }
      this.scratchpad.dragIndex = index;
    },
    onScratchpadDragEnd() {
      this.scratchpad.dragIndex = null;
    },
    dropScratchpadAt(targetIndex) {
      const sourceIndex = this.scratchpad.dragIndex;
      if (!Number.isInteger(sourceIndex)) {
        return;
      }
      if (!Number.isInteger(targetIndex) || targetIndex < 0 || targetIndex >= this.scratchpad.items.length) {
        this.scratchpad.dragIndex = null;
        return;
      }
      if (sourceIndex === targetIndex) {
        this.scratchpad.dragIndex = null;
        return;
      }

      const next = [...this.scratchpad.items];
      const [moved] = next.splice(sourceIndex, 1);
      next.splice(targetIndex, 0, moved);
      this.scratchpad.items = next;
      this.scratchpad.dragIndex = null;
      this.saveScratchpad();
    },
    async copyScratchpadItem(text) {
      const value = String(text || '');
      if (!value) {
        return;
      }
      try {
        if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
          await navigator.clipboard.writeText(value);
          this.statusMessage = 'Copied scratchpad text.';
          return;
        }
      } catch (e) {}

      const textarea = document.createElement('textarea');
      textarea.value = value;
      textarea.setAttribute('readonly', '');
      textarea.style.position = 'absolute';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        this.statusMessage = 'Copied scratchpad text.';
      } catch (e) {
        this.errorMessage = 'Could not copy to clipboard.';
      } finally {
        document.body.removeChild(textarea);
      }
    },
    useScratchpadInCaption(text) {
      const value = String(text || '').trim();
      if (!value) {
        return;
      }
      if (!this.selectedImage) {
        this.errorMessage = 'Select an image in Editor first.';
        return;
      }

      this.uiSection = 'workspace';
      this.mainView = 'editor';
      this.editorView.subTab = 'caption';

      const current = String(this.editorCaptionText || '');
      if (!current.trim()) {
        this.editorCaptionText = value;
      } else if (current.endsWith(' ') || current.endsWith('\n')) {
        this.editorCaptionText = `${current}${value}`;
      } else {
        this.editorCaptionText = `${current}\n${value}`;
      }
      this.statusMessage = 'Inserted scratchpad text into active caption.';
    },
    loadSidebarNotesPrefs() {
      try {
        const data = localStorage.getItem('describeIt.sidebarNotesPrefs');
        if (!data) {
          return;
        }
        const parsed = JSON.parse(data);
        this.sidebarNotes = {
          pinnedProjectIds: Array.isArray(parsed?.pinnedProjectIds) ? parsed.pinnedProjectIds : [],
          pinnedGlobalIds: Array.isArray(parsed?.pinnedGlobalIds) ? parsed.pinnedGlobalIds : [],
          recentProjectIds: Array.isArray(parsed?.recentProjectIds) ? parsed.recentProjectIds : [],
          recentGlobalIds: Array.isArray(parsed?.recentGlobalIds) ? parsed.recentGlobalIds : [],
        };
      } catch (e) {}
    },
    saveSidebarNotesPrefs() {
      try {
        localStorage.setItem('describeIt.sidebarNotesPrefs', JSON.stringify(this.sidebarNotes));
      } catch (e) {}
    },
    isSidebarNotePinned(note, scope = 'project') {
      if (!note?.id) {
        return false;
      }
      const ids = scope === 'global' ? this.sidebarNotes.pinnedGlobalIds : this.sidebarNotes.pinnedProjectIds;
      return ids.includes(note.id);
    },
    isSidebarNoteRecent(note, scope = 'project') {
      if (!note?.id) {
        return false;
      }
      const ids = scope === 'global' ? this.sidebarNotes.recentGlobalIds : this.sidebarNotes.recentProjectIds;
      return ids.includes(note.id);
    },
    toggleSidebarNotePinned(note, scope = 'project') {
      if (!note?.id) {
        return;
      }
      const key = scope === 'global' ? 'pinnedGlobalIds' : 'pinnedProjectIds';
      const ids = Array.isArray(this.sidebarNotes[key]) ? [...this.sidebarNotes[key]] : [];
      if (ids.includes(note.id)) {
        this.sidebarNotes[key] = ids.filter((id) => id !== note.id);
      } else {
        this.sidebarNotes[key] = [note.id, ...ids];
      }
      this.saveSidebarNotesPrefs();
    },
    markSidebarNoteUsed(note, scope = 'project') {
      if (!note?.id) {
        return;
      }
      const key = scope === 'global' ? 'recentGlobalIds' : 'recentProjectIds';
      const ids = Array.isArray(this.sidebarNotes[key]) ? this.sidebarNotes[key].filter((id) => id !== note.id) : [];
      this.sidebarNotes[key] = [note.id, ...ids].slice(0, 100);
      this.saveSidebarNotesPrefs();
    },
    sidebarOrderedNotes(scope = 'project') {
      const items = scope === 'global' ? (this.notes.globalItems || []) : (this.notes.projectItems || []);
      const pinnedIds = scope === 'global' ? this.sidebarNotes.pinnedGlobalIds : this.sidebarNotes.pinnedProjectIds;
      const recentIds = scope === 'global' ? this.sidebarNotes.recentGlobalIds : this.sidebarNotes.recentProjectIds;
      const recentRank = new Map(recentIds.map((id, index) => [id, index]));

      return [...items].sort((a, b) => {
        const aPinned = pinnedIds.includes(a.id) ? 0 : 1;
        const bPinned = pinnedIds.includes(b.id) ? 0 : 1;
        if (aPinned !== bPinned) {
          return aPinned - bPinned;
        }

        const aRecent = recentRank.has(a.id) ? recentRank.get(a.id) : null;
        const bRecent = recentRank.has(b.id) ? recentRank.get(b.id) : null;
        if (aRecent !== null && bRecent !== null && aRecent !== bRecent) {
          return aRecent - bRecent;
        }
        if (aRecent !== null && bRecent === null) {
          return -1;
        }
        if (aRecent === null && bRecent !== null) {
          return 1;
        }

        const aTitle = String(a.title || '').toLowerCase();
        const bTitle = String(b.title || '').toLowerCase();
        return aTitle.localeCompare(bTitle);
      });
    },
    quickChatBackends() {
      return (this.llm.backends || []).filter((item) => item.available);
    },
    quickChatModels() {
      if (!this.quickChat.backend) {
        return [];
      }
      return this.availableModelsForBackend(this.quickChat.backend);
    },
    syncQuickChatSelection() {
      const backends = this.quickChatBackends();
      if (!backends.length) {
        this.quickChat.backend = '';
        this.quickChat.model = '';
        return;
      }

      if (!this.quickChat.backend || !backends.some((item) => item.name === this.quickChat.backend)) {
        this.quickChat.backend = this.llm.backend && backends.some((item) => item.name === this.llm.backend)
          ? this.llm.backend
          : backends[0].name;
      }

      const models = this.quickChatModels();
      if (!models.some((item) => item.name === this.quickChat.model)) {
        this.quickChat.model = this.llm.model && models.some((item) => item.name === this.llm.model)
          ? this.llm.model
          : (models[0]?.name || '');
      }
    },
    onQuickChatBackendChanged() {
      const models = this.quickChatModels();
      this.quickChat.model = models[0]?.name || '';
    },
    async generateQuickChatResponse() {
      this.syncQuickChatSelection();
      if (!this.quickChat.backend || !this.quickChat.model) {
        this.errorMessage = 'Select an available provider and model first.';
        return;
      }
      if (!String(this.quickChat.prompt || '').trim()) {
        this.errorMessage = 'Enter a prompt for Quick LLM Chat.';
        return;
      }
      if (this.quickChat.includeSelectedImage && !this.selectedImage?.id) {
        this.errorMessage = 'Select an image in Editor before enabling image context.';
        return;
      }

      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/generate-note-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            backend: this.quickChat.backend,
            model: this.quickChat.model,
            prompt: this.quickChat.prompt,
            project_path: this.currentProject?.path || null,
            image_id: this.quickChat.includeSelectedImage ? this.selectedImage?.id ?? null : null,
            timeout_seconds: this.settings.llmTimeoutSeconds,
            tools_enabled: [],
            context_urls: [],
            context_files: [],
            include_project_notes: false,
            include_global_notes: false,
            reasoning_mode: 'off',
            reasoning_visibility: 'hidden',
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Quick LLM chat request failed'));
        }
        this.quickChat.response = payload.text || '';
        this.addQuickChatHistoryEntry({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          createdAt: new Date().toISOString(),
          backend: this.quickChat.backend,
          model: this.quickChat.model,
          includeSelectedImage: this.quickChat.includeSelectedImage === true,
          prompt: this.quickChat.prompt,
          response: this.quickChat.response,
        });
        this.statusMessage = `Quick LLM response generated with ${payload.backend || this.quickChat.backend}/${payload.model || this.quickChat.model}.`;
      }, 'quickChatGenerate');
    },
    openQuickChatSaveDialog() {
      const content = String(this.quickChat.response || '').trim();
      if (!content) {
        this.errorMessage = 'Generate a response before saving it as a note.';
        return;
      }
      this.quickChat.saveDialogOpen = true;
      this.$nextTick(() => {
        if (this.$refs.quickChatNoteTitle && typeof this.$refs.quickChatNoteTitle.focus === 'function') {
          this.$refs.quickChatNoteTitle.focus();
        }
      });
    },
    closeQuickChatSaveDialog() {
      this.quickChat.saveDialogOpen = false;
    },
    async saveQuickChatResponseAsNote() {
      const content = String(this.quickChat.response || '').trim();
      if (!content) {
        this.errorMessage = 'Generate a response before saving it as a note.';
        return;
      }
      const scope = this.quickChat.noteScope === 'global' ? 'global' : 'project';
      if (scope === 'project' && !this.currentProject?.path) {
        this.errorMessage = 'Open a project or switch note scope to global.';
        return;
      }

      const fallbackTitle = String(this.quickChat.prompt || '').trim().replace(/\s+/g, ' ').slice(0, 72);
      const title = String(this.quickChat.noteTitle || '').trim() || (fallbackTitle ? (fallbackTitle.length >= 72 ? `${fallbackTitle}...` : fallbackTitle) : 'Quick LLM Chat');
      const tags = String(this.quickChat.noteTags || '').trim();

      await this.withSubmitting(async () => {
        const endpoint = scope === 'global' ? '/api/global-notes/create' : '/api/notes/create';
        const body = {
          title,
          content,
          format: 'markdown',
          tags,
        };
        if (scope === 'project') {
          body.project_path = this.currentProject.path;
        }

        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to save quick chat response as note'));
        }

        if (scope === 'global') {
          await this.loadGlobalNotes();
        } else {
          await this.loadProjectNotes();
        }
        this.quickChat.saveDialogOpen = false;
        this.statusMessage = 'Quick chat response saved as note.';
      }, 'quickChatSaveNote');
    },
    openSidebarNote(note, scope = 'project') {
      if (!note) {
        return;
      }
      this.markSidebarNoteUsed(note, scope);
      this.uiSection = 'workspace';
      this.mainView = 'notes';
      this.notes.scope = scope === 'global' ? 'global' : 'project';
      this.selectNote(note);
    },
    mainView: 'project',
    editorView: {
      subTab: 'caption', // caption, image, batch_tags
      zoomMode: 'fit', // fit, full, percent
      zoomPercent: 100,
    },
    showOpenProject: false,
    showBrowser: false,
    selectedImage: null,
    editorNavigationUseFilteredGrid: false,
    imageTools: {
      showAdvanced: false,
      includeCaptions: true,
      captionCopyMode: 'all_candidates',
      deleteMode: 'soft',
      crop: {
        x: 0,
        y: 0,
        width: '',
        height: '',
        outputName: '',
      },
      scale: {
        mode: 'percent',
        percent: 100,
        width: '',
        height: '',
        keepAspectRatio: true,
        upscale: false,
        outputName: '',
      },
      flipMode: 'horizontal',
      rotateAngle: 90,
      extract: {
        x: 0,
        y: 0,
        width: '',
        height: '',
        outputName: '',
        addSourceReferenceNote: true,
      },
    },
    captionBatch: createDefaultCaptionBatchState(),
    captionTextEdit: createDefaultCaptionTextEditState(),
    tagEditor: {
      activeCaptionId: null,
      tags: [],
      newTagText: '',
      editingTagIndex: null,
      editingTagText: '',
      dragTagIndex: null,
      stats: {
        total_tags: 0,
        total_occurrences: 0,
        top_tags: [],
      },
      statsLoading: false,
      batch: {
        scope: 'included', // included, all, selected
        addInput: '',
        removeInput: '',
        clearConfirm: false,
      },
    },
    editorCaptionText: '',
    newCaptionText: '',
    editingCaptionId: null,
    editingCaptionText: '',
    llm: {
      backends: [],
      backend: '',
      model: '',
      showAllModels: false,
      extraInstructions: '',
      makeActive: true,
      presets: [],
      selectedPresetId: '',
      presetForm: {
        id: null,
        name: '',
        backend: 'ollama',
        modelName: '',
        captionModeStrategy: 'auto',
        systemPrompt: '',
        toolWebSearch: false,
        toolWebFetch: false,
        contextUrlTemplate: '',
        contextFileTemplate: '',
        includeProjectNotes: false,
        includeGlobalNotes: false,
        reasoningMode: 'off',
        reasoningVisibility: 'hidden',
      },
      tools: {
        showPanel: false,
        webSearch: false,
        webFetch: false,
        contextUrl: '',
        contextFile: '',
        includeProjectNotes: false,
        includeGlobalNotes: false,
        reasoningMode: 'off',
        reasoningVisibility: 'hidden',
      },
    },
    batch: createDefaultBatchState(),
    batchPollTimer: null,
    notes: createDefaultNotesState(),
    settings: {
      llmTimeoutSeconds: 120,
      usePresetByDefault: false,
      defaultPresetId: '',
      reopenLastProjectOnStartup: true,
      useNativePathPicker: true,
      showDebugSection: false,
      ollamaBaseUrl: 'http://127.0.0.1:11434',
      lmstudioBaseUrl: 'http://127.0.0.1:1234',
      ollamaTimeoutSeconds: '',
      lmstudioTimeoutSeconds: '',
      ollamaNumCtx: '',
      lmstudioNumCtx: '',
      editorDefaultImageZoomMode: 'fit',
      editorDefaultImageZoomPercent: 100,
      ragEnabled: false,
    },
    rag: {
      enabled: false,
      isRebuildingEmbeddings: false,
      embeddingsStatus: '',
    },
    connectionTest: {
      ollama: null,
      lmstudio: null,
      ollamaTesting: false,
      lmstudioTesting: false,
    },
    imageboards: {
      boards: [],
      credentials: [],
      forms: {},
    },
    imageboardImport: {
      show: false,
      selectedBoard: '',
      query: '',
      sortBy: 'relevance',
      sortDirection: 'desc',
      importCount: 10,
      includeTags: true,
      includeCreatorTags: false,
      skipDuplicates: true,
      ratingFilter: 'any',
      previewImages: [],
      totalAvailable: 0,
      statusMessage: '',
      errorMessage: '',
      searching: false,
      importing: false,
    },
    projectSession: {
      lastProjectPath: '',
      lastProjectDirectory: '',
      reopenLastProject: true,
    },
    statusMessage: '',
    errorMessage: '',
    activeOps: new Set(), // Fine-grained operation tracking (replaces isSubmitting)
    isSubmitting: false, // Kept for backward compatibility
    browser: {
      currentPath: '',
      parentPath: null,
      directories: [],
      dbFiles: [],
      files: [],
      roots: [],
    },
    pathPicker: {
      target: '',
      label: '',
      expects: 'directory',
    },
    panelState: {
      sidebarProject: true,
      sidebarRecentProjects: true,
      sidebarRightBookmarks: true,
      sidebarRightScratchpad: true,
      sidebarRightNotes: true,
      sidebarRightQuickChat: false,
      gridSearch: true,
      editorLLM: false,
      editorImageTools: true,
      editorCaptionCandidates: true,
      editorBatchReplace: false,
      notesList: true,
      notesEditor: true,
      notesAssistant: false,
      ioImport: true,
      ioExport: true,
      batchConfig: true,
      batchTextEdit: true,
      batchProgress: true,
      batchCurrent: true,
      batchHistory: true,
    },
    gridCards: [],
    gridSelectionMode: false,
    selectedGridImageIds: [],
    duplicateCleanup: {
      preview: null,
    },
    loadImagesRequestSeq: 0,
    selectImageRequestSeq: 0,
    keyboard: {
      showShortcutsHelp: false,
      shortcuts: [],
    },
    gridFilter: createDefaultGridFilterState(),
    async init() {
      this.loadColorMode();
      this.loadBookmarks();
      this.loadScratchpad();
      this.loadSidebarNotesPrefs();
      this.loadQuickChatHistory();
      // Initialize keyboard shortcuts
      if (window.DescribeItFeatures && window.DescribeItFeatures.shortcuts) {
        window.DescribeItFeatures.shortcuts.init(this);
        this.keyboard.shortcuts = window.DescribeItFeatures.shortcuts.getDocumentation();
      }

      const deferredStartupTasks = [
        this.loadRecentProjects(true),
        this.loadLLMBackends(true),
        this.loadSettings(true),
        this.loadLLMPresets(true),
        this.loadGlobalNotes(true),
        this.checkRAGStatus(),
        this.loadImageboardSettings(),
      ];
      await Promise.all([
        this.loadHealth(true),
        this.loadProjectSessionState(true),
      ]);
      await this.loadBrowser(this.projectSession.lastProjectDirectory || null, true);
      await this.autoOpenLastProjectIfNeeded();
      await Promise.all(deferredStartupTasks);
    },
    async sleep(ms) {
      const core = window.DescribeItCore || {};
      if (typeof core.sleep === 'function') {
        return core.sleep(ms);
      }
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    async fetchWithRetry(resource, options = {}, retryOptions = {}) {
      const core = window.DescribeItCore || {};
      if (typeof core.fetchWithRetry === 'function') {
        return core.fetchWithRetry(resource, options, retryOptions);
      }

      const attempts = Math.max(1, Number(retryOptions.attempts ?? 1));
      const delayMs = Math.max(0, Number(retryOptions.delayMs ?? 150));
      let lastError = null;

      for (let attempt = 1; attempt <= attempts; attempt += 1) {
        try {
          return await fetch(resource, options);
        } catch (error) {
          lastError = error;
          if (attempt >= attempts) {
            throw error;
          }
          await this.sleep(delayMs * attempt);
        }
      }

      throw lastError || new Error('Request failed');
    },
    formatApiError(payload, fallbackMessage = 'Request failed') {
      const core = window.DescribeItCore || {};
      if (typeof core.formatApiError === 'function') {
        return core.formatApiError(payload, fallbackMessage);
      }

      const detail = payload?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
      if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        if (typeof first === 'string' && first.trim()) {
          return first;
        }
        if (first && typeof first === 'object') {
          const fieldPath = Array.isArray(first.loc) ? first.loc.join('.') : 'field';
          const message = typeof first.msg === 'string' ? first.msg : 'Invalid value';
          return `${fieldPath}: ${message}`;
        }
      }
      if (detail && typeof detail === 'object') {
        return JSON.stringify(detail);
      }
      return fallbackMessage;
    },
    normalizeTimeout(value) {
      const settingsFeature = window.DescribeItFeatures?.settings;
      if (settingsFeature && typeof settingsFeature.normalizeTimeout === 'function') {
        return settingsFeature.normalizeTimeout(value);
      }
      return 120;
    },
    normalizeOptionalTimeout(value) {
      const settingsFeature = window.DescribeItFeatures?.settings;
      if (settingsFeature && typeof settingsFeature.normalizeOptionalTimeout === 'function') {
        return settingsFeature.normalizeOptionalTimeout(value);
      }
      return '';
    },
    normalizeOptionalNumCtx(value) {
      const settingsFeature = window.DescribeItFeatures?.settings;
      if (settingsFeature && typeof settingsFeature.normalizeOptionalNumCtx === 'function') {
        return settingsFeature.normalizeOptionalNumCtx(value);
      }
      return '';
    },
    async loadSettings(isStartup = false) {
      const settingsFeature = window.DescribeItFeatures?.settings;
      if (settingsFeature && typeof settingsFeature.loadSettings === 'function') {
        await settingsFeature.loadSettings(this, isStartup);
        return;
      }
      this.errorMessage = 'Settings module unavailable. Refresh and try again.';
    },
    async saveSettings() {
      const settingsFeature = window.DescribeItFeatures?.settings;
      if (settingsFeature && typeof settingsFeature.saveSettings === 'function') {
        await settingsFeature.saveSettings(this);
        return;
      }
      this.errorMessage = 'Settings module unavailable. Refresh and try again.';
    },
    async loadProjectSessionState(isStartup = false) {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.loadProjectSessionState === 'function') {
        await projectsFeature.loadProjectSessionState(this, isStartup);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    async saveProjectSessionState() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.saveProjectSessionState === 'function') {
        await projectsFeature.saveProjectSessionState(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    async autoOpenLastProjectIfNeeded() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.autoOpenLastProjectIfNeeded === 'function') {
        await projectsFeature.autoOpenLastProjectIfNeeded(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    openSettings(tab = 'general') {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.openSettings === 'function') {
        projectsFeature.openSettings(this, tab);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    openPresetSettings() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.openPresetSettings === 'function') {
        projectsFeature.openPresetSettings(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    openWorkspace() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.openWorkspace === 'function') {
        projectsFeature.openWorkspace(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    showKeyboardShortcutsHelp() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.showKeyboardShortcutsHelp === 'function') {
        uiShellFeature.showKeyboardShortcutsHelp(this);
        return;
      }
      this.keyboard.showShortcutsHelp = true;
    },
    closeKeyboardShortcutsHelp() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.closeKeyboardShortcutsHelp === 'function') {
        uiShellFeature.closeKeyboardShortcutsHelp(this);
        return;
      }
      this.keyboard.showShortcutsHelp = false;
    },
    isTagMode() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.isTagMode === 'function') {
        return uiShellFeature.isTagMode(this);
      }
      return this.currentProject?.caption_mode === 'tags';
    },
    editorSubTabs() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.editorSubTabs === 'function') {
        return uiShellFeature.editorSubTabs(this);
      }
      return [
        { id: 'caption', label: 'Caption' },
        { id: 'image', label: 'Image' },
      ];
    },
    setEditorSubTab(nextTab) {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.setEditorSubTab === 'function') {
        uiShellFeature.setEditorSubTab(this, nextTab);
        return;
      }
      this.editorView.subTab = 'caption';
    },
    ensureEditorSubTab() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.ensureEditorSubTab === 'function') {
        uiShellFeature.ensureEditorSubTab(this);
        return;
      }
      this.editorView.subTab = 'caption';
    },
    batchSubTabs() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.batchSubTabs === 'function') {
        return uiShellFeature.batchSubTabs(this);
      }
      return [
        { id: 'generate', label: 'Generate' },
        { id: 'text_edit', label: 'Text Edit' },
      ];
    },
    setBatchSubTab(nextTab) {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.setBatchSubTab === 'function') {
        uiShellFeature.setBatchSubTab(this, nextTab);
        return;
      }
      this.batch.subTab = 'generate';
    },
    ensureBatchSubTab() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.ensureBatchSubTab === 'function') {
        uiShellFeature.ensureBatchSubTab(this);
        return;
      }
      this.batch.subTab = 'generate';
    },
    normalizeEditorZoomPercent(value) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.normalizeEditorZoomPercent === 'function') {
        return editorFeature.normalizeEditorZoomPercent(this, value);
      }
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) {
        return 100;
      }
      return Math.min(400, Math.max(25, parsed));
    },
    setEditorZoomMode(mode) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.setEditorZoomMode === 'function') {
        editorFeature.setEditorZoomMode(this, mode);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    setEditorZoomPercent(value) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.setEditorZoomPercent === 'function') {
        editorFeature.setEditorZoomPercent(this, value);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    resetEditorZoomToDefault() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.resetEditorZoomToDefault === 'function') {
        editorFeature.resetEditorZoomToDefault(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    editorZoomPresets() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.editorZoomPresets === 'function') {
        return editorFeature.editorZoomPresets(this);
      }
      return [50, 75, 100, 125, 150, 200];
    },
    editorImageClasses() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.editorImageClasses === 'function') {
        return editorFeature.editorImageClasses(this);
      }
      return 'h-auto w-full object-contain mx-auto';
    },
    editorImageStyle() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.editorImageStyle === 'function') {
        return editorFeature.editorImageStyle(this);
      }
      return {};
    },
    tagBatchValidation() {
      if (!this.isTagMode()) {
        return { ok: false, message: 'Tag batch tools are only available in tags mode.' };
      }
      if (this.tagEditor.batch.scope === 'selected' && !this.selectedImage?.id) {
        return { ok: false, message: 'Select an image to run batch operations in selected scope.' };
      }
      return { ok: true, message: '' };
    },
    applyProject(project, options = {}) {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.applyProject === 'function') {
        projectsFeature.applyProject(this, project, options);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    closeProject() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.closeProject === 'function') {
        projectsFeature.closeProject(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    applyImageToolPreset(presetKey) {
      if (!this.selectedImage) {
        return;
      }
      const imgW = Number(this.selectedImage.width) || 0;
      const imgH = Number(this.selectedImage.height) || 0;

      if (presetKey === 'scale50') {
        this.imageTools.scale.mode = 'percent';
        this.imageTools.scale.percent = 50;
        return;
      }

      if (presetKey === 'scale1024fit') {
        this.imageTools.scale.mode = 'dimensions';
        this.imageTools.scale.width = 1024;
        this.imageTools.scale.height = 1024;
        this.imageTools.scale.keepAspectRatio = true;
        this.imageTools.scale.upscale = false;
        return;
      }

      if (presetKey === 'centerSquareCrop' && imgW > 0 && imgH > 0) {
        const side = Math.min(imgW, imgH);
        this.imageTools.crop.width = side;
        this.imageTools.crop.height = side;
        this.imageTools.crop.x = Math.floor((imgW - side) / 2);
        this.imageTools.crop.y = Math.floor((imgH - side) / 2);
        return;
      }

      if (presetKey === 'extractCenterQuarter' && imgW > 0 && imgH > 0) {
        const width = Math.max(1, Math.floor(imgW / 2));
        const height = Math.max(1, Math.floor(imgH / 2));
        this.imageTools.extract.width = width;
        this.imageTools.extract.height = height;
        this.imageTools.extract.x = Math.floor((imgW - width) / 2);
        this.imageTools.extract.y = Math.floor((imgH - height) / 2);
      }
    },
    imageToolValidation(kind) {
      const toInteger = (value) => {
        const n = Number(value);
        return Number.isInteger(n) ? n : null;
      };

      if (kind === 'crop') {
        const x = toInteger(this.imageTools.crop.x);
        const y = toInteger(this.imageTools.crop.y);
        const width = toInteger(this.imageTools.crop.width);
        const height = toInteger(this.imageTools.crop.height);
        if (x === null || y === null || width === null || height === null) {
          return { ok: false, message: 'Crop requires integer x, y, width, and height.' };
        }
        if (x < 0 || y < 0 || width < 1 || height < 1) {
          return { ok: false, message: 'Crop x/y must be >= 0 and width/height must be > 0.' };
        }
        return { ok: true, message: '' };
      }

      if (kind === 'scale') {
        if (this.imageTools.scale.mode === 'percent') {
          const percent = Number(this.imageTools.scale.percent);
          if (!Number.isFinite(percent) || percent <= 0) {
            return { ok: false, message: 'Scale percent must be > 0.' };
          }
          return { ok: true, message: '' };
        }
        const width = toInteger(this.imageTools.scale.width);
        const height = toInteger(this.imageTools.scale.height);
        if (width === null || height === null || width < 1 || height < 1) {
          return { ok: false, message: 'Scale dimensions mode requires width/height integers > 0.' };
        }
        return { ok: true, message: '' };
      }

      if (kind === 'extract') {
        const x = toInteger(this.imageTools.extract.x);
        const y = toInteger(this.imageTools.extract.y);
        const width = toInteger(this.imageTools.extract.width);
        const height = toInteger(this.imageTools.extract.height);
        if (x === null || y === null || width === null || height === null) {
          return { ok: false, message: 'Extract requires integer x, y, width, and height.' };
        }
        if (x < 0 || y < 0 || width < 1 || height < 1) {
          return { ok: false, message: 'Extract x/y must be >= 0 and width/height must be > 0.' };
        }
        return { ok: true, message: '' };
      }

      return { ok: true, message: '' };
    },
    captionBatchValidation() {
      const findText = String(this.captionBatch.query.findText || '').trim();
      if (!findText) {
        return { ok: false, message: 'Find text is required.' };
      }
      if (this.captionBatch.scope.imageScope === 'selected_ids') {
        const raw = String(this.captionBatch.scope.imageIdsText || '').trim();
        if (!raw && !this.selectedImage?.id) {
          return { ok: false, message: 'Provide selected image IDs or choose an image in the grid.' };
        }
      }
      return { ok: true, message: '' };
    },
    filteredGridCards() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.filteredGridCards === 'function') {
        return gridFeature.filteredGridCards(this);
      }
      return Array.isArray(this.gridCards) ? [...this.gridCards] : [];
    },
    gridPageCount() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.gridPageCount === 'function') {
        return gridFeature.gridPageCount(this);
      }
      return 1;
    },
    filteredGridTotal() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.filteredGridTotal === 'function') {
        return gridFeature.filteredGridTotal(this);
      }
      return Array.isArray(this.gridCards) ? this.gridCards.length : 0;
    },
    async toggleGridCardIncluded(imageId) {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.toggleGridCardIncluded === 'function') {
        await gridFeature.toggleGridCardIncluded(this, imageId);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    editorNavigationImages() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.editorNavigationImages === 'function') {
        return editorFeature.editorNavigationImages(this);
      }
      return Array.isArray(this.images) ? this.images : [];
    },
    currentImageIndex() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.currentImageIndex === 'function') {
        return editorFeature.currentImageIndex(this);
      }
      return -1;
    },
    hasPreviousImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.hasPreviousImage === 'function') {
        return editorFeature.hasPreviousImage(this);
      }
      return false;
    },
    hasNextImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.hasNextImage === 'function') {
        return editorFeature.hasNextImage(this);
      }
      return false;
    },
    async goToFirstImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.goToFirstImage === 'function') {
        await editorFeature.goToFirstImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async goToPreviousImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.goToPreviousImage === 'function') {
        await editorFeature.goToPreviousImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async goToNextImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.goToNextImage === 'function') {
        await editorFeature.goToNextImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async goToLastImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.goToLastImage === 'function') {
        await editorFeature.goToLastImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    isGridImageSelected(imageId) {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.isGridImageSelected === 'function') {
        return gridFeature.isGridImageSelected(this, imageId);
      }
      return Array.isArray(this.selectedGridImageIds) && this.selectedGridImageIds.includes(imageId);
    },
    selectedGridCount() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.selectedGridCount === 'function') {
        return gridFeature.selectedGridCount(this);
      }
      return Array.isArray(this.selectedGridImageIds) ? this.selectedGridImageIds.length : 0;
    },
    toggleGridSelectionMode() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.toggleGridSelectionMode === 'function') {
        gridFeature.toggleGridSelectionMode(this);
        return;
      }
      this.gridSelectionMode = !this.gridSelectionMode;
      if (!this.gridSelectionMode) {
        this.selectedGridImageIds = [];
      }
    },
    toggleGridImageSelection(imageId) {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.toggleGridImageSelection === 'function') {
        gridFeature.toggleGridImageSelection(this, imageId);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    selectFilteredGridImages() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.selectFilteredGridImages === 'function') {
        gridFeature.selectFilteredGridImages(this);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    clearGridSelection() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.clearGridSelection === 'function') {
        gridFeature.clearGridSelection(this);
        return;
      }
      this.selectedGridImageIds = [];
    },
    async bulkIncludeSelected() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.bulkIncludeSelected === 'function') {
        await gridFeature.bulkIncludeSelected(this);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    async bulkExcludeSelected() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.bulkExcludeSelected === 'function') {
        await gridFeature.bulkExcludeSelected(this);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    async bulkDuplicateSelected() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.bulkDuplicateSelected === 'function') {
        await gridFeature.bulkDuplicateSelected(this);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    async bulkDeleteSelected() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.bulkDeleteSelected === 'function') {
        await gridFeature.bulkDeleteSelected(this);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    async findDuplicateImages() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.findDuplicateImages === 'function') {
        await gridFeature.findDuplicateImages(this);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    async applyDuplicateCleanup(mode = 'soft') {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.applyDuplicateCleanup === 'function') {
        await gridFeature.applyDuplicateCleanup(this, mode);
        return;
      }
      this.errorMessage = 'Grid module unavailable. Refresh and try again.';
    },
    clearDuplicateCleanupPreview() {
      const gridFeature = window.DescribeItFeatures?.grid;
      if (gridFeature && typeof gridFeature.clearDuplicateCleanupPreview === 'function') {
        gridFeature.clearDuplicateCleanupPreview(this);
        return;
      }
      this.duplicateCleanup.preview = null;
    },
    notesActiveItems() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.notesActiveItems === 'function') {
        return notesFeature.notesActiveItems(this);
      }
      return [];
    },
    newNoteDraft() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.newNoteDraft === 'function') {
        notesFeature.newNoteDraft(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    selectNote(note) {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.selectNote === 'function') {
        notesFeature.selectNote(this, note);
        if (note?.id) {
          this.markSidebarNoteUsed(note, this.notes.scope === 'global' ? 'global' : 'project');
        }
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async loadProjectNotes(isStartup = false) {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.loadProjectNotes === 'function') {
        await notesFeature.loadProjectNotes(this, isStartup);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async loadGlobalNotes(isStartup = false) {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.loadGlobalNotes === 'function') {
        await notesFeature.loadGlobalNotes(this, isStartup);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async refreshNotes() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.refreshNotes === 'function') {
        await notesFeature.refreshNotes(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async onNotesScopeChanged() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.onNotesScopeChanged === 'function') {
        await notesFeature.onNotesScopeChanged(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async onNotesArchivedFilterChanged() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.onNotesArchivedFilterChanged === 'function') {
        await notesFeature.onNotesArchivedFilterChanged(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async saveNote() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.saveNote === 'function') {
        await notesFeature.saveNote(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async deleteNote() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.deleteNote === 'function') {
        await notesFeature.deleteNote(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    selectedNoteLLMBackend() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.selectedNoteLLMBackend === 'function') {
        return notesFeature.selectedNoteLLMBackend(this);
      }
      return null;
    },
    selectedNoteLLMModel() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.selectedNoteLLMModel === 'function') {
        return notesFeature.selectedNoteLLMModel(this);
      }
      return null;
    },
    availableModelsForNoteLLM() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.availableModelsForNoteLLM === 'function') {
        return notesFeature.availableModelsForNoteLLM(this);
      }
      return [];
    },
    onNotesLLMBackendChanged() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.onNotesLLMBackendChanged === 'function') {
        notesFeature.onNotesLLMBackendChanged(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    syncNotesLLMSelection() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.syncNotesLLMSelection === 'function') {
        notesFeature.syncNotesLLMSelection(this);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    buildGeneratedNoteTitle() {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.buildGeneratedNoteTitle === 'function') {
        return notesFeature.buildGeneratedNoteTitle(this);
      }
      return 'LLM Note';
    },
    async generateNoteWithLLM(saveAsNewNote = false) {
      const notesFeature = window.DescribeItFeatures?.notes;
      if (notesFeature && typeof notesFeature.generateNoteWithLLM === 'function') {
        await notesFeature.generateNoteWithLLM(this, saveAsNewNote);
        return;
      }
      this.errorMessage = 'Notes module unavailable. Refresh and try again.';
    },
    async loadHealth(isStartup = false) {
      try {
        const response = await this.fetchWithRetry('/api/health', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        this.healthLabel = payload.status;
      } catch (error) {
        this.healthLabel = 'offline';
      }
    },
    async loadRecentProjects(isStartup = false) {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.loadRecentProjects === 'function') {
        await projectsFeature.loadRecentProjects(this, isStartup);
        return;
      }
      this.recentProjects = [];
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    async loadBrowser(path = null, isStartup = false) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.loadBrowser === 'function') {
        await browserFeature.loadBrowser(this, path, isStartup);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    async openPathPicker(target) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.openPathPicker === 'function') {
        await browserFeature.openPathPicker(this, target);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    pathPickerStartPath(target) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.pathPickerStartPath === 'function') {
        return browserFeature.pathPickerStartPath(this, target);
      }
      return '';
    },
    async requestNativePathPicker(config, startPath = '') {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.requestNativePathPicker === 'function') {
        return browserFeature.requestNativePathPicker(this, config, startPath);
      }
      return {
        available: false,
        selected_path: '',
        reason: 'Browser module unavailable. Refresh and try again.',
      };
    },
    browsePickerModeLabel() {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.browsePickerModeLabel === 'function') {
        return browserFeature.browsePickerModeLabel(this);
      }
      return this.settings.useNativePathPicker ? 'Native' : 'Browser';
    },
    isPanelOpen(panelKey, fallback = true) {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.isPanelOpen === 'function') {
        return uiShellFeature.isPanelOpen(this, panelKey, fallback);
      }
      if (Object.prototype.hasOwnProperty.call(this.panelState, panelKey)) {
        return this.panelState[panelKey] === true;
      }
      return fallback;
    },
    togglePanel(panelKey, fallback = true) {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.togglePanel === 'function') {
        uiShellFeature.togglePanel(this, panelKey, fallback);
        return;
      }
      const current = this.isPanelOpen(panelKey, fallback);
      this.panelState[panelKey] = !current;
    },
    panelTriangle(panelKey, fallback = true) {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.panelTriangle === 'function') {
        return uiShellFeature.panelTriangle(this, panelKey, fallback);
      }
      return this.isPanelOpen(panelKey, fallback) ? '▼' : '▶';
    },
    applyPanelStateFromSettings(panelStatePayload) {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.applyPanelStateFromSettings === 'function') {
        uiShellFeature.applyPanelStateFromSettings(this, panelStatePayload);
        return;
      }
      if (!panelStatePayload || typeof panelStatePayload !== 'object') {
        return;
      }
      const nextPanelState = { ...this.panelState };
      Object.keys(this.panelState).forEach((key) => {
        if (Object.prototype.hasOwnProperty.call(panelStatePayload, key)) {
          nextPanelState[key] = panelStatePayload[key] === true;
        }
      });
      this.panelState = nextPanelState;
    },
    panelStatePayload() {
      const uiShellFeature = window.DescribeItFeatures?.uiShell;
      if (uiShellFeature && typeof uiShellFeature.panelStatePayload === 'function') {
        return uiShellFeature.panelStatePayload(this);
      }
      const payload = {};
      Object.keys(this.panelState).forEach((key) => {
        payload[key] = this.panelState[key] === true;
      });
      return payload;
    },
    clearPathPicker() {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.clearPathPicker === 'function') {
        browserFeature.clearPathPicker(this);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    pickerExpectsDirectory() {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.pickerExpectsDirectory === 'function') {
        return browserFeature.pickerExpectsDirectory(this);
      }
      return false;
    },
    pickerExpectsFile() {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.pickerExpectsFile === 'function') {
        return browserFeature.pickerExpectsFile(this);
      }
      return false;
    },
    pickerAcceptsFile(fileKind = 'file') {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.pickerAcceptsFile === 'function') {
        return browserFeature.pickerAcceptsFile(this, fileKind);
      }
      return false;
    },
    updateLastDirectoryFromPath(path, isFile = false) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.updateLastDirectoryFromPath === 'function') {
        browserFeature.updateLastDirectoryFromPath(this, path, isFile);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    useCurrentBrowserDirectory() {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.useCurrentBrowserDirectory === 'function') {
        browserFeature.useCurrentBrowserDirectory(this);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    useBrowserFile(path, fileKind = 'file') {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.useBrowserFile === 'function') {
        browserFeature.useBrowserFile(this, path, fileKind);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    applyPathPickerSelection(path, kind) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.applyPathPickerSelection === 'function') {
        browserFeature.applyPathPickerSelection(this, path, kind);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    chooseCreateDirectory(path) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.chooseCreateDirectory === 'function') {
        browserFeature.chooseCreateDirectory(this, path);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    chooseOpenFile(path) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.chooseOpenFile === 'function') {
        browserFeature.chooseOpenFile(this, path);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    chooseExportDirectory(path) {
      const browserFeature = window.DescribeItFeatures?.browser;
      if (browserFeature && typeof browserFeature.chooseExportDirectory === 'function') {
        browserFeature.chooseExportDirectory(this, path);
        return;
      }
      this.errorMessage = 'Browser module unavailable. Refresh and try again.';
    },
    clearExportPreview() {
      const exportFeature = window.DescribeItFeatures?.export;
      if (exportFeature && typeof exportFeature.clearExportPreview === 'function') {
        exportFeature.clearExportPreview(this);
        return;
      }
      this.errorMessage = 'Export module unavailable. Refresh and try again.';
    },
    normalizeExportFormOptions() {
      const exportFeature = window.DescribeItFeatures?.export;
      if (exportFeature && typeof exportFeature.normalizeExportFormOptions === 'function') {
        exportFeature.normalizeExportFormOptions(this);
        return;
      }
      this.errorMessage = 'Export module unavailable. Refresh and try again.';
    },
    async requestExportPreview() {
      const exportFeature = window.DescribeItFeatures?.export;
      if (exportFeature && typeof exportFeature.requestExportPreview === 'function') {
        await exportFeature.requestExportPreview(this);
        return;
      }
      this.errorMessage = 'Export module unavailable. Refresh and try again.';
    },
    // Operation tracking helpers for fine-grained submit blocking
    isActive(key) {
      const core = window.DescribeItCore || {};
      if (typeof core.isActive === 'function') {
        return core.isActive(this, key);
      }
      return this.activeOps.has(key);
    },
    isAnyActive() {
      const core = window.DescribeItCore || {};
      if (typeof core.isAnyActive === 'function') {
        return core.isAnyActive(this);
      }
      return this.activeOps.size > 0;
    },
    async withSubmitting(fn, operationKey = null) {
      const core = window.DescribeItCore || {};
      if (typeof core.withSubmitting === 'function') {
        await core.withSubmitting(this, fn, operationKey);
        return;
      }

      // Support both the old behavior (no key = global flag) and new behavior (with key)
      this.isSubmitting = true;
      if (operationKey) {
        this.activeOps.add(operationKey);
      } else {
        // Fallback: set a non-specific flag when no key provided
        this.activeOps.add('_submitting');
      }
      this.errorMessage = '';
      this.statusMessage = '';
      try {
        await fn();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
        if (operationKey) {
          this.activeOps.delete(operationKey);
        } else {
          this.activeOps.delete('_submitting');
        }
      }
    },
    async createProject() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.createProject === 'function') {
        await projectsFeature.createProject(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    async openProject() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.openProject === 'function') {
        await projectsFeature.openProject(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    async saveMetadata() {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.saveMetadata === 'function') {
        await projectsFeature.saveMetadata(this);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    async openRecentProject(path) {
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.openRecentProject === 'function') {
        await projectsFeature.openRecentProject(this, path);
        return;
      }
      this.errorMessage = 'Projects module unavailable. Refresh and try again.';
    },
    selectedLLMBackend() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.selectedLLMBackend === 'function') {
        return llmFeature.selectedLLMBackend(this);
      }
      return null;
    },
    selectedLLMModel() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.selectedLLMModel === 'function') {
        return llmFeature.selectedLLMModel(this);
      }
      return null;
    },
    modelCapabilityLabel(backendName, modelName) {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.modelCapabilityLabel === 'function') {
        return llmFeature.modelCapabilityLabel(this, backendName, modelName);
      }
      return '';
    },
    modelOptionLabel(modelInfo) {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.modelOptionLabel === 'function') {
        return llmFeature.modelOptionLabel(this, modelInfo);
      }
      return modelInfo?.name || '';
    },
    availableModelsForBackend(backendName) {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.availableModelsForBackend === 'function') {
        return llmFeature.availableModelsForBackend(this, backendName);
      }
      return [];
    },
    onModelVisibilityFilterChanged() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.onModelVisibilityFilterChanged === 'function') {
        llmFeature.onModelVisibilityFilterChanged(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    pickDefaultLLMSelection() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.pickDefaultLLMSelection === 'function') {
        llmFeature.pickDefaultLLMSelection(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async loadLLMBackends(isStartup = false) {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.loadLLMBackends === 'function') {
        await llmFeature.loadLLMBackends(this, isStartup);
        this.syncQuickChatSelection();
        return;
      }
      this.llm.backends = [];
      this.syncQuickChatSelection();
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    onLLMBackendChanged() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.onLLMBackendChanged === 'function') {
        llmFeature.onLLMBackendChanged(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    onPresetBackendChanged() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.onPresetBackendChanged === 'function') {
        llmFeature.onPresetBackendChanged(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    resetPresetForm() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.resetPresetForm === 'function') {
        llmFeature.resetPresetForm(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    applyPresetToForm(preset) {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.applyPresetToForm === 'function') {
        llmFeature.applyPresetToForm(this, preset);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async loadLLMPresets(isStartup = false) {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.loadLLMPresets === 'function') {
        await llmFeature.loadLLMPresets(this, isStartup);
        return;
      }
      this.llm.presets = [];
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async createPreset() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.createPreset === 'function') {
        await llmFeature.createPreset(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async updatePreset() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.updatePreset === 'function') {
        await llmFeature.updatePreset(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async deletePreset() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.deletePreset === 'function') {
        await llmFeature.deletePreset(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    onSelectedPresetChanged() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.onSelectedPresetChanged === 'function') {
        llmFeature.onSelectedPresetChanged(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    batchIsActive() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchIsActive === 'function') {
        return batchFeature.batchIsActive(this);
      }
      return false;
    },
    batchCanPause() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchCanPause === 'function') {
        return batchFeature.batchCanPause(this);
      }
      return false;
    },
    batchCanResume() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchCanResume === 'function') {
        return batchFeature.batchCanResume(this);
      }
      return false;
    },
    batchCanCancel() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchCanCancel === 'function') {
        return batchFeature.batchCanCancel(this);
      }
      return false;
    },
    batchProgressPercent() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchProgressPercent === 'function') {
        return batchFeature.batchProgressPercent(this);
      }
      return 0;
    },
    batchCurrentImageSrc() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchCurrentImageSrc === 'function') {
        return batchFeature.batchCurrentImageSrc(this);
      }
      return '';
    },
    batchResultsExportUrl() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchResultsExportUrl === 'function') {
        return batchFeature.batchResultsExportUrl(this);
      }
      return '';
    },
    filteredBatchHistory() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.filteredBatchHistory === 'function') {
        return batchFeature.filteredBatchHistory(this);
      }
      return [];
    },
    formatBatchTimestamp(value) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.formatBatchTimestamp === 'function') {
        return batchFeature.formatBatchTimestamp(this, value);
      }
      return value ? String(value) : '-';
    },
    batchResultTextPreview(value, maxLength = 120) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.batchResultTextPreview === 'function') {
        return batchFeature.batchResultTextPreview(this, value, maxLength);
      }
      return value ? String(value) : '-';
    },
    selectedBatchPresetTemplate() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.selectedBatchPresetTemplate === 'function') {
        return batchFeature.selectedBatchPresetTemplate(this);
      }
      return '';
    },
    _applyBatchJob(job) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.applyBatchJob === 'function') {
        batchFeature.applyBatchJob(this, job);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    _startBatchPolling(jobId) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.startBatchPolling === 'function') {
        batchFeature.startBatchPolling(this, jobId);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    _stopBatchPollingIfTerminal(status) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.stopBatchPollingIfTerminal === 'function') {
        batchFeature.stopBatchPollingIfTerminal(this, status);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    async loadLatestBatchJob() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.loadLatestBatchJob === 'function') {
        await batchFeature.loadLatestBatchJob(this);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    async loadBatchHistory() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.loadBatchHistory === 'function') {
        await batchFeature.loadBatchHistory(this);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    async loadBatchResults(jobId = null) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.loadBatchResults === 'function') {
        await batchFeature.loadBatchResults(this, jobId);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    async selectBatchJob(jobId) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.selectBatchJob === 'function') {
        await batchFeature.selectBatchJob(this, jobId);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    async pollBatchJob(jobId = null) {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.pollBatchJob === 'function') {
        await batchFeature.pollBatchJob(this, jobId);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    cancelBatchGeneration() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.cancelBatchGeneration === 'function') {
        batchFeature.cancelBatchGeneration(this);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    pauseBatchGeneration() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.pauseBatchGeneration === 'function') {
        batchFeature.pauseBatchGeneration(this);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    resumeBatchGeneration() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.resumeBatchGeneration === 'function') {
        batchFeature.resumeBatchGeneration(this);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    async startBatchGeneration() {
      const batchFeature = window.DescribeItFeatures?.batch;
      if (batchFeature && typeof batchFeature.startBatchGeneration === 'function') {
        await batchFeature.startBatchGeneration(this);
        return;
      }
      this.errorMessage = 'Batch module unavailable. Refresh and try again.';
    },
    applyPresetPreference() {
      const selectedExists = this.llm.presets.some((item) => String(item.id) === String(this.llm.selectedPresetId));
      if (!selectedExists) {
        this.llm.selectedPresetId = '';
      }

      if (!this.settings.usePresetByDefault) {
        return;
      }

      if (!this.settings.defaultPresetId) {
        return;
      }

      const preset = this.llm.presets.find((item) => String(item.id) === String(this.settings.defaultPresetId));
      if (preset && !this.llm.selectedPresetId) {
        this.applyPresetToForm(preset);
      }
    },
    async generateCaptionWithPreset() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.generateCaptionWithPreset === 'function') {
        await llmFeature.generateCaptionWithPreset(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async generateCaptionWithLLM() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.generateCaptionWithLLM === 'function') {
        await llmFeature.generateCaptionWithLLM(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async generateCaptionWithTools() {
      const llmFeature = window.DescribeItFeatures?.llm;
      if (llmFeature && typeof llmFeature.generateCaptionWithTools === 'function') {
        await llmFeature.generateCaptionWithTools(this);
        return;
      }
      this.errorMessage = 'LLM module unavailable. Refresh and try again.';
    },
    async loadImageSummary() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.loadImageSummary === 'function') {
        await editorFeature.loadImageSummary(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async loadImages() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.loadImages === 'function') {
        await editorFeature.loadImages(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async selectImage(imageId, switchToEditor = true) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.selectImage === 'function') {
        await editorFeature.selectImage(this, imageId, switchToEditor);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    imageSrc(imageId) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.imageSrc === 'function') {
        return editorFeature.imageSrc(this, imageId);
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
      return '';
    },
    async toggleIncluded() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.toggleIncluded === 'function') {
        await editorFeature.toggleIncluded(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async saveActiveCaption() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.saveActiveCaption === 'function') {
        await editorFeature.saveActiveCaption(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async refreshActiveTags(silent = false) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.refreshActiveTags === 'function') {
        await editorFeature.refreshActiveTags(this, { silent });
        return;
      }
      if (!silent) {
        this.errorMessage = 'Editor module unavailable. Refresh and try again.';
      }
    },
    async addTagsToActiveCaption() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.addTagsToActiveCaption === 'function') {
        await editorFeature.addTagsToActiveCaption(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async removeTagFromActiveCaption(index) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.removeTagFromActiveCaption === 'function') {
        await editorFeature.removeTagFromActiveCaption(this, index);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    startEditTag(index) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.startEditTag === 'function') {
        editorFeature.startEditTag(this, index);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    cancelEditTag() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.cancelEditTag === 'function') {
        editorFeature.cancelEditTag(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async saveEditedTag(index) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.saveEditedTag === 'function') {
        await editorFeature.saveEditedTag(this, index);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    startTagDrag(index) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.startTagDrag === 'function') {
        editorFeature.startTagDrag(this, index);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async moveTagLeft(index) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.moveTagLeft === 'function') {
        await editorFeature.moveTagLeft(this, index);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async moveTagRight(index) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.moveTagRight === 'function') {
        await editorFeature.moveTagRight(this, index);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async dropTagAt(targetIndex) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.dropTagAt === 'function') {
        await editorFeature.dropTagAt(this, targetIndex);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async loadTagStatistics(silent = false) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.loadTagStatistics === 'function') {
        await editorFeature.loadTagStatistics(this, { silent });
        return;
      }
      if (!silent) {
        this.errorMessage = 'Editor module unavailable. Refresh and try again.';
      }
    },
    async runBatchAddTags() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.runBatchAddTags === 'function') {
        await editorFeature.runBatchAddTags(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async runBatchRemoveTags() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.runBatchRemoveTags === 'function') {
        await editorFeature.runBatchRemoveTags(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async runBatchClearTags() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.runBatchClearTags === 'function') {
        await editorFeature.runBatchClearTags(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async addCaptionCandidate(makeActive = true) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.addCaptionCandidate === 'function') {
        await editorFeature.addCaptionCandidate(this, makeActive);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async setActiveCaption(captionId) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.setActiveCaption === 'function') {
        await editorFeature.setActiveCaption(this, captionId);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    startEditCaption(caption) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.startEditCaption === 'function') {
        editorFeature.startEditCaption(this, caption);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    cancelEditCaption() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.cancelEditCaption === 'function') {
        editorFeature.cancelEditCaption(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async saveEditedCaption(caption) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.saveEditedCaption === 'function') {
        await editorFeature.saveEditedCaption(this, caption);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async deleteCaption(caption) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.deleteCaption === 'function') {
        await editorFeature.deleteCaption(this, caption);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async duplicateImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.duplicateImage === 'function') {
        await editorFeature.duplicateImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async deleteImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.deleteImage === 'function') {
        await editorFeature.deleteImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async cropImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.cropImage === 'function') {
        await editorFeature.cropImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async scaleImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.scaleImage === 'function') {
        await editorFeature.scaleImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async flipImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.flipImage === 'function') {
        await editorFeature.flipImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async rotateImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.rotateImage === 'function') {
        await editorFeature.rotateImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async extractRegionImage() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.extractRegionImage === 'function') {
        await editorFeature.extractRegionImage(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async loadCaptionBatchOperations(silent = false) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.loadCaptionBatchOperations === 'function') {
        await editorFeature.loadCaptionBatchOperations(this, { silent });
        return;
      }
      if (!silent) {
        this.errorMessage = 'Editor module unavailable. Refresh and try again.';
      }
    },
    async previewCaptionBatchReplace() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.previewCaptionBatchReplace === 'function') {
        await editorFeature.previewCaptionBatchReplace(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async applyCaptionBatchReplace() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.applyCaptionBatchReplace === 'function') {
        await editorFeature.applyCaptionBatchReplace(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async undoCaptionBatchReplace(operationId = null) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.undoCaptionBatchReplace === 'function') {
        await editorFeature.undoCaptionBatchReplace(this, operationId);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    clearCaptionBatchPreview() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.clearCaptionBatchPreview === 'function') {
        editorFeature.clearCaptionBatchPreview(this);
        return;
      }
      this.captionBatch.preview = null;
      this.captionBatch.apply.confirm = false;
    },
    captionTextEditProgressPercent(jobKey) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.captionTextEditProgressPercent === 'function') {
        return editorFeature.captionTextEditProgressPercent(this, jobKey);
      }
      return 0;
    },
    async startDeleteEmptyCaptionsJob() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.startDeleteEmptyCaptionsJob === 'function') {
        await editorFeature.startDeleteEmptyCaptionsJob(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async startRemoveTagsJob() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.startRemoveTagsJob === 'function') {
        await editorFeature.startRemoveTagsJob(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    async startAddCommonCaptionJob() {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.startAddCommonCaptionJob === 'function') {
        await editorFeature.startAddCommonCaptionJob(this);
        return;
      }
      this.errorMessage = 'Editor module unavailable. Refresh and try again.';
    },
    clearCaptionTextEditHistory(jobKey) {
      const editorFeature = window.DescribeItFeatures?.editor;
      if (editorFeature && typeof editorFeature.clearCaptionTextEditHistory === 'function') {
        editorFeature.clearCaptionTextEditHistory(this, jobKey);
        return;
      }
      if (this.captionTextEdit?.history && Array.isArray(this.captionTextEdit.history[jobKey])) {
        this.captionTextEdit.history[jobKey] = [];
      }
    },
    async importFolder() {
      const importFeature = window.DescribeItFeatures?.import;
      if (importFeature && typeof importFeature.importFolder === 'function') {
        await importFeature.importFolder(this);
        return;
      }
      this.errorMessage = 'Import module unavailable. Refresh and try again.';
    },
    async importSingleImage() {
      const importFeature = window.DescribeItFeatures?.import;
      if (importFeature && typeof importFeature.importSingleImage === 'function') {
        await importFeature.importSingleImage(this);
        return;
      }
      this.errorMessage = 'Import module unavailable. Refresh and try again.';
    },
    async exportProjectDataset() {
      const exportFeature = window.DescribeItFeatures?.export;
      if (exportFeature && typeof exportFeature.exportProjectDataset === 'function') {
        await exportFeature.exportProjectDataset(this);
        return;
      }
      this.errorMessage = 'Export module unavailable. Refresh and try again.';
    },
    async testConnection(backend) {
      const settingsFeature = window.DescribeItFeatures?.settings;
      if (settingsFeature && typeof settingsFeature.testConnection === 'function') {
        await settingsFeature.testConnection(this, backend);
        return;
      }
      this.errorMessage = 'Settings module unavailable. Refresh and try again.';
    },
    async checkRAGStatus() {
      const ragFeature = window.DescribeItFeatures?.rag;
      if (ragFeature && typeof ragFeature.checkRAGStatus === 'function') {
        await ragFeature.checkRAGStatus(this);
        return;
      }
      this.rag.enabled = false;
      this.errorMessage = 'RAG module unavailable. Refresh and try again.';
    },
    async rebuildEmbeddings() {
      const ragFeature = window.DescribeItFeatures?.rag;
      if (ragFeature && typeof ragFeature.rebuildEmbeddings === 'function') {
        await ragFeature.rebuildEmbeddings(this);
        return;
      }
      this.rag.isRebuildingEmbeddings = false;
      this.rag.embeddingsStatus = 'RAG module unavailable';
      this.errorMessage = 'RAG module unavailable. Refresh and try again.';
    },
    async loadImageboardSettings() {
      const feature = window.DescribeItFeatures?.imageboardSettings;
      if (feature && typeof feature.loadImageboardBoards === 'function') {
        await feature.loadImageboardBoards(this);
        await feature.loadImageboardCredentials(this);
        
        // Initialize forms for each board
        if (!this.imageboards.forms) this.imageboards.forms = {};
        if (this.imageboards.boards && this.imageboards.boards.length > 0) {
          for (const board of this.imageboards.boards) {
            if (!this.imageboards.forms[board.board_id]) {
              this.imageboards.forms[board.board_id] = {
                apiKey: '',
                username: '',
              };
            }
          }
        }
        return;
      }
      this.errorMessage = 'Imageboard settings module unavailable.';
    },
    async saveImageboardCredential(boardId) {
      const feature = window.DescribeItFeatures?.imageboardSettings;
      if (feature && typeof feature.saveImageboardCredentials === 'function') {
        const form = this.imageboards.forms[boardId];
        const success = await feature.saveImageboardCredentials(
          this,
          boardId,
          form.apiKey,
          form.username || null
        );
        
        if (success) {
          // Clear the form after successful save
          form.apiKey = '';
          form.username = '';
        }
        return success;
      }
      this.errorMessage = 'Imageboard settings module unavailable.';
      return false;
    },
    async deleteImageboardCredential(boardId) {
      const feature = window.DescribeItFeatures?.imageboardSettings;
      if (feature && typeof feature.deleteImageboardCredentials === 'function') {
        const confirmed = confirm(`Are you sure you want to delete credentials for ${boardId}?`);
        if (!confirmed) {
          return;
        }
        
        const success = await feature.deleteImageboardCredentials(this, boardId);
        if (success) {
          // Clear the form after successful deletion
          if (this.imageboards.forms[boardId]) {
            this.imageboards.forms[boardId].apiKey = '';
            this.imageboards.forms[boardId].username = '';
          }
        }
        return;
      }
      this.errorMessage = 'Imageboard settings module unavailable.';
    },

    // ---------- Imageboard Import delegates ----------
    async openImageboardImport() {
      const feature = window.DescribeItFeatures?.imageboardImport;
      if (feature) return feature.openImportModal(this);
      this.errorMessage = 'Imageboard import module unavailable.';
    },
    closeImageboardImport() {
      const feature = window.DescribeItFeatures?.imageboardImport;
      if (feature) return feature.closeImportModal(this);
    },
    imageboardImportSorts() {
      const feature = window.DescribeItFeatures?.imageboardImport;
      return feature ? feature.getSortsForBoard(this) : ['relevance'];
    },
    onImageboardBoardChange() {
      const feature = window.DescribeItFeatures?.imageboardImport;
      if (feature) feature.onBoardChange(this);
    },
    async searchImageboard() {
      const feature = window.DescribeItFeatures?.imageboardImport;
      if (feature) return feature.searchBoard(this);
      this.errorMessage = 'Imageboard import module unavailable.';
    },
    async doImageboardImport() {
      const feature = window.DescribeItFeatures?.imageboardImport;
      if (feature) return feature.doImport(this);
      this.errorMessage = 'Imageboard import module unavailable.';
    },
  };
}

window.describeItApp = describeItApp;
