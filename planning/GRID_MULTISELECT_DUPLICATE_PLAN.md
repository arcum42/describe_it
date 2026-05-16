# Grid Multi-Select and Duplicate Cleanup Plan

## Goal

Add two related project-management workflows to the existing image grid:

- Multi-select in grid view with bulk actions for delete, duplicate, include, exclude, and clear selection.
- Duplicate-image cleanup by content hash, with caption merging from removed images onto the kept image.

The implementation should stay consistent with the current static frontend, FastAPI backend, and conservative handling of destructive operations.

## Current Anchors

### Frontend

- Grid state lives in `frontend/app.js` via `images`, `gridCards`, and `gridFilter`.
- Grid rendering lives in `frontend/index.html` under the `mainView === 'grid'` block.
- Image loading and editor actions live in `frontend/js/features/editor.js`.
- Existing single-image actions already exist for:
  - include/exclude via `toggleIncluded()`
  - duplicate via `duplicateImage()`
  - delete/restore via image tools

### Backend

- Image API router is `backend/routers/images.py`.
- Core image operations live in `backend/services/image_service.py`.
- Duplicate detection by SHA-256 already exists for imageboard import in `backend/services/imageboard_import_service.py`.
- Images already support soft delete through `deleted_at` and hard delete by explicit confirmation.
- Captions are separate rows in `CaptionRecord`, so caption merging can be handled without schema changes.

## Product Decisions

### Multi-select scope

- Selection is only a grid-view concern.
- Selection should persist while filtering/sorting changes, as long as the image still exists.
- Selection should be cleared when:
  - project changes
  - images are reloaded and an image no longer exists
  - user clicks `Unselect All`

### Bulk delete behavior

- Default bulk delete should use the existing soft-delete path.
- Hard delete should remain a separate explicit confirmation path if added later.
- For the first pass, the bulk delete action should map to soft delete only.

This matches the repo's preference for conservative destructive operations.

### Duplicate cleanup behavior

- Duplicate detection should use SHA-256 of stored image bytes.
- For parity with current import-time duplicate detection, hash the `original_blob` when present.
- Ignore rows already soft-deleted.
- Group duplicates by exact hash.
- Keep one image per hash group and remove the rest.

Recommended keep rule:

- Keep the oldest surviving image in the group by ascending `id`.

Recommended caption merge rule:

- Copy captions from removed images onto the kept image when the caption text is not already present on the kept image.
- Treat exact normalized text match as duplicate:
  - compare `text.strip()`
  - preserve original casing/content when inserting
- Preserve the kept image's existing active caption.
- Imported captions added during merge should be created as inactive unless there is no active caption on the kept image.

Recommended delete mode for duplicate cleanup:

- Produce a preview first.
- On apply, soft-delete duplicates by default.
- If later needed, a hard-delete follow-up can be added behind a second explicit confirmation.

## Phase 1: Grid Selection State

Add app-level state in `frontend/app.js`:

- `gridSelectionMode: boolean`
- `selectedGridImageIds: number[]` or `Set`-like array-backed helper state
- Helper methods/computed values:
  - `isGridImageSelected(imageId)`
  - `toggleGridImageSelection(imageId)`
  - `clearGridSelection()`
  - `selectAllFilteredGridImages()` (optional but useful)
  - `selectedGridImages()`
  - `selectedGridCount()`

Implementation notes:

- Keep this state near `gridCards` and `gridFilter`.
- Reconcile selection after every `loadImages()` call so deleted/missing IDs drop out automatically.
- Avoid tying bulk selection to `selectedImage`; single-image editor flow should remain unchanged.

## Phase 2: Grid UI Changes

Update `frontend/index.html` grid view to support selection without breaking the current click-to-open-editor behavior.

### Proposed UX

- Add a compact grid action bar above the card list with:
  - `Select Multiple` toggle
  - selected count
  - `Include Selected`
  - `Exclude Selected`
  - `Duplicate Selected`
  - `Delete Selected`
  - `Unselect All`
  - `Find Duplicates`
