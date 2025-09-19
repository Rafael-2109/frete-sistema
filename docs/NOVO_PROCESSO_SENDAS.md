Preciso refatorar o sistema de agendamento do portal do Sendas.
Atualmente há 3 fluxos, sendo eles:
Fluxo 1- Agendamento em lote
Fluxo 2- Agendamento por Separação
Fluxo 3- Agendamento por NF

Hoje esses fluxos captam as informações dos pedidos a serem agendados corretamente e enviam para uma fila workers.
Esses workers:
- Acessam o portal do Sendas
- Baixam a planilha modelo
- Abrem ela através do libreoffice devido a exportação do portal enviar uma planilha "quebrada"
que só é ajustada no momento que ocorre um "abre e fecha da planilha" por um excel e o
libreoffice foi o unico que conseguiu consertar a planilha, xlsx, openpyxl e panda já testei e
não funcionou.
- Filtram as lojas/pedido/produto a serem agendados
- Preenchem com as informações recebidas (Informações dos pedidos / produto / filial / protocolo inicial)
- Apagam as linhas desconsideradas.
- Salva o arquivo preenchido.
- Acessam o modal de "Upload".
- Por ultimo enviam a planilha nesse modal.

Devido a exaustivas tentativas de mascarar o playwright no Render por ser headless=true, decidi fazer parte automatizada e parte manual.

O processo que quero implantar agora consiste em 4 etapas.
Essas etapas deverão ser criadas POR ETAPAS, criando a primeira etapa, validando e depois seguindo para as demais:

1- Recepção da planilha modelo
2- Solicitação de agendamento
3- Exportação da planilha adequada
4- Verificação das agendas

Abaixo irei detalhar cada etapa que pretendo implantar e como deve funcionar o processo:

1- Recepção da planilha modelo:
A planilha modelo contem toda a disponibilidade que temos para agendar no portal.
Dessa forma precisamos gravar no sistema o conteudo para que possa ser usado na exportação da planilha com as agendas que queremos agendar.
Essa planilha será importada pelo sistema diariamente para atualizar a base das agendas disponiveis.

2- Solicitação de agendamento:
A solicitação de agendamento ocorrerá através do registro do agendamento solicitado em FilaAgendamentoSendas.
Em FilaAgendamentoSendas haverá 3 origens possiveis:
- NF (Se refere a solicitação vindo do monitoramento "Fluxo 3")
- Separação (Se refere a solicitação vindo da Separação na carteira "Fluxo 2")
- Lote (Se refere a solicitação vindo da página de programação em lote "Fluxo 1")

Dessa forma o usuario preenche a data de agendamento em uma das 3 telas, o sistema compara a solicitação com a disponibilidade (planilha modelo) convertendo os campos do sistema para o padrão do Sendas, e devolve uma avaliação considerando a filial, pedido do cliente e produto que queremos agendar (Nessa avaliação, utilize os nossos padrões, ou seja, converta o padrão do Sendas para o nosso).
Essa avaliação deverá comparar e mostrar o que estamos querendo agendar X o que tem disponivel na planilha através da filial.

Caso não encontre o pedido no portal mas encontre a filial, informar o usuario e perguntar se deseja agendar todo saldo dessa filial, se ele aceitar, envie todo "Saldo disponível" para FilaAgendamentoSendas convertendo os dados da planilha modelo para o nosso.
Caso não possua algum item ou qtd disponivel na planilha, permitir que a solicitação grave apenas o que possui na planilha modelo.

As colunas da planilha modelo que se referem ao vinculo do portal X solicitação de agendamento são:
- "Unidade de destino"(conversão através do CNPJ)(Essa é a filial quando eu cito)
- "Código Produto Cliente" (conversão através do cod_produto) 
- "Código do pedido Cliente" (onde analisamos o que está antes do "-" pois a "mascara" do Sendas mostra: "pedido_cliente"&"-"&"código da filial").
- "Saldo disponível"
As informações que deverão ser gravadas em FilaAgendamentoSendas, deverão ser as informações que serão exportadas.
Dessa forma precisamos seguir o cod_produto, quantidade e pedido_cliente de acordo com que foi escolhido pelo usuario (no caso de optar por agendar um pedido divergente do disponibilizado) / pelo disponivel (no caso de 1 ou mais itens não estarem presentes na planilha ou não tiverem a qtd total da solicitação na planilha).
No caso do protocolo, deverá ser preenchido em FilaAgendamentoSendas.protocolo um protocolo para rastrearmos o agendamento, visto que no momento que fizermos o upload pro portal, não teremos nenhum vinculo direto da solicitação X portal, portanto acredito que o ideal seja utilizar a seguinte mascara: "AG_"&"filial do cnpj"(CNPJ-7 a -4)&"Data DDMMYY"&"HHMM".

