"""
Panel Log Aktivitas
=======================
Menampilkan log realtime (bukan popup) di bagian bawah aplikasi, dengan
filter: Semua, Info, Warning, Error, Success. Terhubung langsung ke
Signal `pesan_baru` dari adb.logger.Logger sehingga setiap log yang
ditulis backend (termasuk dari dalam thread automation) otomatis muncul.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from adb.logger import logger

WARNA_TIPE = {
    "INFO": "#FFFFFF",
    "SUKSES": "#4CAF50",
    "ERROR": "#F44336",
    "WARNING": "#FFC107",
    "PROSES": "#00BCD4",
    "STAT": "#B39DDB",
}

PILIHAN_FILTER = ["Semua", "Info", "Warning", "Error", "Success"]

PEMETAAN_FILTER = {
    "Semua": None,
    "Info": {"INFO", "PROSES"},
    "Warning": {"WARNING"},
    "Error": {"ERROR"},
    "Success": {"SUKSES", "STAT"},
}


class LogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._riwayat: list[tuple[str, str, str]] = []  # (waktu, tipe, pesan)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("Log Aktivitas"))
        header.addStretch()

        header.addWidget(QLabel("Filter:"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(PILIHAN_FILTER)
        self.combo_filter.currentTextChanged.connect(self._render_ulang)
        header.addWidget(self.combo_filter)

        self.btn_bersihkan = QPushButton("🗑  Bersihkan")
        self.btn_bersihkan.clicked.connect(self.bersihkan)
        header.addWidget(self.btn_bersihkan)

        layout.addLayout(header)

        self.area_log = QPlainTextEdit()
        self.area_log.setReadOnly(True)
        self.area_log.setMaximumBlockCount(2000)
        self.area_log.setStyleSheet(
            "background-color: #1A1A1B; font-family: Consolas, monospace; font-size: 12px;"
        )
        layout.addWidget(self.area_log)

        logger.pesan_baru.connect(self.tambah_log)

    def tambah_log(self, waktu: str, tipe: str, pesan: str) -> None:
        self._riwayat.append((waktu, tipe, pesan))
        if self._cocok_filter(tipe):
            self._tulis_baris(waktu, tipe, pesan)

    def _cocok_filter(self, tipe: str) -> bool:
        aktif = PEMETAAN_FILTER.get(self.combo_filter.currentText())
        return aktif is None or tipe in aktif

    def _tulis_baris(self, waktu: str, tipe: str, pesan: str) -> None:
        warna = WARNA_TIPE.get(tipe, "#FFFFFF")
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(warna))
        cursor = self.area_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"[{waktu}] [{tipe:7}] {pesan}\n", fmt)
        self.area_log.setTextCursor(cursor)
        self.area_log.ensureCursorVisible()

    def _render_ulang(self) -> None:
        self.area_log.clear()
        for waktu, tipe, pesan in self._riwayat:
            if self._cocok_filter(tipe):
                self._tulis_baris(waktu, tipe, pesan)

    def bersihkan(self) -> None:
        self.area_log.clear()
        self._riwayat.clear()
