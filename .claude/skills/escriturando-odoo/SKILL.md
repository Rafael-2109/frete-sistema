---
name: escriturando-odoo
description: >-
  Skill WRITE para ESCRITURAR ENTRADA de NF SEFAZ-autorizada no destino
  (DFe -> PO -> picking -> invoice de entrada), com 7 atomos versateis
  servindo qualquer direcao FB-LF-CD via FLUXOS L3 1.2.1/1.2.2. Usar quando
  o pedido eh "escriture a NF SEFAZ na FB", "criar DFe via upload do XML
  para inventario inter-company", "gerar PO a partir do DFe X", "preencher
  lotes do picking gerado", "criar invoice draft a partir do PO Y". dry_run
  eh o DEFAULT em cada atomo. NAO usar para faturamento SAIDA (NF para
  SEFAZ) -> faturando-odoo. Matriz USAR/NAO-USAR completa no corpo.
allowed-tools: Read, Bash, Glob, Grep
---

# escriturando-odoo (WRITE — Skill 7 ABRANGENTE v19+ + wrapper V1 STRICT deprecado)

> **🆕 v19+ ABRANGENTE (2026-05-26)**: Skill 7 agora expõe **7 átomos versáteis** que servem qualquer direção FB↔LF↔CD via FLUXOS L3 1.2.1 (caminho A — DFe veio via SEFAZ) e 1.2.2 (caminho B — DFe criado via XML da SAÍDA). AP1+AP4 ✅ resolvidos. Wrapper V1 STRICT (`criar_recebimento_orchestrado`) preservado como deprecado v20+.

## Quando usar / Quando NÃO usar

**Átomos** (cada um dry-run-first AP4 + idempotência por campos Odoo): `buscar_dfe`,
`criar_dfe_a_partir_do_invoice_saida`, `escriturar_dfe`, `gerar_po_from_dfe`
(fire-and-poll), `preencher_po`, `confirmar_po`, `criar_invoice_from_po`.
Constituição §6: Skill 7 = SO ENTRADA (DFe/NF→in_invoice→saldo); par da Skill 8
`faturando-odoo` (= SO SAÍDA NF→SEFAZ). Composição (caminho A vs B + sequência) é
decidida por FLUXO L3 ou orchestrator — átomos NÃO decidem caminho.

**Wrapper LEGACY** `criar_recebimento_orchestrado` V1 STRICT (LF→FB only via
service externo `RecebimentoLfOdooService`) preservado para retrocompatibilidade
da ETAPA E legacy do orchestrator — deprecado v20+ após canary REAL PROD validar
`executar_fluxo_l3_1_2_x`.

**USAR QUANDO** o pedido é: "escriture a NF SEFAZ na FB", "criar DFe via upload
do XML para inventário inter-company", "gerar PO a partir do DFe X", "preencher
lotes do picking gerado", "criar invoice draft a partir do PO Y". Átomos são
invocados em Python pelo orchestrator (`executar_fluxo_l3_1_2_x`) ou diretamente
pelo operador via fluxo L3.

**NÃO USAR PARA:**
- Faturamento SAÍDA (NF→SEFAZ) -> orchestrator `inventario_pipeline`
  (ex-`faturamento_pipeline`; Skill 8 `faturando-odoo`)
- DFe de fornecedor externo (CTe / Compras — XML externo não controlado
  por nós): `criar_dfe_a_partir_do_invoice_saida` raise FALHA_XML_VAZIO
  pois XML existe em `account.move.l10n_br_xml_aut_nfe` APENAS para NF nossa.
  Para CTe/Compras -> `gestor-recebimento` (subagente).
- Recebimento de COMPRAS (DFe fornecedor 4 fases) -> `gestor-recebimento`
- Cancelar RecLf orfão / DFe (idempotência falha) -> investigação manual

**Defaults**: `--dry-run` é o DEFAULT no CLI (futuro v20+); só efetiva com
`--confirmar`. Em Python (invocação pelo orchestrator), caller controla dry_run
via argumento.

## Átomos v19+ ABRANGENTES (NOVOS — `escrituracao.py` v19+)

Todos os átomos seguem pattern: **kwargs nomeados, `dry_run=True` default, retorno `dict` estruturado com `status`/`erro`/`tempo_ms`**.

