#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta docs/images/reperio.ico (PNG dentro do ICO, aceito desde o Windows Vista)
a partir de docs/images/logo_{16,32,48,256}.png, gerados por tools/make_logo.ps1.
Também imprime o PNG de 64 px em base64 para o ícone da janela em reperio.py.
"""
import base64
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "docs", "images")


def main():
    sizes = (16, 32, 48, 256)
    pngs = [open(os.path.join(IMG, "logo_%d.png" % s), "rb").read() for s in sizes]
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries, data = b"", b""
    for s, png in zip(sizes, pngs):
        dim = 0 if s >= 256 else s
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    with open(os.path.join(IMG, "reperio.ico"), "wb") as f:
        f.write(header + entries + data)
    icon64 = open(os.path.join(IMG, "logo_64.png"), "rb").read()
    print("reperio.ico: %d bytes | logo_64.png em base64: %d caracteres" % (
        len(header + entries + data), len(base64.b64encode(icon64))))
    with open(os.path.join(IMG, "logo_64.b64"), "w") as f:
        f.write(base64.b64encode(icon64).decode("ascii"))


if __name__ == "__main__":
    main()
