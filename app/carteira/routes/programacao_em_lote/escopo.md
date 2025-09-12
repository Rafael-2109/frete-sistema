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

## Definição do status Ao lado do agendamento poderá haver alguns status:

### Status 1 - "Ag. Aprovação"
- Aguardando aprovação do agendamento.
-> Exibir Relógio 
-> Exibir a linha na cor azul

Condições:

- Haja protocolo em todas as Separações / NF no CD do cliente
- As datas de agendamento sejam futuras
- Agendamento_confirmado = False
- Não haja saldo do pedido que não esteja em Separacao


### Status 2 - "Pronto"
- Aguardando embarque e entrega
-> Exibir "check" verde
-> Exibir a linha na cor verde

Condições:

- Haja protocolo em todas as Separações / NF no CD do cliente
- As datas de agendamento sejam futuras
- Agendamento_confirmado = True
- Não haja saldo do pedido que não esteja em Separacao


### Status 3 - "Reagendar"
- Necessario reagendar
-> Exibir a linha na cor vermelha

Condições obrigatórias:

- Caso tenha algum agendamento preenchido < hoje


### Status 4 - "Consolidar"
- Necessario consolidar
-> Exibir sinal de atenção
-> Exibir a linha na cor amarela

Condições obrigatórias:

- As datas de agendamento que estiverem preenchidas sejam futuras

Condições opcionais ("ou", qualquer uma dispara o status 4):

- Haja protocolo porem não em todas as Separações / NF no CD do cliente
- Haja protocolo em todas as separações porem não são iguais
- Haja saldo pendente sem separação porem que não seja o total do CNPJ


### Status 5 - "Pendente"
- Total Pendente
-> Manter a linha na cor original

Condições opcionais: 

- Não haja Separação e nem NF no CD
- Não haja protocolo em nenhuma Separação ou NF no CD

## Integração das funções:

1- Arquivos envolvendo programacao)lote:

- Template principal: app/templates/carteira/programacao_em_lote.html
- Funções Python utilize a pasta app/carteira/routes/programacao_em_lote/  
- Funções JS utilize app/static/js/programacao_em_lote/

2- Arquivos envolvendo download da planilha + preenchimento da planilha

- Função de download da planilha de agendamento: app/portal/sendas/consumir_agendas.py
- Função de preenchimento da planilha de agendamento: app/portal/sendas/preencher_planilha.py

### Fluxo de agendamento

1- Usuario acessa /carteira/programacao-lote/listar/{portal}
2- Clica em "Sugerir Datas"
3- Sistema preenche as datas de Expedição e Agendamento seguindo as regras implementadas.
4- Usuario marcar os "Checkbox" desejados

Até o passo 4 já existe no sistema, os passos que precisam ser verificados se existem colocarei um "*" ao lado do passo

5*- Usuario clicar em "Agendar Selecionados" (Existe o botão, precisa confirmar a funcionalidade)
6*- Sistema identifica que o portal é do Sendas
7- Sistema baixa a planilha do Sendas através de app/portal/sendas/consumir_agendas.py
8*- Sistema preenche utiliza a data de "agendamento" da planilha preenchido através do botão "Sugerir Datas" das linhas com checkbox marcados. (Acabamos de realizar o teste de preenchimento da planilha)
9*- Após o preenchimento, o sistema deverá fazer "Upload" no portal do Sendas localizado ao lado do botão dropdown "Download Planilha / Todos itens"(botão utilizado para baixar a planilha) chamado "Upload da planilha".
10*- O sistema poderá fazer upload de 2 maneiras, arrastando o arquivo da planilha preenchida para a área citada abaixo ou clicar na área, selecionar o arquivo e realizar o upload.
11*- Após realizar o Upload, deverá gerar Separação para todos os pedidos que estiverem pendentes e marcar a data de expedição / agendamento / protocolo de cada Separação de acordo com os valores utilizados na agenda e provisóriamente gravar a "observacao_unica"(campo do arquivo app/portal/sendas/preencher_planilha.py) no campo de protocolo

