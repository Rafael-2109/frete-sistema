"""
Odoo Cached Lookups — Cache Redis para dados estaticos/semi-estaticos do Odoo
==============================================================================

Cacheia automaticamente lookups frequentes que raramente mudam:
- res.partner (CNPJ, nome) — TTL 3600s (1h)
- account.journal (nome, tipo) — TTL 7200s (2h)
- account.account (codigo, nome) — TTL 7200s (2h)

USO:
    from app.odoo.utils.cached_lookups import OdooCachedLookup

    lookup = OdooCachedLookup()

    # Buscar partner por ID (cache automatico)
    partner = lookup.get_partner(partner_id)
    # {'id': 123, 'cnpj': '12.345.678/0001-99', 'name': 'Empresa X'}

    # Buscar batch de partners
    partners = lookup.get_partners_batch([1, 2, 3])
    # {1: {'id': 1, 'cnpj': ..., 'name': ...}, 2: ..., 3: ...}

    # Buscar journal por ID
    journal = lookup.get_journal(journal_id)

    # Buscar account por ID
    account = lookup.get_account(account_id)

    # Invalidar cache (apos mudancas no Odoo)
    lookup.invalidate_partner(partner_id)
    lookup.invalidate_all('partner')

NAO CACHEAR: Saldos, reconciliacoes, dados transacionais.
"""

import json
import logging
from typing import Dict, List, Optional, Any

from app.utils.redis_cache import RedisCache

logger = logging.getLogger(__name__)

# Singleton do cache Redis
_cache = None


def _get_cache():
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


# TTLs por tipo de entidade (segundos)
TTL_PARTNER = 3600    # 1 hora — partners podem mudar endereco
TTL_JOURNAL = 7200    # 2 horas — journals quase nunca mudam
TTL_ACCOUNT = 7200    # 2 horas — contas contabeis quase nunca mudam

# Prefixos de chave Redis
PREFIX_PARTNER = 'odoo:partner:'
PREFIX_JOURNAL = 'odoo:journal:'
PREFIX_ACCOUNT = 'odoo:account:'


