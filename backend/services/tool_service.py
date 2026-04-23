"""Tool implementations for LLM function/tool calling.

Each tool exposes:
- A JSON schema dict for inclusion in the ``tools`` array of an LLM request.
- An executor registered in ``TOOL_EXECUTORS``.

Call ``execute_tool(name, arguments)`` to run any registered tool.
``list_tool_schemas(names)`` returns the schema dicts for a given set of tool names.
"""

from __future__ import annotations

import ipaddress
import pathlib
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
MAX_FILE_BYTES = 512 * 1024  # 512 KB
MAX_FILE_CHARS = 8_000
MAX_PAGE_WORDS = 4_000
MAX_SEARCH_RESULTS = 10
_DEFAULT_SEARCH_RESULTS = 5
_FETCH_TIMEOUT = 15
_SEARCH_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    tool_name: str
    content: str          # returned to the model as the tool message content
    display_summary: str  # short human-readable note for UI status messages


# ---------------------------------------------------------------------------
# Internal HTML helpers
# ---------------------------------------------------------------------------

_SKIP_TAGS = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form"}


class _TextExtractor(HTMLParser):
    """Strips tags and collects visible text, skipping non-content elements."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _extract_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


def _extract_title(html: str) -> str:
    lower = html.lower()
    start = lower.find("<title>")
    if start == -1:
        return ""
    end = lower.find("</title>", start)
    if end == -1:
        return ""
    return html[start + 7 : end].strip()


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------

def _assert_safe_url(url: str) -> None:
    """Raise ValueError for non-HTTP schemes or private/loopback destinations."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Only http/https URLs are allowed, got: {parsed.scheme!r}")

    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL has no host.")

    # Resolve to IP(s) and check for private/loopback ranges.
    try:
        results = socket.getaddrinfo(host, None)
    except OSError as error:
        raise ValueError(f"Could not resolve host {host!r}: {error}") from error

    for *_, sockaddr in results:
        ip_str = sockaddr[0]
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_multicast:
            raise ValueError(
                f"Requests to private/loopback addresses are not allowed ({ip_str})."
            )


_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Tool: web_search
# ---------------------------------------------------------------------------

WEB_SEARCH_SCHEMA: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for information relevant to the image caption. "
            "Returns titles, URLs, and snippets for the top results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query.",
                },
                "max_results": {
                    "type": "integer",
                    "description": f"Number of results to return (1–{MAX_SEARCH_RESULTS}). Default {_DEFAULT_SEARCH_RESULTS}.",
                    "minimum": 1,
                    "maximum": MAX_SEARCH_RESULTS,
                },
            },
            "required": ["query"],
        },
    },
}