Botão Upload da planilha:
" <button type="button" class="upload-button rs-btn rs-btn-default"><svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M14.5586 7.08984C13.7198 7.08984 13.0608 7.78004 13.0608 8.65847V11.2938C13.0608 12.1722 12.4018 12.8624 11.563 12.8624H4.4934C3.65463 12.8624 2.9956 12.1722 2.9956 11.2938V8.65847C2.9956 7.78004 2.33657 7.08984 1.4978 7.08984C0.659032 7.08984 0 7.78004 0 8.65847V11.2938C0 13.8663 2.03701 15.9996 4.4934 15.9996H11.5031C13.9595 15.9996 15.9965 13.8663 15.9965 11.2938V8.65847C16.0564 7.84279 15.3375 7.08984 14.5586 7.08984Z" fill="#3A84FF"></path><path d="M6.17126 5.58431L6.53073 5.20784V9.16079C6.53073 10.0392 7.18976 10.7294 8.02853 10.7294C8.8673 10.7294 9.52633 10.0392 9.52633 9.16079V5.27059L9.8858 5.64706C10.1854 5.96078 10.5448 6.08627 10.9642 6.08627C11.3836 6.08627 11.7431 5.96078 12.0426 5.64706C12.6418 5.01961 12.6418 4.01569 12.0426 3.45098L9.16686 0.439216C8.8673 0.12549 8.50783 0 8.08844 0C7.66906 0 7.30959 0.188235 7.01003 0.439216L4.07434 3.38824C3.47522 4.01569 3.47522 5.01961 4.07434 5.58431C4.67346 6.21177 5.57214 6.21177 6.17126 5.58431Z" fill="#3A84FF"></path></svg>Upload da planilha<span class="rs-ripple-pond"><span class="rs-ripple" style="width: 3261.6px; height: 3261.6px; left: -1288.8px; top: -1231.8px;"></span></span></button>)"

