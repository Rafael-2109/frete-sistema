# Atualizacao Memory Eval — 2026-04-13-1

**Data**: 2026-04-13
**Health Score**: 84/100 (anterior: 81/100, delta: +3)

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total sessoes | 391 |
| Sessoes ultima semana | 30 |
| Sessoes ultimo mes | 169 |
| Usuarios unicos | 21 |
| Media mensagens/sessao | 8.5 |
| Media custo/sessao (USD) | $1.90 |

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Importance | Avg Usage | Avg Effective | Avg Efficacy | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|----------------|-----------|---------------|--------------|------|----------|-----------|-----------|
| contextual | pessoal | 6 | 0.40 | 17.3 | 14.7 | 0.85 | 3 | 0 | 1 | 0 |
| operational | empresa | 14 | 0.86 | 112.4 | 63.2 | 0.56 | 0 | 0 | 4 | 0 |
| operational | pessoal | 20 | 0.59 | 29.6 | 21.8 | 0.74 | 1 | 0 | 3 | 0 |
| permanent | empresa | 4 | 0.90 | 174.0 | 71.0 | 0.41 | 0 | 0 | 4 | 0 |
| permanent | pessoal | 21 | 0.90 | 38.5 | 23.7 | 0.62 | 0 | 0 | 3 | 0 |
| structural | empresa | 99 | 0.73 | 61.3 | 33.4 | 0.54 | 10 | 0 | 29 | 0 |
| structural | pessoal | 33 | 0.70 | 10.0 | 5.5 | 0.55 | 1 | 0 | 2 | 2 |
| **TOTAL** | | **197** | | | | | **15** | **0** | **46** | **2** |

**Observacoes**:
- `structural/empresa` concentra 50% das memorias (99/197) e 67% das cold (10/15)
- `permanent/empresa` tem a maior media de uso (174.0) mas eficacia relativamente baixa (0.41)
- Zero conflitos detectados em todas as categorias
- 46 memorias stale 30d (23.4%) — atencao para tendencia

---

## Top 20 Memorias Baixa Eficacia (Q3)

Memorias com usage >= 3 e efficacy < 0.3 (candidatas a revisao/remocao):

| # | Path | Efficacy | Usage | Effective | Category |
|---|------|----------|-------|-----------|----------|
| 1 | empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 0.000 | 32 | 0 | structural |
| 2 | empresa/regras/quando-o-usuario-envia-saudacao-e-pedido | 0.000 | 19 | 0 | structural |
| 3 | empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 0.000 | 10 | 0 | structural |
| 4 | empresa/termos/modo-debug | 0.000 | 6 | 0 | structural |
| 5 | empresa/usuarios/kerley | 0.000 | 5 | 0 | structural |
| 6 | empresa/regras/operadores-do-teams-bot-possuem-user-id | 0.000 | 5 | 0 | operational |
| 7 | empresa/termos/integracao-nf | 0.046 | 108 | 5 | structural |
| 8 | empresa/termos/confirmar-pedido | 0.049 | 81 | 4 | structural |
| 9 | empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i | 0.061 | 49 | 3 | structural |
| 10 | system/download_config | 0.064 | 47 | 3 | structural |
| 11 | empresa/termos/cotacao | 0.074 | 27 | 2 | structural |
| 12 | empresa/armadilhas/integracao/save-memory-ignora-target-user-id-sem-debug-mode | 0.106 | 47 | 5 | structural |
| 13 | corrections/o-usuario-interrompeu-uma-analise-que-havia-saido-do-escopo | 0.111 | 9 | 1 | structural |
| 14 | empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo | 0.114 | 79 | 9 | operational |
| 15 | empresa/regras/pedidos-para-a-rede-assai-no-odoo-precis | 0.128 | 78 | 10 | structural |
| 16 | empresa/heuristicas/integracao/user-xml-nao-atualiza-por-threshold-de-sessoes | 0.139 | 201 | 28 | structural |
| 17 | empresa/correcoes/gilberto-nao-existe-na-equipe-da-nacom-g | 0.149 | 47 | 7 | structural |
| 18 | corrections/quando-o-usuario-disse-nao-fazer-o-padrao-juros-outros | 0.154 | 13 | 2 | structural |
| 19 | empresa/termos/tabela-frete-minimo-valor | 0.200 | 5 | 1 | structural |
| 20 | empresa/termos/pedido-de-venda | 0.205 | 44 | 9 | structural |

