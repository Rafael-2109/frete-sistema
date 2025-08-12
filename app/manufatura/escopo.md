1- Define previsão de vendas em PrevisaoDemanda junto ao comercial e histórico das demandas realizadas por grupo

2- Define/avalia estoque de segurança, avalia qtd_reposicao_sugerida e gera as ordens em PlanoMestreProducao.
Essa tela deverá mostrar:
- qtd_demanda_prevista.
- qtd_estoque_seguranca.
- qtd_estoque
- qtd_producao_programada (esse campo acredito que deva ser uma querie sum(OrdemProducao.qtd_planejada) através do join com data_mes, data_ano com data_inicio_prevista e cod_produto)
- qtd_reposicao_sugerida = qtd_demanda_prevista + qtd_estoque_seguranca - qtd_estoque - qtd_producao_programada


3- Sequencia Ordens de produção através de:
A- Carteira de Pedidos
Deverá considerar as datas de expedicao das Separacao onde Pedido.status!=FATURADO (join através de separacao_lote_id), PreSeparacaoItem quando não houver Separacao (comparação se há duplicidade pelo separacao_lote_id) e considerar o saldo da CarteiraPrincipal que não contem Separacao/PreSeparacaoItem

B- Disponibilidade dos componentes
B.1 As ordens de produção deverá avaliar a ListaMateriais verificando separadamente os produtos_produzidos e produtos_comprados
B.2- Os produtos_produzidos, deverão ser avaliados através do estoque previsto do produto filho na data da ordem do produto pai e gerar uma ordem de produção de maneira automatica e vinculada à ordem pai, dessa forma qualquer alteração na ordem pai, deverá ser reavaliado o estoque previsto do produto filho na data da ordem do produto pai e atualizar a ordem filho. 
B.3- PedidoCompras / RequisicaoCompras
Considerar as data_pedido_previsao dos componentes do produto pai e dos componentes do produto_produzido da ListaMateriais do produto pai através da ListaMateriais do produto filho
B.4- Lead time dos componentes
Considerar o LeadTime dos produtos_comprados através dos componentes da ListaMateriais incluindo o componente dos produtos_produzidos constantes no produto pai


C- Disponibilidade de maquinas
Mostrar na tela de uma forma que seja extremamente visual e interativo para o usuario verificar se é possivel incluir aquela ordem de produção naquele dia ou se ele prefere quebrar a ordem de produção para coloca-la naquele momento

4- Requisita compras.
Cria uma requisição de compras respeitando lead time dos componentes de maneira automatica na criação da ordem de produção ou opta por não criar a requisição de compras na ordem de produção e cria posteriormente avaliando o estoque dos componentes.

5- Avaliação dos estoques de produtos onde CadastroPalletizacao.produto_comprado = True junto com as RequisicaoCompras, PedidoCompras (Não sei como vincular a requisição criada no Odoo com a requisição criada no sistema, onde a requisição do sistema deverá ser um "rascunho" da requisição do sistema)
