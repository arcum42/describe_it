# Phase 6: Dataset Export Guide

This guide explains how to export your captioned image dataset from describe_it in a format ready for training.

## Quick Start

1. Open or create a project in describe_it.
2. In the sidebar, scroll to the **Export Dataset** section.
3. Set your **Output Folder** (or use the path browser to select one).
4. Click **Preview Export** to see what will be exported.
5. Click **Export Dataset** to write the files.

## Export Basics

### Output Format

Export creates a folder with:
- Image files (original format: PNG, JPG, WebP, etc.)
- Accompanying `.txt` files with captions (same filename as the image, but with `.txt` extension)

**Example:**
```
exports/my_dataset/
├── image_001.jpg
├── image_001.txt
├── image_002.png
├── image_002.txt
└── image_003.webp
└── image_003.txt
```

### Active Captions

Export always uses the **active caption** for each image. If an image has multiple caption candidates, only the one marked active will be exported.

If an image has no active caption (blank), the exported `.txt` file will be empty.

## Export Options

### Basic Options

#### Export Only Included Images
**Checked by default.** When enabled, only images marked as "included" in the grid will be exported. Excluded images are skipped.

#### Output Folder
The destination folder where images and captions will be written. You can:
- Type an absolute or relative path directly.
- Use the path browser to navigate and select a folder.
- Use the **Use Dir For Export** button in the path browser to set the current directory.

### Advanced Options

#### Export Into a New Subfolder
When enabled, export creates a new subfolder inside the Output Folder. Useful for organizing multiple export runs.

**Example:** If Output Folder is `exports/` and "New Folder Name" is `run_001`, files will be written to `exports/run_001/`.

If the folder name is left blank, the backend auto-generates a timestamped name like `export_20260421_142530/`.

#### Apply Project Trigger Word (if set)
**Optional.** When enabled and a trigger word is set on the project, the trigger word is prepended to each caption during export, separated by a comma.

**Example:**
- Project trigger word: `dog`
- Original caption: `a dog sitting on grass`
- Exported caption: `dog, a dog sitting on grass`

If no trigger word is set on the project, this option has no effect (captions export as-is).

#### Write Export Metadata Manifest
When enabled, exports an `export_manifest.json` file containing:
- Project metadata (name, description, caption mode, trigger word)
- Export options used (included-only, trigger-word applied, etc.)
- Per-image records with filename, caption status, and inclusion state
- Summary counts (exported, skipped, collision details)

Useful for tracking export provenance and validating dataset integrity.

#### Overwrite Existing Files in Destination
By default, if target files already exist, they are **skipped** (no collision).

When enabled, existing files are replaced. Useful for re-exporting the same dataset after captions have changed.

**Note:** You cannot use this option together with **Clean Destination Folder**.

#### Clean Destination Folder Before Export
When enabled, all files and subdirectories in the destination folder are **deleted** before export begins.

Ensures a fresh export with no stale or leftover files from previous runs.

**Note:** You cannot use this option together with **Overwrite Existing Files**.

**Safety:** The app prevents cleaning critical system directories (filesystem root, home directory, application directory).

## Export Preview

Before exporting, use the **Preview Export** button to see:
- Final destination path (including any new subfolder)
- Number of images ready to export
- Number of excluded images
- Number of blank captions
- Collision warning if target files already exist
- Trigger word applicability note

Preview helps you catch configuration mistakes before the export runs.

## Export Results

After export completes, you'll see a status message like:

```
Exported 42 images to /home/user/exports/my_dataset.
```

If files were skipped:

```
Exported 40 images to /home/user/exports/my_dataset (2 skipped: 1 collisions, 1 missing image data).
```

Reasons for skipped images:
- **Collision:** Target file already existed and "Overwrite" was not enabled.
- **Missing image data:** Image record exists but the original file was corrupted or lost (rare).

## Workflow Examples

### Simple Export to Folder

1. Set Output Folder to `~/ml_datasets/`
2. Leave all options at defaults (include all, no trigger word).
3. Click Preview Export → confirm counts.
4. Click Export Dataset.
5. Result: `~/ml_datasets/image_001.jpg`, `image_001.txt`, etc.

### Export to New Run Folder

1. Set Output Folder to `~/exports/`
2. Enable **Export Into a New Subfolder**.
3. Type **New Folder Name:** `experiment_001`
4. Click Preview Export.
5. Click Export Dataset.
6. Result: `~/exports/experiment_001/image_001.jpg`, etc.

### Export with Trigger Word

1. In project settings, set **Trigger Word** to `training_tag`.
2. In Export section, enable **Apply Project Trigger Word (if set)**.
3. Preview → Export.
4. Result: captions will have `training_tag,` prepended.

### Safe Re-export After Edits

1. Set Output Folder to existing `~/exports/my_dataset/`.
2. Enable **Overwrite Existing Files**.
3. Preview → Export (files will be updated).

Or:

1. Set Output Folder to `~/exports/`.
2. Enable **Export Into a New Subfolder** with name `my_dataset_v2`.
3. Enable **Write Export Metadata Manifest**.
4. Export → creates `~/exports/my_dataset_v2/` with manifest for comparison.

## Export Manifest

When **Write Export Metadata Manifest** is enabled, an `export_manifest.json` file is created:

```json
{
  "generated_at": "2026-04-21T14:25:30",
  "project_name": "My Dataset",
  "project_description": "Training images",
  "project_caption_mode": "description",
  "project_trigger_word": "dog",
  "options": {
    "included_only": true,
    "apply_trigger_word": true,
    "trigger_word_applied": true,
    "overwrite_existing": false,
    "clean_output_folder": false,
    "create_new_folder": true,
    "new_folder_name": "run_001"
  },
  "counts": {
    "exported_images": 42,
    "skipped_images": 0,
    "skipped_missing_blob": 0,
    "skipped_due_to_collision": 0
  },
  "images": [
    {
      "image_id": 1,
      "filename": "photo_001.jpg",
      "image_file": "photo_001.jpg",
      "caption_file": "photo_001.txt",
      "included": true,
      "caption_is_blank": false
    },
    ...
  ]
}
```

Use this manifest to:
- Document what was exported and when.
- Verify which options were used.
- Track per-image inclusion and blank caption status.
- Cross-check counts programmatically.

## Tips & Gotchas

- **Relative Paths:** Export folder paths are resolved relative to the app's working directory (usually the project root). Use absolute paths (starting with `/` or `~`) for clarity.
- **Permissions:** Ensure you have write permissions to the destination folder.
- **Disk Space:** Large exports can consume significant disk space. Preview the count before exporting thousands of images.
- **Trigger Word and Blank Captions:** If a caption is blank and trigger word is enabled, only the trigger word is exported.
- **Preview Doesn't Modify Anything:** The Preview Export button only reads data; it doesn't write or delete files.
- **Include/Exclude Toggle:** Use the grid view to include/exclude individual images before export.

## Troubleshooting

**"Select an export output folder first"**
→ Set the Output Folder field or use the path browser to select one.

**"No images matched the selected batch target"** (if exporting from batch context)
→ Ensure at least one image is included and has a blob stored.

**"Refusing to clean..."**
→ The clean option won't allow you to delete critical system directories. Choose a different output folder.

**Exported files don't have expected content**
→ Check that the active caption is set correctly in the image editor. Export uses only active captions.

**"Exported X images, Y skipped due to collisions"**
→ Target files already exist. Either enable Overwrite, use a new subfolder name, or clean the destination first.
