"""
Microsoft Graph API Client — Minimal
=====================================

Cliente minimalista para Microsoft Graph API v1.0, focado em leitura de email.
Autenticacao via `client_credentials` flow (app-only, sem usuario interativo).

Requisitos:
-----------
- Lib: `msal` (no requirements.txt)
- Azure AD App Registration com permissao de API (Application):
  - `Mail.Read` concedida pelo admin do tenant
- Variaveis de ambiente:
  - GRAPH_TENANT_ID
  - GRAPH_CLIENT_ID
  - GRAPH_CLIENT_SECRET

Uso basico:
-----------
    from app.utils.graph_client import GraphClient

    gc = GraphClient()
    folder_id = gc.obter_pasta_id(upn='fiscal@empresa.com', folder_name='CTe Cancelados')
    mensagens = gc.listar_emails_pasta(
        upn='fiscal@empresa.com',
        folder_id=folder_id,
        unread_only=True,
        top=50,
    )
    for msg in mensagens:
        attachments = gc.listar_anexos(upn='fiscal@empresa.com', message_id=msg['id'])
        for att in attachments:
            if att['name'].lower().endswith('.xml'):
                xml_bytes = gc.baixar_anexo(
                    upn='fiscal@empresa.com',
                    message_id=msg['id'],
                    attachment_id=att['id'],
                )
        gc.marcar_como_lido(upn='fiscal@empresa.com', message_id=msg['id'])

Data: 2026-04-09
Referencia: https://learn.microsoft.com/en-us/graph/api/resources/message
"""

import base64
import logging
import os
import time
from datetime import datetime, timezone
from typing import List, Optional, Union

import requests

logger = logging.getLogger(__name__)

GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'
GRAPH_SCOPE = ['https://graph.microsoft.com/.default']

# Timeouts generosos (em segundos)
HTTP_TIMEOUT_CONNECT = 10
HTTP_TIMEOUT_READ = 60

# Retry em caso de 429 (rate limit) ou 5xx
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # segundos


class GraphClientError(Exception):
    """Erro generico do GraphClient."""


class GraphAuthError(GraphClientError):
    """Falha de autenticacao no Microsoft Graph."""


class GraphNotFoundError(GraphClientError):
    """Recurso nao encontrado (pasta, mensagem, anexo)."""


