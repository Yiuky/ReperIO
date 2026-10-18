# Usando o ReperIO com uma IA (agentes, MCP, scripts)

O ReperIO responde às perguntas mais comuns de "limpeza de disco" e "onde está o arquivo X" com
**uma linha de comando e uma saída JSON estável**. Um agente não precisa de interface gráfica, de
biblioteca extra nem de permissão de administrador.

> Descoberta automática: `python reperio.py --manifesto` imprime em JSON todos os argumentos, os campos
> de saída, os códigos de saída e exemplos. Comece por ele. Referência completa em [CLI.md](CLI.md).

## Regras de ouro para agentes

1. **Sempre `--json`.** O stdout é *um* objeto JSON em ASCII; progresso e avisos vão para o stderr.
   Leia `ok` antes de tudo. Em erro: `{"ok": false, "codigo": N, "erro": "..."}`.
2. **Consulte com `--so-indice`** depois da primeira leitura: responde em milissegundos e **nunca**
   dispara uma varredura longa por engano (sem dados: código 3).
3. **Indexe uma vez, consulte muitas.** `--indexar PASTA` custa minutos em discos grandes; `--espaco`,
   `--maiores`, `--extensoes`, `--buscar` e `--treemap` leem do índice SQLite.
4. **Meça o disco local com `--ignorar OneDrive`.** Arquivos só-nuvem contam o tamanho lógico.
5. **Confira `completo`/`pastas_pendentes`** em `espaco` e `varredura.falhas`: dizem se o número é
   total ou parcial (pastas sem permissão aparecem lá, não derrubam a execução).
6. **O ReperIO só lê.** Nenhuma ação da CLI apaga, move ou altera arquivos. Quem decide remover é
   a pessoa, depois de ver o relatório; mostre os caminhos exatos (`caminho`) antes de qualquer remoção.
7. Argumentos desconhecidos dão código 2 (a janela nunca abre por engano); `Ctrl+C` dá 130 e preserva o
   que já foi lido.

## Receitas

| Pergunta | Comando |
|---|---|
| Quanto sobrou e o que ocupa o disco D:? | `python reperio.py --espaco D:\ --json --profundidade 2 --top 15` |
| Quais são os 20 maiores arquivos do perfil? | `python reperio.py --maiores 20 --em C:\Users\eu --json --so-indice --ignorar OneDrive` |
| Que tipo de arquivo ocupa mais espaço? | `python reperio.py --extensoes 15 --em D:\ --json --so-indice` |
| Onde estão os `.iso` com mais de 1 GB? | `python reperio.py --buscar "*.iso" --em D:\ --tamanho "> 1 GB" --json --so-indice` |
| O índice está atual? | `python reperio.py --status --json` (veja `leitura_mais_recente`) e `--atualizar` para revarrer só o que mudou |
| Quero um mapa visual para a pessoa | `python reperio.py --espaco D:\ --treemap D:\mapa.html --json` e abra o `.html` |
| Atualizar depois de limpar | `python reperio.py --indexar D:\ --json -q` (relê só pastas alteradas) |

## Fluxo recomendado para "liberar espaço"

1. `--status --json`: há índice? De quando?
2. `--indexar <disco> --ignorar OneDrive --json -q` (ou `--espaco` na pasta, que mapeia se faltar).
3. `--espaco <disco> --json --profundidade 2` para achar as pastas gordas; `--extensoes` e `--maiores`
   para entender o *quê*; `--treemap` para a pessoa ver.
4. Propor a lista de candidatos **com caminho, tamanho e motivo**; esperar a decisão.
5. Depois de remover (feito pela pessoa ou com autorização explícita), reindexar com `--indexar` e
   reportar o ganho (`espaco.total_bytes` antes e depois).

## Esquema da resposta (resumo)

```jsonc
{
  "reperio": "2.7.0", "ok": true, "pasta": "D:\\",
  "varredura": { "executada": true, "tempo_s": 41.2, "arquivos": 300000, "pastas_lidas": 52000,
                 "arquivos_por_s": 7280.4, "n_falhas": 0, "falhas": [], "interrompido": false },
  "espaco": {
    "total_bytes": 152000000000, "total": "141.57 GB", "total_arquivos": 300000,
    "pastas_pendentes": 0, "completo": true,
    "itens": [ { "nome": "Projetos", "caminho": "D:\\Projetos", "tipo": "pasta",
                 "bytes": 90000000000, "tamanho": "83.82 GB", "arquivos": 12000, "subpastas": 40,
                 "pct_pai": 59.2, "pct_raiz": 59.2, "filhos": [ /* com --profundidade 2 */ ] } ]
  },
  "desempenho": { "tempo_total_s": 41.9, "pico_ram_mb": 188.1 }
}
```

Campos de cada ação: veja a tabela em [CLI.md](CLI.md#formato-do-json). Todos os nomes de campo são
ASCII em português; datas em ISO 8601 (`2026-10-17T16:52:50`, hora local).

## Integração como ferramenta (exemplo)

Qualquer agente que execute comandos pode usar o ReperIO. Em Python:

```python
import json, subprocess, sys

def reperio(*args):
    p = subprocess.run([sys.executable, "reperio.py", *args, "--json", "-q"],
                       capture_output=True, text=True, encoding="utf-8")
    data = json.loads(p.stdout)
    if not data["ok"]:
        raise RuntimeError("%s (código %s)" % (data["erro"], data["codigo"]))
    return data

top = reperio("--espaco", "D:\\", "--profundidade", "2", "--top", "10")["espaco"]["itens"]
for it in top:
    print(it["tamanho"], it["caminho"])
```

Para registrar em um servidor MCP ou numa *skill*, basta expor esse invólucro com os parâmetros
`pasta`, `acao` (`espaco`, `maiores`, `extensoes`, `buscar`, `treemap`) e `so_indice`. A autodescrição
de `--manifesto` já traz os nomes e as descrições dos argumentos para gerar o esquema da ferramenta.

## Desempenho esperado

Veja [BENCHMARK.md](BENCHMARK.md): números medidos pela própria CLI em discos reais (varredura a frio,
reverificação a quente e cada consulta ao índice).
