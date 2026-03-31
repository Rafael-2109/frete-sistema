# Odoo — Routing para o Agente Web

> **Criado em**: 2026-03-18
> **Objetivo**: Ponto de entrada Odoo para o agente web — verificar modelos ANTES de executar, saber onde encontrar cada informacao.

---

## Regra Zero — Verificar ANTES de Operar

> **OBRIGATORIO**: Antes de QUALQUER chamada Odoo (XML-RPC, Bash com `python -c`, script):

1. **Consultar `MODELOS_CAMPOS.md`** — modelos `l10n_br_fiscal.*` NAO EXISTEM nesta instalacao. Usar `l10n_br_ciel_it_account.*` (CIEL IT).
2. **Consultar `IDS_FIXOS.md`** — NUNCA inventar IDs de company, journal, picking_type ou operacao.
3. **Consultar `GOTCHAS.md`** — timeouts, campos inexistentes e commit preventivo.

**NUNCA executar Bash/XML-RPC com nome de modelo sem confirmar que existe.**
Se o modelo NAO esta em `MODELOS_CAMPOS.md` → usar skill `descobrindo-odoo-estrutura` para verificar.

---

## Routing de Skills Odoo

Para arvore de decisao completa (qual skill usar): **`ROUTING_SKILLS.md`** Passos 2 e 3.

Resumo rapido:

| Intencao | Skill |
|----------|-------|
| Rastrear NF, PO, SO, pagamento | `rastreando-odoo` |
| Match NF x PO (Fase 2) | `validacao-nf-po` |
| Split/Consolidar PO (Fase 3) | `conciliando-odoo-po` |
| Lotes/Quality Check (Fase 4) | `recebimento-fisico-odoo` |
| Pagamentos, reconciliacoes (clientes/fornecedores) | `executando-odoo-financeiro` |
| Transferencias internas entre contas NACOM GOYA | `conciliando-transferencias-internas` |
| Razao geral, balancete | `razao-geral-odoo` |
| Explorar modelo desconhecido | `descobrindo-odoo-estrutura` (ULTIMO RECURSO) |

---

## Docs Disponiveis em `odoo/`

| Documento | Quando consultar |
|-----------|-----------------|
| `MODELOS_CAMPOS.md` | Antes de qualquer query/script — campos e mapeamento de modelos CIEL IT |
| `IDS_FIXOS.md` | Antes de referenciar IDs de company, journal, picking_type, operacao |
| `GOTCHAS.md` | Ao debugar falhas — timeouts, campos inexistentes, commit preventivo |
| `CONVERSAO_UOM.md` | Problemas de quantidade/unidade no recebimento |
| `PIPELINE_RECEBIMENTO.md` | Entender as 4 fases (Fiscal → Match → Consolidacao → Fisico) |
| `PIPELINE_RECEBIMENTO_LF.md` | Recebimento especifico La Famiglia |
| `PADROES_AVANCADOS.md` | Padroes de implementacao (auditoria, batch, retry) |
