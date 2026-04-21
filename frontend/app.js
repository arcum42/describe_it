function describeItApp() {
  return {
    healthLabel: 'checking',
    recentProjects: [],
    gridCards: [
      { id: 1, label: 'sample_001.png', status: 'empty' },
      { id: 2, label: 'sample_002.png', status: 'empty' },
      { id: 3, label: 'sample_003.png', status: 'empty' },
      { id: 4, label: 'sample_004.png', status: 'empty' },
    ],
    async init() {
      await Promise.all([this.loadHealth(), this.loadRecentProjects()]);
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
  };
}

document.addEventListener('alpine:init', () => {
  window.Alpine.data('describeItApp', describeItApp);
});
