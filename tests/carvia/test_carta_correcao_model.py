"""Models da Carta de Correção (CCe) CarVia — B2 do plano."""
from app import db as _db


def test_cria_carta_e_vinculo(db):
    from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
    carta = CarviaCartaCorrecao(
        nome_original='cce.pdf', nome_arquivo='abc_cce.pdf',
        caminho_s3='carvia/cartas_correcao/abc_cce.pdf',
        content_type='application/pdf', criado_por='t')
    _db.session.add(carta)
    _db.session.flush()
    v = CarviaCartaCorrecaoVinculo(
        carta_id=carta.id, entidade_tipo='nf', entidade_id=10,
        origem=CarviaCartaCorrecaoVinculo.ORIGEM_MANUAL, criado_por='t')
    _db.session.add(v)
    _db.session.flush()
    assert carta.id and v.id
    assert 'nf' in CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS
    assert 'cotacao' in CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS
    assert carta.ativo is True
