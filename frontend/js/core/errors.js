(function initDescribeItCoreErrors(global) {
  const core = global.DescribeItCore || (global.DescribeItCore = {});

  core.formatApiError = function formatApiError(payload, fallbackMessage = 'Request failed') {
    const detail = payload?.detail;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0];
      if (typeof first === 'string' && first.trim()) {
        return first;
      }
      if (first && typeof first === 'object') {
        const fieldPath = Array.isArray(first.loc) ? first.loc.join('.') : 'field';
        const message = typeof first.msg === 'string' ? first.msg : 'Invalid value';
        return `${fieldPath}: ${message}`;
      }
    }
    if (detail && typeof detail === 'object') {
      return JSON.stringify(detail);
    }
    return fallbackMessage;
  };
})(window);