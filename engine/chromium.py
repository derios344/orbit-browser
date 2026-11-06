"""Motor de renderizado basado en Chromium (Qt WebEngine).

Este módulo es el único punto que conoce QtWebEngine. La interfaz
espera que el motor exponga al menos estos métodos y señales:

    - Métodos: load(url), back(), forward(), reload(), stop(), history()
    - Señales: urlChanged, titleChanged, loadStarted, loadProgress,
      loadFinished, new_tab_requested(vista), search_requested(texto)

new_tab_requested se emite cuando una página pide una ventana nueva
(window.open, target="_blank", Ctrl+clic, ...): ORBIT la convierte en
una pestaña nueva sin conocer los detalles del motor.

Si en el futuro se incorpora otro motor (por ejemplo, Servo), bastará
con crear engine/servo.py que cumpla la misma interfaz y cambiar la
importación aquí.
"""

from PySide6.QtCore import QTimer, QUrl, QUrlQuery, Signal
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView


class ChromiumPage(QWebEnginePage):
    """Página que canaliza las búsquedas de la página de inicio.

    El formulario de inicio envía la consulta a DuckDuckGo. En lugar de
    dejar que el renderizador navegue por su cuenta, la petición se
    intercepta y se emite search_requested: la ventana principal repite
    la búsqueda con el motor (load), el mismo camino que usa la barra de
    direcciones. Así la búsqueda funciona igual en cualquier entorno y
    la URL final queda normalizada.
    """

    search_requested = Signal(str)

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        is_form = (
            nav_type
            == QWebEnginePage.NavigationType.NavigationTypeFormSubmitted
        )
        if (
            is_main_frame
            and is_form
            and url.host() in ("duckduckgo.com", "www.duckduckgo.com")
            and url.path() in ("", "/")
        ):
            query = QUrlQuery(url).queryItemValue(
                "q", QUrl.ComponentFormattingOption.FullyDecoded
            )
            # El envío de formularios codifica los espacios como '+'.
            query = query.replace("+", " ").strip()
            if query:
                # Diferido: no se puede iniciar otra navegación dentro
                # de acceptNavigationRequest.
                QTimer.singleShot(
                    0, lambda: self.search_requested.emit(query)
                )
                return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class ChromiumView(QWebEngineView):
    """Vista Chromium que promueve las ventanas nuevas a pestañas.

    Cuando la página pide una ventana nueva, Qt WebEngine llama a
    createWindow. Esta clase devuelve una vista nueva y espera a que
    arranque una navegación real; en ese momento emite
    new_tab_requested con la vista ya creada para que la ventana
    principal la adopte como pestaña (evita cargar la página dos veces).
    """

    new_tab_requested = Signal(object)
    search_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_view = None
        self._page = ChromiumPage(self)
        self._page.search_requested.connect(self.search_requested)
        self.setPage(self._page)

    def createWindow(self, window_type):
        """Solicitud de ventana nueva: la convertimos en pestaña."""
        if window_type == QWebEnginePage.WebWindowType.WebDialog:
            # Las ventanas de diálogo no son pestañas; se ignoran.
            return None

        if self._pending_view is None:
            view = ChromiumView(self)
            view.urlChanged.connect(self._promote_pending_view)
            self._pending_view = view
        return self._pending_view

    def _promote_pending_view(self, url):
        """Promueve la vista pendiente a pestaña en su primera URL real."""
        text = url.toString()
        if not text or text in ("about:blank", ""):
            return

        view, self._pending_view = self._pending_view, None
        if view is not None:
            self.new_tab_requested.emit(view)


def create_engine(parent=None):
    """Crea y devuelve la vista de navegación que usa ORBIT.

    Concentrar la construcción en una sola función permite cambiar
    de motor sin tocar browser/window.py.
    """
    return ChromiumView(parent)
