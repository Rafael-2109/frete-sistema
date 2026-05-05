# Atualizacao Memory Eval — 2026-05-05-1

**Data**: 2026-05-05
**Health Score**: 86/100 (anterior: 85/100, delta: +1)
**Status**: OK — todas as 7 queries executaram com sucesso

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total sessoes | 502 |
| Sessoes ultima semana | 30 |
| Sessoes ultimo mes | 143 |
| Usuarios unicos | 23 |
| Media mensagens/sessao | 8.75 |
| Media custo/sessao (USD) | $2.39 |

**Delta vs 2026-04-27**: +41 sessoes (+8.9%), +1 ultima semana (29 -> 30) — uso semanal estabilizou. Usuarios unicos +1 (22 -> 23). Custo medio por sessao subiu levemente ($2.36 -> $2.39).

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Importance | Avg Usage | Avg Effective | Avg Efficacy | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|----------------|-----------|---------------|--------------|------|----------|-----------|-----------|
| contextual | pessoal | 8 | 0.43 | 35.25 | 29.50 | 0.837 | 3 | 0 | 0 | 0 |
| operational | empresa | 16 | 0.83 | 166.69 | 99.56 | 0.597 | 1 | 0 | 7 | 0 |
| operational | pessoal | 29 | 0.55 | 34.03 | 27.38 | 0.804 | 2 | 0 | 6 | 0 |
| permanent | empresa | 4 | 0.90 | 225.00 | 105.50 | 0.469 | 0 | 0 | 4 | 3 |
| permanent | pessoal | 25 | 0.89 | 68.64 | 49.96 | 0.728 | 0 | 0 | 5 | 1 |
| structural | empresa | 136 | 0.75 | 91.43 | 53.20 | 0.582 | 22 | 0 | 53 | 0 |
| structural | pessoal | 99 | 0.67 | 9.92 | 6.44 | 0.650 | 9 | 0 | 3 | 2 |
| **TOTAL** | | **317** | | | | **0.641** | **37** | **0** | **78** | **6** |

**Observacoes**:
- Total: 297 -> 317 (+20, +6.7% em 8 dias) — crescimento continua desacelerando (era +9%)
- `structural/empresa`: 131 -> 136 (+5, +3.8%) — estavel
- `structural/pessoal`: 88 -> 99 (+11, +12.5%) — segue como segmento de maior crescimento, mas em ritmo menor
- `operational/pessoal`: 26 -> 29 (+3) — leve crescimento
- `permanent/pessoal`: 24 -> 25 (+1)
- Cold: 32 -> 37 (+5) — voltou a crescer apos estabilidade do ciclo anterior
- Stale 30d: 70 -> 78 (+8) — crescimento moderado
- Stale 60d: 5 -> 6 (+1) — 3 em `permanent/empresa` (mantidos), 1 nova em `permanent/pessoal`, 2 em `structural/pessoal`
- Eficacia media subiu de 0.613 -> 0.641 (+4.6%)
- Zero conflitos detectados

---

## Top 20 Memorias Baixa Eficacia (Q3)

