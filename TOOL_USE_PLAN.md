# Tool Use Plan

This document describes the planned implementation of tool-augmented caption generation in describe_it.

---

## Overview

Three phases of work:

1. **Detection** — expose which models support tool/function calling; show a hammer icon in the UI next to tool-capable models (alongside the existing eye icon for vision models)
2. **Backend tools** — implement the tool execution layer: web search, web page fetch, and local text file reference
3. **Generation integration + UI** — wire tools into the caption generation flow and expose controls in the Editor and LLM tabs

---

## Background: How Tool Calling Works

Both Ollama and LM Studio follow the OpenAI function-calling API format, sent over the `/v1/chat/completions` endpoint (`tools` array in the request body).

The agentic loop:
1. Send initial request with tool definitions and the image + prompt
2. If the model's response has `tool_calls`, execute each requested tool and collect results
3. Append the assistant's tool-call message and each tool result message to the conversation
4. Send the updated conversation back to the model (without tools, so it writes the final caption)
5. Extract the final text as the caption

Smaller or non-trained models may attempt tool calls with malformed output — the loop must handle this gracefully (fall back to the plain text response).

---

## Phase 1 — Tool-Capability Detection

### 1a. Add `tool_capable` to `ModelInfo`

**File:** `backend/llm/base.py`

Add a `tool_capable: bool = False` field to the `ModelInfo` dataclass alongside the existing `vision_capable` field.

```python
@dataclass
class ModelInfo:
    name: str
    vision_capable: bool = False
    tool_capable: bool = False
    capabilities: list[str] | None = None
```

### 1b. Populate `tool_capable` in Ollama client

**File:** `backend/llm/ollama_client.py`

Ollama's `/api/show` endpoint returns a `capabilities` list for each model. The capability string is `"tools"` when the model supports tool calling (same pattern as `"vision"`).

In `list_models()`, update the `ModelInfo` construction:

```python
ModelInfo(
    name=name,
    vision_capable="vision" in capabilities,
    tool_capable="tools" in capabilities,
    capabilities=capabilities,
)
```

**Reference:** https://docs.ollama.com/capabilities/tool-calling

### 1c. Populate `tool_capable` in LM Studio client

**File:** `backend/llm/lmstudio_client.py`

LM Studio's `/api/v1/models` response includes a `capabilities` object per model:

```json
"capabilities": {
  "vision": true,
  "trained_for_tool_use": true
}
```

Add a `_tool_capable()` method mirroring `_vision_capable()`:

```python
def _tool_capable(self, entry: dict[str, object], capabilities: list[str]) -> bool:
    raw_capabilities = entry.get("capabilities")
    if isinstance(raw_capabilities, dict):
        tool_value = raw_capabilities.get("trained_for_tool_use")
        if isinstance(tool_value, bool):
            return tool_value
    return any(token in {"tools", "function_calling", "tool_use"} for token in capabilities)
```

Update `_parse_models()` to call it and pass the result to `ModelInfo`.

**Reference:** https://lmstudio.ai/docs/developer/rest/list (`capabilities.trained_for_tool_use`)

### 1d. Expose `tool_capable` from the router

**File:** `backend/routers/llm.py`

The `/api/llm/backends` route currently returns `vision_capable` per model. Add `tool_capable` to the same dict:

```python
{
    "name": model.name,
    "vision_capable": model.vision_capable,
    "tool_capable": model.tool_capable,
    "capabilities": model.capabilities or [],
}
```

### 1e. Show hammer icon in the UI

**File:** `frontend/app.js`

Add a `modelCapabilityLabel()` function update (or a new helper `modelToolLabel()`) that returns a hammer emoji/icon string when `tool_capable` is true. The existing `modelCapabilityLabel()` already handles the eye icon — extend it to also append a hammer indicator.

**File:** `frontend/index.html`

Wherever the eye icon is shown (model picker dropdowns in the Editor, LLM, Batch tabs), add the same conditional hammer icon inline. LM Studio's own UI already shows a hammer badge for `trained_for_tool_use` models; we mirror that convention.

The icon can be a simple `🔨` emoji in the option text (matching the existing `👁` eye approach), or an SVG badge on the select option label — since `<option>` elements don't support rich HTML, emoji in the text label is the practical choice.

---

## Phase 2 — Tool Implementations

### Architecture

All tools live in a new service module. The tool definitions (JSON schema) and the Python executor functions are co-located so the tool loop can reference both.

**New file:** `backend/services/tool_service.py`

Each tool exposes:
- A JSON schema dict (for inclusion in the `tools` array of the LLM request)
- An executor function `(arguments: dict) -> str` that performs the action and returns a result string

