(function initDescribeItFeatureImport(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function resetImportProgress(app) {
    app.importProgress.active = false;
    app.importProgress.total = 0;
    app.importProgress.current = 0;
    app.importProgress.percent = 0;
    app.importProgress.currentFilename = '';
    app.importProgress.label = '';
  }

  function updateImportProgress(app, current, total, filename = '') {
    const normalizedTotal = Math.max(0, Number(total || 0));
    const normalizedCurrent = Math.max(0, Number(current || 0));
    const percent = normalizedTotal > 0
      ? Math.min(100, Math.round((normalizedCurrent / normalizedTotal) * 100))
      : 0;
    app.importProgress.active = true;
    app.importProgress.total = normalizedTotal;
    app.importProgress.current = normalizedCurrent;
    app.importProgress.percent = percent;
    app.importProgress.currentFilename = filename || '';
    app.importProgress.label = normalizedTotal > 0
      ? `${normalizedCurrent} / ${normalizedTotal} (${percent}%)`
      : 'Preparing import...';
  }

  function applyStreamEvent(app, event) {
    if (!event || typeof event !== 'object') {
      return { completedResult: null, errorMessage: null };
    }
    if (event.type === 'start') {
      updateImportProgress(app, 0, event.total || 0, '');
      return { completedResult: null, errorMessage: null };
    }
    if (event.type === 'progress') {
      updateImportProgress(app, event.current || 0, event.total || 0, event.filename || '');
      return { completedResult: null, errorMessage: null };
    }
    if (event.type === 'error') {
      return { completedResult: null, errorMessage: event.message || 'Import failed.' };
    }
    if (event.type === 'complete' && event.result) {
      const result = event.result;
      updateImportProgress(app, result.imported_images || 0, result.imported_images || 0, '');
      app.importProgress.active = false;
      return { completedResult: result, errorMessage: null };
    }
    return { completedResult: null, errorMessage: null };
  }

  async function importFolderWithProgress(app) {
    const response = await fetch('/api/projects/import-folder-stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_path: app.currentProject.path,
        source_folder: app.importForm.source_folder,
        replace_existing: app.importForm.replace_existing,
        default_caption: app.importForm.default_caption,
      }),
    });

    if (!response.ok) {
      let payload = null;
      try {
        payload = await response.json();
      } catch (error) {
        payload = null;
      }
      throw new Error(app.formatApiError(payload, 'Import failed'));
    }

    if (!response.body) {
      throw new Error('Import progress stream is unavailable.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let completedResult = null;
    let streamError = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split('\n\n');
      buffer = chunks.pop() || '';

      for (const chunk of chunks) {
        const dataLines = chunk
          .split('\n')
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim());
        if (dataLines.length === 0) {
          continue;
        }

        let event = null;
        try {
          event = JSON.parse(dataLines.join('\n'));
        } catch (error) {
          continue;
        }

        const eventResult = applyStreamEvent(app, event);
        if (eventResult.errorMessage) {
          streamError = eventResult.errorMessage;
          break;
        }
        if (eventResult.completedResult) {
          completedResult = eventResult.completedResult;
        }
      }

      if (streamError) {
        break;
      }
    }

    if (streamError) {
      throw new Error(streamError);
    }
    if (!completedResult) {
      throw new Error('Import ended before completion.');
    }
    return completedResult;
  }

  async function importFolderWithoutProgressStream(app) {
    const response = await fetch('/api/projects/import-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_path: app.currentProject.path,
        source_folder: app.importForm.source_folder,
        replace_existing: app.importForm.replace_existing,
        default_caption: app.importForm.default_caption,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(app.formatApiError(payload, 'Import failed'));
    }
    return payload.result;
  }

  async function importFolder(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }
    await app.withSubmitting(async () => {
      resetImportProgress(app);
      app.importProgress.active = true;
      app.importProgress.label = 'Preparing import...';

      let result = null;
      try {
        result = await importFolderWithProgress(app);
      } catch (error) {
        // Fallback keeps import functional if streaming is unsupported by the browser/server path.
        app.importProgress.label = 'Streaming unavailable, finishing import...';
        result = await importFolderWithoutProgressStream(app);
        updateImportProgress(app, result.imported_images || 0, result.imported_images || 0, '');
      }
      const defaultCaptionApplied = Number(result.default_captions_applied || 0);
      app.statusMessage = `Imported ${result.imported_images} images (${result.captions_from_files} from sidecar, ${defaultCaptionApplied} defaulted, ${result.blank_captions} blank).`;
      await app.loadImages();
      await app.loadImageSummary();
    }, 'importFolder');
    app.importProgress.active = false;
  }

  async function importSingleImage(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/projects/import-image', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          source_image: app.importForm.source_image,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Single image import failed');
      }
      const result = payload.result;
      const filename = String(result.source_image).split(/[\\/]/).pop() || result.source_image;
      app.statusMessage = `Imported image ${filename} (${result.captions_from_files ? 'with caption file' : 'blank caption'}).`;
      await app.loadImages();
      await app.loadImageSummary();
    }, 'importSingleImage');
  }

  features.import = {
    importFolder,
    importSingleImage,
  };
})(window);