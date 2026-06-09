# A5 — Uso REAL de Skills em Producao

**Subagente**: A5 (missao: validar R-7 e R-3/R-4 do Rafael via dados de producao)
**Data**: 2026-06-09
**Banco**: `sistema-fretes-db` (dpg-d13m38vfte5s738t6p50-a, Render Oregon, Postgres 18)

---

## 1. Mecanismo de Rastreamento de Skills (como funciona no codigo)

### 1a. Ponto de gravacao: `routes/chat.py:922-940`

O campo `tools_used` (JSON array) de cada mensagem assistant e populado durante o stream SSE.
Quando o agente invoca `Skill`, o nome da skill e extraido do `tool_input`:

```python
# routes/chat.py:925-928
if tool_name == 'Skill' and isinstance(tool_input, dict):
    skill_name = tool_input.get('skill', '')
    if skill_name:
        enriched_name = f"Skill:{skill_name}"
```

O enriched name `Skill:<nome>` e adicionado ao `response_state['tools_used']` e persistido em dois lugares:
- `agent_sessions.data['messages'][i]['tools_used']` — JSONB dentro do campo data da sessao
- `agent_step.tools_used` — coluna JSON separada (tabela `agent_step`, existe desde 2026-05-31)

### 1b. Tabela `agent_step` (coluna `channel` disponivel)

Estrutura relevante:
- `session_id`, `user_id`, `channel` ('web' | 'teams'), `tools_used` (JSON array), `created_at`
- Existe desde: **2026-05-31** (apenas ~10 dias de historico no momento desta analise)
- 329 steps no total, 230 com tools_used array valido, 99 com JSON null

### 1c. Tabela `agent_skill_effectiveness` (avaliador pos-sessao)

Modelo: `app/agente/models.py:2411-2435`
Colunas: `skill_name`, `user_id`, `session_id`, `anchor_msg_id`, `stage_reached` (0/1/2), `resolveu`, `ramo`, `confidence`, `action_ref`, `evidencia_json`
Existe desde: **2026-06-07** (feature flag `AGENT_SKILL_EVAL`). Apenas **5 linhas** no banco.

**Conclusao sobre rastreamento**: A tabela `agent_skill_effectiveness` NAO e fonte para uso geral — ela avalia efetividade pos-sessao, nao conta invocacoes. A fonte primaria de contagem e `agent_sessions.data['messages']` (historico completo 90 dias) e `agent_step.tools_used` (apenas desde 31/05).

### 1d. Separacao de responsabilidades no mapeamento

`tool_skill_mapper.py` (383 LOC) faz mapeamento ANALITICO (Tool → Categoria → Dominio) para o dashboard de insights — NAO e a tabela de rastreamento. Mapeia `Skill:nome` para categoria legivel. NAO ha gravacao por canal individual de skill — canal esta na sessao/step, nao por invocacao de skill.

---

## 2. Queries Executadas e Resultados

### Query 1: Periodo coberto

```sql
-- agent_step
SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM agent_step;
-- Resultado: 2026-05-31 a 2026-06-09, 329 steps

-- agent_sessions (90 dias)
SELECT COUNT(*), MIN(created_at) FROM agent_sessions WHERE created_at >= NOW() - INTERVAL '90 days';
-- Resultado: 573 sessoes desde 2026-03-11
```

**Janela real de dados**: agent_step cobre apenas ~10 dias. agent_sessions cobre ~3 meses mas skills so existem no campo messages JSONB.

---

## 3. Ranking Completo de Skills (90 dias, fonte: agent_sessions.data messages)

Fonte primaria: query com `jsonb_array_elements` sobre `data->'messages'` em agent_sessions.
Periodo: 2026-03-11 a 2026-06-09 (90 dias retroativos).

