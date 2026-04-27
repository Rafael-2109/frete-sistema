# Atualizacao Memory Eval — 2026-04-27-1 (PARCIAL — sandbox bloqueado)

**Data**: 2026-04-27
**Health Score**: 85/100 (anterior: 84/100, delta: +1)
**Status**: PARCIAL — `.claude/atualizacoes/memory-eval/` bloqueado por sandbox; relatorio salvo em `/tmp/manutencao-2026-04-27/`. Historico nao foi atualizado.

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total sessoes | 461 |
| Sessoes ultima semana | 29 |
| Sessoes ultimo mes | 151 |
| Usuarios unicos | 22 |
| Media mensagens/sessao | 8.80 |
| Media custo/sessao (USD) | $2.36 |

**Delta vs 2026-04-20**: +27 sessoes (+6%), -16 na ultima semana (45 -> 29) — desaceleracao significativa, usuarios unicos estaveis (22).

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Importance | Avg Usage | Avg Effective | Avg Efficacy | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|----------------|-----------|---------------|--------------|------|----------|-----------|-----------|
| contextual | pessoal | 8 | 0.43 | 31.4 | 25.1 | 0.80 | 3 | 0 | 0 | 0 |
| operational | empresa | 16 | 0.83 | 155.4 | 90.9 | 0.585 | 1 | 0 | 7 | 0 |
| operational | pessoal | 26 | 0.56 | 33.1 | 25.4 | 0.768 | 2 | 0 | 5 | 0 |
| permanent | empresa | 4 | 0.90 | 210.8 | 95.0 | 0.451 | 0 | 0 | 4 | 3 |
| permanent | pessoal | 24 | 0.89 | 63.5 | 43.6 | 0.687 | 0 | 0 | 6 | 0 |
| structural | empresa | 131 | 0.74 | 90.3 | 51.4 | 0.570 | 17 | 0 | 45 | 0 |
| structural | pessoal | 88 | 0.67 | 10.0 | 6.1 | 0.606 | 9 | 0 | 3 | 2 |
| **TOTAL** | | **297** | | | | **0.613** | **32** | **0** | **70** | **5** |

**Observacoes**:
- Total: 272 -> 297 (+25, +9% em 7 dias) — crescimento desacelerou (era +38% no ciclo anterior)
- `structural/empresa`: 126 -> 131 (+5, +4%) — desaceleracao acentuada
- `structural/pessoal`: 68 -> 88 (+20, +29%) — continua o segmento de maior crescimento
- Cold: 32 -> 32 (estavel) — primeira parada apos crescimento exponencial dos ciclos anteriores
- Stale 30d: 62 -> 70 (+8) — crescimento moderado proporcional ao total
- Stale 60d: 2 -> 5 (+3) — alerta inicial (3 memorias `permanent/empresa` cruzaram o limite)
- Eficacia media subiu de 0.597 -> 0.613 (+2.7%)
- Zero conflitos detectados

---

## Top 20 Memorias Baixa Eficacia (Q3)

| # | Path | Efficacy | Usage | Effective | Category | User |
|---|------|----------|-------|-----------|----------|------|
| 1 | empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 0.000 | 32 | 0 | structural | u0 |
| 2 | empresa/regras/quando-o-usuario-envia-saudacao-e-pedido | 0.000 | 19 | 0 | structural | u0 |
| 3 | empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 0.000 | 10 | 0 | structural | u0 |
| 4 | corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente | 0.000 | 9 | 0 | structural | u18 |
| 5 | learned/expertise_demonstra-conhecimento-de-seguranca-web-csrf-tokens | 0.000 | 6 | 0 | structural | u1 |
| 6 | empresa/termos/modo-debug | 0.000 | 6 | 0 | structural | u0 |
| 7 | empresa/regras/operadores-do-teams-bot-possuem-user-id | 0.000 | 5 | 0 | operational | u0 |
| 8 | empresa/usuarios/kerley | 0.000 | 5 | 0 | structural | u0 |
| 9 | empresa/heuristicas/financeiro/consolidated (operational) | 0.000 | 3 | 0 | operational | u0 |
| 10 | empresa/termos/integracao-nf | 0.046 | 108 | 5 | structural | u0 |
| 11 | empresa/termos/confirmar-pedido | 0.049 | 81 | 4 | structural | u0 |
| 12 | empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo | 0.052 | 172 | 9 | operational | u0 |
| 13 | empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i | 0.061 | 49 | 3 | structural | u0 |
| 14 | system/download_config | 0.064 | 47 | 3 | structural | u1 |
| 15 | empresa/termos/cotacao | 0.074 | 27 | 2 | structural | u0 |
| 16 | corrections/o-usuario-interrompeu-uma-analise-que-havia-saido-do-escopo | 0.091 | 11 | 1 | structural | u18 |
| 17 | empresa/armadilhas/integracao/save-memory-ignora-target-user-id-sem-debug-mode | 0.106 | 47 | 5 | structural | u0 |
| 18 | empresa/pitfalls/agente/memory-injection-protocolo-vs-heuristica | 0.111 | 54 | 6 | structural | u0 |
| 19 | empresa/heuristicas/integracao/user-xml-nao-atualiza-por-threshold-de-sessoes | 0.124 | 386 | 48 | structural | u0 |
| 20 | empresa/armadilhas/logistica/prazo-d-0-em-embarques-do-dia-gera-risco-critico-atacadao | 0.139 | 36 | 5 | structural | u0 |

