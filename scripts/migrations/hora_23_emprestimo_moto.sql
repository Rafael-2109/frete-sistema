-- hora_23: Empréstimo de moto entre nossa loja HORA e loja externa.
--
-- Cenarios:
--   SAIDA   = nossa loja HORA empresta moto para externa (chassi sai do
--             estoque). Ressarcimento entra com OUTRA moto (mesmo modelo).
--   ENTRADA = externa empresta moto para nossa loja HORA (chassi entra no
--             estoque). Ressarcimento sai com OUTRA moto (mesmo modelo).
--
-- Idempotente para Render Shell.

CREATE TABLE IF NOT EXISTS hora_emprestimo_moto (
  id                       SERIAL PRIMARY KEY,

  tipo                     VARCHAR(10) NOT NULL,
  status                   VARCHAR(15) NOT NULL DEFAULT 'EM_ABERTO',

  loja_hora_id             INTEGER NOT NULL,
  loja_externa_nome        VARCHAR(200) NOT NULL,
  loja_externa_cnpj        VARCHAR(20),

  modelo_id                INTEGER NOT NULL,

  -- chassi_saida = chassi que sai do nosso estoque (em SAIDA: o emprestado;
  -- em ENTRADA: o que enviamos no ressarcimento).
  chassi_saida             VARCHAR(30),
  -- chassi_entrada = chassi que entra no nosso estoque (em SAIDA: o
  -- ressarcimento; em ENTRADA: o emprestado).
  chassi_entrada           VARCHAR(30),

  data_emprestimo          DATE NOT NULL,
  data_ressarcimento       DATE,

  observacoes              TEXT,

  criado_em                TIMESTAMP NOT NULL DEFAULT now(),
  criado_por               VARCHAR(100),
  atualizado_em            TIMESTAMP,

  ressarcido_em            TIMESTAMP,
  ressarcido_por           VARCHAR(100),

  cancelado_em             TIMESTAMP,
  cancelado_por            VARCHAR(100),
  cancelamento_motivo      TEXT
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage
                 WHERE table_name='hora_emprestimo_moto'
                   AND constraint_name='ck_hora_emprestimo_tipo') THEN
    ALTER TABLE hora_emprestimo_moto
      ADD CONSTRAINT ck_hora_emprestimo_tipo
      CHECK (tipo IN ('SAIDA', 'ENTRADA'));
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.constraint_column_usage
                 WHERE table_name='hora_emprestimo_moto'
                   AND constraint_name='ck_hora_emprestimo_status') THEN
    ALTER TABLE hora_emprestimo_moto
      ADD CONSTRAINT ck_hora_emprestimo_status
      CHECK (status IN ('EM_ABERTO', 'RESSARCIDO', 'CANCELADO'));
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                 WHERE table_name='hora_emprestimo_moto'
                   AND constraint_name='fk_hora_emprestimo_loja_hora') THEN
    ALTER TABLE hora_emprestimo_moto
      ADD CONSTRAINT fk_hora_emprestimo_loja_hora
      FOREIGN KEY (loja_hora_id) REFERENCES hora_loja(id);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                 WHERE table_name='hora_emprestimo_moto'
                   AND constraint_name='fk_hora_emprestimo_modelo') THEN
    ALTER TABLE hora_emprestimo_moto
      ADD CONSTRAINT fk_hora_emprestimo_modelo
      FOREIGN KEY (modelo_id) REFERENCES hora_modelo(id);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                 WHERE table_name='hora_emprestimo_moto'
                   AND constraint_name='fk_hora_emprestimo_chassi_saida') THEN
    ALTER TABLE hora_emprestimo_moto
      ADD CONSTRAINT fk_hora_emprestimo_chassi_saida
      FOREIGN KEY (chassi_saida) REFERENCES hora_moto(numero_chassi);
  END IF;

  IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                 WHERE table_name='hora_emprestimo_moto'
                   AND constraint_name='fk_hora_emprestimo_chassi_entrada') THEN
    ALTER TABLE hora_emprestimo_moto
      ADD CONSTRAINT fk_hora_emprestimo_chassi_entrada
      FOREIGN KEY (chassi_entrada) REFERENCES hora_moto(numero_chassi);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_hora_emprestimo_status ON hora_emprestimo_moto(status);
CREATE INDEX IF NOT EXISTS ix_hora_emprestimo_loja_hora ON hora_emprestimo_moto(loja_hora_id);
CREATE INDEX IF NOT EXISTS ix_hora_emprestimo_modelo ON hora_emprestimo_moto(modelo_id);
CREATE INDEX IF NOT EXISTS ix_hora_emprestimo_chassi_saida ON hora_emprestimo_moto(chassi_saida);
CREATE INDEX IF NOT EXISTS ix_hora_emprestimo_chassi_entrada ON hora_emprestimo_moto(chassi_entrada);
CREATE INDEX IF NOT EXISTS ix_hora_emprestimo_data ON hora_emprestimo_moto(data_emprestimo);