- When selection mode is on:
  - each card shows a checkbox in a stable corner position
  - clicking the checkbox toggles selection without switching to editor view
  - clicking the rest of the card can still open the editor
- When selection mode is off:
  - current grid behavior remains unchanged

### UX safeguards

- Disable bulk action buttons when no images are selected.
- Show `N selected` based on current selection, not only visible filtered cards.
- If filters hide some selected items, keep them selected and communicate this in the count.
- For bulk delete and duplicate cleanup apply actions, require confirmation.

## Phase 3: Backend Bulk Image Operations

Add batch-oriented API support in `backend/routers/images.py` and service helpers in `backend/services/image_service.py`.

### New request models

- `BatchIncludedRequest`
  - `project_path`
  - `image_ids: list[int]`
  - `included: bool`
- `BatchDuplicateRequest`
  - `project_path`
  - `image_ids: list[int]`
  - `include_captions`
  - `copy_mode`
- `BatchDeleteRequest`
  - `project_path`
  - `image_ids: list[int]`
  - `mode` default `soft`

Use `Field(min_length=1)` on `image_ids` in Pydantic v2 style.

### New endpoints

- `POST /api/images/batch/included`
- `POST /api/images/batch/duplicate`
- `POST /api/images/batch/delete`

### Service design

Refactor `image_service.py` so single-item and batch-item flows share session-level helpers instead of calling one route helper in a loop.

Suggested private helpers:

- `_set_image_included(session, ...)`
- `_duplicate_image_record(session, ...)`
- `_delete_image_record(session, ...)`

Then expose public wrappers:

- `update_image_included(...)`
- `batch_update_image_included(...)`
- `duplicate_image(...)`
- `batch_duplicate_images(...)`
- `delete_image(...)`
- `batch_delete_images(...)`

### Response shape

Return summary-oriented payloads rather than one giant object per image:

- affected count
- skipped IDs if any
- for duplicate: created image count and new image IDs
- for delete: deleted count and mode

That keeps frontend refresh simple: execute action, reload images and summary, prune selection, show status message.

## Phase 4: Frontend Bulk Action Wiring

Add new grid action methods in `frontend/app.js` delegating into `frontend/js/features/editor.js` or a new `grid.js` feature module.

Recommended direction:

- Create `frontend/js/features/grid.js` for grid-only workflows.
- Keep editor-specific logic in `editor.js`.

Methods to add:

- `bulkIncludeSelected()`
- `bulkExcludeSelected()`
- `bulkDuplicateSelected()`
- `bulkDeleteSelected()`
- `clearGridSelection()`
- `runDuplicateCleanupPreview()`
- `applyDuplicateCleanup()`

Shared post-action behavior:

- call the backend endpoint
- reload images
- reload image summary
- drop missing/deleted IDs from selection
- keep surviving selections when sensible
- update status/error message

## Phase 5: Duplicate Hash Scan Service

Add a dedicated duplicate-cleanup service, preferably in `backend/services/image_service.py` unless it becomes large enough to justify `backend/services/image_dedup_service.py`.

### New service functions

- `find_duplicate_images_by_hash(project_path: str) -> dict`
- `apply_duplicate_cleanup(project_path: str, duplicate_groups: ... , delete_mode: str = "soft") -> dict`

### Detection algorithm

1. Load non-deleted images.
2. For each image, hash `original_blob` when present.
3. Skip rows with null blobs.
4. Build `hash -> [image rows]` groups.
5. Return only groups where count > 1.

### Preview payload

Return enough detail for the UI to explain what will happen:

- hash prefix
- kept image ID and filename
- duplicate image IDs and filenames
- caption counts on kept/duplicate rows
- total duplicate groups
- total removable images

### Apply algorithm

For each duplicate group:

1. Determine kept image.
2. Load captions for the kept image and duplicate images.
3. Build a normalized set of kept caption texts.
4. Insert missing captions from duplicates onto the kept image.
5. Delete duplicates using the selected delete mode.
6. Commit one transaction per apply run.

