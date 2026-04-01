-- Data fix: Persistir as 4 decisoes do D8 (2026-04-01) que falharam por CSRF
-- As 4 sugestoes v1 (agent_sdk) existem mas as respostas v2 (claude_code) nao foram salvas.
--
-- Executar via Render Shell:
--   psql $DATABASE_URL -f fix_d8_persist_decisions_2026_04_01.sql

BEGIN;

-- IMP-001: PROPOSTA (gotcha critical — requer arquivos protegidos)
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity, title,
    description, implementation_notes, affected_files, auto_implemented
) VALUES (
    'IMP-2026-04-01-001', 2, 'claude_code', 'responded', 'gotcha_report', 'critical',
    'Agente retornando erro generico em todas as mensagens — sessao completamente quebrada',
    'Gap real confirmado: sem deteccao cross-turn de erros repetidos. Plano proposto em 4 pontos: (1) circuit breaker em client.py, (2) error pattern tracker em services, (3) alerta ao usuario apos 2+ erros consecutivos, (4) log estruturado para diagnostico.',
    'Requer modificacao de arquivos protegidos (client.py, routes.py, services.py). Proposta para revisao humana.',
    ARRAY['app/agente/sdk/client.py', 'app/agente/routes.py', 'app/agente/services/'],
    false
) ON CONFLICT (suggestion_key, version) DO NOTHING;

-- IMP-002: REJEITADO (skill duplicata — raio-x-pedido ja existe)
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity, title,
    description, implementation_notes, affected_files, auto_implemented
) VALUES (
    'IMP-2026-04-01-002', 2, 'claude_code', 'rejected', 'skill_suggestion', 'critical',
    'Criar skill para consulta rapida de pedido por codigo (posicao, separacao, embarque)',
    'Subagente raio-x-pedido (.claude/agents/raio-x-pedido.md) ja cobre 100% desta funcionalidade: consolidacao de posicao, separacao, embarque e frete por pedido.',
    'Nenhuma acao necessaria. Funcionalidade ja existe como subagente.',
    ARRAY[]::text[],
    false
) ON CONFLICT (suggestion_key, version) DO NOTHING;

-- IMP-003: REJEITADO (skill duplicata — conciliando-transferencias-internas ja existe)
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity, title,
    description, implementation_notes, affected_files, auto_implemented
) VALUES (
    'IMP-2026-04-01-003', 2, 'claude_code', 'rejected', 'skill_suggestion', 'warning',
    'Criar skill para conciliacao de transferencias internas entre bancos no Odoo',
    'Skill conciliando-transferencias-internas (.claude/skills/conciliando-transferencias-internas/) ja existe com suporte a intervalos de datas e reconciliacao automatica.',
    'Nenhuma acao necessaria. Funcionalidade ja existe como skill.',
    ARRAY[]::text[],
    false
) ON CONFLICT (suggestion_key, version) DO NOTHING;

-- IMP-004: IMPLEMENTADO (regra R8 no system_prompt.md)
INSERT INTO agent_improvement_dialogue (
    suggestion_key, version, author, status, category, severity, title,
    description, implementation_notes, affected_files, auto_implemented
) VALUES (
    'IMP-2026-04-01-004', 2, 'claude_code', 'responded', 'instruction_request', 'warning',
    'Instruir agente a detectar multiplas datas em solicitacoes repetitivas e processar em lote',
    'Regra R8 (Deteccao de Padroes Repetitivos) adicionada ao system_prompt.md. Agente detecta 2+ solicitacoes similares e oferece processar lote completo.',
    'Implementado em app/agente/prompts/system_prompt.md linhas 172-179. Regra R8 com exemplo concreto de conciliacoes por data.',
    ARRAY['app/agente/prompts/system_prompt.md'],
    true
) ON CONFLICT (suggestion_key, version) DO NOTHING;

COMMIT;

-- Verificacao
SELECT suggestion_key, version, author, status, auto_implemented
FROM agent_improvement_dialogue
ORDER BY id;
