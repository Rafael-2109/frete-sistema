# Atualizacao Memory Eval — 2026-04-20-1

**Data**: 2026-04-20
**Health Score**: 84/100 (anterior: 84/100, delta: 0)

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total sessoes | 434 |
| Sessoes ultima semana | 45 |
| Sessoes ultimo mes | 157 |
| Usuarios unicos | 22 |
| Media mensagens/sessao | 8.73 |
| Media custo/sessao (USD) | $2.27 |

**Delta vs 2026-04-13**: +43 sessoes (+11%), +15 na ultima semana (30 -> 45), +1 usuario unico.

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Importance | Avg Usage | Avg Effective | Avg Efficacy | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|----------------|-----------|---------------|--------------|------|----------|-----------|-----------|
| contextual | pessoal | 8 | 0.43 | 26.5 | 21.0 | 0.79 | 3 | 0 | 0 | 0 |
| operational | empresa | 16 | 0.83 | 146.9 | 81.1 | 0.55 | 1 | 0 | 4 | 0 |
| operational | pessoal | 26 | 0.56 | 29.4 | 21.7 | 0.74 | 2 | 0 | 5 | 0 |
| permanent | empresa | 4 | 0.90 | 206.3 | 91.5 | 0.44 | 0 | 0 | 4 | 0 |
| permanent | pessoal | 24 | 0.89 | 56.6 | 37.0 | 0.65 | 0 | 0 | 6 | 0 |
| structural | empresa | 126 | 0.74 | 88.8 | 49.0 | 0.55 | 17 | 0 | 40 | 0 |
| structural | pessoal | 68 | 0.68 | 11.4 | 6.9 | 0.60 | 9 | 0 | 3 | 2 |
| **TOTAL** | | **272** | | | | **0.597** | **32** | **0** | **62** | **2** |

**Observacoes**:
- `structural/empresa` cresceu de 99 -> 126 (+27, +27%), concentra 46% das memorias e 53% das cold
- `structural/pessoal` dobrou: 33 -> 68 (+35, +106%) — crescimento mais forte do ciclo
- Total: 197 -> 272 (+75, +38% em 7 dias) — crescimento continua acelerado
- Cold: 15 -> 32 (+17, +113%) — tendencia de deterioracao preocupante
- Stale 30d: 46 -> 62 (+16) ainda controlado mas crescendo
- Stale 60d: 2 -> 2 (estavel) — ponto forte
- Zero conflitos detectados em todas as categorias

---

## Top 20 Memorias Baixa Eficacia (Q3)

Memorias com usage >= 3 e efficacy < 0.3 (candidatas a revisao/remocao):

| # | Path | Efficacy | Usage | Effective | Category |
|---|------|----------|-------|-----------|----------|
| 1 | empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 0.000 | 32 | 0 | structural |
| 2 | empresa/regras/quando-o-usuario-envia-saudacao-e-pedido | 0.000 | 19 | 0 | structural |
| 3 | empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 0.000 | 10 | 0 | structural |
| 4 | corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente (u18) | 0.000 | 9 | 0 | structural |
| 5 | empresa/termos/modo-debug | 0.000 | 6 | 0 | structural |
| 6 | empresa/regras/operadores-do-teams-bot-possuem-user-id | 0.000 | 5 | 0 | operational |
| 7 | empresa/usuarios/kerley | 0.000 | 5 | 0 | structural |
| 8 | empresa/heuristicas/financeiro/consolidated (u0 operational) | 0.000 | 3 | 0 | operational |
| 9 | empresa/termos/integracao-nf | 0.046 | 108 | 5 | structural |
| 10 | empresa/termos/confirmar-pedido | 0.049 | 81 | 4 | structural |
| 11 | empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo | 0.052 | 172 | 9 | operational |
| 12 | empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i | 0.061 | 49 | 3 | structural |
| 13 | system/download_config | 0.064 | 47 | 3 | structural |
| 14 | empresa/termos/cotacao | 0.074 | 27 | 2 | structural |
| 15 | corrections/o-usuario-interrompeu-uma-analise-que-havia-saido-do-escopo | 0.091 | 11 | 1 | structural |
| 16 | empresa/armadilhas/financeiro/ordenacao-cronologica-mes-exige-parse-nao-sort-lexicografico | 0.100 | 10 | 1 | structural |
| 17 | empresa/armadilhas/integracao/save-memory-ignora-target-user-id-sem-debug-mode | 0.106 | 47 | 5 | structural |
| 18 | empresa/pitfalls/agente/memory-injection-protocolo-vs-heuristica | 0.107 | 28 | 3 | structural |
| 19 | empresa/heuristicas/integracao/user-xml-nao-atualiza-por-threshold-de-sessoes | 0.124 | 386 | 48 | structural |
| 20 | empresa/regras/pedidos-para-a-rede-assai-no-odoo-precis | 0.139 | 79 | 11 | structural |

