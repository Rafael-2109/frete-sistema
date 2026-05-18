# Quick Start — Próxima sessão (pós-piloto)

**Data do checkpoint:** 2026-05-18 ~02:15 (regeneracao ondas 1-4 concluida)
**Branch:** `main` (commits a8e0d0bb + 995f856e + 5682bec9 + commit pendente)
**Estado:** piloto end-to-end EXECUTADO em PROD (NF-e SEFAZ autorizada).
D004 GENERALIZADA para FB+CD e ajustes REGENERADOS:
- 23.207 PROPOSTO (era 23.633, -426)
- 6 EXECUTADO (piloto preservado)
- 3.338 NFs SEFAZ a emitir (era 3.627, -289 = -8%, ~16h economizadas)
Pronto para construir bulk onda 1.

> **Leitura primeira**:
> 1. `CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md` — snapshot atual
> 2. `00-decisoes/D006-...md` — secao "Licoes aprendidas piloto"

---

## 🎯 PROMPT PRONTO PARA NOVA SESSAO

```
Retomando inventario 2026-05 apos piloto 210030325 LF concluido com
SEFAZ autorizada (chave 35260518467441000163550010000131491006086070,
cstat=100).

LER PRIMEIRO (ordem):
1. docs/inventario-2026-05/CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md
2. docs/inventario-2026-05/00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md
   (secao "Licoes aprendidas piloto" — 5 fixes ja generalizados)
3. docs/inventario-2026-05/SOT.md §7.4-7.5

OBJETIVO: rodar bulk dos 1.065 ajustes restantes da onda 1 (LF) com
fixes do piloto ja integrados:
- L1 incoterm CIF + carrier NACOM em StockPickingService (default)
- L2 cids/menu_id por CNPJ em playwright_nfe_transmissao
- L3 fechar modais tecnicos antes de cada click
- L4 tratar wizard confirmacao apos Transmitir
- L5 payment_provider_id=38 setado em F5d (InventarioPipelineService)

VALIDAR baseline antes (no automatico):
- pytest tests/odoo/ -p no:randomly -q  → 117 passed
- Piloto: 6 ajustes (ids 139003-139008) status=EXECUTADO no DB
- Estado quants: LF lote 26014 com 82.300 un consolidado

REGENERACAO JA FEITA (2026-05-18 ~02:10): ondas 1-4 regeradas com D004
generalizada. 23.207 PROPOSTO + 6 EXECUTADO. Pular para construir bulk.

CONSTRUIR (nesta ordem):
1. Listar onda 1 + capturar hash:
     04_propor_ajustes.py --listar-onda=1
   Filtrar so LF (cid=5)? Onda 1 inclui INDUSTRIALIZACAO_FB_LF,
   PERDA_LF_FB, DEV_*. Confirmar com usuario se quer:
   - aprovar onda 1 inteira (1.065 LF), OU
   - subset por produto via --aprovar-ids
   - ou bloco menor (e.g. 10 produtos primeiro como sub-piloto)

2. Construir 09_executar_onda1_bulk.py:
   - Itera por (cod_produto, company_id) APROVADO
   - Por produto:
     a. Pre-flight: mapear quants reais (StockInternalTransferService.listar_quants)
     b. Garantir lote_alvo (criar_se_nao_existe)
     c. Para cada ajuste RENOMEAR_LOTE: transferir_quantidade_para_lote
     d. Para PERDA/INDUS/DEV (1+ por produto): 1 picking com N linhas
     e. f5b validar, f5c liberar, f5d aguardar (+ payment_provider auto), f5e SEFAZ
   - Checkpoint pos cada produto + tratamento erro parcial
   - Flag --dry-run, --confirmar, --confirmar-sefaz, --limite=N
     (testar com 10 produtos primeiro)

3. Dry-run completo (sem tocar Odoo)
4. PAUSE para confirmacao do usuario
5. --confirmar com --limite=5 (sub-piloto bulk antes)
6. Validar via 08_extrair_pos_execucao.py
7. Se sub-piloto OK: --confirmar sem limite

ATENCAO operacao parcialmente IRREVERSIVEL:
- inventory adjustments: reversiveis via adjustment inverso (trabalhoso)
- picking + invoice: cancelavel ate F5e
- SEFAZ autorizada: irreversivel (precisa NF cancelamento <24h ou CCe)

PAUSE OBRIGATORIO antes do bulk real, mesmo apos dry-run OK.
```

---

## ⚡ Comandos prontos (em ordem)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Validar baseline (117 tests)
pytest tests/odoo/ -p no:randomly -q | tail -3

