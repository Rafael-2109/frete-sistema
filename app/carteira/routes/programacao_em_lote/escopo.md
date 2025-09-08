# Projeto - Programação Redes SP em Lote
## Objetivo - Programar multiplas Redes situadas em SP de maneira otimizada através de analises e execuções em lote.
### Funcionalidades - Agrupamento de pedidos em carteira, em separação + NFs faturadas por CNPJ; Agendamento em lote feito por worker e enfileirado através de Redis; Verificação de protocolo no portal, preenchimento da data de expedição e envio pra separação seguindo regras especificas.

Utilize os locais/arquivo já criados conforme abaixo:
- Template principal: app/templates/carteira/programacao_em_lote.html
- Funções Python utilize a pasta app/carteira/routes/programacao_em_lote/  
- Funções JS utilize app/static/js/programacao_em_lote/

## 1ª etapa - CONCLUIDA
###- Front end:
Criar um botão no template: "app/templates/carteira/dashboard.html" (endpoint /carteira/) com nome "Clientes Rede SP"
Esse botão deverá renderizar um modal com os botões "Atacadão SP" e "Sendas SP".
Ao clicar deverá abrir uma tela para analise dos pedidos conforme descrito na 2ª etapa.

###- Back end:
Identificar os CNPJ que o prefixo se referem ao atacadao e sendas.
Unir os cnpj através de CarteiraPrincipal.cnpj_cpf + (Separacao.cnpj_cpf se sincronizado_nf=True e nf_cd=True)
Identificar pela função GrupoEmpresarial.identificar_portal(cnpj_cpf) onde "Atacadão" é portal=atacadao e "Sendas" é portal=sendas
Filtrar apenas os CNPJ onde cod_uf="SP"
Com isso terá uma relação dos CNPJ referente a Atacadão SP e Sendas SP através da CarteiraPrincipal.cnpj_cpf + os Separacao.cnpj_cpf das NFs que estiverem no CD e o cliente não possui pedidos na CarteiraPrincipal. 

## 2ª etapa - CONCLUIDA
- Extrair os dados de "Atacadão SP" e "Sendas SP" 
"através dos cnpj_cpf descobertos na CarteiraPrincipal, a API deverá formar uma tabela com 1 linha por CNPJ e os dados de cada dado do escopo da tabela que montei 1 embaixo do outro:

Linha 1:
cnpj 1
pedido 1
N Separação / NF no CD
pedido 2
N Separação / NF no CD
pedido 3
N Separação / NF no CD
N NF no CD s/ Cart.

Linha 2:
cnpj 2
pedido 1
N Separação / NF no CD
pedido 2
N Separação / NF no CD
pedido 3
N Separação / NF no CD
N NF no CD s/ Cart.

Tabela

Cabeçalho da tela: (campos iguais dentro da seleção que fizemos, pode pegar ""first"")
""Atacadão"" ou ""Sendas""
CarteiraPrincipal.cod_uf
CarteiraPrincipal.vendedor
CarteiraPrincipal.equipe_vendas

Embaixo do cnpj colocar cada num_pedido correspondente.
### A lista de num_pedido será através da CarteiraPrincipal + Separacao.sincronizar_nf=True e Separacao.nf_cd=True(casos que não tenha mais pedido na carteira, apenas faturados)
Embaixo de cada num_pedido colocar ""Separação"" para cada Separacao.separacao_lote_id filtrando Separacao.sincronizar_nf=False e tambem colocar ""NF no CD"" onde Separacao.sincronizar_nf=True e Separacao.nf_cd=True.

No template montar os dados considerando:

for cnpj in cnpjs (N):
- Dados do cnpj_cpf com totais.
Totais: CarteiraPrincipal.cnpj_cpf + Separacao.cnpj_cpf(Separacao.nf_cd==True, Separacao.num_pedido not in CarteiraPrincipal.num_pedido)
### Quando Separacao.num_pedido[Separacao.sincronizado_nf=True, Separacao.nf_cd=True] not in CarteiraPrincipal.num_pedido, pegar valores de FaturamentoProduto.valor_produto_faturado através da pesquisa de Faturamento.numero_nf em Separacao.numero_nf, para peso e pallet usar qtd_produto_faturado e CadastroPalletizacao

Dados:
""Total""
CarteiraPrincipal.cnpj_cpf # CNPJ do cliente
CarteiraPrincipal.raz_social_red # Nome reduzido
CarteiraPrincipal.nome_cidade # Cidade extraída
CarteiraPrincipal.sub_rota # Sub-rota baseada em cod_uf + nome_cidade
Valores de CarteiraPrincipal + NF no CD quando num_pedido NOT IN CarteiraPrincipal:
Valor: qtd * preco_produto_pedido
Peso: CadastroPalletizacao.peso_bruto * qtd
Pallets: qtd / CadastroPalletizacao.palletizacao

