"""Cotacao Rapida PUBLICA (tela sem login): modelo, service, rotas, rate-limit."""
from decimal import Decimal


def test_modelo_persiste_e_le(db):
    from app.carvia.models import CarviaCotacaoRapidaPublica
    reg = CarviaCotacaoRapidaPublica(
        solicitante_nome='Fulano',
        uf_destino='RJ',
        cidade_destino='Rio de Janeiro',
        itens=[{'modelo_id': 1, 'quantidade': 2}],
        opcoes=[{'tabela_nome': 'T1', 'valor_total': 100.0}],
        valor_total_min=Decimal('100.00'),
        qtd_total_motos=2,
    )
    db.session.add(reg)
    db.session.commit()
    lido = CarviaCotacaoRapidaPublica.query.get(reg.id)
    assert lido.solicitante_nome == 'Fulano'
    assert lido.itens[0]['quantidade'] == 2
    assert lido.criado_em is not None
