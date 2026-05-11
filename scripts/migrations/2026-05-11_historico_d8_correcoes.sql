-- =====================================================================
-- HISTORICO D8 — Correcoes 2026-05-11
-- =====================================================================
-- Insere/atualiza 5 entradas no agent_improvement_dialogue:
--
-- 1. IMP-2026-05-11-002 v3 — CORRECAO: a deducao da v1 (D8 batch 04:01 BRT)
--    estava errada. JSONLs de 6 linhas/turns=0 NAO eram padrao normal;
--    eram fallback filesystem do CLI causado por bug no agent_loader.py
--    (commit 8d2d28f1 corrigiu).
--
-- 2. IMP-2026-05-11-004 v1 — max_turns=30 hardcoded no client.py cortava
--    respostas longas (Sentry PYTHON-FLASK-H, 46 events). Removido em
--    2026-05-11 (default Optional[int]=None).
--
-- 3. IMP-2026-05-11-005 v1 — additionalProperties=true no schema do
--    session_summarizer quebrava structured outputs (Sentry PYTHON-FLASK-A0,
--    62 events). Trocado para false em 2026-05-11.
--
-- 4. IMP-2026-05-11-006 v1 — text_to_sql_tool passava UUID para campos
--    bigint (Sentry PYTHON-FLASK-M, 32 events). Adicionada deteccao
--    pre-execucao em 2026-05-11.
--
-- 5. IMP-2026-05-11-007 v1 — REQUEST_TIMEOUT=10s em render_logs_tool.py
--    estourava com horas=24, agente reportava "nao tenho acesso ao MCP
--    Render". Aumentado para 30s em 2026-05-11.
--
-- IDEMPOTENTE: ON CONFLICT (suggestion_key, version) DO UPDATE.
-- =====================================================================

BEGIN;

-- 1) IMP-002 v3: correcao da deducao
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity,
    title, description, evidence_json, affected_files,
    implementation_notes, auto_implemented, source_session_ids,
    created_at, updated_at
)
VALUES (
    'IMP-2026-05-11-002', 3, 'claude_code', 'responded', 'gotcha_report', 'critical',
    'CORRECAO: JSONLs 6 linhas/turns=0 ERAM bug de loader, NAO padrao normal',
    'A v1 (agent_sdk batch das 07:01 UTC) deduziu erroneamente que JSONLs de 6 linhas + turns=0 + cost granular SKIP eram "padrao normal para subagentes sem ferramentas". Investigacao real ja havia descoberto e corrigido o bug 39 minutos antes do batch D8: o commit 8d2d28f1 (Rafael, 11/05 00:52 BRT) corrigiu agent_loader.py que fazia .strip() em max_turns int (de yaml.safe_load). O AttributeError silenciava o load de 7 agents Opus heavy (gestor-recebimento, especialista-odoo, analista-carteira, auditor-financeiro, raio-x-pedido, gestor-motos-assai, desenvolvedor-integracao-odoo). Sem o agent no dict do ClaudeAgentOptions, o CLI bundled caia em fallback filesystem com spawn parcial que abortava em ~3s. Resultado: 18 SKIPs em 7 dias — eliminados pelo fix. A v2 do claude_code (que documentou em SUBAGENT_RELIABILITY.md como "padrao normal") foi atualizada nesta v3 com a causa correta.',
    '{"commit_fix": "8d2d28f1", "commit_date": "2026-05-11T00:52:36-03:00", "agents_descartados": 7, "agents_list": ["gestor-recebimento", "especialista-odoo", "analista-carteira", "auditor-financeiro", "raio-x-pedido", "gestor-motos-assai", "desenvolvedor-integracao-odoo"], "skips_eliminados_em_7d": 18, "session_referencia": "3cc9b481-a63c-44c3-821a-a2da8c6b56a9", "codigo_antigo": "int(max_turns_str) if max_turns_str and max_turns_str.strip().isdigit() else None", "codigo_novo": "isinstance(max_turns_raw, int) ou isinstance(str) + strip", "linhas_codigo": "app/agente/config/agent_loader.py:382-393", "deducao_d8_errada": true, "tempo_entre_fix_e_d8": "189 minutos (fix 00:52, batch 04:01)", "licao": "D8 nao tem visibilidade de commits ocorridos no intervalo entre as sessoes que ele resume e a execucao do batch."}'::jsonb,
    ARRAY['app/agente/config/agent_loader.py', '.claude/references/SUBAGENT_RELIABILITY.md'],
    'Atualizado: .claude/references/SUBAGENT_RELIABILITY.md — adicionada secao "Caso 2026-05-11 — JSONL 6 linhas / turns=0: ERA bug de loader (NAO padrao normal)" com causa, cascade da falha, fix e licao para investigacoes futuras. A secao anterior "Observabilidade — Padroes Normais" da v2 mencionada no implementation_notes original NAO foi aplicada por engano historico.',
    true,
    ARRAY['3cc9b481-a63c-44c3-821a-a2da8c6b56a9'],
    NOW(), NOW()
)
ON CONFLICT (suggestion_key, version) DO UPDATE SET
    author = EXCLUDED.author,
    status = EXCLUDED.status,
    severity = EXCLUDED.severity,
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    evidence_json = EXCLUDED.evidence_json,
    affected_files = EXCLUDED.affected_files,
    implementation_notes = EXCLUDED.implementation_notes,
    auto_implemented = EXCLUDED.auto_implemented,
    source_session_ids = EXCLUDED.source_session_ids,
    updated_at = NOW();


