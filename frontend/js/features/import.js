(function initDescribeItFeatureImport(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  async function importFolder(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/projects/import-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          source_folder: app.importForm.source_folder,
          replace_existing: app.importForm.replace_existing,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Import failed');
      }
      const result = payload.result;
      app.statusMessage = `Imported ${result.imported_images} images (${result.captions_from_files} with captions, ${result.blank_captions} blank).`;
      await app.loadImages();
      await app.loadImageSummary();
    }, 'importFolder');
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