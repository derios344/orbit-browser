# ORBIT — Experimental Browser

> **🌐 Description / Descripción**
>
> **English:** ORBIT is an experimental, open-source desktop web browser written in Python with PySide6. It renders web pages with Chromium through Qt WebEngine, and it is built around a modular architecture designed to explore new rendering engines and to learn desktop application engineering by building.
>
> **Español:** ORBIT es un navegador web de escritorio experimental y de código abierto escrito en Python con PySide6. Renderiza las páginas web con Chromium a través de Qt WebEngine y está construido con una arquitectura modular pensada para explorar nuevos motores de renderizado y para aprender ingeniería de aplicaciones de escritorio construyendo.

ORBIT is an experimental, open-source desktop web browser written in Python with PySide6, rendering web pages with Chromium through Qt WebEngine.

ORBIT is not a clone of Chrome or Firefox. The goal is to build an independent, modular browser that can evolve step by step, explore new rendering engines, and serve as a real project to learn desktop application engineering.

## Project goal

- Build a functional, maintainable desktop browser from scratch.
- Keep a modular architecture so future rendering engines (e.g. Servo) can be added without rewriting the interface.
- Write simple, readable code that is easy to understand, explain and maintain.
- Learn by building: every technical decision is documented so the project can be maintained by its author.

## Technologies

- Python 3
- PySide6 (Qt 6)
- Qt WebEngine (Chromium)
- Qt Style Sheets (QSS) for the visual theme

## Features — version 0.2.0

- Main ORBIT window.
- Functional Qt WebEngine integration.
- **Navigation tabs**: open, close, reorder and switch tabs; a `+` button and `Ctrl+T` open new tabs; `Ctrl+W` closes the current tab; the last tab always remains.
- Links that request a new window (`target="_blank"`, `window.open`, Ctrl+clic) open in a new tab instead.
- Address bar with direct navigation to `http://` and `https://` URLs.
- Address bar falls back to a DuckDuckGo search for any other text.
- `Ctrl+L` focuses and selects the address bar.
- Back and forward navigation buttons, plus `Alt+Left` / `Alt+Right`.
- Reload and stop buttons, plus `Ctrl+R`.
- Basic loading indicator (progress bar) that follows the active tab.
- Tab titles and window title update with the page title of each tab.
- Minimalist dark interface (charcoal backgrounds, muted violet accents).

## Requirements

- Fedora Linux (or any modern Linux distribution)
- Python 3.10 or newer
- `pip` and `venv`

## Installation on Fedora

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running ORBIT

```bash
source .venv/bin/activate
python main.py
```

Type a URL (starting with `http://` or `https://`) or any search text in the address bar and press Enter.

Tabs: press `Ctrl+T` or the `+` button on the tab bar to open a new tab, and `Ctrl+W` (or the close button) to close one. Links that open in a new window open as a new tab. `Alt+Left` / `Alt+Right` navigate back and forward, and `Ctrl+L` focuses the address bar.

## Project structure

```
orbit-browser/
│
├── browser/
│   ├── __init__.py
│   └── window.py          # Main window: navigation bar, address bar, tab
│                          # bar, status indicators, and connection to engine
├── engine/
│   ├── __init__.py
│   └── chromium.py        # Chromium engine: the only module that knows
│                          # Qt WebEngine (engine factory + expected interface)
├── resources/
│   └── styles/
│       └── main.qss       # Visual theme (Qt Style Sheets)
├── main.py                # Application entry point
├── requirements.txt
├── README.md
└── LICENSE
```

## Roadmap

Future phases (not implemented yet):

- 0.3.0 — Browsing history
- 0.4.0 — Bookmarks
- Later — Downloads, extensions, additional rendering engines, experimental features

## Version history

- **0.2.0** — Tabs: multi-tab navigation, tab bar with new-tab button, keyboard shortcuts, and new-window requests opening as tabs.
- **0.1.0** — Foundation: main window, Qt WebEngine integration, address bar with search fallback, back/forward/reload/stop, loading indicator, dark theme.

## Current status

Phase 2 (0.2.0) — Tabs. See the features list above. Browsing history, bookmarks, downloads, AI features and ad blocking are not part of this version.
