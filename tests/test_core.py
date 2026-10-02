# -*- coding: utf-8 -*-
"""Testes do núcleo (busca, filtro, cópia) e um teste de fumaça da interface.
Rodar:  python -m unittest discover -s tests -v
"""
import errno
import gc
import os
import queue
import shutil
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import reperio as g  # noqa: E402

# Os testes não escrevem no log real do usuário.
g.LOG_PATH = os.path.join(tempfile.gettempdir(), "reperio_tests.log")


def make_tree(base, files):
    for rel in files:
        p = os.path.join(base, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x" * 4096)


def run_search(root, pattern="*", exts=(), case=False, fast=True, stop=None,
               index=None, refresh=False, thread_out=None, retry_problems=False, channels=None):
    q, ev = queue.Queue(maxsize=2000), stop or threading.Event()
    t = g.SearchThread(root, pattern, list(exts), case, q, ev, fast_mode=fast,
                       index=index, refresh=refresh, retry_problems=retry_problems,
                       channels=channels)
    if thread_out is not None:
        thread_out.append(t)
    t.start()
    found, errors = [], []
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            it = q.get(timeout=0.5)
        except queue.Empty:
            if not t.is_alive():
                break
            continue
        if it is g.SearchThread.DONE:
            break
        if it[0] == "__ERR__":
            errors.append(it[1])
        elif it[0] == "__REMOVE__":
            found = [f for f in found if f[0] != it[1]]
            t.removed = getattr(t, "removed", []) + [it[1]]
        elif it[0] == "__REMOVE_DIR__":
            t.removed_dirs = getattr(t, "removed_dirs", []) + [it[1]]
        elif it[0] != "__STATUS__":
            found.append(it)
    t.join(5)
    return found, errors


class FakeNetError(OSError):
    """OSError que o app reconhece como falha transitória de rede."""
    def __init__(self, path):
        super(FakeNetError, self).__init__(errno.ETIMEDOUT, "timeout simulado", path)
        if os.name == "nt":
            self.winerror = 121


class TestMatcher(unittest.TestCase):
    def test_contains_without_wildcards(self):
        m = g.make_matcher("IMAGENS_", ())
        self.assertTrue(m("DATA_IMAGENS_LT8_2013.shp"))
        self.assertTrue(m("data_imagens_x.tif"))           # sem diferenciar caixa
        self.assertFalse(m("IMAGENS SPOT.zip"))

    def test_wildcards(self):
        m = g.make_matcher("*IMAGENS_*", ())
        self.assertTrue(m("IMAGENS_UHESINOP.rar"))
        self.assertFalse(m("1-Apresentacao_das_imagens rapideye.pdf"))
        self.assertTrue(g.make_matcher("*.shp", ())("a.SHP"))
        self.assertTrue(g.make_matcher("IMG_??", ())("IMG_01.tif"))

    def test_partial_wildcard_tolerance(self):
        self.assertTrue(g.make_matcher("*IMAGENS_", ())("X_IMAGENS_2013.dbf"))

    def test_case_sensitive(self):
        m = g.make_matcher("Mapa", (), case_sensitive=True)
        self.assertTrue(m("Mapa_01.shp"))
        self.assertFalse(m("mapa_01.shp"))

    def test_extensions(self):
        m = g.make_matcher("*", g.parse_exts(".shp tif, PDF"))
        self.assertTrue(m("a.shp"))
        self.assertTrue(m("b.TIF"))
        self.assertTrue(m("c.pdf"))
        self.assertFalse(m("d.dbf"))

    def test_clean_pattern(self):
        self.assertEqual(g.clean_pattern("  * IMAGENS_ *  "), "*IMAGENS_*")


class TestFormat(unittest.TestCase):
    def test_fsize(self):
        self.assertEqual(g.fsize(-1), "-")
        self.assertEqual(g.fsize(512), "512 B")
        self.assertEqual(g.fsize(2048), "2.0 KB")
        self.assertEqual(g.fsize(3 * 1024 ** 3), "3.00 GB")

    def test_fdate(self):
        self.assertEqual(g.fdate(-1), "-")
        self.assertRegex(g.fdate(0 + 86400 * 365), r"\d\d/\d\d/\d{4} \d\d:\d\d")


class TestSearch(unittest.TestCase):
    FILES = ["a/x.shp", "a/sub/x.shp", "b/ção/x.shp", "b/y.tif",
             "b/DATA_IMAGENS_LT8.dbf", "c/d/e/f/IMAGENS_UHE.rar"]

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        make_tree(self.base, self.FILES)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_both_modes_find_same(self):
        for fast in (True, False):
            found, errs = run_search(self.base, "*", [".shp"], fast=fast)
            self.assertEqual(errs, [])
            self.assertEqual(len(found), 3, "fast=%s" % fast)
            names = sorted(os.path.relpath(f[0], self.base).replace(os.sep, "/") for f in found)
            self.assertEqual(names, ["a/sub/x.shp", "a/x.shp", "b/ção/x.shp"])

    def test_pattern_contains(self):
        found, _ = run_search(self.base, "*IMAGENS_*")
        self.assertEqual(sorted(f[1] for f in found), ["DATA_IMAGENS_LT8.dbf", "IMAGENS_UHE.rar"])

    def test_sequential_has_metadata(self):
        found, _ = run_search(self.base, "y.tif", fast=False)
        self.assertEqual(len(found), 1)
        path, name, ext, size, folder, mtime = found[0]
        self.assertEqual((name, ext, size), ("y.tif", ".tif", 4096))
        self.assertGreater(mtime, 0)

    def test_root_missing_reports_error(self):
        found, errs = run_search(os.path.join(self.base, "nao_existe"))
        self.assertEqual(found, [])
        self.assertEqual(len(errs), 1)
        self.assertIn("inacess", errs[0])

    def test_stop_finishes_quickly(self):
        many = ["d%03d/f%03d.txt" % (i, j) for i in range(60) for j in range(10)]
        make_tree(self.base, many)
        ev = threading.Event()
        ev.set()
        t0 = time.time()
        run_search(self.base, "*", stop=ev)
        self.assertLess(time.time() - t0, 5)

    @unittest.skipIf(os.name == "nt", "symlink de pasta exige privilégio no Windows")
    def test_symlink_loop_is_skipped(self):
        os.symlink(self.base, os.path.join(self.base, "a", "loop"))
        found, _ = run_search(self.base, "*", [".shp"])
        self.assertEqual(len(found), 3)


class TestIndex(unittest.TestCase):
    FILES = ["a/x.shp", "a/sub/x.shp", "b/y.tif", "b/IMAGENS_1.tif", "c/d/IMAGENS_2.rar"]

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        self.data = os.path.join(self.base, "dados")
        make_tree(self.data, self.FILES)
        self.index = g.Index(os.path.join(self.base, "index.sqlite"))
        self._orig_list_dir = g.list_dir
        self.listed = []

        def spy(path, want_meta=True):
            self.listed.append(os.path.relpath(path, self.data))
            return self._orig_list_dir(path, want_meta)
        g.list_dir = spy

    def tearDown(self):
        g.list_dir = self._orig_list_dir
        self.index.close()
        shutil.rmtree(self.base, ignore_errors=True)

    def names(self, found):
        return sorted(os.path.relpath(f[0], self.data).replace(os.sep, "/") for f in found)

    def test_second_search_comes_from_index_only(self):
        found, _ = run_search(self.data, "*.shp", index=self.index)
        self.assertEqual(self.names(found), ["a/sub/x.shp", "a/x.shp"])
        self.listed.clear()
        th = []
        found, _ = run_search(self.data, "*IMAGENS_*", index=self.index, thread_out=th)
        self.assertEqual(self.names(found), ["b/IMAGENS_1.tif", "c/d/IMAGENS_2.rar"])
        self.assertEqual(self.listed, [], "não deveria ler o disco com índice completo")
        self.assertIn("índice local", th[0].summary)

    def test_index_works_for_subfolder_and_keeps_metadata(self):
        # Modo sequencial: lê tamanho/data em qualquer sistema (no Linux o modo
        # rápido não lê metadados, de propósito, para poupar uma consulta por arquivo).
        run_search(self.data, "*", index=self.index, fast=False)
        self.listed.clear()
        found, _ = run_search(os.path.join(self.data, "b"), "*.tif", index=self.index)
        self.assertEqual(self.names(found), ["b/IMAGENS_1.tif", "b/y.tif"])
        self.assertEqual(found[0][3], 4096)
        self.assertEqual(self.listed, [])

    def test_interrupted_search_resumes_only_missing_folders(self):
        # Simula uma busca interrompida: só a raiz foi lida.
        self.index.record_dir(self.data, ["a", "b", "c"], [])
        found, _ = run_search(self.data, "*", index=self.index)
        self.assertEqual(len(found), 5)
        self.assertNotIn(".", self.listed, "a raiz já lida não deve ser relida")
        self.assertIn("a", self.listed)

    def test_refresh_adds_new_files_without_duplicates(self):
        run_search(self.data, "*.tif", index=self.index)
        make_tree(self.data, ["b/novo.tif"])
        found, _ = run_search(self.data, "*.tif", index=self.index, refresh=True)
        self.assertEqual(self.names(found), ["b/IMAGENS_1.tif", "b/novo.tif", "b/y.tif"])

    def test_deleted_folder_is_removed_from_index(self):
        run_search(self.data, "*", index=self.index)
        shutil.rmtree(os.path.join(self.data, "a"))
        run_search(self.data, "*", index=self.index, refresh=True)
        found, _ = run_search(self.data, "*.shp", index=self.index)
        self.assertEqual(found, [])

    def test_incremental_refresh_relists_only_changed_folders(self):
        run_search(self.data, "*", index=self.index)
        # 1ª verificação: acerta as datas (a cópia vinda da pasta-mãe pode estar atrasada)
        run_search(self.data, "*", index=self.index, refresh=True)
        time.sleep(0.05)
        make_tree(self.data, ["c/d/novo_IMAGENS_3.tif"])   # muda só a pasta c/d
        self.listed.clear()
        th = []
        found, _ = run_search(self.data, "*IMAGENS_*", index=self.index, refresh=True, thread_out=th)
        self.assertEqual(self.names(found), ["b/IMAGENS_1.tif", "c/d/IMAGENS_2.rar",
                                             "c/d/novo_IMAGENS_3.tif"])
        self.assertIn(os.path.join("c", "d"), self.listed)
        self.assertNotIn("a", self.listed, "pasta sem mudança não deve ser relida")
        self.assertNotIn(os.path.join("a", "sub"), self.listed)
        self.assertGreaterEqual(th[0].checked, 5)

    def test_refresh_removes_deleted_files_from_results(self):
        run_search(self.data, "*.tif", index=self.index)
        time.sleep(0.05)
        os.remove(os.path.join(self.data, "b", "y.tif"))
        th = []
        found, _ = run_search(self.data, "*.tif", index=self.index, refresh=True, thread_out=th)
        self.assertEqual(self.names(found), ["b/IMAGENS_1.tif"])
        self.assertEqual([os.path.basename(p) for p in th[0].removed], ["y.tif"])

    def test_clear(self):
        run_search(self.data, "*", index=self.index)
        self.assertTrue(self.index.clear())
        self.listed.clear()
        run_search(self.data, "*", index=self.index)
        self.assertIn(".", self.listed)


class TestResilience(unittest.TestCase):
    """Pastas lentas ou com falha não podem segurar a busca."""
    FILES = ["ok1/a.shp", "ok2/b.shp", "ruim/c.shp", "lenta1/d.shp", "lenta2/e.shp"]

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        make_tree(self.base, self.FILES)
        self._saved = (g.list_dir, g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN, g.RESPONSIVE_WINDOW)
        g.RETRY_PAUSE = 0.1
        g.JAM_COOLDOWN = 0.1
        self.fail_times = {}      # pasta -> quantas vezes ainda falha
        self.slow = {}            # pasta -> segundos de atraso
        orig = g.list_dir

        def fake(path, want_meta=True):
            name = os.path.basename(path)
            if self.fail_times.get(name, 0) > 0:
                self.fail_times[name] -= 1
                raise FakeNetError(path)
            if name in self.slow:
                time.sleep(self.slow[name])
            return orig(path, want_meta)
        g.list_dir = fake

    def tearDown(self):
        g.list_dir, g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN, g.RESPONSIVE_WINDOW = self._saved
        shutil.rmtree(self.base, ignore_errors=True)

    def test_failed_folder_is_retried_at_the_end(self):
        self.fail_times["ruim"] = 2              # falha 2x, funciona na 3ª
        th = []
        found, errs = run_search(self.base, "*.shp", thread_out=th)
        self.assertEqual(len(found), 5)
        self.assertEqual(errs, [])
        self.assertEqual(th[0].failed, [])
        self.assertEqual(th[0].round, 2)
        # a pasta com falha foi a ÚLTIMA a entregar resultado
        self.assertEqual(found[-1][1], "c.shp")

    def test_permanent_failure_is_reported_and_others_complete(self):
        self.fail_times["ruim"] = 99
        th = []
        found, errs = run_search(self.base, "*.shp", thread_out=th)
        self.assertEqual(sorted(f[1] for f in found), ["a.shp", "b.shp", "d.shp", "e.shp"])
        self.assertEqual([os.path.basename(p) for p, _ in th[0].failed], ["ruim"])
        self.assertEqual(th[0].round, g.MAX_RETRY_ROUNDS)
        self.assertIn("não lidas", th[0].summary)

    def test_slow_folder_does_not_block_the_others(self):
        g.SLOW_AFTER = 0.3
        self.slow = {"lenta1": 2.0, "lenta2": 2.0}
        t0 = time.time()
        found, _ = run_search(self.base, "*.shp", fast=False)   # 1 leitura por vez
        self.assertEqual(len(found), 5)
        # Sem liberar a vaga, seriam >= 4 s em sequência.
        self.assertLess(time.time() - t0, 3.6)


class TestPoisonFolder(unittest.TestCase):
    """Reproduz o servidor real: enquanto a pasta-veneno está sendo lida, a
    sessão SMB inteira congestiona e TODAS as outras leituras travam e falham."""
    FILES = ["ok%d/f%d.shp" % (i, i) for i in range(6)] + ["veneno/x.shp"]

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        make_tree(self.base, self.FILES)
        self._saved = (g.list_dir, g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN, g.RESPONSIVE_WINDOW)
        g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN, g.RESPONSIVE_WINDOW = 0.05, 0.3, 0.1, 0.2
        self.index = g.Index(os.path.join(self.base, "idx.sqlite"))
        self.jam = threading.Event()
        self.lock = threading.Lock()
        self.active = self.max_active = 0
        self.calls = []
        orig = g.list_dir

        def fake(path, want_meta=True):
            name = os.path.basename(path)
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.calls.append(name)
            try:
                if name == "veneno":
                    self.jam.set()
                    time.sleep(1.0)
                    self.jam.clear()
                    raise FakeNetError(path)
                if self.jam.is_set():          # vítima do congestionamento
                    while self.jam.is_set():
                        time.sleep(0.02)
                    raise FakeNetError(path)
                return orig(path, want_meta)
            finally:
                with self.lock:
                    self.active -= 1
        g.list_dir = fake

    def tearDown(self):
        g.list_dir, g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN, g.RESPONSIVE_WINDOW = self._saved
        self.index.close()
        shutil.rmtree(self.base, ignore_errors=True)

    def test_poison_does_not_pile_up_requests_and_is_remembered(self):
        th = []
        found, _ = run_search(self.base, "*.shp", index=self.index, thread_out=th)
        t = th[0]
        # Todas as vítimas do congestionamento foram lidas depois, sozinhas.
        self.assertEqual(sorted(f[1] for f in found), ["f%d.shp" % i for i in range(6)])
        self.assertEqual([os.path.basename(p) for p, _ in t.failed], ["veneno"])
        # Com a sessão travada, não pode empilhar pedidos (2 vagas + 1 sonda).
        self.assertLessEqual(self.max_active, 3)

        # Próxima busca: a pasta-veneno fica de fora, com aviso — não trava nada.
        self.calls.clear()
        th = []
        found, _ = run_search(self.base, "*.shp", index=self.index, thread_out=th)
        self.assertEqual(len(found), 6)
        self.assertNotIn("veneno", self.calls)
        self.assertEqual([os.path.basename(p) for p, _f, _e in th[0].skipped_problems], ["veneno"])
        self.assertIn("problemática", th[0].summary)

    def test_problem_folder_retried_last_when_asked_and_cleared_when_it_works(self):
        run_search(self.base, "*.shp", index=self.index)       # vira problemática
        g.list_dir = self._saved[0]                            # servidor normalizou
        th = []
        found, _ = run_search(self.base, "*.shp", index=self.index, thread_out=th,
                              retry_problems=True)
        self.assertIn("x.shp", [f[1] for f in found])
        self.assertEqual(th[0].failed, [])
        th = []
        run_search(self.base, "*.shp", index=self.index, thread_out=th)
        self.assertEqual(th[0].skipped_problems, [], "saiu da lista ao funcionar")


class TestChannels(unittest.TestCase):
    """Várias conexões com o mesmo servidor (como medido num servidor real):
    a pasta-veneno trava SÓ a conexão por onde foi pedida; as outras seguem."""
    FILES = ["ok%02d/f%02d.shp" % (i, i) for i in range(20)] + ["veneno/x.shp", "veneno/sub/y.shp"]
    POISON_SECONDS = 1.0

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        make_tree(self.base, self.FILES)
        names = ("list_dir", "RETRY_PAUSE", "SLOW_AFTER", "JAM_COOLDOWN", "RESPONSIVE_WINDOW",
                 "JAM_DETECT", "CHANNEL_RECOVER")
        self._saved = {n: getattr(g, n) for n in names}
        g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN = 0.05, 30.0, 0.05
        g.RESPONSIVE_WINDOW, g.JAM_DETECT, g.CHANNEL_RECOVER = 0.2, 0.3, 0.2
        # Duas "conexões" para a mesma pasta: caminhos diferentes, mesmo conteúdo.
        self.A = g.Channel("conexão A", self.base, self.base, conn="a")
        self.B = g.Channel("conexão B", self.base, os.path.join(self.base, "."), conn="b")
        self.U = g.Channel("conexão do usuário", self.base, os.path.join(self.base, ".", "."), conn="u")
        self.U.user = True
        self.jammed = {"a": threading.Event(), "b": threading.Event(), "u": threading.Event()}
        self.poison_ok_on = None          # conexão onde a pasta-veneno funciona (None = nenhuma)
        self.calls = []
        self.lock = threading.Lock()
        orig = self._saved["list_dir"]
        sep = os.sep

        def conn_of(p):
            if (sep + "." + sep + "." + sep) in p or p.endswith(sep + "." + sep + "."):
                return "u"
            return "b" if (sep + "." + sep) in p or p.endswith(sep + ".") else "a"

        def fake(path, want_meta=True):
            c = conn_of(path)
            name = os.path.basename(os.path.normpath(path))
            with self.lock:
                self.calls.append((c, name))
            if name == "veneno" and c != self.poison_ok_on:
                self.jammed[c].set()
                time.sleep(self.POISON_SECONDS)
                self.jammed[c].clear()
                raise FakeNetError(path)
            if self.jammed[c].is_set():          # vítima: presa atrás da veneno
                while self.jammed[c].is_set():
                    time.sleep(0.02)
                raise FakeNetError(path)
            return orig(path, want_meta)
        g.list_dir = fake

    def tearDown(self):
        for n, v in self._saved.items():
            setattr(g, n, v)
        shutil.rmtree(self.base, ignore_errors=True)

    def test_switches_connection_and_finds_everything_else(self):
        th = []
        t0 = time.time()
        found, errs = run_search(self.base, "*.shp", thread_out=th, channels=[self.A, self.B, self.U])
        t = th[0]
        self.assertEqual(sorted(f[1] for f in found), ["f%02d.shp" % i for i in range(20)])
        self.assertGreaterEqual(t.switches, 1, "deveria trocar de conexão")
        self.assertEqual([os.path.basename(p) for p, _ in t.failed], ["veneno"])
        self.assertIn("2 conexões", t.failed[0][1])
        # A veneno nunca é tentada pela conexão do usuário (a do Explorer).
        self.assertNotIn(("u", "veneno"), self.calls)
        self.assertLess(time.time() - t0, 10)

    def test_victims_are_redone_immediately_not_after_timeout(self):
        # Como no servidor real: as leituras presas atrás da veneno demoram MUITO
        # mais para falhar do que a troca de conexão. Elas devem ser refeitas na hora.
        self.VICTIM_EXTRA = 4.0
        orig_fake = g.list_dir
        jammed = self.jammed

        def slow_victims(path, want_meta=True):
            try:
                dirs, files = orig_fake(path, want_meta)
                # A veneno vai PRIMEIRO na fila: assim sempre há leituras chegando à
                # conexão enquanto ela está travada (vítimas), em qualquer máquina —
                # sem depender da ordem do sistema de arquivos nem da velocidade do CI.
                dirs = sorted(dirs, key=lambda d: d[0] != "veneno")
                return dirs, files
            except FakeNetError:
                if os.path.basename(os.path.normpath(path)) != "veneno":
                    time.sleep(self.VICTIM_EXTRA)     # Windows demora a desistir
                raise
        g.list_dir = slow_victims
        q, ev = queue.Queue(maxsize=2000), threading.Event()
        t = g.SearchThread(self.base, "*.shp", [], False, q, ev, channels=[self.A, self.B, self.U])
        t0 = time.time()
        t.start()
        arrivals = []
        while True:
            it = q.get(timeout=60)
            if it is g.SearchThread.DONE:
                break
            if not it[0].startswith("__"):
                arrivals.append(time.time() - t0)
        t.join(5)
        self.assertEqual(len(arrivals), 20)
        self.assertGreaterEqual(t.hedged, 1, "vítimas deveriam ser refeitas na hora")
        # Os 20 resultados chegam ANTES de as vítimas presas desistirem
        # (veneno 1 s + vítimas 4 s): sem refazer na hora, o último levaria > 5 s.
        self.assertLess(arrivals[-1], self.POISON_SECONDS + self.VICTIM_EXTRA - 1)

    def test_big_folders_in_progress_are_not_mistaken_for_a_jam(self):
        # Teste real: 8 pastas IMAGENS enormes ao mesmo tempo, todas recebendo
        # dados, eram tomadas como "conexão travada" e duplicadas em cascata.
        base_fake = g.list_dir

        def big(path, want_meta=True):
            if os.path.basename(os.path.normpath(path)).startswith("ok"):
                for _ in range(12):            # ~1,2 s recebendo lotes
                    time.sleep(0.1)
                    g._touch()
            return base_fake(path, want_meta)
        g.list_dir = big
        self.poison_ok_on = "a"                # sem veneno neste teste
        th = []
        found, _ = run_search(self.base, "*.shp", thread_out=th, channels=[self.A, self.B, self.U])
        self.assertEqual(len(found), 22)
        self.assertEqual(th[0].switches, 0, "pasta grande progredindo não é travamento")
        self.assertEqual(th[0].hedged, 0)

    def test_user_connection_is_never_used_when_alternatives_exist(self):
        # Só 1 conexão alternativa + a do usuário: sem troca/quarentena, e a do
        # usuário (Explorer) nunca recebe nada — vale o modo de rodadas no fim.
        th = []
        found, _ = run_search(self.base, "*.shp", thread_out=th, channels=[self.U, self.A])
        self.assertEqual(sorted(f[1] for f in found), ["f%02d.shp" % i for i in range(20)])
        self.assertFalse(any(c == "u" for c, _n in self.calls), "usou a conexão do usuário")
        self.assertEqual([os.path.basename(p) for p, _ in th[0].failed], ["veneno"])

    def test_poison_rescued_by_separate_connection(self):
        self.poison_ok_on = "b"            # pela conexão B o servidor responde
        th = []
        found, _ = run_search(self.base, "*.shp", thread_out=th, channels=[self.A, self.B, self.U])
        names = sorted(f[1] for f in found)
        self.assertIn("x.shp", names)
        self.assertIn("y.shp", names, "subpastas da pasta recuperada também são lidas")
        self.assertEqual(len(names), 22)
        self.assertEqual(th[0].failed, [])
        self.assertEqual(th[0].rescued, 1)

    def test_known_problem_is_read_in_quarantine_without_blocking(self):
        idx = g.Index(os.path.join(self.base, "idx.sqlite"))
        try:
            run_search(self.base, "*.shp", index=idx, channels=[self.A, self.B, self.U])
            idx.flush()
            # Próxima busca, com retry pedido e servidor corrigido para a veneno.
            self.poison_ok_on = "b"
            th = []
            found, _ = run_search(self.base, "*.shp", index=idx, retry_problems=True, thread_out=th,
                                  channels=[g.Channel("conexão A", self.base, self.base, conn="a"),
                                            g.Channel("conexão B", self.base, os.path.join(self.base, "."), conn="b")])
            self.assertIn("x.shp", [f[1] for f in found])
            self.assertEqual(th[0].failed, [])
            th = []
            run_search(self.base, "*.shp", index=idx, thread_out=th, channels=[self.A, self.B])
            self.assertEqual(th[0].skipped_problems, [], "saiu da lista de problemáticas")
        finally:
            idx.close()


class TestNoCascade(unittest.TestCase):
    """Teste real (14:33): a suspeita escolhida (a leitura presa mais antiga) era
    uma vítima; a culpada era refeita na conexão nova e a travava também — em
    cascata. A culpada deve ser identificada no 2º travamento e não refeita mais."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        # "a_lenta" começa ANTES da veneno e fica presa como vítima (a mais antiga).
        make_tree(self.base, ["a_lenta/a.shp"] + ["ok%02d/f%02d.shp" % (i, i) for i in range(10)]
                  + ["veneno/x.shp"])
        names = ("list_dir", "RETRY_PAUSE", "SLOW_AFTER", "JAM_COOLDOWN", "RESPONSIVE_WINDOW",
                 "JAM_DETECT", "CHANNEL_RECOVER")
        self._saved = {n: getattr(g, n) for n in names}
        g.RETRY_PAUSE, g.SLOW_AFTER, g.JAM_COOLDOWN = 0.05, 30.0, 0.05
        g.RESPONSIVE_WINDOW, g.JAM_DETECT, g.CHANNEL_RECOVER = 0.2, 0.3, 0.2
        sep = os.sep
        self.chs = [g.Channel("c%d" % i, self.base, self.base + (sep + ".") * i, conn="c%d" % i)
                    for i in range(4)]
        self.jam = {"c%d" % i: threading.Event() for i in range(4)}
        self.calls = []
        orig = self._saved["list_dir"]

        def conn_of(p):
            return "c%d" % p.count(sep + ".")

        def fake(path, want_meta=True):
            c = conn_of(path)
            name = os.path.basename(os.path.normpath(path))
            self.calls.append((c, name))
            if name == "veneno":
                self.jam[c].set()
                time.sleep(1.0)
                self.jam[c].clear()
                raise FakeNetError(path)
            if name == "a_lenta":
                time.sleep(0.15)                  # começa antes e fica presa
            if self.jam[c].is_set():
                while self.jam[c].is_set():
                    time.sleep(0.02)
                raise FakeNetError(path)
            return orig(path, want_meta)
        g.list_dir = fake

    def tearDown(self):
        for n, v in self._saved.items():
            setattr(g, n, v)
        shutil.rmtree(self.base, ignore_errors=True)

    def test_culprit_identified_and_cascade_stops(self):
        th = []
        found, _ = run_search(self.base, "*.shp", thread_out=th, channels=self.chs)
        t = th[0]
        self.assertEqual(len(found), 11)
        self.assertEqual([os.path.basename(p) for p, _ in t.failed], ["veneno"])
        self.assertLessEqual(t.switches, 2, "a cascada deveria parar no 2º travamento")
        # a veneno roda no máx. em 2 conexões na busca principal + quarentena (2 tentativas)
        self.assertLessEqual(sum(1 for c, n in self.calls if n == "veneno"), 4)


class TestChannelResolution(unittest.TestCase):
    def test_local_path_has_single_channel(self):
        base = tempfile.mkdtemp(prefix="gff_")
        try:
            chs = g.resolve_channels(base)
            self.assertEqual(len(chs), 1)
            self.assertEqual(chs[0].path(os.path.join(base, "x")), os.path.join(base, "x"))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_host_aliases_include_trailing_dot_fqdn(self):
        import socket
        saved = (socket.getfqdn, socket.gethostbyname)
        socket.getfqdn = lambda h: "arquivos.empresa.local"
        socket.gethostbyname = lambda h: "10.0.0.5"
        try:
            names = g._host_aliases("arquivos")
        finally:
            socket.getfqdn, socket.gethostbyname = saved
        self.assertEqual(names, ["arquivos.empresa.local", "arquivos.empresa.local.",
                                 "10.0.0.5", "arquivos"])

    def test_channel_path_translation(self):
        ch = g.Channel("IP", r"Y:\Banco", r"\\10.0.0.1\share\Banco", conn="10.0.0.1")
        self.assertEqual(ch.path(r"Y:\Banco\a\b"), r"\\10.0.0.1\share\Banco\a\b")
        self.assertEqual(ch.path(r"Y:\Banco"), r"\\10.0.0.1\share\Banco")


class TestNetTimeout(unittest.TestCase):
    def test_detects_timeouts(self):
        e = OSError(110, "timeout")
        e.errno = __import__("errno").ETIMEDOUT
        self.assertTrue(g.is_net_timeout(e))
        self.assertFalse(g.is_net_timeout(OSError(2, "not found")))


class TestAdaptiveGate(unittest.TestCase):
    def _timeout(self, gate, stop):
        gate.acquire(stop)
        gate.release(timed_out=True)

    def test_timeout_serializes_and_pauses(self):
        # Timeout = sessão congestionada (medido no servidor real): cai para 1 e pausa.
        gate = g.AdaptiveGate(start=6, maximum=8, grow_after=1, cooldown=0.3)
        stop = threading.Event()
        self._timeout(gate, stop)
        self.assertEqual(gate.limit, 1)
        self.assertEqual(gate.ceiling, 5)
        t0 = time.time()
        gate.acquire(stop)                    # espera a pausa
        self.assertGreaterEqual(time.time() - t0, 0.25)
        gate.release()
        for _ in range(20):
            gate.acquire(stop)
            gate.release()
        self.assertEqual(gate.limit, 5)       # cresce de novo, mas só até 6-1

    def test_probe_rule_when_server_unresponsive(self):
        gate = g.AdaptiveGate(start=2, maximum=8)
        gate.last_ok = time.time() - 60       # nada concluído há 1 min
        self.assertTrue(gate.can_detach())    # uma leitura-sonda é permitida
        stop = threading.Event()
        gate.acquire(stop)
        gate.detach()
        self.assertFalse(gate.can_detach())   # a segunda não: servidor travado

    def test_detach_frees_a_slot(self):
        gate = g.AdaptiveGate(start=1, maximum=1)
        stop = threading.Event()
        gate.acquire(stop)
        gate.detach()                          # leitura lenta liberou a vaga
        self.assertTrue(gate.acquire(stop))
        gate.release(detached=True)
        gate.release()
        self.assertEqual(gate.active, 0)

    def test_acquire_respects_stop(self):
        gate = g.AdaptiveGate(start=1, maximum=1)
        stop = threading.Event()
        gate.acquire(stop)
        stop.set()
        self.assertFalse(gate.acquire(stop))


class TestCopy(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="gff_")
        make_tree(self.base, ["src/a/x.shp", "src/b/x.shp", "src/c/x.shp", "src/c/y.tif"])
        self.src = os.path.join(self.base, "src")
        self.files = [os.path.join(self.src, p) for p in
                      ("a/x.shp", "b/x.shp", "c/x.shp", "c/y.tif")]

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _copy(self, keep, stop=None):
        dest = os.path.join(self.base, "dest")
        pq = queue.Queue()
        g.CopyManager(self.files, dest, keep, pq, stop or threading.Event()).start(self.src)
        while True:
            m = pq.get(timeout=30)
            if m[0] == "DONE":
                return dest, m[1]

    def test_flat_renames_duplicates(self):
        dest, errs = self._copy(keep=False)
        self.assertEqual(errs, [])
        self.assertEqual(sorted(os.listdir(dest)), ["x.shp", "x_1.shp", "x_2.shp", "y.tif"])

    def test_keep_structure(self):
        dest, errs = self._copy(keep=True)
        self.assertEqual(errs, [])
        self.assertTrue(os.path.isfile(os.path.join(dest, "c", "y.tif")))
        self.assertTrue(os.path.isfile(os.path.join(dest, "a", "x.shp")))

    def test_copy_file_cancel_removes_partial(self):
        src = os.path.join(self.base, "big.bin")
        with open(src, "wb") as f:
            f.write(b"0" * (3 * 1024 * 1024))
        dst = os.path.join(self.base, "big_copy.bin")
        stop = threading.Event()
        stop.set()
        with self.assertRaises(g.CopyCancelled):
            g.copy_file(src, dst, stop)
        self.assertFalse(os.path.exists(dst))

    def test_copy_file_preserves_size_and_mtime(self):
        dst = os.path.join(self.base, "copia.tif")
        n = g.copy_file(self.files[3], dst, threading.Event())
        self.assertEqual(n, 4096)
        self.assertAlmostEqual(os.path.getmtime(dst), os.path.getmtime(self.files[3]), delta=2)


class TestExport(unittest.TestCase):
    ROWS = [
        {"path": os.path.join("Y:" + os.sep, "Banco", "ção & <teste>", "IMG_01.tif"),
         "dir": os.path.join("Y:" + os.sep, "Banco", "ção & <teste>"), "size": 3 * 1024 ** 3,
         "mtime": 1700000000.0},
        {"path": os.path.join("Y:" + os.sep, "Banco", "mapa\x01.shp"),
         "dir": os.path.join("Y:" + os.sep, "Banco"), "size": -1, "mtime": -1},
    ]

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="gff_exp_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_csv_opens_in_excel_ptbr(self):
        import csv
        p = os.path.join(self.d, "r.csv")
        self.assertEqual(g.export_results(self.ROWS, p), 2)
        raw = open(p, "rb").read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "BOM UTF-8 para o Excel reconhecer acentos")
        with open(p, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.reader(f, delimiter=";"))
        self.assertEqual(rows[0], list(g.EXPORT_HEADER))
        self.assertEqual(rows[1][0], "IMG_01.tif")
        self.assertEqual(rows[1][2], str(3 * 1024 ** 3))
        self.assertEqual(rows[1][3], "3.00 GB")
        self.assertRegex(rows[1][4], r"^\d\d/\d\d/\d{4} \d\d:\d\d:\d\d$")
        self.assertIn("ção & <teste>", rows[1][5])
        self.assertEqual(rows[2][2:5], ["", "", ""], "sem tamanho/data (modo rápido no Linux)")

    def test_txt_one_path_per_line(self):
        p = os.path.join(self.d, "r.txt")
        g.export_results(self.ROWS, p)
        lines = open(p, encoding="utf-8").read().splitlines()
        self.assertEqual(lines, [r["path"] for r in self.ROWS])

    def test_xlsx_is_valid_spreadsheet(self):
        import zipfile
        import xml.etree.ElementTree as ET
        p = os.path.join(self.d, "r.xlsx")
        self.assertEqual(g.export_results(self.ROWS, p), 2)
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with zipfile.ZipFile(p) as z:
            self.assertIsNone(z.testzip())
            for name in z.namelist():                      # todas as partes são XML válido
                ET.fromstring(z.read(name))
            sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows = sheet.findall(".//m:sheetData/m:row", ns)
        self.assertEqual(len(rows), 3)
        texts = ["".join(c.itertext()) for c in rows[1]]
        self.assertEqual(texts[0], "IMG_01.tif")
        size_cell = [c for c in rows[1] if c.get("r") == "C2"][0]
        self.assertEqual(size_cell.find("m:v", ns).text, str(3 * 1024 ** 3))   # número, não texto
        date_cell = [c for c in rows[1] if c.get("r") == "E2"][0]
        self.assertGreater(float(date_cell.find("m:v", ns).text), 45000)       # data serial (2023)
        self.assertIn("ção & <teste>", "".join(rows[1].itertext()))
        self.assertNotIn("\x01", "".join(rows[2].itertext()), "caractere de controle removido")
        self.assertIsNotNone(sheet.find("m:autoFilter", ns))

    def test_unknown_extension_is_rejected(self):
        with self.assertRaises(ValueError):
            g.export_results(self.ROWS, os.path.join(self.d, "r.pdf"))

    def test_xlsx_column_letters(self):
        self.assertEqual([g._xlsx_col(i) for i in (0, 25, 26, 27, 701, 702)],
                         ["A", "Z", "AA", "AB", "ZZ", "AAA"])


class TestReviewFixes(unittest.TestCase):
    """Correções da revisão de código (2.5.0): cada teste reproduz o problema."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="gff_rev_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_invalid_name_does_not_kill_index_writer_and_round_trips(self):
        # Nome com "surrogate" isolado (Samba antigo): antes matava o gravador do índice.
        idx = g.Index(os.path.join(self.d, "i.sqlite"))
        try:
            pasta = os.path.join(self.d, "pasta\udcff")
            idx.record_dir(pasta, [], [("ruim\udcff.tif", 10, 1.7e9)], None)
            idx.record_dir(os.path.join(self.d, "ok"), [], [("bom.tif", 1, 1.7e9)], None)
            self.assertTrue(idx.flush(timeout=5), "gravador do índice morreu")
            self.assertTrue(idx._t.is_alive())
            got = []
            idx.query(self.d, lambda n: True, got.append, threading.Event())
            names = sorted(it[1] for it in got)
            self.assertEqual(names, ["bom.tif", "ruim\udcff.tif"], "nome original recuperado")
            self.assertIn(os.path.join(pasta, "ruim\udcff.tif"), [it[0] for it in got])
        finally:
            idx.close()

    def test_db_encoding_is_reversible(self):
        for s in ("normal ção", "a\udcffb\ud800", "", "\U000F0000 raro"):
            if "\U000F0000" in s:
                continue          # caractere de uso privado real: fora do escopo
            self.assertEqual(g.db_dec(g.db_enc(s)), s)
            g.db_enc(s).encode("utf-8")      # sempre gravável no SQLite

    def test_refresh_removes_deleted_subfolder_from_screen(self):
        data = os.path.join(self.d, "dados")
        make_tree(data, ["sub/a.tif", "b.tif"])
        idx = g.Index(os.path.join(self.d, "i.sqlite"))
        try:
            run_search(data, "*", index=idx)
            run_search(data, "*", index=idx, refresh=True)     # acerta as datas
            time.sleep(0.05)
            shutil.rmtree(os.path.join(data, "sub"))
            th = []
            run_search(data, "*", index=idx, refresh=True, thread_out=th)
            self.assertIn(os.path.join(data, "sub"), getattr(th[0], "removed_dirs", []))
        finally:
            idx.close()

    def test_folder_deleted_during_search_is_not_a_failure(self):
        data = os.path.join(self.d, "dados")
        make_tree(data, ["sumiu/a.tif", "fica/b.tif"])
        saved = g.list_dir

        def fake(path, want_meta=True):
            if os.path.basename(path) == "sumiu":
                raise FileNotFoundError(errno.ENOENT, "não encontrado", path)
            return saved(path, want_meta)
        g.list_dir = fake
        try:
            th = []
            found, errs = run_search(data, "*", thread_out=th)
        finally:
            g.list_dir = saved
        self.assertEqual([f[1] for f in found], ["b.tif"])
        self.assertEqual(th[0].failed, [], "pasta apagada não é 'não lida'")
        self.assertEqual(errs, [])

    def test_export_survives_invalid_date_and_name(self):
        rows = [{"path": os.path.join("C:" + os.sep, "x", "data_absurda.tif"), "dir": "C:" + os.sep,
                 "size": 1, "mtime": 1e13},
                {"path": os.path.join("C:" + os.sep, "x", "nome\udcff.tif"), "dir": "C:" + os.sep,
                 "size": 1, "mtime": 1.7e9}]
        for ext in (".xlsx", ".csv", ".txt"):
            self.assertEqual(g.export_results(rows, os.path.join(self.d, "r" + ext)), 2, ext)

    def test_csv_formula_injection_is_neutralized(self):
        import csv
        rows = [{"path": os.path.join("C:" + os.sep, "x", "=SOMA(1;2).tif"), "dir": "C:" + os.sep,
                 "size": 1, "mtime": 1.7e9},
                {"path": os.path.join("C:" + os.sep, "x", "@cmd.tif"), "dir": "C:" + os.sep,
                 "size": 1, "mtime": 1.7e9}]
        p = os.path.join(self.d, "f.csv")
        g.export_results(rows, p)
        with open(p, encoding="utf-8-sig", newline="") as f:
            got = [r[0] for r in list(csv.reader(f, delimiter=";"))[1:]]
        self.assertEqual(got, ["'=SOMA(1;2).tif", "'@cmd.tif"])

    def test_friendly_error_messages(self):
        e = OSError(13, "x")
        e.winerror = 5
        self.assertTrue(g.describe_error(e).startswith("acesso negado"))
        e = OSError(22, "y")
        e.winerror = 121
        self.assertIn("timeout", g.describe_error(e))
        self.assertEqual(g.describe_error(OSError(9999, "z")), str(OSError(9999, "z")))


class TestGuiExport(unittest.TestCase):
    """Botão Exportar na interface real (diálogos simulados): a gravação ocorre
    em outra thread e o aviso de conclusão volta pela fila, sem erro do tkinter."""

    def test_export_button_selected_and_all(self):
        if g.tk is None:
            self.skipTest("tkinter indisponível")
        try:
            root = g.tk.Tk()
        except g.tk.TclError as e:
            self.skipTest("sem display: %s" % e)
        base = tempfile.mkdtemp(prefix="gff_")
        saved = (g.filedialog.asksaveasfilename, g.messagebox.askyesnocancel, g.messagebox.askyesno)
        errors = []
        old_hook = threading.excepthook
        threading.excepthook = lambda a: errors.append(a.exc_value)
        try:
            make_tree(base, ["d/a%02d.shp" % i for i in range(12)])
            root.withdraw()
            app = g.App(root)
            app.v_root.set(base)
            app._start()
            deadline = time.time() + 15
            while (app._running or app._rcount == 0) and time.time() < deadline:
                root.update()
                time.sleep(0.02)
            app.tree.selection_set(app.tree.get_children()[:4])
            app._on_sel()
            g.messagebox.askyesno = lambda *a, **k: False          # não abrir o arquivo
            for ext, only_sel, expected in ((".xlsx", True, 4), (".txt", False, 12)):
                dest = os.path.join(base, "saida" + ext)
                g.filedialog.asksaveasfilename = lambda *a, **k: dest
                g.messagebox.askyesnocancel = lambda *a, **k: only_sel
                app._export()
                deadline = time.time() + 10
                while str(app.b_export["state"]) == "disabled" and time.time() < deadline:
                    root.update()
                    time.sleep(0.02)
                self.assertTrue(os.path.exists(dest))
                self.assertIn("Exportado(s) %d" % expected, app.lbl_st.cget("text"))
            self.assertEqual(errors, [], "exceção em thread de exportação")
        finally:
            threading.excepthook = old_hook
            g.filedialog.asksaveasfilename, g.messagebox.askyesnocancel, g.messagebox.askyesno = saved
            root.destroy()
            # Libera as variáveis do Tk AQUI, na thread principal: se o coletor de
            # lixo as recolher numa thread de busca de outro teste, o Tcl aborta.
            app = root = None
            gc.collect()
            shutil.rmtree(base, ignore_errors=True)


class TestGuiDoubleStart(unittest.TestCase):
    def test_two_quick_clicks_leave_no_orphan_search(self):
        if g.tk is None:
            self.skipTest("tkinter indisponível")
        try:
            root = g.tk.Tk()
        except g.tk.TclError as e:
            self.skipTest("sem display: %s" % e)
        base = tempfile.mkdtemp(prefix="gff_")
        try:
            make_tree(base, ["d%02d/x.shp" % i for i in range(40)])
            root.withdraw()
            app = g.App(root)
            app.v_root.set(base)
            threads = []
            orig = g.SearchThread.start

            def spy(self_):
                threads.append(self_)
                orig(self_)
            g.SearchThread.start = spy
            try:
                app._start()
                app._start()                      # 2º clique antes do 1º _do_start rodar
                deadline = time.time() + 15
                while (len(threads) < 2 or app._running) and time.time() < deadline:
                    root.update()
                    time.sleep(0.02)
            finally:
                g.SearchThread.start = orig
            self.assertEqual(len(threads), 2)
            self.assertTrue(threads[0].stop.is_set(), "a 1ª busca deveria ter sido parada")
            threads[0].join(5)
            self.assertFalse(threads[0].is_alive(), "busca órfã continua rodando")
        finally:
            root.destroy()
            app = root = None
            gc.collect()
            shutil.rmtree(base, ignore_errors=True)


class TestGuiSmoke(unittest.TestCase):
    def test_app_builds_and_searches(self):
        if g.tk is None:
            self.skipTest("tkinter indisponível")
        try:
            root = g.tk.Tk()
        except g.tk.TclError as e:
            self.skipTest("sem display: %s" % e)
        base = tempfile.mkdtemp(prefix="gff_")
        try:
            make_tree(base, ["a/x.shp", "b/y.shp"])
            root.withdraw()
            app = g.App(root)
            app.v_root.set(base)
            app.v_ext.set(".shp")
            app._start()
            deadline = time.time() + 15
            while (app._running or app._rcount == 0) and time.time() < deadline:
                root.update()
                time.sleep(0.02)
            self.assertFalse(app._running)
            self.assertEqual(app._rcount, 2)
            app._sel_all()
            self.assertEqual(app._nsel, 2)
            app._sort("name")
        finally:
            root.destroy()
            # Libera as variáveis do Tk AQUI, na thread principal: se o coletor de
            # lixo as recolher numa thread de busca de outro teste, o Tcl aborta.
            app = root = None
            gc.collect()
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