### Safety rules

- Reject apply if preview data is stale or malformed.
- Prefer recomputing duplicate groups on apply rather than trusting client-submitted hash groups blindly.
- Return counts for:
  - groups processed
  - images removed
  - captions merged
  - captions skipped as duplicates

## Phase 6: Duplicate Cleanup UI

Add a lightweight duplicate-cleanup flow in the grid toolbar or a modal.

### Proposed flow

1. User clicks `Find Duplicates`.
2. Frontend requests duplicate preview.
3. If no duplicates:
   - show status message and stop.
4. If duplicates exist:
   - show summary and a short preview list
   - explain keep rule and caption-merge rule
   - show `Apply Cleanup` button
5. On apply:
   - require confirmation
   - run cleanup
   - reload grid and summary

### UI scope for first pass

- A summary modal or inline panel is sufficient.
- No need for per-group manual keep-selection in v1.

That keeps the initial implementation small and deterministic.

## API Summary

### Bulk grid actions

- `POST /api/images/batch/included`
- `POST /api/images/batch/duplicate`
- `POST /api/images/batch/delete`

### Duplicate cleanup

- `GET /api/images/duplicates?project_path=...`
- `POST /api/images/duplicates/cleanup`

Suggested cleanup request body:

```json
{
  "project_path": "projects/example.db",
  "mode": "soft"
}
```

For v1, the server can recompute groups on apply instead of accepting a client-supplied plan.

## Test Plan

### Backend tests

Add focused pytest coverage in:

- `tests/test_image_tools_phaseb.py`
  - batch include/exclude updates multiple rows
  - batch duplicate creates one derived image per selected source
  - batch delete soft-deletes multiple rows
- new `tests/test_image_duplicate_cleanup.py`
  - duplicate scan groups identical blobs
  - cleanup keeps oldest image by ID
  - cleanup merges only missing captions
  - cleanup ignores already deleted rows
  - cleanup handles null blob rows safely
  - cleanup preserves kept active caption

### API/smoke coverage

Extend `tests/test_smoke_e2e.py` with:

- multi-image include/exclude API flow
- duplicate cleanup endpoint flow on a small synthetic project

### Optional frontend regression coverage

If UI test coverage is added later, target:

- selection survives filter changes
- `Unselect All` clears selection state
- bulk action buttons disable correctly

## Implementation Order

1. Backend batch operation helpers and endpoints.
2. Backend duplicate-scan preview and cleanup endpoints.
3. Grid selection state in `frontend/app.js`.
4. Grid toolbar and checkbox UI in `frontend/index.html`.
5. Frontend wiring for bulk actions.
6. Frontend duplicate preview/apply flow.
7. Focused regression tests.

This order keeps the first executable slice on the backend, where behavior is easiest to verify with pytest before adding UI complexity.

## Risks and Mitigations

### Risk: selection and filters drift apart

Mitigation:

- store selection by image ID only
- reconcile against freshly loaded `images`
- compute visible vs selected counts explicitly

### Risk: duplicate cleanup is more destructive than intended

Mitigation:

- preview before apply
- default cleanup to soft delete
- keep deterministic keep rule
- surface merged/deleted counts in result message

### Risk: duplicate caption merge creates noisy candidate lists

Mitigation:

- exact normalized-text dedupe during merge
- keep added captions inactive by default

### Risk: duplicated backend logic between single and batch actions

Mitigation:

- extract session-level helpers and reuse them from both single-item and batch-item service functions

## Recommended First Slice

If implemented incrementally, start with:

1. Batch include/exclude endpoint and tests.
2. Grid selection UI with `Include Selected`, `Exclude Selected`, and `Unselect All`.
3. Batch duplicate and soft-delete.
4. Duplicate hash scan preview and apply flow.

That sequence delivers user-visible value early while keeping the duplicate-cleanup work isolated until the bulk-action foundation is stable.
