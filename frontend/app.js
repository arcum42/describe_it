function describeItApp() {
  return {
    healthLabel: 'checking',
    currentProject: null,
    metadataForm: {
      path: '',
      name: '',
      description: '',
      trigger_word: '',
      caption_mode: 'description',
    },
    recentProjects: [],
    createForm: {
      name: '',
      path: 'projects/my_first_project.db',
      description: '',
    },
    openForm: {
      path: '',
    },
    importForm: {
      source_folder: 'practice_dataset/CheerBear',
      replace_existing: false,
    },
    imageSummary: {
      count: 0,
      non_empty_caption_count: 0,
      blank_caption_count: 0,
      previews: [],
    },
    images: [],
    selectedImage: null,
    editorCaptionText: '',
    newCaptionText: '',
    statusMessage: '',
    errorMessage: '',
    isSubmitting: false,
    browser: {
      currentPath: '',
      parentPath: null,
      directories: [],
      dbFiles: [],
      roots: [],
    },
    gridCards: [],
    async init() {
      await Promise.all([this.loadHealth(), this.loadRecentProjects(), this.loadBrowser()]);
    },
    applyProject(project) {
      this.currentProject = project;
      this.metadataForm = {
        path: project.path,
        name: project.name ?? '',
        description: project.description ?? '',
        trigger_word: project.trigger_word ?? '',
        caption_mode: project.caption_mode ?? 'description',
      };
      this.openForm.path = project.path;
      this.selectedImage = null;
      this.editorCaptionText = '';
      this.newCaptionText = '';
      this.loadImageSummary();
      this.loadImages();
    },
    async loadHealth() {
      try {
        const response = await fetch('/api/health');
        const payload = await response.json();
        this.healthLabel = payload.status;
      } catch (error) {
        this.healthLabel = 'offline';
      }
    },
    async loadRecentProjects() {
      try {
        const response = await fetch('/api/projects/recent');
        const payload = await response.json();
        this.recentProjects = payload.projects ?? [];
      } catch (error) {
        this.recentProjects = [];
      }
    },
    async loadBrowser(path = null) {
      try {
        const url = new URL('/api/projects/browser', window.location.origin);
        if (path) {
          url.searchParams.set('path', path);
        }
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to browse paths');
        }
        this.browser = {
          currentPath: payload.current_path,
          parentPath: payload.parent_path,
          directories: payload.directories ?? [],
          dbFiles: payload.db_files ?? [],
          roots: payload.roots ?? [],
        };
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    chooseCreateDirectory(path) {
      const trimmedName = (this.createForm.name || 'my_project').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'my_project';
      this.createForm.path = `${path}/${trimmedName}.db`;
      this.statusMessage = `Create path set to ${this.createForm.path}`;
      this.errorMessage = '';
    },
    chooseOpenFile(path) {
      this.openForm.path = path;
      this.statusMessage = `Open path set to ${path}`;
      this.errorMessage = '';
    },
    async createProject() {
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/projects/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.createForm),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to create project');
        }
        this.applyProject(payload.project);
        this.statusMessage = `Created project ${payload.project.name}`;
        await this.loadRecentProjects();
        await this.loadBrowser(payload.project.path);
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async openProject() {
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/projects/open', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.openForm),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to open project');
        }
        this.applyProject(payload.project);
        this.statusMessage = `Opened project ${payload.project.name}`;
        await this.loadRecentProjects();
        await this.loadBrowser(payload.project.path);
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async saveMetadata() {
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/projects/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.metadataForm),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to save metadata');
        }
        this.applyProject(payload.project);
        this.statusMessage = `Saved metadata for ${payload.project.name}`;
        await this.loadRecentProjects();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async openRecentProject(path) {
      this.openForm.path = path;
      await this.openProject();
    },
    async loadImageSummary() {
      if (!this.currentProject?.path) {
        this.imageSummary = { count: 0, non_empty_caption_count: 0, blank_caption_count: 0, previews: [] };
        return;
      }
      try {
        const url = new URL('/api/images/summary', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load image summary');
        }
        this.imageSummary = payload;
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async loadImages() {
      if (!this.currentProject?.path) {
        this.images = [];
        this.gridCards = [];
        this.selectedImage = null;
        return;
      }
      try {
        const url = new URL('/api/images/list', window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load images');
        }
        this.images = payload.images ?? [];
        this.gridCards = this.images.map((item) => ({
          id: item.id,
          label: item.filename,
          status: item.included ? 'included' : 'excluded',
          active_caption_preview: item.active_caption_preview,
        }));
        if (this.images.length > 0 && !this.selectedImage) {
          await this.selectImage(this.images[0].id);
        }
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    async selectImage(imageId) {
      if (!this.currentProject?.path) {
        return;
      }
      try {
        const url = new URL(`/api/images/${imageId}`, window.location.origin);
        url.searchParams.set('project_path', this.currentProject.path);
        const response = await fetch(url);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to load image details');
        }
        this.selectedImage = payload.image;
        const active = this.selectedImage.captions.find((caption) => caption.is_active);
        this.editorCaptionText = active ? active.text : '';
      } catch (error) {
        this.errorMessage = error.message;
      }
    },
    imageSrc(imageId) {
      if (!this.currentProject?.path) {
        return '';
      }
      const url = new URL(`/api/images/${imageId}/content`, window.location.origin);
      url.searchParams.set('project_path', this.currentProject.path);
      return url.toString();
    },
    async toggleIncluded() {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch(`/api/images/${this.selectedImage.id}/included`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            included: !this.selectedImage.included,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to update include state');
        }
        this.selectedImage.included = payload.included;
        this.statusMessage = payload.included ? 'Image included in export set.' : 'Image excluded from export set.';
        await this.loadImages();
        await this.loadImageSummary();
        await this.selectImage(this.selectedImage.id);
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async saveActiveCaption() {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/captions/update-active', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            text: this.editorCaptionText,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to save caption');
        }
        this.statusMessage = 'Active caption saved.';
        await this.selectImage(this.selectedImage.id);
        await this.loadImages();
        await this.loadImageSummary();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async addCaptionCandidate(makeActive = true) {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      const text = this.newCaptionText.trim();
      if (!text) {
        this.errorMessage = 'Enter caption text before adding a candidate.';
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/captions/create', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            text,
            make_active: makeActive,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to create caption candidate');
        }
        this.newCaptionText = '';
        this.statusMessage = makeActive ? 'Created and activated new caption candidate.' : 'Created new caption candidate.';
        await this.selectImage(this.selectedImage.id);
        await this.loadImages();
        await this.loadImageSummary();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async setActiveCaption(captionId) {
      if (!this.currentProject?.path || !this.selectedImage) {
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/captions/set-active', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            image_id: this.selectedImage.id,
            caption_id: captionId,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Failed to set active caption');
        }
        this.statusMessage = 'Active caption updated.';
        await this.selectImage(this.selectedImage.id);
        await this.loadImages();
        await this.loadImageSummary();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
    async importFolder() {
      if (!this.currentProject?.path) {
        this.errorMessage = 'Open or create a project first.';
        return;
      }
      this.errorMessage = '';
      this.statusMessage = '';
      this.isSubmitting = true;
      try {
        const response = await fetch('/api/projects/import-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_path: this.currentProject.path,
            source_folder: this.importForm.source_folder,
            replace_existing: this.importForm.replace_existing,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail ?? 'Import failed');
        }
        const result = payload.result;
        this.statusMessage = `Imported ${result.imported_images} images (${result.captions_from_files} with captions, ${result.blank_captions} blank).`;
        await this.loadImages();
        await this.loadImageSummary();
      } catch (error) {
        this.errorMessage = error.message;
      } finally {
        this.isSubmitting = false;
      }
    },
  };
}

document.addEventListener('alpine:init', () => {
  window.Alpine.data('describeItApp', describeItApp);
});
