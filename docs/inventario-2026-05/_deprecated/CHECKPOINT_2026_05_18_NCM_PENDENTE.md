# CHECKPOINT — NF 626032 cancelamento pendente + NCM/weight cadastros

**Sessao Claude Code 1**: 2026-05-18 ~07:20 (root cause NF 626032)
**Sessao Claude Code 2**: 2026-05-18 ~08:00 (audit + G017 fix)
**Status global**: Sub-piloto end-to-end com root cause identificado.
G017 fix implementado. Audit fiscal LF completo revelou bloqueios adicionais.
**Aguardando 3 acoes manuais do usuario** + 1 reset DB para refazer pipeline.

> Substitui `CHECKPOINT_2026_05_18_FIXES_L18_L23.md`.

---

## 1. Resumo executivo

Sub-piloto bulk 10 produtos foi executado end-to-end. Identificadas 8
falhas estruturais (L18-L25), 7 ja fixadas. Bloqueio remanescente:

- **NF 626032 (LF perda)** ficou em `excecao_autorizado` (G008) — root
  cause foi NCM=False no produto **103000020 ALHO EM PO** (G017).
- **NF 627348 (FB industr PEPINO)** OK — autorizada normal.

### Estado atual no Odoo

| Picking | Name | State | Detalhe |
|---|---|---|---|
| 317311 | LF/LF/SAI/RNA/00007 | done | 10 ajustes — picking original, devolvido via 317315 |
| 317313 | FB/SAI/IND/01558 | done | 3 ajustes — PEPINO industr OK |
| **317315** | LF/RECEB/IND/01356 | **done** | ✅ Devolucao do 317311 (estoque LF restaurado) |
| 317307-310, 317312 | (varios) | cancel | Pickings das tentativas falhas (sem invoice/SEFAZ) |

| Invoice | NF | Direcao | State | Chave SEFAZ | XML | Acao pendente |
|---|---|---|---|---|---|---|
| **626032** | RETNA/2026/00032 | LF→FB perda | **cancel** local + excecao_autorizado SEFAZ | OK | ✅ inserido (13412b64) | **Cancelar SEFAZ manual** |
| 627348 | RPI/2026/00202 | FB→LF industr | posted | OK | OK | Sem acao (FB→LF nao requer entrada FB — L17) |

### Estado atual no DB local

- **10 ajustes em F5e_SEFAZ_OK** (invoice 626032) com `erro_msg`:
  "G008+G017 cstat=225 NCM=False produto 103000020 ALHO EM PO. NF 626032
  a cancelar manual + cadastrar NCM antes de reset+refazer. Picking
  317311 ja devolvido via 317315."
- 3 ajustes em F5e_SEFAZ_OK (invoice 627348) — OK final, sem necessidade
  de entrada FB (FB→LF).

---

## 2. ROOT CAUSE NF 626032 = G017 (NCM=False)

XML preview baixado via Playwright revelou linha 5 do XML com:

```xml
<det nItem="5">
    <prod>
        <cProd>103000020</cProd>
        <xProd>ALHO EM PO</xProd>
        <NCM>False</NCM>  <!-- ❌ deveria ser 8 dígitos -->
```

Histórico de tentativas (chatter Odoo):
1. 09:10-09:16 — 4 tentativas: `cstat=225 Falha no Schema XML do lote de NFe`
2. 09:18 — cstat=656 `Consumo Indevido` (rate limit)
3. 09:20 — `EspdManNFeEnviadaJaExisteException` (SEFAZ marcou chave)
4. 09:20 — Resolver NFe: ainda cstat=225

Apos meu fix manual G015 (price_unit > 0), as 4 primeiras tentativas
AINDA falharam. Confirmou-se: NCM=False era o problema REAL, nao price.

**Doc completa**: `docs/inventario-2026-05/02-gotchas/G017-ncm-false-bloqueia-sefaz.md`

---

## 3. Acoes manuais pendentes (PRE-REFAZER)

> **Update 2026-05-18 08:19**: pre-reqs 3.2 e 3.3 EXECUTADOS via XML-RPC
> com autorizacao Rafael. Ver `EXECUCAO_CADASTRO_NCM_WEIGHT_2026_05_18.md`.
> Apenas 3.1 (cancel NF 626032) permanece pendente — Rafael fara depois.

### 3.1. Cancelar NF 626032 (manual via UI Odoo) — ⚠️ PENDENTE

**URL**:
```
https://odoo.nacomgoya.com.br/web#id=626032&cids=5&model=account.move&view_type=form
```

**Justificativa** (84 chars, atende >=15):
```
Inventario 2026-05 LF: NFe com Schema XML invalido (cstat 225) - re-emissao corrigida
```

XML autorizado ja foi inserido em `l10n_br_xml_aut_nfe` via script
`baixar_xml_preview_626032.py` — Odoo agora consegue processar o cancel.

### 3.2. Cadastrar NCM em 3 produtos (sub-piloto + onda 1 LF) — ✅ CONCLUIDO 2026-05-18 08:19 UTC

