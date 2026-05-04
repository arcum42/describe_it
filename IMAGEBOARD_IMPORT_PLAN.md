# Imageboard Import Feature Plan

## Overview

Add support for importing images and their tags from external imageboards (e.g., Derpibooru, Danbooru, e621, Twibooru, Tantabus) directly into projects. Tags from the imageboard become captions in the project.

## Goals

- Allow users to search imageboards and import results directly into a project.
- Support multiple imageboard APIs with different authentication/configuration patterns.
- Make API clients extensible and maintainable for future board additions.
- **Store API credentials securely in the database for easy credential management.**
- Preserve the local-first, Python-only runtime experience.
- Keep image downloads efficient and handle pagination gracefully.

## Current Status Snapshot (May 2026)

- Phase 0 through Phase 5 are implemented and in active use.
- Phase 6 test coverage is implemented with service, router, client parsing, duplicate detection, and live-diagnostic coverage.
- Source attribution is implemented as a separate inactive caption (`source:<url>`) instead of polluting the active caption.
- Rating filter UI/API is implemented (`any`, `safe`, `questionable`, `explicit`) with board-specific query formatting.
- Duplicate detection is implemented via SHA-256 hash comparison with import-time skip support.
- e621 total count reporting is fixed for single-tag queries using tag `post_count` lookup.
- Rails query normalization is implemented for parenthetical tags, including multi-word prefixes (for example `apple bloom (mlp)` -> `apple_bloom_(mlp)`).
- Caption rating formatting is normalized to comma-separated tokens (`safe, tag1, tag2`) without brackets.
- Philomena-family rating extraction now falls back to tag scanning when the dedicated rating field is absent.

## Architecture Overview

### Component Layer

```
Frontend (UI)
    ↓
Settings UI: Imageboard Credentials Manager
    ↓
Credentials Service ← → Database (ImageboardCredential table)
    ↓
Imageboard Import Router (/api/imageboard-import)
    ↓
Imageboard Import Service (service layer)
    ↓
Imageboard API Clients (abstract + concrete implementations)
    ↓
Credentials Service (retrieves auth for each client)
    ↓
HTTP Client (requests + retry logic + rate limiting)
    ↓
External imageboard APIs
```

### Key Components

1. **Imageboard Credentials Service** (`backend/services/imageboard_credentials_service.py`)
   - Manage storage and retrieval of API keys/usernames
   - Provide masked summaries for UI display
   - Validate credentials with test API calls
   - Encrypt keys if cryptography available (optional enhancement)

2. **Imageboard Credentials Database Model** (`backend/db/models.py`)
   - `ImageboardCredential` table: board_id, api_key, username, timestamps
   - One row per board; updated when user adds/modifies credentials

3. **Settings UI Extensions** (`frontend/js/imageboard-settings.js`)
   - Credentials editor for all 5 boards
   - Display masked keys and usernames
   - Add/update/delete buttons
   - Links to API key generation instructions per board

4. **Imageboard API Client Abstraction** (`backend/llm/imageboard/`)
   - Abstract base class for all imageboard clients
   - Concrete implementations for each board
   - Common patterns: pagination, search, tag normalization
   - Accept credentials from credentials service

5. **Imageboard Import Service** (`backend/services/imageboard_import_service.py`)
   - Orchestrates searches, previews, and imports
   - Manages metadata/configuration per board
   - Handles image downloads and caption creation

6. **Imageboard Import Router** (`backend/routers/imageboard_import.py`)
   - API endpoints for search, preview, import
   - Request validation
   - Error handling and progress reporting

7. **Frontend UI** (extension to `frontend/app.js` + new module)
   - Search interface per imageboard
   - Preview grid with image count
   - Import count selector
   - Progress indication

5. **Configuration/Registry** (`backend/config.py` extension)
   - Board metadata (base URL, optional auth fields, features)
   - Optional: per-user API keys/credentials in app state

## Detailed Phases

---

## Phase 0: API Credentials Management (Foundation) ✅ COMPLETE

**Goal:** Store and manage imageboard API keys securely before any import operations.

### Database Schema

Add to `backend/db/models.py`:

```python
from sqlalchemy import String, Text, DateTime, func

class ImageboardCredential(Base):
    """Store API keys and credentials for imageboard access."""
    __tablename__ = "imageboard_credentials"
    
    id = Column(Integer, primary_key=True)
    board_id = Column(String(50), unique=True, nullable=False)  # "e621", "derpibooru", etc.
    api_key = Column(Text, nullable=True)  # Encrypted in practice
    username = Column(String(255), nullable=True)  # For boards that need it (e621, Danbooru)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
```

**Security Notes:**
- In production, encrypt `api_key` and `username` fields (use `cryptography` library, optional dependency)
- For MVP: store plaintext (warn user to set restrictive file permissions on database)
- Never log or display full API keys in UI (show last 4 chars only)

### Settings Router Endpoints

Add to `backend/routers/` or extend `backend/routers/projects.py`:

```python
# GET /api/settings/imageboard-credentials
# Response: list of boards with masked keys
[
  {
    "board_id": "e621",
    "display_name": "e621",
    "has_key": true,
    "masked_key": "****1234",
    "username": "my_e621_username",
    "created_at": "2024-01-15T10:00:00Z"
  },
  ...
]

# POST /api/settings/imageboard-credentials/update
# Body:
{
  "board_id": "e621",
  "api_key": "actual_api_key_here",
  "username": "optional_username"
}
# Response: { "success": true, "board_id": "e621" }

# DELETE /api/settings/imageboard-credentials/:board_id
# Response: { "success": true, "deleted": "e621" }

# GET /api/settings/imageboard-boards
# Response: list of available boards with config
[
  {
    "board_id": "e621",
    "display_name": "e621",
    "base_url": "https://e621.net",
    "requires_auth": true,
    "requires_username": true,
    "available_sorts": ["date", "score", ...],
    "supports_galleries": false,
    "supports_pools": false,
    "rate_limit_info": "2 requests/second (hard limit)"
  },
  ...
]
```

### Service Layer

Create `backend/services/imageboard_credentials_service.py`:

```python
class ImageboardCredentialsService:
    """Manage imageboard API credentials."""
    
    def get_credentials(self, board_id: str) -> Optional[dict]:
        """Retrieve unencrypted credentials for a board."""
        # Used internally only; never expose full key to frontend
        
    def get_all_credentials_summary(self) -> list[dict]:
        """Get masked summary of all stored credentials."""
        # For settings display
        
    def save_credentials(self, board_id: str, api_key: str, username: str = None) -> dict:
        """Save or update credentials for a board."""
        # Validate board_id exists
        # Encrypt if crypto available
        # Store in DB
        
    def delete_credentials(self, board_id: str) -> bool:
        """Remove credentials for a board."""
        
    def validate_credentials(self, board_id: str, api_key: str, username: str = None) -> bool:
        """Test credentials by making a small API call."""
        # Call board's API with provided credentials
        # Return True if successful, False if 401/403
```

### Frontend UI (Settings Tab Extension)

Update `frontend/app.js` to include imageboard settings section:

```javascript
// In settings modal
<section id="imageboard-settings">
  <h3>Imageboard API Keys</h3>
  <p>Add API keys to enable importing from imageboards.</p>
  
  <div id="imageboard-credentials-list">
    <!-- Populated by fetch -->
    <div class="credential-row">
      <label>e621</label>
      <input type="text" placeholder="API Key (****1234)" readonly>
      <input type="text" placeholder="Username" value="my_username">
      <button onclick="saveCredential('e621')">Save</button>
      <button onclick="deleteCredential('e621')">Remove</button>
    </div>
    <!-- Repeat for other boards -->
  </div>
  
  <details>
    <summary>How to get API keys</summary>
    <ul>
      <li><strong>e621:</strong> Go to Profile → API Key → Generate</li>
      <li><strong>Danbooru:</strong> Profile → API key → Generate</li>
      <li><strong>Derpibooru:</strong> Account settings → API token (optional for higher limits)</li>
      <li><strong>Tantabus:</strong> Account settings → API token (optional)</li>
      <li><strong>Twibooru:</strong> Account settings → API key (optional)</li>
    </ul>
  </details>
</section>
```

