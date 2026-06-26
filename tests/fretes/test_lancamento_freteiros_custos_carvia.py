"""Custos de Entrega CarVia no Lancamento Freteiros (paridade DespesaExtra Nacom).

Garante por execucao (HTTP) que:
  - GET /fretes/lancamento_freteiros renderiza os CEs CarVia pendentes do
    freteiro (checkbox `carvia_custos_selecionados`);
  - POST /fretes/emitir_fatura_freteiro vincula o CE selecionado a FT CarVia.
"""
from datetime import date


def _criar_user(db):
    from app.auth.models import Usuario
    u = Usuario(
        nome='Financeiro Teste', email='fin.freteiro@test.bot', senha_hash='x',
        perfil='administrador', status='ativo',
    )
    db.session.add(u)
    db.session.flush()
    return u


def _criar_freteiro(db, cnpj='88888888000188'):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj=cnpj, razao_social='FRETEIRO CUSTO TESTE',
        cidade='SAO PAULO', uf='SP', freteiro=True,
    )
    db.session.add(t)
    db.session.flush()
    return t


def _criar_embarque(db):
    from app.embarques.models import Embarque
    e = Embarque(status='ativo', criado_por='test@bot',
                 data_embarque=date(2026, 6, 25))
    db.session.add(e)
    db.session.flush()
    return e


def _criar_frete_carvia(db, transp, embarque, cnpj_destino='22222222000122'):
    from app.carvia.models import CarviaFrete
    f = CarviaFrete(
        transportadora_id=transp.id, embarque_id=embarque.id,
        cnpj_emitente='11111111000111', nome_emitente='EMIT',
        cnpj_destino=cnpj_destino, nome_destino='CLIENTE T',
        uf_destino='SP', cidade_destino='SAO PAULO', tipo_carga='DIRETA',
        peso_total=100.0, valor_total_nfs=5000.0, quantidade_nfs=1,
        numeros_nfs='5187', valor_cotado=160.0, status='PENDENTE',
        criado_por='test@bot',
    )
    db.session.add(f)
    db.session.flush()
    return f


def _criar_custo(db, frete, valor=75.0):
    from app.carvia.models import CarviaCustoEntrega
    ce = CarviaCustoEntrega(
        numero_custo=f'CE-{frete.id}', tipo_custo='TAXA_DESCARGA',
        descricao='descarga teste', valor=valor, data_custo=date(2026, 6, 25),
        status='PENDENTE', frete_id=frete.id, criado_por='test@bot',
    )
    db.session.add(ce)
    db.session.flush()
    return ce


def test_get_lancamento_freteiros_renderiza_custo_carvia(client, db):
    user = _criar_user(db)
    transp = _criar_freteiro(db)
    emb = _criar_embarque(db)
    frete = _criar_frete_carvia(db, transp, emb)
    _criar_custo(db, frete, valor=75.0)

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)

    resp = client.get('/fretes/lancamento_freteiros')
    assert resp.status_code == 200, resp.data[:300]
    html = resp.data.decode('utf-8')
    # o checkbox dos custos CarVia foi renderizado
    assert 'carvia_custos_selecionados' in html
    assert 'TAXA_DESCARGA' in html


def test_post_emitir_fatura_freteiro_vincula_custo_carvia(client, db):
    from app.carvia.models import CarviaCustoEntrega
    user = _criar_user(db)
    transp = _criar_freteiro(db, cnpj='89999999000199')
    emb = _criar_embarque(db)
    frete = _criar_frete_carvia(db, transp, emb)
    ce = _criar_custo(db, frete, valor=75.0)
    ce_id = ce.id

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)

    resp = client.post(
        f'/fretes/emitir_fatura_freteiro/{transp.id}',
        data={
            'data_vencimento': '2026-06-30',
            'carvia_selecionados': [str(frete.id)],
            'carvia_custos_selecionados': [str(ce_id)],
        },
        follow_redirects=False,
    )
    assert resp.status_code in (302, 303), resp.data[:300]

    db.session.expire_all()
    ce_db = db.session.get(CarviaCustoEntrega, ce_id)
    assert ce_db.fatura_transportadora_id is not None
    assert ce_db.numero_documento != 'PENDENTE_FATURA'
