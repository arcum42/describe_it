(function initDescribeItFeatureUiShell(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function showKeyboardShortcutsHelp(app) {
    app.keyboard.showShortcutsHelp = true;
  }

  function closeKeyboardShortcutsHelp(app) {
    app.keyboard.showShortcutsHelp = false;
  }

  function isTagMode(app) {
    return app.currentProject?.caption_mode === 'tags';
  }

  function editorSubTabs(app) {
    const tabs = [
      { id: 'caption', label: 'Caption' },
      { id: 'image', label: 'Image' },
    ];
    if (isTagMode(app)) {
      tabs.push({ id: 'batch_tags', label: 'Batch Tags' });
    }
    return tabs;
  }

  function setEditorSubTab(app, nextTab) {
    const allowed = editorSubTabs(app).map((tab) => tab.id);
    app.editorView.subTab = allowed.includes(nextTab) ? nextTab : 'caption';
  }

  function ensureEditorSubTab(app) {
    const allowed = editorSubTabs(app).map((tab) => tab.id);
    if (!allowed.includes(app.editorView.subTab)) {
      app.editorView.subTab = 'caption';
    }
  }

  function batchSubTabs() {
    return [
      { id: 'generate', label: 'Generate' },
      { id: 'text_edit', label: 'Text Edit' },
    ];
  }

  function setBatchSubTab(app, nextTab) {
    const allowed = batchSubTabs().map((tab) => tab.id);
    app.batch.subTab = allowed.includes(nextTab) ? nextTab : 'generate';
    if (app.batch.subTab === 'text_edit') {
      app.loadCaptionBatchOperations(true);
    }
  }

  function ensureBatchSubTab(app) {
    const allowed = batchSubTabs().map((tab) => tab.id);
    if (!allowed.includes(app.batch.subTab)) {
      app.batch.subTab = 'generate';
    }
  }

  function isPanelOpen(app, panelKey, fallback = true) {
    if (Object.prototype.hasOwnProperty.call(app.panelState, panelKey)) {
      return app.panelState[panelKey] === true;
    }
    return fallback;
  }

  function togglePanel(app, panelKey, fallback = true) {
    const current = isPanelOpen(app, panelKey, fallback);
    app.panelState[panelKey] = !current;
  }

  function panelTriangle(app, panelKey, fallback = true) {
    return isPanelOpen(app, panelKey, fallback) ? '▼' : '▶';
  }

  function applyPanelStateFromSettings(app, panelStatePayload) {
    if (!panelStatePayload || typeof panelStatePayload !== 'object') {
      return;
    }
    const nextPanelState = { ...app.panelState };
    Object.keys(app.panelState).forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(panelStatePayload, key)) {
        nextPanelState[key] = panelStatePayload[key] === true;
      }
    });
    app.panelState = nextPanelState;
  }

  function panelStatePayload(app) {
    const payload = {};
    Object.keys(app.panelState).forEach((key) => {
      payload[key] = app.panelState[key] === true;
    });
    return payload;
  }

  features.uiShell = {
    showKeyboardShortcutsHelp,
    closeKeyboardShortcutsHelp,
    isTagMode,
    editorSubTabs,
    setEditorSubTab,
    ensureEditorSubTab,
    batchSubTabs,
    setBatchSubTab,
    ensureBatchSubTab,
    isPanelOpen,
    togglePanel,
    panelTriangle,
    applyPanelStateFromSettings,
    panelStatePayload,
  };
})(window);
