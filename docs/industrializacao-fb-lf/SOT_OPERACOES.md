# SOT — Operações de Industrialização FB↔LF (fonte única)

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

### Tributação por CFOP (✔v2 — NF de retorno é MISTA)
| CFOP | O que é | ICMS | Observação |
|---|---|---|---|
| 5901→1901 | Remessa dos insumos (da FB) | **suspenso CST 51** | valor = custo dos insumos; prazo legal de retorno (**180 dias** ❓Contador) |
| 5902→1902 | Retorno **simbólico** dos insumos **utilizados** | **suspenso CST 51** | **valor = valor da remessa 5901** (invariante de fechamento ✔v2) |
| 5903→1903 | Retorno dos insumos **não utilizados** (sobra) | **suspenso CST 51** | valor = custo da sobra |
| 5124→1124 | **Industrialização efetuada** = valor agregado LF (serviço + materiais próprios LF) | **SEM ICMS** ✔v2.1 (confirmado em NF real: CBS/IBS/PIS/COFINS + "INDUSTRIALIZACAO", zero ICMS) | **NÃO é "o PA"** ✔v2; é o valor agregado |

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

### Etapa 4 — LF SAÍDA / Retorno (NF MISTA 5902+5903+5124) — 🔴 BLOQUEADO POR DESENHO (v2.4)
> 🔴 **v2.4 (2026-06-01, grounding sessão 5 — `ACHADOS`):** o plano abaixo (Lever L4: criar journal LF + `tipo.pedido.diario(dev-industrializacao/perda)`) está **REFUTADO**. A NF de retorno **real** é MISTA e cai em **j847 VENDA PRODUÇÃO** (header `venda-industrializacao`, op 5902 = **2864**), não por `dev-industrializacao`/`perda` (que já têm journal: j1002/j1003) nem em PERDAS. Logo a NF mista **não baixa a PASSIVA** hoje. **Fechar G4 exige decisão FISCAL da Contadora** — **EXPERIMENTO (sessão 5) provou que a opção (a) [no_payment no journal] NÃO baixa a 5902 em NF mista** (o `D CLIENTES` do serviço absorve). **Caminho = opção (b): emitir a 5902 em NF SEPARADA** do serviço (simbólica pura → no_payment baixa a PASSIVA, como na perda j1003). Detalhe: `PROPOSTA §4` + `MATERIAL_CONTADORA_G4.md`.
- **Física**: pt98 (hoje usa genéricos "Ordens de Entrega"/"VENDA PRODUÇÃO").
- **NF de retorno (montagem por linha ✔v2):**
  - **5902 (insumos utilizados, =valor remessa, CST51)**: simbólico → **`D 5101020001 (PASSIVA) / C [par net-zero/terceiros — NUNCA resultado]`** ✔v2 (baixa a obrigação LF). Contrapartida = a mesma camada net-zero da Etapa 2 (def. §5).
  - **5903 (sobras, CST51)**: idem, baixa parcial da PASSIVA + devolve fisicamente.
  - **5124 (valor agregado LF, SEM ICMS ✔v2.1)**: `D CLIENTES / C 3101030001 SERVIÇOS DE INDUSTRIALIZAÇÃO (S) + C CBS/IBS/PIS/COFINS a recolher`. ✅ a receita de serviço já espelha o `2120100001 FORNECEDORES` da FB.
- ⚠️ **LF deve usar SÓ a PASSIVA `51020xx`** — hoje a LF também debita `5101010001 (ATIVA)` via journal **"SAÍDA - PERDAS"** (+R$ 8,67M) ✔v2 → corrigir operação/journal de saída LF p/ não cair em PERDAS.
- **Lever L4** ~~(✔v2.2 "caminho mapeado": criar journal LF sale + `tipo.pedido.diario(LF, dev-industrializacao/perda)` p/ a 5902 op 850)~~ 🔴 **REFUTADO v2.4** (ver nota no topo desta Etapa 4 + `ACHADOS §sessão 5`): a NF mista de retorno cai em **j847/venda-industrializacao** (op 5902 = **2864**, não 850/dev-industrializacao); aquele plano é **inerte**. ✔v2.1 confirmado: granularidade POR LINHA (5902/5124 coexistem na mesma NF, operações distintas) — **mas o journal é UNO (do cabeçalho)**. Fechar G4 = 1 das 3 opções (`PROPOSTA §4`), decisão Rafael+Contadora. Obrigação do piloto a baixar = **R$ 278,56** (ENTIN 737062).

### Etapa 5 — FB ENTRADA / Recebe retorno (1124+1902+1903) — 🔴 PRINCIPAL
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
| L4 | LF retorno (5902→baixa PASSIVA) | **v2.5:** EXPERIMENTO provou que no_payment NÃO baixa a 5902 em NF mista (CLIENTES absorve). **Caminho = opção (b): 5902 em NF SEPARADA** → journal c/ no_pay 26667 (`PROPOSTA §4`) | **aprovação FISCAL** (Contadora) | 🔴 aguarda Contadora |
| **L5a** | FB entrada: NF credita `5101010001` | **v2.6 (PROVADO):** no_payment no j1001 **sozinho NÃO baixa** em NF mista (FORNECEDORES do serviço absorve a 1902). **Converge com L4/G4: a 1902 em NF SEPARADA** do serviço | **aprovação FISCAL** (Contadora, = a do G4) | 🔴 converge G4 |
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
