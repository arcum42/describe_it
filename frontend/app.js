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
      ragEnabled: false,
    },
    rag: {
      enabled: false,
      isRebuildingEmbeddings: false,
      embeddingsStatus: '',
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
      await Promise.all([this.loadHealth(), this.loadRecentProjects(), this.loadLLMBackends(), this.loadSettings(), this.loadLLMPresets(), this.loadProjectSessionState(), this.checkRAGStatus()]);
      await this.loadBrowser(this.projectSession.lastProjectDirectory || null);
      await this.autoOpenLastProjectIfNeeded();
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
    async loadSettings() {
      try {
        const response = await fetch('/api/llm/settings');
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
      }
    },
    async saveSettings() {
      this.settings.llmTimeoutSeconds = this.normalizeTimeout(this.settings.llmTimeoutSeconds);
      this.settings.ollamaTimeoutSeconds = this.normalizeOptionalTimeout(this.settings.ollamaTimeoutSeconds);
      this.settings.lmstudioTimeoutSeconds = this.normalizeOptionalTimeout(this.settings.lmstudioTimeoutSeconds);
      const defaultPresetId = this.settings.defaultPresetId ? Number(this.settings.defaultPresetId) : null;
      const ollamaTimeoutSeconds = this.settings.ollamaTimeoutSeconds === '' ? null : Number(this.settings.ollamaTimeoutSeconds);
      const lmstudioTimeoutSeconds = this.settings.lmstudioTimeoutSeconds === '' ? null : Number(this.settings.lmstudioTimeoutSeconds);
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
        this.projectSession.reopenLastProject = this.settings.reopenLastProjectOnStartup;
        await this.saveProjectSessionState();
        this.applyPresetPreference();
        this.statusMessage = `Saved settings. LLM timeout set to ${this.settings.llmTimeoutSeconds}s.`;
        this.errorMessage = '';
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadProjectSessionState() {
      try {
        const response = await fetch('/api/projects/session-state');
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
        this.applyProject(payload.project);
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
    applyProject(project) {
      this.currentProject = project;
      this.mainView = 'grid';
      this.metadataForm = {
        path: project.path,
        name: project.name ?? '',
        description: project.description ?? '',
        trigger_word: project.trigger_word ?? '',
        caption_mode: project.caption_mode ?? 'description',
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
    },
    closeProject() {
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
      this.loadBrowser(this.projectSession.lastProjectDirectory || null);
    },
    async loadHealth() {
      try {
        const response = await fetch('/api/health');
        const payload = await response.json();
        this.healthLabel = payload.status;
      } catch (error) {
        this.healthLabel = 'offline';
      }
    },
    async loadRecentProjects() {
      try {
        const response = await fetch('/api/projects/recent');
        const payload = await response.json();
        this.recentProjects = payload.projects ?? [];
      } catch (error) {
        this.recentProjects = [];
      }
    },
    async loadBrowser(path = null) {
      try {
        const url = new URL('/api/projects/browser', window.location.origin);
        if (path) {
          url.searchParams.set('path', path);
        }
        const response = await fetch(url);
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
    async createProject() {
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async openProject() {
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async saveMetadata() {
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async openRecentProject(path) {
      this.openForm.path = path;
      await this.openProject();
    },
    selectedLLMBackend() {
      return this.llm.backends.find((item) => item.name === this.llm.backend) || null;
    },
    modelCapabilityLabel(backendName, modelName) {
      const backend = this.llm.backends.find((item) => item.name === backendName);
      const model = backend?.models?.find((item) => item.name === modelName);
      if (!model) {
        return '';
      }
      return model.vision_capable ? '👁️' : '';
    },
    modelOptionLabel(modelInfo) {
      if (!modelInfo) {
        return '';
      }
      return modelInfo.vision_capable ? `${modelInfo.name}  👁️` : modelInfo.name;
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
    async loadLLMBackends() {
      try {
        const response = await fetch('/api/llm/backends');
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load LLM backends');
        }
        this.llm.backends = payload.backends ?? [];
        this.pickDefaultLLMSelection();
        this.onPresetBackendChanged();
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
      const models = this.availableModelsForBackend(this.llm.presetForm.backend);
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
      };
      this.llm.selectedPresetId = String(preset.id);
    },
    async loadLLMPresets() {
      try {
        const response = await fetch('/api/llm/presets');
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
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/llm/presets/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: this.llm.presetForm.name,
            backend: this.llm.presetForm.backend,
            model_name: this.llm.presetForm.modelName,
            caption_mode_strategy: this.llm.presetForm.captionModeStrategy,
            system_prompt: this.llm.presetForm.systemPrompt,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to create preset');
        }
        await this.loadLLMPresets();
        this.applyPresetToForm(payload.preset);
        this.statusMessage = `Created preset ${payload.preset.name}.`;
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async updatePreset() {
      if (!this.llm.presetForm.id) {
        this.errorMessage = 'Select a preset to update.';
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/llm/presets/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            preset_id: this.llm.presetForm.id,
            name: this.llm.presetForm.name,
            backend: this.llm.presetForm.backend,
            model_name: this.llm.presetForm.modelName,
            caption_mode_strategy: this.llm.presetForm.captionModeStrategy,
            system_prompt: this.llm.presetForm.systemPrompt,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to update preset');
        }
        await this.loadLLMPresets();
        this.applyPresetToForm(payload.preset);
        this.statusMessage = `Updated preset ${payload.preset.name}.`;
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async deletePreset() {
      if (!this.llm.presetForm.id) {
        this.errorMessage = 'Select a preset to delete.';
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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

      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
        this.statusMessage = `Generated caption with preset ${payload.preset.name}.`;
        await this.selectImage(this.selectedImage.id, false);
        await this.loadImages();
        await this.loadImageSummary();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async saveActiveCaption() {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async setActiveCaption(captionId) {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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

      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async deleteCaption(caption) {
      if (!this.currentProject?.path || !this.selectedImage || !caption) {
        return;
      }

      const confirmDelete = window.confirm('Delete this caption? This cannot be undone.');
      if (!confirmDelete) {
        return;
      }

      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async importFolder() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open or create a project first.';
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
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

      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
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
        this.statusMessage = `Exported ${result.exported_images} images to ${result.output_folder}${result.skipped_images ? ` (${result.skipped_images} skipped${collisionSuffix}${blobSuffix})` : ''}.${metadataSuffix}`;
        this.exportPreview = null;
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
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
