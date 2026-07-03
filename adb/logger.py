"""
Modul Logger
=============
Mempertahankan logika logging asli (tulis_log ke file) dari program CLI,
ditambah lapisan Signal PySide6 agar log bisa ditampilkan realtime di GUI
tanpa mengubah cara kerja pencatatan log yang sudah ada.

Dibuat Oleh Obod - direfactor untuk versi GUI.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime

from PySide6.QtCore import QObject, Signal


# Lokasi file log dipindahkan ke folder data/ sesuai struktur project baru
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "log.txt")

_log_lock = threading.Lock()

# Tipe log yang didukung (dipakai juga sebagai daftar filter di GUI)
TIPE_LOG = ("INFO", "SUKSES", "ERROR", "WARNING", "PROSES", "STAT")


def tulis_log(pesan: str, tipe: str = "INFO") -> None:
    """Menulis satu baris log ke file data/log.txt.

    Fungsi ini persis dengan logika asli pada program CLI: setiap pesan
    dicatat dengan format [waktu] [TIPE] pesan, menggunakan lock supaya
    aman diakses oleh banyak thread sekaligus.
    """
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    baris = f"[{waktu}] [{tipe.upper():7}] {pesan}\n"
    with _log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(baris)


class Logger(QObject):
    """Logger tunggal (singleton) yang menjembatani logging file dengan GUI.

    Setiap kali log() dipanggil dari thread manapun (thread automation,
    thread refresh device, dsb), pesan akan:
      1. Ditulis ke file log.txt (sama seperti versi CLI / tulis_log()).
      2. Dipancarkan lewat signal `pesan_baru` agar panel log GUI dapat
         menampilkannya secara realtime (Qt akan otomatis queue signal
         lintas-thread karena QueuedConnection default untuk sinyal
         antar-thread berbeda).
    """

    pesan_baru = Signal(str, str, str)  # waktu, tipe, pesan

    _instance: "Logger | None" = None

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard agar __init__ QObject tidak dipanggil berulang pada singleton
        if getattr(self, "_initialized", False):
            return
        super().__init__()
        self._initialized = True

    def log(self, pesan: str, tipe: str = "info") -> None:
        tipe_upper = tipe.upper()
        waktu = datetime.now().strftime("%H:%M:%S")
        tulis_log(pesan, tipe_upper)
        self.pesan_baru.emit(waktu, tipe_upper, pesan)


# Instance global tunggal yang dipakai di seluruh backend & GUI
logger = Logger()
