"""Fixtures compartilhadas para tests do modulo pessoal."""
from datetime import date
from decimal import Decimal

import pytest

from app import db as _db
from app.pessoal.models import (
    PessoalMembro, PessoalConta, PessoalCategoria,
    PessoalImportacao, PessoalTransacao,
)


@pytest.fixture
def membro(db):
    m = PessoalMembro(nome='Teste', ativo=True)
    _db.session.add(m)
    _db.session.commit()
    return m


@pytest.fixture
def categoria_alimentacao(db):
    c = PessoalCategoria(nome='Mercado Teste', grupo='Alimentacao Teste', ativa=True)
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def categoria_transporte(db):
    c = PessoalCategoria(nome='Uber Teste', grupo='Transporte Teste', ativa=True)
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def conta(db, membro):
    c = PessoalConta(
        nome='CC Bradesco Teste',
        tipo='conta_corrente',
        banco='bradesco',
        membro_id=membro.id,
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def importacao(db, conta):
    imp = PessoalImportacao(
        conta_id=conta.id,
        nome_arquivo='teste.csv',
        tipo_arquivo='extrato_cc',
        total_linhas=0,
        linhas_importadas=0,
        status='IMPORTADO',
    )
    _db.session.add(imp)
    _db.session.commit()
    return imp


def _transacao_factory(importacao, conta, **kwargs):
    """Cria transacao com defaults razoaveis e hash unico.

    Chaves nomeadas aceitas: data, historico, descricao, historico_completo,
    valor, tipo, status, categoria_id, membro_id, excluir_relatorio,
    hash_transacao (se nao informado, auto-gera).
    """
    defaults = {
        'importacao_id': importacao.id,
        'conta_id': conta.id,
        'data': date(2026, 4, 1),
        'historico': 'TESTE PADRAO',
        'descricao': None,
        'historico_completo': None,  # sera derivado de historico se nao informado
        'valor': Decimal('100.00'),
        'tipo': 'debito',
        'status': 'PENDENTE',
        'excluir_relatorio': False,
    }
    defaults.update(kwargs)

    # historico_completo default = historico
    if defaults.get('historico_completo') is None:
        defaults['historico_completo'] = defaults['historico']

    # hash unico se nao fornecido
    if not defaults.get('hash_transacao'):
        defaults['hash_transacao'] = (
            f"hash_{defaults['data']}_{defaults['historico']}_{defaults['valor']}"
        )

    t = PessoalTransacao(**defaults)
    _db.session.add(t)
    _db.session.commit()
    return t


@pytest.fixture
def make_transacao(db, importacao, conta):
    """Factory para criar transacoes customizadas no teste."""
    def _factory(**kwargs):
        return _transacao_factory(importacao, conta, **kwargs)
    return _factory


@pytest.fixture
def client_autorizado(app, client, monkeypatch):
    """Client com pode_acessar_pessoal=True (bypass da lista de IDs)."""
    monkeypatch.setattr(
        'app.pessoal.routes.transacoes.pode_acessar_pessoal',
        lambda user: True,
    )
    return client
