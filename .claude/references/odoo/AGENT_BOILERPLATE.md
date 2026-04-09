# Odoo Agent Boilerplate — Blocos Compartilhados

**Ultima Atualizacao**: 2026-04-09

Blocos compartilhados entre `especialista-odoo` e `desenvolvedor-integracao-odoo`. Atualizacao aqui propaga aos dois agents. Extraido para eliminar ~135 linhas de duplicacao.

**Como usar**: Cada agent Odoo inclui referencia no topo do bloco:
```markdown
## REGRA ZERO
> Ver: `.claude/references/odoo/AGENT_BOILERPLATE.md#regra-zero`
```

---

## regra-zero

**EXECUTAR ANTES DE QUALQUER OUTRA COISA** quando a tarefa contem **"rastreie"**, **"rastrear"**, **"fluxo de"** ou **"titulo de"**:

**Executar IMEDIATAMENTE** (primeira acao do agent):

```bash
source .venv/bin/activate && python .claude/skills/rastreando-odoo/scripts/rastrear.py "ENTRADA_DO_USUARIO" --json
```

Substitua `ENTRADA_DO_USUARIO` pelo termo mencionado (ex: "NF 54321", "PO00789", "VCD123").

**NAO FACA**:
- ❌ Queries manuais com `search_read` antes do rastrear.py
- ❌ Perguntas ao usuario antes de executar o script
- ❌ Investigar por conta propria (fabricacao de caminhos)

**FACA**:
- ✅ Executar o script `rastrear.py` PRIMEIRO
- ✅ Analisar o resultado JSON (contem o fluxo completo)
- ✅ SO DEPOIS fazer perguntas se necessario

**Por que**: O script `rastrear.py` ja segue todos os relacionamentos automaticamente (DFE → PO → Fatura → Titulos → Pagamentos). Refazer esse caminho manualmente eh redundante e fabrica mais risco de erro.

---

## scripts-disponiveis

Scripts principais para tarefas comuns em agents Odoo.

| Tarefa | Script Recomendado | Alternativa |
|--------|-------------------|-------------|
| Rastrear fluxo documental (NF → titulo) | `rastrear.py` (segue relacionamentos) | `descobrindo.py` (consultas manuais) |
| Descobrir campos de modelo | `descobrindo.py --listar-campos` | — |
| Auditoria de faturas | `auditoria_faturas_compra.py` | — |

### Rastrear Fluxo (NF, PO, SO → titulo, pagamento)

```bash
source .venv/bin/activate && python .claude/skills/rastreando-odoo/scripts/rastrear.py "NF 54321" --json
```

> Retorna fluxo completo: DFE → PO → Fatura → Titulos → Pagamentos

### Descobrir Campos de Modelo

```bash
source .venv/bin/activate && python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py --modelo account.move --listar-campos
```

### Consulta Generica (quando precisa filtro especifico)

```bash
source .venv/bin/activate && python .claude/skills/descobrindo-odoo-estrutura/scripts/descobrindo.py --modelo l10n_br_ciel_it_account.dfe --filtro '[[\"nfe_infnfe_ide_nnf\",\"=\",\"54321\"]]' --limit 10
```

**DICA**: Para tarefas de "rastrear" ou "fluxo de", prefira `rastrear.py` — ele segue relacionamentos automaticamente. Para explorar campos novos, use `descobrindo.py`.

---

## conexao-odoo

Padrao de conexao com Odoo ERP.

```python
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()
if not odoo.authenticate():
    raise Exception("Falha na autenticacao com Odoo")

# Metodos principais:
odoo.search_read(modelo, domain, fields, limit)
odoo.search(modelo, domain, limit)
odoo.read(modelo, ids, fields)
odoo.write(modelo, ids, valores)
odoo.create(modelo, valores)
odoo.execute_kw(modelo, metodo, args, kwargs, timeout_override=None)
```

**Arquivos de referencia**:
- Conexao: `app/odoo/utils/connection.py`
- Config: `app/odoo/config/odoo_config.py`
- Circuit Breaker: `app/odoo/utils/circuit_breaker.py`
- Safe Connection: `app/odoo/utils/safe_connection.py`

**GOTCHA geral**: Metodos que retornam `None` no Odoo (`button_validate`, `action_create_payments`, `reconcile`) causam erro `"cannot marshal None"` no XML-RPC. Este erro significa **SUCESSO** — sempre tratar com try/except.

```python
try:
    odoo.execute_kw('stock.picking', 'button_validate', [[picking_id]])
except Exception as e:
    if "cannot marshal None" not in str(e):
        raise
    # "cannot marshal None" = SUCESSO! Odoo retorna None via XML-RPC
```

---

## checklist-extrato-bancario

Para boletos, o Odoo NAO preenche automaticamente 3 campos ao reconciliar extrato. **TODOS** devem ser escritos ANTES do `reconcile()`.

**Usar metodo consolidado** que faz tudo em UM ciclo `button_draft → write → action_post`:
- `baixa_pagamentos_service.preparar_extrato_para_reconciliacao(move_id, stmt_line_id, partner_id, rotulo)` — publico, IDs raw
- `extrato_conciliacao_service._preparar_extrato_para_reconciliacao(item, partner_id, partner_name)` — privado, ExtratoItem

### Ordem Obrigatoria

| Ordem | O que | GOTCHA |
|-------|-------|--------|
| 1 | `button_draft` | — |
| 2 | Write `partner_id` + `payment_ref` na statement_line | Pode REGENERAR move_lines! |
| 3 | Write `name` nas move_lines | Re-buscar IDs apos passo 2! |
| 4 | Write `account_id` TRANSITORIA → PENDENTES | **ULTIMO!** Re-buscar IDs! |
| 5 | `action_post` | — |
| 6 | `reconcile()` | **POR ULTIMO** — fora do metodo consolidado |

### Gotchas Criticos

- **GOTCHA O11**: `button_draft` em move reconciliado **DESFAZ a reconciliacao**. Por isso reconcile SEMPRE por ultimo.
- **GOTCHA O12**: Write na `account.bank.statement.line` faz Odoo **REGENERAR** `account.move.line`, revertendo `account_id` se escrito antes. Por isso `account_id` DEVE ser ULTIMO write.
- **NUNCA** fazer as 3 operacoes (trocar conta, atualizar partner, atualizar rotulo) em chamadas separadas — cada uma faz seu proprio ciclo `button_draft → post`, causando O11/O12.
- **DEPRECADO**: `_atualizar_campos_extrato()` — NAO usar.

### Contas-Chave

| ID | Codigo | Nome | Papel |
|----|--------|------|-------|
| 22199 | 1110100003 | TRANSITORIA | Contrapartida temporaria do extrato |
| 26868 | 1110100004 | PENDENTES | Ponte payment ↔ extrato (reconciliacao) |
| 24801 | 1120100001 | CLIENTES NACIONAIS | Receivable (clientes) |

> IDs completos: `.claude/references/odoo/IDS_FIXOS.md`

---

## Historico

- **2026-04-09**: Criacao inicial. Blocos extraidos de `especialista-odoo.md` (linhas 11-29, 62-86, 90-113, 228-251) e `desenvolvedor-integracao-odoo.md` (linhas 11-29, 47-71, 141-162, 409-431). Os dois agents passaram a referenciar este boilerplate, reduzindo ~135 linhas de duplicacao.
