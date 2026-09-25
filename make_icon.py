"""
make_icon.py — Genera assets/icon.ico y assets/icon.png
Un ícono de "latido/uptime": círculo azul + onda ECG blanca.
Sin dependencias externas.
"""
import struct
import zlib
from pathlib import Path

SIZE = 256
BG   = (0x1F, 0x4E, 0x78, 0xFF)   # azul corporativo
FG   = (0xFF, 0xFF, 0xFF, 0xFF)   # blanco para la onda


def _inside_circle(x, y, size, radius, cx, cy):
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


def _on_wave(x, y, size):
    """Onda ECG simple: línea base + pico triangular."""
    cy = size // 2
    thickness = 14

    # Segmento central
    if size * 0.12 <= x <= size * 0.88:
        # Pico arriba
        if size * 0.35 <= x <= size * 0.42:
            t = (x - size * 0.35) / (size * 0.42 - size * 0.35)
            y_top = cy - 90 + t * 0
            if cy - 90 <= y <= cy + thickness // 2:
                return True
        # Pico abajo
        if size * 0.58 <= x <= size * 0.65:
            if cy - thickness // 2 <= y <= cy + 90:
                return True
        # Línea base
        if abs(y - cy) <= thickness // 2:
            return True
    return False


def render_rgba():
    """Devuelve un buffer RGBA (bytes) de SIZE x SIZE."""
    cx = cy = SIZE / 2
    radius = SIZE / 2 - 4
    buf = bytearray()

    for y in range(SIZE):
        # Filtro PNG: 0 (None) al inicio de cada fila
        buf.append(0)
        for x in range(SIZE):
            if _inside_circle(x, y, SIZE, radius, cx, cy):
                if _on_wave(x, y, SIZE):
                    buf.extend(FG)
                else:
                    buf.extend(BG)
            else:
                buf.extend((0, 0, 0, 0))
    return bytes(buf)


def png_bytes():
    """Construye un PNG RGBA en memoria."""
    raw = render_rgba()

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return c + struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(
        ">IIBBBBB",
        SIZE, SIZE,
        8,        # bit depth
        6,        # color type RGBA
        0, 0, 0   # compression, filter, interlace
    )
    idat = zlib.compress(raw, 9)

    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def ico_bytes(png_data):
    """
    ICO con un único tamaño (256x256).
    El ICONDIR + ICONDIRENTRY apuntan al PNG embebido.
    """
    width  = 0   # 0 significa 256 en ICO
    height = 0
    color_count = 0
    reserved = 0
    planes  = 1
    bpp     = 32
    size    = len(png_data)
    offset  = 6 + 16  # cabecera + una entrada

    header = struct.pack("<HHH", 0, 1, 1)  # reserved, type=1 (icon), count
    entry  = struct.pack(
        "<BBBBHHII",
        width, height, color_count, reserved,
        planes, bpp,
        size, offset,
    )
    return header + entry + png_data


def main():
    assets = Path("assets")
    assets.mkdir(exist_ok=True)

    png = png_bytes()
    (assets / "icon.png").write_bytes(png)
    (assets / "icon.ico").write_bytes(ico_bytes(png))

    print(f"[+] Generado: {assets/'icon.png'}  ({len(png)} bytes)")
    print(f"[+] Generado: {assets/'icon.ico'}  ({len(ico_bytes(png))} bytes)")


if __name__ == "__main__":
    main()