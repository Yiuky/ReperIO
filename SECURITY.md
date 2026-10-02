# Política de segurança

## Versões com suporte

Correções de segurança são feitas na versão mais recente publicada em
[Releases](https://github.com/Yiuky/ReperIO/releases/latest).

## Como relatar uma vulnerabilidade

**Não abra uma issue pública** para falhas de segurança. Use o recurso
[*Report a vulnerability*](https://github.com/Yiuky/ReperIO/security/advisories/new) do GitHub (aba **Security** do
repositório), que cria um relato privado para os mantenedores.

Inclua, se possível:

- versão e sistema operacional;
- passos para reproduzir;
- o impacto esperado (ex.: leitura ou gravação de arquivos fora do esperado).

Você receberá uma resposta assim que possível; a correção é publicada numa nova versão, com
crédito a quem relatou (se desejar).

## O que o programa faz (e o que não faz)

- Só **lê** as pastas da busca. Só **grava** no destino de cópia e no arquivo de exportação
  escolhidos pelo usuário, e nos próprios arquivos de log/índice, na pasta de dados do usuário.
- Não envia dados pela internet e não abre portas de rede.
- Usa apenas as credenciais de rede da sessão do Windows/Linux do próprio usuário.
