-- Migration: indice GIN para consultas agregadas em subagent_costs
-- Data: 2026-04-16
-- Spec: docs/superpowers/specs/2026-04-16-agent-sdk-0160-features-design.md #3

CREATE INDEX IF NOT EXISTS idx_agent_sessions_subagent_costs
ON agent_sessions USING GIN ((data -> 'subagent_costs'));

COMMENT ON INDEX idx_agent_sessions_subagent_costs IS
'Suporta queries agregadas "top subagentes por custo no mes" via jsonb_array_elements(data->subagent_costs->entries)';