| # | Path | Efficacy | Usage | Effective | Category | User |
|---|------|----------|-------|-----------|----------|------|
| 1 | empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 0.000 | 32 | 0 | structural | u0 |
| 2 | empresa/regras/quando-o-usuario-envia-saudacao-e-pedido | 0.000 | 19 | 0 | structural | u0 |
| 3 | empresa/armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus | 0.000 | 14 | 0 | structural | u0 |
| 4 | empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 0.000 | 10 | 0 | structural | u0 |
| 5 | corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente | 0.000 | 9 | 0 | structural | u18 |
| 6 | empresa/termos/modo-debug | 0.000 | 6 | 0 | structural | u0 |
| 7 | learned/expertise_demonstra-conhecimento-de-seguranca-web-csrf-tokens | 0.000 | 6 | 0 | structural | u1 |
| 8 | empresa/regras/operadores-do-teams-bot-possuem-user-id | 0.000 | 5 | 0 | operational | u0 |
| 9 | empresa/usuarios/kerley | 0.000 | 5 | 0 | structural | u0 |
| 10 | learned/expertise_conhece-infraestrutura-render-restart-vs-redeploy-git-dep | 0.000 | 3 | 0 | structural | u1 |
| 11 | learned/expertise_conhece-riscos-de-deploy-em-prod-mencionou-cache-de-templat | 0.000 | 3 | 0 | structural | u1 |
| 12 | empresa/termos/integracao-nf | 0.046 | 108 | 5 | structural | u0 |
| 13 | empresa/termos/confirmar-pedido | 0.049 | 81 | 4 | structural | u0 |
| 14 | empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo | 0.052 | 172 | 9 | operational | u0 |
| 15 | empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i | 0.061 | 49 | 3 | structural | u0 |
| 16 | system/download_config | 0.064 | 47 | 3 | structural | u1 |
| 17 | empresa/armadilhas/integracao/_archived_sessao-teams-reinicia-antes-de-subagente-concluir | 0.067 | 15 | 1 | structural | u0 |
| 18 | empresa/termos/cotacao | 0.074 | 27 | 2 | structural | u0 |
| 19 | corrections/o-usuario-interrompeu-uma-analise-que-havia-saido-do-escopo | 0.091 | 11 | 1 | structural | u18 |
| 20 | empresa/armadilhas/integracao/save-memory-ignora-target-user-id-sem-debug-mode | 0.106 | 47 | 5 | structural | u0 |

**Destaque critico**: 11 memorias com efficacy = 0 e usage >= 3 (vs 9 no ciclo anterior, +2). Novas: `reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus` (u0, 14 usos, criada 2026-05-01), `learned/expertise_conhece-infraestrutura-render` (u1, 3 usos), `learned/expertise_conhece-riscos-de-deploy-em-prod` (u1, 3 usos). Padrao `learned/expertise_*` continua gerando ruido.

---

## Sessoes por Usuario — Ultimos 30d (Q5)

| Usuario | Sessions | Mensagens | Custo (USD) | Ultima Sessao |
|---------|----------|-----------|-------------|---------------|
| Rafael (id=1) | 46 | 255 | $67.01 | 2026-05-01 |
| Marcus Lima (id=18) | 25 | 675 | $307.29 | 2026-05-04 |
| Gabriella (id=69) | 20 | 258 | $197.93 | 2026-05-04 |
| Elaine (id=67) | 17 | 140 | $36.16 | 2026-04-30 |
| Denise (id=2) | 9 | 78 | $21.81 | 2026-04-30 |
| Thamires (id=27) | 7 | 20 | $2.03 | 2026-05-05 |
| Rafael (id=55) | 6 | 42 | $17.86 | 2026-04-30 |
| Claude Code (id=74) | 4 | 8 | $0.37 | 2026-04-10 |
| Thamyrez (id=63) | 3 | 14 | $1.99 | 2026-04-30 |
| Nicoly (id=71) | 2 | 46 | $15.43 | 2026-04-30 |
| Marcus V. (id=56) | 1 | 8 | $2.31 | 2026-05-03 |
| Talita (id=17) | 1 | 4 | $0.20 | 2026-04-06 |
| Guilherme (id=72) | 1 | 2 | $0.26 | 2026-04-14 |
| Jessica (id=4) | 1 | 2 | $0.18 | 2026-04-16 |

**Destaques**:
- Marcus Lima: +13 sessoes (12 -> 25), maior custo $307.29 (+$27) — pico de uso, 675 mensagens (+128)
- Rafael (id=1): -11 sessoes (57 -> 46), custo +$7 — menos sessoes mas mais caras
- Gabriella: +1 sessao (19 -> 20), custo praticamente igual ($197 vs $200)
- Elaine: estavel (17 sessoes)
- Denise: +2 sessoes (7 -> 9), custo subiu para $21.81
- Claude Code (id=74): -17 sessoes (21 -> 4) — quase saiu do recorte
- Novos: Thamyrez (3 sessoes), Marcus V. (1)

---

## Memorias Empresa (Q6) — user_id=0

Total: 136 memorias empresa (+5 vs ciclo anterior).

**Memorias empresa com efficacy = 0 persistentes**:

