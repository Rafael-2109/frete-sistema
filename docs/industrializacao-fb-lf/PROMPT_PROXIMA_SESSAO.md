<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# PROMPT — Próxima sessão (Industrialização FB↔LF)

> **Atualizado 2026-06-03 (fim da 8ª sessão — CONTADORA APROVOU emitir 2 NF + 3 requisitos. A próxima sessão MUDA DE FASE: de grounding/decisão → IMPLEMENTAÇÃO da automação).**
> Handoff = próximo passo + estado. Estado completo: `README.md`. Desenho/decisões (dona): `SOT_OPERACOES.md` (§6 = requisitos da Contadora). Mecanismo + provas (NÃO refazer): `ACHADOS_TECNICOS.md §"ACHADO 2026-06-02 (sessão 7)"` blocos **A–I** (ler o TL;DR lá).

## Como começar
Leia nesta ordem: **`README.md`** (índice+estado) → **este handoff** → **`ACHADOS_TECNICOS.md` blocos A–I da sessão 7** (o que já foi PROVADO — não refazer) + TL;DR sessões 5/6. Desenho/decisões: **`SOT_OPERACOES.md`** (§6 requisitos + Etapa 4/5; em conflito, ela vence). Material da Contadora (decisão registrada): `MATERIAL_CONTADORA_G4.md §0`.

## A DECISÃO (aprovada 2026-06-02) — ponto de partida da implementação
A Contadora **APROVOU emitir o retorno em 2 NF** — o retorno de insumos (5902/1902) em **documento separado** do serviço (5124/1124) — com **3 REQUISITOS invioláveis**:
1. **R1 — emissão da NF de retorno AUTOMÁTICA:** a 2ª NF (insumos) deve sair **automaticamente, do mesmo jeito que os componentes são incluídos na NF hoje** (= expansão da BoM do PA). Zero digitação manual de insumos.
2. **R2 — escrituração da ENTRADA AUTOMÁTICA:** o DFe da NF de retorno deve ser escriturado automaticamente na FB **junto com** a NF de industrialização.
3. **R3 — VÍNCULO entre as 2 NFs** (retorno ↔ industrialização) para rastreabilidade.

⇒ Caminho **(b) separar = confirmado**. **Forma 1 (subcontratação nativa) DESCARTADA** (configurada mas dormente — `ACHADOS §I`). **Forma 2 (nosso pipeline deriva a 2ª NF) é o caminho.**

## Onde estamos (piloto 1 caixa, produto 4870112, lote PILOTO-3105)
- ✅ Etapas **1 → dreno físico → 2 → E** (remessa `RPI/2026/00245` SEFAZ-OK; entrada LF Model B ENTIN 737062; MO 20252+20254; PA em 31093). **Faltam Etapa 4 (faturar retorno) + Etapa 5 (escriturar FB).**
- ✅ Sessões 5–7: mecanismo do retorno **totalmente mapeado e provado** (READ-only + experimentos NF-teste postada/excluída; **zero escrita definitiva no Odoo**).

## O QUE JÁ FOI PROVADO — NÃO refazer (`ACHADOS §A–§I`)
- 1 NF mista **NÃO baixa** a compensação (8 ângulos + R-UNIF nos 2 lados). Caminho = **2 documentos**.
- A separação é de **COMPOSIÇÃO de linhas**, não de movimento físico: insumos 5902/1902 **já são simbólicos** (0 stock.move); só o **PA** tem move, na **linha de serviço 5124↔1124**.
- **Fonte dos insumos = BoM do PA** (9/9 batem) → a 2ª NF é **100% derivável** ⇒ **R1 é viável** (já explodimos a mesma BoM na remessa, `RUNBOOK §1`).
- **Vínculo nativo existe:** `account.move.referencia_ids` (refNFe) na saída; cadeia `DFe→PO→invoice` na entrada (3087 casos reais) ⇒ **R2/R3 viáveis** (entrada já é automática).
- Operador cria **1 picking (só o PA)**; o robô expande a BoM via `stock.invoice.onshipping.create_invoice` (`journal = picking_type.l10n_br_tipo_pedido`; 1 picking = 1 account.move).

