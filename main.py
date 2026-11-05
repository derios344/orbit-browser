"""Punto de entrada de ORBIT."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from browser.window import MainWindow


def load_styles(app):
    """Aplica la hoja de estilos de ORBIT a toda la aplicación."""
    styles_path = Path(__file__).parent / "resources" / "styles" / "main.qss"
    if styles_path.exists():
        app.setStyleSheet(styles_path.read_text(encoding="utf-8"))
    else:
        print(f"Advertencia: no se encontró la hoja de estilos en {styles_path}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ORBIT")
    app.setOrganizationName("ORBIT")

    load_styles(app)

    window = MainWindow()
    window.resize(1100, 750)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