**Aplicado**:
- 103000020 ALHO EM PO -> NCM 07129010 (id=29005)
- 104000046 CORANTE VERMELHO -> NCM 32041100 (id=27676)
- 109000101 OLEO MISTO -> NCM 15179090 (id=28485)

Modelo NCM CIEL IT: `l10n_br_ciel_it_account.ncm` (NAO `l10n_br_fiscal.ncm`).
Campo de codigo: `codigo_ncm` (NAO `code` nem `code_unmasked`).

### 3.2.x. (referencia) Acoes manuais alternativas se precisar redo

Audit (executado em 2026-05-18 sessao 2) listou **3 produtos sem NCM**
em toda a onda 1 LF (escopo: ajustes PROPOSTO + acoes pickings/lotes):

| cod | nome | id Odoo | weight |
|---|---|---|---|
| 103000020 | ALHO EM PO | 31416 | 1.0 ✓ |
| 104000046 | CORANTE VERMELHO | 34907 | **0.0** ❌ (tambem sem weight) |
| 109000101 | OLEO MISTO | 34914 | **0.0** ❌ (tambem sem weight) |

Via UI Odoo: produto → aba Faturamento → NCM (8 dígitos, e.g., 09109100 para ALHO).

OU via XML-RPC (em batch):

```python
from app.odoo.utils.connection import get_odoo_connection
odoo = get_odoo_connection()
# Encontrar NCM apropriado por produto
mapeamento = {
    103000020: '09109100',  # ALHO EM PO
    104000046: '32030000',  # CORANTE VERMELHO (consultar com contadora)
    109000101: '15179090',  # OLEO MISTO (consultar com contadora)
}
for pid, ncm_code in mapeamento.items():
    ncm = odoo.search_read('l10n_br_fiscal.ncm',
        [['code_unmasked', '=', ncm_code]], ['id'], limit=1)
    if ncm:
        odoo.write('product.product', [pid], {'l10n_br_ncm_id': ncm[0]['id']})
```

### 3.3. Cadastrar weight em 2 produtos (sub-piloto) — ✅ CONCLUIDO 2026-05-18 08:14 UTC

**Aplicado** (valores informados pelo Rafael):
- 104000046 CORANTE VERMELHO -> weight=1.0 kg
- 109000101 OLEO MISTO -> weight=0.93 kg

ALHO EM PO ja tinha weight=1.0 (sem mudanca).

### 3.4. Audit fiscal LF completo (REFERENCIA — sessao 2 ja gerou)

Relatorio completo: `docs/inventario-2026-05/07-relatorios/audit_fiscal_LF.md`.

Resumo dos 455 produtos onda 1 LF:
- 3 produtos sem NCM (G017)
- 109 produtos sem weight em acao de picking (G012/G013) — **BLOQUEANTE
  para LF completo**, exige decisao (cadastrar / G018 protecao auto / excluir)
- 128 sem standard_price (G015 cobre auto)
- 1 orfao Odoo (210010600 — script ja pula via skip_pid)

---

## 4. Refazer pipeline (apos acoes manuais)

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# 1. Validar baseline (130 tests passing)
pytest tests/odoo/ -p no:randomly -q

# 2. Confirmar NF 626032 cancelada SEFAZ
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    inv = odoo.read('account.move', [626032], 
        ['name', 'state', 'l10n_br_situacao_nf', 'l10n_br_protocolo_cancelamento'])
    print(inv[0])
"
# Esperado: state=cancel + l10n_br_situacao_nf='cancelado'
#                       + l10n_br_protocolo_cancelamento populado

# 3. Confirmar NCM cadastrado em ALHO EM PO
python3 -c "
import sys; sys.path.insert(0, '.')
from app import create_app
from app.odoo.utils.connection import get_odoo_connection
app = create_app()
with app.app_context():
    odoo = get_odoo_connection()
    p = odoo.search_read('product.product', 
        [['default_code', '=', '103000020']],
        ['default_code', 'name', 'l10n_br_ncm_id'])
    print(p)
"
# Esperado: l10n_br_ncm_id = [N, '09109100 - ...']

# 4. Resetar 10 ajustes do 626032 para PROPOSTO (sem picking_id/fase)
PGPASSWORD=frete_senha_2024 psql -h localhost -U frete_user -d frete_sistema -c "
UPDATE ajuste_estoque_inventario
SET status='PROPOSTO',
    fase_pipeline=NULL,
    picking_id_odoo=NULL,
    invoice_id_odoo=NULL,
    chave_nfe=NULL,
    erro_msg=NULL
WHERE invoice_id_odoo=626032
RETURNING id, cod_produto;
"

# 5. Re-rodar etapa B+C+D+E (G017 fix IMPLEMENTADO em sessao 2!)
# validacao-fiscal=strict (default) aborta etapa B se faltarem NCM/weight.
python scripts/inventario_2026_05/09_executar_onda1_bulk.py \
    --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \
    --confirmar --confirmar-sefaz --usuario=rafael \
    --validacao-fiscal=strict
