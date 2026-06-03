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

## STATUS (2026-06-01, piloto PROD)

**G0 ✅** (remessa) · **G1 ✅** (SVL entrada LF `D 1150200001 / C 1150100011`, Δ1150100011=0) · **G2 ✅** (material em 31092 via Model B) · **G3 ✅** (MOs 20252+20254 net-zero terceiros; fix G-ENT-10) · **G5b ✅** (op 3252) · **Dreno físico FB ✅** (26489→30720, picking `FB/INT/08128`/322875, 0 SVL — G-DRENO-1). **G5a 🔴 CONVERGE com G4** (sessão 6: **R-UNIF PROVADO** — NF-teste mista postada/excluída: `no_payment=22800` no j1001 **sozinho não baixa** a ATIVA, o FORNECEDORES do serviço absorve a 1902; exige a 1902 em **doc separado**, = a solução do G4). **G4 🔴 BLOQUEADO por desenho** (grounding sessão 5 refutou o plano: NF mista real → j847/venda-industrializacao; 3 opções em `PROPOSTA §4`, Rafael decidiu investigar). **G6/G8/G9 ⬜**. **Sessão 7 (2026-06-02): grounding do FLUXO 2-NF nas 3 esferas** (READ-only, zero escrita) — separação = **composição de linhas** (insumos 5902/1902 já simbólicos; PA viaja na linha de serviço 5124↔1124, única com move); robô: journal=`picking_type.tipo_pedido`; **3 gaps p/ executar (b)** (journal no_payment PASSIVA `5101020001` · picking_type 31093 · veículo NF insumos simbólica); **G8 (PA=Ic+S) confirmado como resíduo do piloto** (SVL usa `unit_cost`, não `price_unit`). (Detalhe: `ACHADOS §sessões 5 e 7`; material Contadora §5.)

> **"Saldo do ciclo" = Δ(débito−crédito)** das `account.move.line` da **cadeia documental do piloto** (não o saldo absoluto, que tem histórico R$60,8M). Estoque/26489: filtrar por produto 4870112 + lote do piloto. Toda métrica `=0` abaixo é Δ do ciclo.
> **Cenário do piloto:** SEM SOBRA (Is=0) → sem linha 5903/1903; Ic = R$279,24 (16 componentes), S = R$35/cx; PA-alvo = Ic+S = R$314,24.

| # | GOAL | Critério de SUCESSO (objetivo) | Status |
|---|---|---|---|
| **G0** | FB saída (remessa) baseline | NET `D 5101010001 +I / C 1150100002 −I`; transitória 1150100012=0 | ✅ |
| **G1** | LF SVL não inflar ativo próprio | SVL `D 1150200001 / C 1150100011`; estoque próprio LF não sobe; 1150100011 LF=0 no par NF+SVL | ✅ |
| **G2** | LF entrada física | material em **31092** (Materiais de Terceiros), não LF/Estoque | ✅ (via Model B) |
| **G3** | LF produção (MO) net-zero | MO consome 31092 → PA em 31093; net-zero terceiros; estoque próprio LF intacto | ✅ |
| **G4** | LF retorno baixa a PASSIVA | retorno **debita 5101020001** → Δciclo 5101020001(LF)=0; CST51, sem ICMS | 🔴 **caminho definido, aguarda Contadora** — R2 provado (no_payment não baixa em NF mista; CLIENTES absorve). **Opção (b): emitir 5902 em NF SEPARADA** do serviço → journal c/ no_pay 26667 (`PROPOSTA §4`). Pendente: aprovação fiscal (`MATERIAL_CONTADORA_G4.md`) + Skill 8 emitir 2 docs |
| **G5a** | FB entrada baixa a ATIVA | retorno **credita 5101010001** → Δciclo 5101010001(FB)=0 | 🔴 **CONVERGE com G4 (R-UNIF PROVADO sessão 6):** `no_payment=22800` no **j1001 sozinho NÃO baixa** numa NF mista — o FORNECEDORES do serviço (1124) absorve a 1902 (NF-teste: NET ATIVA=0). ⇒ exige a **1902 em DOC SEPARADO** do serviço + aprovação fiscal (= a do G4). Medido: 0/1600 ENTSI tocam a ATIVA; 1124→op1917, 1902→op2027 (autocancela). `ACHADOS §"ACHADO 2026-06-02 (sessão 6)"` |
| **G5b** | FB entrada sem double-count | linha 1902 gera **0 SVL** de entrada; estoque FB sobe só em PA(1150100007)+sobras(1150100002) | ✅ op 3252 (`movimento_estoque=False`) |
| **G6** | FB entrada física | DFe de retorno entra por **pt52** (`src=26489`); 26489 zera no par remessa↔retorno | ⬜ |
| ~~G7~~ | ~~ICMS 5124~~ | **MOOT**: NÃO há ICMS (CST51 + CBS/IBS/PIS/COFINS já tratados). Resta só o prazo 180d (Contador) | — |
| **G8** | PA valorado (AVCO) | custo do PA na FB = **Ic+S** (NF de retorno declara `price_unit`) | ⬜ medir no piloto |
| **G9** | Regularizar acumulados | plano p/ `5101010001` R$60,8M(FB)+R$8,67M(LF), double-count R$785k, `1150100011` −R$1,49bi | ⬜ Contador |

### Critério GLOBAL de ciclo fechado (meta-final)
Ciclo-piloto sem sobra: **`5101010001`(FB)=0 · `5101020001`(LF)=0 · estoque FB +(Ic+S) só em PA · 0 re-entrada de componentes · `26489`=0 · `30720`=0 · LF impacto-equity=0 · FORNECEDORES(FB)=ReceitaServiço(LF)=S**.

---

## Ordem de ataque (revisada — grounding sessão 6: G4 e G5a UNIFICADOS)
1. **G4 + G5a UNIFICADOS — decisão FISCAL (Contadora):** separar o retorno de **insumos** (1902↔5902) do **serviço** (1124↔5124). **PROVADO (sessão 6)** que o `no_payment` sozinho NÃO baixa nem na saída nem na entrada quando a NF é mista → **a mesma separação resolve os 2 lados**. `MATERIAL_CONTADORA_G4.md`. **Bloqueia Etapas 4 e 5.**
2. **Se SEPARAR aprovado:** configurar (LF saída) journal/picking_type de retorno-de-insumos só-5902 (no_pay 26667) **+** (FB entrada) escriturar a 1902 separada (no_pay 22800 j1001 ou journal dedicado); medir no piloto. *(detalhe op 3252 = G5b; CFOP 5902/1902.)*
3. **Faturar retorno LF→FB** (Etapa 4) + **escriturar FB** (Etapa 5) no piloto — medir G4/G5a/G6/G8. **Gate:** abortar se `Δ5101020001(LF) != 0` ou `Δ5101010001(FB) != 0`.
4. **3 pernas / AVCO** (G8): a NF de retorno declara `price_unit` do PA = Ic+S; medir no piloto (`PROPOSTA §6`).
5. **Regularização** (G9) — Contador, separado.

## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: GOALS — Industrialização FB↔LF (metas com métrica de sucesso)
