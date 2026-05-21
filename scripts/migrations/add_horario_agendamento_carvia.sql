-- Migration: campos de horario de agendamento (feature CarVia)
-- Data: 2026-05-21
-- Descricao:
--   Adiciona o horario do agendamento ao fluxo CarVia (o fluxo Nacom NAO usa horario):
--     carvia_cotacoes.horario_agenda   (TIME) — FONTE (cotacao comercial CarVia)
--     embarque_itens.hora_agendamento  (TIME) — RECEPTOR (propagado da cotacao; Nacom = NULL)
--   O destino final (agendamentos_entrega.hora_agendada) ja existe.
-- Idempotente (ADD COLUMN IF NOT EXISTS). Executar no Render Shell.

ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS horario_agenda TIME;
ALTER TABLE embarque_itens  ADD COLUMN IF NOT EXISTS hora_agendamento TIME;
