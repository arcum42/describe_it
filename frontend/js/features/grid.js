(function initDescribeItFeatureGrid(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function normalizedSelectedIds(app) {
    const ids = Array.isArray(app.selectedGridImageIds) ? app.selectedGridImageIds : [];
    return [...new Set(ids.filter((imageId) => Number.isInteger(imageId)))];
  }

  function setSelectedIds(app, imageIds) {
    app.selectedGridImageIds = [...new Set((imageIds || []).filter((imageId) => Number.isInteger(imageId)))];
  }

  function clearGridSelection(app) {
    app.selectedGridImageIds = [];
  }

  function clearDuplicateCleanupPreview(app) {
    app.duplicateCleanup.preview = null;
  }

  function selectedGridCount(app) {
    return normalizedSelectedIds(app).length;
  }

  function isGridImageSelected(app, imageId) {
    return normalizedSelectedIds(app).includes(imageId);
  }

  function toggleGridSelectionMode(app) {
    app.gridSelectionMode = !app.gridSelectionMode;
    if (!app.gridSelectionMode) {
      clearGridSelection(app);
    }
  }

  function toggleGridImageSelection(app, imageId) {
    const selectedIds = normalizedSelectedIds(app);
    if (selectedIds.includes(imageId)) {
      setSelectedIds(app, selectedIds.filter((candidateId) => candidateId !== imageId));
      return;
    }
    setSelectedIds(app, [...selectedIds, imageId]);
  }

  function selectFilteredGridImages(app) {
    const filteredIds = (app.filteredGridCards?.() || []).map((card) => card.id).filter((imageId) => Number.isInteger(imageId));
    setSelectedIds(app, filteredIds);
    if (!app.gridSelectionMode) {
      app.gridSelectionMode = true;
    }
    app.statusMessage = `Selected ${filteredIds.length} filtered image(s).`;
  }

  function onImagesLoaded(app) {
    const validImageIds = new Set((app.images || []).map((image) => image.id));
    setSelectedIds(app, normalizedSelectedIds(app).filter((imageId) => validImageIds.has(imageId)));
    if (!app.currentProject?.path) {
      app.gridSelectionMode = false;
      clearDuplicateCleanupPreview(app);
    }
  }

  function filteredGridCards(app) {
    let filtered = Array.isArray(app.gridCards) ? [...app.gridCards] : [];

    if (app.gridFilter.searchText.trim()) {
      const search = app.gridFilter.searchText.toLowerCase();
      const mode = String(app.gridFilter.searchMode || 'filename');
      filtered = filtered.filter((card) => {
        const inFilename = card.label.toLowerCase().includes(search)
          || (card.filename && card.filename.toLowerCase().includes(search));
        const inCaption = (card.caption_search_text || card.active_caption_preview || '').toLowerCase().includes(search);
        if (mode === 'caption') {
          return inCaption;
        }
        if (mode === 'both') {
          return inFilename || inCaption;
        }
        return inFilename;
      });
    }

    if (app.gridFilter.inclusionStatus === 'included') {
      filtered = filtered.filter((card) => card.included === true);
    } else if (app.gridFilter.inclusionStatus === 'excluded') {
      filtered = filtered.filter((card) => card.included === false);
    }

    if (app.gridFilter.captionStatus === 'with_captions') {
      filtered = filtered.filter((card) => card.active_caption_preview && card.active_caption_preview.trim() !== '');
    } else if (app.gridFilter.captionStatus === 'blank_captions') {
      filtered = filtered.filter((card) => !card.active_caption_preview || card.active_caption_preview.trim() === '');
    }

    const sortBy = app.gridFilter.sortBy;
    const sortOrder = app.gridFilter.sortOrder === 'desc' ? -1 : 1;

    if (sortBy === 'name') {
      filtered.sort((a, b) => sortOrder * a.label.localeCompare(b.label));
    } else if (sortBy === 'status') {
      const statusOrder = { excluded: 0, included: 1 };
      filtered.sort((a, b) => {
        const aStatus = statusOrder[a.status] ?? 2;
        const bStatus = statusOrder[b.status] ?? 2;
        return sortOrder * (aStatus - bStatus);
      });
    } else if (sortBy === 'caption_count') {
      filtered.sort((a, b) => {
        const aEmpty = !a.active_caption_preview || a.active_caption_preview.trim() === '' ? 0 : 1;
        const bEmpty = !b.active_caption_preview || b.active_caption_preview.trim() === '' ? 0 : 1;
        return sortOrder * (bEmpty - aEmpty);
      });
    }

    if (app.gridFilter.pageSize && app.gridFilter.pageSize !== 'all') {
      const pageSize = parseInt(app.gridFilter.pageSize, 10);
      filtered = filtered.slice(0, pageSize);
    }

    return filtered;
  }

  async function refreshGridAfterMutation(app, statusMessage) {
    const previousSelectedImageId = app.selectedImage?.id ?? null;
    await app.loadImages();
    await app.loadImageSummary();

    const validImageIds = new Set((app.images || []).map((image) => image.id));
    if (previousSelectedImageId && validImageIds.has(previousSelectedImageId)) {
      await app.selectImage(previousSelectedImageId, false);
    } else if (previousSelectedImageId && !validImageIds.has(previousSelectedImageId)) {
      app.selectedImage = null;
    }

    app.statusMessage = statusMessage;
  }

  async function runBulkIncluded(app, included) {
    if (!app.currentProject?.path) {
      return;
    }

    const imageIds = normalizedSelectedIds(app);
    if (imageIds.length === 0) {
      app.errorMessage = 'Select at least one image first.';
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/images/batch/included', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_ids: imageIds,
          included,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to update selected images'));
      }

      await refreshGridAfterMutation(
        app,
        included ? `Included ${payload.updated_count} selected image(s).` : `Excluded ${payload.updated_count} selected image(s).`,
      );
    }, included ? 'bulkIncludeSelected' : 'bulkExcludeSelected');
  }

  async function bulkIncludeSelected(app) {
    await runBulkIncluded(app, true);
  }

  async function bulkExcludeSelected(app) {
    await runBulkIncluded(app, false);
  }

  async function bulkDuplicateSelected(app) {
    if (!app.currentProject?.path) {
      return;
    }

    const imageIds = normalizedSelectedIds(app);
    if (imageIds.length === 0) {
      app.errorMessage = 'Select at least one image first.';
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/images/batch/duplicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_ids: imageIds,
          include_captions: !!app.imageTools.includeCaptions,
          copy_mode: app.imageTools.captionCopyMode,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to duplicate selected images'));
      }

      await refreshGridAfterMutation(app, `Duplicated ${payload.created_count} selected image(s).`);
    }, 'bulkDuplicateSelected');
  }

  async function bulkDeleteSelected(app) {
    if (!app.currentProject?.path) {
      return;
    }

    const imageIds = normalizedSelectedIds(app);
    if (imageIds.length === 0) {
      app.errorMessage = 'Select at least one image first.';
      return;
    }

    if (!window.confirm(`Soft delete ${imageIds.length} selected image(s)? You can restore them later.`)) {
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/images/batch/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_ids: imageIds,
          mode: 'soft',
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to delete selected images'));
      }

      await refreshGridAfterMutation(app, `Soft-deleted ${payload.deleted_count} selected image(s).`);
      clearDuplicateCleanupPreview(app);
    }, 'bulkDeleteSelected');
  }

  async function findDuplicateImages(app) {
    if (!app.currentProject?.path) {
      return;
    }

    await app.withSubmitting(async () => {
      const url = new URL('/api/images/duplicates', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to scan for duplicate images'));
      }

      app.duplicateCleanup.preview = payload;
      if (payload.removable_image_count > 0) {
        app.statusMessage = `Found ${payload.removable_image_count} removable duplicate image(s).`;
        return;
      }
      app.statusMessage = 'No duplicate images found.';
    }, 'findDuplicateImages');
  }

  async function applyDuplicateCleanup(app, mode = 'soft') {
    if (!app.currentProject?.path) {
      return;
    }
    if (!app.duplicateCleanup.preview || app.duplicateCleanup.preview.removable_image_count === 0) {
      app.errorMessage = 'No duplicate cleanup preview is available.';
      return;
    }

    const normalizedMode = mode === 'hard' ? 'hard' : 'soft';
    const confirmText = normalizedMode === 'hard'
      ? `Hard delete ${app.duplicateCleanup.preview.removable_image_count} duplicate image(s) and merge unique captions onto kept image(s)? This cannot be undone.`
      : `Soft delete ${app.duplicateCleanup.preview.removable_image_count} duplicate image(s) and merge unique captions onto kept image(s)?`;
    if (!window.confirm(confirmText)) {
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/images/duplicates/cleanup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          mode: normalizedMode,
          confirm_hard_delete: normalizedMode === 'hard',
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to clean up duplicate images'));
      }

      clearDuplicateCleanupPreview(app);
      clearGridSelection(app);
      await refreshGridAfterMutation(
        app,
        `${normalizedMode === 'hard' ? 'Hard' : 'Soft'} duplicate cleanup removed ${payload.removed_image_count} image(s) and merged ${payload.captions_merged} caption(s).`,
      );
    }, normalizedMode === 'hard' ? 'applyDuplicateCleanupHard' : 'applyDuplicateCleanup');
  }

  features.grid = {
    onImagesLoaded,
    filteredGridCards,
    isGridImageSelected,
    selectedGridCount,
    toggleGridSelectionMode,
    toggleGridImageSelection,
    selectFilteredGridImages,
    clearGridSelection,
    clearDuplicateCleanupPreview,
    bulkIncludeSelected,
    bulkExcludeSelected,
    bulkDuplicateSelected,
    bulkDeleteSelected,
    findDuplicateImages,
    applyDuplicateCleanup,
  };
})(window);