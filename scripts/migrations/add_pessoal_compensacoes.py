"""Migration: sistema de compensacao Saida <-> Entrada Empresa (pessoal).

Cria:
- Tabela `pessoal_compensacoes` (N:M saida <-> entrada com valor consumido)
- Coluna `pessoal_categorias.compensavel_tipo` CHAR(1): 'S' (saida) | 'E' (entrada) | NULL
- Coluna `pessoal_transacoes.valor_compensado` NUMERIC(15,2) DEFAULT 0
- Indices necessarios

Idempotente (usa IF NOT EXISTS).
"""
from app import create_app, db
from sqlalchemy import text


def main():
    app = create_app()
    with app.app_context():
        print('[*] Iniciando migration pessoal_compensacoes...')

        # 1. Coluna em pessoal_categorias
        db.session.execute(text("""
            ALTER TABLE pessoal_categorias
            ADD COLUMN IF NOT EXISTS compensavel_tipo CHAR(1)
        """))
        db.session.execute(text("""
            ALTER TABLE pessoal_categorias
            ADD CONSTRAINT IF NOT EXISTS ck_pessoal_categorias_compensavel_tipo
            CHECK (compensavel_tipo IS NULL OR compensavel_tipo IN ('S', 'E'))
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_categorias_compensavel
            ON pessoal_categorias (compensavel_tipo)
            WHERE compensavel_tipo IS NOT NULL
        """))
        print('[OK] pessoal_categorias.compensavel_tipo criada')

        # 2. Coluna em pessoal_transacoes
        db.session.execute(text("""
            ALTER TABLE pessoal_transacoes
            ADD COLUMN IF NOT EXISTS valor_compensado NUMERIC(15, 2) NOT NULL DEFAULT 0
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_compensado
            ON pessoal_transacoes (valor_compensado)
            WHERE valor_compensado > 0
        """))
        print('[OK] pessoal_transacoes.valor_compensado criada')

        # 3. Tabela pessoal_compensacoes
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS pessoal_compensacoes (
                id SERIAL PRIMARY KEY,
                saida_id INTEGER NOT NULL REFERENCES pessoal_transacoes(id) ON DELETE CASCADE,
                entrada_id INTEGER NOT NULL REFERENCES pessoal_transacoes(id) ON DELETE CASCADE,
                valor_compensado NUMERIC(15, 2) NOT NULL,
                residuo_saida NUMERIC(15, 2) NOT NULL,
                residuo_entrada NUMERIC(15, 2) NOT NULL,
                origem VARCHAR(10) NOT NULL DEFAULT 'manual',
                status VARCHAR(10) NOT NULL DEFAULT 'ATIVA',
                observacao TEXT,
                criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                criado_por VARCHAR(100),
                revertido_em TIMESTAMP,
                revertido_por VARCHAR(100),
                CONSTRAINT ck_compensacoes_valor_positivo CHECK (valor_compensado > 0),
                CONSTRAINT ck_compensacoes_origem CHECK (origem IN ('auto', 'manual')),
                CONSTRAINT ck_compensacoes_status CHECK (status IN ('ATIVA', 'REVERTIDA')),
                CONSTRAINT ck_compensacoes_saida_diff_entrada CHECK (saida_id <> entrada_id)
            )
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_compensacoes_saida
            ON pessoal_compensacoes (saida_id) WHERE status = 'ATIVA'
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_compensacoes_entrada
            ON pessoal_compensacoes (entrada_id) WHERE status = 'ATIVA'
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_pessoal_compensacoes_status
            ON pessoal_compensacoes (status, criado_em DESC)
        """))
        print('[OK] pessoal_compensacoes criada')

        db.session.commit()
        print('[OK] Migration concluida.')

        # Verificacao
        n_cat = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='pessoal_categorias' AND column_name='compensavel_tipo'"
        )).scalar()
        n_tx = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='pessoal_transacoes' AND column_name='valor_compensado'"
        )).scalar()
        n_comp = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name='pessoal_compensacoes'"
        )).scalar()
        print(f'[VERIFY] categorias.compensavel_tipo: {n_cat}/1')
        print(f'[VERIFY] transacoes.valor_compensado: {n_tx}/1')
        print(f'[VERIFY] tabela pessoal_compensacoes: {n_comp}/1')


if __name__ == '__main__':
    main()
