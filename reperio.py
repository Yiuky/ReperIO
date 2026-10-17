#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReperIO
=======
Do latim *reperire*, "achar, descobrir, trazer à luz", origem de *repertório*.

Busca rápida de arquivos por nome/extensão em pastas locais ou de rede
(SMB/CIFS, DFS), índice local, exportação (Excel/CSV/TXT) e cópia paralela.

Windows e Linux | Python 3.8+ | somente biblioteca padrão (tkinter incluso).
Projeto pessoal e open source de Joberth Firmino Gambati — licença MIT.
https://github.com/Yiuky/ReperIO

REGRAS ANTI-FREEZE da interface:
  1. Nenhum I/O de disco/rede na thread da GUI.
  2. Nenhum sleep(), update() ou update_idletasks() na thread da GUI.
  3. Toda comunicação thread -> GUI via queue.Queue + root.after (polling).
  4. Treeview limpo com um único comando Tcl; contadores mantidos em Python.
"""
import errno
import fnmatch
import os
import platform
import queue
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import traceback

__version__ = "2.6.0"
APP_NAME = "ReperIO"
APP_TAGLINE = "busca, índice, exportação e cópia de arquivos em servidores"
APP_URL = "https://github.com/Yiuky/ReperIO"
IS_WIN = os.name == "nt"

# Ícone da janela (docs/images/logo_64.png em base64; gerado por tools/make_icon.py)
ICON_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAA"
    "DsMAAA7DAcdvqGQAAAhDSURBVHhe7ZtbUBvXGcf9mMc+9gWv0QUhy0LX1eoCSFyFuIMhgLnaBhsPmEBsCLaxLZsYAhjHbt12"
    "mjrpLRk36bTuuO3E7rTjmXRomqZJJpP0+pJHHvPox6/f2V3kvXxoBRKpJfub+Y3He86e8///dc6RFtC+5/W8dlYcZwlynDlW"
    "xJlGijhz8unBNMJ0MWSpuStvIBL0ByM/9gfDX+O/8LTjE8KPfcHIXV8o1C5b2F3xfPTbXiFyzyewQfMTbyD8iOfDbtlS5sVe"
    "da8Q3sQ0caD8xhsIPfYLoV7ZmnFhcjFqoHwnoxBcgnDAEwhv4tJhy6eg8PChxy6j7eDhg/dwyeANhUrwM9mqvlw+IYYpsaQK"
    "GhcvjMiW1eXmg3epGwoNtz/0oWz5SUWj0RfcfuExbgHsVPiws062LpUXN4fbH8R0ng08fkH9juDyBdpxBWDjs4HLH5iWrUvF"
    "LlAdtcTqEtDW3f/UQWlNBx74Sdm6VOyC24eNBrR19cPUXDKnjC18H45cuw9dq38Wabz5H5GOtb+K/+9ZegDHLt2B068skvcz"
    "KK3pIALgk7gNsCE9rTkK4NS5NdFY840vUoaNaLr5T+h57Q9w8sIt3XiU1vTwmgA8GIAXGwwQIlGI1jTsmlhTN9RPvQGNN74k"
    "TWZKfO4uxFqOpMaltKYF/crWpXLihTIvD3uJr7YL4q9ukIZ2Q8PqpyC0jZNzGcH8ytalEgPwYOMeIXROQSLNq87MVM++C9Gp"
    "tyAysgiRwcsQnXwDYjM/hfqlv5D3bFE+skzOmQ4iAF/S6fFjQ+4J4KtECWfUXvgdhPovAN98LC2hnlmoevkd3Dr/IMcpH10j"
    "594e3+4C4MMVUFkTz5hY2xC53xuWNqDm+KtQ1TedMZXdkyB0zUDd5T/qxmMEOk+Tmmm0AbgwADc2GNBy+IjuBN4O9rbVtv6p"
    "Tmjn2gYcv/wmjF764Y7onVkDvglXBCKuBs24bIv5qg+TunWgX9m6VA68cMjtAyNaDveRZimGrtzViey4/iFpLhNYAP6moymo"
    "ENg1SrcW5le2LpUYgAsbDaioqoeWzj5jeseg8frnaoGrH0PziUVoPn5xV9QNzoG/Ec0rqL34vnoOxB8fILUr2XUAmRIZXtIJ"
    "i+BprTWQLYGOSd3BWDP/G1KTEiIAT9Lh8mJDbqi99FAlqn7xA/A1juwJlaffVM2VWP8SnHwFqesJHk0ATgygDBtygCscVwli"
    "hI+tgi+BgvcAvn1CNx/fcoLUlgL9ytalsuOFg2UeyAXCi7NqQbhE/S3j4EWxe0UdrjDlnBWnvkdq24L5la1LlWkAzZ295Imv"
    "pP/aPZWYjusfkad6tjQdX0gFEH3pJ6o5a+bvkfq3oANwYqMBzR3GAbAnNqWYrpUPVMKP3r4KQ+9NZAUbQxlA+Ylbqjnrrjwi"
    "9W9BBOBK2p1ubEhPTUMrDI5OpqV1Wb0c25P3oWdmNUXf7TMw8GAgK9gYdQOzaH5YJDR8TTUnOwgp/U9waQJwYACHsCEHVL+i"
    "3gKVk3fA24BCZeLJQdLUTmBjKMcMH11RzckerihtKdCvbF0qKQAXNmZPxQQ+7yvEVM3+EkUOpSgfHRQNZAMbQzXmyduqOWsv"
    "PiS1pdAGYMMLpQ4X5ALtq8H2oyc+tKfEpn+umjN29l1S2xbMr2xdKpvDiQGUYWP28B1TKjEMX+s4Ch3cM+LLf1PNVz56g9S2"
    "BfMrW5cq0wCq4y3kwadk4OQZlRhG56X3VAdhOmoHzpImt8Pfjh+HNfN5antJ/VvoA7A7k7aDTjCisf1F8q1Pi/Knu4y29U9U"
    "b4XpaDx2Htz1gxkTO6N+6kysfwGlZT5Sfwr0K1uXKtcBDF95WyWK0bv0e9Kwlp0EwHed1c1TefotUrsKbQBWuyNZYj8EucLm"
    "9OK+/EglrGHtc/C1TaDwgZzA3vsTOGbjrf9CQjGPs7yF1KSE+ZWtS5XrABjU3qy/tgHeplHS0E7QLnuRW/jIPXaT1KLlGwmA"
    "UT33a51QFkI2K0HoPa8bc4uquV+Jq4/SokQfgM2RtJY6INfYvRGoX1QfiAy2HYLDy+Cq698RATQfX/1EN56S6JlfQMkhD6kn"
    "BfqVrUuVaQDB8hgk2rp3xtDMtj/OblzagMTLP4LEaBISR89vS9XYClSfuy/f92/1GASGIew2AGaIOvWNOLHwXWi5ofkZoYb2"
    "9b+LT449yw9FulceiY/STTf/pe+P+113TUPaEPQB2JNW20FsSE+idXcBMCbOvSb+xpcSu1OUp346xBAcbsKLXR2AGS9YsMEI"
    "p4cXf0GaDdGRq9Cw8jEpOBPYBx2h/6p4hlDtWlgIVgxB6YP5la1LZbZiACV2+KawOf14oC1AzcIDUjRFbfJPaHoJSt2h1DhC"
    "/xWyr5bI2HdU8zO/snWp2AUza/g/YEND3tYJCKCZisk74lsZo/Kln4nX/F1zUOqLkvcyWB/KtBbLQdeT+/QB2JJmayk25CeB"
    "I8YhlHorFffY1AGYLKXzJmzIZ9KFwM4NZd9iXQDW0l5lh3xluxC8HdPqvviCy9alMpttMZPFhg35j7OmD6rO/VY0Xr3wPnia"
    "T+n7WW3qP5flOO5bxdjwrMBZrfq/Gi82lTwqNpdA4WP9SrasLs5kGadvKDSsy7JlfR0wlXx2ADsVLtZN3O4vyHb1xZnNsQMm"
    "KxQqnMlKf1dAWbgVprEj61xQ7C+2vi5bNC4MYZ4aJF9B8z+QrWVe7FuY+4stm1yxBfIV1P81x1nGZUs7L3ZgFHGW+aJiy1c4"
    "GBswL0C9m/uLza+zzzeyleyL46zuIs40T3939+mBfb9Zlvy80te+ff8DoL6jGLRfO/gAAAAASUVORK5CYII="
)

# ===========================================================================
# Log de diagnóstico
# ===========================================================================
def _log_dir():
    """Pasta gravável do usuário (o .exe pode estar numa pasta somente leitura).
    Versões até 2.4 (nome antigo "GIS File Finder") usavam "gis-file-finder":
    se ela existir e a nova não, é renomeada — o índice e o log são mantidos."""
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    d = os.path.join(base, "reperio")
    old = os.path.join(base, "gis-file-finder")
    try:
        if not os.path.exists(d) and os.path.isdir(old):
            os.replace(old, d)
    except OSError:
        pass
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        d = tempfile.gettempdir()
    return d

LOG_PATH = os.path.join(_log_dir(), "debug_execution.log")
LOG_LOCK = threading.Lock()
_LOG_MAX = 5 * 1024 * 1024   # rotaciona ao iniciar se passar de 5 MB

def rotate_log():
    try:
        if os.path.getsize(LOG_PATH) > _LOG_MAX:
            os.replace(LOG_PATH, LOG_PATH + ".old")
    except OSError:
        pass

def dlog(msg):
    """Grava uma linha no log. Nunca escreve no console: com o QuickEdit do
    Windows, um clique na janela do console bloqueia a escrita e congelava
    todas as threads que logavam (inclusive a GUI)."""
    try:
        line = "[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
        with LOG_LOCK:
            with open(LOG_PATH, "a", encoding="utf-8", errors="replace") as f:
                f.write(line)
    except Exception:
        pass

# ===========================================================================
# Formatação
# ===========================================================================
def fsize(b):
    if b is None or b < 0: return "-"
    if b < 1024:           return "%d B" % b
    if b < 1 << 20:        return "%.1f KB" % (b / 1024.0)
    if b < 1 << 30:        return "%.1f MB" % (b / 1048576.0)
    return "%.2f GB" % (b / 1073741824.0)

def fdate(t):
    if t is None or t < 0: return "-"
    try:
        return time.strftime("%d/%m/%Y %H:%M", time.localtime(t))
    except (ValueError, OSError, OverflowError):
        return "N/A"

def shorten(path, n=60):
    return path if len(path) <= n else "..." + path[-(n - 3):]

# ===========================================================================
# Sistema de arquivos
# ===========================================================================
_LOOP_REPARSE_TAGS = (0xA0000003, 0xA000000C)   # junction, symlink (Windows)
# Erros transitórios de rede: a pasta vai para o FIM da fila e é tentada de novo.
#   121 semáforo expirou | 64 nome de rede não disponível | 59 erro inesperado de rede
#   53 caminho de rede não encontrado | 1231 local de rede inacessível | 1236 conexão anulada
_WIN_RETRYABLE = (121, 64, 59, 53, 1231, 1236)
_RETRYABLE_ERRNOS = tuple(getattr(errno, n) for n in
                          ("ETIMEDOUT", "EHOSTDOWN", "EHOSTUNREACH", "ECONNRESET",
                           "ECONNABORTED", "EIO") if hasattr(errno, n))

def fs_path(path):
    """No Windows, caminhos longos (>= 240) recebem o prefixo \\\\?\\ para
    ultrapassar o limite de 260 caracteres. Caminhos exibidos não mudam."""
    if IS_WIN and len(path) >= 240 and not path.startswith("\\\\?\\"):
        path = os.path.abspath(path)
        if path.startswith("\\\\"):
            return "\\\\?\\UNC\\" + path[2:]
        return "\\\\?\\" + path
    return path

def is_loop_link(entry):
    """Diretórios-link (symlink / junction) podem formar ciclos infinitos.
    Links DFS (comuns em compartilhamentos de rede) NÃO são pulados."""
    try:
        if entry.is_symlink():
            return True
        if IS_WIN:
            st = entry.stat(follow_symlinks=False)
            return getattr(st, "st_reparse_tag", 0) in _LOOP_REPARSE_TAGS
    except OSError:
        pass
    return False

def is_retryable(e):
    """Erro transitório de rede (vale tentar de novo mais tarde)?"""
    we = getattr(e, "winerror", None)
    if we is not None:
        return we in _WIN_RETRYABLE
    return getattr(e, "errno", None) in _RETRYABLE_ERRNOS

is_net_timeout = is_retryable   # nome antigo

def is_not_found(e):
    return (getattr(e, "winerror", None) in (2, 3)
            or getattr(e, "errno", None) == errno.ENOENT)

# Causa legível dos erros mais comuns em pastas de rede (mostrada ao usuário e
# na lista de pastas não lidas, antes do texto técnico do sistema).
_WIN_ERRORS = {
    2: "arquivo ou pasta não encontrado",
    3: "caminho não encontrado (pasta apagada, renomeada ou unidade desconectada)",
    5: "acesso negado (sem permissão nesta pasta)",
    32: "em uso por outro processo",
    53: "caminho de rede não encontrado (servidor desligado ou nome errado)",
    59: "erro inesperado de rede",
    64: "o nome de rede não está mais disponível (conexão caiu)",
    65: "acesso à rede negado",
    67: "nome de rede (compartilhamento) não encontrado",
    86: "senha de rede incorreta",
    121: "o servidor não respondeu a tempo (timeout) — pasta travada no servidor",
    123: "nome de arquivo ou pasta inválido",
    1231: "local de rede inacessível",
    1236: "a conexão de rede foi anulada",
    1311: "nenhum servidor de logon disponível (problema de domínio/rede)",
    1326: "usuário ou senha incorretos",
    1920: "o sistema não consegue acessar o arquivo",
}
_ERRNO_ERRORS = {
    errno.EACCES: "acesso negado (sem permissão nesta pasta)",
    errno.EPERM: "operação não permitida",
    errno.ENOENT: "arquivo ou pasta não encontrado",
    errno.ETIMEDOUT: "o servidor não respondeu a tempo (timeout)",
    errno.EIO: "erro de entrada/saída (rede ou disco)",
    getattr(errno, "EHOSTDOWN", -1): "servidor indisponível",
    getattr(errno, "EHOSTUNREACH", -2): "servidor inacessível",
    getattr(errno, "ECONNRESET", -3): "a conexão com o servidor caiu",
}

def describe_error(e):
    """'causa legível — texto técnico' (o texto técnico ajuda a TI)."""
    cause = (_WIN_ERRORS.get(getattr(e, "winerror", None))
             or (getattr(e, "winerror", None) is None and _ERRNO_ERRORS.get(getattr(e, "errno", None))))
    return "%s — %s" % (cause, e) if cause else str(e)

# Última atividade de rede de cada thread (lote de itens recebido). Diferencia
# pasta GRANDE (recebe lotes continuamente) de pasta PRESA (parada numa chamada).
_activity = {}

def _touch():
    _activity[threading.get_ident()] = time.time()

# ---------------------------------------------------------------------------
# Windows: FindFirstFileExW com FIND_FIRST_EX_LARGE_FETCH + FindExInfoBasic.
# O os.scandir usa FindFirstFileW "simples": buffer pequeno por ida ao servidor
# e pede ao servidor o nome curto 8.3 de cada arquivo (caro em pastas enormes).
# LARGE_FETCH pede lotes maiores por requisição SMB e Basic dispensa o 8.3.
# Medido numa pasta de 65 mil arquivos na rede: 114,8 s -> 34,8 s.
# ---------------------------------------------------------------------------
_win_find = None
if IS_WIN:
    try:
        import ctypes
        from ctypes import wintypes

        class _FILETIME(ctypes.Structure):
            _fields_ = [("lo", wintypes.DWORD), ("hi", wintypes.DWORD)]

        class _WIN32_FIND_DATAW(ctypes.Structure):
            _fields_ = [("attr", wintypes.DWORD), ("ctime", _FILETIME),
                        ("atime", _FILETIME), ("mtime", _FILETIME),
                        ("size_hi", wintypes.DWORD), ("size_lo", wintypes.DWORD),
                        ("reparse_tag", wintypes.DWORD), ("reserved1", wintypes.DWORD),
                        ("name", wintypes.WCHAR * 260), ("alt_name", wintypes.WCHAR * 14)]

        _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _FindFirstFileExW = _k32.FindFirstFileExW
        _FindFirstFileExW.argtypes = [wintypes.LPCWSTR, ctypes.c_int,
                                      ctypes.POINTER(_WIN32_FIND_DATAW), ctypes.c_int,
                                      ctypes.c_void_p, wintypes.DWORD]
        _FindFirstFileExW.restype = wintypes.HANDLE
        _FindNextFileW = _k32.FindNextFileW
        _FindNextFileW.argtypes = [wintypes.HANDLE, ctypes.POINTER(_WIN32_FIND_DATAW)]
        _FindNextFileW.restype = wintypes.BOOL
        _FindClose = _k32.FindClose
        _FindClose.argtypes = [wintypes.HANDLE]
        _FindClose.restype = wintypes.BOOL
        _INVALID_HANDLE = ctypes.c_void_p(-1).value
        _FIND_EX_INFO_BASIC = 1
        _FIND_FIRST_EX_LARGE_FETCH = 2
        _ERROR_FILE_NOT_FOUND = 2
        _ERROR_NO_MORE_FILES = 18
        _EPOCH_AS_FILETIME = 116444736000000000

        def _ft(ft):
            v = (ft.hi << 32) | ft.lo
            return (v - _EPOCH_AS_FILETIME) / 1e7 if v > _EPOCH_AS_FILETIME else -1

        def _win_find(path):
            """Lista via Win32. Retorna ([(subpasta, mtime)], [(nome, tamanho, mtime)])."""
            data = _WIN32_FIND_DATAW()
            h = _FindFirstFileExW(os.path.join(fs_path(path), "*"), _FIND_EX_INFO_BASIC,
                                  ctypes.byref(data), 0, None, _FIND_FIRST_EX_LARGE_FETCH)
            if h == _INVALID_HANDLE or not h:
                err = ctypes.get_last_error()
                if err == _ERROR_FILE_NOT_FOUND:
                    return [], []
                raise ctypes.WinError(err, "%s: %s" % (ctypes.FormatError(err).strip(), path))
            dirs, files = [], []
            n = 0
            try:
                while True:
                    n += 1
                    if not n & 63:
                        _touch()          # progresso: pasta grande, não presa
                    name = data.name
                    if name not in (".", ".."):
                        attr = data.attr
                        if attr & 0x10:   # FILE_ATTRIBUTE_DIRECTORY
                            if not (attr & 0x400 and data.reparse_tag in _LOOP_REPARSE_TAGS):
                                dirs.append((name, _ft(data.mtime)))
                        else:
                            files.append((name, (data.size_hi << 32) | data.size_lo, _ft(data.mtime)))
                    if not _FindNextFileW(h, ctypes.byref(data)):
                        err = ctypes.get_last_error()
                        if err != _ERROR_NO_MORE_FILES:
                            raise ctypes.WinError(err, "%s: %s" % (ctypes.FormatError(err).strip(), path))
                        break
            finally:
                _FindClose(h)
            return dirs, files
    except Exception:   # qualquer problema com ctypes: usa o os.scandir
        _win_find = None

def list_dir(path, want_meta=True):
    """
    Lista uma pasta — uma única passada pelo servidor por pasta.
    No Windows usa _win_find (lotes grandes); no Linux, os.scandir.
    Retorna ([(subpasta, mtime)], [(nome, tamanho, mtime)]); -1 = não lido.
    A data das SUBPASTAS sempre é lida: é ela que permite a atualização
    incremental do índice (relê só pastas cuja data mudou).
    Lança OSError se a pasta for inacessível.
    """
    if _win_find is not None:
        return _win_find(path)
    dirs, files = [], []
    meta = want_meta or IS_WIN
    with os.scandir(fs_path(path)) as it:
        for i, e in enumerate(it):
            if not i & 63:
                _touch()
            try:
                if e.is_dir():
                    if not is_loop_link(e):
                        try:
                            dm = e.stat(follow_symlinks=False).st_mtime
                        except OSError:
                            dm = -1
                        dirs.append((e.name, dm))
                    continue
                if meta:
                    st = e.stat(follow_symlinks=False)
                    files.append((e.name, st.st_size, st.st_mtime))
                else:
                    files.append((e.name, -1, -1))
            except OSError:
                continue   # entrada individual ilegível: ignora, segue a pasta
    return dirs, files

def dir_mtime(path):
    return os.stat(fs_path(path)).st_mtime

# ===========================================================================
# Filtro de nomes
# ===========================================================================
def clean_pattern(raw):
    """Remove espaços acidentais em volta de asteriscos."""
    p = (raw or "").strip()
    while " *" in p: p = p.replace(" *", "*")
    while "* " in p: p = p.replace("* ", "*")
    return p

def parse_exts(raw):
    """'.shp tif, PDF' -> ['.shp', '.tif', '.pdf']"""
    res = []
    for t in (raw or "").replace(",", " ").split():
        if not t.startswith("."):
            t = "." + t
        res.append(t.lower())
    return res

def make_matcher(pattern, exts=(), case_sensitive=False):
    """
    Devolve uma função nome -> bool.
      - sem curingas  -> "contém" (ex.: IMAGENS_)
      - com * ou ?    -> fnmatch no nome completo ou no nome sem extensão
      - curinga parcial sem ponto (ex.: *IMAGENS_) também aceita sufixo
    """
    p = clean_pattern(pattern)
    exts = [e.lower() for e in exts if e]
    if not case_sensitive:
        p = p.lower()
    any_name = (not p or p == "*")
    has_wild = ("*" in p or "?" in p)
    p_wild = p + "*" if (has_wild and "." not in p and not p.endswith("*")) else None
    # fnmatch.fnmatch normaliza caixa no Windows; fnmatchcase respeita a escolha.
    fm = fnmatch.fnmatchcase

    def match(name):
        base, ext = os.path.splitext(name)
        if exts and ext.lower() not in exts:
            return False
        if any_name:
            return True
        n = name if case_sensitive else name.lower()
        b = base if case_sensitive else base.lower()
        if not has_wild:
            return p in n
        if fm(n, p) or fm(b, p):
            return True
        return bool(p_wild) and (fm(b, p_wild) or fm(n, p_wild))
    return match

_SIZE_UNITS = {
    "": 1, "b": 1, "byte": 1, "bytes": 1,
    "k": 1 << 10, "kb": 1 << 10, "kib": 1 << 10,
    "m": 1 << 20, "mb": 1 << 20, "mib": 1 << 20,
    "g": 1 << 30, "gb": 1 << 30, "gib": 1 << 30,
    "t": 1 << 40, "tb": 1 << 40, "tib": 1 << 40,
}
_SIZE_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*([a-zA-Z]*)\s*$")

def parse_size(raw):
    """'100 MB' -> 104857600; '1,5 GB' -> 1610612736. None se vazio; ValueError se inválido."""
    s = (raw or "").strip()
    if not s:
        return None
    m = _SIZE_RE.match(s)
    if not m:
        raise ValueError("Tamanho inválido: %r (use ex.: 100 MB, 1,5 GB, 500 KB)" % raw)
    val = float(m.group(1).replace(",", "."))
    unit = m.group(2).lower()
    if unit not in _SIZE_UNITS:
        raise ValueError("Unidade de tamanho desconhecida: %r (use B, KB, MB, GB, TB)" % m.group(2))
    return int(val * _SIZE_UNITS[unit])

def parse_size_filter(raw):
    """
    Interpreta um filtro de tamanho e devolve (min_bytes, max_bytes):
      - vazio                       -> (None, None)
      - '100 MB' / '> 100 MB'       -> (104857600, None)
      - '< 10 MB' / '<= 10 MB'      -> (None, 10485760)
      - '10 MB .. 500 MB'           -> (10485760, 524288000)
    """
    s = (raw or "").strip()
    if not s:
        return None, None
    low = s.lower()
    for sep in ("..", " a ", " até ", " ate ", "-"):
        if sep in low and not low.lstrip().startswith("-"):
            idx = low.find(sep)
            left, right = s[:idx].strip(), s[idx + len(sep):].strip()
            lo = parse_size(left) if left else None
            hi = parse_size(right) if right else None
            if lo is not None and hi is not None and lo > hi:
                lo, hi = hi, lo
            return lo, hi
    if s.startswith((">=", "=>")):
        return parse_size(s[2:]), None
    if s.startswith((">", "+")):
        return parse_size(s[1:]), None
    if s.startswith(("<=", "=<")):
        return None, parse_size(s[2:])
    if s.startswith("<"):
        return None, parse_size(s[1:])
    return parse_size(s), None

def make_size_matcher(min_size=None, max_size=None):
    """Devolve uma função tamanho_em_bytes -> bool (ou None se sem filtro)."""
    if min_size is None and max_size is None:
        return None

    def match_size(sz):
        if sz is None or sz < 0:
            return False
        if min_size is not None and sz < min_size:
            return False
        if max_size is not None and sz > max_size:
            return False
        return True
    return match_size

def parse_excludes(raw):
    """'MOSAICOS, _backup' ou 'node_modules .git' -> ['MOSAICOS', '_backup']"""
    s = (raw or "").strip()
    if not s:
        return []
    parts = re.split(r"[,;]+", s) if ("," in s or ";" in s) else s.split()
    return [p.strip() for p in parts if p.strip()]

def make_dir_excluder(excludes=(), root=None):
    """
    Devolve função dir_path -> bool (True = pasta deve ser ignorada).
    Aceita nomes de pasta ('MOSAICOS', 'node_modules', '.git'), curingas
    ('*backup*', 'temp*') ou subcaminhos ('AppData/Local/Temp'). Quando `root`
    é informado, também ignora descendentes de uma pasta ignorada (para que a
    consulta ao índice SQLite tenha o mesmo efeito da varredura ao vivo).
    """
    pats = []
    for raw in (excludes or ()):
        p = clean_pattern(raw).replace("/", os.sep).replace("\\", os.sep).strip(os.sep).lower()
        if p:
            pats.append((p, "*" in p or "?" in p, os.sep in p))
    if not pats:
        return None
    root_norm = os.path.normpath(root) if root else None
    root_key = path_key(root_norm) if root_norm else None
    fm = fnmatch.fnmatchcase

    def is_excluded(dir_path):
        dp = os.path.normpath(dir_path)
        if root_key is not None:
            dk = path_key(dp)
            if dk == root_key:
                return False
            if is_under(dk, root_key):
                rel = dp[len(root_norm):].lstrip(os.sep).lower()
                segs = [s for s in rel.split(os.sep) if s]
            else:
                rel = os.path.basename(dp).lower()
                segs = [rel] if rel else []
        else:
            rel = os.path.basename(dp).lower()
            segs = [rel] if rel else []
        for p, is_wild, has_sep in pats:
            if has_sep:
                if is_wild:
                    if (fm(rel, p) or fm(rel, p + os.sep + "*")
                            or fm(rel, "*" + os.sep + p)
                            or fm(rel, "*" + os.sep + p + os.sep + "*")):
                        return True
                elif (rel == p or rel.startswith(p + os.sep)
                        or (os.sep + p + os.sep) in (os.sep + rel + os.sep)):
                    return True
            else:
                for seg in segs:
                    if fm(seg, p) if is_wild else (seg == p):
                        return True
        return False
    return is_excluded

# ===========================================================================
# Controle de concorrência adaptativo
# ===========================================================================
SCAN_WORKERS     = 8        # teto de leituras simultâneas no modo rápido
MAX_RESULTS      = 100000   # acima disso o Treeview do Tk fica lento demais
MAX_RETRY_ROUNDS = 2        # rodadas extras (no fim da busca) para pastas adiadas
RETRY_PAUSE      = 10.0     # pausa antes de cada rodada de novas tentativas (s)
SLOW_AFTER       = 20.0     # leitura mais longa que isso libera a vaga para outra
JAM_COOLDOWN     = 20.0     # pausa de novas leituras após um timeout (sessão congestionada)
RESPONSIVE_WINDOW = 10.0    # sem nenhuma leitura concluída nesse tempo = servidor não responde
MTIME_TOL        = 0.001    # tolerância na comparação de datas de pasta (s)

def fmt_n(n):
    return "{:,}".format(n).replace(",", ".")

class AdaptiveGate(object):
    """
    Limita quantas leituras vão ao servidor ao mesmo tempo. Todas as threads
    compartilham UMA sessão SMB com o servidor, e foi medido no servidor real
    que UMA pasta-problema (leitura que nunca responde) congestiona a sessão
    inteira: até pastas de 4 arquivos passam a falhar com timeout (erro 121)
    por vários minutos. Nem CancelSynchronousIo destrava. Por isso:
      - começa com `start` e libera +1 a cada `grow_after` leituras OK, até o teto;
      - qualquer timeout = sessão congestionada: concorrência cai para 1,
        novas leituras PAUSAM por `cooldown` segundos e o teto desce um nível;
      - leitura lenta só é "desligada" da vaga (detach) se o servidor ainda
        responde a outras leituras — ou para UMA leitura-sonda que descobre
        se é só uma pasta grande ou o servidor todo travado.
    """
    def __init__(self, start=2, maximum=SCAN_WORKERS, grow_after=50, cooldown=None):
        self.maximum = max(1, maximum)
        self.ceiling = self.maximum
        self.limit = max(1, min(start, self.maximum))
        self.grow_after = grow_after
        self.cooldown = JAM_COOLDOWN if cooldown is None else cooldown
        self.active = 0          # leituras ocupando vaga
        self.detached = 0        # leituras lentas que liberaram a vaga
        self.ok_streak = 0
        self.reduced = False
        self.last_ok = time.time()
        self.pause_until = 0.0
        self.timeouts = 0
        self.cv = threading.Condition()

    def acquire(self, stop, abandon=None):
        """True = vaga obtida; False = busca parada; None = `abandon()` ficou
        verdadeiro enquanto esperava (ex.: a conexão deixou de ser a principal)."""
        with self.cv:
            while True:
                if stop.is_set():
                    return False
                if abandon is not None and abandon():
                    return None
                now = time.time()
                if self.active < self.limit and now >= self.pause_until:
                    self.active += 1
                    return True
                wait = self.pause_until - now if now < self.pause_until else 0.5
                self.cv.wait(min(0.5, max(0.05, wait)))

    def responsive(self, window=None):
        """O servidor concluiu alguma leitura nos últimos `window` segundos?"""
        return time.time() - self.last_ok < (RESPONSIVE_WINDOW if window is None else window)

    def can_detach(self):
        return self.responsive() or self.detached == 0

    def cancel(self):
        """Devolve uma vaga obtida e não usada."""
        with self.cv:
            self.active -= 1
            self.cv.notify_all()

    def detach(self):
        """A leitura em curso continua, mas deixa de ocupar uma vaga."""
        with self.cv:
            self.active -= 1
            self.detached += 1
            self.cv.notify_all()

    def release(self, timed_out=False, detached=False):
        with self.cv:
            if detached:
                self.detached -= 1
            else:
                self.active -= 1
            if timed_out:
                self.timeouts += 1
                old = self.limit
                if self.maximum > 1:
                    self.ceiling = min(self.ceiling, max(2, old - 1))
                self.limit = 1
                self.reduced = self.maximum > 1
                self.ok_streak = 0
                self.pause_until = time.time() + self.cooldown
                dlog("[ADAPTATIVO] Timeout: sessão com o servidor congestionada — concorrência "
                     "%d -> 1, pausa de %ds (teto %d)" % (old, self.cooldown, self.ceiling))
            else:
                self.last_ok = time.time()
                self.ok_streak += 1
                if self.ok_streak >= self.grow_after and self.limit < self.ceiling:
                    self.limit += 1
                    self.ok_streak = 0
                    self.reduced = self.limit < self.maximum
                    dlog("[ADAPTATIVO] Servidor respondendo bem: concorrência -> %d" % self.limit)
            self.cv.notify_all()

    def force(self, limit):
        """Fixa o limite (rodadas de novas tentativas: 1 por vez)."""
        with self.cv:
            self.limit = self.ceiling = max(1, limit)
            self.cv.notify_all()

# ===========================================================================
# Índice local (SQLite)
# ===========================================================================
INDEX_PATH = os.path.join(_log_dir(), "index.sqlite")

_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS dirs (
    id      INTEGER PRIMARY KEY,
    key     TEXT NOT NULL UNIQUE,   -- caminho normalizado (minúsculo no Windows)
    path    TEXT NOT NULL,          -- caminho para exibição
    parent  INTEGER,
    state   INTEGER NOT NULL DEFAULT 0,   -- 0 = falta ler, 1 = lida
    scanned REAL,                   -- quando foi lida
    dmtime  REAL,                   -- data da pasta correspondente à leitura guardada
    pmtime  REAL                    -- data da pasta vista na última leitura da pasta-mãe
);
CREATE INDEX IF NOT EXISTS dirs_parent ON dirs(parent);
CREATE TABLE IF NOT EXISTS files (
    dir_id INTEGER NOT NULL,
    name   TEXT NOT NULL,
    size   INTEGER,
    mtime  REAL
);
CREATE INDEX IF NOT EXISTS files_dir ON files(dir_id);
-- Pastas que travaram a sessão com o servidor (timeout mesmo lidas sozinhas).
-- Ficam de fora das próximas buscas, com aviso; saem daqui ao serem lidas com sucesso.
CREATE TABLE IF NOT EXISTS problems (
    key        TEXT PRIMARY KEY,
    path       TEXT NOT NULL,
    fails      INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    last_try   REAL
);
"""

