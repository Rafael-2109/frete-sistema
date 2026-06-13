<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-13
-->
# Industrialização FB↔LF — Índice

> **Papel:** Industrialização FB↔LF — Índice.

Industrialização por encomenda no grupo: **FB** (encomendante) remete insumos → **LF** (industrializadora) produz e devolve o PA. Objetivo: fechar o fluxo físico+contábil para os insumos de terceiros **não inflarem o estoque** (passivo medido R$ 785k só no MOLHO SHOYU PET; `5101010001` FB acumulado R$ 60,8M).

> **Este README é o ÍNDICE** — só ponteiros. Cada assunto tem **um dono**; a informação mora num lugar só (não é replicada entre docs). Progressive disclosure: abra o doc do tema quando precisar do detalhe.

## Mapa dos documentos (cada um = 1 tema)

| Camada | Doc | Dono de | Abra quando |
|---|---|---|---|
| índice | **`README.md`** (este) | índice + ESTADO atual | ponto de entrada |
| handoff | **`PROMPT_PROXIMA_SESSAO.md`** | próximo passo da sessão | retomar o trabalho |
| desenho ⭐ | **`SOT_OPERACOES.md`** | desenho-alvo + **DECISÕES** (CFOP/contábil/estoque por etapa) | entender "o que deve ser" / qualquer decisão |
| metas | **`GOALS.md`** | metas + critério de sucesso por goal | medir se uma etapa fechou |
| mecanismo | **`ACHADOS_TECNICOS.md`** | como o Odoo/CIEL IT decide + IDs/constantes | precisar de um ID ou do mecanismo |
| execução config | **`PROPOSTA_CONFIG_RETORNO.md`** | **COMO** executar a config G4/G5a (IDs, roteamento, dry-run) | criar/ajustar journals do retorno |
| decisão Contadora | **`MATERIAL_CONTADORA_G4.md`** | material objetivo p/ a Contadora decidir o G4 (3 opções, lançamentos, perguntas) | levar o G4 à Contadora |
| procedimento | **`RUNBOOK_PILOTO_4870112.md`** | passos do piloto + gotchas (G-ENT/G-REM/G-DRENO) + drivers | executar uma etapa no Odoo |
| histórico | **`HISTORICO/`** | superseded (DIRETRIZ, PLANO_EXECUCAO, 00_FLUXO, PASSO0, CICLO, T-*) | arqueologia — **NÃO seguir** |

⭐ fonte única. **Em conflito, a SOT vence**; os demais apontam para ela, não copiam.

## ESTADO (checkpoint 2026-06-03 — piloto 4870112, 1 caixa, lote PILOTO-3105)

Config base (reversível): ✅ op 3252 (`movimento_estoque=False`) · ✅ L1 (categorias LF, Design A).

| Etapa | Estado |
|---|---|
| 1 — Remessa FB→LF | ✅ NF `RPI/2026/00245` SEFAZ-OK; `D 5101010001 +279,23` |
| Dreno físico FB `26489→30720` | ✅ EXECUTADO — picking `FB/INT/08128` (322875); 26489→0, 30720=42,29, **0 SVL** |
| 2 — Entrada LF (Model B) | ✅ picking 322451→31092; ENTIN 737062 posted; Δ1150100011=0 |
| E — MO | ✅ MOs 20252+20254; net-zero terceiros; PA em 31093 |
| 4 — Retorno LF→FB (faturar) | 🟢 **DESBLOQUEADO — Contadora APROVOU 2 NF** (2026-06-02, c/ 3 requisitos R1/R2/R3). Caminho (b) separar a 5902. **A IMPLEMENTAR** (Forma 2): emissão automática da 2ª NF (deriva da BoM) + journal `no_payment` PASSIVA. `SOT §6` |
| Sessão 8 (engenharia R1) | ✅ **Hipótese (i) REFUTADA** (`create_invoice` CIEL IT **funde** 5124+5902; toda op 5124 ≡ venda-industrializacao → VIA 1 fechada). **Caminho = split na janela DRAFT→pré-SEFAZ.** `ACHADOS §sessão 8` |
| Sessão 9 (desenho §6.1 + GATE 0) | ✅ **Desenho E2E da emissão 2-NF fechado** (`SOT §6.1 v3.1`, revisado por painel adversarial 3 lentes) + ✅ **GATE 0 EXECUTADO E APROVADO (13/06)**: split contábil em journals de teste **provou** que doc só-5902 com `no_payment=26667` **baixa a PASSIVA `5101020001`** (sem CLIENTES); NF só-5124 limpa. Sem SEFAZ, deletado (zero rabo). ✅ **Veículo DECIDIDO: server action** (Rafael 13/06; dívida: script de re-aplicação + monitor anti-upgrade). `ACHADOS §"GATE 0 EXECUTADO"` |
| 5 — Entrada FB (escriturar) | 🟢 **DESBLOQUEADO** (= G4). **A IMPLEMENTAR**: escrituração automática do DFe da NF de retorno junto da industrialização (entrada já é `DFe→PO→invoice`, 3087 casos — estender p/ 2 DFes vinculados). `SOT §6` |
| Sessão 5 (execução G4/G5a) | ✅ READ-ONLY + 4 lentes + 2 NF-teste (postadas/excluídas, sem sujeira) — mecanismo provado; **nada escrito em definitivo** (`ACHADOS §sessão 5` TL;DR) |
| Sessão 6 (R-UNIF) | ✅ **R-UNIF PROVADO** — NF-teste mista de ENTRADA postada/excluída (zero sujeira): `no_payment=22800` no j1001 não baixa a ATIVA (FORNECEDORES absorve a 1902). **G5a = G4** (1902/5902 em doc separado). j1001 intacto (`ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`) |
| Sessão 7 (fluxo 2-NF) | ✅ **GROUNDING 2-NF nas 3 esferas (READ-only, 5 scripts `s7_*`, zero escrita).** Separação = **composição de linhas** (insumos 5902/1902 já simbólicos; PA viaja na linha de serviço 5124↔1124). Robô: journal = `picking_type.tipo_pedido`. **3 gaps p/ executar (b):** journal c/ no_payment PASSIVA `5101020001` inexistente · pt98 `tipo_pedido=False` · veículo da NF de insumos simbólica. Anexado ao `MATERIAL_CONTADORA §5`; provas em `ACHADOS §sessão 7` |
| ⭐ **Decisão Contadora (2026-06-02)** | ✅ **APROVADO emitir 2 NF** (retorno de insumos 5902/1902 SEPARADO do serviço 5124/1124) com **3 requisitos**: (R1) emissão da NF de retorno **automática** (= a inclusão dos componentes na NF hoje) · (R2) escrituração do DFe **automática junto** da industrialização · (R3) **vínculo** entre as 2 NFs. ⇒ caminho (b); **próxima fase = IMPLEMENTAÇÃO** (Forma 2). `SOT §6` · `MATERIAL_CONTADORA §0` |

