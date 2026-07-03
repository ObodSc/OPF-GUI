"""
Halaman Pengaturan
=====================
Konfigurasi yang pada versi CLI diminta lewat input() di terminal
(durasi per link, jumlah putaran) kini dipindahkan ke sini.
Disimpan/dimuat dari config/config.json.
"""

from __future__ import annotations

import json
import os

from PySide6.QtWidgets import (
    QDoubleSpinBox, QFormLayout, QMessageBox, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)

from gui.widgets import JudulHalaman

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_CONFIG = {
    "durasi_menit": 3.0,
    "jumlah_putaran": 0,
}


def muat_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        simpan_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        hasil = dict(DEFAULT_CONFIG)
        hasil.update(data)
        return hasil
    except Exception:  # noqa: BLE001
        return dict(DEFAULT_CONFIG)


def simpan_config(config: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


class SettingsPage(QWidget):

    def __init__(self, on_simpan=None, parent=None):
        super().__init__(parent)
        self.on_simpan = on_simpan

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        layout.addWidget(JudulHalaman("Pengaturan", "Konfigurasi automation, disimpan ke config.json"))

        form = QFormLayout()
        form.setSpacing(12)

        self.spin_durasi = QDoubleSpinBox()
        self.spin_durasi.setRange(0.1, 999)
        self.spin_durasi.setSuffix(" menit")
        self.spin_durasi.setDecimals(1)
        form.addRow("Durasi Per Link:", self.spin_durasi)

        self.spin_putaran = QSpinBox()
        self.spin_putaran.setRange(0, 999999)
        self.spin_putaran.setSpecialValueText("Tak terbatas")
        form.addRow("Jumlah Putaran (0 = tak terbatas):", self.spin_putaran)

        layout.addLayout(form)

        self.btn_simpan = QPushButton("💾  Simpan Pengaturan")
        self.btn_simpan.setObjectName("btnPrimary")
        self.btn_simpan.clicked.connect(self.simpan)
        layout.addWidget(self.btn_simpan)
        layout.addStretch()

        self.muat()

    def muat(self) -> None:
        config = muat_config()
        self.spin_durasi.setValue(config["durasi_menit"])
        self.spin_putaran.setValue(config["jumlah_putaran"])

    def simpan(self) -> None:
        config = {
            "durasi_menit": self.spin_durasi.value(),
            "jumlah_putaran": self.spin_putaran.value(),
        }
        simpan_config(config)
        QMessageBox.information(self, "Tersimpan", "Pengaturan berhasil disimpan.")
        if self.on_simpan:
            self.on_simpan(config)

    def get_config(self) -> dict:
        return muat_config()
