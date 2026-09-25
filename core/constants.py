from pathlib import Path
import sys

# --- Identidad de la aplicación ---
APP_NAME    = "HeartbeatMonitor"
APP_AUTHOR  = "Soluciones Melis"
APP_EMAIL   = "solucionesmelis@gmail.com"
APP_CREDIT  = f"Creada por {APP_AUTHOR} | {APP_EMAIL}"
APP_VERSION = "2.0"
APP_TITLE   = f"{APP_NAME} - {APP_CREDIT}"

# --- Intervalos ---
HEARTBEAT_INTERVAL = 60
POWER_LOSS_THRESHOLD = HEARTBEAT_INTERVAL * 2.5   # 150 s

# --- Tipos de evento ---
EVENT_BOOT       = "BOOT"
EVENT_SHUTDOWN   = "SHUTDOWN"
EVENT_POWER_LOSS = "POWER_LOSS"
EVENT_SUSPEND    = "SUSPEND"
EVENT_RESUME     = "RESUME"
EVENT_HEARTBEAT  = "HEARTBEAT"

# --- Rutas ---
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR    = BASE_DIR / "data"
LOGS_DIR    = DATA_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
STATE_FILE  = DATA_DIR / "state.json"
DB_FILE     = DATA_DIR / "heartbeat.db"

for d in (DATA_DIR, LOGS_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- Config por defecto ---
DEFAULT_PING_HOST = "8.8.8.8"
DEFAULT_PING_INTERVAL = 60          # segundos
DEFAULT_METRICS_INTERVAL = 60       # segundos
DEFAULT_DISK_THRESHOLD = 90.0       # % de uso de disco que dispara alerta
DEFAULT_RAM_THRESHOLD = 90.0        # %
DEFAULT_CPU_THRESHOLD = 90.0        # %

# --- Temas ---
THEME_DARK  = "dark"
THEME_LIGHT = "light"

# --- Tipos de evento adicionales ---
EVENT_HW_ALERT   = "HW_ALERT"
EVENT_NET_DOWN   = "NET_DOWN"
EVENT_NET_UP     = "NET_UP"
EVENT_KERNEL_PWR = "KERNEL_POWER"

# --- Ping multi-host ---
DEFAULT_PING_HOSTS = ["8.8.8.8", "1.1.1.1"]
DEFAULT_PING_INTERVAL = 60