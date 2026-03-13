-- Migration: Popular modelos de moto na tabela carvia_modelos_moto
-- Data: 2026-03-13
-- Descricao: Insere 18 modelos de moto com dimensoes (cm) e regex auto-gerado
-- Idempotente via ON CONFLICT

INSERT INTO carvia_modelos_moto (nome, comprimento, largura, altura, regex_pattern, cubagem_minima, ativo, criado_em, criado_por)
VALUES
  ('PATINETE',    118, 25, 48, '(?i)patinete',        300, true, NOW(), 'sistema'),
  ('MCQ3',        130, 37, 64, '(?i)mcq3',            300, true, NOW(), 'sistema'),
  ('JOY SUPER',   131, 34, 71, '(?i)joy[\s\-]*super', 300, true, NOW(), 'sistema'),
  ('X12-10',      147, 37, 63, '(?i)x12[\s\-]*10',    300, true, NOW(), 'sistema'),
  ('X11 MINI',    141, 39, 65, '(?i)x11[\s\-]*mini',  300, true, NOW(), 'sistema'),
  ('BOB',         144, 33, 76, '(?i)bob',             300, true, NOW(), 'sistema'),
  ('RET',         170, 32, 87, '(?i)ret',             300, true, NOW(), 'sistema'),
  ('SOMA',        154, 42, 78, '(?i)soma',            300, true, NOW(), 'sistema'),
  ('DOT',         158, 45, 80, '(?i)dot',             300, true, NOW(), 'sistema'),
  ('GIGA',        158, 45, 80, '(?i)giga',            300, true, NOW(), 'sistema'),
  ('SOFIA',       158, 45, 80, '(?i)sofia',           300, true, NOW(), 'sistema'),
  ('JET',         168, 42, 84, '(?i)jet',             300, true, NOW(), 'sistema'),
  ('X15',         167, 56, 64, '(?i)x15',             300, true, NOW(), 'sistema'),
  ('S8',          180, 43, 78, '(?i)s8',              300, true, NOW(), 'sistema'),
  ('BIG TRI',     137, 76, 61, '(?i)big[\s\-]*tri',   300, true, NOW(), 'sistema'),
  ('VED',         142, 72, 83, '(?i)ved',             300, true, NOW(), 'sistema'),
  ('MIA TRI',     154, 71, 83, '(?i)mia[\s\-]*tri',   300, true, NOW(), 'sistema'),
  ('POP',         141, 26, 85, '(?i)pop',             300, true, NOW(), 'sistema')
ON CONFLICT (nome) DO UPDATE SET
  comprimento = EXCLUDED.comprimento,
  largura = EXCLUDED.largura,
  altura = EXCLUDED.altura,
  regex_pattern = EXCLUDED.regex_pattern;