| Path | Usage | Reviewed |
|------|-------|----------|
| protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 32 | NULL |
| regras/quando-o-usuario-envia-saudacao-e-pedido | 19 | NULL |
| armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus (NOVA) | 14 | NULL |
| perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 10 | NULL |
| termos/modo-debug | 6 | NULL |
| usuarios/kerley | 5 | NULL |
| regras/operadores-do-teams-bot-possuem-user-id | 5 | NULL |
| termos/embarque-criado-pelo-sistema | 0 | NULL |
| regras/o-campo-purchase-order-id-no-odoo-pode-n | 0 | NULL |
| regras/ao-alterar-o-campo-tabela-frete-minimo-v | 3 | NULL |
| termos/relatoriofaturamentoimportado | 1 | NULL |

**Nota critica (5o ciclo consecutivo)**: NENHUMA das 136 memorias empresa possui `reviewed_at` preenchido. Identificado em 06/04, 13/04, 20/04, 27/04, 05/05.

**Memorias empresa com efficacy alta (destaques 2026-05-05)**:
- `armadilhas/recebimento/consolidacao-bloqueada-por-ajuste-manual-po-pos-match` — 1.000 efficacy, 104 usos (+19)
- `armadilhas/system-pitfalls.json` — 1.000 efficacy, 30 usos
- `regras/financeiro/gabriella-sempre-referencia-pos-com-o-prefixo-c` — 0.950 efficacy, 161 usos
- `protocolos/carvia/bloqueio-de-credito-ssw-impede-emissao-de-cte` — 0.895 efficacy, 19 usos
- `armadilhas/financeiro/nosso-numero-dac-zero-grava-caracter-invalido` — 0.885 efficacy, 26 usos
- `armadilhas/financeiro/nosso-numero-cnab-exige-unicidade-e-dac-por-algoritmo-do` — 0.833 efficacy, 54 usos
- `armadilhas/system-pitfalls.xml` — 0.825 efficacy, 40 usos
- `protocolos/comercial/confirmacao-em-lote-de-cotacoes-exige-selecao-previa-por` — 0.800 efficacy, 90 usos

**Novas memorias empresa criadas no ciclo (1-4 maio)**:
- `heuristicas/financeiro/baseline-de-extratos-formato-fixo` (u18, 102 usos, efficacy 0.569)
- `heuristicas/recebimento/de-para-fornecedor-usa-codigos-numericos-simples` (u69, 552 usos, efficacy 0.652) — estrela do ciclo
- `armadilhas/financeiro/nosso-numero-dac-zero-grava-caracter-invalido` (u18, 26 usos, efficacy 0.885)
- `armadilhas/financeiro/nosso-numero-cnab-exige-unicidade-e-dac-por-algoritmo-do` (u18, 54 usos, efficacy 0.833)
- `protocolos/remessa_cnab400_vortx_310.md` (u18, 62 usos, efficacy 0.710)
- `protocolos/financeiro/migracao-cnab-entre-bancos-exige-mais-que-troca-de-codigo` (u18, 60 usos, efficacy 0.783)
- `protocolos/integracao/caminho-nfe-para-pedido-completo-via-tagplus` (u1, 16 usos, efficacy 0.625)
- `armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus` (u1, 14 usos, efficacy 0.000) — ZERO efficacy

---

## Knowledge Graph (Q4 + Q7)

### Entidades por Tipo

| Tipo | Total | Memorias Linkadas | Avg Mentions |
|------|-------|-------------------|--------------|
| conceito | 888 | 127 | 1.50 |
| processo | 129 | 70 | 1.33 |
| campo | 94 | 58 | 1.24 |
| produto | 74 | 35 | 2.07 |
| regra | 68 | 9 | 1.12 |
| termo | 62 | 38 | 1.97 |
| valor | 44 | 11 | 1.14 |
| uf | 31 | 8 | 4.06 |
| cliente | 27 | 21 | 8.63 |
| transportadora | 25 | 15 | 1.88 |
| usuario | 13 | 13 | 7.00 |
| cnpj | 10 | 8 | 1.40 |
| pedido | 7 | 5 | 5.43 |
| fornecedor | 6 | 6 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Total entidades**: 1.479 (+59 vs 1.420 ciclo anterior, +4.2%)
**KG Coverage estimada**: ~127/317 = **40.1%** (vs 41.4% anterior)

**Observacao**: KG coverage caiu novamente (-1.3pp) pois entidades cresceram +4.2% enquanto memorias cresceram +6.7%. 5o ciclo consecutivo de queda. Limite assintotico aparente em ~40%.

