# main.py
import sys
import time
import logging

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

from core.constants import (
    LOGS_DIR, HEARTBEAT_INTERVAL, BASE_DIR,
    APP_NAME, APP_AUTHOR, APP_EMAIL, APP_VERSION, APP_TITLE,
)
from core.config import Config
from core.database import Database
from core.monitor import HeartbeatMonitor
from core.startup import enable_startup
from core.shutdown_handler import install as install_shutdown_handler
from core import power_filter

from services.scheduler import BackgroundWorker
from services.notifier import notifier

from ui.main_window import MainWindow
from ui.tray import TrayIcon
from ui.theme import apply_theme


# ----------------------------------------------------------------------
# Splash
# ----------------------------------------------------------------------
def _make_splash() -> QSplashScreen:
    W, H = 560, 340

    pm = QPixmap(W, H)
    pm.fill(QColor("#1F4E78"))

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    logo_path = BASE_DIR / "assets" / "icon.png"
    text_top = 110
    if logo_path.exists():
        logo = QPixmap(str(logo_path))
        if not logo.isNull():
            logo = logo.scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap((W - logo.width()) // 2, 30, logo)
            text_top = 30 + logo.height() + 16

    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    p.drawText(0, text_top, W, 40,
               Qt.AlignmentFlag.AlignHCenter, APP_NAME)

    p.setPen(QColor("#CFE2F3"))
    p.setFont(QFont("Segoe UI", 11))
    p.drawText(0, text_top + 50, W, 22,
               Qt.AlignmentFlag.AlignHCenter,
               f"Creada por {APP_AUTHOR}")
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(0, text_top + 72, W, 22,
               Qt.AlignmentFlag.AlignHCenter, APP_EMAIL)

    p.setPen(QColor("#8FAFC7"))
    p.setFont(QFont("Segoe UI", 8))
    p.drawText(0, H - 28, W, 20,
               Qt.AlignmentFlag.AlignHCenter,
               f"v{APP_VERSION}  —  Iniciando...")
    p.end()

    splash = QSplashScreen(pm, Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    return splash


# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
def setup_logging():
    logging.basicConfig(
        filename=LOGS_DIR / "app.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main():
    setup_logging()
    logging.info(f"Iniciando {APP_NAME} v{APP_VERSION}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_AUTHOR)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)

    # Config + tema
    cfg = Config.load()
    apply_theme(app, cfg.get("theme", "dark"))

    # Splash
    splash = _make_splash()
    splash.show()
    app.processEvents()

    t0 = time.time()

    enable_startup()
    app.processEvents()

    Database.init()
    Database.init_ping()
    app.processEvents()

    try:
        power_filter.install(app)
    except Exception as e:
        logging.warning(f"power_filter: {e}")
    app.processEvents()

    monitor = HeartbeatMonitor()
    monitor.startup_check()
    app.processEvents()

    # GUI
    window = MainWindow()
    tray = TrayIcon(window)
    window.tray = tray
    tray.show()

    notifier.set_tray(tray)

    window.show()
    app.processEvents()

    # Splash mínimo 1.2 s
    elapsed_ms = int((time.time() - t0) * 1000)
    remaining = max(2500 - elapsed_ms, 1200)
    QTimer.singleShot(remaining, lambda: splash.finish(window))

    install_shutdown_handler()

    # Heartbeat
    timer = QTimer()
    timer.timeout.connect(monitor.heartbeat)
    timer.start(HEARTBEAT_INTERVAL * 1000)

    # Worker de fondo (pings multi-host + medianoche)
    worker = BackgroundWorker()
    worker.summary_ready.connect(
        lambda r: logging.info(f"Resumen: {r}")
    )
    worker.ping_ready.connect(
        lambda r: logging.debug(f"Pings: {list(r.keys())}")
    )
    window._worker = worker

    sys.exit(app.exec())


if __name__ == "__main__":
    main()