Outro detalhe é a questão da atuallização das informações do      │
│   sistema perante a importação do faturamento, conforme irei        │
│   detalhar abaixo:\\                                                │
│   \                                                                 │
│   1- As nfs do tagplus não possuem o numero do pedido.\             │
│   \                                                                 │
│   Dessa forma, o mapeamento do separacao_lote_id para ser           │
│   registrado a movimentação de estoque deverá ser feito através do  │
│   CNPJ + Cod. produto + Qtd. (Através da mesma lógica de            │
│   avaliação de score como ocorre em ProcessadorFaturamento), com    │
│   isso tambem irá gerar movimentações com o numero da NF +          │
│   separacao_lote_id ou NF + "Sem Separação"(da mesma forma que as   │
│   importações do Odoo incluindo a validação do EmbarqueItem,        │
│   preenchimento da NF em EmbarqueItem e geração de                  │
│   inconsistencia)\                                                  │
│   \                                                                 │
│   2- O registro das NFs deverão constar em FaturamentoProduto e     │
│   tambem deverão ser consolidadas em RelatorioFaturmaentoImportado  │
│   através das informações importadas / enviadas pelo webhook +      │
│   informações do cliente em CadastroCliente\                        │
│   \                                                                 │
│   A maioria das funções chamadas em                                 │
│   app/odoo/services/faturamento_service.py se aplicam ao            │
│   faturamento do tagplus, com exceção do filtro de pedidos ("VCD",  │
│   "VFB" e "VSC") pois o propósito é o mesmo, o que muda é que no    │
│   Odoo há a importação de uma nova carteira e o numero do pedido    │
│   na NF.\                                                           │
│   \                                                                 │
│   3- A carteira de pedidos não está no tagplus.                     │
│   \                                                                 │
│   Diante disso, a atualização da carteira se dará através de 4      │
│   fatores:\                                                         │
│   A- Importação do formulario de pedidos para pedidos novos (Já     │
│   implantado)\                                                      │
│   B- Cancelamento de pedidos/Qtd no                                 │
│   sistema(qtd_cancelada_produto_pedido) através da tela             │
│   "carteira_nao_odoo.html" (Ainda não testei, porem não vejo campo  │
│   para atualizar a Qtd. Cancelada)\\                                │
│   C- Importação do formulario de pedidos com o mesmo numero do      │
│   pedido (Deverá substituir o pedido anterior nesse caso, deverá    │
│   ser possivel apenas no caso que o pedido não tenha uma Separacao  │
│   com Pedido="COTADO" (Vinculação através de separacao_lote_id)\    │
│   D- Faturamento deverá preencher alem das movimentações de         │
│   estoque, o campo "baixa_produto_pedido" de acordo com o pedido    │
│   do EmbarqueItem que for preenchida a NF (visto que será extraido  │
│   o separacao_lote_id do EmbarqueItem através do CNPJ e score dos   │
│   produtos, será possivel identificar tambem o pedido, obtendo      │
│   assim num_pedido, cod_produto e qtd_produto_faturado que deverá   │
│   ser preenchido em baixa_produto_pedido)\                          │
│   \                                                                 │
│   Veja com atenção o que descrevi acima.  

 No caso do Score, pode determinar o maior score, desde que o      │
│   CNPJ seja igual e o score seja maior que 0, igual o               │
│   ProcessadorFaturamento.\                                          │
│   Movimentacao de estoque, revise como é feito na importação do     │
│   Odoo, apenas mude a origem para FATURAMENTO TAGPLUS, restante     │
│   deve ser exatamente igual.\                                       │
│   EmbarqueItem.updated_by nao existe e nem precisa existir.\        │
│   CarteiraPrincipal não possui baixa_produto_pedido.\               │
│   A atualização da CarteiraPrincipal, deverá ocorrer SEMPRE que     │
│   houver qualquer alteração em CarteiraCopia e o                    │
│   qtd_saldo_produto_pedido de CarteiraPrincipal deverá ser          │
│   sincronizado com qtd_saldo_produto_calculado e já há uma função   │
│   que recalcula o saldo de qtd_saldo_produto_calculado em           │
│   app/carteira/models.py linha 263.\                                │
│   RelatorioFaturamentoImportado e FaturamentoProduto deverá         │
│   constar em "origem" o numero do pedido vinculado no EmbarqueItem  │
│   com a nf, para casos "Sem Separação" precisamos criar uma tela    │
│   simples para vincular as NFs do tagplus nos EmbarqueItem onde     │
│   deverá trazer os EmbarqueItem com os mesmos critérios da          │
│   avaliação do score onde deverá clicar na NF e no EmbarqueItem e   │
│   um botão "Registrar" em que irá atualizar o EmbarqueItem.pedido,  │
│   RelatorioFaturamentoImportado.origem,                             │
│   FaturamentoProduto.origem, CarteiraCopia(incluindo                │
│   CarteiraPrincipal através da atualização de baixa_produto_pedido  │
│   vinculado pelo num_pedido e cod_produto) e MovimentacaoEstoque    │
│   (preenchendo a separacao_lote_id na Movimentação através da       │
│   busca pela NF) sejam preenchidas nos casos que não encontre       │
│   EmbarqueItem   


Criei um arquivo xml com os CadastroCliente.
Pesquise o modelo CadastroCliente e identifique os campos que aderem ao modelo citado em clientes.xml
Alem disso, crie um script que funcione tbm no Render para importar os dados de clientes.xml para o CadastroCliente.
Há um filtro na tela cadastro_cliente.html porem não sei se há no front end uma forma dinamica de pesquisa, verifique e se não existir implante um JS ou AJAX ou pode ser através de um botão "Filtrar".

Alem disso, importei um relatorio de faturamento onde há um layout padrão do sistema tagplus que deveremos converter para se adequar ao FaturamentoProduto e RelatorioFaturamentoImportado.
Ao realizar essa importarção, deverá passar pelo mesmo processamento que a importação pelo tagplus, incluindo validação e atualização do embarque, preenchimento das movimentações de estoque seguindo os critérios do processamento, atualização da CarteiraCopia e consequentemente da CarteiraPrincipal.

Abaixo irei detalhar como iremos converter o layout que o tagplus exporta através de um arquivo excel para podermos importar no nosso sistema:

1- Em uma linha conterá a seguinte informação:
NF-e - 3548 - PAO PAO E ARROZ LTDA EPP
Essa linha será usada para extrairmos o numero_nf e a raz_social em que usaremos para buscar o cnpj_cpf e com isso trazer as outras informações para preenchimento de FaturamentoProduto e RelatorioFaturamentoImportado
Ela deverá ser identificada através dos 4 primeiros caracteres sendo "NF-e"
Diante dessa informação deveremos extrair:
caracteres do 8 ao 11 se referem a numero_nf. (3548 no exemplo)
Caracteres apartir do 15º se referem a raz_social do cliente (PAO PAO E ARROZ LTDA EPP no exemplo)
Essa raz_social deverá ser consultada em CadastroCliente para identificar o cnpj_cpf a que se refere para que possa extrair os outros dados para o FaturamentoProduto e RelatorioFaturamentoImportado.

2- 2 linhas abaixo da linha que conter "NF-e" iniciarão as linhas da nf finalizando 1 linha antes da linha que conter "Total de Custo Utilizado:" e o custo utilizado por exemplo: "Total de Custo Utilizado: 0,35" porem deveremos identificar através do texto "Total" no inicio, isso significa que a linha de cima é a última linha da NF.

3- As colunas das linhas da NF terão as seguintes informações que serão de nossa utilidade:
Coluna A: cod_produto entre aspas simples ('4320162'), com isso deveremos retirar as aspas simples, pesquisar a descrição e peso no modelo CadastroPalletizacao através do cod_produto extraido dentro das aspas simples da coluna A e pesquisar em CadastroPalletizacao.cod_produto para obter o nome_produto e peso_bruto.

coluna D: data_fatura, extraida através dos 10 primeiros caracteres no formato dd/mm/yyyy, o campo do excel terá o seguinte formato "01/07/2025 às 16:32:39"

coluna E: qtd_produto_faturado no formato com "," e tres numeros "0", por exemplo (5,000) onde a "," identifica um separador decimal portanto a qtd nesse caso é "5".

coluna F: valor_produto_faturado no formato com "." como separador de milhar e "," como separador decimal por exemplo "1.001,40".

Dessa forma é possivel utilizar uma forma alternativa de atualizar os cadastros dos clientes e importar o faturamento enquanto eu obtenho as credenciais necessarias para se fazer as importações via API e atualizações através do WebHook.