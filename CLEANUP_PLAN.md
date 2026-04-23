# Cleanup & Polish Plan

This document tracks concrete improvements now that the feature set is stable.
Work items are grouped by theme and roughly ordered by priority within each group.

---

## 1. Remove Phase References & Dead Markup

### 1a. Strip the "Phase 4" badge from the sidebar header
**File:** `frontend/index.html` line 47  
The `<span>` badge reading "Phase 4" is a leftover build-phase label.
Replace it with nothing, or with a small version/status badge that actually
means something (e.g. app version, or remove the right side of the header
entirely and let "Projects" stand alone).

### 1b. Audit OVERVIEW.md and any other root docs
Scan `OVERVIEW.md` for references to individual phases that only made sense
during incremental development. Rewrite phase-specific sections as feature
sections.

---

## 2. Left Sidebar: Structure & Usability

The sidebar currently shows a large amount of content at once and requires
significant scrolling. Several structural improvements are possible without
changing functionality.

### 2a. Collapse the "Open Project" panel when a project is already open
When `currentProject` is set, the "Open Project" path-input + browser still
renders in full. Its only purpose at that point is to switch projects.
Options:
- Render only a compact "Switch Project" button that expands the open form on
  demand (preferred — single click to reveal, second click hides it again).
- Or collapse the path browser by default and add a small toggle chevron to
  the "Path Browser" subheading to expand/collapse it.

### 2b. Move Import and Export panels to the main workspace area
Import Folder and Export Dataset logically belong to the workspace, not the
navigation sidebar. They are currently only visible when a project is open,
but are still large sections that add sidebar scroll.

Proposal:
- Add **Import** and **Export** as tabs alongside Grid / Editor / LLM / Batch
  in the main view tab bar.
- The sidebar retains only: project create/open/switch, project metadata, and
  recent projects.
- This also removes the need for "Use Dir For Export" in the browser when
  a project is open; that context-sensitive button can live next to the export
  output field instead.

### 2c. Cleaner "no project" state
When no project is open, the sidebar shows Create and Open forms plus the
path browser simultaneously. This is a lot of UI for a first-time user.

Consider a two-tab toggle at the top of the sidebar ("Create" / "Open") so
only one form is visible at a time, with the path browser shared below both.

### 2d. "Close Project" confirmation
`closeProject()` immediately wipes project state with no confirmation. If the
user has unsaved caption edits in the editor, they are silently discarded.
Add a brief `window.confirm` before closing, or track `isDirty` on
`editorCaptionText` and only prompt when there are unsaved changes.

### 2e. Path browser: make it a collapsible accordion
The path browser adds ~250px of sidebar height. Wrap it in a details/summary
or an Alpine `x-show` accordion with a heading that clearly reads
"Browse filesystem ▼". Collapsed by default — the user unfolds it when they
need it.

### 2f. Recent projects: show open-project path when a project is already active
Currently the recent projects list shows all entries and clicking one opens it
even if one is already open. Add visual differentiation:
- Mark the currently-open project in the list (e.g. amber border, "● Open" badge).
- Clicking another recent project could either close the current one and open
  the new one, or prompt if there are unsaved changes (ties into 2d).

---

## 3. Dropdown / Select Styling

All `<select>` elements currently rely entirely on native browser styling.
On most Linux/GTK environments the native dropdown is visually inconsistent
with the rest of the UI and is not obviously interactive.

### 3a. Add a reusable select wrapper class in `styles.css`

```css
.select-wrapper {
  position: relative;
}

.select-wrapper select {
  appearance: none;
  -webkit-appearance: none;
  padding-right: 2.25rem; /* room for the chevron */
}

.select-wrapper::after {
  content: '';
  pointer-events: none;
  position: absolute;
  right: 0.625rem;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #a8a29e; /* stone-400 */
}
```

Alternatively, inline an SVG chevron with `absolute right-3 top-1/2 -translate-y-1/2
pointer-events-none` inside a `relative` wrapper — this is slightly more
flexible for theming but requires more HTML changes.

