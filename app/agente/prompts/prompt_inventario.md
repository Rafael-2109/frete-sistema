/superpowers:brainstorming

Realizamos um inventario na data de ontem na NACOM e na LA FAMIGLIA e preciso realizar os ajustes de estoque seguindo <regras>, <tipo_produtos> e <ordem> das operações por <empresas>.

Avalie o prompt abaixo para realizarmos esse trabalho extenso.

<empresas>
  - NACOM GOYA - Filiais FB(Matriz - Fabrica), CD(Filial 0003 - Centro de Distribuição) e SC(Filial 0002 - Santa Catarina)
  - LA FAMIGLIA - Sem filiais
  <contexto_lf>
    A LA FAMIGLIA é uma empresa do grupo que presta serviço de industrialização para a NACOM GOYA, portanto:
    1- Ajustes de estoque na LA FAMIGLIA deverão ser realizados através de NF entre NACOM GOYA e LA FAMIGLIA respeitando o tipo de produto.
  </contexto_lf>
</empresas>

<tipo_produtos>
  Os tipos dos produtos são determinados pelo primeiro digito do codigo do produto.
  Nesse inventario estaremos tratando os produtos com codigo iniciados em [1,2,3,4]
  Numero | Tipo:
  1 | Insumos/Matéria Prima
  2 | Embalagens
  3 | Produtos intermediarios
  4 | Produtos acabados

  <exemplos>
    código = 101001001 
    nome = COGUMELO FATIADO - IND
    inicio = 1
    tipo = Matéria Prima

    código = 301000002
    nome = SALMOURA AZEITONA PRETA PADRAO
    inicio = 3
    tipo = Produto Intermediario

    código = 4030162
    nome = PICLES - BD 6X2 KG - CAMPO BELO
    inicio = 4
    tipo = Produto acabado
  </exemplos>
</tipo_produtos>

