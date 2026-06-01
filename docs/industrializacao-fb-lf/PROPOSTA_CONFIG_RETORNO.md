# PROPOSTA — Config das operações + journals de RETORNO (G4 LF + G5a FB)

> Proposta concreta (**read-only/design — nenhuma escrita feita no Odoo**) para fechar o ciclo contábil do retorno: a LF baixar a PASSIVA `5101020001` (G4) e a FB baixar a ATIVA `5101010001` (G5a). Base: grounding ao vivo 2026-06-01 (`inv_cfg_g4_g5a`, `inv_entsi`, `inv_roteamento_completo`, `inv_etapa4_*`). ⚠️ **Config GLOBAL** (afeta todos os retornos de industrialização) — exige OK Rafael + dry-run antes de qualquer escrita; o piloto **testa**.

---

## 0. CONFIRMAÇÃO DA CONTADORA (2026-06-01) — desenho validado

A Contadora **confirmou** o desenho das **Etapas 4 e 5** do SOT e definiu a **Opção A (Ativo→Ativo)** para o custo dos insumos no retorno:

- **Insumos consumidos incorporam-se ao custo do PA** (`D 1150100007 PRODUTO-ACABADO / C 5101010001`) — **Ativo→Ativo**, NÃO CMV/CPV.
- **CPV só é reconhecido na venda final** do PA pela FB ao cliente. **Não há CPV no retorno.**
- Pergunta original dela ("o custo de produção vai a `D CPV / C Estoque em terceiros`?") → respondida: **não**; o picking valora o PA no Ativo (1150100007); a baixa do "estoque em terceiros" (= conta `5101010001`, controle da remessa) é Ativo→Ativo via a NF.
- Journal usado **hoje** na entrada FB das notas de industrialização da LF: **`ENTRADA - SERVIÇO DE INDUSTRIALIZAÇÃO` (j1001)**.

> Validação factual (ground-truth `ENTSI/2026/05/0126`): hoje a entrada já lança **tudo no Ativo** (PA + MP + EMB), **zero CPV** — confirma a Opção A. O problema atual é (a) **double-count** (insumos re-entram no estoque) e (b) o journal **não baixa 5101010001**. A proposta corrige ambos sem nunca tocar CPV.

---

## 1. Mapa de roteamento ATUAL (verificado ao vivo 2026-06-01)

Cadeia: `operação → tipo_pedido(_entrada) → tipo.pedido.diario(empresa) → journal → account_no_payment_id`.

### FB (company 1) — ENTRADA do retorno
| Linha | CFOP | Operação | `tipo_pedido_entrada` | → Journal | `no_payment` | Avaliação |
|---|---|---|---|---|---|---|
| 1902 insumos | 1902 | 2807 / 2027 / **3252** | `industrializacao` / `serv-industrializacao` | **j1001 ENTSI** | **(VAZIO)** | 🔴 não baixa 5101010001 |
| 1124 serviço | 1124 | 3064 / 3134 | `serv-industrializacao` | (sem registro → default) | — | ⚠️ confirmar |
| 1903 sobras | 1903 | 838 / 3120 | `retorno` | j1007 ENTRADA-RETORNO | 5101020002 (PASSIVA RETORNO) | 🔴 conta errada (FB usa ATIVA) |

### LF (company 5) — SAÍDA do retorno
| Linha | CFOP | Operação | `tipo_pedido` | → Journal | `no_payment` | Avaliação |
|---|---|---|---|---|---|---|
| 5124 serviço | 5124 | 849 / **2702** | `venda-industrializacao` | **j847 VENDA DE PRODUÇÃO** | (VAZIO) | ✅ serviço OK (vai p/ CLIENTES + 3101030001) |
| 5902 insumos | 5902 | 850 | `dev-industrializacao` | **(sem registro LF → default)** | — | 🔴 não baixa 5101020001 |
| 5903 sobras | 5903 | 2711 | `perda` | **(sem registro LF → default)** | — | 🔴 cai em PERDAS/ATIVA (5101010001) |

> ⚠️ Hoje a LF, quando cai no journal `SAÍDA - PERDAS` (j1003, no_payment=5101010001 **ATIVA**), debita a ATIVA da LF (+R$ 8,67M acumulado) — exatamente o que o SOT manda corrigir.

### Referência (remessa — já funciona, a espelhar)
| Empresa | Operação | tipo | Journal | `no_payment` | Efeito |
|---|---|---|---|---|---|
| FB saída (remessa) | op 80 (5901) | `industrializacao` | **j17** REMESSA P/ IND. (sale) | **5101010001 (ATIVA)** | `D 5101010001` |
| LF entrada (recebe) | op 2686 (1901) | `serv-industrializacao` (ent) | **j1047** ENTRADA-REMESSA (purchase) | **5101020001 (PASSIVA)** | `C 5101020001` |

