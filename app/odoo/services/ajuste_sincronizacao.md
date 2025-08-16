# Processo de ajuste de pedidos, PreSeparacaoItem e Separacao ao importar uma carteira de pedidos atualizada do Odoo com pedido ALTERADOS.

Detalhes essenciais:
1- Quando os pedidos são cotados, eles vão para EmbarqueItem
2- Considere "ativo" os embarques que EmbarqueItem.status = ativo e Embarque.status = ativo
3- Há uma relação direta em PreSeparacaoItem, Separacao, Pedido, EmbarqueItem através de separacao_lote_id
4- A definição de "COTADO" vem de Pedido.status = "COTADO"
5- Pedido é um "agrupamento" da Separacao ignorando os produtos e agrupando em 1 linha com os totais por separacao_lote_id da Separacao, portanto quando eu falo Separacao COTADO significa o join entre Pedido e Separacao pelo separacao_lote_id onde o COTADO se refere ao status.
6- Quando eu falo pedido significa num_pedido em CarteiraPrincipal

## Caso 1 - Separação Total:
Premissa 1: Quando houver uma Separacao ou PreSeparacaoItem total, isto é, todos os produtos e todas as qtds de cada produto do pedido estão em 1 PreSeparacaoItem ou a 1 Separacao.
Premissa 2: Houver uma alteração do pedido no Odoo.
Premissa 3: Importar uma carteira de pedidos atualizada do Odoo.

Nesse caso, o pedido "atualizado" deverá:
1- Substituir completamente os itens e qtd que constar na PreSeparacaoItem ou na Separacao, contanto que seja "Total".
2- Caso a Separacao esteja COTADO, deverá alem de substituir, criar um alerta que deverá aparecer no topo do endpoint "/pedidos/lista_pedidos.html"

## Caso 2 - Separação Parcial:
Premissa 1: Quando houver uma Separacao ou PreSeparacaoItem parcial, isto é, não há 1 separacao_lote_id em PreSeparacaoItem ou Separacao com o total do pedido.
Premissa 2: Houver uma alteração do pedido no Odoo.
Premissa 3: Importar uma carteira de pedidos atualizada do Odoo.

Nesse caso, o pedido "atualizado" deverá:
1- Seguir uma ordem de hierarquia ao importar um pedido que contenha uma atualização envolvendo redução (diminuição de qtd de um item ou exclusão do item no Odoo)
A- A hierarquia deverá alterar na seguinte ordem:
A.1 - Saldo livre, isto é, quantidade que ainda não consta em PreSeparacao e Separacao (pedido tem 10 qtds, PreSeparacaoItem tem 3 qtd, Separacao tem 3 qtds, logo Saldo livre = 4)
A.2 - PreSeparacaoItem
A.3 - Separacao que não esteja COTADO
A.4 - Separacao que esteja COTADO

Ao reduzir/excluir a qtd de uma Separacao COTADO, deverá emitir um alerta no mesmo local da Separacao Total (endpoint "/pedidos/lista_pedidos.html")

2- Acrescentar o excedente em Saldo Livre ao importar um pedido que contenha uma atualização envolvendo adição (aumento de qtd de um item ou adição de um item)


Os testes que realizarei serão sempre através de:
- Pedido VFB2500241
Itens:
- 4320162 - 10
- 4360162 - 10
- 4310162 - 10

Alternando para:

Itens:
- 4320162 - 15
- 4360162 - 5
- 4350162 - 10

E vice versa.
psql $DATABASE_URL -c "ALTER TABLE saldo_standby ADD COLUMN observacoes TEXT;"
python -c "from app import app, db; db.engine.execute('ALTER TABLE saldo_standby ADD COLUMN observacoes TEXT;')"