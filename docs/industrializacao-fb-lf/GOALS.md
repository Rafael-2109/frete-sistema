# GOALS — Industrialização FB↔LF (atual × correto × mudança → metas com métrica)

> Registro **direto**: por operação, o que é HOJE, o que DEVE SER, e a MUDANÇA — nas 3 dimensões **CFOP / Contábil / Estoque**. Base: `SOT_OPERACOES.md` v2.0 (verificado). Cada GOAL tem **critério de sucesso objetivo** (verificável em 1 ciclo-piloto do produto 4870112).
> Convenção: `I`=custo insumos remessa; `Ic`=consumido; `Is`=sobra (`I=Ic+Is`); `S`=valor agregado LF (serviço+materiais próprios). Empresas mesma UF (SP) → intraestadual.

---

## A. FLUXO POR OPERAÇÃO (atual × correto × mudança)

### OP1 — FB SAÍDA / Remessa de insumos — ✅ JÁ CORRETO
| Dim | HOJE = CORRETO | Mudança |
|---|---|---|
| CFOP | 5901 (CST 51 suspenso) | — |
| Contábil | NET `D 5101010001 REMESSA IND.(ATIVA) +I / C 1150100002 −I` | — |
| Estoque | FB/Estoque(8) → Em Trânsito(26489); SVL D 1150100012/C 1150100002, NF fp25/journal17 fecha 1150100012 | — |

### OP2 — LF ENTRADA / Recebe remessa
| Dim | HOJE | CORRETO | MUDANÇA |
|---|---|---|---|
| CFOP | 1901 | 1901 | — |
| Contábil NF | `D 1150100011 / C 5101020001 (PASSIVA)` ✅ | igual ✅ | — |
| Contábil SVL | ❌ `D 1150100002/001 (estoque próprio) / C 3201000002 (resultado)` | `D 1150200001 (valoração terceiros) / C 1150100011 (fecha transitória)` → NET `D 1150200001 / C 5101020001` | **repoint categoria LF: valoração→1150200001; input/output→manter 1150100011/012** (desenho A) |
| Estoque | 26489 → LF/Estoque(42) próprio, via pt19 | 26489 → **31092 (Materiais de Terceiros)**, via **pt64** | migrar pt19→**pt64 dst=31092** |

### OP3 — LF PRODUÇÃO / MO
| Dim | HOJE | CORRETO | MUDANÇA |
|---|---|---|---|
| CFOP | — (interno) | — (interno) | — |
| Contábil | consumo/produção em contas próprias LF | net-zero terceiros: consumo (terceiros→PRODUÇÃO) + produção PA (PRODUÇÃO→terceiros) | depende de OP2; conta `1150100004` ❓Contador |
| Estoque | LF/Estoque próprio → produção → pós-produção | 31092 → Produção → **31093 (PA de Terceiros)**; LF só agrega ÁGUA(consu)+serviço, **nunca product próprio** | MO manual (BoM 3695→3646); destino 31093 |

### OP4 — LF SAÍDA / Retorno (NF MISTA)
| Dim | HOJE | CORRETO | MUDANÇA |
|---|---|---|---|
| CFOP | emitido como "VENDA DE PRODUÇÃO" genérica | **5902** (insumos=remessa, CST51) + **5903** (sobras, CST51) + **5124** (valor agregado, **sem ICMS**) | montar NF por linha-CFOP |
| Contábil | receita `C 3101030001 SERVIÇOS IND. (S)` ✅; **NÃO baixa 5101020001** ❌; parte via journal "SAÍDA-PERDAS" debita 5101010001 LF ❌ | 5902/5903: `D 5101020001 (PASSIVA) / C [par terceiros net-zero]` (baixa obrigação); 5124: `D CLIENTES / C 3101030001 (S) + impostos` | operação fiscal de retorno **debita 5101020001**; **sair do journal PERDAS** |
| Estoque | genérico | 31093 → 26489 via **pt98** | padronizar pt98 |

### OP5 — FB ENTRADA / Recebe retorno — 🔴 PRINCIPAL
| Dim | HOJE | CORRETO | MUDANÇA |
|---|---|---|---|
| CFOP | entra via **pt1 genérico** (2.880×); NF = ENTSI (entrada serviço) | **1902** (consumidos) + **1903** (sobras) + **1124** (valor agregado, sem ICMS) via **pt52** | rotear DFe→pt52; operação de retorno por linha-CFOP |
| Contábil | ❌ NF: `C 2120100001 FORNECEDORES + PIS/COFINS`, **NÃO baixa 5101010001**; SVL: `D 1150100007 PA + D 1150100001 MP + D 1150100002 EMB / C 1150100011` (**DOUBLE-COUNT** dos componentes, R$785k) | **1902**: `D 1150100007 PA(Ic) / C 5101010001 (baixa Ic)` (simbólico); **1124**: `D 1150100007 PA(S) / C 2120100001 FORNECEDORES (S)`; **1903**: `D 1150100002 (Is) / C 5101010001 (baixa Is)` | **L5a**: NF de 1902 **credita 5101010001** (criar operação); **L5b**: 1902 **NÃO gera stock.move** (`movimento_estoque=False`, op 3252) |
| Estoque | ❌ PA + MP + EMB todos re-entram FB/Estoque | **só PA (1124) + sobras (1903)** entram FB/Estoque; componentes consumidos (1902) **não** entram | **1902 simbólico** (sem movimento físico) |
| AVCO PA | custo via price_unit da NF | PA valorado por **`Ic + S`** (NF de retorno declara) | NF de retorno LF declarar price_unit PA = Ic+S |

