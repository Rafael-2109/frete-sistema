# Atualizacao Memory Eval — 2026-05-18-1

**Data**: 2026-05-18
**Health Score**: 80/100 (-2 vs 2026-05-11)
**Status**: OK — todas as 7 queries executaram

---

## Resumo Executivo

Avaliacao bem-sucedida apos falha do ciclo anterior (MCP Render reconectado). Sistema continua **saudavel mas em tendencia de desaceleracao**: health score 80 (queda de 2 pontos vs 2026-05-11 = 82, queda de 6 vs pico 2026-05-05 = 86).

**Crescimento**: 338 -> 378 memorias (+40, +11.8%); 539 -> 592 sessoes (+53, +9.8%); 23 -> 25 usuarios unicos (+2).

**Drivers da queda**:
- **Cold em aceleracao**: 37 -> 40 (+3, +8%) — agora 10.58% do total (acima do threshold ideal de 10%).
- **Stale 60d voltou a crescer**: 35 -> 51 (+16, +45.7%) apos a explosao do ciclo anterior. Agora 13.49% do total — driver principal da queda.
- **KG coverage subiu mas ainda baixa**: 39.05% -> 50.79% (+11.74pp) — primeira melhora em 7 ciclos. Total entidades pulou de patamar ~1000 para 1672 (+670).
- **Empresa explodiu mais**: 163 -> 182 (+19, +11.6%). 77 ainda sem `reviewed_at` (42.3%).

**Highlight positivo**: KG saltou de coverage 39% -> 50.79%, 1672 entidades, 5925 relacoes, **zero entidades orfas**.

---

## Metricas de Sessoes

| Metrica | Valor |
|---------|-------|
| Total sessoes | 592 |
| Ultima semana | 52 (+11 vs 41) |
| Ultimos 30 dias | 161 |
| Usuarios unicos (total) | 25 |
| Avg mensagens/sessao | 8.44 |
| Avg custo/sessao USD | 2.62 |

**Top usuarios (30d)**:
| User | Sessoes | Mensagens | Custo USD |
|------|---------|-----------|-----------|
| Rafael (1) | 60 | 391 | 200.00 |
| Marcus Lima (18) | 34 | 302 | 72.35 |
| Gabriella (69) | 18 | 230 | 187.52 |
| Elaine (67) | 14 | 86 | 35.51 |
| Rafael (55) | 7 | 60 | 47.07 |

---

## Memorias por Categoria/Escopo

| Categoria | Escopo | Total | Avg Imp | Avg Use | Avg Efic | Cold | Stale 30d | Stale 60d |
|-----------|--------|-------|---------|---------|----------|------|-----------|-----------|
| contextual | pessoal | 11 | 0.45 | 32.9 | 28.27 | 3 | 3 | 0 |
| operational | empresa | 18 | 0.84 | 159.3 | 98.94 | 2 | 12 | 4 |
| operational | pessoal | 34 | 0.55 | 33.3 | 27.29 | 2 | 13 | 5 |
| permanent | empresa | 4 | 0.90 | 245.5 | 130.5 | 0 | 4 | 4 |
| permanent | pessoal | 31 | 0.88 | 66.4 | 49.19 | 0 | 8 | 5 |
| structural | empresa | 158 | 0.76 | 88.9 | 53.72 | 23 | 87 | 32 |
| structural | pessoal | 122 | 0.67 | 9.9 | 6.50 | 10 | 67 | 1 |

**Total**: 378 memorias (+40 vs ciclo anterior)
**Cold**: 40 (10.58%)
**Stale 60d**: 51 (13.49%)
**Avg efficacy global**: 0.573

---

## Top Memorias Baixa Eficacia (efficacy < 0.3, usage >= 3)

