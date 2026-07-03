

from __future__ import annotations

import subprocess
from typing import List, Tuple
from urllib.parse import urlparse, parse_qs


def jalankan_adb(perintah: List[str], device_id: str | None = None) -> Tuple[str, str]:
    """Menjalankan perintah ADB mentah. Logika asli, tidak diubah."""
    base = ["adb"]
    if device_id:
        base += ["-s", device_id]
    hasil = subprocess.run(base + perintah, capture_output=True, text=True)
    return hasil.stdout.strip(), hasil.stderr.strip()


def get_daftar_device() -> List[str]:
    """Mengambil daftar device dengan status 'device' (online & authorized).

    Logika asli dipertahankan: hanya baris yang mengandung '\\tdevice'
    yang dianggap device aktif/siap dipakai.
    """
    out, _ = jalankan_adb(["devices"])
    baris = out.splitlines()[1:]
    devices = []
    for b in baris:
        if "\tdevice" in b:
            devices.append(b.split("\t")[0].strip())
    return devices


def get_daftar_device_detail() -> List[Tuple[str, str]]:
    """Tambahan untuk GUI: mengambil SEMUA device beserta status mentahnya
    (device / unauthorized / offline), agar GUI bisa menampilkan notifikasi
    device unauthorized/offline. Tidak mengubah get_daftar_device() asli.
    """
    out, _ = jalankan_adb(["devices"])
    baris = out.splitlines()[1:]
    hasil = []
    for b in baris:
        b = b.strip()
        if not b or "\t" not in b:
            continue
        serial, status = b.split("\t", 1)
        hasil.append((serial.strip(), status.strip()))
    return hasil

def ambil_video_id(url):
    try:
        parsed = urlparse(url)

        if "youtu.be" in parsed.netloc:
            return parsed.path.strip("/")

        if "youtube.com" in parsed.netloc or "m.youtube.com" in parsed.netloc:

            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [None])[0]

            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/")[2]

            if parsed.path.startswith("/live/"):
                return parsed.path.split("/")[2]

    except Exception:
        pass

    return None

def buka_url_di_device(device_id, url):

    video_id = ambil_video_id(url)

    if video_id:
        tujuan = f"vnd.youtube:{video_id}"

        perintah = [
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            tujuan
        ]
    else:
        perintah = [
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            url,
            "com.android.chrome"
        ]

    _, err = jalankan_adb(perintah, device_id)
    return "Error" not in err

def paksa_putar_video(device_id: str) -> None:
    """Logika asli dipertahankan (tap tengah layar)."""
    import time
    jalankan_adb(["shell", "input", "tap", "540", "960"], device_id)
    time.sleep(0.5)


def scroll_halaman(device_id: str) -> None:
    """Logika asli dipertahankan."""
    jalankan_adb(["shell", "input", "swipe", "540", "900", "540", "400", "800"], device_id)


def kembali_ke_home(device_id: str) -> None:
    """Logika asli dipertahankan."""
    jalankan_adb(["shell", "input", "keyevent", "KEYCODE_HOME"], device_id)


def get_model_device(device_id: str) -> str:
    """Logika asli dipertahankan."""
    model, _ = jalankan_adb(["shell", "getprop", "ro.product.model"], device_id)
    return model or "Unknown"


def get_baterai_device(device_id: str) -> str:
    """Logika asli dipertahankan."""
    battery, _ = jalankan_adb(["shell", "dumpsys", "battery"], device_id)
    if battery:
        for baris in battery.splitlines():
            if "level" in baris:
                return baris.split(":")[-1].strip() + "%"
    return "?"


# ── Fungsi tambahan kecil khusus kebutuhan tampilan GUI (bukan bagian
#    logika automation, jadi aman ditambahkan tanpa menyentuh algoritma) ──

def get_android_version(device_id: str) -> str:
    """Mengambil versi Android device, dibutuhkan kolom 'Android' di tabel Perangkat."""
    versi, _ = jalankan_adb(["shell", "getprop", "ro.build.version.release"], device_id)
    return versi or "?"


def restart_adb_server() -> Tuple[str, str]:
    """Restart ADB server (adb kill-server && adb start-server), dibutuhkan
    oleh tombol toolbar 'Restart ADB'."""
    subprocess.run(["adb", "kill-server"], capture_output=True, text=True)
    hasil = subprocess.run(["adb", "start-server"], capture_output=True, text=True)
    return hasil.stdout.strip(), hasil.stderr.strip()
