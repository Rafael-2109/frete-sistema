# Atualizacao Memory Eval — 2026-05-11-1

**Data**: 2026-05-11
**Health Score**: 82/100 (anterior: 86/100, delta: -4)
**Status**: OK — todas as 7 queries executaram com sucesso

---

## Metricas de Sessoes (Q1)

| Metrica | Valor |
|---------|-------|
| Total sessoes | 539 |
| Sessoes ultima semana | 41 |
| Sessoes ultimo mes | 150 |
| Usuarios unicos | 23 |
| Media mensagens/sessao | 8.57 |
| Media custo/sessao (USD) | $2.41 |

**Delta vs 2026-05-05**: +37 sessoes (+7.4%), +11 na ultima semana (30 -> 41, +37%) — pico de uso semanal. Usuarios unicos estaveis (23). Custo medio por sessao subiu levemente ($2.39 -> $2.41).

---

## Memorias por Categoria e Escopo (Q2)

| Categoria | Escopo | Total | Avg Importance | Avg Usage | Avg Effective | Avg Efficacy | Cold | Conflict | Stale 30d | Stale 60d |
|-----------|--------|-------|----------------|-----------|---------------|--------------|------|----------|-----------|-----------|
| contextual | pessoal | 9 | 0.43 | 35.33 | 29.78 | 0.843 | 3 | 0 | 0 | 0 |
| operational | empresa | 16 | 0.83 | 172.44 | 105.38 | 0.611 | 1 | 0 | 10 | 3 |
| operational | pessoal | 29 | 0.55 | 36.38 | 29.38 | 0.808 | 2 | 0 | 6 | 2 |
| permanent | empresa | 4 | 0.90 | 233.25 | 114.50 | 0.491 | 0 | 0 | 4 | 3 |
| permanent | pessoal | 25 | 0.89 | 74.76 | 55.04 | 0.736 | 0 | 0 | 7 | 3 |
| structural | empresa | 141 | 0.75 | 92.33 | 54.75 | 0.593 | 22 | 0 | 69 | 22 |
| structural | pessoal | 114 | 0.66 | 9.49 | 6.17 | 0.650 | 9 | 0 | 32 | 2 |
| **TOTAL** | | **338** | | | | **0.630** | **37** | **0** | **128** | **35** |

**Observacoes**:
- Total: 317 -> 338 (+21, +6.6% em 6 dias) — crescimento estavel em ritmo similar ao ciclo anterior
- `structural/empresa`: 136 -> 141 (+5, +3.7%) — estavel
- `structural/pessoal`: 99 -> 114 (+15, +15.2%) — segmento de maior crescimento absoluto
- `contextual/pessoal`: 8 -> 9 (+1)
- Cold: 37 -> 37 (estavel)
- Stale 30d: 78 -> 128 (+50, **+64%**) — salto grande, esperado dado o ciclo de 6 dias e idade da base
- Stale 60d: 6 -> 35 (+29, **+483%**) — **EXPLOSAO**: muitas memorias atravessaram a marca de 60 dias neste ciclo
- Eficacia media caiu de 0.641 -> 0.630 (-1.7%)
- Zero conflitos detectados (8o ciclo consecutivo)

---

## Top 20 Memorias Baixa Eficacia (Q3)

