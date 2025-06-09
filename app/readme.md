Cotação

Deverá utilizar os pedidos selecionados para realizar a cotação do frete.

## REGRAS PARA UF E CIDADE DOS PEDIDOS NO MOMENTO DA COTAÇÃO ##
Campos em pedidos:
UF = cod_uf
Cidade = nome_cidade
Rota = rota

- Regra numero 1
Pedidos com Rota FOB deverá ser desconsiderado o UF e Cidade ao pesquisar nos pedidos, sendo possivel encontra-los apenas ao filtrar FOB no UF ou pela Rota

- Regra numero 2
Pedidos com Rota RED deverão ser considerados como UF SP e Cidade GUARULHOS

- Regra numero 3 
Pedidos com Cidade SP deverão ser considerados SAO PAULO

- Regra numero 4
Pedidos com Cidade RJ deverão ser considerados RIO DE JANEIRO

- Regra numero 5
As cidades no módulo vinculos e no modulo localidades estão com letras maiusculas, minusculas e acentos, portanto ao ser comparada com as cidades dos pedidos, deverão sempre serem convertidas para maiusculas e retirado os acentos

- Regra numero 6
Para verificar quais cidades são consideradas para as tabelas de frete, deverão sempre procurar as cidades atendidas nos vinculos em cidades e uf através do vinculo da transportadora, nome_tabela e uf_destino em TabelaFrete (tabelas) e transportadora, nome_tabela e uf em CidadeAtendida (vinculos).

- Regra numero 7
Para verificar qual tabela é possivel usar deverá considerar buscar o uf e cidade nos vinculos e procurar a tabela através do uf, nome_tabela e transportadora nos vinculos.


## REGRAS PARA AS COTAÇÕES ##

Todas as cotações deverão ser realizadas considerando por CNPJ (N pedidos / 1 CNPJ)

- Regra numero 1
As cotações deverão ser separadas em 3 partes:

- 1a parte: 
As cotações de carga direta são aquelas em que o tipo_carga de tabelas for "DIRETA".
As cargas diretas, terão os veiculos no campo modalidade de tabelas.
Cotações de carga direta, deverão ser consideradas apenas para cotações com pedidos do mesmo UF.
Cotações de carga direta deverão sempre considerar o total de valor e peso dos pedidos cotados.
Cotações de carga direta, deverão avaliar se o peso_maximo do veiculo suporta o peso total dos pedidos cotados:
- veiculos.nome = nome do veiculo
- veiculos.peso_maximo = peso limite do veiculo

- 2a parte:
As cotações de carga fracionada na pagina de cotação, deverão ser apresentadas apenas as melhores cotações.
Elas deverão ser agrupadas por transportadora e apresentadas dentro de um card da transportadora vencedora.
Elas deverão considerar para o calculo o frete_minimo_peso e frete_minimo_Valor por CNPJ.

- 3a parte:
Modal de escolha de transportadora por CNPJ:
Deverá existir um card por cliente e dentro dele todas as cotações de frete fracionado para esse CNPJ.
Deverá existir um card no topo do modal em que será preenchido com apenas a transportadora escolhida.
Ao lado de cada transportadora deverá existir um botão "Escolher", ao clicar nele a transportadora escolhida deverá aparecer no card da transportadora do topo.
Quando houver uma transportadora escolhida, os botões ao lado da transportadora escolhida em cada card de CNPJ do cliente, deverá aparecer "Adicionar à Cotação", quando clicado, deverá ser adicionado ao card da transportadora esse cliente.
Ao lado das transportadoras que não forem a escolhida, deverá aparecer "Escolher", ao clicar deverá ser substiuida a transportadora do card pela escolhida e apagado os clientes do card da transportadora.


- Regra numero 2: 
As cotações de carga direta, deverá ser considerado 1 para todos os pedidos e clientes contidos nela.
Os embaques terão apenas 1 cotação por embarque no caso de ser uma cotação de carga direta.
As cotações de carga direta, deverão ser aberto os valor por cliente apenas quando o Embarque for salvo com as NFs e gravado os fretes em fretes.

Cotações de carga direta:
1 Cotacao / N Pedidos
1 Cotacao / 1 Embarque
1 Pedido / 1 EmbarqueItem

