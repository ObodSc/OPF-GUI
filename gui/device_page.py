
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from adb.device_manager import DeviceInfo, DeviceManager
from adb.thread_manager import DeviceRefreshThread
from gui.widgets import JudulHalaman, StatusBadge

KOLOM = ["No", "Serial", "Model", "Android", "Baterai", "Status", "Dikecualikan"]


class DevicePage(QWidget):
    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager
        self._refresh_thread: DeviceRefreshThread | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.addWidget(JudulHalaman("Perangkat", "Kelola device ADB yang terhubung"))
        header_row.addStretch()

        self.input_cari = QLineEdit()
        self.input_cari.setPlaceholderText("Cari serial atau model...")
        self.input_cari.setFixedWidth(240)
        self.input_cari.textChanged.connect(self._filter_tabel)
        header_row.addWidget(self.input_cari)

        self.btn_refresh = QPushButton("⟳  Refresh Device")
        self.btn_refresh.setObjectName("btnPrimary")
        self.btn_refresh.clicked.connect(self.refresh_device)
        header_row.addWidget(self.btn_refresh)

        layout.addLayout(header_row)

        self.tabel = QTableWidget(0, len(KOLOM))
        self.tabel.setHorizontalHeaderLabels(KOLOM)
        self.tabel.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabel.verticalHeader().setVisible(False)
        self.tabel.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabel.setAlternatingRowColors(True)
        self.tabel.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabel)

        self.label_ringkasan = QLabel("Belum ada data device. Klik 'Refresh Device'.")
        self.label_ringkasan.setObjectName("subtitle")
        layout.addWidget(self.label_ringkasan)

    def refresh_device(self) -> None:
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("⏳  Memindai...")
        self._refresh_thread = DeviceRefreshThread(self.device_manager)
        self._refresh_thread.selesai.connect(self._on_refresh_selesai)
        self._refresh_thread.error.connect(self._on_refresh_error)
        self._refresh_thread.start()

    def _on_refresh_selesai(self, devices: list[DeviceInfo]) -> None:
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("⟳  Refresh Device")
        self._isi_tabel(devices)

    def _on_refresh_error(self, pesan: str) -> None:
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("⟳  Refresh Device")
        self.label_ringkasan.setText(f"Gagal memindai device: {pesan}")

    def _isi_tabel(self, devices: list[DeviceInfo]) -> None:
        self.tabel.setRowCount(0)
        for i, d in enumerate(devices):
            self.tabel.insertRow(i)
            self.tabel.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.tabel.setItem(i, 1, QTableWidgetItem(d.serial))
            self.tabel.setItem(i, 2, QTableWidgetItem(d.model))
            self.tabel.setItem(i, 3, QTableWidgetItem(d.android))
            self.tabel.setItem(i, 4, QTableWidgetItem(d.baterai))

            badge = StatusBadge(d.status_runtime)
            self.tabel.setCellWidget(i, 5, badge)

            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk = QCheckBox()
            chk.setChecked(d.dikecualikan)
            chk.stateChanged.connect(
                lambda state, serial=d.serial: self.device_manager.set_pengecualian(
                    serial, state != 0
                )
            )
            chk_layout.addWidget(chk)
            self.tabel.setCellWidget(i, 6, chk_widget)

        jumlah_dikecualikan = sum(1 for d in devices if d.dikecualikan)
        self.label_ringkasan.setText(
            f"Total: {len(devices)} device  |  Aktif: {len(devices) - jumlah_dikecualikan}  |  "
            f"Dikecualikan: {jumlah_dikecualikan}"
        )

    def _filter_tabel(self, teks: str) -> None:
        teks = teks.lower().strip()
        for row in range(self.tabel.rowCount()):
            serial = self.tabel.item(row, 1).text().lower() if self.tabel.item(row, 1) else ""
            model = self.tabel.item(row, 2).text().lower() if self.tabel.item(row, 2) else ""
            cocok = teks in serial or teks in model
            self.tabel.setRowHidden(row, not cocok)