| # | Path | Efficacy | Usage | Effective | Category | User |
|---|------|----------|-------|-----------|----------|------|
| 1 | empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 0.000 | 32 | 0 | structural | u0 |
| 2 | empresa/armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus | 0.000 | 20 | 0 | structural | u0 |
| 3 | empresa/regras/quando-o-usuario-envia-saudacao-e-pedido | 0.000 | 19 | 0 | structural | u0 |
| 4 | empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 0.000 | 10 | 0 | structural | u0 |
| 5 | corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente | 0.000 | 9 | 0 | structural | u18 |
| 6 | empresa/termos/modo-debug | 0.000 | 6 | 0 | structural | u0 |
| 7 | learned/expertise_demonstra-conhecimento-de-seguranca-web-csrf-tokens | 0.000 | 6 | 0 | structural | u1 |
| 8 | empresa/regras/operadores-do-teams-bot-possuem-user-id | 0.000 | 5 | 0 | operational | u0 |
| 9 | empresa/usuarios/kerley | 0.000 | 5 | 0 | structural | u0 |
| 10 | learned/expertise_usuario-conhece-estrutura-tecnica-do-sistema-regex-aliases | 0.000 | 4 | 0 | structural | u1 |
| 11 | learned/expertise_conhece-infraestrutura-render-restart-vs-redeploy-git-dep | 0.000 | 3 | 0 | structural | u1 |
| 12 | learned/expertise_executa-fluxos-oauth-reautorizacao-scope-callback-de-for | 0.000 | 3 | 0 | structural | u1 |
| 13 | learned/expertise_conhece-riscos-de-deploy-em-prod-mencionou-cache-de-templat | 0.000 | 3 | 0 | structural | u1 |
| 14 | empresa/termos/integracao-nf | 0.046 | 108 | 5 | structural | u0 |
| 15 | empresa/termos/confirmar-pedido | 0.049 | 81 | 4 | structural | u0 |
| 16 | empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo | 0.052 | 172 | 9 | operational | u0 |
| 17 | empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i | 0.061 | 49 | 3 | structural | u0 |
| 18 | system/download_config | 0.064 | 47 | 3 | structural | u1 |
| 19 | empresa/armadilhas/_archived_sessao-teams-reinicia-antes-de-subagente-concluir | 0.067 | 15 | 1 | structural | u0 |
| 20 | empresa/termos/cotacao | 0.074 | 27 | 2 | structural | u0 |

**Destaque critico**: **13 memorias com efficacy = 0 e usage >= 3** (vs 11 no ciclo anterior, **+2**). Novas zero-efficacy desde 05/05:
- `learned/expertise_usuario-conhece-estrutura-tecnica-do-sistema-regex-aliases` (u1, 4 usos, criada 2026-05-09)
- `learned/expertise_executa-fluxos-oauth-reautorizacao-scope-callback-de-for` (u1, 3 usos)

Padrao `learned/expertise_*` u1 segue piorando: **5 das 13 zero-efficacy** sao desse padrao (vs 3 no ciclo anterior). `reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus` subiu de 14 -> 20 usos (todos sem efeito).

---

## Sessoes por Usuario — Ultimos 30d (Q5)

| Usuario | Sessions | Mensagens | Custo (USD) | Ultima Sessao |
|---------|----------|-----------|-------------|---------------|
| Rafael (id=1) | 57 | 300 | $98.55 | 2026-05-11 |
| Marcus Lima (id=18) | 32 | 718 | $312.23 | 2026-05-10 |
| Gabriella (id=69) | 18 | 234 | $185.77 | 2026-05-08 |
| Elaine (id=67) | 16 | 130 | $40.10 | 2026-05-07 |
| Thamires (id=27) | 7 | 16 | $1.75 | 2026-05-07 |
| Rafael (id=55) | 6 | 40 | $26.37 | 2026-05-08 |
| Denise (id=2) | 6 | 60 | $20.21 | 2026-05-05 |
| Thamyrez (id=63) | 3 | 14 | $1.99 | 2026-04-30 |
| Nicoly (id=71) | 2 | 46 | $15.43 | 2026-04-30 |
| Marcus V. (id=56) | 1 | 8 | $2.31 | 2026-05-03 |
| Jessica (id=4) | 1 | 2 | $0.18 | 2026-04-16 |
| Guilherme (id=72) | 1 | 2 | $0.26 | 2026-04-14 |

**Destaques**:
- Rafael (id=1): +11 sessoes (46 -> 57), custo +$31 ($67.01 -> $98.55), 300 mensagens (+45) — retomada de uso intenso
- Marcus Lima: +7 sessoes (25 -> 32), maior custo $312.23 (+$5), 718 mensagens (+43) — pico de uso continua
- Gabriella: -2 sessoes (20 -> 18), custo praticamente igual ($186 vs $198)
- Elaine: -1 sessao (17 -> 16), estavel
- Denise: -3 sessoes (9 -> 6), custo estavel
- Sumiram do top: Claude Code (id=74), Talita (id=17)
- Total sessoes em 30d: 150 (vs 143)

