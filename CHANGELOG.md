# Histórico de mudanças do ReperIO

Todas as mudanças relevantes do projeto. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões seguem
[SemVer](https://semver.org/lang/pt-BR/). Próximos passos ficam no [roadmap](BACKLOG.md).

## [Não lançado]

### Adicionado
- `tools/smoke_exe.py`: teste de fumaça do **executável** pela CLI (31 verificações no Windows, 28 no
  Linux: `--version`, `--ajuda`, argumentos inválidos, `--manifesto`, indexar, espaço, maiores, extensões,
  busca, status, treemap HTML, exportações, códigos de saída, nomes com acentos e ideogramas, `--no-index`
  e, no Windows com `--gui`, abrir e fechar a janela). A Release agora roda esse teste no binário
  recém-compilado, em Windows e Linux, **antes de publicar**.
- `tools/release_notes.py`: o texto da Release sai da seção da versão no CHANGELOG (tabela de download,
  como abrir, SHA-256 e novidades), no padrão da v2.6.0; as notas automáticas de PRs continuam anexadas.
  A Release **falha** se a versão não tiver seção no CHANGELOG.

## [2.7.1] — 2026-10-18

### Corrigido
- **Botões que sumiam ao redimensionar:** na janela *Espaço por pasta* os botões da direita ("Abrir no
  sistema", "Usar como Pasta Raiz", "Ocultar treemap") desapareciam abaixo de ~1220 px de largura, e na
  janela principal "Apagar índice" ficava cortado no tamanho mínimo. A barra de botões da janela de espaço
  agora tem **duas linhas** e o **tamanho mínimo das duas janelas é calculado pelo conteúdo** (fonte e
  escala do sistema), nunca passando da tela.
- Barras de progresso paradas pareciam "meio cheias": agora só aparecem enquanto trabalham.

### Alterado
- Janela principal abre mais alta (mais espaço para a lista de resultados); botão renomeado para
  **Espaço e treemap...**; a métrica do treemap virou **Blocos por: Tamanho / Quantidade**.

### Adicionado
- Teste automático de layout (`TestResponsiveLayout`): reduz e amplia as duas janelas e confere que nenhum
  botão fica escondido, cortado ou fora da janela.
- `tools/screenshots.py`: gera as imagens do README a partir de um acervo **fictício** gravado direto no
  índice (nada do computador de quem roda aparece).
- README reescrito com imagens (busca, treemap por tamanho e por quantidade, HTML exportado, tamanho
  mínimo das janelas, CLI em texto e JSON).

## [2.7.0] — 2026-10-17

### Adicionado
- **Treemap por tamanho ou por quantidade de arquivos** (opcional):
  - Em **Espaço por pasta...**, painel interativo **acima da tabela, na mesma janela** (estilo
    SpaceSniffer; **Ocultar treemap** e **Por: tamanho/quantidade**). Passar o mouse destaca o bloco e
    mostra uma dica flutuante; clique seleciona e sincroniza com a tabela (nos dois sentidos); duplo
    clique ou roda do mouse para cima entra na pasta; roda para baixo, botão direito ou Backspace sobe.
    Desenha só dados já em memória, sem I/O na interface.
  - **Exportação para HTML autônomo** (`Exportar... → Treemap`, ou `--treemap ARQ.html`): SVG com
    dicas, alternância entre as duas métricas, tema claro/escuro e tabela dos maiores itens.
  - Algoritmo *squarified* (`squarify`, `space_tree`, `treemap_layout`), testado quanto a proporção,
    limites e sobreposição.
- **CLI para pessoas, scripts e IAs** (`docs/CLI.md`, `docs/IA.md`):
  - Novas ações: `--maiores N`, `--extensoes [N]`, `--buscar PADRÃO` (com `--ext`, `--tamanho`,
    `--ordenar`, `--limite`, `--maiusculas`), `--treemap`, `--status` e `--manifesto`.
  - **`--json`**: um objeto JSON em ASCII no stdout (mensagens vão para o stderr), com estatísticas da
    varredura (tempo, arquivos/s, pastas lidas, falhas com o motivo) e do processo (pico de RAM).
  - **`--so-indice`** (nunca varre o disco), `--em PASTA`, `--profundidade`, `--ignorar` em todas as
    ações, `--silencioso`, `--sem-indice`, `--ajuda`.
  - **Códigos de saída fixos** (0 ok, 1 erro, 2 uso, 3 pasta/índice ausente, 130 Ctrl+C).
  - `--manifesto`: descrição da CLI em JSON (argumentos, campos de saída, códigos, exemplos).
- `tools/benchmark.py` e `docs/BENCHMARK.md`: varredura a frio, reverificação a quente e consultas,
  medidas pela própria CLI nos discos reais.
- Consultas novas no índice: `Index.largest_files`, `Index.extension_summary`, `Index.stats`.

### Corrigido
- **`--ajuda`/`--help` abria a janela** e argumentos desconhecidos (ou com erro de digitação, como
  `--espacoo`) também: agora são erro de uso (código 2) e a janela nunca abre por engano.
- A CLI **descartava em silêncio as pastas que não conseguiu ler** (sem permissão, servidor caiu);
  agora aparecem em `varredura.falhas` e as pastas sem leitura em `pastas_pendentes`/`completo`.
- A CLI **caía com `UnicodeEncodeError`** ao imprimir nomes de arquivo fora da codificação do console
  (cp1252/cp850); agora usa substituição segura.
- A CLI **sempre saía com código 0**, mesmo com pasta inexistente ou raiz inacessível; agora há códigos
  de saída distintos (3 = pasta inexistente ou sem dados no índice).

## [2.6.0] — 2026-10-17

### Adicionado
- **Análise de espaço por pasta (`Espaço por pasta...` e `--espaco`):**
  - Nova janela interativa **Espaço por pasta...** que agrega o tamanho recursivo, percentual do pai,
    quantidade total de arquivos e espaço na própria pasta para todas as subpastas sob a raiz,
    aproveitando o índice SQLite local (em milissegundos) ou os resultados atuais.
  - **Navegação drill-down:** duplo clique em qualquer subpasta entra nela para inspecionar os
    maiores consumidores de espaço nível a nível; botão **⬆ Pasta acima** para subir.
  - **Mapeamento com pausa e retomada:** botão **Mapear pasta agora** varre pastas ainda não
    indexadas em segundo plano atualizando os totais em tempo real; clicar em **Parar** pausa na
    hora e preserva no índice tudo o que já foi lido, continuando de onde parou na próxima vez.
  - **Exportação do resumo de espaço** para **Excel (.xlsx)**, **CSV** e **TXT**.
- **Filtro por tamanho (`Tamanho:`):** aceita mínimo (`> 100 MB`, `1,5 GB`), máximo (`< 10 KB`) ou
  faixa (`10MB..500MB`, `10 MB - 500 MB`). Mesmo com filtro de tamanho ativo, a varredura grava todos
  os arquivos no índice para não prejudicar buscas futuras nem o cálculo de espaço por pasta.
- **Exclusão de pastas (`Ignorar pastas:`):** permite pular árvores inteiras por nome ou curinga
  (ex.: `MOSAICOS, _backup, node_modules, .git, temp_*`), tanto na varredura ao vivo quanto nas
  consultas ao índice.
- **Duplo clique em um resultado** abre a pasta de origem no gerenciador de arquivos do sistema já
  destacando o arquivo (`explorer /select` no Windows, `open -R` no macOS, `xdg-open` no Linux).
- **Soma de tamanho nos resultados:** o contador mostra o volume total encontrado e o volume
  selecionado (ex.: `1.240 encontrados (48.20 GB)  |  12 selecionados (3.10 GB)`).
- **Modo de linha de comando (sem janela) e índice customizável:**
  - `--indexar <pasta>` indexa em modo headless (ideal para Agendador de Tarefas / `cron`).
  - `--espaco <pasta>` (com `--top <N>` e `--exportar <arquivo.xlsx|.csv|.txt>`) exibe e exporta os
    maiores consumidores de espaço direto no terminal.
  - `--indice <caminho.sqlite>` permite escolher o arquivo de índice (inclusive em pasta de rede).
  - `--ignorar <pastas>` e `--atualizar` para controlar exclusões e atualização via CLI.

### Corrigido
- Fechamento explícito de arquivos em `TestExport` (`tests/test_core.py`), eliminando `ResourceWarning`
  na suíte de testes.
- 68 testes automatizados (7 novos cobrindo filtros de tamanho, exclusão de pastas, espaço por pasta,
  exportação de espaço, CLI e diálogo gráfico).

## [2.5.0] — 2026-10-02

### Alterado
- **Novo nome: ReperIO**, do latim *reperire* ("achar, descobrir"), raiz de *repertório*. Antes se
  chamava "GIS File Finder & Copier".
  - Arquivo `reperio.py`, executável `ReperIO.exe` / `ReperIO`, logo e ícone próprios.
  - A pasta de dados passa a ser `reperio`. A antiga `gis-file-finder` (índice e log) é **migrada
    automaticamente** na primeira execução.
  - O lançador aceita `REPERIO_PYTHON` (e ainda `GFF_PYTHON`).
- Mensagens de erro com a **causa legível** antes do texto técnico (ex.: "acesso negado (sem
  permissão nesta pasta)", "o servidor não respondeu a tempo (timeout)"), na lista de pastas não
  lidas e nos erros de cópia.

### Corrigido (revisão de código)
- **Nome de arquivo com caractere inválido** (comum em servidores Samba antigos) **derrubava a thread
  que grava o índice**. Daí em diante nada mais era indexado, sem aviso, e cada busca esperava 60 s.
  - Agora esses nomes são guardados de forma reversível: o caminho original continua servindo para
    copiar e exportar.
  - Qualquer erro numa gravação é registrado sem derrubar a thread.
- **Dois cliques rápidos em "Iniciar busca"** deixavam a primeira busca órfã, rodando escondida e
  carregando o servidor.
- **"Verificar alterações"** não tirava da lista os arquivos de uma **subpasta apagada** no servidor
  (o índice era corrigido, mas a tela não).
- **Data de arquivo inválida** (ex.: ano 30828) derrubava a exportação inteira. Agora a célula de data
  fica vazia e o resto é exportado.
- Pasta apagada ou renomeada **durante** a busca era contada como "não lida". Agora só sai da lista.
- O aviso "Índice apagado" aparecia por tempo fixo (1,5 s), antes de a limpeza terminar. Agora aparece
  ao concluir, ou mostra o erro.
- Os ciclos de atualização da interface não param mais se ocorrer um erro inesperado; antes a janela
  podia ficar "buscando" para sempre.
- Nomes que o Tk não consegue exibir aparecem com caractere de substituição, em vez de travar a lista.

### Segurança
- **Injeção de fórmulas no CSV:** campos que começam com `=`, `+`, `-`, `@`, tab ou retorno recebem um
  apóstrofo, para que o Excel não os interprete como fórmula (recomendação OWASP). O `.xlsx` já
  gravava tudo como texto.

### Projeto
- Repositório no padrão dos projetos do autor: `CITATION.cff`, `CODE_OF_CONDUCT.md`, `AGENTS.md`
  (guia para IA e desenvolvedores), botão Sponsor e README com resumo em inglês.
- 61 testes automatizados (8 novos, um para cada correção desta versão).

## [2.4.0] — 2026-10-01

### Adicionado
- **Exportar resultados** (botão *Exportar...*): todos ou só os selecionados, na ordem da lista.
  - **Excel (.xlsx)**, gerado sem Excel e sem bibliotecas extras. Tem cabeçalho congelado,
    filtro, tamanho como número e data de modificação como data real. Validado no Microsoft
    Excel, sem aviso de reparo.
  - **CSV** com `;` e UTF-8 com BOM, que abre direto no Excel em português, com acentos.
  - **TXT** com um caminho completo por linha.
  - A gravação acontece fora da interface, porque o destino pode ser uma pasta de rede, e no
    fim o app oferece abrir o arquivo.
- Projeto preparado para publicação: README completo com captura de tela, guia de
  contribuição, política de segurança, modelos de issue e pull request, `.editorconfig` e somas
  SHA-256 nas Releases.
- `tools/screenshot.py`: regenera a imagem do README com dados de demonstração.

### Alterado
- Os testes automáticos gravam num log próprio, e não no log do usuário.

## [2.3.0] — 2026-10-01

### Adicionado
- **Várias conexões independentes com o servidor.** O app descobre o servidor real por trás da
  unidade mapeada e do DFS e testa nomes alternativos do mesmo servidor: nome completo, nome
  completo com ponto final e IP. Para o Windows, cada nome é uma conexão SMB separada.
  - Medido em servidor de produção: uma pasta que o servidor não consegue abrir congestiona a
    conexão por onde foi pedida durante minutos, enquanto as outras conexões seguem normais.
- **Troca de conexão na hora:** se nenhuma leitura de uma conexão recebe dados por alguns
  segundos, a busca passa para outra conexão e **refaz imediatamente** as leituras que ficaram
  presas. O resultado da leitura presa é descartado quando ela voltar.
- **Detecção por progresso:** cada leitura registra a última atividade (lote recebido). Uma pasta
  grande que continua recebendo dados não é confundida com uma pasta presa.
- **Quarentena:** a pasta culpada é lida em segundo plano por uma conexão separada (até 2), sem
  atrasar a busca. Se a leitura funcionar, a pasta e as subpastas entram nos resultados.
- **Pastas problemáticas no índice:** as que falham por todas as conexões são registradas e
  tentadas de novo automaticamente a cada 12 h, ou já, com a opção *Tentar de novo as pastas
  problemáticas agora*. Quando voltam a funcionar, saem da lista.
- Aviso com a lista de pastas não lidas e o diagnóstico, para encaminhar à TI.
- Log: marcas `[CANAL]`, `[QUARENTENA]` e `[REFEITA]`.

### Corrigido
- **Cascata:** a pasta culpada podia ser refeita na conexão nova e travá-la também. Agora a pasta
  que esteve presa em dois travamentos não é refeita de novo.
- **A conexão da unidade mapeada (a mesma do Explorer) nunca é usada** pela busca quando há
  alternativas, para que a navegação do usuário não seja afetada.
- A quarentena não disputa a conexão principal.
- Leituras que esperavam vaga numa conexão que travou passam a seguir pela conexão nova.

### Resultado medido (árvore com 3.246 pastas e uma pasta ilegível no servidor)
| Versão | Resultado |
|---|---|
| 2.1.0 | 36 pastas em 28 min (travada) |
| 2.2.0 | 2.974 pastas; resultados principais em 13,5 min |
| **2.3.0** | **3.246 pastas; resultados principais em ~1 min**; só a pasta ilegível ficou de fora, com aviso |
| 2ª busca | < 1 s, direto do índice |

## [2.2.0] — 2026-10-01

### Adicionado
- **Falha ou lentidão não param a busca:** pastas com falha de rede vão para o fim da fila e são
  tentadas de novo em rodadas, uma por vez.
- **Linha de avisos** na base da janela: pastas lentas, adiadas e não lidas; um clique mostra a
  lista e o motivo.
- **Atualização incremental do índice** (*Verificar alterações no servidor*): confere a data de
  cada pasta direto no servidor e relê só as que mudaram. Arquivos apagados saem da lista.

### Alterado
- Um timeout passa a significar sessão congestionada: as leituras simultâneas caem para 1 e
  pausam por 20 s antes de retomar.

### Corrigido
- Nova busca iniciada durante outra podia pular subpastas.
- A data de subpastas vinda da listagem da pasta-mãe pode estar atrasada no NTFS/SMB; a
  verificação passa a consultar a própria pasta.

## [2.1.0] — 2026-10-01

### Adicionado
- **Índice local (SQLite)** alimentado por toda busca: buscas repetidas em segundos, retomada de
  buscas interrompidas e troca de padrão no meio da busca sem perder o que foi lido.
- Registro `[PASTA LENTA]` no log.

### Alterado
- **Listagem ~3× mais rápida em pastas grandes no Windows** (`FindFirstFileExW` com
  `LARGE_FETCH`, sem nomes 8.3). Medido numa pasta de rede com 65 mil arquivos: 114,8 s → 34,8 s.
- Até 8 leituras simultâneas, com controle adaptativo.

## [2.0.0] — 2026-10-01

### Adicionado
- Migração para **Python 3.8+**, com um único código para **Windows e Linux**.
- **Executável autônomo** (PyInstaller) para máquinas sem Python.
- Lançadores `iniciar.bat` / `iniciar.sh`: usam o Python 3 + tkinter da máquina, senão o
  executável.
- Testes automatizados e CI no GitHub Actions; publicação automática de executáveis nas Releases.

### Corrigido (herdado da versão 1.x)
- Congelamento geral ao clicar na janela do console (QuickEdit bloqueava o log).
- Janela de console aberta atrás do programa.
- Cópia que nunca terminava (as threads de cópia encerravam com a fila vazia).
- Pasta inacessível virava um "arquivo" sem nome (handle inválido não detectado no 32 bits).
- "Parar" podia descartar os últimos resultados.
- Arquivos de mesmo nome se sobrescreviam na cópia em modo Plana.
- Cópia de arquivos grandes não podia ser cancelada no meio.
- Ciclos infinitos por junctions/symlinks.
- Falta de limite de resultados na lista.

## [1.x] — versão original

Utilitário em Python 2.7 para o ArcGIS Desktop 10.x (Tkinter).

[2.5.0]: https://github.com/Yiuky/ReperIO/releases/tag/v2.5.0
[2.4.0]: https://github.com/Yiuky/ReperIO/releases/tag/v2.4.0
[2.3.0]: https://github.com/Yiuky/ReperIO/releases/tag/v2.3.0
[2.2.0]: https://github.com/Yiuky/ReperIO/releases/tag/v2.2.0
[2.1.0]: https://github.com/Yiuky/ReperIO/releases/tag/v2.1.0
[2.0.0]: https://github.com/Yiuky/ReperIO/releases/tag/v2.0.0