| # | Skill | Invocacoes | Sessoes Distintas | Usuarios | Canais |
|---|-------|-----------|-------------------|----------|--------|
| 1 | exportando-arquivos | 58 | 53 | 7 | web, null/legado |
| 2 | gerando-baseline-conciliacao | 39 | 38 | 1 | web |
| 3 | lendo-arquivos | 28 | 24 | 9 | web, null/legado |
| 4 | conciliando-transferencias-internas | 21 | 15 | 3 | web, null/legado |
| 5 | gerindo-expedicao | 13 | 13 | 8 | web, teams, null/legado |
| 6 | rastreando-odoo | 11 | 11 | 6 | web |
| 7 | lendo-documentos | 10 | 9 | 3 | web |
| 8 | gerindo-carvia | 10 | 10 | 2 | web |
| 9 | cotando-frete | 9 | 9 | 3 | web |
| 10 | descobrindo-odoo-estrutura | 4 | 4 | 2 | web |
| 11 | gerando-artifact | 4 | 4 | 1 | web |
| 12 | consultando-quant-odoo | 4 | 4 | 3 | web |
| 13 | criar-separacao | 3 | 3 | 1 | web |
| 14 | consultar-estoque | 3 | 3 | 3 | web |
| 15 | monitorando-entregas | 3 | 3 | 2 | web |
| 16 | operando-portal-atacadao | 2 | 2 | 2 | web |
| 17 | resolvendo-entidades | 2 | 2 | 2 | web |
| 18 | transferindo-interno-odoo | 2 | 2 | 1 | web |
| 19 | verificar-disponibilidade | 2 | 2 | 1 | web |
| 20 | executando-odoo-financeiro | 2 | 2 | 2 | web, null/legado |
| 21 | operando-mo-odoo | 2 | 2 | 1 | web |
| 22 | consultando-sentry | 2 | 2 | 2 | web, null/legado |
| 23 | gerindo-agente | 1 | 1 | 1 | web |
| 24 | conferindo-recibo-assai | 1 | 1 | 1 | web |
| 25 | consultando-sql | 1 | 1 | 1 | web |
| 26 | acessando-ssw | 1 | 1 | 1 | web |
| 27 | operando-ssw | 1 | 1 | 1 | web |
| 28 | razao-geral-odoo | 1 | 1 | 1 | web |

**Total de invocacoes de skills rastreadas**: ~253
**Total de skills distintas invocadas**: 28 (de ~50+ no listing)

**Nota sobre "null/legado"**: canal=null em sessoes criadas antes de 2026-04-12 (quando o campo channel foi adicionado ao `get_or_create` — models.py:386). NAO e um canal especifico.

---

## 4. Por Canal (agent_step — 10 dias, mais preciso pois tem coluna channel)

Fonte: agent_step (coluna channel explicita, dados 2026-05-31 a 2026-06-09)
Todas as 17 skills observadas em agent_step foram no canal **web**.
Nenhuma skill foi invocada via **teams** nesse periodo.

Skills observadas em agent_step (10 dias):
lendo-arquivos(12), exportando-arquivos(11), rastreando-odoo(6), gerando-baseline-conciliacao(5), cotando-frete(5), gerindo-expedicao(4), gerindo-carvia(3), lendo-documentos(2), acessando-ssw(1), transferindo-interno-odoo(1), consultar-estoque(1), descobrindo-odoo-estrutura(1), executando-odoo-financeiro(1), gerindo-agente(1), operando-portal-atacadao(1), razao-geral-odoo(1), resolvendo-entidades(1)

**Achado**: gerindo-expedicao e a unica skill com uso confirmado em **teams** (via agent_sessions, canal=teams, 2 invocacoes, 1 usuario). As demais sao exclusivamente web.

---

## 5. Skills do R-3 (candidatas a dev-only): Uso Real

Questao do Rafael (R-7/R-3): "Web usa gerindo-agente, diagnosticando-banco, consultando-sentry?"

### gerindo-agente
- agent_sessions: **1 invocacao**, 1 sessao, user_id=38, data 2026-06-08, canal=web
- agent_step: **1 invocacao**, user_id=38, data 2026-06-08, canal=web, session_id=ac365bcb
- **Diagnostico**: uso EXTREMAMENTE baixo. Provavelmente o proprio admin (user 38) testando.

### diagnosticando-banco
- agent_sessions: **0 invocacoes** em 90 dias
- agent_step: **0 invocacoes** em 10 dias
- **Diagnostico**: NUNCA usada em producao no periodo. Candidata forte a remocao do listing.

### consultando-sentry
- agent_sessions: **2 invocacoes**, 2 sessoes distintas, 2 usuarios distintos (user_id=1 em 2026-03-27 e user_id=38 em 2026-05-22), canal=null/legado e web
- agent_step: **0 invocacoes** no periodo de 10 dias do agent_step
- **Diagnostico**: uso residual/isolado. Ultimo uso: 2026-05-22 (18 dias atras). Ambos os usuarios sao tecnicos/admins.

### padronizando-docs
- agent_sessions: **0 invocacoes** em 90 dias
- agent_step: **0 invocacoes** em 10 dias
- **Diagnostico**: NUNCA usada em producao no periodo. Candidata forte a remocao do listing.

**Conclusao R-3/R-7**: A suspeita do Rafael e CONFIRMADA por dados. Das 4 skills apontadas:
- diagnosticando-banco: zero uso
- padronizando-docs: zero uso
- gerindo-agente: 1 invocacao (admin testando)
- consultando-sentry: 2 invocacoes em 90 dias (usuarios tecnicos, ultima ha 18 dias)

