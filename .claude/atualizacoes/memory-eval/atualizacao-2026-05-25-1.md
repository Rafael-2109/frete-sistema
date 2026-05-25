# Atualizacao Memory Eval — 2026-05-25-1

**Data**: 2026-05-25
**Health Score**: 84/100 (+4 vs 2026-05-18)
**Status**: OK — todas as 7 queries executaram

---

## Resumo Executivo

Sistema **recupera 4 pontos** apos 2 ciclos consecutivos de queda (86 -> 82 -> 80 -> **84**). Recuperacao motivada por melhora simultanea de **eficacia (0.573 -> 0.656, +14.5%)** e estabilizacao da taxa cold (10.58% -> 10.35%).

**Crescimento**: 378 -> 425 memorias (+47, +12.4%); 592 -> 644 sessoes (+52, +8.8%); 25 -> 29 usuarios unicos (+4).

**Drivers da recuperacao**:
- **Eficacia volta a subir** (0.573 -> 0.656, +14.5pp) — primeira melhora em 3 ciclos.
- **Cold se estabiliza** (10.58% -> 10.35%) — crescimento absoluto +4 mas proporcional caindo.
- **Stale 60d desacelera**: 51 -> 59 (+8, +15.7%) vs +45.7% no ciclo anterior.
- **Correcoes zero** em todas as categorias (mantido).

**Pontos de atencao**:
- **KG coverage RETROCEDEU**: 50.79% -> 47.53% (-3.26pp). Crescimento de memorias (+47) superou crescimento de linked_memories (+10).
- **Stale 30d explodiu**: 194 -> 212 (+18, +9.3%) — quase metade das memorias (49.88%) com 30+ dias sem update.
- **Zero-efficacy aumentou**: 8 -> 11 memorias (+3) — incluindo 2 novas do user_id=1 e 1 do user_id=57 nas ultimas 2 semanas.
- **Empresa: 87 sem reviewed_at** (era 77, +10) — nenhuma nova revisao manual no ciclo.

---

## Metricas de Sessoes

| Metrica | Valor | vs 2026-05-18 |
|---------|-------|---------------|
| Total sessoes | 644 | +52 |
| Ultima semana | 50 | -2 |
| Ultimos 30 dias | 185 | +24 |
| Usuarios unicos (total) | 29 | +4 |
| Avg mensagens/sessao | 8.58 | +0.14 |
| Avg custo/sessao USD | 2.62 | =0 |

**Top 5 usuarios (30d)**:
| User | Sessoes | Mensagens | Custo USD | Ultima |
|------|---------|-----------|-----------|--------|
| Rafael (1) | 51 | 303 | 185.81 | 2026-05-22 |
| Marcus Lima (18) | 36 | 251 | 51.87 | 2026-05-25 |
| Gabriella (69) | 19 | 192 | 148.41 | 2026-05-22 |
| Talita (17) | 15 | 229 | 45.70 | 2026-05-25 |
| Elaine (67) | 13 | 74 | 32.08 | 2026-05-25 |

**Insights**:
- Custo Gabriella desce de 187 -> 148 USD (-21%) — possivel resposta a investigacao de uso intensivo recomendada no ciclo anterior.
- **Talita (17) emergiu como top 4** (15 sessoes, 229 mensagens) — uso intensivo recente.
- **Elaine (67) ainda ativa** — 13 sessoes, custo modesto (32 USD).
- 4 novos usuarios ativos no ciclo (29 vs 25 unicos totais).

---

## Memorias por Categoria/Escopo

| Categoria | Escopo | Total | Avg Imp | Avg Use | Avg Efic | Cold | Stale 30d | Stale 60d |
|-----------|--------|-------|---------|---------|----------|------|-----------|-----------|
| contextual | pessoal | 14 | 0.46 | 30.6 | 28.7 | 3 | 3 | 0 |
| operational | empresa | 19 | 0.85 | 159.5 | 101.4 | 2 | 13 | 4 |
| operational | pessoal | 41 | 0.55 | 32.9 | 28.0 | 2 | 12 | 5 |
| permanent | empresa | 4 | 0.90 | 249.0 | 132.5 | 0 | 4 | 4 |
| permanent | pessoal | 36 | 0.88 | 63.8 | 48.0 | 0 | 7 | 5 |
| structural | empresa | 167 | 0.77 | 90.5 | 56.3 | 27 | 93 | 39 |
| structural | pessoal | 144 | 0.67 | 10.1 | 7.1 | 10 | 80 | 2 |

