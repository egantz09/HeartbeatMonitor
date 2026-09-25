# core/constants.py
import sys
from pathlib import Path

# =====================================================================
# Identidad de la aplicación
# =====================================================================
APP_NAME    = "HeartbeatMonitor"
APP_AUTHOR  = "Soluciones Melis"
APP_EMAIL   = "solucionesmelis@gmail.com"
APP_CREDIT  = f"Creada por {APP_AUTHOR} | {APP_EMAIL}"
APP_VERSION = "2.0"
APP_TITLE   = f"{APP_NAME} - {APP_CREDIT}"

# =====================================================================
# Intervalos
# =====================================================================
HEARTBEAT_INTERVAL = 60                              # segundos
POWER_LOSS_THRESHOLD = HEARTBEAT_INTERVAL * 2.5      # 150 s

# =====================================================================
# Tipos de evento
# =====================================================================
EVENT_BOOT          = "BOOT"
EVENT_SHUTDOWN      = "SHUTDOWN"
EVENT_POWER_LOSS    = "POWER_LOSS"
EVENT_SUSPEND       = "SUSPEND"
EVENT_RESUME        = "RESUME"
EVENT_HEARTBEAT     = "HEARTBEAT"      # solo en state.json
EVENT_KERNEL_POWER  = "KERNEL_POWER"   # Event Log ID 41
EVENT_HW_ALERT      = "HW_ALERT"
EVENT_NET_DOWN      = "NET_DOWN"
EVENT_NET_UP        = "NET_UP"

# =====================================================================
# Configuración por defecto
# =====================================================================
DEFAULT_PING_HOSTS    = ["8.8.8.8", "1.1.1.1"]
DEFAULT_PING_INTERVAL = 60
DEFAULT_DISK_THRESHOLD = 90.0
DEFAULT_RAM_THRESHOLD  = 90.0
DEFAULT_CPU_THRESHOLD  = 90.0

# =====================================================================
# Temas
# =====================================================================
THEME_DARK  = "dark"
THEME_LIGHT = "light"

# =====================================================================
# Rutas (compatibles con desarrollo y PyInstaller onefile)
# =====================================================================
if getattr(sys, "frozen", False):
    # Dentro del .exe: BASE_DIR es la carpeta real del ejecutable
    # (donde se guardan datos persistentes)
    BASE_DIR = Path(sys.executable).resolve().parent
    # BUNDLE_DIR es la carpeta temporal donde PyInstaller extrae los assets
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    # Modo desarrollo
    BASE_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DIR = BASE_DIR

# Datos persistentes (junto al .exe / raíz del proyecto)
DATA_DIR    = BASE_DIR / "data"
LOGS_DIR    = DATA_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
STATE_FILE  = DATA_DIR / "state.json"
DB_FILE     = DATA_DIR / "heartbeat.db"

# Assets embebidos en el bundle (iconos, etc.)
ASSETS_DIR  = BUNDLE_DIR / "assets"

# Crear directorios necesarios
for _d in (DATA_DIR, LOGS_DIR, REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)