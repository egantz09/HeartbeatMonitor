# ui/tabs/config_tab.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton, QLabel,
    QComboBox, QListWidget, QListWidgetItem, QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt

from core.config import Config


class ConfigTab(QWidget):

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)

        # --- Formulario general ---
        form = QFormLayout()

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

        lay.addLayout(form)

        # --- Lista de hosts ---
        lbl_hosts = QLabel("Hosts a monitorear (ping):")
        lbl_hosts.setStyleSheet("font-weight: bold; margin-top: 10px;")
        lay.addWidget(lbl_hosts)

        self.lst_hosts = QListWidget()
        self.lst_hosts.setMaximumHeight(160)
        lay.addWidget(self.lst_hosts)

        # Botones de gestión de hosts
        btn_row = QHBoxLayout()
        btn_add = QPushButton("Añadir")
        btn_add.clicked.connect(self._add_host)
        btn_edit = QPushButton("Editar")
        btn_edit.clicked.connect(self._edit_host)
        btn_del = QPushButton("Eliminar")
        btn_del.clicked.connect(self._del_host)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        # --- Botón guardar ---
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self._save)
        lay.addWidget(btn_save)

        self.lbl_info = QLabel("")
        self.lbl_info.setStyleSheet("color: #888;")
        lay.addWidget(self.lbl_info)
        lay.addStretch()
    # ------------------------------------------------------------------

    def _on_ping_toggled(self, checked: bool):
        """Habilita o deshabilita los controles de ping según el toggle."""
        self.spn_ping.setEnabled(checked)
        self.lst_hosts.setEnabled(checked)
        # Los botones de la lista también:
        for b in self.findChildren(QPushButton):
            if b.text() in ("Añadir", "Editar", "Eliminar"):
                b.setEnabled(checked)

    # ------------------------------------------------------------------
    def _load(self):
        cfg = Config.load()
        self.cmb_theme.setCurrentText(cfg.get("theme", "dark"))
        self.chk_notif.setChecked(cfg.get("notifications_enabled", True))
        self.chk_evlog.setChecked(cfg.get("read_event_log", True))
        self.spn_ping.setValue(int(cfg.get("ping_interval", 60)))
        self.chk_ping.setChecked(cfg.get("ping_enabled", True))
        self._on_ping_toggled(cfg.get("ping_enabled", True))

        self.lst_hosts.clear()
        for h in cfg.get("ping_hosts", []):
            self.lst_hosts.addItem(QListWidgetItem(h))

    # ------------------------------------------------------------------
    def _add_host(self):
        text, ok = QInputDialog.getText(
            self, "Añadir host",
            "IP o dominio (ej. 8.8.8.8, google.com):"
        )
        if ok and text.strip():
            text = text.strip()
            # Evitar duplicados
            for i in range(self.lst_hosts.count()):
                if self.lst_hosts.item(i).text() == text:
                    QMessageBox.warning(self, "Duplicado",
                                        f"'{text}' ya está en la lista.")
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
        if not item:
            return
        row = self.lst_hosts.row(item)
        self.lst_hosts.takeItem(row)

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
        Config.set("ping_interval", self.spn_ping.value())
        Config.set("ping_hosts", hosts)
        Config.set("ping_enabled", self.chk_ping.isChecked())

        self.lbl_info.setText(
            "Guardado. Los cambios de pings se aplican en el próximo ciclo."
        )
        QMessageBox.information(self, "Configuración",
                                "Configuración guardada correctamente.")