----------------------------------------

for pedido in cnpj(1-N):

Dados:
""Pendente""
CarteiraPrincipal.data_pedido # Data de criação
CarteiraPrincipal.pedido_cliente # Pedido de Compra do Cliente
CarteiraPrincipal.num_pedido # Chave principal
CarteiraPrincipal.observ_ped_1 # Observações
pedido = CarteiraPrincipal.num_pedido(
CarteiraPrincipal.cnpj_cpf==cnpj)
for produto in pedido:
qtd_pendente =CarteiraPrincipal.qtd_saldo_produto_pedido - SUM(Separacao.qtd_saldo) WHERE (Separacao.num_pedido == CarteiraPrincipal.num_pedido, Separacao.sincronizado_nf==False)
Valor: qtd_pendente * preco_produto_pedido
Peso: qtd_pendente * CadastroPalletizacao.peso_bruto
Pallets: qtd_pendente / CadastroPalletizacao.palletizacao

-----------------------------------------

for separacao in pedido(1-1-N):

Dados:
""Em Separação""
status
separacao_lote_id
Separacao.expedicao # Data programada para expedição
Separacao.agendamento # Data da agenda
Separacao.agendamento_confirmado # Flag para confirmação de agendamento
Separacao.protocolo # Protocolo de agendamentoseparacao=Separacao.separacao_lote_id (
Separacao.num_pedido==pedido,
Separacao.sincronizado_nf==False)
for produto in separacao:
Sum(Separacao.valor_saldo)
Sum(Separacao.pallet)
Sum(Separacao.peso)

---------------------------------------

for nf_cd in pedido(1-1-N):

Dados:
""NF no CD""
Separacao.status
Separacao.numero_nf
Separacao.expedicao # Data programada para expedição
Separacao.agendamento # Data da agenda
Separacao.agendamento_confirmado # Flag para confirmação de agendamento
Separacao.protocolo # Protocolo de agendamento
nf_cd_carteira = sum(FaturamentoProduto.valor_produto_faturado) in(
Separacao.numero_nf == FaturamentoProduto.numero_nf,
Separacao.num_pedido == CarteiraPrincipal.num_pedido,
Separacao.sincronizado_nf==True)
for produto in nf_cd_carteira:
Sum(Separacao.valor_saldo)
Sum(Separacao.pallet)
Sum(Separacao.peso)

-------------------------------------

for nf_cd not in pedido(1-1-N):

Dados:
""NF no CD s/ Cart.""
Separacao.status
Separacao.numero_nf
Separacao.expedicao # Data programada para expedição
Separacao.agendamento # Data da agenda
Separacao.agendamento_confirmado # Flag para confirmação de agendamento
Separacao.protocolo # Protocolo de agendamento
nf_cd_fora_carteira = sum(FaturamentoProduto.valor_produto_faturado) in(
Separacao.numero_nf == FaturamentoProduto.numero_nf,
Separacao.num_pedido NOT IN CarteiraPrincipal.num_pedido,
Separacao.sincronizado_nf==True)
for produto in nf_cd_fora_carteira:
Sum(Separacao.valor_saldo)
Sum(Separacao.pallet)
Sum(Separacao.peso)"

## 3ª etapa
- Agora preciso verificar uma data possivel de envio total de cada pedido assim como o % de disponibilidade para envio imediato.
- Essa função é chamada através de app/templates/carteira/js/ruptura-estoque.js em analisarRuptura que chama a API "const response = await fetch(`/carteira/api/ruptura/sem-cache/analisar-pedido/${numPedido}`);" localizado em app/carteira/routes/ruptura_api_sem_cache.py

