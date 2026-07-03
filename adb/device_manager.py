

from __future__ import annotations

import random
import threading
from typing import Dict, List, Set

from adb.adb_manager import (
    get_android_version,
    get_baterai_device,
    get_daftar_device_detail,
    get_model_device,
)


class AntrianDevice:
    """Antrian link anti-double per device. Logika asli dipertahankan
    persis dari program CLI (shuffle, hindari link sama berturut-turut)."""

    def __init__(self, device_id: str, nomor: int, links: List[str]):
        self.device_id = device_id
        self.nomor = nomor
        self.nama = f"HP#{nomor}(...{device_id[-6:]})"
        self.semua_link = links.copy()
        self.antrian: List[str] = []
        self.riwayat: List[str] = []
        self._isi_antrian()

    def _isi_antrian(self) -> None:
        acak = self.semua_link.copy()
        random.shuffle(acak)
        if self.riwayat and len(acak) > 1:
            while acak[0] == self.riwayat[-1]:
                random.shuffle(acak)
        self.antrian = acak

    def ambil_link_berikutnya(self) -> str:
        if not self.antrian:
            self._isi_antrian()
        link = self.antrian.pop(0)
        self.riwayat.append(link)
        return link

    def sisa_antrian(self) -> int:
        return len(self.antrian)


class DeviceInfo:
    """Struktur data ringkas informasi satu device untuk ditampilkan di GUI."""

    def __init__(self, serial: str, status_adb: str):
        self.serial = serial
        self.status_adb = status_adb  # "device" | "unauthorized" | "offline"
        self.model = "?"
        self.android = "?"
        self.baterai = "?"
        self.dikecualikan = False
        self.status_runtime = "Offline"  # Online / Running / Waiting / Offline

    def muat_detail(self) -> None:
        """Mengambil detail device via ADB (model, versi android, baterai).
        Hanya dilakukan untuk device dengan status 'device' (online & authorized)."""
        if self.status_adb == "device":
            self.model = get_model_device(self.serial)
            self.android = get_android_version(self.serial)
            self.baterai = get_baterai_device(self.serial)
            self.status_runtime = "Online"
        elif self.status_adb == "unauthorized":
            self.status_runtime = "Unauthorized"
        else:
            self.status_runtime = "Offline"


class DeviceManager:
    """Mengganti variabel global `device_dikecualikan` (set) pada versi CLI
    dengan objek state yang thread-safe dan bisa dipakai bersama oleh GUI.

    Fungsi kelola_pengecualian() versi CLI (menu 5) dipecah menjadi method:
    kecualikan(), aktifkan_kembali(), reset_semua() — logika/perilaku sama.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._dikecualikan: Set[str] = set()
        self._devices: Dict[str, DeviceInfo] = {}

    # ── Pengelolaan pengecualian (logika sama seperti menu 5 CLI) ──
    def kecualikan(self, device_id: str) -> None:
        with self._lock:
            self._dikecualikan.add(device_id)
            if device_id in self._devices:
                self._devices[device_id].dikecualikan = True

    def aktifkan_kembali(self, device_id: str) -> None:
        with self._lock:
            self._dikecualikan.discard(device_id)
            if device_id in self._devices:
                self._devices[device_id].dikecualikan = False

    def reset_semua(self) -> int:
        with self._lock:
            jumlah = len(self._dikecualikan)
            self._dikecualikan.clear()
            for d in self._devices.values():
                d.dikecualikan = False
            return jumlah

    def set_pengecualian(self, device_id: str, dikecualikan: bool) -> None:
        if dikecualikan:
            self.kecualikan(device_id)
        else:
            self.aktifkan_kembali(device_id)

    def daftar_dikecualikan(self) -> Set[str]:
        with self._lock:
            return set(self._dikecualikan)

    def is_dikecualikan(self, device_id: str) -> bool:
        with self._lock:
            return device_id in self._dikecualikan

    # ── Pemindaian device (dipakai tombol Refresh Device & auto refresh) ──
    def refresh(self) -> List[DeviceInfo]:
        """Memindai ulang seluruh device (logika get_daftar_device_detail),
        memperbarui detail (model/android/baterai) dan status pengecualian."""
        detail = get_daftar_device_detail()
        with self._lock:
            serial_terkini = {serial for serial, _ in detail}
            # Hapus device yang sudah tidak terhubung sama sekali
            for serial in list(self._devices.keys()):
                if serial not in serial_terkini:
                    del self._devices[serial]

            for serial, status_adb in detail:
                info = self._devices.get(serial)
                if info is None:
                    info = DeviceInfo(serial, status_adb)
                    info.dikecualikan = serial in self._dikecualikan
                    self._devices[serial] = info
                else:
                    info.status_adb = status_adb
                info.muat_detail()

            return list(self._devices.values())

    def get_devices(self) -> List[DeviceInfo]:
        with self._lock:
            return list(self._devices.values())

    def get_device_aktif_ids(self) -> List[str]:
        """Device yang online (status_adb == 'device') dan TIDAK dikecualikan.
        Ini setara `devices_aktif` pada fungsi jalankan_program() versi CLI."""
        with self._lock:
            return [
                d.serial for d in self._devices.values()
                if d.status_adb == "device" and d.serial not in self._dikecualikan
            ]

    def tandai_status_runtime(self, device_id: str, status: str) -> None:
        """Dipakai automation engine untuk menandai status Running/Waiting
        pada device saat proses berjalan (agar tabel Perangkat ikut update)."""
        with self._lock:
            info = self._devices.get(device_id)
            if info:
                info.status_runtime = status
