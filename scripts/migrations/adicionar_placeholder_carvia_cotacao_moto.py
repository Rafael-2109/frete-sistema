"""Migration: placeholder em carvia_cotacao_motos + cadastro_pendente em carvia_modelos_moto.

Suporta cadastro tardio de modelo trazido por NF (BUG B4 da analise COT-76):
- carvia_cotacao_motos.placeholder=TRUE indica peso/cubagem pendentes
- carvia_modelos_moto.cadastro_pendente=TRUE indica modelo criado sem dimensoes reais
- Filtro de UI mostra badge amarelo enquanto pendente
- Apos completar peso/dimensoes, helper recalcula provisorio do embarque
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def _coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :t AND column_name = :c
    """), {'t': tabela, 'c': coluna}).scalar())


def verificar_antes():
    placeholder = _coluna_existe('carvia_cotacao_motos', 'placeholder')
    cadastro = _coluna_existe('carvia_modelos_moto', 'cadastro_pendente')
    print(f"[BEFORE] carvia_cotacao_motos.placeholder = {'existe' if placeholder else 'NAO existe'}")
    print(f"[BEFORE] carvia_modelos_moto.cadastro_pendente = {'existe' if cadastro else 'NAO existe'}")
    return placeholder, cadastro


def executar_migration(placeholder_existe, cadastro_existe):
    if not placeholder_existe:
        db.session.execute(db.text("""
            ALTER TABLE carvia_cotacao_motos
            ADD COLUMN placeholder BOOLEAN NOT NULL DEFAULT FALSE
        """))
        print("[OK] carvia_cotacao_motos.placeholder adicionado")

    if not cadastro_existe:
        db.session.execute(db.text("""
            ALTER TABLE carvia_modelos_moto
            ADD COLUMN cadastro_pendente BOOLEAN NOT NULL DEFAULT FALSE
        """))
        print("[OK] carvia_modelos_moto.cadastro_pendente adicionado")

    # Indices parciais para queries de pendentes (badge UI)
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_motos_placeholder
            ON carvia_cotacao_motos (cotacao_id)
            WHERE placeholder = TRUE
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_modelos_moto_cadastro_pendente
            ON carvia_modelos_moto (id)
            WHERE cadastro_pendente = TRUE
    """))
    print("[OK] Indices parciais criados/garantidos")

    db.session.commit()


def verificar_depois():
    placeholder = _coluna_existe('carvia_cotacao_motos', 'placeholder')
    cadastro = _coluna_existe('carvia_modelos_moto', 'cadastro_pendente')
    print(f"[AFTER] carvia_cotacao_motos.placeholder = {'existe' if placeholder else 'NAO existe'}")
    print(f"[AFTER] carvia_modelos_moto.cadastro_pendente = {'existe' if cadastro else 'NAO existe'}")

    assert placeholder, "placeholder nao foi criado"
    assert cadastro, "cadastro_pendente nao foi criado"


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        placeholder_existe, cadastro_existe = verificar_antes()
        if placeholder_existe and cadastro_existe:
            print("[SKIP] ambos campos ja existem - apenas garantindo indices")
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS ix_carvia_cotacao_motos_placeholder
                    ON carvia_cotacao_motos (cotacao_id) WHERE placeholder = TRUE
            """))
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS ix_carvia_modelos_moto_cadastro_pendente
                    ON carvia_modelos_moto (id) WHERE cadastro_pendente = TRUE
            """))
            db.session.commit()
        else:
            executar_migration(placeholder_existe, cadastro_existe)
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
