"""Validacao de integridade no Fechamento Freteiros (decisao Rafael 2026-06-26).

So aparecem na aba principal as faturas onde Σ itens == valor_total_fatura.
Faturas inconsistentes (orfa fantasma ou Σ != valor) vao para a aba
'Inconsistencias' (ocultas do fechamento, mas rastreaveis). Vale Nacom + CarVia.
"""
from datetime import date
from io import BytesIO

import pandas as pd


def _criar_admin(db):
    from app.auth.models import Usuario
    u = Usuario(
        nome='Admin Integridade', email='admin.integridade@test.bot',
        senha_hash='x', perfil='administrador', status='ativo',
    )
    db.session.add(u)
    db.session.flush()
    return u


def _criar_freteiro(db, cnpj='80000000000180'):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj=cnpj, razao_social='FRETEIRO INTEGRIDADE', cidade='SAO PAULO',
        uf='SP', freteiro=True,
    )
    db.session.add(t)
    db.session.flush()
    return t


def _criar_embarque(db):
    from app.embarques.models import Embarque
    e = Embarque(status='ativo', criado_por='test@bot', data_embarque=date(2026, 6, 25))
    db.session.add(e)
    db.session.flush()
    return e


def _criar_fatura_nacom(db, transp, *, numero, valor_total):
    from app.fretes.models import FaturaFrete
    f = FaturaFrete(
        transportadora_id=transp.id, numero_fatura=numero,
        data_emissao=date(2026, 6, 25), valor_total_fatura=valor_total,
        status_conferencia='CONFERIDO', criado_por='test@bot',
    )
    db.session.add(f)
    db.session.flush()
    return f


def _criar_frete_nacom(db, transp, embarque, fatura, *, valor_cte, status='APROVADO'):
    from app.fretes.models import Frete
    fr = Frete(
        embarque_id=embarque.id, cnpj_cliente='22222222000122',
        nome_cliente='CLIENTE NACOM', transportadora_id=transp.id,
        tipo_carga='DIRETA', modalidade='VALOR', uf_destino='SP',
        cidade_destino='SAO PAULO', peso_total=100, valor_total_nfs=1000,
        quantidade_nfs=1, numeros_nfs='999', valor_cotado=valor_cte,
        valor_cte=valor_cte, valor_considerado=valor_cte, status=status,
        numero_cte=f'Frete teste {numero_seq()}', fatura_frete_id=fatura.id,
        criado_por='test@bot',
    )
    db.session.add(fr)
    db.session.flush()
    return fr


_seq = [0]


def numero_seq():
    _seq[0] += 1
    return _seq[0]


def test_export_oculta_fatura_divergente_e_lista_em_inconsistencias(client, db):
    admin = _criar_admin(db)
    transp = _criar_freteiro(db)
    emb = _criar_embarque(db)

    # Fatura integra: 1 frete de 100, valor_total 100
    fat_ok = _criar_fatura_nacom(db, transp, numero='FT-INTEGRA', valor_total=100)
    _criar_frete_nacom(db, transp, emb, fat_ok, valor_cte=100)

    # Fatura divergente: 1 frete de 100, mas valor_total 999
    fat_div = _criar_fatura_nacom(db, transp, numero='FT-DIVERGENTE', valor_total=999)
    _criar_frete_nacom(db, transp, emb, fat_div, valor_cte=100)

    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)

    resp = client.get('/fretes/faturas/exportar-fechamento-freteiros')
    assert resp.status_code == 200, resp.data[:300]
    sheets = pd.read_excel(BytesIO(resp.data), sheet_name=None)

    assert 'Detalhamento' in sheets
    assert 'Inconsistencias' in sheets

    det_faturas = set(sheets['Detalhamento']['Fatura'].astype(str))
    assert 'FT-INTEGRA' in det_faturas
    assert 'FT-DIVERGENTE' not in det_faturas  # ocultada do fechamento

    inc = sheets['Inconsistencias']
    inc_faturas = set(inc['Fatura'].astype(str))
    assert 'FT-DIVERGENTE' in inc_faturas
    assert 'FT-INTEGRA' not in inc_faturas


def test_export_ignora_itens_cancelados_nacom(client, db):
    """Frete CANCELADO vinculado nao deve ser exibido nem somado (paridade CarVia,
    que ja filtra status != CANCELADO). Fatura com ativo (100) + cancelado (50),
    valor_total=100 -> integra (so o ativo conta) e aparece 1 linha."""
    admin = _criar_admin(db)
    transp = _criar_freteiro(db, cnpj='81000000000181')
    emb = _criar_embarque(db)
    fat = _criar_fatura_nacom(db, transp, numero='FT-COM-CANCELADO', valor_total=100)
    _criar_frete_nacom(db, transp, emb, fat, valor_cte=100, status='APROVADO')
    _criar_frete_nacom(db, transp, emb, fat, valor_cte=50, status='CANCELADO')

    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)

    resp = client.get('/fretes/faturas/exportar-fechamento-freteiros')
    assert resp.status_code == 200, resp.data[:300]
    sheets = pd.read_excel(BytesIO(resp.data), sheet_name=None)

    det = sheets['Detalhamento']
    linhas = det[det['Fatura'].astype(str) == 'FT-COM-CANCELADO']
    assert len(linhas) == 1  # so o frete ativo, nao o cancelado
    # fatura e integra (so o ativo conta) -> nao vai para Inconsistencias
    if 'Inconsistencias' in sheets:
        assert 'FT-COM-CANCELADO' not in set(sheets['Inconsistencias']['Fatura'].astype(str))