---

## Memorias Empresa (Q6) — user_id=0

Total: **163** memorias empresa (+27 vs 136 do ciclo anterior, **+19.9%** — maior crescimento da serie).

**Aviso**: O numero de empresa pulou de 136 -> 163. O total geral foi de 317 -> 338 (+21), enquanto empresa cresceu +27. Algumas memorias podem ter migrado de escopo pessoal para empresa. Verificar.

**Memorias empresa com efficacy < 0.2 e usage >= 3 (18 memorias problematicas)**:

| Path | Usage | Effective | Efficacy | Reviewed |
|------|-------|-----------|----------|----------|
| heuristicas/integracao/user-xml-nao-atualiza-por-threshold-de-sessoes | 386 | 48 | 0.124 | NULL |
| heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo | 172 | 9 | 0.052 | NULL |
| termos/integracao-nf | 108 | 5 | 0.046 | NULL |
| termos/confirmar-pedido | 81 | 4 | 0.049 | NULL |
| regras/pedidos-para-a-rede-assai-no-odoo-precis | 80 | 12 | 0.150 | NULL |
| pitfalls/agente/memory-injection-protocolo-vs-heuristica | 54 | 6 | 0.111 | NULL |
| regras/a-rede-assai-opera-com-multiplas-lojas-i | 49 | 3 | 0.061 | NULL |
| correcoes/gilberto-nao-existe-na-equipe-da-nacom-g | 47 | 7 | 0.149 | NULL |
| armadilhas/integracao/save-memory-ignora-target-user-id-sem-debug-mode | 47 | 5 | 0.106 | NULL |
| protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel | 32 | 0 | 0.000 | NULL |
| termos/cotacao | 27 | 2 | 0.074 | NULL |
| armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus | 20 | 0 | 0.000 | NULL |
| regras/quando-o-usuario-envia-saudacao-e-pedido | 19 | 0 | 0.000 | NULL |
| armadilhas/_archived_sessao-teams-reinicia-antes-de-subagente-concluir | 15 | 1 | 0.067 | NULL |
| perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di | 10 | 0 | 0.000 | NULL |
| termos/modo-debug | 6 | 0 | 0.000 | NULL |
| regras/operadores-do-teams-bot-possuem-user-id | 5 | 0 | 0.000 | NULL |
| usuarios/kerley | 5 | 0 | 0.000 | NULL |

**Carregamentos perdidos**: 1.163 loads cumulativos sem produzir efeito (foram 91 zero-efficacy ciclo passado + agora muitos com efficacy < 0.2).

**Nota critica (6o ciclo consecutivo)**: NENHUMA das 163 memorias empresa possui `reviewed_at` preenchido. Identificado em 06/04, 13/04, 20/04, 27/04, 05/05, 11/05. **14 novas memorias empresa criadas na ultima semana** sem revisao.

**Memorias empresa com alta efficacy (destaques 2026-05-11)**:
- `heuristicas/recebimento/de-para-fornecedor-usa-codigos-numericos-simples` (efficacy 0.65, +alto uso) — estrela do ciclo anterior, continua produtiva
- `armadilhas/recebimento/consolidacao-bloqueada-por-ajuste-manual-po-pos-match` — segue alta efficacy
- `armadilhas/financeiro/nosso-numero-dac-zero-grava-caracter-invalido` — produtiva
- `protocolos/comercial/confirmacao-em-lote-de-cotacoes-exige-selecao-previa-por` — produtiva

