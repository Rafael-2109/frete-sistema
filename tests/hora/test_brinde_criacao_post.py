"""REPRO do cenario do dono: brinde adicionado na CRIACAO (secao 'Brindes
opcional') chega ao banco via o POST da rota tagplus_pedido_venda_criar?

Cobre a lacuna que test_criar_venda_com_brinde NAO cobria: o caminho HTTP
(rota lendo brinde_peca_id[]/brinde_qtd[] do form), nao o service direto.
"""
import uuid
from decimal import Decimal

from app import db as _db
from app.auth.models import Usuario
from app.hora.models import HoraModelo, HoraVenda, HoraVendaBrinde
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _admin(db):
    u = Usuario(nome='Admin Post', email=f'{uuid.uuid4().hex[:10]}@t.local',
                senha_hash='x', perfil='administrador', status='ativo', sistema_lojas=True)
    db.session.add(u)
    db.session.flush()
    return u


def _login(client, u):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
        sess['_fresh'] = True


def _modelo():
    m = HoraModelo(nome_modelo='POST-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000.00'))
    _db.session.add(m)
    _db.session.flush()
    return m


def _chassi(modelo_nome, loja_id):
    chassi = ('PT' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(numero_chassi=chassi, modelo_nome=modelo_nome, cor='PRETA', criado_por='t')
    registrar_evento(numero_chassi=chassi, tipo='RECEBIDA', loja_id=loja_id, operador='t')
    registrar_evento(numero_chassi=chassi, tipo='CONFERIDA', loja_id=loja_id, operador='t')
    _db.session.flush()
    return chassi


def test_post_criacao_grava_brinde(client, db, loja_factory, peca_factory):
    _login(client, _admin(db))
    loja = loja_factory()
    modelo = _modelo()
    chassi = _chassi(modelo.nome_modelo, loja.id)
    peca = peca_factory(descricao='CAPACETE BRINDE')
    peca.preco_venda_padrao = Decimal('25')
    _db.session.flush()

    resp = client.post('/hora/tagplus/pedido-venda', data={
        'cpf': '12345678909', 'nome': 'Cliente Brinde POST',
        'cep': '01001000', 'logradouro': 'Rua A', 'numero_endereco': '1',
        'bairro': 'Centro', 'cidade': 'SP', 'uf': 'SP',
        'chassi': chassi, 'valor': '1000,00',
        'loja_id': str(loja.id), 'origem_lead': 'INSTAGRAM',
        'modalidade_frete': '0',
        # exatamente o que o form da secao "Brindes (opcional)" envia:
        'brinde_peca_id': str(peca.id), 'brinde_qtd': '1',
    }, follow_redirects=False)

    # 302 redireciona para o detalhe da venda criada
    assert resp.status_code in (301, 302), resp.data[:500]

    venda = HoraVenda.query.filter_by(cpf_cliente='12345678909').order_by(HoraVenda.id.desc()).first()
    assert venda is not None, 'venda nao foi criada'
    brindes = HoraVendaBrinde.query.filter_by(venda_id=venda.id).all()
    assert len(brindes) == 1, f'esperava 1 brinde, achei {len(brindes)} (status venda={venda.status})'
    assert brindes[0].peca_id == peca.id
