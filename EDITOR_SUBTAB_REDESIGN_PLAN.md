# Editor Sub-Tab Redesign Plan

Status: Proposed
Date: 2026-05-03

## 1. Goals

- Split the current Editor experience into focused sub-pages so each workflow is easier to use.
- Keep caption generation and caption editing as the primary entry path.
- Move image manipulation tools out of the main caption workflow.
- Keep batch tag operations separate from both captioning and image manipulation.
- Show the selected image on both the Caption page and Image page.
- Add zoom controls (including full-size behavior) and a default zoom setting.

## 2. Proposed Information Architecture

Current:
- One Editor page with many stacked sections.

Proposed:
- Main tab remains Editor.
- Inside Editor, add a second-level tab bar with 3 sub-tabs:

1. Caption (default)
- Image preview with zoom controls.
- Included/Excluded toggle and image metadata summary.
- Caption generation panel.
- Active caption editor (or active tags editor in tags mode).
- Caption candidates (when not in tags mode).

2. Image
- Image preview with zoom controls.
- Included/Excluded toggle and metadata summary.
- Image tools panel (duplicate/delete/crop/scale/flip/rotate/extract).

3. Batch Tags
- Batch tag operations panel.
- Tag statistics panel.
- Visible only when project caption mode is tags.
- In description mode, either hide tab or show disabled tab with explanation.

## 3. UX Behavior Details

### 3.1 Sub-tab defaults

- On entering Editor, default to Caption sub-tab.
- Remember last used Editor sub-tab per project session.
- If user switches project mode from tags to description while on Batch Tags, auto-switch to Caption.

### 3.2 Image preview behavior

Show image preview on Caption and Image sub-tabs with identical controls:

- Fit to panel (default behavior).
- 50%, 75%, 100%, 125%, 150%, 200% zoom presets.
- Full size toggle (native pixel size, scroll container if needed).
- Reset zoom action.

Recommended interactions:
- Mouse wheel while hovering image uses zoom in/out (optional for first pass).
- Keyboard shortcuts for zoom in/out/reset (optional follow-up).

### 3.3 Zoom persistence

- Add a global default image zoom mode in Settings.
- Apply default when selecting a new image.
- Optionally remember per-session override while user is in Editor.

Suggested setting values:
- fit
- full
- 100
- 150

## 4. Technical Design

## 4.1 Frontend state additions

In app state (frontend/app.js), add:

- editorView:
  - subTab: caption | image | batch_tags
  - zoomMode: fit | full | percent
  - zoomPercent: number
  - rememberSubTab: boolean (optional)

In settings state, add:
- defaultEditorImageZoomMode
- defaultEditorImageZoomPercent (used when mode is percent)

## 4.2 Template structure changes

In frontend/index.html Editor section:

- Add second-level tab strip near the Editor header.
- Move existing sections into conditional blocks by sub-tab:
  - Caption sub-tab:
    - preview block
    - generation block
    - caption editing blocks
  - Image sub-tab:
    - preview block
    - image tools block
  - Batch Tags sub-tab:
    - existing batch tags + stats blocks
- Remove batch tags panel from default mixed layout to reduce scroll and cognitive load.

## 4.3 Feature module changes

In frontend/js/features/editor.js:

- Add helper methods:
  - setEditorSubTab
  - nextValidEditorSubTabForProject
  - initializeEditorViewForSelectedImage
  - setImageZoomMode
  - setImageZoomPercent
  - resetImageZoom
  - imagePreviewStyle (returns style object for current zoom mode)

- Ensure selectImage path initializes zoom with settings default and preserves expected behavior when switching images.

In frontend/app.js:

- Add delegated methods for new Editor sub-tab and zoom actions.
- Ensure applyProject and closeProject reset editorView state safely.

## 4.4 Settings API and persistence

Backend:
- Extend LLM/settings payload (or general app settings payload) with editor image zoom defaults.
- Keep backward compatibility by providing defaults if fields are absent.

Frontend:
- Add controls in Settings > General for default zoom mode and default zoom percent.

## 5. Suggested Improvements Beyond Original Request

1. Keep heavy controls out of caption flow
- Move all image manipulation controls to Image sub-tab only.
- Caption sub-tab remains focused on generate, refine, and choose.

2. Add sticky mini image header
- In both Caption and Image sub-tabs, keep filename/dimensions/included status in a compact sticky strip while scrolling long forms.

3. Add quick jump actions
- Small shortcuts near top:
  - Go to Image Tools
  - Go to Batch Tags (tags mode only)

4. Improve mobile behavior
- Sub-tab strip should become horizontally scrollable pills on narrow screens.
- Zoom presets collapse to a compact dropdown on mobile.

5. Preserve context safety
- If unsaved caption edit is in progress, sub-tab switch should keep draft in memory (no data loss).

## 6. Rollout Plan

Phase 1: Sub-tab scaffolding (no behavior changes)
- Add editor sub-tab state and visual sub-tab navigation.
- Keep existing sections but gated behind sub-tabs.

Phase 2: Move panels into target sub-tabs
- Caption content on Caption page.
- Image tools on Image page.
- Batch tag operations on Batch Tags page.

Phase 3: Add zoom controls and defaults
- Implement preview style controls in Caption and Image pages.
- Add settings fields and persistence.

Phase 4: Polish
- Improve mobile tabs.
- Add optional wheel zoom.
- Add quick-jump links and sticky metadata bar.

## 7. Testing Plan

Automated checks:

- Frontend smoke (API-driven style tests plus any existing e2e smoke):
  - Editor opens on Caption sub-tab by default.
  - Batch Tags sub-tab only available in tags mode.
  - Image tools actions still work from Image sub-tab.
  - Caption generation and candidate operations still work from Caption sub-tab.

- Settings persistence checks:
  - Default zoom settings round-trip through settings API.
  - Selecting new image applies configured default zoom.

Manual checks:

1. Description mode project:
- Caption sub-tab is default.
- Image sub-tab has tools and preview.
- Batch Tags is hidden or disabled with clear message.

2. Tags mode project:
- Caption sub-tab works for tags editing/generation.
- Batch Tags sub-tab displays batch add/remove/clear and stats.

3. Zoom behavior:
- Fit/full/percent controls update preview predictably.
- Reset returns to configured default.
- Same zoom control behavior on both Caption and Image sub-tabs.

## 8. Acceptance Criteria

- Editor has second-level tabs: Caption, Image, Batch Tags.
- Caption is default sub-tab.
- Image appears with zoom controls on Caption and Image sub-tabs.
- Batch tag operations are separated from caption and image manipulation workflows.
- Default zoom can be configured in settings and persists across app restarts.
- Existing generation, editing, image tool, and tag batch workflows remain functional.