def path_key(path):
    return os.path.normcase(os.path.normpath(path))

# Nomes vindos de servidores Samba antigos (ou bytes inválidos no Linux) podem
# conter "surrogates" isolados (U+D800–U+DFFF), que não existem em UTF-8 — e o
# SQLite só guarda UTF-8. No banco eles viram caracteres da área de uso privado
# U+F0000–U+F07FF (mesma posição relativa); na leitura, voltam a ser o que eram.
# É reversível: o caminho original continua servindo para abrir/copiar o arquivo.
_SURROGATE_RE = re.compile("[\ud800-\udfff]")
_PRIVATE_RE = re.compile("[\U000F0000-\U000F07FF]")

def db_enc(s):
    if not s:
        return s
    try:
        s.encode("utf-8")
        return s
    except UnicodeEncodeError:
        return _SURROGATE_RE.sub(lambda m: chr(0xF0000 + ord(m.group()) - 0xD800), s)

def db_dec(s):
    if not s or max(s) < "\U000F0000":
        return s
    return _PRIVATE_RE.sub(lambda m: chr(0xD800 + ord(m.group()) - 0xF0000), s)

def db_key(path):
    return db_enc(path_key(path))

def _subtree_range(key):
    """Faixa [lo, hi) de chaves dos descendentes de `key` (comparação binária)."""
    lo = key if key.endswith(os.sep) else key + os.sep
    return lo, lo[:-1] + chr(ord(os.sep) + 1)

_UNDER = "(d.key = ? OR (d.key >= ? AND d.key < ?))"

def _under_args(root):
    k = path_key(root)
    lo, hi = _subtree_range(k)
    return (k, lo, hi)

def is_under(key, root_key):
    lo, hi = _subtree_range(root_key)
    return key == root_key or lo <= key < hi

def _norm_subdirs(subdirs):
    return [(s, None) if isinstance(s, str) else (s[0], s[1]) for s in subdirs]

class Index(object):
    """
    Guarda TODO arquivo de toda pasta lida em qualquer busca, com a data de
    cada pasta. Assim:
      - buscas seguintes na mesma árvore saem do índice em segundos;
      - busca interrompida continua de onde parou (pastas com state=0);
      - "verificar alterações" relê só pastas cuja data mudou.
    Uma única thread escreve no banco; as buscas só enfileiram. Leituras usam
    conexões próprias (modo WAL: ler e escrever ao mesmo tempo é seguro).
    """
    def __init__(self, path=INDEX_PATH):
        self.path = path
        self.q = queue.Queue()
        self._ready = threading.Event()
        self._error = None
        self._t = threading.Thread(target=self._writer, daemon=True)
        self._t.start()
        self._ready.wait(15)
        if self._error is not None:
            raise self._error

    def connect(self):
        c = sqlite3.connect(self.path, timeout=60, check_same_thread=False)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        return c

    # -- escrita (somente na thread _writer) -------------------------------
    def _writer(self):
        try:
            c = self.connect()
            c.executescript(_INDEX_SCHEMA)
            cols = {r[1] for r in c.execute("PRAGMA table_info(dirs)")}
            for col in ("dmtime", "pmtime"):          # índices da versão 2.1
                if col not in cols:
                    c.execute("ALTER TABLE dirs ADD COLUMN %s REAL" % col)
            c.commit()
        except Exception as e:
            self._error = e
            self._ready.set()
            return
        self._ready.set()
        dirty, last = 0, time.time()
        while True:
            try:
                op = self.q.get(timeout=0.5)
            except queue.Empty:
                op = None
            if op is not None:
                kind = op[0]
                try:
                    if kind in ("flush", "close"):
                        c.commit()
                        dirty = 0
                        if kind == "close":
                            c.close()
                            op[1].set()
                            return
                        op[1].set()
                        continue
                    if kind == "dir":
                        self._w_dir(c, *op[1:])
                    elif kind == "missing":
                        self._w_delete_subtree(c, db_key(op[1]))
                    elif kind == "problem":
                        _, path, err, now = op
                        key = db_key(path)
                        c.execute("INSERT OR IGNORE INTO problems(key, path) VALUES (?, ?)",
                                  (key, db_enc(path)))
                        c.execute("UPDATE problems SET fails = fails + 1, last_error = ?, last_try = ? "
                                  "WHERE key = ?", (err, now, key))
                    elif kind == "clear":
                        c.execute("DELETE FROM files")
                        c.execute("DELETE FROM dirs")
                        c.execute("DELETE FROM problems")
                        c.commit()
                        c.execute("VACUUM")
                        op[1].set()
                        continue
                    dirty += 1
                except Exception as e:
                    # QUALQUER erro numa gravação é registrado e a thread segue viva.
                    # (Antes só sqlite3.Error: um nome inválido derrubava o gravador e
                    # todo o resto da busca deixava de ir para o índice, em silêncio.)
                    dlog("[ÍNDICE] erro de escrita (%s): %s" % (kind, e))
                    if kind == "clear":
                        op[1].set()
            if dirty and (dirty >= 200 or time.time() - last >= 1.0):
                try:
                    c.commit()
                except sqlite3.Error as e:
                    dlog("[ÍNDICE] erro no commit: %s" % e)
                dirty, last = 0, time.time()
            elif not dirty:
                last = time.time()

    def _w_dir(self, c, path, subdirs, files, now, dmtime):
        key = db_key(path)
        epath = db_enc(path)
        row = c.execute("SELECT id FROM dirs WHERE key = ?", (key,)).fetchone()
        if row:
            did = row[0]
            c.execute("UPDATE dirs SET path = ?, state = 1, scanned = ?, dmtime = ? WHERE id = ?",
                      (epath, now, dmtime, did))
        else:
            did = c.execute("INSERT INTO dirs(key, path, state, scanned, dmtime) "
                            "VALUES (?, ?, 1, ?, ?)", (key, epath, now, dmtime)).lastrowid
        c.execute("DELETE FROM problems WHERE key = ?", (key,))   # voltou a funcionar
        c.execute("DELETE FROM files WHERE dir_id = ?", (did,))
        c.executemany("INSERT INTO files(dir_id, name, size, mtime) VALUES (?, ?, ?, ?)",
                      ((did, db_enc(n), s, m) for n, s, m in files))
        children = {}
        for name, mt in subdirs:
            p = os.path.join(path, name)
            children[db_key(p)] = (db_enc(p), mt)
        # Subpastas que sumiram do servidor: remove do índice com tudo dentro.
        for _oid, okey in c.execute("SELECT id, key FROM dirs WHERE parent = ?", (did,)).fetchall():
            if okey not in children:
                self._w_delete_subtree(c, okey)
        c.executemany("INSERT OR IGNORE INTO dirs(key, path, parent, state, pmtime) "
                      "VALUES (?, ?, ?, 0, ?)",
                      ((k, p, did, mt) for k, (p, mt) in children.items()))
        c.executemany("UPDATE dirs SET parent = ?, pmtime = ? WHERE key = ?",
                      ((did, mt, k) for k, (p, mt) in children.items()))

    def _w_delete_subtree(self, c, key):
        lo, hi = _subtree_range(key)
        c.execute("DELETE FROM files WHERE dir_id IN (SELECT id FROM dirs "
                  "WHERE key = ? OR (key >= ? AND key < ?))", (key, lo, hi))
        c.execute("DELETE FROM dirs WHERE key = ? OR (key >= ? AND key < ?)", (key, lo, hi))

    # -- API usada pelas buscas -------------------------------------------
    def record_dir(self, path, subdirs, files, dmtime=None):
        """subdirs: nomes ou (nome, mtime); files: (nome, tamanho, mtime)."""
        self.q.put(("dir", path, _norm_subdirs(subdirs), list(files), time.time(), dmtime))

    def record_missing(self, path):
        self.q.put(("missing", path))

    def record_problem(self, path, error):
        self.q.put(("problem", path, error, time.time()))

    def _sync(self, kind, timeout):
        ev = threading.Event()
        self.q.put((kind, ev))
        return ev.wait(timeout)

    def flush(self, timeout=60):
        return self._sync("flush", timeout)

    def clear(self, timeout=300):
        return self._sync("clear", timeout)

    def close(self, timeout=10):
        if self._t.is_alive():
            self._sync("close", timeout)

    def query(self, root, matcher, emit, stop, size_matcher=None, dir_excluder=None):
        """
        Emite os arquivos indexados sob `root` que casam com `matcher`
        (e opcionalmente `size_matcher` e `dir_excluder`) e devolve um resumo:
        pastas lidas, pastas pendentes [(caminho, pmtime)], se a própria raiz
        já foi lida e a data da leitura mais antiga.
        """
        self.flush()
        c = self.connect()
        try:
            c.create_function("gff_match", 1, lambda n: 1 if matcher(db_dec(n)) else 0)
            c.set_progress_handler(lambda: 1 if stop.is_set() else 0, 50000)
            args = tuple(db_enc(a) for a in _under_args(root))
            n_done, n_files, oldest = c.execute(
                "SELECT count(*), (SELECT count(*) FROM files f JOIN dirs d ON d.id = f.dir_id "
                "WHERE %s AND d.state = 1), min(scanned) FROM dirs d WHERE %s AND state = 1"
                % (_UNDER, _UNDER), args + args).fetchone()
            emitted = 0
            excl_cache = {}
            if n_done:
                cur = c.execute(
                    "SELECT d.path, f.name, f.size, f.mtime FROM files f "
                    "JOIN dirs d ON d.id = f.dir_id "
                    "WHERE %s AND d.state = 1 AND gff_match(f.name)" % _UNDER, args)
                for dpath, name, size, mtime in cur:
                    dpath = db_dec(dpath)
                    if dir_excluder is not None:
                        ex = excl_cache.get(dpath)
                        if ex is None:
                            ex = dir_excluder(dpath)
                            excl_cache[dpath] = ex
                        if ex:
                            continue
                    sz = -1 if size is None else size
                    if size_matcher is not None and not size_matcher(sz):
                        continue
                    name = db_dec(name)
                    emit((os.path.join(dpath, name), name, os.path.splitext(name)[1],
                          sz, dpath, -1 if mtime is None else mtime))
                    emitted += 1
            pending = [(db_dec(r[0]), r[1]) for r in c.execute(
                "SELECT path, pmtime FROM dirs d WHERE %s AND state = 0" % _UNDER, args)]
            if dir_excluder is not None:
                pending = [(p, mt) for p, mt in pending if not dir_excluder(p)]
            root_done = c.execute("SELECT 1 FROM dirs WHERE key = ? AND state = 1",
                                  (args[0],)).fetchone() is not None
            problems = [(db_dec(r[0]),) + tuple(r[1:]) for r in c.execute(
                "SELECT d.path, d.fails, d.last_error, d.last_try FROM problems d WHERE %s" % _UNDER, args)]
            if dir_excluder is not None:
                problems = [pr for pr in problems if not dir_excluder(pr[0])]
            return {"dirs": n_done, "files": n_files, "emitted": emitted, "pending": pending,
                    "root_done": root_done, "oldest": oldest, "problems": problems}
        except sqlite3.OperationalError:
            if stop.is_set():
                return None   # interrompido pelo usuário
            raise
        finally:
            c.close()

    def folder_space(self, root, exclude_dirs=(), stop=None):
        """
        Soma o espaço ocupado por pasta e subárvore sob `root` diretamente do
        índice SQLite. Devolve a estrutura de `aggregate_folder_space` (ou None
        se `stop` for acionado durante a consulta).
        """
        self.flush()
        c = self.connect()
        try:
            if stop is not None:
                c.set_progress_handler(lambda: 1 if stop.is_set() else 0, 50000)
            args = tuple(db_enc(a) for a in _under_args(root))
            excluder = make_dir_excluder(exclude_dirs, root) if exclude_dirs else None
            cur = c.execute(
                "SELECT d.path, count(f.rowid), "
                "COALESCE(sum(CASE WHEN f.size > 0 THEN f.size ELSE 0 END), 0) "
                "FROM dirs d LEFT JOIN files f ON f.dir_id = d.id "
                "WHERE %s AND d.state = 1 GROUP BY d.id" % _UNDER, args)
            stats = []
            for dpath, fcnt, fbytes in cur:
                dp = db_dec(dpath)
                if excluder is not None and excluder(dp):
                    continue
                stats.append((dp, fcnt, fbytes))
            pending = [db_dec(r[0]) for r in c.execute(
                "SELECT path FROM dirs d WHERE %s AND state = 0" % _UNDER, args)]
            if excluder is not None:
                pending = [p for p in pending if not excluder(p)]
            return aggregate_folder_space(stats, root, pending_dirs=len(pending))
        except sqlite3.OperationalError:
            if stop is not None and stop.is_set():
                return None
            raise
        finally:
            c.close()

