<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# GOALS — Industrialização FB↔LF (metas com métrica de sucesso)

> **Papel deste doc:** metas + **critério de sucesso objetivo** por goal (verificável em 1 ciclo-piloto do 4870112). O **desenho-alvo por operação** (atual×correto×mudança, CFOP/contábil/estoque) mora na **`SOT_OPERACOES.md §2`** (dona) — não é duplicado aqui. Índice: `README.md`.
> Convenção: `I`=custo insumos remessa; `Ic`=consumido; `Is`=sobra (`I=Ic+Is`); `S`=valor agregado LF. Empresas mesma UF (SP) → intraestadual.

---

## STATUS (2026-06-03, piloto PROD)

**✅ CONTADORA APROVOU emitir 2 NF (2026-06-02) — G4/G5a DESBLOQUEADOS; projeto entra na fase de IMPLEMENTAÇÃO dos 3 requisitos R1/R2/R3 (`SOT §6`).**

**G0 ✅** (remessa) · **G1 ✅** (SVL entrada LF `D 1150200001 / C 1150100011`, Δ1150100011=0) · **G2 ✅** (material em 31092 via Model B) · **G3 ✅** (MOs 20252+20254 net-zero terceiros; fix G-ENT-10) · **G5b ✅** (op 3252) · **Dreno físico FB ✅** (26489→30720, picking `FB/INT/08128`/322875, 0 SVL — G-DRENO-1). **G4 + G5a 🟢 APROVADOS (Contadora 2026-06-02) → a IMPLEMENTAR** (R-UNIF sessão 6: `no_payment` sozinho NÃO baixa numa NF mista nos 2 lados → 1902/5902 precisam vir em **doc separado**; caminho (b) aprovado — `SOT §6`). **G6/G8/G9 ⬜**. **Sessão 7 (2026-06-02): grounding do FLUXO 2-NF nas 3 esferas** (READ-only, zero escrita) — separação = **composição de linhas** (insumos 5902/1902 já simbólicos; PA viaja na linha de serviço 5124↔1124, única com move); robô: journal=`picking_type.tipo_pedido`; **3 gaps p/ executar (b)** (journal no_payment PASSIVA `5101020001` · picking_type 31093 · veículo NF insumos simbólica); **G8 (PA=Ic+S) confirmado como resíduo do piloto** (SVL usa `unit_cost`, não `price_unit`). (Detalhe: `ACHADOS §sessões 5 e 7`; material Contadora §5.)

> **"Saldo do ciclo" = Δ(débito−crédito)** das `account.move.line` da **cadeia documental do piloto** (não o saldo absoluto, que tem histórico R$60,8M). Estoque/26489: filtrar por produto 4870112 + lote do piloto. Toda métrica `=0` abaixo é Δ do ciclo.
> **Cenário do piloto:** SEM SOBRA (Is=0) → sem linha 5903/1903; Ic = R$279,24 (16 componentes), S = R$35/cx; PA-alvo = Ic+S = R$314,24.

