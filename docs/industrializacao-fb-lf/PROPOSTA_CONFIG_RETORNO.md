# PROPOSTA — Config das operações + journals de RETORNO (G4 LF + G5a FB)

> **Papel deste doc (anexo de EXECUÇÃO):** IDs, roteamento ao vivo e passos de dry-run da config G4/G5a. O **desenho-alvo e as DECISÕES** moram na `SOT_OPERACOES.md` (dona) — aqui só se expande o "como". Índice geral: `README.md`.
>
> Objetivo: fechar o ciclo contábil do retorno — a LF baixar a PASSIVA `5101020001` (G4) e a FB baixar a ATIVA `5101010001` (G5a). Base: grounding ao vivo 2026-06-01. ⚠️ **Config GLOBAL** (afeta todos os retornos de industrialização) — exige OK Rafael + dry-run antes de qualquer escrita; o piloto **testa**.

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
| 1124 serviço | 1124 | **1917** (real, 1530/1550) / 3134 / 3064 | `serv-industrializacao` | **j1001 ENTSI** (mesma NF mista) | — | ✅ gera FORNECEDORES (sessão 6: op real é 1917, NÃO 3064/3134) |
| 1903 sobras | 1903 | 838 / 3120 | `retorno` | j1007 ENTRADA-RETORNO | 5101020002 (PASSIVA RETORNO) | 🔴 conta errada (FB usa ATIVA) |

### LF (company 5) — SAÍDA do retorno
> 🔴 **TABELA REFUTADA pelo grounding 2026-06-01 (sessão 5) — ver `ACHADOS §"ACHADO 2026-06-01 (sessão 5)"`.** A realidade ao vivo:
> - A NF de retorno real é **MISTA (5124 serviço + 5902 insumos)** e cai em **j847 VENDA PRODUÇÃO** (header `venda-industrializacao`, op_hdr 2702, op da 5902 = **2864**), **não** em PERDAS j1003 nem por `dev-industrializacao`.
> - op **850 é company FB** (não LF); `dev-industrializacao`→**j1002 RETRABALHO** e `perda`→**j1003** **já têm journal** (não estão "livres").
> - j847 hoje tem no_payment VAZIO → as linhas 5902 creditam só a transitória 1150100012 (fechada pelo SVL) e o valor fica embutido no D CLIENTES ⇒ **a NF mista NÃO baixa a PASSIVA 5101020001**.

| Linha | CFOP | Operação real (LF) | `tipo_pedido` | → Journal real | `no_payment` | Avaliação |
|---|---|---|---|---|---|---|
| 5124 serviço | 5124 | **2702** | `venda-industrializacao` | **j847 VENDA DE PRODUÇÃO** | VAZIO | ✅ serviço OK (CLIENTES + 3101030001) |
| 5902 insumos | 5902 | **2864** | `venda-industrializacao` | **j847** (mesma NF mista) | VAZIO | 🔴 não baixa 5101020001 (vai p/ transitória/recebível) |
| 5903 sobras (só se houver) | 5903 | 2711 | `perda` | **j1003 PERDAS** (no_pay 26652 ATIVA) | 5101010001 | 🔴 debita a ATIVA da LF (+R$8,67M); piloto é SEM sobra |

> ⚠️ A NF de **perda pura** (5903) é o que cai em `SAÍDA - PERDAS` (j1003, no_payment=5101010001 ATIVA) e infla a ATIVA da LF. A NF **mista de retorno** (caso do piloto) cai em **j847**.

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

> 🔴 **v2.6 (2026-06-02, EXPERIMENTO PROVADO — `ACHADOS §"ACHADO 2026-06-02 (sessão 6)"`):** a config abaixo (no_payment=22800 no j1001) é **necessária mas INSUFICIENTE sozinha**. NF-teste mista de entrada postada/excluída: o `no_payment` **NÃO baixou** a ATIVA (NET 5101010001=0); o `FORNECEDORES` do serviço (1124) **absorveu** a 1902. ⇒ **G5a converge com o G4:** a 1902 só baixa a ATIVA se chegar à FB em **documento separado** do serviço (mesma decisão fiscal). O `no_payment` no j1001 só "morde" quando a NF de entrada é simbólica pura (insumos sem serviço). **Aplicar a config abaixo isolada não fecha o ciclo.**

**Objetivo:** o retorno **creditar `5101010001`** (mesma conta da remessa) → `Δciclo 5101010001 = 0`.