JavaScript handlers:

```javascript
async function saveCredential(boardId) {
  const apiKey = document.getElementById(`${boardId}-key`).value;
  const username = document.getElementById(`${boardId}-username`).value;
  
  const response = await fetch("/api/settings/imageboard-credentials/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      board_id: boardId,
      api_key: apiKey,
      username: username || null
    })
  });
  
  if (response.ok) {
    alert("Credentials saved!");
    refreshCredentialsList();
  } else {
    alert("Failed to save credentials");
  }
}

async function deleteCredential(boardId) {
  if (confirm("Remove credentials for " + boardId + "?")) {
    const response = await fetch(`/api/settings/imageboard-credentials/${boardId}`, {
      method: "DELETE"
    });
    if (response.ok) {
      refreshCredentialsList();
    }
  }
}

async function refreshCredentialsList() {
  const response = await fetch("/api/settings/imageboard-credentials");
  const credentials = await response.json();
  
  // Populate UI with masked keys and usernames
  // Show status: "Configured" / "Not set" per board
}
```

### Integration with Imageboard Clients

Each client retrieves credentials at runtime:

```python
class E621Client(ImageboardClient):
    def __init__(self, credentials_service: ImageboardCredentialsService):
        creds = credentials_service.get_credentials("e621")
        self.api_key = creds.get("api_key") if creds else None
        self.username = creds.get("username") if creds else None
        
        # Use in requests
        self.session.headers.update({
            "Authorization": f"Basic {self._encode_auth()}",
            "User-Agent": f"DescribeIt/1.0 (by {self.username} on e621)"
        })
    
    def _encode_auth(self):
        """Encode username:api_key for Basic auth."""
        if self.username and self.api_key:
            credentials = f"{self.username}:{self.api_key}"
            return base64.b64encode(credentials.encode()).decode()
        return None
```

### Flow

1. **User enters settings:** Clicks "Settings" → "Imageboards" tab
2. **Fetch available boards:** GET `/api/settings/imageboard-boards` → shows all 5 boards with descriptions
3. **View existing credentials:** GET `/api/settings/imageboard-credentials` → shows masked keys, usernames
4. **Add/update credentials:** User enters API key + optional username, clicks "Save" → POST `/api/settings/imageboard-credentials/update`
5. **Validation:** Service validates credentials by making test API call (optional but recommended)
6. **Display feedback:** "✓ Configured" or "⚠ Not set" per board
7. **Delete:** User clicks "Remove" → DELETE endpoint clears credentials
8. **Import time:** When user searches/imports, clients automatically retrieve credentials from service

---

## Phase 1: Abstract Imageboard Client Framework ✅ COMPLETE

**Goal:** Create extensible architecture for imageboard APIs.

### Deliverables

1. **`backend/llm/imageboard/__init__.py`**
   - Module init, re-export main classes

2. **`backend/llm/imageboard/base.py`**
   ```python
   class ImageboardClient(ABC):
       """Abstract base for imageboard API clients."""
       
       # Meta
       board_name: str          # "derpibooru", "danbooru", etc.
       board_display_name: str  # "Derpibooru"
       base_url: str
       supports_galleries: bool = False
       supports_pools: bool = False
       available_sorts: list[str]  # e.g., ["score", "wilson_score", "upvotes", ...]
       
       # Optional config
       optional_auth_fields: dict[str, str]  # {"api_key": "...", "username": "..."}
       
       # Abstract methods
       @abstractmethod
       async def search(
           self,
           query: str,
           sort_by: str,
           sort_direction: str = "desc",
           page: int = 1,
           per_page: int = 20,
           **kwargs,
       ) -> SearchResult:
           """Execute search query. sort_by must be in available_sorts."""
       
       @abstractmethod
       async def get_gallery_or_pool(self, gallery_id: int) -> SearchResult:
           """Fetch images from a specific gallery/pool."""
       
       @abstractmethod
       def normalize_tags(self, raw_tags: list[str]) -> list[str]:
           """Normalize board-specific tags (e.g., remove aliases)."""
       
       @abstractmethod
       async def fetch_image_bytes(self, image_url: str) -> bytes:
           """Download image data."""
   
   @dataclass
   class SearchResult:
       """Standardized search result."""
       images: list[ImageboardImage]
       total_count: int  # or estimated if not provided by API
       page: int
       has_next_page: bool
   
   @dataclass
   class ImageboardImage:
       """Represents one image from search result."""
       id: str | int  # board-specific ID
       title: str  # filename or title hint
       image_url: str
       source_url: str | None  # link back to board page
       tags: list[str]
       rating: str | None  # e.g., "safe", "suggestive", "explicit" if available
   ```

3. **`backend/llm/imageboard/http_client.py`**
   - Shared HTTP utilities:
     - `requests` Session with connection pooling
     - Configurable User-Agent per client
     - Retry logic with exponential backoff
     - Rate limiting (per-board delays, token buckets, or similar)
     - Timeout defaults (30 sec recommended, adjustable per board)
   - Response parsing:
     - JSON handling with error recovery
     - Binary image download with content-length validation
     - Special handling for Derpibooru 501 challenges (pause 5+ sec)
     - Special handling for e621/Danbooru User-Agent enforcement
   - Rate limit header parsing:
     - Danbooru `x-rate-limit` (JSON)
     - Twibooru `X-RL`, `X-RL-Remaining`, `X-RL-Reset`
     - Proactive throttling based on remaining quota
   - Board-specific delays:
     - e621: min 1 sec between requests (safe)
     - Danbooru: min 100 ms between requests (10/sec global)
     - Derpibooru/Tantabus: min 250 ms between requests (20-30 per 5-10 sec)
     - Twibooru: min 6 sec between search requests (10/minute limit)

### Considerations

- Use `requests` library (already available or add to `requirements-optional.txt`).
- Consider `httpx` or `aiohttp` if async is needed; prefer sync for now to keep it simple.
- Include reasonable timeouts and retry logic.
- Add mock/stub client for testing without hitting real APIs.

---

## Phase 2: Core Imageboard API Clients ✅ COMPLETE

**Goal:** Implement clients for the initial set of boards (Derpibooru, Danbooru, e621, Twibooru, Tantabus).

### Deliverables

1. **`backend/llm/imageboard/derpibooru.py`** (Derpibooru client)
   - API: https://derpibooru.org/pages/api
   - Search endpoint: `GET /api/v1/search/images`
   - Query params: `q` (search terms, supports negation: `-animated`), `sf` (sort field), `sd` (sort direction: "desc", "asc"), `page`
   - **Supported sort fields:** `score`, `wilson_score`, `upvotes`, `downvotes`, `first_seen_at`, `random:<seed>`, `faves`, `tag_count`, `relevance` (default)
   - Optional: API key for higher rate limits
   - Tags in response: `tags` (list of tag objects with name, slug)
   - **Specifics:**
     - Normalize tags (use slug if available, lowercase)
     - Handle ratings: `rating` field is "safe", "suggestive", "explicit"
     - For random sort, allow user to optionally specify seed; generate random seed if not provided

