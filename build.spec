# build.spec - Modo ONEFILE
# Compilar con:  pyinstaller build.spec --noconfirm --clean

from pathlib import Path

block_cipher = None
PROJECT_ROOT = Path(SPECPATH).resolve()

# =====================================================================
# Assets a embeber dentro del .exe
# =====================================================================
datas = []
assets_dir = PROJECT_ROOT / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "assets"))

# =====================================================================
# Imports que PyInstaller no detecta automaticamente
# =====================================================================
hidden_imports = [
    # Windows API
    "win32api",
    "win32con",
    "win32gui",
    "win32evtlog",
    "win32evtlogutil",

    # PyQt6 (por si acaso)
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",

    # Matplotlib embebido
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",

    # ReportLab (fuentes)
    "reportlab.pdfbase._fontdata",
    "reportlab.pdfbase.ttfonts",
    "reportlab.pdfbase.pdfmetrics",

    # Modulos propios (por si el analisis estatico falla)
    "core.monitor",
    "core.config",
    "core.analytics",
    "core.event_log",
    "core.metrics",
    "core.summary",
    "core.excel_manager",
    "core.startup",
    "core.shutdown_handler",
    "core.power_filter",
    "core.state_manager",
    "core.database",
    "services.notifier",
    "services.scheduler",
    "services.pdf_export",
    "ui.theme",
    "ui.charts",
    "ui.tray",
    "ui.main_window",
    "ui.tabs.dashboard_tab",
    "ui.tabs.events_tab",
    "ui.tabs.analytics_tab",
    "ui.tabs.metrics_tab",
    "ui.tabs.config_tab",

    # Base de datos
    "sqlite3",
]

# =====================================================================
# Modulos que NO queremos (reducen tamano)
# =====================================================================
excludes = [
    "tkinter",
    "PyQt5",
    "PySide2",
    "PySide6",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
    "numpy.testing",
    "matplotlib.tests",
]

# =====================================================================
# Version info (para las propiedades del .exe en Windows)
# =====================================================================
version_info = """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(2, 0, 0, 0),
    prodvers=(2, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'Soluciones Melis'),
         StringStruct('FileDescription', 'HeartbeatMonitor - Monitor de uptime'),
         StringStruct('FileVersion', '2.0.0.0'),
         StringStruct('InternalName', 'HeartbeatMonitor'),
         StringStruct('LegalCopyright', 'Copyright 2026 Soluciones Melis'),
         StringStruct('OriginalFilename', 'HeartbeatMonitor.exe'),
         StringStruct('ProductName', 'HeartbeatMonitor'),
         StringStruct('ProductVersion', '2.0.0.0')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

# Guardar el version_info en un archivo temporal
version_file = PROJECT_ROOT / "version_info.txt"
version_file.write_text(version_info, encoding="utf-8")

# =====================================================================
# Analisis
# =====================================================================
a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# =====================================================================
# EXE - modo ONEFILE (todo dentro de un solo archivo)
# =====================================================================
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="HeartbeatMonitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX desactivado: los .exe empaquetados con UPX disparan falsos
    # positivos de antivirus con mucha frecuencia.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets_dir / "icon.ico") if (assets_dir / "icon.ico").exists() else None,
    version=str(version_file),
)