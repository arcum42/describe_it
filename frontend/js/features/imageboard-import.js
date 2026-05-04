(function initDescribeItFeatureImageboardImport(global) {
  const features = global.DescribeItFeatures || (global.DescribeItFeatures = {});

  /**
   * Open the imageboard import modal and load boards if not already loaded.
   */
  async function openImportModal(app) {
    if (!app.currentProject?.path) {
      app.errorMessage = 'Open or create a project first.';
      return;
    }

    // Load boards if not already loaded (reuses credentials service boards)
    if (!app.imageboards?.boards?.length) {
      await features.imageboardSettings?.loadImageboardBoards(app);
    }

    // Reset modal state
    app.imageboardImport.query = '';
    app.imageboardImport.sortBy = 'relevance';
    app.imageboardImport.sortDirection = 'desc';
    app.imageboardImport.importCount = 10;
    app.imageboardImport.includeTags = true;
    app.imageboardImport.includeCreatorTags = false;
    app.imageboardImport.ratingFilter = 'any';
    app.imageboardImport.previewImages = [];
    app.imageboardImport.totalAvailable = 0;
    app.imageboardImport.statusMessage = '';
    app.imageboardImport.errorMessage = '';
    app.imageboardImport.importing = false;
    app.imageboardImport.searching = false;

    // Select first board with credentials, else first board
    const creds = app.imageboards?.credentials || [];
    const boards = app.imageboards?.boards || [];
    const configured = boards.find(b => creds.find(c => c.board_id === b.board_id && c.has_key));
    app.imageboardImport.selectedBoard = configured?.board_id || boards[0]?.board_id || '';

    app.imageboardImport.show = true;
  }

  /**
   * Close the import modal.
   */
  function closeImportModal(app) {
    app.imageboardImport.show = false;
  }

  /**
   * Return the available sort options for the currently selected board.
   */
  function getSortsForBoard(app) {
    const board = (app.imageboards?.boards || []).find(
      b => b.board_id === app.imageboardImport.selectedBoard
    );
    return board?.available_sorts || ['relevance'];
  }

  /**
   * Reset sort to first valid option when the board changes.
   */
  function onBoardChange(app) {
    const sorts = getSortsForBoard(app);
    if (!sorts.includes(app.imageboardImport.sortBy)) {
      app.imageboardImport.sortBy = sorts[0] || 'relevance';
    }
    // Clear previous results
    app.imageboardImport.previewImages = [];
    app.imageboardImport.totalAvailable = 0;
    app.imageboardImport.statusMessage = '';
    app.imageboardImport.errorMessage = '';
  }

  /**
   * Search the selected board and show a preview grid.
   */
  async function searchBoard(app) {
    const { selectedBoard, query, sortBy, sortDirection, ratingFilter } = app.imageboardImport;

    if (!selectedBoard) {
      app.imageboardImport.errorMessage = 'Select a board first.';
      return;
    }
    if (!query.trim()) {
      app.imageboardImport.errorMessage = 'Enter a search query.';
      return;
    }

    app.imageboardImport.searching = true;
    app.imageboardImport.errorMessage = '';
    app.imageboardImport.statusMessage = '';
    app.imageboardImport.previewImages = [];
    app.imageboardImport.totalAvailable = 0;

    try {
      const resp = await fetch('/api/imageboard-import/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          board_id: selectedBoard,
          query: query.trim(),
          sort_by: sortBy,
          sort_direction: sortDirection,
          preview_count: 6,
          rating_filter: ratingFilter,
        }),
      });
      const payload = await resp.json();
      if (!resp.ok) {
        throw new Error(payload.detail ?? 'Search failed');
      }
      app.imageboardImport.previewImages = payload.preview_images || [];
      app.imageboardImport.totalAvailable = payload.total_available || 0;
      if (payload.total_available === 0) {
        app.imageboardImport.statusMessage = 'No results found.';
      } else {
        app.imageboardImport.statusMessage = `Found ${payload.total_available.toLocaleString()} results.`;
      }
    } catch (err) {
      app.imageboardImport.errorMessage = err.message;
    } finally {
      app.imageboardImport.searching = false;
    }
  }

  /**
   * Import images from the selected board into the current project.
   */
  async function doImport(app) {
    const { selectedBoard, query, sortBy, sortDirection, importCount, includeTags, includeCreatorTags, skipDuplicates, ratingFilter } =
      app.imageboardImport;

    if (!app.currentProject?.path) {
      app.imageboardImport.errorMessage = 'No project open.';
      return;
    }
    if (!selectedBoard || !query.trim()) {
      app.imageboardImport.errorMessage = 'Board and query are required.';
      return;
    }

    app.imageboardImport.importing = true;
    app.imageboardImport.errorMessage = '';
    app.imageboardImport.statusMessage = 'Importing…';

    try {
      const resp = await fetch('/api/imageboard-import/do-import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: app.currentProject.path,
          board_id: selectedBoard,
          query: query.trim(),
          sort_by: sortBy,
          sort_direction: sortDirection,
          import_count: importCount,
          include_tags_in_caption: includeTags,
          include_creator_tags: includeCreatorTags,
          skip_duplicates: skipDuplicates,
          rating_filter: ratingFilter,
        }),
      });
      const payload = await resp.json();
      if (!resp.ok) {
        throw new Error(payload.detail ?? 'Import failed');
      }

      const { imported_count, failed_count, duplicate_count } = payload;
      const parts = [`Imported ${imported_count} image(s).`];
      if (duplicate_count > 0) parts.push(`${duplicate_count} duplicate(s) skipped.`);
      if (failed_count > 0) parts.push(`${failed_count} failed — check console.`);
      app.imageboardImport.statusMessage = parts.join(' ');

      // Refresh project images
      if (typeof app.loadImages === 'function') await app.loadImages();
      if (typeof app.loadImageSummary === 'function') await app.loadImageSummary();
    } catch (err) {
      app.imageboardImport.errorMessage = err.message;
      app.imageboardImport.statusMessage = '';
    } finally {
      app.imageboardImport.importing = false;
    }
  }

  features.imageboardImport = {
    openImportModal,
    closeImportModal,
    getSortsForBoard,
    onBoardChange,
    searchBoard,
    doImport,
  };
})(window);
