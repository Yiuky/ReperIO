# Linha de comando do ReperIO

Tudo que a janela faz com espaço, índice e busca também roda **sem janela**, para scripts, tarefas
agendadas e IAs. Só biblioteca padrão do Python (3.8+). A janela abre quando nenhuma ação é informada.

```text
python reperio.py [ação] [filtros] [saída] [índice]
python reperio.py --ajuda
```

## Ações

| Ação | O que faz |
|---|---|
| `--indexar PASTA` | Lê `PASTA` e grava no índice. Em pastas já indexadas só relê o que mudou (data da pasta). |
| `--espaco PASTA` | Espaço ocupado por subpasta (tamanho, `%`, arquivos). Usa o índice; **mapeia a pasta se o índice ainda não a cobre**. |
| `--maiores N` | Os `N` maiores arquivos de `--em PASTA`. |
| `--extensoes [N]` | Espaço por extensão (as `N` maiores, padrão 20). |
| `--buscar PADRÃO` | Arquivos por nome em `--em PASTA`: sem curingas é "contém"; com `*` e `?`, curingas. |
| `--treemap ARQ.html` | Grava o [treemap](#treemap) em uma página HTML autônoma. |
| `--status` | O que o índice conhece: pastas, arquivos, raízes, datas, tamanho do arquivo. |
| `--manifesto` | JSON com tudo que a CLI faz (argumentos, saídas, códigos). Pensado para IAs. |

Ações combinam: `--espaco D:\ --maiores 10 --treemap mapa.html --json` faz as três coisas de uma vez,
com uma só leitura do índice.

## Alvo e filtros

| Opção | Efeito |
|---|---|
| `--em PASTA` | Pasta-alvo de `--buscar`, `--maiores`, `--extensoes` e `--treemap` (padrão: a de `--espaco` ou `--indexar`). |
| `--ignorar LISTA` | Pula pastas: nomes, curingas ou subcaminhos (`_backup, node_modules, temp_*, AppData/Local/Temp`). Vale na varredura **e** nas consultas. |
| `--ext LISTA` | `--buscar`: extensões (`shp tif`). |
| `--tamanho FILTRO` | `--buscar`: `> 100 MB`, `< 10 KB`, `10MB..500MB`. |
| `--maiusculas` | `--buscar` diferencia maiúsculas de minúsculas. |
| `--limite N` | `--buscar`: máximo de resultados exibidos (padrão 100); o total encontrado é sempre contado. |
| `--ordenar` | `--buscar`: `tamanho` (padrão), `data` ou `nome`. |

## Saída

| Opção | Efeito |
|---|---|
| `--json` | **Um único objeto JSON no stdout** (ASCII puro). Mensagens e progresso vão para o stderr. |
| `--top N` | `--espaco`: itens por nível (padrão 30). |
| `--profundidade N` | Níveis de subpastas: `--espaco` (padrão 1) e `--treemap` (padrão 3). |
| `--treemap-por` | Métrica mostrada primeiro no HTML: `tamanho` ou `quantidade`. |
| `--exportar ARQ` | `--espaco`: tabela em `.xlsx`, `.csv` ou `.txt`. |
| `-q`, `--silencioso` | Sem mensagens de progresso. |

## Índice e execução

| Opção | Efeito |
|---|---|
| `--indice ARQ` | Arquivo SQLite do índice (padrão `%LOCALAPPDATA%\reperio\index.sqlite`). Pode ficar em um compartilhamento. |
| `--no-index` | Sem índice, tudo em memória; só `--espaco` e `--treemap`. |
| `--atualizar` | Relê no disco as pastas alteradas mesmo que o índice já cubra a pasta. |
| `--so-indice` | **Nunca varre o disco.** Sem dados no índice, termina com código 3. Garante respostas rápidas. |

## Códigos de saída

| Código | Significado |
|---:|---|
| 0 | Ok |
| 1 | Erro inesperado (o detalhe vai no JSON `erro` ou no stderr) |
| 2 | Uso incorreto dos argumentos (inclui argumento desconhecido: **nunca abre a janela por engano**) |
| 3 | Pasta inexistente, ou sem dados no índice com `--so-indice` |
| 130 | Interrompido com Ctrl+C; o que já foi lido fica no índice |

## Exemplos

```bash
# Onde está o espaço do disco D:? (mapeia na 1ª vez; depois responde do índice)
python reperio.py --espaco D:\ --top 20

# O mesmo para uma IA ou script: JSON, dois níveis
python reperio.py --espaco D:\ --json --profundidade 2 --top 15

# Indexar o C: sem entrar no OneDrive (cujos arquivos só-nuvem contam tamanho lógico)
python reperio.py --indexar C:\ --ignorar OneDrive

# Consultas instantâneas, sem tocar o disco
python reperio.py --maiores 30 --em C:\Users\eu --so-indice
python reperio.py --extensoes 15 --em D:\ --so-indice
python reperio.py --buscar "*.zip" --em D:\ --tamanho "> 1 GB" --json --so-indice

# Treemap
python reperio.py --espaco D:\ --treemap D:\mapa.html

# Indexação agendada (Agendador de Tarefas / cron), sem barulho
python reperio.py --indexar "\\servidor\dados" --indice "\\servidor\dados\_reperio.sqlite" -q
```

## Formato do JSON

Sempre um objeto com `reperio` (versão) e `ok`. Em erro: `{"ok": false, "codigo": N, "erro": "..."}`.

| Campo | Quando | Conteúdo |
|---|---|---|
| `pasta` | há pasta-alvo | Caminho normalizado consultado |
| `varredura` | sempre | `executada: false` se o índice bastou; senão `tempo_s`, `arquivos`, `pastas_lidas`, `pastas_conferidas`, `pastas_relidas`, `arquivos_por_s`, `falhas[]` (`pasta`, `erro`), `n_falhas`, `interrompido`, `indice` |
| `espaco` | `--espaco` | `total_bytes`, `total`, `total_arquivos`, `pastas_lidas`, `pastas_pendentes`, `completo`, `itens[]` |
| `espaco.itens[]` | | `nome`, `caminho`, `tipo` (`pasta` ou `arquivos_diretos`), `bytes`, `tamanho`, `arquivos`, `subpastas`, `bytes_diretos`, `arquivos_diretos`, `pct_pai`, `pct_raiz`, `filhos[]` (com `--profundidade` > 1) |
| `maiores[]` | `--maiores` | `caminho`, `bytes`, `tamanho`, `modificado` (ISO 8601) |
| `extensoes[]` | `--extensoes` | `extensao`, `arquivos`, `bytes`, `tamanho`, `pct` |
| `busca` | `--buscar` | `padrao`, `total_encontrado`, `bytes_total`, `exibidos`, `ordenado_por`, `resultados[]` (`caminho`, `nome`, `bytes`, `tamanho`, `modificado`) |
| `treemap` | `--treemap` | `arquivo`, `por`, `profundidade` |
| `indice` | `--status` | `arquivo`, `pastas`, `pastas_pendentes`, `arquivos`, `bytes`, `raizes[]`, `leitura_mais_antiga`, `leitura_mais_recente` |
| `desempenho` | sucesso | `tempo_total_s`, `pico_ram_mb` |

`bytes` é exato; `tamanho` é só para leitura humana (`1.50 GB`, base 1024).

## Treemap

Mapa de blocos em que **a área é proporcional ao tamanho ou à quantidade de arquivos**. Pastas viram
retângulos aninhados (algoritmo *squarified*: blocos o mais quadrados possível), com uma cor por pasta
de primeiro nível. Serve para achar em segundos "o que está comendo o disco".

- **Na janela (painel interativo, estilo SpaceSniffer):** em **Espaço por pasta...** o treemap fica em um
  painel **acima da tabela**, na mesma janela (a divisória é ajustável; **Ocultar treemap** esconde o
  painel e **Blocos por: Tamanho / Quantidade** troca a métrica). Mostra 3 níveis de subpastas aninhadas.
  - **Passar o mouse:** destaca o bloco e mostra uma dica com caminho, tamanho, arquivos e participação.
  - **Clique:** seleciona o bloco e marca a linha correspondente da tabela (e vice-versa: escolher uma
    linha da tabela contorna o bloco).
  - **Duplo clique** ou **roda do mouse para cima:** entra na pasta sob o mouse.
  - **Roda para baixo**, **botão direito** ou **Backspace:** sobe um nível.
- **Em arquivo:** `--treemap mapa.html` (CLI) ou **Exportar... → Treemap (página HTML)** na janela.
  Um único `.html`, sem dependências nem internet: abre em qualquer navegador, tem tema claro/escuro e
  alterna entre as duas métricas. Passe o mouse sobre um bloco para ver o caminho completo.
- **Blocos pequenos** (abaixo de 3 px) não são desenhados; cada pasta mostra no máximo 40 itens por
  tamanho e por quantidade, e o resto vira um bloco cinza `[outros N itens]`. Arquivos soltos numa pasta
  viram o bloco `[arquivos desta pasta]`.

## Limitações conhecidas

- **Arquivos do OneDrive só-nuvem** (e outros provedores de arquivos sob demanda) aparecem com o tamanho
  **lógico**, não o ocupado no disco. Use `--ignorar OneDrive` para medir o disco local de verdade.
- O tamanho é o do arquivo, não o espaço alocado em clusters; links simbólicos e *junctions* não são
  seguidos (evita ciclos) e hardlinks contam em duplicidade.
- `--espaco` e `--treemap` mostram só o que o índice já leu: veja `pastas_pendentes` e `completo`.
