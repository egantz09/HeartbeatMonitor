# ui/theme.py
"""
Aplicación de tema (dark / light) a la QApplication.
"""
import logging

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

log = logging.getLogger(__name__)


# =====================================================================
# Paletas
# =====================================================================
def _dark_palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(37, 37, 38))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.Base,            QColor(28, 28, 30))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(45, 45, 48))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(45, 45, 48))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.Button,          QColor(53, 53, 55))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor(255, 80, 80))
    pal.setColor(QPalette.ColorRole.Link,            QColor(80, 160, 255))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(38, 79, 120))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    # Estados deshabilitados
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.Text, QColor(120, 120, 120))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.ButtonText, QColor(120, 120, 120))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.WindowText, QColor(120, 120, 120))
    return pal


def _light_palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(240, 240, 240))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(30, 30, 30))
    pal.setColor(QPalette.ColorRole.Base,            QColor(255, 255, 255))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(245, 245, 245))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(255, 255, 240))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(30, 30, 30))
    pal.setColor(QPalette.ColorRole.Text,            QColor(30, 30, 30))
    pal.setColor(QPalette.ColorRole.Button,          QColor(230, 230, 230))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(30, 30, 30))
    pal.setColor(QPalette.ColorRole.BrightText,      QColor(200, 40, 40))
    pal.setColor(QPalette.ColorRole.Link,            QColor(20, 90, 180))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(31, 78, 120))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return pal


# =====================================================================
# Stylesheets
# =====================================================================
_STYLESHEET_DARK = """
QToolTip {
    color: #DCDCDC;
    background-color: #2D2D30;
    border: 1px solid #3F3F46;
    padding: 4px;
}
QHeaderView::section {
    background-color: #353538;
    color: #DCDCDC;
    border: 0;
    padding: 5px 8px;
    font-weight: bold;
}
QTableWidget {
    gridline-color: #3F3F46;
    selection-background-color: #1F4E78;
    selection-color: #FFFFFF;
}
QTabWidget::pane {
    border: 1px solid #3F3F46;
    top: -1px;
}
QTabBar::tab {
    background: #353538;
    color: #DCDCDC;
    padding: 7px 16px;
    border: 1px solid #3F3F46;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1F4E78;
    color: #FFFFFF;
    border-color: #1F4E78;
}
QTabBar::tab:hover:!selected {
    background: #45454A;
}
QGroupBox {
    border: 1px solid #3F3F46;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QScrollBar:vertical {
    background: #2D2D30;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #555558;
    min-height: 20px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #6C6C70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #2D2D30;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #555558;
    min-width: 20px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background: #6C6C70;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QPushButton {
    background-color: #353538;
    border: 1px solid #4A4A4F;
    border-radius: 4px;
    padding: 6px 12px;
    color: #DCDCDC;
}
QPushButton:hover {
    background-color: #3F3F44;
    border-color: #5A5A60;
}
QPushButton:pressed {
    background-color: #1F4E78;
}
QPushButton:disabled {
    color: #707070;
    background-color: #2D2D30;
}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit {
    background-color: #2D2D30;
    border: 1px solid #4A4A4F;
    border-radius: 4px;
    padding: 4px 6px;
    color: #DCDCDC;
}
QComboBox:disabled, QLineEdit:disabled, QSpinBox:disabled,
QDoubleSpinBox:disabled, QDateEdit:disabled {
    color: #707070;
    background-color: #282828;
}
QComboBox QAbstractItemView {
    background-color: #2D2D30;
    color: #DCDCDC;
    selection-background-color: #1F4E78;
}
QListWidget {
    background-color: #2D2D30;
    border: 1px solid #4A4A4F;
    border-radius: 4px;
}
"""

_STYLESHEET_LIGHT = """
QTabWidget::pane {
    border: 1px solid #CCCCCC;
    top: -1px;
}
QTabBar::tab {
    background: #E8E8E8;
    color: #333333;
    padding: 7px 16px;
    border: 1px solid #CCCCCC;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #1F4E78;
    color: #FFFFFF;
    border-color: #1F4E78;
}
QTabBar::tab:hover:!selected {
    background: #D5D5D5;
}
QGroupBox {
    border: 1px solid #CCCCCC;
    border-radius: 5px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
"""


# =====================================================================
# API
# =====================================================================
def apply_theme(app, theme: str):
    """
    Aplica el tema a la QApplication.
    `theme` puede ser 'dark' o 'light'.
    """
    app.setStyle("Fusion")

    if theme == "dark":
        app.setPalette(_dark_palette())
        app.setStyleSheet(_STYLESHEET_DARK)
    else:
        app.setPalette(_light_palette())
        app.setStyleSheet(_STYLESHEET_LIGHT)

    log.info(f"Tema aplicado: {theme}")