# Roadmap do ReperIO

Ideias e próximos passos, em ordem de prioridade. O que já foi entregue está no
[CHANGELOG](CHANGELOG.md). Sugestões são bem-vindas: abra uma
[issue](https://github.com/Yiuky/ReperIO/issues/new/choose).

**Prioridade:** P1 = próximo · P2 = importante · P3 = quando der
**Esforço:** P = horas · M = ~1 dia · G = vários dias

| # | Pri. | Esf. | Item | Por quê |
|---|------|------|------|---------|
| 1 | P1 | M | **Indexação agendada + índice compartilhado na rede**: modo sem janela (`--indexar <pasta>`) para o Agendador de Tarefas/cron e índice gravado numa pasta da rede, lido por toda a equipe | A varredura completa acontece uma vez (de madrugada) para todos; ninguém espera |
| 2 | P2 | P | **Excluir pastas da busca** (ex.: `MOSAICOS`, `_backup`) | Evita varrer árvores enormes onde o arquivo sabidamente não está |
| 3 | P2 | P | **Filtros por tamanho e data** (ex.: > 1 GB, modificados em 2024) | Fácil com o índice; útil para limpeza e auditoria |
| 4 | P2 | P | **Duplo clique abre a pasta do arquivo** | Pedido comum no uso diário |
| 5 | P2 | M | **Cópia inteligente**: pular arquivos já existentes com o mesmo tamanho; retomar cópia interrompida | Cópias grandes pela rede caem com frequência |
| 6 | P2 | P | Tela para **gerenciar pastas problemáticas** (ver, remover, exportar para a TI) | Hoje a lista aparece ao fim de cada busca |
| 7 | P3 | P | Lembrar as **últimas pastas raiz** usadas | Conforto |
| 8 | P3 | P | Ícone próprio da aplicação | Identidade visual |
| 9 | P3 | M | Executável para **macOS** nas Releases | Hoje o macOS usa o código-fonte |
| 10 | P3 | M | Troca de conexão no **Linux** (montagens CIFS alternativas) | Hoje o Linux usa o modo de rodadas no fim |
| 11 | P3 | — | **Assinatura digital** do executável | Elimina o aviso do SmartScreen e reduz bloqueios de antivírus |

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