| Átomo | Inputs essenciais | Outputs | XML-RPC primário |
|-------|-------------------|---------|------------------|
| `buscar_dfe(chave_nfe, company_id)` | chave_nfe (44 dígitos) | `{encontrado, dfe_id, status, raw}` (status: `pendente`/`a_processar`/`processado`/`ausente`) | `l10n_br_ciel_it_account.dfe.search_read([(protnfe_infnfe_chnfe, =, X), (company_id, =, Y)], ...)` |
| `criar_dfe_a_partir_do_invoice_saida(invoice_id_saida, company_destino, dry_run)` ⚠️ APENAS NF NOSSA | invoice_id da SAÍDA (NF nossa SEFAZ-OK — CNPJ emitente ∈ NACOM); company_destino (1/4/5) | `{status, dfe_id, chave_nfe}` (status: `CRIADO`/`IDEMPOTENT_EXISTE`/`DRY_RUN_OK`/`FALHA`) | Lê `account.move.l10n_br_xml_aut_nfe` + `create('l10n_br_ciel_it_account.dfe', {company_id, l10n_br_xml_dfe})` + `action_processar_arquivo_manual` fire-and-poll. **CTe/Compras (XML externo) → não aplicável** (retorna `FALHA xml_aut_nfe_vazio` ou produz DFe inconsistente; redirecionar para `gestor-recebimento`). |
| `escriturar_dfe(dfe_id, l10n_br_tipo_pedido, data_entrada, dry_run)` | dfe_id; tipo_pedido (`serv-industrializacao`/`transf-filial`/`retorno`/`outro`) | `{status, dfe_id, l10n_br_tipo_pedido, data_entrada}` | `write('l10n_br_ciel_it_account.dfe', [dfe_id], {l10n_br_data_entrada, l10n_br_tipo_pedido})` |
| `gerar_po_from_dfe(dfe_id, fire_timeout_s, poll_timeout_s, dry_run)` | dfe_id (escriturado) | `{status, po_id}` (status: `CRIADO`/`IDEMPOTENT_EXISTE`/`TIMEOUT`/`FALHA`) | `dfe.action_gerar_po_dfe` fire-and-poll (1800s default) via `dfe.purchase_id` + fallback `purchase.order.search([(dfe_id, =, X)])` |
| `preencher_po(po_id, team_id, payment_term_id, picking_type_id, company_id, payment_provider_id, dry_run)` | po_id; constants por company | `{status, po_id}` | `write('purchase.order', [po_id], {team_id, payment_provider_id, payment_term_id, company_id, picking_type_id})` |
| `confirmar_po(po_id, auto_approve, fire_timeout_s, dry_run)` | po_id | `{status, po_id, state_final}` (status: `CONFIRMADO`/`IDEMPOTENT_CONFIRMADO`/`FALHA`) | `purchase.order.button_confirm` + cond `button_approve` (`state='to approve'`) |
| `criar_invoice_from_po(po_id, fire_timeout_s, poll_timeout_s, dry_run)` | po_id (state=`purchase`) | `{status, invoice_id}` (status: `CRIADO`/`IDEMPOTENT_EXISTE`/`TIMEOUT`/`FALHA`) | `purchase.order.action_create_invoice` fire-and-poll via `po.invoice_ids` |

**Cobertura pytest**: 22 testes mockados em `tests/odoo/services/test_escrituracao_lf_service_v19.py` (3 por átomo + 1 AP4 pre-cond invalid).

## Composição via FLUXO L3 (orchestrator/operador)

A inteligência de **decisão caminho A vs B** vive nos fluxos L3, NÃO nos átomos:

- **Fluxo L3 1.2.1** (`app/odoo/estoque/fluxos/1.2.1-escriturar-dfe-industrializacao.md`): caminho A — `buscar_dfe` retornou `encontrado=True` → escriturar→PO→picking→invoice direto.
- **Fluxo L3 1.2.2** (`app/odoo/estoque/fluxos/1.2.2-criar-dfe-manual-transferencia.md`): caminho B — `buscar_dfe` retornou `encontrado=False` + NF é nossa → `criar_dfe_a_partir_do_invoice_saida` → daí em diante idêntico ao 1.2.1.

Implementação Python do dispatch caminho A vs B: `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x` (em `orchestrators/faturamento_pipeline.py` v19+).

---

## Wrapper V1 STRICT (deprecado v20+) — `criar_recebimento_orchestrado`

Skill **mínimo viável V1** (criada em 2026-05-26 v17.5 a partir de revert da
lógica inline `executar_etapa_e` no orchestrator Skill 8 v17). Constituição:
`app/odoo/estoque/CLAUDE.md` §6.

Service: `app/odoo/estoque/scripts/escrituracao.py` (EscrituracaoLfService).
Service externo (4562 LOC, **NÃO MEXER**): `app/recebimento/services/recebimento_lf_odoo_service.py`.

> **Status v19+**: o método `criar_recebimento_orchestrado` permanece funcional para ETAPA E legacy do orchestrator. Em v20+ será removido após canary REAL PROD validar `executar_fluxo_l3_1_2_x` substituindo as ETAPAS E+F.

---

## REGRAS CRÍTICAS

