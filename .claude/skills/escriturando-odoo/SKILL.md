---
name: escriturando-odoo
description: >-
  Skill WRITE (átomo C3 macro) para ESCRITURAR ENTRADA de NF SEFAZ-autorizada no
  destino via RecebimentoLf + agregação de lotes + invocação do service externo
  RecebimentoLfOdooService (37 etapas LF→FB). Constituição §6: Skill 7 = SO
  ENTRADA (DFe/NF→in_invoice→saldo); par da Skill 8 `faturando-odoo` (= SO
  SAÍDA NF→SEFAZ). Quem une saída + entrada é o FLUXO L3.

  V1 STRICT (2026-05-26 v17.5): SO LF→FB via service externo
  (PERDA_LF_FB, DEV_LF_FB, TRANSFERIR_CD_FB). Outras direções (CD→LF, etc)
  raise NotImplementedError até service externo suportar.

  Usar quando o pedido é: "escriture a NF SEFAZ na FB", "cria RecebimentoLf
  da invoice X", "retoma o RecLf travado da invoice Y", "registra entrada
  da PERDA_LF_FB no Odoo da FB". Atomo é invocado em Python pela Skill 8
  (`executar_etapa_e`) ou diretamente pelo operador via fluxo L3.

  NÃO USAR PARA:
  - Faturamento SAÍDA (NF→SEFAZ) -> usar faturando-odoo (Skill 8)
  - Picking entrada manual SEM RecebimentoLf (G023 FB→LF industr) -> Skill 5
    atomo criar_picking_entrada_destino_manual (invocado pela Skill 8 ETAPA F)
  - Recebimento de COMPRAS (DFe fornecedor 4 fases) -> gestor-recebimento (subagente)
  - Cancelar RecLf orfão (idempotência falha) -> investigação manual (não há
    atomo para cancel; service externo decide via etapa_atual)

  `--dry-run` é o DEFAULT no CLI (futuro v18); só efetiva com `--confirmar`.
  Em Python (invocação pela Skill 8), caller controla dry_run via argumento.
allowed-tools: Read, Bash, Glob, Grep
---

# escriturando-odoo (WRITE — átomo C3 macro)

Skill **mínimo viável V1** (criada em 2026-05-26 v17.5 a partir de revert da
lógica inline `executar_etapa_e` no orchestrator Skill 8 v17). Constituição:
`app/odoo/estoque/CLAUDE.md` §6.

Service: `app/odoo/estoque/scripts/escrituracao.py` (EscrituracaoLfService).
Service externo (4562 LOC, **NÃO MEXER**): `app/recebimento/services/recebimento_lf_odoo_service.py`.

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
