# D007 — Patches para documentos existentes (NAO aplicados nesta sessao)

**Data**: 2026-05-18
**Status**: aguardando integracao
**Contexto**: D007 (pre-etapa CD/FB) foi implementado em sessao paralela.
Para evitar race condition com outra sessao Claude Code (que estava
mexendo em SOT.md, D005, QUICK_START_NEXT_SESSION.md, 03_confrontar,
04_propor), esta sessao **NAO modificou** nenhum dos documentos
abaixo. Este arquivo lista o que DEVE ser inserido em cada um quando
a outra sessao finalizar.

> **Ordem sugerida de aplicacao**: D004 → D005 → D006 → SOT → QUICK_START → 03/04 (scripts).

---

## 1. `SOT.md` — adicionar ao final da secao §3 "ESTADO POR FASE"

### Trecho a inserir (apos §7.4.3 "D004 GENERALIZADA para FB+CD"):

```markdown
### §7.4.4 — PRE-ETAPA CD/FB para minimizar NFs inter-filial (2026-05-18)

Apos analise do valor anormal das NFs FB↔CD (R$ 32,9 mi em
TRANSFERIR_CD_FB e R$ 60,5 mi em INDISPONIBILIZAR_LOTE), o usuario
decidiu substituir a abordagem fiscal por uma **pre-etapa interna**
ao CD. Mesma logica aplicada na FB depois (Onda 6 futura).

**Mecanismo**: por produto no CD, transferir quantidades entre lotes
INTERNAMENTE para satisfazer o inventario, consolidando residual em
lote `MIGRAÇÃO` do CD. So gera NF (TRANSFERIR_FB_CD) quando FB
precisa doar para CD nao coberto internamente.

**3 novas acoes**:
- `AJUSTE_CD_TRANSF_INTERNA_POS` — lote_X (CD) → lote_alvo (CD)
- `AJUSTE_CD_TRANSF_INTERNA_NEG` — lote_X (CD) → MIGRAÇÃO (CD)
- `AJUSTE_CD_POSITIVO_PURO` — `stock.quant.action_apply_inventory`

**Onda 5** (nova) = pre-etapa CD. Executa ANTES da Onda 2 (que fica
drasticamente reduzida — so TRANSFERIR_FB_CD residual).

**Impacto pos-regeneracao** (ver D007):
- TRANSFERIR_CD_FB: 356 ajustes → **0** (eliminado, R$ 32,9 mi)
- INDISPONIBILIZAR_LOTE CD: 5.470 → **0** (eliminado, R$ 60,5 mi)
- INDISPONIBILIZAR_LOCAL CD: 107 → **0** (eliminado, R$ 340,3 mi)
- TRANSFERIR_FB_CD: 29 → ~poucos (residual real)

Onda 6 (FB pre-etapa) sera criada apos outra sessao finalizar.

Ver `00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`.
```

### Trecho a inserir em §3 (tabela "Estado por fase"):

Adicionar uma linha apos F5:

```markdown
| **F5b** Pre-etapa CD/FB | ⚠️ CD implementado em sessao paralela, FB pendente | `pre_etapa_estoque_service.py` + scripts 03b/04b/09b | N tests (cobrir 12 cenarios) |
```

### Trecho a inserir em §8 (Artefatos persistidos):

```
app/odoo/services/
  pre_etapa_estoque_service.py  # D007 — planejador parametrizado company_id

tests/odoo/services/
  test_pre_etapa_estoque_service.py  # D007 (12 tests)

scripts/inventario_2026_05/
  03b_planejar_pre_etapa_cd.py     # D007 — gera plano /tmp/plano_pre_etapa_cd.json + Excel
  04b_propor_pre_etapa_cd.py       # D007 — DELETE + insert Onda 5
  09b_executar_pre_etapa.py        # D007 — executa via StockInternalTransferService

docs/inventario-2026-05/00-decisoes/
  D007-pre-etapa-cd-fb-minimizar-nf.md
  D007-PATCHES-PARA-DOCS-EXISTENTES.md  # ESTE ARQUIVO
```

---

## 2. `QUICK_START_NEXT_SESSION.md` — adicionar ao final

### Trecho a inserir:

```markdown
---

## Pre-etapa CD/FB (D007 — 2026-05-18)

**Em paralelo** ao bulk Onda 1 LF, sessao paralela implementou
pre-etapa CD para minimizar NFs inter-filial. Status apos sessao:

- Onda 5 CD (interno): ajustes regenerados, prontos para aprovar
- Onda 2 (TRANSFERIR_FB_CD): drasticamente reduzida
- Onda 6 FB (futura): aguarda esta sessao do bulk finalizar

**Para retomar**: ver `00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`.

**Comandos rapidos**:
```bash
# Listar Onda 5 + hash
python scripts/inventario_2026_05/04b_propor_pre_etapa_cd.py --listar-onda=5

# Aprovar onda 5
python scripts/inventario_2026_05/04b_propor_pre_etapa_cd.py \
    --aprovar-onda=5 --hash=<sha> --usuario=rafael

# Executar pre-etapa CD (dry-run primeiro)
python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
    --company-id=4 --dry-run
python scripts/inventario_2026_05/09b_executar_pre_etapa.py \
    --company-id=4 --confirmar --usuario=rafael
```
```

