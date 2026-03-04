-- ============================================================
-- Memory System v2 — Recategorização de memórias
-- Gerado automaticamente pela revisão de 7 Sonnets
-- Total: 61 updates
-- ============================================================

BEGIN;

-- cat=permanent, perm=True, score=0.95 (12 memórias)
UPDATE agent_memories SET category = 'permanent', is_permanent = true, importance_score = 0.95, is_cold = false
WHERE id IN (50, 51, 53, 54, 57, 59, 62, 63, 65, 67, 70, 73);

-- cat=permanent, perm=True, score=0.8 (11 memórias)
UPDATE agent_memories SET category = 'permanent', is_permanent = true, importance_score = 0.8, is_cold = false
WHERE id IN (35, 40, 74, 77, 83, 85, 87, 90, 91, 94, 96);

-- cat=permanent, perm=True, score=0.85 (8 memórias)
UPDATE agent_memories SET category = 'permanent', is_permanent = true, importance_score = 0.85, is_cold = false
WHERE id IN (5, 75, 76, 78, 79, 82, 92, 93);

-- cat=permanent, perm=True, score=0.75 (6 memórias)
UPDATE agent_memories SET category = 'permanent', is_permanent = true, importance_score = 0.75, is_cold = false
WHERE id IN (28, 86, 88, 89, 95, 97);

-- cat=structural, perm=False, score=0.85 (3 memórias)
UPDATE agent_memories SET category = 'structural', is_permanent = false, importance_score = 0.85, is_cold = false
WHERE id IN (10, 46, 49);

-- cat=structural, perm=False, score=0.6 (2 memórias)
UPDATE agent_memories SET category = 'structural', is_permanent = false, importance_score = 0.6, is_cold = false
WHERE id IN (9, 24);

-- cat=operational, perm=False, score=0.75 (2 memórias)
UPDATE agent_memories SET category = 'operational', is_permanent = false, importance_score = 0.75, is_cold = false
WHERE id IN (11, 25);

-- cat=operational, perm=False, score=0.4, cold=True (2 memórias)
UPDATE agent_memories SET category = 'operational', is_permanent = false, importance_score = 0.4, is_cold = true
WHERE id IN (7, 16);

-- cat=contextual, perm=False, score=0.2, cold=True (2 memórias)
UPDATE agent_memories SET category = 'contextual', is_permanent = false, importance_score = 0.2, is_cold = true
WHERE id IN (38, 44);

-- cat=structural, perm=False, score=0.7 (2 memórias)
UPDATE agent_memories SET category = 'structural', is_permanent = false, importance_score = 0.7, is_cold = false
WHERE id IN (14, 17);

-- cat=permanent, perm=True, score=0.88 (2 memórias)
UPDATE agent_memories SET category = 'permanent', is_permanent = true, importance_score = 0.88, is_cold = false
WHERE id IN (80, 81);

-- cat=contextual, perm=False, score=0.3, cold=True (1 memórias)
UPDATE agent_memories SET category = 'contextual', is_permanent = false, importance_score = 0.3, is_cold = true
WHERE id IN (41);

-- cat=structural, perm=False, score=0.75 (1 memórias)
UPDATE agent_memories SET category = 'structural', is_permanent = false, importance_score = 0.75, is_cold = false
WHERE id IN (37);

-- cat=operational, perm=False, score=0.55 (1 memórias)
UPDATE agent_memories SET category = 'operational', is_permanent = false, importance_score = 0.55, is_cold = false
WHERE id IN (99);

-- cat=contextual, perm=False, score=0.35, cold=True (1 memórias)
UPDATE agent_memories SET category = 'contextual', is_permanent = false, importance_score = 0.35, is_cold = true
WHERE id IN (39);

-- cat=operational, perm=False, score=0.35, cold=True (1 memórias)
UPDATE agent_memories SET category = 'operational', is_permanent = false, importance_score = 0.35, is_cold = true
WHERE id IN (34);

-- cat=contextual, perm=False, score=0.1, cold=True (1 memórias)
UPDATE agent_memories SET category = 'contextual', is_permanent = false, importance_score = 0.1, is_cold = true
WHERE id IN (20);

-- cat=structural, perm=False, score=0.78 (1 memórias)
UPDATE agent_memories SET category = 'structural', is_permanent = false, importance_score = 0.78, is_cold = false
WHERE id IN (22);

-- cat=structural, perm=False, score=0.65 (1 memórias)
UPDATE agent_memories SET category = 'structural', is_permanent = false, importance_score = 0.65, is_cold = false
WHERE id IN (31);

-- cat=permanent, perm=True, score=0.82 (1 memórias)
UPDATE agent_memories SET category = 'permanent', is_permanent = true, importance_score = 0.82, is_cold = false
WHERE id IN (84);

COMMIT;

-- ============================================================
-- Verificação pós-update
-- ============================================================
-- SELECT category, is_permanent, count(*), avg(importance_score)::numeric(3,2)
-- FROM agent_memories WHERE NOT is_directory
-- GROUP BY category, is_permanent ORDER BY category;