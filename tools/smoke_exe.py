#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste de fumaça de um executável (ou do próprio reperio.py) pela linha de comando: garante que o que
foi empacotado se comporta como o código-fonte. Serve para a Release (Windows e Linux).

Uso:
  python tools/smoke_exe.py C:\\caminho\\ReperIO.exe
  python tools/smoke_exe.py ./ReperIO
  python tools/smoke_exe.py reperio.py          (roda com o Python atual)
  python tools/smoke_exe.py ReperIO.exe --gui   (Windows: também abre a janela, confere e fecha)

Sai com código 0 se tudo passou. Só lê e grava dentro de uma pasta temporária própria.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("  [%s] %s%s" % ("OK " if ok else "FALHA", name, (" — " + detail) if (detail and not ok) else ""),
          flush=True)
    return ok


def make_runner(target):
    if target.lower().endswith(".py"):
        base = [sys.executable, target]
    else:
        base = [target]

    def run(*args, timeout=180):
        t0 = time.time()
        p = subprocess.run(base + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), \
            time.time() - t0

    def js(*args, **kw):
        rc, out, err, el = run(*args, "--json", "-q", **kw)
        try:
            return rc, json.loads(out), err, el
        except ValueError:
            return rc, None, out + err, el
    return base, run, js


def make_tree(root):
    spec = {
        "fotos/a.jpg": 5000, "fotos/b.JPG": 3000, "fotos/sub/c.png": 1200,
        "zips/c.zip": 9000, "zips/d.zip": 100, "doc.txt": 50, "_lixo/e.tmp": 7000,
        "acentuação/ação_çãõ_日本.txt": 777,
    }
    for rel, size in spec.items():
        p = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x" * size)
    return len(spec), sum(spec.values())