## PRÓXIMA SESSÃO = IMPLEMENTAR (investigar a engenharia da automação, nesta ordem)
1. **R1 — emitir a 2ª NF (saída LF):** decidir ONDE separar — **(A)** customizar o `create_invoice` do CIEL IT (fornecedor, menos controle) **OU (B) nosso pipeline emite a 2ª NF** de insumos (explodindo a BoM, como já fazemos na remessa). Investigar o gatilho real (picking do PA / `liberar_faturamento`) e como derivar+emitir a NF de insumos sem trabalho manual.
2. **Journal + no_payment (config):** criar/repontar **1 journal de retorno-de-insumos** (LF sale) com `no_payment=26667` (PASSIVA `5101020001`) — hoje **NENHUM** journal sale LF aponta a PASSIVA (j1002 RETRABALHO usa 5101010046; mudá-lo atinge todo o retrabalho). Lado FB: journal de entrada-de-insumos com `no_payment=22800` (ATIVA) ou ajustar j1001. *(CFOP 5902/1902, não 5949 — confirmar fp que força 5902.)*
3. **R3 — vínculo:** preencher `referencia_ids` (refNFe) automaticamente nas 2 NFs de retorno (apontando remessa RPI/5901 e/ou uma à outra) + mesmo `invoice_origin`.
4. **R2 — escrituração automática (entrada FB):** estender `DFe→PO→invoice` para os 2 DFes (serviço + insumos) escriturarem **juntos e vinculados** (o trilho já roda em 3087 casos).
5. **G8 (AVCO Ic+S):** medir no piloto como o PA recebe Ic+S com a 1902 simbólica (op 3252, `mov_estoque=False`) — `ACHADOS §D` (resíduo a fechar só no ciclo real).
6. **Pontos de código que assumem "1 NF":** ajustar conforme `ACHADOS §E` (orchestrator `inventario_pipeline`, Skill 8 `faturamento.py`, Skill 7 `escrituracao.py`, `recebimento_lf_odoo_service`, ETL `faturamento_service` — filtrar a NF de insumos total=0 p/ não re-baixar carteira).
7. **Piloto 4870112 (ciclo 4+5 com 2 NF):** gate de sucesso — `Δ5101020001(LF)=0`, `Δ5101010001(FB)=0`, PA por `Ic+S`, 26489=0, 30720=0, **vínculo refNFe presente nas 2 NFs**.

## Regras invioláveis
- **dry-run + "go" FRESCO do Rafael em CADA escrita Odoo** (go DEPOIS da dry-run). NF SEFAZ (irreversível) só com go explícito. 1 comando por escrita.
- Experimentos Odoo: NF-teste em journal de teste, postar só se necessário, **SEMPRE limpar depois** (deletar NF + journal — "não sobrar rabo").
- **NUNCA** `action_apply_inventory` cru → Skill 1. Ops LF: contexto `allowed_company_ids=[1,5]`.

## IDs/constantes-chave
Empresas FB=1/LF=5 · partner LF=35 · trânsito 26489 · 31092 (LF/Mat.Terceiros) · 31093 (LF/PA Terceiros) · 30720 (FB customer terceiros) · pt98 (LF saída retorno 31093→26489, `tipo_pedido=False`) · pt66 (LF Exp.Industrializacao `venda-industrializacao`→j847) · pt97 (LF Exp.Ind.Retorno `dev-industrializacao`→j1002) · pt52 (FB entrada retorno src=26489).
Contas: 5101010001 ATIVA FB=**22800**/LF=26652 · 5101020001 PASSIVA FB=22815/LF=**26667**.
Journals: j1001 ENTSI FB-purchase (no_pay VAZIO) · j1047 ENTRADA-REMESSA LF-purchase (no_pay 26667) · j847 VENDA PRODUÇÃO LF-sale (NF mista retorno; no_pay VAZIO) · j1002 RETRABALHO LF-sale (`dev-industrializacao`, no_pay 26863=5101010046) · j1003 PERDAS LF-sale (5903). **Nenhum journal sale LF aponta a PASSIVA 26667 — criar/repontar (gap R1/journal).**
Operações: 5124→2702 · 5902→2864 (NF mista) / **2710 (dev-ind, separa)** · 5903→2711. FB entrada: 1124→**1917** · 1902→2027 (mov_estoque=True, double-count) / **3252 (mov_estoque=False, mata double-count)**. fp retorno LF=**111**; fp entrada FB serviço=**88**.
BoM do PA: `normal` + `subcontract` (subcontratante=LF) — a fonte dos insumos 5902. Lote FB PILOTO-3105 ids 60496-60511 (company 1, imutável).

## Contador — status
✅ **APROVADO emitir 2 NF (2026-06-02)** + 3 requisitos (R1/R2/R3) + Etapas 4-5 + Opção A (Ativo→Ativo, CPV só na venda) + PA=Ic+S. **Sem gargalo fiscal restante.** Separado/sem prazo: regularização dos acumulados (5101010001 R$60,8M FB; insumos sem baixa R$8,68M LF — `GOALS G9`).