| Path | Cat | Use | Eff | Efic |
|------|-----|-----|-----|------|
| empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel.xml | struct | 32 | 0 | 0.00 |
| empresa/armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus.xml | struct | 20 | 0 | 0.00 |
| empresa/regras/quando-o-usuario-envia-saudacao-e-pedido.xml | struct | 19 | 0 | 0.00 |
| empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di.xml | struct | 12 | 0 | 0.00 |
| corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente.xml (u18) | struct | 9 | 0 | 0.00 |
| empresa/termos/modo-debug.xml | struct | 6 | 0 | 0.00 |
| empresa/usuarios/kerley.xml | struct | 5 | 0 | 0.00 |
| empresa/regras/operadores-do-teams-bot-possuem-user-id.xml | op | 5 | 0 | 0.00 |
| empresa/termos/integracao-nf.xml | struct | 108 | 5 | 0.046 |
| empresa/termos/confirmar-pedido.xml | struct | 81 | 4 | 0.049 |
| empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml | op | 172 | 9 | 0.052 |
| empresa/correcoes/build_artifact_pnpm.md | op | 36 | 2 | 0.056 |
| empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i.xml | struct | 49 | 3 | 0.061 |
| system/download_config.xml (u1) | struct | 47 | 3 | 0.064 |
| _archived_sessao-teams-reinicia-antes-de-subagente-concluir.xml | struct | 15 | 1 | 0.067 |
| empresa/termos/cotacao.xml | struct | 27 | 2 | 0.074 |
| corrections/o-usuario-interrompeu-uma-analise (u18) | struct | 11 | 1 | 0.091 |
| empresa/armadilhas/integracao/save-memory-ignora-target-user-id-sem-debug-mode.xml | struct | 47 | 5 | 0.106 |
| empresa/pitfalls/agente/memory-injection-protocolo-vs-heuristica.xml | struct | 54 | 6 | 0.111 |
| empresa/heuristicas/integracao/user-xml-nao-atualiza-por-threshold-de-sessoes.xml | struct | **413** | 55 | 0.133 |

**Destaques**:
- **8 memorias zero-efficacy** (era 13 no ciclo anterior — melhora de -5)
- **`user-xml-nao-atualiza-por-threshold-de-sessoes.xml`**: 7o ciclo na lista, agora com 413 usos (+ ~60) e efficacy 0.133 — protocolo ativo mas marcado como nao-efetivo. Trigger de save-memory esta quebrado.
- **`memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml`**: 172 usos, efficacy 0.052 — meta-pitfall sobre proprio sistema, paradoxalmente nao-efetivo.

---

## Knowledge Graph

| Tipo Entidade | Total | Linked Memories | Avg Mentions |
|---------------|-------|-----------------|--------------|
| conceito | 1094 | 148 | 1.45 |
| processo | 178 | 91 | 1.39 |
| campo | 131 | 74 | 1.19 |
| produto | 81 | 40 | 1.98 |
| termo | 70 | 44 | 1.86 |
| regra | 68 | 9 | 1.12 |
| valor | 67 | 24 | 1.18 |
| uf | 62 | 25 | 4.06 |
| cliente | 32 | 26 | 7.81 |
| transportadora | 28 | 18 | 1.86 |
| pedido | 24 | 18 | 2.29 |
| cnpj | 14 | 12 | 1.43 |
| usuario | 13 | 13 | 7.00 |
| fornecedor | 7 | 7 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Totais**:
- Entidades: **1672** (de ~1000 ciclo anterior, +670)
- Relacoes: **5925**
- Coverage: **50.79%** (192/378 memorias linkadas) — primeira melhora em 7 ciclos (+11.74pp)
- Orfas: **0**

**Top relacoes semanticas** (peso >= 3):
- ASSAI --requer--> CONFIRMACAO-MANUAL (5)
- DRY-RUN-OBRIGATORIO --precede--> ACOES-EM-LOTE-ODOO (5)
- PEDIDO-DE-VENDA <-->co_occurs<--> COTACAO (3.5)
- CONFIRMAR-PEDIDO <-->co_occurs<--> COTACAO (3.5)
- VCD --complementa--> PEDIDO (3)
- GABRIELLA --responsavel_por--> COMPRAS (3)

