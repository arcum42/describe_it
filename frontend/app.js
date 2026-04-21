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
    gridCards: [
      { id: 1, label: 'sample_001.png', status: 'empty' },
      { id: 2, label: 'sample_002.png', status: 'empty' },
      { id: 3, label: 'sample_003.png', status: 'empty' },
      { id: 4, label: 'sample_004.png', status: 'empty' },
    ],
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
  };
}

document.addEventListener('alpine:init', () => {
  window.Alpine.data('describeItApp', describeItApp);
});