**Destaque critico**: 9 memorias com efficacy = 0 e usage >= 3 (8 na semana anterior, +1 nova: `learned/expertise_demonstra-conhecimento-de-seguranca-web-csrf-tokens` u1 com 6 usos). `user-xml-nao-atualiza-por-threshold-de-sessoes` estabilizou em 386 usos (parou de crescer), mas efficacy 0.124 confirma problema persistente.

---

## Sessoes por Usuario — Ultimos 30d (Q5)

| Usuario | Sessions | Mensagens | Custo (USD) | Ultima Sessao |
|---------|----------|-----------|-------------|---------------|
| Rafael (id=1) | 57 | 277 | $59.93 | 2026-04-24 |
| Claude Code (id=74) | 21 | 42 | $1.45 | 2026-04-10 |
| Gabriella (id=69) | 19 | 288 | $200.64 | 2026-04-27 |
| Elaine (id=67) | 17 | 160 | $28.31 | 2026-04-23 |
| Marcus Lima (id=18) | 12 | 547 | $279.94 | 2026-04-26 |
| Rafael (id=55) | 9 | 108 | $51.52 | 2026-04-21 |
| Denise (id=2) | 7 | 35 | $6.80 | 2026-04-16 |
| Thamires (id=27) | 5 | 14 | $1.22 | 2026-04-16 |
| Nicoly (id=71) | 1 | 38 | $13.54 | 2026-04-16 |
| Talita (id=17) | 1 | 4 | $0.20 | 2026-04-06 |
| Guilherme Silva (id=72) | 1 | 2 | $0.26 | 2026-04-14 |
| Jessica (id=4) | 1 | 2 | $0.18 | 2026-04-16 |

**Destaques**:
- Marcus Lima: +6 sessoes (6 -> 12), maior custo $279.94 (+$16) — uso intenso continua
- Gabriella: -3 sessoes (22 -> 19), MAS custo +15% ($173 -> $200) — sessoes mais caras
- Rafael (id=1): +6 sessoes (51 -> 57), custo caiu (-$11) — eficiencia maior
- Claude Code: -10 sessoes (31 -> 21), custo praticamente zerado
- Fernando saiu do recorte 30d

---

## Memorias Empresa (Q6) — user_id=0

Total: 131 memorias empresa (+5 vs ciclo anterior).

**Memorias empresa com efficacy = 0 persistentes**:

| Path | Usage | Reviewed |
|------|-------|----------|
| protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 32 | NULL |
| regras/quando-o-usuario-envia-saudacao-e-pedido | 19 | NULL |
| perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 10 | NULL |
| termos/modo-debug | 6 | NULL |
| usuarios/kerley | 5 | NULL |
| regras/operadores-do-teams-bot-possuem-user-id | 5 | NULL |
| heuristicas/financeiro/consolidated (operational) | 3 | NULL |
| termos/embarque-criado-pelo-sistema | 0 | NULL |
| regras/o-campo-purchase-order-id-no-odoo-pode-n | 0 | NULL |
| regras/ao-alterar-o-campo-tabela-frete-minimo-v | 1 | NULL |
| termos/relatoriofaturamentoimportado | 1 | NULL |

**Nota critica (4o ciclo consecutivo)**: NENHUMA das 131 memorias empresa possui `reviewed_at` preenchido. Identificado em 06/04, 13/04, 20/04, 27/04.

**Memorias empresa com efficacy alta (destaques)**:
- `causas/financeiro/nfs-de-entrada-frequentemente-fazem-match-automati` — 0.745 efficacy, 349 usos (criada/atualizada 27/04 por u69)
- `armadilhas/recebimento/vinculacao-nf-po-exige-update-em-dois-sistemas` — 0.739 efficacy, 138 usos
- `armadilhas/recebimento/consolidacao-bloqueada-por-ajuste-manual-po-pos-match` — 1.000 efficacy, 85 usos
- `protocolos/recebimento/desvinculacao-nf-po-requer-limpeza-em-tres-tabelas` — 0.752 efficacy, 210 usos
- `regras/financeiro/gabriella-sempre-referencia-pos-com-o-prefixo-c` — 0.926 efficacy, 148 usos (subiu vs 0.855)