As cotações de carga fracionada, deverão ser consideradas 1 para cada CNPJ.
As cotações de carga fracionada, deverão ser gravadas no EmbarqueItem para cada pedido do CNPJ.
As cotações realizadas pelo Modal "Escolher Transportadora por CNPJ" são consideradas cargas fracionadas.

Cotações de carga fracionada:
N Pedidos / 1 CNPJ / 1 CotacaoItem / 1 tabela / N EmbarqueItem
1 Pedido / 1 EmbarqueItem
1 transportadora / 1 Embarque
1 CotacaoItem / 1 CNPJ
N EmbarqueItem / 1 Embarque
N Pedidos / 1 CNPJ

## REGRAS PARA GRAVAÇÃO DAS COTAÇÕES NO EMBARQUE ##

- Regra numero 1:
As cotações deverão ser gravadas no embarque todos os dados da tabela utilizada para aquela cotação.

Apenas os dados da tabela utilizada deverá ser gravado no Embarque / EmbarqueItem.

Os dados da tabela deverão ser gravados no Embarque (para as cargas com tipo_carga = "DIRETA") ou no EmbarqueItem (para as cargas com tipo_carga = "FRACIONADA"), mas nunca nos 2 locais.

## REGISTRO DOS FRETES ##

1- Os fretes deverão ser registrados através da tabela contida no embarque / itens do embarque (depende do tipo da carga)

2- Para o calculo do frete no momento do registro, deverá ser usado:

    a- Para cargas fracionadas: A tabela de qualquer Item (Pedido) do CNPJ no embarque (visto que para registrar no embarque foi copiada a tabela do CNPJ para todos os pedidos daquele CNPJ naquele embarque) calculado através do valor e peso da somatória das NFs daquele CNPJ (por isso tem q ter a NF no embarque e no faturamento, no embarque vincula a tabela e no faturamento traz o peso e valores corretos)

    b- Para cargas diretas: A tabela do Embarque (visto que para carga direta o valor é da carga, e não por pedido ou CNPJ, por isso que é registrada no embarque e não por Item) rateada pelo peso total das NFs de cada CNPJ daquele embarque.

3- O lançamento do frete será realizado após todos os itens do embarque conter NF preenchida e todas essas NFs estarem importadas no faturamento (a ordem do que será lançado primeiro pode variar entre NF no embarque e importação das NFs do faturamento)

4- Os fretes deverão ser lançados na proporção 1 Frete / 1 CTe / 1 Valor de frete / 1 Vencimento / 1 CNPJ / 1 Embarque / N pedidos / N Nfs (Respeitando o item 2)

5- Para o registro do frete haverão 4 valores de frete:

    a- Valor cotado: Valor proveniente da tabela e das informações das NFs, valor esse que será registrado automaticamente quando houver 1 embarque com todas as nfs preenchidas e com todas as nfs importadas.
    
    b- Valor CTe: Valor cobrado pela transportadora, esse valor iremos estudar uma forma de ou preencher no sistema ou de importar através de um excel ou arquivo xml

    c- Valor Considerado: Esse valor é o valor que definiremos ser o valor "valido".
    Ele existirá pois há diversas vezes em que a transportadora cobra um valor menor que o valor cotado e nesse caso queremos considerar esse valor como válido para não gerar crédito a ela, porem tambem há vezes em que a transportadora cobra um valor maior que o valor da tabela por alguma particularidade, porem negociamos e definimos um valor com ela posteriormente, se tornando o valor "valido".

    d- Valor Pago: Esse será o valor que enviaremos para pagamento, ele é diferente do Valor Considerado, pois há algumas vezes em que a transportadora nos cobra um valor maior, porem o acerto desse valor será feito em um frete posterior, exemplo:
    Valor Cotado: R$ 5.000,00 (todos os pedidos do CNPJ X * tabela de um pedido do CNPJ X em uma carga fracionada)
    Valor CTe: R$ 7.000,00 (Valor cobrado pela transportadora)
    Valor Considerado R$ 5.000,00 (Nesse momento é possivel definir que a transportadora cobrou errado, pois consideramos o nosso valor)
    Valor Pago: R$ 7.000,00 (Negociamos para a transportadora abater os R$ 2.000,00 de diferença em um próximo frete )

