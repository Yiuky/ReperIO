#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera as imagens do README (docs/images/) a partir de um acervo FICTÍCIO: nada do computador de quem
roda aparece nas capturas. O acervo é gravado direto no índice SQLite (sem criar arquivos em disco),
por isso a pasta "D:\\Acervo_Geoespacial" não precisa existir.

Só Windows. Requer Pillow (apenas para este script: `pip install pillow`) e o Microsoft Edge (para a
captura do treemap em HTML). Uso:  python tools/screenshots.py
"""
import contextlib
import io
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import reperio as g  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageGrab  # noqa: E402

OUT = os.path.join(ROOT, "docs", "images")
DEMO_ROOT = "D:\\Acervo_Geoespacial"
NOW = time.mktime((2026, 10, 17, 9, 30, 0, 0, 0, -1))
MB, GB = 1 << 20, 1 << 30


def build_demo(index):
    """Grava um acervo geoespacial fictício (≈ 120 GB, ≈ 45 mil arquivos) no índice."""
    rnd = random.Random(7)
    tree = {}      # pasta -> (subpastas, arquivos)

    def put(path, subdirs=(), files=()):
        tree[path] = (list(subdirs), list(files))

    def mt():
        return NOW - rnd.randint(1, 900) * 86400

    cenas = ("226_068", "227_069", "228_070")
    anos = (2019, 2020, 2021, 2022, 2023)
    p_land = DEMO_ROOT + "\\LANDSAT"
    put(p_land, [str(a) for a in anos])
    for a in anos:
        pa = "%s\\%d" % (p_land, a)
        put(pa, cenas)
        for c in cenas:
            base = "LC08_L2SP_%s_%d0715" % (c.replace("_", ""), a)
            files = [("%s_%s.TIF" % (base, b), int(rnd.uniform(60, 130) * MB), mt())
                     for b in ("B2", "B3", "B4", "B5", "B6", "B7")]
            files.append((base + "_MTL.xml", 9 * 1024, mt()))
            put("%s\\%s" % (pa, c), (), files)
    p_s2 = DEMO_ROOT + "\\SENTINEL"
    muns = ("Cuiaba", "Sinop", "Rondonopolis", "Barra_do_Garcas", "Caceres", "Lucas_do_Rio_Verde")
    put(p_s2, ["2023"])
    put(p_s2 + "\\2023", muns)
    for m in muns:
        put("%s\\2023\\%s" % (p_s2, m), (), [
            ("S2A_MSIL2A_20230812_%s_NDVI.tif" % m, int(rnd.uniform(380, 520) * MB), mt()),
            ("S2A_MSIL2A_20230812_%s_RGB.tif" % m, int(rnd.uniform(600, 800) * MB), mt()),
            ("S2A_MSIL2A_20230812_%s_meta.json" % m, 4096, mt())])
    p_mos = DEMO_ROOT + "\\MOSAICOS"
    put(p_mos, (), [("IMAGENS_mosaico_2020.tif", int(6.2 * GB), mt()),
                    ("IMAGENS_mosaico_2021.tif", int(7.1 * GB), mt()),
                    ("IMAGENS_mosaico_2022.ecw", int(1.1 * GB), mt()),
                    ("IMAGENS_mosaico_2023.tif", int(7.8 * GB), mt())])
    p_vet = DEMO_ROOT + "\\VETORES"
    put(p_vet, ["limites", "car"])
    put(p_vet + "\\limites", (), [("%s%s" % (n, e), int(rnd.uniform(5, 800) * 1024), mt())
                                  for n in ("Cuiaba", "Sinop", "Rondonopolis", "Caceres")
                                  for e in (".shp", ".shx", ".dbf", ".prj")])
    put(p_vet + "\\car", (), [("CAR_MT_2023.gpkg", int(1.4 * GB), mt()),
                              ("CAR_MT_2022.gpkg", int(1.2 * GB), mt())])
    p_vid = DEMO_ROOT + "\\VIDEOS_DRONE"
    put(p_vid, ["2022", "2023"])
    for ano in ("2022", "2023"):
        put("%s\\%s" % (p_vid, ano), (), [("DJI_%04d.MP4" % i, int(rnd.uniform(0.9, 3.2) * GB), mt())
                                          for i in range(1, 15)])
    p_bk = DEMO_ROOT + "\\BACKUP"
    put(p_bk, (), [("acervo_2022_completo.zip", int(9.4 * GB), mt()),
                   ("acervo_2023_completo.zip", int(12.6 * GB), mt()),
                   ("vetores_2024-01.zip", int(0.6 * GB), mt())])
    p_doc = DEMO_ROOT + "\\DOCUMENTOS"
    put(p_doc, (), [("Relatorio_IMAGENS_%d_%02d.pdf" % (2020 + i // 12, i % 12 + 1),
                     int(rnd.uniform(0.2, 4.5) * MB), mt()) for i in range(60)])
    p_til = DEMO_ROOT + "\\TILES_WEB"
    put(p_til, ["z14", "z15"])
    for z, n in (("z14", 9000), ("z15", 33000)):
        put("%s\\%s" % (p_til, z), (), [("tile_%06d.png" % i, int(rnd.uniform(8, 38) * 1024), mt())
                                        for i in range(n)])
    put(DEMO_ROOT, ["LANDSAT", "SENTINEL", "MOSAICOS", "VETORES", "VIDEOS_DRONE", "BACKUP",
                    "DOCUMENTOS", "TILES_WEB"], [("LEIAME.txt", 2048, NOW)])
    for path, (subs, files) in tree.items():
        index.record_dir(path, subs, files, dmtime=NOW)
    index.flush()


def pump(root, sec):
    end = time.time() + sec
    while time.time() < end:
        root.update()
        time.sleep(0.02)


def grab(win, name):
    win.update()
    x, y = win.winfo_rootx(), win.winfo_rooty()
    ImageGrab.grab(bbox=(x, y, x + win.winfo_width(), y + win.winfo_height())).save(
        os.path.join(OUT, name))
    print("  ->", name)


def block(dlg, name, depth=2, nth=0):
    cand = [r for r in dlg._tm_rects if r["node"]["name"] == name and r["depth"] >= depth - 1]
    return cand[nth] if cand else None


class Ev(object):
    def __init__(self, r):
        self.x, self.y = int(r["x"] + r["w"] / 2), int(r["y"] + r["h"] / 2)


def gui_shots(index_path):
    index = g.Index(index_path)
    root = g.tk.Tk()
    root.geometry("1100x820+10+10")
    app = g.App(root, index)
    pump(root, 1.0)
    root.lift()
    root.attributes("-topmost", True)
    app.v_root.set(DEMO_ROOT)
    app.v_pat.set("*.tif")
    app._start()
    deadline = time.time() + 20
    while (app._running or app._rcount == 0) and time.time() < deadline:
        pump(root, 0.1)
    pump(root, 0.8)
    app.tree.selection_set(app.tree.get_children()[:3])
    pump(root, 0.3)
    print("janela principal")
    grab(root, "janela_principal.png")

    app._open_space()
    dlg = app._space_win
    dlg.win.geometry("1200x780+30+20")
    dlg.win.attributes("-topmost", True)
    pump(root, 2.5)
    print("treemap por tamanho")
    mosaicos = block(dlg, "MOSAICOS", 1)
    dlg._tm_click(Ev(mosaicos))
    other = block(dlg, "acervo_2023_completo.zip") or block(dlg, "BACKUP", 1)
    dlg._tm_motion(Ev(other or mosaicos))
    pump(root, 0.5)
    grab(dlg.win, "espaco_treemap_tamanho.png")

    print("treemap por quantidade")
    dlg.v_metric.set("quantidade")
    dlg._set_metric()
    pump(root, 0.8)
    tiles = block(dlg, "TILES_WEB", 1)
    dlg._tm_click(Ev(tiles))
    dlg._tm_motion(Ev(tiles))
    pump(root, 0.5)
    grab(dlg.win, "espaco_treemap_quantidade.png")

    print("tamanho mínimo da janela de espaço")
    dlg.v_metric.set("tamanho")
    dlg._set_metric()
    mw, mh = dlg.win.minsize()
    dlg.win.geometry("%dx%d+30+20" % (mw, mh))
    pump(root, 1.0)
    grab(dlg.win, "espaco_tamanho_minimo.png")
    dlg._close()
    mw, mh = root.minsize()
    root.geometry("%dx%d+10+10" % (mw, mh))
    pump(root, 1.0)
    print("tamanho mínimo da janela principal")
    grab(root, "janela_principal_minima.png")
    index.close()
    root.destroy()


def cli(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            g.main(list(args))
        except SystemExit:
            pass
    return out.getvalue()


def terminal_png(title, blocks, dest, width=1040):
    """Desenha uma 'janela de terminal' com os comandos e suas saídas (fonte monoespaçada)."""
    font = None
    for f in ("consola.ttf", "Consolas.ttf", "cour.ttf"):
        try:
            font = ImageFont.truetype(f, 15)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    lines = []
    for cmd, out in blocks:
        lines.append(("$ " + cmd, "#7ee787"))
        for ln in out.rstrip("\n").split("\n"):
            lines.append((ln, "#d6dde4"))
        lines.append(("", "#d6dde4"))
    lh = 20
    img = Image.new("RGB", (width, 36 + lh * len(lines) + 16), "#0d1117")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, width, 34), fill="#1f2630")
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        d.ellipse((14 + i * 22, 11, 26 + i * 22, 23), fill=c)
    d.text((100, 9), title, fill="#8b949e", font=font)
    y = 46
    for text, color in lines:
        d.text((16, y), text, fill=color, font=font)
        y += lh
    img.save(dest)
    print("  ->", os.path.basename(dest))


def cli_shots(index_path):
    base = ["--indice", index_path, "--so-indice"]
    top = cli(*base, "--espaco", DEMO_ROOT, "--top", "6")
    ext = cli(*base, "--extensoes", "5", "--em", DEMO_ROOT)
    big = cli(*base, "--maiores", "5", "--em", DEMO_ROOT)
    terminal_png("ReperIO — espaço, extensões e maiores arquivos", [
        ("reperio --espaco D:\\Acervo_Geoespacial --top 6", top),
        ("reperio --extensoes 5 --em D:\\Acervo_Geoespacial", ext),
        ("reperio --maiores 5 --em D:\\Acervo_Geoespacial", big)],
        os.path.join(OUT, "cli_texto.png"), width=1180)
    raw = cli(*base, "--espaco", DEMO_ROOT, "--json", "--top", "2", "--profundidade", "2")
    data = json.loads(raw)
    for it in data["espaco"]["itens"]:
        for ch in it.get("filhos", []):
            ch.pop("filhos", None)
    data.pop("varredura", None)
    data["espaco"]["itens"] = data["espaco"]["itens"][:2]
    for it in data["espaco"]["itens"]:
        it["filhos"] = it.get("filhos", [])[:2]
        for k in ("bytes_diretos", "arquivos_diretos", "subpastas", "pct_pai"):
            it.pop(k, None)
            for ch in it["filhos"]:
                ch.pop(k, None)
    data.pop("desempenho", None)
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    terminal_png("ReperIO --json — saída para scripts e IAs", [
        ("reperio --espaco D:\\Acervo_Geoespacial --json --top 2 --profundidade 2 --so-indice",
         pretty)], os.path.join(OUT, "cli_json.png"), width=1040)


def html_shot(index_path, tmp):
    html = os.path.join(tmp, "treemap.html")
    cli("--indice", index_path, "--so-indice", "--espaco", DEMO_ROOT, "--treemap", html, "-q")
    edge = shutil.which("msedge") or os.path.join(
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        "Microsoft", "Edge", "Application", "msedge.exe")
    if not os.path.exists(edge):
        print("  (Edge não encontrado: pulei treemap_html.png)")
        return
    shot = os.path.join(OUT, "treemap_html.png")
    subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--window-size=1280,1180", "--screenshot=" + shot,
                    "file:///" + html.replace("\\", "/")], stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=90)
    time.sleep(1)
    print("  -> treemap_html.png")


def main():
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="reperio_shots_")
    index_path = os.path.join(tmp, "demo.sqlite")
    try:
        idx = g.Index(index_path)
        build_demo(idx)
        idx.close()
        print("acervo fictício gravado")
        gui_shots(index_path)
        cli_shots(index_path)
        html_shot(index_path, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("imagens em", OUT)


if __name__ == "__main__":
    main()
