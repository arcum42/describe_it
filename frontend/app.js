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
    images: [],
    mainView: 'grid',
    editorView: {
      subTab: 'caption', // caption, image, batch_tags
      zoomMode: 'fit', // fit, full, percent
      zoomPercent: 100,
    },
    showOpenProject: false,
    showBrowser: false,
    selectedImage: null,
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
    captionBatch: {
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
    },
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
      skipDuplicates: true,
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
      roots: [],
    },
    gridCards: [],
    loadImagesRequestSeq: 0,
    selectImageRequestSeq: 0,
    keyboard: {
      showShortcutsHelp: false,
      shortcuts: [],
    },
    gridFilter: {
      searchText: '',
      inclusionStatus: 'all', // 'all', 'included', 'excluded'
      captionStatus: 'all', // 'all', 'with_captions', 'blank_captions'
      sortBy: 'name', // 'name', 'status', 'caption_count'
      sortOrder: 'asc', // 'asc', 'desc'
      pageSize: 100, // Items per page: 25, 50, 100, all
    },
    async init() {
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
    openSettings(tab = 'general') {
      this.uiSection = 'settings';
      this.settingsTab = tab;
      this.errorMessage = '';
      this.statusMessage = '';
      this.checkRAGStatus();
    },
    openPresetSettings() {
      this.openSettings('presets');
    },
    openWorkspace() {
      this.uiSection = 'workspace';
    },
    showKeyboardShortcutsHelp() {
      this.keyboard.showShortcutsHelp = true;
    },
    closeKeyboardShortcutsHelp() {
      this.keyboard.showShortcutsHelp = false;
    },
    isTagMode() {
      return this.currentProject?.caption_mode === 'tags';
    },
    editorSubTabs() {
      const tabs = [
        { id: 'caption', label: 'Caption' },
        { id: 'image', label: 'Image' },
      ];
      if (this.isTagMode()) {
        tabs.push({ id: 'batch_tags', label: 'Batch Tags' });
      }
      return tabs;
    },
    setEditorSubTab(nextTab) {
      const allowed = this.editorSubTabs().map((tab) => tab.id);
      this.editorView.subTab = allowed.includes(nextTab) ? nextTab : 'caption';
    },
    ensureEditorSubTab() {
      const allowed = this.editorSubTabs().map((tab) => tab.id);
      if (!allowed.includes(this.editorView.subTab)) {
        this.editorView.subTab = 'caption';
      }
    },
    normalizeEditorZoomPercent(value) {
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) {
        return 100;
      }
      return Math.min(400, Math.max(25, parsed));
    },
    setEditorZoomMode(mode) {
      const normalized = String(mode || '').trim().toLowerCase();
      if (!['fit', 'full', 'percent'].includes(normalized)) {
        this.editorView.zoomMode = 'fit';
        return;
      }
      this.editorView.zoomMode = normalized;
      if (normalized === 'percent') {
        this.editorView.zoomPercent = this.normalizeEditorZoomPercent(this.editorView.zoomPercent);
      }
    },
    setEditorZoomPercent(value) {
      this.editorView.zoomPercent = this.normalizeEditorZoomPercent(value);
      this.editorView.zoomMode = 'percent';
    },
    resetEditorZoomToDefault() {
      const defaultMode = this.settings.editorDefaultImageZoomMode || 'fit';
      const defaultPercent = this.normalizeEditorZoomPercent(this.settings.editorDefaultImageZoomPercent);
      this.editorView.zoomPercent = defaultPercent;
      this.setEditorZoomMode(defaultMode);
    },
    editorZoomPresets() {
      return [50, 75, 100, 125, 150, 200];
    },
    editorImageClasses() {
      if (this.editorView.zoomMode === 'fit') {
        return 'h-auto w-full object-contain mx-auto';
      }
      return 'h-auto max-w-none object-contain mx-auto';
    },
    editorImageStyle() {
      if (this.editorView.zoomMode === 'percent') {
        return { width: `${this.normalizeEditorZoomPercent(this.editorView.zoomPercent)}%` };
      }
      if (this.editorView.zoomMode === 'full') {
        return { width: 'auto' };
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
      this.editorView.subTab = 'caption';
      this.resetEditorZoomToDefault();
      this.editorCaptionText = '';
      this.newCaptionText = '';
      this.tagEditor.activeCaptionId = null;
      this.tagEditor.tags = [];
      this.tagEditor.newTagText = '';
      this.tagEditor.editingTagIndex = null;
      this.tagEditor.editingTagText = '';
      this.tagEditor.dragTagIndex = null;
      this.tagEditor.stats = {
        total_tags: 0,
        total_occurrences: 0,
        top_tags: [],
      };
      this.tagEditor.batch.clearConfirm = false;
      this.resetPresetForm();
      this.loadImageSummary();
      this.loadImages();
      this.loadTagStatistics(true);
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
      this.editorView.subTab = 'caption';
      this.resetEditorZoomToDefault();
      this.images = [];
      this.gridCards = [];
      this.editorCaptionText = '';
      this.newCaptionText = '';
      this.tagEditor.activeCaptionId = null;
      this.tagEditor.tags = [];
      this.tagEditor.newTagText = '';
      this.tagEditor.editingTagIndex = null;
      this.tagEditor.editingTagText = '';
      this.tagEditor.dragTagIndex = null;
      this.tagEditor.stats = {
        total_tags: 0,
        total_occurrences: 0,
        top_tags: [],
      };
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
      let filtered = [...this.gridCards];

      // Apply search filter
      if (this.gridFilter.searchText.trim()) {
        const search = this.gridFilter.searchText.toLowerCase();
        filtered = filtered.filter(card => 
          card.label.toLowerCase().includes(search) || 
          (card.filename && card.filename.toLowerCase().includes(search))
        );
      }

      // Apply inclusion status filter
      if (this.gridFilter.inclusionStatus === 'included') {
        filtered = filtered.filter(card => card.included === true);
      } else if (this.gridFilter.inclusionStatus === 'excluded') {
        filtered = filtered.filter(card => card.included === false);
      }

      // Apply caption status filter
      if (this.gridFilter.captionStatus === 'with_captions') {
        filtered = filtered.filter(card => card.active_caption_preview && card.active_caption_preview.trim() !== '');
      } else if (this.gridFilter.captionStatus === 'blank_captions') {
        filtered = filtered.filter(card => !card.active_caption_preview || card.active_caption_preview.trim() === '');
      }

      // Apply sorting
      const sortBy = this.gridFilter.sortBy;
      const sortOrder = this.gridFilter.sortOrder === 'desc' ? -1 : 1;

      if (sortBy === 'name') {
        filtered.sort((a, b) => sortOrder * a.label.localeCompare(b.label));
      } else if (sortBy === 'status') {
        const statusOrder = { excluded: 0, included: 1 };
        filtered.sort((a, b) => {
          const aStatus = statusOrder[a.status] ?? 2;
          const bStatus = statusOrder[b.status] ?? 2;
          return sortOrder * (aStatus - bStatus);
        });
      } else if (sortBy === 'caption_count') {
        filtered.sort((a, b) => {
          const aEmpty = !a.active_caption_preview || a.active_caption_preview.trim() === '' ? 0 : 1;
          const bEmpty = !b.active_caption_preview || b.active_caption_preview.trim() === '' ? 0 : 1;
          return sortOrder * (bEmpty - aEmpty);
        });
      }

      // Apply pagination
      if (this.gridFilter.pageSize && this.gridFilter.pageSize !== 'all') {
        const pageSize = parseInt(this.gridFilter.pageSize, 10);
        filtered = filtered.slice(0, pageSize);
      }

      return filtered;
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
        return;
      }
      this.errorMessage = 'Imageboard settings module unavailable.';
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
