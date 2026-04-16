"""
Odoo Injector — State Machine com retry e checkpoints
======================================================

Injeta remessa CNAB VORTX no Odoo em 3 etapas com checkpointing:
    CNAB_GERADO -> ESCRITURAL_OK -> REMESSA_OK -> TITULOS_OK -> CONCLUIDO

Cada etapa e idempotente: verifica se o trabalho ja foi feito antes de criar.
Em falha, salva estado parcial para retomada posterior.

Usa _call_odoo_with_retry() para resiliencia contra 502/503/504 transientes.
"""

import base64
import uuid
import time
import logging

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry wrapper
# ---------------------------------------------------------------------------

MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]


WRITE_METHODS = {'create', 'write', 'unlink'}


def _call_odoo_with_retry(odoo, model, method, *args, **kwargs):
    """Wrapper que retenta chamadas Odoo em erros transientes (502/503/504).
    NAO retenta create/write/unlink — 502 em create pode significar sucesso (O6 gotcha).
    """
    for attempt in range(MAX_RETRIES):
        try:
            return odoo.execute_kw(model, method, *args, **kwargs)
        except Exception as e:
            err_str = str(e)
            is_transient = any(
                code in err_str
                for code in ['502', '503', '504', 'ConnectionError',
                             'TimeoutError', 'Connection refused']
            )
            if method in WRITE_METHODS:
                logger.error(
                    f'Odoo error on {method} (NOT retrying to avoid duplicates): '
                    f'{err_str[:200]}'
                )
                raise
            if is_transient and attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(
                    f'Odoo transient error (attempt {attempt + 1}/{MAX_RETRIES}), '
                    f'retry in {delay}s: {err_str[:200]}'
                )
                time.sleep(delay)
            else:
                raise


# ---------------------------------------------------------------------------
# OdooInjector — State Machine
# ---------------------------------------------------------------------------