def aggregate_folder_space(dir_stats, root, pending_dirs=0):
    """
    Agrega o consumo de espaço de toda a árvore sob `root` em uma única passada.
    `dir_stats`: iterável de (caminho_da_pasta, qtd_arquivos_diretos, bytes_diretos).
    """
    root = os.path.normpath(root)
    rk = path_key(root)
    nodes = {
        rk: {
            "path": root,
            "name": os.path.basename(root) or root,
            "total_size": 0,
            "total_files": 0,
            "direct_size": 0,
            "direct_files": 0,
            "children": set(),
        }
    }
    n_scanned = 0
    for dpath, fcount, fbytes in dir_stats:
        dpath = os.path.normpath(dpath)
        dk = path_key(dpath)
        if not is_under(dk, rk):
            continue
        n_scanned += 1
        fcount = max(0, int(fcount or 0))
        fbytes = max(0, int(fbytes or 0))
        if dk not in nodes:
            nodes[dk] = {
                "path": dpath,
                "name": os.path.basename(dpath) or dpath,
                "total_size": 0,
                "total_files": 0,
                "direct_size": 0,
                "direct_files": 0,
                "children": set(),
            }
        nodes[dk]["direct_size"] += fbytes
        nodes[dk]["direct_files"] += fcount
        cur_path, cur_key = dpath, dk
        while True:
            node = nodes[cur_key]
            node["total_size"] += fbytes
            node["total_files"] += fcount
            if cur_key == rk:
                break
            parent_path = os.path.dirname(cur_path)
            if not parent_path or parent_path == cur_path:
                break
            parent_key = path_key(parent_path)
            if not is_under(parent_key, rk):
                parent_key = rk
                parent_path = root
            if parent_key not in nodes:
                nodes[parent_key] = {
                    "path": parent_path,
                    "name": os.path.basename(parent_path) or parent_path,
                    "total_size": 0,
                    "total_files": 0,
                    "direct_size": 0,
                    "direct_files": 0,
                    "children": set(),
                }
            nodes[parent_key]["children"].add(cur_key)
            cur_path, cur_key = nodes[parent_key]["path"], parent_key
    root_node = nodes[rk]
    return {
        "root": root,
        "root_key": rk,
        "total_size": root_node["total_size"],
        "total_files": root_node["total_files"],
        "scanned_dirs": n_scanned,
        "pending_dirs": pending_dirs,
        "nodes": nodes,
    }

def folder_space_children(space_info, folder_path=None):
    """
    Lista o detalhamento de espaço das subpastas imediatas de `folder_path`
    (padrão: raiz), ordenadas do maior `total_size` para o menor.
    Inclui `[Arquivos na própria pasta]` se houver arquivos diretos nela.
    """
    nodes = space_info["nodes"]
    rk = space_info["root_key"]
    target_key = path_key(folder_path) if folder_path else rk
    parent = nodes.get(target_key)
    if parent is None:
        return []
    parent_total = parent["total_size"]
    root_total = space_info["total_size"]
    out = []
    for ck in parent["children"]:
        ch = nodes[ck]
        sz = ch["total_size"]
        pct_p = (sz * 100.0 / parent_total) if parent_total > 0 else 0.0
        out.append({
            "path": ch["path"],
            "name": ch["name"],
            "total_size": sz,
            "total_files": ch["total_files"],
            "direct_size": ch["direct_size"],
            "direct_files": ch["direct_files"],
            "subdirs": len(ch["children"]),
            "pct": pct_p,
            "pct_parent": pct_p,
            "pct_root": (sz * 100.0 / root_total) if root_total > 0 else 0.0,
            "is_direct_entry": False,
            "is_self": False,
        })
    if parent["direct_files"] > 0:
        dsz = parent["direct_size"]
        pct_p = (dsz * 100.0 / parent_total) if parent_total > 0 else 0.0
        out.append({
            "path": parent["path"],
            "name": "[Arquivos na própria pasta]",
            "total_size": dsz,
            "total_files": parent["direct_files"],
            "direct_size": dsz,
            "direct_files": parent["direct_files"],
            "subdirs": 0,
            "pct": pct_p,
            "pct_parent": pct_p,
            "pct_root": (dsz * 100.0 / root_total) if root_total > 0 else 0.0,
            "is_direct_entry": True,
            "is_self": True,
        })
    out.sort(key=lambda r: (r["total_size"], r["total_files"]), reverse=True)
    return out

def summarize_rows_space(rows, root, exclude_dirs=()):
    """Agrega espaço por pasta a partir de resultados em memória (dicts com dir e size)."""
    excluder = make_dir_excluder(exclude_dirs, root) if exclude_dirs else None
    by_dir = {}
    for r in rows:
        dp = r.get("dir") or os.path.dirname(r["path"])
        if excluder is not None and excluder(dp):
            continue
        sz = r.get("size")
        sz = sz if isinstance(sz, (int, float)) and sz > 0 else 0
        prev = by_dir.get(dp)
        if prev is None:
            by_dir[dp] = [1, sz]
        else:
            prev[0] += 1
            prev[1] += sz
    stats = [(dp, cnt, tot) for dp, (cnt, tot) in by_dir.items()]
    return aggregate_folder_space(stats, root, pending_dirs=0)

# ===========================================================================
# Canais: várias conexões SMB independentes com o mesmo servidor
# ===========================================================================
# Medido num servidor de produção: uma pasta cuja leitura não responde congestiona
# a CONEXÃO por onde foi pedida (tudo nela espera ~60 s e falha com erro 121),
# mas o servidor continua respondendo normalmente por OUTRA conexão. O Windows
# abre uma conexão SMB separada para cada NOME de servidor; então o mesmo
# compartilhamento acessado por \\nome-completo, \\IP e \\nome-curto são 3
# conexões independentes. Um caminho por unidade mapeada ou DFS (ex.: Y: ->
# \\empresa.local\dados) é traduzido para o servidor real por trás dele.

class Channel(object):
    """Uma conexão: troca o prefixo exibido (`display`) pelo prefixo real."""
    def __init__(self, name, display, actual, conn=None):
        self.name = name              # rótulo para log/tela (ex.: "IP 10.0.0.5")
        self.display = display        # prefixo como o usuário vê (ex.: Y:\Imagens)
        self.actual = actual          # prefixo usado nesta conexão
        # Identidade da conexão SMB (o nome de servidor usado). Y:, o DFS e
        # \\servidor compartilham a MESMA conexão se o DFS aponta para \\servidor.
        self.conn = (conn or actual.lstrip("\\").split("\\")[0]).lower()
        # True = mesma conexão que a unidade/caminho original (a que o Explorer
        # e outros programas usam): nunca recebe leituras arriscadas.
        self.user = False
        self.stuck = 0                # leituras presas nesta conexão
        self.jammed_since = None      # quando foi considerada congestionada
        self.last_ok = time.time()

    def path(self, p):
        if self.actual == self.display:
            return p
        rest = p[len(self.display):]
        return self.actual + rest

    def __repr__(self):
        return "<Canal %s %s>" % (self.name, self.actual)

def _unc_of_drive(path):
    """Y:\\x -> (\\\\servidor\\compart, \\x) para unidade de rede mapeada."""
    if not (IS_WIN and len(path) >= 2 and path[1] == ":"):
        return None, None
    try:
        import ctypes
        from ctypes import wintypes
        mpr = ctypes.WinDLL("mpr")
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if mpr.WNetGetConnectionW(path[:2], buf, ctypes.byref(n)) == 0 and buf.value.startswith("\\\\"):
            return buf.value.rstrip("\\"), path[2:]
    except Exception:
        pass
    return None, None

