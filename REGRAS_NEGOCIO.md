# 📚 REGRAS DE NEGÓCIO CRÍTICAS - SISTEMA DE FRETE

## 🎯 PRINCÍPIOS FUNDAMENTAIS

### 1. Separacao como Fonte da Verdade
- **Separacao** é a ÚNICA fonte de verdade para projeção de estoque
- **sincronizado_nf=False**: Item SEMPRE aparece na carteira e SEMPRE é considerado na projeção de estoque
- **sincronizado_nf=True**: Foi faturado (tem NF), NÃO aparece mais na carteira

### 2. Relacionamento entre Modelos
- **Separacao → num_pedido**: 1x1 (uma separação tem um pedido)
- **Separacao → separacao_lote_id**: 1x1 (uma separação tem um lote)
- **num_pedido → Separacao**: 1xN (um pedido pode ter múltiplas separações)
- **Pedido (VIEW)**: Agrega Separacao por separacao_lote_id onde status != 'PREVISAO'

## 🔄 FLUXO DE STATUS

### Status Possíveis e Transições
```
PREVISAO → ABERTO → COTADO → FATURADO → NF no CD
         ↘_(raro)_↗         ↗
```

### Regras de Status:
1. **PREVISAO → ABERTO**: 100% obrigatório (não pula)
2. **ABERTO → COTADO**: 99,9% dos casos
3. **ABERTO → FATURADO**: 0,1% (exceção operacional)
4. **COTADO → EMBARCADO**: 0% (status não usado na prática)
5. **COTADO → FATURADO**: 99,9% dos casos
6. **FATURADO → NF no CD**: Apenas quando há problema (não é sempre)

### Regra Crítica de sincronizado_nf:
- **IMPOSSÍVEL**: status='PREVISAO' com sincronizado_nf=True
- **Motivo**: Para sincronizar NF, precisa estar em embarque ativo → status mínimo é COTADO

## 📊 QUERIES PADRÃO CORRETAS

### 1. Buscar itens para Carteira de Pedidos
```python
# ✅ CORRETO - Usar sincronizado_nf=False
items = Separacao.query.filter_by(
    sincronizado_nf=False  # SEMPRE este critério para carteira
).all()

# ❌ ERRADO - Não usar status para carteira
items = Separacao.query.filter(
    Separacao.status.in_(['ABERTO', 'COTADO'])  # NÃO USE ISSO
).all()
```

### 2. Buscar separações de um pedido
```python
# ✅ CORRETO - Todas as separações do pedido
separacoes = Separacao.query.filter_by(
    num_pedido=num_pedido,
    sincronizado_nf=False  # Para aparecer na carteira
).all()
```

### 3. Identificar separações parciais (irmãs)
```python
# ✅ CORRETO - Buscar todas as "irmãs" de uma separação parcial
irmas = Separacao.query.filter_by(
    num_pedido=separacao.num_pedido,
    tipo_envio='parcial'
).all()
```

## 🚫 CAMPOS DEPRECATED/NÃO USADOS

### CarteiraPrincipal - Campos para REMOVER:
```python
# NUNCA USADOS - podem ser removidos:
qtd_saldo  # Calculado de carga/lote - não usado
valor_saldo  # Calculado de carga/lote - não usado
peso  # Calculado de carga/lote - não usado
pallet  # Calculado de carga/lote - não usado

# TOTALIZADORES - não usados:
valor_saldo_total
pallet_total
peso_total
valor_cliente_pedido
pallet_cliente_pedido
peso_cliente_pedido
qtd_total_produto_carteira
estoque

# PROJEÇÃO D0-D28 - não usados:
estoque_d0 até estoque_d28

# OUTROS:
hora_agendamento  # Não usado
```

## ⚠️ ARMADILHAS COMUNS

### 1. Confusão de Campos de Quantidade
- **qtd_saldo_produto_pedido** (CarteiraPrincipal): Saldo disponível na carteira
- **qtd_saldo** (Separacao): Quantidade efetivamente separada
- **NÃO** são a mesma coisa!

### 2. Filtros de Carteira
- **SEMPRE** use `sincronizado_nf=False` para itens na carteira
- **NUNCA** use status para filtrar carteira
- **EXCEÇÃO**: PreSeparacaoItem (deprecated) usava status, mas agora é Separacao

### 3. VIEW Pedido
- **IGNORA** Separacao com status='PREVISAO'
- **AGREGA** por separacao_lote_id
- **NÃO** fazer JOIN desnecessário quando os dados já estão em Separacao

### 4. Tipo de Envio
- **total**: Gerado por "Gerar Separação Completa"
- **parcial**: Criado no workspace de montagem (drag & drop)
- Múltiplas separações parciais = mesmo num_pedido

## 📝 MIGRAÇÃO PreSeparacaoItem → Separacao

### Regra Absoluta:
**SEMPRE** substituir PreSeparacaoItem por Separacao com status='PREVISAO'

### Mapeamento de Queries:
```python
# ❌ ANTES (PreSeparacaoItem):
PreSeparacaoItem.query.filter_by(
    status='CRIADO'
)

# ✅ DEPOIS (Separacao):
Separacao.query.filter_by(
    status='PREVISAO'
)
```

### Mapeamento de Filtros para Carteira:
```python
# ❌ ANTES (buscava por status):
Separacao.query.filter(
    Separacao.status.in_(['ABERTO', 'COTADO'])
)

# ✅ DEPOIS (busca por sincronizado_nf):
Separacao.query.filter_by(
    sincronizado_nf=False
)
```

## 🏗️ CAMPOS DE NORMALIZAÇÃO

### Processo Automático:
1. **Executado por**: app.cli
2. **Usado em**: app.cotacao, app.utils.frete_simulador, app.utils.localizacao
3. **Objetivo**: Padronizar nomes e extrair codigo_ibge

### Campos Envolvidos:
- **cidade_normalizada**: Nome padronizado da cidade
- **uf_normalizada**: UF padronizada
- **codigo_ibge**: Extraído de app.localidades via Cidade.nome e Cidade.uf

## 🔑 RESUMO EXECUTIVO

### Para Carteira de Pedidos:
- **Filtro**: sincronizado_nf=False (SEMPRE)
- **Não usar**: status como filtro

### Para Status:
- **Fluxo normal**: PREVISAO → ABERTO → COTADO → FATURADO
- **Status não usado**: EMBARCADO (sempre pula)

### Para Migração:
- **Substituir**: PreSeparacaoItem → Separacao com status='PREVISAO'
- **Filtro carteira**: Mudou de status para sincronizado_nf

### Para Performance:
- **Evitar**: JOINs com Pedido VIEW quando desnecessário
- **Usar**: Queries agrupadas e dicionários para lookup O(1)