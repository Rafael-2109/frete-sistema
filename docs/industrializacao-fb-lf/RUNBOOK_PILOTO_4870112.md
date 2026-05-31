# RUNBOOK — Piloto E2E 4870112 (Industrialização FB↔LF)

> **Batch do piloto = 1 CAIXA de 4870112** (MOLHO SHOYU PET 12×1,01 L = 12 frascos). Unidade mínima.
> Detalha a **Etapa 1 (Remessa)** completa; Etapas 2–5 em esqueleto (ref. `GOALS §A`, `SOT §2`).
> **Gates invioláveis:** toda escrita Odoo com dry-run + aprovação do Rafael; **NF SEFAZ (Etapas 1 e 4) = IRREVERSÍVEL → só com "go" explícito**.
> **Validado ao vivo 2026-05-30** (Odoo PROD v17): op 3252 ✓ · L1 ✓ · receita/Ic ✓ · preview e g5b rodando. Sondas: `/tmp/ind_fb_lf_validar_estado.py`, `scripts/e2e_remessa_etapa1_dryrun.py`, `scripts/g5b_aplicar_op3252_na_linha.py`.
> **Gotcha Odoo 17:** linhas de produto da fatura têm `display_type='product'` (não `False`); CFOP usa `codigo_cfop`; incoterm em `stock.picking` é o campo **`incoterm`** (não `incoterm_id`).

---

## 0. Visão da sequência (5 etapas) e onde os levers entram

| Etapa | O quê | pt | NF/CFOP | Lever | Métrica (Δ ciclo, por LOTE do piloto) |
|---|---|---|---|---|---|
| **1. Remessa FB→LF** | 16 insumos saem FB→Em Trânsito | **53** (8→26489) | NF **5901** CST51 | — (já correto) | `D 5101010001 +I / C 1150100002 −I`; 1150100012=0 |
| 2. LF recebe | DFe 1901; entra em Materiais de Terceiros | **64** (26489→**31092**)¹ | 1901 | **L1** (val→1150200001) | SVL `D 1150200001 / C 1150100011`; **Δ1150100011(LF)=0** |
| 3. MO LF | BoM 3695→3646; PA em PA-Terceiros | interno | — | — | net-zero terceiros; PA em 31093 |
| 4. LF retorno | NF mista | **98** (31093→26489) | **5902+5903+5124** CST51, s/ICMS | L4 | **Δ5101020001(LF)=0**; 0 em "SAÍDA-PERDAS" |
| 5. FB recebe | DFe; **op 3252 na linha 1902** | **52** (26489→8) | 1902+1903+1124 | **G5b** (op 3252) | **G5b: 0 SVL de componentes** (estoque FB não infla) |

¹ pt64 hoje aponta `dst=42` (LF/Estoque), **não** 31092 → exige override na Etapa 2 (lever L2).
**⚠️ Distinção G5b × G5a (não confundir):** o **piloto valida só G5b** (op 3252 → componentes não re-entram no estoque). **`Δ5101010001(FB)=0` é G5a** (creditar a ATIVA no retorno) → depende de **journal de entrada novo (Contador)** que ainda não existe (validado ao vivo: 0 journals `purchase` com `account_no_payment_id=5101010001`). G5a **não** é alcançável pela op 3252 sozinha.

---

## 0.5 — PLANO DO TESTE CONTROLADO (1 caixa, lote dedicado) — A0→K

> Estratégia: **clean-slate** (zerar componentes na FB + adicionar quantidade controlada num **lote dedicado**, ex. `PILOTO-3105`) → rodar o ciclo **validando após cada etapa** para *recortar a etapa duvidosa*. Toda medição é **por lote/cadeia do piloto** (não saldo absoluto). 🔴 = gate SEFAZ irreversível · ⚠️ = etapa duvidosa (onde L1/G5b são testados).

