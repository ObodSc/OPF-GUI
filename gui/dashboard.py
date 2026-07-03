"""
Halaman Dashboard
===================
Menampilkan ringkasan kondisi program secara keseluruhan:
Jumlah Device, Device Aktif, Device Dikecualikan, Jumlah Link,
Total Visit, Total Sukses, Total Gagal, dan Lama Program Berjalan.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QVBoxLayout, QWidget

from adb.adb_manager import get_daftar_device_detail
from adb.automation import AutomationEngine
from adb.device_manager import DeviceManager
from gui.widgets import JudulHalaman, StatCard


class DashboardPage(QWidget):
    def __init__(self, device_manager: DeviceManager, automation: AutomationEngine,
                 baca_link_func, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self.automation = automation
        self.baca_link_func = baca_link_func
        self.waktu_program_mulai = datetime.now()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(JudulHalaman("Dashboard", "Ringkasan status program secara realtime"))

        grid = QGridLayout()
        grid.setSpacing(16)

        self.card_jumlah_device = StatCard("Jumlah Device")
        self.card_device_aktif = StatCard("Device Aktif")
        self.card_device_dikecualikan = StatCard("Device Dikecualikan")
        self.card_jumlah_link = StatCard("Jumlah Link")
        self.card_total_visit = StatCard("Total Visit")
        self.card_total_sukses = StatCard("Total Sukses")
        self.card_total_gagal = StatCard("Total Gagal")
        self.card_lama_berjalan = StatCard("Lama Program Berjalan")

        kartu = [
            self.card_jumlah_device, self.card_device_aktif,
            self.card_device_dikecualikan, self.card_jumlah_link,
            self.card_total_visit, self.card_total_sukses,
            self.card_total_gagal, self.card_lama_berjalan,
        ]
        for i, kartu_item in enumerate(kartu):
            grid.addWidget(kartu_item, i // 4, i % 4)

        layout.addLayout(grid)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self.refresh()

    def refresh(self) -> None:
        devices = self.device_manager.get_devices()
        dikecualikan = self.device_manager.daftar_dikecualikan()
        aktif = [d for d in devices if d.status_adb == "device" and d.serial not in dikecualikan]

        links = self.baca_link_func()

        self.card_jumlah_device.set_nilai(len(devices))
        self.card_device_aktif.set_nilai(len(aktif))
        self.card_device_dikecualikan.set_nilai(len(dikecualikan))
        self.card_jumlah_link.set_nilai(len(links))

        stat = self.automation.statistik
        total_visit = stat.total_sukses + stat.total_gagal
        self.card_total_visit.set_nilai(total_visit)
        self.card_total_sukses.set_nilai(stat.total_sukses)
        self.card_total_gagal.set_nilai(stat.total_gagal)

        durasi = datetime.now() - self.waktu_program_mulai
        jam = int(durasi.total_seconds()) // 3600
        menit = (int(durasi.total_seconds()) % 3600) // 60
        detik = int(durasi.total_seconds()) % 60
        self.card_lama_berjalan.set_nilai(f"{jam:02d}:{menit:02d}:{detik:02d}")
