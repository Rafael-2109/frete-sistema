# MISSAO - Sincronizar PO c/ sistema Odoo


## Continuação da implementação do sistema de validacao do PO X NF


## Objetivo - Resolver inconsistencias da fase 2, testar a solução, verificar mais alguma "ponta solta" e avaliar algum risco de loop eterno.


1- Implementar importação dos numeros dos POs vinculado aos DFes importados para manter o sistema sincronizado com o Odoo.

2- Um DFe vinculado ao PO e recebido é considerado finalizado.

3- Atualizar a validação do DFe através da criação de um novo "De-Para" (Caso status seja "Sem De-Para", deverá validar essa etapa ao cadastrar o "De-Para")

4- Alem de incluir/atualizar o "De-Para" no Odoo através da criação pelo sistema, tambem deverá sincronizar com o Odoo em caso de alteração e em caso de exclusão.

5- Após excluir um "De-Para" e tentar cadastra-lo, o sistema mostra um erro por exemplo: "Erro: Ja existe De-Para para fornecedor 52502978000155 e produto 73600306", identifique e corrija.

6- Voce pode e deve realizar testes no sistema local, e caso precise no Odoo.

7- O problema que eu identifiquei ocorreu no sistema em produção no Render, caso precise identifica-lo, pode acessar os logs pelo MCP do Render.

8- O caso que ocorreu o erro foi o caso abaixo, que no momento não está mais cadastrado por eu ter excluido e não consegui cadastra-lo novamente por aparecer o erro:

- CNPJ: 52.502.978/0001-55
- Nome fornecedor: METALGRAFICA ROJEK LTDA
- Cod produto fornecedor: 73600306
- Nome produto fornecedor: TAMPA ARJEK BR-1 58 - DOURADA P/ POTES
- Cod produto interno: 206030034
- Nome produto interno: TAMPA ALUMINIO AZUL - VD 100/200 G - CONSERVA
- UM fornecedor: MIL
- Fator de conversão: 1000

**Obrigatório** Verifique o plano existente em /plans.
**Obrigatório** Os campos do Odoo só deverão ser citados com evidencia real de serem os campos corretos
**Obrigatório** Alem de identificar os campos corretos, é necessario identificar o tipo do campo correto.


