-- Migration HORA 59: vinculo HoraAvaria -> conferencia de recebimento.
-- Adiciona hora_avaria.recebimento_conferencia_id (FK opcional) para vincular a
-- avaria criada no recebimento (regra avaria=NAO-vendavel, 2026-06-28) a
-- conferencia que a originou. Espelha hora_peca_faltando.recebimento_conferencia_id.
-- Permite: (1) excluir_recebimento limpar a avaria daquele recebimento;
-- (2) desmarcar avaria na reconferencia resolver SO a avaria daquela conferencia.
-- Idempotente — pode rodar 2x (IF NOT EXISTS).

ALTER TABLE hora_avaria
    ADD COLUMN IF NOT EXISTS recebimento_conferencia_id INTEGER
    REFERENCES hora_recebimento_conferencia (id);

CREATE INDEX IF NOT EXISTS ix_hora_avaria_rec_conf
    ON hora_avaria (recebimento_conferencia_id);
