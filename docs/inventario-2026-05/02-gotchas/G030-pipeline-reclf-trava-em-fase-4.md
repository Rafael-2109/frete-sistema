# G030 — Pipeline RecebimentoLfOdooService trava em Fase 4 (rare)

**Descoberta**: 2026-05-18 sessao 3 tarde (RecLf 14)
**Severidade**: MEDIUM (raro, manual fix simples)
**Status**: 📝 DOCUMENTADO (causa raiz não isolada; workaround OK)

---

## Sintoma

`RecebimentoLfOdooService.processar_recebimento(rec_id)` trava em
**Fase 4 etapa 14/37** sem progredir. Comparação com casos normais:

| RecLf | NF | Tempo | Status |
|-------|-----|-------|--------|
| 7 | 13151 | 1m42s ✅ | processado |
| 11 | 13153 | 1m26s ✅ | processado |
| 14 | 13155 | **>14min ❌** | processando (preso) |
| 16 | 13156 | 1m30s ✅ | processado |
| 17 | 13157 | 1m20s ✅ | processado |

Processo Python em `hrtimer_nanosleep` (sleeping). Sem CPU usage,
sem crash, sem timeout. Conexões TCP ativas com Odoo permanecem.

## Estado no Odoo quando trava

Investigação do RecLf 14:
```
DFe FB 42885: status=06 (Discovery confirmado) ✅
PO C2619254 (id 41932): state=purchase ✅
Picking FB/IN/13159 (id 317481): state=done ✅
Invoice in_invoice 629567: state=draft ❌  ← AQUI TRAVOU
```

**Tudo criado, só falta postar a invoice in_invoice da entrada FB**.

## Causa raiz hipotetizada

Fase 4 do pipeline (etapas 12-18) faz `fire_and_poll` em:
- Etapa 12: action_post invoice (postar)
- Etapa 13: aguardar invoice ser postada
- Etapa 14: validar dados (linha onde travou)

Hipóteses não confirmadas:
1. `fire_and_poll` com timeout muito longo + Odoo CIEL IT processing
   silenciosamente lento.
2. Lock interno do Odoo em hooks pós-`action_post`.
3. SSL transiente que travou silenciosamente o XML-RPC ack.

## Workaround manual

```python
# 1. Verificar estado real no Odoo
inv = odoo.read('account.move', [invoice_fb_id], ['state', 'name'])
# state=draft, name='/'

# 2. Postar manualmente
odoo.execute_kw('account.move', 'action_post', [[invoice_fb_id]])
# Resultado: state=posted, name='ENTSI/2026/05/0047'

# 3. Marcar RecLf como processado no DB local
db.session.execute(text("""
    UPDATE recebimento_lf
    SET status='processado',
        fase_atual=7, etapa_atual=37,
        transfer_status='sem_transferencia',
        odoo_invoice_id=:inv_id,
        processado_em=NOW()
    WHERE id=:rec_id
"""), {'inv_id': invoice_fb_id, 'rec_id': rec_id})
db.session.commit()
```

## Para evitar (recomendação operacional)

- Não interromper o background quando RecLf está em Fase 4-5 (etapas 12-18)
- Se interrompido, verificar estado no Odoo ANTES de reiniciar (evita
  duplicar PO/invoice)
- Pipeline tem retomada (`processar_recebimento` lê `etapa_atual` do DB
  e retoma) — mas se trava de novo no mesmo ponto, fazer manual

## Detecção

Trigger de alarme operacional: RecLf com `status='processando'` por
mais de 5 min:

```sql
SELECT id, numero_nf, fase_atual, etapa_atual,
       NOW() - criado_em AS duracao
FROM recebimento_lf
WHERE status='processando' AND criado_em < NOW() - INTERVAL '5 minutes';
```

## Ref

- `app/recebimento/services/recebimento_lf_odoo_service.py` (pipeline 37 etapas)
- Fase 4: etapas 12-18 = "Postar invoice in_invoice FB"
- G016 (SSL crash) — possivel causa relacionada
