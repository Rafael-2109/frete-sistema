# Opção 701 — Entradas no Estoque

> **Módulo**: Logística
> **Páginas de ajuda**: 6 páginas consolidadas
> **Atualizado em**: 2026-02-15

## Função

Efetua entrada de produtos para armazenagem na transportadora (Armazém Geral). Registra a transferência fiscal de mercadorias do cliente para o estoque da transportadora usando Nota Fiscal do cliente.

## Quando Usar

- Cliente contrata serviço de armazenagem (Armazém Geral)
- Produtos chegam para armazenagem e precisam dar entrada no sistema
- Integração com sistemas WMS (Warehouse Management System)
- Necessidade de controle fiscal de produtos de terceiros

## Pré-requisitos

- Cliente configurado na opção 388 como **ARMAZEM GERAL** ou **OPERADOR LOGISTICO**
- Nota Fiscal do cliente transferindo mercadoria para a transportadora
- Produtos cadastrados (opção 741) ou chave NF-e para cadastro automático
- CFOP cadastrado (opção 432) ou uso automático de 1905/2905

## Campos / Interface

### Tela Principal

- **CNPJ do consignatário**: Proprietário das mercadorias, contratante dos serviços de armazenagem
- **CNPJ do emitente da NF**: Emissor da Nota Fiscal dos produtos (pode ser diferente do consignatário)

### Métodos de Entrada

#### Importar NF-e (Automático)

- **Chave de acesso**: Captura dados da NF-e via XML
- Todos os produtos e ICMSs dão entrada automaticamente
- Cadastro do produto (opção 741) ocorre automaticamente
- IBS/CBS salvos da nota fiscal
- CST e Código de Classificação Tributária salvos no cadastro de mercadorias

#### Digitação Manual

- **Código do produto**: Conforme opção 741
- **Quantidade**: Quantidade de produtos
- **Peso**: Peso dos produtos
- **Volumes**: Quantidade de volumes
- **Valor**: Valor dos produtos
- **ICMS**: Valor do ICMS (guardado para crédito fiscal)

### Opções Relacionadas no Menu

- **Informar entrada no estoque**: Registra produtos entrando
- **Excluir Nota Fiscal de entrada**: Remove NF incluída anteriormente

## Fluxo de Uso

### Processo Armazém Geral

```
1. Opção 701 → Entrada no estoque
   - Cliente envia produtos com NF própria
   - Importar NF-e ou digitar manualmente
   - Sistema guarda ICMS para crédito fiscal (se configurado)

2. Opção 721 → Situação do estoque
   - Consulta entradas, saídas e saldos

3. Opção 702 → Saída do estoque
   - Registra NF de venda do cliente
   - Gera NFT (Nota Fiscal de Transferência)

4. Opção 707 → Aprovação da NFT
   - Submete NFT ao SEFAZ
   - Imprime NFT aprovada

5. Opção 004 → Emissão do CTRC
   - Para transporte da mercadoria
   - Usa NFT como documento base

6. Opção 733 → Cobrança do serviço
   - Emite RPS para cobrar armazenagem
```

### Processo Operador Logístico

```
1. Opção 701 → Entrada no estoque
   - Mesma entrada de Armazém Geral

2. Opção 702 → Saída de estoque
   - Usa MESMAS NFs de entrada
   - NÃO emite NFT

3. Opção 733 → Cobrança do serviço
```

### Integração com WMS

```
1. Opção 701 → Entrada manual ou importação NF-e

2. Opção 708 → Exportar arquivo de entradas
   - Gera CSV com NFs que deram entrada
   - WMS importa para controle de armazenagem

3. WMS → Controle interno da armazenagem

4. Opção 709 → Recebe arquivo de NFs de saída
   - WMS exporta NFs de saída
   - SSW importa dispensando digitação (opção 702)

5. Opção 702 → Emissão NF-e de Transferência
   - Usa NFs importadas do WMS

6. Opção 707 → Aprovação e impressão da NFT

7. Opção 004 → Emissão do CTRC
```

## Integração com Outras Opções

### Operações de Estoque

- **Opção 702**: Saídas do estoque
  - Armazém Geral: usa NF de venda do cliente + emite NFT
  - Operador Logístico: usa mesmas NFs de entrada, sem NFT
- **Opção 721**: Situação do estoque (entradas, saídas, saldos)
- **Opção 723**: Ajuste de estoque (corrige saldos quando diferença física vs sistema)
- **Opção 722**: Relatório de situação do estoque (histórico de movimentações)
- **Opção 703**: Relação de NFs emitidas (todas as NFs de entrada/saída/retorno)

### Documentos Fiscais

- **Opção 707**: Aprovação e impressão de NF de Transferência (SEFAZ)
- **Opção 004**: Emissão de CTRC para transporte
- **Opção 432**: Cadastro de CFOPs
  - Padrão automático: 1905/2905 (entrada para depósito fechado ou armazém geral)
- **Opção 433**: Livro Fiscal de ICMS (créditos gerados)
- **Opção 512**: SPED Fiscal (registro de inventário de produtos de terceiros)

### Cadastros

- **Opção 388**: Configuração de cliente
  - Define se é ARMAZÉM GERAL ou OPERADOR LOGÍSTICO
  - Flag VINCULAR NF DE ENTRADA (para repasse ICMS)
- **Opção 741**: Cadastro de produtos
  - Cadastro automático na importação NF-e
  - CST e Classificação Tributária salvos para uso em NFT
- **Opção 483**: Cadastro de clientes (consignatário/emitente)

