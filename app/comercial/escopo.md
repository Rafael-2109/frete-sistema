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

As equipes de vendas e vendedores são pesquisadas através de:
CarteiraPrincipal.equipe_vendas
ou
FaturamentoProduto.equipe_vendas

Os vendedores são pesquisados dentro do filtro de equipe de vendas:
CarteiraPrincipal.vendedor
ou
FaturamentoProduto.vendedor

===========================================

O valores serão obtidos através de: 


Valor total do pedido:
if CarteiraPrincipal.num_pedido:
pedidos = CarteiraPrincipal.num_pedido
for produto in pedidos
produto = CarteiraPrincipal.cod_produto
valor.produto = pedidos.preco_produto_pedido * pedidos.qtd_produto_pedido
else
'Valor total do pedido faturado'


Saldo da pedido:
Utilizar qtd_saldo_produto_pedido ao invés de qtd_produto_pedido


Valor total do cliente:
Somar 'Valor total do pedido' por cnpj_cliente


Valor da NF:
nf_faturada = FaturamentoProduto.numero_nf
for produtos in nf_faturada:
produtos = FaturamentoProduto.cod_produto
valor_nf=produtos.valor_produto_faturado


Valor total do pedido faturado:
pedidos_faturados = FaturamentoProduto.origem
for p in prod_faturados
valor.p = pedidos_faturados.valor_produto_faturado

Valor da Separação:

separacao = Separacao.separacao_lote_id
for valor in separacao:
valor = separacao.valor_saldo


Caso todo o pedido tenha sido faturado, o total será o 'Valor total do pedido faturado'
Caso haja saldo em CarteiraPrincipal, o total será 'Valor total do pedido'  


=========================================

Etapa 1:

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

=================================================
Etapa 1 Concluida
=================================================

# Etapa 2 - Enriquecimento dos clientes com pedidos

## Objetivo: Enriquecer os clientes agrupados com informações dos pedidos

## Formato de exibição

Em cada cliente agrupado deverá contem um botão que deverá renderizar um modal com as informações dos pedidos do cliente respeitando o filtro selecionado [Em Aberto, Total].

As informações deverão ser renderizadas 1 pedido por linha.

## Informações da linha

num_pedido
pedido_cliente (Buscar de Separacao.pedido_cliente, fallback para CarteiraPrincipal.pedido_cliente fallback para app.odoo.utils.pedido_cliente_utils.py)
incoterm
metodo_entrega_pedido
data_pedido
status (
    If 'Valor total do pedido faturado'=0
        status="Em Aberto"
    Elif 'Valor total do pedido faturado'<'Valor total do pedido'
        status="Parcialmente Faturado"
    Elif ('pedidos_monitoramento'.status_finalizacao=="Entregue")<'Valor total do pedido'
        status="Parcialmente Entregue"
    Else status="Entregue"
    )
'Valor total do pedido'
'Valor total do pedido faturado'
Entregue = ('pedidos_monitoramento'.status_finalizacao=="Entregue")
Saldo em Carteira = 'Valor total do pedido' - 'Valor total do pedido faturado'

======================================================
ETAPA 2 CONCLUIDA
======================================================

# Etapa 3: Enriquecer os pedidos com as Separações, faturamentos e dados de monitoramento

Visto que:
- 1 pedido - N NFs, mas:
- N Separacao - 1 separacao_lote_id - 1 NF - 1 pedido - 1 entrega

## O propósito dessa etapa é enriquecer os pedidos com as informações de Separacao, FaturamentoProduto e EntregaMonitorada

## Formato de exibição

Em cada pedido do "cliente agrupado" deverá contem um botão que deverá renderizar um modal com as informações de cada "documento" do pedido respeitando o filtro selecionado [Em Aberto, Total] + o Saldo.

### As informações deverão ser renderizadas 1 documento por linha.

Os documentos ao qual me refiro são utilizados para demonstrar como o pedido foi programado/separado.

Documentos:
1- documento [Separação] = Cada Separacao deverá ser agrupada por Separacao.separacao_lote_id filtrando apenas Separacao.sincronizado_nf=False do pedido correspondente.
2- documento [NF] = Cada NF deverá ser agrupada por FaturamentoProduto.numero_nf

[NF, Separação, Saldo] deverão compartilhar as mesmas colunas e indices do modal.

