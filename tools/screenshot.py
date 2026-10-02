#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera docs/images/janela_principal.png para o README: cria uma pasta de demonstração com nomes
típicos de dados GIS, abre o app, faz uma busca e captura a janela.
Só Windows (usa a API Win32 PrintWindow). Uso: python tools/screenshot.py
"""
import ctypes
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import reperio as g  # noqa: E402

DEMO = os.path.join(os.environ.get("PUBLIC", tempfile.gettempdir()), "Banco_de_imagens")
OUT = os.path.join(ROOT, "docs", "images", "janela_principal.png")

FILES = []
for ano in (2019, 2020, 2021, 2022, 2023):
    for cena in ("226_068", "227_069", "228_070"):
        base = "LC08_L2SP_%s_%d0715" % (cena.replace("_", ""), ano)
        for banda in ("B2", "B3", "B4", "B5"):
            FILES.append("LANDSAT/%d/%s/%s_%s.TIF" % (ano, cena, base, banda))
        FILES.append("LANDSAT/%d/%s/%s_MTL.xml" % (ano, cena, base))
for mun in ("Cuiaba", "Sinop", "Rondonopolis", "Barra_do_Garcas"):
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        FILES.append("VETORES/limites/%s%s" % (mun, ext))
    FILES.append("SENTINEL/2023/%s/S2A_MSIL2A_20230812_%s_NDVI.tif" % (mun, mun))
FILES += ["MOSAICOS/IMAGENS_mosaico_2020.tif", "MOSAICOS/IMAGENS_mosaico_2021.tif",
          "MOSAICOS/IMAGENS_mosaico_2022.ecw", "DOCUMENTOS/Relatorio_IMAGENS_2022.pdf"]


def make_demo():
    shutil.rmtree(DEMO, ignore_errors=True)
    for i, rel in enumerate(FILES):
        p = os.path.join(DEMO, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.truncate((i % 9 + 1) * 13_000_000 if p.lower().endswith((".tif", ".ecw")) else 48_000)


def capture(hwnd, path):
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    hdc_win = user32.GetWindowDC(hwnd)
    hdc = gdi32.CreateCompatibleDC(hdc_win)
    bmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    gdi32.SelectObject(hdc, bmp)
    user32.PrintWindow(hwnd, hdc, 2)            # PW_RENDERFULLCONTENT

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                    ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                    ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                    ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]
    bi = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    bmp_path = path[:-4] + ".bmp"
    with open(bmp_path, "wb") as f:
        f.write(b"BM" + struct.pack("<IHHI", 54 + len(buf.raw), 0, 0, 54))
        f.write(bytes(bi))
        f.write(buf.raw)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(hdc)
    user32.ReleaseDC(hwnd, hdc_win)
    # BMP -> PNG com o .NET do próprio Windows
    ps = ("Add-Type -AssemblyName System.Drawing; $i=[Drawing.Image]::FromFile('%s'); "
          "$i.Save('%s',[Drawing.Imaging.ImageFormat]::Png); $i.Dispose()" % (bmp_path, path))
    subprocess.check_call(["powershell", "-NoProfile", "-Command", ps])
    os.remove(bmp_path)


def main():
    ctypes.windll.user32.SetProcessDPIAware()
    make_demo()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = tempfile.mkdtemp()
    g.LOG_PATH = os.path.join(tmp, "log.txt")
    idx = g.Index(os.path.join(tmp, "idx.sqlite"))
    root = g.tk.Tk()
    app = g.App(root, idx)
    root.geometry("1180x720+40+40")
    app.v_root.set(DEMO)
    app.v_pat.set("*.tif")
    app._start()
    t0 = time.time()
    while (app._running or not app._rcount) and time.time() - t0 < 20:
        root.update()
        time.sleep(0.02)
    app._sort("folder")
    kids = app.tree.get_children()
    app.tree.selection_set(kids[3:9])
    app._on_sel()
    for _ in range(30):
        root.update()
        time.sleep(0.03)
    capture(int(root.wm_frame(), 16), OUT)
    root.destroy()
    idx.close()
    shutil.rmtree(DEMO, ignore_errors=True)
    print("Captura: %s" % OUT)


if __name__ == "__main__":
    main()