---

## Memorias Empresa (user_id=0) — Detalhe

| Metrica | Valor |
|---------|-------|
| Total | 182 (+19) |
| Sem reviewed_at | 77 (42.3%) |
| Revisao stale > 30d | 0 |
| Zero usage | 6 |
| Zero efficacy (use > 0) | 9 |
| Baixa efficacy + use >= 10 | 11 |
| Avg efficacy | 0.543 |
| Avg importance | 0.77 |
| Cold | 25 (13.7%) |

**Observacao**: 77 memorias empresa nunca passaram por revisao humana (era 163 sem reviewed_at no ciclo anterior — melhora significativa de -86). Porem nenhuma foi marcada como "revisao stale > 30d", o que indica que apenas a leitura mudou (alguma flag administrativa) ou houve reset.

---

## Health Score Detalhado

| Dimensao | Peso | Valor | Score |
|----------|------|-------|-------|
| Eficacia media | 30% | 0.573 (linear 0.2->0.7) | 22.4 |
| Taxa cold | 20% | 10.58% (linear 50%->10%) | 19.7 |
| Stale 60d | 20% | 13.49% (linear 40%->5%) | 15.1 |
| KG coverage | 15% | 50.79% (linear 20%->80%) | 7.7 |
| Correcoes | 15% | 0.0 (avg) | 15.0 |
| **TOTAL** | 100% | | **80** |

---

## Comparativo Serie Historica

| Metrica | 04-06 | 04-13 | 04-20 | 04-27 | 05-05 | 05-11 | 05-18 |
|---------|-------|-------|-------|-------|-------|-------|-------|
| Health | 81 | 83 | 84 | 85 | 86 | 82 | **80** |
| Memorias | 128 | 220 | 272 | 297 | 317 | 338 | **378** |
| Sessoes | - | - | - | 461 | 502 | 539 | **592** |
| Cold | 14 | - | - | 32 | 37 | 37 | **40** |
| Stale 60d | 2 | - | - | 5 | 6 | 35 | **51** |
| KG cov% | - | - | - | 41.4 | 40.1 | 39.05 | **50.79** |
| Avg eff | - | - | - | - | 0.641 | 0.630 | **0.573** |

**Tendencia**: Score em queda pelo 2o ciclo consecutivo (86 -> 82 -> 80). Driver principal: stale 60d cresce de 6 -> 35 -> 51 (8.5x em 2 ciclos). Eficacia media tambem caindo (0.641 -> 0.573, -10.6%).

---

## Recomendacoes

### R1 [URGENTE] — Auditoria de zero-efficacy (8 memorias)
8 memorias com usage >= 3 e effective_count = 0. Acoes:
- **Marcar arquivada** ou **deletar** (efficacy nao-recuperavel apos ciclos repetidos):
  - `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel.xml` (u32, ciclo recorrente)
  - `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido.xml` (u19)
  - `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di.xml` (u12)
  - `corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente.xml` (u18, u9)
  - `empresa/termos/modo-debug.xml` (u6)
  - `empresa/usuarios/kerley.xml` (u5)
  - `empresa/regras/operadores-do-teams-bot-possuem-user-id.xml` (u5)
- **Aguardar dados** apos investigacao do bug `user-xml-nao-atualiza-por-threshold-de-sessoes`:
  - `empresa/armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus.xml` (u20, criada 2026-05-13)

### R2 [CRITICO] — `user-xml-nao-atualiza-por-threshold-de-sessoes` (7o ciclo)
413 usos, efficacy 0.133. Memoria descreve bug de save-memory que ela mesma viola. Hipoteses:
- Trigger `effective_count` esta marcando como nao-efetivo errado (bug de calculo).
- Importance_score = 0.4 nao reflete uso real (importance baixa explica baixa eficacia).
- O proprio bug que ela descreve (save-memory ignora target_user_id sem debug_mode) impede a atualizacao dos contadores.

