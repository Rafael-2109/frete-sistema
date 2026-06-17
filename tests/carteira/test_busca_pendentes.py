"""Busca de Separacoes 'pendentes de embarque' (sem data_embarque OU nf_cd) com
filtros, para incluir no mapa a partir de um modal — item #7."""
from datetime import date
from app.separacao.models import Separacao
from app.carteira.routes.mapa_routes import mapa_service


def _sep(**kw):
    base = dict(cod_uf='SP', nf_cd=False, sincronizado_nf=False, qtd_saldo=10, cod_produto='P1')
    base.update(kw)
    return Separacao(**base)


def test_busca_exclui_embarcado(client, db):
    db.session.add(_sep(separacao_lote_id='LOTE_TST_A', num_pedido='VCDTST1',
                        raz_social_red='CLITESTE_PEND', nome_cidade='SAO PAULO', cod_uf='SP',
                        sub_rota='SP-CAP', expedicao=date(2026, 6, 18), data_embarque=None))
    db.session.add(_sep(separacao_lote_id='LOTE_TST_B', num_pedido='VCDTST2',
                        raz_social_red='CLITESTE_PEND', nome_cidade='RIO', cod_uf='RJ',
                        expedicao=date(2026, 6, 18), data_embarque=date(2026, 6, 19)))
    db.session.commit()
    res = mapa_service.buscar_separacoes_pendentes({'cliente': 'CLITESTE_PEND'})
    lotes = [r['separacao_lote_id'] for r in res]
    assert 'LOTE_TST_A' in lotes        # pendente (sem data_embarque)
    assert 'LOTE_TST_B' not in lotes     # ja embarcado


def test_busca_inclui_nf_cd_mesmo_embarcado(client, db):
    db.session.add(_sep(separacao_lote_id='LOTE_TST_C', num_pedido='VCDTST3',
                        raz_social_red='CLITESTE_NFCD', nome_cidade='CAMPINAS', cod_uf='SP',
                        expedicao=date(2026, 6, 18), data_embarque=date(2026, 6, 19),
                        nf_cd=True, qtd_saldo=0))
    db.session.commit()
    res = mapa_service.buscar_separacoes_pendentes({'cliente': 'CLITESTE_NFCD'})
    assert any(r['separacao_lote_id'] == 'LOTE_TST_C' for r in res)  # NF no CD


def test_busca_filtro_endpoint(client, db):
    db.session.add(_sep(separacao_lote_id='LOTE_TST_D', num_pedido='VCDTST4',
                        raz_social_red='CLITESTE_EP', nome_cidade='SANTOS', cod_uf='SP',
                        expedicao=date(2026, 6, 18), data_embarque=None))
    db.session.commit()
    import json
    r = client.post('/carteira/mapa/api/rota/buscar-pendentes',
                    data=json.dumps({'cliente': 'CLITESTE_EP'}), content_type='application/json')
    assert r.status_code == 200
    assert r.get_json()['sucesso'] is True
    assert any(x['num_pedido'] == 'VCDTST4' for x in r.get_json()['resultados'])
