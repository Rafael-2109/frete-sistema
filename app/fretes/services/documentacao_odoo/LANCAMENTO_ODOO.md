<!-- doc:meta
tipo: reference
camada: L3
sot_de: lancamento de frete no Odoo (16 etapas DFe -> PO -> Invoice)
hub: app/fretes/CLAUDE.md
superseded_by: —
atualizado: 2026-06-19
-->
# Lancamento de Frete no Odoo — Referencia Tecnica (16 etapas)

> **Papel:** SOT do detalhe tecnico do lancamento automatico de frete no Odoo (pipeline DFe -> PO -> Invoice). Dono dos IDs fixos, campos por modelo Odoo, ordem das 16 etapas e problemas conhecidos. As REGRAS/GOTCHAS de alto nivel (R1-R8, anti-detach, lock Redis) vivem em `app/fretes/CLAUDE.md`; este doc detalha cada etapa. Consolida 6 snapshots historicos de 14/11/2025.

## Indice

- [Visao geral](#visao-geral)
- [IDs fixos](#ids-fixos)
- [CNPJ tomador -> company](#cnpj-tomador-company)
- [As 16 etapas](#as-16-etapas)
- [Campos por modelo Odoo](#campos-por-modelo-odoo)
- [Problemas conhecidos e solucoes](#problemas-conhecidos-e-solucoes)
- [Checkpoint, retomada e rollback](#checkpoint-retomada-e-rollback)
- [Fontes](#fontes)

## Visao geral

Service: `app/fretes/services/lancamento_odoo_service.py` (`LancamentoOdooService.lancar_frete_odoo`). Entrada: `frete_id` + `cte_chave` (44 digitos) + `data_vencimento`. Executa ate 16 etapas automatizadas no Odoo, da busca do DFe ate a confirmacao da Invoice, gravando auditoria por etapa em `LancamentoFreteOdooAuditoria`. `LancamentoDespesaOdooService` herda deste service (mesmo pipeline para `DespesaExtra`, override de auditoria + verificacao de existencia). Roda em job RQ (`workers/lancamento_odoo_jobs.py`, fila `odoo_lancamento`, 600s, lock Redis anti duplo-clique — ver `app/fretes/CLAUDE.md` R7).

> **Numeracao preservada**: a Etapa 8 e PULADA (desabilitada) mas o numero e mantido para nao quebrar a auditoria. Por isso ha "16 etapas" mas 15 efetivas.

## IDs fixos

Hardcoded em `lancamento_odoo_service.py` (NAO mudar sem validar no Odoo):

| Constante | Valor | Significado |
|-----------|------:|-------------|
| `PRODUTO_SERVICO_FRETE_ID` | 29993 | "SERVICO DE FRETE" (cod 800000025) |
| `CONTA_ANALITICA_LOGISTICA_ID` | 1186 | "LOGISTICA TRANSPORTE" (cod 119009) |
| `TEAM_LANCAMENTO_FRETE_ID` | 119 | "Lancamento Frete" |
| `PAYMENT_PROVIDER_TRANSFERENCIA_ID` | 30 | "Transferencia Bancaria" |

## CNPJ tomador -> company

`CNPJ_PARA_COMPANY` mapeia o CNPJ tomador do CTe para a `company_id` do Odoo:

| CNPJ | company_id | Empresa |
|------|-----------:|---------|
| 61724241000178 | 1 | FB |
| 61724241000259 | 3 | SC |
| 61724241000330 | 4 | CD |
| 18467441000163 | 5 | LF |

**Default quando nao encontra: company=4 (CD) com warning** — pode lancar na empresa errada se surgir CNPJ novo. Setar `company_id` ANTES de confirmar o PO e CRITICO (ver Problemas conhecidos).

## As 16 etapas

```
ENTRADA: frete_id + cte_chave (44 digitos) + data_vencimento
   |
[1] Buscar DFe pela chave (l10n_br_ciel_it_account.dfe, campo protnfe_infnfe_chnfe)
   |
[CHECKPOINT] _verificar_lancamento_existente() -> continuar_de_etapa (0|7|9|11|13|16)
[VALIDACAO]  DFe status '04' (novo) | '04' ou '06' (retomada)
   |
[2] Atualizar l10n_br_data_entrada + payment_reference  (SEMPRE, mesmo em retomada)
[3] Verificar/corrigir operacao fiscal (OPERACAO_DE_PARA)
[4] l10n_br_tipo_pedido = 'servico'
[5] Verificar company_id do DFe
   |
[6] *** FIRE-AND-POLL ***  action_gerar_po_dfe
    fire: ~90s; em timeout/502/socket/'cannot marshal None' -> poll DFe.purchase_id a cada 10s ate 600s
    reconcilia auditorias ERRO->SUCESSO se o PO aparece no polling
   |
[7] Configurar PO: valor, picking_type_id, l10n_br_operacao_id, partner_ref,
    team_id=119, payment_provider_id=30, company_id (CRITICO)
[8] PULADA (DESABILITADA) — onchange_l10n_br_calcular_imposto zerava valores no PO
[9] Confirmar PO (button_confirm, ctx validate_analytic=True)
[10] Aprovar PO se state=='to approve' (button_approve — OPCIONAL)
[11] Criar Invoice (action_create_invoice)
[12] Atualizar impostos da Invoice (OPCIONAL — erro logado como warning, fluxo segue)
[13] Configurar Invoice: l10n_br_compra_indcom='out', l10n_br_situacao_nf='autorizado', invoice_date_due
[14] Atualizar impostos da Invoice (OPCIONAL)
[15] Confirmar Invoice (action_post, ctx validate_analytic=True)
   |
[16] db.session.remove() -> re-fetch Frete+CTe -> status='LANCADO_ODOO', salvar IDs Odoo, commit
```

## Campos por modelo Odoo

| Modelo | Campos relevantes |
|--------|-------------------|
| `l10n_br_ciel_it_account.dfe` | `protnfe_infnfe_chnfe` (chave), `l10n_br_data_entrada`, `l10n_br_tipo_pedido` ('servico'), `l10n_br_status` ('04'=pronto p/ PO; '06'=concluido, so retomada), `purchase_id` |
| `l10n_br_ciel_it_account.dfe.line` | `product_id` (=29993), `l10n_br_quantidade`, `product_uom_id`, `analytic_distribution` |
| `l10n_br_ciel_it_account.dfe.pagamento` | `cobr_dup_dvenc` (vencimento), `cobr_dup_ndup`, `cobr_dup_vdup` |
| `purchase.order` | `team_id` (119), `payment_provider_id` (30), `company_id` (CRITICO), `l10n_br_operacao_id`, `state` (draft/to approve/purchase), `invoice_ids` |
| `account.move` (Invoice) | `l10n_br_compra_indcom` ('out'), `l10n_br_situacao_nf` ('autorizado'), `invoice_date_due`, `state` (draft/posted) |

> Campos de TABELAS LOCAIS (Frete, ConhecimentoTransporte, etc.): SOT em `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`.

## Problemas conhecidos e solucoes

1. **`cannot marshal None`** — metodos Odoo retornam `None` e o XML-RPC nao serializa. Afeta `onchange_l10n_br_calcular_imposto[_btn]` e `button_approve`. **Solucao**: capturar a excecao e continuar (o metodo executa do lado do Odoo). Na Etapa 6 esse sinal e tratado como gatilho de polling (o PO foi gerado, so o retorno nao chegou).
2. **"Empresas incompativeis"** — operacao fiscal nao pertence a empresa CD. **Solucao**: setar `company_id` ANTES de confirmar o PO, na ordem: (1) company_id, (2) impostos/operacao fiscal, (3) confirmar.
3. **Impostos zerados no PO** — motivo da Etapa 8 estar DESABILITADA: `onchange_l10n_br_calcular_imposto` no PO zerava valores. Impostos da Invoice (Etapas 12/14) sao OPCIONAIS — podem precisar de ajuste manual no Odoo.
4. **Permissoes** — se falhar por acesso, liberar o modelo no Odoo para o usuario de integracao.

## Checkpoint, retomada e rollback

- **Checkpoint** (`_verificar_lancamento_existente`): inspeciona o estado do DFe/PO/Invoice no Odoo e devolve `continuar_de_etapa` (0=novo; 7/9/11/13/16=retoma). Em retomada, as etapas ja concluidas sao PULADAS (logs "ETAPA N PULADA").
- **Retomada**: DFe pode estar em '04' ou '06'; `l10n_br_data_entrada` e re-atualizado mesmo em retomada (refletir o dia real, nao-bloqueante).
- **Rollback** (`_rollback_frete_odoo`): reseta os IDs Odoo do Frete para NULL — so executa se `etapas_concluidas < 16`.

## Fontes

- FONTE codigo (SOT vivo): `app/fretes/services/lancamento_odoo_service.py` (16 etapas, IDs, CNPJ_PARA_COMPANY, rollback/checkpoint).
- FONTE regras/gotchas de alto nivel: `app/fretes/CLAUDE.md` (R1-R8, lock Redis R7, anti-detach R1).
- FONTE patterns Odoo (P1-P7): `app/odoo/CLAUDE.md`; IDs por empresa: `.claude/references/odoo/IDS_FIXOS.md`.
- Consolida (historico, 14/11/2025): `DOCUMENTACAO_LANCAMENTO_FRETE_ODOO.md`, `IMPLEMENTACAO_LANCAMENTO_ODOO_COMPLETA.md`, `IMPLEMENTACAO_FINAL_COMPLETA.md`, `RESUMO_RAPIDO_LANCAMENTO.md`, `STATUS_IMPLEMENTACAO.md`, `lancamento.md` (agora stubs apontando para este SOT).
