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
      replace_existing: false,
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
    images: [],
    mainView: 'grid',
    sidebarMode: 'create',
    showOpenProject: false,
    showBrowser: false,
    selectedImage: null,
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
      },
      tools: {
        showPanel: false,
        webSearch: false,
        webFetch: false,
        contextUrl: '',
        contextFile: '',
        includeProjectNotes: false,
        includeGlobalNotes: false,
      },
    },
    batch: {
      target: 'included',
      usePreset: true,
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
    },
    batchPollTimer: null,
    notes: {
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
      },
    },
    settings: {
      llmTimeoutSeconds: 120,
      usePresetByDefault: false,
      defaultPresetId: '',
      reopenLastProjectOnStartup: true,
      showDebugSection: false,
      ollamaBaseUrl: 'http://127.0.0.1:11434',
      lmstudioBaseUrl: 'http://127.0.0.1:1234',
      ollamaTimeoutSeconds: '',
      lmstudioTimeoutSeconds: '',
      ollamaNumCtx: '',
      lmstudioNumCtx: '',
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
    projectSession: {
      lastProjectPath: '',
      lastProjectDirectory: '',
      reopenLastProject: true,
    },
    statusMessage: '',
    errorMessage: '',
    isSubmitting: false,
    browser: {
      currentPath: '',
      parentPath: null,
      directories: [],
      dbFiles: [],
      roots: [],
    },
    gridCards: [],
    async init() {
      await Promise.all([
        this.loadHealth(true),
        this.loadRecentProjects(true),
        this.loadLLMBackends(true),
        this.loadSettings(true),
        this.loadLLMPresets(true),
        this.loadGlobalNotes(true),
        this.loadProjectSessionState(true),
        this.checkRAGStatus(),
      ]);
      await this.loadBrowser(this.projectSession.lastProjectDirectory || null, true);
      await this.autoOpenLastProjectIfNeeded();
    },
    async sleep(ms) {
      return new Promise((resolve) => setTimeout(resolve, ms));
    },
    async fetchWithRetry(resource, options = {}, retryOptions = {}) {
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
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) {
        return 120;
      }
      return Math.min(900, Math.max(10, parsed));
    },
    normalizeOptionalTimeout(value) {
      if (value === '' || value === null || value === undefined) {
        return '';
      }
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) {
        return '';
      }
      return Math.min(900, Math.max(10, parsed));
    },
    normalizeOptionalNumCtx(value) {
      if (value === '' || value === null || value === undefined) {
        return '';
      }
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) {
        return '';
      }
      return Math.min(262144, Math.max(256, parsed));
    },
    async loadSettings(isStartup = false) {
      try {
        const response = await this.fetchWithRetry('/api/llm/settings', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load settings');
        }
        this.settings.llmTimeoutSeconds = this.normalizeTimeout(payload.llm_timeout_seconds);
        this.settings.usePresetByDefault = payload.llm_use_preset_by_default === true;
        this.settings.defaultPresetId = payload.llm_default_preset_id ? String(payload.llm_default_preset_id) : '';
        this.settings.showDebugSection = payload.ui_show_debug_section === true;
        this.settings.ollamaBaseUrl = payload.ollama_base_url || 'http://127.0.0.1:11434';
        this.settings.lmstudioBaseUrl = payload.lmstudio_base_url || 'http://127.0.0.1:1234';
        this.settings.ollamaTimeoutSeconds = this.normalizeOptionalTimeout(payload.ollama_timeout_seconds);
        this.settings.lmstudioTimeoutSeconds = this.normalizeOptionalTimeout(payload.lmstudio_timeout_seconds);
        this.settings.ollamaNumCtx = this.normalizeOptionalNumCtx(payload.ollama_num_ctx);
        this.settings.lmstudioNumCtx = this.normalizeOptionalNumCtx(payload.lmstudio_num_ctx);
        this.applyPresetPreference();
      } catch (error) {
        this.settings.llmTimeoutSeconds = 120;
        this.settings.usePresetByDefault = false;
        this.settings.defaultPresetId = '';
        this.settings.showDebugSection = false;
        this.settings.ollamaBaseUrl = 'http://127.0.0.1:11434';
        this.settings.lmstudioBaseUrl = 'http://127.0.0.1:1234';
        this.settings.ollamaTimeoutSeconds = '';
        this.settings.lmstudioTimeoutSeconds = '';
        this.settings.ollamaNumCtx = '';
        this.settings.lmstudioNumCtx = '';
      }
    },
    async saveSettings() {
      this.settings.llmTimeoutSeconds = this.normalizeTimeout(this.settings.llmTimeoutSeconds);
      this.settings.ollamaTimeoutSeconds = this.normalizeOptionalTimeout(this.settings.ollamaTimeoutSeconds);
      this.settings.lmstudioTimeoutSeconds = this.normalizeOptionalTimeout(this.settings.lmstudioTimeoutSeconds);
      this.settings.ollamaNumCtx = this.normalizeOptionalNumCtx(this.settings.ollamaNumCtx);
      this.settings.lmstudioNumCtx = this.normalizeOptionalNumCtx(this.settings.lmstudioNumCtx);
      const defaultPresetId = this.settings.defaultPresetId ? Number(this.settings.defaultPresetId) : null;
      const ollamaTimeoutSeconds = this.settings.ollamaTimeoutSeconds === '' ? null : Number(this.settings.ollamaTimeoutSeconds);
      const lmstudioTimeoutSeconds = this.settings.lmstudioTimeoutSeconds === '' ? null : Number(this.settings.lmstudioTimeoutSeconds);
      const ollamaNumCtx = this.settings.ollamaNumCtx === '' ? null : Number(this.settings.ollamaNumCtx);
      const lmstudioNumCtx = this.settings.lmstudioNumCtx === '' ? null : Number(this.settings.lmstudioNumCtx);
      try {
        const response = await fetch('/api/llm/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            llm_timeout_seconds: this.settings.llmTimeoutSeconds,
            llm_use_preset_by_default: this.settings.usePresetByDefault,
            llm_default_preset_id: defaultPresetId,
            ui_show_debug_section: this.settings.showDebugSection,
            ollama_base_url: this.settings.ollamaBaseUrl,
            lmstudio_base_url: this.settings.lmstudioBaseUrl,
            ollama_timeout_seconds: ollamaTimeoutSeconds,
            lmstudio_timeout_seconds: lmstudioTimeoutSeconds,
            ollama_num_ctx: ollamaNumCtx,
            lmstudio_num_ctx: lmstudioNumCtx,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to save settings');
        }
        this.settings.llmTimeoutSeconds = this.normalizeTimeout(payload.llm_timeout_seconds);
        this.settings.usePresetByDefault = payload.llm_use_preset_by_default === true;
        this.settings.defaultPresetId = payload.llm_default_preset_id ? String(payload.llm_default_preset_id) : '';
        this.settings.showDebugSection = payload.ui_show_debug_section === true;
        this.settings.ollamaBaseUrl = payload.ollama_base_url || 'http://127.0.0.1:11434';
        this.settings.lmstudioBaseUrl = payload.lmstudio_base_url || 'http://127.0.0.1:1234';
        this.settings.ollamaTimeoutSeconds = this.normalizeOptionalTimeout(payload.ollama_timeout_seconds);
        this.settings.lmstudioTimeoutSeconds = this.normalizeOptionalTimeout(payload.lmstudio_timeout_seconds);
        this.settings.ollamaNumCtx = this.normalizeOptionalNumCtx(payload.ollama_num_ctx);
        this.settings.lmstudioNumCtx = this.normalizeOptionalNumCtx(payload.lmstudio_num_ctx);
        this.projectSession.reopenLastProject = this.settings.reopenLastProjectOnStartup;
        await this.saveProjectSessionState();
        this.applyPresetPreference();
        this.statusMessage = `Saved settings. LLM timeout set to ${this.settings.llmTimeoutSeconds}s.`;
        this.errorMessage = '';
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadProjectSessionState(isStartup = false) {
      try {
        const response = await this.fetchWithRetry('/api/projects/session-state', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load project session state');
        }
        this.projectSession.lastProjectPath = payload.last_project_path || '';
        this.projectSession.lastProjectDirectory = payload.last_project_directory || '';
        this.projectSession.reopenLastProject = payload.reopen_last_project !== false;
        this.settings.reopenLastProjectOnStartup = this.projectSession.reopenLastProject;
      } catch (error) {
        this.projectSession.lastProjectPath = '';
        this.projectSession.lastProjectDirectory = '';
        this.projectSession.reopenLastProject = true;
        this.settings.reopenLastProjectOnStartup = true;
      }
    },
    async saveProjectSessionState() {
      try {
        await fetch('/api/projects/session-state', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            last_project_path: this.projectSession.lastProjectPath,
            last_project_directory: this.projectSession.lastProjectDirectory,
            reopen_last_project: this.projectSession.reopenLastProject,
          }),
        });
      } catch (error) {
        // Ignore persistence errors to avoid interrupting normal UI interactions.
      }
    },
    async autoOpenLastProjectIfNeeded() {
      if (!this.projectSession.reopenLastProject || !this.projectSession.lastProjectPath) {
        return;
      }
      this.openForm.path = this.projectSession.lastProjectPath;
      try {
        const response = await fetch('/api/projects/open', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: this.projectSession.lastProjectPath }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to reopen last project');
        }
        this.applyProject(payload.project, { preserveMainView: true });
        await this.loadRecentProjects();
        this.statusMessage = `Reopened last project ${payload.project.name}.`;
      } catch (error) {
        this.projectSession.lastProjectPath = '';
        await this.saveProjectSessionState();
      }
    },
    openSettings() {
      this.uiSection = 'settings';
      this.errorMessage = '';
      this.statusMessage = '';
      this.checkRAGStatus();
    },
    openWorkspace() {
      this.uiSection = 'workspace';
    },
    applyProject(project, options = {}) {
      const preserveMainView = options.preserveMainView === true;
      this.currentProject = project;
      if (!preserveMainView) {
        this.mainView = 'grid';
      }
      this.metadataForm = {
        path: project.path,
        name: project.name ?? '',
        description: project.description ?? '',
        trigger_word: project.trigger_word ?? '',
        caption_mode: project.caption_mode ?? 'description',
        context_url: project.context_url ?? '',
        context_file_path: project.context_file_path ?? '',
      };
      this.openForm.path = project.path;
      const lastSeparator = project.path.lastIndexOf('/');
      if (lastSeparator > 0) {
        this.projectSession.lastProjectDirectory = project.path.slice(0, lastSeparator);
      }
      this.projectSession.lastProjectPath = project.path;
      this.projectSession.reopenLastProject = true;
      this.saveProjectSessionState();
      this.selectedImage = null;
      this.editorCaptionText = '';
      this.newCaptionText = '';
      this.resetPresetForm();
      this.loadImageSummary();
      this.loadImages();
      this.loadLatestBatchJob();
      this.loadProjectNotes();
    },
    closeProject() {
      const activeCaption = this.selectedImage?.captions?.find((c) => c.is_active);
      const savedText = activeCaption?.text ?? '';
      if (this.selectedImage && this.editorCaptionText !== savedText) {
        if (!window.confirm('You have unsaved caption changes. Close project anyway?')) {
          return;
        }
      }
      this.currentProject = null;
      this.mainView = 'grid';
      this.selectedImage = null;
      this.images = [];
      this.gridCards = [];
      this.editorCaptionText = '';
      this.newCaptionText = '';
      this.metadataForm = {
        path: '',
        name: '',
        description: '',
        trigger_word: '',
        caption_mode: 'description',
        context_url: '',
        context_file_path: '',
      };
      this.imageSummary = {
        count: 0,
        non_empty_caption_count: 0,
        blank_caption_count: 0,
        previews: [],
      };
      this.projectSession.lastProjectPath = '';
      this.projectSession.reopenLastProject = false;
      this.saveProjectSessionState();
      this.statusMessage = 'Closed current project.';
      this.errorMessage = '';
      if (this.batchPollTimer) {
        clearInterval(this.batchPollTimer);
        this.batchPollTimer = null;
      }
      this.batch.jobId = '';
      this.batch.status = 'idle';
      this.batch.history = [];
      this.batch.historyStatusFilter = 'all';
      this.batch.results = [];
      this.notes.projectItems = [];
      this.notes.selectedNoteId = null;
      this.newNoteDraft();
      this.loadBrowser(this.projectSession.lastProjectDirectory || null);
    },
    notesActiveItems() {
      return this.notes.scope === 'global' ? this.notes.globalItems : this.notes.projectItems;
    },
    newNoteDraft() {
      this.notes.selectedNoteId = null;
      this.notes.editor = {
        id: null,
        title: '',
        content: '',
        format: 'markdown',
        tags: '',
        is_archived: false,
      };
    },
    selectNote(note) {
      if (!note) {
        this.newNoteDraft();
        return;
      }
      this.notes.selectedNoteId = note.id;
      this.notes.editor = {
        id: note.id,
        title: note.title ?? '',
        content: note.content ?? '',
        format: note.format ?? 'markdown',
        tags: note.tags ?? '',
        is_archived: note.is_archived === true,
      };
    },
    async loadProjectNotes(isStartup = false) {
      if (!this.currentProject?.path) {
        this.notes.projectItems = [];
        if (this.notes.scope === 'project') {
          this.newNoteDraft();
        }
        return;
      }
      try {
        const url = new URL('/api/notes', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        url.searchParams.set('include_archived', this.notes.includeArchived ? 'true' : 'false');
        const response = await this.fetchWithRetry(url, {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to load project notes'));
        }
        this.notes.projectItems = payload.notes ?? [];
        const selected = this.notes.projectItems.find((item) => item.id === this.notes.selectedNoteId);
        if (selected) {
          this.selectNote(selected);
        } else if (this.notes.scope === 'project') {
          this.newNoteDraft();
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadGlobalNotes(isStartup = false) {
      try {
        const url = new URL('/api/global-notes', window.location.origin);
        url.searchParams.set('include_archived', this.notes.includeArchived ? 'true' : 'false');
        const response = await this.fetchWithRetry(url, {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to load global notes'));
        }
        this.notes.globalItems = payload.notes ?? [];
        const selected = this.notes.globalItems.find((item) => item.id === this.notes.selectedNoteId);
        if (selected) {
          this.selectNote(selected);
        } else if (this.notes.scope === 'global') {
          this.newNoteDraft();
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async refreshNotes() {
      if (this.notes.scope === 'global') {
        await this.loadGlobalNotes();
      } else {
        await this.loadProjectNotes();
      }
    },
    async onNotesScopeChanged() {
      this.newNoteDraft();
      await this.refreshNotes();
    },
    async onNotesArchivedFilterChanged() {
      await this.refreshNotes();
    },
    async saveNote() {
      if (this.notes.scope === 'project' && !this.currentProject?.path) {
        this.errorMessage = 'Open a project to create project notes.';
        return;
      }
      await this.withSubmitting(async () => {
        const isUpdate = !!this.notes.editor.id;
        const endpoint = this.notes.scope === 'global'
          ? (isUpdate ? '/api/global-notes/update' : '/api/global-notes/create')
          : (isUpdate ? '/api/notes/update' : '/api/notes/create');

        const body = {
          title: this.notes.editor.title,
          content: this.notes.editor.content,
          format: this.notes.editor.format,
          tags: this.notes.editor.tags,
        };
        if (isUpdate) {
          body.is_archived = this.notes.editor.is_archived;
          if (this.notes.scope === 'global') {
            body.note_id = this.notes.editor.id;
          } else {
            body.note_id = this.notes.editor.id;
            body.project_path = this.currentProject.path;
          }
        } else if (this.notes.scope === 'project') {
          body.project_path = this.currentProject.path;
        }

        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to save note'));
        }
        const savedNote = payload.note;
        await this.refreshNotes();
        this.selectNote(savedNote);
        this.statusMessage = isUpdate ? 'Note updated.' : 'Note created.';
      });
    },
    async deleteNote() {
      if (!this.notes.editor.id) {
        this.errorMessage = 'Select a note to delete.';
        return;
      }
      if (!window.confirm('Delete this note? This cannot be undone.')) {
        return;
      }
      if (this.notes.scope === 'project' && !this.currentProject?.path) {
        this.errorMessage = 'Open a project to delete project notes.';
        return;
      }
      await this.withSubmitting(async () => {
        const endpoint = this.notes.scope === 'global' ? '/api/global-notes/delete' : '/api/notes/delete';
        const body = this.notes.scope === 'global'
          ? { note_id: this.notes.editor.id }
          : { project_path: this.currentProject.path, note_id: this.notes.editor.id };
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to delete note'));
        }
        await this.refreshNotes();
        this.newNoteDraft();
        this.statusMessage = 'Note deleted.';
      });
    },
    selectedNoteLLMBackend() {
      return this.llm.backends.find((item) => item.name === this.notes.llm.backend) || null;
    },
    selectedNoteLLMModel() {
      const backend = this.selectedNoteLLMBackend();
      if (!backend) {
        return null;
      }
      return backend.models?.find((item) => item.name === this.notes.llm.model) || null;
    },
    availableModelsForNoteLLM() {
      if (!this.notes.llm.backend) {
        return [];
      }
      return this.availableModelsForBackend(this.notes.llm.backend);
    },
    onNotesLLMBackendChanged() {
      const models = this.availableModelsForNoteLLM();
      this.notes.llm.model = models[0]?.name ?? '';
    },
    syncNotesLLMSelection() {
      if (!this.llm.backends.length) {
        this.notes.llm.backend = '';
        this.notes.llm.model = '';
        return;
      }
      if (!this.notes.llm.backend || !this.llm.backends.some((item) => item.name === this.notes.llm.backend)) {
        this.notes.llm.backend = this.llm.backend || this.llm.backends[0].name;
      }
      const models = this.availableModelsForNoteLLM();
      if (!models.some((item) => item.name === this.notes.llm.model)) {
        this.notes.llm.model = models[0]?.name ?? '';
      }
    },
    buildGeneratedNoteTitle() {
      const explicit = this.notes.llm.title.trim();
      if (explicit) {
        return explicit;
      }
      const source = this.notes.llm.prompt.trim();
      if (!source) {
        return 'LLM Note';
      }
      const oneLine = source.replace(/\s+/g, ' ').trim();
      return oneLine.length > 72 ? `${oneLine.slice(0, 72).trimEnd()}...` : oneLine;
    },
    async generateNoteWithLLM(saveAsNewNote = false) {
      if (!this.notes.llm.prompt.trim()) {
        this.errorMessage = 'Enter a prompt for note generation.';
        return;
      }
      this.syncNotesLLMSelection();
      if (!this.notes.llm.backend || !this.notes.llm.model) {
        this.errorMessage = 'Select an available backend and model first.';
        return;
      }
      if (this.notes.scope === 'project' && !this.currentProject?.path) {
        this.errorMessage = 'Open a project to generate project notes.';
        return;
      }
      if (this.notes.llm.useSelectedImage && !this.selectedImage?.id) {
        this.errorMessage = 'Select an image in the editor tab before enabling image context.';
        return;
      }

      const toolsEnabled = [];
      if (this.notes.llm.webSearch) toolsEnabled.push('web_search');
      if (this.notes.llm.webFetch) toolsEnabled.push('web_fetch');
      const selectedModel = this.selectedNoteLLMModel();
      let fallbackNotice = '';
      if (toolsEnabled.length > 0 && selectedModel && !selectedModel.tool_capable) {
        toolsEnabled.length = 0;
        fallbackNotice = ` Model ${this.notes.llm.model} is not tool-capable, so tools were skipped.`;
      }

      const projectPath = this.currentProject?.path || null;
      const contextUrls = this.notes.llm.contextUrl.trim() ? [this.notes.llm.contextUrl.trim()] : [];
      const contextFiles = this.notes.llm.contextFile.trim() ? [this.notes.llm.contextFile.trim()] : [];

      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/generate-note-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            backend: this.notes.llm.backend,
            model: this.notes.llm.model,
            prompt: this.notes.llm.prompt,
            project_path: projectPath,
            image_id: this.notes.llm.useSelectedImage ? this.selectedImage?.id ?? null : null,
            timeout_seconds: this.settings.llmTimeoutSeconds,
            tools_enabled: toolsEnabled,
            context_urls: contextUrls,
            context_files: contextFiles,
            include_project_notes: this.notes.llm.includeProjectNotes,
            include_global_notes: this.notes.llm.includeGlobalNotes,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Note generation failed'));
        }

        const generatedText = payload.text || '';
        const generatedTitle = this.buildGeneratedNoteTitle();
        const generatedTags = this.notes.llm.tags.trim();
        const generatedFormat = this.notes.llm.outputFormat === 'text' ? 'text' : 'markdown';

        this.notes.editor.title = generatedTitle;
        this.notes.editor.content = generatedText;
        this.notes.editor.format = generatedFormat;
        this.notes.editor.tags = generatedTags;

        const log = payload.tool_usage_log?.length ? ` (${payload.tool_usage_log.length} tool/context event(s))` : '';
        const modeMap = {
          tool_calls: 'Mode: Tool Calls',
          context_injection: 'Mode: Context Injection',
        };
        const modeLabel = modeMap[payload.generation_mode] || `Mode: ${payload.generation_mode || 'unknown'}`;

        if (!saveAsNewNote) {
          this.statusMessage = `Generated note draft with ${payload.backend}/${payload.model}${log}. ${modeLabel}.${fallbackNotice}`;
          return;
        }

        const endpoint = this.notes.scope === 'global' ? '/api/global-notes/create' : '/api/notes/create';
        const body = {
          title: generatedTitle,
          content: generatedText,
          format: generatedFormat,
          tags: generatedTags,
        };
        if (this.notes.scope === 'project') {
          body.project_path = this.currentProject.path;
        }

        const saveResponse = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const savePayload = await saveResponse.json();
        if (!saveResponse.ok) {
          throw new Error(this.formatApiError(savePayload, 'Failed to save generated note'));
        }

        const savedNote = savePayload.note;
        await this.refreshNotes();
        this.selectNote(savedNote);
        this.statusMessage = `Generated and saved note with ${payload.backend}/${payload.model}${log}. ${modeLabel}.${fallbackNotice}`;
      });
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
      try {
        const response = await this.fetchWithRetry('/api/projects/recent', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        this.recentProjects = payload.projects ?? [];
      } catch (error) {
        this.recentProjects = [];
      }
    },
    async loadBrowser(path = null, isStartup = false) {
      try {
        const url = new URL('/api/projects/browser', window.location.origin);
        if (path) {
          url.searchParams.set('path', path);
        }
        const response = await this.fetchWithRetry(url, {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to browse paths');
        }
        this.browser = {
          currentPath: payload.current_path,
          parentPath: payload.parent_path,
          directories: payload.directories ?? [],
          dbFiles: payload.db_files ?? [],
          roots: payload.roots ?? [],
        };
        this.projectSession.lastProjectDirectory = this.browser.currentPath || this.projectSession.lastProjectDirectory;
        this.saveProjectSessionState();
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    chooseCreateDirectory(path) {
      const trimmedName = (this.createForm.name || 'my_project').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'my_project';
      this.createForm.path = `${path}/${trimmedName}.db`;
      this.projectSession.lastProjectDirectory = path;
      this.saveProjectSessionState();
      this.statusMessage = `Create path set to ${this.createForm.path}`;
      this.errorMessage = '';
    },
    chooseOpenFile(path) {
      this.openForm.path = path;
      const lastSeparator = path.lastIndexOf('/');
      if (lastSeparator > 0) {
        this.projectSession.lastProjectDirectory = path.slice(0, lastSeparator);
      }
      this.saveProjectSessionState();
      this.statusMessage = `Open path set to ${path}`;
      this.errorMessage = '';
    },
    chooseExportDirectory(path) {
      this.exportForm.output_folder = path;
      this.projectSession.lastProjectDirectory = path;
      this.saveProjectSessionState();
      this.exportPreview = null;
      this.statusMessage = `Export folder set to ${path}`;
      this.errorMessage = '';
    },
    clearExportPreview() {
      this.exportPreview = null;
    },
    normalizeExportFormOptions() {
      if (this.exportForm.clean_output_folder && this.exportForm.overwrite_existing) {
        this.exportForm.overwrite_existing = false;
      }
      if (!this.exportForm.create_new_folder) {
        this.exportForm.new_folder_name = '';
      }
    },
    async requestExportPreview() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open or create a project first.';
        return;
      }
      if (!this.exportForm.output_folder.trim()) {
        this.errorMessage = 'Select an export output folder first.';
        return;
      }

      this.normalizeExportFormOptions();
      this.errorMessage = '';
      this.statusMessage = '';
      try {
        const response = await fetch('/api/projects/export-preview', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            output_folder: this.exportForm.output_folder,
            included_only: this.exportForm.included_only,
            apply_trigger_word: this.exportForm.apply_trigger_word,
            create_new_folder: this.exportForm.create_new_folder,
            new_folder_name: this.exportForm.new_folder_name,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Export preview failed');
        }
        this.exportPreview = payload.result;
        this.statusMessage = `Preview ready: ${this.exportPreview.images_to_export} image(s) will be exported.`;
      } catch (error) {
        this.exportPreview = null;
        this.errorMessage = error.message;
      }
    },
    async withSubmitting(fn) {
      this.isSubmitting = true;
      this.errorMessage = '';
      this.statusMessage = '';
      try {
        await fn();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async createProject() {
      await this.withSubmitting(async () => {
        const response = await fetch('/api/projects/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.createForm),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to create project');
        }
        this.applyProject(payload.project);
        this.statusMessage = `Created project ${payload.project.name}`;
        await this.loadRecentProjects();
        await this.loadBrowser(payload.project.path);
      });
    },
    async openProject() {
      await this.withSubmitting(async () => {
        const response = await fetch('/api/projects/open', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.openForm),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to open project');
        }
        this.applyProject(payload.project);
        this.statusMessage = `Opened project ${payload.project.name}`;
        await this.loadRecentProjects();
        await this.loadBrowser(payload.project.path);
      });
    },
    async saveMetadata() {
      await this.withSubmitting(async () => {
        const response = await fetch('/api/projects/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.metadataForm),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to save metadata');
        }
        this.applyProject(payload.project);
        this.statusMessage = `Saved metadata for ${payload.project.name}`;
        await this.loadRecentProjects();
      });
    },
    async openRecentProject(path) {
      this.openForm.path = path;
      await this.openProject();
    },
    selectedLLMBackend() {
      return this.llm.backends.find((item) => item.name === this.llm.backend) || null;
    },
    selectedLLMModel() {
      const backend = this.selectedLLMBackend();
      if (!backend) {
        return null;
      }
      return backend.models?.find((item) => item.name === this.llm.model) || null;
    },
    modelCapabilityLabel(backendName, modelName) {
      const backend = this.llm.backends.find((item) => item.name === backendName);
      const model = backend?.models?.find((item) => item.name === modelName);
      if (!model) {
        return '';
      }
      const icons = [];
      if (model.vision_capable) icons.push('👁️');
      if (model.tool_capable) icons.push('🔨');
      return icons.join(' ');
    },
    modelOptionLabel(modelInfo) {
      if (!modelInfo) {
        return '';
      }
      const icons = [];
      if (modelInfo.vision_capable) icons.push('👁️');
      if (modelInfo.tool_capable) icons.push('🔨');
      return icons.length > 0 ? `${modelInfo.name}  ${icons.join(' ')}` : modelInfo.name;
    },
    availableModelsForBackend(backendName) {
      const backend = this.llm.backends.find((item) => item.name === backendName);
      const models = backend?.models ?? [];
      if (this.llm.showAllModels) {
        return models;
      }
      return models.filter((model) => model.vision_capable);
    },
    onModelVisibilityFilterChanged() {
      this.pickDefaultLLMSelection();
      this.onPresetBackendChanged();
    },
    pickDefaultLLMSelection() {
      const available = this.llm.backends.filter((item) => item.available);
      if (available.length === 0) {
        this.llm.backend = '';
        this.llm.model = '';
        return;
      }
      if (!available.some((item) => item.name === this.llm.backend)) {
        this.llm.backend = available[0].name;
      }

      let models = this.availableModelsForBackend(this.llm.backend);
      if (models.length === 0) {
        const fallbackBackend = available.find((item) => this.availableModelsForBackend(item.name).length > 0);
        if (fallbackBackend) {
          this.llm.backend = fallbackBackend.name;
          models = this.availableModelsForBackend(this.llm.backend);
        }
      }

      if (!models.some((item) => item.name === this.llm.model)) {
        this.llm.model = models[0]?.name ?? '';
      }
    },
    async loadLLMBackends(isStartup = false) {
      try {
        const response = await this.fetchWithRetry('/api/llm/backends', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load LLM backends');
        }
        this.llm.backends = payload.backends ?? [];
        this.pickDefaultLLMSelection();
        this.onPresetBackendChanged();
        this.syncNotesLLMSelection();
      } catch (error) {
        this.llm.backends = [];
        this.errorMessage = error.message;
      }
    },
    onLLMBackendChanged() {
      const models = this.availableModelsForBackend(this.llm.backend);
      this.llm.model = models[0]?.name ?? '';
    },
    onPresetBackendChanged() {
      let models = this.availableModelsForBackend(this.llm.presetForm.backend);
      if (models.length === 0) {
        const backend = this.llm.backends.find((item) => item.name === this.llm.presetForm.backend);
        models = backend?.models ?? [];
      }
      if (!models.some((item) => item.name === this.llm.presetForm.modelName)) {
        this.llm.presetForm.modelName = models[0]?.name ?? '';
      }
    },
    resetPresetForm() {
      this.llm.presetForm = {
        id: null,
        name: '',
        backend: this.llm.backends.some((item) => item.name === 'ollama') ? 'ollama' : (this.llm.backends[0]?.name ?? ''),
        modelName: '',
        captionModeStrategy: 'auto',
        systemPrompt: '',
        toolWebSearch: false,
        toolWebFetch: false,
        contextUrlTemplate: '',
        contextFileTemplate: '',
        includeProjectNotes: false,
        includeGlobalNotes: false,
      };
      this.onPresetBackendChanged();
    },
    applyPresetToForm(preset) {
      this.llm.presetForm = {
        id: preset.id,
        name: preset.name,
        backend: preset.backend,
        modelName: preset.model_name,
        captionModeStrategy: preset.caption_mode_strategy || 'auto',
        systemPrompt: preset.system_prompt ?? '',
        toolWebSearch: preset.tool_web_search === true,
        toolWebFetch: preset.tool_web_fetch === true,
        contextUrlTemplate: preset.context_url_template ?? '',
        contextFileTemplate: preset.context_file_template ?? '',
        includeProjectNotes: preset.include_project_notes === true,
        includeGlobalNotes: preset.include_global_notes === true,
      };
      this.llm.selectedPresetId = String(preset.id);
    },
    async loadLLMPresets(isStartup = false) {
      try {
        const response = await this.fetchWithRetry('/api/llm/presets', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load presets');
        }
        this.llm.presets = payload.presets ?? [];
        if (this.llm.selectedPresetId && !this.llm.presets.some((preset) => String(preset.id) === this.llm.selectedPresetId)) {
          this.llm.selectedPresetId = '';
        }
        if (this.settings.defaultPresetId && !this.llm.presets.some((preset) => String(preset.id) === this.settings.defaultPresetId)) {
          this.settings.defaultPresetId = '';
        }
        this.applyPresetPreference();
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async createPreset() {
      if (!this.llm.presetForm.name.trim()) {
        this.errorMessage = 'Preset name is required.';
        return;
      }
      if (!this.llm.presetForm.backend) {
        this.errorMessage = 'Select a backend for the preset.';
        return;
      }
      if (!this.llm.presetForm.modelName) {
        this.errorMessage = 'Select a model for the preset.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/presets/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.llm.presetForm.name.trim(),
            backend: this.llm.presetForm.backend,
            model_name: this.llm.presetForm.modelName,
            caption_mode_strategy: this.llm.presetForm.captionModeStrategy,
            system_prompt: this.llm.presetForm.systemPrompt,
            tool_web_search: this.llm.presetForm.toolWebSearch,
            tool_web_fetch: this.llm.presetForm.toolWebFetch,
            context_url_template: this.llm.presetForm.contextUrlTemplate,
            context_file_template: this.llm.presetForm.contextFileTemplate,
            include_project_notes: this.llm.presetForm.includeProjectNotes,
            include_global_notes: this.llm.presetForm.includeGlobalNotes,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to create preset'));
        }
        await this.loadLLMPresets();
        this.applyPresetToForm(payload.preset);
        this.statusMessage = `Created preset ${payload.preset.name}.`;
      });
    },
    async updatePreset() {
      if (!this.llm.presetForm.id) {
        this.errorMessage = 'Select a preset to update.';
        return;
      }
      if (!this.llm.presetForm.name.trim()) {
        this.errorMessage = 'Preset name is required.';
        return;
      }
      if (!this.llm.presetForm.backend) {
        this.errorMessage = 'Select a backend for the preset.';
        return;
      }
      if (!this.llm.presetForm.modelName) {
        this.errorMessage = 'Select a model for the preset.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/presets/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            preset_id: this.llm.presetForm.id,
            name: this.llm.presetForm.name.trim(),
            backend: this.llm.presetForm.backend,
            model_name: this.llm.presetForm.modelName,
            caption_mode_strategy: this.llm.presetForm.captionModeStrategy,
            system_prompt: this.llm.presetForm.systemPrompt,
            tool_web_search: this.llm.presetForm.toolWebSearch,
            tool_web_fetch: this.llm.presetForm.toolWebFetch,
            context_url_template: this.llm.presetForm.contextUrlTemplate,
            context_file_template: this.llm.presetForm.contextFileTemplate,
            include_project_notes: this.llm.presetForm.includeProjectNotes,
            include_global_notes: this.llm.presetForm.includeGlobalNotes,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(this.formatApiError(payload, 'Failed to update preset'));
        }
        await this.loadLLMPresets();
        this.applyPresetToForm(payload.preset);
        this.statusMessage = `Updated preset ${payload.preset.name}.`;
      });
    },
    async deletePreset() {
      if (!this.llm.presetForm.id) {
        this.errorMessage = 'Select a preset to delete.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/presets/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            preset_id: this.llm.presetForm.id,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to delete preset');
        }
        await this.loadLLMPresets();
        this.resetPresetForm();
        this.llm.selectedPresetId = '';
        this.statusMessage = `Deleted preset ${payload.deleted_preset_id}.`;
      });
    },
    onSelectedPresetChanged() {
      const preset = this.llm.presets.find((item) => String(item.id) === String(this.llm.selectedPresetId));
      if (preset) {
        this.applyPresetToForm(preset);
      }
    },
    batchIsActive() {
      return ['queued', 'running', 'paused', 'failed'].includes(this.batch.status);
    },
    batchCanPause() {
      return this.batch.status === 'running' || this.batch.status === 'queued';
    },
    batchCanResume() {
      return this.batch.status === 'paused' || this.batch.status === 'failed';
    },
    batchCanCancel() {
      return this.batch.status === 'running' || this.batch.status === 'queued' || this.batch.status === 'paused' || this.batch.status === 'failed';
    },
    batchProgressPercent() {
      if (!this.batch.total) {
        return 0;
      }
      return Math.round((this.batch.completed / this.batch.total) * 100);
    },
    batchCurrentImageSrc() {
      if (!this.batch.currentImageId) {
        return '';
      }
      return this.imageSrc(this.batch.currentImageId);
    },
    batchResultsExportUrl() {
      if (!this.batch.jobId) {
        return '';
      }
      return `/api/llm/batch-jobs/${this.batch.jobId}/results/export`;
    },
    filteredBatchHistory() {
      if (this.batch.historyStatusFilter === 'all') {
        return this.batch.history;
      }
      return this.batch.history.filter((job) => job.status === this.batch.historyStatusFilter);
    },
    formatBatchTimestamp(value) {
      if (!value) {
        return '-';
      }
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) {
        return String(value);
      }
      return parsed.toLocaleString();
    },
    batchResultTextPreview(value, maxLength = 120) {
      if (!value) {
        return '-';
      }
      if (value.length <= maxLength) {
        return value;
      }
      return `${value.slice(0, maxLength - 1)}...`;
    },
    _applyBatchJob(job) {
      this.batch.jobId = job.id || '';
      this.batch.status = job.status || 'idle';
      this.batch.total = Number(job.total || 0);
      this.batch.completed = Number(job.completed || 0);
      this.batch.succeeded = Number(job.succeeded || 0);
      this.batch.failed = Number(job.failed || 0);
      this.batch.currentImageId = job.current_image_id || null;
      this.batch.currentFilename = job.current_filename || '';
      this.batch.currentGeneratedText = job.current_generated_text || '';
      this.batch.lastError = job.last_error || '';
      if (job.target) {
        this.batch.target = job.target;
      }
      if (typeof job.use_preset === 'boolean') {
        this.batch.usePreset = job.use_preset;
      }
      if (job.output_mode) {
        this.batch.outputMode = job.output_mode;
      }
      if (typeof job.skip_on_failure === 'boolean') {
        this.batch.skipOnFailure = job.skip_on_failure;
      }
      if (typeof job.retry_count === 'number') {
        this.batch.retryCount = job.retry_count;
      }
    },
    _startBatchPolling(jobId) {
      if (this.batchPollTimer) {
        clearInterval(this.batchPollTimer);
      }
      this.batchPollTimer = setInterval(() => {
        this.pollBatchJob(jobId);
      }, 1200);
    },
    _stopBatchPollingIfTerminal(status) {
      if (['completed', 'cancelled', 'paused', 'failed'].includes(status)) {
        if (this.batchPollTimer) {
          clearInterval(this.batchPollTimer);
          this.batchPollTimer = null;
        }
      }
    },
    async loadLatestBatchJob() {
      if (!this.currentProject?.path) {
        return;
      }
      try {
        const url = new URL('/api/llm/batch-jobs', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load batch jobs');
        }
        const latest = (payload.jobs || [])[0];
        this.batch.history = payload.jobs || [];
        if (!latest) {
          this.batch.results = [];
          return;
        }
        this._applyBatchJob(latest);
        await this.loadBatchResults(latest.id);
        if (this.batchCanCancel()) {
          this._startBatchPolling(latest.id);
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadBatchHistory() {
      if (!this.currentProject?.path) {
        this.batch.history = [];
        return;
      }
      try {
        const url = new URL('/api/llm/batch-jobs', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load batch jobs');
        }
        this.batch.history = payload.jobs || [];
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadBatchResults(jobId = null) {
      const targetJobId = jobId || this.batch.jobId;
      if (!targetJobId) {
        this.batch.results = [];
        return;
      }
      try {
        const response = await fetch(`/api/llm/batch-jobs/${targetJobId}/results?limit=500`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load batch results');
        }
        this.batch.results = payload.results || [];
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async selectBatchJob(jobId) {
      this.batch.jobId = jobId;
      await this.pollBatchJob(jobId);
      await this.loadBatchHistory();
      await this.loadBatchResults(jobId);
      if (this.batchCanCancel()) {
        this._startBatchPolling(jobId);
      }
    },
    async pollBatchJob(jobId = null) {
      const targetJobId = jobId || this.batch.jobId;
      if (!targetJobId) {
        return;
      }
      try {
        const response = await fetch(`/api/llm/batch-jobs/${targetJobId}`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to poll batch job');
        }
        const job = payload.job;
        this._applyBatchJob(job);
        this._stopBatchPollingIfTerminal(job.status);
        await this.loadBatchResults(job.id);

        if (job.status === 'completed') {
          this.statusMessage = `Batch complete: ${job.succeeded}/${job.total} succeeded, ${job.failed} failed.`;
          await this.loadImages();
          await this.loadImageSummary();
          await this.loadBatchHistory();
        }
        if (job.status === 'cancelled') {
          this.statusMessage = `Batch cancelled: ${job.completed}/${job.total} processed (${job.succeeded} succeeded, ${job.failed} failed).`;
          await this.loadImages();
          await this.loadImageSummary();
          await this.loadBatchHistory();
        }
        if (job.status === 'failed') {
          this.errorMessage = job.last_error || 'Batch failed.';
          this.statusMessage = `Batch failed after ${job.completed}/${job.total} images. You can resume to continue.`;
          await this.loadBatchHistory();
        }
        if (job.status === 'paused') {
          this.statusMessage = `Batch paused at ${job.completed}/${job.total}.`;
          await this.loadBatchHistory();
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    cancelBatchGeneration() {
      if (!this.batch.jobId) {
        return;
      }
      fetch('/api/llm/batch-jobs/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: this.batch.jobId }),
      })
        .then((response) => response.json())
        .then((payload) => {
          if (payload?.job) {
            this._applyBatchJob(payload.job);
          }
          this.statusMessage = 'Cancelling batch after current image...';
          this.loadBatchHistory();
        })
        .catch((error) => {
          this.errorMessage = error.message;
        });
    },
    pauseBatchGeneration() {
      if (!this.batch.jobId) {
        return;
      }
      fetch('/api/llm/batch-jobs/pause', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: this.batch.jobId }),
      })
        .then((response) => response.json())
        .then((payload) => {
          if (payload?.job) {
            this._applyBatchJob(payload.job);
          }
          this.statusMessage = 'Pause requested. Job will pause after current image.';
          this.loadBatchHistory();
        })
        .catch((error) => {
          this.errorMessage = error.message;
        });
    },
    resumeBatchGeneration() {
      if (!this.batch.jobId) {
        return;
      }
      fetch('/api/llm/batch-jobs/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: this.batch.jobId }),
      })
        .then((response) => response.json())
        .then((payload) => {
          if (payload?.job) {
            this._applyBatchJob(payload.job);
            this._startBatchPolling(this.batch.jobId);
          }
          this.statusMessage = 'Batch resumed.';
          this.loadBatchHistory();
        })
        .catch((error) => {
          this.errorMessage = error.message;
        });
    },
    async startBatchGeneration() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open a project first.';
        return;
      }

      this.errorMessage = '';
      this.statusMessage = '';
      if (this.batch.usePreset && !this.llm.selectedPresetId) {
        this.errorMessage = 'Choose a preset before starting batch generation.';
        return;
      }
      if (!this.batch.usePreset && (!this.llm.backend || !this.llm.model)) {
        this.errorMessage = 'Select backend and model before starting manual batch generation.';
        return;
      }

      this.batch.lastError = '';
      this.batch.currentGeneratedText = '';
      this.batch.currentFilename = '';
      this.batch.currentImageId = null;
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/batch-jobs/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            target: this.batch.target,
            use_preset: this.batch.usePreset,
            preset_id: this.batch.usePreset && this.llm.selectedPresetId ? Number(this.llm.selectedPresetId) : null,
            backend: this.batch.usePreset ? '' : this.llm.backend,
            model: this.batch.usePreset ? '' : this.llm.model,
            extra_instructions: this.batch.usePreset ? '' : this.llm.extraInstructions,
            timeout_seconds: this.settings.llmTimeoutSeconds,
            make_active: this.llm.makeActive,
            output_mode: this.batch.outputMode,
            skip_on_failure: this.batch.skipOnFailure,
            retry_count: Number(this.batch.retryCount || 0),
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to start batch job');
        }
        const job = payload.job;
        this._applyBatchJob(job);
        this._startBatchPolling(job.id);
        await this.loadBatchHistory();
        await this.loadBatchResults(job.id);
        this.statusMessage = 'Batch job started.';
      });
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
      if (!this.currentProject?.path || !this.selectedImage) {
        this.errorMessage = 'Open a project and select an image first.';
        return;
      }
      if (!this.llm.selectedPresetId) {
        this.errorMessage = 'Choose a preset first.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/generate-with-preset', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            preset_id: Number(this.llm.selectedPresetId),
            make_active: this.llm.makeActive,
            timeout_seconds: this.settings.llmTimeoutSeconds,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Preset generation failed');
        }
        const modeMap = {
          tool_calls: 'Mode: Tool Calls',
          context_injection: 'Mode: Context Injection',
        };
        const modeLabel = modeMap[payload.preset?.generation_mode] || '';
        const events = payload.preset?.tool_usage_log?.length || 0;
        const eventLabel = events > 0 ? ` (${events} tool/context event(s))` : '';
        this.statusMessage = `Generated caption with preset ${payload.preset.name}${eventLabel}.${modeLabel ? ` ${modeLabel}.` : ''}`;
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async generateCaptionWithLLM() {
      if (!this.currentProject?.path || !this.selectedImage) {
        this.errorMessage = 'Open a project and select an image first.';
        return;
      }
      if (!this.llm.backend || !this.llm.model) {
        this.errorMessage = 'Select an available backend and model first.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/generate-caption', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            backend: this.llm.backend,
            model: this.llm.model,
            extra_instructions: this.llm.extraInstructions,
            make_active: this.llm.makeActive,
            timeout_seconds: this.settings.llmTimeoutSeconds,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Caption generation failed');
        }
        this.statusMessage = `Generated caption with ${payload.backend}/${payload.model}.`;
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async generateCaptionWithTools() {
      if (!this.currentProject?.path || !this.selectedImage) {
        this.errorMessage = 'Open a project and select an image first.';
        return;
      }
      if (!this.llm.backend || !this.llm.model) {
        this.errorMessage = 'Select an available backend and model first.';
        return;
      }
      const toolsEnabled = [];
      if (this.llm.tools.webSearch) toolsEnabled.push('web_search');
      if (this.llm.tools.webFetch) toolsEnabled.push('web_fetch');
      const selectedModel = this.selectedLLMModel();
      let fallbackNotice = '';
      if (toolsEnabled.length > 0 && selectedModel && !selectedModel.tool_capable) {
        toolsEnabled.length = 0;
        fallbackNotice = ` Model ${this.llm.model} is not tool-capable, so tools were skipped.`;
      }
      const contextUrls = this.llm.tools.contextUrl.trim() ? [this.llm.tools.contextUrl.trim()] : [];
      const contextFiles = this.llm.tools.contextFile.trim() ? [this.llm.tools.contextFile.trim()] : [];
      await this.withSubmitting(async () => {
        const response = await fetch('/api/llm/generate-caption-with-tools', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            backend: this.llm.backend,
            model: this.llm.model,
            extra_instructions: this.llm.extraInstructions,
            make_active: this.llm.makeActive,
            timeout_seconds: this.settings.llmTimeoutSeconds,
            tools_enabled: toolsEnabled,
            context_urls: contextUrls,
            context_files: contextFiles,
            include_project_notes: this.llm.tools.includeProjectNotes,
            include_global_notes: this.llm.tools.includeGlobalNotes,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Caption generation failed');
        }
        const log = payload.tool_usage_log?.length ? ` (${payload.tool_usage_log.length} tool/context event(s))` : '';
        const modeMap = {
          tool_calls: 'Mode: Tool Calls',
          context_injection: 'Mode: Context Injection',
        };
        const modeLabel = modeMap[payload.generation_mode] || `Mode: ${payload.generation_mode || 'unknown'}`;
        this.statusMessage = `Generated caption with ${payload.backend}/${payload.model}${log}. ${modeLabel}.${fallbackNotice}`;
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async loadImageSummary() {
      if (!this.currentProject?.path) {
        this.imageSummary = { count: 0, non_empty_caption_count: 0, blank_caption_count: 0, previews: [] };
        return;
      }
      try {
        const url = new URL('/api/images/summary', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load image summary');
        }
        this.imageSummary = payload;
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadImages() {
      if (!this.currentProject?.path) {
        this.images = [];
        this.gridCards = [];
        this.selectedImage = null;
        return;
      }
      try {
        const url = new URL('/api/images/list', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load images');
        }
        this.images = payload.images ?? [];
        this.gridCards = this.images.map((item) => ({
          id: item.id,
          label: item.filename,
          status: item.included ? 'included' : 'excluded',
          active_caption_preview: item.active_caption_preview,
        }));
        if (this.images.length > 0 && !this.selectedImage) {
          await this.selectImage(this.images[0].id, false);
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async selectImage(imageId, switchToEditor = true) {
      if (!this.currentProject?.path) {
        return;
      }
      try {
        const url = new URL(`/api/images/${imageId}`, window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load image details');
        }
        this.selectedImage = payload.image;
        this.editingCaptionId = null;
        this.editingCaptionText = '';
        const active = this.selectedImage.captions.find((caption) => caption.is_active);
        this.editorCaptionText = active ? active.text : '';
        if (switchToEditor) {
          this.mainView = 'editor';
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    imageSrc(imageId) {
      if (!this.currentProject?.path) {
        return '';
      }
      const url = new URL(`/api/images/${imageId}/content`, window.location.origin);
      url.searchParams.set('project_path', this.currentProject.path);
      return url.toString();
    },
    async toggleIncluded() {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch(`/api/images/${this.selectedImage.id}/included`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            included: !this.selectedImage.included,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to update include state');
        }
        this.selectedImage.included = payload.included;
        this.statusMessage = payload.included ? 'Image included in export set.' : 'Image excluded from export set.';
        await this.loadImages();
        await this.loadImageSummary();
        await this.selectImage(this.selectedImage.id, false);
      });
    },
    async saveActiveCaption() {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/captions/update-active', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            text: this.editorCaptionText,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to save caption');
        }
        this.statusMessage = 'Active caption saved.';
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async addCaptionCandidate(makeActive = true) {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      const text = this.newCaptionText.trim();
      if (!text) {
        this.errorMessage = 'Enter caption text before adding a candidate.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/captions/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            text,
            make_active: makeActive,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to create caption candidate');
        }
        this.newCaptionText = '';
        this.statusMessage = makeActive ? 'Created and activated new caption candidate.' : 'Created new caption candidate.';
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async setActiveCaption(captionId) {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/captions/set-active', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            caption_id: captionId,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to set active caption');
        }
        this.statusMessage = 'Active caption updated.';
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    startEditCaption(caption) {
      if (!caption) {
        return;
      }
      this.editingCaptionId = caption.id;
      this.editingCaptionText = caption.text || '';
      this.errorMessage = '';
      this.statusMessage = '';
    },
    cancelEditCaption() {
      this.editingCaptionId = null;
      this.editingCaptionText = '';
    },
    async saveEditedCaption(caption) {
      if (!this.currentProject?.path || !this.selectedImage || !caption) {
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/captions/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            caption_id: caption.id,
            text: this.editingCaptionText,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to update caption');
        }
        this.cancelEditCaption();
        this.statusMessage = 'Caption updated.';
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async deleteCaption(caption) {
      if (!this.currentProject?.path || !this.selectedImage || !caption) {
        return;
      }
      const confirmDelete = window.confirm('Delete this caption? This cannot be undone.');
      if (!confirmDelete) {
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/captions/delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            caption_id: caption.id,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to delete caption');
        }
        this.statusMessage = 'Caption deleted.';
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async importFolder() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open or create a project first.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/projects/import-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            source_folder: this.importForm.source_folder,
            replace_existing: this.importForm.replace_existing,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Import failed');
        }
        const result = payload.result;
        this.statusMessage = `Imported ${result.imported_images} images (${result.captions_from_files} with captions, ${result.blank_captions} blank).`;
        await this.loadImages();
        await this.loadImageSummary();
      });
    },
    async exportProjectDataset() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open or create a project first.';
        return;
      }
      if (!this.exportForm.output_folder.trim()) {
        this.errorMessage = 'Select an export output folder first.';
        return;
      }
      this.normalizeExportFormOptions();
      if (this.exportForm.clean_output_folder && this.exportForm.overwrite_existing) {
        this.errorMessage = 'Choose either clean output folder or overwrite existing files.';
        return;
      }
      await this.withSubmitting(async () => {
        const response = await fetch('/api/projects/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            output_folder: this.exportForm.output_folder,
            included_only: this.exportForm.included_only,
            apply_trigger_word: this.exportForm.apply_trigger_word,
            include_metadata: this.exportForm.include_metadata,
            overwrite_existing: this.exportForm.overwrite_existing,
            clean_output_folder: this.exportForm.clean_output_folder,
            create_new_folder: this.exportForm.create_new_folder,
            new_folder_name: this.exportForm.new_folder_name,
            include_project_notes: this.exportForm.include_project_notes,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Export failed');
        }
        const result = payload.result;
        const collisionSuffix = result.skipped_due_to_collision ? `, ${result.skipped_due_to_collision} skipped due to collisions` : '';
        const blobSuffix = result.skipped_missing_blob ? `, ${result.skipped_missing_blob} missing image data` : '';
        const metadataSuffix = result.metadata_written && result.metadata_file ? ' Metadata manifest written.' : '';
        const notesSuffix = result.exported_notes ? ` ${result.exported_notes} note(s) exported to notes/.` : '';
        this.statusMessage = `Exported ${result.exported_images} images to ${result.output_folder}${result.skipped_images ? ` (${result.skipped_images} skipped${collisionSuffix}${blobSuffix})` : ''}.${metadataSuffix}${notesSuffix}`;
        this.exportPreview = null;
      });
    },
    async testConnection(backend) {
      const urlKey = backend === 'ollama' ? 'ollamaBaseUrl' : 'lmstudioBaseUrl';
      const testingKey = backend === 'ollama' ? 'ollamaTesting' : 'lmstudioTesting';
      this.connectionTest[testingKey] = true;
      this.connectionTest[backend] = null;
      try {
        const response = await fetch('/api/llm/test-connection', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ backend, url: this.settings[urlKey] }),
        });
        const payload = await response.json();
        this.connectionTest[backend] = payload;
      } catch (error) {
        this.connectionTest[backend] = { ok: false, message: error.message };
      } finally {
        this.connectionTest[testingKey] = false;
      }
    },
    async checkRAGStatus() {
      try {
        const response = await fetch('/api/llm/rag/status');
        const payload = await response.json();
        if (response.ok) {
          this.rag.enabled = payload.rag_enabled ?? false;
        }
      } catch (error) {
        this.rag.enabled = false;
      }
    },
    async rebuildEmbeddings() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open or create a project first.';
        return;
      }
      this.rag.isRebuildingEmbeddings = true;
      this.rag.embeddingsStatus = 'Rebuilding embeddings...';
      this.errorMessage = '';
      this.statusMessage = '';
      try {
        const response = await fetch('/api/llm/rag/rebuild-embeddings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_path: this.currentProject.path }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to rebuild embeddings');
        }
        const result = payload.result;
        this.rag.embeddingsStatus = `Indexed ${result.indexed} captions`;
        this.statusMessage = `Embeddings rebuilt: ${result.indexed} captions indexed`;
      } catch (error) {
        this.errorMessage = error.message;
        this.rag.embeddingsStatus = 'Failed to rebuild embeddings';
      } finally {
        this.rag.isRebuildingEmbeddings = false;
      }
    },
  };
}

window.describeItApp = describeItApp;
