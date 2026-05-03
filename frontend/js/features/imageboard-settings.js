(function initDescribeItFeatureImageboardSettings(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  async function loadImageboardBoards(app) {
    // Load available imageboard boards from the server.
    try {
      const response = await app.fetchWithRetry('/api/settings/imageboard-boards', {}, { attempts: 1 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load imageboard boards');
      }
      app.imageboards = {
        boards: payload.boards || [],
        credentials: [],
      };
    } catch (error) {
      app.imageboards = {
        boards: [],
        credentials: [],
      };
      console.error('Error loading imageboard boards:', error);
    }
  }

  async function loadImageboardCredentials(app) {
    // Load masked imageboard credentials from the server.
    try {
      const response = await app.fetchWithRetry('/api/settings/imageboard-credentials', {}, { attempts: 1 });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load imageboard credentials');
      }
      app.imageboards.credentials = payload.credentials || [];
    } catch (error) {
      app.imageboards.credentials = [];
      console.error('Error loading imageboard credentials:', error);
    }
  }

  async function saveImageboardCredentials(app, boardId, apiKey, username = null) {
    // Save or update credentials for an imageboard.
    try {
      const response = await fetch('/api/settings/imageboard-credentials/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board_id: boardId,
          api_key: apiKey,
          username: username,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to save credentials');
      }
      
      // Reload credentials after saving
      await loadImageboardCredentials(app);
      app.statusMessage = `Saved credentials for ${boardId}`;
      app.errorMessage = '';
      return true;
    } catch (error) {
      app.errorMessage = error.message;
      return false;
    }
  }

  async function deleteImageboardCredentials(app, boardId) {
    // Delete credentials for an imageboard.
    try {
      const response = await fetch(`/api/settings/imageboard-credentials/${boardId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to delete credentials');
      }
      
      // Reload credentials after deletion
      await loadImageboardCredentials(app);
      app.statusMessage = `Deleted credentials for ${boardId}`;
      app.errorMessage = '';
      return true;
    } catch (error) {
      app.errorMessage = error.message;
      return false;
    }
  }

  features.imageboardSettings = {
    loadImageboardBoards,
    loadImageboardCredentials,
    saveImageboardCredentials,
    deleteImageboardCredentials,
  };
})(window);
