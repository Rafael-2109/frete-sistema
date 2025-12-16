# ROADMAP: Suporte a Múltiplos Títulos por Linha de Extrato

**Data**: 2025-12-15
**Status**: ✅ Concluído

## Visão Geral

Permitir vincular N títulos a 1 linha de extrato bancário, suportando:
- Pagamento agrupado (cliente paga múltiplas NFs de uma vez)
- Alocação parcial (pagar parte de um título)
- Rastreabilidade completa

## Estrutura de Dados

```
┌─────────────────────────────────────────────────────────────────┐
│  ExtratoItem (linha do extrato)                                 │
│  ├── titulo_receber_id (FK legacy - 1:1)                       │
│  ├── titulo_pagar_id (FK legacy - 1:1)                         │
│  │                                                              │
│  └── titulos_vinculados (M:N via ExtratoItemTitulo)            │
│       ├── ExtratoItemTitulo #1 → Título A (valor_alocado)      │
│       ├── ExtratoItemTitulo #2 → Título B (valor_alocado)      │
│       └── ExtratoItemTitulo #3 → Título C (valor_alocado)      │
└─────────────────────────────────────────────────────────────────┘
```

## Estratégia de Compatibilidade

**Modo 1:1 (atual)**: Continua usando `titulo_receber_id` / `titulo_pagar_id`
**Modo M:N (novo)**: Usa `titulos_vinculados` (ExtratoItemTitulo)

Regra de decisão:
- Se `titulos_vinculados.count() > 0` → Usar modo M:N
- Senão → Usar modo 1:1 (legacy)

---

## ETAPAS DE IMPLEMENTAÇÃO

### FASE 1: Infraestrutura ✅
- [x] Criar modelo `ExtratoItemTitulo`
- [x] Adicionar relacionamento no `ExtratoItem`
- [x] Criar scripts de migração SQL/Python
- [x] Adicionar properties helper (`valor_alocado_total`, `tem_multiplos_titulos`)

### FASE 2: Matching Service ✅
Arquivo: `app/financeiro/services/extrato_matching_service.py`

#### 2.1 Detectar Agrupamentos
- [x] Método `buscar_titulos_agrupados()` implementado
  - Busca todos os títulos do mesmo CNPJ
  - Algoritmo subset-sum para encontrar combinações
  - Retorna lista de títulos candidatos com score

#### 2.2 Novo Critério de Match
- [x] Critério `CNPJ+SOMA_TITULOS` implementado
  - Score 95: múltiplos títulos fecham exato (diferença = 0)
  - Score 90: múltiplos títulos com diferença < 1%
  - Score 85: múltiplos títulos com diferença < 5%

#### 2.3 Método `vincular_multiplos_titulos()`
- [x] Implementado com validações
- [x] Método `desvincular_titulos()` também criado

### FASE 3: API de Vinculação ✅
Arquivo: `app/financeiro/routes/extrato.py`

#### 3.1 Novas Rotas
- [x] `POST /financeiro/extrato/api/vincular-multiplos` - Vincula múltiplos títulos
- [x] `POST /financeiro/extrato/api/desvincular-multiplos` - Remove vínculos M:N
- [x] `GET /financeiro/extrato/api/titulos-agrupados/<item_id>` - Sugestões de agrupamento
- [x] `GET /financeiro/extrato/api/titulos-vinculados/<item_id>` - Lista vínculos existentes

#### 3.2 Rota de Candidatos
- [x] `buscar_titulos_candidatos()` atualizado para incluir sugestões de agrupamento

### FASE 4: Conciliação ✅
Arquivo: `app/financeiro/services/extrato_conciliacao_service.py`

#### 4.1 Atualizar `conciliar_item()`
- [x] Verificar se item tem `titulos_vinculados`
- [x] Se sim, chamar `_conciliar_multiplos_titulos()`
- [x] Se não, manter fluxo atual (1:1)

#### 4.2 Método `_conciliar_multiplos_titulos()`
- [x] Implementado com processamento individual de cada vínculo
- [x] Status CONCILIADO, PARCIAL ou ERRO baseado no resultado

#### 4.3 Método `_conciliar_titulo_individual()`
- [x] Cria payment com valor_alocado do vínculo
- [x] Reconcilia payment ↔ título
- [x] Atualiza status do ExtratoItemTitulo

