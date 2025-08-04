# Entity Mapping Patterns Documentation

## Overview

This document describes the entity mapping patterns discovered through analysis of the freight system's data models. The patterns enable dynamic entity recognition and mapping without hardcoding specific values.

## Core Models Analyzed

1. **EntregaMonitorada** (Monitored Deliveries)
2. **CarteiraPrincipal** (Main Portfolio)
3. **Pedido** (Orders)
4. **Embarque** (Shipments)
5. **Frete** (Freight)

## Key Patterns Discovered

### 1. CNPJ Grouping Pattern

**Pattern**: First 8 digits of CNPJ represent the company group
- Format: `XX.XXX.XXX/0001-YY` where `XX.XXX.XXX` is the company root
- Multiple branches share the same root: `/0001-`, `/0002-`, etc.
- Used for grouping related entities across the system

**Implementation**:
```python
cnpj_root = extract_cnpj_root(cnpj)  # Returns first 8 digits
groups = group_by_cnpj_root(entities)  # Groups by company
```

### 2. Client Name Variations

**Patterns Identified**:
- Abbreviation variations: `LTDA` vs `Limitada`, `S.A.` vs `Sociedade Anônima`
- Case inconsistencies: Mixed case usage across modules
- Special characters: Accents and punctuation variations
- Word order variations: Company type placement

**Normalization Strategy**:
1. Convert to uppercase
2. Remove accents
3. Expand common abbreviations
4. Standardize spacing

### 3. Location Normalization

**City/State Patterns**:
- State codes: 2-letter UF codes (SP, RJ, MG, etc.)
- City name variations: Accents, prepositions (de, do, da)
- IBGE codes: Unique identifier per city
- Normalization fields: `cidade_normalizada`, `uf_normalizada`

**Fields Identified**:
- `municipio`, `cidade`, `nome_cidade`, `cidade_destino`
- `uf`, `estado`, `cod_uf`, `uf_destino`
- `codigo_ibge` (unique city identifier)

### 4. Status Field Harmonization

**Status Categories Found**:
- **Open States**: `ABERTO`, `PENDENTE`, `AGUARDANDO`, `CRIADO`
- **Processing States**: `COTADO`, `EMBARCADO`, `EM_ANDAMENTO`
- **Completed States**: `ENTREGUE`, `FINALIZADO`, `FATURADO`
- **Cancelled States**: `CANCELADO`, `ANULADO`
- **Special States**: `NF no CD`, `STANDBY`, `RECOMPOSTO`

**Context-Specific Status**:
- Order context: `ABERTO` → `COTADO` → `FATURADO`
- Delivery context: `AGUARDANDO` → `EMBARCADO` → `ENTREGUE`
- Freight context: `PENDENTE` → `APROVADO` → `PAGO`

### 5. Temporal Relationships

**Date Field Categories**:
1. **Creation Dates**: `criado_em`, `data_pedido`, `data_criacao`
2. **Update Dates**: `updated_at`, `alterado_em`, `data_atual_pedido`
3. **Schedule Dates**: `agendamento`, `data_agendada`, `data_prevista`
4. **Execution Dates**: `data_entrega`, `data_embarque`, `data_faturamento`
5. **Deadline Dates**: `vencimento`, `data_limite`, `data_entrega_pedido`

**Temporal Patterns**:
- Order to delivery: Average 5-7 days
- Quote to shipment: Average 2-3 days
- Invoice to payment: 30-day cycles common

### 6. Value Field Patterns

**Naming Conventions**:
- Prefixes: `valor_`, `preco_`, `qtd_`, `quantidade_`, `total_`
- Suffixes: `_total`, `_saldo`, `_pedido`, `_produto`

**Common Fields**:
- Monetary: `valor_nf`, `valor_frete`, `valor_total`, `preco_produto_pedido`
- Quantities: `qtd_produto_pedido`, `qtd_saldo`, `quantidade_nfs`
- Calculations: `valor_saldo_total`, `peso_total`, `pallet_total`

### 7. Identifier Patterns

**Primary Identifiers**:
- `numero_nf`, `num_pedido`: Business keys
- `separacao_lote_id`: Batch/lot identifier
- `embarque_id`, `cotacao_id`: Foreign keys

**Identifier Formats**:
- NF: Numeric, usually 6-10 digits
- Pedido: Alphanumeric, varies by source
- Lote: String with timestamp pattern

### 8. Relationship Patterns

**Common Relationships**:
```
Pedido (1) ←→ (N) Embarque Items
Embarque (1) ←→ (N) Fretes
CNPJ Root (1) ←→ (N) Branches
Transportadora (1) ←→ (N) Fretes
```

**Key Foreign Keys**:
- `transportadora_id`: Links to transport companies
- `cotacao_id`: Links quotes to shipments
- `embarque_id`: Links shipments to freight
- `separacao_lote_id`: Links batch operations

## Business Rules Discovered

### 1. CNPJ-Based Rules
- Companies with same CNPJ root often use same:
  - Payment terms (`forma_pgto_pedido`)
  - Transport companies
  - Sales teams (`equipe_vendas`)

### 2. Status Transition Rules
- Orders must be `COTADO` before `FATURADO`
- Deliveries require `agendamento` before `ENTREGUE`
- Freight requires `APROVADO` for payment > R$ 5.00 difference

### 3. Temporal Constraints
- `data_entrega` ≥ `data_pedido`
- `data_embarque` ≥ `data_cotacao`
- `vencimento` typically = `data_emissao` + 30 days

### 4. Value Constraints
- Minimum freight values exist (varies by table)
- `valor_considerado` vs `valor_pago` tolerance: R$ 5.00
- Quantity splits preserve totals in pre-separation

## Query Optimization Patterns

### High-Frequency Query Fields
1. `cnpj_cpf` - Company identification
2. `status` fields - Workflow filtering
3. Date fields - Temporal queries
4. `num_pedido` - Direct lookups
5. Location fields - Geographic filtering

### Suggested Indices
- Composite: `(cnpj_cpf, status, data_pedido)`
- Composite: `(separacao_lote_id, status)`
- Individual: High-cardinality identifiers

## Implementation Guidelines

### 1. Dynamic Mapping
```python
# Don't hardcode values
# Bad: if cnpj == "11.222.333/0001-44"
# Good: if extract_cnpj_root(cnpj) == extract_cnpj_root(reference_cnpj)
```

### 2. Fuzzy Matching
```python
# Use similarity scores for client matching
similarity = calculate_name_similarity(name1, name2)
if similarity > 0.8:  # 80% threshold
    # Consider as same client
```

### 3. Status Normalization
```python
# Normalize status across contexts
normalized = harmonize_status(raw_status, context='order')
# Returns standardized status: 'open', 'processing', etc.
```

### 4. Temporal Queries
```python
# Use categorized date fields
temporal_fields = extract_temporal_fields(entity)
# Returns: {'creation': [...], 'execution': [...], etc.}
```

## Performance Considerations

1. **Pre-compile Regex**: Patterns are compiled once for performance
2. **Limit Unique Value Tracking**: Cap at 1000 to prevent memory issues
3. **Use Normalized Fields**: Query `cidade_normalizada` instead of raw
4. **Batch Operations**: Group entities by CNPJ root for bulk processing

## Future Enhancements

1. **Machine Learning Integration**: Train models on discovered patterns
2. **Automatic Index Suggestions**: Based on query frequency analysis
3. **Data Quality Scoring**: Automated quality metrics per entity
4. **Pattern Evolution Tracking**: Monitor how patterns change over time
5. **Cross-Module Validation**: Ensure consistency across modules