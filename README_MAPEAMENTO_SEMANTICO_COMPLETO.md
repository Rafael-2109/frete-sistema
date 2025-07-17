# MAPEAMENTO SEMÂNTICO COMPLETO - SISTEMA DE FRETES
==================================================

**Data de Geração:** 23/06/2025 20:29
**Modelos Mapeados:** 15
**Status:** Aguardando Definições do Usuário

## OBJETIVO

Este documento contém TODOS os campos dos modelos do sistema e as perguntas necessárias 
para criar um mapeamento semântico profissional que permita ao Claude AI interpretar 
corretamente as consultas em linguagem natural.

## METODOLOGIA

1. **Dados 100% Reais:** Todos os campos foram extraídos diretamente do banco PostgreSQL
2. **Mapeamento Automático:** Utilizando SQLAlchemy Inspector para garantir precisão  
3. **Validação Cruzada:** Campos validados contra dados reais existentes
4. **Zero Invenção:** Nenhum campo foi inventado ou deduzido

---

## 🔄 CAMPOS COMUNS (MAPEAR UMA VEZ)

**IMPORTANTE:** Os campos abaixo aparecem em múltiplos modelos. Mapeie UMA VEZ aqui, depois apenas referencie quando necessário.

### CAMPOS DE IDENTIFICAÇÃO:
- **id** - Chave primária única
- **criado_em** - Data/hora de criação do registro
- **criado_por** - Usuário que criou o registro

### CAMPOS DE CLIENTE:
- **cliente / nome_cliente / raz_social_red** - Nome do cliente
- **cnpj_cliente / cnpj_cpf** - CNPJ/CPF do cliente

### CAMPOS DE LOCALIZAÇÃO:
- **uf / cod_uf / estado** - Estado (UF)
- **cidade / nome_cidade / municipio** - Cidade
- **codigo_ibge** - Código IBGE da cidade

### CAMPOS DE VALORES:
- **valor_total / valor** - Valor monetário
- **peso_total / peso** - Peso em quilos
- **pallet_total / pallets** - Quantidade de pallets

### CAMPOS DE DATAS:
- **data_embarque** - Data que mercadoria saiu
- **data_fatura / data_faturamento** - Data do faturamento
- **data_entrega_prevista** - Data prevista para entrega
- **data_agenda / agendamento** - Data do agendamento

### CAMPOS DE DOCUMENTOS:
- **numero_nf / nf / nota_fiscal** - Número da Nota Fiscal
- **numero_cte** - Número do Conhecimento de Transporte
- **num_pedido / pedido** - Número do pedido

### CAMPOS DE STATUS:
- **status** - Situação atual do registro
- **ativo** - Se o registro está ativo

### CAMPOS DE TRANSPORTADORA:
- **transportadora / nome_transportadora** - Nome da transportadora
- **transportadora_id** - ID da transportadora
- **cnpj_transportadora** - CNPJ da transportadora

### CAMPOS DE VENDEDOR:
- **vendedor** - Nome do vendedor
- **vendedor_vinculado** - Vendedor vinculado ao usuário

### CAMPOS DE OBSERVAÇÕES:
- **observacoes** - Observações gerais
- **observacao_operacional** - Observações operacionais

---

## MODELOS E CAMPOS COMPLETOS


### 🔸 PEDIDO
**Tabela:** `pedidos`
Essa tabela se refere ao resumo dos itens da separação (tabela separacao) que no caso separacao é onde tem os pedidos disponiveis para embarque considerando os produtos, quantidades, valor, peso e pallet total por produto dentro do pedido, já a tabela pedidos é um resumo dos pedidos desconsiderando o produto, ou seja, somando valores, pesos e pallets por cada numero de pedido + protocolo de agendamento + data de expedição, pois podem haver mais do que 1 embarque para cada pedido, possivelmente por não caber no caminhão ou por outros motivos que o faça ir de maneira parcial.
Nesse momento a tabela de separacao, que no caso contem produtos, não é usada em mais nenhum lugar por apenas ela conter os produtos.
**Total de Campos:** 36

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **separacao_lote_id** (VARCHAR(50)) - Nulo: ✅

SIGNIFICADO: Esse campo é utilizado para vincular desde os itens da separação (onde contem os produtos vinculado ao pedido, data de expedição e protocolo de agendamento), pedido, embarque, frete, e monitoramento 
LINGUAGEM_NATURAL: Esse campo é codificado, portanto não tratamos ele especificamente
CONTEXTO: 
OBSERVAÇÕES: 

-    **num_pedido** (VARCHAR(30)) - Nulo: ✅
SIGNIFICADO: numero do pedido no sistema
LINGUAGEM_NATURAL: ["pedido", "pdd", "numero do pedido"]
CONTEXTO: É utilizado como referencia para os vendedores pois eles inserem o pedido no sistema ERP da empresa e controlam se o "pedido" já foi faturado.
OBSERVAÇÕES: Em outros modelos pode ser chamado de "origem" pois é o campo extraido do ERP da empresa

-    **data_pedido** (DATE) - Nulo: ✅
SIGNIFICADO: data de inserção do pedido no sistema ERP
LINGUAGEM_NATURAL: ["data do pedido", "data de inserção do pedido", "data do pdd", "data do pdd inserido"]
CONTEXTO: Pode ser usado pelos vendedores quando perguntarem "os pedidos de X data" 
OBSERVAÇÕES: 

-    **cnpj_cpf** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: CNPJ ou CPF do cliente 
LINGUAGEM_NATURAL: ["cnpj do pedido", "cnpj do cliente" ]
CONTEXTO: Ótima referencia para se buscar informações entre os modelos, pois é mais confiavel do que o nome, por mais que as buscam devam vir todas através do nome do cliente.
OBSERVAÇÕES: Muitos clientes que são redes de atacado e atacarejo o inicio do CNPJ é o mesmo, mudando apenas as filiais, porem não é uma regra, há clientes que cada filial é um CNPJ distinto, portanto não sei se é util

-    **raz_social_red** (VARCHAR(255)) - Nulo: ✅
SIGNIFICADO: Nome do cliente 
LINGUAGEM_NATURAL: ["cliente", "razão social do cliente", "nome do cliente"]
CONTEXTO: Quando alguem quiser saber a informação de um cliente, provavelmente irá informar o nome do cliente, identificação do cliente.
OBSERVAÇÕES: Relação direta com o CNPJ, muitos clientes são clientes de rede, ou seja, há diversas filiais, sendo alguns possiveis identificar através do nome ou do CNPJ.

-    **nome_cidade** (VARCHAR(120)) - Nulo: ✅
SIGNIFICADO: Cidade do cliente
LINGUAGEM_NATURAL: ["cidade do cliente", "municipio do cliente", "cliente da cidade"]
CONTEXTO: Cidade em que o cliente se situa.
OBSERVAÇÕES: 

-    **cod_uf** (VARCHAR(2)) - Nulo: ✅
SIGNIFICADO: Estado do cliente, UF do cliente.
LINGUAGEM_NATURAL: ["estado do cliente", "uf do cliente", "região do cliente", "regiao do cliente" ]
CONTEXTO: Estado que o cliente se situa
OBSERVAÇÕES: 

-    **cidade_normalizada** (VARCHAR(120)) - Nulo: ✅
SIGNIFICADO: Cidade do cliente normalizado para não gerar problema com as diferenças de acento e letras maiusculas
LINGUAGEM_NATURAL: ["cidade normalizada", "cidade padronizada", "cidade sem acento"]
CONTEXTO: Era ou é utilizado para se relacionar com a cidade dos vinculos e das localidades para padronizar o nome
OBSERVAÇÕES: 

-    **uf_normalizada** (VARCHAR(2)) - Nulo: ✅
SIGNIFICADO: Mesma coisa da cidade normalizada porem com UF normalizado
LINGUAGEM_NATURAL: ["uf normalizada", "estado normalizado", "uf padronizada"]
CONTEXTO: 
OBSERVAÇÕES:

💡 **COMENTÁRIO:** Campos técnicos importantes para padronização. Para o Claude AI, é melhor não expor esses campos diretamente nas consultas do usuário, mas usá-los internamente para buscas mais precisas. 

-    **codigo_ibge** (VARCHAR(10)) - Nulo: ✅
SIGNIFICADO: Codificação única extraida do governo para idenficar uma cidade especifica de um estado especifico através de numeros, tornando precisa a identificação e única.
LINGUAGEM_NATURAL: ["codigo ibge", "código ibge", "código da cidade", "identificação da cidade"]
CONTEXTO: Usado para converter a cidade/uf do pedido e para comparar de maneira padronizada com as localidades e os vinculos na identificação da tabela correta através do codigo_ibge extraido do pedido e identificado a transportadora e nome da tabela para buscar nas tabelas as opções validas para as cotações de frete
OBSERVAÇÕES:

