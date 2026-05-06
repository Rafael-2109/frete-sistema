"""Migration HORA 29: unificacao de modelos (N nomes -> 1 modelo canonico).

Cria 2 tabelas novas + ALTER em hora_modelo (auditoria de merge):

  - hora_modelo_alias    -> N nomes que apontam para 1 modelo canonico.
                            Resolver de ingestao (TagPlus, NF, pedido, DANFE)
                            consulta esta tabela ANTES de criar modelo novo.
  - hora_modelo_pendente -> fila de nomes nao reconhecidos. Sistema NAO cria
                            modelo silenciosamente; operador decide vincular
                            ou criar via tela /hora/modelos/pendencias.
  - hora_modelo (ALTER)  -> 3 colunas: merged_em_id (self FK), merged_em,
                            merged_por. Modelo absorvido fica ativo=False
                            apontando para o canonico.

Idempotente — pode rodar 2x sem efeito (IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_29_modelo_alias.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)


SQL_CREATE_ALIAS = """
CREATE TABLE IF NOT EXISTS hora_modelo_alias (
    id              SERIAL PRIMARY KEY,
    modelo_id       INTEGER NOT NULL REFERENCES hora_modelo(id) ON DELETE CASCADE,
    nome_alias      VARCHAR(200) NOT NULL,
    tipo            VARCHAR(30) NOT NULL,
    criado_em       TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por      VARCHAR(100),
    observacao      TEXT,
    CONSTRAINT uq_hora_modelo_alias_tipo_nome UNIQUE (tipo, nome_alias)
);
"""

SQL_INDICES_ALIAS = [
    "CREATE INDEX IF NOT EXISTS ix_hora_modelo_alias_modelo_id "
    "ON hora_modelo_alias (modelo_id);",
    "CREATE INDEX IF NOT EXISTS ix_hora_modelo_alias_tipo "
    "ON hora_modelo_alias (tipo);",
]


SQL_CREATE_PENDENTE = """
CREATE TABLE IF NOT EXISTS hora_modelo_pendente (
    id                  SERIAL PRIMARY KEY,
    nome_observado      VARCHAR(200) NOT NULL,
    origem              VARCHAR(30) NOT NULL,
    origem_id           INTEGER,
    tagplus_codigo      VARCHAR(50),
    tagplus_produto_id  VARCHAR(50),
    qtd_ocorrencias     INTEGER NOT NULL DEFAULT 1,
    primeiro_visto      TIMESTAMP NOT NULL DEFAULT NOW(),
    ultimo_visto        TIMESTAMP NOT NULL DEFAULT NOW(),
    status              VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
    resolvido_modelo_id INTEGER REFERENCES hora_modelo(id),
    resolvido_em        TIMESTAMP,
    resolvido_por       VARCHAR(100),
    observacao          TEXT,
    CONSTRAINT uq_hora_modelo_pendente_nome_origem UNIQUE (nome_observado, origem)
);
"""

SQL_INDICES_PENDENTE = [
    "CREATE INDEX IF NOT EXISTS ix_hora_modelo_pendente_status "
    "ON hora_modelo_pendente (status);",
    "CREATE INDEX IF NOT EXISTS ix_hora_modelo_pendente_origem "
    "ON hora_modelo_pendente (origem);",
    "CREATE INDEX IF NOT EXISTS ix_hora_modelo_pendente_resolvido "
    "ON hora_modelo_pendente (resolvido_modelo_id);",
]


SQL_ALTER_MODELO = [
    "ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS merged_em_id INTEGER;",
    "ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS merged_em TIMESTAMP;",
    "ALTER TABLE hora_modelo ADD COLUMN IF NOT EXISTS merged_por VARCHAR(100);",
]

SQL_ADD_FK_MERGED = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_hora_modelo_merged_em'
          AND table_name = 'hora_modelo'
    ) THEN
        ALTER TABLE hora_modelo
            ADD CONSTRAINT fk_hora_modelo_merged_em
            FOREIGN KEY (merged_em_id) REFERENCES hora_modelo(id);
    END IF;
END $$;
"""

SQL_INDEX_MERGED = (
    "CREATE INDEX IF NOT EXISTS ix_hora_modelo_merged_em_id "
    "ON hora_modelo (merged_em_id);"
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        antes_alias = inspector.has_table('hora_modelo_alias')
        antes_pendente = inspector.has_table('hora_modelo_pendente')
        cols_modelo_antes = {c['name'] for c in inspector.get_columns('hora_modelo')}

        print('Estado antes:')
        print(f'  hora_modelo_alias existe? {antes_alias}')
        print(f'  hora_modelo_pendente existe? {antes_pendente}')
        print(f'  hora_modelo tem merged_em_id? {"merged_em_id" in cols_modelo_antes}')
        print(f'  hora_modelo tem merged_em? {"merged_em" in cols_modelo_antes}')
        print(f'  hora_modelo tem merged_por? {"merged_por" in cols_modelo_antes}')

        with db.engine.begin() as conn:
            # 1. CREATE hora_modelo_alias + indices
            conn.execute(text(SQL_CREATE_ALIAS))
            for sql in SQL_INDICES_ALIAS:
                conn.execute(text(sql))

            # 2. CREATE hora_modelo_pendente + indices
            conn.execute(text(SQL_CREATE_PENDENTE))
            for sql in SQL_INDICES_PENDENTE:
                conn.execute(text(sql))

            # 3. ALTER hora_modelo (3 colunas + FK self + indice)
            for sql in SQL_ALTER_MODELO:
                conn.execute(text(sql))
            conn.execute(text(SQL_ADD_FK_MERGED))
            conn.execute(text(SQL_INDEX_MERGED))

        # Verifica estado final
        inspector = inspect(db.engine)
        depois_alias = inspector.has_table('hora_modelo_alias')
        depois_pendente = inspector.has_table('hora_modelo_pendente')
        cols_modelo_depois = {c['name'] for c in inspector.get_columns('hora_modelo')}

        print('\nEstado depois:')
        print(f'  hora_modelo_alias existe? {depois_alias}')
        print(f'  hora_modelo_pendente existe? {depois_pendente}')
        print(f'  hora_modelo tem merged_em_id? {"merged_em_id" in cols_modelo_depois}')
        print(f'  hora_modelo tem merged_em? {"merged_em" in cols_modelo_depois}')
        print(f'  hora_modelo tem merged_por? {"merged_por" in cols_modelo_depois}')

        if depois_alias:
            cols = {c['name'] for c in inspector.get_columns('hora_modelo_alias')}
            print(f'\n  hora_modelo_alias colunas ({len(cols)}): {sorted(cols)}')
        if depois_pendente:
            cols = {c['name'] for c in inspector.get_columns('hora_modelo_pendente')}
            print(f'  hora_modelo_pendente colunas ({len(cols)}): {sorted(cols)}')

        ok = (
            depois_alias
            and depois_pendente
            and 'merged_em_id' in cols_modelo_depois
            and 'merged_em' in cols_modelo_depois
            and 'merged_por' in cols_modelo_depois
        )
        if not ok:
            print('\nERRO: alguma estrutura nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 29 concluida com sucesso.')


if __name__ == '__main__':
    main()