### Top Relacoes Semanticas (Q7) — Top 20

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
| COTACAO | co_occurs | PEDIDO-DE-VENDA | 2.5 |
| ASSAI | co_occurs | CONFIRMACAO-MANUAL | 2.5 |
| DRY-RUN-OBRIGATORIO | co_occurs | ACOES-EM-LOTE-ODOO | 2.5 |
| VCD2667872 | co_occurs | PEDIDO | 2.5 |
| INTEGRACAO-NF | pertence_a | FASE2-RECEBIMENTO | 2.0 |
| ASSAI | co_occurs | MULTIPLAS-LOJAS-INDEPENDENTES | 2.0 |
| INTEGRACAO-NF | co_occurs | PEDIDO-DE-COMPRA | 2.0 |
| INTEGRACAO-NF | complementa | PEDIDO-DE-COMPRA | 2.0 |
| ASSAI | requer | CONFIRMACAO MANUAL | 2.0 |

Top 11 relacoes identicas aos ultimos 3 ciclos — grafo semantico permanece estavel.

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor Medido | Score (0-100%) | Pontos |
|----------|------|--------------|----------------|--------|
| Eficacia media | 30% | 0.641 (range 0.2-0.7) | 88.2% | 26.5 |
| Taxa cold | 20% | 11.67% (37/317) | 95.8% | 19.2 |
| Stale 60d | 20% | 1.89% (6/317) | 100% | 20.0 |
| KG coverage | 15% | 40.1% (127/317) | 33.5% | 5.0 |
| Correcoes | 15% | 0.00 | 100% | 15.0 |
| **TOTAL** | **100%** | | | **86** |

**Comparativo serie historica**:

| Metrica | 2026-04-06 | 2026-04-13 | 2026-04-20 | 2026-04-27 | 2026-05-05 | Delta 8d |
|---------|------------|------------|------------|------------|------------|----------|
| Health Score | 81 | 84 | 84 | 85 | 86 | +1 |
| Total memorias | 128 | 197 | 272 | 297 | 317 | +20 |
| Cold | 14 | 15 | 32 | 32 | 37 | +5 |
| Stale 60d | 2 | 2 | 2 | 5 | 6 | +1 |
| KG coverage | - | 52.8% | 43.4% | 41.4% | 40.1% | -1.3pp |
| Eficacia media | - | 0.54 | 0.597 | 0.613 | 0.641 | +0.028 |
| Sessoes total | - | 391 | 434 | 461 | 502 | +41 |
| Sessoes ultima semana | - | 30 | 45 | 29 | 30 | +1 |
| Usuarios unicos | - | 21 | 22 | 22 | 23 | +1 |

---

## Recomendacoes Acionaveis

### R1 [URGENTE] — Auditar 11 memorias com efficacy=0 e usage >= 3

3 NOVAS memorias entraram na lista zero-efficacy:
- `armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus` (u0, 14 usos) — criada 2026-05-01, ja com efficacy zero
- `learned/expertise_conhece-infraestrutura-render` (u1, 3 usos)
- `learned/expertise_conhece-riscos-de-deploy-em-prod` (u1, 3 usos)

Memorias legadas que persistem ha >= 28 dias (5o ciclo consecutivo):
- `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel` (32 usos)
- `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido` (19 usos)
- `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di` (10 usos)
- `empresa/termos/modo-debug` (6 usos)
- `empresa/usuarios/kerley` (5 usos)
- `empresa/regras/operadores-do-teams-bot-possuem-user-id` (5 usos)

**Acao**: Auditoria humana URGENTE. 91 carregamentos sem valor (subiu de 77). 5o ciclo sem acao. Padrao `learned/expertise_*` u1 deve ser desabilitado/refinado.

### R2 [CRITICO] — user-xml-nao-atualiza-por-threshold-de-sessoes

Memoria com 386 usos (estavel) e efficacy 0.124. 5o ciclo consecutivo no top zero. 386 carregamentos com 48 efetivos = 338 carregamentos inutiles.

**Acao**: Investigar padrao de injection. Reescrever ou rebaixar prioridade. Decisao em aberto desde 06/04.

### R3 [ALTO] — Reverter queda lenta de KG coverage (40.1% -> meta 70%)

