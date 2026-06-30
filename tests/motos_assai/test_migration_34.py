from app import db
from sqlalchemy import text

TABELAS = [
    'assai_peca', 'assai_peca_modelo', 'assai_peca_compra',
    'assai_pendencia', 'assai_peca_compra_item', 'assai_estoque_movimento',
]


def test_seis_tabelas_existem(app):
    with app.app_context():
        existentes = {
            r[0] for r in db.session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:nomes)"
            ), {'nomes': TABELAS})
        }
        faltando = set(TABELAS) - existentes
        assert not faltando, f'Tabelas faltando: {sorted(faltando)}'


def test_indice_parcial_pendencia_aberta(app):
    with app.app_context():
        idx = db.session.execute(text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_assai_pendencia_aberta'"
        )).scalar()
        assert idx is not None, 'ix_assai_pendencia_aberta nao existe'
        assert 'resolvida_em IS NULL' in idx and 'cancelada_em IS NULL' in idx
