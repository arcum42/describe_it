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
        reasoningMode: 'off',
        reasoningVisibility: 'hidden',
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
    activeOps: new Set(), // Fine-grained operation tracking (replaces isSubmitting)
    isSubmitting: false, // Kept for backward compatibility
    browser: {
      currentPath: '',
      parentPath: null,
      directories: [],
      dbFiles: [],
      roots: [],
    },
    gridCards: [],
    loadImagesRequestSeq: 0,
    selectImageRequestSeq: 0,
    async init() {
      const deferredStartupTasks = [
        this.loadRecentProjects(true),
        this.loadLLMBackends(true),
        this.loadSettings(true),
        this.loadLLMPresets(true),
        this.loadGlobalNotes(true),
        this.checkRAGStatus(),
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
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.saveProjectSessionState === 'function') {
        await projectsFeature.saveProjectSessionState(this);
        return;
      }
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
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.autoOpenLastProjectIfNeeded === 'function') {
        await projectsFeature.autoOpenLastProjectIfNeeded(this);
        return;
      }
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
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.applyProject === 'function') {
        projectsFeature.applyProject(this, project, options);
        return;
      }
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
      const projectsFeature = window.DescribeItFeatures?.projects;
      if (projectsFeature && typeof projectsFeature.closeProject === 'function') {
        projectsFeature.closeProject(this);
        return;
      }
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
        return;
      }
      this.llm.backends = [];
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
    async importFolder() {
      const importFeature = window.DescribeItFeatures?.import;
      if (importFeature && typeof importFeature.importFolder === 'function') {
        await importFeature.importFolder(this);
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
  };
}

window.describeItApp = describeItApp;