Colunas: "Subseção Faturamento":[NF, Faturamento], "Subseção Embarque":[Embarque, Transportadora], "Subseção Agendamento"(Caso cliente precise de agendamento): [Agendamento, Protocolo, Status Agenda], Entrega Prevista (Caso o cliente não precise de agendamento) Entrega, Valor.
No caso, de Separação, não terá todas as colunas preenchidas, por não haver numero_nf, data de faturamento... Portanto preencha com "-" quando não houver informação.

### [NF]
FaturamentoProduto.numero_nf (Nota fiscal)
FaturamentoProduto.data_fatura (Data do Faturamento)
EntregaMonitorada.data_embarque (utilizar fallback para Embarque.data_embarque através de EmbarqueItem.nota_fiscal)
transportadora.nf = EntregaMonitorada.transportadora
agendamento.nf = EntregaMonitorada.data_agenda fallback para EntregaMonitorada.data_entrega_prevista 
Ultimo AgendamentoEntrega.protocolo_agendamento / 
Ultimo AgendamentoEntrega.status ['aguardando', 'confirmado'] / 
EntregaMonitorada.data_hora_entrega_realizada
'Valor da NF'

### [Separação]
X - Nota Fiscal
Separacao.expedicao (Data prevista de Embarque, utilizar prefixo "Previsão: " para casos de Separação)
? - Transportadora (Tentar buscar em Embarque.transportadora)
Separacao.agendamento
Separacao.protocolo
Separacao.agendamento_confirmado
X - Entrega realizada
'Valor da Separação'

### [Saldo]
Saldo do pedido(total do pedido - faturado) - (for 'Valor da Separação' in num_pedido)

==================================
Etapa 3 Concluido
==================================

# Etapa 4 Enriquecer os documentos com produtos

## Formato de exibição

Em cada documento [NF, Separação, Saldo] deverá ter um novo acordion, tambem destacando o documento selecionado ao abrir, que deverá mostrar os produtos daquele documento.

As colunas desse novo acordion deverá ser:
Código
Produto
Quantidade
Preço
Valor
Peso
Pallet

Abaixo vou listar a fonte de informação de cada documento:

"NF"
*Dados através de FaturamentoProduto.numero_nf
*Todos os campos sem modelo especificado, considere FaturamentoProduto
*Campos calculados com CadastroPalletizacao, utilizar como pesquisa FaturamentoProduto.cod_produto com CadastroPalletizacao.cod_produto

cod_produto
nome_produto
qtd_produto_faturado
preco_produto_faturado
valor_produto_faturado
CadastroPalletizacao.peso_bruto * qtd_produto_faturado
qtd_produto_faturado / CadastroPalletizacao.palletizacao


"Separação"
*Dados através de Separacao.separacao_lote_id

cod_produto
nome_produto
qtd_saldo
preço = valor_saldo / qtd_saldo
valor_saldo
peso
pallet

"Saldo"
*Dados através de CarteiraPrincipal.num_pedido abatendo valor das separacoes=(Separacao.num_pedido com sincronizado_nf=False)

cod_produto
nome_produto
qtd_saldo_pedido = qtd_saldo_produto_pedido - separacoes.qtd_saldo (qtd do saldo do pedido abatendo faturamento - soma de todas as qtd_saldo das separacoes desse pedido com sincronizado_nf=False)
preco_produto_pedido
preco_produto_pedido * qtd_saldo_pedido
CadastroPalletizacao.peso_bruto * qtd_saldo_pedido
qtd_saldo_pedido / CadastroPalletizacao.palletizacao

1- Sim, cada documento precisa de um ícone de expansão próprio
- Não, pode acumular as expansões.

2- Sim, as 3 formas de identificação que voce citou estão corretas.

3- Sempre encontrará mas pode deixar com "-" caso não encontre o peso ou pallet

4- Inicialmente vamos carregar sob demanda, as otimizações faremos posteriormente.

5- Pode usar indentação se fizer sentido no projeto.
- Pode Seguir semelhante ao que voce fez para documentos.
- Pode usar uma cor diferente, contando que seja coerente com o tema dark
- Mantenha o tema dark

6- Não há necessidade de totais visto que já consta no documento

7- Crie separadamente e depois otimizamos e unificamos.

8- Visto que o saldo é (1 produto de 1 pedido) - (1 produto de N separações) deverá subtrair da qtd do pedido -  somatória da qtd das separações que atendam aos requisitos 

9- 2 casas decimais
- Se o saldo for 0 mostrar "-"

10- Sim, pode criar esses métodos.
- Crie um ProdutoDocumentoService

==========================================
Etapa 4 concluida
==========================================

Etapa 5

Finalidade: Criar restrição de acesso por usuario sobre os filtros de vendedor e equipe_vendas.

