"""Listagem de NFs CarVia: o link 'ver frete' resolve pelo CarviaFrete REAL (numeros_nfs +
cnpj), nao pela FK de operacao.

Bug (NF 39147 / frete 803): a Query 5 da listagem juntava `CarviaFrete.operacao_id ==
CarviaOperacaoNf.operacao_id`, entao uma NF com frete mas AINDA sem CTe (operacao_id NULL)
nao aparecia — o botao ficava "Sem frete" desativado apesar do CarviaFrete existir.
"""
import uuid

from app import db as _db

from app.carvia.routes.nf_routes import _frete_id_por_nf


def _nf(numero, emit, dest):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente=emit, nome_emitente='E',
        cnpj_destinatario=dest, nome_destinatario='D',
        status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    _db.session.add(nf)
    _db.session.flush()
    return nf


def _frete(numeros_nfs, emit, dest, operacao_id=None, status='PENDENTE'):
    from app.carvia.models import CarviaFrete
    from app.embarques.models import Embarque
    from app.transportadoras.models import Transportadora
    emb = Embarque(numero=int(uuid.uuid4().int % 9_000_000) + 1_000_000, status='ativo')
    _db.session.add(emb)
    _db.session.flush()
    tr = Transportadora(razao_social='T', cnpj=str(uuid.uuid4().int)[:14], cidade='SP', uf='SP')
    _db.session.add(tr)
    _db.session.flush()
    f = CarviaFrete(
        transportadora_id=tr.id, embarque_id=emb.id, cnpj_emitente=emit, cnpj_destino=dest,
        nome_destino='D', uf_destino='SP', cidade_destino='X', tipo_carga='DIRETA',
        operacao_id=operacao_id, status=status, numeros_nfs=numeros_nfs, criado_por='test',
    )
    _db.session.add(f)
    _db.session.flush()
    return f


def test_link_acha_frete_sem_cte(db):
    """NF com CarviaFrete mas SEM operacao (op=None) -> link ativo. Reproduz a NF 39147."""
    nf = _nf('39147', '09089839000112', '61981557000145')
    f = _frete('39147', '09089839000112', '61981557000145', operacao_id=None)

    res = _frete_id_por_nf([nf.id])
    assert res.get(nf.id) == f.id


def test_link_csv_membro_nao_primeiro(db):
    """NF que e um membro (nao o 1o) do CSV numeros_nfs tambem resolve."""
    nf = _nf('39121', '09089839000112', '52921890000178')
    f = _frete('38906,39121', '09089839000112', '52921890000178')

    res = _frete_id_por_nf([nf.id])
    assert res.get(nf.id) == f.id


def test_link_nao_pega_cnpj_diferente(db):
    """Frete de outro cnpj (mesmo numero de NF) NAO e atribuido a esta NF."""
    nf = _nf('5000', '11111111000111', '22222222000122')
    _frete('5000', '99999999000199', '88888888000188')

    res = _frete_id_por_nf([nf.id])
    assert nf.id not in res


def test_link_match_exato_de_membro(db):
    """numero '500' NAO casa com membro '5000' do CSV (match exato, sem substring)."""
    nf = _nf('500', '11111111000111', '22222222000122')
    _frete('5000,5001', '11111111000111', '22222222000122')

    res = _frete_id_por_nf([nf.id])
    assert nf.id not in res


def test_link_ignora_frete_cancelado(db):
    """Frete CANCELADO nao ativa o link."""
    nf = _nf('6000', '11111111000111', '22222222000122')
    _frete('6000', '11111111000111', '22222222000122', status='CANCELADO')

    res = _frete_id_por_nf([nf.id])
    assert nf.id not in res
