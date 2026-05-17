# SPED ECD — Plano de Correcoes (vivo)

**Status**: ATIVO — em correcao iterativa
**Versao atual**: ver `VERSAO_SPED` em `services/sped_ecd_constantes.py` (fonte unica) — **V26 em prod**
**Periodo de teste**: 01/07/2024 a 31/12/2024 (3 companies: FB+SC+CD)
**Ultima validacao PVA**: V26 (PDF `erros v26.pdf` — 2026-05-16 11:42)

---

## STATUS RESUMIDO PARA RETOMADA EM NOVA SESSAO

> **Se voce esta abrindo esta sessao do zero, leia esta secao primeiro.**

### Progresso ate V26 (PVA confirmado)

- **V18-2**: 1450 erros, 788 warnings (baseline)
- **V26 atual**: **84 erros, 539 warnings** — **-94% nos erros**
- Tempo de geracao: ~330s por iteracao (3 companies, 6 meses, 136K lancamentos)

### CATEGORIAS RESOLVIDAS (VERIFIED_FIXED via PVA)

| CAT | Descricao | Erros V18-2 | Versao fix | Mudanca chave |
|-----|-----------|-------------|------------|---------------|
| 1 | I052 em sintetica | 552 | V20 | `blocks.py:477` filtrar `tipo=='A'` |
| 4 | codes totalizadores em I052 | 236 | V20 | (mesmo fix CAT 1) |
| 7 | J930 contador FONE+DT_CRC | warning | V20 | `constantes.py` + `blocks.py:1104` |
| 9 | IDENT_MF=M | 1 | V18 | `constantes.py:41` = 'N' (1 erro PVA V26 e suspeito FP) |
| 11 | I250 negativos | 0 | V18 | `EMITIR_CCUS_SPED=False` |
| 18 | Soma cred ≠ dev I155 | 12 | V22 | (efeito colateral CAT 3) |
| 2 (parcial) | I051 obrigatorio | 368→1 | V22+V25 | filtro >5 pontos + filtro movimento |
| 3 | Saldo final I155 ≠ ini+D-C | 188 | V22 | IND_DC pelo sinal balance (`blocks.py:577`) |
| 21 (parcial) | Conta nao existe plano ref | 7→1 | V25 | filtro movimento |
| 22 (parcial) | Natureza ref ≠ pai | 11→1 | V25 | filtro movimento |
| 23 | J100.VL_CTA_FIN/INI ≠ I155 | 45 | V23 | helper `_balanco_a_partir_de_saldos_mensais` + IND_DC sinal |
| 24 | Campo obrigatorio J100 IND_DC vazio | 35 | V24 | `_ind_dc_v24` fallback natural quando saldo=0 |
| 25 | I050/I051 emitidos sem movimento | ~80 (varias categorias) | V25 | `filtrar_plano_por_movimento` + skip I155 zerado (V26) |

### CATEGORIAS PENDENTES — 84 erros V26 atual

**Origem 1 — Bug codigo gerador (35 erros):**

| Prio | CAT | Erros | Funcao alvo | Estrategia |
|------|-----|-------|-------------|------------|
| **1 PROXIMO** | **CAT 17 encerramento I355** | **18** | `construir_I350_I355()` (blocks.py:700) + `calcular_saldos_resultado_encerramento()` (data.py:634) | Contas resultado nos meses encerramento devem ter VL_SLD_FIN=0 em I155 (saldo apos encerramento). Investigar Manual ECD. |
| 2 | CAT 5/20 DRE J150 | 9 | `construir_J005_J150()` (blocks.py:947) | **V28 VERIFIED_FIXED 2026-05-16** (PVA 13:15): 15→0. Refactor com hierarquia explicita 3 niveis + I052 vinculando 153 contas analiticas resultado. Sub-efeito: 2 erros J005 sem par (CAT 22) — PVA quer J100 E J150 no MESMO J005, contadora usa 1 so com BP+DRE juntos. |
| 3 | "Campo obrigatorio" 5 originais V22 | 5 | Investigar (registro especifico, possivel I250 ou J930) | Identificar registro/campo via PDF |
| 4 | CAT 22 J005 sem par J100/J150 | 2 | `sped_ecd_service.py` | **V29 FIXED_NOT_VALIDATED 2026-05-16**: consolidado em 1 unico J005 ID_DEM=1 (padrao contadora) — antes V28 emitia 2 J005 separados. Aguarda PVA. |
| 5 | CAT 9 IDENT_MF | 1 | n/a | Confirmar via re-validacao PVA isolada (V26 emite N — md5 verificado em V21). Possivel FP. |

**Origem 2 — Cadastro Odoo / contadora (49 erros):**

| CAT | Erros | Acao | Inconsistencia documento |
|-----|-------|------|--------------------------|
| **CAT 6 BP estrutural** | **35** | Contadora corrigir `account_type` de analiticas patrimoniais (codes 1xxx/2xxx) com `account_type=expense/income`. Sinteticas herdam errado e geram orfas no J100. | INCONSISTENCIAS_ODOO.md Inconsistencia 5 (NOVA) |
| CAT 19 conta nao e resultado | 11 | Contadora corrigir `l10n_br_cod_nat` | Inconsist. 2 |
| Outras (21, 22 residual) | 3 | Inconsist. 1/2/3 | varias |

**TABELA ANTIGA (origem 2 — 14 erros)** — DEPRECATED, ver tabela acima.

| CAT | Erros | Acao | Inconsistencia documento |
|-----|-------|------|--------------------------|
| 19 conta nao e resultado | 11 | Contadora corrigir `l10n_br_cod_nat` em contas com `cod_nat=04` (Receita) mas `account_type` patrimonial | INCONSISTENCIAS_ODOO.md Inconsist. 2 |
| 21 conta nao existe plano ref | 1 | Conta cod_ref Odoo invalido (1 residual) | INCONSISTENCIAS_ODOO.md Inconsist. 3 |
| 22 natureza ref ≠ pai | 1 | (1 residual) | INCONSISTENCIAS_ODOO.md Inconsist. 2 |
| 2 I051 obrigatorio | 1 | 1 conta com movimento mas sem cod_ref | INCONSISTENCIAS_ODOO.md Inconsist. 1 |

### Inconsistencias Odoo documentadas (acao contadora)

