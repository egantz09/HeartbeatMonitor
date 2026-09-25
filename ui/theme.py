# ui/theme.py
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt


def apply_theme(app, theme: str):
    if theme == "dark":
        _apply_dark(app)
    else:
        _apply_light(app)


def _apply_dark(app):
    app.setStyle("Fusion")

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

    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.Text, QColor(120, 120, 120))
    pal.setColor(QPalette.ColorGroup.Disabled,
                 QPalette.ColorRole.ButtonText, QColor(120, 120, 120))

    app.setPalette(pal)

    # Estilos adicionales
    app.setStyleSheet("""
        QToolTip {
            color: #DCDCDC;
            background-color: #2D2D30;
            border: 1px solid #3F3F46;
        }
        QHeaderView::section {
            background-color: #353538;
            color: #DCDCDC;
            border: 0;
            padding: 4px 8px;
        }
        QTableWidget {
            gridline-color: #3F3F46;
        }
        QTabWidget::pane {
            border: 1px solid #3F3F46;
        }
        QTabBar::tab {
            background: #353538;
            color: #DCDCDC;
            padding: 6px 14px;
            border: 0;
        }
        QTabBar::tab:selected {
            background: #1F4E78;
            color: white;
        }
    """)


def _apply_light(app):
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("""
        QTabBar::tab:selected {
            background: #1F4E78;
            color: white;
            padding: 6px 14px;
        }
        QTabBar::tab {
            padding: 6px 14px;
        }
    """)