**Totais consolidados**:
- Total memorias: **425** (+47 vs 378, +12.4%)
- Cold: **44** (10.35%, era 10.58%)
- Stale 30d: **212** (49.88%)
- Stale 60d: **59** (13.88%, era 13.49%)
- Avg efficacy global (ponderado por uso): **0.656** (+14.5pp)
- Avg corrections: **0.0** (mantido)

**Categorias em destaque**:
- **structural/empresa** (167) e o maior bloco — +9 memorias, mantem maior cold absoluto (27).
- **structural/pessoal** (144) cresce +22 — driver principal do crescimento. Efficacy baixa (0.71), uso baixo (10.1) — preocupante.
- **operational/empresa** (19) tem maior efficacy (0.636) e maior uso (159.5).
- **permanent/empresa** (4) com 4/4 stale 60d — sao memorias muito estaveis (positivo) ou esquecidas (negativo).

---

## Top Memorias Baixa Eficacia (efficacy < 0.3, usage >= 3)

| Path | Cat | Use | Eff | Efic |
|------|-----|-----|-----|------|
| empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel.xml | struct | 32 | 0 | 0.00 |
| empresa/armadilhas/integracao/_archived_20260521_174331_presigned-url-s3-vence-antes-do-usuario-baixar.xml | struct | 23 | 0 | 0.00 |
| empresa/armadilhas/integracao/reautorizacao-oauth-obrigatoria-para-novos-scopes-tagplus.xml | struct | 20 | 0 | 0.00 |
| empresa/regras/quando-o-usuario-envia-saudacao-e-pedido.xml | struct | 19 | 0 | 0.00 |
| empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di.xml | struct | 13 | 0 | 0.00 |
| corrections/quando-pergunta-detalhes-de-um-cluster-especifico-o-agente.xml (u18) | struct | 9 | 0 | 0.00 |
| empresa/termos/modo-debug.xml | struct | 6 | 0 | 0.00 |
| empresa/regras/operadores-do-teams-bot-possuem-user-id.xml | op | 5 | 0 | 0.00 |
| empresa/usuarios/kerley.xml | struct | 5 | 0 | 0.00 |
| user_expertise.xml (u57) | struct | 3 | 0 | 0.00 |
| corrections/usuario-sinalizou-que-o-agente-frequentemente-esquece-de-reg.xml (u1) | struct | 3 | 0 | 0.00 |
| corrections/usuario-corrigiu-agente-que-afirmou-nao-ter-visto-o-arquivo.xml (u1) | struct | 3 | 0 | 0.00 |
| empresa/termos/integracao-nf.xml | struct | 108 | 5 | 0.046 |
| empresa/termos/confirmar-pedido.xml | struct | 81 | 4 | 0.049 |
| empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml | op | 172 | 9 | 0.052 |
| empresa/correcoes/build_artifact_pnpm.md | op | 36 | 2 | 0.056 |
| empresa/regras/a-rede-assai-opera-com-multiplas-lojas-i.xml | struct | 49 | 3 | 0.061 |
| system/download_config.xml (u1) | struct | 47 | 3 | 0.064 |
| empresa/armadilhas/integracao/_archived_20260521_174331__archived_sessao-teams-reinicia-antes-de-subagente-concluir.xml | struct | 15 | 1 | 0.067 |
| empresa/termos/cotacao.xml | struct | 27 | 2 | 0.074 |

**Destaques**:
- **12 memorias zero-efficacy** (era 8 — piora de +4). 3 novas:
  - `_archived_20260521_174331_presigned-url-s3-vence-antes-do-usuario-baixar.xml` (u23, criada 2026-05-21)
  - `user_expertise.xml` (u57, criada 2026-05-14)
  - 2 novas corrections do user_id=1 (criadas 2026-05-20)