def _dfs_target(unc):
    """Se `unc` estiver num namespace DFS, devolve o caminho no servidor real
    (link ativo). Usa o cache local do cliente DFS — não lê pastas."""
    try:
        import ctypes
        from ctypes import wintypes

        class DFS_STORAGE_INFO(ctypes.Structure):
            _fields_ = [("State", wintypes.ULONG), ("ServerName", wintypes.LPWSTR),
                        ("ShareName", wintypes.LPWSTR)]

        class DFS_INFO_3(ctypes.Structure):
            _fields_ = [("EntryPath", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                        ("State", wintypes.DWORD), ("NumberOfStorages", wintypes.DWORD),
                        ("Storage", ctypes.POINTER(DFS_STORAGE_INFO))]
        net = ctypes.WinDLL("netapi32")
        net.NetDfsGetClientInfo.argtypes = [wintypes.LPWSTR, wintypes.LPWSTR, wintypes.LPWSTR,
                                            wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        p = ctypes.c_void_p()
        if net.NetDfsGetClientInfo(unc, None, None, 3, ctypes.byref(p)) != 0:
            return None
        try:
            info = ctypes.cast(p, ctypes.POINTER(DFS_INFO_3)).contents
            entry = "\\" + info.EntryPath.lstrip("\\")
            entry = "\\" + entry                     # "\\dominio\namespace\link"
            target = None
            for i in range(info.NumberOfStorages):
                s = info.Storage[i]
                if target is None or s.State & 0x4:  # DFS_STORAGE_STATE_ACTIVE
                    target = "\\\\%s\\%s" % (s.ServerName, s.ShareName)
            if target is None or not unc.lower().startswith(entry.lower()):
                return None
            return target + unc[len(entry):]
        finally:
            net.NetApiBufferFree(p)
    except Exception:
        return None

def _host_aliases(host):
    """Nomes distintos para o mesmo servidor: nome completo, nome completo com
    ponto final, IP, nome curto. Medido em servidor real: "nome." (com o
    ponto final do DNS) é uma conexão SMB separada de "nome" — com uma delas
    travada por 150 s, a outra respondeu normalmente o tempo todo."""
    import socket
    names = []
    try:
        fq = socket.getfqdn(host)
        names.append(fq)
        if "." in fq and not fq.replace(".", "").isdigit():
            names.append(fq.rstrip(".") + ".")
    except Exception:
        pass
    try:
        names.append(socket.gethostbyname(host))
    except Exception:
        pass
    names.append(host.split(".")[0])
    names.append(host)
    out, seen = [], set()
    for n in names:
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)
    return out

def resolve_channels(root, probe_timeout=6.0):
    """
    Lista as conexões independentes que levam à pasta `root`, já testadas
    (cada uma precisa listar `root` em até `probe_timeout` s). A primeira é a
    preferida; o caminho original (unidade/DFS) fica por último, como reserva.
    No Linux (ou se nada for descoberto) devolve só o caminho original.
    """
    root = os.path.normpath(root)
    original = Channel("caminho original", root, root)
    original.user = True
    if not IS_WIN:
        return [original]
    unc, rest = _unc_of_drive(root)
    if unc is None:
        if root.startswith("\\\\"):
            unc, rest = root, ""
        else:
            return [original]                      # disco local
    full = unc + rest
    real = _dfs_target(full) or full               # caminho no servidor real
    parts = real.lstrip("\\").split("\\", 1)
    host, tail = parts[0], ("\\" + parts[1]) if len(parts) > 1 else ""
    cands = []
    for alias in _host_aliases(host):
        actual = "\\\\" + alias + tail
        label = ("IP " if alias.replace(".", "").isdigit() else "servidor ") + alias
        cands.append(Channel(label, root, actual))
    # Unidade mapeada / DFS acabam na conexão do servidor real (nome usado no link).
    if real != full:
        cands.append(Channel("DFS " + unc, root, full, conn=host))
    original.conn = host.lower()
    cands.append(original)

    ok = []
    results = {}

    def test(ch):
        t0 = time.time()
        try:
            os.listdir(fs_path(ch.actual))
            results[id(ch)] = time.time() - t0
        except OSError as e:
            results[id(ch)] = e
    ths = [threading.Thread(target=test, args=(ch,), daemon=True) for ch in cands]
    for th in ths:
        th.start()
    deadline = time.time() + probe_timeout
    for th in ths:
        th.join(max(0.0, deadline - time.time()))
    for ch in cands:
        ch.user = ch.conn == original.conn
    # Conexões "do usuário" por último: a busca prefere não disputá-las.
    cands.sort(key=lambda c: c.user)
    seen_conn = set()
    for ch in cands:
        r = results.get(id(ch))
        # Uma entrada por CONEXÃO: dois caminhos na mesma conexão travam juntos.
        if isinstance(r, float) and ch.conn not in seen_conn:
            seen_conn.add(ch.conn)
            ok.append(ch)
        dlog("[CANAL] %-28s %s -> %s" % (ch.name, ch.actual,
             "OK %.2fs" % r if isinstance(r, float) else ("sem resposta" if r is None else "erro: %s" % r)))
    return ok or [original]

# ===========================================================================
# Thread de busca
# ===========================================================================
JAM_DETECT       = 15.0     # leitura presa há tanto tempo, sem nenhuma outra concluir = conexão travada
CHANNEL_RECOVER  = 30.0     # conexão volta a ser usada após ficar esse tempo sem leituras presas
Q_ATTEMPTS       = 2        # tentativas de uma pasta suspeita (cada uma por uma conexão diferente)
PROBLEM_RETRY_H  = 12.0     # pasta problemática conhecida é tentada de novo após esse nº de horas

class SearchThread(threading.Thread):
    """
    Modos:
      sem índice ........... varre tudo no servidor;
      índice ............... mostra o índice e lê no servidor só o que falta;
      índice + verificar ... mostra o índice e confere a data de cada pasta:
                             relê só as que mudaram (atualização incremental).

    Confiabilidade (medida no servidor real: uma pasta que não responde
    congestiona a CONEXÃO inteira por vários minutos, mas o servidor segue
    respondendo por outras conexões):
      - a busca usa várias conexões independentes com o servidor (resolve_channels);
      - se a conexão principal travar, a busca TROCA de conexão na hora; as
        pastas que travaram junto (vítimas) são refeitas imediatamente;
      - a pasta suspeita de ter causado o travamento vai para a QUARENTENA:
        é lida em segundo plano por uma conexão separada (nunca a do caminho
        original/unidade mapeada), em paralelo com o resto da busca;
      - o que não puder ser lido termina em `failed`, com o motivo, e fica
        registrado no índice como problemático (tentado de novo depois).
      - sem conexões alternativas (Linux, disco local): rodadas de novas
        tentativas no fim, 1 pasta por vez.

    Fila de saída:
      (caminho, nome, ext, tamanho, pasta, mtime)  — arquivo encontrado
      ("__STATUS__", texto, aviso)                 — progresso (a cada 0,5 s)
      ("__REMOVE__", caminho)                      — arquivo sumiu do servidor
      ("__REMOVE_DIR__", pasta)                    — pasta sumiu do servidor
      ("__ERR__", texto)                           — erro relevante
      SearchThread.DONE                            — fim
    """
    DONE = object()

    def __init__(self, root_dir, pattern, extensions, case_sensitive,
                 q, stop_ev, fast_mode=True, index=None, refresh=False, retry_problems=False,
                 channels=None, min_size=None, max_size=None, exclude_dirs=()):
        super(SearchThread, self).__init__(daemon=True)
        self.root_dir = os.path.normpath(root_dir)
        self.pattern = clean_pattern(pattern) or "*"
        self.exts = [e.lower() for e in extensions if e]
        self.case = case_sensitive
        self.match = make_matcher(self.pattern, self.exts, case_sensitive)
        self.min_size = min_size
        self.max_size = max_size
        self.size_match = make_size_matcher(min_size, max_size)
        self.exclude_dirs = list(exclude_dirs or ())
        self.dir_excluder = make_dir_excluder(self.exclude_dirs, self.root_dir)
        self.q = q
        self.stop = stop_ev
        self.fast_mode = fast_mode
        self.index = index
        self.verify = index is not None and refresh
        self.n_workers = SCAN_WORKERS if fast_mode else 1
        self.want_meta = (not fast_mode) or (self.size_match is not None)
        self._lock = threading.Lock()
        # Conexões (descobertas no início da busca, fora da GUI).
        self._given_channels = channels
        orig = Channel("caminho original", self.root_dir, self.root_dir)
        orig.user = True
        self.channels = [self._new_channel(orig)]
        self.main = self.channels[0]
        self.switches = 0
        # Contadores e estado
        self.dirs = self.scanned = self.matches = 0
        self.checked = self.changed = 0
        self.pending = 0
        self.cur_dir = self.root_dir
        self._inflight = {}    # thread -> [pasta, início, desligada_da_vaga, canal, suspeita]
        self.deferred = []     # [(tarefa, erro, início)] — sem quarentena: rodadas no fim
        self.failed = []       # [(pasta, erro)] — não lidas
        self.round = 0
        self.summary = ""
        self._shown = None     # caminhos já exibidos a partir do índice
        self._tls = threading.local()
        self._dbs = []
        self._queued = set()   # chaves de pastas já postas na fila nesta busca
        self._root_key = path_key(self.root_dir)
        self._work_q = None
        # Pastas problemáticas
        self.retry_problems = retry_problems
        self._problems = {}          # chave -> (pasta, falhas, último erro, última tentativa)
        self.skipped_problems = []   # [(pasta, falhas, erro)] puladas nesta busca
        self._tail = []              # sem quarentena: problemáticas a tentar no fim
        self._once = set()           # chaves com UMA tentativa só (problemáticas conhecidas)
        self._fails = {}             # chave -> falhas de rede nesta busca
        self._recorded = set()       # chaves já gravadas como problemáticas
        # Quarentena
        self._qq = queue.Queue()     # (tarefa, conexões já tentadas)
        self._q_active = 0           # itens da quarentena em andamento
        self._q_reading = {}         # thread -> (pasta, início, canal)
        self.quarantined = 0
        self.rescued = 0             # pastas suspeitas lidas com sucesso na quarentena
        self.hedged = 0              # vítimas refeitas na hora pela conexão saudável
        self._jams = {}              # chave -> em quantos travamentos esteve presa
        self._done = set()           # chaves de pastas já lidas nesta busca

    # -- conexões -------------------------------------------------------------
    def _new_channel(self, ch):
        ch.gate = AdaptiveGate(start=min(2, self.n_workers), maximum=self.n_workers)
        ch.inflight = 0
        ch.q_busy = False
        ch.last_return = time.time()
        return ch

    @property
    def gate(self):
        return self.main.gate

    @property
    def can_quarantine(self):
        """Troca de conexão e quarentena exigem 2+ conexões que NÃO sejam a do
        usuário (a do Explorer nunca recebe leituras arriscadas)."""
        return sum(1 for c in self.channels if not c.user) >= 2

    def _setup_channels(self):
        chs = self._given_channels
        if chs is None and IS_WIN:
            self._put(("__STATUS__", "Preparando conexões com o servidor...", ""))
            try:
                chs = resolve_channels(self.root_dir)
            except Exception as e:
                dlog("[CANAL] falha ao descobrir conexões: %s" % e)
                chs = None
        if chs:
            self.channels = [self._new_channel(c) for c in chs]
            alt = [c for c in self.channels if not c.user]
            self.main = alt[0] if alt else self.channels[0]
        dlog("[CANAL] %d conexão(ões) independente(s): %s" % (
            len(self.channels), " | ".join("%s (%s)" % (c.name, c.actual) for c in self.channels)))

    def _pick_channel(self, exclude=(), quarantine=False):
        """Conexão saudável e livre. A do caminho original (unidade/DFS, a mesma
        que o Explorer usa) NUNCA é usada quando há alternativas — nem para a
        busca principal: se todas as alternativas estiverem ocupadas, espera-se
        (teste real: cair nela travou o Explorer por ~4,5 min)."""
        cands = [c for c in self.channels
                 if c.conn not in exclude and c.jammed_since is None and not c.q_busy]
        if any(not c.user for c in self.channels):
            cands = [c for c in cands if not c.user]
        return cands[0] if cands else None

    def _idle(self, tid, e, now):
        """Segundos desde a última atividade (lote recebido) desta leitura."""
        return now - _activity.get(tid, e[1])

    def _check_channels(self, now, spawn):
        """Detecta conexão principal travada e troca; libera conexões recuperadas."""
        for c in self.channels:
            if (c.jammed_since is not None and c.inflight == 0 and not c.q_busy
                    and now - c.last_return >= CHANNEL_RECOVER):
                c.jammed_since = None
                dlog("[CANAL] %s voltou a responder" % c.name)
        if not self.can_quarantine:
            return
        ch = self.main
        with self._lock:
            items = [(tid, e) for tid, e in self._inflight.items() if e[3] is ch]
        if not items:
            return
        # Travada = NENHUMA leitura nesta conexão concluiu nem recebeu dados
        # recentemente. Pasta grande recebe lotes o tempo todo (atividade), então
        # não é confundida com pasta presa (teste real: 8 pastas IMAGENS grandes
        # ao mesmo tempo eram tomadas como "travamento" e duplicadas em cascata).
        if now - ch.last_ok < RESPONSIVE_WINDOW:
            return
        if any(self._idle(tid, e, now) < RESPONSIVE_WINDOW for tid, e in items):
            return
        stuck = [e for tid, e in items if self._idle(tid, e, now) >= JAM_DETECT]
        if not stuck:
            return
        on_main = [e for _tid, e in items]
        oldest = min(stuck, key=lambda e: e[1])
        nxt = self._pick_channel(exclude={ch.conn})
        if nxt is None:
            return
        victims = []
        with self._lock:
            oldest[4] = True               # suspeita de ter travado a conexão
            ch.jammed_since = now
            self.main = nxt
            self.switches += 1
            # Vítimas: leituras presas atrás da suspeita. Cada uma levaria minutos
            # para o Windows desistir; refaz JÁ pela conexão saudável e descarta a
            # presa quando ela voltar (self._done / entrada marcada como duplicada).
            # A suspeita (a mais antiga) pode não ser a culpada; se a culpada for
            # refeita, trava a conexão nova também (cascata vista no teste real).
            # Por isso conta em quantos travamentos cada pasta estava presa: quem
            # esteve presa em 2 é a culpada quase certa — não é refeita, fica para
            # a quarentena (quando a leitura presa falhar).
            for e in on_main:
                k = path_key(e[0])
                self._jams[k] = self._jams.get(k, 0) + 1
            for e in on_main:
                if e is oldest or e[6] or e[5] is None:
                    continue
                if self._jams.get(path_key(e[0]), 0) >= 2:
                    e[4] = True              # também suspeita: vai para a quarentena
                    continue
                e[6] = True
                victims.append(e[5])
            self.pending += len(victims)
            self.hedged += len(victims)
        dlog("[CANAL] %s travada há %ds por %s — busca continua por %s; %d leitura(s) presa(s) "
             "refeita(s) na hora" % (ch.name, now - oldest[1], oldest[0], nxt.name, len(victims)))
        wq = self._work_q
        for t in victims:
            wq.put(t)
        spawn(self.n_workers)

    # -- utilidades -------------------------------------------------------------
    def _put(self, item):
        """put() que desiste se a busca for parada — nunca bloqueia para sempre."""
        while not self.stop.is_set():
            try:
                self.q.put(item, timeout=0.05)
                return True
            except queue.Full:
                pass
        return False

    def _db(self):
        c = getattr(self._tls, "db", None)
        if c is None:
            c = self.index.connect()
            self._tls.db = c
            with self._lock:
                self._dbs.append(c)
        return c

    def _admit(self, children, skip_done):
        """Filtra subpastas: nunca enfileira a mesma pasta duas vezes na mesma
        busca, ignora pastas excluídas e, no modo índice, pula as já lidas."""
        db = self._db() if (skip_done and self.index is not None) else None
        out = []
        for cp, mt in children:
            if self.dir_excluder is not None and self.dir_excluder(cp):
                continue
            k = path_key(cp)
            if db is not None:
                row = db.execute("SELECT state FROM dirs WHERE key = ?", (db_enc(k),)).fetchone()
                if row and row[0] == 1:
                    continue
            with self._lock:
                if k in self._queued:
                    continue
                self._queued.add(k)
                if k in self._problems and k != self._root_key:
                    self._park_problem(k, (cp, mt))
                    continue
            out.append((cp, mt))
        return out

    def _park_problem(self, k, task):
        """Pasta que já travou a conexão antes. Chamar com self._lock.
        Com conexões alternativas: vai para a quarentena (lida em segundo
        plano, sem atrasar nada) se pedida pelo usuário ou se a última
        tentativa foi há mais de PROBLEM_RETRY_H horas; senão é pulada com
        aviso. Sem conexões alternativas: fim da busca ou pulada."""
        p, fails, err, last_try = self._problems[k]
        due = self._problem_due(k)
        if due and self.can_quarantine:
            self._once.add(k)
            self._q_active += 1
            self.quarantined += 1
            self._qq.put((task, frozenset()))
        elif due and self.retry_problems:
            self._tail.append(task)
            self._once.add(k)
        else:
            self.skipped_problems.append((p, fails, err))

    def _problem_due(self, k):
        """Pasta problemática deve ser tentada de novo nesta busca?"""
        last_try = self._problems[k][3]
        return (self.retry_problems or not last_try
                or (time.time() - last_try) / 3600.0 >= PROBLEM_RETRY_H)

    def _dir_row(self, path):
        return self._db().execute("SELECT id, state, dmtime FROM dirs WHERE key = ?",
                                  (db_key(path),)).fetchone()

    def _call(self, fn, path, ch, follow_main=False):
        """Uma ida ao servidor pela conexão `ch`, respeitando a vaga dela.
        follow_main=True (busca principal): se a conexão principal mudou
        enquanto esperava a vaga, vai pela nova — nunca entra numa travada."""
        while True:
            gate = ch.gate
            c = ch
            got = gate.acquire(self.stop, (lambda: c is not self.main) if follow_main else None)
            if got is False:
                return None
            if got and (not follow_main or ch is self.main):
                break
            if got:
                gate.cancel()
            ch = self.main       # a principal mudou enquanto esperava: vai pela nova
        me = threading.get_ident()
        # [pasta, início, desligada_da_vaga, canal, suspeita, tarefa, duplicada]
        entry = [path, time.time(), False, ch, False, getattr(self._tls, "task", None), False]
        _activity[me] = entry[1]
        with self._lock:
            self._inflight[me] = entry
            ch.inflight += 1
        timed_out = False
        try:
            res = fn(ch.path(path))
            ch.last_ok = time.time()
            return res
        except OSError as e:
            timed_out = is_retryable(e)
            e.gff_entry = entry
            raise
        finally:
            _activity.pop(me, None)
            with self._lock:
                self._inflight.pop(me, None)
                detached = entry[2]
                ch.inflight -= 1
                ch.last_return = time.time()
            gate.release(timed_out, detached=detached)

    # -- processamento de uma pasta ----------------------------------------
    def _list_and_emit(self, path, observed, trust, ch):
        t0 = time.time()
        res = self._call(lambda p: list_dir(p, self.want_meta), path, ch or self.main,
                         follow_main=ch is None)
        if res is None:
            return []
        with self._lock:
            k = path_key(path)
            if k in self._done:
                return []          # a cópia refeita pela outra conexão já leu esta pasta
            self._done.add(k)
        dnames, files = res
        el = time.time() - t0
        if el >= 5:
            dlog("[PASTA LENTA] %.1fs | %d subpastas, %d arquivos | %s" % (
                el, len(dnames), len(files), path))
        # Decide as subpastas ANTES de gravar esta leitura no índice (a gravação
        # insere as subpastas como pendentes e confundiria o filtro).
        children = self._admit([(os.path.join(path, name), mt if mt is not None and mt >= 0 else None)
                                for name, mt in dnames], skip_done=trust)
        db = self._db() if self.index is not None else None
        old_names = None
        if self.index is not None:
            if self.verify:
                row = self._dir_row(path)
                if row:
                    old_names = {db_dec(r[0]) for r in db.execute(
                        "SELECT name FROM files WHERE dir_id = ?", (row[0],))}
                    # Subpastas que sumiram do servidor: tira da TELA o que veio delas
                    # pelo índice (o índice em si é corrigido pela gravação abaixo).
                    now_dirs = {path_key(os.path.join(path, n)) for n, _m in dnames}
                    for (old,) in db.execute("SELECT path FROM dirs WHERE parent = ?", (row[0],)):
                        old = db_dec(old)
                        if path_key(old) not in now_dirs:
                            self._put(("__REMOVE_DIR__", old))
            # Grava mesmo se a busca foi parada: a leitura já foi paga.
            self.index.record_dir(path, dnames, files, observed)
        self.cur_dir = path
        shown = self._shown
        for name, size, mtime in files:
            if self.stop.is_set():
                break
            if self.match(name) and (self.size_match is None or self.size_match(size)):
                fp = os.path.join(path, name)
                if shown is not None and path_key(fp) in shown:
                    continue   # já exibido a partir do índice
                with self._lock:
                    self.matches += 1
                self._put((fp, name, os.path.splitext(name)[1], size, path, mtime))
        if old_names:
            for name in old_names - {f[0] for f in files}:
                if self.match(name):
                    self._put(("__REMOVE__", os.path.join(path, name)))
        with self._lock:
            self.dirs += 1
            self.scanned += len(files)
        return children

    def _verify(self, path, _observed, ch):
        """
        Atualização incremental: relê a pasta só se a data dela mudou.
        A data é consultada NA PRÓPRIA PASTA (1 ida rápida ao servidor): a
        cópia que vem na listagem da pasta-mãe pode estar atrasada no
        NTFS/SMB e esconderia alterações. A data guardada no índice pode ser
        essa cópia atrasada — nunca adiantada —, então no pior caso a pasta
        é relida sem necessidade; uma alteração nunca passa despercebida.
        """
        row = self._dir_row(path)
        m = self._call(dir_mtime, path, ch or self.main, follow_main=ch is None)  # ANTES de listar
        if m is None:
            return []
        with self._lock:
            self.checked += 1
        if row and row[1] == 1 and row[2] is not None and abs(m - row[2]) < MTIME_TOL:
            # Pasta igual à do índice: arquivos dela continuam válidos.
            kids = [db_dec(r[0]) for r in self._db().execute(
                "SELECT path FROM dirs WHERE parent = ?", (row[0],))]
            return self._admit([(k, None) for k in kids], skip_done=False)
        with self._lock:
            self.changed += 1
        return self._list_and_emit(path, m, trust=False, ch=ch)

    def _process(self, task, ch):
        if self.verify:
            return self._verify(task[0], task[1], ch)
        return self._list_and_emit(task[0], task[1], trust=self.index is not None, ch=ch)

    def _mark_problem(self, path, err):
        k = path_key(path)
        if self.index is not None and k not in self._recorded:
            self._recorded.add(k)
            self.index.record_problem(path, err)
            dlog("[PROBLEMÁTICA] %s registrada: %s" % (path, err))

    def _fail_other(self, path, e):
        """Erro que não é de rede (sem permissão, pasta apagada...)."""
        dlog("[AVISO] %s: %s" % (path, e))
        if is_not_found(e) and path_key(path) != self._root_key:
            # Pasta apagada/renomeada no servidor durante a busca: não é falha de
            # leitura (não entra em "não lidas"); só some do índice e da tela.
            if self.index is not None:
                self.index.record_missing(path)
            self._put(("__REMOVE_DIR__", path))
            return
        with self._lock:
            self.failed.append((path, describe_error(e)))

    def _on_error(self, task, e, work_q):
        """Erro numa leitura da busca principal. Devolve True se a tarefa foi
        reposta na fila principal (vítima de conexão travada)."""
        path = task[0]
        if not is_retryable(e):
            self._fail_other(path, e)
            return False
        k = path_key(path)
        entry = getattr(e, "gff_entry", None)
        with self._lock:
            if k in self._done or (entry is not None and entry[6]):
                return False       # leitura presa já refeita pela conexão saudável
            n = self._fails[k] = self._fails.get(k, 0) + 1
        if self.can_quarantine:
            ch = entry[3] if entry else None
            victim = entry is not None and not entry[4] and ch is not None and ch.jammed_since is not None
            if victim and n == 1:
                # Travou junto com a suspeita: refaz já, pela conexão saudável.
                dlog("[REFEITA] %s (presa na conexão travada %s)" % (path, ch.name))
                with self._lock:
                    self.pending += 1
                work_q.put(task)
                return True
            with self._lock:
                self._q_active += 1
                self.quarantined += 1
            dlog("[QUARENTENA] %s: %s — será lida por conexão separada" % (path, e))
            self._qq.put((task, frozenset([ch.conn]) if ch is not None else frozenset()))
            return False
        # Sem conexões alternativas: adia para as rodadas do fim.
        if k in self._once:
            dlog("[PROBLEMÁTICA] %s continua travando: %s" % (path, e))
            self._mark_problem(path, describe_error(e))
            with self._lock:
                self.failed.append((path, describe_error(e)))
            return False
        with self._lock:
            self.deferred.append((task, describe_error(e), entry[1] if entry else time.time()))
        dlog("[ADIADA] %s: %s" % (path, e))
        if self.round > 0 or n >= 2:
            self._mark_problem(path, describe_error(e))
        return False

    def _worker(self, work_q):
        while not self.stop.is_set():
            try:
                task = work_q.get(timeout=0.3)
            except queue.Empty:
                with self._lock:
                    # Espera a quarentena: ela pode devolver subpastas para cá.
                    if self.pending == 0 and self._q_active == 0:
                        return
                continue
            children = []
            self._tls.task = task
            try:
                children = self._process(task, None)     # None = conexão principal do momento
            except OSError as e:
                self._on_error(task, e, work_q)
            except Exception:
                dlog("[ERRO] %s\n%s" % (task[0], traceback.format_exc()))
            finally:
                with self._lock:
                    if self.stop.is_set():
                        children = []
                    self.pending += len(children) - 1
                for c in children:
                    work_q.put(c)

    # -- quarentena (leituras suspeitas por conexão separada) ------------------
    def _q_loop(self, work_q):
        while not self.stop.is_set():
            try:
                task, tried = self._qq.get(timeout=0.5)
            except queue.Empty:
                with self._lock:
                    if self.pending == 0 and self._q_active == 0:
                        return
                continue
            ch = None
            while not self.stop.is_set():
                with self._lock:
                    main_idle = self.pending == 0
                # Nunca disputa a conexão principal (uma pasta recuperada devolve
                # subpastas para ela — teste real: travou a principal de novo).
                # Exceção: a principal é a ÚNICA conexão que falta tentar.
                others = [c for c in self.channels if not c.user and c.conn not in tried
                          and c is not self.main]
                use_main = main_idle and not others
                excl = set(tried) | (set() if use_main else {self.main.conn})
                ch = self._pick_channel(exclude=excl, quarantine=True)
                if ch is not None:
                    break
                if all(c.conn in tried for c in self.channels
                       if not c.user or all(x.user for x in self.channels)):
                    break      # já tentada por todas as conexões possíveis
                self.stop.wait(1.0)
            if ch is None:
                self._q_give_up(task, "não respondeu por nenhuma das %d conexão(ões) testadas" % len(tried))
                continue
            ch.q_busy = True
            threading.Thread(target=self._q_read, args=(task, tried, ch, work_q), daemon=True).start()

    def _q_give_up(self, task, err):
        path = task[0]
        self._mark_problem(path, err)
        with self._lock:
            self.failed.append((path, err))
            self._q_active -= 1

    def _q_read(self, task, tried, ch, work_q):
        path = task[0]
        me = threading.get_ident()
        with self._lock:
            self._q_reading[me] = (path, time.time(), ch)
        dlog("[QUARENTENA] lendo %s por %s (tentativa %d de %d)" % (path, ch.name, len(tried) + 1, Q_ATTEMPTS))
        requeued = False
        try:
            children = self._process(task, ch)
            dlog("[QUARENTENA] %s lida com sucesso por %s" % (path, ch.name))
            with self._lock:
                self.rescued += 1
                if self.stop.is_set():
                    children = []
                self.pending += len(children)
            for c in children:
                work_q.put(c)
        except OSError as e:
            if is_retryable(e):
                ch.jammed_since = time.time()
                tried2 = tried | {ch.conn}
                if len(tried2) < Q_ATTEMPTS and not self.stop.is_set():
                    dlog("[QUARENTENA] %s falhou por %s (%s) — tentará outra conexão" % (path, ch.name, e))
                    self._qq.put((task, tried2))
                    requeued = True
                else:
                    self._mark_problem(path, describe_error(e))
                    with self._lock:
                        self.failed.append((path, "%s (tentada por %d conexões)" % (
                            describe_error(e), len(tried2))))
            else:
                self._fail_other(path, e)
        except Exception:
            dlog("[ERRO] quarentena %s\n%s" % (path, traceback.format_exc()))
        finally:
            ch.q_busy = False
            with self._lock:
                self._q_reading.pop(me, None)
                if not requeued:
                    self._q_active -= 1

    # -- progresso ------------------------------------------------------------
    def _status(self):
        now = time.time()
        with self._lock:
            d, s, p = self.dirs, self.scanned, self.pending
            ck, ch = self.checked, self.changed
            nd, nf = len(self.deferred), len(self.failed)
            slow = sorted(((now - e[1], e[0]) for e in self._inflight.values()
                           if e[3] is self.main and now - e[1] >= 5), reverse=True)
            ns = len(self.skipped_problems)
            qr = sorted(((now - t0, pth) for pth, t0, _c in self._q_reading.values()), reverse=True)
            qa = self._q_active
            tail = [w for _a, w in slow if path_key(w) in self._once]
            # Suspeitas presas e leituras já refeitas não contam como "na fila".
            stuck = sum(1 for e in self._inflight.values() if e[4] or e[6])
        p = max(0, p - stuck)
        multi = len(self.channels) > 1
        if stuck and p == 0 and self.round == 0:
            qa += stuck
        if self.round == 0 and p > 0:
            if self.verify:
                main = "Verificando alterações: %s pastas conferidas, %s relidas · %s na fila" % (
                    fmt_n(ck), fmt_n(ch), fmt_n(p))
            else:
                main = "Lendo servidor: %s pastas · %s arquivos · %s na fila" % (
                    fmt_n(d), fmt_n(s), fmt_n(p))
            main += " · %d leitura(s) simultânea(s)" % self.gate.limit
            if multi:
                main += " · conexão: %s" % self.main.name
        elif qa:
            main = ("Busca principal concluída (%s pastas). Lendo %d pasta(s) problemática(s) por "
                    "conexão separada — pode Parar sem perder resultados" % (fmt_n(d), qa))
        elif tail:
            main = ("Busca principal concluída. Tentando pasta problemática (costuma travar o "
                    "servidor — pode Parar sem perder resultados): %s" % shorten(tail[0], 60))
        elif self.round > 0:
            main = ("Busca principal concluída. Novas tentativas — rodada %d de %d (1 pasta por vez): "
                    "%s pasta(s) restante(s)" % (self.round, MAX_RETRY_ROUNDS, fmt_n(p)))
        else:
            main = "Finalizando..."
        warn = []
        jammed = [c for c in self.channels if c.jammed_since is not None]
        if slow and not self.gate.responsive(15):
            age, where = slow[0]
            warn.append("conexão sem responder há %ds — %s; pedido mais antigo: %s" % (
                now - self.gate.last_ok,
                "trocando de conexão" if multi else "novas leituras suspensas para não piorar",
                shorten(where, 50)))
        elif slow:
            age, where = slow[0]
            warn.append("%d pasta(s) lenta(s) em leitura, a busca continua nas demais — "
                        "mais antiga há %ds: %s" % (len(slow), age, shorten(where, 50)))
        if self.gate.pause_until > now:
            warn.append("conexão congestionada: pausa de %ds antes de continuar"
                        % (self.gate.pause_until - now + 1))
        if jammed:
            warn.append("%d conexão(ões) travada(s) por pasta problemática, isolada(s) da busca" % len(jammed))
        if qr:
            warn.append("quarentena: %d pasta(s) em leitura por conexão separada — mais antiga há %ds: %s"
                        % (len(qr), qr[0][0], shorten(qr[0][1], 45)))
        elif qa:
            warn.append("quarentena: %d pasta(s) aguardando conexão livre" % qa)
        if nd:
            warn.append("%d pasta(s) com falha de rede adiada(s) para o final" % nd)
        if nf:
            warn.append("%d pasta(s) não puderam ser lidas" % nf)
        if ns:
            warn.append("%d pasta(s) problemática(s) puladas" % ns)
        return main, " · ".join(warn)

    # -- coordenação ----------------------------------------------------------
    def _from_index(self):
        """Fase 1: emite o que já está no índice e decide o que falta ler.
        Devolve a lista de tarefas [(pasta, mtime_observado)]."""
        self._put(("__STATUS__", "Lendo índice local...", ""))
        t0 = time.time()
        shown = set()   # limitado pelo nº de resultados exibidos (MAX_RESULTS)

        def emit(item):
            shown.add(path_key(item[0]))
            with self._lock:
                self.matches += 1
            self._put(item)

        try:
            info = self.index.query(self.root_dir, self.match, emit, self.stop,
                                    size_matcher=self.size_match, dir_excluder=self.dir_excluder)
        except Exception as e:
            dlog("[ÍNDICE] falha na leitura, varrendo o servidor: %s" % e)
            self.index = None
            self.verify = False
            return [(self.root_dir, None)]
        if info is None:          # parada durante a leitura do índice
            return []
        dlog("[ÍNDICE] %d encontrados em %.1fs | %d pastas / %d arquivos indexados | "
             "%d pastas pendentes | raiz lida: %s" % (
                 info["emitted"], time.time() - t0, info["dirs"], info["files"],
                 len(info["pending"]), info["root_done"]))
        when = fdate(info["oldest"]) if info["oldest"] else ""
        self._problems = {path_key(r[0]): (r[0], r[1], r[2], r[3] if len(r) > 3 else None)
                          for r in info.get("problems", [])}
        if self._problems:
            dlog("[ÍNDICE] %d pasta(s) problemática(s) conhecida(s) sob a raiz: %s" % (
                len(self._problems), "; ".join(v[0] for v in list(self._problems.values())[:10])))
        if self.verify:
            self._shown = shown
            self.summary = ("índice (%s arquivos) + verificação incremental no servidor"
                            % fmt_n(info["files"])) if info["dirs"] else "servidor"
            return [(self.root_dir, None)]
        tasks = list(info["pending"])
        if not info["root_done"]:
            tasks.insert(0, (self.root_dir, None))
        if not info["dirs"]:
            self.summary = "servidor"
        elif tasks:
            self.summary = "índice (%s arquivos, de %s) + %s pasta(s) que faltavam" % (
                fmt_n(info["files"]), when, fmt_n(len(tasks)))
        else:
            self.summary = ("índice local: %s arquivos, lidos em %s — marque "
                            "\"Verificar alterações\" para atualizar") % (fmt_n(info["files"]), when)
        return tasks

    def _run_round(self, tasks, n):
        work_q = queue.Queue()
        self._work_q = work_q
        with self._lock:
            self.pending = len(tasks)
        for t in tasks:
            work_q.put(t)
        threads = []

        def spawn(k):
            alive = sum(1 for th in threads if th.is_alive())
            for _ in range(max(0, min(k, 4 * max(n, 1) - alive))):
                th = threading.Thread(target=self._worker, args=(work_q,), daemon=True)
                th.start()
                threads.append(th)
        spawn(n)
        q_thread = None
        if self.can_quarantine and self.round == 0:
            q_thread = threading.Thread(target=self._q_loop, args=(work_q,), daemon=True)
            q_thread.start()
        t_status = t_log = 0.0
        while True:
            alive = [th for th in threads if th.is_alive()]
            q_alive = q_thread is not None and q_thread.is_alive()
            if (not alive and not q_alive) or self.stop.wait(0.25):
                break
            now = time.time()
            if self.round == 0:
                self._check_channels(now, spawn)
            # Leitura lenta numa conexão que segue respondendo (pasta grande):
            # libera a vaga para a busca seguir nas outras pastas.
            newly_slow = []
            with self._lock:
                for e in self._inflight.values():
                    g = e[3].gate
                    if (self.round == 0 and e[3] is self.main and not e[2]
                            and now - e[1] >= SLOW_AFTER and g.can_detach()):
                        e[2] = True
                        newly_slow.append(e)
                        g.detach()
            for e in newly_slow:
                dlog("[LENTA] %s — lendo há %ds; a busca segue nas demais pastas" % (e[0], now - e[1]))
                spawn(1)
            if now - t_status >= 0.5:
                t_status = now
                main, warn = self._status()
                self._put(("__STATUS__", main, warn))
            if now - t_log >= 15:
                t_log = now
                main, warn = self._status()
                dlog("[PROGRESSO] %s | %d encontrados%s" % (
                    main, self.matches, (" | " + warn) if warn else ""))
        self._work_q = None

    def _scan(self):
        mode = "verificar alterações" if self.verify else ("índice" if self.index is not None else "sem índice")
        dlog("=== BUSCA %s === raiz=%s | padrão=%r | exts=%s | case=%s | até %d simultâneas | %s" % (
            "RÁPIDA" if self.fast_mode else "SEQUENCIAL", self.root_dir,
            self.pattern, self.exts, self.case, self.n_workers, mode))
        tasks = self._from_index() if self.index is not None else [(self.root_dir, None)]
        # Descobrir/testar conexões custa alguns segundos: só quando houver
        # algo a ler no servidor (índice completo = nenhuma ida ao servidor).
        if any(path_key(t[0]) not in self._problems or self._problem_due(path_key(t[0]))
               for t in tasks):
            self._setup_channels()
        main_tasks = []
        with self._lock:
            for t in tasks:
                k = path_key(t[0])
                if k in self._queued:
                    continue
                self._queued.add(k)
                if k in self._problems and k != self._root_key:
                    self._park_problem(k, t)
                else:
                    main_tasks.append(t)
        tasks = main_tasks
        if not self.summary:
            self.summary = "servidor"
        try:
            while not self.stop.is_set():
                if tasks or (self.round == 0 and self._q_active):
                    self._run_round(tasks, self.n_workers if self.round == 0 else 1)
                with self._lock:
                    # Sem quarentena: a pasta-veneno é a que COMEÇOU primeiro quando a
                    # conexão travou (as outras ficaram presas atrás dela): tenta as
                    # mais recentes antes.
                    last = [(t, err) for t, err, _st in sorted(self.deferred, key=lambda x: -x[2])]
                    self.deferred = []
                    tail, self._tail = self._tail, []
                tasks = [t for t, _err in last] + tail
                if not tasks or self.stop.is_set():
                    break
                if self.round >= MAX_RETRY_ROUNDS:
                    with self._lock:
                        self.failed.extend((t[0], err) for t, err in last)
                        self.skipped_problems.extend(self._problems[path_key(t[0])][:3] for t in tail)
                    for t, err in last:
                        self._mark_problem(t[0], err)
                    break
                self.round += 1
                self.gate.force(1)
                dlog("[RODADA %d/%d] tentando de novo %d pasta(s) adiada(s)%s" % (
                    self.round, MAX_RETRY_ROUNDS, len(last),
                    " + %d problemática(s) conhecida(s)" % len(tail) if tail else ""))
                end = time.time() + RETRY_PAUSE
                while not self.stop.is_set() and time.time() < end:
                    self._put(("__STATUS__",
                               "Busca principal concluída. Pausa de %ds antes de tentar de novo "
                               "%d pasta(s) que falharam (rodada %d de %d)..." % (
                                   max(0, end - time.time()), len(tasks), self.round, MAX_RETRY_ROUNDS),
                               "%d pasta(s) deixadas para o final" % len(tasks)))
                    self.stop.wait(min(1.0, max(0.0, end - time.time())))
        finally:
            with self._lock:
                dbs, self._dbs = self._dbs, []
            for c in dbs:
                try: c.close()
                except Exception: pass
        if self.switches or self.quarantined:
            self.summary += " · %d troca(s) de conexão, %d pasta(s) em quarentena (%d recuperada(s))" % (
                self.switches, self.quarantined, self.rescued)
        if self.failed:
            dlog("[FALHA FINAL] %d pasta(s) não lidas:\n  %s" % (
                len(self.failed), "\n  ".join("%s — %s" % f for f in self.failed[:200])))
            if any(path_key(p) == path_key(self.root_dir) for p, _ in self.failed):
                self._put(("__ERR__", "Pasta raiz inacessível: %s" % self.failed[0][1]))
            self.summary += " · %d pasta(s) não lidas" % len(self.failed)
        if self.skipped_problems:
            dlog("[PROBLEMÁTICAS PULADAS] %d: %s" % (
                len(self.skipped_problems), "; ".join(p for p, _f, _e in self.skipped_problems[:50])))
            self.summary += " · %d problemática(s) puladas" % len(self.skipped_problems)
        dlog("[BUSCA ENCERRADA] %d pastas | %d arquivos | %d encontrados | %d conferidas, %d relidas | "
             "%d falhas | %d trocas de conexão | quarentena %d (%d recuperadas) — %s%s" % (
                 self.dirs, self.scanned, self.matches, self.checked, self.changed,
                 len(self.failed), self.switches, self.quarantined, self.rescued, self.summary,
                 " (parada pelo usuário)" if self.stop.is_set() else ""))

    def run(self):
        try:
            self._scan()
        except Exception as e:
            dlog("[EXCEÇÃO NA BUSCA] %s" % traceback.format_exc())
            try: self.q.put(("__ERR__", str(e)), timeout=1)
            except queue.Full: pass
        finally:
            # A GUI drena a fila continuamente; insiste até entregar o DONE.
            # Se a busca foi parada, desiste — o watchdog da GUI finaliza.
            while True:
                try:
                    self.q.put(SearchThread.DONE, timeout=0.1)
                    break
                except queue.Full:
                    if self.stop.is_set():
                        break

# ===========================================================================
# Cópia
# ===========================================================================
_COPY_CHUNK = 1024 * 1024   # 1 MB — o padrão do shutil (16-64 KB) é lento em SMB

class CopyCancelled(Exception):
    pass

def copy_file(src, dst, stop):
    """Como shutil.copy2, em blocos de 1 MB e cancelável a cada bloco.
    Em cancelamento/erro remove o arquivo parcial do destino."""
    sz = 0
    try:
        with open(fs_path(src), "rb") as fi, open(fs_path(dst), "wb") as fo:
            while True:
                if stop.is_set():
                    raise CopyCancelled("cancelado")
                buf = fi.read(_COPY_CHUNK)
                if not buf:
                    break
                fo.write(buf)
                sz += len(buf)
    except BaseException:
        try: os.remove(fs_path(dst))
        except OSError: pass
        raise
    try: shutil.copystat(fs_path(src), fs_path(dst))
    except OSError: pass
    return sz

class CopyWorker(threading.Thread):
    def __init__(self, wq, dq, stop):
        super(CopyWorker, self).__init__(daemon=True)
        self.wq, self.dq, self.stop = wq, dq, stop

    def run(self):
        # NÃO encerra por fila vazia: o alimentador pode demorar (exists/makedirs
        # na rede). Sai apenas no sentinela None ou no cancelamento.
        while not self.stop.is_set():
            try:
                task = self.wq.get(timeout=0.5)
            except queue.Empty:
                continue
            if task is None:
                break
            src, dst = task
            ok, msg, sz = True, "", 0
            try:
                sz = copy_file(src, dst, self.stop)
            except Exception as e:
                ok, msg = False, describe_error(e)
            self.dq.put((src, dst, ok, msg, sz))

class CopyManager(object):
    """Cópia paralela. Mensagens na fila `pq`:
         ("TOTAL", n) | ("PROG", feitos, total, src, ok, bytes_por_s, n_erros)
         ("DONE", [(src, msg_erro), ...])"""
    N = 4

    def __init__(self, files, dest, keep, pq, stop):
        self.files, self.dest, self.keep = files, dest, keep
        self.pq, self.stop = pq, stop
        self.wq, self.dq = queue.Queue(), queue.Queue()
        # Destinos já reservados nesta cópia: dois arquivos de mesmo nome
        # (modo Plana) não podem receber o mesmo destino.
        self._reserved = set()

    def _taken(self, d):
        return os.path.normcase(d) in self._reserved or os.path.exists(fs_path(d))

    def _dst(self, src, root):
        rel = None
        if self.keep and root:
            try:
                rel = os.path.relpath(src, root)
            except ValueError:   # unidades diferentes no Windows
                rel = None
            if rel and rel.startswith(os.pardir):
                rel = None
        d = os.path.join(self.dest, rel or os.path.basename(src))
        if self._taken(d):
            base, ext = os.path.splitext(d)
            n = 1
            while self._taken("%s_%d%s" % (base, n, ext)):
                n += 1
            d = "%s_%d%s" % (base, n, ext)
        self._reserved.add(os.path.normcase(d))
        return d

    def start(self, root):
        total = len(self.files)
        self.pq.put(("TOTAL", total))
        workers = [CopyWorker(self.wq, self.dq, self.stop)
                   for _ in range(min(self.N, max(total, 1)))]
        for w in workers:
            w.start()

        def feed():
            # Fora da GUI: exists/makedirs num destino de rede desconectado
            # pode bloquear por dezenas de segundos.
            try:
                for src in self.files:
                    if self.stop.is_set():
                        break
                    try:
                        d = self._dst(src, root)
                        os.makedirs(fs_path(os.path.dirname(d)), exist_ok=True)
                    except Exception as e:
                        self.dq.put((src, "", False, describe_error(e), 0))
                        continue
                    self.wq.put((src, d))
            finally:
                for _ in workers:
                    self.wq.put(None)

        def monitor():
            done, errs, sz = 0, [], 0
            t0 = time.time()
            while done < total and not self.stop.is_set():
                try:
                    src, dst, ok, msg, s = self.dq.get(timeout=0.5)
                except queue.Empty:
                    continue
                done += 1
                sz += s
                if not ok:
                    errs.append((src, msg))
                el = time.time() - t0
                self.pq.put(("PROG", done, total, src, ok, sz / el if el > 0 else 0, len(errs)))
            for w in workers:
                w.join(timeout=2)
            self.pq.put(("DONE", errs))

        threading.Thread(target=feed, daemon=True).start()
        threading.Thread(target=monitor, daemon=True).start()

# ===========================================================================
# Exportação de resultados (CSV / TXT / Excel) — só biblioteca padrão
# ===========================================================================
EXPORT_HEADER = ("Nome", "Extensão", "Tamanho (bytes)", "Tamanho", "Modificado",
                 "Pasta", "Caminho completo")
EXPORT_FORMATS = {".xlsx": "Excel", ".csv": "CSV", ".txt": "TXT"}

def _valid_mtime(mt):
    """Data utilizável (algum arquivo pode ter data absurda, ex.: ano 30828 do
    FILETIME máximo): None em vez de derrubar a exportação inteira."""
    if not isinstance(mt, (int, float)) or mt <= 0:
        return None
    try:
        time.localtime(mt)
        import datetime
        datetime.datetime.fromtimestamp(mt)
        return mt
    except (ValueError, OSError, OverflowError):
        return None

def _export_rows(rows):
    """rows: dicts com path, dir, size, mtime (como guardados pela interface)."""
    for r in rows:
        path = r["path"]
        name = os.path.basename(path)
        size = r.get("size")
        size = size if isinstance(size, (int, float)) and size >= 0 else None
        mt = _valid_mtime(r.get("mtime"))
        yield name, os.path.splitext(name)[1], size, mt, r.get("dir") or os.path.dirname(path), path

_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")

def _csv_safe(s):
    """Injeção de fórmula (OWASP "CSV Injection"): um nome como =HYPERLINK(...)
    viraria fórmula ao abrir o CSV no Excel. O apóstrofo faz o Excel tratá-lo
    como texto. (No .xlsx não é preciso: as células são gravadas como texto.)"""
    return "'" + s if s.startswith(_FORMULA_START) else s

def export_csv(rows, dest):
    """CSV com ';' e UTF-8 com BOM: abre direto no Excel em português, com acentos."""
    import csv
    n = 0
    # errors="replace": nome com caractere inválido (Samba antigo) não derruba a exportação
    with open(fs_path(dest), "w", encoding="utf-8-sig", errors="replace", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(EXPORT_HEADER)
        for name, ext, size, mt, folder, path in _export_rows(rows):
            w.writerow([_csv_safe(name), ext, "" if size is None else int(size),
                        fsize(size) if size is not None else "",
                        time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(mt)) if mt else "",
                        _csv_safe(folder), _csv_safe(path)])
            n += 1
    return n

def export_txt(rows, dest):
    """Um caminho completo por linha (para scripts, robocopy, listas de cópia)."""
    n = 0
    with open(fs_path(dest), "w", encoding="utf-8", errors="replace", newline="\n") as f:
        for _name, _ext, _size, _mt, _folder, path in _export_rows(rows):
            f.write(path + "\n")
            n += 1
    return n

_XML_BAD = dict.fromkeys(c for c in range(32) if c not in (9, 10, 13))

def _xml(s):
    s = _SURROGATE_RE.sub("�", str(s).translate(_XML_BAD))   # XML não aceita surrogates
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def _xlsx_col(i):
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s

def export_xlsx(rows, dest, sheet="Resultados"):
    """
    Planilha .xlsx mínima e válida (Office Open XML), escrita com zipfile:
    cabeçalho em negrito e congelado, filtro, tamanho como número e data como
    data de verdade (ordenáveis no Excel/LibreOffice).
    """
    import datetime
    import zipfile
    epoch = datetime.datetime(1899, 12, 30)
    widths = [len(h) for h in EXPORT_HEADER]
    out = []
    n = 0
    for name, ext, size, mt, folder, path in _export_rows(rows):
        n += 1
        r = n + 1
        cells = []

        def s(col, v):
            widths[col] = max(widths[col], min(len(v), 80))
            cells.append('<c r="%s%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                         % (_xlsx_col(col), r, _xml(v)))
        s(0, name)
        s(1, ext)
        if size is not None:
            cells.append('<c r="C%d" s="2"><v>%d</v></c>' % (r, int(size)))
            s(3, fsize(size))
        if mt:
            serial = (datetime.datetime.fromtimestamp(mt) - epoch).total_seconds() / 86400.0
            cells.append('<c r="E%d" s="3"><v>%.8f</v></c>' % (r, serial))
        s(5, folder)
        s(6, path)
        out.append('<row r="%d">%s</row>' % (r, "".join(cells)))
    widths[4] = max(widths[4], 17)
    _write_xlsx_package(dest, sheet, EXPORT_HEADER, out, widths)
    return n

def _write_xlsx_package(dest, sheet, header, out, widths):
    import zipfile
    n = len(out)
    last = _xlsx_col(len(header) - 1)
    head = "".join('<c r="%s1" t="inlineStr" s="1"><is><t>%s</t></is></c>' % (_xlsx_col(i), _xml(h))
                   for i, h in enumerate(header))
    cols = "".join('<col min="%d" max="%d" width="%.1f" customWidth="1"/>' % (i + 1, i + 1, w + 2)
                   for i, w in enumerate(widths))
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<dimension ref="A1:%s%d"/>'
        '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
        'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
        '<cols>%s</cols><sheetData><row r="1">%s</row>%s</sheetData>'
        '<autoFilter ref="A1:%s%d"/></worksheet>' % (last, n + 1, cols, head, "".join(out), last, n + 1))
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<numFmts count="2">'
        '<numFmt numFmtId="164" formatCode="dd/mm/yyyy hh:mm"/>'
        '<numFmt numFmtId="165" formatCode="0.0&quot;%&quot;"/>'
        '</numFmts>'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="5"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        '<xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
        '</cellXfs></styleSheet>')
    files = {
        "[Content_Types].xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '</Types>',
        "_rels/.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        "xl/workbook.xml":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="%s" sheetId="1" r:id="rId1"/></sheets>'
            '<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">'
            "'%s'!$A$1:$%s$%d</definedName></definedNames></workbook>"
            % (_xml(sheet), _xml(sheet), last, n + 1),
        "xl/_rels/workbook.xml.rels":
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>',
        "xl/styles.xml": styles,
        "xl/worksheets/sheet1.xml": sheet_xml,
    }
    with zipfile.ZipFile(fs_path(dest), "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data.encode("utf-8"))

def export_results(rows, dest):
    """Escolhe o formato pela extensão de `dest` (.xlsx, .csv, .txt)."""
    ext = os.path.splitext(dest)[1].lower()
    if ext == ".txt":
        return export_txt(rows, dest)
    if ext == ".csv":
        return export_csv(rows, dest)
    if ext == ".xlsx":
        return export_xlsx(rows, dest)
    raise ValueError("Formato não suportado: %s (use .xlsx, .csv ou .txt)" % ext)

SPACE_EXPORT_HEADER = (
    "Pasta", "Tamanho (bytes)", "Tamanho", "% do total",
    "Arquivos", "Na própria pasta (bytes)", "Caminho completo",
)

def _space_export_rows(rows):
    for r in rows:
        name = r.get("name") or os.path.basename(r.get("path", "")) or r.get("path", "")
        ts = int(r.get("total_size", 0) or 0)
        pct = float(r.get("pct", 0.0) or 0.0)
        tf = int(r.get("total_files", 0) or 0)
        ds = int(r.get("direct_size", 0) or 0)
        path = r.get("path", "")
        yield name, ts, pct, tf, ds, path

def export_space_csv(rows, dest):
    """CSV (UTF-8 com BOM, `;`) do resumo de espaço por pasta."""
    import csv
    n = 0
    with open(fs_path(dest), "w", encoding="utf-8-sig", errors="replace", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(SPACE_EXPORT_HEADER)
        for name, ts, pct, tf, ds, path in _space_export_rows(rows):
            w.writerow([name, ts, fsize(ts), "%.1f%%" % pct, tf, ds, path])
            n += 1
    return n

def export_space_txt(rows, dest):
    """Texto UTF-8 com resumo de espaço por pasta (uma pasta por linha)."""
    n = 0
    with open(fs_path(dest), "w", encoding="utf-8", errors="replace", newline="\n") as f:
        for _name, ts, pct, tf, _ds, path in _space_export_rows(rows):
            f.write("%12s  %5.1f%%  %8d arq.  %s\n" % (fsize(ts), pct, tf, path))
            n += 1
    return n

def export_space_xlsx(rows, dest, sheet="Espaco"):
    """Planilha .xlsx com espaço ocupado por pasta, % e contagem de arquivos."""
    widths = [len(h) for h in SPACE_EXPORT_HEADER]
    out = []
    n = 0
    for name, ts, pct, tf, ds, path in _space_export_rows(rows):
        n += 1
        r = n + 1
        cells = []

        def s(col, v):
            widths[col] = max(widths[col], min(len(v), 80))
            cells.append('<c r="%s%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                         % (_xlsx_col(col), r, _xml(v)))
        s(0, name)
        cells.append('<c r="B%d" s="2"><v>%d</v></c>' % (r, ts))
        s(2, fsize(ts))
        cells.append('<c r="D%d" s="4"><v>%.2f</v></c>' % (r, pct))
        cells.append('<c r="E%d" s="2"><v>%d</v></c>' % (r, tf))
        cells.append('<c r="F%d" s="2"><v>%d</v></c>' % (r, ds))
        s(6, path)
        out.append('<row r="%d">%s</row>' % (r, "".join(cells)))
    _write_xlsx_package(dest, sheet, SPACE_EXPORT_HEADER, out, widths)
    return n

def export_space_results(rows, dest):
    """Exporta o resumo de espaço por pasta (.xlsx, .csv ou .txt)."""
    ext = os.path.splitext(dest)[1].lower()
    if ext == ".txt":
        return export_space_txt(rows, dest)
    if ext == ".csv":
        return export_space_csv(rows, dest)
    if ext == ".xlsx":
        return export_space_xlsx(rows, dest)
    raise ValueError("Formato não suportado: %s (use .xlsx, .csv ou .txt)" % ext)

def open_with_default_app(path):
    """Abre o arquivo no programa padrão do sistema (Excel, LibreOffice, editor)."""
    if IS_WIN:
        os.startfile(path)
    else:
        import subprocess
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])

def open_folder(path):
    """Abre uma pasta no gerenciador de arquivos do sistema."""
    p = os.path.normpath(path)
    if IS_WIN:
        os.startfile(p)
    else:
        import subprocess
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", p])

def reveal_in_folder(path):
    """Abre a pasta pai destacando o arquivo quando o sistema suporta."""
    p = os.path.normpath(path)
    import subprocess
    if IS_WIN:
        subprocess.Popen(["explorer", "/select," + p])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", p])
    else:
        subprocess.Popen(["xdg-open", os.path.dirname(p) or "."])

# ===========================================================================
# Interface (tkinter)
# ===========================================================================
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    import tkinter.font as tkFont
except ImportError:   # permite importar o núcleo (testes) sem Tk
    tk = None

class App(object):
    COLS = ("name", "ext", "size", "folder", "modified")
    CLBLS = {"name": "Nome", "ext": "Ext.", "size": "Tamanho",
             "folder": "Pasta de Origem", "modified": "Modificado"}
    CWIDTHS = {"name": 240, "ext": 65, "size": 90, "folder": 330, "modified": 130}

    BG, PNL, ACC = "#2B2B2B", "#3C3F41", "#4A90D9"
    TXT, SUB = "#EBEBEB", "#AAAAAA"
    OK, ERR, WARN = "#5CB85C", "#D9534F", "#F0AD4E"
    EBGC = "#45494A"
    RODD, REVEN = "#313335", "#3C3F41"
    SEL = "#214283"

    def __init__(self, root, index=None):
        self.root = root
        self._index = index
        self._fonts()
        self._styles()
        self._win()
        self._build()
        self._sthread = None
        self._sq = None
        self._stop_s = threading.Event()
        self._running = False
        self._cq = None
        self._stop_c = threading.Event()
        self._copying = False
        self._rdata = {}      # iid -> metadados
        self._iid_by_key = {} # caminho normalizado -> iid (para remover linhas)
        self._rcount = 0      # contador O(1)
        self._rbytes = 0      # soma de bytes dos resultados (tamanho conhecido)
        self._nsel = 0
        self._sbytes = 0      # soma de bytes dos selecionados
        self._sroot = ""
        self._srev = False
        self._scol = None
        self._space_win = None
        self._poll_s()
        self._poll_c()

    # -- Configuração -----------------------------------------------------
    def _win(self):
        self.root.title("%s  v%s" % (APP_NAME, __version__))
        try:
            self._icon = tk.PhotoImage(data="".join(ICON_PNG_B64))
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass   # Tk sem suporte a PNG (muito antigo): fica o ícone padrão
        self.root.geometry("1100x700")
        self.root.minsize(900, 560)
        self.root.configure(bg=self.BG)

    def _fonts(self):
        fams = set(tkFont.families(self.root))
        fam = next((f for f in ("Segoe UI", "Ubuntu", "Cantarell", "Noto Sans",
                                "DejaVu Sans", "Liberation Sans") if f in fams),
                   tkFont.nametofont("TkDefaultFont").actual("family"))
        self.fn = tkFont.Font(family=fam, size=9)
        self.fb = tkFont.Font(family=fam, size=9, weight="bold")
        self.ft = tkFont.Font(family=fam, size=10, weight="bold")
        self.fh = tkFont.Font(family=fam, size=13, weight="bold")
        self.fs = tkFont.Font(family=fam, size=8)

    def _styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("Dark.TFrame", background=self.BG)
        s.configure("Panel.TFrame", background=self.PNL)

        def lbl(n, bg, fg, f=None):
            s.configure(n, background=bg, foreground=fg, font=f or self.fn)
        lbl("Dark.TLabel", self.BG, self.TXT)
        lbl("Panel.TLabel", self.PNL, self.TXT)
        lbl("Sub.TLabel", self.PNL, self.SUB)
        lbl("Title.TLabel", self.PNL, self.ACC, self.ft)
        lbl("Head.TLabel", self.PNL, self.ACC, self.fh)
        lbl("Status.TLabel", self.BG, self.SUB, self.fs)
        lbl("Warn.TLabel", self.BG, self.WARN, self.fs)
        lbl("Counter.TLabel", self.PNL, self.WARN, self.fb)

        s.configure("Dark.TEntry", fieldbackground=self.EBGC,
                    foreground=self.TXT, insertcolor=self.TXT)
        for n, bg, ab in [("Primary", self.ACC, "#357ABD"), ("Danger", self.ERR, "#B52B27"),
                          ("Success", self.OK, "#3E8E41"), ("Secondary", "#555", "#666")]:
            s.configure(n + ".TButton", background=bg, foreground="#FFF",
                        font=self.fb, padding=(8, 4))
            s.map(n + ".TButton", background=[("active", ab), ("disabled", "#555")],
                  foreground=[("disabled", "#888")])
        s.configure("Accent.Horizontal.TProgressbar", troughcolor=self.EBGC,
                    background=self.ACC, thickness=14)
        s.configure("Results.Treeview", background=self.REVEN, foreground=self.TXT,
                    fieldbackground=self.REVEN, rowheight=22, font=self.fn)
        s.configure("Results.Treeview.Heading", background=self.PNL, foreground=self.ACC,
                    font=self.fb, relief="flat")
        s.map("Results.Treeview", background=[("selected", self.SEL)],
              foreground=[("selected", "#FFF")])
        for n in ("Dark.Vertical.TScrollbar", "Dark.Horizontal.TScrollbar"):
            s.configure(n, background=self.PNL, troughcolor=self.BG, arrowcolor=self.TXT)
        for n in ("Dark.TCheckbutton", "Dark.TRadiobutton"):
            s.configure(n, background=self.PNL, foreground=self.TXT, font=self.fn)
            s.map(n, background=[("active", self.PNL)])
        s.configure("TSeparator", background="#555555")

    # -- Construção -------------------------------------------------------
    def _build(self):
        self._hdr()
        ttk.Separator(self.root, orient="horizontal").pack(fill="x")
        self._statusbar()
        pane = ttk.PanedWindow(self.root, orient="vertical")
        pane.pack(fill="both", expand=True)
        tp = ttk.Frame(pane, style="Panel.TFrame"); pane.add(tp, weight=0)
        mp = ttk.Frame(pane, style="Dark.TFrame");  pane.add(mp, weight=1)
        bp = ttk.Frame(pane, style="Panel.TFrame"); pane.add(bp, weight=0)
        self._filter(tp)
        self._results(mp)
        self._copy_panel(bp)

    def _hdr(self):
        h = ttk.Frame(self.root, style="Panel.TFrame")
        h.pack(fill="x")
        ttk.Label(h, text="  " + APP_NAME, style="Head.TLabel").pack(side="left", padx=(12, 4), pady=8)
        ttk.Label(h, text="·  " + APP_TAGLINE, style="Sub.TLabel").pack(side="left", pady=8)
        ttk.Label(h, text="v%s  |  Python %s  |  %s" % (
                      __version__, platform.python_version(), platform.system()),
                  style="Sub.TLabel").pack(side="right", padx=12, pady=8)

    def _filter(self, p):
        p.columnconfigure(1, weight=1)
        L = {"style": "Panel.TLabel", "anchor": "e"}
        E = {"style": "Dark.TEntry"}

        def row(r, lbl, var, hint=""):
            ttk.Label(p, text=lbl, **L).grid(row=r, column=0, padx=(12, 4), pady=3, sticky="e")
            ttk.Entry(p, textvariable=var, **E).grid(row=r, column=1, padx=(0, 4), pady=3, sticky="ew")
            if hint:
                ttk.Label(p, text=hint, style="Sub.TLabel").grid(
                    row=r, column=2, padx=(0, 12), pady=3, sticky="w")

        self.v_root = tk.StringVar()
        self.v_pat = tk.StringVar(value="*")
        self.v_ext = tk.StringVar()
        self.v_size = tk.StringVar()
        self.v_excl = tk.StringVar()
        self.v_mode = tk.StringVar(value="fast")

        ttk.Label(p, text="Pasta Raiz:", **L).grid(row=0, column=0, padx=(12, 4), pady=(10, 3), sticky="e")
        e_root = ttk.Entry(p, textvariable=self.v_root, **E)
        e_root.grid(row=0, column=1, padx=(0, 4), pady=(10, 3), sticky="ew")
        ttk.Button(p, text="Procurar...", style="Secondary.TButton",
                   command=self._browse_root).grid(row=0, column=2, padx=(0, 12), pady=(10, 3), sticky="w")

        row(1, "Padrão:", self.v_pat, "contém texto (ex: IMAGENS_) ou curingas (*.shp, IMG_*)")
        row(2, "Extensões:", self.v_ext, "ex: .shp .tif .pdf  (vazio = todas)")
        row(3, "Tamanho:", self.v_size, "ex: > 100 MB, < 10 KB, 10MB..500MB  (vazio = todos)")
        row(4, "Ignorar pastas:", self.v_excl, "ex: _backup, node_modules, .git  (separar por vírgula)")

        mf = ttk.Frame(p, style="Panel.TFrame")
        mf.grid(row=5, column=0, columnspan=3, padx=12, pady=(4, 2), sticky="w")
        ttk.Label(mf, text="Modo de busca:", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        ttk.Radiobutton(mf, text="Rápida (paralela, se adapta ao servidor) — recomendado",
                        variable=self.v_mode, value="fast",
                        style="Dark.TRadiobutton").pack(side="left", padx=(0, 16))
        ttk.Radiobutton(mf, text="Sequencial (1 pasta por vez, com tamanho e data)",
                        variable=self.v_mode, value="full",
                        style="Dark.TRadiobutton").pack(side="left")

        xf = ttk.Frame(p, style="Panel.TFrame")
        xf.grid(row=6, column=0, columnspan=3, padx=12, pady=(2, 2), sticky="w")
        self.v_index = tk.BooleanVar(value=self._index is not None)
        self.v_refresh = tk.BooleanVar(value=False)
        ttk.Label(xf, text="Índice local:", style="Panel.TLabel").pack(side="left", padx=(0, 10))
        ttk.Checkbutton(xf, text="Usar (buscas repetidas em segundos)", variable=self.v_index,
                        style="Dark.TCheckbutton",
                        state="normal" if self._index is not None else "disabled"
                        ).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(xf, text="Verificar alterações no servidor", variable=self.v_refresh,
                        style="Dark.TCheckbutton").pack(side="left", padx=(0, 16))
        self.v_retry_prob = tk.BooleanVar(value=False)
        ttk.Checkbutton(xf, text="Tentar de novo as pastas problemáticas agora", variable=self.v_retry_prob,
                        style="Dark.TCheckbutton").pack(side="left", padx=(0, 16))
        ttk.Button(xf, text="Apagar índice", style="Secondary.TButton",
                   command=self._clear_index).pack(side="left")

        f = ttk.Frame(p, style="Panel.TFrame")
        f.grid(row=7, column=0, columnspan=3, padx=12, pady=(4, 10), sticky="w")
        self.v_case = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Diferenciar maiúsculas/minúsculas", variable=self.v_case,
                        style="Dark.TCheckbutton").pack(side="left", padx=(0, 20))
        self.b_start = ttk.Button(f, text="Iniciar busca", style="Primary.TButton", command=self._start)
        self.b_start.pack(side="left", padx=4)
        self.b_stop = ttk.Button(f, text="Parar", style="Danger.TButton",
                                 command=self._stop, state="disabled")
        self.b_stop.pack(side="left", padx=4)
        self.prog_s = ttk.Progressbar(f, mode="indeterminate", length=120,
                                      style="Accent.Horizontal.TProgressbar")
        self.prog_s.pack(side="left", padx=(12, 0))
        self.root.bind("<Return>", lambda _e: self._start())
        e_root.focus_set()

    def _results(self, p):
        p.rowconfigure(1, weight=1)
        p.columnconfigure(0, weight=1)
        tb = ttk.Frame(p, style="Panel.TFrame")
        tb.grid(row=0, column=0, sticky="ew")
        ttk.Label(tb, text="  Resultados:", style="Title.TLabel").pack(side="left", padx=4, pady=5)
        self.lbl_cnt = ttk.Label(tb, text="0 encontrados  |  0 selecionados", style="Counter.TLabel")
        self.lbl_cnt.pack(side="left", padx=(8, 0), pady=5)
        self.b_export = ttk.Button(tb, text="Exportar...", style="Primary.TButton", command=self._export)
        self.b_export.pack(side="right", padx=(3, 8), pady=5)
        self.b_space = ttk.Button(tb, text="Espaço por pasta...", style="Secondary.TButton",
                                  command=self._open_space)
        self.b_space.pack(side="right", padx=3, pady=5)
        for t, c in [("Inverter", self._invert),
                     ("Desmarcar todos", self._desel),
                     ("Selecionar todos", self._sel_all)]:
            ttk.Button(tb, text=t, style="Secondary.TButton", command=c).pack(side="right", padx=3, pady=5)

        tf = ttk.Frame(p, style="Dark.TFrame")
        tf.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tf, columns=self.COLS, show="headings",
                                 selectmode="extended", style="Results.Treeview")
        for c in self.COLS:
            self.tree.heading(c, text=self.CLBLS[c], command=lambda col=c: self._sort(col))
            self.tree.column(c, width=self.CWIDTHS[c],
                             anchor="w" if c in ("name", "folder") else "center",
                             stretch=(c == "folder"))
        self.tree.tag_configure("o", background=self.RODD)
        self.tree.tag_configure("e", background=self.REVEN)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview,
                            style="Dark.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview,
                            style="Dark.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_sel)
        self.tree.bind("<Double-1>", self._on_double_click)

    def _copy_panel(self, p):
        p.columnconfigure(1, weight=1)
        ttk.Label(p, text="  Ações de cópia", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, padx=12, pady=(8, 4), sticky="w")
        ttk.Label(p, text="Destino:", style="Panel.TLabel", anchor="e").grid(
            row=1, column=0, padx=(12, 4), pady=3, sticky="e")
        self.v_dest = tk.StringVar()
        ttk.Entry(p, textvariable=self.v_dest, style="Dark.TEntry").grid(
            row=1, column=1, padx=(0, 4), pady=3, sticky="ew")
        ttk.Button(p, text="Procurar...", style="Secondary.TButton",
                   command=self._browse_dest).grid(row=1, column=2, padx=(0, 12), pady=3, sticky="w")
        sf = ttk.Frame(p, style="Panel.TFrame")
        sf.grid(row=2, column=0, columnspan=3, padx=12, pady=3, sticky="w")
        ttk.Label(sf, text="Estrutura:", style="Panel.TLabel").pack(side="left", padx=(0, 8))
        self.v_struct = tk.StringVar(value="flat")
        ttk.Radiobutton(sf, text="Plana", variable=self.v_struct, value="flat",
                        style="Dark.TRadiobutton").pack(side="left", padx=4)
        ttk.Radiobutton(sf, text="Manter estrutura original", variable=self.v_struct,
                        value="keep", style="Dark.TRadiobutton").pack(side="left", padx=4)
        cf = ttk.Frame(p, style="Panel.TFrame")
        cf.grid(row=3, column=0, columnspan=3, padx=12, pady=(4, 6), sticky="ew")
        cf.columnconfigure(2, weight=1)
        self.b_copy = ttk.Button(cf, text="Copiar selecionados", style="Success.TButton",
                                 command=self._do_copy)
        self.b_copy.grid(row=0, column=0, padx=(0, 6), pady=2, sticky="w")
        self.b_ccancel = ttk.Button(cf, text="Cancelar", style="Danger.TButton",
                                    command=self._ccancel, state="disabled")
        self.b_ccancel.grid(row=0, column=1, padx=6, pady=2, sticky="w")
        self.prog_c = ttk.Progressbar(cf, mode="determinate", length=300,
                                      style="Accent.Horizontal.TProgressbar")
        self.prog_c.grid(row=0, column=2, padx=(12, 6), pady=2, sticky="ew")
        self.lbl_cs = ttk.Label(cf, text="Nenhuma cópia em andamento.", style="Sub.TLabel")
        self.lbl_cs.grid(row=1, column=0, columnspan=3, padx=0, pady=(2, 4), sticky="w")

    def _statusbar(self):
        b = ttk.Frame(self.root, style="Dark.TFrame")
        b.pack(fill="x", side="bottom")
        ttk.Separator(self.root, orient="horizontal").pack(fill="x", side="bottom")
        # Linha 1: o que a busca está fazendo. Linha 2: avisos (pastas lentas,
        # adiadas, falhas) — clicável quando há pastas que não puderam ser lidas.
        self.lbl_st = ttk.Label(b, text="  Pronto.  Log: " + LOG_PATH, style="Status.TLabel")
        self.lbl_st.pack(side="top", anchor="w", padx=4, pady=(3, 0))
        self.lbl_warn = ttk.Label(b, text="", style="Warn.TLabel", cursor="")
        self.lbl_warn.pack(side="top", anchor="w", padx=4, pady=(0, 3))
        self.lbl_warn.bind("<Button-1>", lambda _e: self._show_failures())
        self._failures = []
        self._skipped = []

    def _st(self, txt, color=None):
        self.lbl_st.config(text="  " + txt, foreground=color or self.SUB)

    def _warn(self, txt, clickable=False):
        self.lbl_warn.config(text=("  ⚠ " + txt) if txt else "",
                             cursor="hand2" if clickable else "")

    def _show_failures(self):
        failed, skipped = self._failures, self._skipped
        if not failed and not skipped:
            return
        lines = []
        if failed:
            lines.append("%d pasta(s) não puderam ser lidas:" % len(failed))
            for p, err in failed[:15]:
                lines.append("- %s\n    %s" % (p, err[:150]))
            if len(failed) > 15:
                lines.append("...e mais %d (lista completa no log)." % (len(failed) - 15))
            lines.append("")
        if skipped:
            lines.append("%d pasta(s) problemática(s) puladas — foram tentadas há menos de %d h "
                         "e o servidor não respondeu:" % (len(skipped), PROBLEM_RETRY_H))
            for p, fails, _err in skipped[:15]:
                lines.append("- %s  (%d falha(s))" % (p, fails))
            if len(skipped) > 15:
                lines.append("...e mais %d." % (len(skipped) - 15))
            lines.append("\nElas são tentadas de novo automaticamente a cada %d h (ou já, marcando "
                         "\"Tentar de novo as pastas problemáticas agora\"), sempre por uma conexão "
                         "separada, sem atrasar a busca. Quando voltarem a funcionar, saem da lista."
                         % PROBLEM_RETRY_H)
            lines.append("")
        lines.append("Diagnóstico medido no servidor: nessas pastas o servidor não responde nem para "
                     "ABRIR a pasta (timeout, erro 121), por nenhuma conexão. É um problema do lado do "
                     "servidor (bloqueio de arquivo, antivírus, disco ou sistema de arquivos): encaminhe "
                     "a lista à TI. O restante da busca não é afetado.\n\nLog: " + LOG_PATH)
        messagebox.showwarning("Pastas não lidas", "\n".join(lines), parent=self.root)

    def _update_counter(self):
        if self._rbytes > 0:
            stxt = ("%d selecionados (%s)" % (self._nsel, fsize(self._sbytes))
                    if self._sbytes > 0 else "%d selecionados" % self._nsel)
            self.lbl_cnt.config(text="%d encontrados (%s)  |  %s" % (
                self._rcount, fsize(self._rbytes), stxt))
        else:
            self.lbl_cnt.config(text="%d encontrados  |  %d selecionados" % (self._rcount, self._nsel))

    # -- Busca ------------------------------------------------------------
    def _browse_root(self):
        d = filedialog.askdirectory(parent=self.root, title="Pasta Raiz", mustexist=True)
        if d:
            self.v_root.set(os.path.normpath(d))

    def _start(self):
        """Só valida strings e agenda _do_start: nenhum I/O aqui."""
        rd = self.v_root.get().strip()
        if not rd:
            messagebox.showwarning("Pasta não informada", "Informe uma Pasta Raiz de busca.",
                                   parent=self.root)
            return
        try:
            min_sz, max_sz = parse_size_filter(self.v_size.get())
        except ValueError as e:
            messagebox.showwarning("Tamanho inválido", str(e), parent=self.root)
            return
        if self._running:
            # Nova busca durante uma busca (ex.: trocar o padrão): encerra a
            # atual e começa já. O que ela leu foi para o índice e é reaproveitado.
            dlog("=== UI: NOVA BUSCA SUBSTITUI A ATUAL ===")
            self._stop_s.set()
        self._running = True
        self.b_stop.config(state="normal")
        self.prog_s.start(12)
        self._st("Iniciando busca...", self.WARN)
        params = {
            "root": rd,
            "pattern": clean_pattern(self.v_pat.get()) or "*",
            "exts": parse_exts(self.v_ext.get()),
            "min_size": min_sz,
            "max_size": max_sz,
            "exclude_dirs": parse_excludes(self.v_excl.get()),
            "case": self.v_case.get(),
            "fast_mode": self.v_mode.get() == "fast",
            "index": self.v_index.get() and self._index is not None,
            "refresh": self.v_refresh.get(),
            "retry_problems": self.v_retry_prob.get(),
        }
        # Cede o event loop para os botões serem redesenhados antes do resto.
        self.root.after(20, self._do_start, params)

    def _do_start(self, params):
        if not self._running:
            return
        dlog("=== UI: NOVA BUSCA === %s" % params)
        try:
            tw = self.tree._w
            self.tree.tk.eval("catch {%s delete [%s children {}]}" % (tw, tw))
        except tk.TclError:
            pass
        self._rdata = {}
        self._iid_by_key = {}
        self._rcount = 0
        self._rbytes = 0
        self._nsel = 0
        self._sbytes = 0
        self._failures = []
        self._skipped = []
        self._warn("")
        self._update_counter()
        self._sroot = os.path.normpath(params["root"])
        # Dois cliques rápidos em "Iniciar busca" agendam dois _do_start: o
        # segundo precisa parar a busca criada pelo primeiro (senão ela fica
        # órfã, rodando escondida e carregando o servidor).
        if self._sthread is not None and self._sthread.is_alive():
            self._sthread.stop.set()
            dlog("UI: busca anterior encerrada antes de iniciar a nova")
        self._stop_s = threading.Event()
        self._sq = queue.Queue(maxsize=2000)
        self._sthread = SearchThread(params["root"], params["pattern"], params["exts"],
                                     params["case"], self._sq, self._stop_s,
                                     fast_mode=params["fast_mode"],
                                     index=self._index if params["index"] else None,
                                     refresh=params["refresh"],
                                     retry_problems=params["retry_problems"],
                                     min_size=params.get("min_size"),
                                     max_size=params.get("max_size"),
                                     exclude_dirs=params.get("exclude_dirs"))
        self._sthread.start()
        self._t0 = time.time()
        self._st("Buscando em: %s" % params["root"], self.WARN)

    def _clear_index(self):
        if self._index is None:
            return
        if self._running:
            messagebox.showinfo("Aguarde", "Pare a busca antes de apagar o índice.", parent=self.root)
            return
        if not messagebox.askyesno("Apagar índice",
                                   "Apagar o índice local? As próximas buscas voltarão a ler "
                                   "tudo do servidor.", parent=self.root):
            return
        self._st("Apagando índice...", self.WARN)
        idx = self._index
        done_q = queue.Queue()

        def work():
            ok = idx.clear()
            dlog("=== ÍNDICE APAGADO === %s" % ("ok" if ok else "tempo esgotado"))
            done_q.put(ok)

        def poll():
            # Avisa só quando a limpeza TERMINAR (antes era um tempo fixo de 1,5 s).
            try:
                ok = done_q.get_nowait()
            except queue.Empty:
                self.root.after(200, poll)
                return
            if not self._running:
                if ok:
                    self._st("Índice apagado.", self.OK)
                else:
                    self._st("O índice não pôde ser apagado (ver log).", self.ERR)
        threading.Thread(target=work, daemon=True).start()
        self.root.after(200, poll)

    def _stop(self):
        """Só sinaliza: _put() da busca verifica o stop a cada 50 ms."""
        dlog("=== UI: PARAR ===")
        self._stop_s.set()
        self.b_stop.config(state="disabled")
        self._st("Parando busca... aguarde (uma pasta lenta pode levar até 1 min).", self.WARN)

    def _poll_s(self):
        # Um erro inesperado aqui não pode interromper o ciclo: sem o after()
        # a interface ficaria "buscando" para sempre.
        try:
            self._poll_s_once()
        except Exception:
            dlog("[ERRO] interface (busca)\n%s" % traceback.format_exc())
        finally:
            self.root.after(100, self._poll_s)

    def _insert_row(self, values, tag):
        try:
            return self.tree.insert("", "end", values=values, tags=(tag,))
        except tk.TclError:
            # Nome com caractere que o Tk não exibe (Samba antigo): mostra com
            # substituição; o caminho real continua guardado para copiar/exportar.
            safe = tuple(_SURROGATE_RE.sub("\ufffd", str(v)) for v in values)
            return self.tree.insert("", "end", values=safe, tags=(tag,))

    def _poll_s_once(self):
        if self._running and self._sq is not None:
            for _ in range(200):   # até 200 itens por ciclo de 100 ms
                try:
                    item = self._sq.get_nowait()
                except queue.Empty:
                    break
                if item is SearchThread.DONE:
                    self._done_s()
                    break
                tag = item[0]
                if tag == "__ERR__":
                    dlog("UI: erro recebido: %s" % item[1])
                    self._st("Erro: " + item[1], self.ERR)
                    continue
                if tag == "__STATUS__":
                    if not self._stop_s.is_set():
                        self._st(item[1], self.WARN)
                        self._warn(item[2] if len(item) > 2 else "")
                    continue
                if tag == "__REMOVE__":
                    self._remove_rows([self._iid_by_key.get(path_key(item[1]))])
                    continue
                if tag == "__REMOVE_DIR__":
                    k = path_key(item[1])
                    self._remove_rows([i for i, r in self._rdata.items()
                                       if is_under(path_key(r["dir"]), k)])
                    continue
                if self._rcount >= MAX_RESULTS:
                    if not self._stop_s.is_set():
                        dlog("Limite de %d resultados atingido" % MAX_RESULTS)
                        self._stop()
                    continue
                path, name, ext, sz, dp, mt = item
                iid = self._insert_row((name, ext, fsize(sz), dp, fdate(mt)),
                                       "o" if self._rcount % 2 == 0 else "e")
                self._rcount += 1
                if sz is not None and sz > 0:
                    self._rbytes += sz
                self._rdata[iid] = {"path": path, "dir": dp, "size": sz, "mtime": mt}
                self._iid_by_key[path_key(path)] = iid

            if self._running:
                self._update_counter()
                # Watchdog: só finaliza com a fila VAZIA (não descarta resultados).
                if (self._sthread is not None and not self._sthread.is_alive()
                        and self._sq is not None and self._sq.empty()):
                    dlog("Watchdog: busca terminou sem DONE")
                    self._done_s()

    def _done_s(self):
        self._running = False
        self._sq = None
        el = time.time() - getattr(self, "_t0", time.time())
        stopped = self._stop_s.is_set()
        dlog("=== UI: BUSCA FINALIZADA: %d resultados em %.1fs ===" % (self._rcount, el))
        self.b_start.config(state="normal")
        self.b_stop.config(state="disabled")
        self.prog_s.stop()
        extra = ""
        if self._sthread is not None and self._sthread.summary:
            extra = "  — origem: " + self._sthread.summary
        if self._rcount >= MAX_RESULTS:
            extra = "  — LIMITE DE %d ATINGIDO, refine o padrão" % MAX_RESULTS
        self._st("Busca %s: %d arquivo(s) em %.1fs%s" % (
            "parada" if stopped else "concluída", self._rcount, el, extra),
            self.WARN if stopped else self.OK)
        self._failures = list(self._sthread.failed) if self._sthread is not None else []
        self._skipped = list(self._sthread.skipped_problems) if self._sthread is not None else []
        if self._failures or self._skipped:
            parts = []
            if self._failures:
                parts.append("%d pasta(s) não puderam ser lidas" % len(self._failures))
            if self._skipped:
                parts.append("%d pasta(s) problemática(s) puladas" % len(self._skipped))
            self._warn(" e ".join(parts) + " — clique aqui para ver a lista.", clickable=True)
        elif stopped:
            self._warn("Busca parada: o que já foi lido ficou no índice e será aproveitado.")
        else:
            self._warn("")
        self._update_counter()

    def _remove_rows(self, iids):
        """Tira da lista arquivos/pastas que sumiram do servidor (modo verificar)."""
        for iid in iids:
            if not iid or iid not in self._rdata:
                continue
            r = self._rdata.pop(iid)
            sz = r.get("size")
            if sz is not None and sz > 0:
                self._rbytes = max(0, self._rbytes - sz)
            self._iid_by_key.pop(path_key(r["path"]), None)
            try:
                self.tree.delete(iid)
            except tk.TclError:
                pass
            self._rcount -= 1

    # -- Seleção e Abertura -----------------------------------------------
    def _on_sel(self, _=None):
        sel = self.tree.selection()
        self._nsel = len(sel)
        self._sbytes = sum((self._rdata[i].get("size") or 0) for i in sel
                           if i in self._rdata and (self._rdata[i].get("size") or 0) > 0)
        self._update_counter()

    def _on_double_click(self, event=None):
        iid = self.tree.identify_row(event.y) if event is not None else None
        if not iid:
            sel = self.tree.selection()
            iid = sel[0] if sel else None
        if not iid or iid not in self._rdata:
            return
        path = self._rdata[iid]["path"]
        threading.Thread(target=lambda: self._safe_reveal(path), daemon=True).start()

    def _safe_reveal(self, path):
        try:
            reveal_in_folder(path)
        except Exception as e:
            dlog("[AVISO] não foi possível mostrar na pasta %s: %s" % (path, e))

    def _open_space(self):
        rd = self.v_root.get().strip() or self._sroot
        if self._space_win is not None:
            try:
                if self._space_win.win.winfo_exists():
                    self._space_win.win.lift()
                    self._space_win.win.focus_force()
                    if rd:
                        self._space_win.load_dir(rd)
                    return
            except tk.TclError:
                pass
        self._space_win = SpaceDialog(self, rd)

    # -- Exportação ----------------------------------------------------------
    def _export(self):
        if not self._rcount:
            messagebox.showinfo("Exportar", "Não há resultados para exportar.", parent=self.root)
            return
        order = self.tree.get_children()          # respeita a ordenação da lista
        sel = set(self.tree.selection())
        iids = order
        if sel and len(sel) < len(order):
            ans = messagebox.askyesnocancel(
                "Exportar",
                "Exportar só os %d resultado(s) selecionado(s)?\n\n"
                "Sim = só os selecionados   ·   Não = todos os %d" % (len(sel), len(order)),
                parent=self.root)
            if ans is None:
                return
            if ans:
                iids = [i for i in order if i in sel]
        rows = [self._rdata[i] for i in iids if i in self._rdata]
        dest = filedialog.asksaveasfilename(
            parent=self.root, title="Exportar resultados",
            initialfile="resultados_%s" % time.strftime("%Y-%m-%d_%H%M"),
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx"),
                       ("CSV (Excel, LibreOffice, QGIS)", "*.csv"),
                       ("Texto: um caminho por linha", "*.txt")])
        if not dest:
            return
        dest = os.path.normpath(dest)
        if os.path.splitext(dest)[1].lower() not in EXPORT_FORMATS:
            dest += ".xlsx"
        self.b_export.config(state="disabled")
        self._st("Exportando %d resultado(s) para %s..." % (len(rows), dest), self.WARN)
        done_q = queue.Queue()

        def work():
            # Fora da GUI: o destino pode ser uma pasta de rede lenta. O resultado
            # volta pela fila (o tkinter não aceita chamadas de outra thread).
            try:
                n = export_results(rows, dest)
                dlog("=== EXPORTAÇÃO: %d linha(s) -> %s ===" % (n, dest))
                done_q.put((n, None))
            except Exception as e:
                dlog("[ERRO] exportação %s: %s" % (dest, e))
                done_q.put((0, str(e)))

        def poll():
            try:
                n, err = done_q.get_nowait()
            except queue.Empty:
                self.root.after(100, poll)
                return
            self._export_done(dest, n, err)
        threading.Thread(target=work, daemon=True).start()
        self.root.after(100, poll)

    def _export_done(self, dest, n, err):
        self.b_export.config(state="normal")
        if err:
            self._st("Falha ao exportar: " + err, self.ERR)
            messagebox.showerror("Exportar", "Não foi possível exportar:\n\n%s" % err, parent=self.root)
            return
        self._st("Exportado(s) %d resultado(s) para %s" % (n, dest), self.OK)
        if messagebox.askyesno("Exportado",
                               "%d resultado(s) exportado(s) para:\n%s\n\nAbrir o arquivo agora?" % (n, dest),
                               parent=self.root):
            threading.Thread(target=lambda: self._safe_open(dest), daemon=True).start()

    def _safe_open(self, path):
        try:
            open_with_default_app(path)
        except Exception as e:
            dlog("[AVISO] não foi possível abrir %s: %s" % (path, e))

    def _sel_all(self):
        self.tree.selection_set(self.tree.get_children())
        self._on_sel()

    def _desel(self):
        self.tree.selection_remove(self.tree.selection())
        self._on_sel()

    def _invert(self):
        sel = set(self.tree.selection())
        self.tree.selection_set([i for i in self.tree.get_children() if i not in sel])
        self._on_sel()

    # -- Ordenação --------------------------------------------------------
    def _sort(self, col):
        self._srev = (not self._srev) if self._scol == col else False
        self._scol = col
        kids = self.tree.get_children()
        if col in ("size", "modified"):
            key = "size" if col == "size" else "mtime"
            items = sorted(kids, key=lambda i: self._rdata.get(i, {}).get(key, -1),
                           reverse=self._srev)
        else:
            vals = {i: self.tree.set(i, col).lower() for i in kids}
            items = sorted(kids, key=vals.get, reverse=self._srev)
        for n, iid in enumerate(items):
            self.tree.move(iid, "", n)
            self.tree.item(iid, tags=("o" if n % 2 == 0 else "e",))
        arr = " ▲" if not self._srev else " ▼"
        for c in self.COLS:
            self.tree.heading(c, text=self.CLBLS[c] + (arr if c == col else ""))

    # -- Cópia ------------------------------------------------------------
    def _browse_dest(self):
        d = filedialog.askdirectory(parent=self.root, title="Pasta de Destino")
        if d:
            self.v_dest.set(os.path.normpath(d))

    def _do_copy(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Nada selecionado", "Selecione arquivos na lista.", parent=self.root)
            return
        dest = self.v_dest.get().strip()
        if not dest:
            messagebox.showwarning("Destino", "Informe a Pasta de Destino.", parent=self.root)
            return
        if self._copying:
            messagebox.showinfo("Aguarde", "Cópia em andamento.", parent=self.root)
            return
        files = [self._rdata[i]["path"] for i in sel if i in self._rdata]
        self._copying = True
        self._stop_c = threading.Event()
        self._cq = queue.Queue()
        self.b_copy.config(state="disabled")
        self.b_ccancel.config(state="normal")
        self.prog_c["value"] = 0
        self.prog_c["maximum"] = max(len(files), 1)
        self.lbl_cs.config(text="Iniciando cópia de %d arquivo(s)..." % len(files), foreground=self.WARN)
        self._ct0 = time.time()
        dlog("=== UI: CÓPIA de %d arquivo(s) para %s ===" % (len(files), dest))
        CopyManager(files, os.path.normpath(dest), self.v_struct.get() == "keep",
                    self._cq, self._stop_c).start(self._sroot)

    def _ccancel(self):
        self._stop_c.set()
        self.lbl_cs.config(text="Cancelando...", foreground=self.WARN)

    def _poll_c(self):
        try:
            self._poll_c_once()
        except Exception:
            dlog("[ERRO] interface (cópia)\n%s" % traceback.format_exc())
        finally:
            self.root.after(150, self._poll_c)

    def _poll_c_once(self):
        if self._cq is not None:
            try:
                while True:
                    m = self._cq.get_nowait()
                    if m[0] == "TOTAL":
                        self.prog_c["maximum"] = max(m[1], 1)
                    elif m[0] == "PROG":
                        _, done, tot, src, ok, spd, ne = m
                        self.prog_c["value"] = done
                        pct = (done * 100.0 / tot) if tot else 0
                        t = "%d/%d (%.0f%%)  %s  [%s/s]" % (
                            done, tot, pct, os.path.basename(src), fsize(int(spd)))
                        if ne:
                            t += "  -  %d erro(s)" % ne
                        self.lbl_cs.config(text=t, foreground=self.TXT)
                    elif m[0] == "DONE":
                        self._done_c(m[1])
                        self._cq = None
                        break
            except queue.Empty:
                pass

    def _done_c(self, errs):
        self._copying = False
        el = time.time() - getattr(self, "_ct0", time.time())
        tot = int(self.prog_c["maximum"])
        done = int(self.prog_c["value"]) - len(errs)
        self.b_copy.config(state="normal")
        self.b_ccancel.config(state="disabled")
        stopped = self._stop_c.is_set()
        dlog("=== UI: CÓPIA FINALIZADA: %d ok, %d erros, %.1fs%s ===" % (
            done, len(errs), el, " (cancelada)" if stopped else ""))
        if errs and not stopped:
            lines = ["Cópia com %d erro(s):\n" % len(errs)]
            for s, m in errs[:20]:
                lines.append("- %s\n  %s" % (os.path.basename(s), m))
            if len(errs) > 20:
                lines.append("\n...e mais %d." % (len(errs) - 20))
            messagebox.showwarning("Erros na cópia", "\n".join(lines), parent=self.root)
            self.lbl_cs.config(text="%d/%d copiados em %.1fs (%d erros)" % (done, tot, el, len(errs)),
                               foreground=self.WARN)
        elif stopped:
            self.lbl_cs.config(text="Cancelado: %d arquivo(s) copiados em %.1fs" % (done, el),
                               foreground=self.WARN)
        else:
            self.lbl_cs.config(text="%d arquivo(s) copiados em %.1fs" % (done, el), foreground=self.OK)
            messagebox.showinfo("Concluído", "%d arquivo(s) copiados em %.1fs." % (done, el),
                                parent=self.root)

class SpaceDialog(object):
    """Janela de análise de espaço por pasta (usa o índice SQLite ou resultados
    atuais; permite navegar subpastas com duplo clique, mapear em background e
    exportar para .xlsx/.csv/.txt sem nunca tocar disco na thread da GUI)."""
    COLS = ("name", "size", "pct", "files", "direct", "path")
    CLBLS = {
        "name": "Pasta", "size": "Tamanho", "pct": "% do Pai",
        "files": "Arquivos", "direct": "Na própria pasta", "path": "Caminho completo",
    }
    CWIDTHS = {
        "name": 210, "size": 100, "pct": 75,
        "files": 90, "direct": 115, "path": 330,
    }

    def __init__(self, app, initial_dir=""):
        self.app = app
        self.win = tk.Toplevel(app.root)
        self.win.title("Espaço por pasta — %s" % APP_NAME)
        self.win.geometry("980x580")
        self.win.minsize(780, 420)
        self.win.configure(bg=app.BG)
        self._closed = False
        self._q = queue.Queue()
        self._scan_stop = threading.Event()
        self._scan_thread = None
        self._scanning = False
        self._cur_dir = ""
        self._rows = []          # lista de dicts exibidos
        self._rdata = {}         # iid -> dict
        self._root_total = {"total_size": 0, "total_files": 0}
        self._scol = "size"
        self._srev = True
        self._build(initial_dir)
        self.win.protocol("WM_DELETE_WINDOW", self._close)
        self._poll()
        if initial_dir:
            self.load_dir(initial_dir)

    def _build(self, initial_dir):
        a = self.app
        top = ttk.Frame(self.win, style="Panel.TFrame")
        top.pack(fill="x", padx=0, pady=0)
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Pasta:", style="Panel.TLabel").grid(
            row=0, column=0, padx=(12, 4), pady=(10, 4), sticky="e")
        self.v_dir = tk.StringVar(value=os.path.normpath(initial_dir) if initial_dir else "")
        e = ttk.Entry(top, textvariable=self.v_dir, style="Dark.TEntry")
        e.grid(row=0, column=1, padx=(0, 4), pady=(10, 4), sticky="ew")
        e.bind("<Return>", lambda _e: self.load_dir(self.v_dir.get().strip()))
        ttk.Button(top, text="Procurar...", style="Secondary.TButton",
                   command=self._browse).grid(row=0, column=2, padx=(0, 12), pady=(10, 4))

        bf = ttk.Frame(top, style="Panel.TFrame")
        bf.grid(row=1, column=0, columnspan=3, padx=12, pady=(2, 8), sticky="ew")
        self.b_up = ttk.Button(bf, text="⬆ Pasta acima", style="Secondary.TButton",
                               command=self.go_up)
        self.b_up.pack(side="left", padx=(0, 4))
        self.b_refresh = ttk.Button(bf, text="Consultar índice", style="Primary.TButton",
                                    command=lambda: self.load_dir(self.v_dir.get().strip()))
        self.b_refresh.pack(side="left", padx=4)
        self.b_scan = ttk.Button(bf, text="Mapear pasta agora", style="Success.TButton",
                                 command=self.scan_dir)
        self.b_scan.pack(side="left", padx=4)
        self.b_stop = ttk.Button(bf, text="Parar", style="Danger.TButton",
                                 command=self.stop_scan, state="disabled")
        self.b_stop.pack(side="left", padx=4)
        self.prog = ttk.Progressbar(bf, mode="indeterminate", length=110,
                                    style="Accent.Horizontal.TProgressbar")
        self.prog.pack(side="left", padx=(8, 8))

        self.b_export = ttk.Button(bf, text="Exportar...", style="Primary.TButton",
                                   command=self._export)
        self.b_export.pack(side="right", padx=(4, 0))
        ttk.Button(bf, text="Abrir no sistema", style="Secondary.TButton",
                   command=self._open_selected).pack(side="right", padx=4)
        ttk.Button(bf, text="Usar como Pasta Raiz", style="Secondary.TButton",
                   command=self._use_as_root).pack(side="right", padx=4)

        ttk.Separator(self.win, orient="horizontal").pack(fill="x")

        sf = ttk.Frame(self.win, style="Panel.TFrame")
        sf.pack(fill="x")
        self.lbl_sum = ttk.Label(
            sf, text="  Informe uma pasta para ver o espaço ocupado por cada subpasta.",
            style="Counter.TLabel")
        self.lbl_sum.pack(side="left", padx=8, pady=5)
        ttk.Label(sf, text="Duplo clique em uma subpasta para entrar nela  ",
                  style="Sub.TLabel").pack(side="right", padx=8, pady=5)

        tf = ttk.Frame(self.win, style="Dark.TFrame")
        tf.pack(fill="both", expand=True, padx=4, pady=4)
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(tf, columns=self.COLS, show="headings",
                                 selectmode="browse", style="Results.Treeview")
        for c in self.COLS:
            self.tree.heading(c, text=self.CLBLS[c], command=lambda col=c: self._sort(col))
            self.tree.column(c, width=self.CWIDTHS[c],
                             anchor="w" if c in ("name", "path") else "e" if c in ("size", "pct", "files", "direct") else "center",
                             stretch=(c == "path"))
        self.tree.tag_configure("o", background=a.RODD)
        self.tree.tag_configure("e", background=a.REVEN)
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview,
                            style="Dark.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(tf, orient="horizontal", command=self.tree.xview,
                            style="Dark.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", self._on_double_click)

        self.lbl_st = ttk.Label(self.win, text="  Pronto.", style="Status.TLabel")
        self.lbl_st.pack(fill="x", side="bottom", padx=4, pady=3)

    def _browse(self):
        d = filedialog.askdirectory(parent=self.win, title="Escolher pasta para análise de espaço",
                                    mustexist=True)
        if d:
            self.load_dir(os.path.normpath(d))

    def go_up(self):
        cur = (self._cur_dir or self.v_dir.get()).strip()
        if not cur:
            return
        norm = os.path.normpath(cur)
        parent = os.path.dirname(norm.rstrip("\\/"))
        if parent and parent != norm:
            self.load_dir(parent)

    def load_dir(self, target_dir):
        """Consulta o espaço de `target_dir` em thread separada (zero I/O na GUI)."""
        target_dir = (target_dir or "").strip()
        if not target_dir:
            return
        norm = os.path.normpath(target_dir)
        self._cur_dir = norm
        self.v_dir.set(norm)
        self.lbl_st.config(text="  Calculando espaço por pasta em %s..." % norm,
                           foreground=self.app.WARN)
        idx = self.app._index
        excl = parse_excludes(self.app.v_excl.get())
        rdata_snap = list(self.app._rdata.values())
        q = self._q

        def work():
            try:
                if idx is not None:
                    sp = idx.folder_space(norm, exclude_dirs=excl)
                    if sp and (sp["scanned_dirs"] > 0 or sp["total_files"] > 0):
                        items = folder_space_children(sp, norm)
                        q.put(("DATA", norm, items, sp, "índice local"))
                        return
                if rdata_snap:
                    sp = summarize_rows_space(rdata_snap, norm, exclude_dirs=excl)
                    if sp and (sp["scanned_dirs"] > 0 or sp["total_files"] > 0):
                        items = folder_space_children(sp, norm)
                        q.put(("DATA", norm, items, sp, "resultados da busca atual"))
                        return
                q.put(("EMPTY", norm))
            except Exception as e:
                dlog("[ERRO] espaço por pasta (%s): %s" % (norm, e))
                q.put(("ERR", str(e)))
        threading.Thread(target=work, daemon=True).start()

    def scan_dir(self):
        """Varre `v_dir` em segundo plano alimentando o índice e atualizando a tabela."""
        target_dir = (self.v_dir.get() or self._cur_dir).strip()
        if not target_dir:
            messagebox.showwarning("Pasta não informada", "Informe uma pasta para mapear.",
                                   parent=self.win)
            return
        norm = os.path.normpath(target_dir)
        self._cur_dir = norm
        self.v_dir.set(norm)
        if self._scanning:
            self._scan_stop.set()
        self._scanning = True
        self._scan_stop = threading.Event()
        self.b_scan.config(state="disabled")
        self.b_stop.config(state="normal")
        self.prog.start(12)
        self.lbl_st.config(text="  Mapeando %s..." % norm, foreground=self.app.WARN)
        idx = self.app._index
        excl = parse_excludes(self.app.v_excl.get())
        stop_ev = self._scan_stop
        q = self._q

        def runner():
            sq = queue.Queue(maxsize=2000)
            st = SearchThread(norm, "*", set(), False, sq, stop_ev,
                              fast_mode=True, index=idx, refresh=True,
                              exclude_dirs=excl)
            self._scan_thread = st
            st.start()
            mem_rows = [] if idx is None else None
            last_snap = time.time()
            while True:
                try:
                    item = sq.get(timeout=0.2)
                except queue.Empty:
                    if not st.is_alive() and sq.empty():
                        break
                    item = None
                if item is SearchThread.DONE:
                    break
                if item is not None:
                    tag = item[0]
                    if tag == "__STATUS__":
                        q.put(("SCAN_ST", item[1]))
                    elif tag not in ("__ERR__", "__REMOVE__", "__REMOVE_DIR__"):
                        if mem_rows is not None:
                            path, _name, _ext, sz, dp, mt = item
                            mem_rows.append({"path": path, "dir": dp, "size": sz, "mtime": mt})
                now = time.time()
                if now - last_snap >= 1.5:
                    last_snap = now
                    if idx is not None:
                        idx.flush()
                        sp = idx.folder_space(norm, exclude_dirs=excl)
                    else:
                        sp = summarize_rows_space(mem_rows, norm, exclude_dirs=excl)
                    items = folder_space_children(sp, norm)
                    q.put(("DATA", norm, items, sp, "mapeamento em andamento"))
            if idx is not None:
                idx.flush()
                sp = idx.folder_space(norm, exclude_dirs=excl)
            else:
                sp = summarize_rows_space(mem_rows, norm, exclude_dirs=excl)
            items = folder_space_children(sp, norm)
            q.put(("SCAN_DONE", norm, items, sp, stop_ev.is_set()))
        threading.Thread(target=runner, daemon=True).start()

    def stop_scan(self):
        self._scan_stop.set()
        self.b_stop.config(state="disabled")
        self.lbl_st.config(text="  Parando mapeamento (o que já foi lido fica salvo no índice)...",
                           foreground=self.app.WARN)

    def _populate(self, norm, items, rt, origin):
        try:
            tw = self.tree._w
            self.tree.tk.eval("catch {%s delete [%s children {}]}" % (tw, tw))
        except tk.TclError:
            pass
        self._rows = list(items)
        self._rdata = {}
        self._root_total = rt
        for n, it in enumerate(self._rows):
            iid = self.tree.insert(
                "", "end",
                values=(
                    it["name"],
                    fsize(it["total_size"]),
                    "%.1f%%" % it["pct"],
                    "%d" % it["total_files"],
                    fsize(it["direct_size"]),
                    it["path"],
                ),
                tags=("o" if n % 2 == 0 else "e",),
            )
            self._rdata[iid] = it
        self.lbl_sum.config(
            text="  Total em %s: %s em %d arquivo(s)  |  %d item(ns)"
            % (os.path.basename(norm) or norm, fsize(rt["total_size"]),
               rt["total_files"], len(self._rows)))
        if not self._scanning:
            self.lbl_st.config(
                text="  Espaço calculado (%s): %s em %d arquivo(s)."
                % (origin, fsize(rt["total_size"]), rt["total_files"]),
                foreground=self.app.OK)

    def _poll(self):
        if self._closed:
            return
        try:
            if not self.win.winfo_exists():
                self._closed = True
                return
            while True:
                try:
                    m = self._q.get_nowait()
                except queue.Empty:
                    break
                kind = m[0]
                if kind == "DATA":
                    _, norm, items, rt, origin = m
                    self._populate(norm, items, rt, origin)
                elif kind == "EMPTY":
                    _, norm = m
                    self._populate(norm, [], {"total_size": 0, "total_files": 0}, "vazio")
                    self.lbl_sum.config(
                        text="  Pasta ainda não indexada: clique em \"Mapear pasta agora\" para calcular.")
                    self.lbl_st.config(
                        text="  Nenhum dado no índice para %s. Clique em \"Mapear pasta agora\"." % norm,
                        foreground=self.app.WARN)
                elif kind == "SCAN_ST":
                    self.lbl_st.config(text="  " + m[1], foreground=self.app.WARN)
                elif kind == "SCAN_DONE":
                    _, norm, items, rt, stopped = m
                    self._scanning = False
                    self.b_scan.config(state="normal")
                    self.b_stop.config(state="disabled")
                    self.prog.stop()
                    self._populate(norm, items, rt, "mapeamento pausado" if stopped else "índice atualizado")
                    self.lbl_st.config(
                        text="  Mapeamento %s: %s em %d arquivo(s)."
                        % ("pausado (dados salvos no índice)" if stopped else "concluído",
                           fsize(rt["total_size"]), rt["total_files"]),
                        foreground=self.app.WARN if stopped else self.app.OK)
                elif kind == "ERR":
                    self.lbl_st.config(text="  Erro: " + m[1], foreground=self.app.ERR)
        except Exception:
            dlog("[ERRO] SpaceDialog poll\n%s" % traceback.format_exc())
        if not self._closed:
            self.win.after(100, self._poll)

    def _on_double_click(self, event=None):
        iid = self.tree.identify_row(event.y) if event is not None else None
        if not iid:
            sel = self.tree.selection()
            iid = sel[0] if sel else None
        if not iid or iid not in self._rdata:
            return
        it = self._rdata[iid]
        if it.get("is_self"):
            return
        self.load_dir(it["path"])

    def _selected_or_cur_dir(self):
        sel = self.tree.selection()
        if sel and sel[0] in self._rdata:
            return self._rdata[sel[0]]["path"]
        return (self._cur_dir or self.v_dir.get()).strip()

    def _use_as_root(self):
        p = self._selected_or_cur_dir()
        if p:
            self.app.v_root.set(os.path.normpath(p))
            self.app.root.lift()

    def _open_selected(self):
        p = self._selected_or_cur_dir()
        if p:
            threading.Thread(target=lambda: self._safe_open_folder(p), daemon=True).start()

    def _safe_open_folder(self, path):
        try:
            open_folder(path)
        except Exception as e:
            dlog("[AVISO] não foi possível abrir pasta %s: %s" % (path, e))

    def _sort(self, col):
        self._srev = (not self._srev) if self._scol == col else (col in ("size", "pct", "files", "direct"))
        self._scol = col
        kids = self.tree.get_children()
        key_map = {"size": "total_size", "pct": "pct", "files": "total_files", "direct": "direct_size"}
        if col in key_map:
            k = key_map[col]
            items = sorted(kids, key=lambda i: self._rdata.get(i, {}).get(k, 0), reverse=self._srev)
        else:
            vals = {i: self.tree.set(i, col).lower() for i in kids}
            items = sorted(kids, key=vals.get, reverse=self._srev)
        for n, iid in enumerate(items):
            self.tree.move(iid, "", n)
            self.tree.item(iid, tags=("o" if n % 2 == 0 else "e",))
        arr = " ▲" if not self._srev else " ▼"
        for c in self.COLS:
            self.tree.heading(c, text=self.CLBLS[c] + (arr if c == col else ""))

    def _export(self):
        if not self._rows:
            messagebox.showinfo("Exportar", "Não há dados de espaço para exportar.", parent=self.win)
            return
        rows = [self._rdata[i] for i in self.tree.get_children() if i in self._rdata]
        dest = filedialog.asksaveasfilename(
            parent=self.win, title="Exportar espaço por pasta",
            initialfile="espaco_%s" % time.strftime("%Y-%m-%d_%H%M"),
            defaultextension=".xlsx",
            filetypes=[("Planilha Excel", "*.xlsx"),
                       ("CSV (Excel, LibreOffice, QGIS)", "*.csv"),
                       ("Texto formatado", "*.txt")])
        if not dest:
            return
        dest = os.path.normpath(dest)
        if os.path.splitext(dest)[1].lower() not in EXPORT_FORMATS:
            dest += ".xlsx"
        self.b_export.config(state="disabled")
        self.lbl_st.config(text="  Exportando %d linha(s) para %s..." % (len(rows), dest),
                           foreground=self.app.WARN)
        done_q = queue.Queue()

        def work():
            try:
                n = export_space_results(rows, dest)
                done_q.put((n, None))
            except Exception as e:
                done_q.put((0, str(e)))

        def poll():
            if self._closed:
                return
            try:
                n, err = done_q.get_nowait()
            except queue.Empty:
                self.win.after(100, poll)
                return
            self.b_export.config(state="normal")
            if err:
                self.lbl_st.config(text="  Falha ao exportar: " + err, foreground=self.app.ERR)
                messagebox.showerror("Exportar", "Não foi possível exportar:\n\n%s" % err, parent=self.win)
            else:
                self.lbl_st.config(text="  Exportado(s) %d item(ns) para %s" % (n, dest),
                                   foreground=self.app.OK)
        threading.Thread(target=work, daemon=True).start()
        self.win.after(100, poll)

    def _close(self):
        self._closed = True
        self._scan_stop.set()
        try:
            self.win.destroy()
        except tk.TclError:
            pass