| Passo | Ação | Ferramenta | Critério |
|---|---|---|---|
| **A0** | Snapshot baseline (contábil + físico por lote) | `e2e_piloto_validar.py --modo baseline --lote PILOTO-3105 --out base.json` | foto antes de tudo (p/ Δ) |
| **A** | Zerar comps + adicionar 1 caixa em lote dedicado (inclui CAIXA 210030203) | *manual (Rafael) — ajuste de estoque* | 16 comps em FB/Estoque(8) lote PILOTO |
| **B** 🔴 | Remessa FB→LF (pt53, NF 5901) — **lote pinado** | `e2e_remessa_criar.py --lote PILOTO-3105` (dry-run → `--execute` → `--liberar`) | `D 5101010001 +I / C 1150100002 −I` |
| **C** ⚠️ | Entrada LF — **pré-flight pt64/pt19 dst** | `--modo preflight-lf` antes; *receb LF*; dst=**31092** | material em **31092** (não 42) |
| **D** | Valida B+C (Δ computado) | `e2e_piloto_validar.py --modo remessa` / `--modo entrada-lf --base base.json` | `Δ1150100011(LF)=0`; 26489 do lote=0 |
| **E** | 2 MOs (BATELADA + PA), origem 31092 → PA em 31093 | *MO manual (LF)* | só ÁGUA+serviço; PA em 31093 |
| **F** | Valida E | `e2e_piloto_validar.py --modo mo --mo <bat> --mo2 <pa> --base base.json` | net-zero; PA 31093; loc 42 inalt. |
| **G** 🔴 | Retorno LF→FB (pt98, NF mista 5902+5124) | *retorno fiscal* | debita 5101020001; PA price=Ic+S |
| **H** | Entrada FB (pt52) + **op 3252 na 1902 em DRAFT** | `g5b_aplicar_op3252_na_linha.py --move-id <draft>` | 1902 com op 3252 |
| **I** ⚠️ | Valida entrada FB | `e2e_piloto_validar.py --modo entrada-fb --nf <id>` | **G5b**: 0 SVL comps. ❗**G5a não fecha** (Contador) |
| **J** | Ajuste/conferência do PA produzido (AVCO=Ic+S; cleanup) | *manual + validar* | AVCO PA = Ic+S |
| **K** 🔴 | Rollout p/ todos LF | **GATE CONTADOR** (G5a + 3 pernas + regularização) | — |

---

## 1. RECEITA — 16 componentes remetidos (1 caixa) ✅ validado ao vivo

> Explosão BoM **3695** (PA, rende 1 caixa) + **3646** (BATELADA semi, ×12,818 un/caixa), dividindo pelo rendimento de cada BoM. Validado: `scripts/e2e_remessa_etapa1_dryrun.py` → **16 componentes**, `Ic` ao vivo.

