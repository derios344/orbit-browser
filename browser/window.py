"""Ventana principal de ORBIT.

Esta clase monta la interfaz (barra de navegación, barra de
direcciones, pestañas, indicadores de estado) y la conecta con el
motor de renderizado. No conoce los detalles de Chromium: solo usa la
interfaz que engine/chromium.py expone (load, back, forward, reload,
stop, history y sus señales, incluida new_tab_requested).
"""

from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QStyle,
    QTabBar,
    QTabWidget,
    QToolBar,
    QToolButton,
)

from engine.chromium import create_engine

# Página de inicio: un archivo HTML local con el buscador de
# DuckDuckGo. Se resuelve desde la ruta del proyecto para que funcione
# desde cualquier directorio de trabajo.
HOME_PAGE_PATH = (
    Path(__file__).resolve().parent.parent / "resources" / "pages" / "home.html"
)
HOME_PAGE = QUrl.fromLocalFile(str(HOME_PAGE_PATH))

SEARCH_URL = "https://duckduckgo.com/?q={query}"

NEW_TAB_TITLE = "Nueva pestaña"
MAX_TAB_TITLE_LENGTH = 32


def _is_internal_url(url):
    """True para URLs que no deben mostrarse en la barra de direcciones
    (página de inicio local, data: y about:)."""
    return url.scheme() in ("data", "about") or url.toLocalFile() == str(
        HOME_PAGE_PATH
    )


class TabBar(QTabBar):
    """Barra de pestañas con un botón '+' para abrir pestañas nuevas."""

    new_tab_requested = Signal()
    tab_close_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setExpanding(False)
        self.setUsesScrollButtons(True)

        self.new_tab_button = QToolButton(self)
        self.new_tab_button.setText("+")
        self.new_tab_button.setToolTip("Nueva pestaña (Ctrl+T)")
        self.new_tab_button.clicked.connect(self.new_tab_requested)
        self._position_new_tab_button()

    def mouseReleaseEvent(self, event):
        # Clic central sobre una pestaña: cerrarla.
        if event.button() == Qt.MouseButton.MiddleButton:
            index = self.tabAt(event.position().toPoint())
            if index != -1:
                self.tab_close_requested.emit(index)
                return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        # La capa de pestañas encoge la barra al ancho de su contenido;
        # le exigimos que ocupe todo el ancho del widget de pestañas.
        parent = self.parentWidget()
        if parent is not None and self.minimumWidth() != parent.width():
            self.setMinimumWidth(max(parent.width(), self.minimumWidth()))
        super().resizeEvent(event)
        self._position_new_tab_button()

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._position_new_tab_button()

    def _position_new_tab_button(self):
        """Coloca el botón '+' justo después de la última pestaña."""
        if getattr(self, "new_tab_button", None) is None:
            return  # todavía no se construyó el botón
        size = self.new_tab_button.sizeHint()
        if self.count() > 0:
            last_tab = self.tabRect(self.count() - 1)
            x = last_tab.right() + 6
        else:
            x = 4
        if x + size.width() > self.width():
            self.new_tab_button.hide()
            return
        self.new_tab_button.show()
        self.new_tab_button.setGeometry(
            x,
            (self.height() - size.height()) // 2,
            size.width(),
            size.height(),
        )


