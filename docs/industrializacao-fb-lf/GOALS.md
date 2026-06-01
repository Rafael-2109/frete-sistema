# GOALS — Industrialização FB↔LF (metas com métrica de sucesso)

> **Papel deste doc:** metas + **critério de sucesso objetivo** por goal (verificável em 1 ciclo-piloto do 4870112). O **desenho-alvo por operação** (atual×correto×mudança, CFOP/contábil/estoque) mora na **`SOT_OPERACOES.md §2`** (dona) — não é duplicado aqui. Índice: `README.md`.
> Convenção: `I`=custo insumos remessa; `Ic`=consumido; `Is`=sobra (`I=Ic+Is`); `S`=valor agregado LF. Empresas mesma UF (SP) → intraestadual.

---

## STATUS (2026-06-01, piloto PROD)

**G0 ✅** (remessa) · **G1 ✅** (SVL entrada LF `D 1150200001 / C 1150100011`, Δ1150100011=0) · **G2 ✅** (material em 31092 via Model B) · **G3 ✅** (MOs 20252+20254 net-zero terceiros; fix G-ENT-10) · **G5b ✅** (op 3252) · **Dreno físico FB ✅** (26489→30720, picking `FB/INT/08128`/322875, 0 SVL — G-DRENO-1). **G4/G5a 🟡** desbloqueados (Contadora confirmou Opção A); **decisão fixada (`SOT §2 L5a`): G5a = ajustar o j1001 / G4 = criar journal LF saída** — falta executar (dry-run). **G6/G8/G9 ⬜**.

> **"Saldo do ciclo" = Δ(débito−crédito)** das `account.move.line` da **cadeia documental do piloto** (não o saldo absoluto, que tem histórico R$60,8M). Estoque/26489: filtrar por produto 4870112 + lote do piloto. Toda métrica `=0` abaixo é Δ do ciclo.
> **Cenário do piloto:** SEM SOBRA (Is=0) → sem linha 5903/1903; Ic = R$279,24 (16 componentes), S = R$35/cx; PA-alvo = Ic+S = R$314,24.

| # | GOAL | Critério de SUCESSO (objetivo) | Status |
|---|---|---|---|
| **G0** | FB saída (remessa) baseline | NET `D 5101010001 +I / C 1150100002 −I`; transitória 1150100012=0 | ✅ |
| **G1** | LF SVL não inflar ativo próprio | SVL `D 1150200001 / C 1150100011`; estoque próprio LF não sobe; 1150100011 LF=0 no par NF+SVL | ✅ |
| **G2** | LF entrada física | material em **31092** (Materiais de Terceiros), não LF/Estoque | ✅ (via Model B) |
| **G3** | LF produção (MO) net-zero | MO consome 31092 → PA em 31093; net-zero terceiros; estoque próprio LF intacto | ✅ |
| **G4** | LF retorno baixa a PASSIVA | retorno **debita 5101020001** → Δciclo 5101020001(LF)=0; **0** em "SAÍDA-PERDAS"; NF 5902(+5903)+5124 CST51, sem ICMS | 🟡 config — criar journal LF saída (no_payment=26667) + `tipo.pedido.diario(LF, dev-industrializacao)`; `PROPOSTA §4` |
| **G5a** | FB entrada baixa a ATIVA | retorno **credita 5101010001** → Δciclo 5101010001(FB)=0 | 🟡 config — **DECISÃO (`SOT §2 L5a`): ajustar o j1001** (`account_no_payment_id`=22800) + `tipo.pedido.diario(FB, serv-industrializacao→j1001)`, op 3252 na 1902; `PROPOSTA §3` |
| **G5b** | FB entrada sem double-count | linha 1902 gera **0 SVL** de entrada; estoque FB sobe só em PA(1150100007)+sobras(1150100002) | ✅ op 3252 (`movimento_estoque=False`) |
| **G6** | FB entrada física | DFe de retorno entra por **pt52** (`src=26489`); 26489 zera no par remessa↔retorno | ⬜ |
| ~~G7~~ | ~~ICMS 5124~~ | **MOOT**: NÃO há ICMS (CST51 + CBS/IBS/PIS/COFINS já tratados). Resta só o prazo 180d (Contador) | — |
| **G8** | PA valorado (AVCO) | custo do PA na FB = **Ic+S** (NF de retorno declara `price_unit`) | ⬜ medir no piloto |
| **G9** | Regularizar acumulados | plano p/ `5101010001` R$60,8M(FB)+R$8,67M(LF), double-count R$785k, `1150100011` −R$1,49bi | ⬜ Contador |

### Critério GLOBAL de ciclo fechado (meta-final)
Ciclo-piloto sem sobra: **`5101010001`(FB)=0 · `5101020001`(LF)=0 · estoque FB +(Ic+S) só em PA · 0 re-entrada de componentes · `26489`=0 · `30720`=0 · LF impacto-equity=0 · FORNECEDORES(FB)=ReceitaServiço(LF)=S**.

---

## Ordem de ataque (atualizada)
1. **Config do retorno (G4+G5a)** — execução técnica (não DEV). Decisão na `SOT §2 L5a`; IDs/roteamento/dry-run em `PROPOSTA §3-4`. Mecanismo (no_payment do journal, operação por-linha) em `ACHADOS §1`.
2. **Faturar retorno LF→FB** (Etapa 4) + **escriturar FB** (Etapa 5) no piloto — medir os critérios G4/G5a/G6/G8.
3. **3 pernas / AVCO** (G8): a NF de retorno declara `price_unit` do PA = Ic+S; medir no piloto (`PROPOSTA §6`).
4. **Regularização** (G9) — Contador, separado.
