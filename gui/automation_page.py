"""
Halaman Otomasi
==================
Halaman paling penting: menampilkan Progress Global, tabel Automation
per device (Device, Status, Link Saat Ini, Progress, Putaran, Durasi,
Sisa Waktu) dengan ProgressBar per device, ditambah panel Queue Monitor
dan Thread Monitor.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QListWidget, QProgressBar,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from adb.automation import AutomationEngine
from adb.device_manager import DeviceManager
from adb.thread_manager import ThreadMonitor
from gui.widgets import JudulHalaman, StatusBadge

KOLOM = ["Device", "Status", "Link Saat Ini", "Progress", "Putaran", "Durasi", "Sisa Waktu"]


def format_detik(detik: float) -> str:
    detik = max(0, int(detik))
    m, s = divmod(detik, 60)
    return f"{m:02d}:{s:02d}"


class AutomationPage(QWidget):
    def __init__(self, automation: AutomationEngine, device_manager: DeviceManager,
                 thread_monitor: ThreadMonitor, parent=None):
        super().__init__(parent)
        self.automation = automation
        self.device_manager = device_manager
        self.thread_monitor = thread_monitor
        self._baris_device: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        layout.addWidget(JudulHalaman("Otomasi", "Progres real-time seluruh device saat menjalankan link"))

        # ── Progress Global ──
        progres_row = QHBoxLayout()
        progres_row.addWidget(QLabel("Progress Global (per Sesi):"))
        self.progress_global = QProgressBar()
        self.progress_global.setRange(0, 100)
        self.progress_global.setValue(0)
        progres_row.addWidget(self.progress_global, stretch=1)
        self.label_progres_teks = QLabel("0 / 0 sesi")
        progres_row.addWidget(self.label_progres_teks)
        layout.addLayout(progres_row)

        # ── Tabel Automation ──
        self.tabel = QTableWidget(0, len(KOLOM))
        self.tabel.setHorizontalHeaderLabels(KOLOM)
        self.tabel.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabel.verticalHeader().setVisible(False)
        self.tabel.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabel.setAlternatingRowColors(True)
        layout.addWidget(self.tabel, stretch=3)

        # ── Tab bawah: Queue Monitor & Thread Monitor ──
        tab_bawah = QTabWidget()

        self.list_queue = QListWidget()
        tab_bawah.addTab(self.list_queue, "📦  Queue Monitor")

        self.panel_thread = QWidget()
        thread_layout = QHBoxLayout(self.panel_thread)
        self.label_thread_aktif = QLabel("Thread Aktif: 0")
        self.label_thread_idle = QLabel("Thread Idle: 0")
        self.label_task_berjalan = QLabel("Task Berjalan: 0")
        self.label_task_selesai = QLabel("Task Selesai: 0")
        for w in (self.label_thread_aktif, self.label_thread_idle,
                  self.label_task_berjalan, self.label_task_selesai):
            w.setObjectName("subtitle")
            w.setStyleSheet("font-size: 13px; color: #FFFFFF; padding: 8px;")
            thread_layout.addWidget(w)
        thread_layout.addStretch()
        tab_bawah.addTab(self.panel_thread, "🧵  Thread Monitor")

        layout.addWidget(tab_bawah, stretch=2)

        # ── Koneksi signal dari AutomationEngine ──
        self.automation.progres_device.connect(self._update_baris_device)
        self.automation.progres_global.connect(self._update_progress_global)
        self.automation.status_berubah.connect(self._on_status_berubah)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_monitor)
        self._timer.start()

    # ── Update tabel & queue tiap device menerima progres baru ──
    def _update_baris_device(self, device_id: str, data: dict) -> None:
        if device_id not in self._baris_device:
            row = self.tabel.rowCount()
            self.tabel.insertRow(row)
            self._baris_device[device_id] = row
            self.tabel.setItem(row, 0, QTableWidgetItem(data["nama"]))
            self.tabel.setCellWidget(row, 1, StatusBadge(data["status"]))
            self.tabel.setItem(row, 2, QTableWidgetItem(data["link_saat_ini"]))
            bar = QProgressBar()
            bar.setRange(0, 100)
            self.tabel.setCellWidget(row, 3, bar)
            self.tabel.setItem(row, 4, QTableWidgetItem(str(data["putaran"])))
            self.tabel.setItem(row, 5, QTableWidgetItem(format_detik(data["durasi_detik"])))
            self.tabel.setItem(row, 6, QTableWidgetItem(format_detik(data["sisa_detik"])))

        row = self._baris_device[device_id]
        badge: StatusBadge = self.tabel.cellWidget(row, 1)
        badge.set_status(data["status"])
        self.tabel.item(row, 2).setText(data["link_saat_ini"])
        bar: QProgressBar = self.tabel.cellWidget(row, 3)
        bar.setValue(data["progress_persen"])
        self.tabel.item(row, 4).setText(str(data["putaran"]))
        self.tabel.item(row, 5).setText(format_detik(data["durasi_detik"]))
        self.tabel.item(row, 6).setText(format_detik(data["sisa_detik"]))

        self._update_queue_monitor()

    def _update_progress_global(self, sesi_selesai: int, total_sesi: int) -> None:
        persen = int((sesi_selesai / total_sesi) * 100) if total_sesi else 0
        self.progress_global.setValue(persen)
        self.label_progres_teks.setText(f"{sesi_selesai} / {total_sesi} sesi")

    def _on_status_berubah(self, status: str) -> None:
        if status == "berhenti":
            self.progress_global.setValue(0)
            self.label_progres_teks.setText("0 / 0 sesi")

    def _update_queue_monitor(self) -> None:
        self.list_queue.clear()
        progres = self.automation.get_progress_semua_device()
        for prog in progres.values():
            self.list_queue.addItem(
                f"{prog.nama}  ↓  link saat ini: {prog.link_saat_ini}  "
                f"(sisa antrian: {prog.sisa_antrian})"
            )

    def _update_monitor(self) -> None:
        progres = self.automation.get_progress_semua_device()
        task_berjalan = sum(1 for p in progres.values() if p.status == "Running")
        ringkasan = self.thread_monitor.ringkasan(task_berjalan)
        self.label_thread_aktif.setText(f"Thread Aktif: {ringkasan['thread_aktif']}")
        self.label_thread_idle.setText(f"Thread Idle: {ringkasan['thread_idle']}")
        self.label_task_berjalan.setText(f"Task Berjalan: {ringkasan['task_berjalan']}")
        self.label_task_selesai.setText(f"Task Selesai: {ringkasan['task_selesai']}")

    def reset_tabel(self) -> None:
        self.tabel.setRowCount(0)
        self._baris_device.clear()
        self.list_queue.clear()
