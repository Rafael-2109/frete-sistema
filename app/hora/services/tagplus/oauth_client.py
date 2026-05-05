"""OAuth2 com persistencia em DB (espelha oauth2_v2.py mas SEM session Flask).

Diferenca chave: tokens vivem em `hora_tagplus_token`, encriptados. Funciona em
worker RQ (sem request ativo). Lock pessimista no refresh para serializar
workers concorrentes (TagPlus invalida refresh_token apos uso).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import urlencode

import requests

from app import db
from app.hora.models.tagplus import HoraTagPlusConta, HoraTagPlusToken
from app.hora.services.tagplus.crypto import decrypt, encrypt
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class OAuthClient:
    AUTH_URL = 'https://developers.tagplus.com.br/authorize'
    TOKEN_URL = 'https://api.tagplus.com.br/oauth2/token'

    # Margem antes de expirar para considerar token vivo (evita 401 em meio de request).
    EXPIRY_MARGIN = timedelta(minutes=5)

    def __init__(self, conta: HoraTagPlusConta):
        self.conta = conta
        # Snapshot do PK — usado por `_ensure_conta_attached` para re-buscar
        # a conta apos `db.engine.dispose()` no recovery do backfill.
        # `self.conta.id` continua acessivel mesmo em DETACHED state, mas
        # guardar o ID separado evita qualquer chance de NotFoundError.
        self._conta_id = conta.id

    def _ensure_conta_attached(self) -> HoraTagPlusConta:
        """Re-vincula `self.conta` a sessao corrente se ficou DETACHED.

        O backfill TagPlus faz `db.session.close()` + `db.engine.dispose()` em
        `_importar_com_retry_db` para recuperar de SSL drop no Postgres do
        Render. Apos o dispose, qualquer objeto carregado anteriormente fica
        DETACHED — a proxima leitura lazy de relationship (ex.: `conta.token`)
        levanta `DetachedInstanceError`.

        Aqui re-buscamos a conta da sessao corrente para restaurar o vinculo.
        Idempotente: se ja esta atachada, no-op.
        """
        from sqlalchemy import inspect as sa_inspect

        try:
            state = sa_inspect(self.conta)
            if not state.detached:
                return self.conta
        except Exception:
            # Falha na inspecao: melhor recarregar do que arriscar.
            pass

        recarregada = db.session.get(HoraTagPlusConta, self._conta_id)
        if recarregada is None:
            raise RuntimeError(
                f'HoraTagPlusConta {self._conta_id} sumiu do banco apos recovery.'
            )
        self.conta = recarregada
        return self.conta

    # ----- Authorization Code flow -----

    def get_authorization_url(self, state: str) -> str:
        """URL para redirecionar o usuario ao TagPlus para autorizar."""
        self._ensure_conta_attached()
        params = {
            'response_type': 'code',
            'client_id': self.conta.client_id,
            'scope': self.conta.scope_contratado,
            'state': state,
        }
        # NOTA: redirect_uri NAO e aceito como query param (scripts/guia.md:181).
        # E configurado uma vez no portal developers.tagplus.com.br.
        return f'{self.AUTH_URL}?{urlencode(params)}'

    def exchange_code(self, code: str) -> HoraTagPlusToken:
        """Troca authorization_code por access/refresh tokens."""
        self._ensure_conta_attached()
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.conta.client_id,
            'client_secret': decrypt(self.conta.client_secret_encrypted),
        }
        r = requests.post(
            self.TOKEN_URL,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30,
        )
        r.raise_for_status()
        return self._save_token(r.json())

    # ----- Refresh -----

    def refresh_if_needed(self) -> HoraTagPlusToken:
        """Retorna token valido. Refresh se faltar < EXPIRY_MARGIN."""
        self._ensure_conta_attached()
        # Query explicita em vez de `self.conta.token` (lazy load) — ja que
        # garantimos a sessao acima, ambos funcionariam, mas a query explicita
        # eh mais defensiva e nao depende do relationship estar carregado.
        token = (
            HoraTagPlusToken.query.filter_by(conta_id=self._conta_id).first()
        )
        if token and token.expires_at > agora_utc_naive() + self.EXPIRY_MARGIN:
            return token
        return self._do_refresh()

    def _do_refresh(self) -> HoraTagPlusToken:
        """Refresh com lock pessimista (FOR UPDATE) para serializar workers."""
        self._ensure_conta_attached()
        token = (
            HoraTagPlusToken.query
            .filter_by(conta_id=self._conta_id)
            .with_for_update()
            .first()
        )
        if not token:
            raise RuntimeError(
                f'Conta {self._conta_id} sem token. Refazer OAuth em /hora/tagplus/conta/oauth'
            )

        # Re-check apos lock: outro worker pode ter refreshed enquanto esperavamos.
        if token.expires_at > agora_utc_naive() + self.EXPIRY_MARGIN:
            return token

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': decrypt(token.refresh_token_encrypted),
            'client_id': self.conta.client_id,
            'client_secret': decrypt(self.conta.client_secret_encrypted),
        }
        r = requests.post(
            self.TOKEN_URL,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30,
        )
        if r.status_code != 200:
            logger.error(
                'TagPlus refresh falhou: status=%s body=%s',
                r.status_code, r.text[:500],
            )
            r.raise_for_status()
        return self._save_token(r.json())

    # ----- Persistencia -----

    def _save_token(self, body: dict) -> HoraTagPlusToken:
        self._ensure_conta_attached()
        expires_in = int(body.get('expires_in', 86400))
        expires_at = agora_utc_naive() + timedelta(seconds=expires_in)

        # Query explicita (em vez de `self.conta.token` lazy) por defesa em
        # profundidade — _ensure_conta_attached ja garantiu sessao viva.
        token = (
            HoraTagPlusToken.query.filter_by(conta_id=self._conta_id).first()
        )
        is_new = token is None
        if is_new:
            token = HoraTagPlusToken(conta_id=self._conta_id)
            db.session.add(token)

        token.access_token_encrypted = encrypt(body['access_token'])
        if body.get('refresh_token'):
            # TagPlus pode ou nao retornar refresh_token novo.
            token.refresh_token_encrypted = encrypt(body['refresh_token'])
        token.token_type = body.get('token_type', 'bearer')
        token.expires_at = expires_at
        # Persistir scope retornado pelo TagPlus. Pode divergir de
        # conta.scope_contratado se admin atualizou contratado mas ainda nao
        # reautorizou (refresh_token NAO re-emite scope — RFC OAuth2).
        scope_resp = body.get('scope')
        if scope_resp:
            token.scope_efetivo = scope_resp.strip()[:255]
        if not is_new:
            token.refreshed_em = agora_utc_naive()

        db.session.commit()
        logger.info(
            'TagPlus token %s salvo conta=%s expires_at=%s',
            'criado' if is_new else 'refreshed',
            self._conta_id, expires_at,
        )
        return token

    def get_access_token_plain(self) -> str:
        """Retorna access_token em plaintext para uso em Authorization header."""
        token = self.refresh_if_needed()
        return decrypt(token.access_token_encrypted)