Esse protocolo deverá ser propagado de volta para o ponto da solicitação, respeitando os locais onde estão os protocolos de cada Fluxo:
Fluxo 1: Lote - Será realizado através das Separações + Saldo em carteira que será criado Separação para agendar, portanto o local de gravação do protocolo será Separacao.protocolo
Fluxp 2: Separação - Será realizado através de uma Separação, portanto o local de gravação do protocolo será Separacao.protocolo
Fluxo 3: EntregaMonitorada - Será realizado pelo monitoramento, onde o local que armazena as agendas é AgendamentoEntrega sendo N AgendamentoEntrega para 1 EntregaMonitorada, portanto deverá ser criado um agendamento com esse protocolo e será gravado em AgendamentoEntrega.protocolo_agendamento.

Para casos de Separacao por Lote ("Fluxo 1"), deverá comparar por 1 ou mais pedidos e apenas perguntar se deseja agendar todo saldo dessa filial se não encontrar nenhum dos pedidos/produtos na planilha modelo e encontrar apenas a filial.

3- Exportação da planilha adequada:
Essa exportação deverá partir de informações da planilha modelo + FilaAgendamentoSendas, onde deverá ser montado através de informações das informações da planilha modelo acrescidas de informações de FilaAgendamentoSendas:
A planilha modelo contem campos que são preenchidos pelo Sendas automaticamente quando importada do portal:
Coluna 2 - 	Razão Social - Fornecedor
Coluna 3 - 	Nome Fantasia - Fornecedor
Coluna 4 - 	Unidade de destino
Coluna 5 - 	UF Destino
Coluna 6 - 	Fluxo de operação
Coluna 7 - 	Código do pedido Cliente
Coluna 8 - 	Código Produto Cliente
Coluna 9 - 	Código Produto SKU Fornecedor
Coluna 10 - EAN
Coluna 11 - Setor
Coluna 12 - Número do pedido Trizy
Coluna 13 - Descrição do Item
Coluna 14 - Quantidade total
Coluna 15 - Saldo disponível
Coluna 16 - Unidade de medida

Os campos acima não poderão ser sobrescritos e deverão ser copiados da planilha modelo para se criar a planilha exportada.
Abaixo seguem os campos que o Sendas permite alteração juntamente com informações que devemos preencher:

Coluna 1 - 	Demanda	 - Numero sequencial por agendamento
Coluna 17 - 	Quantidade entrega	 - Quantidade que iremos agendar
Coluna 18 - 	Data sugerida de entrega	 - Data que queremos agendar (necessario formato "Date" sem "time")
Coluna 19 - 	ID de agendamento (opcional)	 - Deixar vazio
Coluna 20 - 	Reserva de Slot (opcional)	 - Deixar vazio
Coluna 21 - 	Característica da carga	 - Sempre preencher "Paletizada"
Coluna 22 - 	Característica do veículo	 - Preencher com o nome exato do veiculo conforme o json de CAMINHÕES, onde constará "Nome do veiculo","Peso máximo"
Coluna 23 - 	Transportadora CNPJ (opcional)	 - Deixar vazio
Coluna 24 - 	Observação/ Fornecedor (opcional)	 - Preencher com o protocolo criado

json de CAMINHÕES:

CAMINHOES = [
    ('Utilitário', 800),
    ('Caminhão VUC 3/4', 2000),
    ('Caminhão 3/4 (2 eixos) 16T', 4000),
    ('Caminhão Truck (6x2) 23T', 8000),
    ('Carreta Simples Toco (3 eixos) 25T', 25000),
    ('Caminhão (4 eixos) 31T', float('inf'))  # Acima de 25000
]

4- Verificação das agendas:
A verificação das agnedas, devemos assumir que há possibilidade do portal do Sendas apresentar algum erro silencioso e as agendas não serem processadas, diante disso precisamos fazer algumas verificações.
Primeiro vou explicar as colunas e depois explicarei como deverá ser feito as verificações:
Colunas:
"ID"	Protocolo real do Sendas
"Status"	Status do Agendamento (Deverá exibir na tela para o usuario apenas)
"Data Efetiva"	Data do agendamento que foi aprovado (Sendas envia Datetime, precisamos extrair apenas Date)
"Obs. Criação"	Protocolo criado por nós para rastreabilidade
"Data/Hora Sugerida:"	Data do agendamento que solicitamos (Sendas envia Datetime, precisamos extrair apenas Date)