---

## Knowledge Graph (Q4 + Q7)

### Entidades por Tipo

| Tipo | Total | Memorias Linkadas | Avg Mentions |
|------|-------|-------------------|--------------|
| conceito | 846 | 123 | 1.53 |
| processo | 118 | 66 | 1.34 |
| campo | 91 | 54 | 1.25 |
| produto | 74 | 35 | 2.07 |
| regra | 68 | 9 | 1.12 |
| termo | 60 | 36 | 1.97 |
| valor | 43 | 10 | 1.14 |
| uf | 31 | 8 | 4.06 |
| cliente | 27 | 21 | 8.63 |
| transportadora | 25 | 15 | 1.88 |
| usuario | 13 | 13 | 7.00 |
| cnpj | 10 | 8 | 1.40 |
| pedido | 7 | 5 | 5.43 |
| fornecedor | 6 | 6 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Total entidades**: 1.420 (+69 vs 1.351 ciclo anterior, +5%)
**KG Coverage estimada**: ~123/297 = **41.4%**

**Observacao**: KG coverage cairia mais lentamente (43.4% -> 41.4%, -2pp). Crescimento de entidades (+5%) menor que de memorias (+9%) gera queda residual. Crescimento de entidades desacelerou drasticamente vs ciclo anterior (+40% -> +5%).

### Top Relacoes Semanticas (Q7)

| Source | Relation | Target | Weight |
|--------|----------|--------|--------|
| DRY-RUN-OBRIGATORIO | precede | ACOES-EM-LOTE-ODOO | 5.0 |
| ASSAI | requer | CONFIRMACAO-MANUAL | 5.0 |
| PEDIDO-DE-VENDA | co_occurs | COTACAO | 3.5 |
| CONFIRMAR-PEDIDO | co_occurs | COTACAO | 3.5 |
| DENISE | pertence_a | COMPRAS | 3.0 |
| VCD | complementa | PEDIDO | 3.0 |
| ASSAI | complementa | MULTIPLAS-LOJAS-INDEPENDENTES | 3.0 |
| VCD (produto) | complementa | PEDIDO | 3.0 |
| VCD2667872 | co_occurs | SANNA | 3.0 |
| PEDIDO-DE-VENDA | co_occurs | CONFIRMAR-PEDIDO | 3.0 |
| GABRIELLA | responsavel_por | COMPRAS | 3.0 |

Top 11 relacoes identicas aos ultimos 2 ciclos — grafo semantico permanece estavel.

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor Medido | Score (0-100%) | Pontos |
|----------|------|--------------|----------------|--------|
| Eficacia media | 30% | 0.613 (range 0.2-0.7) | 82.6% | 24.8 |
| Taxa cold | 20% | 10.77% (32/297) | 98.1% | 19.6 |
| Stale 60d | 20% | 1.68% (5/297) | 100% | 20.0 |
| KG coverage | 15% | 41.4% (123/297) | 35.7% | 5.4 |
| Correcoes | 15% | 0.00 | 100% | 15.0 |
| **TOTAL** | **100%** | | | **85** |

**Comparativo serie historica**:

| Metrica | 2026-04-06 | 2026-04-13 | 2026-04-20 | 2026-04-27 | Delta 7d |
|---------|------------|------------|------------|------------|----------|
| Health Score | 81 | 84 | 84 | 85 | +1 |
| Total memorias | 128 | 197 | 272 | 297 | +25 |
| Cold | 14 | 15 | 32 | 32 | 0 |
| Stale 60d | 2 | 2 | 2 | 5 | +3 |
| KG coverage | - | 52.8% | 43.4% | 41.4% | -2.0pp |
| Eficacia media | - | 0.54 | 0.597 | 0.613 | +0.016 |
| Sessoes total | - | 391 | 434 | 461 | +27 |
| Sessoes ultima semana | - | 30 | 45 | 29 | -16 |
| Usuarios unicos | - | 21 | 22 | 22 | 0 |

---

## Recomendacoes Acionaveis

### R1 [URGENTE] — Auditar 9 memorias com efficacy=0 e usage >= 3

Nova memoria entrou na lista zero-efficacy: `learned/expertise_demonstra-conhecimento-de-seguranca-web-csrf-tokens` (u1, 6 usos). Provavel ruido de extracao automatica de "expertise".