-    **valor_saldo_total** (FLOAT) - Nulo: ✅
SIGNIFICADO: Valor total do pedido naquela separação, isso significa que pode haver mais separações para o mesmo pedido e portanto esse valor saldo é o valor daquela separação especifica.
LINGUAGEM_NATURAL: ["valor do pedido", "total do pedido", "valor do pdd", "total do pdd"]
CONTEXTO: 
OBSERVAÇÕES: Futuramente vou implementar a carteira de pedidos, em que a separação será derivada da carteira de pedidos, aumentando muito rastreabilidade das separações, porem nesse momento ela é exportada de um excel e importada no sistema, portanto é um gargalo na rastreabilidade da operação.

-    **pallet_total** (FLOAT) - Nulo: ✅
SIGNIFICADO: Pallets total do pedido naquela separação
LINGUAGEM_NATURAL: ["qtd de pallets do pedido", "pallets do pedido", "palets do pedido", "palets do pdd", "total de pallets do pedido", "pallet do pedido", "pallet pdd", "qtd de palets", "qtd de pallets", "qtd de pallet"]
CONTEXTO: 
OBSERVAÇÕES: 

-    **peso_total** (FLOAT) - Nulo: ✅
SIGNIFICADO: Peso total do pedido naquela separação
LINGUAGEM_NATURAL: ["peso do pedido", "peso do pdd", "quilos", "kg", "peso bruto", "peso liquido", "quantos quilos"]
CONTEXTO: 
OBSERVAÇÕES:

-    **rota** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: Divisão macro das regiões, utilizado como uma "pré separação" das regiões na roteirização, cada rota contem varios estados.
LINGUAGEM_NATURAL: ["rotas", "rota"]
CONTEXTO: 
OBSERVAÇÕES: 

-    **sub_rota** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: Divisão dos estados para a roteirização, utilizado como uma sub divisão das rotas, cada rota contem N sub rotas.
LINGUAGEM_NATURAL: ["sub rota", "subrota", "divisão da rota", "região específica"]
CONTEXTO: 
OBSERVAÇÕES:

-    **observ_ped_1** (TEXT) - Nulo: ✅
SIGNIFICADO: Observação do pedido, pode conter informações importantes dos pedidos.
LINGUAGEM_NATURAL: ["obs do pdd", "observação do pedido", "observação no pdd", "observacao no pedido", "observacao do pdd", "obs no pdd" ]
CONTEXTO: É inserido pelo comercial e pode conter informações importantes para o PCP, produção, logistica dos pedidos, como entrega imediata, necessario produção especifica.  
OBSERVAÇÕES: 

-    **roteirizacao** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: Rascunho usado na logistica antes do pedido ir para separação, pode conter transportadoras "pre avaliadas", ordem das entregas.
LINGUAGEM_NATURAL: ["planejamento de rota", "rascunho de entrega", "pre avaliação"]
CONTEXTO: 
OBSERVAÇÕES:

-    **expedicao** (DATE) - Nulo: ✅
SIGNIFICADO: Data disponivel ou data programada para embarque
LINGUAGEM_NATURAL: ["data programada", "data prevista de faturamento", "data prevista de embarque", "quando está previsto sair" ]
CONTEXTO: utilizada pela roteirização como referencia de data disponivel / data necessaria de embarque.
OBSERVAÇÕES: 

-    **agendamento** (DATE) - Nulo: ✅
SIGNIFICADO: Data de agendamento do cliente
LINGUAGEM_NATURAL: ["data de agendamento", "agenda", "data da agenda", "agendamento", "data agendada"]
CONTEXTO: Data necessaria de entrega
OBSERVAÇÕES: quando esse campo está preenchido, é necessario entregar nessa data, diversos clientes há a necessidade de se agendar a entrega.

-    **protocolo** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: Protocolo do agendamento
LINGUAGEM_NATURAL: ["protocolo", "protocolo do agendamento"]
CONTEXTO: Protocolo do agendamento.
OBSERVAÇÕES: Necessario para referencia de que há um agendamento, necessario para se imprimir o agendamento em diversos clientes.

-    **transportadora** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: transportadora
LINGUAGEM_NATURAL: [""]
CONTEXTO: 
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **valor_frete** (FLOAT) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **valor_por_kg** (FLOAT) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **nome_tabela** (VARCHAR(100)) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **modalidade** (VARCHAR(50)) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **melhor_opcao** (VARCHAR(100)) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **valor_melhor_opcao** (FLOAT) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **lead_time** (INTEGER) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **data_embarque** (DATE) - Nulo: ✅
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

💡 **COMENTÁRIO SOBRE CAMPOS NÃO UTILIZADOS:** Ótima observação! Isso é importante para o Claude AI não consultar campos obsoletos. Recomendo validar no código se realmente não são usados. Se confirmado, podemos marcar como "DEPRECATED" no mapeamento.

-    **nf** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: NF originada através do faturamento desse pedido.
LINGUAGEM_NATURAL: ["nf", "nota fiscal", "numero da nf"]
CONTEXTO: 
OBSERVAÇÕES: 

-    **status** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: Identificação do status do pedido, variando entre "aberto" significa que não há embarques ativos, "cotado" significa que está em um embarque que ainda não embarcou e não faturou, "embarcado" significa que tem data de embarque porem não tem Nota fiscal nos itens do embarque ou "faturado", significa que está em um embarque com nf preenchida.
"Cotado" não significa que há um frete, pois pedidos "FOB" que não há uma cotação, pois não há frete, tambem aparecem como "cotado"
LINGUAGEM_NATURAL: ["aberto", "cotado", "faturado", "status do pedido", "situação do pedido", "posição do pedido", "embarcado"]


CONTEXTO: é utilizado em conjunto com "nf_cd" para se definir a posição do pedido perante a carteira de pedidos, quando nf_cd = true, sobrepõe o status, tornando o status_calculado = "NF no CD", pois indica que esse pedido já foi cotado, faturado, porem por algum motivo voltou para a empresa, para posteriormente gerar uma possivel reentrega
OBSERVAÇÕES: Esse campo é usado em conjunto com o campo "nf_cd" para se definir o "status_calculado" que de fato é o campo mostrado na tela

-    **nf_cd** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: Campo disparado através do monitoramento quando gera um evento do tipo "NF no CD", indicando que a mercadoria (NF ou Pedido) voltou para a empresa e a entrega não foi concluida, necessitando de uma nova contratação de frete
LINGUAGEM_NATURAL: ["nf no cd", "nota no cd", "voltou para empresa", "entrega não concluída", "precisa reentrega"]
CONTEXTO: 
OBSERVAÇÕES: Acredito que esse campo não esteja sendo usado nas rotas

-    **criado_em** (DATETIME) - Nulo: ✅
SIGNIFICADO: Acredito que seja a data de inserção do pedido no sistema da logistica, diferente da data_pedido que se refere a data de criação do pedido.
-    **cotacao_id** (INTEGER) - Nulo: ✅
Esse campo deve indicar a cotação que se refere mas não deve ser usado eu acho.
-    **usuario_id** (INTEGER) - Nulo: ✅
Não sei onde se usa e nem se ele se refere a inserção do pedido, a cotação ou a outro registro com usuario

💡 **CAMPOS RELACIONAMENTOS:** Estes campos são chaves estrangeiras. Podem referenciar "VER CAMPOS COMUNS" se aplicável.

#### RELACIONAMENTOS:
Não sei pra que servem essas relações
- **usuario** → Usuario
- **cotacao_item** → CotacaoItem

---

### 🔸 EMBARQUEITEM
**Tabela:** `embarque_itens`
Embarque itens é onde consta cada pedido do embarque (1 embarque item = 1 pedido)
Ela tambem é usada para armazenar os dados da tabela de frete do tipo_carga "FRACIONADA" utilizada na cotação de cada pedido.
Há diferenciação de onde será gravado a tabela de frete utilizada na cotação pelo tipo_carga da cotação pois no caso de uma carga fracionada, a qtd de clientes, região, valores etc de cada cliente não interfere no frete de outro cliente, portanto cada cotação é realizada por CNPJ, portanto para prevenir de que alguma alteração na tabela altere um frete fechado anteriormente, eu decidi gravar todos os campos da tabela direto no embarque item pois ao gravar os campos ajuda muito na conferencia do frete a ter a rastreabilidade do "porque" daquele valor.


