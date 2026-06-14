"""PPD web-based desktop UI (pywebview)."""

from __future__ import annotations

import webview

from ppd.api import PPDApi
from ppd.paths import ensure_runtime_dirs, seed_default_files, web_dir


def main() -> None:
    ensure_runtime_dirs()
    seed_default_files()

    web_root = web_dir()
    index_html = web_root / "index.html"
    if not index_html.exists():
        raise FileNotFoundError(f"Web UI not found: {index_html}")

    api = PPDApi()
    window = webview.create_window(
        title="PPD Editor - Advanced Resume Dashboard",
        url=str(index_html),
        js_api=api,
        width=1440,
        height=900,
        min_size=(1100, 700),
    )
    api.set_window(window)

    def kick_boot(_=None) -> None:
        js = (
            "if(typeof boot==='function'){boot();}"
            "else{setTimeout(function(){if(typeof boot==='function')boot();},200);}"
        )
        try:
            window.evaluate_js(js)
        except Exception:
            pass

    window.events.loaded += kick_boot
    # http_server=True is required for js_api bridge with local HTML on Windows
    webview.start(http_server=True, debug=False)


if __name__ == "__main__":
    main()