5o ciclo consecutivo de queda (52.8% -> 43.4% -> 41.4% -> 41.4% -> 40.1%). Aparenta estabilizacao em ~40%.

**Acao**: Rodar extrator de entidades em batch sobre as 20 memorias criadas nos ultimos 8 dias. Priorizar `structural/empresa` (5 novas) e `structural/pessoal` (11 novas). Avaliar se 40% e teto natural ou se extrator esta saturado.

### R4 [ALTO] — Implementar revisao formal de memorias empresa (5o ciclo)

NENHUMA das 136 memorias empresa tem `reviewed_at` preenchido. Recomendado em 06/04, 13/04, 20/04, 27/04, 05/05. Nao implementado ha 5 ciclos.

**Acao**: Criar processo de curadoria que preencha `reviewed_at` apos verificacao. Comecar pelas 11 memorias empresa com efficacy=0 ou criadas neste ciclo (8 novas). Considerar bloqueio automatico via constraint ou alerta.

### R5 [ALTO] — Padrao `learned/expertise_*` gera ruido sistematico

3 das 11 zero-efficacy sao `learned/expertise_*` (u1). Ciclo anterior tinha 1, agora 3. Padrao em crescimento.

**Acao**: Revisar logica de extracao de "expertise" — provavelmente identifica conhecimento sem mapear para uso operacional. Considerar desabilitar ou recalibrar threshold.

### R6 [MEDIO] — Investigar 6 memorias stale 60d

Stale 60d subiu para 6 (vs 5). Composicao:
- 3 em `permanent/empresa` (mantidos)
- 1 em `permanent/pessoal` (NOVA)
- 2 em `structural/pessoal`

**Acao**: Identificar por path, atualizar ou arquivar com prefixo `_archived_`. Memorias `permanent` com 60 dias sem uso devem virar `cold` ou ser revisadas.

### R7 [MEDIO] — Revisar memorias permanent com baixa efficacy

- `corrections/capacidade-caminhoes-consultar-veiculos` — efficacy 0.212, 222 usos (subiu de 211)
- `corrections/agent-sdk-production-scope` — efficacy 0.212, 33 usos (estavel ha 3 ciclos)
- `corrections/confirmar-para-pedido-odoo` — efficacy 0.564, 360 usos (subiu de 331)

**Acao**: Memorias permanentes devem ser de alta qualidade. Revisar essas 3 e reescrever ou rebaixar. 4o ciclo consecutivo na lista.

### R8 [MEDIO] — Consolidar termos de glossario redundantes (4o ciclo)

Termos `integracao-nf` (0.046, 108 usos), `confirmar-pedido` (0.049, 81 usos), `cotacao` (0.074, 27 usos) sao carregados frequentemente mas raramente efetivos.

**Acao**: Consolidar redundantes ou enriquecer com contexto operacional. Entidades do KG ja capturam esses conceitos.

### R9 [BAIXO] — Cold tier voltou a crescer

Cold subiu de 32 -> 37 (+5) apos estabilidade no ciclo anterior. Concentracao em `structural/empresa` (22 cold). Estavel pelo total proporcional (10.77% -> 11.67%, +0.9pp).

**Acao**: Sem acao imediata. Monitorar proximo ciclo.

---

## Resumo Executivo

O sistema de memorias atingiu health score 86/100 (+1 vs ciclo anterior, NOVO RECORDE). Eficacia media subiu para 0.641 (+4.6%) — melhor metrica desde o inicio da serie. Crescimento total foi de +20 memorias (+6.7%) em 8 dias, continuando a desaceleracao iniciada no ciclo anterior. Sessoes totais subiram para 502 (+41), com Marcus Lima e Gabriella como heavy users. Pelo 5o ciclo consecutivo: ZERO memorias empresa tem `reviewed_at` preenchido, e KG coverage continua caindo (52.8 -> 40.1%). Surgiu padrao novo: `learned/expertise_*` u1 gerando ruido sistematico (3 das 11 zero-efficacy). Acoes URGENTES: R1 (auditar 11 zero-efficacy, 91 carregamentos perdidos), R2 (intervir em user-xml de 386 loads sem valor), R4 (5o ciclo sem implementar revisao empresa), R5 (recalibrar extrator `learned/expertise_*`).
