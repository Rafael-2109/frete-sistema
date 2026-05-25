# Inconsistencias no Plano de Contas Odoo CIEL IT — Correcoes para Contadora

**Data da analise**: 15/05/2026
**Companies analisadas**: NACOM GOYA FB (id=1) + SC (id=3) + CD (id=4)
**Total de codes unicos no plano**: 692
**Origem**: validacao PVA do SPED ECD V21 (01/07/2024 a 31/12/2024) — 661 erros, ~789 ja corrigidos no codigo

> Este documento lista as inconsistencias que sao **comprovadamente cadastrais no Odoo** (nao bugs de codigo). Cada item tem evidencia objetiva, impacto no SPED ECD e acao requerida. Anexos CSV neste diretorio.

---

## SUMARIO

| # | Inconsistencia | Contas afetadas | Impacto SPED | Origem |
|---|----------------|-----------------|--------------|--------|
| 1 | Contas sem `l10n_br_conta_referencial` | **89 codes** (267 registros 3-companies) | I051 nao emitido — PVA reclama 48x (V22) | CAT 2 PLANO |
| 2 | `l10n_br_cod_nat` conflita com `account_type` | **376 codes** (~1036 registros) | Natureza I050 errada — afeta 22+ erros estruturais V22 (11 nao-resultado + 11 natureza ref≠pai) | CAT 4/19/22 PLANO |
| 3 | `l10n_br_conta_referencial` com >5 pontos | **4 codes** | Filtrado por codigo (V22 — pontos>5) — sem erro PVA, mas indica dado errado | CAT 21 PLANO |
| 4 | Codes do `PLANO_REFERENCIAL` fallback nao existem na Tabela 11 RFB | **4-5 codes (codigo+Odoo)** | PVA reclama 7x CAT 21 + parte CAT 22 V22 | CAT 21/22 PLANO (NOVA — descoberta V22 2026-05-16) |
| 5 | Analiticas patrimoniais com `account_type` Odoo incompativel com a hierarquia do code | TBD (subset da Inconsist 2) | Sinteticas geradas pelo gerador herdam `account_type` da primeira filha — quando filha tem `expense` mas code e patrimonial (1xxx/2xxx), sintetica fica orfa no J100. Provoca CAT 6 BP estrutural (~24 erros V26). | CAT 6 PLANO (NOVA — descoberta V26 PVA 2026-05-16) |
| **6** | **Contas Passivo (code 2*) cadastradas com `account_type=expense`** | **9 codes** (~27 registros 3-companies) | Saldo nao agrega no Passivo do J100 — gera **diff R$ 444.771,25** no balanco V36 (Ativo 287.370.144 vs Passivo+PL 286.925.019). | **NOVA — descoberta V36 2026-05-24 via diff vs CONT-2S** |

**Total de codes para corrigir no Odoo**: ate ~478 (89 + 376 + 4 + 9 — alguns podem se sobrepor).

---

## INCONSISTENCIA 6 — Contas Passivo (code 2*) com account_type=expense

### Evidencia objetiva

Query Odoo: 9 codes unicos com `code` comecando com `2` (Passivo no plano NACOM) mas
`account_type` em (`expense`, `expense_depreciation`, `expense_direct_cost`). Esses
codes representam **obrigacoes trabalhistas/fiscais a recolher** (INSS, FGTS, IRRF,
etc.) que sao Passivos Circulantes, nao despesas.

### Por que e problema

- Manual ECD: `account_type` deve refletir a natureza contabil real da conta.
- Em V36, o `_classe_da_conta` retorna 'asset' para `expense*` so se code patrimonial
  ja foi processado (sintetica). Para analitica, lê o `account_type` direto e
  retorna '' (resultado) — saldo NAO entra no Passivo do J100.
- Resultado: saldo de R$ 444.771,25 (somatorio destas 9 contas) **desaparece**
  do Passivo no balanco V36.

### Impacto no PVA do SPED V36

Diff Ativo (R$ 287.370.144,07) ≠ Passivo+PL (R$ 286.925.019,21) = R$ 445.124,86.
PVA reprova upload (REGRA_VALIDA_ATIVO_PASSIVO_FIN).

