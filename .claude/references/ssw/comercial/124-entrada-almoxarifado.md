# Opção 124 — Entrada no Almoxarifado

> **Módulo**: Comercial
> **Páginas de ajuda**: 4 páginas consolidadas
> **Atualizado em**: 2026-02-14

## Função
Registra entradas de produtos no almoxarifado da transportadora com base em Notas Fiscais de compra, permitindo controle de estoque por unidade e integração com contas a pagar e veículos.

## Quando Usar
- Recebimento de produtos comprados de fornecedores
- Registro de material adquirido para consumo operacional
- Entrada automática após lançamento de despesa (via opção 475)
- Registro de compras realizadas via pedidos (opção 158)

## Pré-requisitos
- **Opção 123**: Tabela de produtos cadastrados
- **Opção 401**: Liberação do Almoxarifado na unidade
- **Opção 478**: Cadastro de fornecedores
- **Opção 503**: Eventos configurados para sugerir entrada (integração com contas a pagar)
- **Opção 158**: Pedidos de compras (opcional, para vincular entradas)

## Campos / Interface

### Tela de Entrada (Opção 124)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Almoxarifado unid | Sim | Unidade que irá estocar os produtos |
| Fornecedor | Sim | Fornecedor cadastrado (opção 478) |
| Nota Fiscal | Sim | Número da NF de compra dos produtos |
| Código | Sim | Código do produto cadastrado (opção 123) |
| Código fornecedor | Não | Código do produto conforme descrito na NF do fornecedor |
| Pedido | Não | Número do pedido de compras (opção 158) vinculado |
| Endereço | Não | Local de estocagem conforme cadastro do produto (opção 123) |
| Quantidade entrada | Sim | Quantidade do produto que dará entrada no estoque |
| Valor unitário | Sim | Valor da unidade do produto |
| Histórico | Não | Observação sobre o produto, compra, etc. |

### Tela de Saída (Opção 126)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| ALMOXARIFADO UNID | Sim | Almoxarifado da unidade de origem (MTZ pode informar qualquer) |
| CÓDIGO | Sim | Código do produto a ser retirado |
| QTDE SAÍDA | Sim | Quantidade a ser retirada do estoque |
| UNID USUÁRIA | Condicional | Unidade destino (entrada automática no almoxarifado dela) |
| PLACA VEÍCULO | Condicional | Placa do veículo (frota→opção 324, terceiro→opção 486) |
| HISTÓRICO | Não | Observação sobre a retirada |
| RETIRADO POR | Não | Nome da pessoa que fez a retirada |

### Tela de Ajuste (Opção 127)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| Nova quantidade saldo | Não | Novo saldo de estoque (apagar para zerar) |
| Novo valor unitário | Não | Novo valor unitário do produto |
| Novo pendentes | Não | Nova quantidade de produtos pendentes em Compras (opção 158) |

### Tela de Consulta (Opção 128)
| Campo | Obrigatório | Descrição |
|-------|-------------|-----------|
| ALMOXARIFADO UNID | Sim | Unidade que terá o estoque consultado |
| PERÍODO MOVIMENTO | Não | Seleciona produtos com movimento (entrada/saída) no período |
| CÓDIGO | Não | Produto específico a ser consultado |
| ESTOQUE MÍNIMO | Sim | **C** (acima do mínimo), **B** (abaixo), **A** (ambos/não verifica) |
| MOSTRAR EM | Sim | **V** (vídeo/tela) ou **R** (relatório) |

## Fluxo de Uso

### Entrada de Produtos
1. Receber NF de compra do fornecedor
2. Acessar opção 124
3. Informar almoxarifado da unidade
4. Selecionar fornecedor (opção 478)
5. Informar número da Nota Fiscal
6. Para cada produto:
   - Informar código (opção 123)
   - Opcionalmente vincular código do fornecedor
   - Opcionalmente vincular pedido de compras (opção 158)
   - Opcionalmente informar endereço de estocagem
   - Informar quantidade entrada e valor unitário
   - Adicionar histórico se necessário
7. Salvar entrada → produto é adicionado ao estoque

### Saída de Produtos
1. Acessar opção 126
2. Informar almoxarifado da unidade
3. Informar código do produto
4. Informar quantidade de saída
5. Escolher destino:
   - **Para outra unidade**: informar UNID USUÁRIA (entrada automática no almoxarifado dela)
   - **Para veículo da frota**: informar PLACA VEÍCULO → lançamento no resultado do veículo (opção 324)
   - **Para veículo terceiro**: informar PLACA VEÍCULO → lançamento na CCF do proprietário (opção 486)
6. Adicionar histórico e nome do responsável pela retirada
7. Salvar saída → produto é deduzido do estoque

### Ajuste de Saldo (MTZ apenas)
1. Acessar opção 127
2. Informar nova quantidade saldo (apagar para zerar)
3. Opcionalmente informar novo valor unitário
4. Opcionalmente informar nova quantidade pendente em compras
5. Salvar ajuste

### Consulta de Estoque
1. Acessar opção 128
2. Informar almoxarifado da unidade
3. Opcionalmente filtrar por período de movimento
4. Opcionalmente filtrar por código de produto específico
5. Escolher filtro de estoque mínimo (**C**, **B** ou **A**)
6. Escolher exibição (**V** vídeo ou **R** relatório)
7. Visualizar estoque atual

## Integração com Outras Opções
| Opção | Relação |
|-------|---------|
| 123 | Cadastro de produtos (tabela mestre) |
| 124 | Entrada no almoxarifado (esta opção) |
| 126 | Saída do almoxarifado |
| 127 | Ajuste de saldo do almoxarifado (MTZ apenas) |
| 128 | Consulta ao almoxarifado |
| 158 | Pedidos de compras (vinculação opcional em entradas) |
| 324 | Resultado do veículo (saída para frota) |
| 325 | Controle de estoque de combustível em bomba própria (separado do almoxarifado) |
| 401 | Cadastro de unidades (liberação do almoxarifado) |
| 475 | Contas a pagar (pode sugerir entrada automática) |
| 478 | Cadastro de fornecedores |
| 486 | CCF do proprietário (saída para veículo terceiro) |
| 503 | Cadastro de eventos (configuração para sugerir entrada via contas a pagar) |

## Observações e Gotchas
- **Controle por unidade**: Cada unidade pode possuir seu próprio almoxarifado
- **Almoxarifado não é ativo**: Produtos são lançados em contas de resultados, não em estoques do ativo (produtos são para consumo, não comercialização/industrialização)
- **Combustível separado**: Controle de estoque de bomba própria é feito pela opção 325, não pelo almoxarifado
- **Integração com pedidos**: Entrada pode ser vinculada a pedidos de compras (opção 158), registrando no histórico do pedido
- **Repasse para frota**: Saída para veículo da frota gera despesa no resultado do veículo (opção 324)
- **Repasse para terceiros**: Saída para veículo terceiro gera débito na CCF do proprietário (opção 486)
- **Entrada automática**: Contas a pagar (opção 475) pode sugerir entrada se EVENTO (opção 503) estiver configurado
- **Transferência entre unidades**: Saída para UNID USUÁRIA gera entrada automática no almoxarifado de destino
- **Ajustes restritos**: Opção 127 (ajuste de saldo) é exclusiva para usuários da MTZ
- **Endereçamento**: Campo endereço permite organizar localização física do produto no almoxarifado
- **Histórico de compras**: Pedidos vinculados facilitam rastreabilidade e conferência
