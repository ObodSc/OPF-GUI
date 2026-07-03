

from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import QObject, Signal

from adb.adb_manager import buka_url_di_device
from adb.device_manager import AntrianDevice, DeviceManager
from adb.logger import logger, tulis_log


class Statistik:
    """Logika asli dipertahankan persis dari program CLI."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.total_sukses = 0
        self.total_gagal = 0
        self.per_device: Dict[str, Dict[str, int]] = defaultdict(lambda: {"sukses": 0, "gagal": 0})
        self.per_link: Dict[str, Dict[str, int]] = defaultdict(lambda: {"sukses": 0, "gagal": 0})
        self.waktu_mulai = datetime.now()

    def catat(self, device_nama: str, link: str, sukses: bool) -> None:
        with self.lock:
            if sukses:
                self.total_sukses += 1
                self.per_device[device_nama]["sukses"] += 1
                self.per_link[link]["sukses"] += 1
            else:
                self.total_gagal += 1
                self.per_device[device_nama]["gagal"] += 1
                self.per_link[link]["gagal"] += 1

    def ringkasan_teks(self) -> str:
        """Versi teks dari tampilkan_ringkasan() asli, dipakai untuk ditulis
        ke log GUI (bukan dicetak ke terminal)."""
        durasi = datetime.now() - self.waktu_mulai
        jam = int(durasi.total_seconds()) // 3600
        menit = (int(durasi.total_seconds()) % 3600) // 60
        detik = int(durasi.total_seconds()) % 60
        baris = [
            "===== RINGKASAN STATISTIK =====",
            f"Total sukses : {self.total_sukses}",
            f"Total gagal  : {self.total_gagal}",
            f"Durasi       : {jam:02d}:{menit:02d}:{detik:02d}",
        ]
        for nama, data in self.per_device.items():
            baris.append(f"  {nama} -> sukses:{data['sukses']} gagal:{data['gagal']}")
        return "\n".join(baris)

    def tampilkan_ringkasan_log(self) -> None:
        """Menulis ringkasan ke file log, menggantikan print() ke terminal
        pada versi CLI (tulis_log tetap dipanggil persis seperti asli)."""
        durasi = datetime.now() - self.waktu_mulai
        jam = int(durasi.total_seconds()) // 3600
        menit = (int(durasi.total_seconds()) % 3600) // 60
        detik = int(durasi.total_seconds()) % 60

        tulis_log("=" * 50, "STAT")
        tulis_log(
            f"RINGKASAN — Sukses: {self.total_sukses} | Gagal: {self.total_gagal} | "
            f"Durasi: {jam:02d}:{menit:02d}:{detik:02d}", "STAT"
        )
        for nama, data in self.per_device.items():
            tulis_log(f"  {nama} -> sukses:{data['sukses']} gagal:{data['gagal']}", "STAT")
        for link, data in self.per_link.items():
            tulis_log(f"  {link} -> sukses:{data['sukses']} gagal:{data['gagal']}", "STAT")
        tulis_log("=" * 50, "STAT")


def tugas_device(antrian: AntrianDevice, link: str, durasi_detik: float,
                  hasil_dict: dict, statistik: Statistik, putaran: int, sesi: int,
                  stop_event: threading.Event | None = None) -> None:
    """Logika asli dipertahankan dari program CLI (tugas per-device yang
    dijalankan di dalam thread). log() dari CLI diganti logger.log() yang
    setara (menulis file + memancarkan signal ke GUI).

    Perbedaan dari versi asli: delay durasi_detik sekarang ditunggu dalam
    potongan-potongan kecil (bukan satu time.sleep() panjang) sambil
    memeriksa stop_event, supaya tombol Stop bisa langsung menghentikan
    proses yang sedang berjalan alih-alih menunggu delay selesai."""
    nama = antrian.nama
    LANGKAH_CEK = 0.2  # detik, granularitas pengecekan stop_event

    def tidur_bisa_dihentikan(total_detik: float) -> bool:
        """Tidur selama total_detik, dicicil per LANGKAH_CEK.
        Mengembalikan True jika sempat dihentikan oleh stop_event."""
        sisa = total_detik
        while sisa > 0:
            if stop_event is not None and stop_event.is_set():
                return True
            waktu_tidur = min(LANGKAH_CEK, sisa)
            time.sleep(waktu_tidur)
            sisa -= waktu_tidur
        return False

    try:
        tulis_log(f"MULAI | {nama} | Putaran:{putaran} Sesi:{sesi} | {link}", "PROSES")

        sukses = buka_url_di_device(antrian.device_id, link)
        if not sukses:
            logger.log(f"{nama} -> GAGAL buka: {link}", "error")
            hasil_dict[antrian.device_id] = False
            statistik.catat(nama, link, False)
            tulis_log(f"GAGAL | {nama} | {link}", "ERROR")
            return

        logger.log(f"{nama} -> {link}", "sukses")
        tulis_log(f"BUKA  | {nama} | {link}", "SUKSES")

        if tidur_bisa_dihentikan(durasi_detik):
            hasil_dict[antrian.device_id] = False
            tulis_log(f"DIHENTIKAN | {nama} | {link}", "WARNING")
            return

        hasil_dict[antrian.device_id] = True
        statistik.catat(nama, link, True)
        tulis_log(f"DONE  | {nama} | {link}", "SUKSES")

    except Exception as e:  # noqa: BLE001 - dipertahankan seperti aslinya
        logger.log(f"{nama} -> ERROR: {e}", "error")
        tulis_log(f"ERROR | {nama} | {link} | {e}", "ERROR")
        hasil_dict[antrian.device_id] = False
        statistik.catat(nama, link, False)


class DeviceProgress:
    """Data progres satu device untuk ditampilkan di tabel halaman Otomasi."""

    def __init__(self, device_id: str, nama: str):
        self.device_id = device_id
        self.nama = nama
        self.status = "Waiting"
        self.link_saat_ini = "-"
        self.progress_persen = 0
        self.putaran = 0
        self.durasi_detik = 0
        self.sisa_detik = 0
        self.sisa_antrian = 0


class AutomationEngine(QObject):
    """Adaptasi alur jalankan_program() versi CLI agar bisa dikontrol GUI.

    Alur inti TIDAK berubah:
      - Buat AntrianDevice untuk tiap device aktif (anti-double per device)
      - Loop per PUTARAN -> loop per SESI -> jalankan tugas_device() paralel
        (satu thread per device) -> tunggu semua device selesai -> lanjut sesi
      - Statistik dicatat lewat class Statistik yang sama

    Tambahan untuk GUI: pause (Event), stop (Event), dan signal progres.
    """

    progres_global = Signal(int, int)              # sesi_selesai, total_sesi (per putaran)
    progres_device = Signal(str, dict)              # device_id, data progres (untuk tabel)
    putaran_selesai = Signal(int)
    automation_selesai = Signal()
    status_berubah = Signal(str)                    # "berjalan" | "pause" | "berhenti"

    def __init__(self, device_manager: DeviceManager):
        super().__init__()
        self.device_manager = device_manager
        self.statistik = Statistik()
        self._thread: threading.Thread | None = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # set = tidak dipause (berjalan)
        self._stop_event = threading.Event()
        self._devices_progress: Dict[str, DeviceProgress] = {}
        self.sedang_berjalan = False

    # ── Kontrol dari GUI (tombol toolbar) ──
    def mulai(self, links: List[str], durasi_menit: float, jumlah_putaran: int) -> bool:
        if self.sedang_berjalan:
            return False
        devices_aktif = self.device_manager.get_device_aktif_ids()
        if not devices_aktif or not links:
            return False

        self._stop_event.clear()
        self._pause_event.set()
        self.statistik = Statistik()
        self.sedang_berjalan = True

        self._thread = threading.Thread(
            target=self._loop_utama,
            args=(devices_aktif, links, durasi_menit * 60, jumlah_putaran),
            daemon=True,
        )
        self._thread.start()
        self.status_berubah.emit("berjalan")
        return True

    def pause(self) -> None:
        self._pause_event.clear()
        self.status_berubah.emit("pause")
        logger.log("Automation dijeda (pause).", "warning")

    def resume(self) -> None:
        self._pause_event.set()
        self.status_berubah.emit("berjalan")
        logger.log("Automation dilanjutkan (resume).", "sukses")

    def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()  # bangunkan jika sedang pause agar bisa berhenti
        logger.log("Automation dihentikan oleh pengguna.", "warning")

    # ── Loop inti (struktur sama dengan jalankan_program() versi CLI) ──
    def _loop_utama(self, devices_aktif: List[str], links: List[str],
                     durasi_detik: float, jumlah_putaran: int) -> None:
        tak_terbatas = jumlah_putaran == 0

        antrian_devices = []
        for i, dev in enumerate(devices_aktif, 1):
            ant = AntrianDevice(dev, i, links)
            antrian_devices.append(ant)
            self._devices_progress[dev] = DeviceProgress(dev, ant.nama)

        tulis_log("=" * 60, "INFO")
        tulis_log(f"SESI DIMULAI — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        tulis_log(
            f"Device aktif: {len(devices_aktif)} | Link: {len(links)} | "
            f"Durasi: {durasi_detik/60} menit", "INFO"
        )
        tulis_log("=" * 60, "INFO")
        logger.log(f"Automation dimulai dengan {len(devices_aktif)} device.", "sukses")

        putaran = 0
        try:
            while (tak_terbatas or putaran < jumlah_putaran) and not self._stop_event.is_set():
                putaran += 1
                tulis_log(f"PUTARAN {putaran} DIMULAI", "INFO")
                jumlah_sesi = len(links)

                for sesi in range(jumlah_sesi):
                    if self._stop_event.is_set():
                        break

                    # Tunggu jika sedang di-pause
                    self._pause_event.wait()
                    if self._stop_event.is_set():
                        break

                    penugasan = {}
                    for antrian in antrian_devices:
                        penugasan[antrian.device_id] = antrian.ambil_link_berikutnya()

                    hasil_dict: Dict[str, bool] = {}
                    threads = []

                    for antrian in antrian_devices:
                        link = penugasan[antrian.device_id]
                        prog = self._devices_progress[antrian.device_id]
                        prog.status = "Running"
                        prog.link_saat_ini = link
                        prog.putaran = putaran
                        prog.durasi_detik = durasi_detik
                        prog.sisa_detik = durasi_detik
                        prog.sisa_antrian = antrian.sisa_antrian()
                        self.device_manager.tandai_status_runtime(antrian.device_id, "Running")
                        self.progres_device.emit(antrian.device_id, vars(prog))

                        t = threading.Thread(
                            target=tugas_device,
                            args=(antrian, link, durasi_detik, hasil_dict,
                                  self.statistik, putaran, sesi + 1, self._stop_event),
                            daemon=True,
                        )
                        threads.append(t)

                    logger.log(f"Membuka {len(devices_aktif)} HP secara serentak...", "proses")
                    for t in threads:
                        t.start()

                    waktu_mulai = time.time()
                    while any(t.is_alive() for t in threads):
                        berlalu = time.time() - waktu_mulai
                        sisa = max(0, durasi_detik - berlalu)
                        for antrian in antrian_devices:
                            prog = self._devices_progress[antrian.device_id]
                            prog.sisa_detik = sisa
                            prog.progress_persen = int(min(100, (berlalu / durasi_detik) * 100)) if durasi_detik else 100
                            self.progres_device.emit(antrian.device_id, vars(prog))
                        # Polling singkat (bukan 1 detik penuh) supaya saat stop_event
                        # diset, loop ini juga langsung keluar begitu semua thread
                        # tugas_device selesai (yang sekarang berhenti dalam <=0.2 detik).
                        time.sleep(0.2 if self._stop_event.is_set() else 1)

                    for t in threads:
                        t.join()

                    if self._stop_event.is_set():
                        for antrian in antrian_devices:
                            prog = self._devices_progress[antrian.device_id]
                            prog.status = "Stopped"
                            self.device_manager.tandai_status_runtime(antrian.device_id, "Offline")
                            self.progres_device.emit(antrian.device_id, vars(prog))
                        break

                    for antrian in antrian_devices:
                        prog = self._devices_progress[antrian.device_id]
                        prog.status = "Waiting"
                        prog.progress_persen = 100
                        prog.sisa_detik = 0
                        self.device_manager.tandai_status_runtime(antrian.device_id, "Waiting")
                        self.progres_device.emit(antrian.device_id, vars(prog))

                    sukses_sesi = sum(1 for v in hasil_dict.values() if v)
                    logger.log(
                        f"Sesi {sesi+1}: {sukses_sesi}/{len(devices_aktif)} HP sukses "
                        f"| Total: sukses={self.statistik.total_sukses} gagal={self.statistik.total_gagal}",
                        "stat"
                    )
                    self.progres_global.emit(sesi + 1, jumlah_sesi)

                tulis_log(f"PUTARAN {putaran} SELESAI", "INFO")
                logger.log(f"Putaran {putaran} selesai.", "sukses")
                self.putaran_selesai.emit(putaran)

        finally:
            self.statistik.tampilkan_ringkasan_log()
            tulis_log("SESI BERAKHIR", "INFO")
            self.sedang_berjalan = False
            self.status_berubah.emit("berhenti")
            self.automation_selesai.emit()

    def get_progress_semua_device(self) -> Dict[str, DeviceProgress]:
        return dict(self._devices_progress)
