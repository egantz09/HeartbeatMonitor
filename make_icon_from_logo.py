# make_icon_from_logo.py
"""
Convierte logo.png en assets/icon.ico (multitamaño)
y assets/icon.png (cuadrado, redimensionado).
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QImage
from PyQt6.QtCore import Qt, QSize


SOURCE = Path("logo.png")            # ← tu logo original
OUT_DIR = Path("assets")
SIZES = [16, 24, 32, 48, 64, 128, 256]   # tamaños dentro del .ico


def _square_pixmap(src: QPixmap, size: int) -> QPixmap:
    """Redimensiona manteniendo proporción y centra sobre un cuadrado transparente."""
    scaled = src.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(size, size)
    canvas.fill(Qt.GlobalColor.transparent)

    p = QPainter(canvas)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    p.drawPixmap(x, y, scaled)
    p.end()
    return canvas


def main():
    app = QApplication(sys.argv)   # requerido por QPixmap

    if not SOURCE.exists():
        print(f"[!] No se encontró {SOURCE}. Coloca tu logo.png en la raíz.")
        sys.exit(1)

    OUT_DIR.mkdir(exist_ok=True)

    src = QPixmap(str(SOURCE))
    if src.isNull():
        print(f"[!] No se pudo cargar {SOURCE}. ¿Es un PNG válido?")
        sys.exit(1)

    print(f"[i] Origen: {SOURCE}  ({src.width()}x{src.height()})")

    # --- icon.png cuadrado (256x256) ---
    png256 = _square_pixmap(src, 256)
    png_path = OUT_DIR / "icon.png"
    png256.save(str(png_path), "PNG")
    print(f"[+] {png_path}")

    # --- icon.ico multitamaño ---
    # Qt guarda ICO tomando el pixmap y generando un solo tamaño.
    # Para multitamaño real escribimos el ICO a mano (formato PNG-ICO).
    ico_path = OUT_DIR / "icon.ico"
    _write_multi_ico(src, ico_path, SIZES)
    print(f"[+] {ico_path}")


def _write_multi_ico(src: QPixmap, out_path: Path, sizes: list[int]):
    """
    Construye un .ico con múltiples entradas PNG embebidas.
    Formato: ICONDIR + N*(ICONDIRENTRY) + N*(PNG bytes)
    """
    import struct
    from io import BytesIO
    from PyQt6.QtCore import QBuffer, QByteArray

    # Renderizar cada tamaño y guardarlo como PNG en memoria
    png_blobs = []
    for s in sizes:
        pm = _square_pixmap(src, s)
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        pm.save(buf, "PNG")
        buf.close()
        png_blobs.append((s, bytes(ba)))

    # ICONDIR: reserved(2)=0, type(2)=1, count(2)=N
    header = struct.pack("<HHH", 0, 1, len(png_blobs))

    # Entradas: 16 bytes por imagen
    entries = b""
    offset = 6 + 16 * len(png_blobs)
    for s, blob in png_blobs:
        w = 0 if s >= 256 else s   # 0 significa 256 en ICO
        h = 0 if s >= 256 else s
        entries += struct.pack(
            "<BBBBHHII",
            w, h,
            0,    # color count (0 = truecolor)
            0,    # reserved
            1,    # planes
            32,   # bpp
            len(blob),
            offset,
        )
        offset += len(blob)

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(entries)
        for _, blob in png_blobs:
            f.write(blob)


if __name__ == "__main__":
    main()