(function initDescribeItFeatureRag(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  async function checkRAGStatus(app) {
    try {
      const response = await fetch('/api/llm/rag/status');
      const payload = await response.json();
      if (response.ok) {
        app.rag.enabled = payload.rag_enabled ?? false;
      }
    } catch (error) {
      app.rag.enabled = false;
    }
  }

  async function rebuildEmbeddings(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }

    app.rag.isRebuildingEmbeddings = true;
    app.rag.embeddingsStatus = 'Rebuilding embeddings...';
    app.errorMessage = '';
    app.statusMessage = '';

    try {
      const response = await fetch('/api/llm/rag/rebuild-embeddings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_path: app.currentProject.path }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to rebuild embeddings');
      }
      const result = payload.result;
      app.rag.embeddingsStatus = `Indexed ${result.indexed} captions`;
      app.statusMessage = `Embeddings rebuilt: ${result.indexed} captions indexed`;
    } catch (error) {
      app.errorMessage = error.message;
      app.rag.embeddingsStatus = 'Failed to rebuild embeddings';
    } finally {
      app.rag.isRebuildingEmbeddings = false;
    }
  }

  features.rag = {
    checkRAGStatus,
    rebuildEmbeddings,
  };
})(window);