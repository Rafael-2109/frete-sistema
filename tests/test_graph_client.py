"""
Testes do GraphClient (Microsoft Graph API minimal).

Todos mockados — nao chamam a rede. Focam no comportamento de:
- Validacao de config
- Cacheamento de token
- Retry em 429/5xx
- Decodificacao base64 de anexos
"""

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.utils.graph_client import (
    GraphClient,
    GraphAuthError,
    GraphClientError,
    GraphNotFoundError,
)


# ======================================================================
# Fixture que injeta env vars mockadas
# ======================================================================


@pytest.fixture
def graph_env(monkeypatch):
    monkeypatch.setenv('GRAPH_TENANT_ID', 'tenant-guid-fake')
    monkeypatch.setenv('GRAPH_CLIENT_ID', 'client-guid-fake')
    monkeypatch.setenv('GRAPH_CLIENT_SECRET', 'secret-fake')


@pytest.fixture
def graph_client(graph_env):
    """GraphClient com MSAL mockado que sempre retorna token valido."""
    with patch('msal.ConfidentialClientApplication') as mock_msal:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = {
            'access_token': 'fake-access-token',
            'expires_in': 3600,
            'token_source': 'client_credentials',
        }
        mock_msal.return_value = mock_app
        client = GraphClient()
        yield client


# ======================================================================
# Auth
# ======================================================================


class TestAuth:
    def test_raise_sem_env_vars(self, monkeypatch):
        monkeypatch.delenv('GRAPH_TENANT_ID', raising=False)
        monkeypatch.delenv('GRAPH_CLIENT_ID', raising=False)
        monkeypatch.delenv('GRAPH_CLIENT_SECRET', raising=False)
        with pytest.raises(GraphAuthError):
            GraphClient()

    def test_raise_com_env_parcial(self, monkeypatch):
        monkeypatch.setenv('GRAPH_TENANT_ID', 'x')
        monkeypatch.setenv('GRAPH_CLIENT_ID', 'y')
        monkeypatch.delenv('GRAPH_CLIENT_SECRET', raising=False)
        with pytest.raises(GraphAuthError):
            GraphClient()

    def test_token_e_cacheado(self, graph_client):
        t1 = graph_client._get_token()
        t2 = graph_client._get_token()
        assert t1 == t2 == 'fake-access-token'
        # Deve chamar acquire_token apenas 1 vez (cache)
        assert graph_client._msal_app.acquire_token_for_client.call_count == 1

    def test_msal_retorna_erro_raise(self, graph_env):
        with patch('msal.ConfidentialClientApplication') as mock_msal:
            mock_app = MagicMock()
            mock_app.acquire_token_for_client.return_value = {
                'error': 'invalid_client',
                'error_description': 'Client credenciais invalidas',
            }
            mock_msal.return_value = mock_app
            client = GraphClient()
            with pytest.raises(GraphAuthError, match='Client credenciais'):
                client._get_token()


# ======================================================================
# Listagem de emails
# ======================================================================


class TestListarEmails:
    def test_listar_emails_retorna_value(self, graph_client):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.ok = True
        fake_response.json.return_value = {
            'value': [
                {'id': 'msg1', 'subject': 'Teste 1'},
                {'id': 'msg2', 'subject': 'Teste 2'},
            ]
        }

        with patch('requests.request', return_value=fake_response) as mock_req:
            emails = graph_client.listar_emails_pasta(
                upn='test@empresa.com',
                folder_id='folder123',
                unread_only=True,
                top=50,
            )

        assert len(emails) == 2
        assert emails[0]['subject'] == 'Teste 1'

        # Verificar que $filter foi passado
        call_kwargs = mock_req.call_args.kwargs
        assert call_kwargs['params']['$filter'] == 'isRead eq false'
        assert call_kwargs['params']['$top'] == '50'

    def test_listar_emails_sem_unread_filter(self, graph_client):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.ok = True
        fake_response.json.return_value = {'value': []}

        with patch('requests.request', return_value=fake_response) as mock_req:
            graph_client.listar_emails_pasta(
                upn='test@empresa.com',
                folder_id='folder123',
                unread_only=False,
            )

        call_kwargs = mock_req.call_args.kwargs
        assert '$filter' not in call_kwargs['params']


