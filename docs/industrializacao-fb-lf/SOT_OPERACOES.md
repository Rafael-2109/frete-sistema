<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-13
-->
# SOT — Operações de Industrialização FB↔LF (fonte única)

> **Papel:** SOT — Operações de Industrialização FB↔LF (fonte única).

## Indice

- [0. Princípio fiscal-contábil (a regra)](#0-princípio-fiscal-contábil-a-regra)
  - [Tributação por CFOP (✔v2 — NF de retorno é MISTA)](#tributação-por-cfop-v2-nf-de-retorno-é-mista)
- [1. Decisão de conta (❓ Contador — base do SOT)](#1-decisão-de-conta-contador-base-do-sot)
- [2. Mapa por operação (hoje → ideal → lever)](#2-mapa-por-operação-hoje-ideal-lever)
  - [Etapa 1 — FB SAÍDA / Remessa (5901, CST51) — ✅ JÁ CORRETO (referência)](#etapa-1-fb-saída-remessa-5901-cst51-já-correto-referência)
  - [Etapa 2 — LF ENTRADA / Recebe remessa (1901) — ✅ EXECUTADA E VALIDADA (Model B, 2026-06-01)](#etapa-2-lf-entrada-recebe-remessa-1901-executada-e-validada-model-b-2026-06-01)
  - [Etapa 3 — LF PRODUÇÃO / MO (interno) — ✅ EXECUTADA E VALIDADA (2026-06-01)](#etapa-3-lf-produção-mo-interno-executada-e-validada-2026-06-01)
  - [Etapa 4 — LF SAÍDA / Retorno — 🟢 DESBLOQUEADO (Contadora APROVOU 2 NF, 2026-06-02) — a IMPLEMENTAR (v2.8)](#etapa-4-lf-saída-retorno-desbloqueado-contadora-aprovou-2-nf-2026-06-02-a-implementar-v28)
  - [Etapa 5 — FB ENTRADA / Recebe retorno (1124+1902+1903) — 🟢 DESBLOQUEADO (= Etapa 4; Contadora aprovou) — a IMPLEMENTAR](#etapa-5-fb-entrada-recebe-retorno-112419021903-desbloqueado-etapa-4-contadora-aprovou-a-implementar)
- [3. Prova de fechamento (✔v2 — baixa única; caso com sobra)](#3-prova-de-fechamento-v2-baixa-única-caso-com-sobra)
- [4. Levers — o que configurar](#4-levers-o-que-configurar)
- [5. Decisões / verificações pendentes](#5-decisões-verificações-pendentes)
- [6. Requisitos da Contadora (APROVAÇÃO 2026-06-02) — desenho da implementação 2-NF](#6-requisitos-da-contadora-aprovação-2026-06-02-desenho-da-implementação-2-nf)
- [Histórico](#histórico)
- [Contexto](#contexto)

> **Source of Truth único** do desenho-alvo. Mecanismo Odoo/CIEL IT + IDs: `ACHADOS_TECNICOS.md`. Índice geral: `README.md`. Supersede a abordagem antiga (`1150200001` como conta fiscal) — docs preliminares arquivados em `HISTORICO/` (DIRETRIZ, 00_FLUXO, CICLO_COMPLETO_MAPA, PASSO0).
> **v2.1 (2026-05-30)** — corrigido após verificação adversarial (5 lentes) + reviewer de ambiguidades. Itens ✔v2/✔v2.1. **Reconciliado**: `movimento_estoque` é POR LINHA (não cabeçalho); sem ICMS em nenhuma etapa.
> **v2.2 (2026-06-01)** — ✅ **Contadora CONFIRMOU as Etapas 4 e 5 + Opção A (Ativo→Ativo)**: insumos consumidos incorporam-se ao custo do PA (`D 1150100007 / C 5101010001`), **CPV só na venda final** (não CPV no retorno). Roteamento G4/G5a mapeado ao vivo → spec em `PROPOSTA_CONFIG_RETORNO.md`. Itens ✔v2.2.
> Status: ✅ correto · 🔧 config · 🔴 principal/dev · ❓ Contador.
> **FB e LF = mesma UF (SP, Santana de Parnaíba) → operações INTRAESTADUAIS (CFOP 5xxx/1xxx). Não há 6xxx.** ✔v2

---

## 0. Princípio fiscal-contábil (a regra)

Industrialização por encomenda: os **insumos nunca mudam de dono** — são e seguem da **FB**. A LF agrega **valor (serviço + materiais próprios da LF: ÁGUA `consu` + energia)**. Por isso:
- **FB**: na remessa reclassifica insumos de estoque próprio → conta de controle "material em poder de 3os". No retorno **baixa** essa conta: insumos consumidos **incorporam-se ao custo do PA** (Ativo→Ativo, **não** DRE/CMV ✔v2); sobras voltam ao estoque. FB paga o **serviço** à LF.
- **LF**: material **não é seu** → balanço com impacto de equity **zero**; reconhece **receita de serviço de industrialização**.
- **Ciclo fecha**: controle FB e compensação LF **zeram** a cada remessa↔retorno; estoque físico só reflete PA (FB) + sobras.

### Tributação por CFOP (✔v2 — NF de retorno é MISTA; CST corrigido v3.1)
| CFOP | O que é | ICMS | Observação |
|---|---|---|---|
| 5901→1901 | Remessa dos insumos (da FB) | **suspensão CST 50** ✔v3.1 (verificado ao vivo: RPI/2026/00245 linhas `icms_cst=50`, PIS/COFINS 08) | valor = custo dos insumos; prazo legal de retorno (**180 dias** ❓Contador) |
| 5902→1902 | Retorno **simbólico** dos insumos **utilizados** | **suspensão CST 50** ✔v3.1 (verificado: VND 738097 linhas 5902 `icms_cst=50`, PIS/COFINS 08, tax_ids=[]) | **valor = valor da remessa 5901** (invariante de fechamento ✔v2) |
| 5903→1903 | Retorno dos insumos **não utilizados** (sobra) | CST 50 presumido (mesmo regime) — [confirmar no GATE 1] | valor = custo da sobra |
| 5124→1124 | **Industrialização efetuada** = valor agregado LF (serviço + materiais próprios LF) | **SEM ICMS destacado — CST 51 (diferimento)** ✔v3.1 (verificado: linha 5124 `icms_cst=51`, PIS/COFINS **01**) | **NÃO é "o PA"** ✔v2; é o valor agregado |

> ⚠️ **v3.1 (2026-06-12):** as versões anteriores diziam "CST 51 suspenso" para todas as linhas — INCORRETO em 2 sentidos (51 = diferimento, não suspensão; remessa/retorno usam **50**). Na implementação **NÃO hardcodar CST** — deixar a operação/posição fiscal derivar; assert no GATE 1 de que as linhas saem iguais às NFs autorizadas de referência.

> ✔v2.1 (2026-05-30, NF real): **NÃO há ICMS em nenhuma etapa** (CST51 suspenso na remessa; impostos do retorno = CBS/IBS/PIS/COFINS + "INDUSTRIALIZACAO", já tratados pelas operações atuais). **Não mexer em imposto.** A NF de retorno LF→FB tem **N linhas 5902** (insumos, valor=remessa) + **linha(s) 5124** (valor agregado) + **linhas 5903** (sobra). O PA físico na FB é valorado por (insumos consumidos + valor agregado).

---

## 1. Decisão de conta (❓ Contador — base do SOT)

Família de compensação existente, já parcialmente usada:

| Conta | Tipo | Papel |
|---|---|---|
| `5101010001` REMESSA IND. **(ATIVA)** | asset | **FB**: debita na remessa (saldo R$ 60,8M). Baixa no retorno. |
| `5101020001` REMESSA IND. **(PASSIVA)** | liability | **LF**: credita na entrada (ENTIN). Baixa no retorno. |
| `5101010002`/`5101020002` RETORNO IND. (ATIVA/PASSIVA) | asset/liab | **R$ 0 — nunca usados**. ❓ usar para a perna de retorno, ou baixar direto a REMESSA? (decisão §5) ✔v2 |
| `1150200001`/`1150200002` MATERIAL EM TERCEIROS / (−) | asset | **Inadequadas como conta FISCAL da NF** (a `DIRETRIZ` errou aqui). **Candidatas válidas só para a camada de VALORAÇÃO (SVL) net-zero da LF** — papel distinto ✔v2. ⚠️ já usadas pelo server action 1899 "Transferir TERCEIROS" → risco de colisão/rastreabilidade (❓§5). |

**Recomendação:** família `51010xx`/`51020xx` para a camada FISCAL (NF). Para a camada VALORAÇÃO (SVL) da LF, ver Etapa 2 (design em aberto).

---

## 2. Mapa por operação (hoje → ideal → lever)

### Etapa 1 — FB SAÍDA / Remessa (5901, CST51) — ✅ JÁ CORRETO (referência)
NET = `D 5101010001 (ATIVA) +I / C 1150100002 −I` (SVL via 1150100012 + NF fp25/journal17 fecham a transitória). **Manter.** Lever da location/categoria **refutado** empiricamente.

### Etapa 2 — LF ENTRADA / Recebe remessa (1901) — ✅ EXECUTADA E VALIDADA (Model B, 2026-06-01)
> **CORREÇÃO 2026-06-01 (piloto PROD):** o desenho "26489→31092 direto" (Model A) é **INVIÁVEL** — `company_id` de lote com estoque é IMUTÁVEL no Odoo, e a LF não consome estoque sob lote FB (G-ENT-6). **Adotado Model B (Rafael):** a LF recebe **fresco de Vendors→31092 com lotes LF próprios**; o trânsito 26489 (FB-lote) drena pelo companheiro **26489→30720** (lado FB). SVL/NF abaixo CONFIRMADOS em PROD (Design A: `D 1150200001 / C 1150100011` + ENTIN `D 1150100011 / C 5101020001`, Δ=0). Detalhes: `RUNBOOK §0.7`.
- **Física (original, Model A — inviável)**: hoje pt19 genérico (96% intercompany) → ~~padronizar pt64 dst=31092~~ → **Model B: pt19 Vendors→31092 lotes LF**.
- **NF (ENTIN)**: `D 1150100011 / C 5101020001 (PASSIVA)` — ✅ correto.
- **SVL hoje (errado)**: `D 1150100002/001 (estoque PRÓPRIO LF) / C 3201000002 (resultado!)` — infla ativo LF.
- **SVL ideal — ❓ design em aberto (✔v2):** a valoração deve ir para terceiros (`1150200001`), MAS a **contrapartida (input/output) precisa fechar a transitória `1150100011`** que a NF debita — senão `1150100011` (LF) acumula (gap que o teste simples não pegou). Dois desenhos candidatos:
  - **(A)** valoração→`1150200001`, **input/output→manter transitórias `1150100011/012`**: SVL `D 1150200001 / C 1150100011`; NF `D 1150100011 / C 5101020001`; **NET `D 1150200001 / C 5101020001`** (transitória zera; material sob custódia compensado pela obrigação). ← provável correto.
  - **(B)** valoração→`1150200001`, input/output→`1150200002` (o que testamos): net-zero no SVL isolado, **mas deixa `1150100011` aberta** pela NF.
- **Lever L1**: repoint categorias contexto LF (Design A). ✅ **VIVO e validado em PROD** — entrada LF (Etapa 2) + MO (Etapa E) executadas com Δ1150100011=0 e net-zero terceiros (estado em `README`).

### Etapa 3 — LF PRODUÇÃO / MO (interno) — ✅ EXECUTADA E VALIDADA (2026-06-01)
MO manual (BoM 3695→3646). Consumo (terceiros)→PRODUÇÃO; produção do PA←PRODUÇÃO. **Invariante ✔v2: a LF só agrega `consu` (ÁGUA) + serviço — NUNCA adiciona `product` próprio ao PA de terceiros.** Conta `1150100004 PRODUÇÃO` transitória (zera por MO).
> **✅ Validado em PROD (piloto 4870112):** MOs 20252 (BATELADA→semi 31092) + 20254 (PA→31093). **Net-zero terceiros confirmado**: `1150100004` (produção) bal=0 E `1150200001` (terceiros) bal=0 nas duas MOs; **estoque próprio LF (1150100001/002/007) intacto** (double-count R$785k NÃO se repetiu). AVCO do PA na LF = R$188,62 (custo LF dos comps, transitório — valor final na FB = Ic+S vem da NF de retorno, §3/§7). **Fix G-ENT-10** (RUNBOOK §0.7): MO via XML-RPC exige `picked=True` nas `stock.move.line` dos raws antes do `button_mark_done` (senão `skip_consumption` cancela os raws = produz sem consumir).

### Etapa 4 — LF SAÍDA / Retorno — 🟢 DESBLOQUEADO (Contadora APROVOU 2 NF, 2026-06-02) — a IMPLEMENTAR (v2.8)
> 🟢 **v2.8 (2026-06-02): a Contadora APROVOU emitir em 2 NF** (retorno de insumos 5902 SEPARADO do serviço 5124) com 3 requisitos — **R1** emissão automática · **R2** escrituração automática · **R3** vínculo (ver **§6**). Caminho (b) confirmado; **Forma 2 (pipeline deriva a 2ª NF da BoM)** = `ACHADOS §G/§H/§I`. As notas v2.4–v2.7 abaixo são o histórico do desenho (mantidas; o BLOQUEIO por desenho foi **resolvido** pela aprovação).
> 🔴 **v2.4 (2026-06-01, grounding sessão 5 — `ACHADOS`):** o plano abaixo (Lever L4: criar journal LF + `tipo.pedido.diario(dev-industrializacao/perda)`) está **REFUTADO**. A NF de retorno **real** é MISTA e cai em **j847 VENDA PRODUÇÃO** (header `venda-industrializacao`, op 5902 = **2864**), não por `dev-industrializacao`/`perda` (que já têm journal: j1002/j1003) nem em PERDAS. Logo a NF mista **não baixa a PASSIVA** hoje. **Fechar G4 exige decisão FISCAL da Contadora** — **EXPERIMENTO (sessão 5) provou que a opção (a) [no_payment no journal] NÃO baixa a 5902 em NF mista** (o `D CLIENTES` do serviço absorve). **Caminho = opção (b): emitir a 5902 em NF SEPARADA** do serviço (simbólica pura → no_payment baixa a PASSIVA, como na perda j1003). Detalhe: `PROPOSTA §4` + `MATERIAL_CONTADORA_G4.md`.
>
> 🟢 **v2.7 (2026-06-02, grounding sessão 7 — `ACHADOS §"ACHADO 2026-06-02 (sessão 7)"`): o "COMO" do caminho (b) mapeado ao vivo.** A separação é de **COMPOSIÇÃO de linhas, não de movimento**: as linhas 5902 (insumos) **já são simbólicas hoje** (0 `stock.move`; só o **PA na linha 5124** move — provado em `VND/2026/00359`). O journal (= no_payment) vem do `picking_type.l10n_br_tipo_pedido` (robô: **1 picking = 1 NF**). **Gaps para executar (b):** (a) **nenhum journal sale LF aponta a PASSIVA `5101020001`** → criar/repontar 1 journal de retorno-de-insumos com `no_payment=26667` (mudar o j1002 RETRABALHO atingiria todo o retrabalho); (b) **pt98** (retorno terceiros `31093→26489`) tem **`tipo_pedido=False`** → não roteia — falta picking_type saindo de 31093 com `tipo_pedido`; (c) a NF de insumos é **simbólica (sem movimento)** → definir o **veículo** (picking simbólico OU composição SO/robô em 2 docs). O precedente **SARET** (pt97/j1002) prova o **mecanismo contábil** mas é **devolução de produto REAL** (estoque próprio LF), não o retorno simbólico de terceiros.
- **Física**: pt98 (hoje usa genéricos "Ordens de Entrega"/"VENDA PRODUÇÃO").
- **NF de retorno (montagem por linha ✔v2):**
  - **5902 (insumos utilizados, =valor remessa, CST51)**: simbólico → **`D 5101020001 (PASSIVA) / C [par net-zero/terceiros — NUNCA resultado]`** ✔v2 (baixa a obrigação LF). Contrapartida = a mesma camada net-zero da Etapa 2 (def. §5).
  - **5903 (sobras, CST51)**: idem, baixa parcial da PASSIVA + devolve fisicamente.
  - **5124 (valor agregado LF, SEM ICMS ✔v2.1)**: `D CLIENTES / C 3101030001 SERVIÇOS DE INDUSTRIALIZAÇÃO (S) + C CBS/IBS/PIS/COFINS a recolher`. ✅ a receita de serviço já espelha o `2120100001 FORNECEDORES` da FB.
- ⚠️ **LF deve usar SÓ a PASSIVA `51020xx`** — hoje a LF também debita `5101010001 (ATIVA)` via journal **"SAÍDA - PERDAS"** (+R$ 8,67M) ✔v2 → corrigir operação/journal de saída LF p/ não cair em PERDAS.
- **Lever L4** ~~(✔v2.2 "caminho mapeado": criar journal LF sale + `tipo.pedido.diario(LF, dev-industrializacao/perda)` p/ a 5902 op 850)~~ 🔴 **REFUTADO v2.4** (ver nota no topo desta Etapa 4 + `ACHADOS §sessão 5`): a NF mista de retorno cai em **j847/venda-industrializacao** (op 5902 = **2864**, não 850/dev-industrializacao); aquele plano é **inerte**. ✔v2.1 confirmado: granularidade POR LINHA (5902/5124 coexistem na mesma NF, operações distintas) — **mas o journal é UNO (do cabeçalho)**. Fechar G4 = 1 das 3 opções (`PROPOSTA §4`), decisão Rafael+Contadora. Obrigação do piloto a baixar = **R$ 278,56** (ENTIN 737062).

### Etapa 5 — FB ENTRADA / Recebe retorno (1124+1902+1903) — 🟢 DESBLOQUEADO (= Etapa 4; Contadora aprovou) — a IMPLEMENTAR
- **Física**: hoje **2.880× pt1 genérico** vs 10× pt52 → 🔧 rotear DFe → **pt52** (`src=26489`).
- **Lançamento-alvo por linha (✔v2 — baixa ÚNICA de I, sem double-count):**
  - **1902 (insumos consumidos, simbólico)**: **`D 1150100007 PA (incorpora I_consumido) / C 5101010001 (baixa I_consumido)`** — ✔v2.2 **Contadora CONFIRMOU Ativo→Ativo** (não CPV; CPV só na venda final do PA). **NÃO gera stock.move de entrada dos componentes** (senão SVL re-infla estoque = o R$ 785k). *Estado atual (errado) verificado: a entrada cai em j1001 ENTSI (no_payment VAZIO) + re-infla MP/EMB — `ACHADO 2026-06-01`.*
  - **1124 (valor agregado, SEM ICMS ✔v2.1)**: **`D 1150100007 PA (+S) / C 2120100001 FORNECEDORES (S)`** (+ CBS/IBS/PIS/COFINS a recuperar). Só serviço (não baixa `5101010001` de novo — a baixa de I é única, no 1902).
  - **1903 (sobras)**: **`D 1150100002 (sobra volta) / C 5101010001 (baixa I_sobra)`** — físico (re-entra estoque).
- **AVCO do PA (leg ✔v2):** o PA entra valorado pelo **price_unit da linha 1124/1902 da NF** = `I_consumido + S`. Não é soma automática → a NF de retorno da LF **deve declarar** esse valor. **Sem isso o AVCO grava custo errado.**
- **Lever L5 — SEPARAR em duas camadas (✔v2):**
  - **L5a (conta da NF) — ✔v2.3 DECISÃO (Rafael 2026-06-01): AJUSTAR o journal existente `j1001 ENTRADA - SERVIÇO DE INDUSTRIALIZAÇÃO`** (NÃO criar journal novo): setar `account_no_payment_id=22800` (5101010001 ATIVA) no j1001 + `tipo.pedido.diario(FB, serv-industrializacao → j1001)` para rotear a op **3252** da linha 1902. Motivo: o j1001 **já é a NF mista** que separa 1124(→Fornecedores) de 1902(→conta-da-operação) — só falta o no_payment p/ a 1902 baixar a ATIVA; criar journal paralelo seria redundante. Efeito GLOBAL e intencional (todo retorno de serviço de industrialização baixa 5101010001 = fecha o regime). **Premissa-chave:** a conta de compensação 51010xx vem do `account_no_payment_id` do **JOURNAL**, NÃO da posição fiscal (a operação não tem campo de fp — verificado ao vivo). IDs/roteamento/dry-run: `PROPOSTA §3`.
    - 🔴 **v2.6 (2026-06-02, EXPERIMENTO PROVADO — `ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`):** a premissa "o j1001 já separa 1124(→Fornecedores) de 1902 — só falta o no_payment" está **REFUTADA**. NF-teste mista postada/excluída com `no_payment=22800`: a 1902 **NÃO baixou** a ATIVA (NET 5101010001=0); o `FORNECEDORES` do serviço (1124) **absorveu** a 1902 (NET −120,05 = total), espelho exato do `R2` da saída. ⇒ **G5a CONVERGE com o G4: a 1902 (entrada) precisa vir em DOCUMENTO SEPARADO do serviço** — o `no_payment` no j1001 **sozinho** é inerte em NF mista. Mesma decisão fiscal (Contadora) resolve os 2 lados. Estrutura real: **0/1600 ENTSI tocam a ATIVA**; 1124→op **1917**, 1902→op **2027** (autocancela em 1150100011); op 3252 recompute >400s (lento, normal).
  - **L5b (não re-inflar estoque) — ✔v2.1 RECONCILIADO (POR LINHA, config)**: a linha **1902 NÃO pode gerar stock.move**. Governado por **`l10n_br_movimento_estoque`** da operação, que é **por LINHA** (`account.move.line.l10n_br_operacao_id`; 95 ops já usam `False`). → setar a operação da linha 1902 com `movimento_estoque=False` suprime o stock.move **sem separar NF nem DEV**. **Op 3252 criada** para isso. **Resíduo ÚNICO a confirmar no piloto**: que a NF mista gere picking só das linhas `movimento_estoque=True` (1124/1903), pulando a 1902. *(Corrige a versão anterior que dizia "por cabeçalho / pode exigir separar NFs / DEV".)*

---

## 3. Prova de fechamento (✔v2 — baixa única; caso com sobra)

Remessa: insumos `I = Ic (consumido) + Is (sobra)`; valor agregado `S`. Invariante fiscal: `valor 5902 = valor 5901` (Ic) e `valor 5903 = Is`.

| Conta FB | Remessa (Et.1) | Retorno 1902 (Ic) | Retorno 1124 (S) | Retorno 1903 (Is) | Final |
|---|---:|---:|---:|---:|---:|
| `5101010001` Remessa Ativa | +I | −Ic | — | −Is | **0** ✅ |
| `1150100002` Estoque insumos | −I | — | — | +Is | **−Ic** (só consumidos saíram) |
| `1150100007` PA | — | +Ic | +S | — | **+(Ic+S)** |
| `2120100001` Fornecedores LF | — | — | −S | — | **−S** (a pagar serviço) |

`5101010001` **zera** (+I−Ic−Is, com I=Ic+Is). PA entra por `Ic+S` (consumidos + serviço) — **sem double-count** (Is volta ao estoque, NÃO entra no PA; Ic vira PA, NÃO re-entra estoque). Espelho LF: `5101020001 PASSIVA` zera; receita serviço +S; estoque LF impacto-equity zero.
> Condição: (1) `1902` baixa **exatamente Ic** e não gera stock.move; (2) PA valorado por `Ic+S` (AVCO via NF); (3) `1903` baixa Is contra estoque.

---

## 4. Levers — o que configurar

| # | Operação | Lever | Viabilidade | Status |
|---|---|---|---|---|
| L1 | LF estoque (SVL) | repoint categorias LF → valoração terceiros (desenho A: input/output=transitórias) | config | ✅ validado **só ajuste simples**; re-testar fluxo entrada+MO (Fase 2) ✔v2 |
| L2 | LF entrada física | pt64 `dst=31092` | config+processo | 🔧 |
| L3 | LF MO / conta PRODUÇÃO | `1150100004` transitória vs terceiros | ❓Contador / Fase 2 | 🔧 |
| L4 | LF retorno (5902→baixa PASSIVA) | **v2.5:** EXPERIMENTO provou que no_payment NÃO baixa a 5902 em NF mista (CLIENTES absorve). **Caminho = opção (b): 5902 em NF SEPARADA** → journal c/ no_pay 26667 (`PROPOSTA §4`) | ✅ **APROVADO** (Contadora 2026-06-02) | 🟢 a implementar (§6) |
| **L5a** | FB entrada: NF credita `5101010001` | **v2.6 (PROVADO):** no_payment no j1001 **sozinho NÃO baixa** em NF mista (FORNECEDORES do serviço absorve a 1902). **Converge com L4/G4: a 1902 em NF SEPARADA** do serviço | ✅ **APROVADO** (= a do G4, 2026-06-02) | 🟢 a implementar (§6) |
| **L5b** | FB entrada: `1902` não re-inflar estoque | `l10n_br_movimento_estoque=False` na operação da linha 1902 (**op 3252** criada) — **POR LINHA ✔v2.1** | **config** (resíduo: confirmar picking da NF mista no piloto) | 🟠 |
| L6 | FB entrada física | rotear DFe → pt52 (`src=26489`) | config+mapeamento CFOP→pt | 🔧 |
| — | FB saída (remessa) | já correto | — | ✅ |

---

## 5. Decisões / verificações pendentes
1. **Conta**: confirmar família `51010xx`/`51020xx` (fiscal). Par net-zero da **valoração SVL da LF** — `1150200001/1150200002` (⚠️ colisão com server action 1899) vs **par dedicado** (rastreabilidade). E desenho **(A) vs (B)** da Etapa 2 (fechar `1150100011`). ✔v2 → **✔v2.2 Contadora confirmou família 51010xx + Opção A (Ativo→Ativo); SVL Design A já vivo na entrada LF (Etapa 2).**
2. **L5b ✔v2.1 RESOLVIDO (config, por linha)**: op 3252 (`movimento_estoque=False`) na linha 1902. Único resíduo: confirmar no piloto que a NF mista gera picking só das linhas `movimento_estoque=True` (1124/1903).
3. **L4**: granularidade por-linha (5902 baixar PASSIVA na mesma NF do 5124). ✔v2
4. ~~Tributação 5124 ICMS~~ → **RESOLVIDO ✔v2.1**: NF real NÃO tem ICMS (CST51 suspenso; CBS/IBS/PIS/COFINS já tratados). **Não mexer em imposto.** Resta só o controle do **prazo de 180 dias** da suspensão CST51 (5901).
5. **Conta PRODUÇÃO** `1150100004` (L3) e **invariante** "LF só agrega consu+serviço".
6. **Regularização** dos acumulados: `5101010001` R$ 60,8M (FB) + R$ 8,67M (LF, journal PERDAS), double-count estoque (R$ 785k/produto), `1150100011` −R$ 1,49 bi. Modo A/B/C.
7. **AVCO do PA**: garantir que a NF de retorno declare price_unit do PA = `Ic+S`. ✔v2
8. **Conta RETORNO `5101010002`** (R$0): usar para a perna de retorno ou baixar direto a REMESSA? ✔v2 → **✔v2.2 RESOLVIDO: baixar a REMESSA direto** (`5101010001`/`5101020001`) — desenho confirmado pela Contadora; a perna RETORNO (`...02`) NÃO entra.

---

## 6. Requisitos da Contadora (APROVAÇÃO 2026-06-02) — desenho da implementação 2-NF

A Contadora **aprovou separar em 2 NF** (`MATERIAL_CONTADORA §0`) com **3 requisitos**. Cada um mapeia a um achado já provado (`ACHADOS §G/§H/§I`) e à **Forma 2** (nosso pipeline deriva a 2ª NF):

| Req | Exigência da Contadora | Como atender (provado) | Esfera |
|---|---|---|---|
| **R1** | NF de retorno emitida **automática** (= a inclusão dos componentes na NF hoje) | a 2ª NF (5902/1902) é derivável da **BoM do PA** (9/9 batem) → o pipeline explode/emite automaticamente (como já faz na remessa) | SAÍDA LF |
| **R2** | DFe da NF de retorno escriturado **automático junto** com a NF de industrialização | a entrada já é `DFe→PO→invoice` automática (3087 casos) → estender p/ os 2 DFes (serviço+insumos) vinculados | ENTRADA FB |
| **R3** | **vínculo** entre as 2 NFs (retorno↔industrialização) | `account.move.referencia_ids` (refNFe) na saída + `dfe_id`/`invoice_origin=PO` na entrada | RASTREABILIDADE |

**Forma 1 (subcontratação nativa) DESCARTADA** — configurada (153 BoMs subcontract, subcontratante=LF) mas **dormente** (0 pickings resupply pt75; `ACHADOS §I`). **Forma 2 = nosso pipeline deriva a 2ª NF.**

**Gaps de execução (a resolver na implementação — detalhe em `PROMPT_PROXIMA_SESSAO`):**
1. **Journal de retorno-insumos** (LF sale) com `no_payment=26667` (PASSIVA `5101020001`) — **NENHUM** journal sale LF aponta a PASSIVA hoje (criar/repontar; mudar j1002 atinge o retrabalho). Lado FB: `no_payment=22800` (ATIVA) no j1001 ou journal dedicado.
2. **Onde emitir a 2ª NF:** (A) customizar `create_invoice` do CIEL IT (fornecedor) **ou (B) nosso pipeline** (recomendado — mais controle). → resolvido pelo desenho §6.1 (wizard nativo + split em draft).
3. **Veículo da NF de insumos** (simbólica, sem movimento físico) + CFOP **5902/1902** (não 5949). → resolvido pelo desenho §6.1 (account.move direto, sem picking).
4. **AVCO Ic+S (G8)** — medir no piloto (`ACHADOS §D`).
5. **Pontos de código que assumem 1 NF** — `ACHADOS §E` (orchestrator `inventario_pipeline`, Skill 7/8, `recebimento_lf_odoo_service`, ETL `faturamento_service`).

### 6.1 Desenho E2E da EMISSÃO 2-NF (v3.1, sessão 9 — 🟡 PROPOSTA, validar com Rafael)

> Grounding READ-only sessão 9 (`s9_grounding_desenho.py` + código da server action 1512) — `ACHADOS §sessão 9`. **v3.1 = v3.0 revisada por painel adversarial 3 lentes** (mecanismo/fiscal/operacional; 30 findings, veredicto unânime AJUSTES_NECESSARIOS — nenhuma refutação da espinha). Princípio do Rafael: **replicar a forma automática de puxar os componentes** (expansão nativa da BoM = R1 literal) **em 2 docs separados**, com a NF do serviço **puxando** a NF de retorno dos insumos.

**Premissa confirmada (2 camadas — por que 2 docs):**
- **Física (stock.move): GRANULARIZA por linha** — `l10n_br_movimento_estoque` é da operação, atribuída POR LINHA (`account.move.line.l10n_br_operacao_id`); op 3252 já criada p/ a 1902. ⇒ o lado "não re-inflar estoque" se resolve por item da NF.
- **Contábil (contrapartida/baixa da compensação): NÃO granulariza por linha** — o `no_payment` é do JOURNAL (documento); em NF mista o CLIENTES/FORNECEDORES do serviço **absorve** a contrapartida das linhas simbólicas (provado 2×: sessão 5 saída, sessão 6 entrada/R-UNIF; a operação NÃO tem campo de conta — 133 campos verificados). ⇒ a baixa da 5101010001/5101020001 **exige documento separado**. É a razão de ser das 2 NFs.

**Escopo desta versão:** ciclo SEM sobras (piloto consome 100%). O desenho-alvo geral inclui a perna **5903** (sobras — tem movimento físico real; 3º documento via picking próprio) — adicionar antes do rollout.

**Fluxo da emissão (Etapa 4, LF→FB):**
| # | Passo | Mecanismo | Fonte/prova |
|---|---|---|---|
| 0 | Operador cria **1 picking só com o PA** (como hoje), **NÃO libera faturamento** + **isolamento técnico**: `picking.robo` fora da partição 1..11 e `refaturar_se_cancelado=False` | 3 alavancas: domain do robô exige `liberado_faturamento=True` E `robo=N` (1..11); robô pula picking c/ `invoice_id` não-cancelado (⚠️ guard comentado `# REGRA DESATIVADA` no code — não confiar só nele). POP operacional formalizado (quem NÃO libera) | código 1512 (sessão 9) + painel |
| 1 | Automação detecta picking done do regime — **discriminador: origem `31093` / pt98 / whitelist do piloto** — e chama o **wizard nativo** `stock.invoice.onshipping` (`create({company_id, journal_id=j847})` → `create_invoice()`) | mesma chamada do robô ⇒ NF mista nasce em DRAFT com expansão automática da BoM (R1 literal). **PRÉ-REQUISITO: pt98 hoje tem `invoice_move_type=False` e `tipo_pedido=False`** (verificado) → configurar `invoice_move_type='out_invoice'` (plano B: clonar pt66 com src=31093). ⚠️ Expansão só foi provada em pt66 — assert no GATE 1 | código 1512; BoM 9/9 (`ACHADOS §G`); painel (pt98) |
| 2 | **Split em DRAFT** (ordem fixa): remover linhas 5902 da NF original → criar NF-insumos no **journal RETIND** com as 5902 → **write `price_unit` = valores da REMESSA (RPI)** → recompute fiscal → **RE-ASSERT linha a linha** (preço sobrevive? 5902 não re-expandiu na NF-serviço?) | **Spec RETIND** (LF sale): `l10n_br_no_payment=True` **+** `account_no_payment_id=26667` (precedentes j1002/j1003 têm AMBOS — boolean é campo independente) **+ `l10n_br_tipo_pedido` VAZIO** (sempre setado por nós; evita o search `limit=1` do robô rotear retrabalho p/ o RETIND). NF-insumos = `account.move` direto, sem picking | V3 (expansão valora por `lst_price`, NÃO remessa ⇒ forçar obrigatório); painel (boolean + ordem + re-expansão) |
| 3 | `onchange impostos` + `action_post` das 2 — **imediatamente antes da transmissão** (janela de segundos, não minutos: NF-serviço posted em j847 é visualmente idêntica às VND que o operador transmite hoje) | contrapartidas: serviço `D CLIENTES (S) / C receita+tributos`; insumos `D 5101020001 PASSIVA (Ic) / C [transitória]` = **a baixa**. ⚠️ recompute via XML-RPC já mediu **>400s** → timeout ≥600s + cada passo idempotente (pesa pró-server-action) | **GATE 0 (s8d) prova antes do piloto**; painel |
| 4-5 | **Saga de transmissão** (Playwright; máquina de estados persistida por picking): pré-validar NF-insumos → transmitir **serviço** → `cstat=100` → gravar `referencia_ids` (chave do serviço + da RPI) na NF-insumos → transmitir **insumos** → `cstat=100` | robô tem transmissão **DESATIVADA** (código). Em rejeição da NF-insumos: retentativas + correção em draft + **deadline < janela de ~24h de cancelamento da NF-serviço**. ⚠️ **NF só-5902 é INÉDITA na SEFAZ** (SARET autorizada = 5949; única 5902 está cancelada) — precedente de FORMA = a própria RPI/5901 (CST 50, autorizada rotineiramente); rejeição = cenário normal, não falha do desenho | sessão 9 + painel (V4 corrigido) |

**Veículo da automação — ✅ DECIDIDO: SERVER ACTION (Rafael, 2026-06-13).** Roda server-side ⇒ elimina o timeout do recompute >400s; gatilho via **cron** (padrão dos 12 robôs 1512; `base.automation` quase não usado no ambiente — só 1). Precedente: **264 server actions `state=code`** (2 do Rafael — 1952/1953); uid 42 cria/edita SA+automation+journal+picking_type (verificado 13/06). ⚠️ **Dívida de manutenção OBRIGATÓRIA** (o código vive no banco do Odoo, não no Git): (a) **script de re-aplicação idempotente versionado** (re-cria a SA via XML-RPC) + (b) **monitor anti-upgrade** (SA custom some em upgrade CIEL IT — precedente DFE NFD). A **transmissão SEFAZ fica FORA da SA** (Playwright nosso, com saga/rollback — o robô 1512 já tem a transmissão desativada). GATE 1 ainda mede o recompute (informa a implementação da SA).

**Resiliência (falha no meio — obrigatório na implementação):** máquina de estados persistida keyed por `picking_id` (retomada idempotente em cada passo); **marcador na NF mista draft** (`ref`/narration "AUTOMACAO-2NF — NÃO POSTAR/TRANSMITIR" + activity); varredura "mista draft do regime > N min" com alerta; rollback sempre zera `liberado_faturamento` e garante `refaturar_se_cancelado=False` (senão o robô re-fatura NF cancelada).

**Gates até o faturamento (ordem, sem SEFAZ até o GATE 2):**
- **GATE 0** — ✅ **EXECUTADO E APROVADO (2026-06-13)** (`s8d` v3.1, journal B com `l10n_br_no_payment=True`): split contábil em journals de teste provou que a NF só-5902 com no_payment **baixa a PASSIVA `5101020001` (`D 8,37`, total=0)** e a NF só-5124 fica limpa (`D CLIENTES / C serviço+tributos`). Sem SEFAZ, postado e deletado (zero rabo). **Aprendizado:** redirecionamento só aparece pós-`action_post` (draft mostra CLIENTES); resíduo = conta de contrapartida das 5902 (transitória vs terceiros `1150200001`) p/ o GATE 1. Detalhe: `ACHADOS §"GATE 0 EXECUTADO"`.
- **CONFIG** — ✅ journal RETIND `id=1083` criado (mantido). ⚠️ **pt98 REVERTIDO** — GATE 1 provou que o picking de retorno sai por **pt66 → Clientes(5)**, não pt98→26489. Detalhe: `ACHADOS §"CONFIG APLICADA"` + `§"GATE 1 EXECUTADO"`.
- **GATE 1** — ⚠️ **EXECUTADO (2026-06-13), 1 BLOQUEADOR** (`s11_gate1_emissao.py`; NF draft revertida, PA preservado em 31093). **3 camadas:** (1) picking de retorno = **pt66 src override 31093→dst 5 Clientes** (pt98/26489 falha a operação fiscal); (2) **🔑 `create_invoice` via XML-RPC exige `allowed_company_ids=[5]` LF-ONLY** (com `[1,5]` pega a conta income da FB → "empresas incompatíveis"); recompute=48s; (3) **🔴 a expansão dos 5902 NÃO ocorre p/ o piloto 4870112** (NF só com 1×5124) — falta **BoM `subcontract`** (o azeite tem a 14794; é o GATILHO da expansão no CIEL IT, corrige sessão 7 §I). **Próximo: criar a BoM subcontract do shoyu → re-rodar.** Detalhe: `ACHADOS §"GATE 1 EXECUTADO"`.
- **GATE 1** (piloto, draft-only, tudo deletável) — asserts: (a) wizard aceita o picking pt98 configurado; (b) nº linhas 5902 == BoM do 4870112 (16 comps); (c) CFOPs (5124/5902) + CST (51/50) + ops por linha iguais às NFs autorizadas de referência; (d) pós-onchange a NF-serviço NÃO re-expande as 5902; (e) `price_unit` forçado == RPI/2026/00245 (11 casas) pós-recompute; (f) robô não seleciona o RETIND p/ nenhum picking existente; (g) write de `referencia_ids` em move posted funciona.
- **GATE 2** (piloto, SEFAZ — irreversível, go duplo) — **PRÉ-CONDIÇÕES**: filtro ETL deployado (`faturamento_service` ignora NF do journal RETIND — ⚠️ `total≈0` NÃO é filtro confiável: `amount_untaxed` carrega valor) + contenção lado FB (avisar fiscal: **NÃO escriturar os 2 DFes** até a Etapa 5 — op default 2027 re-infla estoque) + POP de transmissão (auditar `write_uid` das últimas transmissões p/ confirmar o ator) + runbook de rollback parcial (3 saídas: retransmitir insumos corrigida / cancelar serviço na janela 24h via UI / estorno contábil). Medição: `Δ5101020001(LF) = −278,56` (baixa Ic), refNFe presente, j847 íntegro, **zero `FaturamentoProduto`/PO espúrios**.

**Resíduos conhecidos (pós-piloto, antes do rollout):** G8 AVCO Ic+S na entrada FB (medir no piloto, `ACHADOS §D`) · perna **5903** (sobras) · mapeamento insumo→preço-da-remessa p/ ciclos com N remessas (par remessa↔retorno por ciclo/lote via refNFe) · controle do prazo **180 dias** CST 50 (alerta ~150d; backlog R$60,8M = `GOALS G9`) · pontos de código 1-NF (`ACHADOS §E`) · Etapa 5 (escrituração 2 DFes na FB).

> Mecanismo/provas: `ACHADOS §A–§I` + `§sessão 8` + `§sessão 9`. Próximo passo operacional: `PROMPT_PROXIMA_SESSAO`.

---

## Histórico
| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 2026-05-30 | SOT inicial — ciclo verificado; foco no RETORNO; adota família 51010xx |
| 2.0 | 2026-05-30 | Correções pós-verificação adversarial: baixa única de I (sem double-count); NF de retorno MISTA (5902 CST51 + 5124 ICMS); leg AVCO do PA (Ic+S); L5 separado em L5a(NF=config)/L5b(SVL=dev); desenho SVL-LF em aberto (fechar 1150100011); LF sair do journal PERDAS; intraestadual confirmado; 180d CST51; invariante 5902=5901; Ativo→Ativo supersede CMV |
| 2.1 | 2026-05-30 | Reconciliado: `movimento_estoque` por linha (não cabeçalho); sem ICMS em nenhuma etapa (CST51 + CBS/IBS/PIS/COFINS) |
| 2.2 | 2026-06-01 | **Contadora confirmou Etapas 4-5 + Opção A (Ativo→Ativo, CPV só na venda)**; roteamento G4/G5a mapeado ao vivo (journals/operações/tipo.pedido.diario); spec em `PROPOSTA_CONFIG_RETORNO.md`; resíduo NF mista (cabeçalho×linha) |
| 2.3 | 2026-06-01 | **DECISÃO G5a: ajustar o j1001 existente** (não criar journal novo); premissa fixada: compensação 51010xx vem do `account_no_payment_id` do JOURNAL, não da posição fiscal (operação não tem campo de fp — verificado ao vivo). **Docs reorganizados** (centralização + progressive disclosure): esta SOT = dona do desenho/decisões; `PROPOSTA` = anexo de execução; `README` = índice. Superseded → `HISTORICO/`. |
| 2.4 | 2026-06-01 | **Grounding de EXECUÇÃO (sessão 5, READ-ONLY + 4 lentes adversariais)** — `ACHADOS §"ACHADO 2026-06-01 (sessão 5)"`. **Mecanismo validado ao vivo:** journal = header (campo `l10n_br_tipo_pedido` do journal); `no_payment` = contrapartida das linhas simbólicas (C entrada/D saída), confirmado em j1011/j868/j993. **G5a viável** (sinal validado; resíduo R1). **G4 REFUTADO:** NF mista real → j847 (venda-industrializacao, op 2864), não dev-industrializacao/perda. R$8,68M de insumos sem baixa desde 2026-01. |
| 2.5 | 2026-06-01 | **EXPERIMENTO no_payment (sessão 5, NF-teste postada/excluída — zero sujeira)** — `ACHADOS §sessão 5 R2`. **Opção (a) [no_payment no j847] DESCARTADA:** em NF mista o `D CLIENTES` do serviço (5124) absorve a contrapartida da 5902; o no_payment só substitui o receivable em NF 100%-simbólica. **R1 RESOLVIDO:** a 1902/op 3252 debita a transitória 1150100011 (não o PA); Ativo→Ativo fecha via SVL físico do PA. **G4 caminho = opção (b): 5902 em NF SEPARADA** do serviço → aguarda aprovação FISCAL da Contadora (`MATERIAL_CONTADORA_G4.md`). |
| 2.6 | 2026-06-02 | **EXPERIMENTO ENTRADA (sessão 6, NF-teste postada/excluída — zero sujeira) — R-UNIF PROVADO** (`ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`). `no_payment=22800` no j1001 **sozinho NÃO baixa a ATIVA** numa NF mista de entrada: o `FORNECEDORES` do serviço (1124) absorve a 1902 (NET ATIVA=0, FORNECEDORES=−120,05), espelho do `R2` da saída. **G5a CONVERGE com G4:** a 1902 precisa vir em DOC SEPARADO do serviço — **mesma decisão fiscal (Contadora) resolve os 2 lados**. Estrutura real medida: **0/1600 ENTSI tocam a ATIVA**; 1124→op **1917** (docs diziam 3064/3134), 1902→op **2027** (autocancela); 490 mista / 1060 pura-serviço / 1 pura-1902; op 3252 recompute >400s (lento, normal). |
| 2.7 | 2026-06-02 | **GROUNDING FLUXO 2-NF (sessão 7, READ-only, 5 scripts `s7_*`) — `ACHADOS §"ACHADO 2026-06-02 (sessão 7)"`.** O "COMO" da separação mapeado ao vivo: separação = **composição de linhas** (insumos 5902/1902 já simbólicos, 0 move; PA viaja na linha de serviço 5124↔1124, única com move). Journal = `picking_type.l10n_br_tipo_pedido` (1 picking=1 NF). **3 gaps p/ executar (b):** journal c/ no_payment PASSIVA `5101020001` inexistente; pt98 `tipo_pedido=False`; veículo da NF de insumos simbólica a definir. SARET prova o mecanismo (no_payment em doc total=0) mas é devolução de produto REAL. Anexado ao `MATERIAL_CONTADORA §5`. PA=Ic+S = resíduo do piloto (G8). |
| **2.8** | **2026-06-02** | **CONTADORA APROVOU emitir 2 NF** (`MATERIAL_CONTADORA §0`) + **3 requisitos** (R1 emissão automática · R2 escrituração automática · R3 vínculo — ver **§6**). Caminho (b) confirmado. **Forma 1 (subcontratação nativa) DESCARTADA** (configurada mas dormente, `ACHADOS §I`); **Forma 2 (pipeline deriva a 2ª NF)** = caminho. **Etapas 4/5 DESBLOQUEADAS** → projeto entra na fase de **IMPLEMENTAÇÃO**. Requisitos+gaps em §6; handoff em `PROMPT_PROXIMA_SESSAO`. |
| **3.1** | **2026-06-12** | **Desenho E2E da emissão 2-NF (§6.1)** — sessão 9: hipótese (i) já refutada (sessão 8) → caminho = **wizard nativo chamado por nós + split em DRAFT** (NF do serviço puxa a NF de insumos, princípio Rafael). Grounding ao vivo: robô **não transmite** SEFAZ (code 1512), expansão valora por `lst_price` (≠ remessa ⇒ forçar price_unit), 3 alavancas de isolamento do robô. Revisado por **painel adversarial 3 lentes** (30 findings → v3.1): CST corrigido (5901/5902=**50**; 5124=**51**), spec RETIND completa (`l10n_br_no_payment=True`+conta+tipo_pedido vazio), pt98 config = pré-req GATE 1, ETL = pré-condição GATE 2, saga SEFAZ c/ janela 24h, NF só-5902 é inédita (precedente de forma = RPI). **🟡 PROPOSTA — aguarda validação Rafael → GATE 0.** |

## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: SOT — Operações de Industrialização FB↔LF (fonte única)