**Novas memorias empresa criadas no ciclo (5-11 maio)** (14 totais — destaques):
- `heuristicas/financeiro/baseline-de-extratos-formato-fixo` (criada u18, agora 141 usos, efficacy 0.553) — destaque do ciclo
- `heuristicas/integracao/alias-de-modelo-ausente-bloqueia-importacao-recibo-inteiro` (u1, 8 usos, efficacy 0.75)
- `armadilhas/integracao/regex-fallback-nunca-ativa-quando-principal-captura-parcial` (u1, 21 usos, efficacy 0.476)
- `armadilhas/carvia/cte-sefaz-externo-e-cte-interno-carvia-sao-entidades` (u55, 20 usos, efficacy 0.45)
- `heuristicas/carvia/tde-automatica-dago-deve-entrar-como-despesa-extra` (u55, 20 usos, efficacy 0.30)
- `armadilhas/carvia/peso-cubado-nao-e-automatico-no-backfill-carvia` (u55, efficacy 0.80)

---

## Knowledge Graph (Q4 + Q7)

### Entidades por Tipo

| Tipo | Total | Memorias Linkadas | Avg Mentions |
|------|-------|-------------------|--------------|
| conceito | 935 | 132 | 1.48 |
| processo | 140 | 75 | 1.33 |
| campo | 101 | 62 | 1.23 |
| produto | 76 | 37 | 2.04 |
| regra | 68 | 9 | 1.12 |
| termo | 64 | 40 | 1.94 |
| valor | 44 | 11 | 1.14 |
| uf | 31 | 8 | 4.06 |
| cliente | 27 | 21 | 8.63 |
| transportadora | 27 | 17 | 1.81 |
| usuario | 13 | 13 | 7.00 |
| cnpj | 10 | 8 | 1.40 |
| pedido | 7 | 5 | 5.43 |
| fornecedor | 6 | 6 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Total entidades**: 1.550 (+71 vs 1.479 ciclo anterior, +4.8%)
**KG Coverage estimada**: ~132/338 = **39.05%** (vs 40.1% anterior, -1.05pp)

**Observacao**: KG coverage cai pelo 6o ciclo consecutivo (52.8 -> 43.4 -> 41.4 -> 40.1 -> 39.05%). Entidades crescem +4.8%, memorias crescem +6.6%. Limite assintotico aparente em ~40% — esta degradacao confirma que extrator nao acompanha o ritmo de novas memorias.

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

Top 11 relacoes identicas aos ultimos 4 ciclos — grafo semantico permanece estavel.

---

## Memorias Permanent com baixa efficacy (auxiliar)

| Path | Usage | Efficacy | Escopo | User |
|------|-------|----------|--------|------|
| corrections/capacidade-caminhoes-consultar-veiculos | 232 | 0.233 | empresa | u0 |
| preferences (u1) | 114 | 0.430 | pessoal | u1 |
| preferences (u67) | 58 | 0.069 | pessoal | u67 |
| corrections/identidade-agent-sdk-producao | 41 | 0.415 | pessoal | u1 |
| corrections/agent-sdk-production-scope | 35 | 0.257 | empresa | u0 |
| user.xml (u56) | 12 | 0.417 | pessoal | u56 |
| preferences (u71) | 10 | 0.400 | pessoal | u71 |

**Destaque**: `preferences.xml` do u67 (Elaine) com **0.069 efficacy em 58 loads** — provavel preferences orfa ou mal-formatada.

---

## Health Score — Detalhamento

| Dimensao | Peso | Valor Medido | Score (0-100%) | Pontos |
|----------|------|--------------|----------------|--------|
| Eficacia media | 30% | 0.630 (range 0.2-0.7) | 86.0% | 25.8 |
| Taxa cold | 20% | 10.95% (37/338) | 97.6% | 19.5 |
| Stale 60d | 20% | 10.36% (35/338) | 84.7% | 16.9 |
| KG coverage | 15% | 39.05% (132/338) | 31.75% | 4.8 |
| Correcoes | 15% | 0.00 | 100% | 15.0 |
| **TOTAL** | **100%** | | | **82** |

**Comparativo serie historica**:

