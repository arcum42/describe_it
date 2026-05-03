(function initDescribeItFeatureLlm(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function selectedLLMBackend(app) {
    return app.llm.backends.find((item) => item.name === app.llm.backend) || null;
  }

  function selectedLLMModel(app) {
    const backend = selectedLLMBackend(app);
    if (!backend) {
      return null;
    }
    return backend.models?.find((item) => item.name === app.llm.model) || null;
  }

  function modelCapabilityLabel(app, backendName, modelName) {
    const backend = app.llm.backends.find((item) => item.name === backendName);
    const model = backend?.models?.find((item) => item.name === modelName);
    if (!model) {
      return '';
    }
    const icons = [];
    if (model.vision_capable) icons.push('👁️');
    if (model.tool_capable) icons.push('🔨');
    if (model.reasoning_capable) icons.push('🧠');
    return icons.join(' ');
  }

  function modelOptionLabel(app, modelInfo) {
    if (!modelInfo) {
      return '';
    }
    const icons = [];
    if (modelInfo.vision_capable) icons.push('👁️');
    if (modelInfo.tool_capable) icons.push('🔨');
    if (modelInfo.reasoning_capable) icons.push('🧠');
    return icons.length > 0 ? `${modelInfo.name}  ${icons.join(' ')}` : modelInfo.name;
  }

  function availableModelsForBackend(app, backendName) {
    const backend = app.llm.backends.find((item) => item.name === backendName);
    const models = backend?.models ?? [];
    if (app.llm.showAllModels) {
      return models;
    }
    return models.filter((model) => model.vision_capable);
  }

  function onModelVisibilityFilterChanged(app) {
    pickDefaultLLMSelection(app);
    onPresetBackendChanged(app);
  }

  function pickDefaultLLMSelection(app) {
    const available = app.llm.backends.filter((item) => item.available);
    if (available.length === 0) {
      app.llm.backend = '';
      app.llm.model = '';
      return;
    }
    if (!available.some((item) => item.name === app.llm.backend)) {
      app.llm.backend = available[0].name;
    }

    let models = availableModelsForBackend(app, app.llm.backend);
    if (models.length === 0) {
      const fallbackBackend = available.find((item) => availableModelsForBackend(app, item.name).length > 0);
      if (fallbackBackend) {
        app.llm.backend = fallbackBackend.name;
        models = availableModelsForBackend(app, app.llm.backend);
      }
    }

    if (!models.some((item) => item.name === app.llm.model)) {
      app.llm.model = models[0]?.name ?? '';
    }
  }

  async function loadLLMBackends(app, isStartup = false) {
    try {
      const response = await app.fetchWithRetry('/api/llm/backends', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load LLM backends');
      }
      app.llm.backends = payload.backends ?? [];
      pickDefaultLLMSelection(app);
      onPresetBackendChanged(app);
      app.syncNotesLLMSelection();
    } catch (error) {
      app.llm.backends = [];
      app.errorMessage = error.message;
    }
  }

  function onLLMBackendChanged(app) {
    const models = availableModelsForBackend(app, app.llm.backend);
    app.llm.model = models[0]?.name ?? '';
  }

  function onPresetBackendChanged(app) {
    let models = availableModelsForBackend(app, app.llm.presetForm.backend);
    if (models.length === 0) {
      const backend = app.llm.backends.find((item) => item.name === app.llm.presetForm.backend);
      models = backend?.models ?? [];
    }
    if (!models.some((item) => item.name === app.llm.presetForm.modelName)) {
      app.llm.presetForm.modelName = models[0]?.name ?? '';
    }
  }

  function resetPresetForm(app) {
    app.llm.presetForm = {
      id: null,
      name: '',
      backend: app.llm.backends.some((item) => item.name === 'ollama') ? 'ollama' : (app.llm.backends[0]?.name ?? ''),
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
    };
    onPresetBackendChanged(app);
  }

  function applyPresetToForm(app, preset) {
    app.llm.presetForm = {
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
      reasoningMode: preset.reasoning_mode || 'off',
      reasoningVisibility: preset.reasoning_visibility || 'hidden',
    };
    app.llm.selectedPresetId = String(preset.id);
  }

  async function loadLLMPresets(app, isStartup = false) {
    try {
      const response = await app.fetchWithRetry('/api/llm/presets', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load presets');
      }
      app.llm.presets = payload.presets ?? [];
      if (app.llm.selectedPresetId && !app.llm.presets.some((preset) => String(preset.id) === app.llm.selectedPresetId)) {
        app.llm.selectedPresetId = '';
      }
      if (app.settings.defaultPresetId && !app.llm.presets.some((preset) => String(preset.id) === app.settings.defaultPresetId)) {
        app.settings.defaultPresetId = '';
      }
      app.applyPresetPreference();
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function createPreset(app) {
    if (!app.llm.presetForm.name.trim()) {
      app.errorMessage = 'Preset name is required.';
      return;
    }
    if (!app.llm.presetForm.backend) {
      app.errorMessage = 'Select a backend for the preset.';
      return;
    }
    if (!app.llm.presetForm.modelName) {
      app.errorMessage = 'Select a model for the preset.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/presets/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: app.llm.presetForm.name.trim(),
          backend: app.llm.presetForm.backend,
          model_name: app.llm.presetForm.modelName,
          caption_mode_strategy: app.llm.presetForm.captionModeStrategy,
          system_prompt: app.llm.presetForm.systemPrompt,
          tool_web_search: app.llm.presetForm.toolWebSearch,
          tool_web_fetch: app.llm.presetForm.toolWebFetch,
          context_url_template: app.llm.presetForm.contextUrlTemplate,
          context_file_template: app.llm.presetForm.contextFileTemplate,
          include_project_notes: app.llm.presetForm.includeProjectNotes,
          include_global_notes: app.llm.presetForm.includeGlobalNotes,
          reasoning_mode: app.llm.presetForm.reasoningMode,
          reasoning_visibility: app.llm.presetForm.reasoningVisibility,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to create preset'));
      }
      await loadLLMPresets(app);
      applyPresetToForm(app, payload.preset);
      app.statusMessage = `Created preset ${payload.preset.name}.`;
    });
  }

  async function updatePreset(app) {
    if (!app.llm.presetForm.id) {
      app.errorMessage = 'Select a preset to update.';
      return;
    }
    if (!app.llm.presetForm.name.trim()) {
      app.errorMessage = 'Preset name is required.';
      return;
    }
    if (!app.llm.presetForm.backend) {
      app.errorMessage = 'Select a backend for the preset.';
      return;
    }
    if (!app.llm.presetForm.modelName) {
      app.errorMessage = 'Select a model for the preset.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/presets/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset_id: app.llm.presetForm.id,
          name: app.llm.presetForm.name.trim(),
          backend: app.llm.presetForm.backend,
          model_name: app.llm.presetForm.modelName,
          caption_mode_strategy: app.llm.presetForm.captionModeStrategy,
          system_prompt: app.llm.presetForm.systemPrompt,
          tool_web_search: app.llm.presetForm.toolWebSearch,
          tool_web_fetch: app.llm.presetForm.toolWebFetch,
          context_url_template: app.llm.presetForm.contextUrlTemplate,
          context_file_template: app.llm.presetForm.contextFileTemplate,
          include_project_notes: app.llm.presetForm.includeProjectNotes,
          include_global_notes: app.llm.presetForm.includeGlobalNotes,
          reasoning_mode: app.llm.presetForm.reasoningMode,
          reasoning_visibility: app.llm.presetForm.reasoningVisibility,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to update preset'));
      }
      await loadLLMPresets(app);
      applyPresetToForm(app, payload.preset);
      app.statusMessage = `Updated preset ${payload.preset.name}.`;
    });
  }

  async function deletePreset(app) {
    if (!app.llm.presetForm.id) {
      app.errorMessage = 'Select a preset to delete.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/presets/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset_id: app.llm.presetForm.id,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to delete preset');
      }
      await loadLLMPresets(app);
      resetPresetForm(app);
      app.llm.selectedPresetId = '';
      app.statusMessage = `Deleted preset ${payload.deleted_preset_id}.`;
    });
  }

  function onSelectedPresetChanged(app) {
    const preset = app.llm.presets.find((item) => String(item.id) === String(app.llm.selectedPresetId));
    if (preset) {
      applyPresetToForm(app, preset);
    }
  }

  async function generateCaptionWithPreset(app) {
    if (!app.currentProject?.path || !app.selectedImage) {
      app.errorMessage = 'Open a project and select an image first.';
      return;
    }
    if (!app.llm.selectedPresetId) {
      app.errorMessage = 'Choose a preset first.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/generate-with-preset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          preset_id: Number(app.llm.selectedPresetId),
          make_active: app.llm.makeActive,
          timeout_seconds: app.settings.llmTimeoutSeconds,
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
      app.statusMessage = `Generated caption with preset ${payload.preset.name}${eventLabel}.${modeLabel ? ` ${modeLabel}.` : ''}`;
      await app.selectImage(app.selectedImage.id, false);
      await app.loadImages();
      await app.loadImageSummary();
    });
  }

  async function generateCaptionWithLLM(app) {
    if (!app.currentProject?.path || !app.selectedImage) {
      app.errorMessage = 'Open a project and select an image first.';
      return;
    }
    if (!app.llm.backend || !app.llm.model) {
      app.errorMessage = 'Select an available backend and model first.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/generate-caption', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          backend: app.llm.backend,
          model: app.llm.model,
          extra_instructions: app.llm.extraInstructions,
          make_active: app.llm.makeActive,
          timeout_seconds: app.settings.llmTimeoutSeconds,
          reasoning_mode: app.llm.tools.reasoningMode,
          reasoning_visibility: app.llm.tools.reasoningVisibility,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Caption generation failed');
      }
      app.statusMessage = `Generated caption with ${payload.backend}/${payload.model}.`;
      await app.selectImage(app.selectedImage.id, false);
      await app.loadImages();
      await app.loadImageSummary();
    });
  }

  async function generateCaptionWithTools(app) {
    if (!app.currentProject?.path || !app.selectedImage) {
      app.errorMessage = 'Open a project and select an image first.';
      return;
    }
    if (!app.llm.backend || !app.llm.model) {
      app.errorMessage = 'Select an available backend and model first.';
      return;
    }
    const toolsEnabled = [];
    if (app.llm.tools.webSearch) toolsEnabled.push('web_search');
    if (app.llm.tools.webFetch) toolsEnabled.push('web_fetch');
    const selectedModel = selectedLLMModel(app);
    let fallbackNotice = '';
    if (toolsEnabled.length > 0 && selectedModel && !selectedModel.tool_capable) {
      toolsEnabled.length = 0;
      fallbackNotice = ` Model ${app.llm.model} is not tool-capable, so tools were skipped.`;
    }
    const contextUrls = app.llm.tools.contextUrl.trim() ? [app.llm.tools.contextUrl.trim()] : [];
    const contextFiles = app.llm.tools.contextFile.trim() ? [app.llm.tools.contextFile.trim()] : [];
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/generate-caption-with-tools', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          backend: app.llm.backend,
          model: app.llm.model,
          extra_instructions: app.llm.extraInstructions,
          make_active: app.llm.makeActive,
          timeout_seconds: app.settings.llmTimeoutSeconds,
          tools_enabled: toolsEnabled,
          context_urls: contextUrls,
          context_files: contextFiles,
          include_project_notes: app.llm.tools.includeProjectNotes,
          include_global_notes: app.llm.tools.includeGlobalNotes,
          reasoning_mode: app.llm.tools.reasoningMode,
          reasoning_visibility: app.llm.tools.reasoningVisibility,
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
      app.statusMessage = `Generated caption with ${payload.backend}/${payload.model}${log}. ${modeLabel}.${fallbackNotice}`;
      await app.selectImage(app.selectedImage.id, false);
      await app.loadImages();
      await app.loadImageSummary();
    });
  }

  features.llm = {
    selectedLLMBackend,
    selectedLLMModel,
    modelCapabilityLabel,
    modelOptionLabel,
    availableModelsForBackend,
    onModelVisibilityFilterChanged,
    pickDefaultLLMSelection,
    loadLLMBackends,
    onLLMBackendChanged,
    onPresetBackendChanged,
    resetPresetForm,
    applyPresetToForm,
    loadLLMPresets,
    createPreset,
    updatePreset,
    deletePreset,
    onSelectedPresetChanged,
    generateCaptionWithPreset,
    generateCaptionWithLLM,
    generateCaptionWithTools,
  };
})(window);