---

## 2. IDs verificados (para a config)

**Contas (account.account):**
| Conta | FB id | LF id | Tipo |
|---|---|---|---|
| 5101010001 REMESSA IND. (ATIVA) | **22800** | 26652 | asset_current |
| 5101020001 REMESSA IND. (PASSIVA) | 22815 | **26667** | liability_current |
| 5101010002 RETORNO IND. (ATIVA) | 22801 | 26653 | asset_current |
| 5101020002 RETORNO IND. (PASSIVA) | 22816 | 26668 | liability_current |

**Operações de retorno:** 5124→op **849/2702**; 5902→op **850**; 5903→op **2711**; 1902 simbólica→op **3252** (`movimento_estoque=False`, já criada); 1124→op 3064/3134; 1903→op 838/3120.
**Picking types:** retorno LF=**pt98** (`31093→26489`, ativo, **0 usos**); entrada FB=**pt52** (`src=26489`).

---

## 3. Spec G5a — FB ENTRADA baixar a ATIVA `5101010001` (Design A)

**Objetivo:** o retorno **creditar `5101010001`** (mesma conta da remessa) → `Δciclo 5101010001 = 0`.

**(a) Criar journal** — espelho inverso de j17:
- Nome: `ENTRADA - RETORNO DE INDUSTRIALIZAÇÃO` · tipo **purchase** · company **FB (1)** · `account_no_payment_id = 22800` (**5101010001 ATIVA**).

**(b) Rotear a linha 1902 (e 1903) para esse journal** — `[A CONFIRMAR: caminho]`:
- O roteamento é por `tipo_pedido_entrada → tipo.pedido.diario(FB)`. `tipo_pedido_entrada` é um **selection** (não dá p/ criar valor novo sem DEV).
- **Opção (i) — registro novo no tipo.pedido.diario:** criar registro `(company=FB, tipo_pedido_entrada=serv-industrializacao, journal=novo)` e usar a op **3252** (que já é `serv-industrializacao` + `movimento_estoque=False`) na linha 1902. ✅ não-global se `serv-industrializacao` não estiver em uso na FB (hoje **não tem registro** → seguro).
- **Opção (ii) — setar no_payment no j1001 ENTSI:** afeta TODAS as entradas de industrialização (global). ❌ menos isolado.
- **Recomendado: (i)** + op 3252 na 1902.

**(c) G5b (double-count) — já resolvido por config:** a op **3252** (`movimento_estoque=False`) na linha 1902 → 0 stock.move → os insumos **param de re-entrar** no estoque FB (mata o R$ 785k). *(Ground-truth do double-count: `ENTSI/2026/05/0126` re-entra MP+EMB ≈ R$ 6.955.)*

**(d) Sobras 1903:** hoje cai em j1007 (no_payment=**5101020002 PASSIVA RETORNO** — conta errada). Repontar para creditar **5101010001** (mesma lógica). ✅ **RESOLVIDO: perna REMESSA direto** — o desenho que a Contadora confirmou (2026-06-01) usa `5101020001`/`5101010001` (família REMESSA); a perna RETORNO (`...02`, saldo R$0) **não entra**.

**NET-alvo FB (piloto):** `1902: D 1150100007 PA / C 5101010001` + `1124: D 1150100007 PA / C 2120100001 FORNEC` → `Δ5101010001 = 0`, PA por `Ic+S`, sem double-count, sem CPV.

---

## 4. Spec G4 — LF SAÍDA baixar a PASSIVA `5101020001`

**Objetivo:** o retorno **debitar `5101020001`** (a obrigação aberta na entrada LF) → `Δciclo 5101020001 = 0`. **Obrigação do piloto a baixar = R$ 278,56** (ENTIN 737062).

**(a) Criar journal** — espelho inverso de j1047:
- Nome: `SAÍDA - RETORNO DE INDUSTRIALIZAÇÃO` · tipo **sale** · company **LF (5)** · `account_no_payment_id = 26667` (**5101020001 PASSIVA**).

**(b) Criar registros no tipo.pedido.diario (LF)** — hoje **inexistentes** (caem em default/PERDAS):
- `(company=LF, tipo_pedido=dev-industrializacao, journal=novo)` → para a linha **5902** (op 850).
- `(company=LF, tipo_pedido=perda, journal=novo)` → para a linha **5903** (op 2711). `[A CONFIRMAR: sobra usa mesma conta REMESSA ou tratamento próprio]`.
- ⚠️ **tirar a LF do journal PERDAS** (j1003, no_payment=5101010001 ATIVA) — é o que infla +R$ 8,67M.

