# ui/tabs/config_tab.py
"""
Configuracion general, hosts de ping y toggles.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QCheckBox, QPushButton, QLabel, QComboBox,
    QListWidget, QListWidgetItem, QMessageBox, QInputDialog,
    QGroupBox,
)
from PyQt6.QtCore import pyqtSignal

from core.config import Config

log = logging.getLogger(__name__)


class ConfigTab(QWidget):

    # Emitida al guardar: permite a otros componentes recargarse
    # (p. ej. reprogramar el intervalo de pings) sin reiniciar la app.
    config_saved = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load()

    # ------------------------------------------------------------------
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(12)

        # ---------- General ----------
        grp_gen = QGroupBox("General")
        form = QFormLayout(grp_gen)

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["dark", "light"])
        form.addRow("Tema:", self.cmb_theme)

        self.chk_notif = QCheckBox("Activar notificaciones de bandeja")
        form.addRow("", self.chk_notif)

        self.chk_evlog = QCheckBox("Leer Event Log de Windows (ID 41)")
        form.addRow("", self.chk_evlog)

        self.chk_ping = QCheckBox("Activar monitoreo de red (ping)")
        self.chk_ping.toggled.connect(self._on_ping_toggled)
        form.addRow("", self.chk_ping)

        self.spn_ping = QSpinBox()
        self.spn_ping.setRange(10, 3600)
        self.spn_ping.setSuffix(" s")
        form.addRow("Intervalo entre pings:", self.spn_ping)

        lay.addWidget(grp_gen)

        # ---------- Hosts ----------
        grp_hosts = QGroupBox("Hosts a monitorear (ping)")
        vl = QVBoxLayout(grp_hosts)

        self.lst_hosts = QListWidget()
        self.lst_hosts.setMaximumHeight(160)
        vl.addWidget(self.lst_hosts)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Anadir")
        self.btn_add.clicked.connect(self._add_host)
        self.btn_edit = QPushButton("Editar")
        self.btn_edit.clicked.connect(self._edit_host)
        self.btn_del = QPushButton("Eliminar")
        self.btn_del.clicked.connect(self._del_host)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_del)
        btn_row.addStretch()
        vl.addLayout(btn_row)

        lay.addWidget(grp_hosts)

        # ---------- Guardar ----------
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self._save)
        lay.addWidget(self.btn_save)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888;")
        lay.addWidget(self.lbl_info)
        lay.addStretch()

    # ------------------------------------------------------------------
    def _load(self):
        cfg = Config.load()

        self.cmb_theme.setCurrentText(cfg.get("theme", "dark"))
        self.chk_notif.setChecked(cfg.get("notifications_enabled", True))
        self.chk_evlog.setChecked(cfg.get("read_event_log", True))
        self.chk_ping.setChecked(cfg.get("ping_enabled", True))
        self.spn_ping.setValue(int(cfg.get("ping_interval", 60)))

        self.lst_hosts.clear()
        for h in cfg.get("ping_hosts", []):
            self.lst_hosts.addItem(QListWidgetItem(h))

        self._on_ping_toggled(self.chk_ping.isChecked())

    # ------------------------------------------------------------------
    def _on_ping_toggled(self, checked: bool):
        """Habilita/deshabilita los controles relacionados con ping."""
        self.spn_ping.setEnabled(checked)
        self.lst_hosts.setEnabled(checked)
        self.btn_add.setEnabled(checked)
        self.btn_edit.setEnabled(checked)
        self.btn_del.setEnabled(checked)

    # ------------------------------------------------------------------
    def _add_host(self):
        text, ok = QInputDialog.getText(
            self, "Anadir host",
            "IP o dominio (ej. 8.8.8.8, google.com):"
        )
        if ok and text.strip():
            text = text.strip()
            for i in range(self.lst_hosts.count()):
                if self.lst_hosts.item(i).text() == text:
                    QMessageBox.warning(
                        self, "Duplicado",
                        f"'{text}' ya esta en la lista."
                    )
                    return
            self.lst_hosts.addItem(QListWidgetItem(text))

    def _edit_host(self):
        item = self.lst_hosts.currentItem()
        if not item:
            return
        text, ok = QInputDialog.getText(
            self, "Editar host", "Nuevo valor:", text=item.text()
        )
        if ok and text.strip():
            item.setText(text.strip())

    def _del_host(self):
        item = self.lst_hosts.currentItem()
        if item:
            self.lst_hosts.takeItem(self.lst_hosts.row(item))

    # ------------------------------------------------------------------
    def _save(self):
        hosts = [
            self.lst_hosts.item(i).text().strip()
            for i in range(self.lst_hosts.count())
            if self.lst_hosts.item(i).text().strip()
        ]

        Config.set("theme", self.cmb_theme.currentText())
        Config.set("notifications_enabled", self.chk_notif.isChecked())
        Config.set("read_event_log", self.chk_evlog.isChecked())
        Config.set("ping_enabled", self.chk_ping.isChecked())
        Config.set("ping_interval", self.spn_ping.value())
        Config.set("ping_hosts", hosts)

        self.lbl_info.setText("Configuracion guardada.")
        self.config_saved.emit()
        QMessageBox.information(
            self, "Configuracion",
            "Configuracion guardada correctamente."
        )