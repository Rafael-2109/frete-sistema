# ANALISE COMPLETA: CONCILIACAO EXTRATO MULTI-COMPANY

**Data:** 2025-12-11
**Caso de Teste:** NF 142211 (VND/2025/05370) - Cliente NUTRICIONALE
**Objetivo:** Entender como conciliar extrato (empresa 1) com titulo (empresa 4)

## IMPLEMENTACAO

**Servico:** `app/financeiro/services/extrato_conciliacao_service.py`

A logica foi implementada no metodo `conciliar_item()`:

### Cenario 1: Titulo JA tem payment (CNAB/manual)
1. Busca titulo no Odoo (SEM filtro de empresa)
2. Verifica matched_credit_ids (payment vinculado)
3. Busca linha PENDENTES do payment (nao reconciliada)
4. Reconcilia: `linha_PENDENTES <-> linha_EXTRATO`

### Cenario 2: Titulo NAO tem payment (MESMA empresa)
1. Busca titulo no Odoo
2. Verifica que nao tem payment
3. Verifica que titulo e extrato sao da mesma empresa
4. Reconcilia direto: `linha_EXTRATO <-> titulo`

### Cenario 3: Titulo NAO tem payment (empresas DIFERENTES)
1. Busca titulo no Odoo
2. Verifica que nao tem payment
3. Verifica que titulo e extrato sao de empresas diferentes
4. CRIA payment na empresa do titulo
5. Reconcilia payment com titulo
6. Busca linha PENDENTES do payment criado
7. Reconcilia: `linha_PENDENTES <-> linha_EXTRATO`

**Resultado:** Titulo baixado + extrato conciliado em uma unica operacao!

---

## 1. CENARIO ANALISADO

| Entidade | Empresa | ID | Valor |
|----------|---------|-----|-------|
| NF | 4 - CD | 413628 | R$ 2.135,93 |
| Parcela 1 | 4 - CD | 2687723 | R$ 711,98 |
| Linha Extrato | 1 - FB | 18120 | R$ 711,98 |
| Move Extrato | 1 - FB | 428302 | - |
| Payment CNAB | 4 - CD | 17846 | R$ 711,98 |

---

## 2. DESCOBERTA PRINCIPAL

### A CONTA PONTE

O Odoo usa a conta **"1110100004 PAGAMENTOS/RECEBIMENTOS PENDENTES"** (ID 26868) como PONTE entre empresas diferentes!

Esta conta:
- Existe em AMBAS as empresas (1 e 4)
- Recebe lancamentos de AMBOS os lados (payment e extrato)
- Permite reconciliacao cross-company

---

## 3. FLUXO DETALHADO DA CONCILIACAO

### ANTES da conciliacao via extrato:

```
EMPRESA 4 (CD)                           EMPRESA 1 (FB)
─────────────                            ─────────────

Parcela 1 (2687723)                      Extrato (stmt_line 18120)
├─ reconciled: True                      ├─ is_reconciled: False
├─ matched_credit_ids: [32963]           ├─ move_id: 428302
└─ l10n_br_paga: True                    └─ amount: 711.98

Payment CNAB (17846)                     Move Extrato (428302)
├─ move_id: 423249                       ├─ linha 2770009 (debito banco)
└─ linhas:                               └─ linha 2770010 (credito transitoria)
   ├─ 2734615 (debito PENDENTES)
   │   └─ amount_residual: 711.98 ← ESPERANDO RECONCILIACAO!
   └─ 2734616 (credito CLIENTES)
       └─ reconciled: True (com parcela)
```

### DEPOIS da conciliacao via extrato:

```
EMPRESA 4 (CD)                           EMPRESA 1 (FB)
─────────────                            ─────────────

Payment CNAB (17846)                     Move Extrato (428302)
└─ linha 2734615 (debito PENDENTES)      └─ linha 2780042 (credito PENDENTES)
   ├─ amount_residual: 0.0                  ├─ amount_residual: 0.0
   ├─ reconciled: True                      ├─ reconciled: True
   ├─ matched_credit_ids: [33387]           ├─ matched_debit_ids: [33387]
   └─ full_reconcile_id: 27438              └─ full_reconcile_id: 27438
              │                                        │
              └────────────────┬───────────────────────┘
                               │
                    PARTIAL_RECONCILE 33387
                    ├─ company_id: 1 (FB)
                    ├─ debit_move_id: 2734615 (payment linha)
                    ├─ credit_move_id: 2780042 (extrato linha)
                    ├─ amount: 711.98
                    └─ full_reconcile_id: 27438
```

---

## 4. O QUE O ODOO FEZ NA CONCILIACAO

1. **Modificou o move do extrato** (428302)
   - Linhas originais (2770009, 2770010) foram substituidas
   - Novas linhas (2780041, 2780042) foram criadas
   - Linha 2780042 usa conta PAGAMENTOS PENDENTES

2. **Reconciliou as linhas da conta PENDENTES**
   - Linha 2734615 (empresa 4 - payment) ↔ Linha 2780042 (empresa 1 - extrato)
   - Criou partial_reconcile 33387
   - Criou full_reconcile 27438