-- 2) IMP-004 v1: max_turns=30 cortava respostas
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity,
    title, description, evidence_json, affected_files,
    implementation_notes, auto_implemented, source_session_ids,
    created_at, updated_at
)
VALUES (
    'IMP-2026-05-11-004', 1, 'claude_code', 'responded', 'gotcha_report', 'critical',
    'Agente principal cortado por max_turns=30 hardcoded; UI ficava presa ate READ_TIMEOUT_MS=60s',
    'Default max_turns=30 em client.py:1309 cortava respostas longas com cadeias tool_use extensas. SDK emitia ResultMessage com stop_reason=tool_use + errors=[Reached maximum number of turns (30)] (cobrindo Sentry PYTHON-FLASK-H "Fatal error in message reader: exit code 1" com 46 events; SDK 0.1.77 troca msg generica por mensagem real). Frontend (chat.js:938) com READ_TIMEOUT_MS=60000 ficava esperando chunks ate desistir — sintoma: thinking block some, botao volta a "Enviar" sem resposta visivel. Observado em sessoes 555 (2954ae95) e 556 (93ccedf9) hoje, custo combinado $27.90, 16 mensagens, ~10.7M tokens. Diagnosticado pelo claude_code apos analise dos logs Render 11:30-12:13 UTC.',
    '{"stop_reason_observado": "tool_use", "erro_real": "Reached maximum number of turns (30)", "sentry_issue": "PYTHON-FLASK-H", "sentry_events": 46, "sentry_first_seen": "2026-03-10", "sessoes_afetadas": ["2954ae95-8d29-4319-89ec-21d55b21868a", "93ccedf9-f761-402d-925a-156cb55cd12a"], "custo_sessoes_2026-05-11": 27.90, "tokens_combinados": 10739240, "frontend_timeout_ms": 60000, "antes": "max_turns: int = 30", "depois": "max_turns: Optional[int] = None"}'::jsonb,
    ARRAY['app/agente/sdk/client.py'],
    'Mudanca: app/agente/sdk/client.py:1309 — max_turns: int = 30 -> Optional[int] = None. options_dict:1367 — remocao da chave hardcoded; injecao condicional apos fechamento do dict (linha 1428): if max_turns is not None: options_dict["max_turns"] = max_turns. Pattern identico a agent_loader.py:434 (subagentes). Quem quiser cap defensivo passa explicito. Validado: assinatura ok, hardcoded removido, guard presente, docstring atualizada.',
    true,
    ARRAY['2954ae95-8d29-4319-89ec-21d55b21868a', '93ccedf9-f761-402d-925a-156cb55cd12a'],
    NOW(), NOW()
)
ON CONFLICT (suggestion_key, version) DO UPDATE SET
    description = EXCLUDED.description,
    evidence_json = EXCLUDED.evidence_json,
    implementation_notes = EXCLUDED.implementation_notes,
    updated_at = NOW();


