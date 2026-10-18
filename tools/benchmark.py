#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark do ReperIO pela própria CLI (o que uma IA ou um script veria).

Para cada pasta/disco informado mede, com um índice temporário novo:
  1. varredura "a frio"      (--indexar, índice vazio)
  2. reverificação "a quente" (--indexar de novo: só relê pastas alteradas)
  3. consultas ao índice      (--espaco, --maiores, --extensoes, --buscar, --treemap)
e grava um relatório em Markdown e um JSON com os números brutos.

Uso:
  python tools/benchmark.py C:\\ D:\\ [--ignorar OneDrive] [--md docs/BENCHMARK.md] [--json saida.json]

Atenção: a varredura "a frio" lê o disco inteiro. O cache do sistema operacional já pode estar
aquecido por leituras anteriores, então o tempo "a frio" é o do ReperIO, não do disco puro.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "reperio.py")


def run(index, *args):
    """Executa a CLI com --json; devolve (resultado_json, segundos_de_parede, código)."""
    cmd = [sys.executable, CLI, "--indice", index] + list(args) + ["--json", "-q"]
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wall = time.time() - t0
    try:
        data = json.loads(p.stdout.decode("utf-8", "replace"))
    except ValueError:
        data = {"ok": False, "erro": p.stderr.decode("utf-8", "replace")[-400:]}
    return data, wall, p.returncode