Memorias legadas que persistem ha >= 21 dias (4o ciclo consecutivo no top zero):
- `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel` (32 usos, 0 efetivos)
- `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido` (19 usos, 0 efetivos)
- `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di` (10 usos, 0 efetivos)
- `empresa/termos/modo-debug` (6 usos, 0 efetivos)
- `empresa/usuarios/kerley` (5 usos, 0 efetivos)
- `empresa/regras/operadores-do-teams-bot-possuem-user-id` (5 usos, 0 efetivos)

**Acao**: Auditoria humana URGENTE. 77 carregamentos sem valor. Decisao: remover ou reescrever.

### R2 [CRITICO] — user-xml-nao-atualiza-por-threshold-de-sessoes (estabilizou)

Memoria estabilizou em 386 usos (igual ao ciclo anterior). Efficacy ainda 0.124 (48 efetivos). Bom: parou de crescer. Ruim: continua sendo carregada inutilmente.

**Acao**: Investigar por que e carregada tanto sem ajudar. Reescrever ou rebaixar prioridade. A estabilidade pode indicar "teto de carregamento" — remove-la economiza memoria de contexto.

### R3 [ALTO] — Reverter queda lenta de KG coverage (41.4% -> meta 70%)

Queda continuou (43.4% -> 41.4%, -2pp). 174 memorias sem entidades. Crescimento de entidades desacelerou (+5% vs +9% memorias).

**Acao**: Rodar extrator de entidades em batch sobre as 25 memorias criadas nos ultimos 7 dias. Priorizar `structural/pessoal` (categoria que mais cresceu, +20).

### R4 [ALTO] — Implementar revisao formal de memorias empresa (4o ciclo)

NENHUMA das 131 memorias empresa tem `reviewed_at` preenchido. Recomendado em 06/04, 13/04, 20/04, 27/04. Continua nao implementado.

**Acao**: Criar processo de curadoria que preencha `reviewed_at` apos verificacao. Comecar pelas 11 memorias empresa com efficacy=0. Bloquear novas escritas em `user_id=0` sem `reviewed_at` ou marcar com flag.

### R5 [MEDIO] — Investigar 3 memorias permanent/empresa que cruzaram stale 60d

Stale 60d subiu de 2 para 5 (+3). Q2 mostra que 3 memorias `permanent/empresa` cruzaram a barreira. Como sao "permanent", precisam de revisao especial.

**Acao**: Identificar quais sao via Q3 expandida. Se ainda relevantes, atualizar. Se obsoletas, mover para tier menor ou arquivar com prefixo `_archived_`.

### R6 [MEDIO] — Revisar memorias permanent com baixa efficacy

- `corrections/capacidade-caminhoes-consultar-veiculos` — efficacy 0.199, 211 usos (subiu de 206)
- `corrections/agent-sdk-production-scope` — efficacy 0.212, 33 usos (estavel)
- `corrections/confirmar-para-pedido-odoo` — efficacy 0.526, 331 usos (subiu de 327)

**Acao**: Memorias permanentes devem ser de alta qualidade. Revisar essas 3 e reescrever ou rebaixar.

### R7 [MEDIO] — Consolidar termos de glossario redundantes (3o ciclo)

Termos `integracao-nf` (0.046, 108 usos), `confirmar-pedido` (0.049, 81 usos), `cotacao` (0.074, 27 usos) sao carregados frequentemente mas raramente efetivos.

**Acao**: Consolidar termos redundantes ou enriquecer com contexto operacional. Considerar que entidades do KG ja capturam esses conceitos (PEDIDO-DE-VENDA, CONFIRMAR-PEDIDO, COTACAO ja sao nodes).

### R8 [BAIXO] — Monitorar desaceleracao geral

Crescimento desacelerou: total +9% (vs +38% anterior), sessoes ultima semana -36%. Possivel sinal de:
- Estabilizacao natural pos-pico
- Reducao de uso (ferias, projeto especifico finalizado)
- Bloqueio em algum subsistema

**Acao**: Sem acao imediata. Monitorar proximo ciclo.

---

## Resumo Executivo

O sistema de memorias atingiu health score 85/100 (+1 vs ciclo anterior, melhor pontuacao da serie). Eficacia media subiu para 0.613 (+2.7%) e cold tier estabilizou em 32 (parou de crescer). Stale 60d subiu de 2 para 5 (3 memorias `permanent/empresa` cruzaram limite). Crescimento total desacelerou para +9% (vs +38%, +75% e +54% nos ciclos anteriores), assim como sessoes da ultima semana caiu 36% (45 -> 29). Permanecem 9 memorias com efficacy zero (1 nova: `learned/expertise_csrf-tokens`). Pela 4a vez, ZERO memorias empresa tem `reviewed_at` preenchido. Acoes URGENTES: R1 (auditar zero-efficacy), R2 (intervir em user-xml de 386 loads), R4 (implementar processo de revisao empresa), R5 (investigar 3 novas stale 60d em permanent/empresa).
