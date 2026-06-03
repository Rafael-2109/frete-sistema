# PLANO DE EXECUÇÃO — Industrialização FB↔LF

> ⚠️ **SUPERSEDED (2026-05-30)** — Plano preliminar (config de categoria LF → 1150200001 + 5 etapas). Superado por **`GOALS.md`** (plano atual com métricas) + **`SOT_OPERACOES.md`** (desenho). O Bloqueador 1 (teste controlado) foi executado ✅ (`T-PASSO0-TESTE`). Mantido como histórico.

> Plano de ação concreto que implementa a `DIRETRIZ.md` sobre a infra já criada. Desenho-alvo: `00_FLUXO_ATUAL_VS_IDEAL.md` §3. Mecanismo: `ACHADOS_TECNICOS.md`.
> **Pré-condição de início**: os 16 insumos do piloto de volta em FB/Estoque (gatilho de retomada — `DIRETRIZ.md` §5).

---

## Passo 0 — Configurar as contas de terceiros na LF (a base de tudo)

Como a LF não tem estoque próprio, ajustar as **contas de estoque das categorias no contexto da LF** (campos `ir.property`, company-dependent) para o par de terceiros:

| Conta da categoria (contexto LF) | Apontar para |
|---|---|
| Valoração de Estoque (`property_stock_valuation_account_id`) | **1150200001 MATERIAL EM TERCEIROS** |
| Entrada de Estoque (`property_stock_account_input_categ_id`) | **1150200002 ( − ) MATERIAL DE TERCEIROS** |
| Saída de Estoque (`property_stock_account_output_categ_id`) | **1150200002 ( − ) MATERIAL DE TERCEIROS** |

**Antes de aplicar:**
1. Levantar **todas as categorias** que os produtos da industrialização usam na LF (PA, BATELADA/semi, embalagens, químicos, MP) — a config vale para todas, pois tudo na LF é terceiros.
2. Validar com o **Contador** o par de contas + o tratamento da conta de Produção/Elaboração (1150100004) — ver perguntas abaixo.
3. Aplicar **no contexto da LF** (não afeta FB/CD/SC).

Resultado esperado: toda movimentação de estoque na LF passa a lançar **net-zero em terceiros** (D 1150200001 / C 1150200002 na entrada; inverso na saída), sem inflar ativo próprio.

---

## As 5 etapas (fluxo físico + fiscal + contábil)

| # | Etapa | Empresa | Picking type | Origem → Destino | NF / CFOP | Contábil |
|---|---|---|---|---|---|---|
| **1** | Remessa de componentes | FB | **53** FB/SAI/IND | FB/Estoque (8) → Em Trânsito Ind. (26489) | NF saída FB **5901** (fp 25) | FB: D 1150200001 MATERIAL EM TERCEIROS / C estoque normal (reclassifica p/ "em terceiros") |
| **2** | Recebimento na LF | LF | **64** LF/RECEB/IND | Em Trânsito (26489) → **LF/Materiais de Terceiros (31092)** | DFe entrada LF **1901** (fp 131) | LF: net-zero em terceiros (Passo 0) — sem inflar ativo LF |
| **3** | Ordem de Produção | LF | 34/36 (MO) | **31092** → Pré-Produção → **LF/PA de Terceiros (31093)** | — (interno) | LF: consumo/produção transita por Produção e zera; tudo em terceiros |
| **4** | Retorno LF→FB | LF | **98** LF/SAI/IND/RET | 31093 → Em Trânsito (26489) | NF saída LF **5124** (PA) + **5902** (consumidos) + **5903** (sobras) | LF: saída net-zero terceiros |
| **5** | Recebimento na FB | FB | **52** RECEB/FB/IND | Em Trânsito (26489) → FB/Estoque (8) | DFe entrada FB **1124** + **1902** + **1903** | **FB: baixa — ver abaixo** |

**O par "Em Trânsito Industrialização" (26489) deve zerar a cada ciclo** (tudo que sai na Etapa 1 entra na 2; tudo que sai na 4 entra na 5).

