# Manual — `StockQuantAdjustmentService` (gold-script: Ajuste de inventário)

> **NOTA (Onda 2 PAD-A):** "gold-script" é vocabulário APOSENTADO — hoje é o service/primitiva (C1) `app/odoo/estoque/scripts/quant.py`, skill `ajustando-quant-odoo`; constituição em `app/odoo/estoque/CLAUDE.md`. Este doc é mineração transitória válida.

**Assunto:** A1 — ajuste de inventário de **1 quant** (a operação atômica de estoque)
**Arquivo:** `app/odoo/services/stock_quant_adjustment_service.py`
**Testes:** `tests/odoo/services/test_stock_quant_adjustment_service.py` (22)
**Status:** ✅ pronto

> Este manual é o **template** dos demais manuais de gold-script. Estrutura:
> O que faz · Quando usar · Assinatura · Receitas · Exemplos · Armadilhas · Ponte p/ orquestrador.

---

## O que faz

Aplica **um** ajuste de saldo num único `stock.quant` via *inventory adjustment*
(`inventory_quantity` + `action_apply_inventory`) — o padrão oficial Odoo 16+, que gera
1 `stock.move` auditável ("Physical Inventory"). É o **átomo** de ajuste de estoque:
operações maiores (transferência = 2 ajustes; net-zero = N ajustes) se compõem dele.

**Não faz** (responsabilidade do orquestrador): ler planilha, resolver `default_code`→produto,
decidir o lote, criar o lote. A primitiva recebe IDs já resolvidos.

## Quando usar

- Você tem um `(produto, empresa, local, lote)` ou um `quant_id` e quer **somar/definir/zerar** saldo.
- Quer a escrita no Odoo feita de forma segura (validações, dry-run, criação opcional de quant).

Quando **NÃO** usar: para mover saldo entre 2 lotes use `StockInternalTransferService`
(faz os 2 ajustes atomicamente). Para resolver/criar lote use `StockLotService`.

## Assinatura

```python
StockQuantAdjustmentService(odoo=None, lot_svc=None).ajustar_quant(*,
    # identificação do quant — UMA das duas formas:
    quant_id=None,                       # direto (ex.: quant fantasma conhecido)
    product_id=None, company_id=None, location_id=None, lot_id=None,  # por chave; lot_id=None => SEM lote
    # quantidade alvo — UMA das duas formas (XOR):
    delta=None,                          # soma ao saldo atual (+/-)
    valor_absoluto=None,                 # define o saldo (set); 0 = zerar
    # comportamento:
    criar_se_faltar=False,               # cria o quant se não existe (exige chave, não quant_id; qty_apos>=0)
    validar_nao_negativar=True,          # bloqueia qty_apos < 0
    validar_nao_abaixo_reserva=True,     # bloqueia qty_apos < reserva (ignorado se resetar_reserva)
    resetar_reserva=False,               # zera reserved_quantity antes (corrige reserva órfã/negativa)
    casas_decimais=6,
    dry_run=False,                       # não escreve; retorna o plano calculado
) -> dict  # {status, qty_antes, qty_apos, ajuste_aplicado, reservada, acao, quant_id, tempo_ms, erro}
```

**Status retornados:** `EXECUTADO`, `DRY_RUN_OK`, `NOOP` (nada muda), `FALHA_QUANT_VAZIO`,
`FALHA_QUANT_NEGATIVO`, `FALHA_RESERVADO`, `FALHA_ODOO`. Erros de **uso** (args incompatíveis)
levantam `ValueError` (é bug do orquestrador, não condição de dado).

## Receitas (caso real → args)

| Preciso de... | Args | Vinha de |
|---------------|------|----------|
| Ajuste **positivo** por planilha (cria lote/quant se faltar) | `delta=+X, criar_se_faltar=True` | 12, 13, 14_v2, criar_saldo |
| Ajuste **negativo** residual (não cria; valida) | `delta=-X` (validações default on) | 11 |
| **Zerar** um quant fantasma conhecido | `quant_id=Q, valor_absoluto=0` | limpar_quants_ghost |
| **Definir** saldo exato (contagem física absoluta) | `valor_absoluto=X` | — |
| **Reduzir** um lote-fonte (passo de "zerar negativos") | `delta=-take` | zerar_negativos (fontes) |
| **Corrigir** `reserved_quantity` negativo + zerar | `quant_id=Q, valor_absoluto=0, resetar_reserva=True` | corrigir_reserved |
| Realocação **net-zero** entre lotes A→B | 2 chamadas: `delta=-X` (lote A) + `delta=+X` (lote B) — **ou** `StockInternalTransferService` | pasta17 |

## Exemplos

```python
from app.odoo.services.stock_quant_adjustment_service import StockQuantAdjustmentService
svc = StockQuantAdjustmentService(odoo=odoo)   # reusa conexão; lot_svc opcional

# 1) Somar 50 un num lote (cria quant se faltar) — dry-run primeiro
r = svc.ajustar_quant(product_id=28239, company_id=5, location_id=42, lot_id=44098,
                      delta=50.0, criar_se_faltar=True, dry_run=True)
# r['status'] == 'DRY_RUN_OK', r['qty_apos'] == r['qty_antes'] + 50

# 2) Zerar um quant fantasma por id
svc.ajustar_quant(quant_id=12073, valor_absoluto=0)

# 3) Corrigir reserva negativa e zerar saldo
svc.ajustar_quant(quant_id=98765, valor_absoluto=0, resetar_reserva=True)
```

## Armadilhas

- **`delta` XOR `valor_absoluto`** — exatamente um. Os dois (ou nenhum) → `ValueError`.
- **`lot_id=None` significa SEM lote** (`lot_id=False` no Odoo), **não** "lote a criar".
  Para lote a criar: resolva/crie via `StockLotService.criar_se_nao_existe` e passe o `lot_id` real.
- **`criar_se_faltar` exige identificação por chave** (`product_id`+`company_id`+`location_id`),
  não por `quant_id`; e só cria se `qty_apos >= 0`.
- **Validações ligadas por padrão** (`validar_nao_negativar`, `validar_nao_abaixo_reserva`).
  Desligue conscientemente (ex.: reduzir lote-fonte que ficará abaixo da reserva por design).
- **`dry_run=True` não escreve** — sempre rode dry-run antes do real.
- A primitiva **não resolve produto nem cria lote** — faça isso no orquestrador.

## Ponte para orquestrador

Um orquestrador lê a fonte, resolve produto/lote e delega a escrita. Exemplo real:
`scripts/inventario_2026_05/ajuste_inventario.py` (planilha → por linha):

```python
prod = resolver_produto(odoo, cod)                       # default_code -> product + tracking
lot_id = lot_svc.buscar_por_nome(lote, prod['pid'], company_id) or (criar se positivo)
res = svc.ajustar_quant(product_id=prod['pid'], company_id=company_id,
                        location_id=location_id, lot_id=lot_id,
                        delta=qtd, criar_se_faltar=(qtd > 0), dry_run=dry_run)
```

Ver `GUIA_CRIAR_ORQUESTRADOR.md` (passo 8 do roadmap) para o template completo.
