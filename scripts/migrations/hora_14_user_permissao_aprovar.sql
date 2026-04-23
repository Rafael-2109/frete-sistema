-- Migration HORA 14: pode_aprovar em hora_user_permissao.
--
-- NOTA: hora_13 ja foi atualizada para incluir pode_aprovar no CREATE TABLE
-- e tem ALTER ... ADD COLUMN IF NOT EXISTS para tabelas legadas.
-- Este arquivo permanece como no-op idempotente para nao quebrar deploys que
-- ja registraram hora_14 na sequencia. Pode ser removido apos confirmacao
-- de que todas as instancias rodaram hora_13 atualizada.

ALTER TABLE hora_user_permissao
    ADD COLUMN IF NOT EXISTS pode_aprovar BOOLEAN NOT NULL DEFAULT FALSE;
