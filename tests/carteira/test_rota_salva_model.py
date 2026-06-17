from app.carteira.models import RotaSalva


def test_cria_rota_salva(db):
    r = RotaSalva(nome='SP Capital', criado_por=1, lotes=['L1', 'L2'],
                  ordem_otimizada=['L2', 'L1'], inclui_volta=True, dias_viagem=2,
                  distancia_km=120.5, custo_total=850.0, status='salva')
    db.session.add(r)
    db.session.flush()
    assert r.id is not None
    assert r.lotes == ['L1', 'L2']
    assert r.inclui_volta is True
    assert float(r.custo_total) == 850.0


def test_to_dict(db):
    r = RotaSalva(nome='Rota X', lotes=['A'], custo_total=100.0)
    db.session.add(r)
    db.session.flush()
    d = r.to_dict()
    assert d['nome'] == 'Rota X'
    assert d['lotes'] == ['A']
    assert d['custo_total'] == 100.0
