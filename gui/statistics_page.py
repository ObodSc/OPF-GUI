"""
Halaman Statistik
====================
Menampilkan card: Total Visit, Sukses, Gagal, Putaran, dan Visit per Menit.
Data diambil dari class Statistik yang sama dipakai oleh AutomationEngine
(logika pencatatan asli dari program CLI, tidak diubah).
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from adb.automation import AutomationEngine
from gui.widgets import JudulHalaman, StatCard


class StatisticsPage(QWidget):
    def __init__(self, automation: AutomationEngine, parent=None):
        super().__init__(parent)
        self.automation = automation

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(JudulHalaman("Statistik", "Detail performa automation link"))

        grid = QGridLayout()
        grid.setSpacing(16)
        self.card_total_visit = StatCard("Total Visit")
        self.card_sukses = StatCard("Sukses")
        self.card_gagal = StatCard("Gagal")
        self.card_putaran = StatCard("Putaran")
        self.card_visit_per_menit = StatCard("Visit per Menit")

        for i, kartu in enumerate([
            self.card_total_visit, self.card_sukses, self.card_gagal,
            self.card_putaran, self.card_visit_per_menit,
        ]):
            grid.addWidget(kartu, 0, i)
        layout.addLayout(grid)

        self.tabel_per_device = QTableWidget(0, 3)
        self.tabel_per_device.setHorizontalHeaderLabels(["Device", "Sukses", "Gagal"])
        self.tabel_per_device.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabel_per_device.verticalHeader().setVisible(False)
        self.tabel_per_device.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.tabel_per_device)

        self._putaran_terakhir = 0

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self.refresh()

    def tandai_putaran(self, putaran: int) -> None:
        self._putaran_terakhir = putaran

    def refresh(self) -> None:
        stat = self.automation.statistik
        total_visit = stat.total_sukses + stat.total_gagal
        self.card_total_visit.set_nilai(total_visit)
        self.card_sukses.set_nilai(stat.total_sukses)
        self.card_gagal.set_nilai(stat.total_gagal)
        self.card_putaran.set_nilai(self._putaran_terakhir)

        durasi_menit = max(1e-6, (datetime.now() - stat.waktu_mulai).total_seconds() / 60)
        visit_per_menit = total_visit / durasi_menit
        self.card_visit_per_menit.set_nilai(f"{visit_per_menit:.1f}")

        self.tabel_per_device.setRowCount(0)
        for i, (nama, data) in enumerate(stat.per_device.items()):
            self.tabel_per_device.insertRow(i)
            self.tabel_per_device.setItem(i, 0, QTableWidgetItem(nama))
            self.tabel_per_device.setItem(i, 1, QTableWidgetItem(str(data["sukses"])))
            self.tabel_per_device.setItem(i, 2, QTableWidgetItem(str(data["gagal"])))
