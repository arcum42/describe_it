from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from backend.config import get_settings


def open_browser(url: str) -> None:
    webbrowser.open(url, new=1)


def open_browser_when_ready(base_url: str, *, timeout_seconds: float = 15.0) -> None:
    health_url = f"{base_url}/api/health"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.5) as response:
                if 200 <= response.status < 500:
                    open_browser(base_url)
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(0.2)

    # Fallback: still open the browser after timeout so startup is not blocked.
    open_browser(base_url)


def main() -> None:
    settings = get_settings()
    url = f"http://{settings.host}:{settings.port}"
    watcher = threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True)
    watcher.start()
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