### Acao requerida

Corrigir `account_type` no Odoo CIEL IT para `liability_payable` ou `liability_current`:

| Code | Descricao | Companies | account_type atual | Saldo 31/12/2024 |
|------|-----------|-----------|--------------------|------------------|
| 2110100008 | RESCISOES | FB | expense | -4.551,16 |
| 2110200001 | INSS A RECOLHER | FB+SC+CD | expense | -344.700,19 |
| 2110200008 | IRRF - SALARIOS A RECOLHER | FB+SC+CD | expense | -17.896,66 |
| 2110200015 | FGTS A RECOLHER | FB+SC+CD | expense | -46.644,00 |
| 2110200030 | CONTRIBUICAO SINDICAL A RECOLHER | FB+SC+CD | expense | -8.815,66 |
| 2110200031 | CONTRIBUICAO CONFEDERATIVA A RECOLHER | FB+SC+CD | expense | 0,00 |
| 2150100006 | CSRF A RECOLHER | FB+SC+CD | expense | -4.866,53 |
| 2150100007 | IRRF - SERVICOS A RECOLHER | FB+SC+CD | expense | -3.050,22 |
| 2150100008 | INSS DE TERCEIROS A RECOLHER | FB+SC+CD | expense | -14.601,27 |
| **TOTAL** | | | | **-R$ 445.125,69** |

### Excecao reconhecida (NAO mexer)

Codes `2140100*` (DESC.DUPL./ANTECIPACOES — 26 codes) e `2140200001` (EMPRESTIMOS
NACIONAIS) com `account_type=asset_cash` sao **INTENCIONAIS** segundo a contadora
(reclassificacao redutora de Ativo no fechamento — ver memoria
`gotcha_desconto_duplicatas_classificacao`). NAO corrigir.

---

## INCONSISTENCIA 1 — Contas sem `l10n_br_conta_referencial`

### Evidencia objetiva

Query Odoo (account.account, companies=[1,3,4], deprecated=false):
- 692 codes unicos no plano
- **89 codes (12.9%)** com campo `l10n_br_conta_referencial` vazio

### Por que e problema (Manual ECD Leiaute 9)

- Registro `0000` campo `COD_PLAN_REF=1` (PJ Lucro Real) **obriga** emissao de I051 para TODA conta analitica do I050.
- I051 mapeia conta da empresa para conta da Tabela 11 RFB (Plano Referencial PJ Lucro Real).
- Sem `l10n_br_conta_referencial` preenchido no Odoo, o gerador do SPED nao tem o que emitir — I051 fica ausente.

### Impacto no PVA do SPED V21

Mensagem: `O registro I051 e obrigatorio quando existe codigo do plano de contas referencial informado no registro 0000 (COD_PLAN_REF).`

Reportado **368 vezes** no PVA (uma por linha I050 sem I051 — inclui consolidacao 3 companies).

### Acao requerida

Preencher o campo `l10n_br_conta_referencial` no Odoo CIEL IT para as **89 contas** do anexo:

**Anexo**: `odoo_corrigir_sem_conta_referencial.csv`

Como referencia, o **SPED da contadora** (`SpedContabil-61724241000178...txt` em Downloads) usa codes da Tabela 11 RFB com 5 a 6 niveis hierarquicos:
- `1.01.01.01.01` (Caixa e Equivalentes — Numerario)
- `1.01.02.01.03` (Clientes — Duplicatas a Receber)
- `2.01.01.01.01` (Salarios a Pagar)
- `3.01.01.01.02.05` (Receita de Vendas — Mercado Interno — Mercadorias)

### Amostra (10 primeiras das 89)

