"""
Configuração de fixtures para testes

Este arquivo contém fixtures compartilhadas entre todos os testes.

IMPORTANTE: Os testes usam PostgreSQL pois o sistema usa tipos específicos
do PostgreSQL (JSONB, etc) que não funcionam com SQLite.

Os testes são executados em transações que são revertidas após cada teste,
garantindo isolamento e sem afetar dados de produção.
"""
import os
import pytest
from datetime import datetime
from decimal import Decimal

# NÃO sobrescrever DATABASE_URL - usar o PostgreSQL local
os.environ['TESTING'] = 'true'

# Desabilitar Sentry nos testes. create_app() chama load_dotenv(), que sobe a
# arvore de diretorios e acha o .env da raiz — ativando o profiler do Sentry
# (profiles_sample_rate=0.1). O profiler amostra stacks durante compile()/
# ast.parse das rotas (werkzeug) e contribui para SIGSEGV flaky. Testes nao
# precisam de APM/profiler. Forcar vazio ANTES de importar `app` garante que
# `if _sentry_dsn:` (app/__init__.py) seja falso. load_dotenv(override=False)
# preserva este valor (nao sobrescreve var ja definida no ambiente).
os.environ['SENTRY_DSN'] = ''

# Code review fix (2026-05-13): removido `pytest_plugins = ['tests.motos_assai.conftest']`
# que causava "Plugin already registered under a different name" em pytest 8.4+.
# Pytest carrega o conftest local automaticamente quando coleta testes da subpasta.
# Tests/skills/motos_assai tem seu proprio conftest.py — sem dependencia cruzada.

from app import create_app, db as _db


@pytest.fixture(scope='session')
def app():
    """
    Cria uma instância da aplicação configurada para testes.

    Escopo: session (uma vez por sessão de testes)

    NOTA: Usa PostgreSQL local para compatibilidade com tipos PostgreSQL.
    """
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
        'LOGIN_DISABLED': True,
        # Não precisa especificar DATABASE_URL - usa o do ambiente
    })

    return app


@pytest.fixture(scope='function')
def db(app):
    """
    Fornece o banco com isolamento por SAVEPOINT robusto.

    Escopo: function (para cada teste)

    Padrao SQLAlchemy 2.0 "join session into external transaction":
      - uma conexao dedicada abre UMA transacao externa real;
      - a session do Flask-SQLAlchemy e religada a essa conexao com
        join_transaction_mode="create_savepoint";
      - QUALQUER db.session.commit() de service (HORA, Motos Assai) vira
        commit de SAVEPOINT (NAO promove a transacao externa) e um novo
        savepoint e aberto automaticamente na proxima operacao;
      - no teardown, rollback da transacao externa desfaz TUDO.

    Antes (begin_nested + rollback simples), um commit() de service promovia
    a transacao externa e os dados de teste PERSISTIAM, acumulando entre runs
    (colisoes de unique, paginacao/listagem afetadas por residuo).
    """
    from sqlalchemy.orm import scoped_session, sessionmaker

    with app.app_context():
        connection = _db.engine.connect()
        transaction = connection.begin()

        TestingSession = scoped_session(sessionmaker(
            bind=connection,
            join_transaction_mode="create_savepoint",
        ))
        original_session = _db.session
        _db.session = TestingSession

        try:
            yield _db
        finally:
            TestingSession.remove()
            if transaction.is_active:
                transaction.rollback()
            connection.close()
            _db.session = original_session


@pytest.fixture(scope='function')
def client(app):
    """
    Cliente de teste para fazer requisições HTTP.

    Escopo: function (para cada teste)
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    Runner para testar comandos CLI.

    Escopo: function (para cada teste)
    """
    return app.test_cli_runner()


# ============================================================================
# FIXTURES ESPECÍFICAS DO MÓDULO PALLET
# ============================================================================

@pytest.fixture
def dados_nf_remessa():
    """
    Dados padrão para criar uma NF de remessa.
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    return {
        'numero_nf': f'TEST{unique_id}',
        'serie': '1',
        'chave_nfe': f'35260112345678000112550010{unique_id}1234567890',
        'data_emissao': datetime(2026, 1, 25, 10, 0, 0),
        'quantidade': 30,
        'empresa': 'CD',
        'tipo_destinatario': 'TRANSPORTADORA',
        'cnpj_destinatario': '12345678000199',
        'nome_destinatario': 'Transportadora Teste LTDA',
        'cnpj_transportadora': None,
        'nome_transportadora': None,
        'valor_unitario': Decimal('35.00'),
        'valor_total': Decimal('1050.00'),
        'odoo_account_move_id': 12345,
        'odoo_picking_id': 54321,
        'observacao': 'NF de teste',
    }


@pytest.fixture
def dados_nf_remessa_cliente():
    """
    Dados padrão para criar uma NF de remessa para cliente.
    """
    import uuid
    unique_id = str(uuid.uuid4())[:8]

    return {
        'numero_nf': f'CTEST{unique_id}',
        'serie': '1',
        'chave_nfe': f'35260198765432000199550010{unique_id}1234567890',
        'data_emissao': datetime(2026, 1, 25, 10, 0, 0),
        'quantidade': 20,
        'empresa': 'FB',
        'tipo_destinatario': 'CLIENTE',
        'cnpj_destinatario': '98765432000155',
        'nome_destinatario': 'Cliente Teste LTDA',
        'cnpj_transportadora': '12345678000199',
        'nome_transportadora': 'Transportadora Teste LTDA',
        'valor_unitario': Decimal('35.00'),
        'valor_total': Decimal('700.00'),
        'odoo_account_move_id': 67890,
        'odoo_picking_id': 9876,
        'observacao': 'NF de teste para cliente',
    }


@pytest.fixture
def criar_nf_remessa(db, dados_nf_remessa):
    """
    Factory fixture para criar NF de remessa.

    Uso:
        nf = criar_nf_remessa()  # Usa dados padrão
        nf = criar_nf_remessa(quantidade=50)  # Sobrescreve quantidade
    """
    def _criar(**kwargs):
        from app.pallet.services.nf_service import NFService

        # Merge com dados padrão
        dados = dados_nf_remessa.copy()

        # Gerar chave única se estiver criando múltiplas NFs
        if 'numero_nf' not in kwargs:
            import uuid
            unique_id = str(uuid.uuid4())[:10]
            dados['numero_nf'] = f'T{unique_id}'
            dados['chave_nfe'] = f'3526011234567800011255001000{unique_id}'

        dados.update(kwargs)

        return NFService.importar_nf_remessa_odoo(dados, usuario='test_user')

    return _criar


@pytest.fixture
def criar_credito(db, criar_nf_remessa):
    """
    Factory fixture para criar crédito a partir de NF de remessa.

    Uso:
        nf, credito = criar_credito()  # Cria NF + crédito
        nf, credito = criar_credito(quantidade=50)  # Com quantidade específica
    """
    def _criar(**kwargs):
        from app.pallet.models.credito import PalletCredito

        # Criar NF de remessa (já cria crédito automaticamente)
        nf_remessa = criar_nf_remessa(**kwargs)

        # Buscar crédito associado
        credito = PalletCredito.query.filter_by(
            nf_remessa_id=nf_remessa.id,
            ativo=True
        ).first()

        return nf_remessa, credito

    return _criar
