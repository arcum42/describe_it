(function initDescribeItFeatureSettings(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function normalizeTimeout(value) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
      return 120;
    }
    return Math.min(900, Math.max(10, parsed));
  }

  function normalizeOptionalTimeout(value) {
    if (value === '' || value === null || value === undefined) {
      return '';
    }
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
      return '';
    }
    return Math.min(900, Math.max(10, parsed));
  }

  function normalizeOptionalNumCtx(value) {
    if (value === '' || value === null || value === undefined) {
      return '';
    }
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
      return '';
    }
    return Math.min(262144, Math.max(256, parsed));
  }

  function normalizeZoomMode(value) {
    const normalized = String(value || '').trim().toLowerCase();
    if (normalized === 'fit' || normalized === 'full' || normalized === 'percent') {
      return normalized;
    }
    return 'fit';
  }

  function normalizeZoomPercent(value) {
    const parsed = Number.parseInt(value, 10);
    if (!Number.isFinite(parsed)) {
      return 100;
    }
    return Math.min(400, Math.max(25, parsed));
  }

  async function loadSettings(app, isStartup = false) {
    try {
      const response = await app.fetchWithRetry('/api/llm/settings', {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load settings');
      }
      app.settings.llmTimeoutSeconds = normalizeTimeout(payload.llm_timeout_seconds);
      app.settings.usePresetByDefault = payload.llm_use_preset_by_default === true;
      app.settings.defaultPresetId = payload.llm_default_preset_id ? String(payload.llm_default_preset_id) : '';
      app.settings.showDebugSection = payload.ui_show_debug_section === true;
      app.settings.ollamaBaseUrl = payload.ollama_base_url || 'http://127.0.0.1:11434';
      app.settings.lmstudioBaseUrl = payload.lmstudio_base_url || 'http://127.0.0.1:1234';
      app.settings.ollamaTimeoutSeconds = normalizeOptionalTimeout(payload.ollama_timeout_seconds);
      app.settings.lmstudioTimeoutSeconds = normalizeOptionalTimeout(payload.lmstudio_timeout_seconds);
      app.settings.ollamaNumCtx = normalizeOptionalNumCtx(payload.ollama_num_ctx);
      app.settings.lmstudioNumCtx = normalizeOptionalNumCtx(payload.lmstudio_num_ctx);
      app.settings.editorDefaultImageZoomMode = normalizeZoomMode(payload.editor_default_image_zoom_mode);
      app.settings.editorDefaultImageZoomPercent = normalizeZoomPercent(payload.editor_default_image_zoom_percent);
      app.resetEditorZoomToDefault();
      app.applyPresetPreference();
    } catch (error) {
      app.settings.llmTimeoutSeconds = 120;
      app.settings.usePresetByDefault = false;
      app.settings.defaultPresetId = '';
      app.settings.showDebugSection = false;
      app.settings.ollamaBaseUrl = 'http://127.0.0.1:11434';
      app.settings.lmstudioBaseUrl = 'http://127.0.0.1:1234';
      app.settings.ollamaTimeoutSeconds = '';
      app.settings.lmstudioTimeoutSeconds = '';
      app.settings.ollamaNumCtx = '';
      app.settings.lmstudioNumCtx = '';
      app.settings.editorDefaultImageZoomMode = 'fit';
      app.settings.editorDefaultImageZoomPercent = 100;
      app.resetEditorZoomToDefault();
    }
  }

  async function saveSettings(app) {
    app.settings.llmTimeoutSeconds = normalizeTimeout(app.settings.llmTimeoutSeconds);
    app.settings.ollamaTimeoutSeconds = normalizeOptionalTimeout(app.settings.ollamaTimeoutSeconds);
    app.settings.lmstudioTimeoutSeconds = normalizeOptionalTimeout(app.settings.lmstudioTimeoutSeconds);
    app.settings.ollamaNumCtx = normalizeOptionalNumCtx(app.settings.ollamaNumCtx);
    app.settings.lmstudioNumCtx = normalizeOptionalNumCtx(app.settings.lmstudioNumCtx);
    app.settings.editorDefaultImageZoomMode = normalizeZoomMode(app.settings.editorDefaultImageZoomMode);
    app.settings.editorDefaultImageZoomPercent = normalizeZoomPercent(app.settings.editorDefaultImageZoomPercent);
    const defaultPresetId = app.settings.defaultPresetId ? Number(app.settings.defaultPresetId) : null;
    const ollamaTimeoutSeconds = app.settings.ollamaTimeoutSeconds === '' ? null : Number(app.settings.ollamaTimeoutSeconds);
    const lmstudioTimeoutSeconds = app.settings.lmstudioTimeoutSeconds === '' ? null : Number(app.settings.lmstudioTimeoutSeconds);
    const ollamaNumCtx = app.settings.ollamaNumCtx === '' ? null : Number(app.settings.ollamaNumCtx);
    const lmstudioNumCtx = app.settings.lmstudioNumCtx === '' ? null : Number(app.settings.lmstudioNumCtx);

    try {
      const response = await fetch('/api/llm/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          llm_timeout_seconds: app.settings.llmTimeoutSeconds,
          llm_use_preset_by_default: app.settings.usePresetByDefault,
          llm_default_preset_id: defaultPresetId,
          ui_show_debug_section: app.settings.showDebugSection,
          ollama_base_url: app.settings.ollamaBaseUrl,
          lmstudio_base_url: app.settings.lmstudioBaseUrl,
          ollama_timeout_seconds: ollamaTimeoutSeconds,
          lmstudio_timeout_seconds: lmstudioTimeoutSeconds,
          ollama_num_ctx: ollamaNumCtx,
          lmstudio_num_ctx: lmstudioNumCtx,
          editor_default_image_zoom_mode: app.settings.editorDefaultImageZoomMode,
          editor_default_image_zoom_percent: app.settings.editorDefaultImageZoomPercent,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to save settings');
      }

      app.settings.llmTimeoutSeconds = normalizeTimeout(payload.llm_timeout_seconds);
      app.settings.usePresetByDefault = payload.llm_use_preset_by_default === true;
      app.settings.defaultPresetId = payload.llm_default_preset_id ? String(payload.llm_default_preset_id) : '';
      app.settings.showDebugSection = payload.ui_show_debug_section === true;
      app.settings.ollamaBaseUrl = payload.ollama_base_url || 'http://127.0.0.1:11434';
      app.settings.lmstudioBaseUrl = payload.lmstudio_base_url || 'http://127.0.0.1:1234';
      app.settings.ollamaTimeoutSeconds = normalizeOptionalTimeout(payload.ollama_timeout_seconds);
      app.settings.lmstudioTimeoutSeconds = normalizeOptionalTimeout(payload.lmstudio_timeout_seconds);
      app.settings.ollamaNumCtx = normalizeOptionalNumCtx(payload.ollama_num_ctx);
      app.settings.lmstudioNumCtx = normalizeOptionalNumCtx(payload.lmstudio_num_ctx);
      app.settings.editorDefaultImageZoomMode = normalizeZoomMode(payload.editor_default_image_zoom_mode);
      app.settings.editorDefaultImageZoomPercent = normalizeZoomPercent(payload.editor_default_image_zoom_percent);
      app.resetEditorZoomToDefault();
      app.projectSession.reopenLastProject = app.settings.reopenLastProjectOnStartup;
      await app.saveProjectSessionState();
      app.applyPresetPreference();
      app.statusMessage = `Saved settings. LLM timeout set to ${app.settings.llmTimeoutSeconds}s.`;
      app.errorMessage = '';
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function testConnection(app, backend) {
    const urlKey = backend === 'ollama' ? 'ollamaBaseUrl' : 'lmstudioBaseUrl';
    const testingKey = backend === 'ollama' ? 'ollamaTesting' : 'lmstudioTesting';
    app.connectionTest[testingKey] = true;
    app.connectionTest[backend] = null;

    try {
      const response = await fetch('/api/llm/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backend, url: app.settings[urlKey] }),
      });
      const payload = await response.json();
      app.connectionTest[backend] = payload;
    } catch (error) {
      app.connectionTest[backend] = { ok: false, message: error.message };
    } finally {
      app.connectionTest[testingKey] = false;
    }
  }

  features.settings = {
    normalizeTimeout,
    normalizeOptionalTimeout,
    normalizeOptionalNumCtx,
    normalizeZoomMode,
    normalizeZoomPercent,
    loadSettings,
    saveSettings,
    testConnection,
  };
})(window);