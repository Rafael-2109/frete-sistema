"""Fixtures compartilhadas para tests do modulo pessoal.

Nota sobre isolamento: usa commit real + cleanup por ID em teardown.
O parent db fixture usa savepoint, mas o HTTP client Flask opera em
sessao separada e nao enxerga dados uncommitted. Ambiente: PostgreSQL
localhost (dev, nao producao) — seguro persistir temporariamente.
"""
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app import db as _db
from app.pessoal.models import (
    PessoalMembro, PessoalConta, PessoalCategoria,
    PessoalImportacao, PessoalTransacao,
)


def _uid():
    return uuid4().hex[:8]


@pytest.fixture
def pessoal_ctx(app):
    """Mantem app_context aberto durante o teste + cleanup por ID."""
    ids = {
        'transacoes': [], 'importacoes': [], 'contas': [],
        'categorias': [], 'membros': [],
    }
    with app.app_context():
        yield ids
        try:
            for t_id in ids['transacoes']:
                _db.session.query(PessoalTransacao).filter_by(id=t_id).delete()
            for i_id in ids['importacoes']:
                _db.session.query(PessoalImportacao).filter_by(id=i_id).delete()
            for c_id in ids['contas']:
                _db.session.query(PessoalConta).filter_by(id=c_id).delete()
            for c_id in ids['categorias']:
                _db.session.query(PessoalCategoria).filter_by(id=c_id).delete()
            for m_id in ids['membros']:
                _db.session.query(PessoalMembro).filter_by(id=m_id).delete()
            _db.session.commit()
        except Exception:
            _db.session.rollback()
            raise


@pytest.fixture
def membro(pessoal_ctx):
    m = PessoalMembro(nome=f'Teste_{_uid()}', ativo=True)
    _db.session.add(m)
    _db.session.commit()
    pessoal_ctx['membros'].append(m.id)
    return m


@pytest.fixture
def categoria_alimentacao(pessoal_ctx):
    c = PessoalCategoria(
        nome=f'Mercado_{_uid()}',
        grupo=f'Alimentacao_{_uid()}',
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    pessoal_ctx['categorias'].append(c.id)
    return c


@pytest.fixture
def categoria_transporte(pessoal_ctx):
    c = PessoalCategoria(
        nome=f'Uber_{_uid()}',
        grupo=f'Transporte_{_uid()}',
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    pessoal_ctx['categorias'].append(c.id)
    return c


@pytest.fixture
def conta(pessoal_ctx, membro):
    c = PessoalConta(
        nome=f'CC Bradesco Teste_{_uid()}',
        tipo='conta_corrente',
        banco='bradesco',
        membro_id=membro.id,
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    pessoal_ctx['contas'].append(c.id)
    return c


@pytest.fixture
def importacao(pessoal_ctx, conta):
    imp = PessoalImportacao(
        conta_id=conta.id,
        nome_arquivo=f'teste_{_uid()}.csv',
        tipo_arquivo='extrato_cc',
        total_linhas=0,
        linhas_importadas=0,
        status='IMPORTADO',
    )
    _db.session.add(imp)
    _db.session.commit()
    pessoal_ctx['importacoes'].append(imp.id)
    return imp


def _transacao_factory(importacao, conta, ids_registry, **kwargs):
    defaults = {
        'importacao_id': importacao.id,
        'conta_id': conta.id,
        'data': date(2026, 4, 1),
        'historico': 'TESTE PADRAO',
        'descricao': None,
        'historico_completo': None,
        'valor': Decimal('100.00'),
        'tipo': 'debito',
        'status': 'PENDENTE',
        'excluir_relatorio': False,
    }
    defaults.update(kwargs)

    if defaults.get('historico_completo') is None:
        defaults['historico_completo'] = defaults['historico']

    if not defaults.get('hash_transacao'):
        defaults['hash_transacao'] = (
            f"hash_{_uid()}_{defaults['data']}_{defaults['historico']}"
        )
    else:
        defaults['hash_transacao'] = f"{defaults['hash_transacao']}_{_uid()}"

    t = PessoalTransacao(**defaults)
    _db.session.add(t)
    _db.session.commit()
    ids_registry['transacoes'].append(t.id)
    return t


@pytest.fixture
def make_transacao(pessoal_ctx, importacao, conta):
    def _factory(**kwargs):
        return _transacao_factory(importacao, conta, pessoal_ctx, **kwargs)
    return _factory


@pytest.fixture
def client_autorizado(app, client, monkeypatch):
    """Client com pode_acessar_pessoal=True (bypass da lista de IDs)."""
    monkeypatch.setattr(
        'app.pessoal.routes.transacoes.pode_acessar_pessoal',
        lambda user: True,
    )
    return client
