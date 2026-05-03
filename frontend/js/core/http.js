(function initDescribeItCoreHttp(global) {
  const core = global.DescribeItCore || (global.DescribeItCore = {});

  core.sleep = function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  };

  core.fetchWithRetry = async function fetchWithRetry(resource, options = {}, retryOptions = {}) {
    const attempts = Math.max(1, Number(retryOptions.attempts ?? 1));
    const delayMs = Math.max(0, Number(retryOptions.delayMs ?? 150));
    let lastError = null;

    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        return await fetch(resource, options);
      } catch (error) {
        lastError = error;
        if (attempt >= attempts) {
          throw error;
        }
        await core.sleep(delayMs * attempt);
      }
    }

    throw lastError || new Error('Request failed');
  };
})(window);