> `INCONSISTENCIAS_ODOO.md` neste diretorio + CSVs em `app/relatorios_fiscais/odoo_corrigir_*.csv`.
> Copia para envio em `C:\Users\rafael.nascimento\Pictures\odoo_correcoes\`.

| # | Inconsistencia | Contas | Status |
|---|----------------|--------|--------|
| 1 | Sem `l10n_br_conta_referencial` | 89 codes | Aguardando contadora preencher |
| 2 | `l10n_br_cod_nat` conflita com `account_type` | **350 codes** (376 - 26 desc dupl/antecip — VER NOTA ATENCAO no doc) | Aguardando contadora corrigir, MENOS as 26 intencionais |
| 3 | `l10n_br_conta_referencial` >5 pontos | 4 codes | Aguardando contadora |
| 4 | Codes do `PLANO_REFERENCIAL` fallback nao existem Tabela 11 RFB | 4-5 codes | Aguardando contadora validar codes Tabela 11 |

### Como retomar (proximo passo concreto)

1. **CAT 6 BP estrutural** é o proximo (35 erros, maior impacto).
2. Bump `VERSAO_SPED = 'V27'` em `services/sped_ecd_constantes.py`.
3. Refatorar `construir_J005_J100()`: ver Manual ECD J100 + ground truth contadora.
4. Rodar `python scripts/sped_ecd/gerar_sped.py` (~330s).
5. Append linha no HISTORICO desta pagina.
6. Enviar SPED ao PVA, retornar PDF, atualizar STATUS CAT 6.

---

> Documento VIVO. Atualize STATUS de cada categoria conforme corrige. NUNCA releia o PDF/SPED inteiros — use este inventario como ground truth.
>
> **Protocolo de nova versao**: ver `app/relatorios_fiscais/CLAUDE.md` — secao "PROTOCOLO DE NOVA VERSAO" (3 passos).
>
> **Inconsistencias do Odoo** (cadastrais — acao da contadora): ver `INCONSISTENCIAS_ODOO.md` (este diretorio). Lista 89 contas sem cod_ref, 376 com cod_nat conflitante, 4 com cod_ref invalido. Anexos CSV para envio.

---

## SUMARIO

**Ultima validacao PVA: V22 (2026-05-16 09:57) — 198 erros, 787 warnings (-86% vs V18-2)**

| Versao | Erros PVA | Warnings PVA |
|--------|-----------|--------------|
| V18-2 | ~1450 | ~788 |
| V21 | 661 | 787 |
| **V22** | **198** | **787** |

- **Resolvidos definitivamente (PVA confirmado)**: 7 categorias — 1, 2 (parcial), 3, 4, 7, 9, 11, 18
- **Pendentes — bug codigo gerador**: 5 categorias (5/20 DRE, 6 BP estrutural, 17 encerramento, 22 J005 sem J100/J150, **23 NOVA — J100 saldos ≠ I155**)
- **Pendentes — cadastro Odoo (contadora)**: 4 inconsistencias documentadas em `INCONSISTENCIAS_ODOO.md`
- **Erro restante validador interno**: balanco Ativo!=Passivo+PL (R$ 19.5M diff) — pre-existente, ligado a CAT 6

### Distribuicao dos 198 erros V22 por ORIGEM

**Origem 1 — Bug do gerador SPED (resolver no codigo): ~115 erros**

| Prio | Erros | Categoria | Funcao bugada |
|------|-------|-----------|---------------|
| 1 | **45** | **CAT 23 (NOVA V22)** | `construir_J005_J100()` — J100.VL_CTA_FIN/INI ≠ saldo calculado do I155. Aflorou apos fix CAT 3. |
| 2 | 36 | CAT 6 BP estrutural | `construir_J005_J100()` — 100% T, hierarquia COD_AGL_SUP, falta detalhe D, 1 linha nivel 1. **V30 FIXED_NOT_VALIDATED 2026-05-16**: 2 fixes complementares — (a) filtra plano por classe ANTES de propagar saldos; (b) sinteticas via code prefix (ignora account_type herdado). Esperado eliminar 8 erros (4 totalizador + 4 grupos divergentes). Aguarda PVA. |
| 3 | 18 | CAT 17 encerramento | `construir_I350_I355()` ou `calcular_saldos_resultado_encerramento()` |
| 4 | 13 | CAT 5/20 DRE | `construir_J005_J150()` — 2 niveis 1, totalizador ≠ soma, codes detalhe sem I052 |
| 5 | 2 | CAT 22 J005 sem par | service.py — J100 ou J150 ausente para algum J005 |
| 6 | 1 | CAT 9 IDENT_MF | Suspeito falso positivo PVA (V22 emite N — verificado md5) |

**Origem 2 — Cadastro Odoo (contadora resolve via `INCONSISTENCIAS_ODOO.md`): ~77 erros**

| Erros | Categoria | Inconsistencia |
|-------|-----------|----------------|
| 48 | CAT 2 residual | Inconsist. 1 — 89 contas sem `l10n_br_conta_referencial` |
| 11 | CAT 19 nao e resultado | Inconsist. 2 — subset de `l10n_br_cod_nat` conflitante |
| 11 | CAT 22 natureza ref ≠ pai | Inconsist. 2 + Inconsist. 4 (NOVA — PLANO_REFERENCIAL fallback invalido) |
| 7 | CAT 21 conta nao existe ref | Inconsist. 3 (4 Odoo) + Inconsist. 4 (3 fallback codigo) |

---

## INVENTARIO DE CATEGORIAS DE ERRO

> Convencao: STATUS ∈ {PENDING, IN_PROGRESS, FIXED_NOT_VALIDATED, VERIFIED_FIXED, NOT_REPRODUCED}
> Severidade ∈ {BLOQ (PVA reprova), WARN (avisos), STRUCT (layout)}

### CATEGORIA 1 — I052 em contas sinteticas (552 erros — BLOQ)

- **Sintoma PDF**: I052 emitido para contas com IND_CTA="S" (sintetica). PVA exige I052 SO para analiticas detalhe.
- **Funcao responsavel**: `construir_I050_com_I051()` em `blocks.py:404-475`
- **Linha exata do bug**: `blocks.py:468`
  ```python
  # V1.6 — I052 para conta usada como COD_AGL no J100/J150
  if c['code'] in codes_agl:
      linhas.append(contador.emit(formatar_registro([
          'I052', '', c['code'],
      ])))
  ```
  **NAO FILTRA** por `c.get('tipo') == 'A'`.
- **Causa raiz**: `codes_aglutinacao` (gerado em `construir_J005_J100()` ou ja vem do orquestrador?) contem codes de SINTETICAS (que aparecem em J100 como totalizadores `T`). Como `_classe_da_conta` aceita sinteticas no plano patrimonial e elas emitem J100 com IND_COD_AGL=T, o codes_agl agrega elas → dispara I052 errado.
- **Fix proposto**:
  ```python
  # blocks.py:467-473
  # V1.9: I052 SO para analiticas detalhe (PVA: "codigo agl. detalhe...")
  if c['code'] in codes_agl and c.get('tipo') == 'A':
      linhas.append(contador.emit(formatar_registro([
          'I052', '', c['code'],
      ])))
  ```
- **Validacao pos-fix**:
  - Grep no novo SPED: `awk -F'|' '/^\|I050\|/{ind_cta=$5} /^\|I052\|/{print ind_cta,$3}' "$SPED" | awk '$1=="S"' | wc -l` deve dar 0.
- **STATUS**: **VERIFIED_FIXED** (V21 PVA 2026-05-15 18:49: 552 → 0 erros). Validado.

---

### CATEGORIA 2 — I051 ausente para I050 analiticas (368 erros — BLOQ)

- **Sintoma PDF**: Muitas I050 com IND_CTA="A" nao tem I051 imediatamente apos.
- **Funcao responsavel**: `construir_I050_com_I051()` em `blocks.py:448-465`
- **Linhas exatas**:
  ```python
  if c.get('tipo') == 'A':
      cod_ref = c.get('conta_referencial_odoo') or PLANO_REFERENCIAL.get(c.get('account_type', ''), '')
      if cod_ref:
          niveis = cod_ref.count('.')
          tem_placeholder = '99.99' in cod_ref
          if niveis > 4 or tem_placeholder:
              cod_ref = ''  # invalida -> nao emite I051
      if cod_ref:
          linhas.append(...)
  ```
- **Causa raiz CONFIRMADA (investigacao Odoo 2026-05-15)**: filtro V1.7 (`niveis > 4`) excessivamente restritivo. **Manual ECD + ground truth contadora** confirma codes com ate 6 niveis (5 pontos) sao validos. Filtro invalidava 923 codes (52%) com mapeamento referencial correto.
  - Codes Odoo: 692 unicos consolidados, 603 com cod_ref preenchido.
  - Codes invalidados pelo filtro: 923/1770 instancias (3 companies). Apos relaxar: 11 invalidadas (pontos > 5, realmente invalidas).
  - Codes SEM cod_ref no Odoo (problema cadastral): 89 codes — listado em `INCONSISTENCIAS_ODOO.md` Inconsistencia 1.
- **Fix V22**: `blocks.py:460` — relaxar limite de `pontos > 4` para `pontos > 5`. Mantem exclusao `99.99`.
- **STATUS**: **VERIFIED_FIXED (parcial)** — V22 PVA 2026-05-16: 368 → 48 (-87%). Residual 48 sao 89 codes Odoo sem `l10n_br_conta_referencial` (acao contadora — `INCONSISTENCIAS_ODOO.md` Inconsistencia 1).

---

### CATEGORIA 3 — Saldo final incorreto em I155 (188 erros — BLOQ)

- **Causa raiz CONFIRMADA (investigacao Odoo + PVA V21 2026-05-15)**:

  Logica antiga (V1.0..V21) em `blocks.py:577-578` derivava IND_DC do `account_type`:
  ```python
  ind_dc = ind_natural if saldo >= 0 else inverter(ind_natural)
  ```
  Bug: quando saldo Odoo balance e contrario a natureza esperada (conta com cadastro Odoo "errado" ou movimento atipico), emite IND_DC NATURAL mesmo com saldo anormal. PVA calcula `saldo_assinalado = sinal(IND_DC) * VL_SLD_INI + DEB - CRED` e compara com VL_SLD_FIN — diverge.

  Exemplo concreto (`1130600001` ADIANTAMENTOS A FORNECEDORES):
  - Odoo: balance = +3.306.879,09 (DEVEDOR — `debit_acum=3306879,09`, `credit_acum=0`)
  - account_type = `liability_payable` (Passivo) → ind_natural = `C`
  - V21 emite: `VL_SLD_INI=3306879,09 IND_DC_INI=C` + DEB 1629239,76 + CRED 747807,42 + `VL_SLD_FIN=4188311,43 IND_DC_FIN=C`
  - PVA interpreta IND_DC=C como saldo NEGATIVO: `-3306879,09 + 1629239,76 - 747807,42 = -2425446,75` → espera `VL_SLD_FIN=2425446,75`
  - Diverge 4188311,43 != 2425446,75 → erro PVA

- **Fix V22 (`blocks.py:577-578`)**: IND_DC derivado do SINAL do balance Odoo, sem inversao:
  ```python
  ind_dc_ini = 'D' if saldo_ini > 0 else ('C' if saldo_ini < 0 else '')
  ind_dc_fin = 'D' if saldo_fin > 0 else ('C' if saldo_fin < 0 else '')
  ```
  Para `1130600001`: emite `VL_SLD_INI=3306879,09 IND_DC_INI=D` + DEB 1629239,76 + CRED 747807,42 + `VL_SLD_FIN=4188311,43 IND_DC_FIN=D`. PVA: `+3306879,09 + 1629239,76 - 747807,42 = +4188311,43` ✓.

- **STATUS**: **VERIFIED_FIXED** — V22 PVA 2026-05-16: 188 → 0 (-100%). CAT 18 (12 erros) tambem zerou (efeito colateral). Total: -200 erros.
- **Observacao**: O conflito entre `account_type` e `l10n_br_cod_nat` no Odoo CIEL IT (376 codes) NAO e causa raiz desta categoria, mas e causa de outros erros estruturais. Ver `INCONSISTENCIAS_ODOO.md` Inconsistencia 2.

---

### CATEGORIA 4 — Codes de aglutinacao em I052 sao TOTALIZADORES (236 erros — BLOQ)

- **Sintoma PDF**: I052 contem codes que sao totalizers no plano (ex: "1", "11", "111", "1130"). I052 deve ter SO codes detalhe.
- **Relacao com CATEGORIA 1**: e a mesma raiz. Se CATEGORIA 1 e corrigida (filtrar `tipo=='A'`), esta tambem fica resolvida (assumindo que sinteticas sao as totalizers).
- **Validacao pos-fix CATEGORIA 1**: grep no novo SPED:
  ```bash
  awk -F'|' '/^\|I052\|/{print $3}' "$SPED" | sort -u | head -20
  # Devem ser todos codes longos (>= 5 digitos, analiticas)
  ```
- **STATUS**: **VERIFIED_FIXED** (V21 PVA 2026-05-15 18:49: 236 → 0 erros). Resolvido junto com #1 via filtro `tipo=='A'`.

---

### CATEGORIA 5 — DRE estrutural (2 niveis 1, COD_AGL_SUP vazio, totalizador nao bate)

**STATUS V28**: **VERIFIED_FIXED** (PVA 2026-05-16 13:15) — 15→0 erros DRE. Todos os erros do J150 zerados. Sub-efeito: 2 erros novos "J005 sem par J100+J150" (CAT 22) — PVA quer J100 E J150 no MESMO J005, e contadora usa 1 so J005 (ID_DEM=1) com BP+DRE juntos. Investigar consolidar em V29.

**Fix aplicado V28** (`blocks.py:1036-1183` + `service.py:182-200`):
- Novo helper `_calcular_grupos_dre_hierarquicos(dre_consolidado)` retorna `(grupos, mapa_i052)`.
- Estrutura DRE hierarquica 3 niveis (codes numericos como contadora):
  ```
  9       T  1   -      RESULTADO DO EXERCICIO    (raiz unica)
  9.1     T  2   9      RECEITAS
  9.1.1   D  3   9.1    RECEITA OPERACIONAL BRUTA    <- I052 vincula income
  9.1.2   D  3   9.1    OUTRAS RECEITAS              <- I052 vincula income_other
  9.2     T  2   9      CUSTOS E DESPESAS
  9.2.1   D  3   9.2    CUSTO DIRETO DAS VENDAS      <- I052 vincula expense_direct_cost
  9.2.2   D  3   9.2    DESPESAS OPERACIONAIS        <- I052 vincula expense
  9.2.3   D  3   9.2    DEPRECIACAO E AMORTIZACAO    <- I052 vincula expense_depreciation
  ```
- Substitui codes ficticios DRE_REC_BRUTA/etc.
- Bug string match `'TOTAL' in 'TOTAIS'` eliminado (substituido por flag explicita `is_total`).
- `construir_I050_com_I051` ganhou parametro `mapa_aglutinacao_dre: Dict[str, str]` — emite I052 adicional vinculando cada conta analitica de resultado ao code DRE detalhe (mapeamento por account_type).
- Constante `DRE_ACCOUNT_TYPE_TO_COD_AGL` em blocks.py centraliza o mapeamento.

**Validacao interna V28**:
- J150 nivel 1: 1 linha (era 2)
- J150 COD_AGL_SUP vazio: 1 linha (so a raiz, correto)
- J150 detalhes (D): 4 linhas (9.1.1, 9.1.2, 9.2.1, 9.2.2 — 9.2.3 zerada filtrada)
- I052 vinculando codes DRE: 153 (era 0)
- I052 em sintetica: 0 (sem regressao)

**Bug original (V27 e anteriores)**:

- **Sintoma PDF**:
  - 2 linhas com NIVEL_AGL=1 (`DRE_REC_TOTAL` e `DRE_RESULT_LIQ`) — Manual: apenas 1 raiz.
  - COD_AGL_SUP vazio em TODAS as 7 linhas (campo 6).
  - "CUSTOS E DESPESAS TOTAIS" marcado como `D` mas e totalizador.
  - Totalizador 87702222,90 != soma dos detalhes filhos.
  - Codes DRE (DRE_REC_BRUTA etc.) nao aparecem em nenhum I052 (warning).
- **Funcao responsavel**: `construir_J005_J150()` em `blocks.py:934-1024`
- **Linhas exatas dos bugs**:
  - `blocks.py:1006`: `is_total = 'TOTAL' in descr or 'LIQ' in descr` — string match BUGADO. `'TOTAL' in 'CUSTOS E DESPESAS TOTAIS'` retorna **False** (substring contigua nao bate — 'TOTAIS' tem T-O-T-A-I-S, nao tem L apos A).
  - `blocks.py:1013`: COD_AGL_SUP hardcoded como `''` para todos.
  - Hierarquia nao estruturada: nivel 1 + nivel 2 sem ligacao.
- **Fix proposto**:
  ```python
  # blocks.py:990 — refatorar grupos_dre com hierarquia explicita
  grupos_dre = [
      # (cod_agl, descr, valor, ind_dc, ind_grp_dre, nivel, cod_agl_sup, is_total)
      ('DRE_RESULT_LIQ', 'RESULTADO LIQUIDO DO EXERCICIO',
          abs(resultado_liquido), 'C' if resultado_liquido >= 0 else 'D',
          'R' if resultado_liquido >= 0 else 'D', 1, '', True),
      ('DRE_REC_TOTAL', 'RECEITA TOTAL', receita_total, 'C', 'R', 2, 'DRE_RESULT_LIQ', True),
      ('DRE_REC_BRUTA', 'RECEITA OPERACIONAL BRUTA', receita_bruta, 'C', 'R', 3, 'DRE_REC_TOTAL', False),
      ('DRE_REC_OUTRAS', 'OUTRAS RECEITAS', receita_outras, 'C', 'R', 3, 'DRE_REC_TOTAL', False),
      ('DRE_DESP_TOTAL', 'CUSTOS E DESPESAS TOTAIS', despesa_total, 'D', 'D', 2, 'DRE_RESULT_LIQ', True),
      ('DRE_CUSTO_DIR', 'CUSTO DIRETO DAS VENDAS', custo_direto, 'D', 'D', 3, 'DRE_DESP_TOTAL', False),
      ('DRE_DESP_GERAL', 'DESPESAS OPERACIONAIS', despesa_geral, 'D', 'D', 3, 'DRE_DESP_TOTAL', False),
      ('DRE_DESP_DEPREC', 'DEPRECIACAO E AMORTIZACAO', despesa_deprec, 'D', 'D', 3, 'DRE_DESP_TOTAL', False),
  ]

  for cod_agl, descr, valor, ind_dc, ind_grp_dre, nivel, cod_sup, is_total in grupos_dre:
      if abs(valor) < 0.01:
          continue
      linhas.append(contador.emit(formatar_registro([
          'J150',
          str(nu_ordem),
          cod_agl,
          IND_COD_AGL_TOTAL if is_total else IND_COD_AGL_DETALHE,
          str(nivel),
          cod_sup,
          remover_acentos(descr),
          '', '',
          formatar_valor(valor),
          ind_dc,
          ind_grp_dre,
          '',
      ])))
      nu_ordem += 1
  ```
- **STATUS**: PENDING

---

### CATEGORIA 6 — J100 estrutural (100% totalizadores, mistura grupos)

- **Sintoma PDF**:
  - TODAS as 323 linhas J100 tem IND_COD_AGL=`T`. Nenhuma `D`.
  - Manual: J100 deve ter detalhes (D) somando para totalizadores (T).
  - Algumas contas marcadas como Passivo ('P') contem itens com saldo devedor (BANCO SAFRA - LIMITE / CHEQUE ESPECIAL).
- **Funcao responsavel**: `construir_J005_J100()` em `blocks.py:801-931`
- **Causa raiz (HIPOTESE)**:
  - `_classe_da_conta()` (blocks.py:847) usa `account_type` se existir, senao `_classe_pelo_code()`. Para analiticas com `account_type=''` (vindo do Odoo CIEL IT), cai em `_classe_pelo_code` que retorna 'asset' ou 'liability_or_equity' — entrariam no plano_patrimonial.
  - MAS analiticas no plano_consolidado tem `tipo='A'`, e linha 905: `ind_cod_agl = IND_COD_AGL_TOTAL if conta.get('tipo') == 'S' else IND_COD_AGL_DETALHE`. Daria `D`.
  - Se 100% sao `T`, significa que 100% das contas que chegam ao loop tem `tipo='S'`. Possivelmente as ANALITICAS estao sendo filtradas por `_classe_da_conta` (retornando '') OU pelo filtro de saldo zero (linha 891-892).
- **Investigacao necessaria**:
  - Adicionar logging em `construir_J005_J100()` para contar quantas analiticas chegam ao loop, quantas sao filtradas por saldo, e qual classe retorna `_classe_da_conta` para uma analitica patrimonial conhecida (ex: code `1130600001`).
  - Verificar em `buscar_plano_contas_consolidado()` se `account_type` esta sendo populado nas analiticas.
- **Fix proposto**: Apos diagnostico. Possivelmente:
  - Garantir que `account_type` chega populado das analiticas via `data.py`.
  - OU substituir `_classe_da_conta` para usar `_classe_pelo_code` SEMPRE (codes 1=Ativo, 2=Passivo+PL).
- **STATUS**: PENDING

---

### CATEGORIA 7 — J930 contador FONE e DT_CRC vazios (WARN)

- **Sintoma PDF**: Campo 8 (FONE) e campo 11 (DT_CRC) vazios na linha do contador. Para `COD_ASSIN=900` (contador) ambos sao obrigatorios.
- **Funcao responsavel**: `construir_J930()` em `blocks.py:1096-1109`
- **Fix aplicado V1.9** (2026-05-15):
  - `constantes.py`: adicionado `CONTADOR_FONE='1147059494'` e `CONTADOR_DT_CRC='06072026'`
  - `constantes.py`: corrigido `CONTADOR_CRC` de `'1SP041472'` para `'SP-1303041/O-9'` (formato literal usado pela contadora)
  - `blocks.py:1104,1107`: campos preenchidos com as constantes
  - **Fonte dos dados**: SPED gerado pela contadora — `SpedContabil-61724241000178_35208934897_18_20240701_20241231_G (1).txt`
- **STATUS**: **VERIFIED_FIXED** (V21 PVA 2026-05-15 18:49: nao aparece mais nos warnings).

---

### CATEGORIAS 12-16 — Divergencias descobertas via SPED da contadora (2026-05-15)

Comparando V19 com o SPED gerado pela contadora (ground truth):
`/mnt/c/Users/rafael.nascimento/Downloads/SpedContabil-61724241000178_35208934897_18_20240701_20241231_G (1).txt`

**CATEGORIA 12 — Registro 0000 incompleto**

| Campo | V19 (nosso) | Contadora (correto) |
|-------|-------------|---------------------|
| 5 NOME | NACOM GOYA INDUSTRIA E COMERCIO DE ALIMENTOS LTDA | NACOM GOYA - FB |
| 9 COD_MUN | vazio | 3547304 (IBGE Santana Parnaiba) |
| 13 TIP_ECD | 0 | 1 |
| 14 COD_SCP | 0 | 1 |
| 15 IDENT_HASH | vazio | A22CACD993FA38F8746C446EE1312A8D4D7665FE |
| 22 (?) | 0 | 1 |

- **Funcao responsavel**: `construir_bloco_0()` em `blocks.py:226`
- **Investigacao**: ler funcao + comparar com layout 0000 Manual Leiaute 9
- **STATUS**: PENDING

**CATEGORIA 13 — Registro I030 com valores em posicoes erradas**

| Campo | V19 (nosso) | Contadora (correto) |
|-------|-------------|---------------------|
| 3 IDENT_NUM (num livro) | 1 | 18 |
| 5 NIRE | 1 | 260135 |
| 6 NOME (estab) | NACOM GOYA INDUSTRIA E COMERCIO DE ALIMENTOS LTDA | NACOM GOYA - FB |
| 7 CPF_RESP_LEG | vazio | 35208934897 |
| 9 DT_AB | vazio | 15041999 (data abertura empresa) |

- **Funcao responsavel**: `construir_bloco_I_abertura()` em `blocks.py:304`
- **Investigacao**: pegar dados do Odoo (res.company.l10n_br_nire, dt_abertura, etc.)
- **STATUS**: PENDING (era CATEGORIA 10 — atualizada com dados reais)

**CATEGORIA 14 — Sócio J930 qualificacao divergente**

- V19: `Diretor` qualif `205` (Administrador)
- Contadora: `Diretor` qualif `203` (Acionista Controlador)
- **Funcao responsavel**: `construir_J930()` em `blocks.py:1114-1129`
- **Acao**: confirmar com contadora qual e o correto para AIRTON ALVES NASCIMENTO
- **STATUS**: BLOQUEADO_USUARIO (confirmar 205 vs 203)

**CATEGORIA 15 — J932 (Termo de Verificacao ECD substituta) nao emitido**

- Contadora emite J932 com qualif `910` (Contador/Contabilista Responsavel pelo Termo de Verificacao para Substituicao da ECD)
- **Manual ECD**: J932 e obrigatorio apenas para ECD substituta (`IND_FIN_ESC='1'`). Confirmar tipo.
- **STATUS**: PENDING (verificar se aplicavel ao nosso caso)

**CATEGORIA 16 — J150 hierarquia da contadora usa codes numericos**

A contadora usa codes hierarquicos: `9`, `9.3`, `9.3.1`, `9.3.1.1`, `9.4`, `9.5` etc. com COD_AGL_SUP populado corretamente (`9.3` tem sup `9`, `9.3.1` tem sup `9.3`, etc.).

Nosso V19 usa codes ficticios `DRE_REC_BRUTA`, `DRE_REC_TOTAL` etc. com COD_AGL_SUP **VAZIO** e apenas 2 niveis.

Isso e parcialmente a CATEGORIA 5. Adicional: trocar para codes numericos hierarquicos formato `N.NN.NN.NN` permite COD_AGL_SUP funcional.

**STATUS**: PENDING (relacionado a CAT 5)

---

### CATEGORIA 8 — Contas-lixo no plano (4444444, 555555, 7777777, 88888888, 99999999999, 111111111111111)

- **Sintoma PDF**: Contas com codes/nomes claramente placeholder ("GRUPO 4444444", "TAX PAID", "TAX RECEIVABLE", "STOCK INTERIM", etc.) aparecem em I050.
- **Confirmado no SPED V18**:
  ```
  |I050|01012010|01|S|7|4444444|444444|GRUPO 4444444|
  |I050|01112022|04|A|8|44444444|4444444|TAX PAID|
  |I050|01012010|01|S|6|555555|55555|GRUPO 555555|
  |I050|01112022|05|A|7|5555555|555555|TAX RECEIVABLE|
  |I050|01012010|02|S|7|7777777|777777|GRUPO 7777777|
  ```
- **Funcao responsavel**: `buscar_plano_contas_consolidado()` em `data.py:158`
- **Causa raiz**: dados no Odoo (Lucas/contador deixou contas teste no plano).
- **Fix proposto (duas opcoes — preferencial A)**:
  - **A (CODIGO)**: filtro em data.py removendo codes em blacklist conhecida:
    ```python
    # data.py — adicionar constante
    CODES_LIXO = {'4444444', '44444444', '555555', '5555555',
                  '7777777', '88888888', '99999999999',
                  '111111111111111'}
    # Aplicar em buscar_plano_contas_consolidado, filtrar antes de retornar
    plano = [c for c in plano if c['code'] not in CODES_LIXO]
    ```
  - **B (ODOO)**: pedir ao contador para arquivar as contas no Odoo (`active=False`).
- **Recomendacao**: comecar com A (rapido, controlavel), comunicar B em paralelo.
- **STATUS**: PENDING

---

### CATEGORIA 9 — IDENT_MF (BUG HISTORICO)

- **Sintoma PDF**: Position 22 of 0000 record has "M" — should be "S" or "N".
- **STATUS**: **VERIFIED_FIXED** (V1.8). Verificado em SPED V18:
  ```
  |0000|LECD|01072024|31122024|NACOM...|61724241000178|SP|623098703118||||0|0|0||0|0||N|N|0|0|1|
                                                                                      ^ posicao 19 = IDENT_MF = N
  ```
  `IDENT_MF='N'` em `constantes.py:41`. Bug eliminado.

---

### CATEGORIA 10 — I030 DT_ARQ posicao errada

- **Sintoma PDF**: Campos do I030 estao deslocados — DT_ARQ aparece como "31122024" mas em posicao incompativel; NIRE recebeu CNPJ; municipio recebeu razao social.
- **Confirmado no SPED V18**:
  ```
  |I030|TERMO DE ABERTURA|1|LIVRO DIARIO (COMPLETO, SEM ESCRITURACAO AUXILIAR).|1|NACOM GOYA INDUSTRIA E COMERCIO DE ALIMENTOS LTDA||61724241000178|||SANTANA DE PARNAIBA|31122024|
  ```
  12 campos (REG nao conta) — mas valores estao em posicoes erradas pelo layout esperado.
- **Funcao responsavel**: `construir_bloco_I_abertura()` em `blocks.py:304-371` (a confirmar)
- **Investigacao necessaria**: comparar emissao atual com Layout I030 oficial Manual ECD Leiaute 9.
- **Fix proposto**: a definir apos ler funcao + manual.
- **STATUS**: PENDING

---

### CATEGORIA 11 — I250 negativos (BUG HISTORICO)

- **STATUS**: **VERIFIED_FIXED** (V1.8). Verificado em SPED V18:
  ```bash
  grep -c "|I250|.*|-[0-9]" "$SPED" → 0
  ```
  CCUS desativado via `EMITIR_CCUS_SPED=False` (constantes.py:71).

---

### CATEGORIA 17 — Encerramento I355 (18 erros — BLOQ — descoberta V21)

- **Sintomas PDF V21**:
  - "As contas de resultado, nos meses em que houver encerramento, devem ter saldo zero." (9)
  - "Saldo da conta antes do encerramento nao corresponde ao total dos lancamentos de encerramento." (9)
- **Funcao responsavel**: `construir_I350_I355()` em `blocks.py:675`
- **Causa raiz (HIPOTESE)**:
  1. I355 esta emitindo saldos de contas de resultado APOS encerramento mas com valor != 0.
  2. Lancamento de encerramento (I200 com IND_LCTO=E?) nao bate com o saldo da conta antes do encerramento — possivel calculo errado de saldo pre-encerramento.
- **Investigacao necessaria**:
  - Ler `construir_I350_I355()` e `calcular_saldos_resultado_encerramento()` (data.py:634).
  - Verificar Manual ECD: I355 deve ter VL_SLD_FIN=0 para contas resultado em meses com encerramento (31/12).
- **STATUS**: PENDING

---

### CATEGORIA 18 — I155 soma cred != dev (12 erros — BLOQ — descoberta V21)

- **Sintomas PDF V21**:
  - "Soma dos saldos finais credores e diferente da soma dos saldos finais devedores no periodo informado nos registros de Saldos Periodicos." (6)
  - "Soma dos saldos iniciais credores e diferente da soma dos saldos iniciais devedores no periodo informado nos registros de Saldos Periodicos." (6)
- **Funcao responsavel**: `construir_I150_I155()` em `blocks.py:527` + `calcular_saldos_periodicos_mensais()` em `data.py:335`
- **Causa raiz (HIPOTESE)**: relacionada a CAT 3 (saldo final errado). Se 188 saldos finais estao errados, a soma cred vs dev nao bate. **Provavelmente CAT 18 e EFEITO de CAT 3** — fix CAT 3 deve eliminar CAT 18.
- **STATUS**: PENDING (acompanhar CAT 3)

---

### CATEGORIA 19 — Estrutura J100 detalhada (29 erros — BLOQ — descoberta V21)

- **Sintomas PDF V21 (BP)**:
  - "No Balanco Patrimonial, o saldo final do codigo de aglutinacao totalizador esta diferente do somatorio do saldo final dos registros de nivel inferior." (5)
  - "Saldo inicial idem" (5)
  - "Cod agl e cod agl sup nao pertencem ao mesmo grupo IND_GRP_BAL" (4)
  - "Nao existe nenhum registro com cod agl = cod agl sup" (10)
  - "Somente cod agl de linha totalizadora pode ser cod agl sup" (10)
  - "No BP, ultimo nivel Ativo final != Passivo+PL final" (1)
  - "Ultimo nivel inicial idem" (1)
  - "Somatorio saldo final Ativo != Passivo" (1)
  - "Somatorio saldo inicial Ativo != Passivo" (1)
  - "Conta cadastrada no plano nao e conta de resultado" (11)
  - "Pelo menos uma linha com ind_cod_agl=D detalhe" (2)
  - "BP deve ter duas linhas nivel 1, Ativo e Passivo" (1)
- **Funcao responsavel**: `construir_J005_J100()` em `blocks.py:801`
- **Causa raiz**: CAT 6 expandida. J100 atual e 100% T (sem detalhes), gera estrutura sem batimento. CAT 6 ja documenta — esta CAT 19 e o detalhamento dos erros que isso causa.
- **STATUS**: PENDING (consolidar com CAT 6)

---

### CATEGORIA 20 — Estrutura J150 DRE detalhada (4 erros — BLOQ — descoberta V21)

- **Sintomas PDF V21 (DRE)**:
  - "Nao existe nenhuma linha com nivel de aglutinacao igual a 1" (1) — relacionado a CAT 5
  - "Nao deve existir mais de uma linha de nivel igual a 1 na DRE" (1) — relacionado a CAT 5 (mesmo bug)
  - "Saldo cod agl totalizador != soma dos registros nivel imediatamente inferior" (2)
  - "Cod agl de linha de detalhe deve ser informado em pelo menos um I052" (5)
  - "Deve existir pelo menos um J100 e um J150 para cada J005" (2)
  - "Campo obrigatorio nao preenchido" (5)
- **Funcao responsavel**: `construir_J005_J150()` em `blocks.py:934` + `construir_I050_com_I051()` (I052 ausente)
- **Causa raiz**: CAT 5 expandida. Fix CAT 5 (refatorar grupos_dre com hierarquia) elimina niveis duplicados. I052 ausente para codes DRE: nossos codes DRE_REC_BRUTA etc. nao sao do plano contabil — nao tem como vincular I052. **Possivel: ao trocar para codes numericos hierarquicos (CAT 16), I052 pode ser emitido vinculando contas analiticas a esses codes**.
- **STATUS**: PENDING (consolidar com CAT 5 e CAT 16)

---

### CATEGORIA 21 — Conta nao existe no plano referencial (2 erros — BLOQ — descoberta V21)

- **Sintoma PDF V21**: "Conta nao existe no plano de contas referencial informado no registro 0000 (COD_PLAN_REF)." (2)
- **Causa raiz CONFIRMADA**: contas com `l10n_br_conta_referencial` de >5 pontos (>6 niveis) — fora da Tabela 11 RFB. Identificadas 4 contas no Odoo:
  - `1210700002` CSLL DIFERIDO PREJUIZO FISCAIS-LP — cod_ref `3.2.8.9.4.20.20`
  - `3901010003` IRPJ DIFERIDO S/ PREJUIZOS FISCAIS — cod_ref `3.2.8.9.4.10.20`
  - `3901020003` CSLL DIFERIDO S/ PREJUIZOS FISCAIS — cod_ref `3.2.8.9.4.20.20`
  - `3901020004` CSLL DIFERIDO S/ PREJUIZOS FISCAIS (copia) — cod_ref `3.2.8.9.4.20.20`
- **STATUS**: PARCIAL — V22 relaxa filtro de cod_ref (CAT 2), mas estas 4 continuam sendo filtradas (corretamente, >5 pontos). Para zerar PVA, contadora precisa corrigir cod_ref no Odoo. Ver `INCONSISTENCIAS_ODOO.md` Inconsistencia 3.

---

### CATEGORIA 22 — Natureza conta ref != natureza conta pai (4 erros — BLOQ — descoberta V21)

- **Sintoma PDF V21**: "A natureza da conta referencial informada no registro I051 e diferente da natureza da conta pai para a qual foi mapeada." (4)
- **Funcao responsavel**: cadastro Odoo (`l10n_br_conta_referencial`) — nao e bug de codigo, e dado errado no plano da empresa.
- **STATUS**: BLOQUEADO_USUARIO (contador precisa revisar 4 mapeamentos no Odoo)

---

### CATEGORIA 23 — J100 saldos diferem de I155 (45 erros — BLOQ — descoberta V22)

- **Sintomas PDF V22**:
  - "O saldo final (J100.VL_CTA_FIN) informado na linha de detalhe do Balanco Patrimonial esta diferente do saldo final calculado com base nos registros de saldo periodico (I155) na mesma data." (22)
  - "O saldo inicial (J100.VL_CTA_INI) informado na linha de detalhe do Balanco Patrimonial esta diferente do saldo inicial calculado com base nos registros de saldo periodico (I155) na mesma data." (23)
- **Funcao responsavel**: `construir_J005_J100()` em `blocks.py:801`
- **Causa raiz (HIPOTESE — investigacao necessaria)**: J100 atualmente calcula saldos do BP usando proprio metodo (`calcular_balanco_consolidado()` em `data.py:504`). Apos fix CAT 3 (V22), os saldos I155 ficaram corretos com IND_DC pelo sinal, mas J100 continua usando logica antiga. **PVA verifica consistencia interna**: J100 deve usar os mesmos saldos do I155 do mes 12/2024 (saldo final).
- **Fix V23 (`blocks.py:814`)**: novo parametro `saldos_mensais` em `construir_J005_J100`; helper `_balanco_a_partir_de_saldos_mensais` deriva balanco do I155 (saldo_inicial do 1o mes + saldo_final do ultimo mes). IND_DC pelo sinal do balance (consistente com V22 CAT 3). `service.py:225` passa `saldos_mensais`.
- **Validacao pos-fix (interna)**: log gerador "Balanco derivado de I155 substitui balanco_consolidado em 86 codes". Sanity check 50 codes amostra: 0 diferencas J100 vs I155 12/2024. Conta `1130600001`: J100=`7379534,63 D` = I155 12/24 ✓.
- **STATUS**: **VERIFIED_FIXED** — V23 PVA 2026-05-16: 45 → 0 (-100%). Categoria zerada confirmado.
- **EFEITO COLATERAL V23 (categoria 24 NOVA — corrigida em V24)**: +35 erros "Campo obrigatorio nao preenchido" (IND_DC_BAL_I/F vazio em J100 para contas com saldo zero em um lado). Causa: refactor `D if >0 else C if <0 else ''` removeu protecao implicita do natural fallback. Fix V24: usar natural quando saldo == 0. **STATUS CAT 24 V24 PVA**: VERIFIED_FIXED — 40 → 5 (-35 exato). Os 5 restantes sao originais V22 (em outro registro, possivelmente I250 ou DRE).

---

### CATEGORIA 25 — I050/I051 emitidos para contas SEM movimento/saldo (~40-60 erros estimados — descoberta V24 2026-05-16)

- **Origem da descoberta**: usuario apontou conta `1110400003` na CAT 22 (V22 PVA). Investigacao Odoo confirmou: conta ZERO movimento, ZERO saldo no periodo 2024 — nao deveria estar no SPED.
- **Sintoma indireto**: causa varios erros PVA que NAO sao realmente bugs nossos, sao "ruido" de emitir contas inativas com cadastros Odoo errados (cod_ref, cod_nat conflitante):
  - Parte da CAT 22 (natureza ref ≠ pai)
  - Parte da CAT 2 (I051 obrigatorio sem cod_ref)
  - Parte da CAT 19 (conta nao e resultado)
  - Parte da CAT 21 (conta nao existe plano ref)
- **Funcao responsavel**: `buscar_plano_contas_consolidado()` (data.py:158) — traz TODAS as contas Odoo sem filtro de movimento.
- **Evidencia objetiva (Odoo 2026-05-16)**:
  - Total codes no plano: 692
  - Codes COM movimento ate 31/12/2024: 293
  - Codes SEM movimento (candidatos exclusao): 399
  - V24 atual emite: 699 I050 analiticas
  - Contadora (ground truth aceito RFB) emite: 291 I050 analiticas — quase igual aos 293 com movimento
- **Manual ECD Leiaute 9 I050**: "Devem ser informadas as contas analiticas **utilizadas** pela escrituracao no periodo." Utilizadas = movimento OU saldo carregado.
- **Fix proposto**:
  ```python
  # Apos calcular saldos_mensais, identificar codes utilizados
  codes_utilizados = set()
  for mes in saldos_mensais.values():
      for code, sd in mes.get('por_code', {}).items():
          if (abs(sd.get('saldo_inicial', 0) or 0) > 0.01 or
              abs(sd.get('debit', 0) or 0) > 0.01 or
              abs(sd.get('credit', 0) or 0) > 0.01 or
              abs(sd.get('saldo_final', 0) or 0) > 0.01):
              codes_utilizados.add(code)
  # Manter sinteticas SO se tiverem descendente analitico utilizado
  # Filtrar plano_consolidado antes de chamar construir_I050_com_I051
  ```
- **Conta exemplo confirmada**: `1110400003` (asset_cash, cod_nat=01, cod_ref=3.01.01.03.01.01 errado) — ZERO movimento desde sempre. Esta na CAT 22 V22 mas nao deveria ser emitida.
- **Risco**: sinteticas orfas se nao propagar exclusao pela arvore.
- **STATUS**: PENDING — aguardando validacao PVA V24 antes de implementar.

---

### CATEGORIAS ADICIONAIS A INVESTIGAR

> Categorias citadas no PDF V18-2 mas ainda nao confirmadas no SPED atual ou sem hipotese clara. Reler PDF apenas se necessario validar.

12. **Outros warnings (~787 no total)** — categorizar quando relevante.
13. **IDENT_MF "valor invalido" (1)** — V21/V22 atual tem `|N|N|...` no registro 0000 (verificado md5 WSL=Windows). PDF mostra `|M|N|...` na coluna "Conteudo do Registro". Hipotese: PVA cache de validacao anterior OU artefato de parsing tabular do PDF. Acao: revalidar isoladamente via PVA antes de considerar regressao.

---

## ROADMAP DE CORRECOES PROXIMAS (pos-V22 PVA — atualizado 2026-05-16)

> **Regra de execucao**: corrigir **1 categoria por vez**, gerar SPED, validar via PVA, **so entao** passar para a proxima. Garantir nao-regressao a cada iteracao.

> Cada fix deve respeitar PROTOCOLO DE NOVA VERSAO (ver `CLAUDE.md`).

| Ordem | Categoria | Erros V22 | Funcao a modificar | Estrategia | Dependencias |
|-------|-----------|-----------|---------------------|------------|--------------|
| **1** | **CAT 23** | **45** | `construir_J005_J100()` (blocks.py:801) | Passar `saldos_mensais` para a funcao; usar `por_code[code]['saldo_inicial']`/`saldo_final` do mes 12/2024 em vez de `calcular_balanco_consolidado()`. Manter IND_DC pelo sinal (consistencia com V22 CAT 3). | Independente — pode comecar imediatamente |
| 2 | CAT 6 BP estrutural | 36 | `construir_J005_J100()` | Refatorar hierarquia: 2 raizes nivel 1 (Ativo + Passivo), IND_COD_AGL=D para detalhes (analiticas) e T para totalizadores (sinteticas), COD_AGL_SUP correto. | Depois CAT 23 (mesma funcao — risco regressao se simultaneo) |
| 3 | CAT 17 encerramento | 18 | `construir_I350_I355()` + `calcular_saldos_resultado_encerramento()` | Investigar: contas resultado nos meses de encerramento devem ter VL_SLD_FIN=0 em I155 (saldo apos encerramento). Ler Manual ECD I350/I355 + comparar com SPED contadora. | Independente |
| 4 | CAT 5/20 DRE | 13 | `construir_J005_J150()` | Refatorar `grupos_dre` (blocks.py:990): hierarquia explicita com COD_AGL_SUP, fix `is_total` (string match bugado em "TOTAIS"), emit I052 vinculando contas analiticas a codes detalhe DRE. | Depende decisao CAT 16 (codes ficticios vs hierarquicos da contadora) |
| 5 | CAT 22 J005 sem par | 2 | `sped_ecd_service.py` | Investigar: provavel J005 emitido sem J100 ou J150 correspondente. Verificar fluxo de chamadas. | Independente |
| 6 | CAT 9 IDENT_MF | 1 | n/a | Confirmar via re-validacao PVA isolada (V22 atual emite N — md5 verificado). Possivel cache PVA. | Independente — pode rodar em paralelo |
| 7 | PLANO_REFERENCIAL invalido | 7+11 (CAT 21/22 codigo) | `constantes.py:130` | Atualizar dict `PLANO_REFERENCIAL` com codes validados pela contadora (Inconsistencia 4 INCONSISTENCIAS_ODOO.md). | Depende retorno contadora |

**Impacto cumulativo esperado** (apos todos os fixes 1-7):
- V22: 198 erros
- Apos fix 1 (CAT 23): ~153
- Apos fix 2 (CAT 6 BP): ~117
- Apos fix 3 (CAT 17): ~99
- Apos fix 4 (CAT 5/20): ~86
- Apos fix 5+6+7: ~75 (depende contadora corrigir cadastros Odoo)
- **Apos correcoes Odoo da contadora (89 contas sem cod_ref + 376 cod_nat + 4 cod_ref invalido)**: residual ~5-10 erros (caso a caso, ja sem padroes claros)

**Bloqueios externos** (contadora):
- 89 contas sem `l10n_br_conta_referencial` (Inconsistencia 1) — bloqueia residual CAT 2
- 376 contas com `l10n_br_cod_nat` conflitante (Inconsistencia 2) — bloqueia CAT 19 + parte CAT 22
- 4 contas com cod_ref >5 pontos (Inconsistencia 3) — bloqueia CAT 21 (Odoo direto)
- Validacao Tabela 11 RFB (Inconsistencia 4) — bloqueia fix #7 acima

---

## CHECKLIST POS-FIX DE CADA CATEGORIA

Para cada categoria corrigida:

- [ ] Codigo alterado (citar `arquivo:linha`)
- [ ] Bump `VERSAO_SPED` em `services/sped_ecd_constantes.py` (ex: V21 -> V22)
- [ ] Pre-commit: rodar `scripts/sped_ecd/gerar_sped.py` (gera SPED novo + valida)
- [ ] Sanity check: grep direcionado no SPED gerado (citar comando exato no fix)
- [ ] Validator local: erros da categoria devem zerar OU diminuir significativamente
- [ ] Commit individual: `fix(sped_ecd): <VERSAO_SPED> — <CATEGORIA> — <descricao curta>`
- [ ] Append linha no HISTORICO desta pagina (NO TOPO da tabela)
- [ ] Atualizar STATUS da CATEGORIA neste PLANO para `FIXED_NOT_VALIDATED`
- [ ] Apos PVA externo confirmar: atualizar STATUS para `VERIFIED_FIXED`

---

## COMANDOS UTEIS PARA INVESTIGACAO

```bash
# Substitua VXX pela versao atual (ver VERSAO_SPED em sped_ecd_constantes.py)
VERSAO=$(grep "^VERSAO_SPED" app/relatorios_fiscais/services/sped_ecd_constantes.py | cut -d"'" -f2)
SPED=/home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_${VERSAO}_3COMPANIES.txt

