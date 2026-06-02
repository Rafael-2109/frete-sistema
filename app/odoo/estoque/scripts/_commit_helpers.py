# etapa: helper
# doc-dono: app/odoo/estoque/CLAUDE.md §11
"""_commit_helpers.py — Helpers consolidados de commit SSL-resilient.

CR-F9 v15c (CRITICAL Reviewer B+D conf 80-85): consolida 3 padroes de
commit SSL-resilient que estavam duplicados:

1. `script 09 _commit_resilient` (versao MAIS FORTE com `engine.dispose()`)
2. `pre_etapa_executor._commit_resilient` (similar mas inline)
3. `inventario_pipeline_service._commit_with_retry` (versao mais antiga)

Ja existe `app.utils.database_retry.commit_with_retry` mas:
- Match SSL mais estrito (`['ssl', 'decryption', 'bad record']` so).
- Backoff fixo 0.5/1/2s.
- Sem `engine.dispose()` proativo (D14).

Esta utility fica em `app/odoo/estoque/scripts/` (proximo aos consumers
de pipeline) com 2 padroes:

- `commit_resilient(...)`: versao MAIS FORTE com `engine.dispose()` proativo
  em SSL drop + backoff exponencial. Para ops longas (Playwright SEFAZ,
  polling 1800s) onde PgBouncer SSL pode dropar.
- `safe_session_get(model, id)`: re-fetch ORM apos commit_resilient que
  fez `session.close()` (anti-DetachedInstanceError — Reviewer D R-OPS-5).

Decisoes inviolaveis aplicadas:
- D14: dispose proativo se substring `'ssl'`/`'decryption'`/`'bad record'`
  no erro. Tighten match vs versao v15b (que tinha `'connection'` BROAD
  capturando falso-positivos — Reviewer D R-OPS-6 conf 80).
- Backoff exponencial: 2s/4s/8s para ops longas vs fixo curto.

Spec: app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md §9 pendencia.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional, Type, TypeVar

from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


# Substrings que indicam SSL drop / TCP reset / PgBouncer issue.
# Tighten match (Reviewer D R-OPS-6): substituiu BROAD `'connection'` v15b
# por lista especifica — evita capturar `psycopg2.errors.InFailedSql*`
# messages que contem `'connection'` benignamente.
SSL_DROP_MARKERS = ('ssl', 'decryption', 'bad record', 'closed unexpectedly')


def commit_resilient(
    *,
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    dispose_on_ssl: bool = True,
) -> bool:
    """Commit SSL-resilient com `engine.dispose()` proativo (D14).

    Pattern espelha `09_executar_onda1_bulk.py:158-210` (`_commit_resilient`):
    - Detecta SSL drop via substring match em `SSL_DROP_MARKERS`.
    - Se SSL: `rollback() + close() + engine.dispose() + sleep backoff + retry`.
    - Se NAO-SSL (OperationalError generico): retry com backoff sem dispose.
    - Exit se NAO-OperationalError (propaga outras excecoes).

    Args:
        max_attempts: numero maximo de tentativas (default 3).
        backoff_base: base do backoff exponencial em segundos (default 2 → 2s/4s/8s).
        dispose_on_ssl: se True, executa `db.engine.dispose()` em SSL drop
            (D14). Default True. Pass False em testes para evitar reset de
            engine compartilhada.

    Returns:
        True se commit OK em alguma tentativa, False se esgotou.

    Raises:
        Propaga excecoes nao-OperationalError (ex: IntegrityError) sem retry.
    """
    from app import db  # lazy (evita circular em tests)

    last_err: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            db.session.commit()
            if attempt > 1:
                logger.info(
                    f'G016 commit_resilient OK na tentativa {attempt}/{max_attempts}'
                )
            return True
        except OperationalError as e:
            last_err = e
            err_str = str(e)[:200]
            err_low = err_str.lower()
            # Tighten match (Reviewer D R-OPS-6): apenas substrings especificas
            is_ssl = any(m in err_low for m in SSL_DROP_MARKERS)
            logger.warning(
                f'G016 commit_resilient attempt {attempt}/{max_attempts} '
                f'OperationalError (ssl={is_ssl}): {err_str}'
            )
            try:
                db.session.rollback()
            except Exception as e_rb:
                logger.warning(f'G016 rollback falhou (continuando): {e_rb}')
            try:
                db.session.close()
            except Exception as e_cl:
                logger.warning(f'G016 close falhou (continuando): {e_cl}')
            if is_ssl and dispose_on_ssl:
                # D14: dispose proativo do engine se SSL drop detectado.
                try:
                    db.engine.dispose()
                    logger.info(
                        'G016 db.engine.dispose() executado (SSL drop)'
                    )
                except Exception as e_disp:
                    logger.warning(f'G016 engine.dispose falhou: {e_disp}')
            if attempt < max_attempts:
                sleep_s = backoff_base ** (attempt - 1)
                time.sleep(sleep_s)
    logger.error(
        f'G016 commit_resilient FAILED apos {max_attempts} tentativas. '
        f'Ultimo erro: {last_err}'
    )
    return False


M = TypeVar('M')


def safe_session_get(model: Type[M], id: Any) -> Optional[M]:
    """Re-fetch um objeto ORM por ID apos commit_resilient.

    Pattern anti-DetachedInstanceError (Reviewer D R-OPS-5):
    `commit_resilient` faz `session.close()` em falha — objects loaded
    antes ficam detached. Re-fetch via `db.session.get(model, id)` re-anexa
    ao novo session-state ou retorna None se objeto foi deletado.

    Args:
        model: classe SQLAlchemy (ex: AjusteEstoqueInventario).
        id: chave primaria.

    Returns:
        Instancia re-fetched ou None se nao existe.

    Uso tipico (cada commit_resilient apos op longa):
        if not commit_resilient():
            ajuste = safe_session_get(AjusteEstoqueInventario, ajuste.id)
            if ajuste:
                ajuste.fase_pipeline = 'X_FALHA'
                commit_resilient()
    """
    from app import db  # lazy
    try:
        return db.session.get(model, id)
    except Exception as e:
        logger.warning(
            f'safe_session_get({model.__name__}, {id}) falhou: {e}'
        )
        return None