# ===========================================================================
def _hide_own_console():
    """Esconde a janela de console quando ela foi criada SÓ para este processo
    (duplo clique no .py com python.exe). Se o script foi chamado de um
    terminal já aberto, o console é compartilhado e não é escondido."""
    if not IS_WIN or getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        hwnd = k32.GetConsoleWindow()
        if hwnd:
            pids = (wintypes.DWORD * 4)()
            if k32.GetConsoleProcessList(pids, 4) <= 1:
                ctypes.windll.user32.ShowWindow(hwnd, 0)   # SW_HIDE
    except Exception:
        pass

def _parse_cli(argv):
    """Interpreta argumentos de linha de comando sem impedir os flags existentes."""
    opts = {
        "index_path": INDEX_PATH,
        "no_index": "--no-index" in argv,
        "index_dir": None,
        "space_dir": None,
        "export": None,
        "excludes": (),
        "refresh": "--atualizar" in argv,
        "top": 30,
    }
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--indice", "--index") and i + 1 < len(argv):
            opts["index_path"] = os.path.normpath(argv[i + 1])
            i += 2
        elif a == "--indexar" and i + 1 < len(argv):
            opts["index_dir"] = os.path.normpath(argv[i + 1])
            i += 2
        elif a == "--espaco" and i + 1 < len(argv):
            opts["space_dir"] = os.path.normpath(argv[i + 1])
            i += 2
        elif a == "--exportar" and i + 1 < len(argv):
            opts["export"] = os.path.normpath(argv[i + 1])
            i += 2
        elif a == "--ignorar" and i + 1 < len(argv):
            opts["excludes"] = parse_excludes(argv[i + 1])
            i += 2
        elif a == "--top" and i + 1 < len(argv):
            try:
                opts["top"] = max(1, int(argv[i + 1]))
            except ValueError:
                pass
            i += 2
        else:
            i += 1
    return opts

