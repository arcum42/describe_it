(function initDescribeItFeatureBrowser(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  const pickerConfig = {
    create_project_path: { label: 'project folder for create path', expects: 'directory' },
    open_project_db: { label: 'project database file', expects: 'db_file' },
    import_source_folder: { label: 'import source folder', expects: 'directory' },
    import_source_image: { label: 'import source image file', expects: 'file' },
    export_output_folder: { label: 'export output folder', expects: 'directory' },
    metadata_context_file: { label: 'project context file', expects: 'file' },
    llm_context_file: { label: 'LLM context file', expects: 'file' },
    notes_context_file: { label: 'notes context file', expects: 'file' },
  };

  async function loadBrowser(app, path = null, isStartup = false) {
    try {
      const url = new URL('/api/projects/browser', window.location.origin);
      if (path) {
        url.searchParams.set('path', path);
      }
      const response = await app.fetchWithRetry(url, {}, { attempts: isStartup ? 4 : 1, delayMs: 200 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to browse paths');
      }
      app.browser = {
        currentPath: payload.current_path,
        parentPath: payload.parent_path,
        directories: payload.directories ?? [],
        dbFiles: payload.db_files ?? [],
        files: payload.files ?? [],
        roots: payload.roots ?? [],
      };
      app.projectSession.lastProjectDirectory = app.browser.currentPath || app.projectSession.lastProjectDirectory;
      app.saveProjectSessionState();
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  function chooseCreateDirectory(app, path) {
    const trimmedName = (app.createForm.name || 'my_project').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'my_project';
    app.createForm.path = `${path}/${trimmedName}.db`;
    app.projectSession.lastProjectDirectory = path;
    app.saveProjectSessionState();
    app.statusMessage = `Create path set to ${app.createForm.path}`;
    app.errorMessage = '';
  }

  function chooseOpenFile(app, path) {
    app.openForm.path = path;
    const lastSeparator = path.lastIndexOf('/');
    if (lastSeparator > 0) {
      app.projectSession.lastProjectDirectory = path.slice(0, lastSeparator);
    }
    app.saveProjectSessionState();
    app.statusMessage = `Open path set to ${path}`;
    app.errorMessage = '';
  }

  function chooseExportDirectory(app, path) {
    app.exportForm.output_folder = path;
    app.projectSession.lastProjectDirectory = path;
    app.saveProjectSessionState();
    app.exportPreview = null;
    app.statusMessage = `Export folder set to ${path}`;
    app.errorMessage = '';
  }

  function pathPickerStartPath(app, target) {
    const pickerSourceMap = {
      create_project_path: app.createForm.path,
      open_project_db: app.openForm.path,
      import_source_folder: app.importForm.source_folder,
      import_source_image: app.importForm.source_image,
      export_output_folder: app.exportForm.output_folder,
      metadata_context_file: app.metadataForm.context_file_path,
      llm_context_file: app.llm.tools.contextFile,
      notes_context_file: app.notes.llm.contextFile,
    };
    const rawValue = pickerSourceMap[target];
    if (typeof rawValue !== 'string') {
      return '';
    }
    return rawValue.trim();
  }

  async function requestNativePathPicker(app, config, startPath = '') {
    const fallbackStartPath = app.browser.currentPath || app.projectSession.lastProjectDirectory || '';
    try {
      const response = await fetch('/api/projects/native-picker', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          kind: config.expects,
          title: `Select ${config.label}`,
          start_path: startPath || fallbackStartPath,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to open native picker'));
      }
      return {
        available: payload.available === true,
        selected_path: payload.selected_path || '',
        reason: payload.reason || '',
      };
    } catch (error) {
      return {
        available: false,
        selected_path: '',
        reason: error?.message || 'Failed to invoke native picker.',
      };
    }
  }

  function browsePickerModeLabel(app) {
    return app.settings.useNativePathPicker ? 'Native' : 'Browser';
  }

  function clearPathPicker(app) {
    app.pathPicker.target = '';
    app.pathPicker.label = '';
    app.pathPicker.expects = 'directory';
  }

  function pickerExpectsDirectory(app) {
    return app.pathPicker.expects === 'directory';
  }

  function pickerExpectsFile(app) {
    return app.pathPicker.expects === 'file' || app.pathPicker.expects === 'db_file';
  }

  function pickerAcceptsFile(app, fileKind = 'file') {
    if (!app.pathPicker.target) {
      return false;
    }
    if (app.pathPicker.expects === 'db_file') {
      return fileKind === 'db';
    }
    if (app.pathPicker.expects === 'file') {
      return fileKind === 'file' || fileKind === 'db';
    }
    return false;
  }

  function updateLastDirectoryFromPath(app, path, isFile = false) {
    if (!path) {
      return;
    }
    if (!isFile) {
      app.projectSession.lastProjectDirectory = path;
      app.saveProjectSessionState();
      return;
    }
    const lastSeparator = path.lastIndexOf('/');
    if (lastSeparator > 0) {
      app.projectSession.lastProjectDirectory = path.slice(0, lastSeparator);
      app.saveProjectSessionState();
    }
  }

  function applyPathPickerSelection(app, path, kind) {
    if (!app.pathPicker.target) {
      return;
    }
    if (kind === 'directory') {
      if (app.pathPicker.target === 'create_project_path') {
        chooseCreateDirectory(app, path);
      } else if (app.pathPicker.target === 'import_source_folder') {
        app.importForm.source_folder = path;
        updateLastDirectoryFromPath(app, path, false);
        app.statusMessage = `Import folder set to ${path}`;
        app.errorMessage = '';
      } else if (app.pathPicker.target === 'export_output_folder') {
        chooseExportDirectory(app, path);
      }
      clearPathPicker(app);
      return;
    }

    if (app.pathPicker.target === 'open_project_db') {
      chooseOpenFile(app, path);
    } else if (app.pathPicker.target === 'import_source_image') {
      app.importForm.source_image = path;
      updateLastDirectoryFromPath(app, path, true);
      app.statusMessage = `Import image path set to ${path}`;
    } else if (app.pathPicker.target === 'metadata_context_file') {
      app.metadataForm.context_file_path = path;
      updateLastDirectoryFromPath(app, path, true);
      app.statusMessage = `Project context file set to ${path}`;
    } else if (app.pathPicker.target === 'llm_context_file') {
      app.llm.tools.contextFile = path;
      updateLastDirectoryFromPath(app, path, true);
      app.statusMessage = `LLM context file set to ${path}`;
    } else if (app.pathPicker.target === 'notes_context_file') {
      app.notes.llm.contextFile = path;
      updateLastDirectoryFromPath(app, path, true);
      app.statusMessage = `Notes context file set to ${path}`;
    }
    app.errorMessage = '';
    clearPathPicker(app);
  }

  function useCurrentBrowserDirectory(app) {
    if (!app.pathPicker.target || !pickerExpectsDirectory(app) || !app.browser.currentPath) {
      return;
    }
    applyPathPickerSelection(app, app.browser.currentPath, 'directory');
  }

  function useBrowserFile(app, path, fileKind = 'file') {
    if (app.pathPicker.target) {
      if (!pickerAcceptsFile(app, fileKind)) {
        app.errorMessage = 'Selected file type is not valid for this field.';
        return;
      }
      applyPathPickerSelection(app, path, 'file');
      return;
    }
    if (fileKind === 'db') {
      chooseOpenFile(app, path);
    }
  }

  async function openPathPicker(app, target) {
    const config = pickerConfig[target];
    if (!config) {
      app.errorMessage = 'Unsupported browse target.';
      return;
    }

    app.pathPicker.target = target;
    app.pathPicker.label = config.label;
    app.pathPicker.expects = config.expects;
    const startPath = pathPickerStartPath(app, target);

    if (!app.settings.useNativePathPicker) {
      app.showBrowser = true;
      await app.loadBrowser(startPath || app.browser.currentPath || app.projectSession.lastProjectDirectory || null);
      app.statusMessage = `Select ${config.label} from browser.`;
      app.errorMessage = '';
      return;
    }

    app.statusMessage = 'Opening native picker...';
    app.errorMessage = '';
    const nativeResult = await requestNativePathPicker(app, config, startPath);
    if (nativeResult.available) {
      if (nativeResult.selected_path) {
        const selectionKind = config.expects === 'directory' ? 'directory' : 'file';
        applyPathPickerSelection(app, nativeResult.selected_path, selectionKind);
        return;
      }
      clearPathPicker(app);
      app.statusMessage = 'Native picker canceled.';
      app.errorMessage = '';
      return;
    }

    app.showBrowser = true;
    await app.loadBrowser(startPath || app.browser.currentPath || app.projectSession.lastProjectDirectory || null);
    app.statusMessage = nativeResult.reason
      ? `Native picker unavailable (${nativeResult.reason}). Select ${config.label} from browser.`
      : `Select ${config.label} from browser.`;
    app.errorMessage = '';
  }

  features.browser = {
    loadBrowser,
    chooseCreateDirectory,
    chooseOpenFile,
    chooseExportDirectory,
    openPathPicker,
    pathPickerStartPath,
    requestNativePathPicker,
    browsePickerModeLabel,
    clearPathPicker,
    pickerExpectsDirectory,
    pickerExpectsFile,
    pickerAcceptsFile,
    updateLastDirectoryFromPath,
    useCurrentBrowserDirectory,
    useBrowserFile,
    applyPathPickerSelection,
  };
})(window);