**Total de Campos:** 34

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **embarque_id** (INTEGER) - Nulo: ❌
Especificamente não sei aonde usa o embarque_id
-    **separacao_lote_id** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: mesmo campo de Pedido, enviado por Pedido
-    **cnpj_cliente** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "cnpj_cpf"
-    **cliente** (VARCHAR(120)) - Nulo: ❌
SIGNIFICADO: msm campo de Pedido "razao_social_red"
-    **pedido** (VARCHAR(50)) - Nulo: ❌
SIGNIFICADO: msm campo de Pedido "num_pedido"
-    **protocolo_agendamento** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "protocolo"
-    **data_agenda** (VARCHAR(10)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "agendamento"
-    **nota_fiscal** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "nf"
-    **volumes** (INTEGER) - Nulo: ✅
SIGNIFICADO: Soma da qtd dos produtos na separação
LINGUAGEM_NATURAL: ["volumes", "qtd de itens", "qtd do pedido"]
CONTEXTO: Hoje não é nem preenchido e nem usado em nenhum lugar do sistema, poderá ser usado quando for implementado a separação dos pedidos efetivamente no sistema, hoje é apenas gerado uma folha de impressão para separação
OBSERVAÇÕES: 

-    **peso** (FLOAT) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "peso_total"
CONTEXTO: nesse caso o peso é alterado no momento do faturamento, pois pode haver divergencia entre os produtos e qtds do pedido que foi inserido e quando foi faturado
-    **valor** (FLOAT) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "valor_total"
CONTEXTO: nesse caso o valor é alterado no momento do faturamento, pois pode haver divergencia entre os produtos, qtds e preço do pedido que foi inserido e quando foi faturado
-    **pallets** (FLOAT) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "pallet_total"
CONTEXTO: por falta de informação no sistema e no relatorio de faturamento desse campo, mantemos ele igual do pedido, pois no relatório de faturamento não consta esse campo, portanto não podendo ser atualizado
-    **status** (VARCHAR(20)) - Nulo: ❌
SIGNIFICADO: status do item no embarque, é possivel cancelar um item do embarque porem para rastreabilidade eu preferi mante-lo no embarque porem com status cancelado.
As opções desse campo são: "cancelado" e "ativo"
LINGUAGEM_NATURAL: ["pdd cancelado do embarque", "pedido excluido do embarque", "pedido não vai no embarque", "pedido cancelado do embarque", "pedido não vai nesse embarque"]
CONTEXTO: afim de flexibilizar as alterações do embarque eu permiti que cancelasse um item do embarque porem para não perder a rastrabilidade eu decidi mante-lo registrado porem com status "cancelado".
Ao cancelar o item do embarque, a NF é apagada do item (caso esteja preenchida), é bloqueado os campos para edição e altera o status do Pedido para "Aberto" novamente para poder ser cotado de novo.
É utilizado como critério para se imprimir a separação dos pedidos do embarque.
É desconsiderado na impressão do embarque.
É utilizado na validação do status do embarque para o disparo de ações nas alterações de status do embarque, ou seja, para se lançar os fretes, todos os itens do embarque precisam estar com as nfs preenchidas para os itens com status "ativo"
OBSERVAÇÕES: 
-    **uf_destino** (VARCHAR(2)) - Nulo: ❌
SIGNIFICADO: UF de entrega do pedido, ou seja, para entregas em redespacho, é considerado SP, independente de qual seja o UF do cliente, já para os casos "CIF", é considerado o UF do cliente, portanto para se descobrir o UF real do cliente e não se confundir com UF de entrega, é necessario observar no UF do Pedido
Redespacho é possivel se definir quando o campo de "rota" em Pedido for = "RED", já no caso de clientes "FOB" o uf_destino permanece do cliente, porem não é utilizado na cotação por não haver cotação de frete para FOB
LINGUAGEM_NATURAL: ["Uf de entrega", "estado de entrega"]
CONTEXTO: Há uma possivel conversão de UF do cliente através dos arquivos em utils/localizacao.py no momento da cotação de frete para se gerar o uf_destino em casos de Redespacho e para padronização do nome.
Campo essencial para se encontrar a tabela de frete correta anteriormente no momento da cotação.
campo originado no momento da cotação do frete.
OBSERVAÇÕES: Não se confundir com estado do verbo estar.

-    **cidade_destino** (VARCHAR(100)) - Nulo: ❌
SIGNIFICADO: Mesma lógica do uf_destino porem nesse campo nos campos que forem FOB, as informações não terão validade pois em alguns casos poderá estar vazio ou estar com o nome da transportadora que virá coletar, porem não há um padrão para os casos FOB, apenas para CIF e RED (redespacho), sendo os casos de RED sempre terá Guarulhos ou São Paulo, pois são as cidades onde redespachamos as mercadorias nos casos de redespacho.
LINGUAGEM_NATURAL: ["onde entrega", "lugar da entrega", "cidade da entrega"]
CONTEXTO: usado em conjunto com UF no momento da cotação e registrado para se manter a coerencia da tabela de frete utilizada.
OBSERVAÇÕES: 

-    **cotacao_id** (INTEGER) - Nulo: ✅
Acredito que seja alguma referencia do momento da cotação de frete

Os campos abaixo até a palavra "FIM" se referem a tabela de frete utilizada na cotação de frete desse pedido
São (acredito) todos os campos da tabela para garantir integridade e rastreabilidade da tabela utilizada no momento da cotação do frete para esse pedido.
Os campos abaixo se repetem no Embarque e EmbarqueItem.
Quando esses campos estão preenchidos no Embarque, obrigatoriamente se referem a tipo_carga "DIRETA" e a adição ou remoção de 1 item não altera em nada nos campos, eles se referem a 1 frete por embarque, que serão calculados e rateados peso no momento do registro do frete.
Quando esses campos estão preenchidos no EmbarqueItem, eles se referem obrigatoriamente de um frete com tipo_carga "FRACIONADA" e são preenchidos por item, ou seja, por pedido.
*** As tabelas de frete são unicas para cada combinação de transportadora + nome_tabela + uf destino + modalidade
-    **modalidade** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: nos casos de tipo_carga = "FRACIONADA" as modalidades podem ser "FRETE PESO" ou "FRETE VALOR", já nos tipo_carga "DIRETA" as modalidades são os veiculos, cada Embarque contem apenas 1 tipo_carga para todos os itens do embarque.
LINGUAGEM_NATURAL: ["modalidade", "tipo de veiculo"]
CONTEXTO: Esse campo no caso de carga fracionada não interfere tanto, pois não há nenhum critério ou restrição especifica para FRETE PESO ou FRETE VALOR, porem esse campo tambem contem os veiculos no caso do tipo_carga = "DIRETA" e sendo os veiculos há restrição de peso onde é validado em veiculos através do nome e utilizado o campo peso_maximo para validar a capacidade de peso do veiculo no momento da cotação do frete
OBSERVAÇÕES: 

-    **tabela_nome_tabela** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: Nome da tabela de frete utilizada na cotação
LINGUAGEM_NATURAL: ["nome da tabela", "tabela de frete", "qual tabela"]
CONTEXTO: é utilizado na identificação da tabela de frete correspondente, nomeado pela transportadora ou por nós, o que ficar mais objetiva a identificação.
OBSERVAÇÕES: 

-    **tabela_valor_kg** (FLOAT) - Nulo: ✅
SIGNIFICADO: valor cobrado pela transportadora por peso (kg) enviado
LINGUAGEM_NATURAL: ["frete peso", "frete kg", "valor por kg", "valor do kg", "frete excedente", "kg excedente"]
CONTEXTO: é utilizado no calculo do frete através da multiplicado do valor_kg pelo peso enviado.
OBSERVAÇÕES: R$ / kg da mercadoria

-    **tabela_percentual_valor** (FLOAT) - Nulo: ✅
SIGNIFICADO: valor cobrado pela transportadora para cada R$ enviado
LINGUAGEM_NATURAL: [""]
CONTEXTO: 
OBSERVAÇÕES: % * valor da mercadoria

-    **tabela_frete_minimo_valor** (FLOAT) - Nulo: ✅
SIGNIFICADO: Valor minimo cobrado pela transportadora para o frete
LINGUAGEM_NATURAL: ["valor minimo", "frete minimo valor", "valor do frete minimo"]
CONTEXTO: utilizado como um gatilho no calculo do frete em que se utiliza o maior entre valor do frete calculado pelos campos da tabela e frete_minimo_valor
OBSERVAÇÕES: R$ gatilho emcima do valor da mercadoria
-    **tabela_frete_minimo_peso** (FLOAT) - Nulo: ✅
SIGNIFICADO: Peso minimo utilizado no calculo do frete.
LINGUAGEM_NATURAL: ["frete minimo peso", "frete minimo por peso", "peso minimo do frete"]
CONTEXTO:  Utilizado como um gatilho no calculo do frete para o peso considerado no calculo, onde se utliza o maior entre o peso do pedido e o frete_minimo_peso
OBSERVAÇÕES: kg gatilho emcima do peso da mercadoria

-    **tabela_icms** (FLOAT) - Nulo: ✅
SIGNIFICADO: Esse campo foi criado inicialmente para se utilizar como um gatilho em que se estiver preenchido com algum valor de ICMS, deveria considerar esse valor ao invés do ICMS da cidade, porem acredito que não esteja sendo usado em nenhum lugar, talvez apenas para exibir nos dados da tabela do embarque
LINGUAGEM_NATURAL: [""]
CONTEXTO: 
OBSERVAÇÕES: 

-    **tabela_percentual_gris** (FLOAT) - Nulo: ✅
SIGNIFICADO: % de gerenciamento de risco sobre o valor da mercadoria cobrado pela transportadora no calculo do frete
LINGUAGEM_NATURAL: ["gris", "gerenciamento de risco"]
CONTEXTO:  % sobre o valor da mercadoria cobrado pela transportadora e utilizado no calculo do frete.
OBSERVAÇÕES: % * valor da mercadoria 

-    **tabela_pedagio_por_100kg** (FLOAT) - Nulo: ✅
SIGNIFICADO: valor de pedagio cobrado pela transportadora por fração de 100 kgs de mercadoria enviada, isso significa que é cobrado "1 valor" mesmo que a mercadoria seja apenas uma fração de 100 kgs.
LINGUAGEM_NATURAL: ["pedagio", "valor do pedagio", "pedagio por 100 kg"]
CONTEXTO: Utilizado no calculo do frete, sempre calculado emcima de frações inteiras de 100 kg, se houver dezenas ou unidades de kg, arredondar para cima até completar uma nova fração de 100kg para ser utilizado no calculo. (formula = peso/100, arredondado para cima, multiplicado pelo pedagio_por_100kg)
OBSERVAÇÕES: R$ p/ cada 100kg de mercadoria (100 kgs inteiro ou fração cobra-se 1 pedagio_por_100_kg integral)

-    **tabela_valor_tas** (FLOAT) - Nulo: ✅
SIGNIFICADO: Taxa de administração do Sefaz cobrada pela transportadora
LINGUAGEM_NATURAL: ["tas", "taxa do sefaz", "tarifa do sefaz"]
CONTEXTO: Valor fixo adicionado no frete por CTE (CNPJ pois 1 CNPJ = 1 entrega = 1 CTE = 1 frete nos casos de carga fracionada, pode conter multiplos pedidos por CNPJ)
OBSERVAÇÕES: R$ por frete
-    **tabela_percentual_adv** (FLOAT) - Nulo: ✅
SIGNIFICADO: Valor do seguro da carga cobrado pela transportadora, conhecido como Ad Valorem
LINGUAGEM_NATURAL: ["adv", "advalorem", "seguro da carga", "seguro", "valor do seguro"]
CONTEXTO: % sobre o valor da mercadoria cobrado pela transportadora e utilizado no calculo do frete
OBSERVAÇÕES: % * valor da mercadoria 

-    **tabela_percentual_rca** (FLOAT) - Nulo: ✅
SIGNIFICADO: Tarifa do seguro de Responsabilidade Civil do Transportador Aquaviário (RCA), que cobre danos à carga durante o transporte aquaviário, valor do seguro maritimo da carga cobrado pela transportadora, 
LINGUAGEM_NATURAL: ["rca", "seguro maritimo"]
CONTEXTO: % sobre o valor da mercadoria cobrado pela transportadora e utilizado no calculo do frete
OBSERVAÇÕES: % * valor da mercadoria 

-    **tabela_valor_despacho** (FLOAT) - Nulo: ✅
SIGNIFICADO: Taxa inventada pelas transportadoras por emissão de CTE para cobrir os custos administrativos com a documentação de transporte
LINGUAGEM_NATURAL: ["despacho", "tarifa de despacho"]
CONTEXTO: Valor cobrado pela transportadora por CTE
OBSERVAÇÕES: R$ por frete

-    **tabela_valor_cte** (FLOAT) - Nulo: ✅
SIGNIFICADO: Tarifa por emissão de CTE
LINGUAGEM_NATURAL: ["taxa de cte", "tarifa de cte"]
CONTEXTO: Valor cobrado pela transportadora por CTE
OBSERVAÇÕES: R$ por frete


-    **tabela_icms_incluso** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: campo usado na cotação do frete para determinar se o ICMS está incluso no valor do frete ou se deverá ser adicionado
LINGUAGEM_NATURAL: ["icms incluso"]
CONTEXTO: Usado para determinar se adiciona o ICMS ou não no valor do frete
OBSERVAÇÕES: lembrando que o calculo do ICMS deve sempre realizado através de (1-ICMS) no caso de acrescentar o ICMS valor/(1-ICMS)

-    **icms_destino** (FLOAT) - Nulo: ✅
SIGNIFICADO: % de ICMS utilizado no calculo do frete e extraido da tabela localidades através do UF destino e cidade destino
LINGUAGEM_NATURAL: ["icms do frete"]
CONTEXTO: % de icms utilizado tanto para adicionar no calculo do frete para casos em que o icms não está incluso no frete e tambem utilizado para deduzir do valor do frete bruto para se ter o valor liquido do frete em casos que a transportadora não é optante pelo simples nacional (campo optante em transportadora)
OBSERVAÇÕES: 
FIM
-    **erro_validacao** (VARCHAR(500)) - Nulo: ✅
Não sei o que é esse erro_validacao



#### RELACIONAMENTOS:
- **cotacao** → Cotacao
- **embarque** → Embarque

---

### 🔸 EMBARQUE
**Tabela:** `embarques`
1 Embarque = N EmbarqueItem


**Total de Campos:** 46

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **numero** (INTEGER) - Nulo: ✅
SIGNIFICADO: numero do embarque
LINGUAGEM_NATURAL: ["numero do embarque", "numero embarque"]
CONTEXTO: numero referencia no dia a dia das pessoas e para o vinculo da portaria com o embarque
OBSERVAÇÕES: Há 2 "numeros" no embarque, um que aparece no URL que não é a referencia, deve ser ID ou algo do tipo e esse numero que é de fato o numero com que as pessoas conhecem

-    **data_prevista_embarque** (DATE) - Nulo: ✅
SIGNIFICADO: Data prevista do embarque
LINGUAGEM_NATURAL: ["data prevista do embarque", "data prevista embarque", "previsao de embarque"]
CONTEXTO: Data inserida após a criação do embarque como uma previsão de embarque. Serve como gatilho para liberar o botão de "Imprimir completo", que no caso imprime 2 vias do embarque e 1 via de cada separação, que no caso é o pedido contendo todos os itens, qtds, codigo do produto extraidos da separacao e vinculado através do separacao_lote_id
OBSERVAÇÕES: 

-    **data_embarque** (DATE) - Nulo: ✅
SIGNIFICADO: Data efetiva do embarque
LINGUAGEM_NATURAL: ["data de saida", "data do embarque", "data que embarcou", "dia que saiu", "data que enviou pro cliente", "dia que enviou pro cliente", "dia que enviou o pedido"]
CONTEXTO: Data que de fato o pedido saiu para a entrega
OBSERVAÇÕES: 

-    **transportadora_id** (INTEGER) - Nulo: ✅
SIGNIFICADO: esse campo é "INTEGER" então deve ser o id da transportadora do embarque, com exceção dos pedidos FOB que o campo de transportadora fica preenchido por padrão com FOB - COLETA
LINGUAGEM_NATURAL: [""]
CONTEXTO: 
OBSERVAÇÕES: 


Campos não usados em nenhum lugar do sistema nesse momento:
-    **observacoes** (TEXT) - Nulo: ✅
-    **placa_veiculo** (VARCHAR(10)) - Nulo: ✅
-    **paletizado** (BOOLEAN) - Nulo: ✅
-    **laudo_anexado** (BOOLEAN) - Nulo: ✅
-    **embalagem_aprovada** (BOOLEAN) - Nulo: ✅
-    **transporte_aprovado** (BOOLEAN) - Nulo: ✅
-    **horario_carregamento** (VARCHAR(5)) - Nulo: ✅
-    **responsavel_carregamento** (VARCHAR(100)) - Nulo: ✅

-    **status** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: status do embarque, para definir se está ativo ou cancelado, embarques ativos podem conter NF, fretes e data de embarque, no momento que o frete é vinulado um CTE não é mais possivel cancela-lo.
LINGUAGEM_NATURAL: ["status do embarque"]
CONTEXTO: usado para definir se um embarque está valido ou não
OBSERVAÇÕES: 

-    **motivo_cancelamento** (TEXT) - Nulo: ✅
SIGNIFICADO: Campo obrigatório para preenchimento do motivo do cancelamento do embarque
LINGUAGEM_NATURAL: ["motivo de cancelar embarque", "porque cancelou embarque", "motivos dos embarques cancelados"]
CONTEXTO: 
OBSERVAÇÕES: 

-    **cancelado_em** (DATETIME) - Nulo: ✅
SIGNIFICADO: Registro da data do cancelamento do embarque
LINGUAGEM_NATURAL: ["quando cancelou o embarque", "momento de cancelamento do embarque", "data do cancelamento do embarque"]
CONTEXTO: Data registrada automaticamente ao cancelar o embarque
OBSERVAÇÕES: 

-    **cancelado_por** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: Registro do usuario que cancelou o embarque
LINGUAGEM_NATURAL: ["quem cancelou o embarque", "usuario que cancelou o embarque"]
CONTEXTO: Usuario registrado automaticamente ao cancelar o embarque
OBSERVAÇÕES: 

-    **tipo_cotacao** (VARCHAR(20)) - Nulo: ✅
Acho q esse campo não é utilizado

Somatória dos campos de peso, valor e pallets do EmbarqueItem contido no Embarque
-    **valor_total** (FLOAT) - Nulo: ✅
-    **pallet_total** (FLOAT) - Nulo: ✅
-    **peso_total** (FLOAT) - Nulo: ✅

-    **tipo_carga** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: Campo com opção do tipo da carga, variando entre FOB para casos sem frete de pedidos FOB, DIRETA para casos de cargas diretas onde as informações da tabela serão preenchidas no Embarque, ou seja, terá 1 tabela por embarque, e FRACIONADA onde serão para casos de cargas fracionadas em que as tabelas serão preenchidas em cada item do Embarque, ou seja, serão preenchidas em cada EmbarqueItem do Embarque.
LINGUAGEM_NATURAL: ["tipo do frete", "tipo da carga"]
CONTEXTO: Utilizado na definição do tipo da cotação do frete se é um veiculo dedicado/carga lotação é DIRETA ou se é uma carga FRACIONADA.
Critério de definição se a tabela será  registrada no Embarque ou EmbarqueItem
OBSERVAÇÕES: 

-    **criado_em** (DATETIME) - Nulo: ❌
SIGNIFICADO: Registro da data da criação do embarque
LINGUAGEM_NATURAL: ["quando cotou", "quando criou o embarque", "data da criação do embarque"]
CONTEXTO: Registro automatico da data e hora no momento realização da cotação, que é quando se cria o embarque nos casos que não sao FOB, os casos FOB se cria direto dos pedidos. 
OBSERVAÇÕES: 

-    **criado_por** (VARCHAR(100)) - Nulo: ❌
SIGNIFICADO: Registro do usuario que criou o embarque
LINGUAGEM_NATURAL: ["quem cotou", "quem criou o embarque", "usuario que criou o embarque"]
CONTEXTO: Registro automatico do usuario que realizou a cotação do frete e consequentemente criou o embarque
OBSERVAÇÕES: 

Esses campos abaixo são para preenchimento na folha, ou seja, ainda não estão sendo preenchidos no sistema.
-    **nome_motorista** (VARCHAR(100)) - Nulo: ✅
-    **cpf_motorista** (VARCHAR(20)) - Nulo: ✅
-    **qtd_pallets** (INTEGER) - Nulo: ✅
-    **data_embarque_str** (VARCHAR(10)) - Nulo: ✅
-    **cotacao_id** (INTEGER) - Nulo: ✅

Mesmos campos de EmbarqueItem, campos originados da tabela usada na cotação
-    **modalidade** (VARCHAR(50)) - Nulo: ✅
-    **tabela_nome_tabela** (VARCHAR(100)) - Nulo: ✅
-    **tabela_valor_kg** (FLOAT) - Nulo: ✅
-    **tabela_percentual_valor** (FLOAT) - Nulo: ✅
-    **tabela_frete_minimo_valor** (FLOAT) - Nulo: ✅
-    **tabela_frete_minimo_peso** (FLOAT) - Nulo: ✅
-    **tabela_icms** (FLOAT) - Nulo: ✅
-    **tabela_percentual_gris** (FLOAT) - Nulo: ✅
-    **tabela_pedagio_por_100kg** (FLOAT) - Nulo: ✅
-    **tabela_valor_tas** (FLOAT) - Nulo: ✅
-    **tabela_percentual_adv** (FLOAT) - Nulo: ✅
-    **tabela_percentual_rca** (FLOAT) - Nulo: ✅
-    **tabela_valor_despacho** (FLOAT) - Nulo: ✅
-    **tabela_valor_cte** (FLOAT) - Nulo: ✅
-    **tabela_icms_incluso** (BOOLEAN) - Nulo: ✅
-    **icms_destino** (FLOAT) - Nulo: ✅


-    **transportadora_optante** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: Campo especifico para definição se a transportadora é optante pelo simples nacional sendo S = True, N = False.
LINGUAGEM_NATURAL: ["optante", "simples nacional", "optante pelo simples"]
CONTEXTO: caso seja = True, ou seja o regime tributario da transportadora é optante pelo simples nacional, não há credito de icms no calculo do frete liquido, portanto o frete liquido é igual ao frete bruto, para os caso que Não seja optante pelo simples nacional, há crédito do ICMS, portanto o valor do frete liquido será o "frete bruto *(1- %ICMS)"
OBSERVAÇÕES: 

#### RELACIONAMENTOS:
- **transportadora** → Transportadora
- **itens** → EmbarqueItem
- **cotacao** → Cotacao
- **fretes** → Frete
- **fretes_lancados** → FreteLancado
- **registros_portaria** → ControlePortaria

---

### 🔸 FRETE
**Tabela:** `fretes`
**Total de Campos:** 46

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **embarque_id** (INTEGER) - Nulo: ❌
-    **cnpj_cliente** (VARCHAR(20)) - Nulo: ❌
-    **nome_cliente** (VARCHAR(255)) - Nulo: ❌
-    **transportadora_id** (INTEGER) - Nulo: ❌
-    **tipo_carga** (VARCHAR(20)) - Nulo: ❌
-    **modalidade** (VARCHAR(50)) - Nulo: ❌
-    **uf_destino** (VARCHAR(2)) - Nulo: ❌
-    **cidade_destino** (VARCHAR(100)) - Nulo: ❌
-    **peso_total** (FLOAT) - Nulo: ❌
-    **valor_total_nfs** (FLOAT) - Nulo: ❌
-    **quantidade_nfs** (INTEGER) - Nulo: ❌
-    **numeros_nfs** (TEXT) - Nulo: ❌
-    **tabela_nome_tabela** (VARCHAR(100)) - Nulo: ✅
-    **tabela_valor_kg** (FLOAT) - Nulo: ✅
-    **tabela_percentual_valor** (FLOAT) - Nulo: ✅
-    **tabela_frete_minimo_valor** (FLOAT) - Nulo: ✅
-    **tabela_frete_minimo_peso** (FLOAT) - Nulo: ✅
-    **tabela_icms** (FLOAT) - Nulo: ✅
-    **tabela_percentual_gris** (FLOAT) - Nulo: ✅
-    **tabela_pedagio_por_100kg** (FLOAT) - Nulo: ✅
-    **tabela_valor_tas** (FLOAT) - Nulo: ✅
-    **tabela_percentual_adv** (FLOAT) - Nulo: ✅
-    **tabela_percentual_rca** (FLOAT) - Nulo: ✅
-    **tabela_valor_despacho** (FLOAT) - Nulo: ✅
-    **tabela_valor_cte** (FLOAT) - Nulo: ✅
-    **tabela_icms_incluso** (BOOLEAN) - Nulo: ✅
-    **tabela_icms_destino** (FLOAT) - Nulo: ✅
-    **valor_cotado** (FLOAT) - Nulo: ❌
-    **valor_cte** (FLOAT) - Nulo: ✅
-    **valor_considerado** (FLOAT) - Nulo: ✅
-    **valor_pago** (FLOAT) - Nulo: ✅
-    **numero_cte** (VARCHAR(50)) - Nulo: ✅
-    **data_emissao_cte** (DATE) - Nulo: ✅
-    **vencimento** (DATE) - Nulo: ✅
-    **fatura_frete_id** (INTEGER) - Nulo: ✅
-    **status** (VARCHAR(20)) - Nulo: ✅
-    **requer_aprovacao** (BOOLEAN) - Nulo: ✅
-    **aprovado_por** (VARCHAR(100)) - Nulo: ✅
-    **aprovado_em** (DATETIME) - Nulo: ✅
-    **observacoes_aprovacao** (TEXT) - Nulo: ✅
-    **considerar_diferenca** (BOOLEAN) - Nulo: ✅
-    **criado_em** (DATETIME) - Nulo: ✅
-    **criado_por** (VARCHAR(100)) - Nulo: ❌
-    **lancado_em** (DATETIME) - Nulo: ✅
-    **lancado_por** (VARCHAR(100)) - Nulo: ✅

#### RELACIONAMENTOS:
- **embarque** → Embarque
- **transportadora** → Transportadora
- **fatura_frete** → FaturaFrete
- **despesas_extras** → DespesaExtra
- **movimentacoes_conta_corrente** → ContaCorrenteTransportadora
- **aprovacao** → AprovacaoFrete

---

### 🔸 ENTREGAMONITORADA
**Tabela:** `entregas_monitoradas`
**Total de Campos:** 30

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **numero_nf** (VARCHAR(20)) - Nulo: ❌
SIGNIFICADO: msm campo de Pedido "nf" extraido de RelatorioFaturamentoImportado.numero_nf
-    **cliente** (VARCHAR(255)) - Nulo: ❌
SIGNIFICADO: msm campo de Pedido "razao_social_red" e RelatorioFaturamentoImportado.nome_cliente
-    **transportadora** (VARCHAR(255)) - Nulo: ✅
transportadora preenchida em Embarque, provavelmente preenchido ao rodar a função sincronizar_entrega_por_nf
-    **municipio** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "nome_cidade", Cidade real do cliente
-    **uf** (VARCHAR(2)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "cod_uf", UF real do cliente
-    **vendedor** (VARCHAR(100)) - Nulo: ✅
vendedor que realizou a venda, extraido de RelatorioFaturamentoImportado.vendedor
-    **cnpj_cliente** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "
-    **valor_nf** (FLOAT) - Nulo: ✅
SIGNIFICADO: valor total da nf extraido de RelatorioFaturamentoImportado.valor_total
-    **data_faturamento** (DATE) - Nulo: ✅
SIGNIFICADO: Data de emissão da nf
LINGUAGEM_NATURAL: ["data que faturou", "data de faturamento", "data de emissão da nf"]
CONTEXTO: 
OBSERVAÇÕES: Campo originado de RelatorioFaturamentoImportado.data_fatura

-    **data_embarque** (DATE) - Nulo: ✅
SIGNIFICADO: data_embarque de "Embarque"
-    **data_entrega_prevista** (DATE) - Nulo: ✅
SIGNIFICADO: Previsão de entrega
LINGUAGEM_NATURAL: ["previsao de entrega", "data prevista de entrega", "data que vai ser entregue", "quando entrega"]
CONTEXTO: Essa data é originada inicialmente através de uma hierarquia, caso não tenha agendamento no EmbarqueItem, utiliza-se a data de embarque + Lead time em dias uteis contidos nos vinculos e buscado o lead_time através do nome_tabela, transportadora e uf_destino contido em EmbarqueItem e uf, nome_tabela e transportadora em CidadeAtendida (vinculos), caso tenha a data da agenda em EmbarqueItem, será preenchido utilizado a data da agenda através da função sincronizar_entrega_por_nf
Ou seja, ela sempre segue a data da agenda, caso não tenha a data da agenda, utiliza-se a data de embarque + lead time util da transportadora
OBSERVAÇÕES: 


-    **data_hora_entrega_realizada** (DATETIME) - Nulo: ✅
SIGNIFICADO: Data em que foi entregue a NF
LINGUAGEM_NATURAL: ["dia que entregou", "data que foi entregue", "data da entrega", "entregou no dia"]
CONTEXTO: Data que foi preenchido o status "Entregue"
OBSERVAÇÕES: 


-    **entregue** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: gatilho de que foi entregue
LINGUAGEM_NATURAL: ["foi entregue"]
CONTEXTO: gatilho preenchido ao preencher a finalização da entrega com "Entregue"
OBSERVAÇÕES: 


-    **lead_time** (INTEGER) - Nulo: ✅
SIGNIFICADO: prazo de entrega em dias uteis por transportadora e por região
LINGUAGEM_NATURAL: [""]
CONTEXTO: Lead time em dias uteis contidos nos vinculos e buscado o lead_time através do nome_tabela, transportadora e uf_destino contido em EmbarqueItem e uf, nome_tabela e transportadora em CidadeAtendida (vinculos)
OBSERVAÇÕES: 


-    **reagendar** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: Aviso para o usuario da necessidade de reagendar a nf
LINGUAGEM_NATURAL: ["precisa reagendar", "pendente de reagendamento", "perdeu a agenda", "necessidade de reagendamento"]
CONTEXTO: Gatilho para gerar um filtro no monitoramento para avisar o usuario da necessidade de reagendar a entrega
OBSERVAÇÕES: 

-    **motivo_reagendamento** (VARCHAR(255)) - Nulo: ✅
SIGNIFICADO: motivo de reagendar a NF
LINGUAGEM_NATURAL: ["por que reagendou", "por que perdeu a agenda"]
CONTEXTO: Registro realizado ao reagendar uma entrega, utilizado para identificar gargalos e falhas que geraram a necessidade de reagendar a NF
OBSERVAÇÕES: 

-    **data_agenda** (DATE) - Nulo: ✅
SIGNIFICADO: msm campo de Pedido "agendamento", pode ser originado em Pedido ou pode ser preenchido/criado/reagendado nessa tabela e alterado diversas vezes, sendo registrado os detalhes e as criações em AgendamentoEntrega.
-    **observacao_operacional** (TEXT) - Nulo: ✅
Não me lembro qual o papel desse campo
-    **pendencia_financeira** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: Cobrança do financeiro referente a informações do monitoramento para confirmar data de entrega ou data prevista de entrega para poder provisionar o caixa
LINGUAGEM_NATURAL: ["pendencia financeira", "financeiro cobrando", "posição pro financeiro"]
CONTEXTO: Quando o financeiro previsa confirmar uma provisão no caixa ou atualizar uma informação divergente de entrega com o cliente
OBSERVAÇÕES: 

-    **resposta_financeiro** (TEXT) - Nulo: ✅
SIGNIFICADO: Resposta da logistica da pendencia financeira
LINGUAGEM_NATURAL: [""]
CONTEXTO: Normalmente os clientes de rede, exemplo Atacadão, Assai, Fort, Tenda etc. Lançam no contas a pagar apartir da data de recebimento e não da emissão da NF, porem muitas vezes esses clientes atrasam o lançamento para ganharem dias no vencimento e o financeiro fica emcima disso para não perderem dias no contas a receber e em alguns casos ainda não há canhoto no sistema portanto as "confirmações de entrega" se dá pelo motorista, transportadora e pelo portal do cliente, com isso o financeiro cobra a logistica de uma confirmação, canhoto etc para rebater ao cliente de que a mercadoria foi de fato entregue.
OBSERVAÇÕES: 

Não sei de onde vem esse log de criação
-    **criado_em** (DATETIME) - Nulo: ✅
-    **criado_por** (VARCHAR(100)) - Nulo: ✅

-    **nf_cd** (BOOLEAN) - Nulo: ✅
SIGNIFICADO: Campo gatilho que será a origem de nf_cd em Pedido
LINGUAGEM_NATURAL: ["NF está no CD", "nota voltou pro cd", "nf no cd"]
CONTEXTO: preenchido em EventoEntrega.tipo_evento, quando selecionado "NF no CD" dispara o gatilho para tornar "nf_cd"=True, alterando o status e disparando para a tabela de Pedido tornar o nf_cd = True através do separacao_lote_id, alterando o status_calculado para NF no CD e permitindo o usuario a cotar novamente o frete 
OBSERVAÇÕES: 

-    **finalizado_por** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: usuario que finalizou a entrega
LINGUAGEM_NATURAL: [""]
CONTEXTO: 
OBSERVAÇÕES: 
-    **finalizado_em** (DATETIME) - Nulo: ✅
SIGNIFICADO: momento que o usuario registrou a finalização da entrega
LINGUAGEM_NATURAL: [""]
CONTEXTO: 
OBSERVAÇÕES: 
-    **status_finalizacao** (VARCHAR(50)) - Nulo: ✅
SIGNIFICADO: Status da finalização da entrega, podendo ser "Entregue", "Cancelada", "Devolvida" e "Troca de NF".
LINGUAGEM_NATURAL: ["finalização da entrega", "como finalizou", "entregue", "trocou a nf", "foi devolvida", "nf foi cancelada"]
CONTEXTO: 
OBSERVAÇÕES: 
-    **nova_nf** (VARCHAR(20)) - Nulo: ✅
SIGNIFICADO: é a nova nf que substituiu a nf que foi trocada  
LINGUAGEM_NATURAL: ["nova nf", "nova nota"]
CONTEXTO: Ao trocar uma nf e para manter a rastreabilidade, criei essa função para registrar na nota antiga a Nova NF.
OBSERVAÇÕES: 

-    **substituida_por_nf_id** (INTEGER) - Nulo: ✅
Fiquei confuso no termo pois na NF nova fica o registro de qual nf substituiu em Evento e no badge do Status, mas pelo campo não sei a diferença desse campo para "nova_nf"
-    **canhoto_arquivo** (VARCHAR(500)) - Nulo: ✅
SIGNIFICADO: Arquivo do canhoto, em que ao subir qlqr arquivo nesse campo, altera o flag de "S/ canhoto" para "Canhoto OK"
LINGUAGEM_NATURAL: ["tem canhoto", "com canhoto", "canhoto assinado"]
CONTEXTO:



#### RELACIONAMENTOS:
- **comentarios** → ComentarioNF
Tela de relacionamento com outros usuarios com comentario e resposta na entrega, provavelmente será usada por representantes questionando as entregas.
Há um balão na tela das entregas com a qtd de comentarios não respondida para avisar o usuario da necessidade de responder
- **substituida_por_nf** → EntregaMonitorada
- **substituicoes** → EntregaMonitorada
- **agendamentos** → AgendamentoEntrega
Tela para registrar os agendamentos e reagendamentos da entrega
- **eventos** → EventoEntrega
Tela para registrar eventos que ocorreram durante a entrega e com o gatilho de "NF no CD" 
- **custos_extras** → CustoExtraEntrega
Tela sem uso nesse momento
- **logs** → RegistroLogEntrega
Tela de registros referente entrega, utilizado pela pessoa de monitoramento com tipos como "Ação", "Contado", "Informação"
- **historico_data_prevista** → HistoricoDataPrevista
Registro unificado de todas as alterações na entrega, só não sei se de fato registra tudo.
- **arquivos_entrega** → ArquivoEntrega
Tela para armazenar arquivos relevantes da entrega
- **pendencias_financeiras** → PendenciaFinanceiraNF
Acho que essa relação é para vincular as pendencias preenchidas no modulo financeiro para vincular nas entregas
---

### 🔸 RELATORIOFATURAMENTOIMPORTADO
**Tabela:** `relatorio_faturamento_importado`
**Total de Campos:** 19

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **numero_nf** (VARCHAR(20)) - Nulo: ❌
msm campo de Pedido "nf"
-    **data_fatura** (DATE) - Nulo: ✅
Data do faturamento
-    **cnpj_cliente** (VARCHAR(20)) - Nulo: ✅
msm campo do Pedido "cnpj_cpf"
-    **nome_cliente** (VARCHAR(255)) - Nulo: ✅
msm campo do Pedido "razao_social_red"
-    **valor_total** (FLOAT) - Nulo: ✅
valor total da NF, usado para substituir os valores nos EmbarqueItem após o registro das NFs nos EmbarqueItem e após a importação do RelatorioFaturamentoImportado através da função sincronizar_entrega_por_nf
-    **peso_bruto** (FLOAT) - Nulo: ✅
Mesma coisa do valor_total porem com o peso
-    **cnpj_transportadora** (VARCHAR(20)) - Nulo: ✅
Campo não deve ser utilizado pois o registro no embarque é mais confiavel
-    **nome_transportadora** (VARCHAR(255)) - Nulo: ✅
Campo não deve ser utilizado pois o registro no embarque é mais confiavel
-    **municipio** (VARCHAR(100)) - Nulo: ✅
msm campo do Pedido "nome_cidade"
-    **estado** (VARCHAR(2)) - Nulo: ✅
msm campo do Pedido "cod_uf"
-    **codigo_ibge** (VARCHAR(10)) - Nulo: ✅
msm campo do Pedido "codigo_ibge"
-    **origem** (VARCHAR(50)) - Nulo: ✅
msm campo do Pedido "num_pedido"
-    **incoterm** (VARCHAR(20)) - Nulo: ✅
Campo com o incoterm do faturamento, tem relação com a rota do Pedido quando for RED na rota do Pedido o incoterm será "[RED] REDESPACHO", quando for FOB na rota do Pedido o incoterm será "[FOB] FOB" e para todas as outras rotas no Pedido o incoterm será "[CIF] CIF"
-    **vendedor** (VARCHAR(100)) - Nulo: ✅
Campo com o vendedor que realizou a venda e enviou o pedido para ser faturado, detentor da venda, campo de relação com o vendedor_vinculado em Usuario.
-    **ativo** (BOOLEAN) - Nulo: ❌
Campo que criei para tirar as NFs FOB do monitoramento, visto que a entrega finaliza na coleta do pedido pelo cliente, porem vou alterar para manter o registro no monitoramento, mesmo que sejá preenchido a data de entrega realizada pela data de embarque, esse campo não indica se a nf é valida, foi apenas uma maneira pratica de tirar do monitoramento em um determinado momento, ou seja, as nfs "inativas" são validas tambem.
-    **inativado_em** (DATETIME) - Nulo: ✅
-    **inativado_por** (VARCHAR(100)) - Nulo: ✅
-    **criado_em** (DATETIME) - Nulo: ✅

---

### 🔸 DESPESAEXTRA
**Tabela:** `despesas_extras`
**Total de Campos:** 12

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **frete_id** (INTEGER) - Nulo: ❌
-    **tipo_despesa** (VARCHAR(50)) - Nulo: ❌
-    **setor_responsavel** (VARCHAR(20)) - Nulo: ❌
-    **motivo_despesa** (VARCHAR(50)) - Nulo: ❌
-    **tipo_documento** (VARCHAR(20)) - Nulo: ❌
-    **numero_documento** (VARCHAR(50)) - Nulo: ❌
-    **valor_despesa** (FLOAT) - Nulo: ❌
-    **vencimento_despesa** (DATE) - Nulo: ✅
-    **observacoes** (TEXT) - Nulo: ✅
-    **criado_em** (DATETIME) - Nulo: ✅
-    **criado_por** (VARCHAR(100)) - Nulo: ❌

#### RELACIONAMENTOS:
- **frete** → Frete

---

### 🔸 TRANSPORTADORA
**Tabela:** `transportadoras`
**Total de Campos:** 8

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **cnpj** (VARCHAR(20)) - Nulo: ❌
-    **razao_social** (VARCHAR(120)) - Nulo: ❌
-    **cidade** (VARCHAR(100)) - Nulo: ❌
-    **uf** (VARCHAR(2)) - Nulo: ❌
-    **optante** (BOOLEAN) - Nulo: ✅
-    **condicao_pgto** (VARCHAR(50)) - Nulo: ✅
-    **freteiro** (BOOLEAN) - Nulo: ✅

#### RELACIONAMENTOS:
- **embarques** → Embarque
- **cidades_atendidas** → CidadeAtendida
- **cotacoes** → Cotacao
- **fretes** → Frete
- **faturas_frete** → FaturaFrete
- **conta_corrente** → ContaCorrenteTransportadora
- **tabelas_frete** → TabelaFrete
- **historico_tabelas_frete** → HistoricoTabelaFrete

---

### 🔸 USUARIO
**Tabela:** `usuarios`
**Total de Campos:** 15

#### CAMPOS:
Cadastro dos usuarios
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **nome** (VARCHAR(100)) - Nulo: ❌
-    **email** (VARCHAR(120)) - Nulo: ❌
-    **senha_hash** (VARCHAR(200)) - Nulo: ❌
-    **perfil** (VARCHAR(30)) - Nulo: ✅
SIGNIFICADO: 1 dos critérios  para se definir as permissões de acesso no sistema
-    **status** (VARCHAR(20)) - Nulo: ✅
-    **empresa** (VARCHAR(100)) - Nulo: ✅
-    **cargo** (VARCHAR(100)) - Nulo: ✅
-    **telefone** (VARCHAR(20)) - Nulo: ✅
-    **vendedor_vinculado** (VARCHAR(100)) - Nulo: ✅
SIGNIFICADO: vinculação do vendedor para enxergar e pesquisar apenas informações correspondentes às vendas dele
LINGUAGEM_NATURAL: [""]
CONTEXTO: é vinculado no cadastro do vendedor o nome de referencia dele ou da empresa dele contido na coluna vendedor no RelatorioFaturamentoImportado
OBSERVAÇÕES: 

-    **criado_em** (DATETIME) - Nulo: ✅
-    **aprovado_em** (DATETIME) - Nulo: ✅
-    **aprovado_por** (VARCHAR(120)) - Nulo: ✅
-    **ultimo_login** (DATETIME) - Nulo: ✅
-    **observacoes** (TEXT) - Nulo: ✅

#### RELACIONAMENTOS:
Acredito que esse relacionamentos seja para definir a permissão que cada usuario vai ter de acesso no sistema.
- **pedidos** → Pedido
- **cotacoes** → Cotacao
- **registros_portaria_criados** → ControlePortaria
- **registros_portaria_atualizados** → ControlePortaria

---

### 🔸 CONTATOAGENDAMENTO
Tabela usada para auxiliar na roteirização com informação se o cliente exige que a entrega seja agendada e a forma de agendamento dessa entrega.
Utilizada no monitoramento para realizar o agendamento / reagendamento e para a roteirização em Pedido para alertar sobre possivel necessidade de agendamento antes do embarque para não correr o risco de ter que voltar com a mercadoria para a empresa por não ter agendado a entrega.
**Tabela:** `contatos_agendamento`
**Total de Campos:** 6

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **cnpj** (VARCHAR(20)) - Nulo: ❌
cnpj do cliente
-    **forma** (VARCHAR(50)) - Nulo: ✅
forma de solicitar a agenda ou preenchido com "SEM AGENDAMENTO" informando que o cliente não necessita de agendamento para realizar a entrega.
Campos SELECT = "PORTAL", "TELEFONE", "E-MAIL", "COMERCIAL"(nesse caso a logistica solicita para o comercial agendar a entrega) e "SEM AGENDAMENTO" (dispensado da necessidade de agendamento)

Campos digitaveis para auxiliar na informação de como realizar o agendamento
-    **contato** (VARCHAR(255)) - Nulo: ✅
-    **observacao** (VARCHAR(255)) - Nulo: ✅

-    **atualizado_em** (DATETIME) - Nulo: ✅

---

### 🔸 CIDADE
**Tabela:** `cidades`
**Total de Campos:** 8

#### CAMPOS:
- 🔑 **id** (INTEGER) - Nulo: ❌
-    **nome** (VARCHAR(100)) - Nulo: ❌
nome da cidade no padrão do IBGE (nada demais, apenas a garantia de acentuação e sem erro ortografico)
-    **uf** (VARCHAR(2)) - Nulo: ❌
nome do estado no padrão do IBGE em sigla de UF (2 letras e maiusuculas)
-    **codigo_ibge** (VARCHAR(20)) - Nulo: ❌
identificação unica daquela cidade e daquele estado composta por 7 digitos.
-    **icms** (FLOAT) - Nulo: ❌
Percentual de icms da região, esse campo usa como referencia a origem do embarque em SP pois é onde a empresa reside
-    **substitui_icms_por_iss** (BOOLEAN) - Nulo: ✅
Campo criado por garantia para caso haja regiões onde o frete é cobrado através de NFS ao invés de CTe, porem não me lembro de algum lugar que use esse campo como True

Campos de divisão das regiões entre UF e cidade, não é utilizado em nenhum lugar do sistema porem pode facilmente ser usado em todos os lugares que houver cidade.
A quebra sequencial seria: UF > mesorregiao > microrregiao > cidade
-    **microrregiao** (VARCHAR(100)) - Nulo: ✅
-    **mesorregiao** (VARCHAR(100)) - Nulo: ✅

#### RELACIONAMENTOS:
- **cidades_atendidas** → CidadeAtendida

---


## 📋 PERGUNTAS PARA MAPEAMENTO SEMÂNTICO

### ESTRATÉGIA DE MAPEAMENTO:

**🔄 CAMPOS COMUNS:** Responda uma vez na seção "CAMPOS COMUNS" acima
**🔸 CAMPOS ESPECÍFICOS:** Responda apenas se houver diferença ou contexto específico do modelo
**➡️ REFERENCIAR:** Para campos já mapeados, apenas escreva "VER CAMPOS COMUNS"

### QUANDO ESPECIFICAR POR MODELO:

**ESPECIFIQUE quando:**
- O campo tem significado diferente em cada modelo
- Há regras específicas para aquele modelo
- O contexto de uso muda significativamente
- Existem valores possíveis diferentes

**EXEMPLOS:**
- `status` no FRETE vs `status` no EMBARQUE (regras diferentes)
- `cliente` no PEDIDO vs `cliente` no MONITORAMENTO (mesma coisa, só referenciar)
- `data_embarque` é igual em todos os modelos (só referenciar)

### PARTE 1: CAMPOS PRINCIPAIS (OBRIGATÓRIO)

Para cada campo listado acima, preciso que você responda:

#### A) SIGNIFICADO REAL
**Pergunta:** O que este campo representa no seu negócio?
- Exemplo: `data_embarque` = "Data que o caminhão saiu da nossa empresa"

#### B) COMO VOCÊ SE REFERE A ELE
**Pergunta:** Como você fala/escreve sobre este campo no dia a dia?
- Exemplo: `data_embarque` = ["saiu", "embarcou", "partiu", "saída", "embarque"]

#### C) SINÔNIMOS E VARIAÇÕES
**Pergunta:** Que outras palavras significam a mesma coisa?
- Exemplo: `peso_total` = ["peso", "quilos", "kg", "toneladas", "peso bruto"]

#### D) CONTEXTOS DE USO
**Pergunta:** Em que situações você consulta este campo?
- Exemplo: `status` = ["verificar se entregou", "ver situação", "conferir andamento"]

### PARTE 2: RELACIONAMENTOS (IMPORTANTE)

#### A) COMO OS DADOS SE CONECTAM
**Pergunta:** Como você explicaria a relação entre estes modelos?
- Exemplo: "1 Embarque tem vários Pedidos, 1 Pedido vira 1 Frete"

#### B) CONSULTAS TÍPICAS
**Pergunta:** Que tipo de pergunta você faz que envolve múltiplas tabelas?
- Exemplo: "Quais entregas do Atacadão estão atrasadas?"

### PARTE 3: REGRAS DE NEGÓCIO (CRÍTICO)

#### A) STATUS E ESTADOS
**Pergunta:** Quais os possíveis valores dos campos de status e o que significam?
- Exemplo: `status_pedido` = ["ABERTO", "FATURADO", "ENTREGUE", "CANCELADO"]

#### B) CÁLCULOS E DERIVAÇÕES
**Pergunta:** Existem campos que são calculados a partir de outros?
- Exemplo: `valor_por_kg` = valor_frete ÷ peso_total

#### C) FILTROS COMUNS
**Pergunta:** Como você normalmente filtra os dados?
- Exemplo: "Por cliente", "Por período", "Por UF", "Por transportadora"

### PARTE 4: LINGUAGEM NATURAL (ESSENCIAL)

#### A) FRASES TÍPICAS
**Pergunta:** Como você faria essas perguntas normalmente?
- Exemplo: "Cadê as entregas do Assai?" = Filtrar EntregaMonitorada por cliente="Assai"

#### B) TERMOS ESPECÍFICOS
**Pergunta:** Existem termos únicos do seu setor/empresa?
- Exemplo: "NF no CD" = Nota fiscal que ainda não saiu do centro de distribuição

#### C) ABREVIAÇÕES
**Pergunta:** Que siglas/abreviações vocês usam?
- Exemplo: "CTe" = Conhecimento de Transporte eletrônico

### PARTE 5: DADOS REAIS DE REFERÊNCIA

#### CLIENTES PRINCIPAIS (Top 20):

#### TRANSPORTADORAS ATIVAS (3):
 1. {'id': 1, 'razao_social': 'Transportadora Teste 1 Ltda', 'cnpj': '12345678000123', 'cidade': 'São Paulo', 'uf': 'SP', 'freteiro': False}
 2. {'id': 2, 'razao_social': 'Freteiro Autônomo Silva', 'cnpj': '98765432000198', 'cidade': 'Rio de Janeiro', 'uf': 'RJ', 'freteiro': True}
 3. {'id': 3, 'razao_social': 'Transportes Express', 'cnpj': '11111111000111', 'cidade': 'Belo Horizonte', 'uf': 'MG', 'freteiro': False}

#### ESTADOS ATENDIDOS (0):


---

## 🎯 PRÓXIMOS PASSOS

1. **RESPONDER AS PERGUNTAS:** Vá seção por seção respondendo cada pergunta
2. **SER ESPECÍFICO:** Quanto mais detalhado, melhor o mapeamento
3. **DAR EXEMPLOS:** Sempre que possível, cite exemplos reais
4. **NÃO INVENTAR:** Se não souber, diga "não sei" - vamos descobrir juntos
5. **VALIDAR TESTES:** Após o mapeamento, testaremos com consultas reais

## 📝 COMO RESPONDER

### FORMATO PARA CAMPOS COMUNS:
```
CAMPO: cliente / nome_cliente / raz_social_red
SIGNIFICADO: Nome da empresa que compra nossos produtos
LINGUAGEM_NATURAL: ["cliente", "comprador", "empresa", "razão social"]
CONTEXTO: Filtrar vendas, relatórios, consultas
OBSERVAÇÕES: Pode aparecer abreviado em alguns relatórios
---
```

### FORMATO PARA CAMPOS ESPECÍFICOS:
```
CAMPO: status (no modelo FRETE)
SIGNIFICADO: Situação atual do frete (aprovado, pendente, pago)
LINGUAGEM_NATURAL: ["status", "situação", "estado do frete"]
CONTEXTO: Controle financeiro, aprovações
OBSERVAÇÕES: Específico para fretes, diferente do status geral
---
```

### FORMATO PARA REFERENCIAR:
```
CAMPO: cliente (no modelo PEDIDO)
RESPOSTA: VER CAMPOS COMUNS - mesmo significado
OBSERVAÇÕES: Neste modelo, vem do campo "raz_social_red"
---
```

## ⚠️ LEMBRETE IMPORTANTE

Este mapeamento é a BASE para tornar o Claude AI verdadeiramente útil no seu sistema.
Quanto melhor o mapeamento, mais precisas serão as respostas e relatórios gerados.

**Vamos começar?** 🚀

---
*Gerado automaticamente pelo sistema_real_data.py*
*Dados extraídos diretamente do PostgreSQL*

---
*Gerado automaticamente pelo sistema_real_data.py*
*Dados extraídos diretamente do PostgreSQL*