**(c) Serviço 5124:** manter `venda-industrializacao → j847` (com pagamento → CLIENTES + `3101030001 SERVIÇOS`). ✅ já correto; espelha o `2120100001 FORNECEDORES` da FB.

**(d) Física:** retorno por **pt98** (`31093→26489`) — já existe, nunca usado. `[A CONFIRMAR: o piloto valida pt98]`.

---

## 5. NF MISTA — granularidade por linha JÁ PROVADA (técnico, não Contador)

✅ O ground-truth resolve a dúvida: a `ENTSI/2026/05/0126` (entrada FB real) é **uma NF mista funcionando** — na mesma nota, a linha 1124 (serviço) cai em FORNECEDORES (com pagamento) e as linhas 1902 (insumos) caem na conta da operação. **A conta de cada linha vem de `operação → CFOP → posição fiscal`, NÃO do `no_payment` do cabeçalho.** Logo a granularidade por-linha é fato; **não há decisão do Contador aqui**.

**O que falta (técnico):** apontar a **conta da linha 1902 para `5101010001`** (FB) / a 5902 para `5101020001` (LF) — via a **posição fiscal** da operação de retorno (`account.fiscal.position.account` remapeia conta_src→conta_dest, como a fp 86 já faz `3201000002→1150100011`). **Resolver:** investigar a posição fiscal das ops 850 (5902) / 2027 (1902) + **confirmar no piloto** que a baixa por linha ocorre. Sem separar NF.

---

## 6. "3 PERNAS" (AVCO Ic+S) — POLÍTICA confirmada; MECÂNICA é técnica/piloto

**Política (parte do Contador): ✅ confirmada** — o PA vale `Ic+S` e o `Ic` incorpora-se ao PA (Ativo). Não há mais decisão contábil pendente aqui.

**Mecânica (técnica, medir no piloto):** o AVCO do PA vem do `price_unit` da **linha física** (1124, `movimento_estoque=True`) que gera o stock.move. Para o PA valer `Ic+S`, a **NF de retorno da LF declara `price_unit = Ic+S`** na linha do PA. A linha 1902 (simbólica, `movimento_estoque=False`) **não afeta o AVCO** (sem stock.move) — só baixa contábil de `5101010001`. Caminhos (escolher e **medir no piloto de 1 caixa**):
- (ii) **[provável]** PA físico declarado por `Ic+S`; baixa de `5101010001`(Ic) pela linha 1902 simbólica → **risco a medir: descasamento AVCO (físico=Ic+S) × razão (1150100007 recebe +Ic da 1902 sem stock.move)**.
- (i) PA por S + regularização periódica de Ic; (iii) Ic via custo da MO/BoM.
> Hoje o AVCO do PA na FB = **R$ 35,37/cx** (≈ só S) — subvalorizado (G8). **Só escalar ao Contador SE o piloto revelar descasamento AVCO×razão irreconciliável.**

---

## 7. Sequência proposta (após OK Rafael + dry-run)

1. **Criar os 2 journals** (G5a FB + G4 LF) — dry-run → exec (DDL via UI/XML-RPC; reversível: arquivar).
2. **Criar/repontar registros** `tipo.pedido.diario` (G5a: serv-industrializacao FB; G4: dev-industrializacao + perda LF).
3. **Tirar a LF do journal PERDAS** (rota 5902/5903).
4. **Rotear física**: retorno LF → pt98; entrada FB → pt52.
5. **Piloto 4870112**: 1 ciclo completo de retorno; medir (GOALS §B): `5101010001(FB)=0`, `5101020001(LF)=0`, `26489=0`, 0 re-entrada de componentes, PA por `Ic+S`. **Confirmar o resíduo §5 (NF mista por-linha).**

## 8. Status das decisões — NÃO há bloqueio do Contador

| Item | Status |
|---|---|
| Opção A (Ativo→Ativo, CPV só na venda) | ✅ Contadora confirmou |
| Perna REMESSA × RETORNO (§3d) | ✅ **resolvido** — desenho confirmado usa REMESSA direto |
| PA vale `Ic+S` (política) | ✅ Contadora confirmou |
| NF mista por linha (§5) | ✅ **técnico** — ground-truth prova; falta apontar conta da 1902 via posição fiscal + piloto |
| Mecânica do AVCO (§6) | 🟡 **piloto** — declarar `price_unit=Ic+S`, medir; escalar só se houver descasamento |
| G5b (op 3252, double-count) | ✅ pronto |
| Roteamento tp_ent da 1902 (§3b) | 🟡 **técnico** — criar registro `tipo.pedido.diario` + dry-run |

→ **Próximo é EXECUÇÃO técnica** (criar 2 journals + apontar contas via posição fiscal + dry-run + piloto), **não esperar o Contador**. Só re-escalar se o piloto revelar o descasamento AVCO×razão (§6).
