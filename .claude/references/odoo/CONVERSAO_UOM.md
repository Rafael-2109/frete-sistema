# Documentação: Conversão de Código/Unidade de Medida no Odoo

**Status**: Documentação de referência (sem implementação)
**Data**: 14/01/2026

---

## 1. Fluxo de Recebimento de Compras no Odoo

### Diagrama do Processo

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    FLUXO COMPLETO DE RECEBIMENTO                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 1. PEDIDO DE COMPRA (purchase.order)                             │   │
│  │    ├─ Criação: MANUAL pelo Compras                               │   │
│  │    ├─ Quantidade: Digitada já convertida (ex: 60.000 units)      │   │
│  │    ├─ Preço: Por unidade (ex: R$ 0,041)                          │   │
│  │    └─ Gera: Picking (recebimento) automaticamente                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                               ↓                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 2. NF-e RECEBIDA (l10n_br_ciel_it_account.dfe)                   │   │
│  │    ├─ Origem: AUTOMÁTICO via SEFAZ                               │   │
│  │    ├─ Quantidade NF: Original do fornecedor (ex: 60 ML)          │   │
│  │    ├─ Conversão: NÃO é feita automaticamente                     │   │
│  │    └─ Vinculação: Manual com PO existente                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                               ↓                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 3. PICKING (stock.picking)                                       │   │
│  │    ├─ Origem: AUTOMÁTICO do PO                                   │   │
│  │    ├─ Quantidade: Herdada do PO (60.000 units)                   │   │
│  │    └─ Validação: Confere NF recebida vs PO                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                               ↓                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ 4. ESTOQUE (stock.move)                                          │   │
│  │    ├─ Movimento: AUTOMÁTICO do Picking                           │   │
│  │    └─ Entrada: Quantidade correta (60.000 units)                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Responsabilidades: Manual vs Automático

| Etapa | Tipo | Responsável | Ação |
|-------|------|-------------|------|
| **Criar PO** | MANUAL | Compras | Digita quantidade convertida |
| **Converter UM** | MANUAL | Compras | Multiplica por 1000 se Milhar |
| **Receber NF-e** | AUTOMÁTICO | Odoo/SEFAZ | Download via certificado |
| **Vincular NF↔PO** | MANUAL | Recebimento | Seleciona PO no DFE |
| **Criar Picking** | AUTOMÁTICO | Odoo | Gerado ao aprovar PO |
| **Validar Picking** | MANUAL | Almoxarifado | Confere físico vs sistema |
| **Movimentar Estoque** | AUTOMÁTICO | Odoo | Ao finalizar Picking |

---

## 3. Campos Importantes por Modelo

### 3.1 DFE (NF-e recebida)
**Modelo**: `l10n_br_ciel_it_account.dfe.line`

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `det_prod_cprod` | char | Código do produto no fornecedor | "210030327" |
| `det_prod_xprod` | char | Descrição do produto na NF | "ROTULO ADESIVO..." |
| `det_prod_qcom` | float | **Quantidade na NF** | 60.0 |
| `det_prod_ucom` | char | **UM na NF** | "ML" (Milhar) |
| `det_prod_vuncom` | float | Valor unitário NF | 41.00 (por Milhar) |
| `det_prod_vprod` | float | Valor total | 2460.00 |
| `l10n_br_quantidade` | float | Qtd para estoque (NÃO CONVERTE) | 60.0 |
| `product_uom_id` | many2one | UM do estoque | Units |
| `product_id` | many2one | Produto vinculado | [28241, 'ROTULO...'] |
| `purchase_line_id` | many2one | Linha do PO vinculada | False (não vincula auto) |

### 3.2 Pedido de Compra
**Modelo**: `purchase.order.line`

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `product_id` | many2one | Produto | [28241, 'ROTULO...'] |
| `product_qty` | float | **Quantidade pedida** | 60000.0 |
| `product_uom` | many2one | UM do pedido | Units |
| `price_unit` | float | Preço unitário | 0.041 |
| `qty_received` | float | Quantidade recebida | 60000.0 |
| `qty_invoiced` | float | Quantidade faturada | 60000.0 |

### 3.3 Picking (Recebimento)
**Modelo**: `stock.move`

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `product_id` | many2one | Produto | [28241, 'ROTULO...'] |
| `product_uom_qty` | float | **Quantidade demanda** | 60000.0 |
| `quantity` | float | Quantidade realizada | 60000.0 |
| `product_uom` | many2one | UM | Units |
| `purchase_line_id` | many2one | Linha do PO origem | [98679, '...'] |
| `state` | selection | Estado | "done" |

