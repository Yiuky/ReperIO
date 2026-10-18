# Benchmark do ReperIO

Gerado por `tools/benchmark.py` em 2026-10-17 19:31.

- Máquina: Windows-11-10.0.26200-SP0
- Python 3.13.14 · ReperIO v2.7.0 · 12 CPUs lógicas

## C:\

Disco: 299.1 GB no total, 168.4 GB usados, 130.8 GB livres.
Pastas ignoradas: `OneDrive`.
Indexado: **869.367 arquivos, 164.91 GB**; índice SQLite de 185.1 MB (há pastas sem leitura).

| Etapa | Tempo (s) | Detalhe | Pico de RAM (MB) |
|---|---:|---|---:|
| Varredura a frio (índice vazio) | 85.4 | 869.363 arq. · 263636 pastas · 11182.2 arq./s; 531 pasta(s) não lidas | 410.8 |
| Reverificação a quente (índice pronto) | 49.73 | 264167 pastas conferidas · 563 relidas | 365.5 |
| `--espaco` (2 níveis) | 7.42 | — | 361.7 |
| `--maiores 20` | 8.8 | — | 361.7 |
| `--extensoes 20` | 9.81 | — | 361.7 |
| `--buscar *.zip` | 9.38 | 116 encontrados | 361.8 |
| `--treemap` (HTML) | 7.21 | HTML 229.5 KB | 361.7 |

## D:\

Disco: 176.8 GB no total, 141.3 GB usados, 35.5 GB livres.
Indexado: **19.600 arquivos, 141.18 GB**; índice SQLite de 1.0 MB (há pastas sem leitura).

| Etapa | Tempo (s) | Detalhe | Pico de RAM (MB) |
|---|---:|---|---:|
| Varredura a frio (índice vazio) | 0.76 | 19.600 arq. · 91 pastas · 35455.9 arq./s; 1 pasta(s) não lidas | 47.5 |
| Reverificação a quente (índice pronto) | 0.96 | 92 pastas conferidas · 1 relidas | 44.2 |
| `--espaco` (2 níveis) | 0.16 | — | 41.9 |
| `--maiores 20` | 0.18 | — | 42.0 |
| `--extensoes 20` | 0.2 | — | 42.4 |
| `--buscar *.zip` | 0.2 | 2 encontrados | 41.9 |
| `--treemap` (HTML) | 0.19 | HTML 18.9 KB | 42.0 |

## %USERPROFILE%\OneDrive

Disco: 299.1 GB no total, 168.4 GB usados, 130.8 GB livres.
Indexado: **182.073 arquivos, 653.26 GB**; índice SQLite de 15.6 MB.

| Etapa | Tempo (s) | Detalhe | Pico de RAM (MB) |
|---|---:|---|---:|
| Varredura a frio (índice vazio) | 6.92 | 182.073 arq. · 14698 pastas · 29096.6 arq./s | 84.6 |
| Reverificação a quente (índice pronto) | 5.37 | 14698 pastas conferidas · 0 relidas | 98.9 |
| `--espaco` (2 níveis) | 0.65 | — | 60.5 |
| `--maiores 20` | 0.67 | — | 60.9 |
| `--extensoes 20` | 0.9 | — | 62.8 |
| `--buscar *.zip` | 1.07 | 148 encontrados | 60.8 |
| `--treemap` (HTML) | 0.68 | HTML 125.2 KB | 61.5 |

Tempo = relógio de parede do processo inteiro (inclui iniciar o Python). O cache do sistema operacional pode estar aquecido, então a varredura "a frio" mede o ReperIO, não o disco puro.

## Leitura dos resultados

- **Pastas "não lidas"** são acesso negado a pastas do sistema (`System Volume Information`, `$Recycle.Bin`
  de outros usuários, `PerfLogs`) quando a CLI roda sem administrador. Aparecem em `varredura.falhas` e não
  afetam o restante; o total inclui apenas o que o usuário pode ler.
- **D:** poucos arquivos grandes (19,6 mil arquivos, 141 GB): o custo é por pasta/arquivo, não por byte.
- **Consultas em C: levam 7 a 10 s** com 869 mil arquivos (a de `D:` leva 0,2 s). A causa provável é a
  agregação em Python linha a linha (não medida em separado); é o ponto a otimizar (ver BACKLOG).
- A reverificação "a quente" de C: (50 s) confere a data de cada uma das 264 mil pastas no disco; é bem mais
  barata que a varredura a frio e só relê as pastas alteradas (563).
- A pasta OneDrive soma 653 GB lógicos em 182 mil arquivos, mas esse tamanho é lógico (arquivos só-nuvem não ocupam o disco local): por isso o
  `C:` foi medido com `--ignorar OneDrive`.