| Code | Nome | account_type | Companies |
|------|------|--------------|-----------|
| 1130200001 | IMPORTACAO | asset_current | FB,SC,CD |
| 1130200002 | IMPOSTOS | asset_current | FB,SC,CD |
| 1130700006 | FRETE IMPORTACAO MERCOSUL | asset_prepayments | FB,SC,CD |
| 1140700004 | IRRF A FATURAMENTO | asset_current | FB,SC,CD |
| 1140700005 | IRRF S/ APLICACOES FINANCEIRA | asset_current | FB,SC,CD |
| 1140700006 | IMPOSTOS PAGO A MAIOR | asset_current | FB,SC,CD |
| 1142000001 | IRPJ DIFERIDO PREJUIZOS FISCAIS - CP | asset_current | FB,SC,CD |
| 1142000002 | CSLL DIFERIDO PREJUIZOS FISCAIS - CP | asset_current | FB,SC,CD |
| 1142000003 | IRPJ DIFERIDO VARIACOES TEMPORAIS ATIVO - CP | asset_current | FB,SC,CD |
| 1142000004 | CSLL DIFERIDO VARIACOES TEMPORAIS ATIVO - CP | asset_current | FB,SC,CD |

---

## ATENCAO — 26 contas DESC. DUPL./ANTECIPACOES/EMPRESTIMOS NAO sao erro de cadastro

> **Descoberta 2026-05-16**: confirmado com contadora que as **26 contas com codes `2140100*` e `2140200*`** com `account_type=asset_cash` + `l10n_br_cod_nat=02` (Passivo) **NAO devem ser alteradas**.
>
> **Razao**: sao contas de DESCONTO DE DUPLICATAS, ANTECIPACOES e EMPRESTIMOS — operacoes que durante o mes ficam como Passivo (recurso disponivel) e no FECHAMENTO ANUAL sao reclassificadas como redutora de Ativo (conforme Manual de Contabilidade Societaria). E desenho contabil deliberado, nao bug de cadastro.

**Contas a EXCLUIR da Inconsistencia 2 (NAO solicitar correcao a contadora):**

| Code | Nome |
|------|------|
| 2140100005 | DESC. DUPL. ATACADAO |
| 2140100015 | DESC.DUPL. BARCELONA |
| 2140100016 | DESC.DUPL. PAO ACUCAR |
| 2140100022 | SRM ADM.RECURSOS E FINANCAS |
| 2140100024 | DESC.DUPL. ROLDAO |
| 2140100028 | DESC. DUPL. WMS |
| 2140100029 | DESC.DUPL. ATAKAREJO |
| 2140100035 | ANTECIPACOES - TENDA |
| 2140100038 | ANTECIPACOES - MUFFATO |
| 2140100039 | ANTECIPACOES - ZARAGOZA |
| 2140100040 | ANTECIPACOES - CENCOSUD/ MERCANTIL RODRIGUES |
| 2140100043 | ANTECIPACOES - FORT ATAC GR PEREIRA |
| 2140100044 | ANTECIPACOES - MERCADAO ATACADISTA |
| 2140100046 | ANTECIPACOES - STO ATAC DE ALIM EIRELI |
| 2140100048 | ANTECIPACOES - RICOY SUP |
| 2140100049 | ANTECIPACOES - REDE DIA A DIA (DVA/B2M) |
| 2140100050 | ANTECIPACOES - GIGA |
| 2140100051 | OVERMIND - FUNDO DE INVESTIMENTO |
| 2140100052 | ANTECIPACOES - REDE TONIN ATACADISTA |
| 2140100053 | ANTECIPACOES - REDE CONFIANCA |
| 2140100056 | EMPRESTIMOS NACIONAIS |
| 2140100060 | ANTECIPACOES - ARMAZEM MATEUS |
| 2140100061 | ANTECIPACOES - MATEUS SUP |
| 2140100064 | ANTECIPACOES - OESA |
| 2140100065 | ANTECIPACOES - WMB |
| 2140200001 | EMPRESTIMOS / FINANCIAMENTOS |

**Tratamento no SPED (a investigar)**: provavelmente nosso gerador precisa de logica especial para essas contas — emitir como Passivo no balancete mensal (J100) mas como redutora no encerramento. Categoria potencialmente nova no SPED_ECD_PLANO.md. Ver memoria `gotcha_desconto_duplicatas_classificacao.md`.

**Stats apos exclusao destas 26 contas**: Inconsistencia 2 reduz de 376 → 350 contas a corrigir (gross-up).

---

## INCONSISTENCIA 2 — `l10n_br_cod_nat` conflita com `account_type`