2. **`backend/llm/imageboard/danbooru.py`** (Danbooru client)
   - API: https://danbooru.donmai.us/wiki_pages/help%3Aapi
   - Search endpoint: `GET /posts.json`
   - Query params: `tags` (space-separated, supports negation: `-animated`), `limit` (posts per page), `page`
   - Optional: login/API key for full access
   - Tags in response: `tag_string_*` fields (character, artist, general, meta, copyright)
   - **Supported sort fields:** Verify via API docs; likely similar to Derpibooru (score, date, popularity, etc.). Actual sort param may differ.
   - **Specifics:**
     - Combine all tag types into single list
     - Handle rating: `rating` field ("s", "q", "e")
     - Support sort: `order` param (e.g., "date", "score", "popular", "rank"); document exact options

3. **`backend/llm/imageboard/twibooru.py`** (Twibooru client)
   - API: https://twibooru.org/pages/api (Danbooru fork—likely identical API to Danbooru with possibly different database)
   - Same as Danbooru for sort options and parameters
   - Verify endpoint responses and tag structure match Danbooru

4. **`backend/llm/imageboard/e621.py`** (e621 client)
   - API: https://e621.net/help/api
   - Search endpoint: `GET /posts.json`
   - Query params: `tags` (space-separated), `limit`, `page`
   - User-Agent: **Required** (include username in agent)
   - Tags in response: `tags` object with categories (general, species, character, artist, etc.)
   - **Specifics:**
     - Combine tags across categories
     - Rating: `rating` field ("s", "q", "e")

5. **`backend/llm/imageboard/tantabus.py`** (Tantabus client)
   - API: https://tantabus.ai/pages/api
   - Likely similar to Danbooru
   - Verify endpoints and response format

## API Similarity Matrix & Quick Reference

| Aspect | Derpibooru | Tantabus | Twibooru | Danbooru | e621 |
|--------|-----------|----------|----------|----------|------|
| **Framework** | Philomena | Philomena (Derpibooru fork) | Booru-on-Rails | Rails | Danbooru fork (Rails) |
| **Search endpoint** | `/api/v1/json/search/images` | `/api/v1/json/search/images` | `/api/v3/search/posts` | `/posts.json` | `/posts.json` |
| **Query syntax** | Comma-separated, negation | Comma-separated, negation | Comma-separated, negation | Space-separated, negation | Space-separated, negation |
| **Response format** | `{images: [...]}` | `{images: [...]}` | `{posts: [...]}` | `[{...}]` array | `{posts: [{...}]}` |
| **Tag structure** | `tags: [str]` flat | `tags: [str]` flat | `tags: [str]` flat | `tag_string_*` fields | `tags: {category: [str]}` |
| **Pagination** | `page`, `per_page` | `page`, `per_page` | `page`, `per_page` | `page`, `limit` | `page`, `limit` |
| **Total count** | ✅ `total` field | ✅ `total` field | ❌ Must paginate all | ❌ Must paginate all | ❌ Must paginate all |
| **Image URL** | `representations.full` | `representations.full` | `representations.full` | `file.url` (need fetch) | `file.url` (need fetch) |
| **Auth required** | ❌ Optional | ❌ Optional | ❌ Optional | ✅ Yes (API key) | ✅ Yes (API key) |
| **User-Agent req** | ❌ Optional | ❌ Optional | ❌ Optional | ✅ CRITICAL | ✅ CRITICAL |
| **Rate limit** | 20/10s (search) | ~20/10s (est.) | 10/min (search) | 10/s (global) | 2/s (hard) |
| **Challenges** | 501 block → 15min | Likely same | Very slow | Requires UA | Requires UA |

### Board-by-Board Commonalities

**Derpibooru & Tantabus (Nearly identical):**
- Same Philomena framework
- Nearly identical API endpoints and response structure
- Same sort fields
- Same tag handling (flat list)
- Same rate limits (~20/10s)
- Tantabus is newer fork; may have slight variations—test both to verify parity
- Both support cross-linking via `source_urls` and/or `locations`

**Twibooru (Philomena but modified):**
- Similar to Derpibooru in structure, but:
  - Uses `/api/v3/` instead of `/api/v1/`
  - Response uses `posts` key, not `images`
  - Includes `locations` field for cross-linking (e.g., `derpibooru`, `ponybooru`)
  - Rate limits are much stricter (10/min for search)
  - Much smaller user base—fewer conflicts but also less data

**Danbooru & e621 (Rails-based Booru):**
- Very similar to each other (e621 is Danbooru fork)
- Different API structure than Philomena boards
- Tags split across multiple `tag_string_*` fields (must combine)
- No `total` count; must paginate to find out how many results exist
- Both require authentication AND custom User-Agent
- Danbooru: 10 req/sec global; e621: 2 req/sec hard limit
- e621 stricter on User-Agent enforcement

### Shared Implementation Strategy

1. **Base client pattern:**
   - Parse common search params (query, sort, page)
   - Call board-specific endpoint
   - Normalize response to `SearchResult` + `ImageboardImage`
   - Handle pagination transparently

2. **Tag extraction helper:**
   ```python
   def extract_tags(response_data: dict, board_type: str) -> list[str]:
       if board_type in ("derpibooru", "tantabus", "twibooru"):
           return response_data.get("tags", [])
       elif board_type in ("danbooru"):
           # Combine all tag fields
           tags = []
           for key in ("tag_string_general", "tag_string_character", ...):
               if key in response_data:
                   tags.extend(response_data[key].split())
           return tags
       elif board_type == "e621":
           # Combine tag categories
           all_tags = []
           for category in response_data.get("tags", {}).values():
               all_tags.extend(category)
           return all_tags
   ```

3. **Image extraction helper:**
   ```python
   def extract_image_url(response_data: dict, board_type: str) -> str:
       if board_type in ("derpibooru", "tantabus", "twibooru"):
           return response_data["representations"]["full"]
       elif board_type in ("danbooru", "e621"):
           # Full-resolution URL may not be in search response
           # Use sample or require additional fetch
           return response_data["sample"]["url"]  # or implementation fetch
   ```

---

### Tantabus Special Notes (Derpibooru Fork)

**Relationship to Derpibooru:**
- Tantabus is a recent fork of Derpibooru (within last few years)
- Runs the same Philomena framework with minimal modifications
- API is functionally identical to Derpibooru v1
- Same rate limits, auth patterns, response structures expected
- Main difference: **Content focus** (AI-generated art emphasis vs. fan art)