-- 3) IMP-005 v1: additionalProperties: true quebra structured outputs
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity,
    title, description, evidence_json, affected_files,
    implementation_notes, auto_implemented, source_session_ids,
    created_at, updated_at
)
VALUES (
    'IMP-2026-05-11-005', 1, 'claude_code', 'responded', 'skill_bug', 'warning',
    'session_summarizer: additionalProperties=true rejeitado pela API Anthropic (62 events Sentry desde 2026-03-27)',
    'O schema SUMMARY_OUTPUT_SCHEMA em app/agente/services/session_summarizer.py declarava additionalProperties: True em 3 niveis (raiz, perfil_signals, pedidos_mencionados.items). A API Anthropic structured outputs (output_config.format.schema) so aceita additionalProperties: false ou ausencia explicita do campo, retornando 400 com mensagem "For object type, additionalProperties: true is not supported". Sentry PYTHON-FLASK-A0 registrou 62 events desde 2026-03-27 — nenhum resumo de sessao gerado pelo Sonnet via API ate hoje. Sumarizacao retornava None silenciosamente. Semanticamente true permitia o LLM inventar campos extras nao usados pelo pattern_analyzer downstream — ruido sem leitor.',
    '{"sentry_issue": "PYTHON-FLASK-A0", "sentry_events": 62, "sentry_first_seen": "2026-03-27", "sentry_last_seen": "2026-05-11", "campos_corrigidos": 3, "campos_localizacao": ["raiz", "perfil_signals", "pedidos_mencionados.items"], "consumidor_downstream": "pattern_analyzer", "ja_documentado_em_services_CLAUDE_md": "Sim, secao R3 Truncamento; secao R5 Prompt caching", "impacto_funcional": "session_summarizer:_save_messages_to_db falhava silenciosamente, AgentSession.summary nunca era populado pelo Sonnet"}'::jsonb,
    ARRAY['app/agente/services/session_summarizer.py'],
    'Mudanca: app/agente/services/session_summarizer.py linhas 45, 57, 67 — todos os additionalProperties: True -> False. Comentario adicionado no schema raiz citando o bug historico (62 events Sentry) e justificando semanticamente: o schema declara todos os campos uteis ao pattern_analyzer; campos extras seriam ruido. Validado: zero ocorrencias de "additionalProperties: True" no arquivo apos mudanca.',
    true,
    NULL,
    NOW(), NOW()
)
ON CONFLICT (suggestion_key, version) DO UPDATE SET
    description = EXCLUDED.description,
    evidence_json = EXCLUDED.evidence_json,
    implementation_notes = EXCLUDED.implementation_notes,
    updated_at = NOW();


-- 4) IMP-006 v1: UUID em campo bigint na consultar_sql
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity,
    title, description, evidence_json, affected_files,
    implementation_notes, auto_implemented, source_session_ids,
    created_at, updated_at
)
VALUES (
    'IMP-2026-05-11-006', 1, 'claude_code', 'responded', 'skill_bug', 'warning',
    'consultar_sql: UUID em campo bigint quebrava com InvalidTextRepresentation (32 events Sentry)',
    'Pipeline text_to_sql.py gerava SQL com WHERE coluna = UUID-string em campos declarados bigint/integer no schema (ex: ultima sessao -> WHERE id = "2954ae95-..."). Postgres abortava com InvalidTextRepresentation "invalid input syntax for type bigint" — mensagem ininteligivel para o operador. Sentry PYTHON-FLASK-M registrou 32 events desde 2026-03-10. O Evaluator (Haiku) frequentemente nao capturava o type mismatch porque o esquema era valido sintaticamente. Sanitizacao existente em _sanitize_type_mismatches() so cobria padroes WHERE campo = "X" OR campo = X (defensivo do LLM), nao o caso UUID-em-bigint.',
    '{"sentry_issue": "PYTHON-FLASK-M", "sentry_events": 32, "sentry_first_seen": "2026-03-10", "exemplo_query_quebrada": "SELECT * FROM agent_sessions WHERE id = ''2954ae95-8d29-4319-89ec-21d55b21868a''", "tipo_campo_esperado": "bigint/integer/numeric/etc", "etapa_pipeline_adicionada": "2c (apos _sanitize_type_mismatches, antes do safety validator)", "tipos_cobertos": ["bigint", "integer", "smallint", "int4", "int8", "int2", "numeric", "decimal", "real", "double", "float", "money", "serial", "bigserial", "smallserial"], "operadores_cobertos": ["=", "<>", "!=", "<", ">", "<=", ">=", "LIKE", "ILIKE"]}'::jsonb,
    ARRAY['.claude/skills/consultando-sql/scripts/text_to_sql.py'],
    'Mudanca: text_to_sql.py — adicionada funcao _detect_uuid_in_numeric_field(sql, schema_provider, tables_in_sql) (linhas ~935-1049). Chamada como ETAPA 2c no TextToSQLPipeline.run() (linha ~1219), apos _sanitize_type_mismatches e antes do safety validator. Quando detecta UUID em campo numerico, retorna sucesso=False com aviso claro em PT-BR sugerindo o campo textual correto (ex: session_id em vez de id). Testes manuais: 6/6 casos passaram (bug real, varchar OK, numero em int OK, table.field qualificado, sem schema, LIKE).',
    true,
    NULL,
    NOW(), NOW()
)
ON CONFLICT (suggestion_key, version) DO UPDATE SET
    description = EXCLUDED.description,
    evidence_json = EXCLUDED.evidence_json,
    implementation_notes = EXCLUDED.implementation_notes,
    updated_at = NOW();


