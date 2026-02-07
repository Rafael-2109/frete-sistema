# Regras de Negocio: CarteiraPrincipal e Separacao

**Ultima Atualizacao**: 07/02/2026
**Fonte de verdade para campos**: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`

---

## CarteiraPrincipal (app/carteira/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/carteira_principal.json`

**Tabela**: `carteira_principal`
**Uso**: Pedidos originais com saldo pendente (fonte de verdade para demanda)
**Filtro de pendencia**: `qtd_saldo_produto_pedido > 0`

### CAMPOS QUE NAO EXISTEM EM CarteiraPrincipal - NUNCA USAR
```
# NAO EXISTEM neste modelo (estao na Separacao):
# separacao_lote_id  -> Separacao.separacao_lote_id
# expedicao          -> Separacao.expedicao
# agendamento        -> Separacao.agendamento
# protocolo          -> Separacao.protocolo
# status             -> Separacao.status
# data_entrega       -> usar data_entrega_pedido
# hora_agendamento   -> nao existe em nenhum modelo
# data_expedicao_pedido -> nao existe
# data_agendamento_pedido -> nao existe
# agendamento_confirmado -> Separacao.agendamento_confirmado
# codigo_ibge        -> NAO existe (usar nome_cidade + cod_uf)
# sincronizado_nf    -> SOMENTE em Separacao
```

---

## Separacao (app/separacao/models.py)

> Campos completos: ver schema em `.claude/skills/consultando-sql/schemas/tables/separacao.json`

**Tabela**: `separacao`
**Uso**: Unica fonte da verdade para projetar saidas de estoque via `sincronizado_nf=False`

### REGRA CRITICA: sincronizado_nf
- **sincronizado_nf=False**: Item SEMPRE aparece na carteira e SEMPRE e projetado no estoque
- **sincronizado_nf=True**: Foi faturado (tem NF), NAO aparece na carteira, NAO projeta estoque

### Prioridades de Status (calculado automaticamente pelo listener)
1. **PREVISAO**: Nunca sobrescrito pelo listener (status manual, pre-separacao)
2. **NF no CD**: `nf_cd=True` (NF voltou para o CD)
3. **FATURADO**: `sincronizado_nf=True` ou `numero_nf` preenchido
4. **COTADO**: `cotacao_id` preenchido
5. **ABERTO**: Estado padrao

> `EMBARCADO` NAO e usado na logica automatica de status

---

### Event Listeners da Separacao (app/separacao/models.py)

#### 1. setar_falta_pagamento_inicial (BEFORE_INSERT, linhas 198-230)
- **Trigger**: Apenas no INSERT (criacao)
- **Regra**: Se CarteiraPrincipal.cond_pgto_pedido contiver 'ANTECIPADO', seta falta_pagamento=True
- **NAO roda em UPDATEs** (preserva escolha manual do usuario)

#### 2. atualizar_status_automatico (BEFORE_INSERT + BEFORE_UPDATE, linhas 233-281)
- **Trigger**: Toda insercao e atualizacao
- **Regras**: Ver "Prioridades de Status" acima

#### 3. log_reversao_status (AFTER_UPDATE, linhas 283-312)
- **Trigger**: Apos atualizacao
- **Proposito**: Registra reversoes de status para auditoria
- **Reversoes monitoradas**: EMBARCADO->COTADO, COTADO->ABERTO, FATURADO->ABERTO, etc.

#### 4. recalcular_totais_embarque (AFTER_UPDATE + AFTER_DELETE, linhas 315-427)
- **Trigger**: Apos atualizar ou deletar Separacao
- **Proposito**: Recalcula EmbarqueItem.peso/.valor/.pallets e Embarque.peso_total/.valor_total/.pallet_total
- **Condicao**: Somente se separacao_lote_id esta vinculada a EmbarqueItem ativo

---

### Metodos Auxiliares da Separacao