- Porem há uma grande diferença pois como tratamos clientes de rede, há normalmente 100/150 lojas com pedidos de valores não tão altos, diante disso o propósito dessa tela é de automatizar a analise de estoque para um grande numero de lojas e fazer o sistema nos ajudar e automatizar as etapas necessarias para realizarmos a separação e agendamento em lote porem considerando algumas regras especificas:
1 - O sistema deverá considerar as datas possiveis para expedição apenas 2ª, 3ª, 4ª e 5ª feira, em que se confirmado a expedicao, deverá preencher a data de agendamento automaticamente para D+1 da data de expedição (nesse caso as agendas ficariam 3ª, 4ª, 5ª e 6ª feira)
2- O sistema deverá limitar a 30 cnpjs por dia por Rede (no caso a seleção entre Assai e Atacadão)
3- O sistema deverá considerar a mesma forma de analise de "/carteira/api/ruptura/sem-cache/analisar-pedido/${numPedido}" porem sempre considerando o pedido anterior, por exemplo:
O sistema de ruptura considera estoque, Separação, ProgramacaoProducao, porem deverá considerar em todos os pedidos onde "ID>1" o pedido anterior respeitando a expedicao do pedido anterior, ou seja, nomeando Separação de "saida", falando apenas da "saida" sempre será:
ID 1 -> saida = Total de separações até a data que o sistema informar que esse pedido estará completo
ID 2 -> saida = Separações + ID 1
ID 3 -> saida = Separações + ID 1 + ID 2
Assim por diante...
4- Diante dos pedidos de rede serem dos mesmos itens, com algumas minimas diferenças, pensei em no topo ter um botão "analisar estoques" onde abrirá através de um dropdown, uma listagem dos itens contidos nesses CNPJ, somatória dos CarteiraPrincipal.qtd_saldo_produto_pedido, SUM(CarteiraPrincipal.preco_produto_pedido*CarteiraPrincipal.qtd_saldo_produto_pedido por CarteiraPrincipal.num_pedido *preços podem varias de pedido para pedido, por isso a somatória é por pedido) dos CNPJs da rede, data onde o saldo de estoque será maior que essa somatória e a projeção de estoque dos próximos 15 dias para cada Item DESCONSIDERANDO OS PEDIDOS DESSA REDE para não duplicar as saidas. O objetivo dessa analise é ver quais itens estão "prorrogando" a data de disponibilidade, o impacto financeiro da "saida com falta" desses itens.
5- Retire a coluna de "Vendedor" e "Pedidos" juntamente com o contador e adicione no CABEÇALHO DA PÁGINA na frente de "Programação em Lote - Sendas SP", ficando "Programação em Lote - Sendas SP - {vendedor} - {equipe_vendas}" e diminua um pouco o tamanho da letra porem mantenha o negrito.
No lugar dessas colunas adicione o botão de analise de estoque, campo para preenchimento de data para expedicao e agendamento e ao lado do agendamento um relógio para caso haja protocolo em todas as Separações / NF no CD do cliente e as datas de agendamento sejam futuras e agendamento_confirmado = False e não haja saldo do pedido que não esteja em Separacao e mantenha a linha na cor original, caso agendamento_confirmado = True mantenha um "check" verde e a linha levemente azul, caso tenha algum agendamento < hoje ou alguma Separacao.protocolo = '', pinte a linha de amarelo clarinho alguma Separação mantendo a apresentação em 1 linha e os campos de data serem "preenchiveis" ou selecionado pelo "mini calendario" direto na página
6- Pode retirar toda aquela seção dos filtros.
7- Adicionar um botão com "sugerir datas" onde esse botão deverá preencher as datas de expedicao e agendamento seguindo as regras dos itens "1, 2 e 3".
8- Se for possivel, ao lado do botão de "analise de ruptura" de cada pedido, acrescentar um botão chamado "Priorizar" onde deverá mover o pedido clicado para 1º da lista, recalculando os estoque e as datas de disponibilidade considerando a nova "ordem".



## Status da Implementação (08/09/2025):

### ✅ Problemas Resolvidos:

1. **Arquivos obsoletos removidos:**
   - ❌ `app/templates/carteira/js/programacao_em_lote/main.js` 
   - ❌ `app/templates/carteira/js/programacao_em_lote/main_v3.js`
   - ✅ Agora usa apenas: `app/static/js/programacao-lote.js`

2. **Blueprint registrado corretamente:**
   - ✅ Blueprint `programacao_em_lote_bp` registrado em `app/carteira/routes/__init__.py`
   - ✅ Rotas API funcionando corretamente:
     - `/carteira/programacao-lote/api/analisar-estoques/<rede>`
     - `/carteira/programacao-lote/api/sugerir-datas/<rede>`

3. **Botão de análise de ruptura corrigido:**
   - ✅ Agora abre modal detalhado similar ao da carteira agrupada
   - ✅ Mostra tabela com itens em ruptura
   - ✅ Exibe resumo com disponibilidade, data completa, valor total e criticidade

### ⚠️ Pendências para verificar:

1. **Botão "Analisar Estoques":**
   - Verificar se a API `/api/analisar-estoques/<rede>` está retornando dados corretos
   - Pode precisar ajustes na função de análise de estoque em lote

2. **Botão "Sugerir Datas":**
   - Verificar se a API `/api/sugerir-datas/<rede>` está processando corretamente
   - Pode precisar validação dos dados enviados pelo frontend

### 📝 Notas de Implementação:

- Template principal: `app/templates/carteira/programacao_em_lote.html`
- JavaScript principal: `app/static/js/programacao-lote.js`
- Rotas Python: `app/carteira/routes/programacao_em_lote/routes.py`
- Blueprint: `programacao_em_lote_bp` com url_prefix `/carteira/programacao-lote`