### 3b. Wrap every `<select>` in the application

Selects to update (all currently missing chevron):
- `metadataForm.caption_mode` (sidebar, Edit Metadata)
- `llm.backend` (Editor tab, LLM Caption Generator)
- `llm.model` (Editor tab, LLM Caption Generator)
- `llm.selectedPresetId` (Editor tab, Preset picker)
- `llm.presetForm.backend` (LLM tab, preset edit form)
- `llm.presetForm.modelName` (LLM tab, preset edit form)
- `llm.presetForm.captionModeStrategy` (LLM tab, preset edit form)
- `batch.target` (Batch tab)
- `batch.outputMode` (Batch tab)
- Batch manual-mode `llm.backend` / `llm.model` selects
- Settings default preset selector
- Batch history status filter

---

## 4. JavaScript Refactors (app.js)

### 4a. Extract a `withSubmitting(fn)` helper to remove boilerplate

Every mutating async method repeats this pattern:
```js
this.isSubmitting = true;
this.errorMessage = '';
try {
    // ...
} catch (e) {
    this.errorMessage = e.message;
} finally {
    this.isSubmitting = false;
}
```

This pattern appears **at least 12 times**. Extract it once:
```js
async withSubmitting(fn) {
    this.isSubmitting = true;
    this.errorMessage = '';
    try {
        await fn();
    } catch (e) {
        this.errorMessage = e.message;
    } finally {
        this.isSubmitting = false;
    }
},
```

Then each method body collapses to `this.withSubmitting(async () => { ... })`.
This makes error handling consistent and removes ~100 lines of repetition.

### 4b. Reduce repeated `selectedImage ? selectedImage.X : ''` guards in the HTML

The editor section wraps most of its content in `<template x-if="selectedImage">`,
but several child bindings still repeat the `selectedImage ?` guard redundantly:
```html
:src="selectedImage ? imageSrc(selectedImage.id) : ''"
:alt="selectedImage ? selectedImage.filename : ''"
x-text="selectedImage ? selectedImage.filename : ''"
x-text="selectedImage ? `${selectedImage.width || '?'} x ...` : ''"
```
Because these elements are already inside the `x-if="selectedImage"` template,
the guards are redundant. Remove them.

### 4c. Single `isSubmitting` flag blocks unrelated operations simultaneously
Currently `isSubmitting` is a single global flag: saving a caption disables the
Import button, the Export button, the Close button, etc. This is overly
restrictive.

Finer-grained approach — replace with a `Set` of active operation keys:
```js
activeOps: new Set(),
isActive(key) { return this.activeOps.has(key); },
isAnyActive() { return this.activeOps.size > 0; },
```
Each operation has a string key (e.g. `'saveCaption'`, `'importFolder'`,
`'generateCaption'`), and only the buttons relevant to that key are disabled.
This is a larger change — consider deferring until after the other cleanup
items are done.

### 4d. `loadLatestBatchJob()` calls duplicated on project open
In `applyProject()`, three sequential calls are made to populate batch state.
`loadLatestBatchJob()` already internally calls `loadBatchHistory()`.
Verify whether the second standalone `loadBatchHistory()` call is truly
needed, or if it is a duplicate that can be removed.

### 4e. Tab auto-switch on image selection
Clicking an image card in the Grid view currently selects it, but does not
automatically navigate to the Editor tab. The user must click the card, then
click the "Editor" tab. Since the most common next action after selecting an
image is editing, consider auto-switching to the Editor tab when an image is
selected from the grid. This could be a simple `this.mainView = 'editor'`
added to the `selectImage(id, true)` call, or a new `selectImage(id, navigateToEditor = false)`
parameter that the grid cards pass as `true`.

---

## 5. HTML Structure & Minor Markup Cleanup