| # | cód | componente | qty / caixa | std_price (FB) | valor | via |
|---|---|---|---:|---:|---:|---|
| 1 | 210030010 | FRASCO INCOLOR 1,01 L | 12,000000 | 22,2310 | **266,77** | BoM 3695 |
| 2 | 105000022 | MOLHO SHOYU TRADICIONAL (MP) | 2,464427 | 2,3481 | 5,79 | BATELADA |
| 3 | 210030322 | RÓTULO MOLHO SHOYU PET 1,01 L | 12,000000 | 0,0954 | 1,14 | BoM 3695 |
| 4 | 210030203 | CAIXA DE PAPELÃO 320X240X267 | 1,000000 | 1,1462 | 1,15 | BoM 3695 |
| 5 | 104000007 | CORANTE CARAMELO III | 0,192270 | 6,2914 | 1,21 | BATELADA |
| 6 | 210030110 | TAMPA PLÁSTICA VERMELHA PET 1,01 | 12,000000 | 0,0932 | 1,12 | BoM 3695 |
| 7 | 105000039 | AROMA SHOYU ST 2175 | 0,058450 | 9,5688 | 0,56 | BATELADA |
| 8 | 104000018 | SORBATO DE POTÁSSIO | 0,012818 | 26,8879 | 0,34 | BATELADA |
| 9 | 105000024 | AÇÚCAR CRISTAL | 0,128180 | 3,1231 | 0,40 | BATELADA |
| 10 | 105000023 | ANTIESPUMANTE AFE 1520 | 0,002564 | 64,5125 | 0,17 | BATELADA |
| 11 | 104000015 | SAL SEM IODO | 0,533998 | 0,2975 | 0,16 | BATELADA |
| 12 | 104000004 | BENZOATO DE SÓDIO | 0,012818 | 9,7107 | 0,12 | BATELADA |
| 13 | 208000008 | FILME STRECH PRE ESTIRADO | 0,011607 | 10,2199 | 0,12 | BoM 3695 |
| 14 | 104000002 | ÁCIDO CÍTRICO | 0,012818 | 8,0546 | 0,10 | BATELADA |
| 15 | 208000010 | FITA ADESIVA TRANSP. 48X1200 | 0,860000 | 0,0622 | 0,05 | BoM 3695 |
| 16 | 207210014 | ETIQUETA BRANCA 104X50 | 1,000000 | 0,0325 | 0,03 | BoM 3695 |
| | | **Ic (valor da remessa, AVCO FB)** | | | **R$ 279,24** | |

**NÃO remetidos:** `104000017` ÁGUA (consu, 9,40/caixa — própria LF) · `3800018` BATELADA semi (produzido na MO LF).
> O **FRASCO** (vidro) é 95,5% do Ic (R$266,77). Custo dominante do batch.

---

## 2. Lotes + disponibilidade em FB/Estoque(8) — ✅ validado · 🔴 1 bloqueador

> O preview **lista** lotes com saldo livre (FIFO por `in_date`); o **operador escolhe/confirma** o lote por componente. Disponibilidade ao vivo 2026-05-30:

- **15/16 componentes têm saldo livre folgado** em FB/Estoque (ex.: FRASCO 120 un livre lote 85127; ROTULO 120 lote 251041; SAL 9.422; ETIQUETA 309.782).
- 🔴 **BLOQUEADOR — `210030203` CAIXA DE PAPELÃO 320X240X267: saldo livre em FB/Estoque = 0** (50 quants do produto existem, mas em Produção/Fornecedores/MIGRAÇÃO/Ajuste — **nenhum em loc 8**). **Repor/transferir ≥1 un de CAIXA para FB/Estoque ANTES da remessa.** (Em 29/05 havia 10 un; foram consumidas.)

> Rodar `e2e_remessa_etapa1_dryrun.py --caixas 1` na hora da remessa para revalidar saldos/lotes (mudam com a operação diária).

---

## 3. Picking type de criação + locations ✅

- **pt 53** "Expedição Industrialização (FB)" · code=outgoing · **src=8 (FB/Estoque) → dst=26489 (Em Trânsito Industrialização)** · wh=FB.
- 26489 é virtual/trânsito (cmp 0) — **deve zerar** no par remessa↔retorno **para o lote do piloto** (ver §9; 26489 carrega ruído histórico de outros ciclos).

---

## 4. Operação / CFOP 5901 por-linha ✅ resolvido ao vivo
- Operação da linha de remessa = **op 80** "Remessa p/ Industrialização" · CFOP **391** (`codigo_cfop`='5901') → journal 17 → `account_no_payment_id=5101010001`.
- Confirmado em remessas reais RPI/2026/00243-244 (e na cancelada 00242). O fluxo CIEL IT auto-seleciona ao criar a remessa pelo mesmo caminho de 01607/01608.

---

## 5. Checklist pré-condições `action_liberar_faturamento` (ACHADOS §4, campos v17)

**AMBIENTE (já satisfeito):**
- [x] `res.company(FB=1).warehouse_id = 1` ✅

