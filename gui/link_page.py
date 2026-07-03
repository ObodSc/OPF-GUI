

from __future__ import annotations

import os
import shutil

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from gui.widgets import JudulHalaman

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LINK_FILE = os.path.join(DATA_DIR, "listlink.txt")


def baca_link(nama_file: str = LINK_FILE) -> list[str]:
    """Logika asli dari fungsi baca_link() versi CLI, dipertahankan."""
    if not os.path.exists(nama_file):
        return []
    links = []
    with open(nama_file, "r", encoding="utf-8") as f:
        for baris in f:
            baris = baris.strip()
            if baris and not baris.startswith("#"):
                links.append(baris)
    return links


def simpan_link(links: list[str], nama_file: str = LINK_FILE) -> None:
    """Menulis ulang listlink.txt, format sama persis dengan versi CLI."""
    with open(nama_file, "w", encoding="utf-8") as f:
        f.write("# Daftar Link Video Website Anda\n")
        for link in links:
            f.write(link + "\n")


class LinkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.addWidget(JudulHalaman("Daftar Link", "Kelola link video yang akan dijalankan"))
        header_row.addStretch()

        self.input_cari = QLineEdit()
        self.input_cari.setPlaceholderText("Cari link...")
        self.input_cari.setFixedWidth(220)
        self.input_cari.textChanged.connect(self._filter_tabel)
        header_row.addWidget(self.input_cari)
        layout.addLayout(header_row)

        tombol_row = QHBoxLayout()
        self.btn_tambah = QPushButton("➕  Tambah")
        self.btn_tambah.setObjectName("btnPrimary")
        self.btn_edit = QPushButton("✏️  Edit")
        self.btn_hapus = QPushButton("🗑  Hapus")
        self.btn_hapus.setObjectName("btnDanger")
        self.btn_import = QPushButton("📂  Import TXT")

        self.btn_tambah.clicked.connect(self.tambah_link)
        self.btn_edit.clicked.connect(self.edit_link)
        self.btn_hapus.clicked.connect(self.hapus_link)
        self.btn_import.clicked.connect(self.import_txt)

        for btn in (self.btn_tambah, self.btn_edit, self.btn_hapus, self.btn_import):
            tombol_row.addWidget(btn)
        tombol_row.addStretch()
        layout.addLayout(tombol_row)

        self.tabel = QTableWidget(0, 2)
        self.tabel.setHorizontalHeaderLabels(["No", "URL Link"])
        self.tabel.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabel.verticalHeader().setVisible(False)
        self.tabel.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabel.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabel.setAlternatingRowColors(True)
        layout.addWidget(self.tabel)

        self.label_ringkasan = QLabel()
        self.label_ringkasan.setObjectName("subtitle")
        layout.addWidget(self.label_ringkasan)

        self.muat_ulang()

    def muat_ulang(self) -> None:
        links = baca_link()
        self.tabel.setRowCount(0)
        for i, link in enumerate(links):
            self.tabel.insertRow(i)
            self.tabel.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.tabel.setItem(i, 1, QTableWidgetItem(link))
        self.label_ringkasan.setText(f"Total link: {len(links)}")

    def _baris_terpilih(self) -> int | None:
        baris = self.tabel.currentRow()
        return baris if baris >= 0 else None

    def tambah_link(self) -> None:
        teks, ok = QInputDialog.getText(self, "Tambah Link", "Masukkan URL baru:")
        if not ok or not teks.strip():
            return
        teks = teks.strip()
        if not teks.startswith("http"):
            QMessageBox.warning(self, "URL Tidak Valid", "URL harus diawali dengan http/https.")
            return
        links = baca_link()
        links.append(teks)
        simpan_link(links)
        self.muat_ulang()

    def edit_link(self) -> None:
        baris = self._baris_terpilih()
        if baris is None:
            QMessageBox.information(self, "Info", "Pilih salah satu link terlebih dahulu.")
            return
        links = baca_link()
        lama = links[baris]
        teks, ok = QInputDialog.getText(self, "Edit Link", "Ubah URL:", text=lama)
        if not ok or not teks.strip():
            return
        teks = teks.strip()
        if not teks.startswith("http"):
            QMessageBox.warning(self, "URL Tidak Valid", "URL harus diawali dengan http/https.")
            return
        links[baris] = teks
        simpan_link(links)
        self.muat_ulang()

    def hapus_link(self) -> None:
        baris = self._baris_terpilih()
        if baris is None:
            QMessageBox.information(self, "Info", "Pilih salah satu link terlebih dahulu.")
            return
        links = baca_link()
        konfirmasi = QMessageBox.question(
            self, "Hapus Link", f"Hapus link:\n{links[baris]} ?"
        )
        if konfirmasi != QMessageBox.Yes:
            return
        links.pop(baris)
        simpan_link(links)
        self.muat_ulang()

    def import_txt(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import File TXT", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            link_baru = baca_link(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Gagal Import", str(e))
            return
        links = baca_link()
        ditambahkan = 0
        for l in link_baru:
            if l not in links:
                links.append(l)
                ditambahkan += 1
        simpan_link(links)
        self.muat_ulang()
        QMessageBox.information(self, "Import Selesai", f"{ditambahkan} link baru ditambahkan.")

    def _filter_tabel(self, teks: str) -> None:
        teks = teks.lower().strip()
        for row in range(self.tabel.rowCount()):
            item = self.tabel.item(row, 1)
            cocok = teks in item.text().lower() if item else False
            self.tabel.setRowHidden(row, not cocok)
