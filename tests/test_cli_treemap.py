# -*- coding: utf-8 -*-
"""Testes do treemap e da linha de comando (v2.7): argumentos, JSON, códigos de saída.
Rodar:  python -m unittest discover -s tests -v
"""
import contextlib
import gc
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import reperio as g  # noqa: E402

g.LOG_PATH = os.path.join(tempfile.gettempdir(), "reperio_tests.log")


def make_files(base, spec):
    """spec: {"a/b.bin": tamanho_em_bytes}"""
    for rel, size in spec.items():
        p = os.path.join(base, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(b"x" * size)


def run_cli(*argv):
    """Executa g.main(argv) e devolve (código, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = g.main(list(argv))
        except SystemExit as e:        # argparse sai com 2 em erro de uso e 0 na ajuda
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TestSquarify(unittest.TestCase):
    def test_areas_proportional_and_inside(self):
        values = [600, 300, 100, 50, 25, 25]
        rects = g.squarify(values, 10, 20, 400, 300)
        self.assertEqual(len(rects), len(values))
        total_area = 400 * 300
        for v, (x, y, w, h) in zip(values, rects):
            self.assertGreaterEqual(x, 10 - 1e-6)
            self.assertGreaterEqual(y, 20 - 1e-6)
            self.assertLessEqual(x + w, 410 + 1e-6)
            self.assertLessEqual(y + h, 320 + 1e-6)
            self.assertAlmostEqual(w * h, total_area * v / sum(values), delta=1e-3 * total_area)
        self.assertAlmostEqual(sum(w * h for _x, _y, w, h in rects), total_area, delta=1e-6 * total_area)

    def test_blocks_do_not_overlap(self):
        values = [50, 40, 30, 20, 10, 9, 8, 7, 3, 1]
        rects = g.squarify(values, 0, 0, 500, 200)
        for i, (x1, y1, w1, h1) in enumerate(rects):
            for x2, y2, w2, h2 in rects[i + 1:]:
                ox = min(x1 + w1, x2 + w2) - max(x1, x2)
                oy = min(y1 + h1, y2 + h2) - max(y1, y2)
                self.assertFalse(ox > 1e-6 and oy > 1e-6)

    def test_degenerate_inputs(self):
        self.assertEqual(g.squarify([], 0, 0, 10, 10), [])
        self.assertEqual(g.squarify([5], 0, 0, 0, 10), [(0, 0, 0.0, 0.0)])
        self.assertEqual(g.squarify([5], 1, 2, 30, 40)[0], (1, 2, 30.0, 40.0))


class TestTreemapData(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="rp_tm_")
        self.data = os.path.join(self.d, "dados")
        make_files(self.data, {"video/a.mp4": 9000, "video/b.mp4": 6000, "docs/x.pdf": 1000,
                               "docs/y.pdf": 500, "docs/z.txt": 10, "solto.bin": 100,
                               "muitos/f1": 1, "muitos/f2": 1, "muitos/f3": 1, "muitos/f4": 1})
        self.sp = g.summarize_rows_space(self._rows(), self.data)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _rows(self):
        rows = []
        for dp, _dn, fns in os.walk(self.data):
            for fn in fns:
                p = os.path.join(dp, fn)
                rows.append({"path": p, "dir": dp, "size": os.path.getsize(p)})
        return rows

    def test_space_tree_totals_and_kinds(self):
        t = g.space_tree(self.sp, self.data, depth=2)
        self.assertEqual(t["size"], 16614)
        self.assertEqual(t["files"], 10)
        kinds = {c["name"]: c["kind"] for c in t["children"]}
        self.assertEqual(kinds["video"], "dir")
        self.assertEqual(kinds["[arquivos desta pasta]"], "files")
        self.assertEqual(sum(c["size"] for c in t["children"]), t["size"])

    def test_space_tree_groups_small_items(self):
        t = g.space_tree(self.sp, self.data, depth=2, max_children=1)
        names = [c["name"] for c in t["children"]]
        self.assertTrue(any(n.startswith("[outros") for n in names))
        self.assertEqual(sum(c["size"] for c in t["children"]), t["size"])
        self.assertIsNone(g.space_tree(self.sp, os.path.join(self.d, "nao_existe")))

    def test_layout_metrics_differ(self):
        t = g.space_tree(self.sp, self.data, depth=2)
        by_size = {r["node"]["name"]: r for r in g.treemap_layout(t, "tamanho", 800, 500) if r["depth"] == 1}
        by_files = {r["node"]["name"]: r for r in g.treemap_layout(t, "quantidade", 800, 500) if r["depth"] == 1}
        # video domina por tamanho; docs (3 arquivos) e muitos (4) pesam mais por quantidade
        self.assertGreater(by_size["video"]["w"] * by_size["video"]["h"],
                           by_size["docs"]["w"] * by_size["docs"]["h"])
        self.assertGreater(by_files["muitos"]["w"] * by_files["muitos"]["h"],
                           by_files["video"]["w"] * by_files["video"]["h"])

    def test_html_export(self):
        dest = os.path.join(self.d, "mapa.html")
        n = g.export_treemap_html(self.sp, dest, self.data, primary="quantidade")
        self.assertEqual(n, 4)
        with open(dest, encoding="utf-8") as f:
            html = f.read()
        self.assertIn("<svg", html)
        self.assertIn("video", html)
        self.assertNotIn("@@", html)
        self.assertIn('value="quantidade" checked', html)
        self.assertNotIn("http://cdn", html)


class TestCliArgs(unittest.TestCase):
    def test_unknown_flag_is_usage_error_not_gui(self):
        code, _o, e = run_cli("--espacoo", "x")
        self.assertEqual(code, 2)
        self.assertIn("unrecognized", e)

    def test_help_and_version(self):
        code, o, _e = run_cli("--help")
        self.assertEqual(code, 0)
        self.assertIn("--espaco", o)
        self.assertIn("códigos de saída", o)
        code, o, _e = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertIn(g.__version__, o)

    def test_modifier_without_action(self):
        self.assertEqual(run_cli("--json")[0], 2)

    def test_search_needs_folder(self):
        self.assertEqual(run_cli("--maiores", "5")[0], 2)

    def test_no_index_limits(self):
        self.assertEqual(run_cli("--no-index", "--status")[0], 2)

    def test_manifest_is_json(self):
        code, o, _e = run_cli("--manifesto")
        self.assertEqual(code, 0)
        m = json.loads(o)
        self.assertEqual(m["versao"], g.__version__)
        flags = [f for a in m["argumentos"] for f in a["flags"]]
        for needed in ("--espaco", "--buscar", "--treemap", "--json", "--so-indice"):
            self.assertIn(needed, flags)
        self.assertIn("3", m["codigos_de_saida"])


class TestCliActions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp(prefix="rp_cli_")
        cls.data = os.path.join(cls.d, "dados")
        make_files(cls.data, {"fotos/a.jpg": 5000, "fotos/b.JPG": 3000, "zips/c.zip": 9000,
                              "zips/d.zip": 100, "doc.txt": 50, "_lixo/e.tmp": 7000})
        cls.idx = os.path.join(cls.d, "i.sqlite")
        code, o, _e = run_cli("--indice", cls.idx, "--indexar", cls.data, "--json", "-q")
        assert code == 0, o
        cls.first = json.loads(o)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def q(self, *argv):
        code, o, e = run_cli("--indice", self.idx, "--so-indice", "--json", *argv)
        return code, (json.loads(o) if o.strip() else None), e

    def test_index_json_stats(self):
        v = self.first["varredura"]
        self.assertEqual(v["arquivos"], 6)
        self.assertEqual(v["n_falhas"], 0)
        self.assertTrue(self.first["ok"])
        self.assertIn("pico_ram_mb", self.first["desempenho"])

    def test_espaco_json_nested(self):
        code, j, _e = self.q("--espaco", self.data, "--profundidade", "2", "--top", "3")
        self.assertEqual(code, 0)
        e = j["espaco"]
        self.assertEqual(e["total_bytes"], 24150)
        self.assertTrue(e["completo"])
        self.assertEqual(len(e["itens"]), 3)
        self.assertEqual(e["itens"][0]["nome"], "zips")
        self.assertEqual(e["itens"][0]["tipo"], "pasta")
        self.assertIn("filhos", e["itens"][0] if e["itens"][0]["subpastas"] else {"filhos": 1})

    def test_espaco_respects_ignorar(self):
        code, j, _e = self.q("--espaco", self.data, "--ignorar", "_lixo")
        self.assertEqual(code, 0)
        self.assertEqual(j["espaco"]["total_bytes"], 17150)

    def test_maiores(self):
        code, j, _e = self.q("--maiores", "2", "--em", self.data)
        self.assertEqual(code, 0)
        self.assertEqual([m["bytes"] for m in j["maiores"]], [9000, 7000])

    def test_extensoes(self):
        code, j, _e = self.q("--extensoes", "2", "--em", self.data)
        self.assertEqual(code, 0)
        self.assertEqual(j["extensoes"][0]["extensao"], ".zip")
        self.assertEqual(j["extensoes"][0]["arquivos"], 2)
        self.assertEqual(j["extensoes"][0]["bytes"], 9100)
        self.assertEqual(len(j["extensoes"]), 2)

    def test_buscar_order_limit_and_size(self):
        code, j, _e = self.q("--buscar", "*.jpg", "--em", self.data)
        self.assertEqual(code, 0)
        self.assertEqual(j["busca"]["total_encontrado"], 2)     # a.jpg e b.JPG
        self.assertEqual([r["bytes"] for r in j["busca"]["resultados"]], [5000, 3000])
        code, j, _e = self.q("--buscar", "*", "--em", self.data, "--limite", "2", "--ordenar", "nome")
        self.assertEqual(j["busca"]["exibidos"], 2)
        self.assertEqual(j["busca"]["total_encontrado"], 6)
        names = [r["nome"] for r in j["busca"]["resultados"]]
        self.assertEqual(names, sorted(names, key=str.lower))
        code, j, _e = self.q("--buscar", "*", "--em", self.data, "--tamanho", "> 4000")
        self.assertEqual(j["busca"]["total_encontrado"], 3)
        code, j, _e = self.q("--buscar", "*", "--em", self.data, "--tamanho", "banana")
        self.assertEqual(code, 2)
        self.assertFalse(j["ok"])

    def test_buscar_case_sensitive(self):
        code, j, _e = self.q("--buscar", "*.JPG", "--maiusculas", "--em", self.data)
        self.assertEqual(j["busca"]["total_encontrado"], 1)

    def test_status(self):
        code, j, _e = self.q("--status")
        self.assertEqual(code, 0)
        self.assertEqual(j["indice"]["arquivos"], 6)
        self.assertIn(os.path.normpath(self.data), j["indice"]["raizes"])

    def test_so_indice_without_data_exit_3(self):
        other = os.path.join(self.d, "outra")
        os.makedirs(other, exist_ok=True)
        code, j, _e = self.q("--espaco", other)
        self.assertEqual(code, 3)
        self.assertFalse(j["ok"])
        self.assertEqual(j["codigo"], 3)

    def test_missing_folder_exit_3(self):
        code, o, e = run_cli("--indice", self.idx, "--espaco", os.path.join(self.d, "nao_existe"))
        self.assertEqual(code, 3)
        self.assertIn("não encontrada", e)

    def test_treemap_file(self):
        dest = os.path.join(self.d, "t.html")
        code, j, _e = self.q("--espaco", self.data, "--treemap", dest, "--treemap-por", "quantidade")
        self.assertEqual(code, 0)
        self.assertEqual(j["treemap"]["por"], "quantidade")
        self.assertTrue(os.path.getsize(dest) > 1000)

    def test_text_mode_unchanged(self):
        code, o, _e = run_cli("--indice", self.idx, "--so-indice", "--espaco", self.data, "--top", "2")
        self.assertEqual(code, 0)
        self.assertIn("Espaço por pasta em:", o)
        self.assertIn("Total:", o)

    def test_json_stdout_is_pure(self):
        code, o, e = run_cli("--indice", self.idx, "--so-indice", "--json", "--espaco", self.data)
        self.assertEqual(code, 0)
        json.loads(o)          # não pode haver texto solto antes/depois do JSON
        self.assertTrue(o.isascii())


class TestGuiTreemap(unittest.TestCase):
    def test_toggle_and_redraw(self):
        if g.tk is None:
            self.skipTest("tkinter indisponível")
        try:
            root = g.tk.Tk()
        except g.tk.TclError as e:
            self.skipTest("sem display: %s" % e)
        base = tempfile.mkdtemp(prefix="rp_gui_")
        idx = g.Index(os.path.join(base, "idx.sqlite"))
        try:
            data = os.path.join(base, "dados")
            make_files(data, {"alfa/x.bin": 6000, "alfa/y.bin": 2000, "beta/z.bin": 1000})
            root.withdraw()
            app = g.App(root, idx)
            app.v_root.set(data)
            app._start()
            deadline = time.time() + 15
            while (app._running or app._rcount == 0) and time.time() < deadline:
                root.update()
                time.sleep(0.02)
            app._open_space()
            dlg = app._space_win
            deadline = time.time() + 10
            while not dlg._rows and time.time() < deadline:
                root.update()
                time.sleep(0.02)
            dlg.win.geometry("900x700")
            for _ in range(40):
                root.update()
                time.sleep(0.02)
            # o painel do treemap já vem visível, junto da tabela
            self.assertTrue(dlg._tm_on)
            self.assertTrue(dlg.canvas.winfo_ismapped() and dlg.tree.winfo_ismapped())
            names = {r["node"]["name"] for r in dlg._tm_rects}
            self.assertTrue({"alfa", "beta"} <= names)
            # seleção: bloco -> tabela e tabela -> bloco
            blk = [r for r in dlg._tm_rects if r["node"]["name"] == "beta"][0]

            class Ev:
                x = int(blk["x"] + blk["w"] / 2)
                y = int(blk["y"] + blk["h"] / 2)
            dlg._tm_click(Ev)
            sel = dlg.tree.selection()
            self.assertEqual(dlg._rdata[sel[0]]["name"], "beta")
            alfa_iid = [i for i, it in dlg._rdata.items() if it["name"] == "alfa"][0]
            dlg.tree.selection_set(alfa_iid)
            root.update()
            self.assertEqual(dlg._tm_sel_key[0], os.path.join(data, "alfa"))
            # passar o mouse mostra a dica flutuante
            dlg._tm_motion(Ev)
            self.assertTrue(dlg.canvas.find_withtag("tip"))
            # roda para cima entra na pasta sob o mouse
            dlg._tm_zoom(Ev, 1)
            deadline = time.time() + 5
            while dlg._cur_dir != os.path.join(data, "beta") and time.time() < deadline:
                root.update()
                time.sleep(0.02)
            self.assertEqual(dlg._cur_dir, os.path.join(data, "beta"))
            dlg._cycle_metric()
            for _ in range(10):
                root.update()
            self.assertEqual(dlg._tm_metric, "quantidade")
            dlg._toggle_treemap()                  # ocultar
            self.assertFalse(dlg._tm_on)
            self.assertEqual(dlg.b_tm.cget("text"), "Mostrar treemap")
            dlg._toggle_treemap()                  # mostrar de novo
            self.assertTrue(dlg._tm_on)
            dlg._close()
        finally:
            idx.close()
            root.destroy()
            dlg = app = root = None
            gc.collect()
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