**Destaque**: 6 memorias com efficacy = 0 e usage significativo (>= 5). Candidatas prioritarias para remocao ou reescrita.

---

## Sessoes por Usuario — Ultimos 30d (Q5)

| Usuario | Sessions | Mensagens | Custo (USD) | Ultima Sessao |
|---------|----------|-----------|-------------|---------------|
| Rafael (id=1) | 43 | 270 | $86.90 | 2026-04-10 |
| Claude Code (id=74) | 31 | 62 | $2.47 | 2026-04-10 |
| Gabriella (id=69) | 30 | 406 | $130.73 | 2026-04-13 |
| Elaine (id=67) | 20 | 172 | $27.28 | 2026-04-10 |
| Rafael (id=55) | 18 | 258 | $54.76 | 2026-04-10 |
| Denise (id=2) | 8 | 51 | $10.99 | 2026-04-10 |
| Jessica (id=4) | 5 | 14 | $2.41 | 2026-03-24 |
| Thamires (id=27) | 4 | 24 | $7.38 | 2026-04-07 |
| Marcus V (id=56) | 4 | 54 | $4.13 | 2026-03-19 |
| Marcus Lima (id=18) | 2 | 273 | $128.62 | 2026-04-10 |
| Nicoly (id=71) | 2 | 22 | $5.65 | 2026-03-19 |
| Talita (id=17) | 1 | 4 | $0.20 | 2026-04-06 |
| Fernando (id=36) | 1 | 2 | $0.00 | 2026-03-25 |

**Destaques**:
- Gabriella e maior consumidora em custo ($130.73) e mensagens (406)
- Marcus Lima (id=18) tem custo alto ($128.62) em apenas 2 sessoes — sessoes longas de conciliacao financeira
- Claude Code (id=74) = sessoes automaticas do sistema (bot)

---

## Memorias Empresa (Q6) — user_id=0

Total: 99 memorias empresa (detalhadas na query).

**Memorias empresa com efficacy = 0 (nunca efetivas apesar de uso)**:

| Path | Usage | Reviewed |
|------|-------|----------|
| protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 32 | NULL |
| regras/quando-o-usuario-envia-saudacao-e-pedido | 19 | NULL |
| perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 10 | NULL |
| termos/modo-debug | 6 | NULL |
| usuarios/kerley | 5 | NULL |
| regras/operadores-do-teams-bot-possuem-user-id | 5 | NULL |
| termos/embarque-criado-pelo-sistema | 0 | NULL |
| regras/o-campo-purchase-order-id-no-odoo-pode-n | 0 | NULL |
| regras/ao-alterar-o-campo-tabela-frete-minimo-v | 1 | NULL |
| termos/relatoriofaturamentoimportado | 1 | NULL |

**Nota**: NENHUMA memoria empresa possui `reviewed_at` preenchido. Revisao formal nunca foi executada.

---

## Knowledge Graph (Q4 + Q7)

### Entidades por Tipo

| Tipo | Total | Memorias Linkadas | Avg Mentions |
|------|-------|-------------------|--------------|
| conceito | 559 | 92 | 1.70 |
| regra | 68 | 9 | 1.12 |
| processo | 65 | 35 | 1.22 |
| produto | 64 | 32 | 2.23 |
| campo | 52 | 29 | 1.17 |
| termo | 38 | 24 | 2.47 |
| valor | 36 | 6 | 1.17 |
| cliente | 24 | 18 | 9.58 |
| uf | 14 | 5 | 3.36 |
| usuario | 12 | 12 | 7.50 |
| cnpj | 10 | 8 | 1.40 |
| transportadora | 9 | 5 | 1.67 |
| pedido | 7 | 5 | 5.43 |
| fornecedor | 4 | 4 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Total entidades**: 963 | **KG Coverage**: 104/197 memorias (52.8%)

### Top Relacoes Semanticas (Q7)