---

## 3. `D004-rename-lote-diferenca-liquida.md` — adicionar nota

### Trecho a inserir no inicio (apos linha de Status):

```markdown
**Atualizacao 2026-05-18 (D007)**: para o CD (cid=4), a logica de
"diferenca liquida via NF" foi superseded por **pre-etapa interna**
— ver `D007-pre-etapa-cd-fb-minimizar-nf.md`. D004 continua valida
para LF↔FB. Generalizacao FB (cid=1) tambem sera substituida na
proxima sessao (Onda 6).
```

---

## 4. `D005-lote-migracao-consolidador-fantasmas.md` — adicionar nota

### Trecho a inserir no inicio (apos linha de Status):

```markdown
**Atualizacao 2026-05-18 (D007)**: o lote MIGRAÇÃO agora consolida
fantasmas em **CADA company** (CD: pre-etapa Onda 5; FB: Onda 6 futura),
nao mais apenas na FB. A semantica permanece (saldo isolado para
tratamento posterior), mas o mecanismo deixa de ser "active=False"
(INDISPONIBILIZAR_LOTE) e passa a ser "transferir via inventory
adjustment para lote MIGRAÇÃO da propria company". Ver
`D007-pre-etapa-cd-fb-minimizar-nf.md`.
```

---

## 5. `D006-transferir-quantidade-entre-lotes-nao-renomear.md` — adicionar nota

### Trecho a inserir no inicio (apos linha de Status):

```markdown
**Atualizacao 2026-05-18 (D007)**: a operacao `transferir_entre_lotes`
deste service e reutilizada pelo `PreEtapaEstoqueService` (D007). O
mesmo padrao funciona para a pre-etapa CD/FB sem mudancas no service
de baixo nivel. Ver `D007-pre-etapa-cd-fb-minimizar-nf.md`.
```

---

## 6. `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py` — desativar geracao CD

### Mudanca proposta em `confrontar_company()` (linha ~282, dentro do bloco D004):

**Antes** (atual):
```python
# D004 generalizado: aplicado a TODAS as companies
if (
    total_odoo > 0
    and total_inv > 0
    and not lotes_odoo_set.intersection(lotes_inv_set)
    and not inv_sem_lote
):
    # gera RENOMEAR_LOTE_PARCIAL + diff liquido (PERDA / TRANSFERIR / INDUSTRIALIZACAO)
    ...
```

**Depois** (proposto):
```python
# D004 generalizado: aplicado a TODAS as companies EXCETO CD (D007)
# CD passa pela pre-etapa via 03b_planejar_pre_etapa_cd.py — D004 nao gera
# diffs CD aqui para evitar duplicacao com Onda 5.
if cid != 4 and (   # <-- D007: pula CD
    total_odoo > 0
    and total_inv > 0
    and not lotes_odoo_set.intersection(lotes_inv_set)
    and not inv_sem_lote
):
    ...
```

**E adicionar** ao final do `confrontar_company()`:
```python
# D007: CD nao gera diffs aqui — sera tratado por 03b_planejar_pre_etapa_cd.py
if cid == 4:
    return [], outliers  # so outliers do CD
```

---

## 7. `scripts/inventario_2026_05/04_propor_ajustes.py` — adicionar onda 5

### Mudanca em `determinar_onda()` (linha ~163):

**Antes**:
```python
return {
    'INDUSTRIALIZACAO_FB_LF': 1,
    ...
    'RENOMEAR_LOTE': 4,
    'SEM_ACAO': 0,
}.get(acao, 0)
```

**Depois**:
```python
return {
    'INDUSTRIALIZACAO_FB_LF': 1,
    ...
    'RENOMEAR_LOTE': 4,
    # D007: novas acoes Onda 5 (pre-etapa CD)
    'AJUSTE_CD_TRANSF_INTERNA_POS': 5,
    'AJUSTE_CD_TRANSF_INTERNA_NEG': 5,
    'AJUSTE_CD_POSITIVO_PURO': 5,
    # D007 futuro: Onda 6 (pre-etapa FB)
    'AJUSTE_FB_TRANSF_INTERNA_POS': 6,
    'AJUSTE_FB_TRANSF_INTERNA_NEG': 6,
    'AJUSTE_FB_POSITIVO_PURO': 6,
    'SEM_ACAO': 0,
}.get(acao, 0)
```

---

## 8. `app/odoo/CLAUDE.md` (modulo) — adicionar referencia

### Trecho a inserir na tabela "References" (final do arquivo):

```markdown
| Pre-etapa CD/FB (D007 — minimizar NFs inter-filial) | `docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md` |
```

---

## Resumo da integracao

Quando a outra sessao finalizar:

1. **Aplicar patches 3, 4, 5** (notas em D004/D005/D006) — 1 paragrafo cada
2. **Aplicar patches 6 e 7** (scripts 03 e 04) — modificacoes pequenas e cirurgicas
3. **Aplicar patches 1 e 2** (SOT + QUICK_START) — apenas adicao de secoes
4. **Aplicar patch 8** (CLAUDE.md modulo Odoo) — 1 linha
5. **Rodar pytest** — esperado: baseline + 12 novos da pre-etapa

**Nada removido**, **nada substituido em conteudo existente** — apenas
adicoes. Operacao de integracao em < 30 min.
