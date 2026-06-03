<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Material de decisão — fechamento contábil do RETORNO de industrialização (G4)

> **Papel:** Material de decisão — fechamento contábil do RETORNO de industrialização (G4).

> **Para:** Contadora · **De:** controle interno (grounding Odoo PROD 2026-06-01) · **Decisão pedida:** como fazer o RETORNO da industrialização **baixar a obrigação da LF** (conta `5101020001` PASSIVA), hoje não baixada.
> Linguagem contábil; IDs Odoo entre parênteses. Tudo CST51 (ICMS suspenso); serviço 5124 sem ICMS (CBS/IBS/PIS/COFINS).

---

## 1. O problema (medido ao vivo)

No regime **FB encomenda → LF industrializa → LF devolve o PA**, a cada ciclo deveriam **zerar**:
- na **FB**: `5101010001 REMESSA INDUSTRIALIZAÇÃO (ATIVA)` — debitada na remessa, baixada no retorno;
- na **LF**: `5101020001 REMESSA INDUSTRIALIZAÇÃO (PASSIVA)` — creditada na entrada, baixada no retorno.

**Hoje o retorno NÃO baixa nenhuma das duas.** Saldos acumulados: ATIVA FB ≈ **R$ 60,8 mi**; insumos sem baixa em **j847** desde 2026-01 = **R$ 8,68 mi**.

### Lançamentos atuais do ciclo (resumo)
| Etapa | Documento | Lançamento atual | Efeito |
|---|---|---|---|
| Remessa (FB→LF) | NF 5901, j17 | `D 5101010001 / C estoque FB` | ATIVA sobe (ok, mas nunca baixa) |
| Entrada (LF) | NF 1901, j1047 ENTIN | `D 1150100011 / C 5101020001` | PASSIVA sobe (ok, mas nunca baixa) |
| **Retorno (LF→FB)** | **NF MISTA 5124+5902, j847** | 5124 `C SERVIÇOS / D CLIENTES`; **5902 `C 1150100012` embutido no D CLIENTES** | 🔴 **PASSIVA 5101020001 não baixa**; insumos inflam o recebível |
| Entrada retorno (FB) | NF 1124+1902, j1001 ENTSI | 1902 `D 1150100011` (+ re-infla estoque); contrapartida não toca a ATIVA | 🔴 **ATIVA 5101010001 não baixa** + double-count |

> Exemplo real (NF `VND/2026/00359`, move 738097): `D CLIENTES 38.877,59` = serviço `13.735,66` + **insumos 24.477,59** + impostos. Os insumos simbólicos estão dentro do recebível.

---

## 2. Lado FB (G5a) — MESMA decisão (corrigido 2026-06-02)
> **Correção:** teste técnico (cópia de NF de entrada, R$ 120,05, postada e excluída — sem efeito real) provou que **apenas** apontar a conta de compensação no diário de entrada (j1001) **NÃO baixa** a `5101010001` quando a NF de entrada é **mista** (serviço 1124 + insumos 1902) — o valor **a pagar (FORNECEDORES)** da linha de serviço **absorve** os insumos simbólicos (1902), exatamente como ocorre no lado da saída.

⇒ **O lado FB (G5a) exige a MESMA separação que o lado LF (G4):** a FB precisa **receber** o retorno simbólico dos insumos (1902) em **NF separada** do faturamento do serviço (1124) — aí a 1902 vira mercadoria simbólica pura e a conta de compensação `5101010001` **baixa** corretamente. *(O PA incorpora o custo dos insumos via a entrada física do PA — Opção A, Ativo→Ativo, já confirmada por você.)*

> **Consequência prática:** a pergunta fiscal da seção 4 (separar retorno-de-insumos do faturamento-de-serviço) **resolve os DOIS lados de uma vez** — não é decisão só do lado LF.

## 3. Lado LF (G4) — **a decisão**: como a NF de retorno baixar a PASSIVA `5101020001`

**Alvo:** a linha **5902** (retorno simbólico dos insumos consumidos) deve **`D 5101020001 / C 1150100012`** (transitória, fechada pela saída física) → **baixa a PASSIVA**. O serviço **5124** continua **`D CLIENTES / C 3101030001 SERVIÇOS`** (inalterado).

**Teste técnico já realizado (cópia de NF, R$ 43,37, postada e excluída — sem efeito real):** apenas apontar a conta de compensação no diário **NÃO baixa** a obrigação quando a NF tem serviço junto — o valor a receber (CLIENTES) da linha de serviço (5124) **absorve** os insumos (5902). A baixa via conta de compensação **só funciona quando a NF é exclusivamente de mercadoria simbólica** (como já ocorre na NF de "perda" de insumos não aplicados).

### Caminho resultante: **separar o RETORNO DE INSUMOS do FATURAMENTO DO SERVIÇO** em dois documentos
| Documento | Linhas | Lançamento | Conta de compensação |
|---|---|---|---|
| **NF de serviço** (como hoje) | 5124 | `D CLIENTES / C 3101030001 SERVIÇOS` (+ tributos) | — (inalterado) |
| **NF de retorno dos insumos** (nova/separada) | 5902 (CST51 simbólico) | **`D 5101020001 (PASSIVA) / C 1150100012`** (transitória, fechada pela saída física) | journal com `5101020001` |