**Destaque critico**: 8 memorias com efficacy = 0 e usage >= 3 (6 na semana anterior, +2). A memoria `user-xml-nao-atualiza-por-threshold-de-sessoes` saltou de 201 -> 386 usos mantendo efficacy baixissima (0.124) — custo de contexto elevado.

---

## Sessoes por Usuario — Ultimos 30d (Q5)

| Usuario | Sessions | Mensagens | Custo (USD) | Ultima Sessao |
|---------|----------|-----------|-------------|---------------|
| Rafael (id=1) | 51 | 222 | $71.39 | 2026-04-17 |
| Claude Code (id=74) | 31 | 62 | $2.47 | 2026-04-10 |
| Gabriella (id=69) | 22 | 308 | $173.39 | 2026-04-17 |
| Elaine (id=67) | 19 | 158 | $22.15 | 2026-04-17 |
| Rafael (id=55) | 8 | 106 | $51.39 | 2026-04-15 |
| Thamires (id=27) | 7 | 30 | $7.90 | 2026-04-16 |
| Denise (id=2) | 7 | 35 | $6.80 | 2026-04-16 |
| Marcus Lima (id=18) | 6 | 486 | $263.58 | 2026-04-18 |
| Jessica (id=4) | 2 | 4 | $0.43 | 2026-04-16 |
| Nicoly (id=71) | 1 | 38 | $13.54 | 2026-04-16 |
| Guilherme Silva (id=72) | 1 | 2 | $0.26 | 2026-04-14 |
| Talita (id=17) | 1 | 4 | $0.20 | 2026-04-06 |
| Fernando (id=36) | 1 | 2 | $0.00 | 2026-03-25 |

**Destaques**:
- Marcus Lima (id=18): maior custo ($263.58) em apenas 6 sessoes (media $44/sessao) — conciliacao financeira intensiva
- Gabriella (id=69): $173.39 em 22 sessoes, 308 mensagens — mantida como heavy user
- Rafael (id=1): +8 sessoes vs ciclo anterior, consumo em alta
- Novo usuario: Guilherme Silva (id=72)

---

## Memorias Empresa (Q6) — user_id=0

Total: 126 memorias empresa (+27 vs ciclo anterior).

**Memorias empresa com efficacy = 0 persistentes (nunca efetivas apesar de uso)**:

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

**Nota critica**: NENHUMA das 126 memorias empresa possui `reviewed_at` preenchido. Processo formal de revisao segue NAO implementado (identificado em 13/04 e 06/04).

**Memorias empresa com efficacy alta (destaques positivos)**:
- `heuristicas/financeiro/_archived_extrato-banco-subutilizado-pode-ter-lacunas-reais` — 0.710 efficacy, 286 usos
- `protocolos/financeiro/conciliacao-transferencias-set2025-pendencias` — 0.804 efficacy, 168 usos
- `armadilhas/financeiro/desconciliar-incorretos-antes-de-conciliar-corretos` — 0.772 efficacy, 202 usos
- `heuristicas/recebimento/divergencia-pequena-nf-x-po-indica-preco-unitario-com-mais` — 0.699 efficacy, 346 usos
- `regras/financeiro/gabriella-sempre-referencia-pos-com-o-prefixo-c` — 0.855 efficacy, 131 usos