Verificações
A - Procurar o "ID" através do protocolo.
A.1 - Não encontrando procurar o protocolo através de "Obs. Criação"
A.1.1 - Encontrando em "Obs. Criação", gravar o ID no campo de protocolo (ID é o protocolo real, "Obs. Criação" é só pra rastrearmos e encontrarmos o ID)
A.1.2 - Não encontrando em "Obs. Criação", informar o usuario que o agendamento não está aparecendo e perguntar se deseja solicitar novamente todos os agendamentos não encontrados.
A.1.2.1 - Usuario desejando solicitar novamente, rastrear o agendamento em FilaAgendamentoSendas e alterar o status para pendente.
A.1.2.2 - Se o usuario não desejar solicitar novamente, ignorar e seguir.
A.2 - Encontrando, deverá procurar em "Data Efetiva" a data de agendamento.
A.2.1 - Caso encontre, gravar essa data e confirmar o agendamento (Separacao.agendamento_confirmado=True ou AgendamentoEntrega.status=confirmado)
A.2.1.1 - Para casos de cod_uf=SP nos fluxos 1 e 2, gravar em expedicao  a "Data Efetiva" - 1 dia útil.
A.2.1.2 - Caso não seja SP ignorar o campo expedicao
A.2.2 - Caso não encontre, compare a "Data/Hora Sugerida:" com o agendamento previamente registrado (Agendamento que solicitamos), encontrando divergencia, informar o usuario se deseja gravar a data correta da solicitação.
A.2.2.1 - Usuario confirmando, grave a "Data/Hora Sugerida:" no agendamento.
A.2.2.2 - Usuario negando ignore e siga.


  1. SEMPRE múltiplos produtos:
    - Nunca comparar 1 item só
    - Sempre usar comparar_multiplas_solicitacoes
    - Posso deletar comparar_solicitacao (singular)
  2. Protocolos:
    - Fluxo 1 (Lote): 1 protocolo por CNPJ
    - Fluxo 2 (Separação): 1 protocolo por separacao_lote_id
    - Fluxo 3 (NF): 1 protocolo por NF
  3. Agendamento Sendas:
    - SEMPRE agendar TODOS os produtos do documento_origem
    - Sendas aceita divergências de qtd, produto e até pedido
    - Sendas NÃO aceita divergência de filial
    - Vincule sempre priorizando o pedido exato para cada item, se não encontrar todos os itens da solicitação no pedido da solicitação, ampliar mostrando todos os pedidos / produtos da filial a ser agendada, permitindo ao usuario escolher a quantidade / pedido (pré preenchendo o que for "match").
    - A vinculação não é por item entre o documento de origem e a agenda e sim por solicitação.

1- 100% das vezes será comparado multiplos produtos do mesmo lote / nf / cnpj, nunca apenas "1 item".
Se "comparar_solicitacao" considera apenas 1 item pode excluir pois nunca acontecerá de comparar "parcialmente" uma nf ou separacao ou cnpj.
Não se esqueça do pedido_cliente.
Releia o documento docs/NOVO_PROCESSO_SENDAS.md para se recordar as informações de cada etapa.
2- Eu já respondi e percebo que voce está se perdendo, é 1 protocolo por separacao_lote_id no fluxo 2, 1 protocolo por nf no fluxo 3 e 1 protocolo por cnpj no fluxo 1.
3- Sempre todos os produtos serão agendados, a questão é que em alguns casos o Sendas nos envia um pedido e não consta todos os produtos na planilha modelo para agendarmos, portanto agendamos uma parte dos itens e mandamos tudo, pois o Sendas aceita dessa forma.
Outro caso é quando um pedido ainda não está disponivel para agendar mas agendamos através de outro pedido e "tentamos" casar as qtds e produtos mas o Sendas é tolerante.
A regra é: tentamos fazer casado mas o Sendas aceita divergencias de pedido e qtd de produto, apenas obviamente não aceita de filial (agendei em uma filial e fui entregar em outra).
Por esse motivo o agendamento possui esses "fallbacks" de qtd, produto e até pedido, mas por via de regra, se for certo é melhor.


SELECT
    'SEPARACAO' as origem,
    s.id,
    s.separacao_lote_id,
    s.num_pedido,
    s.cod_produto,
    s.qtd_saldo as quantidade,
    s.cnpj_cpf,
    s.raz_social_red as cliente,
    s.expedicao,
    s.agendamento,
    s.sincronizado_nf,
    s.status,
    s.numero_nf,
    CASE
        WHEN s.expedicao < CURRENT_DATE THEN 'ATRASADO'
        WHEN s.expedicao = CURRENT_DATE THEN 'HOJE'
        ELSE 'FUTURO'
    END as situacao_data,
    s.criado_em,
    s.observ_ped_1 as observacoes
FROM separacao s
WHERE s.cod_produto = '4040163'
    AND s.sincronizado_nf = FALSE  -- Apenas não faturadas (aparecem na projeção)
ORDER BY s.expedicao, s.num_pedido;