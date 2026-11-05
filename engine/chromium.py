"""Motor de renderizado basado en Chromium (Qt WebEngine).

Este módulo es el único punto que conoce QtWebEngine. La interfaz
espera que el motor exponga al menos estos métodos y señales:

    - Métodos: load(url), back(), forward(), reload(), stop(), history()
    - Señales: urlChanged, titleChanged, loadStarted, loadProgress,
      loadFinished, new_tab_requested(vista)

new_tab_requested se emite cuando una página pide una ventana nueva
(window.open, target="_blank", Ctrl+clic, ...): ORBIT la convierte en
una pestaña nueva sin conocer los detalles del motor.

Si en el futuro se incorpora otro motor (por ejemplo, Servo), bastará
con crear engine/servo.py que cumpla la misma interfaz y cambiar la
importación aquí.
"""

from PySide6.QtCore import Signal
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView


class ChromiumView(QWebEngineView):
    """Vista Chromium que promueve las ventanas nuevas a pestañas.

    Cuando la página pide una ventana nueva, Qt WebEngine llama a
    createWindow. Esta clase devuelve una vista nueva y espera a que
    arranque una navegación real; en ese momento emite
    new_tab_requested con la vista ya creada para que la ventana
    principal la adopte como pestaña (evita cargar la página dos veces).
    """

    new_tab_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pending_view = None

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