> Mecânica idêntica à da NF de perda de insumos não aplicados (que já baixa corretamente via conta de compensação). É o único arranjo em que a obrigação `5101020001` baixa.

---

## 4. Perguntas objetivas para a Contadora
1. **Separação de documentos:** é aceitável **fiscalmente** emitir o **retorno simbólico dos insumos consumidos (CFOP 5902, CST51)** em **NF separada** do faturamento do serviço (CFOP 5124)? Hoje saem juntos numa NF mista. Há impedimento fiscal/SEFAZ para separá-los?
2. **Baixa por valor:** a baixa da PASSIVA `5101020001` é **por valor agregado**, não vinculada documento-a-documento à remessa original. Aceitável para o fechamento mensal?
3. **Sobras (5903):** o retorno de insumos **não aplicados** deve baixar a mesma PASSIVA `5101020001` (hoje cai em "SAÍDA-PERDAS" debitando a ATIVA da LF — provavelmente errado)?
4. **Acumulado:** definido o fluxo, como regularizar os saldos históricos já abertos (ATIVA FB R$ 60,8 mi; insumos LF R$ 8,68 mi)? — item separado, sem prazo.

> Aprovada a separação, o restante é técnico: configurar o diário/operação do retorno de insumos com a conta `5101020001` e ajustar a emissão para gerar os 2 documentos + 1 ciclo-piloto (1 caixa) para medir o fechamento.

> Após a resposta, o ajuste é técnico (cadastro de diário) + 1 ciclo-piloto controlado (1 caixa) para medir o fechamento antes de aplicar ao fluxo corrente.

---

## 5. Como fica o ciclo com 2 documentos (verificado ao vivo 2026-06-02, só leitura)

Confirmamos em produção (sem nenhum lançamento real — apenas leitura do que já existe) como o ciclo se comporta ao **separar o retorno de insumos do faturamento do serviço**. Resumo nas 3 esferas:

**Físico (a mercadoria):** o **produto acabado (PA) sempre acompanha a NF de serviço (CFOP 5124)** — é a única linha com movimento físico de estoque. O retorno dos insumos (CFOP 5902) **já é hoje uma linha simbólica, sem movimento de estoque próprio** (reflete os insumos consumidos, não uma mercadoria nova). Logo, **separar em 2 documentos NÃO cria movimentação física nova** — apenas destaca as linhas simbólicas dos insumos num documento próprio. *(Prova: na NF de retorno real `VND/2026/00359`, das 10 linhas só a do PA tem movimento de estoque; as 9 de insumos são simbólicas.)*

**Fiscal — as 2 notas:**
| Documento | CFOP | CST | Valor | Carrega |
|---|---|---|---|---|
| NF de serviço (mantida) | **5124 ↔ 1124** | s/ ICMS (CBS/IBS/PIS/COFINS) | **S** (valor agregado) | **o PA** (mercadoria física) |
| NF de retorno de insumos (separada) | **5902 ↔ 1902** | CST51 (suspenso) | **Ic** (= valor da remessa) | nada físico (simbólica, total a pagar = 0) |

**Contábil:**
- A NF de retorno de insumos (só 5902, **total = 0**) baixa a conta de compensação via a **conta de "pagamento simbólico" do diário** — exatamente como já ocorre nas notas de retrabalho/perda (**provado em 14 notas `SARET` reais**: a contrapartida vai 100% para a conta de compensação, **sem gerar contas a receber/pagar**). Para o regime de industrialização, basta o diário do retorno de insumos apontar a conta **`5101020001` (PASSIVA, lado LF)** e a entrada na FB apontar **`5101010001` (ATIVA)** — baixando as duas obrigações.
- A NF de serviço (5124) gera o contas a pagar/receber do serviço (**S**), como hoje.
- **Custo do PA (Ativo) = Ic + S:** o serviço (S) entra pela NF de serviço; o custo dos insumos (Ic) incorpora-se ao PA pela baixa da conta de compensação (Ativo→Ativo, como já confirmado). **A medição exata do custo do PA será feita no ciclo-piloto** (não muda a decisão fiscal pedida).

**Consequência operacional (o que muda no dia a dia):** cada ciclo passa a ter **2 notas em vez de 1** (2 emissões/transmissões SEFAZ na LF; 2 escriturações na FB). **Não há aumento de movimentação física** nem de operação de armazém. Os sistemas internos que hoje assumem "1 nota por ciclo" serão ajustados (trabalho técnico nosso).

> **Por que não dá para manter 1 nota só:** numa nota mista (serviço + insumos), o contas a receber/pagar do **serviço absorve** os insumos simbólicos e a conta de compensação **não baixa** (provado nos 2 lados — saída e entrada). A separação em 2 documentos é o **único** arranjo em que a compensação baixa **nativamente**, sem lançamentos manuais de ajuste. A **pergunta 1 (seção 4)** permanece a decisão que destrava tudo.
