"""
Modul Thread Manager
======================
Berisi wrapper QThread untuk operasi yang tidak boleh memblokir GUI
(scan device), serta helper ThreadMonitor untuk panel "Thread Monitor"
pada halaman Otomasi. Ini murni infrastruktur GUI tambahan dan tidak
menyentuh algoritma automation/ADB yang sudah ada.
"""

from __future__ import annotations

import threading
from typing import List

from PySide6.QtCore import QThread, Signal

from adb.device_manager import DeviceInfo, DeviceManager


class DeviceRefreshThread(QThread):
    """Menjalankan device_manager.refresh() di background thread agar
    proses scan ADB (yang bisa memakan waktu beberapa detik) tidak
    membekukan tampilan GUI."""

    selesai = Signal(list)   # List[DeviceInfo]
    error = Signal(str)

    def __init__(self, device_manager: DeviceManager, parent=None):
        super().__init__(parent)
        self.device_manager = device_manager

    def run(self) -> None:
        try:
            hasil: List[DeviceInfo] = self.device_manager.refresh()
            self.selesai.emit(hasil)
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))


class ThreadMonitor:
    """Memberikan ringkasan status thread yang sedang berjalan untuk
    ditampilkan pada panel Thread Monitor di halaman Otomasi."""

    def __init__(self) -> None:
        self.task_selesai = 0
        self._lock = threading.Lock()

    def tambah_task_selesai(self) -> None:
        with self._lock:
            self.task_selesai += 1

    def ringkasan(self, task_berjalan: int = 0) -> dict:
        thread_aktif = threading.active_count()
        with self._lock:
            selesai = self.task_selesai
        return {
            "thread_aktif": thread_aktif,
            "thread_idle": max(0, thread_aktif - task_berjalan - 1),
            "task_berjalan": task_berjalan,
            "task_selesai": selesai,
        }
