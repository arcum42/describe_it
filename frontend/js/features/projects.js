(function initDescribeItFeatureProjects(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function createDefaultCaptionTextEditJobState() {
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

  async function loadProjectSessionState(app, isStartup = false) {
    try {
      const response = await app.fetchWithRetry('/api/projects/session-state', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load project session state');
      }
      app.projectSession.lastProjectPath = payload.last_project_path || '';
      app.projectSession.lastProjectDirectory = payload.last_project_directory || '';
      app.projectSession.reopenLastProject = payload.reopen_last_project !== false;
      app.settings.reopenLastProjectOnStartup = app.projectSession.reopenLastProject;
    } catch (error) {
      app.projectSession.lastProjectPath = '';
      app.projectSession.lastProjectDirectory = '';
      app.projectSession.reopenLastProject = true;
      app.settings.reopenLastProjectOnStartup = true;
    }
  }

  async function saveProjectSessionState(app) {
    try {
      await fetch('/api/projects/session-state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          last_project_path: app.projectSession.lastProjectPath,
          last_project_directory: app.projectSession.lastProjectDirectory,
          reopen_last_project: app.projectSession.reopenLastProject,
        }),
      });
    } catch (error) {
      // Ignore persistence errors to avoid interrupting normal UI interactions.
    }
  }

  async function autoOpenLastProjectIfNeeded(app) {
    if (!app.projectSession.reopenLastProject || !app.projectSession.lastProjectPath) {
      return;
    }
    app.openForm.path = app.projectSession.lastProjectPath;
    try {
      const response = await fetch('/api/projects/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: app.projectSession.lastProjectPath }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to reopen last project');
      }
      applyProject(app, payload.project, { preserveMainView: true });
      await loadRecentProjects(app);
      app.statusMessage = `Reopened last project ${payload.project.name}.`;
    } catch (error) {
      app.projectSession.lastProjectPath = '';
      await saveProjectSessionState(app);
    }
  }

  function applyProject(app, project, options = {}) {
    const preserveMainView = options.preserveMainView === true;
    app.currentProject = project;
    if (!preserveMainView) {
      app.mainView = 'grid';
    }
    app.metadataForm = {
      path: project.path,
      name: project.name ?? '',
      description: project.description ?? '',
      trigger_word: project.trigger_word ?? '',
      caption_mode: project.caption_mode ?? 'description',
      context_url: project.context_url ?? '',
      context_file_path: project.context_file_path ?? '',
    };
    app.openForm.path = project.path;
    const lastSeparator = project.path.lastIndexOf('/');
    if (lastSeparator > 0) {
      app.projectSession.lastProjectDirectory = project.path.slice(0, lastSeparator);
    }
    app.projectSession.lastProjectPath = project.path;
    app.projectSession.reopenLastProject = true;
    saveProjectSessionState(app);
    app.selectedImage = null;
    app.editorView.subTab = 'caption';
    app.resetEditorZoomToDefault();
    app.editorCaptionText = '';
    app.newCaptionText = '';
    app.tagEditor.activeCaptionId = null;
    app.tagEditor.tags = [];
    app.tagEditor.newTagText = '';
    app.tagEditor.editingTagIndex = null;
    app.tagEditor.editingTagText = '';
    app.tagEditor.dragTagIndex = null;
    app.tagEditor.stats = {
      total_tags: 0,
      total_occurrences: 0,
      top_tags: [],
    };
    app.tagEditor.batch.clearConfirm = false;
    app.captionTextEdit.removeTagsPatternsText = '';
    app.captionTextEdit.addCommonCaptionText = '';
    app.captionTextEdit.addCommonScope = 'without_caption';
    app.captionTextEdit.jobs.deleteEmpty = createDefaultCaptionTextEditJobState();
    app.captionTextEdit.jobs.removeTags = createDefaultCaptionTextEditJobState();
    app.captionTextEdit.jobs.addCommon = createDefaultCaptionTextEditJobState();
    app.captionTextEdit.history.deleteEmpty = [];
    app.captionTextEdit.history.removeTags = [];
    app.captionTextEdit.history.addCommon = [];
    app.resetPresetForm();
    app.loadImageSummary();
    app.loadImages();
    app.loadTagStatistics(true);
    app.loadLatestBatchJob();
    app.batch.subTab = 'generate';
    app.loadProjectNotes();
  }

  function closeProject(app) {
    const activeCaption = app.selectedImage?.captions?.find((c) => c.is_active);
    const savedText = activeCaption?.text ?? '';
    if (app.selectedImage && app.editorCaptionText !== savedText) {
      if (!window.confirm('You have unsaved caption changes. Close project anyway?')) {
        return;
      }
    }
    app.currentProject = null;
    app.mainView = 'grid';
    app.selectedImage = null;
    app.editorView.subTab = 'caption';
    app.resetEditorZoomToDefault();
    app.images = [];
    app.gridCards = [];
    app.editorCaptionText = '';
    app.newCaptionText = '';
    app.tagEditor.activeCaptionId = null;
    app.tagEditor.tags = [];
    app.tagEditor.newTagText = '';
    app.tagEditor.editingTagIndex = null;
    app.tagEditor.editingTagText = '';
    app.tagEditor.dragTagIndex = null;
    app.tagEditor.stats = {
      total_tags: 0,
      total_occurrences: 0,
      top_tags: [],
    };
    app.metadataForm = {
      path: '',
      name: '',
      description: '',
      trigger_word: '',
      caption_mode: 'description',
      context_url: '',
      context_file_path: '',
    };
    app.imageSummary = {
      count: 0,
      non_empty_caption_count: 0,
      blank_caption_count: 0,
      previews: [],
    };
    app.projectSession.lastProjectPath = '';
    app.projectSession.reopenLastProject = false;
    saveProjectSessionState(app);
    app.statusMessage = 'Closed current project.';
    app.errorMessage = '';
    if (app.batchPollTimer) {
      clearInterval(app.batchPollTimer);
      app.batchPollTimer = null;
    }
    app.batch.jobId = '';
    app.batch.status = 'idle';
    app.batch.subTab = 'generate';
    app.batch.history = [];
    app.batch.historyStatusFilter = 'all';
    app.batch.results = [];
    app.captionTextEdit.jobs.deleteEmpty = createDefaultCaptionTextEditJobState();
    app.captionTextEdit.jobs.removeTags = createDefaultCaptionTextEditJobState();
    app.captionTextEdit.jobs.addCommon = createDefaultCaptionTextEditJobState();
    app.captionTextEdit.history.deleteEmpty = [];
    app.captionTextEdit.history.removeTags = [];
    app.captionTextEdit.history.addCommon = [];
    app.notes.projectItems = [];
    app.notes.selectedNoteId = null;
    app.newNoteDraft();
    app.loadBrowser(app.projectSession.lastProjectDirectory || null);
  }

  function openSettings(app, tab = 'general') {
    app.uiSection = 'settings';
    app.settingsTab = tab;
    app.errorMessage = '';
    app.statusMessage = '';
    app.checkRAGStatus();
  }

  function openPresetSettings(app) {
    openSettings(app, 'presets');
  }

  function openWorkspace(app) {
    app.uiSection = 'workspace';
  }

  async function loadRecentProjects(app, isStartup = false) {
    try {
      const response = await app.fetchWithRetry('/api/projects/recent', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      app.recentProjects = payload.projects ?? [];
    } catch (error) {
      app.recentProjects = [];
    }
  }

  async function createProject(app) {
    await app.withSubmitting(async () => {
      const response = await fetch('/api/projects/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(app.createForm),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to create project');
      }
      applyProject(app, payload.project);
      app.statusMessage = `Created project ${payload.project.name}`;
      await loadRecentProjects(app);
      await app.loadBrowser(payload.project.path);
    });
  }

  async function openProject(app) {
    await app.withSubmitting(async () => {
      const response = await fetch('/api/projects/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(app.openForm),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to open project');
      }
      applyProject(app, payload.project);
      app.statusMessage = `Opened project ${payload.project.name}`;
      await loadRecentProjects(app);
      await app.loadBrowser(payload.project.path);
    }, 'openProject');
  }

  async function saveMetadata(app) {
    await app.withSubmitting(async () => {
      const response = await fetch('/api/projects/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(app.metadataForm),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to save metadata');
      }
      applyProject(app, payload.project);
      app.statusMessage = `Saved metadata for ${payload.project.name}`;
      await loadRecentProjects(app);
    }, 'saveMetadata');
  }

  async function openRecentProject(app, path) {
    app.openForm.path = path;
    await openProject(app);
  }

  features.projects = {
    loadProjectSessionState,
    saveProjectSessionState,
    autoOpenLastProjectIfNeeded,
    applyProject,
    closeProject,
    openSettings,
    openPresetSettings,
    openWorkspace,
    loadRecentProjects,
    createProject,
    openProject,
    saveMetadata,
    openRecentProject,
  };
})(window);