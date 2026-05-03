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
      const url = new URL('/api/images/list', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load images');
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
      const url = new URL(`/api/images/${imageId}`, window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load image details');
      }
      app.selectedImage = payload.image;
      app.editingCaptionId = null;
      app.editingCaptionText = '';
      const active = app.selectedImage.captions.find((caption) => caption.is_active);
      app.editorCaptionText = active ? active.text : '';
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

  features.editor = {
    loadImageSummary,
    loadImages,
    selectImage,
    imageSrc,
    toggleIncluded,
    saveActiveCaption,
    addCaptionCandidate,
    setActiveCaption,
    startEditCaption,
    cancelEditCaption,
    saveEditedCaption,
    deleteCaption,
  };
})(window);