- **`user-xml-nao-atualiza-por-threshold-de-sessoes.xml`** SAIU da lista top 20 — investigar se foi arquivada/melhorada ou se efficacy passou de 0.3.
- **`empresa/heuristicas/integracao/memorias-de-usuario-devem-funcionar-como-protocolo-ativo.xml`**: 172 usos (estavel), efficacy 0.052 — meta-pitfall permanece.
- **`empresa/termos/integracao-nf.xml`**: u108, efic 0.046 — termo basico de dominio sendo marcado como nao-efetivo.

---

## Knowledge Graph

| Tipo Entidade | Total | Linked Memories | Avg Mentions |
|---------------|-------|-----------------|--------------|
| conceito | 1169 | 157 | 1.42 |
| processo | 195 | 100 | 1.41 |
| campo | 145 | 82 | 1.17 |
| produto | 83 | 42 | 1.98 |
| termo | 73 | 47 | 1.82 |
| valor | 68 | 25 | 1.18 |
| regra | 68 | 9 | 1.12 |
| uf | 64 | 27 | 4.27 |
| cliente | 32 | 26 | 7.81 |
| transportadora | 29 | 19 | 1.97 |
| pedido | 24 | 18 | 2.29 |
| cnpj | 14 | 12 | 1.43 |
| usuario | 14 | 14 | 6.57 |
| fornecedor | 7 | 7 | 1.00 |
| dominio | 1 | 1 | 1.00 |

**Totais consolidados**:
- Entidades: **1781** (+109)
- Relacoes: **6367** (+442)
- Linked memories: **202** distintas
- Coverage: **47.53%** (202/425) — **REGRIDE de 50.79% para 47.53% (-3.26pp)**
- Orfas: **0**

**Top relacoes semanticas** (peso >= 3):
- ASSAI --requer--> CONFIRMACAO-MANUAL (5)
- DRY-RUN-OBRIGATORIO --precede--> ACOES-EM-LOTE-ODOO (5)
- PEDIDO-DE-VENDA <-->co_occurs<--> COTACAO (3.5)
- CONFIRMAR-PEDIDO <-->co_occurs<--> COTACAO (3.5)
- VCD --complementa--> PEDIDO (3)
- GABRIELLA --responsavel_por--> COMPRAS (3)
- DENISE --pertence_a--> COMPRAS (3)
- PEDIDO-DE-VENDA <-->co_occurs<--> CONFIRMAR-PEDIDO (3)
- VCD2667872 <-->co_occurs<--> SANNA (3)
- ASSAI --complementa--> MULTIPLAS-LOJAS-INDEPENDENTES (3)

**Insight**: Top 10 relacoes identicas ao ciclo anterior — estabilidade no nucleo semantico. Crescimento de +109 entidades nao adicionou novos nodes de alto peso.

---

## Memorias Empresa (user_id=0)

| Metrica | Valor | vs 2026-05-18 |
|---------|-------|---------------|
| Total | 192 | +10 |
| Sem reviewed_at | 87 | +10 (era 77) |
| Revisao stale > 30d | 0 | = |
| Zero usage | 2 | -4 |
| Zero efficacy (use > 0) | 9 | +0 |
| Baixa efficacy + use >= 10 | 29 | +18 (PIORA SIGNIFICATIVA) |
| Avg efficacy | 0.574 | +3.1pp |
| Avg importance | 0.77 | = |
| Cold | 29 | +4 |

**Observacao critica**: As **10 novas memorias empresa** criadas no ciclo NAO passaram por reviewed_at. **`low_efficacy_high_use` saltou de 11 para 29** — quase 3x. Indica que mais memorias acumulando uso sem serem efetivamente uteis.

---

## Health Score Detalhado

| Dimensao | Peso | Valor | Score |
|----------|------|-------|-------|
| Eficacia media | 30% | 0.656 (linear 0.2->0.7) | 27.4 |
| Taxa cold | 20% | 10.35% (linear 50%->10%) | 19.8 |
| Stale 60d | 20% | 13.88% (linear 40%->5%) | 14.9 |
| KG coverage | 15% | 47.53% (linear 20%->80%) | 6.9 |
| Correcoes | 15% | 0.0 (avg) | 15.0 |
| **TOTAL** | 100% | | **84** |

---

