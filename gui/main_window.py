"""
Main Window
=============
Jendela utama aplikasi: Toolbar Atas, Sidebar Kiri, Halaman Konten
(QStackedWidget), Panel Log (QDockWidget di bawah), dan Status Bar.
Menghubungkan seluruh halaman GUI ke backend ADB/automation yang sudah ada.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QSpinBox, QStackedWidget, QToolBar, QVBoxLayout, QWidget,
)

from adb.adb_manager import restart_adb_server
from adb.automation import AutomationEngine
from adb.device_manager import DeviceManager
from adb.logger import logger
from adb.thread_manager import ThreadMonitor

from gui.automation_page import AutomationPage
from gui.dashboard import DashboardPage
from gui.device_page import DevicePage
from gui.link_page import LinkPage, baca_link
from gui.log_page import LogPage
from gui.settings_page import SettingsPage, muat_config
from gui.statistics_page import StatisticsPage

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(BASE_DIR, "assets", "icon")

HALAMAN = [
    ("Dashboard", "🏠"),
    ("Perangkat", "📱"),
    ("Otomasi", "⚙️"),
    ("Daftar Link", "🔗"),
    ("Log Aktivitas", "📝"),
    ("Statistik", "📊"),
    ("Pengaturan", "🛠️"),
]


class DialogMulai(QDialog):
    """Dialog kecil pengganti input() durasi & putaran pada versi CLI."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mulai Automation")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.spin_durasi = QDoubleSpinBox()
        self.spin_durasi.setRange(0.1, 999)
        self.spin_durasi.setSuffix(" menit")
        self.spin_durasi.setValue(config.get("durasi_menit", 3.0))
        form.addRow("Durasi per link:", self.spin_durasi)

        self.spin_putaran = QSpinBox()
        self.spin_putaran.setRange(0, 999999)
        self.spin_putaran.setSpecialValueText("Tak terbatas")
        self.spin_putaran.setValue(config.get("jumlah_putaran", 0))
        form.addRow("Jumlah putaran (0=tak terbatas):", self.spin_putaran)

        layout.addLayout(form)

        tombol = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        tombol.accepted.connect(self.accept)
        tombol.rejected.connect(self.reject)
        layout.addWidget(tombol)

    def nilai(self) -> tuple[float, int]:
        return self.spin_durasi.value(), self.spin_putaran.value()



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OPF - Otomasi Perangkat ADB")
        self.resize(1280, 800)

        # ── Backend ──
        self.device_manager = DeviceManager()
        self.automation = AutomationEngine(self.device_manager)
        self.thread_monitor = ThreadMonitor()

        self._bangun_ui()
        self._bangun_toolbar()
        self._hubungkan_signal()

        # Scan device pertama kali saat start
        QTimer.singleShot(300, self.aksi_refresh_device)

    # ── UI ──
    def _bangun_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout_utama = QHBoxLayout(central)
        layout_utama.setContentsMargins(0, 0, 0, 0)
        layout_utama.setSpacing(0)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)
        for nama, ikon in HALAMAN:
            item = QListWidgetItem(f"{ikon}   {nama}")
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._pindah_halaman)
        layout_utama.addWidget(self.sidebar)

        # Stacked pages
        self.stack = QStackedWidget()

        self.link_page = LinkPage()
        self.dashboard_page = DashboardPage(self.device_manager, self.automation, baca_link)
        self.device_page = DevicePage(self.device_manager)
        self.automation_page = AutomationPage(self.automation, self.device_manager, self.thread_monitor)
        self.log_page_full = LogPage()
        self.statistics_page = StatisticsPage(self.automation)
        self.settings_page = SettingsPage()

        for page in (
            self.dashboard_page, self.device_page, self.automation_page,
            self.link_page, self.log_page_full, self.statistics_page,
            self.settings_page,
        ):
            self.stack.addWidget(page)

        layout_utama.addWidget(self.stack, stretch=1)
        self.sidebar.setCurrentRow(0)

        self.statusBar().showMessage("Siap. Silakan refresh device untuk memulai.")

    def _bangun_toolbar(self) -> None:
        toolbar = QToolBar("Toolbar Utama")
        toolbar.setMovable(False)
        toolbar.setIconSize(toolbar.iconSize())
        self.addToolBar(toolbar)

        self.aksi_mulai = QAction("▶  Mulai", self)
        self.aksi_pause = QAction("⏸  Pause", self)
        self.aksi_resume = QAction("▶  Resume", self)
        self.aksi_stop = QAction("■  Stop", self)
        self.aksi_refresh = QAction("⟳  Refresh Device", self)
        self.aksi_restart_adb = QAction("⟳  Restart ADB", self)
        self.aksi_kelola_link = QAction("📂  Kelola Link", self)
        self.aksi_pengaturan = QAction("⚙  Pengaturan", self)
        self.aksi_bersihkan_log = QAction("🗑  Bersihkan Log", self)

        self.aksi_mulai.triggered.connect(self.aksi_mulai_automation)
        self.aksi_pause.triggered.connect(self.automation.pause)
        self.aksi_resume.triggered.connect(self.automation.resume)
        self.aksi_stop.triggered.connect(self.aksi_stop_automation)
        self.aksi_refresh.triggered.connect(self.aksi_refresh_device)
        self.aksi_restart_adb.triggered.connect(self.aksi_restart_adb_server)
        self.aksi_kelola_link.triggered.connect(lambda: self.sidebar.setCurrentRow(3))
        self.aksi_pengaturan.triggered.connect(lambda: self.sidebar.setCurrentRow(6))
        self.aksi_bersihkan_log.triggered.connect(self.aksi_bersihkan_log_func)

        for aksi in (
            self.aksi_mulai, self.aksi_pause, self.aksi_resume, self.aksi_stop,
        ):
            toolbar.addAction(aksi)
        toolbar.addSeparator()
        toolbar.addAction(self.aksi_refresh)
        toolbar.addAction(self.aksi_restart_adb)
        toolbar.addSeparator()
        toolbar.addAction(self.aksi_kelola_link)
        toolbar.addAction(self.aksi_pengaturan)
        toolbar.addAction(self.aksi_bersihkan_log)

        self._perbarui_state_toolbar("berhenti")

    def _hubungkan_signal(self) -> None:
        self.automation.status_berubah.connect(self._perbarui_state_toolbar)
        self.automation.status_berubah.connect(self._on_status_berubah)
        self.automation.putaran_selesai.connect(self.statistics_page.tandai_putaran)
        self.automation.automation_selesai.connect(self._on_automation_selesai)

    # ── Navigasi ──
    def _pindah_halaman(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    # ── Aksi Toolbar ──
    def aksi_mulai_automation(self) -> None:
        if self.automation.sedang_berjalan:
            QMessageBox.information(self, "Info", "Automation sedang berjalan.")
            return

        links = baca_link()
        if not links:
            QMessageBox.warning(self, "Tidak Ada Link", "Tambahkan link terlebih dahulu di halaman Daftar Link.")
            return

        devices_aktif = self.device_manager.get_device_aktif_ids()
        if not devices_aktif:
            QMessageBox.warning(
                self, "Tidak Ada Device",
                "Tidak ada device aktif. Refresh device atau periksa pengecualian di halaman Perangkat."
            )
            return

        config = muat_config()
        dialog = DialogMulai(config, self)
        if dialog.exec() != QDialog.Accepted:
            return
        durasi_menit, jumlah_putaran = dialog.nilai()

        self.automation_page.reset_tabel()
        berhasil = self.automation.mulai(links, durasi_menit, jumlah_putaran)
        if not berhasil:
            QMessageBox.critical(self, "Gagal Memulai", "Automation gagal dimulai. Periksa device & link.")
            return

        self.sidebar.setCurrentRow(2)  # Pindah otomatis ke halaman Otomasi
        self.statusBar().showMessage(f"Automation berjalan dengan {len(devices_aktif)} device...")

    def aksi_stop_automation(self) -> None:
        if not self.automation.sedang_berjalan:
            return
        konfirmasi = QMessageBox.question(self, "Stop Automation", "Yakin ingin menghentikan automation?")
        if konfirmasi == QMessageBox.Yes:
            self.automation.stop()

    def aksi_refresh_device(self) -> None:
        self.device_page.refresh_device()
        self.statusBar().showMessage("Memindai device...")

    def aksi_restart_adb_server(self) -> None:
        self.statusBar().showMessage("Merestart ADB server...")
        _, err = restart_adb_server()
        logger.log("ADB server berhasil di-restart.", "sukses")
        self.statusBar().showMessage("ADB server berhasil di-restart.")
        self.aksi_refresh_device()

    def aksi_bersihkan_log_func(self) -> None:
        konfirmasi = QMessageBox.question(self, "Bersihkan Log", "Hapus tampilan log & file log.txt?")
        if konfirmasi != QMessageBox.Yes:
            return
        self.log_page_full.bersihkan()
        try:
            from adb.logger import LOG_FILE
            open(LOG_FILE, "w", encoding="utf-8").close()
        except Exception:  # noqa: BLE001
            pass
        logger.log("Log dibersihkan oleh pengguna.", "info")

    # ── State & pengaturan ──
    def _perbarui_state_toolbar(self, status: str) -> None:
        berjalan = status == "berjalan"
        pause = status == "pause"
        self.aksi_mulai.setEnabled(not (berjalan or pause))
        self.aksi_pause.setEnabled(berjalan)
        self.aksi_resume.setEnabled(pause)
        self.aksi_stop.setEnabled(berjalan or pause)

    def _on_status_berubah(self, status: str) -> None:
        teks = {"berjalan": "Automation sedang berjalan...",
                "pause": "Automation dijeda.",
                "berhenti": "Automation berhenti."}
        self.statusBar().showMessage(teks.get(status, ""))

    def _on_automation_selesai(self) -> None:
        logger.log("Automation selesai.", "sukses")

    def closeEvent(self, event) -> None:
        if self.automation.sedang_berjalan:
            konfirmasi = QMessageBox.question(
                self, "Keluar", "Automation masih berjalan. Yakin ingin keluar?"
            )
            if konfirmasi != QMessageBox.Yes:
                event.ignore()
                return
            self.automation.stop()
        event.accept()