**Implementation Strategy for Tantabus:**
- Can likely reuse most/all of Derpibooru client code
- Verify endpoints and response structure match (use `/api/v1/json/search/images`)
- Test sort fields (`sf` param) with Derpibooru-documented list first
- If Tantabus diverges, it will likely be in:
  - Additional sort options specific to AI content
  - Different tag categories or implications
  - Possibly different rate limits (if they've tuned the cluster)

**Testing Approach:**
1. Implement Derpibooru client fully
2. Copy to Tantabus client, change `base_url` and `board_name`
3. Run integration tests against test queries on both boards
4. Document any response differences found
5. Only add Tantabus-specific code if divergence confirmed

**Potential Divergences to Watch:**
- Sort field `random:<seed>` — verify still supported
- Tag namespace handling — Tantabus may use different categories
- Rate limits — Tantabus infrastructure may differ
- API versioning — ensure `/api/v1/` is correct (not `/api/v2/`, etc.)
- Feature flags — new Derpibooru features may not be on Tantabus yet

**Tag Normalization (Critical for consistent captions):**

Boards use different tag structures and naming conventions. When extracting tags for captions, normalize them:

```python
def normalize_tags(raw_tags: list[str], board_id: str) -> list[str]:
    """
    Normalize tags across boards for consistent caption format.
    
    - Remove redundant/implied tags
    - Handle aliases (if available from API)
    - Lowercase all tags
    - Remove special formatting
    - Remove ratings (already captured separately)
    """
    normalized = []
    
    # Board-specific skip lists (ratings, meta, implied tags)
    skip_tags = {
        "safe", "suggestive", "explicit", "spoiler",  # Ratings
        "explicit content", "source needed", "artist needed",  # Meta
    }
    
    for tag in raw_tags:
        tag_clean = tag.strip().lower()
        
        if tag_clean in skip_tags:
            continue
        
        # Remove namespace prefixes if desired (e.g., "artist:john" -> "john" or keep as-is)
        if ":" in tag_clean:
            # Decide whether to keep namespace or extract name only
            # For now, keep as-is for fidelity
            pass
        
        normalized.append(tag_clean)
    
    return sorted(list(set(normalized)))  # Deduplicate and sort
```

**Tag Field Mapping (What becomes caption text):**

For each board, combine tags + metadata into caption:

```python
# Derpibooru/Tantabus/Twibooru
caption = ", ".join(normalize_tags(image["tags"]))

# Danbooru/e621 (must combine categories)
all_tags = []
for category_key in image.get("tags", {}).keys():
    all_tags.extend(image["tags"][category_key])
caption = ", ".join(normalize_tags(all_tags))

# Optional: Include metadata
caption += f" | Rating: {image['rating']}"
if image.get("animated"):
    caption += " | Animated"
```

**Pagination Strategies (Critical for collecting all results):**

Different boards paginate differently:

```python
# Derpibooru / Tantabus / Twibooru: page + per_page
# Can get total count upfront to show progress
results = []
page = 1
per_page = 50
total_count = None

while True:
    response = GET f"...?page={page}&per_page={per_page}&q=..."
    if not response:
        break
    
    if total_count is None:
        total_count = response["total"]  # Know goal upfront!
    
    results.extend(response["images"])  # or "posts"
    
    if len(response["images"]) < per_page:
        break  # Last page
    
    page += 1
    time.sleep(rate_delay)


# Danbooru / e621: page + limit (or ID-based pagination)
# Must paginate blindly; no total count in response
results = []
page = 1
limit = 200

while True:
    response = GET f"...?page={page}&limit={limit}&tags=..."
    if not response:
        break
    
    results.extend(response)  # Danbooru returns array directly
    
    if len(response) < limit:
        break  # Last page
    
    page += 1
    time.sleep(rate_delay)

# Alternative: ID-based pagination (faster, no total count)
# results = GET f"...?page=a123456&limit={limit}"
# Then use ID 123456 to fetch results AFTER that ID
```

---

## Critical Implementation Gotchas

**Search Result Size:**
- Small searches (1-10 results): Fast on all boards
- Medium searches (100-1000 results): Manageable; watch rate limits
- Large searches (10k+ results): **Very slow** on Twibooru (10/min limit = hours!)
- Huge searches (100k+ results): Consider Derpibooru/Danbooru database exports instead

**Memory Usage:**
- Collecting all results in memory can exhaust RAM for large imports
- **Solution:** Stream results, import in batches as pages arrive
- Don't fetch all pages before starting DB inserts

**Image Download Failures:**
- Some images may be deleted/hidden after search returns them
- Handle 404 gracefully; continue with next image
- Log failed image IDs for user reporting

**Tag Accuracy:**
- Tags may be incomplete or aliased differently per board
- Consider tag alias resolution (if board API provides it)
- Derpibooru/Danbooru support `implied_tags` field—consider including

**Query Syntax Pitfalls:**
- Derpibooru/Tantabus: comma-separated (`tag1, tag2, -excluded`)
- Danbooru/e621: space-separated (`tag1 tag2 -excluded`)
- Twibooru: unclear (test both!)
- Negation works on all (`-tag` or `NOT tag`)
- Wildcards: `tag*` on some boards

---

## API Endpoint & Response Structure Reference

**Derpibooru & Tantabus (Philomena-based, nearly identical):**

```
GET /api/v1/json/search/images
  Parameters:
    q: "tag1, tag2, -excluded_tag"  # Comma-separated; supports negation
    sf: "score" / "wilson_score" / "upvotes" / "downvotes" / "first_seen_at" / "random:SEED" / "faves" / "tag_count"
    sd: "asc" | "desc"
    page: 1..N
    per_page: 1..50 (default 25)
    key: "api_key" (optional)
    filter_id: integer (optional, for content filtering)

  Response: 
  {
    "images": [
      {
        "id": 123456,
        "name": "filename.png",
        "description": "...",
        "tags": ["tag1", "tag2", ...],  // Flat list of tag names
        "tag_ids": [456, 789, ...],     // Corresponding tag IDs
        "width": 1024,
        "height": 768,
        "format": "png",                // "gif", "jpg", "webm", etc.
        "mime_type": "image/png",
        "size": 123456,
        "upvotes": 42,
        "downvotes": 2,
        "score": 40,
        "wilson_score": 0.92,
        "faves": 10,
        "tag_count": 25,
        "created_at": "2024-01-15T10:30:00.000Z",
        "first_seen_at": "2024-01-15T10:30:00.000Z",
        "updated_at": "2024-01-20T15:45:00.000Z",
        "rating": "safe" | "suggestive" | "explicit",
        "animated": false,
        "source_urls": ["https://example.com/original"],
        "view_url": "https://derpibooru.org/images/123456?q=tag1",
        "representations": {
          "thumb_tiny": "https://cdn.../thumb_tiny.jpg",
          "thumb_small": "https://cdn.../thumb_small.jpg",
          "thumb": "https://cdn.../thumb.jpg",
          "small": "https://cdn.../small.jpg",
          "medium": "https://cdn.../medium.jpg",
          "large": "https://cdn.../large.jpg",
          "tall": "https://cdn.../tall.jpg",
          "full": "https://cdn.../full.jpg"  // Full resolution
        }
      },
      ...
    ],
    "total": 12345,        // Total matching images
  }
```

**Danbooru (Rails-based):**

```
GET /posts.json
  Parameters:
    tags: "tag1 tag2 -excluded_tag"  // Space-separated; supports negation
    limit: 1..200 (default varies)
    page: 1..N  (or b<id>, a<id> for before/after pagination)
    order: "date" | "score" | "popularity" | "rank" | "custom"
    login: "username" (optional)
    api_key: "key" (optional)

  Response:
  [
    {
      "id": 123456,
      "created_at": "2024-01-15T10:30:00.000Z",
      "updated_at": "2024-01-20T15:45:00.000Z",
      "file": {
        "width": 1024,
        "height": 768,
        "ext": "png",
        "size": 123456,
        "md5": "abc123..."
      },
      "preview": {
        "width": 300,
        "height": 225,
        "url": "https://cdn.../preview.jpg"
      },
      "sample": {
        "has": true,
        "height": 600,
        "width": 800,
        "url": "https://cdn.../sample.jpg"
      },
      "source": "https://example.com/original",
      "rating": "s" | "q" | "e",  // safe, questionable, explicit
      "tag_string": "tag1 tag2 tag3",           // All tags as string
      "tag_string_general": "tag1 tag3",        // General tags
      "tag_string_character": "character1",     // Character tags
      "tag_string_copyright": "series",         // Series/copyright tags
      "tag_string_artist": "artist_name",       // Artist tags
      "tag_string_meta": "meta_tag",            // Meta tags
      "tags": ["tag1", "tag2", ...],            // Flat list (synthesized from above)
      "up_score": 42,
      "down_score": 2,
      "score": 40,
      "comment_count": 5,
      "fav_count": 10
    },
    ...
  ]
```

**e621 (Danbooru fork):**

```
GET /posts.json
  Parameters:
    tags: "tag1 tag2 -excluded_tag"  // Space-separated; supports negation
    limit: 1..320 (default 75)
    page: 1..N
    order: "date" | "score" | "popularity" | "rank"
    login: "username"               // Required
    api_key: "key"                  // Required
    (or Basic auth)

  Response:
  {
    "posts": [
      {
        "id": 123456,
        "created_at": {
          "json_class": "Time",
          "s": 1705316400,
          "n": 0
        },
        "updated_at": { ... },
        "file": {
          "width": 1024,
          "height": 768,
          "ext": "png",
          "size": 123456,
          "md5": "abc123...",
          "sha1": "def456...",
          "sha256": "ghi789..."
        },
        "preview": {
          "width": 150,
          "height": 112,
          "url": "https://cdn.../preview.jpg"
        },
        "sample": {
          "has": true,
          "height": 600,
          "width": 800,
          "url": "https://cdn.../sample.jpg",
          "alternates": { ... }
        },
        "score": {
          "up": 42,
          "down": 2,
          "total": 40
        },
        "tags": {
          "general": ["tag1", "tag2"],
          "species": ["canine"],
          "character": ["character1"],
          "copyright": ["series"],
          "artist": ["artist_name"],
          "lore": ["lore_tag"],
          "invalid": []
        },
        "locked_tags": [],
        "change_seq": 999999,
        "flags": {
          "pending": false,
          "flagged": false,
          "note_locked": false,
          "status_locked": false,
          "rating_locked": false,
          "comment_disabled": false
        },
        "rating": "s" | "q" | "e",
        "fav_count": 10,
        "sources": ["https://example.com/original"],
        "pools": [12345],
        "relationships": { ... },
        "approver_id": null,
        "uploader_id": 789,
        "description": "...",
        "comment_count": 5,
        "is_favorited": false
      },
      ...
    ]
  }
```

**Twibooru (Philomena fork with modifications):**

```
GET /api/v3/search/posts  (note: "posts" not "images")
  Parameters:
    q: "tag1, tag2, -excluded_tag"  // Comma-separated (or space?)
    sf: "score" (similar sort fields to Derpibooru)
    sd: "asc" | "desc"
    page: 1..N
    per_page: 1..50 (default 15)
    key: "api_key" (optional)
    filter_id: integer (optional)

  Response:
  {
    "posts": [
      {
        "id": 123456,
        "created_at": "2024-01-15T10:30:00.000Z",
        "updated_at": "2024-01-20T15:45:00.000Z",
        "media_type": "image",  // or "paste"
        "file": {
          "width": 1024,
          "height": 768,
          "ext": "png",
          "mime_type": "image/png",
          "name": "filename.png",
          "sha512_hash": "abc123...",
          "orig_sha512_hash": "def456...",
          "size": 123456
        },
        "format": "png",
        "animated": false,
        "duration": 0.04,
        "tags": ["tag1", "tag2", ...],  // Flat list
        "tag_ids": [456, 789, ...],
        "source_url": "https://example.com/original",
        "description": "...",
        "upvotes": 42,
        "downvotes": 2,
        "score": 40,
        "faves": 10,
        "comment_count": 5,
        "rating": "safe" | "suggestive" | "explicit",
        "deletion_reason": null,
        "hidden_from_users": false,
        "locations": [
          {
            "location": "derpibooru",
            "url_at_location": "https://derpibooru.org/images/999",
            "id_at_location": 999
          }
        ],
        "view_url": "https://twibooru.org/posts/123456",
        "representations": {
          "thumb_tiny": "...",
          "thumb_small": "...",
          "thumb": "...",
          "small": "...",
          "medium": "...",
          "large": "...",
          "tall": "...",
          "full": "..."
        }
      },
      ...
    ]
  }
```

### Considerations

- Each client handles board-specific quirks (auth, tag structure, sort options).
- Standardize all responses through `SearchResult` and `ImageboardImage` dataclasses.
- Document rate limits per board (if any).
- Add error handling for auth failures, 404s, malformed responses.
- **Random sort special case:** Derpibooru's `random:<seed>` format allows reproducible randomization. Either:
  - Let user optionally input a seed for reproducible results, or
  - Auto-generate a new seed on each search (simpler UX)

**Tag Extraction Patterns:**

- **Derpibooru/Tantabus:** `response["images"][i]["tags"]` → flat list of strings
- **Danbooru:** Combine `tag_string_*` fields or split `tag_string` by spaces
- **e621:** Combine all categories: `tags["general"] + tags["character"] + tags["species"] + ...`
- **Twibooru:** `response["posts"][i]["tags"]` → flat list of strings

**Image URL Extraction:**

- **Derpibooru/Tantabus/Twibooru:** Use `representations["full"]` for high-res, or `view_url` for web link
- **Danbooru/e621:** Use `file.url` or `sample.url` (available in full response if you fetch individual post)
- All: Check `animated` flag before displaying; animated content has `webm` or `mp4` format

**Pagination:**

- **Derpibooru/Tantabus/Twibooru:** `page` and `per_page` params; iterate `page` from 1 to until results < `per_page`
- **Danbooru/e621:** `page` param (or before/after ID pagination); iterate until results < `limit`
- **Total count:** Derpibooru provides `"total"` field; others require fetching all pages to know total

**Critical Implementation Details:**

- **User-Agent enforcement (e621, Danbooru):** Both strictly reject default/browser user-agents. Implement configuration during client init:
  ```python
  class E621Client:
      def __init__(self, username: str):
          self.user_agent = f"DescribeIt/1.0 (by {username} on e621)"
  ```

- **Derpibooru 501 Challenge:** Implement special handler:
  ```python
  def handle_response(response):
      if response.status_code == 501 and response.headers['content-type'] == 'text/html':
          # Challenge page returned; back off for 5+ seconds
          time.sleep(5)
          return None  # Retry logic at call site
      elif response.status_code == 500:
          # Likely IP blocked for 15 minutes; abort or queue for later
          return None
  ```

- **Rate limit headers:** Parse and respect them proactively to avoid hitting hard limits:
  - Danbooru: check `x-rate-limit` JSON header before each request
  - Twibooru: check `X-RL-Remaining` to decide if sleeping needed

- **Configuration:** Allow app to store per-board settings in `backend/config.py`:
  ```python
  IMAGEBOARD_CONFIG = {
      "e621": {
          "username_required": True,  # For User-Agent
          "rate_delay_sec": 1.0,
          ...
      },
      ...
  }
  ```

---

## API-Specific Implementation Notes

### e621.net

**Rate Limits:**
- Hard limit: 2 requests per second
- **Target: ≤1 request/second sustained** (best practice)
- Exceeding triggers 503 Service Unavailable or 429 Ratelimited

**User-Agent (CRITICAL - REQUIRED):**
- **Must** include custom, descriptive User-Agent
- Format: `ProjectName/1.0 (by username_on_e621)` 
- **Must NOT impersonate browser** or use library defaults
- Can use `_client` URL parameter as fallback if headers unavailable
- Failure to set proper User-Agent results in 403 Forbidden

**Authentication:**
- API key required (per-user, generated in account settings)
- Use Basic auth: `Authorization: Basic base64(username:api_key)`
- Or query params: `?login=username&api_key=key`

**Special Handling:**
- Database exports available at `/db_export/` for bulk data (preferred for large imports)
- Graceful backoff on 503/429 errors
- CORS supported for GET/POST only

**Challenges:**
- Strict user-agent enforcement
- Hard rate limit enforcement
- Requires API key setup

---

### Derpibooru

**Rate Limits:**
- Normal requests: **30 per 5 seconds** (~6/sec)
- API search paths: **20 per 10 seconds** (~2/sec)
- **Challenge mechanism:** Site returns 501 (HTML) if overall load exceeds limits
  - On 501: Must back off **5+ seconds** before retrying
  - Continued requests after 501: Returns 500, IP blocked for **15 minutes**
  - Each request during block resets the 15-minute timer

**User-Agent:**
- Not explicitly required but recommended for identification

**Authentication:**
- Optional API key for higher rate limits
- Found in account settings
- Query param: `?key=api_key`

**Special Handling:**
- Graceful backoff with exponential delay on errors
- Respect `Cache-Control` headers
- Must credit artist and link source URL
- https required on all URLs

**Challenges:**
- Middleware challenge pages (501 responses) require special handling
- 15-minute IP blocking is aggressive—must respect backoff
- Easy to trigger if search results are large (expensive queries)

---

### Tantabus

**Rate Limits:**
- Not explicitly documented (likely same as Derpibooru, same codebase)
- Assume similar pattern: ~20-30 requests per 5-10 seconds

**User-Agent:**
- Not explicitly required

**Authentication:**
- Optional API key
- Query param: `?key=api_key`

**Special Handling:**
- Likely similar to Derpibooru (Philomena-based)
- Smaller user base = potentially fewer conflicts, but test carefully
- Support for "AI content" tags (generator:* tags) vs traditional boorus

**Challenges:**
- Less mature than Derpibooru; test thoroughly
- May have fewer documented edge cases

---

### Danbooru

**Rate Limits:**
- Global read limit: **10 requests per second**
- Update limits: 1/sec (Basic) or 4/sec (Gold+)
- Each endpoint has burst pool (check `x-rate-limit` header)
- Burst pool recharge depends on endpoint
- Returns 429 when throttled

**User-Agent (REQUIRED):**
- **Must** provide descriptive User-Agent
- Format: `YourBotName/1.0 (your-danbooru-username)`
- **Must NOT impersonate browser or use library defaults**

**Authentication:**
- API key required (generated in user profile)
- Use Basic auth: `curl -u "username:api_key" https://danbooru.donmai.us/...`
- Or query params: `?login=username&api_key=key`

**Special Handling:**
- Test site available: `testbooru.donmai.us` (use for development/testing)
- Supports XML or JSON responses (prefer JSON)
- `x-rate-limit` header contains burst pool info (valuable for optimization)
- Query parameters support ranges and wildcards

**Challenges:**
- User-agent enforcement similar to e621
- 10 req/sec global limit is relatively low for large result sets
- Pagination limit (can't go beyond certain page depths)
- API key setup required upfront

---

### Twibooru

**Rate Limits:**
- Endpoint-specific (returned in headers: `X-RL`, `X-RL-Remaining`, `X-RL-Reset`):
  - `/api/v3/search/posts`: **10 per minute** (~0.17/sec)
  - `/api/v3/search/tags`: **60 per minute** (~1/sec)
  - `/api/v3/posts/:id`: **60 per minute** (~1/sec)
  - `/api/v3/posts/:id/comments`: **60 per minute** (~1/sec)
- Returns 429 Too Many Requests when exceeded

**User-Agent:**
- Not explicitly required

**Authentication:**
- Optional API key for authorized access
- Query param: `?key=api_key`

**Special Handling:**
- Supports cross-post linking (via `locations` field): derpibooru, ponybooru, rainbooru, ponerpics, lyrabooru, manebooru, tantabus
- oEmbed support for embedding
- Smaller, more niche booru—good for testing

**Challenges:**
- **Lowest rate limits** (~10 search req/min is very conservative)
- Means importing large result sets will be slow
- Need explicit rate limiting to avoid 429s

---

## Sort Options Reference

**Derpibooru** (likely shared by Twibooru/Tantabus):
- `score` – Overall engagement score
- `wilson_score` – Wilson score (Bayesian rating)
- `upvotes` – Total upvotes
- `downvotes` – Total downvotes  
- `first_seen_at` – Upload/first seen date
- `random:<seed>` – Randomized (seed-based for reproducibility)
- `faves` – Favorite count
- `tag_count` – Number of tags
- `relevance` – Relevance to query (default)

**Danbooru/Twibooru** (verify `order` param values):
- Likely supports: `date`, `score`, `popularity`, `rank`, etc.
- Use board-specific documentation to confirm exact field names

**e621** (verify via API):
- Likely similar to Danbooru with appropriate variations
- Document actual sort field names

---

## Phase 3: Imageboard Import Service ✅ COMPLETE

**Goal:** Create service layer to orchestrate searches, previews, and downloads.

### Deliverables

1. **`backend/services/imageboard_import_service.py`**
   ```python
   class ImageboardImportService:
       def __init__(self):
           self.clients = {
               "derpibooru": DerpibooruClient(...),
               "danbooru": DanbooruClient(...),
               "e621": E621Client(...),
               "twibooru": TwibooruClient(...),
               "tantabus": TantabusClient(...),
           }
           self.download_cache = {}  # Optional in-memory cache for preview images
   
       def get_available_boards(self) -> list[dict[str, str]]:
           """Return list of available boards with metadata."""
           return [
               {
                   "board_id": client.board_name,
                   "display_name": client.board_display_name,
                   "supports_galleries": client.supports_galleries,
                   "supports_pools": client.supports_pools,
                   "available_sorts": client.available_sorts,
                   "optional_auth_fields": client.optional_auth_fields,
               }
               for client in self.clients.values()
           ]
   
       async def search_board(
           self,
           board_id: str,
           query: str,
           sort_by: str,
           sort_direction: str = "desc",
           page: int = 1,
           per_page: int = 20,
           auth_config: dict | None = None,
       ) -> SearchResult:
           """Search a board and return results."""
           # Validate board_id, resolve client, pass auth_config, call client.search()
       
       async def get_preview_images(
           self,
           board_id: str,
           search_result: SearchResult,
           max_preview: int = 5,
       ) -> list[dict]:
           """Get small preview data (thumbnail URLs, counts) without downloading full images."""
           # Return subset of images with minimal data for UI display
       
       async def import_from_board(
           self,
           project_path: str,
           board_id: str,
           query: str,
           sort_by: str,
           sort_direction: str,
           num_to_import: int,
           auth_config: dict | None = None,
       ) -> ImportResult:
           """Search board, download images, and import into project."""
   
       async def import_gallery_or_pool(
           self,
           project_path: str,
           board_id: str,
           gallery_id: int,
           num_to_import: int,
           auth_config: dict | None = None,
       ) -> ImportResult:
           """Import from a specific gallery/pool."""
   ```

2. **Import result dataclass** (in service module)
   ```python
   @dataclass
   class ImageboardImportResult:
       project_path: str
       board_id: str
       search_query: str
       imported_images: int
       failed_images: int
       total_images_in_project: int
       errors: list[str]  # any download/import errors
   ```

3. **Integration with existing import_service.py**
   - Create new internal helper function (e.g., `_import_imageboard_image_record`) mirroring `_import_image_record`.
   - Reuse image record creation logic but with imageboard-sourced data.

### Considerations

- Use async/await for HTTP calls (consider `asyncio` + `aiohttp` or stick with sync `requests` in a thread pool).
- Implement pagination loop to collect all images across pages if user requests more than one page.
- Cache downloaded image bytes temporarily (in-memory or temp file).
- Store a reference/URL to the source imageboard page in captions or image metadata (optional).
- Handle partial failures gracefully (some downloads fail, others succeed).

---

## Phase 4: Imageboard Import Router ✅ COMPLETE

**Goal:** Expose imageboard import via REST API.

### Deliverables

1. **`backend/routers/imageboard_import.py`**
   ```python
   router = APIRouter(prefix="/api/imageboard-import", tags=["imageboard-import"])
   
   class GetBoardsResponse(BaseModel):
       boards: list[dict]  # Each dict includes board_id, display_name, supports_galleries, supports_pools, available_sorts, optional_auth
   
   class SearchBoardRequest(BaseModel):
       board_id: str
       query: str
       sort_by: str = "relevance"  # Validated against board's available_sorts
       sort_direction: str = Field(default="desc", pattern="^(asc|desc)$")
       page: int = Field(default=1, ge=1)
       per_page: int = Field(default=20, ge=1, le=100)
       auth_config: dict | None = None  # e.g., {"api_key": "..."}
       
       @field_validator("sort_by")
       @classmethod
       def validate_sort_by(cls, v: str, info: ValidationInfo) -> str:
           """Validate sort_by against board's available_sorts."""
           # Get board_id from context and check if sort_by is in available_sorts
           # Raise ValueError if not valid for this board
   
   class SearchBoardResponse(BaseModel):
       images: list[dict]  # preview data
       total_count: int
       page: int
       has_next_page: bool
   
   class ImportBoardRequest(BaseModel):
       project_path: str
       board_id: str
       query: str
       sort_by: str = "relevance"
       sort_direction: str = Field(default="desc", pattern="^(asc|desc)$")
       num_to_import: int = Field(ge=1, le=1000)
       auth_config: dict | None = None
   
   class ImportGalleryRequest(BaseModel):
       project_path: str
       board_id: str
       gallery_id: int
       num_to_import: int = Field(ge=1, le=1000)
       auth_config: dict | None = None
   
   # Endpoints
   @router.get("/boards", response_model=GetBoardsResponse)
   async def get_available_boards():
       """List available imageboard sources."""
   
   @router.post("/search", response_model=SearchBoardResponse)
   async def search_board(req: SearchBoardRequest):
       """Preview search results without importing."""
   
   @router.post("/import", response_model=dict)
   async def import_from_board(req: ImportBoardRequest):
       """Search and import images into project."""
   
   @router.post("/import-gallery", response_model=dict)
   async def import_gallery(req: ImportGalleryRequest):
       """Import from a gallery or pool."""
   ```

2. **Registration in main router** (`backend/main.py`)
   - Include imageboard router in app initialization

### Considerations

- Validate `project_path` exists and is a valid project database.
- Stream progress for long imports (optional: WebSocket or Server-Sent Events for real-time feedback).
- Timeout protection (set max timeout for external API calls).

---

## Phase 5: Frontend UI Components ✅ COMPLETE

**Goal:** Build UI for searching and importing from imageboards.

### Deliverables

1. **New module: `frontend/js/imageboard-import.js`**
   - Modal/panel for imageboard import
   - Board selection dropdown
   - Search form (query, sort, direction)
   - Results preview grid (thumbnails + counts)
   - Import count input + button
   - Progress/status display

2. **Integration with main app** (`frontend/app.js`)
   - Add "Import from Imageboard" button/menu item near existing folder import
   - Launch modal, call search endpoint, display results, call import endpoint
   - Update project summary after import

3. **Styling** (enhance `frontend/styles.css` as needed)
   - Modal layout
   - Responsive grid for preview images
   - Status/progress indicators

4. **Query Syntax Guidance** (in-app help)
   - Document that queries support negation (e.g., `fluttershy, -animated` excludes animated images)
   - Show examples of multi-tag searches (comma or space-separated depending on board)
   - Link to board-specific query documentation if available

### Considerations

- Lazy-load images in preview grid (only load visible thumbnails).
- Disable UI during API calls to prevent duplicate submissions.
- Display helpful error messages if search fails or no results found.
- Show estimated import time or result count before importing.

---

## Phase 6: Testing & Refinement ⬜ IN PROGRESS

**Goal:** Ensure quality and robustness across boards.

### Deliverables

1. **Unit tests** (`tests/test_imageboard_import.py`)
   - Mock clients for each board
   - Test search result parsing
   - Test tag normalization
   - Test error handling (auth failures, 404s, malformed responses)

2. **Integration tests**
   - Test full import flow (search → preview → import)
   - Test database state after import (images + captions created correctly)

3. **Manual testing checklist**
   - Each board (if API access available)
   - Various queries and sort options
   - Edge cases: empty results, single image, very large result sets
   - Network errors and retries
   - Rate limiting (if applicable)

---

## Optional Enhancements (Post-MVP)

1. **Credentials/Auth Management**
   - Store optional API keys securely in app state (encrypted if possible).
   - Per-board auth UI.

2. **Advanced Search Filters** ✅ COMPLETE (rating filter)
   - Rating filter dropdown (Any / Safe / Questionable / Explicit) in import modal
   - Board-aware query injection: Philomena boards use comma-separated tag; Rails boards use `rating:s/q/e`
   - Also: Date range filter, user-specified tag exclusions — not yet implemented

3. **Caching**
   - In-memory cache of recent searches to avoid duplicate API calls.
   - Download cache to skip re-fetching images if user imports same search twice.

4. **Batch Operations**
   - Import multiple search results in sequence
   - Schedule imports for later

5. **Board-Specific Features**
   - Derpibooru favorites/trending
   - Danbooru popular posts
   - e621 favorites lists
   - Twibooru equivalents

6. **Source Attribution** ✅ COMPLETE
   - `source_url` from each board appended to caption text as `| source:<url>`
   - Users can trace imported images back to original board page

7. **Tag Filtering**
   - Exclude/include specific tags before import
   - Map board tags to project tags

8. **Duplicate Detection** ✅ COMPLETE
   - SHA-256 hash of `original_blob` content checked before insert
   - `skip_duplicates` option (default on) exposed in import modal
   - Duplicates within same batch also caught (hash set updated after each insert)
   - `duplicate_count` reported in import result and status message

9. **Async Progress Reporting**
   - WebSocket or Server-Sent Events for real-time import progress
   - Cancel in-progress imports

---

## Dependencies & Configuration

### Database Migration

```sql
-- Add new table in database schema initialization
CREATE TABLE imageboard_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    board_id TEXT UNIQUE NOT NULL,
    api_key TEXT,
    username TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Or using SQLAlchemy ORM (models.py):
class ImageboardCredential(Base):
    __tablename__ = "imageboard_credentials"
    id = Column(Integer, primary_key=True)
    board_id = Column(String(50), unique=True, nullable=False)
    api_key = Column(Text)
    username = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### New Dependencies (requirements-optional.txt)

```
requests>=2.28.0  # HTTP client for external APIs
aiohttp>=3.8.0    # (optional) if async is desired
cryptography>=38.0.0  # (optional) for encrypting stored API keys
```

### Configuration (`backend/config.py` extension)

```python
# Add to settings or new dataclass
IMAGEBOARD_CONFIG = {
    "derpibooru": {
        "base_url": "https://derpibooru.org",
        "api_endpoint": "/api/v1",
        "supports_galleries": True,
        "supports_pools": False,
        "optional_auth": ["api_key"],
    },
    "danbooru": {
        "base_url": "https://danbooru.donmai.us",
        "api_endpoint": "/",
        "supports_galleries": False,
        "supports_pools": True,
        "optional_auth": ["username", "api_key"],
    },
    # ... etc
}

# Rate limiting / timeouts
IMAGEBOARD_REQUEST_TIMEOUT = 30  # seconds
IMAGEBOARD_RETRY_DELAY = 1       # seconds between retries
IMAGEBOARD_MAX_RETRIES = 3

# Board registry (auto-generated from client definitions or hardcoded)
IMAGEBOARD_BOARDS = {
    "e621": {
        "display_name": "e621",
        "base_url": "https://e621.net",
        "requires_auth": True,
        "requires_username": True,
        "available_sorts": ["date", "score", "popularity", "rank"],
        "supports_galleries": False,
        "supports_pools": False,
        "rate_limit_info": "2 requests/second (hard limit)",
        "api_docs": "https://e621.net/help/api"
    },
    "derpibooru": {
        "display_name": "Derpibooru",
        "base_url": "https://derpibooru.org",
        "requires_auth": False,
        "requires_username": False,
        "available_sorts": ["score", "wilson_score", "upvotes", "downvotes", "first_seen_at", "random", "faves", "tag_count", "relevance"],
        "supports_galleries": True,
        "supports_pools": False,
        "rate_limit_info": "20 req/10 sec (search); may trigger 501 challenges",
        "api_docs": "https://derpibooru.org/pages/api"
    },
    "danbooru": {
        "display_name": "Danbooru",
        "base_url": "https://danbooru.donmai.us",
        "requires_auth": True,
        "requires_username": True,
        "available_sorts": ["date", "score", "popular", "rank"],
        "supports_galleries": False,
        "supports_pools": True,
        "rate_limit_info": "10 requests/second (global read limit)",
        "api_docs": "https://danbooru.donmai.us/wiki_pages/help%3Aapi"
    },
    "twibooru": {
        "display_name": "Twibooru",
        "base_url": "https://twibooru.org",
        "requires_auth": False,
        "requires_username": False,
        "available_sorts": ["score", "wilson_score", "upvotes", "downvotes", "first_seen_at", "random", "faves", "tag_count"],
        "supports_galleries": False,
        "supports_pools": False,
        "rate_limit_info": "10 requests/minute (search) — SLOWEST BOARD",
        "api_docs": "https://twibooru.org/pages/api"
    },
    "tantabus": {
        "display_name": "Tantabus",
        "base_url": "https://tantabus.ai",
        "requires_auth": False,
        "requires_username": False,
        "available_sorts": ["score", "wilson_score", "upvotes", "downvotes", "first_seen_at", "random", "faves", "tag_count"],
        "supports_galleries": False,
        "supports_pools": False,
        "rate_limit_info": "~20 requests/10 seconds (Derpibooru fork estimate)",
        "api_docs": "https://tantabus.ai/pages/api"
    }
}
```

---

## File Structure

```
backend/
  db/
    models.py                         # Add ImageboardCredential model
  services/
    imageboard_credentials_service.py # Credentials management (Phase 0)
    imageboard_import_service.py      # Service layer (Phase 3)
  llm/
    imageboard/
      __init__.py
      base.py                         # Abstract base classes (Phase 1)
      http_client.py                  # Shared HTTP utilities (Phase 1)
      derpibooru.py                   # Derpibooru client (Phase 2)
      tantabus.py                     # Tantabus client (Phase 2)
      danbooru.py                     # Danbooru client (Phase 2)
      twibooru.py                     # Twibooru client (Phase 2)
      e621.py                         # e621 client (Phase 2)
  routers/
    imageboard_import.py              # API endpoints (Phase 4)
frontend/
  js/
    imageboard-import.js              # Import UI module (Phase 5)
    imageboard-settings.js            # Credentials UI (Phase 0)
tests/
  test_imageboard_import.py           # Tests (Phase 6)
```

---

## Development Notes

1. **Start with Phase 0** — Database schema + credentials management is the foundation
   - All other phases depend on credentials being retrievable
   - Implement settings UI for easy credential entry
2. **Then Phase 1–3** to establish the client framework
3. **Verify API compatibility** with at least one real board before moving to UI.
4. **Keep API clients stateless** to allow easy testing and mocking.
5. **Document rate limits** and best practices for each board.
6. **Use type hints** throughout (Pydantic for request/response validation).
7. **Test error cases** thoroughly (network errors, malformed responses, auth failures).
8. **Consider future boards**: Design the abstraction so adding new boards requires minimal code changes.
9. **User-Agent configuration:** Prompt user for their e621/Danbooru username during setup for proper User-Agent headers.
10. **Rate limiting strategy:** Implement conservative delays per board (use slowest limit as baseline, then adjust as needed).
11. **Derpibooru challenges:** Treat 501/500 responses as critical—test locally with intentionally aggressive requests to verify backoff works.
12. **Database exports:** Document that Derpibooru/Danbooru offer nightly exports for bulk data; recommend as alternative for very large imports.

---

## Phase 0 Implementation Checklist

- [ ] Add `ImageboardCredential` model to `backend/db/models.py`
- [ ] Create `backend/services/imageboard_credentials_service.py` with:
  - `get_credentials(board_id)` → returns dict with api_key, username
  - `get_all_credentials_summary()` → returns masked display data
  - `save_credentials(board_id, api_key, username)`
  - `delete_credentials(board_id)`
  - `validate_credentials(board_id, api_key, username)` (optional: test API call)
- [ ] Add endpoints to router (or existing settings router):
  - `GET /api/settings/imageboard-credentials`
  - `GET /api/settings/imageboard-boards`
  - `POST /api/settings/imageboard-credentials/update`
  - `DELETE /api/settings/imageboard-credentials/:board_id`
- [ ] Create `frontend/js/imageboard-settings.js` with:
  - Board list display
  - Credential input forms (API key, username)
  - Save/Delete buttons
  - Links to API key generation per board
  - Masked key display (show last 4 chars only)
- [ ] Add settings tab to main app UI linking to imageboard-settings module
- [ ] Test: Add credentials via UI, verify persisted in DB, retrieve and display correctly

---

## Implementation Gotchas & Troubleshooting

| Issue | Root Cause | Solution |
|-------|-----------|----------|
| 403 Forbidden on e621 | Missing or invalid User-Agent header | Ensure User-Agent is set and matches pattern; never use library default |
| 429 / 503 on Derpibooru | Exceeding rate limits or triggering middleware challenge | Implement exponential backoff; parse 501 HTML challenge and pause 5+ sec |
| 429 Too Many Requests on Twibooru | Search endpoint rate limit (10/min) is very low | Reduce request frequency; warn user that large imports will be slow |
| 401 Unauthorized | API key is invalid/expired or format is wrong | Verify key generation; test with query params first, then headers |
| Empty results despite valid query | Query syntax differs per board; tag negation varies | Test queries manually on board website; document syntax differences |
| Slow imports on Twibooru | Rate limits force ~10 search requests/min | Expected; imports will take time. Parallelize by using pools (if supported) or queue imports |
| Memory exhaustion during pagination | Collecting all results in memory before import | Implement streaming/chunked import; import results in batches as they arrive |

---

## Success Criteria

- [ ] **Phase 0:** Users can add/edit/delete API keys in settings for all 5 boards; credentials persisted in DB
- [ ] **Phase 1:** Abstract base class supports all required board operations; HTTP client handles retries/delays
- [ ] **Phase 2:** All 5 boards have working clients; search/tag extraction verified
- [ ] **Phase 3:** Service layer orchestrates search, preview, and import; pagination handled
- [ ] **Phase 4:** REST API endpoints functional for search and import
- [ ] **Phase 5:** UI is responsive and user-friendly; credentials masked in display
- [ ] **Phase 6:** Tests cover core search, import, and error handling paths
- [ ] All five initial boards are functional.
- [ ] Users can select an imageboard and search by query/sort.
- [ ] Search results show preview (thumbnails, count, pagination info).
- [ ] Users can specify number of images to import.
- [ ] Images and their tags are imported as captions into the project database.
- [ ] Import completes without data loss on network errors or partial failures.