class MainWindow(QMainWindow):
    """Ventana principal del navegador."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORBIT")

        self._tab_state = {}

        self._build_tabs()
        self._build_navigation_bar()
        self._build_status_bar()
        self._build_shortcuts()

        self._add_tab()
        self._refresh_current_tab_ui()
        self.address_bar.setFocus()

    # ---- Construcción de la interfaz ----

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tab_bar = TabBar(self.tabs)
        self.tabs.setTabBar(self.tab_bar)
        # setTabBar() restablece estos ajustes; hay que reaplicarlos.
        self.tab_bar.setExpanding(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.new_tab_requested.connect(self._add_tab)
        self.tab_bar.tab_close_requested.connect(self._close_tab)
        self.tab_bar.tabMoved.connect(self._sync_close_buttons)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._refresh_current_tab_ui)
        self.setCentralWidget(self.tabs)

    def _build_navigation_bar(self):
        toolbar = QToolBar("Navegación", self)
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.addToolBar(toolbar)

        self.back_button = self._create_button(
            QStyle.StandardPixmap.SP_ArrowBack, "Regresar (Alt+Izquierda)"
        )
        self.forward_button = self._create_button(
            QStyle.StandardPixmap.SP_ArrowForward, "Avanzar (Alt+Derecha)"
        )
        self.reload_button = self._create_button(
            QStyle.StandardPixmap.SP_BrowserReload, "Recargar (Ctrl+R)"
        )
        self.stop_button = self._create_button(
            QStyle.StandardPixmap.SP_BrowserStop, "Detener"
        )

        toolbar.addWidget(self.back_button)
        toolbar.addWidget(self.forward_button)
        toolbar.addWidget(self.reload_button)
        toolbar.addWidget(self.stop_button)

        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText(
            "Dirección web o búsqueda en DuckDuckGo"
        )
        self.address_bar.setClearButtonEnabled(True)
        toolbar.addWidget(self.address_bar)

    def _create_button(self, icon, tooltip):
        """Crea un botón de navegación con el icono estándar del tema."""
        button = QToolButton()
        button.setIcon(self.style().standardIcon(icon))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tooltip)
        return button

    def _build_status_bar(self):
        self.load_progress = QProgressBar()
        self.load_progress.setMaximumWidth(180)
        self.load_progress.setTextVisible(False)
        self.load_progress.hide()
        self.statusBar().addPermanentWidget(self.load_progress)

    def _build_shortcuts(self):
        shortcuts = [
            (QKeySequence("Ctrl+T"), self._add_tab),
            (QKeySequence("Ctrl+W"), self._close_current_tab),
            (QKeySequence("Ctrl+L"), self._focus_address_bar),
            (QKeySequence("Ctrl+R"), self._reload_current_tab),
            (QKeySequence("Alt+Left"), self._back_current_tab),
            (QKeySequence("Alt+Right"), self._forward_current_tab),
        ]
        for key, handler in shortcuts:
            shortcut = QShortcut(key, self)
            shortcut.activated.connect(handler)

    # ---- Pestañas ----

    @property
    def current_engine(self):
        """Motor de renderizado de la pestaña activa."""
        return self.tabs.currentWidget()

    def _add_tab(self, url=None, view=None):
        """Abre una pestaña nueva.

        Si recibe una vista (ventana nueva pedida por Chromium) la
        adopta directamente; si no, crea un motor nuevo. Carga `url`
        o la página de inicio.
        """
        engine = view if view is not None else create_engine(self)

        self._tab_state[engine] = {
            "loading": False,
            "progress": 0,
            "title": "",
        }

        self.tabs.addTab(engine, NEW_TAB_TITLE)
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

        engine.new_tab_requested.connect(
            lambda requested_view: self._add_tab(view=requested_view)
        )
        engine.search_requested.connect(
            lambda query, e=engine: self._search(query, e)
        )
        engine.urlChanged.connect(
            lambda url, e=engine: self._on_url_changed(url, e)
        )
        engine.titleChanged.connect(
            lambda title, e=engine: self._on_title_changed(title, e)
        )
        engine.loadStarted.connect(lambda e=engine: self._on_load_started(e))
        engine.loadProgress.connect(
            lambda progress, e=engine: self._on_load_progress(progress, e)
        )
        engine.loadFinished.connect(
            lambda ok, e=engine: self._on_load_finished(ok, e)
        )

        engine.load(url if url is not None else HOME_PAGE)
        self._sync_close_buttons()
        self._refresh_current_tab_ui()
        self.address_bar.setFocus()
        return engine

    def _close_tab(self, index):
        """Cierra la pestaña `index`; la última no puede cerrarse."""
        if self.tabs.count() == 1:
            self._add_tab(HOME_PAGE)

        engine = self.tabs.widget(index)
        self.tabs.removeTab(index)
        self._tab_state.pop(engine, None)
        self._sync_close_buttons()
        engine.deleteLater()

    def _close_current_tab(self):
        self._close_tab(self.tabs.currentIndex())

    def _close_tab_for_engine(self, engine):
        """Cierra la pestaña a la que pertenece un motor concreto."""
        index = self.tabs.indexOf(engine)
        if index != -1:
            self._close_tab(index)

    def _create_close_button(self, engine):
        """Crea el botón '×' de una pestaña."""
        button = QToolButton()
        button.setObjectName("tabCloseButton")
        button.setText("×")
        button.setToolTip("Cerrar pestaña (Ctrl+W)")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self._close_tab_for_engine(engine))
        return button

    def _sync_close_buttons(self):
        """Reconstruye los botones de cierre de todas las pestañas.

        Se llama al añadir, quitar o reordenar pestañas: los botones
        quedan así siempre asociados a la pestaña correcta.
        """
        position = QTabBar.ButtonPosition.RightSide
        for i in range(self.tab_bar.count()):
            old = self.tab_bar.tabButton(i, position)
            if old is not None:
                self.tab_bar.setTabButton(i, position, None)
                old.deleteLater()
            engine = self.tabs.widget(i)
            self.tab_bar.setTabButton(
                i, position, self._create_close_button(engine)
            )

    # ---- Navegación ----

    def _navigate(self):
        """Navega hacia lo que hay en la barra de direcciones.

        Las direcciones http:// y https:// se cargan directamente;
        cualquier otro texto se envía a DuckDuckGo como búsqueda.
        """
        text = self.address_bar.text().strip()
        if not text:
            return

        if text.startswith(("http://", "https://")):
            url = QUrl(text)
        else:
            self._search(text)
            return

        self.current_engine.load(url)

    def _search(self, query, engine=None):
        """Busca `query` en DuckDuckGo con el motor indicado (por
        defecto, el de la pestaña activa)."""
        engine = engine if engine is not None else self.current_engine
        if engine is None:
            return
        engine.load(QUrl(SEARCH_URL.format(query=quote(query))))

    def _focus_address_bar(self):
        self.address_bar.setFocus()
        self.address_bar.selectAll()

    def _reload_current_tab(self):
        if self.current_engine is not None:
            self.current_engine.reload()

    def _back_current_tab(self):
        if self.current_engine is not None:
            self.current_engine.back()

    def _forward_current_tab(self):
        if self.current_engine is not None:
            self.current_engine.forward()

    # ---- Señales del motor ----

    def _on_url_changed(self, url, engine):
        if engine is not self.current_engine:
            return
        text = url.toString()
        if _is_internal_url(url):
            self.address_bar.clear()
        else:
            self.address_bar.setText(text)

    def _on_title_changed(self, title, engine):
        index = self.tabs.indexOf(engine)
        if index == -1:
            return

        self._tab_state[engine]["title"] = title
        if len(title) > MAX_TAB_TITLE_LENGTH:
            title = title[: MAX_TAB_TITLE_LENGTH - 1] + "…"
        self.tabs.setTabText(index, title or NEW_TAB_TITLE)
        self.tabs.setTabToolTip(index, title)

        if engine is self.current_engine:
            self._update_window_title()

    def _on_load_started(self, engine):
        state = self._tab_state[engine]
        state["loading"] = True
        state["progress"] = 0

        if engine is self.current_engine:
            self.load_progress.show()
            self.load_progress.setValue(0)
            self.stop_button.setEnabled(True)
            self.reload_button.setEnabled(False)
            self.statusBar().showMessage("Cargando...")

    def _on_load_progress(self, progress, engine):
        self._tab_state[engine]["progress"] = progress
        if engine is self.current_engine:
            self.load_progress.setValue(progress)

    def _on_load_finished(self, ok, engine):
        self._tab_state[engine]["loading"] = False

        if engine is self.current_engine:
            self.load_progress.hide()
            self.stop_button.setEnabled(False)
            self.reload_button.setEnabled(True)
            if ok:
                self.statusBar().clearMessage()
            else:
                self.statusBar().showMessage("No se pudo cargar la página", 5000)
            self._update_navigation_buttons()

    # ---- Refresco del estado visible ----

    def _refresh_current_tab_ui(self, index=-1):
        """Sincroniza barra de direcciones, botones y título con la
        pestaña activa (al cambiar de pestaña o al crearla)."""
        engine = self.current_engine
        if engine is None or engine not in self._tab_state:
            return
        state = self._tab_state[engine]

        if state["loading"]:
            self.load_progress.show()
            self.load_progress.setValue(state["progress"])
            self.stop_button.setEnabled(True)
            self.reload_button.setEnabled(False)
        else:
            self.load_progress.hide()
            self.stop_button.setEnabled(False)
            self.reload_button.setEnabled(True)

        text = engine.url().toString()
        if _is_internal_url(engine.url()) or not text:
            self.address_bar.clear()
        else:
            self.address_bar.setText(text)

        self._update_window_title()
        self._update_navigation_buttons()

    def _update_window_title(self):
        state = self._tab_state.get(self.current_engine)
        title = state["title"] if state else ""
        if title:
            self.setWindowTitle(f"{title} — ORBIT")
        else:
            self.setWindowTitle("ORBIT")

    def _update_navigation_buttons(self):
        history = self.current_engine.history()
        self.back_button.setEnabled(history.canGoBack())
        self.forward_button.setEnabled(history.canGoForward())
