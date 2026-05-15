window.DescribeItCore = window.DescribeItCore || {};

(function initFragmentLoader() {
  const FRAGMENT_ATTR = 'data-fragment';
  const ALPINE_MARKER_ATTR = 'data-describeit-alpine';
  const FRAGMENT_CACHE_VERSION = '20260515b';

  function fragmentUrl(fragmentName) {
    return `/static/fragments/${fragmentName}.html?v=${FRAGMENT_CACHE_VERSION}`;
  }

  async function injectFragment(placeholder) {
    const fragmentName = placeholder.getAttribute(FRAGMENT_ATTR);
    if (!fragmentName) {
      return;
    }

    if (!/^[a-z0-9_\-/]+$/i.test(fragmentName)) {
      placeholder.innerHTML = '<div class="rounded-xl border border-red-700 bg-red-900/20 px-3 py-2 text-xs text-red-200">Invalid fragment name.</div>';
      placeholder.removeAttribute(FRAGMENT_ATTR);
      return;
    }

    try {
      const response = await fetch(fragmentUrl(fragmentName), { cache: 'no-store' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const html = await response.text();
      placeholder.outerHTML = html;
    } catch (error) {
      console.error(`Failed to load fragment: ${fragmentName}`, error);
      placeholder.innerHTML = `<div class="rounded-xl border border-red-700 bg-red-900/20 px-3 py-2 text-xs text-red-200">Failed to load UI fragment: ${fragmentName}</div>`;
      placeholder.removeAttribute(FRAGMENT_ATTR);
    }
  }

  function collectPlaceholders(root) {
    if (!root || typeof root.querySelectorAll !== 'function') {
      return [];
    }

    const placeholders = Array.from(root.querySelectorAll(`[${FRAGMENT_ATTR}]`));
    const templates = Array.from(root.querySelectorAll('template'));
    for (const template of templates) {
      if (template?.content) {
        placeholders.push(...collectPlaceholders(template.content));
      }
    }
    return placeholders;
  }

  async function loadFragments() {
    const maxPasses = 20;
    for (let pass = 0; pass < maxPasses; pass += 1) {
      const placeholders = collectPlaceholders(document);
      if (!placeholders.length) {
        return;
      }

      for (const placeholder of placeholders) {
        await injectFragment(placeholder);
      }
    }

    console.error('Fragment loader exceeded maximum passes; check for cyclic fragment placeholders.');
  }

  function bootAlpine(currentScript) {
    const alpineSrc = currentScript?.dataset?.alpineSrc;
    if (!alpineSrc) {
      return;
    }
    if (window.Alpine || document.querySelector(`script[${ALPINE_MARKER_ATTR}]`)) {
      return;
    }

    const alpineScript = document.createElement('script');
    alpineScript.defer = true;
    alpineScript.src = alpineSrc;
    alpineScript.setAttribute(ALPINE_MARKER_ATTR, '1');
    document.head.appendChild(alpineScript);
  }

  const currentScript = document.currentScript;
  loadFragments()
    .catch((error) => {
      console.error('Fragment loader failed', error);
    })
    .finally(() => {
      bootAlpine(currentScript);
    });
})();
