(function initDescribeItStateGrid(global) {
  const state = global.DescribeItState || (global.DescribeItState = {});

  function createDefaultGridFilterState() {
    return {
      searchText: '',
      searchMode: 'both', // 'filename', 'caption', 'both'
      inclusionStatus: 'all', // 'all', 'included', 'excluded'
      captionStatus: 'all', // 'all', 'with_captions', 'blank_captions'
      sortBy: 'name', // 'name', 'status', 'caption_count'
      sortOrder: 'asc', // 'asc', 'desc'
      pageSize: 50, // Items per page: 25, 50, 100, all
      currentPage: 1, // Current page (1-based)
    };
  }

  state.grid = {
    createDefaultGridFilterState,
  };
})(window);
