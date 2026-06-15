<!-- doc:meta
tipo: explanation
camada: L1
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-15
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
| **POP operacional** 👷 | **`POP_OPERACIONAL_INDUSTRIALIZACAO.md`** | passo a passo das 5 etapas p/ os **usuários** (FB/LF/PCP/fiscal) | treinar/orientar operador no fluxo |
| desenho ⭐ | **`SOT_OPERACOES.md`** | desenho-alvo + **DECISÕES** (CFOP/contábil/estoque por etapa) | entender "o que deve ser" / qualquer decisão |
| metas | **`GOALS.md`** | metas + critério de sucesso por goal | medir se uma etapa fechou |
| mecanismo | **`ACHADOS_TECNICOS.md`** | como o Odoo/CIEL IT decide + IDs/constantes | precisar de um ID ou do mecanismo |
| execução config | **`PROPOSTA_CONFIG_RETORNO.md`** | **COMO** executar a config G4/G5a (IDs, roteamento, dry-run) | criar/ajustar journals do retorno |
| decisão Contadora | **`MATERIAL_CONTADORA_G4.md`** | material objetivo p/ a Contadora decidir o G4 (3 opções, lançamentos, perguntas) | levar o G4 à Contadora |
| procedimento | **`RUNBOOK_PILOTO_4870112.md`** | passos do piloto + gotchas (G-ENT/G-REM/G-DRENO) + drivers | executar uma etapa no Odoo |
| **regularização (G9)** ⭐ | **`G9_REGULARIZACAO_EVIDENCIAS.md`** | retroativo: correto×em-uso + dimensionamento + lock dates + caso-piloto provado + plano de rollout | **corrigir o histórico desde 01/2025** (Pergunta 4 Contadora) |
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
| 4 — Retorno LF→FB (faturar) | ✅✅✅ **CONCLUÍDA — 2 NFs AUTORIZADAS na SEFAZ via SERVER ACTION (14/06).** NF-1 791437 `VND/2026/00384` (5124) + NF-2 791441 `RETIN/2026/00001` (16×5902) cstat **100** + chaves; baixa PASSIVA Δ+279,23; R3 completo (refNFe remessa + cross). **Transmissão via SA provada — Playwright NÃO necessário** (`action_previsualizar_xml_nfe`+`action_gerar_nfe`). 4 gaps de cadastro (CIF+carrier LF+pgto+vencimento a-prazo) incorporados no `s37`. `ACHADOS §"FASE B"` |
| Sessão 8 (engenharia R1) | ✅ **Hipótese (i) REFUTADA** (`create_invoice` CIEL IT **funde** 5124+5902; toda op 5124 ≡ venda-industrializacao → VIA 1 fechada). **Caminho = split na janela DRAFT→pré-SEFAZ.** `ACHADOS §sessão 8` |
| Sessão 9 (desenho §6.1 + GATE 0) | ✅ **Desenho E2E da emissão 2-NF fechado** (`SOT §6.1 v3.1`, revisado por painel adversarial 3 lentes) + ✅ **GATE 0 EXECUTADO E APROVADO (13/06)**: split contábil em journals de teste **provou** que doc só-5902 com `no_payment=26667` **baixa a PASSIVA `5101020001`** (sem CLIENTES); NF só-5124 limpa. Sem SEFAZ, deletado (zero rabo). ✅ **Veículo DECIDIDO: server action** (Rafael 13/06; dívida: script de re-aplicação + monitor anti-upgrade). `ACHADOS §"GATE 0 EXECUTADO"` |
| 5 — Entrada FB (escriturar) | ✅ **CONCLUÍDA (piloto) — GATE CONTÁBIL FECHADO (`s67`, 15/06)**: `j1084 ENTRI` (no_payment=22800 ATIVA); **NF-2 MONTADA DIRETO** (in_invoice j1084, 16×op 3252, `calcular_imposto=False`, preços remessa 279,23 — refuta o caminho A do `s66` que ganhava tax lines espelho) + **NF-1 serviço `792219`** (j1001) **ambas POSTED** (escrituração definitiva, reversível, NÃO SEFAZ) + PA na FB (picking `325347`, C9). **Gate medido pelo CICLO** (não saldo global, que tem tráfego concorrente): **ATIVA `5101010001`=+0,00** (remessa+279,23 / NF-2−279,23) · **transitória `1150100011`=−0,00** · **estoque PA `1150100007`=+305,46 (Ic+S na CONTA)**. **Decisão Rafael 15/06: ajuste de custo MEDIDO PELA CONTA, não pela unidade** (revaloração AVCO dilui o Ic sobre 593 un do pool — inevitável; std 29,87 aceito). ⚠️ Pendência física: 26489=−1 (contorno manual do picking C9, lado LF→26489). `ACHADOS §"R2.3b"` |
| Sessão 5 (execução G4/G5a) | ✅ READ-ONLY + 4 lentes + 2 NF-teste (postadas/excluídas, sem sujeira) — mecanismo provado; **nada escrito em definitivo** (`ACHADOS §sessão 5` TL;DR) |
| Sessão 6 (R-UNIF) | ✅ **R-UNIF PROVADO** — NF-teste mista de ENTRADA postada/excluída (zero sujeira): `no_payment=22800` no j1001 não baixa a ATIVA (FORNECEDORES absorve a 1902). **G5a = G4** (1902/5902 em doc separado). j1001 intacto (`ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`) |
| Sessão 7 (fluxo 2-NF) | ✅ **GROUNDING 2-NF nas 3 esferas (READ-only, 5 scripts `s7_*`, zero escrita).** Separação = **composição de linhas** (insumos 5902/1902 já simbólicos; PA viaja na linha de serviço 5124↔1124). Robô: journal = `picking_type.tipo_pedido`. **3 gaps p/ executar (b):** journal c/ no_payment PASSIVA `5101020001` inexistente · pt98 `tipo_pedido=False` · veículo da NF de insumos simbólica. Anexado ao `MATERIAL_CONTADORA §5`; provas em `ACHADOS §sessão 7` |
| ⭐ **Decisão Contadora (2026-06-02)** | ✅ **APROVADO emitir 2 NF** (retorno de insumos 5902/1902 SEPARADO do serviço 5124/1124) com **3 requisitos**: (R1) emissão da NF de retorno **automática** (= a inclusão dos componentes na NF hoje) · (R2) escrituração do DFe **automática junto** da industrialização · (R3) **vínculo** entre as 2 NFs. ⇒ caminho (b); **próxima fase = IMPLEMENTAÇÃO** (Forma 2). `SOT §6` · `MATERIAL_CONTADORA §0` |

