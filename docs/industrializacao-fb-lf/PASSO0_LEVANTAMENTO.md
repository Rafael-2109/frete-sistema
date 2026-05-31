# PASSO 0 — Levantamento de contas de categoria na LF (READ-ONLY)

> Saída da execução do **Passo 0** do `PLANO_EXECUCAO.md` (sessão 2026-05-29, modo "PODE INICIAR").
> **Tudo aqui é leitura no Odoo PROD via XML-RPC.** Nenhuma escrita foi feita.
> Scripts read-only (re-executáveis) em `scripts/`: `passo0_probe.py`, `passo0_levantar_contas.py`, `passo0_dimensionar.py`, `passo0_pt19_partners.py`, `passo0_classificar_mro.py`, `passo0_escopo_definitivo.py`.

---

## 0. Premissa de negócio confirmada (Rafael, 2026-05-29) — INVIOLÁVEL

> **Componentes produtivos da LF são TODOS da FB** (material de terceiros), categoricamente — independente da contagem de pickings.
> Próprio da LF é **apenas** MRO / peça de manutenção / uso da indústria — **nunca** componente produtivo.
> **NOVACKI** (e demais "fornecedores externos" de insumo) = **remessa por conta e ordem de terceiro** → material da FB.
> **Transferências CD→LF** = produtos acabados enviados **para retrabalho** → grupo FB (terceiros).

**Consequência:** a config de "tudo terceiros" vale para **todas as categorias produtivas** da LF. O MRO próprio é separado por estrutura de categoria (ver §4).

---

## 1. O que foi confirmado (fundamenta a config)

| Achado | Valor verificado |
|---|---|
| Campos de conta em `product.category` | `property_stock_valuation_account_id`, `property_stock_account_input_categ_id`, `property_stock_account_output_categ_id`, `property_stock_account_production_cost_id` — **todos `company_dependent=True`** (ir.property). Também company-dependent: `property_valuation`, `property_cost_method`. |
| Par de contas-alvo **existe na LF (cmp 5)** | `1150200001 MATERIAL EM TERCEIROS` = **id 26140** · `1150200002 (−) MATERIAL DE TERCEIROS` = **id 26141** · `1150100004 PRODUÇÃO` = **id 26135** |
| **Escopo produtivo `real_time`** (subtree completo) | **173 categorias**: EMBALAGEM 24 + MATÉRIA PRIMA 34 + PRODUTO ACABADO 111 + SEMI ACABADOS 4 |
| Subconjunto **ativo** (com quant na LF hoje) | **65** categorias (das 173) |
| 🟢 **OWN/MRO com `real_time` na LF** | **0** — todas USO E CONSUMO (93) / SERVIÇO (35) / ATIVO FIXO (13) / DESPESAS (31) são `consu`/`manual_periodic` → **não geram SVL** → **nunca afetadas pelo repoint** |
| ir.property LF já existe | **389 linhas LF** nesses campos p/ o conjunto ativo → write futuro é majoritariamente **UPDATE** (limpo) |

### Outras contas LF resolvidas (para os lançamentos)
`1150100001 MP`=26132 · `1150100002 EMB`=26133 · `1150100006 SEMI` · `1150100007 PA`=26138 · `1150100011 RECEB FÍS`=26845 · `1150100012 FATUR FÍS`=26855 · `3201000002 VAR POS`=26816 · `3201000003 VAR NEG`=26817.

---

## 2. Estado ATUAL das contas das categorias produtivas na LF (contexto cmp=5)

Padrões distintos no conjunto **ativo** (65 categorias real_time):

| # cats | VAL (valoração) | IN (entrada) | OUT (saída) | PROD |
|---:|---|---|---|---|
| 18 | `1150100007` PA (próprio) | `3201000002` VAR.POSITIVAS ⚠️ | `3201000003` VAR.NEGATIVAS ⚠️ | `1150100004` |
| 17 | `1150100001` MP (próprio) | `3201000002` ⚠️ | `3201000003` ⚠️ | `1150100004` |
| 14 | `1150100002` EMB (próprio) | `1150100011` RECEB.FÍS | `1150100012` FATUR.FÍS | `1150100004` |
| 4 | `1150100001` MP | `1150100011` | `1150100012` | `1150100004` |
| 4 | `1150100007` PA | `1150100011` | `1150100012` | `1150100004` |
| 3 | `1150100002` EMB | `3201000002` ⚠️ | `3201000003` ⚠️ | `1150100004` |
| 3 | `1150100006` SEMI | `3201000002` ⚠️ | `3201000003` ⚠️ | `1150100004` |
| 1 | `1150100010` PALLETS | `1150100011` | `1150100012` | — |
| 1 | **`3201000002`** 🔴 | `1150100001` | `1150100001` | `1150100004` |