# 2. Estado DB do piloto (6 EXECUTADO)
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT id, status, fase_pipeline, chave_nfe
FROM ajuste_estoque_inventario WHERE id BETWEEN 139003 AND 139008
ORDER BY id;
"

# 3. Estado onda 1 restante
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
SELECT status, COUNT(*) qtd,
       SUM(ABS(qtd_ajuste*COALESCE(custo_medio,0)))::NUMERIC(15,2) valor_brl
FROM ajuste_estoque_inventario
WHERE ciclo='INVENTARIO_2026_05' AND
      acao_decidida IN ('INDUSTRIALIZACAO_FB_LF','PERDA_LF_FB',
                        'DEV_FB_LF','DEV_LF_FB','DEV_CD_LF','DEV_LF_CD',
                        'RENOMEAR_LOTE')
GROUP BY status;
"

# 4. Re-validar extrator no piloto (deve dar 6 EXECUTADO_OK)
python scripts/inventario_2026_05/08_extrair_pos_execucao.py \
    --ciclo=INVENTARIO_2026_05 --company-id=5 --cod-produto=210030325

# 5. CONSTRUIR 09_executar_onda1_bulk.py (proxima sessao)

# 6. Listar onda 1 + capturar hash (apos build do bulk)
python scripts/inventario_2026_05/04_propor_ajustes.py --listar-onda=1 | head -20

# 7. Aprovar onda 1 (apos revisar valor + alinhamento Tamiris/contadora)
# python scripts/inventario_2026_05/04_propor_ajustes.py \
#     --aprovar-onda=1 --hash=<sha> --usuario=rafael

# 8. Dry-run + sub-piloto bulk
# python scripts/inventario_2026_05/09_executar_onda1_bulk.py --dry-run
# python scripts/inventario_2026_05/09_executar_onda1_bulk.py --confirmar --limite=5 --usuario=rafael

# 9. Bulk completo (apos sub-piloto OK)
# python scripts/inventario_2026_05/09_executar_onda1_bulk.py --confirmar --confirmar-sefaz --usuario=rafael
```

---

## 📋 Checklist de validacao antes do bulk

- [ ] pytest 117 passed
- [ ] Piloto 6 ajustes EXECUTADO no DB
- [ ] Extrator pos-execucao: 6 EXECUTADO_OK para 210030325 LF
- [ ] Conexao Odoo OK (UID 42)
- [ ] Playwright + Chromium instalados
- [ ] ODOO_USERNAME + ODOO_PASSWORD no .env
- [ ] Certificado SEFAZ valido na empresa LF
- [ ] Robo CIEL IT online
- [ ] Backup `pg_dump --table=ajuste_estoque_inventario --table=operacao_odoo_auditoria`
- [ ] Validacao Tamiris/contadora sobre os 1.065 ajustes restantes
- [ ] Decisao: aprovar onda 1 inteira ou sub-piloto por produtos?

---

## 🚨 Riscos conhecidos para bulk

| Risco | Mitigacao |
|---|---|
| Robo CIEL IT serial → F5d toma 25h+ para 100+ pickings | Canary G005 antes — medir tempo com 5+ pickings paralelos |
| Erro parcial (1 produto falha) propaga para outros | Try/except por produto + checkpoint frequente em ajuste.fase_pipeline |
| Lotes em sub-locations não cobertos | Service descobre dinamicamente via `buscar_quant` por location_id |
| SEFAZ rate-limit em 100+ NFs em poucos minutos | Playwright e' serial — intervalo natural entre transmissoes |
| Conflito lote_destino entre produtos | NAO HA — `stock.lot.name` e' unique por (product_id, company_id) |
| Robo CIEL IT cria invoice em estado errado (ex: amount_total=0) para produtos com cobranca | Validar amount_total > 0 quando esperado, OU forcar payment_provider_id apropriado |

---

## 🔗 Referencias rapidas

| Documento | Para que serve |
|---|---|
| `CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md` | Estado completo atual |
| `00-decisoes/D004` | Rename + diferenca liquida (superseded por D006) |
| `00-decisoes/D005` | Lote MIGRACAO FB consolidador fantasma |
| `00-decisoes/D006` | TRANSFERIR via inventory adjustment + licoes piloto |
| `02-gotchas/G001..G005` | Armadilhas descobertas durante audit |
| `SOT.md` | Estado macro do trabalho |
| `app/agente/prompts/prompt_inventario.md` | Intencao original do dono |
| Commit `a8e0d0bb` | `git show a8e0d0bb --stat` |
