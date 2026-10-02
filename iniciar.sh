#!/bin/sh
# ============================================================================
# ReperIO - lançador para Linux
#
# 1) Usa um Python 3.8+ com tkinter já instalado (python3 do sistema).
# 2) Se não houver, roda o executável ./ReperIO (não precisa de Python).
#
# Para forçar um interpretador:  REPERIO_PYTHON=/caminho/python3 ./iniciar.sh
# ============================================================================
DIR=$(cd "$(dirname "$0")" && pwd)
APP="$DIR/reperio.py"
EXE="$DIR/ReperIO"

if [ -f "$APP" ]; then
    for P in "${REPERIO_PYTHON:-}" "${GFF_PYTHON:-}" python3 python; do
        [ -n "$P" ] || continue
        command -v "$P" >/dev/null 2>&1 || continue
        if "$P" -I -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
            exec "$P" -I "$APP" "$@"
        fi
    done
fi

if [ -f "$EXE" ]; then
    [ -x "$EXE" ] || chmod +x "$EXE" 2>/dev/null
    exec "$EXE" "$@"
fi

echo "[ERRO] Nenhum Python 3.8+ com tkinter foi encontrado e o executável"
echo "       ReperIO não está nesta pasta."
echo
echo "  Baixe o pacote pronto na página de Releases do projeto, ou instale o tkinter:"
echo "    Debian/Ubuntu: sudo apt install python3-tk"
echo "    Fedora/RHEL:   sudo dnf install python3-tkinter"
exit 1