```python
class ToolResult:
    tool_name: str
    content: str         # returned to the model
    display_summary: str # shown in the UI status message

def execute_tool(name: str, arguments: dict) -> ToolResult: ...
```

### Tool 1 — Web Search

**Definition name:** `web_search`

Parameters:
- `query` (string, required) — the search query
- `max_results` (integer, optional, default 5, max 10)

Implementation: Uses DuckDuckGo's HTML search endpoint (`https://html.duckduckgo.com/html/?q=...`) via `urllib`. Parse the response with `html.parser` to extract result titles, URLs, and snippets. No API key required.

Returns a text block of the top N results formatted as:
```
[1] Title
URL: https://...
Snippet: ...
```

Caveats:
- DuckDuckGo rate-limits aggressive scrapers; results are sufficient for occasional captioning use
- A configurable search API endpoint (e.g. Serper, Tavily) can be added in a future settings field if users want more robust search

### Tool 2 — Web Page Fetch

**Definition name:** `web_fetch`

Parameters:
- `url` (string, required) — the URL to fetch

Implementation: Uses `urllib.request.urlopen()` with a browser-like `User-Agent` header. Parse HTML with `html.parser`; strip scripts, styles, and nav elements; return the main text content (capped at ~4000 words to avoid exceeding context).

Input validation:
- Only `http://` and `https://` schemes are allowed
- Reject private/loopback addresses (127.x, 10.x, 192.168.x, etc.) — SSRF mitigation
- Timeout: 15 seconds

Returns the page title + cleaned body text.

### Tool 3 — File Reference

**Definition name:** `read_file`

Parameters:
- `path` (string, required) — local filesystem path

Implementation: `pathlib.Path(path).read_text(encoding='utf-8')`, capped at ~8000 characters.

Input validation:
- Only allow `.txt`, `.md`, `.csv`, `.json` extensions (no binary files)
- Restrict to paths on the same filesystem as the project (no symlink escapes)
- File size limit: 512 KB before truncation

**Note:** Unlike web search (which benefits from the model deciding what to search for), file reference is most naturally handled as **direct context injection** rather than a tool call — the user explicitly picks the file, and we prepend its contents to the system prompt. This makes it work even with models that are not tool-capable. The `read_file` tool definition is provided for tool-capable models that may want to re-fetch it mid-loop; for non-tool-capable models we inject it directly.

Similarly, a user-provided reference URL can be pre-fetched and injected as context, bypassing the tool loop entirely when the model isn't tool-capable.

---

## Phase 3 — Generation Integration & UI

### 3a. Agentic generation loop

**New file:** `backend/llm/tool_loop.py`

The current `generate_caption` methods in each client do a single request→response. Tool-augmented generation needs a multi-turn loop. Rather than duplicating per-client, implement a shared loop that uses the OpenAI-compatible `/v1/chat/completions` format (both backends support it).

Both the `ollama` and `lmstudio` Python SDKs are already in `requirements.txt` and support tool calling. However, the current code uses `urllib` directly for control. For the tool loop, use the `ollama` SDK's `chat()` with `tools=` and the `lmstudio` SDK's equivalent for cleaner integration, or implement the raw HTTP calls for `/v1/chat/completions` to stay dependency-consistent.

Pseudocode:

```python
def generate_with_tools(
    *,
    backend: str,          # "ollama" | "lmstudio"
    model: str,
    messages: list[dict],  # initial system + user messages
    tools_enabled: list[str],  # e.g. ["web_search", "web_fetch"]
    context_files: list[str],  # paths to pre-inject
    context_urls: list[str],   # URLs to pre-fetch and inject
    timeout_seconds: int,
    max_tool_rounds: int = 5,
) -> tuple[str, list[str]]:  # (caption_text, tool_usage_log)
    ...
```

Loop:
1. If `context_files` or `context_urls` provided, fetch/read each and prepend to `messages[0]["content"]` (system message)
2. Build the `tools` array from `tools_enabled`
3. POST to `/v1/chat/completions` with `tools=`
4. If response has `tool_calls`, execute each via `tool_service.execute_tool()`, append assistant + tool messages
5. Loop up to `max_tool_rounds`; break when no tool calls remain
6. Return `choices[0].message.content` as the caption

Safety: if the model loops without producing content (e.g. keeps calling tools), break after `max_tool_rounds` and return whatever content was last produced.

### 3b. New generation route

**File:** `backend/routers/llm.py`

New request model:

```python
class GenerateCaptionWithToolsRequest(BaseModel):
    project_path: str = Field(min_length=1)
    image_id: int
    backend: str = Field(min_length=1)
    model: str = Field(min_length=1)
    extra_instructions: str = ""
    make_active: bool = True
    timeout_seconds: int = Field(default=120, ge=10, le=900)
    tools_enabled: list[str] = []          # ["web_search", "web_fetch", "read_file"]
    context_urls: list[str] = []           # pre-fetch and inject
    context_files: list[str] = []         # pre-read and inject
```