**(a) AJUSTAR o journal `j1001` existente** (`ENTRADA - SERVIÇO DE INDUSTRIALIZAÇÃO`, purchase, FB) — **DECISÃO Rafael (2026-06-01): reusar, NÃO criar novo** (ver `SOT §2 L5a`):
- setar `account_no_payment_id = 22800` (**5101010001 ATIVA**) no j1001 (hoje VAZIO → por isso não baixa a ATIVA).
- Motivo: o j1001 já é a NF mista funcionando (`§5`); só falta o no_payment. Journal paralelo = redundante.
- ⚠️ Efeito GLOBAL (intencional): todas as entradas em j1001 passam a baixar 5101010001.

**(b) Rotear a linha 1902 para o j1001** (verificado ao vivo 2026-06-01):
- criar registro `tipo.pedido.diario(company=FB, l10n_br_tipo_pedido_entrada=serv-industrializacao → j1001)`. `serv-industrializacao` está **LIVRE na FB** (o registro id 29 é `industrializacao`, não `serv-industrializacao`) → não conflita com a ENTSI atual.
- usar a op **3252** (`serv-industrializacao` + `movimento_estoque=False`) na linha 1902 → mata o double-count.
- ⚠️ a linha **1124** (serviço, op 3064/3134) também é `serv-industrializacao` → cairá no mesmo j1001; mas o j1001 já separa 1124(→Fornecedores) de 1902(→no_payment) na NF mista (`§5`) — **confirmar no piloto** que mantém com o no_payment setado.

**(c) G5b (double-count) — já resolvido por config:** a op **3252** (`movimento_estoque=False`) na linha 1902 → 0 stock.move → os insumos **param de re-entrar** no estoque FB (mata o R$ 785k). *(Ground-truth do double-count: `ENTSI/2026/05/0126` re-entra MP+EMB ≈ R$ 6.955.)*

**(d) Sobras 1903:** hoje cai em j1007 (no_payment=**5101020002 PASSIVA RETORNO** — conta errada). Repontar para creditar **5101010001** (mesma lógica). ✅ **RESOLVIDO: perna REMESSA direto** — o desenho que a Contadora confirmou (2026-06-01) usa `5101020001`/`5101010001` (família REMESSA); a perna RETORNO (`...02`, saldo R$0) **não entra**.

**NET-alvo FB (piloto) — corrigido por R1 (`ACHADOS §sessão 5`):** a 1902 com op 3252 debita a TRANSITÓRIA, não o PA. Lançamento real esperado:
- `1902 (op 3252): D 1150100011 / C 5101010001` (baixa a ATIVA) **+** `SVL físico do PA na entrada: D 1150100007 PA / C 1150100011` ⇒ **NET `D 1150100007 PA / C 5101010001`** (a transitória 1150100011 é a ponte, fecha entre as duas).
- `1124 (serviço): C 2120100001 FORNECEDORES` (+ tributos a recuperar).
- Resultado: `Δ5101010001 = 0`, PA por `Ic+S` (via SVL físico), sem double-count (op 3252), sem CPV. ⚠️ **Medir na Etapa 5:** se valor da 1902 (Ic) ≠ valor do SVL do PA na 1150100011, a transitória **não zera** (resíduo) — e o AVCO do PA depende do price_unit (G8).

---

## 4. Spec G4 — LF SAÍDA baixar a PASSIVA `5101020001` — 🔴 BLOQUEADO POR DESENHO

> **PLANO ANTIGO REFUTADO (grounding sessão 5, `ACHADOS`):** criar journal LF + `tipo.pedido.diario(dev-industrializacao/perda)` é **INERTE** — a NF mista de retorno roteia por header `venda-industrializacao`→**j847** e usa op **2864** (não 850/dev-industrializacao). G4 **não fecha** com o plano antigo.

**Objetivo:** o retorno **debitar `5101020001`** (obrigação aberta na entrada LF) → `Δciclo 5101020001 = 0`. **Obrigação do piloto a baixar = R$ 278,56** (ENTIN 737062). Mecânica do no_payment em SAÍDA: vira DÉBITO na conta de compensação das linhas simbólicas (espelho do j1003 que debita a ATIVA — `ACHADOS §mecanismo`).