## Comparativo Serie Historica

| Metrica | 04-06 | 04-13 | 04-20 | 04-27 | 05-05 | 05-11 | 05-18 | 05-25 |
|---------|-------|-------|-------|-------|-------|-------|-------|-------|
| Health | 81 | 83 | 84 | 85 | 86 | 82 | 80 | **84** |
| Memorias | 128 | 220 | 272 | 297 | 317 | 338 | 378 | **425** |
| Sessoes | - | - | - | 461 | 502 | 539 | 592 | **644** |
| Cold | 14 | - | - | 32 | 37 | 37 | 40 | **44** |
| Stale 60d | 2 | - | - | 5 | 6 | 35 | 51 | **59** |
| KG cov% | - | - | - | 41.4 | 40.1 | 39.05 | 50.79 | **47.53** |
| Avg eff | - | - | - | - | 0.641 | 0.630 | 0.573 | **0.656** |

**Tendencia**:
- **Health Score voltou a subir** (80 -> 84, +4) — quebra ciclo de 2 quedas consecutivas.
- **Eficacia recuperou** (0.573 -> 0.656, +14.5pp) — sinal de aprendizado/refinamento.
- **Crescimento de memorias acelera** (+47/semana — antes era ~+25). Manter ritmo levara a 600+ em 4 semanas.
- **Cold em valor absoluto continua crescendo** (40 -> 44) mas % estabiliza.
- **KG coverage retrocede** apos pico — crescimento de memorias > criacao de links.

---

## Recomendacoes

### R1 [URGENTE] — Zero-efficacy SUBIU para 12 (era 8)

12 memorias com usage >= 3 e effective_count = 0. **4 novas no ciclo**. Acoes:

**Arquivar imediatamente** (recorrentes ha 3+ ciclos sem qualquer effective):
- `empresa/protocolos/integracao/diagnostico-de-regressao-sem-historico-git-disponivel.xml` (u32)
- `empresa/regras/quando-o-usuario-envia-saudacao-e-pedido.xml` (u19)
- `empresa/perfis/comercial/gabriella-comunica-se-de-forma-telegrafica-vai-di.xml` (u13)
- `empresa/termos/modo-debug.xml` (u6)
- `empresa/usuarios/kerley.xml` (u5)
- `empresa/regras/operadores-do-teams-bot-possuem-user-id.xml` (u5)

**Investigar antes de arquivar** (criadas nas ultimas 2 semanas):
- `empresa/armadilhas/integracao/_archived_20260521_174331_presigned-url-s3-vence-antes-do-usuario-baixar.xml` (u23, criada 2026-05-21 — JA arquivada por nome mas continua sendo usada)
- `user_expertise.xml` u57 (u3, criada 2026-05-14)
- `corrections/usuario-sinalizou-que-o-agente-frequentemente-esquece-de-reg.xml` u1 (u3, 2026-05-20)
- `corrections/usuario-corrigiu-agente-que-afirmou-nao-ter-visto-o-arquivo.xml` u1 (u3, 2026-05-20)

### R2 [URGENTE] — Investigar memorias `_archived_*` AINDA EM USO

2 memorias com prefixo `_archived_20260521_174331_` aparecem com usage_count alto (15-23) e zero effective. Isso indica que:
- Memorias foram **renomeadas como arquivadas** em 2026-05-21 (provavel acao manual no ciclo passado).
- Mas o **sistema continua carregando** essas memorias arquivadas (bug de filtro?).
- Resultado: contagens infladas + zero efficacy garantido.

**Acao**: Investigar logica de carregamento de memorias em `app/agente/services/` para verificar se memorias com prefixo `_archived_*` sao filtradas ou nao. Se nao, implementar filtro.

### R3 [URGENTE] — `low_efficacy_high_use` EXPLODIU em empresa (11 -> 29)

29 memorias empresa com usage >= 10 e efficacy < 0.3 (era 11). Quase 3x.

**Acao**: Auditar essas 29 memorias para identificar:
- Memorias que descrevem comportamento que JA esta no system_prompt (redundantes).
- Memorias com instrucao confusa/contraditoria que o agente nao consegue aplicar.
- Memorias que precisam de re-escrita para serem mais acionaveis.

