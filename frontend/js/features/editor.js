(function initDescribeItFeatureEditor(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  async function loadImageSummary(app) {
    if (!app.currentProject?.path) {
      app.imageSummary = { count: 0, non_empty_caption_count: 0, blank_caption_count: 0, previews: [] };
      return;
    }
    try {
      const url = new URL('/api/images/summary', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load image summary');
      }
      app.imageSummary = payload;
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function loadImages(app) {
    if (!app.currentProject?.path) {
      app.images = [];
      app.gridCards = [];
      app.selectedImage = null;
      return;
    }
    try {
      const requestSeq = (Number(app.loadImagesRequestSeq) || 0) + 1;
      app.loadImagesRequestSeq = requestSeq;
      const url = new URL('/api/images/list', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load images');
      }
      if (app.loadImagesRequestSeq !== requestSeq) {
        return;
      }
      app.images = payload.images ?? [];
      app.gridCards = app.images.map((item) => ({
        id: item.id,
        label: item.filename,
        status: item.included ? 'included' : 'excluded',
        active_caption_preview: item.active_caption_preview,
      }));
      if (app.images.length > 0 && !app.selectedImage) {
        await selectImage(app, app.images[0].id, false);
      }
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function selectImage(app, imageId, switchToEditor = true) {
    if (!app.currentProject?.path) {
      return;
    }
    try {
      const previousImageId = app.selectedImage?.id ?? null;
      const requestSeq = (Number(app.selectImageRequestSeq) || 0) + 1;
      app.selectImageRequestSeq = requestSeq;
      const url = new URL(`/api/images/${imageId}`, window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load image details');
      }
      if (app.selectImageRequestSeq !== requestSeq) {
        return;
      }
      app.selectedImage = payload.image;
      if (previousImageId !== app.selectedImage.id && typeof app.resetEditorZoomToDefault === 'function') {
        app.resetEditorZoomToDefault();
      }
      app.editingCaptionId = null;
      app.editingCaptionText = '';
      const active = app.selectedImage.captions.find((caption) => caption.is_active);
      app.editorCaptionText = active ? active.text : '';
      await refreshActiveTags(app, { silent: true });
      await loadTagStatistics(app, { silent: true });
      await loadCaptionBatchOperations(app, { silent: true });
      if (switchToEditor) {
        app.mainView = 'editor';
      }
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  function imageSrc(app, imageId) {
    if (!app.currentProject?.path) {
      return '';
    }
    const url = new URL(`/api/images/${imageId}/content`, window.location.origin);
    url.searchParams.set('project_path', app.currentProject.path);
    return url.toString();
  }

  async function toggleIncluded(app) {
    if (!app.currentProject?.path || !app.selectedImage) {
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch(`/api/images/${app.selectedImage.id}/included`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          included: !app.selectedImage.included,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to update include state');
      }
      app.selectedImage.included = payload.included;
      app.statusMessage = payload.included ? 'Image included in export set.' : 'Image excluded from export set.';
      await loadImages(app);
      await loadImageSummary(app);
      await selectImage(app, app.selectedImage.id, false);
    }, 'toggleIncluded');
  }

  async function saveActiveCaption(app) {
    if (!app.currentProject?.path || !app.selectedImage) {
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/update-active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          text: app.editorCaptionText,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to save caption');
      }
      app.statusMessage = 'Active caption saved.';
      await selectImage(app, app.selectedImage.id, false);
      await loadImages(app);
      await loadImageSummary(app);
    }, 'saveCaption');
  }

  async function addCaptionCandidate(app, makeActive = true) {
    if (!app.currentProject?.path || !app.selectedImage) {
      return;
    }
    const text = app.newCaptionText.trim();
    if (!text) {
      app.errorMessage = 'Enter caption text before adding a candidate.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          text,
          make_active: makeActive,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to create caption candidate');
      }
      app.newCaptionText = '';
      app.statusMessage = makeActive ? 'Created and activated new caption candidate.' : 'Created new caption candidate.';
      await selectImage(app, app.selectedImage.id, false);
      await loadImages(app);
      await loadImageSummary(app);
    });
  }

  async function setActiveCaption(app, captionId) {
    if (!app.currentProject?.path || !app.selectedImage) {
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/set-active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          caption_id: captionId,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to set active caption');
      }
      app.statusMessage = 'Active caption updated.';
      await selectImage(app, app.selectedImage.id, false);
      await loadImages(app);
      await loadImageSummary(app);
    });
  }

  function startEditCaption(app, caption) {
    if (!caption) {
      return;
    }
    app.editingCaptionId = caption.id;
    app.editingCaptionText = caption.text || '';
    app.errorMessage = '';
    app.statusMessage = '';
  }

  function cancelEditCaption(app) {
    app.editingCaptionId = null;
    app.editingCaptionText = '';
  }

  async function saveEditedCaption(app, caption) {
    if (!app.currentProject?.path || !app.selectedImage || !caption) {
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          caption_id: caption.id,
          text: app.editingCaptionText,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to update caption');
      }
      cancelEditCaption(app);
      app.statusMessage = 'Caption updated.';
      await selectImage(app, app.selectedImage.id, false);
      await loadImages(app);
      await loadImageSummary(app);
    });
  }

  async function deleteCaption(app, caption) {
    if (!app.currentProject?.path || !app.selectedImage || !caption) {
      return;
    }
    const confirmDelete = window.confirm('Delete this caption? This cannot be undone.');
    if (!confirmDelete) {
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_id: app.selectedImage.id,
          caption_id: caption.id,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to delete caption');
      }
      app.statusMessage = 'Caption deleted.';
      await selectImage(app, app.selectedImage.id, false);
      await loadImages(app);
      await loadImageSummary(app);
    });
  }

  function getActiveCaption(app) {
    if (!app.selectedImage || !Array.isArray(app.selectedImage.captions)) {
      return null;
    }
    return app.selectedImage.captions.find((caption) => caption.is_active) || null;
  }

  function parseTagInput(rawText) {
    return String(rawText || '')
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);
  }

  async function refreshActiveTags(app, { silent = false } = {}) {
    if (!app.currentProject?.path || app.currentProject?.caption_mode !== 'tags') {
      app.tagEditor.activeCaptionId = null;
      app.tagEditor.tags = [];
      app.tagEditor.editingTagIndex = null;
      app.tagEditor.editingTagText = '';
      app.tagEditor.dragTagIndex = null;
      return;
    }

    const activeCaption = getActiveCaption(app);
    if (!activeCaption) {
      app.tagEditor.activeCaptionId = null;
      app.tagEditor.tags = [];
      return;
    }

    try {
      const url = new URL(`/api/captions/tags/${activeCaption.id}`, window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to load active tags'));
      }

      app.tagEditor.activeCaptionId = activeCaption.id;
      app.tagEditor.tags = Array.isArray(payload.tags) ? payload.tags : [];
      app.tagEditor.editingTagIndex = null;
      app.tagEditor.editingTagText = '';
      app.tagEditor.dragTagIndex = null;
    } catch (error) {
      if (!silent) {
        app.errorMessage = error.message;
      }
    }
  }

  async function updateActiveCaptionTags(app, tags, successMessage) {
    if (!app.currentProject?.path || app.currentProject?.caption_mode !== 'tags') {
      return;
    }
    const activeCaption = getActiveCaption(app);
    if (!activeCaption) {
      app.errorMessage = 'No active caption selected for tag editing.';
      return;
    }

    const normalizedTags = tags
      .map((tag) => String(tag || '').trim())
      .filter((tag) => tag.length > 0);

    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/tags/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          caption_id: activeCaption.id,
          tags: normalizedTags,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to update tags'));
      }

      app.editorCaptionText = payload.text || '';
      await selectImage(app, app.selectedImage.id, false);
      await loadImages(app);
      await loadImageSummary(app);
      await loadTagStatistics(app, { silent: true });
      app.statusMessage = successMessage;
    }, 'updateActiveTags');
  }

  async function addTagsToActiveCaption(app) {
    const tagsToAdd = parseTagInput(app.tagEditor.newTagText);
    if (tagsToAdd.length === 0) {
      app.errorMessage = 'Enter at least one tag to add.';
      return;
    }

    const existingTags = app.tagEditor.tags.map((item) => item.tag);
    const mergedTags = [...existingTags];
    const existingLower = new Set(existingTags.map((tag) => tag.toLowerCase()));
    for (const tag of tagsToAdd) {
      if (!existingLower.has(tag.toLowerCase())) {
        mergedTags.push(tag);
      }
    }

    await updateActiveCaptionTags(app, mergedTags, 'Tags updated for active caption.');
    app.tagEditor.newTagText = '';
  }

  async function removeTagFromActiveCaption(app, index) {
    if (!Number.isInteger(index) || index < 0 || index >= app.tagEditor.tags.length) {
      return;
    }
    const nextTags = app.tagEditor.tags
      .map((item) => item.tag)
      .filter((_, i) => i !== index);
    await updateActiveCaptionTags(app, nextTags, 'Removed tag from active caption.');
  }

  function startEditTag(app, index) {
    if (!Number.isInteger(index) || index < 0 || index >= app.tagEditor.tags.length) {
      return;
    }
    app.tagEditor.editingTagIndex = index;
    app.tagEditor.editingTagText = app.tagEditor.tags[index].tag;
    app.errorMessage = '';
    app.statusMessage = '';
  }

  function cancelEditTag(app) {
    app.tagEditor.editingTagIndex = null;
    app.tagEditor.editingTagText = '';
  }

  async function saveEditedTag(app, index) {
    if (!Number.isInteger(index) || index < 0 || index >= app.tagEditor.tags.length) {
      return;
    }
    const newTag = String(app.tagEditor.editingTagText || '').trim();
    if (!newTag) {
      app.errorMessage = 'Tag cannot be empty.';
      return;
    }

    const nextTags = app.tagEditor.tags.map((item) => item.tag);
    nextTags[index] = newTag;
    const deduped = [];
    const seen = new Set();
    for (const tag of nextTags) {
      const key = tag.toLowerCase();
      if (!seen.has(key)) {
        deduped.push(tag);
        seen.add(key);
      }
    }

    await updateActiveCaptionTags(app, deduped, 'Tag edited.');
    cancelEditTag(app);
  }

  function startTagDrag(app, index) {
    app.tagEditor.dragTagIndex = index;
  }

  async function moveTagRelative(app, index, delta) {
    if (!Number.isInteger(index) || !Number.isInteger(delta) || delta === 0) {
      return;
    }
    const targetIndex = index + delta;
    if (index < 0 || targetIndex < 0) {
      return;
    }
    if (index >= app.tagEditor.tags.length || targetIndex >= app.tagEditor.tags.length) {
      return;
    }

    const reordered = app.tagEditor.tags.map((item) => item.tag);
    const [moved] = reordered.splice(index, 1);
    reordered.splice(targetIndex, 0, moved);
    await updateActiveCaptionTags(app, reordered, 'Tag order updated.');
  }

  async function moveTagLeft(app, index) {
    await moveTagRelative(app, index, -1);
  }

  async function moveTagRight(app, index) {
    await moveTagRelative(app, index, 1);
  }

  async function dropTagAt(app, targetIndex) {
    const sourceIndex = app.tagEditor.dragTagIndex;
    app.tagEditor.dragTagIndex = null;

    if (!Number.isInteger(sourceIndex) || !Number.isInteger(targetIndex)) {
      return;
    }
    if (sourceIndex < 0 || targetIndex < 0) {
      return;
    }
    if (sourceIndex >= app.tagEditor.tags.length || targetIndex >= app.tagEditor.tags.length) {
      return;
    }
    if (sourceIndex === targetIndex) {
      return;
    }

    const reordered = app.tagEditor.tags.map((item) => item.tag);
    const [moved] = reordered.splice(sourceIndex, 1);
    reordered.splice(targetIndex, 0, moved);
    await updateActiveCaptionTags(app, reordered, 'Tag order updated.');
  }

  async function loadTagStatistics(app, { silent = false } = {}) {
    if (!app.currentProject?.path || app.currentProject?.caption_mode !== 'tags') {
      app.tagEditor.stats = {
        total_tags: 0,
        total_occurrences: 0,
        top_tags: [],
      };
      return;
    }

    app.tagEditor.statsLoading = true;
    try {
      const url = new URL('/api/captions/tags/statistics', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to load tag statistics'));
      }

      app.tagEditor.stats = {
        total_tags: Number(payload.total_tags || 0),
        total_occurrences: Number(payload.total_occurrences || 0),
        top_tags: Array.isArray(payload.top_tags) ? payload.top_tags : [],
      };
    } catch (error) {
      if (!silent) {
        app.errorMessage = error.message;
      }
    } finally {
      app.tagEditor.statsLoading = false;
    }
  }

  function resolveBatchImageIds(app) {
    const scope = app.tagEditor.batch.scope;
    if (scope === 'all') {
      return app.images.map((image) => image.id);
    }
    if (scope === 'selected') {
      return app.selectedImage?.id ? [app.selectedImage.id] : [];
    }
    return app.images.filter((image) => image.included).map((image) => image.id);
  }

  async function runTagBatchOperation(app, operation, payload = {}, successMessage = 'Tag batch operation complete.') {
    if (!app.currentProject?.path || app.currentProject?.caption_mode !== 'tags') {
      return;
    }

    const imageIds = resolveBatchImageIds(app);
    if (imageIds.length === 0) {
      app.errorMessage = 'No images match the selected batch scope.';
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/tags/batch-operation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          image_ids: imageIds,
          operation,
          ...payload,
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(result, 'Failed to run batch tag operation'));
      }

      await loadImages(app);
      await loadImageSummary(app);
      if (app.selectedImage?.id) {
        await selectImage(app, app.selectedImage.id, false);
      }
      await loadTagStatistics(app, { silent: true });
      app.statusMessage = `${successMessage} Updated ${result.affected_captions || 0} captions.`;
    }, `tagBatch_${operation}`);
  }

  async function runBatchAddTags(app) {
    const tags = parseTagInput(app.tagEditor.batch.addInput);
    if (tags.length === 0) {
      app.errorMessage = 'Enter tags to add for batch operation.';
      return;
    }
    await runTagBatchOperation(app, 'add', { tags }, 'Batch add complete.');
    app.tagEditor.batch.addInput = '';
  }

  async function runBatchRemoveTags(app) {
    const tags = parseTagInput(app.tagEditor.batch.removeInput);
    if (tags.length === 0) {
      app.errorMessage = 'Enter tags to remove for batch operation.';
      return;
    }
    await runTagBatchOperation(app, 'remove', { tags }, 'Batch remove complete.');
    app.tagEditor.batch.removeInput = '';
  }

  async function runBatchClearTags(app) {
    if (!app.tagEditor.batch.clearConfirm) {
      app.errorMessage = 'Confirm clear-all before running batch clear.';
      return;
    }
    await runTagBatchOperation(app, 'clear', {}, 'Batch clear complete.');
    app.tagEditor.batch.clearConfirm = false;
  }

  function parseIntegerField(value, fieldName, { min = null, max = null } = {}) {
    const number = Number(value);
    if (!Number.isInteger(number)) {
      throw new Error(`${fieldName} must be an integer.`);
    }
    if (min !== null && number < min) {
      throw new Error(`${fieldName} must be >= ${min}.`);
    }
    if (max !== null && number > max) {
      throw new Error(`${fieldName} must be <= ${max}.`);
    }
    return number;
  }

  async function runDerivedImageOperation(app, endpoint, body, operationKey, successMessage) {
    if (!app.currentProject?.path || !app.selectedImage) {
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          ...body,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Image tool operation failed'));
      }

      const newImageId = payload?.new_image?.id;
      await loadImages(app);
      await loadImageSummary(app);
      if (newImageId) {
        await selectImage(app, newImageId, false);
      }
      app.statusMessage = successMessage;
    }, operationKey);
  }

  async function duplicateImage(app) {
    await runDerivedImageOperation(
      app,
      `/api/images/${app.selectedImage.id}/duplicate`,
      {
        include_captions: !!app.imageTools.includeCaptions,
        copy_mode: app.imageTools.captionCopyMode,
      },
      'duplicateImage',
      'Image duplicated.',
    );
  }

  async function deleteImage(app) {
    if (!app.currentProject?.path || !app.selectedImage) {
      return;
    }

    const mode = app.imageTools.deleteMode === 'hard' ? 'hard' : 'soft';
    const prompt = mode === 'hard'
      ? 'Hard delete this image and all its captions? This cannot be undone.'
      : 'Soft delete this image? You can restore it later.';
    if (!window.confirm(prompt)) {
      return;
    }

    await app.withSubmitting(async () => {
      const deletedImageId = app.selectedImage.id;
      const response = await fetch(`/api/images/${deletedImageId}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          mode,
          confirm_hard_delete: mode === 'hard',
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to delete image'));
      }

      app.selectedImage = null;
      await loadImages(app);
      await loadImageSummary(app);
      if (app.images.length > 0) {
        await selectImage(app, app.images[0].id, false);
      }
      app.statusMessage = mode === 'hard' ? 'Image permanently deleted.' : 'Image soft-deleted.';
    }, 'deleteImage');
  }

  async function cropImage(app) {
    const x = parseIntegerField(app.imageTools.crop.x, 'Crop X', { min: 0 });
    const y = parseIntegerField(app.imageTools.crop.y, 'Crop Y', { min: 0 });
    const width = parseIntegerField(app.imageTools.crop.width, 'Crop width', { min: 1 });
    const height = parseIntegerField(app.imageTools.crop.height, 'Crop height', { min: 1 });
    await runDerivedImageOperation(
      app,
      `/api/images/${app.selectedImage.id}/crop`,
      {
        rect: { x, y, width, height },
        output_name: app.imageTools.crop.outputName || null,
        include_captions: !!app.imageTools.includeCaptions,
        caption_copy_mode: app.imageTools.captionCopyMode,
      },
      'cropImage',
      'Cropped image created.',
    );
  }

  async function scaleImage(app) {
    const mode = app.imageTools.scale.mode === 'dimensions' ? 'dimensions' : 'percent';
    const requestBody = {
      mode,
      output_name: app.imageTools.scale.outputName || null,
      include_captions: !!app.imageTools.includeCaptions,
      caption_copy_mode: app.imageTools.captionCopyMode,
      keep_aspect_ratio: !!app.imageTools.scale.keepAspectRatio,
      upscale: !!app.imageTools.scale.upscale,
    };

    if (mode === 'percent') {
      requestBody.percent = Number(app.imageTools.scale.percent);
      if (!Number.isFinite(requestBody.percent) || requestBody.percent <= 0) {
        throw new Error('Scale percent must be > 0.');
      }
    } else {
      requestBody.width = parseIntegerField(app.imageTools.scale.width, 'Scale width', { min: 1 });
      requestBody.height = parseIntegerField(app.imageTools.scale.height, 'Scale height', { min: 1 });
    }

    await runDerivedImageOperation(
      app,
      `/api/images/${app.selectedImage.id}/scale`,
      requestBody,
      'scaleImage',
      'Scaled image created.',
    );
  }

  async function flipImage(app) {
    await runDerivedImageOperation(
      app,
      `/api/images/${app.selectedImage.id}/flip`,
      {
        mode: app.imageTools.flipMode,
        include_captions: !!app.imageTools.includeCaptions,
        caption_copy_mode: app.imageTools.captionCopyMode,
      },
      'flipImage',
      'Flipped image created.',
    );
  }

  async function rotateImage(app) {
    const angle = parseIntegerField(app.imageTools.rotateAngle, 'Rotate angle');
    if (![90, 180, 270].includes(angle)) {
      throw new Error('Rotate angle must be 90, 180, or 270.');
    }
    await runDerivedImageOperation(
      app,
      `/api/images/${app.selectedImage.id}/rotate`,
      {
        angle,
        include_captions: !!app.imageTools.includeCaptions,
        caption_copy_mode: app.imageTools.captionCopyMode,
      },
      'rotateImage',
      'Rotated image created.',
    );
  }

  async function extractRegionImage(app) {
    const x = parseIntegerField(app.imageTools.extract.x, 'Extract X', { min: 0 });
    const y = parseIntegerField(app.imageTools.extract.y, 'Extract Y', { min: 0 });
    const width = parseIntegerField(app.imageTools.extract.width, 'Extract width', { min: 1 });
    const height = parseIntegerField(app.imageTools.extract.height, 'Extract height', { min: 1 });
    await runDerivedImageOperation(
      app,
      `/api/images/${app.selectedImage.id}/extract-region`,
      {
        rect: { x, y, width, height },
        output_name: app.imageTools.extract.outputName || null,
        include_captions: !!app.imageTools.includeCaptions,
        caption_copy_mode: app.imageTools.captionCopyMode,
        add_source_reference_note: !!app.imageTools.extract.addSourceReferenceNote,
      },
      'extractRegionImage',
      'Extracted image created.',
    );
  }

  function parseCaptionBatchImageIds(imageIdsText) {
    const raw = String(imageIdsText || '').trim();
    if (!raw) {
      return [];
    }
    const values = raw
      .split(/[\s,]+/)
      .map((item) => Number(item.trim()))
      .filter((value) => Number.isInteger(value) && value > 0);
    return Array.from(new Set(values));
  }

  function buildCaptionBatchScope(app) {
    const imageScope = app.captionBatch.scope.imageScope;
    const scope = {
      caption_scope: app.captionBatch.scope.captionScope,
      image_scope: imageScope,
    };

    if (imageScope === 'selected_ids') {
      const imageIds = parseCaptionBatchImageIds(app.captionBatch.scope.imageIdsText);
      if (imageIds.length === 0 && app.selectedImage?.id) {
        scope.image_ids = [app.selectedImage.id];
      } else {
        scope.image_ids = imageIds;
      }
    }
    return scope;
  }

  async function loadCaptionBatchOperations(app, { silent = false } = {}) {
    if (!app.currentProject?.path) {
      app.captionBatch.operations = [];
      return;
    }
    try {
      const url = new URL('/api/captions/batch/operations', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      url.searchParams.set('limit', String(app.captionBatch.historyLimit || 20));
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to load caption batch operations'));
      }
      app.captionBatch.operations = Array.isArray(payload.operations) ? payload.operations : [];
    } catch (error) {
      if (!silent) {
        app.errorMessage = error.message;
      }
    }
  }

  async function previewCaptionBatchReplace(app) {
    if (!app.currentProject?.path) {
      return;
    }
    const findText = String(app.captionBatch.query.findText || '').trim();
    if (!findText) {
      app.errorMessage = 'Enter text to find before running a preview.';
      return;
    }
    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/batch/preview-replace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          query: {
            find_text: findText,
            replace_text: String(app.captionBatch.query.replaceText || ''),
            mode: app.captionBatch.query.mode,
            case_sensitive: !!app.captionBatch.query.caseSensitive,
          },
          scope: buildCaptionBatchScope(app),
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to preview caption batch replace'));
      }

      app.captionBatch.preview = payload;
      app.captionBatch.apply.confirm = false;
      app.statusMessage = payload.impacted_captions_count > 0
        ? `Preview ready: ${payload.impacted_captions_count} captions across ${payload.impacted_images_count} images.`
        : 'Preview ready: no matching captions.';
    }, 'previewCaptionBatchReplace');
  }

  async function applyCaptionBatchReplace(app) {
    if (!app.currentProject?.path) {
      return;
    }
    const previewId = app.captionBatch.preview?.preview_id;
    if (!previewId) {
      app.errorMessage = 'Run a preview before applying batch replace.';
      return;
    }
    if (!app.captionBatch.apply.confirm) {
      app.errorMessage = 'Confirm apply before running batch replace.';
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/batch/apply-replace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          preview_id: previewId,
          confirm: true,
          create_undo_snapshot: !!app.captionBatch.apply.createUndoSnapshot,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to apply caption batch replace'));
      }

      app.captionBatch.lastOperationId = payload.operation_id;
      app.captionBatch.preview = null;
      app.captionBatch.apply.confirm = false;
      await loadImages(app);
      await loadImageSummary(app);
      if (app.selectedImage?.id) {
        await selectImage(app, app.selectedImage.id, false);
      }
      await loadCaptionBatchOperations(app, { silent: true });
      app.statusMessage = `Applied batch replace: ${payload.updated_captions_count} captions updated.`;
    }, 'applyCaptionBatchReplace');
  }

  async function undoCaptionBatchReplace(app, operationId = null) {
    if (!app.currentProject?.path) {
      return;
    }

    await app.withSubmitting(async () => {
      const response = await fetch('/api/captions/batch/undo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          operation_id: operationId || null,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(app.formatApiError(payload, 'Failed to undo caption batch replace'));
      }

      app.captionBatch.lastOperationId = payload.undone_operation_id;
      await loadImages(app);
      await loadImageSummary(app);
      if (app.selectedImage?.id) {
        await selectImage(app, app.selectedImage.id, false);
      }
      await loadCaptionBatchOperations(app, { silent: true });
      app.statusMessage = `Undo complete: restored ${payload.restored_captions_count} captions.`;
    }, 'undoCaptionBatchReplace');
  }

  function clearCaptionBatchPreview(app) {
    app.captionBatch.preview = null;
    app.captionBatch.apply.confirm = false;
  }

  features.editor = {
    loadImageSummary,
    loadImages,
    selectImage,
    imageSrc,
    toggleIncluded,
    saveActiveCaption,
    refreshActiveTags,
    addTagsToActiveCaption,
    removeTagFromActiveCaption,
    startEditTag,
    cancelEditTag,
    saveEditedTag,
    startTagDrag,
    moveTagLeft,
    moveTagRight,
    dropTagAt,
    loadTagStatistics,
    runBatchAddTags,
    runBatchRemoveTags,
    runBatchClearTags,
    addCaptionCandidate,
    setActiveCaption,
    startEditCaption,
    cancelEditCaption,
    saveEditedCaption,
    deleteCaption,
    duplicateImage,
    deleteImage,
    cropImage,
    scaleImage,
    flipImage,
    rotateImage,
    extractRegionImage,
    loadCaptionBatchOperations,
    previewCaptionBatchReplace,
    applyCaptionBatchReplace,
    undoCaptionBatchReplace,
    clearCaptionBatchPreview,
  };
})(window);