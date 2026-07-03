

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THEME_PATH = os.path.join(BASE_DIR, "assets", "theme", "dark_theme.qss")


def muat_stylesheet(app: QApplication) -> None:
    if os.path.exists(THEME_PATH):
        with open(THEME_PATH, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main() -> None:

    os.chdir(BASE_DIR)

    app = QApplication(sys.argv)
    app.setApplicationName("OPF - Obod Phone Farm Versi GUI")
    muat_stylesheet(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