### 5a. Tab bar description text is not useful at runtime
The inline description `<span>` after the tab bar (e.g. "Browse and pick an
image", "Single image editing mode", etc.) takes up space but users rarely
read it once they know the app. Consider removing it or replacing it with
contextual info, e.g. the currently-selected image filename when in Editor
mode, or the active batch job status when in Batch mode.

### 5b. Consolidate checkbox label patterns
Every checkbox uses a `<label class="flex items-center gap-2 text-sm text-stone-300">` wrapper.
This is consistent but repeated ~10 times with identical classes. Adding a
short Tailwind component class `.field-checkbox` in `styles.css` would remove
the verbosity without a build step:
```css
.field-checkbox {
  @apply flex items-center gap-2 text-sm;
  color: theme('colors.stone.300');
}
```
*(Tailwind CDN supports `@apply` in custom stylesheets if the config is set.
If not, a plain CSS equivalent with flex/gap is fine.)*

### 5c. Caption candidate list height is very short (max-h-48)
With several candidates the list becomes very cramped. Increase to `max-h-64`
or `max-h-72` to show more candidates before scrolling.

### 5d. "Generate Manual Caption" and "Generate With Preset" button placement
These two buttons are currently in a `flex flex-wrap` row along with the
"Set generated caption as active" checkbox and the timeout display. As the
row wraps on narrower viewports they lose their visual relationship.
Give them their own row below the controls so they're always visible side by
side.

---

## 6. Settings Page Usability

### 6a. Group settings visually
The settings form is a flat vertical list. Add section headers:
- **LLM Defaults** (timeout, default preset, show all models)
- **Ollama** (base URL + timeout + Test button)
- **LM Studio** (base URL + timeout + Test button)
- **Project Behaviour** (reopen last project)
- **Debug** (collapsible, RAG controls)

### 6b. Test Connection feedback persistence
After clicking "Test Connection", the inline result (ok/fail message) disappears
as soon as the user types in the URL field (because the URL field has no
`@input="connectionTest.ollama = null"` handler). Decide on the intended
behaviour: either clear the result on input (add the handler), or keep the last
result visible until the next test is run. Currently neither is enforced.

---

## 7. Backend Minor Cleanup

### 7a. Consistent Pydantic model naming
`RebuildEmbeddingsRequest` vs `TestConnectionRequest` — the naming is consistent
in style but could audit that all request models are co-located at the top of
`llm.py` rather than interspersed with route definitions. Currently
`TestConnectionRequest` was added just before its route; move it with the other
request model declarations.

### 7b. `llm_service.py` — `generate_caption_for_image` is the only call path from routers
Verify `apply_generated_caption` in `caption_service.py` is not called from
anywhere else; if it is only called by `llm_service`, ensure its docstring
makes that clear. If it is dead outside of that internal call, mark it
`_apply_generated_caption` to signal it is not a public service function.

### 7c. `rag_service.py` wrapper functions
If RAG is disabled, `rag_service` functions all return early no-ops. Confirm
`chromadb_service.py` functions are only ever called from `rag_service.py`
(not directly from routers), keeping the optional-dependency isolation clean.

---

## Order of Work (Suggested)

| Priority | Item | Effort |
|----------|------|--------|
| High | 1a — remove Phase 4 badge | Trivial |
| High | 3a+3b — dropdown chevrons | Small |
| High | 2a — collapse Open panel when project active | Small |
| High | 2e — collapsible path browser | Small |
| Medium | 4a — `withSubmitting` helper | Medium |
| Medium | 2b — Import/Export as main tabs | Medium |
| Medium | 4e — auto-switch to Editor on image select | Trivial |
| Medium | 5a — remove tab description text (or make contextual) | Small |
| Medium | 4b — remove redundant selectedImage guards | Small |
| Medium | 6a — group settings visually | Small |
| Medium | 2c — Create/Open two-tab toggle (no project state) | Small |
| Low | 2d — Close project confirmation | Small |
| Low | 5b — `.field-checkbox` component class | Small |
| Low | 5c — caption candidate list height | Trivial |
| Low | 5d — generation button layout | Small |
| Low | 6b — connection test feedback clarity | Trivial |
| Low | 7a–7c — backend minor cleanup | Trivial each |
| Deferred | 4c — per-operation `isSubmitting` set | Large |