---

## Knowledge Graph (Q4 + Q7)

### Entidades por Tipo

| Tipo | Total | Memorias Linkadas | Avg Mentions |
|------|-------|-------------------|--------------|
| conceito | 798 | 118 | 1.55 |
| processo | 108 | 61 | 1.37 |
| campo | 88 | 51 | 1.24 |
| produto | 74 | 35 | 2.07 |
| regra | 68 | 9 | 1.12 |
| termo | 55 | 32 | 2.05 |
| valor | 43 | 10 | 1.14 |
| uf | 31 | 8 | 4.06 |
| cliente | 26 | 20 | 8.92 |
| transportadora | 23 | 13 | 1.96 |
| usuario | 13 | 13 | 7.00 |
| cnpj | 10 | 8 | 1.40 |
| pedido | 7 | 5 | 5.43 |
| fornecedor | 6 | 6 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Total entidades**: 1.351 (+388 vs 963 do ciclo anterior, +40%)
**KG Coverage estimada**: ~118/272 memorias com entidades `conceito` linkadas = 43,4%

**Observacao**: KG coverage caiu (52,8% -> 43,4%) apesar de +388 entidades — crescimento de memorias superou o de entidades linkadas. Gap de 154 memorias sem entidades.

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

Top 10 relacoes identicas ao ciclo anterior — grafo semantico estavel apesar do crescimento.

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor Medido | Score (0-100%) | Pontos |
|----------|------|--------------|----------------|--------|
| Eficacia media | 30% | 0.597 (range 0.2-0.7) | 79,4% | 23,8 |
| Taxa cold | 20% | 11,76% (32/272) | 95,6% | 19,1 |
| Stale 60d | 20% | 0,74% (2/272) | 100% | 20,0 |
| KG coverage | 15% | 43,4% (118/272) | 39,0% | 5,9 |
| Correcoes | 15% | 0,00 | 100% | 15,0 |
| **TOTAL** | **100%** | | | **84** |

**Comparativo com avaliacoes anteriores**:

| Metrica | 2026-04-06 | 2026-04-13 | 2026-04-20 | Delta 7d |
|---------|------------|------------|------------|----------|
| Health Score | 81 | 84 | 84 | 0 |
| Total memorias | 128 | 197 | 272 | +75 |
| Cold | 14 | 15 | 32 | +17 |
| Stale 60d | 2 | 2 | 2 | 0 |
| KG coverage | - | 52,8% | 43,4% | -9,4pp |
| Sessoes total | - | 391 | 434 | +43 |
| Usuarios unicos | - | 21 | 22 | +1 |

---

## Recomendacoes Acionaveis

### R1 [URGENTE] — Remover/reescrever 8 memorias com efficacy=0 e usage >= 3

Duas novas memorias entraram na lista zero-efficacy desde o ciclo anterior:
- `corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente` (u18, 9 usos)
- `empresa/heuristicas/financeiro/consolidated` (operational, u0, 3 usos)

Memorias legadas ainda presentes (persistem ha >= 14 dias):
- `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel` (32 usos, 0 efetivos)
- `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido` (19 usos, 0 efetivos)
- `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di` (10 usos, 0 efetivos)
- `empresa/termos/modo-debug` (6 usos, 0 efetivos)
- `empresa/usuarios/kerley` (5 usos, 0 efetivos)
- `empresa/regras/operadores-do-teams-bot-possuem-user-id` (5 usos, 0 efetivos)

**Acao**: Auditoria humana URGENTE. Se obsoleto, remover. Se relevante mas mal escrito, reescrever para melhor ativacao. Essas 8 memorias foram carregadas 89x sem gerar valor.