---

## B. GOALS (ordenados; cada um com métrica objetiva)

> **STATUS 2026-06-01 (piloto PROD, ver `RUNBOOK §0.7`):** **G0 ✅** (remessa) · **G1 ✅ ATINGIDO** (SVL entrada LF `D 1150200001 / C 1150100011`, Δ1150100011=0, estoque próprio LF não subiu) · **G2 ✅** (material em 31092 — via **Model B** Vendors→31092 lotes LF, NÃO pt64/26489 que é inviável, G-ENT-6) · **G3 ✅ ATINGIDO** (MOs 20252+20254 net-zero terceiros: `1150100004`/`1150200001` bal=0, estoque próprio LF intacto; fix G-ENT-10 = `picked=True` nos raws antes do mark_done) · **G4/G5a 🟡 DESBLOQUEADOS — Contadora CONFIRMOU desenho + Opção A (Ativo→Ativo, CPV só na venda); roteamento mapeado, spec pronta em `PROPOSTA_CONFIG_RETORNO.md`** (falta criar os 2 journals + tipo.pedido.diario, dry-run) · G6/G8/G9 ⬜ (físico pt52/pt98 + AVCO Ic+S + regularização). G5b (op 3252) e L1 confirmados vivos. **✅ Dreno 26489→30720 EXECUTADO 2026-06-01** (picking pt5 `FB/INT/08128`/322875 done; 26489→0, 30720=42,29, 0 SVL — gotcha G-DRENO-1 do driver corrigido).

> Verificáveis num **ciclo-piloto** (1 remessa→produção→retorno do 4870112).
> **"Saldo do ciclo" = ATRIBUIÇÃO OBJETIVA (não saldo absoluto da conta — que tem histórico R$60,8M etc.):** Δ(débito−crédito) das `account.move.line` cujo `move` pertence à **cadeia documental do piloto** — remessa 5901 + DFe entrada LF + NF retorno + DFe entrada FB do 4870112 — filtradas por `invoice_origin`/`ref`/picking do ciclo. Para `26489` e estoque: filtrar por **produto 4870112 + lote do piloto**. Toda métrica `=0` abaixo é **Δ do ciclo**, não saldo absoluto.
> **Cenário do piloto** (a fixar com a remessa): definir se Is (sobra)=0 (consumo total → sem linha 5903/1903) ou Is>0. E fixar os valores numéricos esperados Ic (custo 16 componentes) e S (R$35/cx × qtd) p/ o critério do PA (G8).