def bench_target(target, ignorar, keep_dir):
    res = {"alvo": target, "ignorar": ignorar}
    try:
        du = shutil.disk_usage(target)
        res["disco"] = {"total_gb": round(du.total / 2**30, 1), "usado_gb": round(du.used / 2**30, 1),
                        "livre_gb": round(du.free / 2**30, 1)}
    except OSError:
        pass
    tmp = tempfile.mkdtemp(prefix="reperio_bench_", dir=keep_dir)
    index = os.path.join(tmp, "bench.sqlite")
    extra = ["--ignorar", ignorar] if ignorar else []
    try:
        steps = {}
        d, wall, rc = run(index, "--indexar", target, *extra)
        v = d.get("varredura", {})
        steps["varredura_a_frio"] = {
            "ok": d.get("ok"), "parede_s": round(wall, 2), "arquivos": v.get("arquivos"),
            "pastas": v.get("pastas_lidas"), "arquivos_por_s": v.get("arquivos_por_s"),
            "falhas": v.get("n_falhas"), "pico_ram_mb": d.get("desempenho", {}).get("pico_ram_mb")}
        res["indice_mb"] = round(os.path.getsize(index) / 2**20, 1) if os.path.exists(index) else None
        d, wall, rc = run(index, "--indexar", target, *extra)
        v = d.get("varredura", {})
        steps["reverificacao_a_quente"] = {
            "ok": d.get("ok"), "parede_s": round(wall, 2), "pastas_conferidas": v.get("pastas_conferidas"),
            "pastas_relidas": v.get("pastas_relidas"), "arquivos_por_s": v.get("arquivos_por_s"),
            "pico_ram_mb": d.get("desempenho", {}).get("pico_ram_mb")}
        html = os.path.join(tmp, "treemap.html")
        for nome, args in (
                ("consulta_espaco", ["--espaco", target, "--top", "30", "--profundidade", "2"]),
                ("consulta_maiores", ["--maiores", "20", "--em", target]),
                ("consulta_extensoes", ["--extensoes", "20", "--em", target]),
                ("consulta_buscar", ["--buscar", "*.zip", "--em", target, "--limite", "50"]),
                ("treemap_html", ["--espaco", target, "--treemap", html])):
            d, wall, rc = run(index, *(args + ["--so-indice"] + extra))
            steps[nome] = {"ok": d.get("ok"), "parede_s": round(wall, 2),
                           "pico_ram_mb": d.get("desempenho", {}).get("pico_ram_mb")}
            if nome == "consulta_espaco" and d.get("ok"):
                res["total_gb"] = round(d["espaco"]["total_bytes"] / 2**30, 2)
                res["total_arquivos"] = d["espaco"]["total_arquivos"]
                res["completo"] = d["espaco"]["completo"]
            if nome == "consulta_buscar" and d.get("ok"):
                steps[nome]["encontrados"] = d["busca"]["total_encontrado"]
            if nome == "treemap_html" and os.path.exists(html):
                steps[nome]["html_kb"] = round(os.path.getsize(html) / 1024, 1)
        res["etapas"] = steps
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def markdown(results, meta):
    L = ["# Benchmark do ReperIO", "",
         "Gerado por `tools/benchmark.py` em %s." % meta["quando"], "",
         "- Máquina: %s" % meta["maquina"],
         "- Python %s · ReperIO v%s · %d CPUs lógicas" % (meta["python"], meta["versao"], meta["cpus"]), ""]
    for r in results:
        L += ["## %s" % r["alvo"], ""]
        if r.get("disco"):
            L.append("Disco: %(total_gb)s GB no total, %(usado_gb)s GB usados, %(livre_gb)s GB livres." % r["disco"])
        if r.get("ignorar"):
            L.append("Pastas ignoradas: `%s`." % r["ignorar"])
        if "total_gb" in r:
            L.append("Indexado: **%s arquivos, %s GB**; índice SQLite de %s MB%s." % (
                "{:,}".format(r["total_arquivos"]).replace(",", "."), r["total_gb"], r.get("indice_mb"),
                "" if r.get("completo") else " (há pastas sem leitura)"))
        L += ["", "| Etapa | Tempo (s) | Detalhe | Pico de RAM (MB) |", "|---|---:|---|---:|"]
        nomes = {"varredura_a_frio": "Varredura a frio (índice vazio)",
                 "reverificacao_a_quente": "Reverificação a quente (índice pronto)",
                 "consulta_espaco": "`--espaco` (2 níveis)", "consulta_maiores": "`--maiores 20`",
                 "consulta_extensoes": "`--extensoes 20`", "consulta_buscar": "`--buscar *.zip`",
                 "treemap_html": "`--treemap` (HTML)"}
        for k, s in r["etapas"].items():
            det = []
            if s.get("arquivos") is not None:
                det.append("%s arq. · %s pastas · %s arq./s" % (
                    "{:,}".format(s["arquivos"]).replace(",", "."), s.get("pastas"), s.get("arquivos_por_s")))
            if s.get("pastas_conferidas") is not None:
                det.append("%s pastas conferidas · %s relidas" % (s["pastas_conferidas"], s["pastas_relidas"]))
            if s.get("falhas"):
                det.append("%s pasta(s) não lidas" % s["falhas"])
            if s.get("encontrados") is not None:
                det.append("%s encontrados" % s["encontrados"])
            if s.get("html_kb") is not None:
                det.append("HTML %s KB" % s["html_kb"])
            L.append("| %s | %s | %s | %s |" % (nomes.get(k, k), s["parede_s"], "; ".join(det) or "—",
                                                s.get("pico_ram_mb") or "—"))
        L.append("")
    L += ["Tempo = relógio de parede do processo inteiro (inclui iniciar o Python). "
          "O cache do sistema operacional pode estar aquecido, então a varredura \"a frio\" mede o ReperIO, "
          "não o disco puro.", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("alvos", nargs="+", help="pastas ou discos (ex.: C:\\ D:\\)")
    ap.add_argument("--ignorar", default="", help="repassado à CLI (ex.: OneDrive)")
    ap.add_argument("--md", default=os.path.join(ROOT, "docs", "BENCHMARK.md"))
    ap.add_argument("--json", default=None, help="também grava os números brutos neste arquivo")
    ap.add_argument("--tmp", default=None, help="onde criar o índice temporário (padrão: temp do sistema)")
    a = ap.parse_args()
    sys.path.insert(0, ROOT)
    import reperio
    meta = {"quando": time.strftime("%Y-%m-%d %H:%M"), "maquina": platform.platform(),
            "python": platform.python_version(), "versao": reperio.__version__,
            "cpus": os.cpu_count() or 0}
    results = []
    for t in a.alvos:
        t, _sep, ign = t.partition("|")          # "C:\|OneDrive" ignora só nesse alvo
        print(">>> %s" % t, flush=True)
        r = bench_target(os.path.normpath(t), ign or a.ignorar, a.tmp)
        results.append(r)
        for k, s in r["etapas"].items():
            print("   %-24s %8.2f s" % (k, s["parede_s"]), flush=True)
    md = markdown(results, meta)
    with open(a.md, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print("Relatório: %s" % a.md)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "resultados": results}, f, ensure_ascii=False, indent=2)
        print("JSON: %s" % a.json)


if __name__ == "__main__":
    main()
