(function initDescribeItStateBatch(global) {
  const state = global.DescribeItState || (global.DescribeItState = {});

  function createDefaultCaptionBatchState() {
    return {
      query: {
        findText: '',
        replaceText: '',
        mode: 'plain',
        caseSensitive: false,
      },
      scope: {
        captionScope: 'active_only',
        imageScope: 'included_only',
        imageIdsText: '',
      },
      apply: {
        confirm: false,
        createUndoSnapshot: true,
      },
      preview: null,
      operations: [],
      historyLimit: 20,
      lastOperationId: '',
    };
  }

  function createDefaultCaptionTextEditJobState() {
    return {
      id: '',
      status: 'idle',
      total: 0,
      completed: 0,
      affected: 0,
      currentLabel: '',
      lastError: '',
      result: null,
      createdAt: '',
      updatedAt: '',
    };
  }

  function createDefaultCaptionTextEditState() {
    return {
      removeTagsPatternsText: '',
      addCommonCaptionText: '',
      addCommonScope: 'without_caption',
      historyLimit: 10,
      jobs: {
        deleteEmpty: createDefaultCaptionTextEditJobState(),
        removeTags: createDefaultCaptionTextEditJobState(),
        addCommon: createDefaultCaptionTextEditJobState(),
      },
      history: {
        deleteEmpty: [],
        removeTags: [],
        addCommon: [],
      },
    };
  }

  function createDefaultBatchState() {
    return {
      subTab: 'generate',
      target: 'included',
      excludeCaptioned: false,
      usePreset: true,
      presetPromptSuffix: '',
      outputMode: 'new_candidate',
      skipOnFailure: true,
      retryCount: 0,
      jobId: '',
      status: 'idle',
      total: 0,
      completed: 0,
      succeeded: 0,
      failed: 0,
      currentImageId: null,
      currentFilename: '',
      currentGeneratedText: '',
      lastError: '',
      history: [],
      historyStatusFilter: 'all',
      results: [],
    };
  }

  state.batch = {
    createDefaultCaptionBatchState,
    createDefaultCaptionTextEditJobState,
    createDefaultCaptionTextEditState,
    createDefaultBatchState,
  };
})(window);