Essa restrição deverá limitar apenas o usuario vendedor (Usuario.perfil="vendedor") a ver os dados que o seu usuario estiver habilitado.
O usuario poderá ter acesso a multiplos vendedor ou multiplos equipe_vendas.
A restrição se limita a vendedor e equipe_vendas, quais dados o Usuario poderá ver não haverá restrição.
Deverá haver uma interface permitida apenas para os Usuario.perfil="administrador" e "gerente_comercial" administrar.
Os usuario vendedor terão acesso apenas ao módulo comercial e mais nada no sistema.
Não há previsão para novas restrições por usuario, portanto pode ser algo bem especifico.
Faça simples para atender apenas essa necessidade, sem prever expansão posterior de restrições e perfis.

1- C- Remover vendedor_vinculado e criar nova estrutura
2- Sim se usuario tem acesso a uma equipe_vendas ele poderá ver os dados de todos os vendedores dessa equipe.
-Tambem há possibilidade de permitir alguns vendedores apenas e não uma equipe inteira.
3- Criar nova rota para gerenciar.
- Ignorar o sistema de permissões atual e criar esse do zero.
- É bom manter logs de quem e quando alterou.
4- Iniciar no dashboard normal, se uma equipe tiver N vendedores mas o usuario tiver acesso apenas a 1 vendedor de 1 equipe, ele irá clicar na equipe que pertence e dentro da equipe irá mostrar apenas 1 vendedor, se tiver acesso a 1 equipe, irá clicar na equipe e dentro dela irá mostrar todos os vendedores dessa equipe.
5- Não permitir e redirecionar para o dashboard comercial.
Pensando em estrutura e talvez uma idéia que facilite, todas as telas utilizam base.html, se for possivel, ao realizar o login, deixar algum "flag" em base.html marcando que é vendedor e um gatilho no próprio html que restrinja o acesso e mostre apenas o que for pertinente ao vendedor.
6- Poderá ver tudo que for pertinente a permissão dele.
7- Usuario vendedor sem permissão não ve nada.
Todos os outros perfis podem ver tudo, restrição é apenas "If vendedor"
8- Pode deixar para darmos atenção a nova estrutura mas posteriormente irei deletar.
9- Select não, pode ser checkbox ou dois painéis.
Se for bom de manusear pode ser 2 painéis.
10- Redirecionar imediatamente.

NÃO ASSUMA NADA.
Veja se essas respostas respondem todas as duvidas.
Se preferir pode perguntar mais.
Pense profundamente.
ultrathink

1- Separado por tipo
2- 0% chance de nomes repetidos, pode confiar pois os nomes são numerados.
3- Preciso que lembre-se que 1 Usuario pode ter permissões de N vendedores ou N equipes, se essa estrutura atender então está ok.
4- OK
5- Mostrar apenas referente ao que tem acesso.
6- OK
7- Sim
8- Ótimo

NÃO ASSUMA NADA.
Veja se essas respostas respondem todas as duvidas.
Se preferir pode perguntar mais.
Pense profundamente.
ultrathink


> Gzip? pra que serve isso e qual impacto?
  Paginação é interessante, isso vamos implantar.
  Alem disso eu precisava criar filtros tambem na página dos clientes,
  esses filtros devem pegar:
  - cnpj_cpf
  - raz_social
  - raz_social_red
  - UF
  - num_pedido
  - pedido_cliente

  É possivel criar filtros para isso tudo na página de clientes?
  No caso de num_pedido e pedido_cliente são filtros que se referem aos
  pedidos de um cliente, onde deverá considerar os filtros já
  considerados incluindo "Em Aberto".
  Por exemplo: Cliente Assai emite 1 pedido_cliente para todas as
  filiais de SP, ou seja, são 100 "clientes" com o mesmo pedido_cliente,
  pode ser que todas essas 100 lojas do Assai possuam algum
  pedido_cliente "Em Aberto" mas o vendedor pode pesquisar apenas
  referente ao pedido_cliente mais antigo, porem supondo que desse
  pedido_cliente mais antigo, apenas 10 lojas possuem esse pedido "Em
  Aberto", o sistema deverá nesse caso filtrar apenas as 10 lojas caso o
  vendedor filtre pelo pedido_cliente mais antigo, mas ao retirar o
  filtro de pedido_cliente deverá trazer todas as 100 lojas.

  Para voce pode ser um pouco complexo, mas faça perguntas que eu
  esclareço para garantir que a implementação seja correta.

  NÃO ASSUMA NADA.
  PENSE PROFUNDAMENTE.
  u 