**Próximo:** ✅ GATE 0 + ✅ veículo=server action + ⚠️ **GATE 1 executado (achou 1 BLOQUEADOR)**. GATE 1 (13/06) revelou: picking de retorno = **pt66→Clientes(5)** (não pt98/26489); **`create_invoice` exige contexto LF-only `[5]`** (recompute 48s); e o **🔴 bloqueador**: o piloto 4870112 **não tem BoM `subcontract`** → não expande os 5902 (o azeite tem; é o gatilho da expansão — corrige sessão 7). ▶️ **Próximo: criar a BoM subcontract do shoyu** (espelhar a 14794 do azeite) → re-rodar GATE 1 (esperar 1×5124+16×5902) → split → GATE 2 (SEFAZ). Detalhe → `ACHADOS §"GATE 1 EXECUTADO"` + `PROMPT_PROXIMA_SESSAO.md`.

## Decisões fechadas (detalhe e porquê na `SOT`)
- ⭐ **Contadora APROVOU emitir 2 NF** (2026-06-02): retorno de insumos (5902/1902) em documento separado do serviço (5124/1124), com 3 requisitos (R1 emissão automática · R2 escrituração automática · R3 vínculo). `SOT §6` · `MATERIAL_CONTADORA §0`.
- Conta de compensação = família **`51010xx` ATIVA / `51020xx` PASSIVA** (NÃO `1150200001`, que é só valoração SVL-LF).
- **Opção A** (Ativo→Ativo, CPV só na venda) — Contadora confirmou 2026-06-01.
- **G5a NÃO é independente — CONVERGE com o G4** (PROVADO sessão 6): `no_payment=22800` no j1001 **sozinho NÃO baixa** a ATIVA numa NF de entrada mista (o FORNECEDORES do serviço absorve a 1902). O no_payment no j1001 é **necessário mas insuficiente**: a 1902 precisa vir em **documento separado** do serviço (mesma solução do G4). Estrutura real: 0/1600 ENTSI tocam a ATIVA; 1124→op 1917, 1902→op 2027.
- **G4: 1 NF mista NÃO baixa a 5902** (provado, 8 ângulos — `ACHADOS` TL;DR). A contrapartida é por DOCUMENTO (header), não por linha. **2 caminhos:** (b) separar a 5902 em documento próprio (nativo, já roda — SARET) **ou** (V-B) 1 NF mista + lançamento de ajuste na fonte (remendo, aval Contadora). **V-A (editar/repostar a NF) descartada.** Decisão Rafael+Contadora: separar é exigência fiscal ou preferência operacional? (`MATERIAL_CONTADORA_G4.md`).
- Compensação 51010xx/51020xx vem do `account_no_payment_id` do **journal** (não da posição fiscal); journal = cabeçalho da NF (campo `l10n_br_tipo_pedido` do journal).
- Sem ICMS em nenhuma etapa (CST51 + CBS/IBS/PIS/COFINS).
> Fonte: `SOT_OPERACOES.md` (§2 etapa 4 v2.4 · §5 decisões · §histórico v2.4) + `ACHADOS §"ACHADO 2026-06-01 (sessão 5)"`.

## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: Industrialização FB↔LF — Índice