1. **`--dry-run` é o DEFAULT.** Sem `--confirmar`, só calcula e mostra o plano.
2. **G-RECLF-3 idempotência (UK)**: `RecebimentoLf.odoo_lf_invoice_id` tem UK
   aplicada em PROD desde v17. Re-invocar com mesmo `invoice_id` retorna
   `IDEMPOTENT_PROCESSADO` (se já processado) ou retoma (`RETOMADO`).
3. **HIGH-3 retomar `processando`**: se RecLf existe em `status='processando'`,
   o atomo RETOMA (não cria duplicado). Service externo suporta resume via
   `etapa_atual>0`.
4. **HIGH-4 svc fresh**: cada invocação cria nova instância `RecebimentoLfOdooService`
   (anti-vazamento estado via `self._recebimento_id` + caches Redis).
5. **G-RECLF-2 transfer parcial**: `transfer_status='erro'` em FASE 6+7 é
   aceito como `PARCIAL` (FB OK suficiente; FB→CD pode ser re-tentado depois).
6. **D17 CFOP 5xxx→1xxx**: `ACAO_PARA_CFOP_ENTRADA` converte CFOP saída em
   entrada (FB só tem fiscal_position para 1xxx).
7. **NÃO MEXER no service externo** (4562 LOC validados PROD). Atomo apenas
   ORQUESTRA: cria RecLf + agrega lotes + invoca `processar_recebimento`.

## Contrato — `criar_recebimento_orchestrado` (átomo único C3)

```
objeto:        recebimento_lf (model local) + account.move (FB criada pelo svc externo)
input:         invoice_id (int — account.move SEFAZ-OK no Odoo)
               ajustes (List[AjusteEstoqueInventario] pré-filtrada pelo caller)
               ciclo (str — rastreabilidade)
               usuario (str — executado_por svc + auditoria)
               dry_run (bool default True)
               cnpj_emitente (str default '18.467.441/0001-63' = LF; V1 STRICT)
               company_id_recebedor (int default 1 = FB; V1 STRICT)
output (JSON): {status, rec_id, odoo_invoice_id_fb, transfer_status, tempo_ms, erro}
pré-condições: invoice account.move existe + state='posted' + situacao_nf='autorizado'
               ajustes não-vazio com chave_nfe + invoice_id_odoo == invoice_id
               (caller filtra; atomo NÃO re-filtra)
pós-condições: RecebimentoLf criado/retomado/idempotente; svc externo invocado
               sincronamente (30-60min); auditoria registrada por ajuste
gotchas-invariante:
  - G-RECLF-3 idempotência via odoo_lf_invoice_id UK
  - HIGH-3 status='processando' RETOMA (anti-RecLf órfão)
  - HIGH-4 svc instanciado fresh
  - HIGH-5 produto_tracking via fetch batch (D-OPS-5 fix)
  - G-RECLF-2 transfer_status='erro' = PARCIAL OK
  - D17 ACAO_PARA_CFOP_ENTRADA 5xxx→1xxx
  - D9 re-fetch ajustes via safe_session_get pós-svc
  - commit_resilient antes/dentro
modos:         dry_run=True (default, planeja) → dry_run=False (executa)
status:        CRIADO · RETOMADO · IDEMPOTENT_PROCESSADO · PARCIAL · FALHA ·
               DRY_RUN_OK · SKIP_AJUSTES_VAZIOS
raises:        NotImplementedError (cnpj/company_recebedor fora V1 LF→FB)
```

## Receita 1: Criar RecLf orchestrado a partir de NF SEFAZ-OK

**Contexto**: Skill 8 ETAPA E pós-v17.5. Caller filtrou ajustes por
`ACOES_ENTRADA_FB + chave_nfe + invoice_id_odoo` e agrupou por `invoice_id`.

```python
from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService
from app.odoo.utils.connection import get_odoo_connection

odoo = get_odoo_connection()
svc = EscrituracaoLfService(odoo=odoo)

# Para cada invoice_id distinto
for invoice_id, ajustes in ajustes_por_invoice.items():
    # Dry-run primeiro
    plano = svc.criar_recebimento_orchestrado(
        invoice_id=invoice_id,
        ajustes=ajustes,
        ciclo='INVENTARIO_2026_05',
        usuario='operador',
        dry_run=True,
    )
    print(f'invoice {invoice_id}: {plano["observacao"]}')

    # Confirmar via real-run
    resultado = svc.criar_recebimento_orchestrado(
        invoice_id=invoice_id,
        ajustes=ajustes,
        ciclo='INVENTARIO_2026_05',
        usuario='operador',
        dry_run=False,
    )
    if resultado['status'] in ('CRIADO', 'RETOMADO'):
        print(f'OK: rec_id={resultado["rec_id"]} '
              f'inv_fb={resultado["odoo_invoice_id_fb"]}')
    elif resultado['status'] == 'IDEMPOTENT_PROCESSADO':
        print(f'SKIP: ja processado rec_id={resultado["rec_id"]}')
    elif resultado['status'] == 'PARCIAL':
        print(f'PARCIAL: FB OK mas transfer FB->CD erro (G-RECLF-2)')
    else:  # FALHA
        print(f'FALHA: {resultado["erro"]}')
```