New route: `POST /api/llm/generate-caption-with-tools`

Alternatively, fold these fields into the existing `GenerateCaptionRequest` and `GenerateWithPresetRequest` — simpler if all generation eventually supports tools. Whether to keep a separate endpoint or extend the existing one is a decision to make during implementation.

### 3c. Preset storage for tool preferences

If users want presets that always use web search (e.g. a "research" preset), store tool preferences in the preset record.

**File:** `backend/db/models.py` — add nullable `tools_config` JSON column to `PresetRecord`

**File:** `backend/services/llm_service.py` — include `tools_config` in `create_preset` / `update_preset`

This is optional for the initial implementation; tools can be specified per-generation first.

### 3d. UI changes

The UI work is intentionally deferred until the backend is solid, but the plan is:

**In the Editor tab (single image generation):**
- Below the existing "Extra Instructions" textarea, add a "Context & Tools" collapsible section (collapsed by default)
- Inside:
  - Checkboxes for `web_search` and `web_fetch` (only enabled if the selected model is `tool_capable`)
  - A text input to paste in a reference URL (fetched before generation; works even without tool-capable model)
  - A file path input (or file picker) to specify a local text/markdown reference file

**In the LLM tab (preset management):**
- Same fields available when creating/editing a preset so tool choices persist

**In the Batch tab:**
- Show a summary of which tools are enabled for the batch job
- Per-image tool use (e.g. different URLs per image) is not supported in batch — batch uses the same tool config for all images

**Status message feedback:**
- After generation, show what tools were called, e.g. "Generated caption using web_search (2 calls), web_fetch (1 call)"

---

## Key Design Decisions

### Web search implementation
DuckDuckGo HTML scraping is the zero-configuration default. It is rate-limited for heavy use but fine for occasional caption generation. A future setting could allow the user to configure a search API key (Tavily, Serper, etc.) which would be stored in app settings and passed to the tool service.

### Tool use vs. context injection
| Mechanism | When to use | Requires tool-capable model? |
|---|---|---|
| System prompt injection | User provides URL or file explicitly | No |
| Tool call (`web_search`) | Model decides what to search | Yes |
| Tool call (`web_fetch`) | Model decides to fetch a URL (e.g. from search results) | Yes |

Both mechanisms can be available simultaneously: inject the user's provided context upfront, and also give the model search/fetch tools if it is tool-capable.

### Prompt guidance
Tool-capable models still benefit from explicit instructions. The system prompt for tool-augmented generation should include guidance like:
> "You have access to web search and web fetch tools. Use them if you need additional context about what is depicted in the image before writing the caption."

### Error handling in the tool loop
- If a tool call fails (network error, bad URL, file not found), return an error string as the tool result rather than raising — the model can incorporate that information or ignore it
- If the model produces malformed tool call JSON, log and break the loop with whatever content is available

### SSRF / path traversal safety
- `web_fetch`: block non-HTTP schemes and private IP ranges
- `read_file`: only allow a whitelist of safe extensions; resolve symlinks and check the resolved path is under an allowed root (configurable, defaulting to the user's home directory or the project folder)

---

## File Change Summary

| File | Change |
|---|---|
| `backend/llm/base.py` | Add `tool_capable: bool` to `ModelInfo` |
| `backend/llm/ollama_client.py` | Populate `tool_capable` from `capabilities` |
| `backend/llm/lmstudio_client.py` | Populate `tool_capable` from `trained_for_tool_use` |
| `backend/llm/tool_loop.py` | **New** — agentic multi-turn tool calling loop |
| `backend/routers/llm.py` | Expose `tool_capable`; new generation route |
| `backend/services/tool_service.py` | **New** — web_search, web_fetch, read_file implementations |
| `backend/services/llm_service.py` | Wire tool loop into generation service functions |
| `backend/db/models.py` | Optional: `tools_config` on preset records |
| `frontend/app.js` | Hammer icon helper; tool option state; new API call |
| `frontend/index.html` | Hammer icon in model pickers; Context & Tools UI section |

---

## Order of Work

| Step | Task |
|---|---|
| 1 | Phase 1: detection + hammer icon (self-contained, no behaviour change) |
| 2 | `tool_service.py`: implement and unit-test web_search, web_fetch, read_file in isolation |
| 3 | `tool_loop.py`: implement and test agentic loop with a real tool-capable model |
| 4 | Router + service wiring: new generation endpoint |
| 5 | UI integration (Editor tab context & tools panel) |
| 6 | Extend presets to persist tool choices |
| 7 | Batch tab tool support |