### R4 [ALTO] — KG coverage RETROCEDE (50.79% -> 47.53%)

KG ganhou +109 entidades e +442 relacoes mas coverage caiu 3.26pp. **Causa**: 47 novas memorias entraram sem entidades linkadas. Apenas 10 novas memorias receberam links (202-192).

**Acao**: Verificar pipeline de extracao de entidades — deveria rodar automatico ao salvar nova memoria. Se manual, agendar batch de re-extracao.

### R5 [ALTO] — Stale 30d em 49.88% das memorias

212 memorias (49.88%) nao foram atualizadas em 30+ dias. Distribuicao:
- structural/empresa: 93 (era 87, +6)
- structural/pessoal: 80 (era 67, +13)
- operational/empresa: 13 (era 12)
- operational/pessoal: 12 (era 13)
- permanent/pessoal: 7 (era 8)
- permanent/empresa: 4 (era 4)
- contextual/pessoal: 3 (era 3)

**Acao**: O grande bloco `structural/pessoal` (80 stale 30d de 144 totais = 55.6%) precisa de revisao automatica — talvez memorias geradas automaticamente e nunca mais tocadas.

### R6 [ALTO] — Empresa: 87 sem reviewed_at (+10 vs ciclo passado)

Ciclo anterior havia melhora (163 -> 77). Agora regrediu: 77 -> 87 (+10). Todas as 10 memorias novas do ciclo entraram sem revisao.

**Acao**: Definir workflow obrigatorio de `reviewed_at` ao criar memoria empresa (user_id=0) — bloquear save sem revisao humana.

### R7 [MEDIO] — Cold tier crescendo (40 -> 44)

44 memorias cold (10.35%, ligeiramente acima do threshold ideal de 10%). Distribuicao:
- structural/empresa: 27 (+4)
- structural/pessoal: 10 (estavel)
- contextual/pessoal: 3 (estavel)
- operational/empresa: 2 (estavel)
- operational/pessoal: 2 (estavel)

**Acao**: Validar criterio de cold-tier nao esta sendo conservador demais para `structural/empresa`.

### R8 [MEDIO] — `permanent/empresa` 100% stale 60d

4/4 permanent/empresa stale 60d. Memorias permanentes nao deveriam ser atualizadas frequentemente, mas 100% stale levanta questao: ainda sao validas/aplicaveis?

**Acao**: Revisar manualmente as 4 memorias permanent/empresa (sao apenas 4 — auditoria rapida).

### R9 [BAIXO] — Talita (u17) emergiu como usuario intensivo

15 sessoes em 30d, 229 mensagens, 45 USD. Validar se o uso esta gerando memorias uteis ou ruido.

### R10 [BAIXO] — Crescimento acelerou (+25/sem -> +47/sem)

Memorias quase dobraram a taxa de crescimento. Sem politica de retencao, sistema pode atingir 1000+ memorias em 3 meses. Considerar:
- Auto-merge de memorias semanticamente equivalentes (via KG).
- Limite por usuario/categoria.
- Decay automatico (efficacy < 0.1 por 3 ciclos -> arquivar).

---

## Insights da Sessao

1. **Health Score recuperou** apos 2 quedas — sinal de auto-correcao do sistema (eficacia subiu sem intervencao explicita visivel).
2. **Bug latente: memorias `_archived_*` continuam sendo usadas** — investigar urgente (R2).
3. **structural/pessoal cresce 22 -> 144** mas com 80 stale 30d — categoria pode estar acumulando lixo.
4. **Talita (17) e novos usuarios** indicam expansao da base — bom sinal de adocao.
5. **Custo Gabriella desceu** (-21%) — possivel resposta indireta a investigacao recomendada no ciclo anterior.
6. **`user-xml-nao-atualiza-por-threshold-de-sessoes.xml` saiu da lista top 20** — sucesso silencioso ou redirecionamento de uso? Verificar.

---

## Checklist Pre-Commit

- [x] Todas as 7 queries executaram (Q1-Q7 OK)
- [x] Health score calculado (84/100)
- [x] Recomendacoes geradas (10: R1-R10)
- [x] Relatorio gerado
- [x] `historico.md` atualizado