## Receita 2: Retomar RecLf travado em `processando`

**Contexto**: crash mid-process deixou RecLf em status='processando' com
etapa_atual<37. Re-rodar com mesmo invoice_id RETOMA via svc externo.

```python
# Mesmo código da Receita 1 — HIGH-3 detecta status='processando'
# e retorna status='RETOMADO' em vez de criar duplicado.
resultado = svc.criar_recebimento_orchestrado(
    invoice_id=629364,
    ajustes=ajustes_invoice_629364,
    ciclo='INVENTARIO_2026_05',
    usuario='operador_retry',
    dry_run=False,
)
# resultado['status'] == 'RETOMADO' (etapa_atual avancou no svc externo)
```

## Receita 3: Retry FASE 6+7 transfer FB→CD (após PARCIAL)

**Contexto**: `transfer_status='erro'` em FASE 6+7 é aceito como PARCIAL pelo
atomo. Para re-tentar transfer FB→CD, invoque `processar_recebimento` DIRETO
no svc externo (já tem suporte a resume nativo):

```python
from app.recebimento.services.recebimento_lf_odoo_service import (
    RecebimentoLfOdooService,
)
svc_externo = RecebimentoLfOdooService()
# Service externo detecta etapa_atual >= 18 (FASE 6 inicia) e RETOMA dali
resultado = svc_externo.processar_recebimento(rec_id=999, usuario_nome='retry_ops')
```

> NOTA: Skill 7 V1 não tem atomo dedicado para retry transfer. Em v18+
> avaliar `processar_transfer_only(rec_id)` como atomo separado se demanda surgir.

---

## TRADE-OFFS V1 ACEITOS

| Trade-off | Razão | Mitigação |
|-----------|-------|-----------|
| **Sequencial por design** | Decisão 10.7 v17 (Rafael 2026-05-25): `RecebimentoLfOdooService` NÃO é thread-safe (Redis state interno em `self._recebimento_id`). | Recovery via re-invocação (G-RECLF-3 idempotente + HIGH-3 retoma processando). |
| **G-RECLF-1 50-100h/onda 100 invoices** | Service externo demora 30-60min/invoice (XML-RPC + polling). Onda de 100 invoices = ~50-100h sequencial. | Aceito por idempotência perfeita; operador acompanha em iterações. |
| **V1 STRICT só LF→FB** | Service externo (`RecebimentoLfOdooService`) hardcoded para COMPANY_FB=1 e COMPANY_LF=5. | Validação de pre-cond raise NotImplementedError até v18+ expandir service externo OU criar service paralelo (RecebimentoCdFbService). |
| **V1 STRICT raise ANTES de dry-run check** | `cnpj_emitente` ou `company_id_recebedor` fora dos defaults raise `NotImplementedError` mesmo em `dry_run=True`. Operadora não consegue "planejar" um CD→FB hipotético. | Aceito V1 (não há caller fora de LF→FB hoje); em V2 (CD→FB) será revisto — o atomo já terá implementação real. Reviewer 1 F4 conf 80 marcou como API footgun pequeno. |

---

## CROSS-REFS

- Constituição: `app/odoo/estoque/CLAUDE.md` §6 (catálogo Skill 7)
- Planejamento Skill 8: `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` §7.4 G-RECLF-*
- Subagente: `.claude/agents/gestor-estoque-odoo.md` (atualizar com Skill 7)
- ROUTING_SKILLS: `.claude/references/ROUTING_SKILLS.md` (entry Skill 7)
- tool_skill_mapper: `app/agente/services/tool_skill_mapper.py` (description rica)
- Skill 8 par (saída): `.claude/skills/faturando-odoo/SKILL.md` (futuro v18)
- Service externo: `app/recebimento/services/recebimento_lf_odoo_service.py` (NÃO MEXER)

---

## CHECKLIST DE EXPANSÃO V2 (futuro)

- [ ] Atomo `processar_transfer_only(rec_id)` (retry FASE 6+7 sem re-criar RecLf)
- [ ] Atomo `cancelar_reclf_orfao(rec_id)` (cleanup quando idempotência falha)
- [ ] Suporte CD→FB (criar RecebimentoCdFb model + service externo análogo)
- [ ] Suporte CD→LF (DEV_CD_LF — novo service)
- [ ] CLI wrapper `.claude/skills/escriturando-odoo/scripts/escriturar.py`
      (atomo é invocado em Python pelo orchestrator Skill 8 hoje; CLI direto pode ser útil para canary/retry isolado)
- [ ] 5+ pytest novos cobrindo v2 (CD→FB, CD→LF, retry transfer)