# ======================================================================
# Resolucao de pasta por nome
# ======================================================================


class TestObterPastaId:
    def test_encontra_na_raiz(self, graph_client):
        resp_raiz = MagicMock()
        resp_raiz.status_code = 200
        resp_raiz.ok = True
        resp_raiz.json.return_value = {
            'value': [{'id': 'folder-id-abc', 'displayName': 'CTe Cancelados'}]
        }
        with patch('requests.request', return_value=resp_raiz):
            folder_id = graph_client.obter_pasta_id(
                upn='test@empresa.com',
                folder_name='CTe Cancelados',
            )
        assert folder_id == 'folder-id-abc'

    def test_fallback_filha_inbox(self, graph_client):
        resp_raiz_vazia = MagicMock()
        resp_raiz_vazia.status_code = 200
        resp_raiz_vazia.ok = True
        resp_raiz_vazia.json.return_value = {'value': []}

        resp_inbox_match = MagicMock()
        resp_inbox_match.status_code = 200
        resp_inbox_match.ok = True
        resp_inbox_match.json.return_value = {
            'value': [{'id': 'folder-inbox-child', 'displayName': 'CTe Cancelados'}]
        }

        with patch(
            'requests.request',
            side_effect=[resp_raiz_vazia, resp_inbox_match],
        ):
            folder_id = graph_client.obter_pasta_id(
                upn='test@empresa.com',
                folder_name='CTe Cancelados',
            )
        assert folder_id == 'folder-inbox-child'

    def test_nao_encontra_raise(self, graph_client):
        resp_vazia = MagicMock()
        resp_vazia.status_code = 200
        resp_vazia.ok = True
        resp_vazia.json.return_value = {'value': []}

        with patch('requests.request', return_value=resp_vazia):
            with pytest.raises(GraphNotFoundError):
                graph_client.obter_pasta_id(
                    upn='test@empresa.com',
                    folder_name='Pasta Inexistente',
                )


# ======================================================================
# Download de anexos
# ======================================================================


class TestBaixarAnexo:
    def test_baixa_e_decodifica_base64(self, graph_client):
        xml_bytes_original = b'<cteProc xmlns="http://example.com"/>'
        xml_b64 = base64.b64encode(xml_bytes_original).decode('ascii')

        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.ok = True
        fake_response.json.return_value = {
            '@odata.type': '#microsoft.graph.fileAttachment',
            'contentBytes': xml_b64,
            'name': 'teste.xml',
        }

        with patch('requests.request', return_value=fake_response):
            resultado = graph_client.baixar_anexo(
                upn='test@empresa.com',
                message_id='msg1',
                attachment_id='att1',
            )

        assert resultado == xml_bytes_original

    def test_item_attachment_raise(self, graph_client):
        fake_response = MagicMock()
        fake_response.status_code = 200
        fake_response.ok = True
        fake_response.json.return_value = {
            '@odata.type': '#microsoft.graph.itemAttachment',
            'contentBytes': None,
        }

        with patch('requests.request', return_value=fake_response):
            with pytest.raises(GraphClientError, match='ItemAttachment'):
                graph_client.baixar_anexo(
                    upn='test@empresa.com',
                    message_id='msg1',
                    attachment_id='att1',
                )


# ======================================================================
# Retry em 429 / 5xx
# ======================================================================


class TestRetry:
    def test_retry_em_429_entao_sucesso(self, graph_client):
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.ok = False
        resp_429.headers = {'Retry-After': '1'}

        resp_ok = MagicMock()
        resp_ok.status_code = 200
        resp_ok.ok = True
        resp_ok.json.return_value = {'value': []}

        with patch(
            'requests.request',
            side_effect=[resp_429, resp_ok],
        ):
            with patch('time.sleep'):  # acelerar
                result = graph_client.listar_emails_pasta(
                    upn='test@empresa.com',
                    folder_id='f',
                )
        assert result == []