### Evidencia objetiva

O Odoo CIEL IT tem 2 campos paralelos que indicam natureza da conta:
- `account_type` — taxonomia tecnica Odoo (ex: `liability_payable`, `expense`, `asset_current`)
- `l10n_br_cod_nat` — codigo natureza SPED ECD (01=Ativo, 02=Passivo, 03=PL, 04=Receita, 05=Custo/Despesa)

**Esperado**: os dois devem concordar. Mapeamento canonico:

| account_type | cod_nat esperado |
|--------------|------------------|
| asset_* | 01 (Ativo) |
| liability_* | 02 (Passivo) |
| equity, equity_unaffected | 03 (PL) |
| income, income_other | 04 (Receita) |
| expense, expense_depreciation, expense_direct_cost | 05 (Custo/Despesa) |

**Encontrado no Odoo**: **376 codes (54%)** com conflito.

### Por que e problema (Manual ECD Leiaute 9)

- Registro `I050` campo 3 = `COD_NAT` (natureza da conta).
- O gerador SPED emite **`l10n_br_cod_nat`** (campo Odoo CIEL IT) — pois e a fonte oficial.
- Se a natureza emitida nao corresponde a hierarquia do plano (codes 1=Ativo, 2=Passivo, 3=PL, 4=Receita, 5=Despesa), PVA reclama em multiplas regras estruturais:
  - "Conta cadastrada no plano de contas nao e conta de resultado." (11 ocorrencias V21)
  - "Natureza da conta inválida para o tipo de demonstracao." (advertencia)
  - "Conta de nivel superior devera ter a mesma natureza da subconta." (407 advertencias)
- Tambem causa erro no balancete (BP/J100): contas com cod_nat errado entram no lado errado do balanco → "Somatorio do Ativo != Passivo+PL".

### Distribuicao dos 376 conflitos (codes consolidados)

| account_type | cod_nat Odoo (errado) | cod_nat esperado | Quantidade |
|--------------|-----------------------|-------------------|------------|
| expense | 04 (Receita) | 05 (Custo/Despesa) | **254** |
| asset_cash | 02 (Passivo) | 01 (Ativo) | 26 |
| expense_direct_cost | 04 (Receita) | 05 (Custo/Despesa) | 24 |
| asset_current | 05 (Custo/Despesa) | 01 (Ativo) | 18 |
| liability_current | 05 (Custo/Despesa) | 02 (Passivo) | 17 |
| expense_depreciation | 04 (Receita) | 05 (Custo/Despesa) | 14 |
| expense | 02 (Passivo) | 05 (Custo/Despesa) | 8 |
| equity | 02 (Passivo) | 03 (PL) | 6 |
| liability_payable | 01 (Ativo) | 02 (Passivo) | 3 |
| expense | 01 (Ativo) | 05 (Custo/Despesa) | 2 |
| Outros (≤2 cada) | varios | varios | 4 |
| **TOTAL** | | | **376** |

### Acao requerida

Para cada conta do anexo, atualizar `l10n_br_cod_nat` para o valor da coluna `cod_nat_esperado` (alinhar com a hierarquia do code da conta).

**Anexo**: `odoo_corrigir_cod_nat_conflitante.csv`

### Amostra (10 primeiras das 376)

| Code | Nome | account_type | cod_nat Odoo (errado) | cod_nat esperado |
|------|------|--------------|------------------------|-------------------|
| 1130600001 | ADIANTAMENTOS A FORNECEDORES NACIONAIS | liability_payable | 01 (Ativo) | 02 (Passivo) |
| 1130600002 | ADIANTAMENTOS A FORNECEDORES EXTERIOR | liability_payable | 01 (Ativo) | 02 (Passivo) |
| 1130700001 | ADIANTAMENTO DE SALARIOS | expense | 01 (Ativo) | 05 (Custo/Despesa) |
| 1130700002 | ADIANTAMENTO DE FERIAS | expense | 01 (Ativo) | 05 (Custo/Despesa) |
| 1210200003 | EMPRESTIMOS A SOCIOS | liability_payable | 01 (Ativo) | 02 (Passivo) |
| 2110100001 | SALARIOS E ORDENADOS A PAGAR | expense | 02 (Passivo) | 05 (Custo/Despesa) |
| 2110100002 | PRO LABORE A PAGAR | expense | 02 (Passivo) | 05 (Custo/Despesa) |
| 2110100003 | PENSAO ALIMENTICIA | expense | 02 (Passivo) | 05 (Custo/Despesa) |
| 2110100008 | RESCISOES | expense | 02 (Passivo) | 05 (Custo/Despesa) |
| 2110200001 | INSS A RECOLHER | expense | 02 (Passivo) | 05 (Custo/Despesa) |

