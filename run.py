from __future__ import annotations

import threading
import webbrowser

import uvicorn

from backend.config import get_settings


def open_browser(url: str) -> None:
    webbrowser.open(url, new=1)


def main() -> None:
    settings = get_settings()
    url = f"http://{settings.host}:{settings.port}"
    timer = threading.Timer(0.8, open_browser, args=(url,))
    timer.daemon = True
    timer.start()
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
