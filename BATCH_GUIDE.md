# Batch Generation, Presets, and Backend Settings

This guide covers the full AI-assisted captioning workflow: configuring backends, creating presets, running batch jobs, and understanding caption output modes.

---

## Backend Runtime Settings

Before generating captions, make sure your AI backend is reachable. Go to **Settings** and look for the **Backend Runtime** section.

### Base URL

| Field | Default | Purpose |
|-------|---------|---------|
| Ollama Base URL | `http://127.0.0.1:11434` | Address where Ollama is running |
| LM Studio Base URL | `http://127.0.0.1:1234` | Address where LM Studio server is running |

Change these if your backend runs on a different port or a remote machine. Click **Test** next to each URL to verify connectivity — the result shows whether the connection succeeded and how many models were found.

### Timeout Override

Each backend can have its own timeout in seconds, overriding the global timeout set at the top of Settings. Leave blank to use the global timeout.

- **Global timeout**: applies to all backends by default (10–900 seconds)
- **Per-backend override**: useful when one backend is slower (e.g., large models on Ollama vs. a faster LM Studio instance)

### Refreshing Available Backends

The **Backends** panel (visible in the editor and in Settings debug section) lists discovered backends and their available models. Click **Refresh** to re-query. Vision-capable models are marked with a visual indicator.

---

## Presets

A preset is a saved generation configuration: backend, model, caption mode strategy, and an optional custom system prompt.

### Creating a Preset

1. Go to the **Generate** section in the image editor.
2. Click **New Preset**.
3. Fill in:
   - **Name**: a label for the preset (e.g., "Ollama LLaVA — Tags")
   - **Backend**: `ollama` or `lmstudio`
   - **Model**: select from discovered models
   - **Caption Mode Strategy**: see below
   - **System Prompt** (optional): custom instructions appended to the built-in prompt

### Caption Mode Strategy

The caption mode strategy controls what kind of text the AI generates.

| Strategy | Behaviour |
|----------|-----------|
| `auto` | Uses the project's caption mode (set when creating the project). Defaults to `description` if not set. |
| `description` | Generates a single concise prose sentence describing the image. |
| `tags` | Generates a comma-separated tag list of short visual attributes, suitable for Danbooru-style tag training. |

**When to use each:**

- Use `description` for natural language captions (e.g., SDXL DreamBooth or Flux fine-tuning with sentence captions).
- Use `tags` for tag-based training workflows where the model expects comma-separated tokens.
- Use `auto` if you want the preset to respect whatever mode is set on the project, which is convenient when you reuse a preset across multiple projects.

### Custom System Prompts

The built-in prompt is generated automatically from the image filename, dataset description, and caption mode. If you add a system prompt in the preset, it replaces the built-in template entirely.

The following placeholder tokens are available in custom system prompts:

| Token | Replaced with |
|-------|---------------|
| `{dataset_description}` | The project's description field |
| `{current_caption}` | The image's current active caption text |

Leave the system prompt blank to use the built-in auto-generated prompt.

### Setting a Default Preset

In Settings, enable **Use preset by default** and select a preset from the dropdown. This preset will be selected automatically when you open the generator panel or start a batch job.

---

## Batch Generation

Batch generation runs AI captioning across multiple images without manual intervention. Jobs survive backend restarts — any running or queued job is automatically paused when the server stops and can be resumed.

### Starting a Batch Job

1. In the sidebar, open the **Batch Generate** section.
2. Choose a target:
   - **Included only** — process only images marked as included
   - **Uncaptioned included** — only included images with a blank active caption
   - **All** — every image in the project regardless of include status
3. Select a preset (or configure manual backend/model if not using a preset).
4. Configure output options (see below).
5. Click **Start Batch**.

### Output Modes

The output mode controls how the generated text is applied to each image.

| Mode | Behaviour |
|------|-----------|
| `new_candidate` | Creates a new caption candidate. The current active caption is not changed unless **Make active** is also enabled. |
| `replace_active` | Overwrites the current active caption text in place. No new candidate is created. |
| `append_active` | Appends the generated text to the active caption, separated by a newline. Useful for building composite captions (e.g., scene description + tags). |

**Recommendation:** Use `new_candidate` when you want to review AI output before committing it. Use `replace_active` when you trust the model and want a clean, single-caption workflow.

### Make Active

When enabled, the generated caption is immediately set as the active caption for each image. This applies to `new_candidate` mode — in `replace_active` and `append_active` modes, the active caption is always updated.

### Error Handling

| Option | Behaviour |
|--------|-----------|
| **Skip on failure** | If generation fails for an image, log the error and continue to the next image. The job status becomes `completed` even if some images failed. |
| **Retry count** | Number of extra attempts per image before marking it as failed (0 = one attempt total, max 5 retries). |

Set **Skip on failure** to `true` for large unattended batches. Disable it if you want the job to stop on the first error so you can investigate.

### Monitoring Progress

The batch panel shows:
- Current status: `queued` → `running` → `paused` / `completed` / `failed` / `cancelled`
- Counts: total images, completed, succeeded, failed
- The filename currently being processed
- The most recent generated text

### Pause and Resume

Click **Pause** at any time. The job stops after the current image finishes (it will not interrupt mid-generation). Click **Resume** to continue from where it left off.

If the job status is `failed` (stopped on error with skip disabled), **Resume** rewinds one step to retry the failed image.

### Job History

Previous batch jobs are listed in the **History** tab of the batch panel. Filter by status (all, completed, failed, cancelled). Click a job to inspect per-image results.

### Exporting Results as CSV

In the job detail view, click **Export CSV** to download a spreadsheet with one row per image showing:

- `filename`, `status`, `attempts`, `generated_text`, `error`, `started_at`, `finished_at`

This is useful for auditing which images succeeded, reviewing generated captions in bulk, or identifying patterns in failures.

---

## Tips

- **Run a small test batch first.** Start with 5–10 images using `new_candidate` mode before committing to a full dataset run.
- **Use presets per style.** Create separate presets for tags vs. descriptions rather than switching the project caption mode mid-project.
- **Uncaptioned target is safe to re-run.** If a batch fails partway through, starting a new batch with target `uncaptioned included` will only process the images that still have blank captions.
- **Adjust timeout for large models.** If you see timeout errors, raise the per-backend timeout override or the global timeout in Settings.