| Metrica | 2026-04-06 | 2026-04-13 | 2026-04-20 | 2026-04-27 | 2026-05-05 | 2026-05-11 | Delta 6d |
|---------|------------|------------|------------|------------|------------|------------|----------|
| Health Score | 81 | 84 | 84 | 85 | 86 | **82** | **-4** |
| Total memorias | 128 | 197 | 272 | 297 | 317 | 338 | +21 |
| Cold | 14 | 15 | 32 | 32 | 37 | 37 | 0 |
| Stale 60d | 2 | 2 | 2 | 5 | 6 | **35** | **+29** |
| KG coverage | - | 52.8% | 43.4% | 41.4% | 40.1% | 39.05% | -1.05pp |
| Eficacia media | - | 0.54 | 0.597 | 0.613 | 0.641 | 0.630 | -0.011 |
| Sessoes total | - | 391 | 434 | 461 | 502 | 539 | +37 |
| Sessoes ultima semana | - | 30 | 45 | 29 | 30 | 41 | +11 |
| Usuarios unicos | - | 21 | 22 | 22 | 23 | 23 | 0 |

**Drivers da queda do health score** (-4 pontos):
- Stale 60d explodiu (6 -> 35, +29) — dimensao caiu de 100% para 84.7% (-3 pontos)
- KG coverage caiu 1pp (-0.15 pontos)
- Eficacia caiu leve (-0.5 pontos)

---

## Recomendacoes Acionaveis

### R1 [URGENTE] — Auditar 13 memorias com efficacy=0 e usage >= 3

**Crescimento**: 11 -> 13 zero-efficacy. Soma de 125 loads sem efeito.

Novas zero-efficacy desde 05/05:
- `learned/expertise_usuario-conhece-estrutura-tecnica-do-sistema-regex-aliases` (u1, 4 usos)
- `learned/expertise_executa-fluxos-oauth-reautorizacao-scope-callback-de-for` (u1, 3 usos)

Memorias legadas persistentes (>= 5 ciclos, total ~125 loads cumulativos):
- `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel` (32 usos)
- `empresa/armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus` (20 usos, era 14)
- `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido` (19 usos)
- `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di` (10 usos)
- `empresa/termos/modo-debug` (6 usos)
- `empresa/usuarios/kerley` (5 usos)
- `empresa/regras/operadores-do-teams-bot-possuem-user-id` (5 usos)

**Acao**: Auditoria humana URGENTE. 125+ carregamentos sem valor. 6o ciclo sem acao concreta. Padrao `learned/expertise_*` u1 deve ser desabilitado.

### R2 [CRITICO] — user-xml-nao-atualiza-por-threshold-de-sessoes (6o ciclo)

Memoria com **386 usos** (estavel) e efficacy **0.124**. 6o ciclo consecutivo no top zero. 386 carregamentos com 48 efetivos = **338 carregamentos inuteis**.

**Acao**: Investigar padrao de injection. Reescrever ou rebaixar prioridade. Decisao em aberto desde 06/04 (>= 5 semanas).

### R3 [URGENTE-NOVO] — Investigar explosao de stale 60d (6 -> 35)

**Salto de +483%**. Composicao:
- `structural/empresa`: 22 stale 60d (era 0 — explosao concentrada aqui)
- `permanent/empresa`: 3 (estavel)
- `permanent/pessoal`: 3 (era 1, +2)
- `operational/empresa`: 3 (era 0, +3)
- `operational/pessoal`: 2 (era 0, +2)
- `structural/pessoal`: 2 (estavel)

**Acao**: Auditar particularmente as 22 memorias `structural/empresa` stale 60d. Muitas devem ter atravessado a marca de 60 dias por inatividade. Mover candidatas para cold tier ou arquivar.

### R4 [ALTO] — Reverter queda de KG coverage (39.05% -> meta 70%)

6o ciclo consecutivo de queda (52.8 -> 43.4 -> 41.4 -> 41.4 -> 40.1 -> 39.05%). Aparenta estabilizacao em ~39%, abaixo do anterior.

**Acao**: Rodar extrator de entidades em batch sobre as 21 memorias criadas nos ultimos 6 dias. Avaliar se 40% e teto natural do extrator atual ou se precisa de redesign. Sem intervencao, tende a continuar caindo conforme a base cresce.

### R5 [ALTO] — Implementar revisao formal de memorias empresa (6o ciclo)

