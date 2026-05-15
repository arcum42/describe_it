(function initDescribeItStateNotes(global) {
  const state = global.DescribeItState || (global.DescribeItState = {});

  function createDefaultNotesState() {
    return {
      scope: 'project',
      includeArchived: false,
      projectItems: [],
      globalItems: [],
      selectedNoteId: null,
      editor: {
        id: null,
        title: '',
        content: '',
        format: 'markdown',
        tags: '',
        is_archived: false,
      },
      llm: {
        prompt: '',
        useSelectedImage: false,
        backend: '',
        model: '',
        outputFormat: 'markdown',
        title: '',
        tags: '',
        webSearch: false,
        webFetch: false,
        contextUrl: '',
        contextFile: '',
        includeProjectNotes: false,
        includeGlobalNotes: false,
        reasoningMode: 'off',
        reasoningVisibility: 'hidden',
      },
    };
  }

  state.notes = {
    createDefaultNotesState,
  };
})(window);