Nenhuma dessas skills tem uso real por usuarios finais. Todas sao perfil dev/admin.

---

## 6. lendo-arquivos vs lendo-documentos (R-4)

### lendo-arquivos
- 90 dias: **28 invocacoes**, 24 sessoes distintas, 9 usuarios distintos, canal=web+null/legado
- Periodo de uso: 2026-06-01 a 2026-06-05 (agent_step)
- Status: **skill ativa e frequentemente usada**

### lendo-documentos
- 90 dias: **10 invocacoes**, 9 sessoes distintas, 3 usuarios distintos, canal=web
- Periodo: 2026-06-02 (agent_step: 2 invocacoes, 1 sessao, 1 usuario)
- Status: **skill usada, mas com volume 2.8x menor**

**Ratio lendo-arquivos:lendo-documentos = 28:10 (2.8:1)**

Ambas ativas, mas lendo-arquivos e dominante. A unificacao proposta pelo Rafael (R-4) e tecnicamente viavel — o volume sugere que ha demanda real para ambas as funcionalidades, porem com concentracao em lendo-arquivos. Unificar reduz overhead do listing sem perder funcionalidade.

---

## 7. Skills Presentes no Listing mas com ZERO uso em 90 dias

Estas skills estao no listing do agente principal (NAO na deny-list `SKILLS_DELEGADAS_SUBAGENTE`)
e nao aparecem em nenhuma invocacao nos 90 dias:

- diagnosticando-banco
- padronizando-docs
- analise-carteira (subskill — pode ser invocada internamente)
- comunicar-comercial (subskill)
- comunicar-pcp (subskill)
- fp-lojas-motochefe (subskill)
- prd-generator
- ralph-wiggum
- skill-creator
- resolvendo-problemas
- integracao-odoo
- conciliando-odoo-po
- validacao-nf-po
- recebimento-fisico-odoo
- rastreando-chassi (removida da deny-list? — aparece na SKILLS_DOMINIO_HORA)
- ajustando-quant-odoo (na deny-list — mas apareceu via subagente, NAO no principal)

**Nota metodologica**: "zero uso" nao significa "inutil" — skills como ralph-wiggum, prd-generator e skill-creator sao ferramentas de desenvolvimento que podem ser solicitadas esporadicamente. Ja diagnosticando-banco e padronizando-docs sao explicitamente dev-only.

---

## 8. Estado de agent_skill_effectiveness (5 linhas)

| skill_name | user_id | resolveu | ramo | confidence | stage_reached | data |
|-----------|---------|---------|------|-----------|---------------|------|
| rastreando-odoo | 17 | true | null | null | 1 | 2026-06-08 |
| gerindo-carvia | 17 | true | null | null | 0 | 2026-06-08 |
| exportando-arquivos | 1 | true | null | null | 1 | 2026-06-09 |
| gerindo-expedicao | 17 | false | ajuste_codigo | 0.93 | 2 | 2026-06-09 |
| razao-geral-odoo | 18 | true | null | null | 1 | 2026-06-09 |

Feature EM PROD desde 2026-06-07. Primeiro achado concreto: `gerindo-expedicao` foi avaliada como `resolveu=false`, ramo=`ajuste_codigo`, confianca=0.93 — indicando que o avaliador pos-sessao detectou que a skill nao resolveu o problema do user 17 (Rafael, provavelmente) e gerou um item de melhoria em `agent_improvement_dialogue`.

---

## 9. Lacunas Metodologicas

1. **agent_step existe apenas desde 2026-05-31** — historico de ~10 dias, insuficiente para analise robusta de canal (web vs teams). Para analise de canal, recomenda-se aguardar 30+ dias.

2. **Canal null = legado, NAO teams** — sessoes criadas antes de 2026-04-12 nao tem canal registrado. Nao e possivel saber se eram web ou teams.

3. **Teams com skills**: agent_sessions mostra gerindo-expedicao com canal=teams (2 invocacoes), mas agent_step (periodo mais recente) nao confirma. Volume de skills via teams e muito baixo ou zero no periodo recente.

4. **Skills invocadas por subagentes**: quando o agente principal delega ao `gestor-estoque-odoo` e o subagente invoca `ajustando-quant-odoo`, essa invocacao provavelmente NAO aparece em `agent_step.tools_used` do principal (o step e do subagente). Isso significa que skills da deny-list podem ter uso real nao capturado nesta analise.

5. **Cobertura temporal**: agent_sessions cobre 90 dias, mas o campo `channel` so existe a partir de 2026-04-12. Skills usadas antes dessa data aparecem com canal=null.
