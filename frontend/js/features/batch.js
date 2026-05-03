(function initDescribeItFeatureBatch(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  function batchIsActive(app) {
    return ['queued', 'running', 'paused', 'failed'].includes(app.batch.status);
  }

  function batchCanPause(app) {
    return app.batch.status === 'running' || app.batch.status === 'queued';
  }

  function batchCanResume(app) {
    return app.batch.status === 'paused' || app.batch.status === 'failed';
  }

  function batchCanCancel(app) {
    return app.batch.status === 'running' || app.batch.status === 'queued' || app.batch.status === 'paused' || app.batch.status === 'failed';
  }

  function batchProgressPercent(app) {
    if (!app.batch.total) {
      return 0;
    }
    return Math.round((app.batch.completed / app.batch.total) * 100);
  }

  function batchCurrentImageSrc(app) {
    if (!app.batch.currentImageId) {
      return '';
    }
    return app.imageSrc(app.batch.currentImageId);
  }

  function batchResultsExportUrl(app) {
    if (!app.batch.jobId) {
      return '';
    }
    return `/api/llm/batch-jobs/${app.batch.jobId}/results/export`;
  }

  function filteredBatchHistory(app) {
    if (app.batch.historyStatusFilter === 'all') {
      return app.batch.history;
    }
    return app.batch.history.filter((job) => job.status === app.batch.historyStatusFilter);
  }

  function formatBatchTimestamp(app, value) {
    if (!value) {
      return '-';
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return String(value);
    }
    return parsed.toLocaleString();
  }

  function batchResultTextPreview(app, value, maxLength = 120) {
    if (!value) {
      return '-';
    }
    if (value.length <= maxLength) {
      return value;
    }
    return `${value.slice(0, maxLength - 1)}...`;
  }

  function applyBatchJob(app, job) {
    app.batch.jobId = job.id || '';
    app.batch.status = job.status || 'idle';
    app.batch.total = Number(job.total || 0);
    app.batch.completed = Number(job.completed || 0);
    app.batch.succeeded = Number(job.succeeded || 0);
    app.batch.failed = Number(job.failed || 0);
    app.batch.currentImageId = job.current_image_id || null;
    app.batch.currentFilename = job.current_filename || '';
    app.batch.currentGeneratedText = job.current_generated_text || '';
    app.batch.lastError = job.last_error || '';
    if (job.target) {
      app.batch.target = job.target;
    }
    if (typeof job.use_preset === 'boolean') {
      app.batch.usePreset = job.use_preset;
    }
    if (job.output_mode) {
      app.batch.outputMode = job.output_mode;
    }
    if (typeof job.skip_on_failure === 'boolean') {
      app.batch.skipOnFailure = job.skip_on_failure;
    }
    if (typeof job.retry_count === 'number') {
      app.batch.retryCount = job.retry_count;
    }
  }

  function startBatchPolling(app, jobId) {
    if (app.batchPollTimer) {
      clearInterval(app.batchPollTimer);
    }
    app.batchPollTimer = setInterval(() => {
      app.pollBatchJob(jobId);
    }, 1200);
  }

  function stopBatchPollingIfTerminal(app, status) {
    if (['completed', 'cancelled', 'paused', 'failed'].includes(status)) {
      if (app.batchPollTimer) {
        clearInterval(app.batchPollTimer);
        app.batchPollTimer = null;
      }
    }
  }

  async function loadLatestBatchJob(app) {
    if (!app.currentProject?.path) {
      return;
    }
    try {
      const url = new URL('/api/llm/batch-jobs', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load batch jobs');
      }
      const latest = (payload.jobs || [])[0];
      app.batch.history = payload.jobs || [];
      if (!latest) {
        app.batch.results = [];
        return;
      }
      applyBatchJob(app, latest);
      await loadBatchResults(app, latest.id);
      if (batchCanCancel(app)) {
        startBatchPolling(app, latest.id);
      }
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function loadBatchHistory(app) {
    if (!app.currentProject?.path) {
      app.batch.history = [];
      return;
    }
    try {
      const url = new URL('/api/llm/batch-jobs', window.location.origin);
      url.searchParams.set('project_path', app.currentProject.path);
      const response = await fetch(url);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load batch jobs');
      }
      app.batch.history = payload.jobs || [];
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function loadBatchResults(app, jobId = null) {
    const targetJobId = jobId || app.batch.jobId;
    if (!targetJobId) {
      app.batch.results = [];
      return;
    }
    try {
      const response = await fetch(`/api/llm/batch-jobs/${targetJobId}/results?limit=500`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to load batch results');
      }
      app.batch.results = payload.results || [];
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  async function selectBatchJob(app, jobId) {
    app.batch.jobId = jobId;
    await pollBatchJob(app, jobId);
    await loadBatchHistory(app);
    await loadBatchResults(app, jobId);
    if (batchCanCancel(app)) {
      startBatchPolling(app, jobId);
    }
  }

  async function pollBatchJob(app, jobId = null) {
    const targetJobId = jobId || app.batch.jobId;
    if (!targetJobId) {
      return;
    }
    try {
      const response = await fetch(`/api/llm/batch-jobs/${targetJobId}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to poll batch job');
      }
      const job = payload.job;
      applyBatchJob(app, job);
      stopBatchPollingIfTerminal(app, job.status);
      await loadBatchResults(app, job.id);

      if (job.status === 'completed') {
        app.statusMessage = `Batch complete: ${job.succeeded}/${job.total} succeeded, ${job.failed} failed.`;
        await app.loadImages();
        await app.loadImageSummary();
        await loadBatchHistory(app);
      }
      if (job.status === 'cancelled') {
        app.statusMessage = `Batch cancelled: ${job.completed}/${job.total} processed (${job.succeeded} succeeded, ${job.failed} failed).`;
        await app.loadImages();
        await app.loadImageSummary();
        await loadBatchHistory(app);
      }
      if (job.status === 'failed') {
        app.errorMessage = job.last_error || 'Batch failed.';
        app.statusMessage = `Batch failed after ${job.completed}/${job.total} images. You can resume to continue.`;
        await loadBatchHistory(app);
      }
      if (job.status === 'paused') {
        app.statusMessage = `Batch paused at ${job.completed}/${job.total}.`;
        await loadBatchHistory(app);
      }
    } catch (error) {
      app.errorMessage = error.message;
    }
  }

  function cancelBatchGeneration(app) {
    if (!app.batch.jobId) {
      return;
    }
    fetch('/api/llm/batch-jobs/cancel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: app.batch.jobId }),
    })
      .then((response) => response.json())
      .then((payload) => {
        if (payload?.job) {
          applyBatchJob(app, payload.job);
        }
        app.statusMessage = 'Cancelling batch after current image...';
        loadBatchHistory(app);
      })
      .catch((error) => {
        app.errorMessage = error.message;
      });
  }

  function pauseBatchGeneration(app) {
    if (!app.batch.jobId) {
      return;
    }
    fetch('/api/llm/batch-jobs/pause', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: app.batch.jobId }),
    })
      .then((response) => response.json())
      .then((payload) => {
        if (payload?.job) {
          applyBatchJob(app, payload.job);
        }
        app.statusMessage = 'Pause requested. Job will pause after current image.';
        loadBatchHistory(app);
      })
      .catch((error) => {
        app.errorMessage = error.message;
      });
  }

  function resumeBatchGeneration(app) {
    if (!app.batch.jobId) {
      return;
    }
    fetch('/api/llm/batch-jobs/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: app.batch.jobId }),
    })
      .then((response) => response.json())
      .then((payload) => {
        if (payload?.job) {
          applyBatchJob(app, payload.job);
          startBatchPolling(app, app.batch.jobId);
        }
        app.statusMessage = 'Batch resumed.';
        loadBatchHistory(app);
      })
      .catch((error) => {
        app.errorMessage = error.message;
      });
  }

  async function startBatchGeneration(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open a project first.';
      return;
    }

    app.errorMessage = '';
    app.statusMessage = '';
    if (app.batch.usePreset && !app.llm.selectedPresetId) {
      app.errorMessage = 'Choose a preset before starting batch generation.';
      return;
    }
    if (!app.batch.usePreset && (!app.llm.backend || !app.llm.model)) {
      app.errorMessage = 'Select backend and model before starting manual batch generation.';
      return;
    }

    app.batch.lastError = '';
    app.batch.currentGeneratedText = '';
    app.batch.currentFilename = '';
    app.batch.currentImageId = null;
    await app.withSubmitting(async () => {
      const response = await fetch('/api/llm/batch-jobs/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          target: app.batch.target,
          use_preset: app.batch.usePreset,
          preset_id: app.batch.usePreset && app.llm.selectedPresetId ? Number(app.llm.selectedPresetId) : null,
          backend: app.batch.usePreset ? '' : app.llm.backend,
          model: app.batch.usePreset ? '' : app.llm.model,
          extra_instructions: app.batch.usePreset ? '' : app.llm.extraInstructions,
          timeout_seconds: app.settings.llmTimeoutSeconds,
          make_active: app.llm.makeActive,
          output_mode: app.batch.outputMode,
          skip_on_failure: app.batch.skipOnFailure,
          retry_count: Number(app.batch.retryCount || 0),
          reasoning_mode: app.batch.usePreset ? 'off' : app.llm.tools.reasoningMode,
          reasoning_visibility: app.batch.usePreset ? 'hidden' : app.llm.tools.reasoningVisibility,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? 'Failed to start batch job');
      }
      const job = payload.job;
      applyBatchJob(app, job);
      startBatchPolling(app, job.id);
      await loadBatchHistory(app);
      await loadBatchResults(app, job.id);
      app.statusMessage = 'Batch job started.';
    });
  }

  features.batch = {
    batchIsActive,
    batchCanPause,
    batchCanResume,
    batchCanCancel,
    batchProgressPercent,
    batchCurrentImageSrc,
    batchResultsExportUrl,
    filteredBatchHistory,
    formatBatchTimestamp,
    batchResultTextPreview,
    applyBatchJob,
    startBatchPolling,
    stopBatchPollingIfTerminal,
    loadLatestBatchJob,
    loadBatchHistory,
    loadBatchResults,
    selectBatchJob,
    pollBatchJob,
    cancelBatchGeneration,
    pauseBatchGeneration,
    resumeBatchGeneration,
    startBatchGeneration,
  };
})(window);