**Decisão Rafael (2026-06-01): INVESTIGAR antes de decidir → EXPERIMENTO FEITO.** j847 é DEDICADO ao regime (340/340 NFs desde 2026-01 = retorno 100% p/ FB; R$ 8,68M de insumos sem baixa). **R2 resolvido por experimento** (`ACHADOS §sessão 5` R2): **o no_payment do journal NÃO baixa a 5902 numa NF mista** — o `D CLIENTES` do serviço (5124) absorve a contrapartida.

### As 3 opções (✅ provado qual serve)
| Opção | O que faz | Veredito |
|---|---|---|
| **(a) `no_payment=26667` no j847** | esperava-se 5902→`D 5101020001` | 🔴 **DESCARTADA (provado)** — em NF mista o CLIENTES engole a 5902; no_payment só atua em NF 100%-simbólica |
| **(b) separar a NF: insumos 5902 em NF própria** ⭐ | NF só-5902 (simbólica pura) → journal com no_pay 26667 → `D 5101020001`; serviço 5124 segue em j847 | ✅ **caminho** — espelha a mecânica da NF de perda (j1003) que já baixa via no_payment. Exige decisão fiscal da Contadora (separar retorno-de-insumos do faturamento) + a Skill 8 emitir 2 documentos |
| **(c) mudar header da NF inteira** | NF mista → journal dedicado | 🔴 não resolve — mistura serviço; o CLIENTES continua absorvendo a 5902 |

> **Conclusão:** o "problema de granularidade" é que o no_payment opera **por cabeçalho de NF** e só substitui o receivable quando a NF é simbólica pura. **A 5902 precisa de NF própria.** Recomendação: **(b)**. Pendente: aprovação fiscal da Contadora (`MATERIAL_CONTADORA_G4.md`) + ajuste da Skill 8 p/ emitir o retorno de insumos separado.

**Serviço 5124:** manter `venda-industrializacao → j847` (CLIENTES + `3101030001 SERVIÇOS`). ✅ espelha o `2120100001 FORNECEDORES` da FB.
**Física:** retorno por **pt98** (`31093→26489`) — já existe, nunca usado. `[A CONFIRMAR: o piloto valida pt98]`.

---

## 5. NF MISTA — granularidade por linha JÁ PROVADA (técnico, não Contador)

✅ O ground-truth resolve a dúvida: a `ENTSI/2026/05/0126` (entrada FB real) é **uma NF mista funcionando** — na mesma nota, a linha 1124 (serviço) cai em FORNECEDORES (com pagamento) e as linhas 1902 (insumos) caem na conta da operação. **A conta de cada linha vem de `operação → CFOP → posição fiscal`, NÃO do `no_payment` do cabeçalho.** Logo a granularidade por-linha é fato; **não há decisão do Contador aqui**.

**Premissa CORRIGIDA (verificado ao vivo 2026-06-01):** a conta de **compensação** (`5101010001`/`5101020001`) vem do **`account_no_payment_id` do JOURNAL**, NÃO da posição fiscal — a operação **não tem** campo de posição fiscal nem de conta. A posição fiscal só remapeia conta de **resultado→transitória** (ex.: fp 86 `3201000002→1150100011`). **Logo: G5a/G4 = ajustar/criar o journal com o no_payment certo + rotear via `tipo.pedido.diario`** — sem mexer em posição fiscal. A separação 1124(→Fornecedores)/1902(→no_payment) por linha já é fato no j1001 (NF mista) — confirmar no piloto que se mantém com o no_payment setado.

---

## 6. "3 PERNAS" (AVCO Ic+S) — POLÍTICA confirmada; MECÂNICA é técnica/piloto

**Política (parte do Contador): ✅ confirmada** — o PA vale `Ic+S` e o `Ic` incorpora-se ao PA (Ativo). Não há mais decisão contábil pendente aqui.

**Mecânica (técnica, medir no piloto):** o AVCO do PA vem do `price_unit` da **linha física** (1124, `movimento_estoque=True`) que gera o stock.move. Para o PA valer `Ic+S`, a **NF de retorno da LF declara `price_unit = Ic+S`** na linha do PA. A linha 1902 (simbólica, `movimento_estoque=False`) **não afeta o AVCO** (sem stock.move) — só baixa contábil de `5101010001`. Caminhos (escolher e **medir no piloto de 1 caixa**):
- (ii) **[provável]** PA físico declarado por `Ic+S`; baixa de `5101010001`(Ic) pela linha 1902 simbólica → **risco a medir: descasamento AVCO (físico=Ic+S) × razão (1150100007 recebe +Ic da 1902 sem stock.move)**.
- (i) PA por S + regularização periódica de Ic; (iii) Ic via custo da MO/BoM.
> Hoje o AVCO do PA na FB = **R$ 35,37/cx** (≈ só S) — subvalorizado (G8). **Só escalar ao Contador SE o piloto revelar descasamento AVCO×razão irreconciliável.**