**Diagnóstico:**
- A **valoração (VAL)** aponta hoje para **contas-próprias da LF** (MP/EMB/PA/SEMI/PALLET) → o estoque da LF está lançado como **ativo PRÓPRIO** dela (o que a diretriz quer corrigir).
- **IN/OUT inconsistentes**: ~41 cats creditam/debitam **contas de RESULTADO** (`3201000002/003` VARIAÇÕES) — entrada de material gera *ganho* no resultado (erro do `ACHADOS_TECNICOS.md:35`); ~24 usam transitórias físico-fiscais.
- 🔴 **Anomalia isolada — categ 328 (`MP NAC / OLEO`)**: VAL aponta para **`3201000002` (conta de RESULTADO como valoração de ativo!)**. Mal-cadastrada, **independente deste projeto** → sinalizar à TI/Contábil.

---

## 3. PROPOSTA de configuração (Passo 0) — a validar com o Contador

Repointar, **apenas no contexto da LF (cmp 5)**, as categorias **produtivas `real_time`**:

| Campo da categoria (contexto LF) | Hoje (varia) | **Apontar para** | id LF |
|---|---|---|---|
| `property_stock_valuation_account_id` | 1150100001/002/006/007/010 (próprias) | **`1150200001` MATERIAL EM TERCEIROS** | **26140** |
| `property_stock_account_input_categ_id` | 3201000002 / 1150100011 | **`1150200002` (−) MATERIAL DE TERCEIROS** | **26141** |
| `property_stock_account_output_categ_id` | 3201000003 / 1150100012 | **`1150200002` (−) MATERIAL DE TERCEIROS** | **26141** |
| `property_stock_account_production_cost_id` | 1150100004 PRODUÇÃO | **❓ DECISÃO CONTADOR** (manter 1150100004 transitório, ou terceiros) | 26135 |

**Decisão de escopo (Rafael/Contador):**
- **Opção ampla (recomendada)** — repoint das **173** produtivas `real_time` (todo o subtree EMBALAGEM/MP/PA/SEMI). Future-proof: produto produtivo novo já nasce terceiros. Seguro (0 MRO real_time).
- **Opção mínima** — repoint só das **65** ativas (com quant hoje). Menor blast radius, mas exige re-rodar a config quando surgir produto produtivo em categoria nova.

**Efeito esperado** (a confirmar no teste §5): entrada `D 1150200001 / C 1150200002`; consumo na MO + produção do PA transitam por PRODUÇÃO e zeram; saída `C 1150200001 / D 1150200002`. **Net-zero em terceiros**; LF nunca infla ativo próprio.

- **Não** afeta FB/SC/CD (ir.property é por empresa — provado).
- **Não** depende do picking type (config é a nível de categoria) → cobre pt19 e pt64 (ver §4.2).
- Reversível (UPDATE de ir.property; valores atuais ficam neste doc + JSON `/tmp/passo0_contas_lf.json` + `/tmp/passo0_escopo.json`).

---

## 4. Achados que ajustam o plano

### 4.1. ✅ Carve-out RESOLVIDO — é estrutural, não por fornecedor
A premissa §0 bate exatamente com a árvore de categorias:
- As categorias produtivas (`EMBALAGEM/MP/PA/SEMI`) **não contêm itens de MRO**.
- Todo MRO/manutenção/uso vive em ramos **separados** (`USO E CONSUMO`, `SERVIÇO`, `ATIVO FIXO`, `DESPESAS`) que são **`consu`/`manual_periodic` → 0 com `real_time`** → **nunca geram valoração** → **o repoint não os toca**.
- As únicas compras externas que caíram fora do subtree produtivo: categ **51** (ATIVO FIXO / MÁQUINA DE SOLDA, `consu` — MRO próprio ✓) e categ **59** (EMBALAGEM/EMB 1 "BARRICAS" — produtiva, só sem quant hoje; já incluída no subtree de 173).
- ✅ **Não é necessário carve-out dentro do escopo.**

### 4.2. pt64 está abandonado — a remessa entra por **pt19** (96% intercompany)
Entradas LF/12m: pt **19 LF/IN = 800** (726 FB + 41 CD + 33 externos[remessa p/ ordem] + sem parceiro) vs pt **64 = 51**. A remessa FB→LF entra como recebimento via pt19, não pelo pt64 que o plano previa para a Etapa 2.
- **Bom para a config** (category-level, agnóstica ao pt).
- **Mas** a Etapa 2 do `PLANO_EXECUCAO.md` (corrigir pt64 `dst→31092`) só vale se a operação **migrar** para o pt64; senão, padronizar destino/operação no fluxo pt19. → **Decisão de processo.**