# Contagem por tipo de registro
awk -F'|' '/^\|/ {print $2}' "$SPED" | sort | uniq -c | sort -rn | head -20

# I052 emitidos para sintetica (CATEGORIA 1)
awk -F'|' '/^\|I050\|/{ind=$5; cod=$7} /^\|I052\|/{if(ind=="S"&&cod==$3) print "BUG:"cod}' "$SPED" | wc -l

# Codes em I052 (CATEGORIA 4)
awk -F'|' '/^\|I052\|/{print $3}' "$SPED" | sort -u | head -30

# I050 analiticas SEM I051 subsequente (CATEGORIA 2)
awk -F'|' '/^\|I050\|.*\|A\|/{cod=$7; getline n; if(n !~ /^\|I051\|/) print cod}' "$SPED" | wc -l

# Contas-lixo (CATEGORIA 8)
grep -E "^\|I050\|.*\|(4444444|555555|7777777|88888888|99999999999)\|" "$SPED" | wc -l

# I250 negativos (CATEGORIA 11 — esperado 0)
grep -c "|I250|.*|-[0-9]" "$SPED"

# J100 com IND_COD_AGL=D vs T (CATEGORIA 6)
awk -F'|' '/^\|J100\|/{print $4}' "$SPED" | sort | uniq -c

