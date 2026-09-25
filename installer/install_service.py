"""
Instalación como servicio de Windows con NSSM (recomendado).

Uso:
    python installer/install_service.py install
    python installer/install_service.py remove
    python installer/install_service.py status

Requiere nssm.exe en PATH o en la misma carpeta.
"""

import subprocess
import sys
from pathlib import Path

SERVICE_NAME = "HeartbeatMonitor"
EXE_NAME = "HeartbeatMonitor.exe"


def _exe_path() -> Path:
    # Supone que el .exe está en dist/HeartbeatMonitor/
    return Path(__file__).resolve().parent.parent / "dist" / "HeartbeatMonitor" / EXE_NAME


def _nssm(*args):
    return subprocess.run(["nssm", *args], capture_output=True, text=True)


def install():
    exe = _exe_path()
    if not exe.exists():
        print(f"[!] No se encontró {exe}. Compila primero con PyInstaller.")
        sys.exit(1)

    _nssm("install", SERVICE_NAME, str(exe))
    _nssm("set", SERVICE_NAME, "Start", "SERVICE_AUTO_START")
    _nssm("set", SERVICE_NAME, "AppExit", "Default", "Restart")
    _nssm("set", SERVICE_NAME, "AppRestartDelay", "5000")
    _nssm("set", SERVICE_NAME, "AppStdout", str(exe.parent / "service_out.log"))
    _nssm("set", SERVICE_NAME, "AppStderr", str(exe.parent / "service_err.log"))
    _nssm("start", SERVICE_NAME)
    print(f"[+] Servicio '{SERVICE_NAME}' instalado y arrancado.")


def remove():
    _nssm("stop", SERVICE_NAME)
    _nssm("remove", SERVICE_NAME, "confirm")
    print(f"[-] Servicio '{SERVICE_NAME}' eliminado.")


def status():
    r = _nssm("status", SERVICE_NAME)
    print(r.stdout or r.stderr)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"install": install, "remove": remove, "status": status}.get(cmd, status)()