| # | GOAL | Critério de SUCESSO (objetivo, verificável) | Tipo | Depende |
|---|---|---|---|---|
| **G0** | FB saída (remessa) — confirmar baseline | Remessa do piloto gera NET `D 5101010001 +I / C 1150100002 −I`; transitória 1150100012 = 0 | ✅ já ok | — |
| **G1** | LF estoque (SVL) não inflar ativo próprio | SVL da entrada LF gera `D 1150200001 / C 1150100011` (NÃO `1150100002/001` nem `3201000002`); estoque próprio LF (1150100002/001) **não aumenta**; **1150100011 LF = 0** ao fim do par NF+SVL | config (repoint) | — |
| **G2** | LF entrada física correta | Recebimento entra por **pt64** com `location_dest = 31092`; material em "Materiais de Terceiros" (não LF/Estoque) | config+processo | — |
| **G3** | LF produção (MO) net-zero | MO consome de 31092 e produz PA em 31093; consumo+produção **net-zero** em terceiros; estoque próprio LF inalterado; só ÁGUA+serviço agregados | config+teste | G1 |
| **G4** | LF retorno baixa a PASSIVA | Retorno do piloto **debita 5101020001** pelo valor da remessa → **saldo do ciclo em 5101020001 (LF) = 0**; **0 lançamentos** em journal "SAÍDA-PERDAS"; NF tem linhas 5902/5903(CST51)+5124 (**sem ICMS**) | config fiscal CIEL IT | — |
| **G5a** | FB entrada — NF baixa a ATIVA | Entrada de retorno **credita 5101010001** → **Δciclo em 5101010001 (FB) = 0** (baixa = I da remessa) | **config 🟡 — Contadora CONFIRMOU (2026-06-01)**; spec pronta (`PROPOSTA §3`): criar journal entrada FB `account_no_payment_id=5101010001`(id22800) + apontar conta da 1902 via posição fiscal. Sem decisão contábil pendente. | G0 |
| **G5b** | FB entrada — sem double-count | Componentes consumidos (1902) geram **0 SVL de entrada** em FB/Estoque; estoque FB sobe **apenas** em PA (1150100007) + sobras (1150100002); MP/EMB consumidos **não** re-entram | **CONFIG** ✔resolvido: operação é POR LINHA (`account.move.line.l10n_br_operacao_id`); setar operação da linha 1902 com **`l10n_br_movimento_estoque=False`** (95 ops já usam False) → sem stock.move → sem double-count. **Sem separar NF, sem DEV.** | G5a |
| **G6** | FB entrada física correta | DFe de retorno entra por **pt52** (`src=26489`), não pt1; Em Trânsito 26489 zera no par remessa↔retorno | config+mapeamento | — |
| ~~G7~~ | ~~Tributação 5124 (ICMS)~~ | **MOOT (2026-05-30)**: confirmado em NF real — **NÃO há ICMS** em nenhuma etapa (CST51 suspenso; impostos = CBS/IBS/PIS/COFINS + "INDUSTRIALIZACAO", já tratados pelas ops atuais). **Não mexer em imposto.** Resta só o controle do prazo 180d da suspensão (CST51) — Contador | Contador | — |
| **G8** | PA valorado corretamente (AVCO) | Custo do PA no estoque FB = **Ic + S** (NF de retorno declara price_unit) | config NF | G5 |
| **G9** | Regularizar acumulados | Plano contábil (modo A/B/C) para `5101010001` R$60,8M(FB)+R$8,67M(LF), double-count estoque (R$785k/produto), `1150100011` −R$1,49bi | Contador | G1-G8 |

### Critério GLOBAL de ciclo fechado (meta-final)
Num ciclo-piloto completo (sem sobra): **`5101010001`(FB)=0 · `5101020001`(LF)=0 · estoque FB +(Ic+S) só em PA · 0 re-entrada de componentes · `26489`=0 · LF impacto-equity=0 · FORNECEDORES(FB)=ReceitaServiço(LF)=S`**.

---

## C. Estrutura fiscal CIEL IT verificada (✔G5b 2026-05-30)
- **Operação é POR LINHA**: `account.move.line.l10n_br_operacao_id` (+ `l10n_br_operacao_manual`, `l10n_br_cfop_id`). Na mesma NF cada linha tem operação/CFOP própria → **não precisa separar NF**.
- **`l10n_br_movimento_estoque`** (boolean na operação) controla se a linha gera stock.move. **95 operações usam `False`** (serviços/uso-consumo) → setar a operação da linha 1902 com `False` elimina o double-count. **CONFIG.**
- **Conta vem de `tipo_pedido(_entrada)` → journal** (`l10n_br_ciel_it_account.tipo.pedido.diario`); a conta de compensação fica no **`account_no_payment_id`** do journal (ex.: j17 REMESSA→5101010001; j1011 ENTRADA-REMESSA→5101020001; j1007 ENTRADA-RETORNO→5101020002). Operação NÃO tem campo conta.
- **A ENTSI quebrada**: linha 1902 usa op 2027/2807 com `movimento_estoque=True` + cai em 1150100011 → conserto = trocar por operação `False` + journal com `account_no_payment_id=5101010001`.

### Ordem de ataque (atualizada)
1. **G5a/G5b são CONFIG** (não DEV). Próximo: desenhar/criar as **operações fiscais de retorno** (1902 `movimento_estoque=False`+journal→5101010001; 1124 serviço; 1903 sobra→estoque+5101010001) e os journals de entrada correspondentes. Validar em **dry-run + piloto**.
2. **Composição "3 pernas"** (a parcela de insumo `Ic` no valor do PA): como o PA recebe `Ic` (baixa de 5101010001) + `S` (FORNECEDORES) — resolver com Contador/teste (AVCO do PA vem do price_unit da linha física 1124).
3. **G1 (SVL-LF)** + conta de valoração (`1150200001` colide com server action 1899 vs par dedicado) — Contador + re-teste fluxo entrada (desenho A, fechar 1150100011).
4. SEFAZ/ICMS 5124 (G7) + regularização (G9) — Contador/Fiscal.

> **1ª frente recomendada**: montar a **proposta de operações+journals de retorno** (G5a+G5b) em **dry-run** e validar no ciclo-piloto — agora que está provado ser config. Confirmar empiricamente no piloto: NF mista gera picking só das linhas `movimento_estoque=True`.