def _run_cli(opts):
    """Modo de linha de comando (sem abrir janela): `--indexar` e/ou `--espaco`."""
    rotate_log()
    index = None
    if not opts["no_index"]:
        index = Index(opts["index_path"])
    try:
        scan_target = opts["index_dir"]
        if not scan_target and opts["space_dir"]:
            if index is None:
                scan_target = opts["space_dir"]
            elif opts["refresh"]:
                scan_target = opts["space_dir"]
            else:
                sp = index.folder_space(opts["space_dir"], exclude_dirs=opts["excludes"])
                if not sp or (sp["scanned_dirs"] == 0 and sp["total_files"] == 0):
                    scan_target = opts["space_dir"]
        mem_rows = []
        if scan_target:
            t0 = time.time()
            q = queue.Queue(maxsize=4000)
            stop = threading.Event()
            st = SearchThread(scan_target, "*", set(), False, q, stop,
                              fast_mode=True, index=index, refresh=True,
                              exclude_dirs=opts["excludes"])
            st.start()
            count = 0
            while True:
                item = q.get()
                if item is SearchThread.DONE:
                    break
                tag = item[0]
                if tag == "__ERR__":
                    sys.stderr.write("Erro: %s\n" % item[1])
                elif tag not in ("__STATUS__", "__REMOVE__", "__REMOVE_DIR__"):
                    count += 1
                    if index is None:
                        path, _name, _ext, sz, dp, mt = item
                        mem_rows.append({"path": path, "dir": dp, "size": sz, "mtime": mt})
            if index is not None:
                index.flush()
            el = time.time() - t0
            print("Indexado: %s (%d arquivos em %.1fs) -> %s" % (
                scan_target, count, el, opts["index_path"] if index else "memória"))
        if opts["space_dir"]:
            target = opts["space_dir"]
            if index is not None:
                sp = index.folder_space(target, exclude_dirs=opts["excludes"])
            else:
                sp = summarize_rows_space(mem_rows, target, exclude_dirs=opts["excludes"])
            items = folder_space_children(sp, target)
            print("\nEspaço por pasta em: %s" % target)
            print("Total: %s em %d arquivo(s)\n" % (fsize(sp["total_size"]), sp["total_files"]))
            for it in items[:opts["top"]]:
                print("%12s  %5.1f%%  %8d arq.  %s" % (
                    fsize(it["total_size"]), it["pct"], it["total_files"], it["path"]))
            if opts["export"]:
                export_space_results(items, opts["export"])
                print("\nExportado para: %s" % opts["export"])
    finally:
        if index is not None:
            index.close()
    return 0

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--version" in argv:
        print("%s %s" % (APP_NAME, __version__))
        return 0
    opts = _parse_cli(argv)
    if opts["index_dir"] or opts["space_dir"]:
        return _run_cli(opts)
    if tk is None:
        sys.stderr.write("Erro: tkinter não está disponível neste Python.\n"
                         "Linux: sudo apt install python3-tk  (ou dnf install python3-tkinter)\n")
        return 1
    _hide_own_console()
    rotate_log()
    dlog("=== INÍCIO v%s | Python %s | %s ===" % (
        __version__, platform.python_version(), platform.platform()))
    index = None
    if not opts["no_index"]:
        try:
            index = Index(opts["index_path"])
            dlog("Índice local: %s" % opts["index_path"])
        except Exception as e:
            dlog("[ÍNDICE] indisponível (%s): %s" % (opts["index_path"], e))
    root = tk.Tk()
    app = App(root, index)

    def close():
        app._stop_s.set()
        app._stop_c.set()
        root.destroy()
        if index is not None:
            index.close()   # grava o que estiver pendente
    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