> **Atencao**: muitos conflitos sugerem `account_type` ERRADO (nao `cod_nat`).
> Ex: `2110100001 SALARIOS A PAGAR` deveria ter `account_type=liability_current` (e nao `expense`).
> Contadora precisa decidir caso a caso qual dos dois campos esta correto.

---

## INCONSISTENCIA 3 — `l10n_br_conta_referencial` com mais de 5 pontos

### Evidencia objetiva

Manual ECD aceita ate **6 niveis hierarquicos** no Plano Referencial RFB (= 5 pontos no codigo). Encontradas **4 contas** com 6 pontos (7 niveis):

| Code | Nome | l10n_br_conta_referencial | Niveis (pontos) |
|------|------|---------------------------|-----------------|
| 1210700002 | CSLL DIFERIDO PREJUIZO FISCAIS - LP | 3.2.8.9.4.20.20 | 7 (6 pontos) |
| 3901010003 | IRPJ DIFERIDO S/ PREJUIZOS FISCAIS | 3.2.8.9.4.10.20 | 7 (6 pontos) |
| 3901020003 | CSLL DIFERIDO S/ PREJUIZOS FISCAIS | 3.2.8.9.4.20.20 | 7 (6 pontos) |
| 3901020004 | CSLL DIFERIDO S/ PREJUIZOS FISCAIS (copia) | 3.2.8.9.4.20.20 | 7 (6 pontos) |

### Por que e problema

Esses codes nao existem na Tabela 11 RFB. O gerador SPED ja **filtra** automaticamente (codigo blocks.py:460), mas isso significa que **essas 4 contas nao emitem I051** — viram parte do erro CAT 2.

### Acao requerida

Reduzir cod_ref para max 5 pontos. Provavelmente o code correto e o "pai" hierarquico:
- `3.2.8.9.4.20.20` → talvez `3.2.8.9.4` ou `3.02.08.09.04` (recompor)
- Validar contra Tabela 11 RFB

**Anexo**: `odoo_corrigir_cod_ref_invalido.csv`

### Observacao

O code `3901020004` parece duplicata (sufixo "copia"). Considerar **arquivar** essa conta (active=False).

---

## INCONSISTENCIA 4 — Codes do PLANO_REFERENCIAL fallback nao existem na Tabela 11 RFB

> Descoberta na validacao PVA V22 (2026-05-16). Esta inconsistencia e **hibrida**: parte cadastral Odoo (2 codes), parte fallback no codigo do gerador SPED (4-5 codes) que precisam ser validados/atualizados contra a Tabela 11 RFB oficial — a contadora tem o documento oficial.

### Evidencia objetiva

PVA V22 reportou 7 erros "Conta nao existe no plano de contas referencial". Codes emitidos no I051:

| Code emitido no SPED V22 | Origem do code | Conta pai exemplo | Acao |
|--------------------------|----------------|-------------------|------|
| `1.01.01.01.01.01` | **`constantes.py PLANO_REFERENCIAL['asset_cash']`** | 1014000001 SICOOB | Validar contra Tabela 11 RFB — code correto? |
| `1.01.05.01.01.01` | **`constantes.py PLANO_REFERENCIAL['asset_prepayments']`** | 1130700006 FRETE IMPORTACAO MERCOSUL | Validar — code correto? |
| `1.02.01.01.24` | Odoo `l10n_br_conta_referencial` | 1210700001, 1210700003 | Validar — pode ser typo Odoo |
| `1.02.03.01.01.01` | **`constantes.py PLANO_REFERENCIAL['asset_fixed']`** | 1270400001 | Validar contra Tabela 11 |
| `3.05.01.01.01.01` | **`constantes.py PLANO_REFERENCIAL['income_other']`** | 3702010006, 3801010008 | Validar contra Tabela 11 |