def gui_check(target):
    """Windows: abre a janela, espera aparecer, confere o título e fecha com WM_CLOSE."""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    proc = subprocess.Popen([target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum(hwnd, _lp):
        n = user32.GetWindowTextLengthW(hwnd)
        if n and user32.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if buf.value.startswith("ReperIO"):
                found.append((hwnd, buf.value))
        return True
    deadline = time.time() + 60
    while time.time() < deadline and not found:
        user32.EnumWindows(enum, 0)
        if proc.poll() is not None:
            break
        time.sleep(0.5)
    check("janela abre (título ReperIO)", bool(found), "exit=%s" % proc.poll())
    if found:
        hwnd, title = found[0]
        rect = wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w, h = rect.right - rect.left, rect.bottom - rect.top
        check("janela com tamanho útil (%dx%d)" % (w, h), w >= 800 and h >= 560)
        user32.PostMessageW(hwnd, 0x0010, 0, 0)    # WM_CLOSE
        try:
            proc.wait(timeout=30)
            check("fecha limpo ao receber WM_CLOSE", proc.returncode == 0, "exit=%s" % proc.returncode)
        except subprocess.TimeoutExpired:
            proc.kill()
            check("fecha limpo ao receber WM_CLOSE", False, "não encerrou em 30 s")
    elif proc.poll() is None:
        proc.kill()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    target = os.path.abspath(args[0])
    base, run, js = make_runner(target)
    tmp = tempfile.mkdtemp(prefix="reperio_smoke_")
    data = os.path.join(tmp, "dados")
    idx = os.path.join(tmp, "i.sqlite")
    n_files, n_bytes = make_tree(data)
    print("Alvo: %s\nPasta temporária: %s" % (target, tmp), flush=True)
    try:
        rc, out, err, el = run("--version")
        print("  (iniciar o programa levou %.1f s)" % el)
        check("--version", rc == 0 and "ReperIO" in out, out + err)
        version = out.strip().split()[-1] if out.strip() else "?"
        rc, out, err, _ = run("--ajuda")
        check("--ajuda sai com 0 e lista as ações", rc == 0 and "--espaco" in out and "--treemap" in out)
        rc, out, err, _ = run("--espacoo", "x", timeout=30)
        check("argumento desconhecido: código 2, sem abrir janela", rc == 2, "rc=%s" % rc)
        rc, out, err, _ = run("--json", timeout=30)
        check("modificador sem ação: código 2", rc == 2, "rc=%s" % rc)
        rc, out, err, _ = run("--manifesto")
        try:
            m = json.loads(out)
            check("--manifesto é JSON e traz a versão", m.get("versao") == version, str(m.get("versao")))
            flagset = {f for a in m["argumentos"] for f in a["flags"]}
            check("--manifesto lista as ações", {"--espaco", "--buscar", "--treemap", "--so-indice"} <= flagset)
        except (ValueError, KeyError) as e:
            check("--manifesto é JSON", False, str(e))

        rc, j, err, el = js("--indice", idx, "--indexar", data)
        ok = bool(j) and j.get("ok") and j["varredura"]["arquivos"] == n_files and j["varredura"]["n_falhas"] == 0
        check("--indexar: %d arquivos, sem falhas (%.1f s)" % (n_files, el), ok, str(j)[:200] + err[:200])
        check("--indexar informa desempenho (tempo e RAM)",
              bool(j) and "tempo_total_s" in j.get("desempenho", {}))

        base_q = ["--indice", idx, "--so-indice"]
        rc, j, err, _ = js(*base_q, "--espaco", data, "--profundidade", "2")
        e = (j or {}).get("espaco", {})
        check("--espaco: total em bytes exato", rc == 0 and e.get("total_bytes") == n_bytes,
              "%s != %s" % (e.get("total_bytes"), n_bytes))
        itens = e.get("itens") or []
        check("--espaco: maiores primeiro (fotos 9200 > zips 9100) e completo",
              e.get("completo") is True and [i["nome"] for i in itens[:2]] == ["fotos", "zips"],
              str([i["nome"] for i in itens]))
        check("--espaco --profundidade 2 traz subpastas",
              any(f["nome"] == "sub" for i in itens for f in i.get("filhos", [])))
        rc, j, err, _ = js(*base_q, "--espaco", data, "--ignorar", "_lixo")
        check("--ignorar desconta a pasta", rc == 0 and j["espaco"]["total_bytes"] == n_bytes - 7000)
        rc, j, err, _ = js(*base_q, "--maiores", "2", "--em", data)
        check("--maiores", rc == 0 and [x["bytes"] for x in j["maiores"]] == [9000, 7000])
        rc, j, err, _ = js(*base_q, "--extensoes", "2", "--em", data)
        check("--extensoes", rc == 0 and j["extensoes"][0]["extensao"] == ".zip"
              and j["extensoes"][0]["bytes"] == 9100)
        rc, j, err, _ = js(*base_q, "--buscar", "*.jpg", "--em", data)
        check("--buscar *.jpg (acha .jpg e .JPG)", rc == 0 and j["busca"]["total_encontrado"] == 2)
        rc, j, err, _ = js(*base_q, "--buscar", "*", "--em", data, "--tamanho", "> 4000")
        check("--buscar com filtro de tamanho", rc == 0 and j["busca"]["total_encontrado"] == 3)
        rc, j, err, _ = js(*base_q, "--buscar", "çãõ", "--em", data)
        check("--buscar com acentos e ideogramas no nome", rc == 0 and j["busca"]["total_encontrado"] == 1,
              str(j)[:200])
        rc, j, err, _ = js("--indice", idx, "--status")
        check("--status", rc == 0 and j["indice"]["arquivos"] == n_files)

        html = os.path.join(tmp, "mapa.html")
        rc, j, err, _ = js(*base_q, "--espaco", data, "--treemap", html, "--treemap-por", "quantidade")
        size = os.path.getsize(html) if os.path.exists(html) else 0
        body = open(html, encoding="utf-8").read() if size else ""
        check("--treemap grava HTML autônomo", rc == 0 and "<svg" in body and "http://cdn" not in body
              and "@@" not in body, "size=%s" % size)
        for ext in (".csv", ".xlsx", ".txt"):
            dest = os.path.join(tmp, "espaco" + ext)
            rc, out, err, _ = run(*base_q, "--espaco", data, "--exportar", dest, "-q")
            check("--exportar %s" % ext, rc == 0 and os.path.exists(dest) and os.path.getsize(dest) > 50,
                  "rc=%s" % rc)

        rc, j, err, _ = js(*base_q, "--espaco", os.path.join(tmp, "nao_existe"))
        check("--so-indice sem dados: código 3", rc == 3 and j and j.get("ok") is False, "rc=%s" % rc)
        rc, j, err, _ = js("--indice", idx, "--espaco", os.path.join(tmp, "nao_existe2"))
        check("pasta inexistente: código 3", rc == 3 and j and j.get("codigo") == 3, "rc=%s" % rc)
        rc, j, err, _ = js(*base_q, "--buscar", "x", "--em", data, "--tamanho", "banana")
        check("filtro inválido: código 2 com erro em JSON", rc == 2 and j and j.get("ok") is False, "rc=%s" % rc)
        rc, out, err, _ = run(*base_q, "--espaco", data, "--top", "3")
        check("modo texto com acentos no console (pipe)", rc == 0 and "Total:" in out, err[-200:])
        rc, j, err, _ = js("--no-index", "--espaco", data)
        check("--no-index (tudo em memória)", rc == 0 and j["espaco"]["total_bytes"] == n_bytes)
        rc, out, err, el = run("--indice", idx, "--indexar", data, "-q")
        check("reindexar a quente (%.1f s)" % el, rc == 0)

        if "--gui" in flags:
            if os.name == "nt":
                gui_check(target)
            else:
                print("  (--gui só no Windows)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    bad = [r for r in RESULTS if not r[1]]
    print("\n%d verificações, %d falharam" % (len(RESULTS), len(bad)))
    for name, _ok, detail in bad:
        print("  FALHOU:", name, "|", detail[:300])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