### R2 [CRITICO] — Intervir em user-xml-nao-atualiza-por-threshold-de-sessoes

Memoria saltou 201 -> 386 usos em 7 dias (+92%) mantendo efficacy baixissima (0.124, apenas 48 efetivos). Consumo elevado de contexto sem retorno.

**Acao**: Investigar urgente por que essa memoria e carregada tanto mas nao ajuda. Considerar reescrita ou rebaixamento de prioridade.

### R3 [ALTO] — Investigar crescimento acelerado de cold tier

Cold memorias mais que dobraram (15 -> 32, +113%) enquanto total cresceu 38%. Proporcao cold subiu de 7.6% para 11,8%. Se mantido esse ritmo, em 2-3 ciclos ultrapassara 20%.

**Acao**: Auditar criterios de promocao a cold. Verificar se memorias sao criadas ja com baixa relevancia (candidatas imediatas) ou se e deterioracao de memorias antigas.

### R4 [ALTO] — Reverter queda de KG coverage (43,4% -> meta 70%)

Queda de 9,4 pontos percentuais em 7 dias. 154 memorias sem entidades linkadas. Entidades cresceram +40% mas nao acompanharam o ritmo de criacao de memorias.

**Acao**: Rodar extrator de entidades em batch sobre as memorias criadas nos ultimos 14 dias. Priorizar `structural/empresa` (maior volume).

### R5 [MEDIO] — Implementar revisao formal de memorias empresa (repetida ha 2 ciclos)

NENHUMA das 126 memorias empresa tem `reviewed_at` preenchido. Ja recomendado em 13/04. Nao foi implementado.

**Acao**: Criar processo de curadoria que preencha `reviewed_at` apos verificacao humana. Comecar pelas 11 memorias empresa com efficacy=0 (ver R1).

### R6 [MEDIO] — Consolidar termos de glossario redundantes

Termos como `integracao-nf` (0.046, 108 usos), `confirmar-pedido` (0.049, 81 usos), `cotacao` (0.074, 27 usos) sao carregados frequentemente mas raramente efetivos. Mesmo perfil persistente ha 2 ciclos.

**Acao**: Consolidar termos redundantes ou enriquecer com contexto operacional. Considerar que entidades do KG ja capturam esses conceitos (vide top relacoes).

### R7 [MEDIO] — Avaliar memorias permanent/empresa com efficacy baixa

`corrections/capacidade-caminhoes-consultar-veiculos` — efficacy 0.194, 206 usos (subiu de 175)
`corrections/agent-sdk-production-scope` — efficacy 0.212, 33 usos
`corrections/confirmar-para-pedido-odoo` — efficacy 0.523, 327 usos

**Acao**: Memorias permanentes devem ser de alta qualidade — revisar estas 3 e reescrever ou mover para tier inferior.

### R8 [BAIXO] — Monitorar crescimento sustentado de structural/pessoal

Categoria dobrou (33 -> 68) em 7 dias. Avg importance 0.68 (saudavel), avg efficacy 0.60. Nao e problema agora, mas merece monitoramento para evitar ruido futuro.

**Acao**: Revisar threshold de criacao automatica de memorias pessoais. Se taxa mantida, revisitar em 2 ciclos.

---

## Resumo Executivo

O sistema de memorias mantem health score 84/100 (estavel vs ciclo anterior), mas por razoes diferentes: eficacia media melhorou (0.54 -> 0.60, +11%) compensando a queda de KG coverage (52.8% -> 43.4%, -18%). O sistema cresceu +38% em 7 dias (197 -> 272 memorias), com cold tier dobrando (+113%) e 8 memorias com efficacy zero consumindo contexto repetidamente. O gap estrutural persistente e a ausencia total de `reviewed_at` em memorias empresa (126 registros). Acoes URGENTES: R1 (remover zero-efficacy), R2 (investigar user-xml que consome 386 loads sem retorno) e R4 (rodar extrator de entidades em batch para recuperar KG coverage).
