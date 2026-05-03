(function initDescribeItCoreOps(global) {
  const core = global.DescribeItCore || (global.DescribeItCore = {});

  core.isActive = function isActive(app, key) {
    return app.activeOps.has(key);
  };

  core.isAnyActive = function isAnyActive(app) {
    return app.activeOps.size > 0;
  };

  core.withSubmitting = async function withSubmitting(app, fn, operationKey = null) {
    app.isSubmitting = true;
    if (operationKey) {
      app.activeOps.add(operationKey);
    } else {
      app.activeOps.add('_submitting');
    }
    app.errorMessage = '';
    app.statusMessage = '';

    try {
      await fn();
    } catch (error) {
      app.errorMessage = error.message;
    } finally {
      app.isSubmitting = false;
      if (operationKey) {
        app.activeOps.delete(operationKey);
      } else {
        app.activeOps.delete('_submitting');
      }
    }
  };
})(window);