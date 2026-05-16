/**
 * Keyboard shortcuts for image tools and editor actions
 * Loaded conditionally and managed via window.DescribeItFeatures.shortcuts
 */

window.DescribeItFeatures = window.DescribeItFeatures || {};

window.DescribeItFeatures.shortcuts = {
  // Shortcut definitions
  bindings: {
    // Image tools shortcuts (when an image is selected)
    'D': { action: 'duplicateImage', description: 'Duplicate selected image', context: 'editor' },
    'Delete': { action: 'deleteImage', description: 'Delete selected image', context: 'editor' },
    'Shift+D': { action: 'deleteImage', description: 'Delete selected image (alt)', context: 'editor' },
    'ArrowLeft': { action: 'goToPreviousImage', description: 'Previous image', context: 'editor' },
    'ArrowRight': { action: 'goToNextImage', description: 'Next image', context: 'editor' },
    'F': { action: 'flipImage', description: 'Apply flip to selected image', context: 'editor' },
    'R': { action: 'rotateImage', description: 'Apply rotation to selected image', context: 'editor' },
    'C': { action: 'cropImage', description: 'Apply crop to selected image', context: 'editor' },
    'S': { action: 'scaleImage', description: 'Apply scale to selected image', context: 'editor' },
    'E': { action: 'extractRegionImage', description: 'Extract region from selected image', context: 'editor' },
    '?': { action: 'toggleShortcutsHelp', description: 'Toggle keyboard shortcuts help', context: 'global' },
    'Escape': { action: 'closeShortcutsHelpIfOpen', description: 'Close shortcuts help', context: 'global' },
  },

  // State
  helpDialogOpen: false,

  /**
   * Initialize keyboard event listener
   * @param {Object} app - Alpine.js app reference
   */
  init(app) {
    if (this._initialized) return;
    this._initialized = true;
    this.app = app;

    document.addEventListener('keydown', (e) => this._handleKeyDown(e));
  },

  /**
   * Handle keydown events
   * @private
   */
  _handleKeyDown(e) {
    const target = e.target;
    const isTypingTarget = !!(target && (
      target.closest('input, textarea, select')
      || target.isContentEditable
      || target.closest('[contenteditable="true"]')
    ));
    const inEditorContext = this.app?.mainView === 'editor' && !!this.app?.selectedImage;
    
    // Get the key combination string
    const key = this._getKeyString(e);

    // Look up binding
    const binding = this.bindings[key];
    if (!binding) return;

    // Do not fire non-global shortcuts while typing in a form field.
    if (isTypingTarget && binding.context !== 'global') {
      return;
    }

    // Editor shortcuts only run while editor view is active.
    if (binding.context === 'editor' && !inEditorContext) {
      return;
    }

    // Prevent default browser behavior for shortcuts we're handling
    e.preventDefault();

    // Handle special cases
    if (binding.action === 'toggleShortcutsHelp') {
      this.toggleShortcutsHelp();
    } else if (binding.action === 'closeShortcutsHelpIfOpen') {
      this.closeShortcutsHelpIfOpen();
    } else {
      // Get the action method from the app
      const actionMethod = this.app[binding.action];
      if (typeof actionMethod === 'function') {
        actionMethod.call(this.app);
      } else {
        console.warn(`Shortcut action not found: ${binding.action}`);
      }
    }
  },

  /**
   * Convert keyboard event to key combination string
   * @private
   */
  _getKeyString(e) {
    const parts = [];
    
    if (e.ctrlKey) parts.push('Ctrl');
    if (e.altKey) parts.push('Alt');
    if (e.shiftKey) parts.push('Shift');

    // Special key names
    const keyMap = {
      'Delete': 'Delete',
      'Escape': 'Escape',
      'Enter': 'Enter',
      'Tab': 'Tab',
      ' ': 'Space',
      '?': '?',
    };

    if (keyMap[e.key]) {
      parts.push(keyMap[e.key]);
    } else if (e.key.length === 1) {
      // Single character key
      parts.push(e.key.toUpperCase());
    } else {
      // Function keys, arrows, etc.
      parts.push(e.key);
    }

    return parts.join('+');
  },

  /**
   * Get formatted shortcut documentation
   */
  getDocumentation() {
    const editorShortcuts = [];
    const globalShortcuts = [];

    for (const [key, binding] of Object.entries(this.bindings)) {
      const item = {
        key,
        description: binding.description,
        action: binding.action,
      };

      if (binding.context === 'global') {
        globalShortcuts.push(item);
      } else {
        editorShortcuts.push(item);
      }
    }

    return {
      editor: editorShortcuts.sort((a, b) => a.key.localeCompare(b.key)),
      global: globalShortcuts.sort((a, b) => a.key.localeCompare(b.key)),
    };
  },

  /**
   * Toggle shortcuts help dialog
   */
  toggleShortcutsHelp() {
    this.helpDialogOpen = !this.helpDialogOpen;
    if (this.app) {
      if (this.helpDialogOpen) {
        this.app.showKeyboardShortcutsHelp();
      } else {
        this.app.closeKeyboardShortcutsHelp();
      }
    }
  },

  /**
   * Close shortcuts help dialog if it's open
   */
  closeShortcutsHelpIfOpen() {
    if (this.helpDialogOpen && this.app) {
      this.helpDialogOpen = false;
      this.app.closeKeyboardShortcutsHelp();
    }
  },
};
