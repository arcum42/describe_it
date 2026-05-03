(function initDescribeItFeatureNotes(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function notesActiveItems(app) {
    return app.notes.scope === 'global' ? app.notes.globalItems : app.notes.projectItems;
  }

  function newNoteDraft(app) {
    app.notes.selectedNoteId = null;
    app.notes.editor = {
      id: null,
      title: '',
      content: '',
      format: 'markdown',
      tags: '',
      is_archived: false,
    };
  }

  function selectNote(app, note) {
    if (!note) {
      newNoteDraft(app);
      return;
    }
    app.notes.selectedNoteId = note.id;
    app.notes.editor = {
      id: note.id,
      title: note.title ?? '',
      content: note.content ?? '',
      format: note.format ?? 'markdown',
      tags: note.tags ?? '',
      is_archived: note.is_archived === true,
    };
  }

  async function loadProjectNotes(app, isStartup = false) {
    if (!app.currentProject?.path) {
      app.notes.projectItems = [];
      if (app.notes.scope === 'project') {
        newNoteDraft(app);
      }
      return;
    }
    try {
      const url = new URL('/api/notes', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      url.searchParams.set('include_archived', app.notes.includeArchived ? 'true' : 'false');
      const response = await app.fetchWithRetry(url, {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to load project notes'));
      }
      app.notes.projectItems = payload.notes ?? [];
      const selected = app.notes.projectItems.find((item) => item.id === app.notes.selectedNoteId);
      if (selected) {
        selectNote(app, selected);
      } else if (app.notes.scope === 'project') {
        newNoteDraft(app);
      }
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function loadGlobalNotes(app, isStartup = false) {
    try {
      const url = new URL('/api/global-notes', window.location.origin);
      url.searchParams.set('include_archived', app.notes.includeArchived ? 'true' : 'false');
      const response = await app.fetchWithRetry(url, {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to load global notes'));
      }
      app.notes.globalItems = payload.notes ?? [];
      const selected = app.notes.globalItems.find((item) => item.id === app.notes.selectedNoteId);
      if (selected) {
        selectNote(app, selected);
      } else if (app.notes.scope === 'global') {
        newNoteDraft(app);
      }
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function refreshNotes(app) {
    if (app.notes.scope === 'global') {
      await loadGlobalNotes(app);
    } else {
      await loadProjectNotes(app);
    }
  }

  async function onNotesScopeChanged(app) {
    newNoteDraft(app);
    await refreshNotes(app);
  }

  async function onNotesArchivedFilterChanged(app) {
    await refreshNotes(app);
  }

  async function saveNote(app) {
    if (app.notes.scope === 'project' && !app.currentProject?.path) {
      app.errorMessage = 'Open a project to create project notes.';
      return;
    }
    await app.withSubmitting(async () => {
      const isUpdate = !!app.notes.editor.id;
      const endpoint = app.notes.scope === 'global'
        ? (isUpdate ? '/api/global-notes/update' : '/api/global-notes/create')
        : (isUpdate ? '/api/notes/update' : '/api/notes/create');

      const body = {
        title: app.notes.editor.title,
        content: app.notes.editor.content,
        format: app.notes.editor.format,
        tags: app.notes.editor.tags,
      };
      if (isUpdate) {
        body.is_archived = app.notes.editor.is_archived;
        if (app.notes.scope === 'global') {
          body.note_id = app.notes.editor.id;
        } else {
          body.note_id = app.notes.editor.id;
          body.project_path = app.currentProject.path;
        }
      } else if (app.notes.scope === 'project') {
        body.project_path = app.currentProject.path;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to save note'));
      }
      const savedNote = payload.note;
      await refreshNotes(app);
      selectNote(app, savedNote);
      app.statusMessage = isUpdate ? 'Note updated.' : 'Note created.';
    });
  }

  async function deleteNote(app) {
    if (!app.notes.editor.id) {
      app.errorMessage = 'Select a note to delete.';
      return;
    }
    if (!window.confirm('Delete this note? This cannot be undone.')) {
      return;
    }
    if (app.notes.scope === 'project' && !app.currentProject?.path) {
      app.errorMessage = 'Open a project to delete project notes.';
      return;
    }
    await app.withSubmitting(async () => {
      const endpoint = app.notes.scope === 'global' ? '/api/global-notes/delete' : '/api/notes/delete';
      const body = app.notes.scope === 'global'
        ? { note_id: app.notes.editor.id }
        : { project_path: app.currentProject.path, note_id: app.notes.editor.id };
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to delete note'));
      }
      await refreshNotes(app);
      newNoteDraft(app);
      app.statusMessage = 'Note deleted.';
    });
  }

  function selectedNoteLLMBackend(app) {
    return app.llm.backends.find((item) => item.name === app.notes.llm.backend) || null;
  }

  function selectedNoteLLMModel(app) {
    const backend = selectedNoteLLMBackend(app);
    if (!backend) {
      return null;
    }
    return backend.models?.find((item) => item.name === app.notes.llm.model) || null;
  }

  function availableModelsForNoteLLM(app) {
    if (!app.notes.llm.backend) {
      return [];
    }
    return app.availableModelsForBackend(app.notes.llm.backend);
  }

  function onNotesLLMBackendChanged(app) {
    const models = availableModelsForNoteLLM(app);
    app.notes.llm.model = models[0]?.name ?? '';
  }

  function syncNotesLLMSelection(app) {
    if (!app.llm.backends.length) {
      app.notes.llm.backend = '';
      app.notes.llm.model = '';
      return;
    }
    if (!app.notes.llm.backend || !app.llm.backends.some((item) => item.name === app.notes.llm.backend)) {
      app.notes.llm.backend = app.llm.backend || app.llm.backends[0].name;
    }
    const models = availableModelsForNoteLLM(app);
    if (!models.some((item) => item.name === app.notes.llm.model)) {
      app.notes.llm.model = models[0]?.name ?? '';
    }
  }

  function buildGeneratedNoteTitle(app) {
    const explicit = app.notes.llm.title.trim();
    if (explicit) {
      return explicit;
    }
    const source = app.notes.llm.prompt.trim();
    if (!source) {
      return 'LLM Note';
    }
    const oneLine = source.replace(/\s+/g, ' ').trim();
    return oneLine.length > 72 ? `${oneLine.slice(0, 72).trimEnd()}...` : oneLine;
  }

  async function generateNoteWithLLM(app, saveAsNewNote = false) {
    if (!app.notes.llm.prompt.trim()) {
      app.errorMessage = 'Enter a prompt for note generation.';
      return;
    }
    syncNotesLLMSelection(app);
    if (!app.notes.llm.backend || !app.notes.llm.model) {
      app.errorMessage = 'Select an available backend and model first.';
      return;
    }
    if (app.notes.scope === 'project' && !app.currentProject?.path) {
      app.errorMessage = 'Open a project to generate project notes.';
      return;
    }
    if (app.notes.llm.useSelectedImage && !app.selectedImage?.id) {
      app.errorMessage = 'Select an image in the editor tab before enabling image context.';
      return;
    }

    const toolsEnabled = [];
    if (app.notes.llm.webSearch) toolsEnabled.push('web_search');
    if (app.notes.llm.webFetch) toolsEnabled.push('web_fetch');
    const selectedModel = selectedNoteLLMModel(app);
    let fallbackNotice = '';
    if (toolsEnabled.length > 0 && selectedModel && !selectedModel.tool_capable) {
      toolsEnabled.length = 0;
      fallbackNotice = ` Model ${app.notes.llm.model} is not tool-capable, so tools were skipped.`;
    }

    const projectPath = app.currentProject?.path || null;
    const contextUrls = app.notes.llm.contextUrl.trim() ? [app.notes.llm.contextUrl.trim()] : [];
    const contextFiles = app.notes.llm.contextFile.trim() ? [app.notes.llm.contextFile.trim()] : [];

    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/generate-note-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          backend: app.notes.llm.backend,
          model: app.notes.llm.model,
          prompt: app.notes.llm.prompt,
          project_path: projectPath,
          image_id: app.notes.llm.useSelectedImage ? app.selectedImage?.id ?? null : null,
          timeout_seconds: app.settings.llmTimeoutSeconds,
          tools_enabled: toolsEnabled,
          context_urls: contextUrls,
          context_files: contextFiles,
          include_project_notes: app.notes.llm.includeProjectNotes,
          include_global_notes: app.notes.llm.includeGlobalNotes,
          reasoning_mode: app.notes.llm.reasoningMode,
          reasoning_visibility: app.notes.llm.reasoningVisibility,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Note generation failed'));
      }

      const generatedText = payload.text || '';
      const generatedTitle = buildGeneratedNoteTitle(app);
      const generatedTags = app.notes.llm.tags.trim();
      const generatedFormat = app.notes.llm.outputFormat === 'text' ? 'text' : 'markdown';

      app.notes.editor.title = generatedTitle;
      app.notes.editor.content = generatedText;
      app.notes.editor.format = generatedFormat;
      app.notes.editor.tags = generatedTags;

      const log = payload.tool_usage_log?.length ? ` (${payload.tool_usage_log.length} tool/context event(s))` : '';
      const modeMap = {
        tool_calls: 'Mode: Tool Calls',
        context_injection: 'Mode: Context Injection',
      };
      const modeLabel = modeMap[payload.generation_mode] || `Mode: ${payload.generation_mode || 'unknown'}`;

      if (!saveAsNewNote) {
        app.statusMessage = `Generated note draft with ${payload.backend}/${payload.model}${log}. ${modeLabel}.${fallbackNotice}`;
        return;
      }

      const endpoint = app.notes.scope === 'global' ? '/api/global-notes/create' : '/api/notes/create';
      const body = {
        title: generatedTitle,
        content: generatedText,
        format: generatedFormat,
        tags: generatedTags,
      };
      if (app.notes.scope === 'project') {
        body.project_path = app.currentProject.path;
      }

      const saveResponse = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const savePayload = await saveResponse.json();
      if (!saveResponse.ok) {
        throw new Error(app.formatApiError(savePayload, 'Failed to save generated note'));
      }

      const savedNote = savePayload.note;
      await refreshNotes(app);
      selectNote(app, savedNote);
      app.statusMessage = `Generated and saved note with ${payload.backend}/${payload.model}${log}. ${modeLabel}.${fallbackNotice}`;
    });
  }

  features.notes = {
    notesActiveItems,
    newNoteDraft,
    selectNote,
    loadProjectNotes,
    loadGlobalNotes,
    refreshNotes,
    onNotesScopeChanged,
    onNotesArchivedFilterChanged,
    saveNote,
    deleteNote,
    selectedNoteLLMBackend,
    selectedNoteLLMModel,
    availableModelsForNoteLLM,
    onNotesLLMBackendChanged,
    syncNotesLLMSelection,
    buildGeneratedNoteTitle,
    generateNoteWithLLM,
  };
})(window);