| Source | Relation | Target | Weight |
|--------|----------|--------|--------|
| DRY-RUN-OBRIGATORIO | precede | ACOES-EM-LOTE-ODOO | 5.0 |
| ASSAI | requer | CONFIRMACAO-MANUAL | 5.0 |
| PEDIDO-DE-VENDA | co_occurs | COTACAO | 3.5 |
| CONFIRMAR-PEDIDO | co_occurs | COTACAO | 3.5 |
| DENISE | pertence_a | COMPRAS | 3.0 |
| GABRIELLA | responsavel_por | COMPRAS | 3.0 |
| VCD | complementa | PEDIDO | 3.0 |

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor Medido | Score (0-100%) | Pontos |
|----------|------|-------------|----------------|--------|
| Eficacia media | 30% | 0.539 (range 0.2-0.7) | 67.8% | 20.3 |
| Taxa cold | 20% | 7.6% (15/197) | 100% | 20.0 |
| Stale 60d | 20% | 1.0% (2/197) | 100% | 20.0 |
| KG coverage | 15% | 52.8% (104/197) | 54.7% | 8.2 |
| Correcoes | 15% | 0.00 | 100% | 15.0 |
| **TOTAL** | **100%** | | | **84** |

**Comparativo com avaliacao anterior (2026-04-06)**:
- Health Score: 81 -> 84 (+3 pontos)
- Total memorias: 128 -> 197 (+69, crescimento 54%)
- Cold: 14 -> 15 (+1)
- Stale 60d: 2 -> 2 (estavel)

---

## Recomendacoes Acionaveis

### R1 — Remover/reescrever 6 memorias com efficacy=0 e usage >= 5

Memorias carregadas dezenas de vezes sem nunca serem efetivas. Candidatas prioritarias:
- `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel` (32 usos, 0 efetivos)
- `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido` (19 usos, 0 efetivos)
- `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di` (10 usos, 0 efetivos)
- `empresa/termos/modo-debug` (6 usos, 0 efetivos)
- `empresa/usuarios/kerley` (5 usos, 0 efetivos)
- `empresa/regras/operadores-do-teams-bot-possuem-user-id` (5 usos, 0 efetivos)

**Acao**: Avaliar conteudo. Se obsoleto, remover. Se relevante mas mal escrito, reescrever para melhor ativacao.

### R2 — Revisar termos de glossario com efficacy < 0.1

Termos como `integracao-nf` (0.046), `confirmar-pedido` (0.049), `cotacao` (0.074) sao carregados frequentemente mas quase nunca marcados como efetivos. Possivel causa: conteudo generico demais ou redundante com memorias mais especificas.

**Acao**: Consolidar termos redundantes ou enriquecer com contexto operacional.

### R3 — Implementar revisao formal de memorias empresa

NENHUMA das 99 memorias empresa tem `reviewed_at` preenchido. Criar rotina de revisao periodica (mensal) para validar relevancia.

**Acao**: Criar processo de curadoria que preencha `reviewed_at` apos verificacao humana.

### R4 — Aumentar KG coverage (52.8% -> meta 70%)

93 memorias nao possuem entidades linkadas no Knowledge Graph. Isso reduz a capacidade de recuperacao semantica.

**Acao**: Rodar extrator de entidades nas memorias sem links, priorizando `structural/empresa` (maior volume).

### R5 — Mover memorias stale candidates para cold tier

46 memorias com updated_at > 30d, mas apenas 15 sao cold. Avaliar se as 31 restantes devem ser promovidas a cold.

**Acao**: Filtrar as 31 memorias stale-30d que nao sao cold e avaliar usage recente antes de mover.

### R6 — Monitorar crescimento acelerado

Sistema cresceu 54% em 7 dias (128 -> 197 memorias). Se mantido, pode gerar ruido. Verificar se novas memorias estao sendo criadas com criterio ou automaticamente sem filtro.

**Acao**: Avaliar threshold de criacao automatica de memorias e ajustar se necessario.

### R7 — Investigar memorias permanent/empresa com efficacy baixa

As 4 memorias permanent/empresa tem avg efficacy de apenas 0.41 apesar de avg usage 174. Memorias permanentes devem ser de alta qualidade.

**Acao**: Revisar `corrections/confirmar-para-pedido-odoo` (0.46 efficacy, 271 usos) e `corrections/capacidade-caminhoes-consultar-veiculos` (0.15 efficacy, 175 usos).

---

## Resumo Executivo

O sistema de memorias esta saudavel (84/100), com melhoria de 3 pontos desde a ultima avaliacao. Os pontos fortes sao taxa cold controlada (7.6%) e ausencia de memorias stale 60d significativas (1%). O principal ponto fraco e o KG coverage (52.8%) e a existencia de memorias com efficacy zero que consomem contexto sem retorno. O crescimento acelerado (+54% em 7 dias) merece monitoramento para evitar degradacao futura.
