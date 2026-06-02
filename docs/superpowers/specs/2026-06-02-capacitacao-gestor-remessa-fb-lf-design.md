<!-- doc:meta
tipo: explanation
camada: L3
sot_de: desenho da capacitacao do gestor-estoque-odoo para remessa inter-company FB->LF avulsa (correcao L2/L3/L4)
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# Design — Capacitar `gestor-estoque-odoo` para remessa inter-company FB→LF (insumo direto, avulsa)

**Data:** 2026-06-02
**Branch:** `feat/capacitar-gestor-remessa-fb-lf`
**Autor:** Claude Code (dev) + Rafael (aprovação de diagnóstico e escopo)
**Status:** DESIGN APROVADO (diagnóstico de raiz validado pelo usuário) — pendente plano de implementação

---

> **Papel deste doc:** spec/design da correção das 3 camadas (L2/L3/L4) que capacitam o `gestor-estoque-odoo` a executar remessa avulsa FB→LF de insumo. **Não** é a implementação — é o blueprint que vira plano (writing-plans → execução). Dono após implementação: a folha `1.3.1` + o prompt do gestor.
> **Abra quando:** for revisar/ajustar o escopo da capacitação antes de implementar, ou precisar do "porquê" de cada correção.

## TOC

- [Contexto](#contexto)
- [Modelo-alvo](#2-modelo-alvo-constituição-appodooestoqueclaudemd--5-camadas)
- [Diagnóstico de raiz](#3-diagnóstico-de-raiz-evidência-da-auditoria-read-only)
- [Correções por camada](#4-correções-por-camada--modelo-alvo)
- [Estratégia de testes](#5-estratégia-de-testes-determinística--sem-evals-llm-preferência-do-usuário)
- [Canary](#6-canary-validação-real--os-2-produtos)
- [Riscos e mitigações](#7-riscos-e-mitigações)
- [Fora de escopo](#8-fora-de-escopo-yagni)
- [Ordem de implementação](#9-ordem-de-implementação-sugerida)

## Contexto

Pedido do usuário: remeter de **FB → LF** (industrialização) 2 insumos já em `FB/Estoque/MIGRAÇÃO`:
- `105000002` AROMA - ERVAS FINAS — 30,560 kg
- `105000044` SALSA TRITURADO — 5,36 kg
- Destino: `LF/Estoque`, lote **P-02/06** (lote criado na LF; na FB permanece `MIGRAÇÃO`).

Ao tentar executar via subagente `gestor-estoque-odoo`, ele **parou** reportando "não há caminho automatizado; o piloto foi manual". Investigação revelou que **o caminho automatizado EXISTE e foi validado em PROD** (`executar_fluxo_l3_1_2_x`, caso 627348 caminho A + AVULSO_FRASCO caminho B; folha `1.3-transferencia-completa.md` escrita v27+ S5) — mas três desvios da arquitetura impediram o gestor de chegar nele de forma autônoma.

> **Escopo (YAGNI, decidido com o usuário):** SÓ remessa de **insumo direto** (matéria-prima `tipo_produto='01'` remetida como está, **sem explodir BoM**). O caso PA-com-BoM (driver `e2e_remessa_criar.py`) fica fora.

## 2. Modelo-alvo (constituição `app/odoo/estoque/CLAUDE.md` — 5 camadas)

- **L2 — Skills:** átomos **genéricos e capazes dentro do seu objeto Odoo**. Idempotência e validações vivem DENTRO do átomo, baseadas no próprio objeto. Não dependem de contexto externo (ciclo de inventário).
- **L3 — Fluxos (Markdown):** ditam as **regras do jogo** (sequência, gotchas, pré/pós-condições). Compõem átomos.
- **L4 — Prompt do gestor:** **direciona** ao fluxo certo (árvore de decisão).

O diagnóstico abaixo bate com a leitura do usuário: a *estrutura* das 5 camadas existe, mas há **um furo concreto em cada camada** que, somados, tornam a operação inexecutável de forma autônoma.

## 3. Diagnóstico de raiz (evidência da auditoria read-only)

### 3.1 L2 — Skills não estão 100% "genéricas e capazes dentro do objeto"

| Skill (objeto) | Desvio | Evidência | Gotcha |
|---|---|---|---|
| `faturando-odoo` (`account.move`) | `transmitir_sefaz` exige `ajuste_ids >= 1` (`FALHA_AJUSTES_VAZIOS`); idempotência (D8.3) e propagação da chave saem do **`AjusteEstoqueInventario`** (modelo local de ciclo). Acopla a skill a "ciclo" → incapaz no caso avulso. A idempotência deveria vir do **próprio `account.move`** (`situacao_nf`/`chave_nfe`/`l10n_br_status`). | `app/odoo/estoque/scripts/faturamento.py:806-857` (assinatura `ajuste_ids: List[int]`, docstring D8.3) | — |
| `escriturando-odoo` (`DFe`) | `buscar_dfe` devolve `encontrado=True` para **DFe-resumo vazio** (`l10n_br_status='06'`, 0 `dfe.line`, XML vazio). Não qualifica o objeto → orchestrator escolhe caminho A → `gerar_po_from_dfe` cria PO vazia. | `app/odoo/estoque/scripts/escrituracao.py:1005-1020` (branch `else` → `'a_processar'`, sempre `encontrado=True`) | **G-ENT-2** |
| `operando-picking-odoo` (`stock.picking`) | `preencher_lotes_picking` cria/atualiza move.line só por `lot_name`, **sem fixar `company_id`** do lote destino → em contexto multi-company reaproveita o lote da FB e a entrada LF trava ("Empresas incompatíveis"). | `app/odoo/estoque/scripts/picking.py:1632-1665` (`write_data`/`nova_line` sem `company_id`; docstring L1511 delega criação ao Odoo via `lot_name`) | **G-ENT-6** |

### 3.2 L3 — Fluxo não dita todas as regras (folha `1.3` incompleta para o caso avulso)

- Não manda **cancelar o picking-companheiro "Transferir TERCEIROS"** (server action 1899, `picking_terceiro_id`) da saída — **G-ENT-1**. A Skill 5 já tem o verbo genérico "cancelar picking" (capacidade existe; o fluxo não a aciona). Evidência: grep por `companheiro|TERCEIROS|1899|picking_terceiro` nos 3 arquivos → 0 ocorrências.
- Não **força caminho B** para `INDUSTRIALIZACAO_FB_LF` na sequência executável; a decisão real depende de `buscar_dfe` (furado por 3.1). A tabela da folha 1.3 (linha 22) *diz* "sempre B", mas a função não força.
- Não dita como **originar o caso avulso** — assume "ajustes `AjusteEstoqueInventario` já `APROVADO`" (`1.1.1` linha 11; `1.3` linha 61). Não há skill/CLI que crie ajustes para remessa avulsa (Skill 6 só cobre pré-etapa CD/FB; criação ad-hoc é antipadrão A6).
- **G-ENT-5** (picking de entrada não auto-gera, conflito de rotas buy FB×LF): o orchestrator **detecta** (`FALHA_PASSO_7_SEM_PICKING`, `inventario_pipeline.py:3074-3078`) mas **não tem fallback** — para sem recuperação.

### 3.3 L4 — Prompt direciona para o lugar ERRADO (drift de status)

- `.claude/agents/gestor-estoque-odoo.md:93`: `1.3 ... ⬜ pendente v20+ (depende refator AP6)`. Mas AP6 foi resolvido (v24+), a folha 1.3 está `🟢 escrita` (v27+ S5) e a entrada foi validada em PROD. Lendo "⬜ pendente", o gestor abandona o caminho certo e cai no precedente manual.

## 4. Correções (por camada) — modelo-alvo

> Princípio inviolável: **corrigir a CAMADA, não a operação**. Tudo dry-run-first + idempotente. Sem hardcode de CFOP (motor fiscal deriva via `l10n_br_tipo_pedido`+`fiscal_position`).

### C1 — `faturando-odoo`: idempotência pelo próprio `account.move` (âncora opcional)

- Tornar `ajuste_ids` **opcional** (`Optional[List[int]] = None`) em `transmitir_sefaz` (e conferir `validar_invoice_pos_robo`, `polling_invoice`).
- **Idempotência PRIMÁRIA intra-Odoo:** antes de transmitir, ler o `account.move` — se `situacao_nf == 'autorizado'` (ou `chave_nfe` populada / `l10n_br_status` autorizado) → `IDEMPOTENT_SKIP`. Isto é o que protege contra dupla-transmissão SEFAZ, independente de ajustes.
- **Âncora opcional:** quando `ajuste_ids` fornecido, manter D8.3 (skip por fase do ajuste) + propagação de chave **como camada adicional de auditoria/rastreabilidade**, não como pré-requisito. Sem ajustes → pular essa camada (sem `FALHA_AJUSTES_VAZIOS`).
- **Compatibilidade:** comportamento atual (com ajustes) preservado 100%.
- **Risco-chave:** SEFAZ irreversível. A idempotência intra-Odoo deve ser robusta e testada exaustivamente (já-autorizado, rascunho, rejeitado).

### C2 — `escriturando-odoo`: `buscar_dfe` qualifica DFe-resumo vazio

- `buscar_dfe` passa a ler `dfe.line_ids` (count) e/ou `l10n_br_xml_dfe`. Status canônico ampliado: além de `pendente`/`processado`/`ausente`, distinguir **`resumo_vazio`** (DFe existe, 0 linhas / sem XML).
- `criar_dfe_a_partir_do_invoice_saida`: ao encontrar DFe-resumo existente, **popular** (via XML da saída + `action_processar_arquivo_manual`) em vez de retornar `IDEMPOTENT_EXISTE` sem conteúdo.
- Resultado: a decisão de caminho (no fluxo) trata `resumo_vazio` como **caminho B obrigatório** — skill agora qualifica o próprio objeto.

### C3 — `operando-picking-odoo`: `preencher_lotes_picking` fixa company do lote

- Receber `company_destino` (ou derivar do picking). Resolver/criar o `stock.lot` na **company destino** explicitamente (`StockLotService.buscar_por_nome(nome, product_id, company_id=destino)`; criar com `company_id=destino` se faltar — respeitando G031 lote-por-produto).
- Passar `lot_id` **explícito** na move.line (não só `lot_name`); guarda pós-condição: lote resolvido tem `company_id == destino`.
- Resultado: G-ENT-6 (Model B) automatizado — o lote `P-02/06` nasce na LF (company 5), não arrasta o lote FB.

### C4 — Fluxo L3: nova folha `1.3.1-remessa-avulsa-insumo.md` (entry-point avulso)

- Documenta a remessa **avulsa** (sem ciclo de inventário), compondo os átomos já corrigidos:
  1. (origem) saldo já em `{origem}/Estoque/{lote}` (pré-cond; ETAPA 0 interna é fluxo 2.2, fora desta folha).
  2. Pré-flight fiscal C5 (`auditando-cadastro-fiscal-odoo`) → `pode_faturar=True`.
  3. **Saída:** Skill 5 `criar_picking_inter_company` (linhas diretas, sem ajustes) → `validar_picking_inter_company` → Skill 8 `liberar_faturamento`(sem ajuste) → `polling_invoice` → `validar_invoice_pos_robo` → `transmitir_sefaz`(sem ajuste — C1).
  4. **G-ENT-1:** cancelar o picking-companheiro "TERCEIROS" (Skill 5 cancelar, contexto company origem) antes da entrada.
  5. **Entrada:** `executar_fluxo_l3_1_2_x` com `company_destino=5`, `lotes_data=[{P-02/06}]` (C3 garante company), **forçando caminho B** para `INDUSTRIALIZACAO_FB_LF` (C2) → `action_post`.
  6. **G-ENT-5:** se picking de entrada não nascer → diagnóstico claro + (se viável) fallback Skill 5 genérico; senão parar com instrução.
  7. Auditoria pós (`consultando-quant-odoo`): saldo final `LF/Estoque/P-02/06`.
- A folha `1.3` (com-ciclo) permanece; `1.3.1` é a variante avulsa.

### C5 — Prompt do gestor: corrigir drift + apontar avulsa

- `.claude/agents/gestor-estoque-odoo.md` árvore: `1.3` de `⬜ pendente` para `✅ disponível` (com ponteiro correto) + sub-nó `1.3.1` remessa avulsa.
- Sem inlinar lições históricas (D-V18-4) — só a árvore + ponteiro à folha.

## 5. Estratégia de testes (determinística — sem evals LLM, preferência do usuário)

- **pytest mockado** por correção (espelha padrão das skills existentes):
  - C1: `transmitir_sefaz` sem `ajuste_ids` (dry-run + idempotência intra-Odoo por `situacao_nf`); com `ajuste_ids` preserva D8.3.
  - C2: `buscar_dfe` → `populado` / `resumo_vazio` / `ausente`; `criar_dfe_a_partir_do_invoice_saida` popula resumo existente.
  - C3: `preencher_lotes_picking` resolve lote na company destino; pós-cond company correta.
- Atualizar baseline pytest do estoque (atualmente ~688+ verdes). Cada correção mantém os testes existentes verdes (zero regressão).
- Cobertura de skill (memória `feedback_skill_padrao_completo`): SKILL.md + cross-refs + ROADMAP + agente quando aplicável.

## 6. Canary (validação real — os 2 produtos)

Após as correções: o **gestor corrigido** roda a folha `1.3.1` para `105000002` (30,56kg) + `105000044` (5,36kg), dry-run → confirmação → SEFAZ → entrada LF (lote P-02/06) → auditoria. Estado de partida já pronto: saldo em `FB/Estoque/MIGRAÇÃO` (quants 267862/267863), cadastro fiscal corrigido (Fase 1). **SEFAZ exige confirmação explícita do usuário no momento.**

## 7. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| C1 mexe em `transmitir_sefaz` (SEFAZ irreversível) | Idempotência intra-Odoo robusta + testes exaustivos; comportamento com ajustes preservado; dry-run obrigatório no canary |
| G-ENT-5 (rotas) pode travar a entrada | Fluxo detecta + diagnóstico claro; fallback só se seguro; senão para (não força) |
| Regressão nas skills (usadas pelo orchestrator) | Manter compat retroativa; rodar suite pytest completa do estoque a cada correção |
| Worktree sem env → SQLite/ruído | `.env`/`.venv` linkados da raiz; passar `DATABASE_URL` se preciso |

## 8. Fora de escopo (YAGNI)

- Remessa de **PA com explosão de BoM** (driver de piloto).
- Demais direções da MATRIZ (PERDA_LF_FB, DEV_*, TRANSFERIR_*) — embora C1/C2/C3 as beneficiem indiretamente; não validadas aqui.
- Correção cadastral CFOP 5902→5949 (R3b) — decisão fiscal do usuário, fora das skills.

## 9. Ordem de implementação sugerida

1. **C5** (prompt drift) — trivial, destrava o roteamento.
2. **C1** (Skill 8 idempotência intra-Odoo) — desbloqueia o avulso; TDD.
3. **C2** (buscar_dfe resumo) + **C3** (lote company) — TDD.
4. **C4** (folha 1.3.1) — costura as regras.
5. **Canary** com o gestor corrigido.

> Detalhamento de tarefas → `writing-plans` (próximo passo).
