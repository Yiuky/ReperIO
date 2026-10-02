#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o executável autônomo (não exige Python na máquina de destino) e o
pacote .zip de distribuição.

    python tools/build.py            # Windows -> dist/ReperIO.exe
    python3 tools/build.py           # Linux   -> dist/ReperIO

Requisitos SÓ na máquina que compila: Python 3.8+ com tkinter e acesso ao
PyPI (o PyInstaller é instalado num ambiente isolado em .build/venv).
Use o Python do sistema — o Python do QGIS não tem tkinter.
"""
import os
import platform
import re
import shutil
import subprocess
import sys
import venv
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, ".build")
DIST = os.path.join(ROOT, "dist")
NAME = "ReperIO"
PYINSTALLER = "pyinstaller==6.22.3"
IS_WIN = os.name == "nt"


def run(cmd):
    print("+ " + " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


def app_version():
    with open(os.path.join(ROOT, "reperio.py"), encoding="utf-8") as f:
        return re.search(r'^__version__ = "([^"]+)"', f.read(), re.M).group(1)


def main():
    global DIST
    if "--dist" in sys.argv:   # pasta de saída alternativa (ex.: o .exe atual está aberto)
        DIST = os.path.abspath(sys.argv[sys.argv.index("--dist") + 1])
    try:
        import tkinter  # noqa: F401
    except ImportError:
        sys.exit("Este Python não tem tkinter; o executável sairia sem interface.\n"
                 "Compile com um Python 3.8+ que tenha tkinter (python.org, ou "
                 "'sudo apt install python3-tk' no Linux).")

    venv_dir = os.path.join(BUILD, "venv")
    py = os.path.join(venv_dir, "Scripts" if IS_WIN else "bin", "python" + (".exe" if IS_WIN else ""))
    if not os.path.exists(py):
        venv.create(venv_dir, with_pip=True)
    run([py, "-m", "pip", "install", "--disable-pip-version-check", "-q", PYINSTALLER])

    icon = os.path.join(ROOT, "docs", "images", "reperio.ico")
    run([py, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
         "--name", NAME] + (["--icon", icon] if IS_WIN and os.path.exists(icon) else []) + [
         "--distpath", DIST,
         "--workpath", os.path.join(BUILD, "work"),
         "--specpath", BUILD,
         os.path.join(ROOT, "reperio.py")])

    exe = os.path.join(DIST, NAME + (".exe" if IS_WIN else ""))
    ver = app_version()
    osname = "windows" if IS_WIN else platform.system().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(platform.machine().lower(),
                                                                       platform.machine().lower())
    zip_path = os.path.join(DIST, "%s-%s-%s-%s.zip" % (NAME, ver, osname, arch))

    # Pacote: executável + código-fonte + lançador. O lançador usa um Python 3
    # com tkinter da máquina se houver; senão, o executável.
    extras = ["reperio.py", "README.md", "LICENSE", "CHANGELOG.md",
              "iniciar.bat" if IS_WIN else "iniciar.sh"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo(os.path.basename(exe))
        info.external_attr = 0o755 << 16          # mantém o bit de execução no Linux
        info.compress_type = zipfile.ZIP_DEFLATED
        with open(exe, "rb") as f:
            z.writestr(info, f.read())
        for rel in extras:
            src = os.path.join(ROOT, rel)
            if rel.endswith(".sh"):
                info = zipfile.ZipInfo(rel)
                info.external_attr = 0o755 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(src, "rb") as f:
                    z.writestr(info, f.read())
            else:
                z.write(src, rel)

    print("\nExecutável: %s (%.1f MB)" % (exe, os.path.getsize(exe) / 1048576.0))
    print("Pacote:     %s" % zip_path)


if __name__ == "__main__":
    main()