### Comparacao com a contadora (ground truth aceito pela RFB)

O SPED da contadora usa codes da Tabela 11 com max 6 niveis (5 pontos):

| account_type esperado | Contadora usa (exemplos) | Nosso fallback `constantes.py` |
|------------------------|--------------------------|--------------------------------|
| Caixa (asset_cash) | `1.01.01.01.01` (5 niveis) | `1.01.01.01.01.01` (6 niveis) — invalido? |
| Receita vendas (income) | `3.01.01.01.02.05` (6 niveis) | `3.01.01.01.01.01` |
| Outras receitas (income_other) | (consultar contadora) | `3.05.01.01.01.01` — PVA rejeita |

### Por que e problema (Manual ECD)

Quando uma conta Odoo nao tem `l10n_br_conta_referencial` preenchido, o gerador usa fallback do dict `PLANO_REFERENCIAL` em `constantes.py:130`. Os codes nesse dict foram chutados sem confirmacao contra Tabela 11 RFB. Resultado: I051 emite codes que **nao existem** na tabela RFB oficial → PVA rejeita.

### Acao requerida (HIBRIDA — contadora + dev)

**Parte 1 — Contadora valida**: confirmar (ou corrigir) os codes corretos da **Tabela 11 RFB Lucro Real** para cada `account_type` Odoo. Tabela esperada:

| account_type Odoo | Code correto Tabela 11 RFB (PREENCHER) |
|---------------------|----------------------------------------|
| asset_cash | ? |
| asset_receivable | ? |
| asset_current | ? |
| asset_prepayments | ? |
| asset_non_current | ? |
| asset_fixed | ? |
| liability_payable | ? |
| liability_credit_card | ? |
| liability_current | ? |
| liability_non_current | ? |
| equity | ? |
| equity_unaffected | ? |
| income | ? (contadora usa `3.01.01.01.02.05` em vendas) |
| income_other | ? |
| expense | ? |
| expense_direct_cost | ? |
| expense_depreciation | ? |

**Parte 2 — Dev atualiza**: apos contadora preencher tabela acima, atualizar `app/relatorios_fiscais/services/sped_ecd_constantes.py` linhas 130-155 com os codes validados.

**Parte 3 — Cadastros Odoo individuais**: 2 contas com cod_ref do Odoo claramente errado:
- `1210700001` IRPJ DIFERIDO PREJUIZOS FISCAIS-LP — cod_ref `1.02.01.01.24` (so 4 niveis, code parece truncado)
- `1210700003` (mesmo problema)

---

## INCONSISTENCIA 5 — Analiticas patrimoniais com `account_type` incompativel com hierarquia do code

> Descoberta na investigacao CAT 6 BP estrutural (V26 PVA, 2026-05-16). E uma subcategoria da Inconsistencia 2 mas com efeito especifico no balanco patrimonial.

### Evidencia objetiva

Sinteticas geradas pelo gerador SPED (`_gerar_hierarquia_sintetica` em `data.py:253`) herdam `account_type` da primeira analitica filha encontrada. Quando essa filha tem `account_type` que conflita com a hierarquia do code, a sintetica fica com classe BP errada e e excluida do J100, deixando codes-filho orfaos.

**Exemplos concretos** (V26 PVA):

| Sintetica | Code | Filha exemplo | account_type filha | Problema |
|-----------|------|---------------|---------------------|----------|
| `2110` | Passivo Cir. (codigo 2 = Passivo) | `2110100001 SALARIOS A PAGAR` | `expense` (DESPESA — esperado `liability_current`) | Sintetica herda 'expense' → excluida do J100 → 211x analiticas ficam orfas |
| `113070000` | Ativo Cir. (codigo 1 = Ativo) | `1130700001 ADIANTAMENTO SALARIOS` | `expense` (DESPESA — esperado `asset_current`) | Sintetica herda 'expense' → excluida do J100 → 1130700xxx orfas |