class OdooInjector:
    """Avanca um RemessaVortxCache pelas etapas de injecao no Odoo."""

    def __init__(self, cache_record):
        self.cache = cache_record

    def _get_odoo(self):
        """Lazy import + authenticate (project convention: imports Odoo dentro de metodos)."""
        from app.odoo.utils.connection import get_odoo_connection
        conn = get_odoo_connection()
        conn.authenticate()
        return conn

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def executar(self):
        """
        Executa a state machine de injecao.

        Returns:
            dict com 'success' (bool), 'etapa' (str) e opcionalmente 'error' (str).
        """
        try:
            if self.cache.etapa in ('CNAB_GERADO', 'FALHA_ESCRITURAL'):
                self._etapa_escritural()

            if self.cache.etapa in ('ESCRITURAL_OK', 'FALHA_REMESSA'):
                self._etapa_remessa()

            if self.cache.etapa in ('REMESSA_OK', 'FALHA_TITULOS'):
                self._etapa_titulos()

            if self.cache.etapa == 'TITULOS_OK':
                self.cache.etapa = 'CONCLUIDO'
                self.cache.concluido_em = agora_utc_naive()
                db.session.commit()

            return {'success': True, 'etapa': self.cache.etapa}

        except Exception as e:
            self.cache.tentativas += 1
            self.cache.ultimo_erro = str(e)[:2000]
            db.session.commit()
            logger.error(
                f'Falha injecao Odoo (etapa={self.cache.etapa}, '
                f'tentativa={self.cache.tentativas}): {e}'
            )
            return {
                'success': False,
                'etapa': self.cache.etapa,
                'error': str(e)[:500],
            }

    # ------------------------------------------------------------------
    # Etapa 1: Escritural
    # ------------------------------------------------------------------

    def _etapa_escritural(self):
        """Cria arquivo.cobranca.escritural no Odoo."""
        odoo = self._get_odoo()

        # Idempotencia: verificar se ja existe e tem arquivo
        if self.cache.odoo_escritural_id:
            try:
                existing = _call_odoo_with_retry(
                    odoo,
                    'l10n_br_ciel_it_account.arquivo.cobranca.escritural',
                    'read',
                    [[self.cache.odoo_escritural_id]],
                    {'fields': ['id', 'arquivo_remessa']},
                )
                if existing and existing[0].get('arquivo_remessa'):
                    logger.info(
                        f'Escritural {self.cache.odoo_escritural_id} ja existe '
                        f'com arquivo — skip'
                    )
                    self.cache.etapa = 'ESCRITURAL_OK'
                    db.session.commit()
                    return
            except Exception:
                logger.warning(
                    f'Falha ao verificar escritural {self.cache.odoo_escritural_id} '
                    f'existente — abortando para evitar duplicata'
                )
                raise

        try:
            arquivo_b64 = base64.b64encode(self.cache.arquivo_cnab).decode('ascii')

            escritural_id = _call_odoo_with_retry(
                odoo,
                'l10n_br_ciel_it_account.arquivo.cobranca.escritural',
                'create',
                [{
                    'arquivo_remessa': arquivo_b64,
                    'nome_arquivo_remessa': self.cache.nome_arquivo,
                    'l10n_br_tipo_cobranca_id': self.cache.tipo_cobranca_id_odoo,
                    'company_id': self.cache.company_id_odoo,
                }],
            )

            self.cache.odoo_escritural_id = escritural_id
            self.cache.etapa = 'ESCRITURAL_OK'
            db.session.commit()
            logger.info(f'Escritural criado: {escritural_id}')

        except Exception as e:
            self.cache.etapa = 'FALHA_ESCRITURAL'
            db.session.commit()
            raise

    # ------------------------------------------------------------------
    # Etapa 2: Remessa
    # ------------------------------------------------------------------

    def _etapa_remessa(self):
        """Cria arquivo.cobranca.remessa no Odoo."""
        odoo = self._get_odoo()

        # Idempotencia: verificar se ja existe
        if self.cache.odoo_remessa_id:
            try:
                existing = _call_odoo_with_retry(
                    odoo,
                    'l10n_br_ciel_it_account.arquivo.cobranca.remessa',
                    'read',
                    [[self.cache.odoo_remessa_id]],
                    {'fields': ['id']},
                )
                if existing:
                    logger.info(
                        f'Remessa {self.cache.odoo_remessa_id} ja existe — skip'
                    )
                    self.cache.etapa = 'REMESSA_OK'
                    db.session.commit()
                    return
            except Exception:
                logger.warning(
                    f'Falha ao verificar remessa {self.cache.odoo_remessa_id} '
                    f'existente — abortando para evitar duplicata'
                )
                raise

        try:
            arquivo_b64 = base64.b64encode(self.cache.arquivo_cnab).decode('ascii')

            remessa_id = _call_odoo_with_retry(
                odoo,
                'l10n_br_ciel_it_account.arquivo.cobranca.remessa',
                'create',
                [{
                    'content': arquivo_b64,
                    'nome_arquivo': self.cache.nome_arquivo,
                    'uniqueid': str(uuid.uuid4()),
                    'status': 'EMITIDO',
                    'l10n_br_tipo_cobranca_id': self.cache.tipo_cobranca_id_odoo,
                    'company_id': self.cache.company_id_odoo,
                    'created_at_full_date': agora_utc_naive().strftime('%d/%m/%Y %H:%M:%S'),
                }],
            )

            # Tentar setar download_url (nao-fatal se falhar)
            try:
                download_url = (
                    f'/web/content/'
                    f'l10n_br_ciel_it_account.arquivo.cobranca.remessa/'
                    f'{remessa_id}/content/{self.cache.nome_arquivo}'
                    f'?download=true'
                )
                _call_odoo_with_retry(
                    odoo,
                    'l10n_br_ciel_it_account.arquivo.cobranca.remessa',
                    'write',
                    [[remessa_id], {'download_url': download_url}],
                )
            except Exception as e_url:
                logger.warning(
                    f'Falha ao setar download_url na remessa {remessa_id} '
                    f'(nao-fatal): {e_url}'
                )

            self.cache.odoo_remessa_id = remessa_id
            self.cache.etapa = 'REMESSA_OK'
            db.session.commit()
            logger.info(f'Remessa criada: {remessa_id}')

        except Exception as e:
            self.cache.etapa = 'FALHA_REMESSA'
            db.session.commit()
            raise

    # ------------------------------------------------------------------
    # Etapa 3: Titulos (marcacao individual)
    # ------------------------------------------------------------------

    def _etapa_titulos(self):
        """Marca move_lines pendentes com escritural_id e nosso_numero."""
        pendentes = self.cache.get_move_line_ids_pendentes()
        if not pendentes:
            self.cache.etapa = 'TITULOS_OK'
            db.session.commit()
            return

        odoo = self._get_odoo()

        # Verificar quais ainda nao foram marcados no Odoo
        nao_marcados = _call_odoo_with_retry(
            odoo,
            'account.move.line',
            'search',
            [[
                ['id', 'in', pendentes],
                ['l10n_br_arquivo_cobranca_escritural_id', '=', False],
            ]],
        )

        if not nao_marcados:
            # Todos ja marcados
            self.cache.set_move_line_ids_pendentes([])
            marcados_existentes = self.cache.get_move_line_ids_marcados()
            self.cache.set_move_line_ids_marcados(
                list(set(marcados_existentes + pendentes))
            )
            self.cache.etapa = 'TITULOS_OK'
            db.session.commit()
            return

        mapa_nn = self.cache.get_mapa_nn_move_line()
        marcados = self.cache.get_move_line_ids_marcados()
        novos_marcados = []

        try:
            for ml_id in nao_marcados:
                vals = {
                    'l10n_br_arquivo_cobranca_escritural_id': self.cache.odoo_escritural_id,
                }
                # Nosso numero: chave do mapa e str(move_line_id)
                nn = mapa_nn.get(str(ml_id))
                if nn:
                    vals['l10n_br_cobranca_nossonumero'] = nn

                _call_odoo_with_retry(
                    odoo,
                    'account.move.line',
                    'write',
                    [[ml_id], vals],
                )
                novos_marcados.append(ml_id)

        except Exception as e:
            # Falha parcial: salvar progresso
            if novos_marcados:
                todos_marcados = list(set(marcados + novos_marcados))
                self.cache.set_move_line_ids_marcados(todos_marcados)
                ainda_pendentes = [
                    ml for ml in pendentes if ml not in todos_marcados
                ]
                self.cache.set_move_line_ids_pendentes(ainda_pendentes)

            self.cache.etapa = 'FALHA_TITULOS'
            db.session.commit()
            raise

        # Sucesso total
        todos_marcados = list(set(marcados + novos_marcados))
        self.cache.set_move_line_ids_marcados(todos_marcados)
        self.cache.set_move_line_ids_pendentes([])
        self.cache.etapa = 'TITULOS_OK'
        db.session.commit()
        logger.info(
            f'Titulos marcados: {len(novos_marcados)} de {len(nao_marcados)}'
        )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def buscar_titulos_pendentes(odoo, company_id: int, limit: int = 500) -> list:
    """Busca account.move.line pendentes de remessa VORTX no Odoo."""
    from app.financeiro.services.remessa_vortx.layout_vortx import TIPO_COBRANCA_IDS

    tipo_cob = TIPO_COBRANCA_IDS.get(company_id)
    if not tipo_cob:
        return []

    result = _call_odoo_with_retry(
        odoo,
        'account.move.line',
        'search_read',
        [[
            ['l10n_br_arquivo_cobranca_escritural_id', '=', False],
            ['l10n_br_cobranca_transmissao', '=', 'manual'],
            ['parent_state', '=', 'posted'],
            ['move_id.move_type', '=', 'out_invoice'],
            ['company_id', '=', company_id],
        ]],
        {
            'fields': [
                'id', 'move_id', 'name', 'date_maturity', 'debit',
                'partner_id', 'l10n_br_cobranca_nossonumero',
            ],
            'limit': limit,
        },
    )
    return result or []