---

## 7. Sequência proposta (revisada pós-grounding sessão 5)

1. **R1 (G5a) — ✅ RESOLVIDO por READ-ONLY:** a 1902/op 3252 debita a transitória **1150100011** (não o PA); Ativo→Ativo fecha via SVL físico do PA na Etapa 5 (`ACHADOS §sessão 5` R1). Não precisou criar NF draft.
2. **G5a (FB) dry-run + go FRESCO:** ajustar o **j1001** — `account_no_payment_id=22800` (5101010001). Script pronto: `scripts/g5a_aplicar_no_payment_j1001.py` (dry-run default; `--confirmar` efetiva; `--reverter` rollback). `tipo.pedido.diario(FB, serv-industrializacao→j1001)` é **provavelmente redundante** (roteamento pelo campo do journal) — `--criar-tpd` opcional como cinto-de-segurança. ⚠️ GLOBAL: afeta ENTSI que ainda usam op 2027 (mov_estoque=True) — rotear 1902 p/ op 3252 é parte do G5a (R1b).
3. **G4 (LF) — BLOQUEADO por desenho:** decidir entre as 3 opções (§4) com Rafael+Contadora; medir **R2** (NF mista com no_payment) num DRAFT antes de executar. ⚠️ **NÃO** criar journal+tipo.pedido.diario dev-ind/perda (plano refutado, inerte).
4. **Rotear física**: retorno LF → pt98; entrada FB → pt52.
5. **Piloto 4870112**: 1 ciclo; medir (`GOALS`): `5101010001(FB)=0`, `5101020001(LF)=0`, `26489=0`, `30720=0`, 0 re-entrada de componentes, PA por `Ic+S`. **Gate:** abortar se `Δ5101020001(LF) != 0` (não basta a config ter sido criada).

## 8. Status das decisões — **G5a converge com G4** (ambos bloqueados por DESENHO fiscal)

| Item | Status |
|---|---|
| Opção A (Ativo→Ativo, CPV só na venda) | ✅ Contadora confirmou |
| Perna REMESSA × RETORNO (§3d) | ✅ **resolvido** — desenho confirmado usa REMESSA direto |
| PA vale `Ic+S` (política) | ✅ Contadora confirmou |
| G5a sinal (no_payment 22800 → C 5101010001) | ✅ validado em NF **não-mista** (j1011/j868/j993) — MAS 🔴 **insuficiente em NF mista** (sessão 6: FORNECEDORES absorve a 1902) |
| **G5a converge com G4** (1902 em doc separado) | 🔴 **PROVADO (sessão 6)** — `account_no_payment_id` no j1001 sozinho não baixa a ATIVA quando a entrada é mista; exige separar a 1902 do serviço (= a decisão fiscal do G4) |
| G5a efeito global j1001 | 🟡 prospectivo, restrito ao regime LF (351 ENTSI 2026 = 100% LF) — aceitar/medir variantes simbólicas |
| G5a resíduo R1 (conta que a op 3252 debita) | 🟡 **medir em DRAFT** — afeta se o ciclo fecha no Ativo (PA vs transitória) |
| **G4 — separar a NF (opção b)** | 🔴 **aprovação FISCAL Contadora** (experimento provou: no_payment não baixa 5902 em NF mista; opção (a) descartada; caminho = NF separada da 5902) |
| G4 resíduo R2 (NF mista c/ no_payment) | 🟡 **medir em DRAFT** |
| Mecânica do AVCO (§6) | 🟡 **piloto** — declarar `price_unit=Ic+S` |
| G5b (op 3252, double-count) | ✅ op criada (1º uso real no piloto) |

→ **G5a:** 🔴 **NÃO é mais "caminho técnico claro"** — PROVADO (sessão 6) que converge com o G4 (no_payment no j1001 sozinho não baixa em NF mista). **G4 = G5a:** ambos exigem a **mesma decisão de desenho fiscal** (Rafael+Contadora): separar o retorno de insumos (1902↔5902) do serviço. Re-escalar Contador se o piloto revelar descasamento AVCO×razão (§6).