Em V26 PVA, isso provoca **~24 erros CAT 6 BP estrutural** (sub-erros: "Cod agl/sup nao mesmo grupo", "Nao existe registro cod agl=sup", "So totalizadora pode ser sup").

### Por que nao corrigir via codigo (fallback CODE)

A regra de negocio NACOM e: **dados do Odoo sao a fonte autoritativa**. O gerador SPED nao deve sobrescrever `account_type` baseado em heuristica de code, mesmo que pareca corrigir o erro de classificacao. Razoes:

1. **Risco contabil**: se o cadastro Odoo intencionalmente classifica conta de adiantamento como `expense` (politica contabil), heuristica por code violaria a intencao.
2. **Mascaramento de bug**: fallback esconde o cadastro errado, atrasa correcao na fonte.
3. **Inconsistencia entre relatorios**: outros relatorios podem usar `account_type` direto — manter divergencia entre eles e um SPED "consertado por codigo" gera confusao.

### Acao requerida

**Para a contadora**: revisar analiticas patrimoniais (codes 1xxx, 2xxx) com `account_type` nao-patrimonial (`expense`, `income`, `income_other`) e corrigir para o `account_type` patrimonial correto (`asset_*`, `liability_*`, `equity`).

**Cruzar com Inconsistencia 2 CSV** (`odoo_corrigir_cod_nat_conflitante.csv`): essas contas ja estao listadas la quando `l10n_br_cod_nat` tambem esta errado. Casos onde so o `account_type` esta errado (mas `cod_nat` esta correto) precisam ser identificados separadamente.

**Query Odoo para identificar (a ser executada apos contadora autorizar)**:
```python
# Analiticas com code patrimonial (1xxx/2xxx) mas account_type nao-patrimonial
contas_problema = [
    a for a in plano_consolidado
    if a.get('tipo') == 'A'
    and a['code'].startswith(('1', '2'))
    and a.get('account_type', '').startswith(('expense', 'income'))
]
```

### Tratamento atual no gerador SPED (V26)

`_classe_da_conta()` em `construir_J005_J100` (`blocks.py:942`):
- Sinteticas com `account_type=expense` (herdado de filha) sao excluidas do BP — segue o Odoo.
- Filhas com code patrimonial (1xxx/2xxx) E account_type=`asset_*`/`liability_*` continuam emitidas no J100.
- Filhas com code patrimonial (1xxx/2xxx) E account_type=`expense` tambem ficam orfas (sao excluidas).

**Resultado V26**: 35 erros CAT 6 BP — esperam contadora corrigir.

---

## FORA DESTE DOCUMENTO

As seguintes inconsistencias **nao** sao cadastrais — sao bugs do gerador SPED ECD que estao sendo corrigidos no codigo:

- **CAT 3** (saldo final I155 errado) — bug de logica IND_DC em `blocks.py:577-578`. Sera corrigido em V22.
- **CAT 1, 4, 7** — ja corrigidos em V20/V21 (validado pelo PVA: 552+236+1 = 789 erros zerados).
- **CAT 5, 6, 19, 20** (estrutura J100/J150) — bugs estruturais do gerador, em correcao.
- **CAT 17** (encerramento I355) — bug de logica do gerador.

---

## REFERENCIAS

- **Plano de fix em curso**: `app/relatorios_fiscais/SPED_ECD_PLANO.md`
- **Manual ECD Leiaute 9 (RFB)**: http://sped.rfb.gov.br/pasta/show/1569
- **Tabela 11 — Plano Referencial PJ Lucro Real**: anexo do Manual ECD
- **Ground truth (SPED aceito pela RFB — contadora)**: `Downloads/SpedContabil-61724241000178_35208934897_18_20240701_20241231_G (1).txt`

---

## ANEXOS NESTE DIRETORIO

- `odoo_corrigir_sem_conta_referencial.csv` — 89 contas (Inconsistencia 1)
- `odoo_corrigir_cod_nat_conflitante.csv` — 376 contas (Inconsistencia 2)
- `odoo_corrigir_cod_ref_invalido.csv` — 4 contas (Inconsistencia 3)