**POR-PICKING (setar na remessa antes de liberar):**
- [ ] `stock.picking.incoterm = 6` (CIF) — **campo `incoterm`, não `incoterm_id`** (confirmado em 01607/01608)
- [ ] `stock.picking.carrier_id = 996` (NACOM GOYA) ✅ existe
- [ ] **operação 80 (5901) + CFOP 391 na(s) linha(s)** — `l10n_br_operacao_id != False` (GATE bloqueante: sem isso o robô não gera a NF)
- [ ] picking **validado** (componentes em 26489) antes de `action_liberar_faturamento`

Após `action_liberar_faturamento`: **robô CIEL IT cria a invoice em ~90s** (polling). Conferir 5901 (CST51, `amount_total=0`, `amount_untaxed=I≈R$279,24`) **antes** de transmitir.

---

## 6. Reaproveitar vs criar NOVA remessa — ✅ decisão: **NOVA**
- Rastro 29/05 confirmado ao vivo: picking **322049** (FB/SAI/IND/01606) `done`; NF **725676** (RPI/2026/00242) `cancel` (`amount_untaxed`=R$2.797,85 = **10 caixas**); **reversão física completa via `FB/DEV/00658`** (26489→8, `done`, "Devolução de FB/SAI/IND/01606", quantidades ×10).
- **NF SEFAZ cancelada não se reabre** + picking done + devolução feita = **criar remessa NOVA** com lotes frescos. (Não reaproveitar.)

---

## 7. Números do piloto ✅

| Símbolo | Significado | Valor |
|---|---|---|
| **I** | valor remessa (16 remetidos, AVCO FB) = `Ic+Is` | **R$ 279,24** (1 caixa) — *anchor histórico NF725676 R$2.797,85 era **10 caixas** → /10 ≈ R$279,78, bate* |
| **Ic** | insumos consumidos | = I (cenário **sem sobra**) |
| **Is** | sobra | **0** (sem sobra) → SEM linha 5903/1903 |
| **S** | valor agregado LF (serviço) | **R$ 35,00 / caixa** × 1 = **R$ 35,00** (supplierinfo 6319) |
| **PA** | valoração do PA na FB (AVCO-alvo) | **Ic + S = R$ 314,24** |

**Cenário recomendado: SEM SOBRA** (remeter exatamente a BoM → Is=0 → NF retorno só 5902+5124; entrada FB só 1902+1124). Simplifica a prova (`SOT §3`).

> ⚠️ **Risco aberto — AVCO do PA com 1902 simbólica (3 pernas):** com a op 3252 (`movimento_estoque=False`), a linha 1902 **não gera stock.move** → o `Ic` **não** entra no AVCO via 1902. Para o PA valer `Ic+S`, a **NF de retorno da LF deve declarar `price_unit` do PA = Ic+S na linha que gera o stock.move (1124)** (`SOT §76`). **Pós-piloto, conferir `standard_price`/AVCO do 4870112 na FB.** Como exatamente o `Ic` compõe o custo do PA = item "3 pernas" do **Contador** (`PROPOSTA §3 PERNAS`).

---

## 8. Sequência de execução (Etapa 1) — com gates

