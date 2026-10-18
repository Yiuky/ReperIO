# -*- coding: utf-8 -*-
"""Testes do gerador de notas da Release (tools/release_notes.py)."""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import release_notes as rn  # noqa: E402

SAMPLE = """# Histórico

## [Não lançado]

### Adicionado
- algo futuro

## [2.8.0] — 2026-11-01

### Adicionado
- **Novidade** com `código` e acentuação: ação, é, ñ

### Corrigido
- um conserto

## [2.7.1] — 2026-10-18

### Corrigido
- outro conserto
"""


class TestReleaseNotes(unittest.TestCase):
    def test_section_is_isolated(self):
        s = rn.changelog_section(SAMPLE, "2.8.0")
        self.assertIn("**Novidade**", s)
        self.assertIn("um conserto", s)
        self.assertNotIn("outro conserto", s)
        self.assertNotIn("algo futuro", s)

    def test_last_section_and_missing(self):
        self.assertIn("outro conserto", rn.changelog_section(SAMPLE, "2.7.1"))
        self.assertIsNone(rn.changelog_section(SAMPLE, "9.9.9"))
        self.assertIsNone(rn.changelog_section(SAMPLE, "2.8"))     # não casa prefixo

    def test_notes_layout(self):
        n = rn.build_notes("2.8.0", SAMPLE)
        self.assertIn("ReperIO-2.8.0-windows-x64.zip", n)
        self.assertIn("ReperIO-2.8.0-linux-x64.zip", n)
        self.assertIn("SHA256SUMS.txt", n)
        self.assertIn("## ✨ Novidades da 2.8.0", n)
        self.assertIn("#### Adicionado", n)          # sub-títulos rebaixados
        self.assertNotIn("\n### ", n)
        self.assertIn("ação, é, ñ", n)

    def test_missing_version_raises(self):
        with self.assertRaises(ValueError):
            rn.build_notes("9.9.9", SAMPLE)

    def test_cli_for_real_changelog(self):
        ver = None
        with open(os.path.join(ROOT, "reperio.py"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    ver = line.split('"')[1]
                    break
        p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "release_notes.py"), ver],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(p.returncode, 0, p.stderr.decode("utf-8", "replace"))
        out = p.stdout.decode("utf-8")
        self.assertIn("ReperIO-%s-windows-x64.zip" % ver, out)
        self.assertIn("## ✨ Novidades da %s" % ver, out)

    def test_cli_usage_errors(self):
        script = os.path.join(ROOT, "tools", "release_notes.py")
        self.assertEqual(subprocess.run([sys.executable, script], stderr=subprocess.DEVNULL).returncode, 2)
        self.assertEqual(subprocess.run([sys.executable, script, "9.9.9"],
                                        stderr=subprocess.DEVNULL).returncode, 1)


if __name__ == "__main__":
    unittest.main()