<regras>
  <ordem=1 forma="por nf entre FB e LF">
    <ajustes_lf aplicavel_a="produtos tipo[1,2,3]">
      1- Ajustes de estoque negativo na empresa LA FAMIGLIA serão realizados emitindo NF de Retorno de não aplicado de volta para a NACOM GOYA - FB
      2- Ajustes de estoque positivo na empresa LA FAMIGLIA serão realizados emitindo NF de Remessa para industrialização da empresa NACOM GOYA - FB para LA FAMIGLIA
      3- Ajustes de estoque negativo na empresa LA FAMIGLIA serão realizados emitindo NF de Produto não aplicado (Perda).
    <ajustes_lf aplicavel_a="produtos tipo[4]">
      1- Ajustes de estoque de produtos acabados na empresa LA FAMIGLIA serão realizados através de Devolução de Industrialização (bi-direcional)
    </ajuste_lf>
  </ordem=1>

  <ordem=2 forma="transferir ajustes para empresas responsaveis">
    <ajustes_fb_cd>
      1- Os produtos acabados na FB deverão ser ajustados através de NF de transferencia entre CD e FB, mantendo na FB apenas os produtos acabados inventariados na FB e as diferenças jogar pro CD.
      2- Os outros produtos no CD deverão ser ajustados através de NF de transferencia entre CD e FB, mantendo no CD apenas os outros produtos [1,2,3] inventariados no CD e as diferenças jogar pra FB
      <estado_final> 
      FB com estoque de produto acabado [4] de acordo com inventario
      CD com estoque dos outros produtos [1,2,3] de acordo com inventario.
      </estado_final>
      Os outros produtos [1,2,3] na FB, serão tratados em "ordem=3"
      OS produtos acabados [4] no CD, serão tratados em "ordem=3"
    </ajuste_fb_cd>
  </ordem=2>

  <ordem=3 forma="avaliar opções para ajustes negativos e positivos">
    Afim de separar o ajuste no estoque e avaliações do impacto nos relatórios contabeis e no custo, precisamos realizar os ajustes através da segregação do estoque "fantasma" e do estoque real.
    Com isso, pensei em algumas opções alternativas de ajuste que não gerem impacto no balanço mas mantenha uma separação deterministica para não impactar na operação.
    As opções são sequenciais, ou seja, se a opção 1 for viavel, será a utilizada, caso não funcione, iremos para a opção 2.
    <opção_1="indisponibilização por lote">
      <objetivo>
        Indisponibilizar algum lote e verificar se é exibido como opção para o faturamento.
      </objetivo>
      Caso haja opção de indisponibilizar o lote e essa indisponibilização proiba e esconda esse lote na hora do faturamento, seguiremos essa opção.
    </opção_1=>
    <opção_2="por local">
      <objetivo>
        Caso a indisponibilização por lote não funcione, iremos tentar por local.
        Indisponibilizar algum local de estoque e verificar se é exibido como opção para o faturamento.
      </objetivo>
      Caso haja opção de indisponibilizar o local de estoque e essa indisponibilização proiba e esconda esse lote na hora do faturamento, seguiremos essa opção.
    </opção_2>
  </ordem_3>
  
  <conhecimento_necessario>
    Para realizar as operações que envolvem faturamento, preciso que:
    1- Estude o serviço de recebimento da LF afim de que compreenda o fluxo, gotchas e campos necessarios para realizar o faturamento e recebimento.
    2- Estude a criação de um picking.
    3- Valide cada detalhe da emissão da NF, operação extremamente sensivel.
    3.1 Saiba alterar os tipos de faturamento: 
    account.move
    move_type in ['entry', 'in_invoice', 'out_refund']
    l10n_br_tipo_pedido
    [
      "industrializacao;Saída: Remessa p/ Industrialização",
      "transf-filial;Saída: Transferencia entre Filiais",
      "perda;Saída: Perda",
      "dev-industrializacao;Saída: Devolução de Industrialização"
      ]
    3.2- Entenda como e quando aplica-los assim como o CFOP que deverá ser utilizado:
    - "industrializacao" - Saída da FB para LF de produtos [1,2,3] CFOP [5901]
    Ex: NF 94457
    - "perda" - Saída da LF para FB de produtos [1,2,3] CFOP [5903]
    Ex: NF 13075
    - "dev-industrializacao" - Saída entre [FB,LF] de produto [4] CFOP [5949]
    Ex: NF 147772
    - "transf-filial" - Transferencia entre [CD,FB] CFOP [5152]
    Ex: NF 94410
  </conhecimento_necessario>

  <workflow>
    A ordem da realização desses ajustes será através do seguinte workflow:
    1- Estudo do serviço de recebimento da LF
    2- Extração do relatório de estoque da NACOM GOYA [FB,CD] (não trataremos SC inicialmente) e LA FAMIGLIA.
    3- Confronto entre inventario X estoque, sendo inventario = quantidade contada no inventario e estoque = estoque lançado no Odoo.
    Confronto deverá levar em consideração o lote dos produtos para propor os ajustes.
    4- Avaliação da proposta de ajustes.
    5- Relatório das movimentações necessarias e sequenciamento por tipo de saida, empresa e tipo de produto.
    6- Aprovação das movimentações (mesmo que deterministico, preciso validar as movimentações que serão realizadas junto com o "posição estoque alvo").
    7- Para cada tipo de movimentação deverá ter como referencia 1 NF para validar os campos.
    8- Verificação de todos os campos na emissão da NF possuidos X da NF referencia.
    9- Realize 1 movimentação pequena para validação e aprovação.
    10- Operações sem possibilidade de rollback deverão ser aprovadas. 
  </workflow>

  <regras_inviolaveis>
    **IMPORTANTE**
    Todas as decisões deverão ser documentadas.
    Todo o progresso deverá ser documentado.
    A documentação deverá ser organizada em pastas com arquivos atomicos.
    Se necessario, implemente as regras_inviolaveis em forma de hook deterministico.
    Não assuma nada, qualquer duvida deverá ser questionada e documentada.
    Registre GOTCHAS sempre que descoberto.
    Em caso de estoque no lote 1 e inventario no lote 2, faça alteração do lote no produto se possivel.
  </regras_inviolaveis>
</regras>

<estado_desejado>
  1- Estoque disponivel e visivel ajustado com base no inventario.
  2- Conhecimento de todo esse trabalho persistido e reutilizavel.
  2.1- Não documente de maneira especifica o que é reutilizavel, documente com propósito de ser aplicavel em outras ocasiões.
  3- Documentação de todas as etapas e movimentações realizadas.
  4- Quantidades a serem ajustadas contabilmente segregada deterministicamente e invisivel no faturamento para posterior ajuste contabil.
</estado_desejado>