6- Devemos criar uma "conta corrente" por transportadora, onde controlaremos as diferenças entre os valores pagos e os valores considerados, afim de cobrarmos as diferenças deles.

7- As conferencias serão registradas na proporção de 1 Fatura de frete (emitida pela transportadora) por N CTes de N CNPJs, incluir um campo para anexar o PDF da fatura de frete.

8- A tela de conferencia deverá ser por Fatura de frete e trazer os CNPJs e CTes daquela fatura (A base para conferencia e para cobrar a transportadora é emcima da fatura, mesmo que consideremos os fretes por CNPJ)
Para se conferir o frete, devemos lançar as nfs daquela fatura e os CTes daquela fatura.
Para os casos de mais do que 1 NF por CTe (ou seja mais do que 1 pedido / NF por CNPJ de um embarque), deveremos lançar 1 das nfs daquele CTe e o sistema deverá buscar o CNPJ e Embarque daquela transportadora com aquela NF e trazer as outras NFs daquele CNPJ naquele embarque (com isso garante que aquele CTe tenha as mesmas NFs daquele embarque para aquele cliente)

9- Os fretes deverão conter os numeros das NFs por frete (1 frete / N NFs), valor total, peso total, todos os campos da tabela do embarque/itens do embarque calculados emcima das informações das NFs do CNPJ daquele frete ( para os casos de carga fracionada serão calculados pelo valor e peso por CNPJ e para os casos de carga direta serão rateados pelo peso total por CNPJ).

10- No momento de lançar os CTes, os Valores Considerados deverão estar pré-preenchidos com os Valores Cotados.
O sistema deverá mostrar as diferenças dos Valores Cotados para os Valores dos CTes
Deverá haver um campo escrito "Desconsiderar diferença" onde o sistema irá considerar os Valores do CTe para os Valores Considerados (Para casos de pequenas variações para que com isso não gere diferença para a "conta corrente" da transportadora.)

11- É possivel haver mais do que 1 frete para a mesma NF, porem através de um outro embarque, portanto isso não deverá gerar problema, apenas para ter conhecimento.

12- Ao conferir a fatura, deverá ser possivel consultar todos os valores considerados naquele frete (no caso esses são os campos citados no item 9)

13- Há a possibilidade de um frete conter diversas despesas extras, cobradas através de CTe ou NFS (N despesas extras / 1 frete).
Essas despesas extras possuem: 
    a- Tipo de Despesa:
        REENTREGA
        TDE
        PERNOITE
        DEVOLUÇÃO
        DIARIA
        COMPLEMENTO DE FRETE
        COMPRA/AVARIA
        TRANSFERENCIA
        DESCARGA
        ESTACIONAMENTO
        CARRO DEDICADO
        ARMAZENAGEM

    b- Setor Responsavel:
        COMERCIAL
        QUALIDADE
        FISCAL
        FINANCEIRO
        LOGISTICA
        COMPRAS

    c- Motivo da Despesa:
        PEDIDO EM DESACORDO
        PROBLEMA NO CLIENTE
        SEM AGENDA
        DIVERGENCIA DE CADASTRO
        ARQUIVO XML
        FORA DO PADRÃO
        FALTA MERCADORIA
        ATRASO
        INVERSÃO
        EXCESSO DE VEICULO
        VAZAMENTO
        AUTORIZACAO INDEVIDA
        PROBLEMA NO BOLETO
        COLETA CANCELADA
        COLETA DE IMPROPRIOS
        EXIGENCIA TRANSPORTADORA
        AJUDANTE DESCARGA
        DEMORA COLETA
        COMPLEMENTO DE FRETE
        DIVERGENTE IMPOSTO NACOM
        ENTREGA 2° ANDAR
        ENTREGA NOTURNA
        CUSTO DO PRODUTO
        DEMORA RECEBIMENTO
        SEM MONITORAMENTO
        AVARIA

    d- Tipo do Documento: CTe, NFS, recibo etc.

    e- Numero do documento

    f- Valor da despesa

    g- Vencimento da despesa