class _DDGParser(HTMLParser):
    """Minimal parser for DuckDuckGo HTML search results."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._in_title = False
        self._in_snippet = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = dict(attrs)
        classes = attr_dict.get("class") or ""

        if tag == "a" and "result__a" in classes:
            href = attr_dict.get("href") or ""
            self._current = {"url": href, "title": "", "snippet": ""}
            self._in_title = True

        elif tag in {"a", "span"} and "result__snippet" in classes:
            self._in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if self._in_title and tag == "a":
            self._in_title = False
            if self._current and self._current.get("title"):
                self.results.append(self._current)
                self._current = None
        if self._in_snippet:
            self._in_snippet = False

    def handle_data(self, data: str) -> None:
        if self._in_title and self._current is not None:
            self._current["title"] += data
        elif self._in_snippet and self.results:
            self.results[-1]["snippet"] = self.results[-1].get("snippet", "") + data


def _web_search(query: str, max_results: int = _DEFAULT_SEARCH_RESULTS) -> ToolResult:
    max_results = max(1, min(max_results, MAX_SEARCH_RESULTS))
    encoded = urllib.parse.urlencode({"q": query})
    url = f"https://html.duckduckgo.com/html/?{encoded}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=_SEARCH_TIMEOUT) as response:
            html = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as error:
        return ToolResult(
            tool_name="web_search",
            content=f"Search failed: {error.reason}",
            display_summary="web_search failed",
        )

    parser = _DDGParser()
    parser.feed(html)
    results = parser.results[:max_results]

    if not results:
        return ToolResult(
            tool_name="web_search",
            content="No results found.",
            display_summary=f"web_search: no results for {query!r}",
        )

    lines: list[str] = []
    for i, result in enumerate(results, start=1):
        lines.append(f"[{i}] {result['title'].strip()}")
        lines.append(f"URL: {result['url']}")
        snippet = result.get("snippet", "").strip()
        if snippet:
            lines.append(f"Snippet: {snippet}")
        lines.append("")

    content = "\n".join(lines).strip()
    return ToolResult(
        tool_name="web_search",
        content=content,
        display_summary=f"web_search: {len(results)} result(s) for {query!r}",
    )


# ---------------------------------------------------------------------------
# Tool: web_fetch
# ---------------------------------------------------------------------------

WEB_FETCH_SCHEMA: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": (
            "Fetch and read the main text content of a web page. "
            "Useful for reading a specific URL found in search results."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch (http or https only).",
                },
            },
            "required": ["url"],
        },
    },
}


def _web_fetch(url: str) -> ToolResult:
    try:
        _assert_safe_url(url)
    except ValueError as error:
        return ToolResult(
            tool_name="web_fetch",
            content=f"Fetch blocked: {error}",
            display_summary="web_fetch blocked (unsafe URL)",
        )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT) as response:
            html = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return ToolResult(
            tool_name="web_fetch",
            content=f"HTTP error {error.code}: {error.reason}",
            display_summary=f"web_fetch HTTP {error.code}",
        )
    except urllib.error.URLError as error:
        return ToolResult(
            tool_name="web_fetch",
            content=f"Fetch failed: {error.reason}",
            display_summary="web_fetch failed",
        )

    title = _extract_title(html)
    body = _extract_text(html)

    words = body.split()
    if len(words) > MAX_PAGE_WORDS:
        body = " ".join(words[:MAX_PAGE_WORDS]) + " [truncated]"

    content_parts = []
    if title:
        content_parts.append(f"Title: {title}")
    content_parts.append(body)
    content = "\n\n".join(content_parts)

    return ToolResult(
        tool_name="web_fetch",
        content=content,
        display_summary=f"web_fetch: {url}",
    )


# ---------------------------------------------------------------------------
# Tool: read_file
# ---------------------------------------------------------------------------

READ_FILE_SCHEMA: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": (
            "Read the text content of a local file to use as reference context. "
            f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
            },
            "required": ["path"],
        },
    },
}


def _read_file(path: str) -> ToolResult:
    resolved: pathlib.Path
    try:
        resolved = pathlib.Path(path).resolve()
    except (TypeError, ValueError) as error:
        return ToolResult(
            tool_name="read_file",
            content=f"Invalid path: {error}",
            display_summary="read_file: invalid path",
        )

    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        return ToolResult(
            tool_name="read_file",
            content=(
                f"File type {resolved.suffix!r} is not allowed. "
                f"Permitted extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            ),
            display_summary=f"read_file: disallowed extension {resolved.suffix!r}",
        )

    if not resolved.is_file():
        return ToolResult(
            tool_name="read_file",
            content=f"File not found: {resolved}",
            display_summary="read_file: file not found",
        )

    try:
        file_size = resolved.stat().st_size
    except OSError as error:
        return ToolResult(
            tool_name="read_file",
            content=f"Could not stat file: {error}",
            display_summary="read_file: stat error",
        )

    truncated = file_size > MAX_FILE_BYTES
    try:
        with resolved.open("r", encoding="utf-8", errors="replace") as fh:
            text = fh.read(MAX_FILE_BYTES)
    except OSError as error:
        return ToolResult(
            tool_name="read_file",
            content=f"Could not read file: {error}",
            display_summary="read_file: read error",
        )

    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS]
        truncated = True

    if truncated:
        text += "\n[truncated]"

    return ToolResult(
        tool_name="read_file",
        content=text,
        display_summary=f"read_file: {resolved.name}",
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_SCHEMAS: dict[str, dict[str, object]] = {
    "web_search": WEB_SEARCH_SCHEMA,
    "web_fetch": WEB_FETCH_SCHEMA,
    "read_file": READ_FILE_SCHEMA,
}

_EXECUTORS = {
    "web_search": lambda args: _web_search(
        str(args.get("query", "")),
        int(args.get("max_results", _DEFAULT_SEARCH_RESULTS)),
    ),
    "web_fetch": lambda args: _web_fetch(str(args.get("url", ""))),
    "read_file": lambda args: _read_file(str(args.get("path", ""))),
}

SUPPORTED_TOOLS: frozenset[str] = frozenset(_SCHEMAS)


def fetch_url_as_context(url: str) -> ToolResult:
    """Fetch a URL and return its content as a ToolResult for context injection.

    Never raises; errors are captured in the returned ToolResult.
    """
    return _web_fetch(url)


def fetch_file_as_context(path: str) -> ToolResult:
    """Read a local file and return its content as a ToolResult for context injection.

    Never raises; errors are captured in the returned ToolResult.
    """
    return _read_file(path)


def list_tool_schemas(names: list[str]) -> list[dict[str, object]]:
    """Return the JSON schema dicts for the requested tool names."""
    return [_SCHEMAS[name] for name in names if name in _SCHEMAS]


def execute_tool(name: str, arguments: dict[str, object]) -> ToolResult:
    """Execute a named tool with the given arguments dict.

    Returns a ``ToolResult`` — never raises; errors are captured in the result.
    """
    executor = _EXECUTORS.get(name)
    if executor is None:
        return ToolResult(
            tool_name=name,
            content=f"Unknown tool: {name!r}",
            display_summary=f"unknown tool {name!r}",
        )
    try:
        return executor(arguments)
    except Exception as error:  # noqa: BLE001
        return ToolResult(
            tool_name=name,
            content=f"Tool error: {error}",
            display_summary=f"{name} error",
        )