### Cobrança e Transporte

- **Opção 733**: Cobrança pelo serviço de armazenagem (emite RPS)
- **Opção 009**: Cobrança alternativa de armazenagem
- **Opção 725**: Romaneio de carregamento
  - Lista produtos para transporte em Manifestos (opção 020) ou Romaneios (opção 035)
- **Opção 020**: Manifestos
- **Opção 035**: Romaneios de Entrega

### Integração WMS

- **Opção 708**: Exporta arquivo CSV de entradas para WMS
- **Opção 709**: Importa arquivo CSV de saídas do WMS
  - Arquivo de Notas (layout específico)
  - Arquivo de Saldos (para SPED Fiscal - opção 512)

## Observações e Gotchas

### Tipos de Operação

**Armazém Geral:**
- Cliente transfere mercadoria fiscalmente para a transportadora
- Saída usa NF de venda do cliente
- Transportadora emite NFT (Nota Fiscal de Transferência)
- NFT deve ser autorizada pelo SEFAZ (opção 707)

**Operador Logístico:**
- Cliente mantém propriedade fiscal da mercadoria
- Saída usa as MESMAS NFs de entrada
- NÃO emite NFT

### ICMS e Tributação

**VINCULAR NF DE ENTRADA (opção 388):**
- Quando ativado para o consignatário:
  - Sistema guarda valores de ICMS das NFs de entrada
  - Gera **CRÉDITOS** no Livro Fiscal de ICMS (opção 433)
  - Gera **CRÉDITOS** no SPED Fiscal (opção 512)
  - Na saída (opção 702), gera **DÉBITOS** correspondentes (repasse do ICMS)

**IBS/CBS:**
- Valores salvos da NF de entrada
- CST e Classificação Tributária salvos no cadastro (opção 741)
- Usados na emissão da NFT (opção 702)
- Padrão se não cadastrado: CST 410, Classificação 410999

### CFOPs Automáticos

**Entrada (opção 701):**
- Se CFOP da NF não estiver cadastrado: 1905/2905
  - "Entrada de mercadoria recebida para depósito em depósito fechado ou armazém geral"

**Saída/Retorno (opção 702):**
- **N**: Retorno não simbólico → 5906/6906
- **S**: Retorno simbólico → 5907/6907
- **E**: Devolução/retorno de embalagem → 5921/6921
- **I**: Envio para industrialização → 5902/6902
- **Simples Remessa**: Cliente de outro estado → 5949/6949

### Retorno Simbólico vs Não Simbólico

**Retorno simbólico (CFOP 5907/6907):**
- Produto sai do armazém para ser entregue ao comprador
- Consignatário precisa efetuar entrada no seu estoque para corrigir saldo
- Uso: corrigir saldo contábil sem movimentação física para o consignatário

**Retorno não simbólico (CFOP 5906/6906):**
- Produto retorna fisicamente ao consignatário

### Simples Remessa

**Exemplo:**
- Transportadora em Curitiba/PR
- Cliente consignatário em Belo Horizonte/MG
- Venda para terceiro em São Paulo/SP
- NF de venda: origem BH, destino SP
- Mercadoria fisicamente em Curitiba
- **NF Simples Remessa** (5949/6949): comprova transporte Curitiba → São Paulo
- Evita problemas em barreiras fiscais

### Limites e Restrições

- **NFT**: SEFAZ limita em 990 itens por NFT
- **Impressão NFT**: Apenas pela opção 707 (não pela 702)
- **Exclusão**: Só pode excluir NF de entrada se não houver saídas vinculadas

### Relatórios e Consultas

**Opção 722 (Relatório de situação):**
- Histórico de movimentações do consignatário
- Filtros: período, CNPJ, mercadoria, tipo (E/S/A)
- Excel útil para cálculo de cobrança

**Opção 703 (Relação de NFs):**
- **E**: NFs de entrada (opção 701)
- **S**: NFs de saída (opção 702)
- **R**: NFTs (opção 707)
- **C**: Simples remessa
- **T**: Todas
- Apenas operações de Armazém Geral

**Opção 721 (Situação do estoque):**
- Entradas, saídas e saldos em tempo real
- Por consignatário e produto

### Integração WMS (opção 709)

**Layout Arquivo de Notas (CSV):**
```
CNPJ_EMIT (14), CNPJ_DEST (14), SER_NFE (3), NRO_NFE (9),
COD_PRODUTO (25), QTDE_PRODUTO (12,4), SER_NFE_ORI (3),
NRO_NFE_ORI (9), PESO_PRODUTO (10,3), QTDE_VOL (10),
OBS_ITEM (100): NLOTE#QLOTE#DFAB#DVAL#VPMC
```

**Arquivo de Saldos:**
- Para SPED Fiscal (opção 512)
- Registro de inventário de produtos de terceiros

### Pontos de Atenção

- **Cliente deve estar configurado** (opção 388) antes da primeira entrada
- **Importação NF-e é recomendada**: evita erros de digitação e cadastra produtos automaticamente
- **ICMS só é guardado** se cliente tiver flag VINCULAR NF DE ENTRADA
- **Ajustes de estoque** (opção 723) devem ser usados com cuidado (afeta inventário fiscal)
- **WMS deve gerar CSV no layout correto** (opção 709) para importação funcionar
- **NFT precisa de autorização SEFAZ** (opção 707) antes de poder transportar
- **Cobrança pelo serviço** (opção 733) é independente da entrada/saída
- **Romaneio de carregamento** (opção 725) é opcional, útil para separação física