0. **GATE 0 (pré-flight):** confirmar (a) reversão do 322049 feita ✅ (FB/DEV/00658 done); (b) **repor CAIXA 210030203 em FB/Estoque** (§2 bloqueador); (c) 26489 sem resíduo do lote do piloto (snapshot baseline — §9).
1. **Preview (read-only):** `python docs/industrializacao-fb-lf/scripts/e2e_remessa_etapa1_dryrun.py --caixas 1` → confere receita, lotes, Ic, pré-condições. **Apresentar ao Rafael.**
2. *(go)* **Criar picking pt53** (16 moves, src=8→dst=26489, lotes do passo 1). **Meio:** criar `e2e_remessa_criar.py` (dry-run-first) replicando o padrão de `teste_lever_saida_fb.do_transfer` **OU** passo-a-passo na UI Odoo. *(script de criação ainda NÃO existe — próximo entregável após este runbook ser aprovado.)*
3. Setar `incoterm=6`, `carrier_id=996`, operação 80 + CFOP 5901 na(s) linha(s); `button_validate` (componentes → 26489).
4. `action_liberar_faturamento` → aguardar robô CIEL IT (~90s) → ler a NF 5901 → conferir `D 5101010001 +I / C 1150100002 −I` + transitória 1150100012=0 (métrica G0, **filtrando pela cadeia do piloto** — §9).
5. **⛔ GATE SEFAZ:** transmitir a NF 5901 **só com "go" explícito do Rafael** (IRREVERSÍVEL).

---

## 9. Métrica de sucesso da Etapa 1 (G0) — **medir por LOTE/cadeia do piloto** (GOALS §B)
> Saldos absolutos têm histórico (5101010001=R$60,8M; 26489 tem 50 quants negativos de outros ciclos). **Medir o Δ do ciclo, não o saldo absoluto.**
- **Snapshot baseline ANTES da remessa:** quants de 26489 + saldo 1150100012 dos componentes (subtrair depois).
- **Contábil:** Δ(débito−crédito) das `account.move.line` cujo `move` pertence à **cadeia documental do piloto** (NF 5901 + ref/origin do picking) = `D 5101010001 +I / C 1150100002 −I`; transitória `1150100012` da cadeia = 0.
- **Físico:** `stock.move.line` filtradas por **produto + lote do piloto** → componentes saem de FB/Estoque(8) e entram em 26489; 26489 do lote do piloto zera só após o retorno (Etapa 5).

---

## 10. Etapa 5 (G5b) — aplicação da op 3252 ✅ script validado
`scripts/g5b_aplicar_op3252_na_linha.py --move-id <NF entrada FB> [--execute]` — seta `l10n_br_operacao_manual=True` + `l10n_br_operacao_id=3252` **só nas linhas 1902** (insumos consumidos), preservando 1124/1903. Dry-run default; resolve CFOP 1902 ao vivo (`codigo_cfop`); guard de op (ativa, `movimento_estoque=False`), de estado e **anti-falso-sucesso** (aborta se 0 linhas 1902 mas há linhas de produto).
- **⏱️ JANELA OBRIGATÓRIA:** aplicar a op **enquanto o `account.move` está em `draft`** — antes de validar/postar e antes do robô gerar o picking. Aplicar pós-posted = no-op (o stock.move do double-count já foi gerado).
- **Confirmar no piloto:** a NF mista gera picking só das linhas `movimento_estoque=True` (1124/1903), pulando a 1902.

---

## 11. Pendências
**Resolvidas ao vivo (2026-05-30):** Ic por componente (R$279,24) · lotes/saldo · reversão 322049 · warehouse_id(FB)=1 · operação 5901 (op 80) · campos v17.

**Operacional (antes do piloto):**
1. 🔴 Repor **CAIXA 210030203** em FB/Estoque (§2).
2. Criar `e2e_remessa_criar.py` (dry-run-first) OU runbook UI da criação do pt53 (§8 passo 2).
3. Snapshot baseline de 26489 + 1150100012 (§9).

**Contador (não bloqueiam o piloto G5b; destravam o fechamento do ciclo):**
4. **G5a**: journal de entrada com `account_no_payment_id=5101010001` (creditar a ATIVA no retorno) — não existe.
5. **3 pernas**: como `Ic` entra no AVCO do PA com a 1902 simbólica (§7).
6. Conta valoração SVL-LF (`1150200001` × server action 1899) · conta PRODUÇÃO `1150100004` (L3).
7. Regularização dos acumulados (5101010001 R$60,8M FB + R$8,67M LF; double-count R$785k; 1150100011 −R$1,49bi).
