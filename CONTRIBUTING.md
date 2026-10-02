# Como contribuir

Obrigado pelo interesse! Relatos de erro, ideias e código são bem-vindos.

## Relatar um problema ou sugerir uma ideia

Abra uma [issue](https://github.com/Yiuky/ReperIO/issues/new/choose) usando um dos modelos. Para erros, ajuda muito anexar:

- versão (aparece no título da janela) e sistema operacional;
- o que você fez, o que esperava e o que aconteceu;
- o trecho relevante do log (`%LOCALAPPDATA%\reperio\debug_execution.log` no Windows,
  `~/.local/state/reperio/debug_execution.log` no Linux).

> Antes de anexar um log, **troque nomes de servidores, IPs e caminhos internos** da sua
> organização por exemplos genéricos.

## Princípios do projeto

1. **Roda em qualquer computador.** Somente a biblioteca padrão do Python 3.8+. Nada de
   dependências externas no aplicativo (o PyInstaller é usado apenas para gerar o executável).
2. **Arquivo único.** O aplicativo inteiro fica em `reperio.py`, fácil de copiar e auditar.
3. **A interface nunca congela.** Nenhum I/O de disco ou rede na thread da interface; toda
   comunicação entre threads usa `queue.Queue` + `root.after`.
4. **Respeito ao servidor e ao usuário.** Não aumentar a carga sobre um servidor que já está lento,
   e nunca fazer leituras arriscadas pela conexão que o usuário usa no Explorer.
5. **Medir antes de otimizar.** Mudanças de desempenho ou de rede devem vir com números (o log
   ajuda: `[PROGRESSO]`, `[PASTA LENTA]`, `[CANAL]`).

## Ambiente de desenvolvimento

```bash
git clone https://github.com/Yiuky/ReperIO.git
cd ReperIO
python reperio.py                   # roda o app (Python 3.8+ com tkinter)
python -m unittest discover -s tests -v     # testes
```

No Linux, o teste de interface precisa de display (`xvfb-run -a python -m unittest ...`); sem
display ele é pulado automaticamente.

## Enviando um pull request

1. Crie um branch a partir de `main` (`git checkout -b minha-melhoria`).
2. Faça a mudança com **testes** em `tests/` (os cenários de rede são simulados: veja
   `TestChannels` e `TestPoisonFolder`).
3. Rode a suíte inteira: ela deve passar no Windows e no Linux (o CI confere os dois).
4. Atualize o [CHANGELOG](CHANGELOG.md) (seção da próxima versão) e o README, se a mudança for
   visível para o usuário.
5. Abra o pull request descrevendo **o quê** e **por quê**.

## Estilo

- Código, comentários e mensagens em **português**, seguindo o estilo existente.
- Indentação de 4 espaços; linhas de até ~110 colunas (ver `.editorconfig`).
- Comentários explicam o **porquê**, sobretudo quando a decisão veio de uma medição real.
