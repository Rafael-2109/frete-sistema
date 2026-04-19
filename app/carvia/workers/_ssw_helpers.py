"""Helpers compartilhados para workers SSW (CarVia).

Uso:
    from app.carvia.workers._ssw_helpers import (
        formatar_ctrc_ssw,
        liberar_conexao_antes_playwright,
        commit_com_retry,
        consultar_101_por_cte,
        consultar_101_por_cte_com_dacte,
    )

Centraliza padroes usados em:
- `verificar_ctrc_ssw_jobs.py` (3 jobs: CTe Comp, Operacao, DACTE PDF)
- `ssw_cte_jobs.py` (emissao 004)
- `ssw_cte_complementar_jobs.py` (emissao 222)

Principios:
- R15 (SSL Drop Resilience): commit+close+dispose ANTES de Playwright,
  re-busca + retry 3x backoff DEPOIS.
- R2: todos os commits criticos usam `commit_com_retry`.
- Imports tardios (lazy) para evitar ciclos.
"""
import argparse
import asyncio
import logging
import os
import re
import sys
import time

logger = logging.getLogger(__name__)

# Path dos scripts Playwright SSW (3 niveis acima de app/carvia/workers/)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)
SSW_SCRIPTS = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'operando-ssw', 'scripts'
)


def formatar_ctrc_ssw(ctrc_completo):
    """Converte formato SSW para formato sistema.

    Ex: 'CAR000113-9' -> 'CAR-113-9', 'CAR000110-4' -> 'CAR-110-4'
    Se `ctrc_completo` nao bate o padrao, retorna como veio (strip).
    """
    if not ctrc_completo:
        return None
    m = re.match(r'^([A-Z]{2,4})0*(\d+)-(\d)$', ctrc_completo.strip())
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return ctrc_completo.strip()


def liberar_conexao_antes_playwright():
    """R15: Libera conexao do pool ANTES do Playwright (60-120s+).

    PostgreSQL Render tem tcp_keepalive que mata conexoes idle.
    `pool_pre_ping=True` NAO ajuda — a conexao ja estava checked-out.
    Padrao canonico: commit+close+dispose.
    """
    from app import db
    try:
        db.session.commit()
    except Exception as e:
        logger.warning("Commit pre-playwright falhou: %s", e)
        try:
            db.session.rollback()
        except Exception:
            pass
    try:
        db.session.close()
    except Exception:
        pass
    try:
        db.engine.dispose()
    except Exception:
        pass


def commit_com_retry(apply_fn, max_retries=3):
    """Aplica funcao + commit com retry em SSL/DBAPI errors.

    `apply_fn()` e chamada DENTRO do retry — deve (re)buscar objetos,
    aplicar updates e deixar a session pronta pra commit. Backoff
    exponencial 1s, 2s, 4s.

    Returns:
        True em sucesso. Re-raise da ultima excecao se todas as
        tentativas falharem.
    """
    from app import db
    from app.utils.database_helpers import ensure_connection

    last_exc = None
    for tentativa in range(max_retries):
        try:
            ensure_connection()
            apply_fn()
            db.session.commit()
            return True
        except Exception as e:
            last_exc = e
            logger.warning(
                "Commit com retry tentativa %d/%d falhou: %s",
                tentativa + 1, max_retries, e,
            )
            try:
                db.session.rollback()
            except Exception:
                pass
            try:
                db.session.close()
            except Exception:
                pass
            try:
                db.engine.dispose()
            except Exception:
                pass
            if tentativa < max_retries - 1:
                time.sleep(2 ** tentativa)

    logger.error("Commit com retry falhou definitivamente: %s", last_exc)
    if last_exc:
        raise last_exc
    return False


def consultar_101_por_cte(cte_numero, filial='CAR'):
    """Executa `consultar_ctrc_101.py --cte {cte_numero}` via asyncio.run.

    Retorna dict com resultado do script. Chaves tipicas:
      - sucesso: bool
      - dados: dict (ctrc_completo, cte_numero, ...) quando sucesso
      - erro: str quando falha

    Usado por:
      - verificar_ctrc_operacao_job (CarviaOperacao)
      - verificar_ctrc_cte_comp_job (CarviaCteComplementar) apos refator A3.2
    """
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from consultar_ctrc_101 import consultar_ctrc  # type: ignore

    args_101 = argparse.Namespace(
        ctrc=None,
        nf=None,
        cte=str(cte_numero),
        filial=filial,
        baixar_xml=False,
        baixar_dacte=False,
        output_dir='/tmp/ssw_operacoes/verificar_ctrc',
    )
    return asyncio.run(consultar_ctrc(args_101))


def consultar_101_por_cte_com_dacte(cte_numero, filial='CAR', operacao_id=None):
    """Como consultar_101_por_cte mas com `baixar_dacte=True`.

    `output_dir` inclui `operacao_id` para evitar colisao entre jobs
    paralelos rodando na mesma operacao. Nao baixa XML (escopo limitado
    ao PDF — decisao 2026-04-15).
    """
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from consultar_ctrc_101 import consultar_ctrc  # type: ignore

    output_dir = (
        f'/tmp/ssw_operacoes/baixar_pdf_op/{operacao_id or "sem_id"}'
    )
    args_101 = argparse.Namespace(
        ctrc=None,
        nf=None,
        cte=str(cte_numero),
        filial=filial,
        baixar_xml=False,
        baixar_dacte=True,
        output_dir=output_dir,
    )
    return asyncio.run(consultar_ctrc(args_101))


def normalizar_cte_numero(cte_numero):
    """Normaliza cte_numero para consulta SSW.

    SSW aceita numeros sem zeros a esquerda. Ex: '000000161' -> '161'.
    Se nao for conversivel para int, retorna strip do original.
    """
    try:
        return str(int(str(cte_numero).strip()))
    except (ValueError, TypeError):
        return str(cte_numero).strip()
