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
    llm: {
      backends: [],
      backend: '',
      model: '',
      extraInstructions: '',
      makeActive: true,
      presets: [],
      selectedPresetId: '',
      presetForm: {
        id: null,
        name: '',
        backend: 'ollama',
        modelName: '',
        systemPrompt: '',
      },
    },
    settings: {
      llmTimeoutSeconds: 120,
      usePresetByDefault: false,
      defaultPresetId: '',
      reopenLastProjectOnStartup: true,
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
      await Promise.all([this.loadHealth(), this.loadRecentProjects(), this.loadLLMBackends(), this.loadSettings(), this.loadLLMPresets(), this.loadProjectSessionState()]);
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
        this.applyPresetPreference();
      } catch (error) {
        this.settings.llmTimeoutSeconds = 120;
        this.settings.usePresetByDefault = false;
        this.settings.defaultPresetId = '';
      }
    },
    async saveSettings() {
      this.settings.llmTimeoutSeconds = this.normalizeTimeout(this.settings.llmTimeoutSeconds);
      const defaultPresetId = this.settings.defaultPresetId ? Number(this.settings.defaultPresetId) : null;
      try {
        const response = await fetch('/api/llm/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            llm_timeout_seconds: this.settings.llmTimeoutSeconds,
            llm_use_preset_by_default: this.settings.usePresetByDefault,
            llm_default_preset_id: defaultPresetId,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to save settings');
        }
        this.settings.llmTimeoutSeconds = this.normalizeTimeout(payload.llm_timeout_seconds);
        this.settings.usePresetByDefault = payload.llm_use_preset_by_default === true;
        this.settings.defaultPresetId = payload.llm_default_preset_id ? String(payload.llm_default_preset_id) : '';
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
    availableModelsForBackend(backendName) {
      const backend = this.llm.backends.find((item) => item.name === backendName);
      return backend?.models ?? [];
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
      const backend = this.selectedLLMBackend();
      const models = backend?.models ?? [];
      if (!models.includes(this.llm.model)) {
        this.llm.model = models[0] ?? '';
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
      const backend = this.selectedLLMBackend();
      const models = backend?.models ?? [];
      this.llm.model = models[0] ?? '';
    },
    onPresetBackendChanged() {
      const models = this.availableModelsForBackend(this.llm.presetForm.backend);
      if (!models.includes(this.llm.presetForm.modelName)) {
        this.llm.presetForm.modelName = models[0] ?? '';
      }
    },
    resetPresetForm() {
      this.llm.presetForm = {
        id: null,
        name: '',
        backend: this.llm.backends.some((item) => item.name === 'ollama') ? 'ollama' : (this.llm.backends[0]?.name ?? ''),
        modelName: '',
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
  };
}

window.describeItApp = describeItApp;