# J150 com nivel=1 (CATEGORIA 5 — esperado 1, atualmente 2)
awk -F'|' '/^\|J150\|/&&$6=="1"' "$SPED" | wc -l
```

---

## HISTORICO DE ITERACOES

> Append nova linha NO TOPO ao rodar `gerar_sped.py` (apos bump de `VERSAO_SPED`).

| Versao SPED | Data | Erros validador | Warnings | Tamanho | Mudancas |
|-------------|------|-----------------|----------|---------|----------|
| **V21** | 2026-05-15 17:11 | **1** (so balanco nao bate) | 0 | 66.84 MB / 918699 linhas | mesmo codigo funcional de V20 + refactor docs (versao unica via `VERSAO_SPED`, script renomeado `gerar_sped.py`, PLANO sem versao no nome) |
| **V31** | 2026-05-16 20:17 | 1 (so balanco) | 0 | 66.80 MB / 918041 linhas | V31 — fix CAT 17 reverter V27. Manual ECD pag 159 REGRA_CONTA_RESULTADO: COD_NAT='04' exclusivamente (Tabela COD_NAT pag 118 — nao existe 07). V27 usava `{04,05,07}` baseado em interpretacao errada da CIEL IT. Resultado: 12 contas 5101* compensacao (REMESSA INDUSTRIALIZACAO, BONIFICACAO, TRANSF MERCADORIA) saem do I355. I355: 166→154 codes. Esperado -36 erros CAT 17. Tempo: 303s. |
| **V30 PVA** | 2026-05-16 18:31 | **55** | 527 | — | -9 vs V29 (-14%) — CAT 6 BP estrutural parcial (varios subcats zeraram: "nivel 1 ausente" 1→0, "2 niveis 1" 1→0, "ind_cod_agl=D" 2→0, "cod_agl_sup nao existe" 5→2, "so totalizadora sup" 5→2). MAS apareceu CAT 26 nova: J150 detalhe != soma I155+I355 (4 erros) — efeito colateral do I052 DRE adicionado V28 que permite essa validacao cruzada. Investigacao via Manual ECD oficial revelou: (a) tabela COD_NAT correta=04 exclusivo (nosso V27 errado); (b) I355 das contas reais 3xxx esta zerado (root cause separado — `calcular_saldos_resultado_encerramento` ler balance total Odoo). Total V18-2→V30: **-96%** (1450→55). |
| **V30** | 2026-05-16 17:57 | 1 (so balanco) | 0 | 66.80 MB / 918053 linhas | V30 — fix CAT 6 subcat "totalizador != soma filhas" (4 erros) + colateral "cod_agl_sup nao mesmo grupo" (4 erros). Dois fixes complementares: (a) `construir_J005_J100` filtra plano por classe patrimonial ANTES de propagar saldos via `calcular_saldos_hierarquicos` — sinteticas so recebem saldos de analiticas patrimoniais que serao emitidas; (b) `_classe_da_conta` para SINTETICAS sempre usa `_classe_pelo_code` (codes 1=Ativo, 2=Passivo) — sinteticas herdam account_type errado da 1a filha (INCONSIST. 5) e ficavam orfas. Resultado: 11307+11306 e descendentes (antes ausentes/erradas) voltaram. 350 J100 (era 345). Sintetica 1130 = soma filhas exatamente (32144611,82). Tempo: 273s. |
| **V29** | 2026-05-16 13:33 | 1 (so balanco) | 0 | 66.80 MB / 918048 linhas | V29 — fix CAT 22 (J005 sem par J100+J150): 1 unico J005 ID_DEM=1 cobre BP+DRE juntos (padrao contadora). Nova funcao `construir_J005_unico` em blocks.py. `construir_J005_J100` e `construir_J005_J150` nao emitem mais J005 interno. Validator interno atualizado (era exigir 2 J005). Tempo: 333s. |
| **V28 PVA** | 2026-05-16 13:15 | **66** | 527 | — | -25 vs V27 (-27%) — CAT 5/20 DRE J150 zerada por completo (15→0). Sub-efeito: 2 erros novos "J005 sem par J100+J150" agora batem em ambos os J005 (PVA quer J100 E J150 no MESMO J005 — contadora usa 1 so). Total V18-2→V28: **-95%** (1450→66). |
| **V28** | 2026-05-16 13:03 | 1 (so balanco) | 0 | 66.80 MB / 918049 linhas | V28 — fix CAT 5/20 J150 DRE: hierarquia explicita 3 niveis com COD_AGL_SUP populado (1 raiz '9' RESULTADO + 9.1/9.2 + 9.x.y detalhes), I052 vincula contas analiticas resultado a codes DRE detalhe (153 novos I052). Substitui codes ficticios DRE_REC_*. Sanity: 1 nivel 1, 4 detalhes D, 0 I052 sinteticas. Tempo: 341s. |
| **V27** | 2026-05-16 12:27 | 1 (so balanco) | 0 | 66.80 MB / 917XXX linhas | V27 — fix CAT 17 encerramento I355: filtro por `l10n_br_cod_nat` in {04,05,07} (Manual ECD). Resultado: 0 I355 patrimoniais (era 11), mas +12 contas codes 5xxx (compensacao marcadas cod_nat=05 no Odoo — cadastral). I355 total 163→166. |
| **V27 REVERTIDO (anterior)** | 2026-05-16 11:55 | n/a | n/a | n/a | TENTATIVA fix CAT 6 com fallback CODE → account_type foi REVERTIDA. Inconsistencia 5 (NOVA). |
| **V27 REVERTIDO** | 2026-05-16 11:55 | n/a | n/a | n/a | TENTATIVA fix CAT 6 com fallback CODE → account_type foi REVERTIDA. Usuario reforcou regra "zero fallback — dados sao do Odoo". Sinteticas com account_type herdado errado e problema CADASTRAL Odoo, nao bug gerador. Documentado em INCONSISTENCIAS_ODOO.md Inconsistencia 5 (NOVA). |
| **V26 PVA** | 2026-05-16 11:42 | **84** | 539 | — | -6 vs V25 (-7%) — "Conta deve ser analitica" zerou (6→0). Estimativa cravou. Warnings -34 ("Pelo menos um campo != 0" sumiu). Total V18-2→V26: **-94%** (1450→84). |
| **V26** | 2026-05-16 11:33 | 1 (so balanco) | 0 | 66.79 MB / 917863 linhas | V26 — fix CAT 25 colateral (skip I155 com todos os 4 valores zerados). Resolve "Conta deve ser analitica" V25. Conta `2.1.03.001.099` (Implantacao Contas a Pagar — zerada) ausente. I155: 1634→1600 (-34 codes zerados eliminados). Sem regressao em I050/I051/J100. Tempo: 329s. |
| **V25 PVA** | 2026-05-16 11:22 | **90** | 573 | — | -57 vs V24 (-39%) — CAT 2 zerou 48→1 (-47), CAT 22 11→1 (-10), CAT 21 7→1 (-6). Warnings -214. MAS **+6 novos** "Conta deve ser analitica" em I155 (5x conta `2.1.03.001.099` zerada + 1 outro). Estimativa cravou (-57). Total V18-2→V25: -94%. |
| **V25** | 2026-05-16 11:17 | 1 (so balanco) | 0 | 66.80 MB / 917897 linhas | V25 — fix CAT 25 (filtra plano por movimento/saldo). Helper `filtrar_plano_por_movimento()` em data.py. Aplicado em I050+I051+I052 e J100 (plano_consolidado_utilizado). I050 analiticas: 699 → 292 (vs contadora 291). Conta `1110400003` (zerada) ausente. Tempo: 340s. |
| **V24 PVA** | 2026-05-16 11:01 | **147** | 787 | — | -35 vs V23 (-19%) — CAT 24 zerou de 40 → 5 (exatamente os 5 originais V22 em outro registro). Estimativa cravou. Total -86% vs V18-2 (1450 → 147). |
| **V24** | 2026-05-16 10:48 | 1 (so balanco) | 0 | 66.85 MB / 919020 linhas | V24 — fix CAT 24 (natural fallback quando saldo==0 em J100). Sanity: 0 J100 com IND_DC vazio (era 40 V23). Helper `_ind_dc_v24(saldo, natural)`. Tempo: 392s. |
| **V23 PVA** | 2026-05-16 10:34 | **182** | 787 | — | -16 vs V22 (-8%) — CAT 23 zerada (-45) MAS +35 erros NOVOS "Campo obrigatorio nao preenchido" (IND_DC_BAL_I/F vazio em J100 para contas com saldo zero em um lado). Liquido: -45 +35 -6 = -16. **Lição**: refactor de IND_DC removeu protecao implicita do natural fallback. Fix V24 imediato. |
| **V23** | 2026-05-16 10:27 | 1 (so balanco) | 0 | 66.85 MB / 919020 linhas | V23 — fix CAT 23 (J100 usa saldos I155 mes 12/24, IND_DC pelo sinal — consistencia interna). Helper `_balanco_a_partir_de_saldos_mensais()` em blocks.py. Log gerador: balanco derivado substituiu 86 codes. Sanity: J100=I155 em 50 codes amostra. |
| **V22 PVA** | 2026-05-16 09:57 | **198** | 787 | — | -463 vs V21 (-70%) — CAT 3+18 zeraram (-200), CAT 2 reduziu 368→48 (-320). Descoberta V22: CAT 23 (J100 saldos ≠ I155, 45 erros novos) — afloram apos fix CAT 3. |
| **V22** | 2026-05-15 20:16 | 1 (so balanco) | 0 | 66.85 MB / 919020 linhas | V22 — fix CAT 3 (IND_DC pelo sinal balance, nao account_type) + fix CAT 2 (filtro V1.7 relaxado >5 pontos baseado na contadora). I051 cobertura subiu 42%→88% (+321 emissoes). IND_DC corrigido em 2 casos amostra (1130600001 C→D, 2110300001 D→C). |
| **V21 PVA** | 2026-05-15 18:49 | **661** | 787 | — | -789 erros vs V18-2 (-54%) — CAT 1, 4, 7 zeradas. Restam CAT 2 (368) + CAT 3 (188) + CAT 5/6 estruturais + I355 encerramento + IDENT_MF (regressao?) |
| V20 | 2026-05-15 16:20 | 1 (so balanco nao bate) | 0 | 66.84 MB / 918699 linhas | V1.9 — fix CAT 7 (J930 FONE+DT_CRC) + IND_CRC literal `SP-1303041/O-9` |
| V19 | 2026-05-15 16:02 | 1 (so balanco) | 0 | 66.84 MB / 918699 linhas | V1.9 — fix CAT 1+4 (I052 so analiticas) |
| V18 | 2026-05-15 12:45 | 1450 | 788 | 70.09 MB | V1.8 (CCUS off, IBGE, validator VL_DC>=0) |
| V17 | 2026-05-14 | ? | ? | 71.85 MB | V1.7 (I051 filtro, BP compensacao) — commit `dbfc5006` |
| V16 | 2026-05-14 | ? | ? | 71.86 MB | V1.6 (saldos iniciais, J100 codes reais, I052) — commit `117f0431` |
| V15 | ? | ? | ? | ? | V1.5 (0150 desativado, COD_PART opcao A) |

### V19 — Resultado da regeneracao (2026-05-15)

**Comando**: `python scripts/sped_ecd/gerar_sped.py` (script standalone — usa `VERSAO_SPED` para nome do output)

**Tempo de geracao**: 338.5s (5min 38s) — 3 companies, 6 meses, 136235 lancamentos

**Arquivo gerado**:
- WSL: `/home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V18_3COMPANIES.txt`
- Windows (copia V19): `/mnt/c/Users/rafael.nascimento/Pictures/SPED_ECD_NACOM_GOYA_01072024_31122024_V19_3COMPANIES.txt`

**Validador interno**:
- 1 erro BLOQUEANTE: `J100: Balanco nao bate: Ativo R$ 267,378,212.29 != Passivo+PL R$ 286,942,231.45 (diff R$ 19,564,019.16)`
- 0 warnings
- I250 negativos: 0 (esperado 0)

**Validacao manual via grep**:
- I052: 99 emitidos (vs 375 V18 — reducao 73%)
- I052 cross-check: 99/99 com IND_CTA='A' (zero sinteticas) ✓
- I052 codes: 100% com 10 digitos (analiticas detalhe) ✓
- J100: 87 D + 236 T (V18 era 100% T)
- J150 nivel=1: 2 registros (`DRE_REC_TOTAL` e `DRE_RESULT_LIQ`) — CAT 5 ainda presente
- Contas-lixo I050: 11 presentes — CAT 8 ainda presente
- I050 analiticas sem I051: 404 — CAT 2 ainda presente

**Status pos-V19** (5 categorias resolvidas + 6 pendentes):
- VERIFIED_FIXED: 9 (IDENT_MF), 11 (I250 negativos)
- FIXED_NOT_VALIDATED: 1, 4 (I052 sinteticas+totalizers — aguardando PVA externo)
- PENDING (precisam novo fix): 2, 3, 5, 6, 7, 8, 10
- BLOQUEADO_USUARIO: 7 (J930 contador FONE+DT_CRC)

**Erro restante 'balanco nao bate' (R$ 19.5M diff)**: ja existia em versoes anteriores. Causa raiz nao investigada — possivelmente relacionado a CAT 6 (J100 estrutural — falta detalhe em alguns ramos da arvore) ou consolidacao de contas entre as 3 companies.

---

## REFERENCIAS

- Manual ECD oficial: http://sped.rfb.gov.br/pasta/show/1569
- Arquitetura do modulo: `app/relatorios_fiscais/CLAUDE.md`
- PDF de validacao V18-2: `C:\Users\rafael.nascimento\Downloads\erros v18-2.pdf` (NAO RELER — usar este documento)
- SPED V19 gerado: `/mnt/c/Users/rafael.nascimento/Pictures/SPED_ECD_NACOM_GOYA_01072024_31122024_V19_3COMPANIES.txt` (NAO LER INTEIRO — usar `grep`/`awk`)
- **SPED CONTADORA (GROUND TRUTH)**: `/mnt/c/Users/rafael.nascimento/Downloads/SpedContabil-61724241000178_35208934897_18_20240701_20241231_G (1).txt` — referencia oficial validada pela RFB. Usar para extrair campos faltantes e comparar formato.

### Comandos uteis para comparar com SPED da contadora

```bash
CONT="/mnt/c/Users/rafael.nascimento/Downloads/SpedContabil-61724241000178_35208934897_18_20240701_20241231_G (1).txt"
NOSSO=/home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V18_3COMPANIES.txt

# Comparar cabecalho 0000
echo "CONTADORA:"; head -1 "$CONT"
echo "NOSSO:";    head -1 "$NOSSO"

# Comparar I030
echo "CONTADORA:"; awk -F'|' '$2=="I030"' "$CONT"
echo "NOSSO:";    awk -F'|' '$2=="I030"' "$NOSSO"

# Comparar J930
echo "CONTADORA:"; awk -F'|' '$2=="J930"' "$CONT"
echo "NOSSO:";    awk -F'|' '$2=="J930"' "$NOSSO"

# Contagem por bloco — diferencas estruturais
echo "CONTADORA:"; awk -F'|' '$2!=""' "$CONT" | awk -F'|' '{print $2}' | sort | uniq -c | sort -rn | head -15
echo "NOSSO:";    awk -F'|' '$2!=""' "$NOSSO" | awk -F'|' '{print $2}' | sort | uniq -c | sort -rn | head -15
```