```

---

## 5. Pendencias para LF completo (bloqueante para 660 produtos)

### Implementar antes do bulk LF completo

1. **G016 (resiliencia SSL)** em `f5e_transmitir_sefaz`:
   - TCP keepalive em SQLALCHEMY_DATABASE_URI
   - Commit antes Playwright + re-busca por ID
   - Try/except + retry com OperationalError

2. **G017 (validar NCM antes pickings)** em `etapa_b_pickings`:
   - Para todos os pids do batch: validar `l10n_br_ncm_id != False`
   - Raise se houver produtos sem NCM com lista detalhada
   - Audit SQL pre-bulk para identificar TODOS produtos sem NCM no
     ciclo onda 1 LF (~660 produtos)

### Audit fiscal recomendado pre-bulk LF

Para cada produto da onda 1 LF, validar:
- `l10n_br_ncm_id != False` (G017 — CRITICO)
- `standard_price > 0` (G007/G015 — corrigido em f5d.6)
- `weight > 0` (G012/G013 — peso liquido/volumes)
- `expiration_date >= hoje` em pelo menos 1 lote FB livre (G014 — para
  acoes INDUSTRIALIZACAO_FB_LF)

---

## 6. Arquivos modificados/criados nesta sessao

### Novos
- `docs/inventario-2026-05/02-gotchas/G016-ssl-crash-no-loop-f5e-perde-commits.md`
- `docs/inventario-2026-05/02-gotchas/G017-ncm-false-bloqueia-sefaz.md`
- `docs/inventario-2026-05/CHECKPOINT_2026_05_18_NCM_PENDENTE.md` (este)
- `scripts/inventario_2026_05/baixar_xml_preview_626032.py` (Playwright XML download)
- **(sessao 2)** `docs/inventario-2026-05/07-relatorios/audit_fiscal_LF.md`

### Atualizados
- `docs/inventario-2026-05/00-decisoes/D006-...md` — sec L24-L25
- DB local: 10 ajustes 626032 com `erro_msg` explicativo
- **(sessao 2)** `scripts/inventario_2026_05/09_executar_onda1_bulk.py`:
  funcao `validar_cadastro_fiscal` + flag `--validacao-fiscal`
- **(sessao 2)** `docs/inventario-2026-05/02-gotchas/G017-...md`: status FIXADO

### Estado Odoo
- Picking 317311: done (LF perda original)
- Picking 317315: done (devolucao — estoque LF restaurado)
- Invoice 626032: state=cancel local + l10n_br_xml_aut_nfe inserido
  (aguardando cancel SEFAZ manual)
- Produto 103000020 ALHO EM PO: l10n_br_ncm_id=False (a cadastrar)

---

## 7. Visao consolidada de bugs e gotchas (L1-L25)

| Sessao | # | Gotcha | Status |
|---|---|---|---|
| 2026-05-17 piloto | L1-L5 | G001-G005 | ✅ FIXADOS |
| 2026-05-18 madrugada (sub-piloto) | L6-L17 | G006-G009 | ✅ FIXADOS |
| 2026-05-18 madrugada (re-exec) | L18-L23 | G010-G015 | ✅ FIXADOS |
| 2026-05-18 manha sessao 1 (root cause) | L24 | G016 | ⚠️ PROPOSTO (PENDENTE) |
| 2026-05-18 manha sessao 1 (root cause) | L25 | G017 | ✅ **FIXADO sessao 2** |
| 2026-05-18 manha sessao 2 (audit + fix) | L26 | G018 weight=0 LF completo | ⚠️ PROPOSTO (DECISAO) |

Total: 26 bugs descobertos, 24 fixados, 2 pendentes (G016 + G018).

## 8. Sessao 2 — Resumo

### Implementado
- **G017 fix**: funcao `validar_cadastro_fiscal(odoo, prod_cache, modo)` em
  `09_executar_onda1_bulk.py:139-211` + chamada em `etapa_b_pickings:529`
  + flag CLI `--validacao-fiscal=strict|warn|skip` (default strict).
  Cobertura: NCM=False (G017) + weight=0 (G012/G013).
- **Tests**: 4 cenarios validados (modo=warn, modo=strict, produto OK,
  pids_map vazio). Tests existentes (29) seguem passando.

### Documentado
- `docs/inventario-2026-05/07-relatorios/audit_fiscal_LF.md` (novo)
  com snapshot completo dos 455 produtos onda 1 LF.
- `G017-...md` atualizado para "FIX IMPLEMENTADO".
- Este CHECKPOINT.

### Descobertas
- 109 produtos sem weight em acao de picking (PERDA + INDUSTRIALIZACAO)
- 2 produtos com problema duplo: CORANTE VERMELHO + OLEO MISTO (sem NCM
  E sem weight)
- 1 orfao no Odoo (210010600 INDUSTRIALIZACAO_FB_LF qty=250330)
