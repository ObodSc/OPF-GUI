"""
Widget-widget reusable yang dipakai di beberapa halaman GUI
(agar tidak ada duplikasi kode antar halaman).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

WARNA_STATUS = {
    "Online": "#4CAF50",
    "Running": "#00BCD4",
    "Waiting": "#FFC107",
    "Offline": "#F44336",
    "Unauthorized": "#F44336",
}


class StatCard(QFrame):
    """Kartu ringkasan angka untuk Dashboard & Statistik."""

    def __init__(self, judul: str, nilai_awal: str = "0", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        self.label_nilai = QLabel(nilai_awal)
        self.label_nilai.setObjectName("statCardValue")

        self.label_judul = QLabel(judul)
        self.label_judul.setObjectName("statCardLabel")

        layout.addWidget(self.label_nilai)
        layout.addWidget(self.label_judul)
        layout.addStretch()

    def set_nilai(self, nilai) -> None:
        self.label_nilai.setText(str(nilai))


class StatusBadge(QLabel):
    """Label status berwarna (Online/Running/Waiting/Offline)."""

    def __init__(self, status: str = "Offline", parent=None):
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        warna = WARNA_STATUS.get(status, "#9A9A9A")
        self.setText(f"  {status}  ")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background-color: {warna}22; color: {warna}; "
            f"border: 1px solid {warna}; border-radius: 8px; "
            f"padding: 2px 8px; font-weight: 600;"
        )


class JudulHalaman(QWidget):
    """Header standar tiap halaman: judul besar + subjudul kecil."""

    def __init__(self, judul: str, subjudul: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(2)

        label_judul = QLabel(judul)
        label_judul.setObjectName("judulHalaman")
        layout.addWidget(label_judul)

        if subjudul:
            label_sub = QLabel(subjudul)
            label_sub.setObjectName("subtitle")
            layout.addWidget(label_sub)