def buscar_dados_sacado(odoo, partner_id: int) -> dict:
    """Busca dados do sacado (cliente) no res.partner para geracao CNAB."""
    partner = _call_odoo_with_retry(
        odoo,
        'res.partner',
        'read',
        [[partner_id]],
        {
            'fields': [
                'name', 'street', 'street2', 'city', 'zip',
                'l10n_br_cnpj', 'l10n_br_cpf', 'email', 'company_type',
            ],
        },
    )
    if not partner:
        return {}

    p = partner[0]

    cnpj_raw = (
        (p.get('l10n_br_cnpj') or p.get('l10n_br_cpf') or '')
        .replace('.', '').replace('/', '').replace('-', '')
    )
    tipo = '02' if p.get('company_type') == 'company' else '01'

    endereco = (
        (p.get('street') or '') + ', ' + (p.get('street2') or '')
    ).strip(', ')[:40]

    cep = (p.get('zip') or '00000000').replace('-', '').replace('.', '')
    if len(cep) < 8:
        cep = cep.zfill(8)

    return {
        'nome': (p.get('name') or '')[:40],
        'endereco': endereco,
        'cep_prefixo': cep[:5],
        'cep_sufixo': cep[5:8],
        'cnpj_cpf': cnpj_raw.zfill(14),
        'tipo_inscricao': tipo,
        'email': (p.get('email') or '')[:320],
    }