Área para "arrastar" ou clicar:
<div id="dropzone-external"><div id="dropzone-text" class="flex-box"><div class="dropzone-icons-container"><div><svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#C3C3C7"></circle><path fill-rule="evenodd" clip-rule="evenodd" d="M25.4696 11.3358C25.4696 12.2411 25.1271 13.0883 24.5054 13.7211C24.4406 13.7869 24.357 13.8197 24.273 13.8197C24.1868 13.8197 24.1005 13.7847 24.0352 13.7153C23.907 13.5785 23.9093 13.3593 24.0407 13.2258C24.5332 12.7242 24.8046 12.0529 24.8046 11.3355C24.8046 9.87824 23.6665 8.69256 22.2677 8.69256C20.8689 8.69256 19.7311 9.87824 19.7311 11.3355C19.7311 12.0414 19.9949 12.7053 20.4743 13.2044C20.6041 13.3397 20.6041 13.5591 20.4743 13.6943C20.3445 13.8293 20.1339 13.8293 20.0041 13.6943C19.3994 13.064 19.0663 12.2264 19.0663 11.3355C19.0663 9.49631 20.5026 8 22.2677 8C24.0328 8 25.4696 9.49631 25.4696 11.3358ZM10.5877 19.9771C10.4133 19.9161 10.2253 20.0137 10.1668 20.1948C10.0561 20.5371 10 20.8953 10 21.2594C10 21.5277 10.0307 21.7949 10.091 22.0525C10.1282 22.2107 10.2641 22.3167 10.4135 22.3167C10.4398 22.3167 10.4663 22.3135 10.4927 22.3069C10.6711 22.2615 10.7804 22.0741 10.7369 21.8884C10.6889 21.6843 10.6648 21.4728 10.6648 21.2594C10.6648 20.9704 10.7091 20.6866 10.7967 20.4155C10.8552 20.2344 10.7615 20.038 10.5877 19.9771ZM12.8458 23.8767C12.3237 23.8005 11.8443 23.5598 11.4596 23.1809C11.3267 23.0497 11.1161 23.0555 10.9897 23.1945C10.8635 23.3336 10.8696 23.553 11.0028 23.6841C11.4885 24.1625 12.094 24.4663 12.7535 24.5624C12.7692 24.5649 12.7847 24.566 12.7999 24.566C12.963 24.566 13.1054 24.4409 13.1288 24.2676C13.1544 24.078 13.0275 23.9032 12.8458 23.8767ZM16.0215 21.914C15.8484 21.8515 15.6588 21.9468 15.5985 22.1274C15.4149 22.6774 15.0549 23.1563 14.5847 23.4756C14.431 23.58 14.3875 23.7945 14.4877 23.9548C14.5514 24.0567 14.6579 24.1119 14.7664 24.1119C14.8286 24.1119 14.8918 24.0939 14.9476 24.0556C15.5408 23.6529 15.9947 23.0489 16.2263 22.3547C16.2866 22.1741 16.1948 21.9766 16.0215 21.914ZM14.9104 18.4387C14.7551 18.3365 14.5498 18.3846 14.4517 18.5463C14.3537 18.708 14.3998 18.922 14.5551 19.0241C15.0085 19.323 15.3664 19.773 15.5623 20.291C15.614 20.4273 15.7391 20.5103 15.8717 20.5103C15.9121 20.5103 15.9536 20.5027 15.9934 20.4863C16.1641 20.4161 16.2481 20.215 16.1807 20.0369C15.9334 19.3831 15.4823 18.8157 14.9104 18.4387ZM12.5308 17.9977C11.9185 18.1335 11.3618 18.4523 10.9205 18.919C10.7914 19.0553 10.7933 19.2747 10.9239 19.4088C10.9886 19.4752 11.0728 19.5082 11.1573 19.5082C11.2433 19.5082 11.329 19.4738 11.3941 19.405C11.7439 19.0351 12.185 18.7826 12.6696 18.6747C12.8492 18.6348 12.9638 18.451 12.9255 18.2638C12.887 18.0767 12.7092 17.9562 12.5308 17.9977ZM16.0944 18.4944L17.0038 17.3789C17.1226 17.2333 17.1056 17.0148 16.9655 16.891C16.8252 16.767 16.616 16.7844 16.4969 16.9309L15.5875 18.0464C15.4684 18.192 15.4857 18.4105 15.6255 18.5343C15.6882 18.5897 15.7645 18.6168 15.8405 18.6168C15.9349 18.6165 16.0286 18.5753 16.0944 18.4944ZM17.95 15.1485L17.2781 15.9725C17.1593 16.1181 17.1764 16.3367 17.3164 16.4604C17.3791 16.5159 17.4554 16.5429 17.5314 16.5429C17.6256 16.5429 17.7192 16.5017 17.785 16.4208L18.4569 15.5968C18.5757 15.4512 18.5586 15.2327 18.4186 15.1089C18.2786 14.9846 18.069 15.0024 17.95 15.1485ZM18.6006 14.8854C18.663 14.9409 18.7396 14.9679 18.8156 14.9679C18.9098 14.9679 19.0034 14.9267 19.0692 14.8458L19.6524 14.1306C19.7712 13.985 19.7542 13.7664 19.6141 13.6427C19.4744 13.5186 19.2646 13.5361 19.1455 13.6825L18.5623 14.3978C18.4435 14.5431 18.4606 14.7617 18.6006 14.8854ZM29.9169 20.9445C29.8437 20.2341 29.2028 19.7039 28.6558 19.7339C28.375 19.7492 28.3319 19.9511 28.3319 19.9511V22.3607C28.3319 22.438 28.2821 22.5014 28.2215 22.5014C28.1607 22.5014 27.8581 22.438 27.8581 22.3607V19.2924C27.8581 19.2924 27.8694 19.1402 27.7959 19.0372C27.4414 18.5406 26.6639 18.4794 26.3395 18.5551C26.1787 18.5928 26.1903 18.8067 26.1903 18.8067V21.8627C26.1903 21.94 25.8876 22.0034 25.8268 22.0034C25.766 22.0034 25.7164 21.94 25.7164 21.8627V18.6996C25.7164 18.6996 25.7125 18.4652 25.5221 18.3739C25.1791 18.2095 24.4388 18.1209 24.2025 18.1108C24.0218 18.1032 24.0134 18.2635 24.0134 18.2635V20.8874C24.0134 20.9647 23.9636 21.028 23.903 21.028C23.8424 21.028 23.5396 20.9647 23.5396 20.8874L23.4142 12.6206C23.3675 11.8734 22.8929 11.3101 22.3952 11.3101C22.0765 11.3101 21.3439 11.5259 21.2786 12.9862C21.245 15.7288 21.2424 19.6694 21.1897 21.8307C21.1726 21.7646 20.753 20.2492 20.7368 20.1844C20.6935 18.4725 19.2368 17.1612 18.1131 17.3486C17.8118 17.3983 17.9141 17.3814 18.3394 21.831C18.3412 21.849 19.8703 27.3185 21.085 29.3748C21.1642 29.5374 21.1566 31.3596 21.181 31.4738C21.2513 31.8008 21.5159 31.9959 21.8893 31.9959C21.905 31.9959 27.8775 32 28.0503 32C28.4497 32 29.1299 31.7416 29.1596 31.3252C29.1774 31.073 29.206 29.227 29.2264 29.109C29.6777 26.5065 30.2075 23.7622 29.9169 20.9445Z" fill="white"></path></svg></div><div><p id="dropzone-message">Arraste o arquivo do seu computador e solte aqui para fazer upload</p></div></div><div class="divider-dropzone-container"><div id="divider-icon"><svg width="73" height="2" viewBox="0 0 73 2" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="0.5" y="0.5" width="72" height="1" fill="#A4A4AC"></rect></svg></div><p id="divider-message">ou</p><div id="divider-icon"><svg width="73" height="2" viewBox="0 0 73 2" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="0.5" y="0.5" width="72" height="1" fill="#A4A4AC"></rect></svg></div><div></div></div><div class="dropzone-icons-container"><div><svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="20" r="20" fill="#C3C3C7"></circle><path fill-rule="evenodd" clip-rule="evenodd" d="M29.9098 19.5706C29.9932 19.1638 30.0373 18.7428 30.0373 18.3116C30.0373 14.8258 27.177 12 23.6487 12C21.0322 12 18.7842 13.5549 17.7965 15.7798C17.0376 15.2913 16.1333 15.0049 15.1601 15.0049C12.6013 15.0049 10.5116 16.9681 10.3373 19.4523C8.95914 20.0771 8 21.4489 8 23.0451C8 25.2293 9.7923 27 12.0031 27C12.0031 27 16.34 27 17.7855 27C18.069 27 18.0828 26.6892 18.0828 26.6892V24.1519C18.0828 23.9351 17.9033 23.7578 17.6839 23.7578H16.59C16.3706 23.7578 16.2979 23.6153 16.4286 23.4412L19.7626 18.9947C19.8932 18.8205 20.1069 18.8205 20.2375 18.9947L23.5715 23.4412C23.702 23.6153 23.6294 23.7578 23.4101 23.7578H22.3161C22.0969 23.7578 21.9172 23.9351 21.9172 24.1519V26.6942C21.9172 26.6942 21.9339 27 22.2275 27C23.6699 27 27.9969 27 27.9969 27C30.2077 27 32 25.2293 32 23.0451C32 21.5456 31.1549 20.2411 29.9098 19.5706Z" fill="white"></path></svg></div><div><p id="dropzone-message">Faça upload do arquivo clicando aqui</p></div></div></div></div>