NENHUMA das **163** memorias empresa tem `reviewed_at` preenchido. Recomendado em 06/04, 13/04, 20/04, 27/04, 05/05, 11/05. Nao implementado ha **6 ciclos** (>= 5 semanas). Empresa cresceu **+27 memorias** neste ciclo sem revisao.

**Acao**: Criar processo de curadoria que preencha `reviewed_at` apos verificacao. Comecar pelas 18 memorias empresa com efficacy < 0.2 e usage >= 3. Considerar bloqueio automatico via constraint ou alerta no fluxo de criacao.

### R6 [ALTO] — Padrao `learned/expertise_*` gera ruido sistematico (5 das 13 zero-efficacy)

Evolucao: 1 -> 3 -> 5 ciclos. **Padrao em aceleracao**.

**Acao**: Revisar logica de extracao de "expertise" em `app/agente/`. Identifica conhecimento sem mapear para uso operacional. URGENTE desabilitar ou recalibrar threshold de criacao.

### R7 [MEDIO] — `preferences.xml` u67 (Elaine) com 0.069 efficacy em 58 loads

Memoria permanente do u67 com efficacy critica.

**Acao**: Inspecionar conteudo do `preferences.xml` da Elaine. Provavel preferences orfa, malformada ou herdada de outro usuario. Considerar reset.

### R8 [MEDIO] — Revisar memorias permanent com baixa efficacy

- `corrections/capacidade-caminhoes-consultar-veiculos` — efficacy 0.233, **232 usos** (+10)
- `corrections/agent-sdk-production-scope` — efficacy 0.257, 35 usos
- `preferences (u67)` — efficacy 0.069, 58 usos

**Acao**: Memorias permanentes devem ser de alta qualidade. Revisar e reescrever ou rebaixar. 5o ciclo consecutivo na lista.

### R9 [MEDIO] — Consolidar termos de glossario redundantes (5o ciclo)

Termos `integracao-nf` (0.046, 108 usos), `confirmar-pedido` (0.049, 81 usos), `cotacao` (0.074, 27 usos), `pedidos-para-a-rede-assai` (0.150, 80 usos) sao carregados frequentemente mas raramente efetivos. Total: **296 loads cumulativos**.

**Acao**: Consolidar redundantes ou enriquecer com contexto operacional. Entidades do KG ja capturam esses conceitos.

### R10 [BAIXO] — Investigar pulo de empresa (136 -> 163, +27 em 6 dias)

Crescimento atipico de empresa (+19.9%) em 6 dias enquanto total cresceu +6.6%. Possiveis causas: (a) migracao de escopo pessoal -> empresa; (b) batch de criacao operacional; (c) ajuste de classificacao.

**Acao**: Verificar logs ou tabela de auditoria para entender o salto. Confirmar que e crescimento intencional, nao bug.

---

## Resumo Executivo

O sistema de memorias caiu para **health score 82/100 (-4 vs ciclo anterior)** apos 5 ciclos de melhora consecutiva. Driver principal: explosao de stale 60d (6 -> 35, +483%) — muitas memorias `structural/empresa` atravessaram a marca de 60 dias sem update. Total cresceu para 338 (+21), eficacia caiu levemente para 0.630 (-0.011), e KG coverage segue em queda lenta (39.05%, 6o ciclo). Sessoes subiram para 539 (+37), com pico semanal de 41 (+37%). Rafael (id=1) retomou uso intenso (+11 sessoes, +$31 custo) e Marcus Lima segue heavy user ($312 no mes). Memorias empresa explodiram para 163 (+27, +19.9%) sem nenhuma com `reviewed_at` preenchido — 6o ciclo consecutivo desse problema. 13 memorias zero-efficacy (+2), com padrao `learned/expertise_*` u1 acelerando (5 das 13). Acoes URGENTES: R3 (auditar 35 stale 60d, salto inedito), R5 (6o ciclo sem revisao empresa, 163 memorias afetadas), R6 (recalibrar extrator `learned/expertise_*` antes que escale), R10 (investigar pulo +27 em empresa).