```python
# Classe:
Separacao.atualizar_status(separacao_lote_id, num_pedido=None, novo_status='ABERTO')
Separacao.atualizar_nf_cd(separacao_lote_id, num_pedido=None, nf_cd=False)
Separacao.atualizar_cotacao(separacao_lote_id, cotacao_id, nf_cd=False)
Separacao.save()  # db.session.add + commit

# Funcoes do modulo:
remover_do_embarque(separacao_lote_id, num_pedido=None)     # Zera data_embarque
remover_cotacao(separacao_lote_id, num_pedido=None)         # Zera cotacao_id
cancelar_faturamento(separacao_lote_id, num_pedido=None)    # Limpa sincronizado_nf, numero_nf, data_sincronizacao
```

---

## Diferenca entre Campos de Carteira vs Separacao

| Campo | CarteiraPrincipal | Separacao |
|-------|-------------------|-----------|
| Quantidade | `qtd_saldo_produto_pedido` | `qtd_saldo` |
| Valor | `preco_produto_pedido` | `valor_saldo` |
| Data entrega cliente | `data_entrega_pedido` | NAO TEM |
| Data expedicao | NAO TEM | `expedicao` |
| Agendamento | NAO TEM | `agendamento` |
| Agend. confirmado | NAO TEM | `agendamento_confirmado` |
| Protocolo | NAO TEM | `protocolo` |
| Status | `status_pedido` (Odoo) | `status` (operacional) |
| Data embarque | NAO TEM | `data_embarque` |
| Falta item | NAO TEM | `falta_item` |
| Falta pagamento | NAO TEM | `falta_pagamento` |
| Cotacao | NAO TEM | `cotacao_id` |

### Campos Calculados ao Criar Separacao

| Campo | Calculo | Fonte |
|-------|---------|-------|
| peso | qtd_saldo x peso_bruto | CadastroPalletizacao |
| pallet | qtd_saldo / palletizacao | CadastroPalletizacao |
| rota | buscar_rota_por_uf(cod_uf) | app.carteira.utils.separacao_utils |
| sub_rota | buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade) | app.carteira.utils.separacao_utils |

---

## Pallets: Calculo Teorico vs Controle Fisico

### GRUPO 1: PALLETS TEORICOS (via CadastroPalletizacao)

Estimativa baseada em pallets padrao (1 produto por pallet).

| Modelo | Campo | Calculo |
|--------|-------|---------|
| `Separacao` | `pallet` | `qtd_saldo / CadastroPalletizacao.palletizacao` |
| `EmbarqueItem` | `pallets` | Soma de `Separacao.pallet` do lote |
| `Embarque` | `pallet_total` | Soma de `EmbarqueItem.pallets` |

Listener: `app/separacao/models.py:315-427` (`recalcular_totais_embarque`) sincroniza automaticamente.

### GRUPO 2: PALLETS FISICOS (Controle Real - Gestao de Ativos PBR)

Rastrear pallets fisicos reais para faturamento de NF remessa.

| Modelo | Campo | Descricao |
|--------|-------|-----------|
| `Embarque` | `nf_pallet_transportadora` | NF remessa de pallet para transportadora |
| `Embarque` | `qtd_pallet_transportadora` | Quantidade na NF remessa |
| `Embarque` | `qtd_pallets_separados` | Pallets fisicos expedidos |
| `Embarque` | `qtd_pallets_trazidos` | Pallets que a transportadora trouxe de volta |
| `EmbarqueItem` | `nf_pallet_cliente` | NF remessa de pallet para o cliente |
| `EmbarqueItem` | `qtd_pallet_cliente` | Quantidade na NF para o cliente |

**REGRA**: GRUPO 1 (Teorico) != GRUPO 2 (Fisico). Sao INDEPENDENTES.

```python
# Embarque.saldo_pallets_pendentes
# = qtd_pallets_separados - qtd_pallets_trazidos - faturados
```
