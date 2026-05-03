(function initDescribeItFeatureExport(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function clearExportPreview(app) {
    app.exportPreview = null;
  }

  function normalizeExportFormOptions(app) {
    if (app.exportForm.clean_output_folder && app.exportForm.overwrite_existing) {
      app.exportForm.overwrite_existing = false;
    }
    if (!app.exportForm.create_new_folder) {
      app.exportForm.new_folder_name = '';
    }
  }

  async function requestExportPreview(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }
    if (!app.exportForm.output_folder.trim()) {
      app.errorMessage = 'Select an export output folder first.';
      return;
    }

    normalizeExportFormOptions(app);
    app.errorMessage = '';
    app.statusMessage = '';
    try {
      const response = await fetch('/api/projects/export-preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          output_folder: app.exportForm.output_folder,
          included_only: app.exportForm.included_only,
          apply_trigger_word: app.exportForm.apply_trigger_word,
          create_new_folder: app.exportForm.create_new_folder,
          new_folder_name: app.exportForm.new_folder_name,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Export preview failed');
      }
      app.exportPreview = payload.result;
      app.statusMessage = `Preview ready: ${app.exportPreview.images_to_export} image(s) will be exported.`;
    } catch (error) {
      app.exportPreview = null;
      app.errorMessage = error.message;
    }
  }

  async function exportProjectDataset(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }
    if (!app.exportForm.output_folder.trim()) {
      app.errorMessage = 'Select an export output folder first.';
      return;
    }
    normalizeExportFormOptions(app);
    if (app.exportForm.clean_output_folder && app.exportForm.overwrite_existing) {
      app.errorMessage = 'Choose either clean output folder or overwrite existing files.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/projects/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          output_folder: app.exportForm.output_folder,
          included_only: app.exportForm.included_only,
          apply_trigger_word: app.exportForm.apply_trigger_word,
          include_metadata: app.exportForm.include_metadata,
          overwrite_existing: app.exportForm.overwrite_existing,
          clean_output_folder: app.exportForm.clean_output_folder,
          create_new_folder: app.exportForm.create_new_folder,
          new_folder_name: app.exportForm.new_folder_name,
          include_project_notes: app.exportForm.include_project_notes,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Export failed');
      }
      const result = payload.result;
      const collisionSuffix = result.skipped_due_to_collision ? `, ${result.skipped_due_to_collision} skipped due to collisions` : '';
      const blobSuffix = result.skipped_missing_blob ? `, ${result.skipped_missing_blob} missing image data` : '';
      const metadataSuffix = result.metadata_written && result.metadata_file ? ' Metadata manifest written.' : '';
      const notesSuffix = result.exported_notes ? ` ${result.exported_notes} note(s) exported to notes/.` : '';
      app.statusMessage = `Exported ${result.exported_images} images to ${result.output_folder}${result.skipped_images ? ` (${result.skipped_images} skipped${collisionSuffix}${blobSuffix})` : ''}.${metadataSuffix}${notesSuffix}`;
      app.exportPreview = null;
    }, 'exportDataset');
  }

  features.export = {
    clearExportPreview,
    normalizeExportFormOptions,
    requestExportPreview,
    exportProjectDataset,
  };
})(window);