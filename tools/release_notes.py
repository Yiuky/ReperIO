#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monta o texto da Release a partir do CHANGELOG.md, no padrão da v2.6.0: tabela de download, como abrir,
verificação do SHA-256 e as novidades da versão.

    python tools/release_notes.py 2.7.1 > RELEASE_NOTES.md

Falha (código 1) se a versão não tiver seção no CHANGELOG: a Release não sai sem o histórico escrito.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/Yiuky/ReperIO"


def changelog_section(text, version):
    """Corpo da seção `## [versão]` (sem o título), ou None se não existir."""
    head = re.compile(r"^## \[%s\][^\n]*\n" % re.escape(version), re.M)
    m = head.search(text)
    if not m:
        return None
    nxt = re.compile(r"^## \[", re.M).search(text, m.end())
    return text[m.end():nxt.start() if nxt else len(text)].strip("\n")


def build_notes(version, changelog_text):
    body = changelog_section(changelog_text, version)
    if body is None or not body.strip():
        raise ValueError("CHANGELOG.md não tem a seção [%s]" % version)
    body = re.sub(r"^### ", "#### ", body, flags=re.M)     # um nível abaixo de "Novidades"
    return """## 📦 Download

| Sistema | Arquivo |
|---|---|
| Windows 10/11 (64 bits) | `ReperIO-{v}-windows-x64.zip` |
| Linux x64 (glibc 2.35+) | `ReperIO-{v}-linux-x64.zip` |

Extraia e abra o `iniciar.bat` (Windows) ou `./iniciar.sh` (Linux): não precisa instalar nada. A CLI
(`--json`, `--espaco`, `--buscar`...) também roda só com Python 3.8+, sem interface gráfica.

> Os executáveis são testados antes da publicação: a suíte de testes e o teste de fumaça do binário
> (`tools/smoke_exe.py`) rodam em Windows e Linux. Confira a integridade do download com o
> `SHA256SUMS.txt` (`sha256sum -c SHA256SUMS.txt` no Linux, `Get-FileHash` no Windows). O executável não é
> assinado digitalmente: o Windows pode mostrar o aviso do SmartScreen (**Mais informações → Executar assim
> mesmo**).

## ✨ Novidades da {v}

{body}

Histórico completo no [CHANGELOG]({repo}/blob/main/CHANGELOG.md). Guias: [CLI]({repo}/blob/main/docs/CLI.md) ·
[uso por IAs]({repo}/blob/main/docs/IA.md) · [benchmark]({repo}/blob/main/docs/BENCHMARK.md).
""".format(v=version, body=body, repo=REPO)


def main(argv):
    if len(argv) != 1 or not re.match(r"^\d+\.\d+\.\d+$", argv[0]):
        sys.stderr.write("uso: python tools/release_notes.py X.Y.Z\n")
        return 2
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        text = f.read()
    try:
        out = build_notes(argv[0], text)
    except ValueError as e:
        sys.stderr.write("Erro: %s\n" % e)
        return 1
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