3. **A PARCELA NAO MUDOU DIRETAMENTE**
   - Parcela 1 continua com mesmos matched_credit_ids [32963]
   - A conciliacao foi feita nas linhas da conta PENDENTES

---

## 5. IMPLEMENTACAO NO SERVICO

### Passos para conciliar extrato multi-company:

```python
def conciliar_extrato_com_titulo(titulo_id: int, stmt_line_id: int):
    """
    Concilia linha de extrato (empresa 1) com titulo (empresa 4)
    via conta ponte PAGAMENTOS PENDENTES.
    """

    # 1. Buscar o titulo e seu payment vinculado
    titulo = odoo.read('account.move.line', [titulo_id])
    matched_ids = titulo.get('matched_credit_ids', [])

    if not matched_ids:
        raise Exception("Titulo nao tem pagamento vinculado (via CNAB ou manual)")

    # 2. Buscar as partial_reconciles do titulo
    partials = odoo.read('account.partial.reconcile', matched_ids)

    # 3. Encontrar a linha do payment na conta PENDENTES
    payment_pendente_line_id = None

    for p in partials:
        # Buscar o move do credito (payment)
        credit_line_id = p['credit_move_id'][0]
        payment = odoo.read('account.payment', [
            odoo.read('account.move.line', [credit_line_id])['payment_id'][0]
        ])

        # Buscar linha de DEBITO do payment na conta PENDENTES
        payment_move_id = payment['move_id'][0]
        payment_lines = odoo.search_read('account.move.line', [
            ['move_id', '=', payment_move_id],
            ['account_id', '=', 26868],  # PAGAMENTOS PENDENTES
            ['debit', '>', 0],
            ['reconciled', '=', False]   # AINDA NAO RECONCILIADA!
        ])

        if payment_lines:
            payment_pendente_line_id = payment_lines[0]['id']
            break

    if not payment_pendente_line_id:
        raise Exception("Nao encontrou linha de pagamento na conta PENDENTES")

    # 4. Buscar a linha de credito do extrato
    stmt_line = odoo.read('account.bank.statement.line', [stmt_line_id])
    move_id = stmt_line['move_id'][0]

    extrato_lines = odoo.search_read('account.move.line', [
        ['move_id', '=', move_id],
        ['account_id', '=', 26868],  # PAGAMENTOS PENDENTES
        ['credit', '>', 0],
        ['reconciled', '=', False]
    ])

    if not extrato_lines:
        raise Exception("Extrato nao tem linha na conta PENDENTES")

    extrato_pendente_line_id = extrato_lines[0]['id']

    # 5. Reconciliar as duas linhas
    odoo.execute_kw('account.move.line', 'reconcile', [
        [payment_pendente_line_id, extrato_pendente_line_id]
    ])

    return {
        'payment_line_id': payment_pendente_line_id,
        'extrato_line_id': extrato_pendente_line_id,
        'status': 'reconciliado'
    }
```

---

## 6. CONTA PONTE - DETALHES

| Campo | Valor |
|-------|-------|
| **ID** | 26868 |
| **Codigo** | 1110100004 |
| **Nome** | PAGAMENTOS/RECEBIMENTOS PENDENTES |
| **Tipo** | asset_current |
| **Reconciliar** | True |

Esta conta e usada para:
- Pagamentos manuais aguardando conciliacao bancaria
- Pagamentos CNAB aguardando confirmacao no extrato
- Transferencias entre empresas do grupo

---

## 7. IDS IMPORTANTES

### Contas Contabeis
| ID | Codigo | Nome |
|----|--------|------|
| 26868 | 1110100004 | PAGAMENTOS/RECEBIMENTOS PENDENTES |
| 24801 | 1120100001 | CLIENTES NACIONAIS |
| 26706 | 1110200029 | BANCO GRAFENO 08140378-4 |
| 22199 | 1110100003 | TRANSITORIA DE VALORES |

### Journals
| ID | Codigo | Nome | Empresa |
|----|--------|------|---------|
| 883 | GRA1 | GRAFENO | 1 (FB) |

---

## 8. SNAPSHOTS SALVOS

- `snapshot_conciliacao_extrato_ANTES_20251211_192932.json`
- `snapshot_conciliacao_extrato_DEPOIS_20251211_193035.json`

---

## 9. CONCLUSOES

1. **A conciliacao multi-company usa CONTA PONTE**
   - Nao reconcilia diretamente titulo ↔ extrato
   - Reconcilia: linha_payment_pendentes ↔ linha_extrato_pendentes

2. **O titulo ja deve estar "baixado" (via CNAB ou manual)**
   - A conciliacao do extrato e uma SEGUNDA etapa
   - Confirma o recebimento no banco

3. **A partial_reconcile criada e da empresa do EXTRATO (1)**
   - Nao da empresa do titulo (4)

4. **Para implementar no servico:**
   - Buscar linha do payment na conta PENDENTES (empresa titulo)
   - Buscar linha do extrato na conta PENDENTES (empresa banco)
   - Chamar reconcile() com as duas linhas