### Pontos por etapa
- **Etapa 1**: pt 53 já correto. Validar que a NF 5901 carrega valor (amount_untaxed) e que a FB reclassifica para "em terceiros".
- **Etapa 2**: usar **picking físico (pt 64)**, **NÃO** DFe→PO (a entrada de industrialização não é compra). Hoje pt 64 tem `dst=LF/Estoque (42)` → **corrigir para 31092**. A valoração cai em terceiros pelo Passo 0.
- **Etapa 3**: MO criada **manualmente** pelo PCP LF (não depender de MTO cross-company). Consome BoM 3695 (→ sub-MO 3646 da BATELADA). Destino do PA = **31093**.
- **Etapa 4**: NF de retorno com **3 CFOPs por linha** (5124 PA / 5902 consumidos / 5903 sobras). O CIEL IT mapeia CFOP por linha.
- **Etapa 5 (crítica — o passivo)**: o DFe de retorno deve cair no **pt 52** (não no pt 1 genérico). Os **componentes (1902) devem ser simbólicos / baixar a conta de terceiros na FB**, **NÃO** somar ao Ativo Estoque. É aqui que mora o passivo de **R$ 785.569,62**. **A FB tem estoque próprio → exige tratamento próprio (decisão do Contador).**

---

## Perguntas pendentes ao Fiscal/Contábil

Do relatório (`00_FLUXO_ATUAL_VS_IDEAL.md` §5) + desta sessão:

1. Confirmar o desenho fiscal das 5 etapas (CFOPs 5901/1901; 5124+5902+5903 / 1124+1902+1903)?
2. **Passo 0**: o par `1150200001 / 1150200002` nas contas de categoria da LF é o tratamento correto para "material de terceiros sem patrimônio na LF"? E a conta de **Produção/Elaboração** (1150100004) — fica transitória ou também vira terceiros?
3. Conta correta da NF de retorno (5124/5902/5903) e a baixa na FB (Etapa 5) que **não** infla o estoque da FB.
4. Regularização do passivo já postado (**R$ 785k+**): modo **A** (reclassificação D MATERIAL EM TERCEIROS / C MAT. EMBALAGEM, sem DRE), **B** (ajuste a menor, reduz resultado), ou **C** (ajuste de exercícios anteriores, PL)?
5. Tratamento do saldo de R$ −1,49 bi em `1150100011 RECEBIMENTO FÍSICO FISCAL` (conciliar/zerar?).

---

## Bloqueadores antes de executar em volume (resolver primeiro)

1. **Validar o approach por teste controlado** — trocar as contas de UMA categoria na LF e confirmar, num movimento real pequeno, que gera net-zero (`D 1150200001 / C 1150200002`) **e** que a MO consome corretamente. Hoje está **raciocinado, não testado**.
2. **Definir o tratamento do lado FB (Etapa 5)** com o Contador — a FB tem estoque próprio; a baixa dos componentes do retorno (passivo de **R$ 785k**) **ainda não tem mecanismo**.

## Checklist de execução (após o "go" do Rafael)

- [x] 16 insumos de volta em FB/Estoque (gatilho atingido — 2026-05-29).
- [x] **Bloqueador 1 (entrada/saída)**: teste controlado ✅ PASSOU (2026-05-29, categ 104 / 4870110) — net-zero terceiros confirmado (`D 1150200001 / C 1150200002`). Ver `T-PASSO0-TESTE-resultado.md`. **Falta Fase 2 (MO consumo→produção)** após decisão Contador sobre `1150100004`.
- [ ] **Bloqueador 2**: tratamento do lado FB (Etapa 5) definido com Contador.
- [ ] Passo 0: levantar categorias LF + validar contas com Contador + aplicar (contexto LF).
- [ ] Corrigir pt 64 → `dst=31092`.
- [ ] Etapa 1: remessa 5901 (pt 53) — validar valor e reclassificação FB.
- [ ] Etapa 2: recebimento físico Em Trânsito → 31092 (pt 64) — validar net-zero terceiros.
- [ ] Etapa 3: MO manual (BoM 3695→3646), PA → 31093.
- [ ] Etapa 4: NF retorno 5124+5902+5903 (pt 98).
- [ ] Etapa 5: DFe FB → pt 52; validar baixa (sem inflar estoque FB) — **com Contador**.
- [ ] Validar: Em Trânsito (26489) zera; 1150200001 zera no fim do ciclo; estoque FB não infla.
- [ ] Documentar cada etapa executada (convenção `T{NN}-resultado.md`).