### 4.3. 🔴 Lado LF também tem passivo contábil (maior que o da FB)
Saldo contábil ATUAL (posted, cmp 5):

| Conta | Saldo (D−C) | #lançs |
|---|---:|---:|
| `1150100001` MATÉRIA-PRIMA | **−20.176.079,99** | 17.825 |
| `1150100002` MATERIAL DE EMBALAGEM | **−5.201.863,31** | 19.190 |
| `1150100007` PRODUTO-ACABADO | −16.839,13 | 4.437 |
| `1150100006` SEMI-ACABADO | −11.715,60 | 2.642 |
| `1150100004` PRODUÇÃO | −35.965,99 | 31.375 |
| `1150100010` PALLETS | +8.730,39 | 170 |
| **TOTAL estoque-próprio LF** | **≈ −25.397.767,64** | |
| `1150200002` (−) MATERIAL DE TERCEIROS | −11.958.102,17 | 1.738 |
| `1150200001` MATERIAL EM TERCEIROS | **0,00** | **0** |

- Contas de **ativo** de estoque da LF estão **net CREDOR** (sinal anômalo) na casa das **dezenas de milhões**; `1150200001` **nunca foi debitada**; `1150200002` já carrega −R$ 11,96M.
- A config é **prospectiva** — **não** regulariza esses saldos já postados → exige decisão de reclassificação (modo A/B/C do `00_FLUXO §4.2`) **também para a LF** (espelho do R$ 785k da FB, porém muito maior). Interpretação é do Contador.

---

## 5. BLOQUEADOR 1 — Teste controlado (design proposto, sem executar)

Provar empiricamente net-zero terceiros + MO consumindo certo, **antes** do rollout.

1. Escolher **1 categoria-cobaia** produtiva de baixo giro **que tenha 1 produto fácil de movimentar na LF** (ex.: uma EMB do piloto do MOLHO SHOYU). Como 0 MRO é real_time, qualquer produtiva é segura.
2. Snapshot **antes**: ir.property atuais (temos) + saldo SVL/contábil do produto na LF.
3. Repoint **só dessa categoria** (LF context) — `--dry-run` → `--execute`, com aprovação.
4. **1 movimento real pequeno** (entrada/transferência de poucas un de 1 produto da categoria) → inspecionar `account.move`: deve ser **`D 1150200001 / C 1150200002`**.
5. **1 MO mínima** consumindo esse item → verificar consumo (terceiros→produção) + produção PA (produção→terceiros) → conferir net da conta PRODUÇÃO.
6. **Reverter** a categoria ao estado original (registrado) se o Contador ainda não aprovou o rollout.
7. Documentar em `T-PASSO0-TESTE-resultado.md`.

> Pendente: escolher **qual categoria/produto** cobaia.

---

## 6. BLOQUEADOR 2 — Perguntas ao Contador (atualizadas)

1. **Par de contas (Passo 0):** confirmar VAL→`1150200001`, IN/OUT→`1150200002` para as categorias produtivas da LF? E `production_cost_id`: mantém **1150100004 PRODUÇÃO** (transitória que zera por MO) ou também vira terceiros?
2. **Escopo:** repoint do subtree produtivo completo (**173**) ou só do ativo (**65**)? (MRO fica fora por construção — 0 real_time.)
3. **Saldo estoque-próprio LF (≈ −R$ 25,4M, §4.3):** como regularizar (reclassificação A / ajuste B / exercícios anteriores C)? Pré-requisito da config ou paralelo?
4. **Lado FB (Etapa 5 — passivo R$ 785k):** mecanismo da baixa dos componentes do retorno sem inflar o Ativo Estoque da FB.
5. **CFOPs do retorno** (5124+5902+5903 / 1124+1902+1903) e desenho fiscal das 5 etapas — confirmar.
6. **`1150100011 RECEBIMENTO FÍSICO FISCAL`** (−R$ 1,49 bi na FB; LF também usa) — conciliar/zerar?
7. **Anomalia categ 328** (VAL = conta de resultado) — corrigir cadastro independentemente.

---

## 7. Decisão pendente (Rafael) antes de qualquer escrita

- [ ] **Escopo do repoint**: amplo (173) vs mínimo (65).
- [ ] Conta de **PRODUÇÃO** (1150100004 mantém / vira terceiros / pergunta ao Contador e segue com 1150100004).
- [ ] **Categoria-cobaia** do teste controlado (§5).
- [ ] Levar **lado LF (−R$ 25,4M)** + **lado FB (R$ 785k)** ao Contador **antes** de aplicar, ou testar a config (prospectiva) em paralelo.

> Próximo passo sugerido: escolher a cobaia + montar o script de teste em **dry-run** (sem executar) e, em paralelo, levar §3+§4+§6 ao Contador. **Nada será escrito no Odoo sem o "go".**
