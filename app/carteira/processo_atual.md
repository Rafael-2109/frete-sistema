Objetivo 1: Eu preciso atualizar a carteira pendente e o faturamento sem perder a rastreabilidades e atualizando os locais dependentes dessas informações
Objetivo 2: Realizar separações através da carteira pendente
Objetivo 3: Atualizar os estoques

1- Importação dos relatórios do Odoo sequenciais Faturamento -> Carteira.

2- Atualização / Importação do Faturamento:

A Importação do Faturamento deverá confrontar a Separação através do pedido (ou origem), codigo do produto e qtd do produto das separações com as nfs.

Caso 1 - Separação = NF -> Grava a movimentação de estoque

Caso 2 - Separação != NF:
    A - Verifica se há o pedido em separação
    B - Se houver mais do que 1 pedido, verifica o que melhor se adequa.
    C - Identificando o pedido, grave a movimentação de estoque e grave as informações em FaturamentoParcialJustificativa

Gravação da movimentação de estoque:
movimentacao = MovimentacaoEstoque(
                    cod_produto=codigo do produto
                    nome_produto=Nome do produto
                    tipo_movimentacao='FATURAMENTO',
                    local_movimentacao='VENDA',
                    data_movimentacao= Data do faturamento
                    qtd_movimentacao= - Quantidade faturada  # Saída (negativa)
                    observacao=f"Baixa automática NF ###### - lote separação id", (Caso seja um faturamento sem separação trocar lote separação id por "Sem Separação")
                    created_by=Importação Odoo
                )

Caso 3 - NF Cancelada -> Deverá buscar a movimentação de estoque através da NF e apaga-la 



3- Atualização Carteira Pendente:

A- Manter os registros realizados em expedicao, data de entrega, agendamento e protocolo.

B- Manter as separações vinculadas.
*** Há 2 tipos de separações: Totais e Parciais

    B.1 - Separação Total:
    Deverá manter os registros no pedido após a atualização da carteira.
    Caso haja alteração no pedido após a atualização, deverá ser alterada a Separação e manter todas as linhas do pedido atualizadas e com os registros.

    B.2 - Separação Parcial:
    Deverá manter os registros no pedido após a atualização da carteira.
    Caso haja alteração no pedido após a atualização, deverá ter uma tela mostrando: 
    - Separação / Separações (Pode separar por página cada Separação) Atual (codigo do produto / nome do produto / qtd do produto / valor total do produto / peso total do produto / pallet total do produto)
    - Saldo Pedido (Mesmos campos, na frente de cada campo) (Pedido total - Separação)
    - Alteração Separação (Campos pré preenchidos com as menores qtds entre Separação e Saldo Pedido)
    - Botão de Salvar

    Caso haja alteração da Separação em algum dos 2 casos, os modelos de Separação e Pedidos deverão ser atualizados.
    
    Caso haja alteração de alguma Separação com Pedido com status "Cotado" em Pedidos, deverá criar um alerta fixo no topo da tela em Pedidos e Embarques com o/os links do Embarque que há aquela separação alterada. 
    A desativação do alerta ocorrerá ao imprimir aquela separação alterada ou imprimir completo em Embarque.


4- O trabalho realizado na carteira de pedidos é um trabalho de Supply Chain:
A- Avaliar os estoques para programar o atendimento dos pedidos através do campos expedicao.
B- Fazer uma pré separação dos pedidos avaliando se será enviado Total ou Parcial.
C- Fazer a gestão dos agendamentos nos clientes (Registrar os protocolos, acompanhar a aprovação das agendas, registrar as datas solicitadas/aprovadas das agendas)
D- Gerar a Separação (Parcial ou Total) / Pedidos onde ocorrerá a contratação do frete e posteriormente no Embarque a separação do pedido.





