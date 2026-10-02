# AGENTS.md: guia para modelos de IA e desenvolvedores

Leia antes de alterar o ReperIO. O trabalho pendente está no [BACKLOG.md](BACKLOG.md); o histórico, no
[CHANGELOG.md](CHANGELOG.md).

## 1. O que é

Aplicativo desktop (Windows e Linux) para **buscar arquivos por nome/extensão** em pastas locais e
**servidores de arquivos de rede** (SMB/CIFS, DFS, unidades mapeadas), manter um **índice local**,
**exportar** resultados (Excel/CSV/TXT) e **copiar** em lote. Nome do produto: **ReperIO**, projeto
pessoal e independente de Joberth Firmino Gambati (não cite instituições como autoras ou donas).
Nome antigo: "GIS File Finder" (até a 2.4); a pasta de dados antiga `gis-file-finder` é migrada sozinha
para `reperio` (`_log_dir`).

## 2. Restrições que não se negociam

- **Roda em qualquer computador:** Python 3.8+ e **somente a biblioteca padrão** no aplicativo. Nada de
  `pip install` para o usuário. O PyInstaller entra só no build.
- **Arquivo único:** todo o aplicativo fica em `reperio.py`.
- **Português** em código, comentários, interface, log e documentação.
- **Sem dados internos** de organizações nos arquivos publicados (servidores, IPs, caminhos). Notas
  internas ficam em `notas-internas/`, que o `.gitignore` exclui.

## 3. Arquitetura (`reperio.py`, de cima para baixo)

| Seção | Responsabilidade |
|---|---|
| Log | `dlog()` grava em `%LOCALAPPDATA%\reperio\debug_execution.log`; **nunca** escreve no console (o QuickEdit do Windows congelava tudo) |
| Sistema de arquivos | `list_dir()` (Windows: `FindFirstFileExW` + `LARGE_FETCH`; Linux: `os.scandir`), `_touch()` registra progresso, `describe_error()` |
| Filtro | `make_matcher()`: "contém" ou curingas |
| `AdaptiveGate` | Vagas de leitura por conexão; timeout = conexão congestionada → 1 vaga + pausa |
| `Index` | SQLite (modo WAL), **uma** thread escritora; `db_enc/db_dec` tornam reversíveis nomes com surrogates (Samba antigo) |
| Canais | `resolve_channels()`: servidor real por trás de unidade/DFS + nomes alternativos = conexões SMB independentes |
| `SearchThread` | Busca em largura com workers; troca de conexão, vítimas refeitas na hora, quarentena, rodadas no fim |
| Cópia | `CopyManager`/`CopyWorker`, blocos de 1 MB, cancelável |
| Exportação | `export_xlsx/csv/txt` (xlsx escrito com `zipfile`) |
| `App` | Interface tkinter |

## 4. Regras da interface (não quebre)

1. Nenhum I/O de disco ou rede na thread da interface.
2. Nenhum `sleep()`, `update()` ou `update_idletasks()` na thread da interface.
3. Threads de trabalho **nunca** chamam o Tk (nem `root.after`): devolvem resultados por
   `queue.Queue`, lidos por `root.after` na thread principal.
4. Os ciclos de polling (`_poll_s`, `_poll_c`) sempre se reagendam, mesmo após exceção.

## 5. Regras de rede (aprendidas em servidor real)

- Uma pasta que o servidor não abre trava a **conexão** inteira (erro 121 após minutos); outras
  conexões seguem normais. Nem `CancelSynchronousIo` destrava.
- "Conexão travada" = **nenhuma** leitura nela recebeu dados recentemente (`_activity`), e não "leitura
  demorada": pastas grandes progridem.
- A conexão do usuário (`Channel.user`, a mesma do Explorer) **nunca** recebe leituras arriscadas
  quando existem alternativas.
- Pasta presa em 2 travamentos é a culpada: não refaça, mande para a quarentena (evita cascata).
- Ao testar contra um servidor real, use uma trava de segurança (encerrar se houver mais de 3 trocas de
  conexão em 3 min) e lembre que cada pasta-problema ocupa uma conexão por minutos.

## 6. Testes

`python -m unittest discover -s tests -v`: todos os cenários de rede são simulados (veja
`TestChannels`, `TestNoCascade`, `TestPoisonFolder`, `TestReviewFixes`). Toda correção vem com um teste
que reproduz o problema. Testes de interface liberam o Tk na thread principal (`gc.collect()`), senão o
Tcl aborta a suíte.

## 7. Versão e publicação

Atualize `__version__` (`reperio.py`), o `CHANGELOG.md` e o `CITATION.cff`; depois
`git tag vX.Y.Z && git push origin vX.Y.Z`. A Release é montada pelo GitHub Actions
(`.github/workflows/release.yml`).
