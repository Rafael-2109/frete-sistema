Objetivo:
1- Criação de uma tela para acompanhamento e histórico dos pedidos.
2- Essa tela será usada pelos vendedores e gestores de vendas.
3- Essa tela terá informações de datas, produtos, valores sobre a carteira de pedidos, nfs, entregas e separações.

============================================

Localização dos clientes, pedidos e pedidos dos clientes.

Os clientes da empresa são compostos por:
clientes_faturados = FaturamentoProduto.cnpj_cliente 
clientes_carteira = CarteiraPrincipal.cnpj_cpf
todos_clientes = (clientes_faturados + clientes_carteira).distinct

Os pedidos estão em:
pedidos_monitoramento = EntregaMonitorada.numero_nf join com FaturamentoProduto.numero_nf para encontrar FaturamentoProduto.origem (pedido)
pedidos_faturamento = FaturamentoProduto.origem (pedido)
pedidos_separacao = Separacao.num_pedido
pedidos.carteira = CarteiraPrincipal.num_pedido

Os pedidos do cliente estarão em:
Separacao.pedido_cliente
CarteiraPrincipal.pedido_cliente
ou através da função em app/odoo/utils/pedido_cliente_utils.py função: buscar_pedido_cliente_odoo através do num_pedido

===========================================

O valores serão obtidos através de: 

Valor total do pedido:
pedidos = CarteiraPrincipal.num_pedido
for produto in pedidos
produto = CarteiraPrincipal.cod_produto
valor.produto = pedidos.preco_produto_pedido * pedidos.qtd_produto_pedido

Saldo da pedido:
Utilizar qtd_saldo_produto_pedido ao invés de qtd_produto_pedido

Valor total do cliente:
Somar 'Valor total do pedido' por cnpj_cliente

Valor total do pedido faturado:
pedidos_faturados = FaturamentoProduto.origem
for p in prod_faturados
valor.p = pedidos_faturados.valor_produto_faturado

Caso todo o pedido tenha sido faturado, o total será o 'Valor total do pedido faturado'
Caso haja saldo em CarteiraPrincipal, o total será 'Valor total do pedido'  

As equipes de vendas e vendedores são pesquisadas através de:
CarteiraPrincipal.equipe_vendas
ou
FaturamentoProduto.equipe_vendas

Os vendedores são pesquisados dentro do filtro de equipe de vendas:
CarteiraPrincipal.vendedor
ou
FaturamentoProduto.vendedor


=========================================


(é uma tentativa de código mas quero que entenda a intenção, somar todos os produtos do pedido)

# A interface inicial deverá ser composta por "badges botões" com cada equipe de vendas e ao clicar deverá mostrar "badges botões" com os vendedores e com isso renderizar a tela de acompanhamento.

# A tela de acompanhamento será agrupada por cliente

# Esse acompanhamento será realizado através de um filtro amplo por posição [Em Aberto, Total]

Esse filtro envolverá:

## Em Aberto: Posição completa dos pedidos que ainda não foram totalmente entregues.

Filtro pedidos 'Em Aberto':
- CarteiraPrincipal.num_pedido (pedidos em carteira)
or
- pedidos_monitoramento.status_finalizacao != 'Entregue' (pedido faturados porem não entregues)
*Fazer distinct para não repetir os pedidos

## Todos: todos os pedidos:
Todos os pedidos, por isso temos que pegar os da carteira, se não estiver na carteira pegar os faturados

- CarteiraPrincipal.num_pedido (pedido em carteira)
or
- pedidos_faturamento
*Fazer distinct para não repetir os pedidos

# A tela com cliente agrupado deverá ter as seguintes informações:
vendedor
cnpj_cliente / cnpj_cpf
raz_social (campo consta apenas em CarteiraPrincipal, caso não encontre teremos que pensar se trazemos do Odoo ou fazemos query do Odoo sempre)
raz_social_red / nome_cliente
estado
municipio
ContatoAgendamento.forma (através de ContatoAgendamento.cnpj)
Valor Em Aberto
