# main.py
"""
HeartbeatMonitor - Monitor de uptime y disponibilidad para Windows.
Punto de entrada de la aplicacion.

Creada por Soluciones Melis | solucionesmelis@gmail.com
"""
import sys
import time
import logging

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

from core.constants import (
    LOGS_DIR, HEARTBEAT_INTERVAL, ASSETS_DIR,
    APP_NAME, APP_AUTHOR, APP_EMAIL, APP_VERSION,
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


# =====================================================================
# Splash
# =====================================================================
def _make_splash() -> QSplashScreen:
    W, H = 560, 340

    pm = QPixmap(W, H)
    pm.fill(QColor("#1F4E78"))

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    logo_path = ASSETS_DIR / "icon.png"
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

    # Titulo
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
    p.drawText(0, text_top, W, 40,
               Qt.AlignmentFlag.AlignHCenter, APP_NAME)

    # Firma
    p.setPen(QColor("#CFE2F3"))
    p.setFont(QFont("Segoe UI", 11))
    p.drawText(0, text_top + 50, W, 22,
               Qt.AlignmentFlag.AlignHCenter,
               f"Creada por {APP_AUTHOR}")
    p.setFont(QFont("Segoe UI", 10))
    p.drawText(0, text_top + 72, W, 22,
               Qt.AlignmentFlag.AlignHCenter, APP_EMAIL)

    # Version
    p.setPen(QColor("#8FAFC7"))
    p.setFont(QFont("Segoe UI", 8))
    p.drawText(0, H - 28, W, 20,
               Qt.AlignmentFlag.AlignHCenter,
               f"v{APP_VERSION}  -  Iniciando...")
    p.end()

    splash = QSplashScreen(pm, Qt.WindowType.WindowStaysOnTopHint)
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    return splash


# =====================================================================
# Logging
# =====================================================================
def setup_logging():
    logging.basicConfig(
        filename=str(LOGS_DIR / "app.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


# =====================================================================
# main
# =====================================================================
def main():
    setup_logging()
    logging.info(f"Iniciando {APP_NAME} v{APP_VERSION}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_AUTHOR)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)

    # --- Config + tema ---
    cfg = Config.load()
    apply_theme(app, cfg.get("theme", "dark"))

    # --- Splash (lo antes posible) ---
    splash = _make_splash()
    splash.show()
    app.processEvents()

    t0 = time.time()

    # --- Autoarranque ---
    try:
        enable_startup()
    except Exception as e:
        logging.warning(f"No se pudo configurar autoarranque: {e}")
    app.processEvents()

    # --- Base de datos ---
    try:
        Database.init()
        Database.init_ping()
    except Exception as e:
        logging.error(f"Error inicializando base de datos: {e}")
    app.processEvents()

    # --- Filtro de eventos de energia (suspension / reanudacion) ---
    try:
        power_filter.install(app)
    except Exception as e:
        logging.warning(f"No se pudo instalar power_filter: {e}")
    app.processEvents()

    # --- Chequeo de arranque (corte electrico) ---
    try:
        monitor = HeartbeatMonitor()
        monitor.startup_check()
    except Exception as e:
        logging.error(f"Error en startup_check: {e}")
        # Fallback minimo para no romper la app
        from core.database import Database as DB
        DB.init()
        monitor = HeartbeatMonitor()
    app.processEvents()

    # --- GUI ---
    window = MainWindow()

    try:
        tray = TrayIcon(window)
        window.tray = tray
        tray.show()
        notifier.set_tray(tray)
    except Exception as e:
        logging.warning(f"No se pudo crear el tray: {e}")
        window.tray = None

    window.showMaximized()
    app.processEvents()

    # --- Splash: duracion minima garantizada ---
    elapsed_ms = int((time.time() - t0) * 1000)
    remaining = max(2500 - elapsed_ms, 1200)
    QTimer.singleShot(remaining, lambda: splash.finish(window))

    # --- Handler de cierre limpio ---
    try:
        install_shutdown_handler()
    except Exception as e:
        logging.warning(f"No se pudo instalar shutdown handler: {e}")

    # --- Heartbeat periodico ---
    timer = QTimer()
    timer.timeout.connect(monitor.heartbeat)
    timer.start(HEARTBEAT_INTERVAL * 1000)

    # --- Worker de fondo (pings multi-host + resumen medianoche) ---
    worker = BackgroundWorker()
    worker.summary_ready.connect(
        lambda r: logging.info(f"Resumen generado: {r}")
    )
    worker.ping_ready.connect(
        lambda r: logging.debug(f"Pings completados: {list(r.keys())}")
    )
    # Importante: guardar referencia para que el GC no destruya el worker
    window._worker = worker

    sys.exit(app.exec())


if __name__ == "__main__":
    main()