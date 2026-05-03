(function initDescribeItFeatureBrowser(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

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

  features.browser = {
    loadBrowser,
    chooseCreateDirectory,
    chooseOpenFile,
    chooseExportDirectory,
  };
})(window);