"""Preview da NF-e deve EXIBIR o custo de brindes na margem.

O `montar_preview` ja subtrai `custo_brindes_total` do liquido; o template
`venda_preview_nfe.html` precisa exibir essa linha (antes a conta nao fechava
visualmente: Venda - Frete - Custo Moto != Liquido quando havia brinde).
"""
import uuid
from decimal import Decimal

from app import db as _db
from app.auth.models import Usuario
from app.hora.models import HoraVenda
from app.hora.services import venda_service
from app.utils.timezone import agora_utc_naive


def _admin(db):
    u = Usuario(nome='Admin Prev', email=f'{uuid.uuid4().hex[:10]}@t.local',
                senha_hash='x', perfil='administrador', status='ativo', sistema_lojas=True)
    db.session.add(u)
    db.session.flush()
    return u


def _login(client, u):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(u.id)
        sess['_fresh'] = True


def _venda(loja):
    v = HoraVenda(
        loja_id=loja.id, cpf_cliente='12345678909', nome_cliente='Cliente Teste',
        valor_total=Decimal('1000'), status='COTACAO',
        data_venda=agora_utc_naive().date(), origem_criacao='MANUAL',
    )
    _db.session.add(v)
    _db.session.flush()
    return v


def test_preview_exibe_custo_brindes(client, db, loja_factory, peca_factory):
    _login(client, _admin(db))
    v = _venda(loja_factory())
    p = peca_factory(descricao='CAPACETE PRETO')
    p.preco_venda_padrao = Decimal('140')  # != custo, p/ provar uso do custo
    p.custo = Decimal('40')
    _db.session.flush()
    venda_service.adicionar_brinde(v.id, p.id, qtd=1, usuario='t')

    resp = client.get(f'/hora/vendas/{v.id}/nfe/preview')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8', 'replace')
    assert 'Custo Brindes' in html       # label nova na secao de margem
    assert '40,00' in html               # valor do custo de brindes


def test_preview_sem_brinde_nao_quebra(client, db, loja_factory):
    _login(client, _admin(db))
    v = _venda(loja_factory())
    resp = client.get(f'/hora/vendas/{v.id}/nfe/preview')
    assert resp.status_code == 200