### FASE 5: Templates/UI ✅
Arquivos: `app/templates/financeiro/extrato_lote_detalhe.html`, `app/templates/financeiro/extrato_lote_pagamentos_detalhe.html`

#### 5.1 Exibir Múltiplos Títulos
- [x] Detectar `item.tem_multiplos_titulos`
- [x] Mostrar lista de títulos vinculados com valor_alocado
- [x] Exibir total alocado vs valor do extrato
- [x] Totalizador com saldo (diferença extrato - títulos)

#### 5.2 Modal de Agrupamento
- [x] Modal com seleção múltipla via checkboxes
- [x] Botão "Adicionar" individual por título
- [x] Footer com resumo: quantidade, total e diferença em tempo real
- [x] Botão "Limpar Seleção"

#### 5.3 Seção de Comparação
- [x] Exibe badge com quantidade de títulos
- [x] Mostra valor extrato, soma títulos e diferença
- [x] Status de fechamento (Valores fecham / Sobra / Falta)

#### 5.4 Ações
- [x] Botão "Adicionar" para vincular mais títulos
- [x] Botão "Desvincular" para remover todos os vínculos M:N
- [x] Compatibilidade com fluxo 1:1 legacy mantida

---

## PRIORIDADES

| Fase | Prioridade | Complexidade | Dependências | Status |
|------|------------|--------------|--------------|--------|
| 1    | ✅ Feito   | Baixa        | -            | ✅     |
| 2    | ✅ Feito   | Média        | Fase 1       | ✅     |
| 3    | ✅ Feito   | Baixa        | Fase 2       | ✅     |
| 4    | ✅ Feito   | Alta         | Fase 2, 3    | ✅     |
| 5    | ✅ Feito   | Média        | Fase 2, 3, 4 | ✅     |

---

## TESTES NECESSÁRIOS

### Cenário 1: Pagamento Exato (soma = extrato)
```
Extrato: R$ 15.000,00
Títulos: [R$ 5.000, R$ 7.000, R$ 3.000]
Resultado esperado: Todos conciliados, extrato fechado
```

### Cenário 2: Pagamento Maior (soma < extrato)
```
Extrato: R$ 16.000,00
Títulos: [R$ 5.000, R$ 7.000, R$ 3.000]
Resultado esperado: Títulos conciliados, R$ 1.000 sobra no extrato
```

### Cenário 3: Pagamento Menor (soma > extrato)
```
Extrato: R$ 14.000,00
Títulos: [R$ 5.000, R$ 7.000, R$ 3.000]
Resultado esperado: Erro ou alocação parcial no último título
```

### Cenário 4: Compatibilidade (1:1 legacy)
```
Extrato: R$ 5.000,00
Título único: R$ 5.000
Resultado esperado: Fluxo atual funciona normalmente
```

---

## ARQUIVOS ENVOLVIDOS

| Arquivo | Alterações | Status |
|---------|------------|--------|
| `app/financeiro/models.py` | ExtratoItemTitulo criado | ✅ |
| `app/financeiro/services/extrato_matching_service.py` | Detectar agrupamentos, vincular múltiplos | ✅ |
| `app/financeiro/services/extrato_conciliacao_service.py` | Conciliar múltiplos títulos | ✅ |
| `app/financeiro/routes/extrato.py` | APIs de vinculação M:N | ✅ |
| `scripts/sql/criar_tabela_extrato_item_titulo.sql` | Script SQL de migração | ✅ |
| `scripts/migrations/criar_tabela_extrato_item_titulo.py` | Script Python de migração | ✅ |
| `app/templates/financeiro/extrato_lote_detalhe.html` | UI múltiplos (receber) | ✅ |
| `app/templates/financeiro/extrato_lote_pagamentos_detalhe.html` | UI múltiplos (pagar) | ✅ |

---

## NOTAS DE IMPLEMENTAÇÃO

### Regra de Valor Alocado
- Soma dos `valor_alocado` DEVE ser ≤ valor do extrato
- Se soma < valor do extrato, extrato fica com saldo residual
- Se soma > valor do extrato, ERRO (não permitir)

### Odoo Partial Reconcile
O Odoo suporta reconciliação parcial nativamente:
- `account.partial.reconcile` registra cada parte
- `amount` indica quanto foi reconciliado
- Linha só fica `reconciled=True` quando `amount_residual=0`

### Migration dos Dados Existentes
- Dados existentes continuam usando FK legacy
- Novos agrupamentos usam M:N
- Não é necessário migrar dados antigos