class GraphClient:
    """
    Cliente minimal para Microsoft Graph API.

    Instancia unica por processo (token cacheado em memoria).
    Thread-safe? NAO — usar uma instancia por thread se precisar paralelismo.
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """
        Args:
            tenant_id: override env GRAPH_TENANT_ID
            client_id: override env GRAPH_CLIENT_ID
            client_secret: override env GRAPH_CLIENT_SECRET
        """
        self.tenant_id = tenant_id or os.environ.get('GRAPH_TENANT_ID', '').strip()
        self.client_id = client_id or os.environ.get('GRAPH_CLIENT_ID', '').strip()
        self.client_secret = (
            client_secret or os.environ.get('GRAPH_CLIENT_SECRET', '').strip()
        )

        if not (self.tenant_id and self.client_id and self.client_secret):
            raise GraphAuthError(
                "GRAPH_TENANT_ID, GRAPH_CLIENT_ID e GRAPH_CLIENT_SECRET "
                "precisam estar configurados no ambiente"
            )

        # Cache do token (access_token, expires_at_epoch)
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

        # Cache lazy do MSAL ConfidentialClientApplication
        self._msal_app = None

    # ------------------------------------------------------------------
    # Autenticacao
    # ------------------------------------------------------------------

    def _get_msal_app(self):
        """Lazy import msal (evita dependencia rigida se modulo nao for usado)."""
        if self._msal_app is None:
            try:
                import msal  # type: ignore
            except ImportError as exc:
                raise GraphAuthError(
                    "Biblioteca 'msal' nao instalada. "
                    "Adicione 'msal' ao requirements.txt."
                ) from exc

            authority = f'https://login.microsoftonline.com/{self.tenant_id}'
            self._msal_app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=authority,
            )
        return self._msal_app

    def _get_token(self) -> str:
        """
        Obtem access_token usando client_credentials flow.
        Cacheia em memoria ate proximo do expirar (60s de folga).
        """
        now = time.time()
        if self._access_token and now < (self._token_expires_at - 60):
            return self._access_token

        app = self._get_msal_app()
        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)

        if not isinstance(result, dict) or 'access_token' not in result:
            err_desc = (
                result.get('error_description', 'resposta sem access_token')
                if isinstance(result, dict)
                else 'resposta invalida do MSAL'
            )
            raise GraphAuthError(
                f"Falha ao obter token de Microsoft Graph: {err_desc}"
            )

        access_token = result['access_token']
        if not isinstance(access_token, str) or not access_token:
            raise GraphAuthError(
                "Resposta MSAL retornou access_token invalido (nao-string ou vazio)"
            )
        self._access_token = access_token
        expires_in = int(result.get('expires_in', 3600))
        self._token_expires_at = now + expires_in
        logger.info(
            f"[GraphClient] Token obtido (expires_in={expires_in}s, "
            f"scope={result.get('token_source', 'client_credentials')})"
        )
        return access_token

    def _headers(self, extra: Optional[dict] = None) -> dict:
        h = {
            'Authorization': f'Bearer {self._get_token()}',
            'Accept': 'application/json',
        }
        if extra:
            h.update(extra)
        return h

    # ------------------------------------------------------------------
    # HTTP com retry
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
    ) -> requests.Response:
        """
        Request com retry em 429 e 5xx.
        """
        last_exc = None
        for tentativa in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.request(
                    method,
                    url,
                    params=params,
                    json=json_body,
                    headers=self._headers(extra_headers),
                    timeout=(HTTP_TIMEOUT_CONNECT, HTTP_TIMEOUT_READ),
                )
            except requests.RequestException as e:
                last_exc = e
                logger.warning(
                    f"[GraphClient] {method} {url} falhou (tentativa {tentativa}/{MAX_RETRIES}): {e}"
                )
                if tentativa < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_BASE ** tentativa)
                    continue
                raise GraphClientError(f"Erro HTTP: {e}") from e

            # 429 Too Many Requests ou 5xx
            if resp.status_code == 429 or resp.status_code >= 500:
                # Respeitar Retry-After se vier
                retry_after = resp.headers.get('Retry-After')
                delay = int(retry_after) if retry_after and retry_after.isdigit() else RETRY_BACKOFF_BASE ** tentativa
                logger.warning(
                    f"[GraphClient] {method} {url} retornou {resp.status_code}, "
                    f"aguardando {delay}s (tentativa {tentativa}/{MAX_RETRIES})"
                )
                if tentativa < MAX_RETRIES:
                    time.sleep(delay)
                    continue

            return resp

        # Se sair do loop sem retornar, nao deveria acontecer, mas por seguranca:
        if last_exc:
            raise GraphClientError(f"Todas as tentativas falharam: {last_exc}")
        raise GraphClientError("Requisicao falhou apos todos os retries")

    def _raise_for_status(self, resp: requests.Response, contexto: str):
        if resp.status_code == 404:
            raise GraphNotFoundError(f"{contexto}: 404 Not Found")
        if not resp.ok:
            try:
                err = resp.json()
            except ValueError:
                err = {'text': resp.text[:500]}
            raise GraphClientError(
                f"{contexto}: HTTP {resp.status_code} — {err}"
            )

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------

    @staticmethod
    def _odata_escape(value: str) -> str:
        """
        Escape de string para literal em filtro OData.
        Apenas aspas simples precisam ser escapadas (doubled: ' -> '').

        Exemplo: "XML CTe's" -> "XML CTe''s"
        """
        return (value or '').replace("'", "''")

    def obter_pasta_id(self, upn: str, folder_name: str) -> str:
        """
        Resolve nome OU path de pasta em folder_id.

        Suporta tres formatos:
        1. Nome simples na raiz ou Inbox (com fallback automatico):
           'CTe Cancelados' -> busca na raiz, depois como filha de Inbox
        2. Path hierarquico separado por '/':
           'Faturas/XML CTes' -> navega Faturas > XML CTes
           'Inbox/Faturas/XML CTes' -> navega Inbox > Faturas > XML CTes
        3. Nomes com apostrofo sao escapados automaticamente:
           "XML CTe's" funciona sem ajuste.

        Args:
            upn: user principal name da mailbox
            folder_name: nome simples ou path com '/' como separador

        Returns:
            ID da pasta final (ultimo segmento do path)

        Raises:
            GraphNotFoundError: se qualquer segmento do path nao existir.
        """
        # Path hierarquico: dividir e navegar
        if '/' in folder_name:
            partes = [p.strip() for p in folder_name.split('/') if p.strip()]
            if not partes:
                raise GraphNotFoundError(
                    f"Path vazio apos normalizar: {folder_name!r}"
                )

            # Primeiro segmento: raiz ou Inbox (com fallback)
            atual_id = self._buscar_folder_raiz_ou_inbox(upn, partes[0])

            # Segmentos seguintes: filhas do anterior
            for parte in partes[1:]:
                atual_id = self._buscar_child_folder(upn, atual_id, parte)

            logger.info(
                f"[GraphClient] Path '{folder_name}' resolvido: "
                f"folder_id={atual_id}"
            )
            return atual_id

        # Nome simples: raiz ou Inbox
        return self._buscar_folder_raiz_ou_inbox(upn, folder_name)

    def _buscar_folder_raiz_ou_inbox(self, upn: str, folder_name: str) -> str:
        """
        Busca pasta por nome primeiro na raiz, depois como filha da Inbox.
        Usado para o primeiro segmento de path ou nomes simples.
        """
        escaped = self._odata_escape(folder_name)

        # 1. Buscar nas pastas raiz
        url = f'{GRAPH_API_BASE}/users/{upn}/mailFolders'
        resp = self._request(
            'GET', url,
            params={
                '$filter': f"displayName eq '{escaped}'",
                '$top': '10',
            }
        )
        self._raise_for_status(resp, f"listar pastas de {upn}")
        for folder in resp.json().get('value', []):
            if folder.get('displayName') == folder_name:
                return folder['id']

        # 2. Fallback: buscar filhas da Inbox
        logger.info(
            f"[GraphClient] Pasta '{folder_name}' nao encontrada na raiz. "
            f"Buscando filhas da Inbox..."
        )
        url_inbox = f'{GRAPH_API_BASE}/users/{upn}/mailFolders/inbox/childFolders'
        resp = self._request(
            'GET', url_inbox,
            params={
                '$filter': f"displayName eq '{escaped}'",
                '$top': '10',
            }
        )
        self._raise_for_status(resp, f"listar filhas da Inbox de {upn}")
        for folder in resp.json().get('value', []):
            if folder.get('displayName') == folder_name:
                return folder['id']

        raise GraphNotFoundError(
            f"Pasta '{folder_name}' nao encontrada em {upn} "
            f"(nem na raiz nem como filha da Inbox). "
            f"Se a pasta e sub-pasta de outra, use path: 'Pai/{folder_name}'"
        )

    def _buscar_child_folder(
        self,
        upn: str,
        parent_folder_id: str,
        folder_name: str,
    ) -> str:
        """
        Busca uma pasta filha especifica dentro de um parent_folder_id.
        """
        escaped = self._odata_escape(folder_name)
        url = (
            f'{GRAPH_API_BASE}/users/{upn}/mailFolders/'
            f'{parent_folder_id}/childFolders'
        )
        resp = self._request(
            'GET', url,
            params={
                '$filter': f"displayName eq '{escaped}'",
                '$top': '10',
            }
        )
        self._raise_for_status(
            resp, f"listar filhas de pasta {parent_folder_id}"
        )
        for folder in resp.json().get('value', []):
            if folder.get('displayName') == folder_name:
                return folder['id']

        raise GraphNotFoundError(
            f"Sub-pasta '{folder_name}' nao encontrada dentro de "
            f"parent_id={parent_folder_id}"
        )

    def listar_emails_pasta(
        self,
        upn: str,
        folder_id: str,
        received_since: Optional[Union[datetime, str]] = None,
        unread_only: bool = False,
        top: int = 50,
    ) -> List[dict]:
        """
        Lista emails de uma pasta. Retorna lista de message resources.

        Args:
            upn: user principal name
            folder_id: ID da pasta (obtido via obter_pasta_id)
            received_since: filtra por receivedDateTime >= este valor.
                Aceita datetime (UTC preferencial) ou string ISO 8601.
                Este e o filtro PRINCIPAL do uso atual (janela temporal).
            unread_only: filtro adicional: apenas nao lidos (isRead eq false).
                Combina com received_since via AND se ambos forem passados.
                Default False — queremos TODOS os emails na janela, lidos ou nao.
            top: maximo de mensagens a retornar (cap em 50 por query)

        Returns:
            Lista de dicts (message resource do Graph API)
        """
        url = f'{GRAPH_API_BASE}/users/{upn}/mailFolders/{folder_id}/messages'
        params = {
            '$top': str(min(top, 50)),
            '$select': 'id,subject,from,receivedDateTime,hasAttachments,isRead',
            '$orderby': 'receivedDateTime desc',
        }

        # Montar filtros OData combinados
        filtros_odata = []
        if received_since is not None:
            iso_str = self._to_odata_datetime(received_since)
            filtros_odata.append(f'receivedDateTime ge {iso_str}')
        if unread_only:
            filtros_odata.append('isRead eq false')
        if filtros_odata:
            params['$filter'] = ' and '.join(filtros_odata)

        resp = self._request('GET', url, params=params)
        self._raise_for_status(resp, f"listar emails em pasta {folder_id}")
        data = resp.json()
        return data.get('value', [])

    @staticmethod
    def _to_odata_datetime(value: Union[datetime, str]) -> str:
        """
        Converte datetime ou string em literal OData para $filter.

        Formato esperado por Graph API: '2026-04-09T10:00:00Z' (UTC).

        Aceita:
        - datetime naive → assume UTC
        - datetime aware → converte para UTC
        - string ISO 8601 → passa-through (assume que ja esta no formato)
        """
        if isinstance(value, str):
            return value

        if not isinstance(value, datetime):
            raise TypeError(f"received_since deve ser datetime ou str, recebido: {type(value)}")

        if value.tzinfo is None:
            # Naive — assumir UTC
            dt_utc = value
        else:
            dt_utc = value.astimezone(timezone.utc).replace(tzinfo=None)

        return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')

    def listar_anexos(self, upn: str, message_id: str) -> List[dict]:
        """
        Lista metadata dos anexos de uma mensagem (sem baixar o conteudo).

        Returns:
            Lista de dicts com: id, name, contentType, size, @odata.type
        """
        url = f'{GRAPH_API_BASE}/users/{upn}/messages/{message_id}/attachments'
        # $select nao pega o contentBytes (dai ser leve)
        resp = self._request(
            'GET', url,
            params={'$select': 'id,name,contentType,size'},
        )
        self._raise_for_status(resp, f"listar anexos de mensagem {message_id}")
        return resp.json().get('value', [])

    def baixar_anexo(
        self,
        upn: str,
        message_id: str,
        attachment_id: str,
    ) -> bytes:
        """
        Baixa o conteudo binario de um anexo.

        Funciona para FileAttachment (maioria dos XMLs vem assim).
        Para ItemAttachment (email dentro de email) esta fora do escopo da v1.

        Returns:
            bytes do anexo.
        """
        url = (
            f'{GRAPH_API_BASE}/users/{upn}/messages/{message_id}'
            f'/attachments/{attachment_id}'
        )
        resp = self._request('GET', url)
        self._raise_for_status(resp, f"baixar anexo {attachment_id}")
        data = resp.json()

        odata_type = (data.get('@odata.type') or '').lower()
        if 'fileattachment' not in odata_type:
            raise GraphClientError(
                f"Anexo {attachment_id} nao e FileAttachment "
                f"(tipo={data.get('@odata.type')}). "
                f"ItemAttachment nao suportado nesta versao."
            )

        content_b64 = data.get('contentBytes')
        if not content_b64:
            raise GraphClientError(
                f"Anexo {attachment_id} sem contentBytes"
            )

        try:
            return base64.b64decode(content_b64)
        except Exception as e:
            raise GraphClientError(
                f"Erro ao decodificar base64 do anexo {attachment_id}: {e}"
            ) from e

    def marcar_como_lido(self, upn: str, message_id: str) -> None:
        """
        Marca mensagem como lida (isRead=true) via PATCH.
        Falha silenciosa: loga warning mas nao raise.
        """
        url = f'{GRAPH_API_BASE}/users/{upn}/messages/{message_id}'
        try:
            resp = self._request(
                'PATCH', url,
                json_body={'isRead': True},
                extra_headers={'Content-Type': 'application/json'},
            )
            if not resp.ok:
                logger.warning(
                    f"[GraphClient] Falha ao marcar mensagem {message_id} "
                    f"como lida: {resp.status_code}"
                )
        except GraphClientError as e:
            logger.warning(
                f"[GraphClient] Erro ao marcar mensagem {message_id} como lida: {e}"
            )

    def mover_mensagem(
        self,
        upn: str,
        message_id: str,
        destino_folder_id: str,
    ) -> Optional[str]:
        """
        Move uma mensagem para outra pasta.

        NAO e usado na v1 do job (preferimos marcar como lido), mas disponivel
        para uso futuro (ex: mover para 'Processados' ou 'Erros').

        Returns:
            ID da nova mensagem no destino, ou None se falhou.
        """
        url = f'{GRAPH_API_BASE}/users/{upn}/messages/{message_id}/move'
        try:
            resp = self._request(
                'POST', url,
                json_body={'destinationId': destino_folder_id},
                extra_headers={'Content-Type': 'application/json'},
            )
            if resp.ok:
                return resp.json().get('id')
            logger.warning(
                f"[GraphClient] Falha ao mover mensagem {message_id}: "
                f"{resp.status_code}"
            )
            return None
        except GraphClientError as e:
            logger.warning(f"[GraphClient] Erro ao mover mensagem {message_id}: {e}")
            return None