**Acao**: Investigar codigo de tracking de `effective_count` em `app/agente/services/`. Esta e a 7a recomendacao consecutiva sem resolucao.

### R3 [URGENTE] — Stale 60d em alta (35 -> 51, +45.7%)
51 memorias nao atualizadas em 60+ dias (13.49% do total). Distribuicao:
- structural/empresa: 32 (era 23 — +9)
- permanent/pessoal: 5 (estavel)
- operational/pessoal: 5 (estavel)
- operational/empresa: 4 (estavel)
- permanent/empresa: 4 (estavel)
- structural/pessoal: 1 (era 0)

**Acao**: Auditar as 32 `structural/empresa` stale 60d. Se ainda validas, refresh `updated_at`. Se obsoletas, mover para cold ou arquivar.

### R4 [ALTO] — KG melhorou mas precisa consolidar
KG saltou de 39% -> 50.79% coverage. **Validar a saude do novo crescimento**:
- 670 novas entidades de uma vez levanta suspeita de batch ingest.
- 0 entidades orfas e bom sinal.
- `regra` tem 68 entidades mas apenas 9 linked memories — entidades sao geradas mas nao linkam de volta.

**Acao**: Investigar de onde vieram as 670 novas entidades. Pode ser bom (re-extraction) ou ruim (duplicacao).

### R5 [ALTO] — Empresa: 77 sem reviewed_at (era 163)
77 memorias empresa sem revisao humana. Houve reducao significativa vs 163 do ciclo anterior, mas ainda 42.3% do total. Priorizar revisao das 8 zero-efficacy (R1) e as 4 stale 60d em `operational/empresa`.

### R6 [MEDIO] — Cold tier crescendo (37 -> 40)
40 memorias cold (10.58%, acima do threshold ideal de 10%). Distribuicao:
- structural/empresa: 23
- structural/pessoal: 10
- contextual/pessoal: 3
- operational/empresa: 2
- operational/pessoal: 2

**Acao**: Validar que o algoritmo de cold-tier nao esta sendo agressivo demais (false positives em memorias ainda uteis).

### R7 [MEDIO] — `permanent` com baixa efficacy
- permanent/empresa: avg 130.5 effective sobre 245.5 usage = 53.1% efficacy
- permanent/pessoal: avg 49.19 / 66.4 = 74.0% efficacy

permanent/empresa abaixo do esperado (deveria ser > 70%). 4 memorias, possivelmente fixas tanto na lista que ja nao agregam valor unico.

### R8 [BAIXO] — Crescimento de memorias em aceleracao
+40 memorias (+11.8%) em uma semana. Tendencia de crescimento se mantida levara a 500+ memorias em 4 semanas. Considerar:
- Politica de retencao automatica.
- Auto-merge de memorias semanticamente equivalentes (via KG).

---

## Insights da Sessao

1. **KG voltou a crescer** apos 6 ciclos de queda. Investigar causa (batch ingest? re-extraction?).
2. **`reviewed_at` melhorou drasticamente** (163 -> 77 nao revisadas). Provavel acao manual entre 05-11 e 05-18.
3. **Zero-efficacy caiu** de 13 para 8 — algumas memorias foram revisadas/arquivadas.
4. **Avg efficacy continua caindo** (0.641 -> 0.630 -> 0.573, -10.6% em 2 ciclos) — sinal de fadiga do sistema ou crescimento desordenado.
5. **Custo Gabriella desproporcional**: 18 sessoes / 187 USD = ~10.4 USD/sessao (vs media 2.62). Investigar uso intensivo.

---

## Checklist Pre-Commit

- [x] Todas as 7 queries executaram (Q1-Q7 OK; Q6 substituida por aggregate para evitar truncation)
- [x] Health score calculado (80/100)
- [x] Recomendacoes geradas (8: R1-R8)
- [x] Relatorio gerado
- [x] `historico.md` atualizado