### 3.4 De-Para de Fornecedores (NÃO UTILIZADO)
**Modelo**: `product.supplierinfo`

| Campo | Tipo | Descrição | Situação Atual |
|-------|------|-----------|----------------|
| `partner_id` | many2one | Fornecedor | ✅ Preenchido |
| `product_id` | many2one | Produto | ~22% preenchido |
| `product_code` | char | Código do fornecedor | ~22% preenchido |
| `product_uom` | many2one | **UM de compra** | ❌ 99% = Units |
| `fator_un` | float | **Fator de conversão** | ❌ 100% = 1 |
| `price` | float | Preço | Parcialmente |

---

## 4. Unidades de Medida - Fornecedores

### UoMs que indicam MILHAR
- `ML` - Milhar (Gráfica MKT Prime)
- `MI` - Milhar (Odoo nativo, ID=181)
- `MIL` - Milhar (outros fornecedores)

### Fator de Conversão
```
1 ML/MI/MIL = 1.000 unidades
```

### Fornecedores Conhecidos que Usam MILHAR
- **Gráfica MKT Prime** (ID: 97513) - Rótulos
- **PREMIUMPLASTIC** (ID: 97853) - Frascos/Tampas
- **INOVA EMBALAGENS** (ID: 97548) - Sacos/Embalagens
- **METALGRAFICA ROJEK** (ID: 97729) - Tampas metálicas
- **MARCATTO FORTINOX** (ID: 97690) - Tampas
- **THERMOPLAST** (ID: 98013) - Tampas plásticas

---

## 5. Exemplo Real Completo

### Caso: NF 2649 da Gráfica MKT Prime

**DFE (NF-e)**:
- ID: 35014
- Fornecedor: GRAFICA MKT PRIME
- Linha: ROTULO FRONTAL KETCHUP
- Qtd NF: 60 ML (Milhar)
- Valor Unit: R$ 41,00 (por Milhar)
- Valor Total: R$ 2.460,00

**PO (Pedido de Compra)**:
- ID: 30400
- Referência: C2511895
- Linha: ROTULO FRONTAL KETCHUP
- Qtd Pedida: 60.000 Units ✅ (digitado convertido)
- Preço Unit: R$ 0,041 (por unidade)

**Picking (Recebimento)**:
- ID: 293483
- Qtd Demanda: 60.000 Units ✅
- Qtd Realizada: 60.000 Units ✅
- Estado: done

**Resultado no Estoque**: +60.000 unidades de rótulo ✅

---

## 6. Mecanismos Nativos Disponíveis (Não Utilizados)

### 6.1 product.supplierinfo.product_uom
- **O que faz**: Define UM de compra por fornecedor/produto
- **Como usar**: Cadastrar `product_uom = MI` para fornecedores que vendem em Milhar
- **Benefício**: Odoo sugere conversão ao criar linha no PO
- **Status**: NÃO CONFIGURADO

### 6.2 product.product.uom_po_id
- **O que faz**: Define UM de compra padrão do produto
- **Como usar**: Alterar `uom_po_id` de Units para MI
- **Benefício**: Conversão automática em todos os POs
- **Status**: NÃO CONFIGURADO

### 6.3 UoM MI (ID=181) - CONFIGURAÇÃO INCORRETA
- **Problema**: `uom_type = "smaller"` com `factor = 1000`
- **Resultado**: 1000 MI = 1 Unit (INVERTIDO)
- **Correto**: `uom_type = "bigger"` com `factor = 0.001`
- **Resultado esperado**: 1 MI = 1000 Units

---

## 7. Conclusão

### Processo Atual (Funciona)
1. Compras **calcula manualmente** a conversão (ML × 1000)
2. Compras **digita no PO** a quantidade em unidades
3. NF é recebida e vinculada ao PO
4. Picking usa quantidade do PO (correta)
5. Estoque recebe quantidade correta

### Por que Não Automatizar Agora
- Processo atual funciona e é conhecido pela equipe
- Cadastro do De-Para exigiria esforço significativo
- UoM MI precisaria ser corrigida primeiro
- Risco de inconsistências durante transição

### Referência para Futuro
Se decidir automatizar:
1. Corrigir UoM MI no Odoo
2. Cadastrar `product.supplierinfo` com `product_uom` correto
3. Testar em ambiente de homologação
4. Treinar equipe no novo processo
