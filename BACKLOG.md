# Roadmap do ReperIO

Ideias e próximos passos, em ordem de prioridade. O que já foi entregue está no
[CHANGELOG](CHANGELOG.md). Sugestões são bem-vindas: abra uma
[issue](https://github.com/Yiuky/ReperIO/issues/new/choose).

**Prioridade:** P1 = próximo · P2 = importante · P3 = quando der
**Esforço:** P = horas · M = ~1 dia · G = vários dias

| # | Pri. | Esf. | Item | Por quê |
|---|------|------|------|---------|
| 1 | P1 | M | **Cópia inteligente**: pular arquivos já existentes com o mesmo tamanho; retomar cópia interrompida | Cópias grandes pela rede caem com frequência |
| 2 | P2 | P | **Filtro por data de modificação** (ex.: modificados em 2024, últimos 30 dias) | Complementa o filtro por tamanho e a análise de espaço entregues na v2.6.0 |
| 3 | P2 | P | Tela para **gerenciar pastas problemáticas** (ver, remover, exportar para a TI) | Hoje a lista aparece ao fim de cada busca |
| 4 | P3 | P | Lembrar as **últimas pastas raiz** usadas | Conforto |
| 5 | P3 | M | Executável para **macOS** nas Releases | Hoje o macOS usa o código-fonte |
| 6 | P3 | M | Troca de conexão no **Linux** (montagens CIFS alternativas) | Hoje o Linux usa o modo de rodadas no fim |
| 7 | P3 | — | **Assinatura digital** do executável | Elimina o aviso do SmartScreen e reduz bloqueios de antivírus |

## Limitações conhecidas

- **Pastas que o servidor não consegue abrir não podem ser lidas por nenhum programa**, até que o
  servidor seja corrigido. O app as isola, lista com o motivo e tenta de novo periodicamente.
- **Arquivo modificado sem mudar a pasta:** editar um arquivo existente não altera a data da pasta,
  então o tamanho e a data desse arquivo no índice só são atualizados quando a pasta for relida.
- **Limite de 100.000 resultados por busca**: acima disso a lista do Tk fica lenta. Refine o padrão.
- **CSV em Windows em inglês:** o separador `;` (padrão em português) faz o Excel em inglês abrir
  tudo numa coluna. Use o `.xlsx`.
- **Leitura presa não pode ser interrompida:** a chamada do sistema só termina quando o servidor
  responde ou estoura o tempo. "Parar" encerra a busca na hora, mas a leitura presa segue em
  segundo plano até o Windows desistir.
