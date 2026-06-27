"""Gate de gerenciamento de brinde na tela do Pedido de Venda.

Adicionar/remover brinde deve estar disponivel em INCOMPLETO e COTACAO
(pedido nasce INCOMPLETO), e indisponivel em CONFIRMADO/FATURADO. A TABELA
de brindes ja salvos aparece em qualquer status.
"""
import uuid
from decimal import Decimal

from app import db as _db
from app.auth.models import Usuario
from app.hora.models import HoraVenda
from app.hora.services import venda_service
from app.utils.timezone import agora_utc_naive


def _admin(db):
    u = Usuario(nome='Admin Det', email=f'{uuid.uuid4().hex[:10]}@t.local',
                senha_hash='x', perfil='administrador', status='ativo', sistema_lojas=True)
    db.session.add(u)
    db.session.flush()
    return u


def _login(client, u):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
        sess['_fresh'] = True


def _venda(loja, status='COTACAO'):
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=Decimal('1000'), status=status,
        data_venda=agora_utc_naive().date(), origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    return v


def test_detalhe_incompleto_mostra_form_adicionar_brinde(client, db, loja_factory, peca_factory):
    _login(client, _admin(db))
    v = _venda(loja_factory())
    p = peca_factory(descricao='CAPACETE PRETO')
    p.preco_venda_padrao = Decimal('30')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='t')
    v.status = 'INCOMPLETO'
    _db.session.flush()

    resp = client.get(f'/hora/vendas/{v.id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8', 'replace')
    assert 'CAPACETE PRETO' in html        # tabela do brinde aparece
    assert 'Adicionar brinde' in html      # form de gerenciamento liberado


def test_detalhe_confirmado_mostra_tabela_sem_form(client, db, loja_factory, peca_factory):
    _login(client, _admin(db))
    v = _venda(loja_factory())
    p = peca_factory(descricao='RETROVISOR ESQ')
    p.preco_venda_padrao = Decimal('30')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='t')
    v.status = 'CONFIRMADO'
    _db.session.flush()

    resp = client.get(f'/hora/vendas/{v.id}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8', 'replace')
    assert 'RETROVISOR ESQ' in html        # tabela aparece em todos os status
    assert 'Adicionar brinde' not in html  # gerenciamento travado pos-confirmacao