**ESTADO (15/06):** ✅ **Mecanismo E2E provado** — Etapa 4 (2 NFs AUTORIZADAS SEFAZ via SA, `s37`/`s54`) + **Etapa 5 (entrada FB) CONCLUÍDA no piloto, gate contábil fechado** (`s67`: NF-2 montada direto baixa a ATIVA; PA recebe Ic+S na conta; medido pela conta, AVCO aceito). ✅ **Transversal #6 — ETL não importa NFs inter-company da LF** (`faturamento_service` `company_id not in [5]` + 5 testes, commit `43127eb76`; **pende push/deploy**); 34 registros espúrios do piloto **limpos em PROD** (`s68`). ⚠️ Pendências: trânsito físico 26489=−1 · histórico LF no faturamento (934 linhas desde fev, só relatório) · 5903 (sobras) · pontos de código 1-NF (`ACHADOS §E`).

▶️ **PRÓXIMA SESSÃO = AUTOMAÇÃO** (fundação do R2 pronta — falta compor + a SA). **✅ Sessão 15/06:** item 1 (descoberta automática da remessa) CONCLUÍDO como módulo testado+validado PROD (`descoberta_industrializacao.py`; valor via SVL de ENTRADA, rateio faturado/produzido); **FLUXO L3 `1.2.4`** do R2 desenhado; **átomos do R2 capinados** (`montar_invoice_entrada_direta` genérico, skill `revalorando-custo-odoo`, picking C9); 7 commits anteriores (filtro ETL) PUSHADOS. **Próximo:** (1) **WIRE do R2** (compor o FLUXO 1.2.4 end-to-end, dry-run-first; rodar = go fresco); (2) **SA DURÁVEL da saída (G1+G2)** = objetivo final (G1 reusa `montar_invoice_entrada_direta`+descoberta; G2 transmite via SA `s54`); (3) reconciliar 26489. Detalhe: `PROMPT_PROXIMA_SESSAO.md`. **POP do usuário:** `POP_OPERACIONAL_INDUSTRIALIZACAO.md`.

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