-- 5) IMP-007 v1: timeout MCP Render render_logs_tool
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity,
    title, description, evidence_json, affected_files,
    implementation_notes, auto_implemented, source_session_ids,
    created_at, updated_at
)
VALUES (
    'IMP-2026-05-11-007', 1, 'claude_code', 'responded', 'gotcha_report', 'warning',
    'MCP render_logs_tool: REQUEST_TIMEOUT=10s estourava em buscas amplas; agente reportava "nao tem MCP Render"',
    'app/agente/tools/render_logs_tool.py:36 declarava REQUEST_TIMEOUT=10. Quando agente buscava logs amplos (horas=24, limite=100), a API Render demorava >10s, levantava requests.exceptions.Timeout e a tool retornava "Timeout ao buscar logs (>10s)". Hook PostToolUseFailure registrava "mcp__render__consultar_logs falhou". Agente, em sessao 554 (3cc9b481), confundiu o timeout pontual da tool com falta de acesso ao MCP Render como um todo — afirmou "RENDER_API_KEY nao exposta no env do processo". Mensagem confusa: a env var de fato nao esta exposta para Bash direto do agente, mas o MCP Render funciona perfeitamente (usa env do processo Gunicorn). Em sessao 556, agente usou mcp__render__consultar_logs com sucesso 4 vezes — confirmando que MCP funciona. O timeout era so limitante de janela.',
    '{"valor_anterior": "10s", "valor_novo": "30s", "claude_code_stream_close_timeout": "240s (acomoda)", "sessoes_afetadas": ["3cc9b481-a63c-44c3-821a-a2da8c6b56a9", "93ccedf9-f761-402d-925a-156cb55cd12a"], "hook_signal": "[HOOK:PostToolUseFailure] mcp__render__consultar_logs falhou", "agente_dedusao_errada": "afirmou ausencia de MCP Render baseado em timeout pontual", "padrao_observado": "agente nao distinguiu timeout de tool vs ausencia de tool"}'::jsonb,
    ARRAY['app/agente/tools/render_logs_tool.py'],
    'Mudanca: app/agente/tools/render_logs_tool.py:36 — REQUEST_TIMEOUT = 10 -> 30. Comentario adicionado citando o bug. Mensagem de erro :166 atualizada para "(>30s)". Outros 3 callsites internos (_fetch_service_status etc.) tambem usam REQUEST_TIMEOUT — beneficiam-se automaticamente. Validado: timeout 30s presente, mensagem coerente.',
    true,
    ARRAY['3cc9b481-a63c-44c3-821a-a2da8c6b56a9', '93ccedf9-f761-402d-925a-156cb55cd12a'],
    NOW(), NOW()
)
ON CONFLICT (suggestion_key, version) DO UPDATE SET
    description = EXCLUDED.description,
    evidence_json = EXCLUDED.evidence_json,
    implementation_notes = EXCLUDED.implementation_notes,
    updated_at = NOW();


-- Verificacao: deve retornar 5 entradas
SELECT suggestion_key, version, author, severity, title
FROM agent_improvement_dialogue
WHERE suggestion_key IN (
    'IMP-2026-05-11-002', 'IMP-2026-05-11-004', 'IMP-2026-05-11-005',
    'IMP-2026-05-11-006', 'IMP-2026-05-11-007'
)
  AND (suggestion_key != 'IMP-2026-05-11-002' OR version = 3)
ORDER BY suggestion_key, version;

COMMIT;