class OdooCachedLookup:
    """Cache layer para lookups estaticos do Odoo."""

    def __init__(self, connection=None):
        """
        Args:
            connection: OdooConnection (lazy — busca automaticamente se None)
        """
        self._connection = connection

    def _get_connection(self):
        if self._connection is None:
            from app.odoo.utils.connection import get_odoo_connection
            self._connection = get_odoo_connection()
        return self._connection

    # ============================
    # res.partner
    # ============================

    def get_partner(self, partner_id: int) -> Optional[Dict]:
        """Busca partner por ID (cache automatico)."""
        if not partner_id:
            return None

        cache = _get_cache()
        key = f'{PREFIX_PARTNER}{partner_id}'

        # Tentar cache
        cached = cache.get(key)
        if cached:
            try:
                return json.loads(cached) if isinstance(cached, str) else cached
            except (json.JSONDecodeError, TypeError):
                pass

        # Cache miss — buscar no Odoo
        try:
            conn = self._get_connection()
            results = conn.read('res.partner', [partner_id],
                                fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_ie'])
            if results:
                data = {
                    'id': results[0]['id'],
                    'name': (results[0].get('name') or '').strip(),
                    'cnpj': (results[0].get('l10n_br_cnpj') or '').strip(),
                    'ie': (results[0].get('l10n_br_ie') or '').strip(),
                }
                cache.set(key, json.dumps(data), ttl=TTL_PARTNER)
                return data
        except Exception as e:
            logger.debug(f"Erro ao buscar partner {partner_id}: {e}")

        return None

    def get_partners_batch(self, partner_ids: List[int]) -> Dict[int, Dict]:
        """Busca batch de partners. Usa cache para IDs ja conhecidos, busca o restante."""
        if not partner_ids:
            return {}

        cache = _get_cache()
        result = {}
        missing_ids = []

        # Verificar cache para cada ID
        for pid in set(partner_ids):
            if not pid:
                continue
            key = f'{PREFIX_PARTNER}{pid}'
            cached = cache.get(key)
            if cached:
                try:
                    data = json.loads(cached) if isinstance(cached, str) else cached
                    result[pid] = data
                    continue
                except (json.JSONDecodeError, TypeError):
                    pass
            missing_ids.append(pid)

        # Buscar missing no Odoo (1 unica chamada batch)
        if missing_ids:
            try:
                conn = self._get_connection()
                partners = conn.read('res.partner', missing_ids,
                                     fields=['id', 'name', 'l10n_br_cnpj', 'l10n_br_ie'])
                for p in partners:
                    data = {
                        'id': p['id'],
                        'name': (p.get('name') or '').strip(),
                        'cnpj': (p.get('l10n_br_cnpj') or '').strip(),
                        'ie': (p.get('l10n_br_ie') or '').strip(),
                    }
                    result[p['id']] = data
                    cache.set(f'{PREFIX_PARTNER}{p["id"]}', json.dumps(data), ttl=TTL_PARTNER)

                logger.debug(f"Partner cache: {len(partner_ids) - len(missing_ids)} hits, {len(missing_ids)} fetched")
            except Exception as e:
                logger.warning(f"Erro ao buscar partners batch: {e}")

        return result

    # ============================
    # account.journal
    # ============================

    def get_journal(self, journal_id: int) -> Optional[Dict]:
        """Busca journal por ID (cache automatico)."""
        if not journal_id:
            return None

        cache = _get_cache()
        key = f'{PREFIX_JOURNAL}{journal_id}'

        cached = cache.get(key)
        if cached:
            try:
                return json.loads(cached) if isinstance(cached, str) else cached
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            conn = self._get_connection()
            results = conn.read('account.journal', [journal_id],
                                fields=['id', 'name', 'type', 'code', 'company_id'])
            if results:
                data = {
                    'id': results[0]['id'],
                    'name': results[0].get('name', ''),
                    'type': results[0].get('type', ''),
                    'code': results[0].get('code', ''),
                    'company_id': results[0].get('company_id', [False, ''])[0] if isinstance(results[0].get('company_id'), list) else results[0].get('company_id'),
                }
                cache.set(key, json.dumps(data), ttl=TTL_JOURNAL)
                return data
        except Exception as e:
            logger.debug(f"Erro ao buscar journal {journal_id}: {e}")

        return None

    # ============================
    # account.account
    # ============================

    def get_account(self, account_id: int) -> Optional[Dict]:
        """Busca account por ID (cache automatico)."""
        if not account_id:
            return None

        cache = _get_cache()
        key = f'{PREFIX_ACCOUNT}{account_id}'

        cached = cache.get(key)
        if cached:
            try:
                return json.loads(cached) if isinstance(cached, str) else cached
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            conn = self._get_connection()
            results = conn.read('account.account', [account_id],
                                fields=['id', 'name', 'code', 'company_id'])
            if results:
                data = {
                    'id': results[0]['id'],
                    'name': results[0].get('name', ''),
                    'code': results[0].get('code', ''),
                    'company_id': results[0].get('company_id', [False, ''])[0] if isinstance(results[0].get('company_id'), list) else results[0].get('company_id'),
                }
                cache.set(key, json.dumps(data), ttl=TTL_ACCOUNT)
                return data
        except Exception as e:
            logger.debug(f"Erro ao buscar account {account_id}: {e}")

        return None

    # ============================
    # Invalidacao
    # ============================

    def invalidate_partner(self, partner_id: int):
        """Invalida cache de um partner especifico."""
        _get_cache().client.delete(f'{PREFIX_PARTNER}{partner_id}')

    def invalidate_all(self, entity_type: str = 'partner'):
        """Invalida todo o cache de um tipo de entidade."""
        prefix_map = {'partner': PREFIX_PARTNER, 'journal': PREFIX_JOURNAL, 'account': PREFIX_ACCOUNT}
        prefix = prefix_map.get(entity_type, PREFIX_PARTNER)
        try:
            client = _get_cache().client
            cursor = '0'
            deleted = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=f'{prefix}*', count=100)
                if keys:
                    client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0 or cursor == '0':
                    break
            logger.info(f"Cache Odoo invalidado: {entity_type} ({deleted} chaves)")
        except Exception as e:
            logger.warning(f"Erro ao invalidar cache {entity_type}: {e}")
