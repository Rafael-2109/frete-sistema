<!-- doc:meta
tipo: how-to
camada: L1
sot_de: fluxo operacional industrializacao FB-LF (visao do usuario)
hub: docs/industrializacao-fb-lf/README.md
superseded_by: —
atualizado: 2026-06-15
-->
# POP — Industrialização por Encomenda FB↔LF (instrumento de trabalho)

> **Papel:** POP operacional (visão do usuário) — passo a passo das 5 etapas da industrialização FB↔LF para operadores FB/LF, PCP e fiscal.

> **Para quem:** operadores FB (expedição/fiscal), operadores LF (expedição/faturamento), PCP.
> **O que é:** a **FB** (NACOM GOYA, encomendante) envia insumos para a **LF** (LA FAMIGLIA, industrializadora); a LF produz o produto acabado (PA) e o devolve à FB. O objetivo do controle é que **os insumos de terceiros não inflem o estoque** e que o **custo volte para o PA** (PA = serviço + insumos).
> **Regra de ouro:** o operador faz **o de sempre** (cria o picking e transmite a NF principal). O sistema deriva o resto. **Não monte componentes à mão** nem escriture DFe de industrialização manualmente — o sistema cuida disso (ver "Status de automação").

---

## Papéis envolvidos

| Papel | Responsabilidade no fluxo |
|---|---|
| **Operador FB — expedição** | Etapa 1 (envia a remessa de insumos para a LF) |
| **Operador LF — recebimento** | Etapa 2 (recebe/escritura a remessa) |
| **PCP / Produção LF** | Etapa 3 (produz o PA — ordem de produção) |
| **Operador LF — faturamento** | Etapa 4 (cria o picking do PA e transmite a NF de serviço) |
| **Operador / Fiscal FB** | Etapa 5 (confere a entrada do PA na FB) |

---

## O fluxo em 5 etapas

> Em cada etapa: **"Você faz"** = ação manual do operador · **"O sistema faz"** = derivado automaticamente (alvo).

### Etapa 1 — FB envia a remessa de insumos para a LF
- **Você faz (FB):** separa os insumos da ordem e emite a **NF de remessa (CFOP 5901)** para a LF; transmite na SEFAZ.
- **O sistema faz:** registra que aqueles insumos saíram em poder de terceiro (lança a "conta de remessa" — ATIVA). Esse valor fica "em aberto" até o retorno.
- **Atenção:** a NF de remessa é a **referência** de todo o ciclo. Os mesmos insumos (e valores) voltarão no retorno (Etapa 4/5).

### Etapa 2 — LF recebe a remessa
- **Você faz (LF):** escritura a NF de remessa que chegou (entrada de industrialização).
- **O sistema faz:** dá entrada nos insumos em **"Materiais de Terceiros"** (sem virar estoque próprio da LF — são da FB).
- **Atenção:** os insumos ficam separados do estoque próprio da LF. Não vender/consumir fora da ordem de industrialização.

### Etapa 3 — LF produz o PA
- **Você faz (PCP/LF):** abre e conclui a **ordem de produção (MO)** do PA, consumindo os insumos de terceiros (+ insumos próprios da LF, ex.: água/MRO).
- **O sistema faz:** baixa os insumos consumidos e gera o PA acabado, pronto para devolver.
- **Atenção:** registre o **lote** do PA — ele liga a produção à remessa correta (o sistema usa essa genealogia para montar a NF de retorno dos insumos).

### Etapa 4 — LF fatura o retorno para a FB  ⭐ (onde o trabalho diminui)
- **Você faz (LF):** cria **1 picking só com o PA** e transmite a **NF de serviço (CFOP 5124)** — exatamente como uma venda normal.
- **🔄 O que MUDA:** **você NÃO adiciona mais os componentes (5902) à mão.** A NF de serviço sai só com a linha do PA.
- **O sistema faz (2 gatilhos):**
  1. **Ao criar a NF de serviço** → monta automaticamente a **2ª NF, de retorno dos insumos (CFOP 5902)**, descobrindo os componentes pela ordem de produção do lote, e vincula as duas (rastreabilidade).
  2. **Ao transmitir a NF de serviço** → transmite a NF de insumos na sequência.
- **Atenção:** são **2 NFs por ciclo** (1 de serviço, com valor; 1 de insumos, valor de retorno = valor da remessa). A NF de insumos **não gera cobrança** (é só a devolução dos materiais).

### Etapa 5 — FB recebe o PA de volta
- **Você faz (FB):** confere o recebimento físico do PA.
- **🔄 O que MUDA:** **você NÃO escritura mais os 2 DFes à mão.**
- **O sistema faz:** escritura as 2 NFs na FB (serviço + insumos), dá entrada do PA no estoque e **ajusta o custo do PA** para incorporar os insumos (PA = serviço + insumos). A "conta de remessa" (Etapa 1) é baixada — o ciclo fecha.
- **Atenção:** ao final, o PA está no estoque da FB pelo custo cheio e os insumos de terceiros **não ficam mais "em aberto"**.

---

## O que NUNCA fazer (pega o fluxo)
- ❌ **Adicionar os componentes 5902 na NF de serviço manualmente** (Etapa 4) — o sistema os monta; duplicar gera NF errada.
- ❌ **Escriturar os DFes de industrialização na FB manualmente** com a operação padrão (Etapa 5) — re-infla o estoque. O sistema usa a operação simbólica correta.
- ❌ **Transmitir a NF de insumos antes da NF de serviço** — a ordem importa (a de insumos referencia a de serviço).
- ❌ **Faturar a NF de insumos como venda/cobrança** — ela é retorno de material (valor de devolução, sem título a receber).

---

## Status de automação (atualizado 2026-06-15)

> ⚠️ **As Etapas 4 e 5 estão em transição.** O **mecanismo** já foi validado de ponta a ponta no piloto (produto 4870112), mas os **gatilhos automáticos** ainda estão em construção. Enquanto isso, a montagem da 2ª NF e a escrituração na FB são feitas pela equipe de desenvolvimento (sob demanda), não pelo operador.

| Peça | Status |
|---|---|
| Etapas 1–3 (remessa, entrada LF, produção) | ✅ **Em produção** (fluxo normal de hoje) |
| Etapa 4 — emissão das 2 NFs + transmissão SEFAZ | ✅ **Mecanismo provado** (piloto autorizado na SEFAZ) · 🔧 **gatilho automático em construção** |
| Etapa 5 — escrituração na FB + ajuste de custo | ✅ **Mecanismo provado** (piloto, gate contábil fechado) · 🔧 **gatilho automático em construção** |
| ETL de faturamento ignora as NFs inter-company da LF | ✅ **Corrigido** (não conta o retorno como venda; aguarda deploy) |

**Durante a transição:** o operador LF segue criando o picking e transmitindo a **NF de serviço** normalmente. A 2ª NF (insumos) e a escrituração na FB são acompanhadas pela equipe de desenvolvimento por enquanto.

---

## Referências (para a equipe técnica)
- Desenho e decisões do fluxo automatizado: `SOT_OPERACOES.md §6` (requisitos da Contadora) e **§6.2** (automação dos 2 gatilhos).
- Mecanismo Odoo/CIEL IT e provas: `ACHADOS_TECNICOS.md` (§"FASE B" emissão/SEFAZ · §"R2.3b" entrada FB).
- Estado e próximo passo: `README.md` · `PROMPT_PROXIMA_SESSAO.md`.

## Contexto
Documento — industrializacao por encomenda FB↔LF. Tema: POP operacional (visão do usuário) das 5 etapas.