| # | GOAL | Critério de SUCESSO (objetivo) | Status |
|---|---|---|---|
| **G0** | FB saída (remessa) baseline | NET `D 5101010001 +I / C 1150100002 −I`; transitória 1150100012=0 | ✅ |
| **G1** | LF SVL não inflar ativo próprio | SVL `D 1150200001 / C 1150100011`; estoque próprio LF não sobe; 1150100011 LF=0 no par NF+SVL | ✅ |
| **G2** | LF entrada física | material em **31092** (Materiais de Terceiros), não LF/Estoque | ✅ (via Model B) |
| **G3** | LF produção (MO) net-zero | MO consome 31092 → PA em 31093; net-zero terceiros; estoque próprio LF intacto | ✅ |
| **G4** | LF retorno baixa a PASSIVA | retorno **debita 5101020001** → Δciclo 5101020001(LF)=0; CST51, sem ICMS | 🟢 **APROVADO (Contadora 2026-06-02), a IMPLEMENTAR** — opção (b): emitir 5902 em NF SEPARADA (deriva da BoM → automática = R1) → journal c/ no_pay 26667 (PASSIVA). Gaps: criar/repontar journal PASSIVA + onde emitir a 2ª NF (`SOT §6`) |
| **G5a** | FB entrada baixa a ATIVA | retorno **credita 5101010001** → Δciclo 5101010001(FB)=0 | 🟢 **APROVADO (= G4), a IMPLEMENTAR** — 1902 em NF SEPARADA, escriturada automática junto da industrialização (R2) + vínculo (R3). Entrada já é `DFe→PO→invoice` (3087 casos). Gap: no_pay 22800 no j1001/journal dedicado. `ACHADOS §H/§I` · `SOT §6` |
| **G5b** | FB entrada sem double-count | linha 1902 gera **0 SVL** de entrada; estoque FB sobe só em PA(1150100007)+sobras(1150100002) | ✅ op 3252 (`movimento_estoque=False`) |
| **G6** | FB entrada física | DFe de retorno entra por **pt52** (`src=26489`); 26489 zera no par remessa↔retorno | ⬜ |
| ~~G7~~ | ~~ICMS 5124~~ | **MOOT**: NÃO há ICMS (CST51 + CBS/IBS/PIS/COFINS já tratados). Resta só o prazo 180d (Contador) | — |
| **G8** | PA valorado (AVCO) | custo do PA na FB = **Ic+S** (NF de retorno declara `price_unit`) | ⬜ medir no piloto |
| **G9** | Regularizar acumulados | plano p/ `5101010001` R$60,8M(FB)+R$8,67M(LF), double-count R$785k, `1150100011` −R$1,49bi | ⬜ Contador |

### Critério GLOBAL de ciclo fechado (meta-final)
Ciclo-piloto sem sobra: **`5101010001`(FB)=0 · `5101020001`(LF)=0 · estoque FB +(Ic+S) só em PA · 0 re-entrada de componentes · `26489`=0 · `30720`=0 · LF impacto-equity=0 · FORNECEDORES(FB)=ReceitaServiço(LF)=S**.

---

## Ordem de ataque (revisada 2026-06-03 — Contadora APROVOU; fase de IMPLEMENTAÇÃO)
> Decisão fiscal **RESOLVIDA** (✅ 2 NF aprovado + 3 requisitos R1/R2/R3 — `SOT §6`; `MATERIAL_CONTADORA §0`). A ordem agora é **construir a automação** (investigar a engenharia — `PROMPT_PROXIMA_SESSAO`).
1. **R1 — emitir a 2ª NF (saída LF) automática:** decidir (A) customizar `create_invoice` do CIEL IT ou **(B) pipeline deriva a 2ª NF da BoM** (recomendado) **+** criar/repontar journal de retorno-insumos com `no_pay 26667` (PASSIVA). CFOP 5902/1902 (não 5949).
2. **R3 — vínculo:** `referencia_ids` (refNFe) automático nas 2 NFs (retorno↔serviço↔remessa).
3. **R2 — escrituração automática (entrada FB):** estender `DFe→PO→invoice` p/ os 2 DFes vinculados; 1902 com op 3252 (G5b, já criada) + no_pay 22800 (G5a).
4. **Piloto 4870112 (ciclo 4+5 com 2 NF):** medir G4/G5a/G6/G8. **Gate:** abortar se `Δ5101020001(LF)≠0` ou `Δ5101010001(FB)≠0` ou vínculo ausente.
5. **G8 (AVCO Ic+S):** medir no piloto — como o PA recebe Ic+S com a 1902 simbólica (`ACHADOS §D`).
6. **Pontos de código que assumem 1 NF** (`ACHADOS §E`): orchestrator `inventario_pipeline`, Skill 7/8, `recebimento_lf_odoo_service`, ETL `faturamento_service`.
7. **Regularização** (G9) — Contador, separado.

## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: GOALS — Industrialização FB↔LF (metas com métrica de sucesso)
