"""
Jobs RQ: Verificacao de CTRC via SSW (opcao 101).

Dois jobs independentes:

1. `verificar_ctrc_cte_comp_job(cte_comp_id)` — CTe Complementar.
   Disparado quando o usuario marca um CTe Comp. com "Verificar SSW" no
   preview da importacao manual. Consulta opcao 101 pelo CTRC atual e
   corrige se divergir.

2. `verificar_ctrc_operacao_job(operacao_id)` — CTe CarVia (Operacao).
   Disparado apos emissao automatica (worker `ssw_cte_jobs`) ou apos
   importacao manual de XML em `/carvia/importar`. Consulta opcao 101
   pesquisando pelo **numero do CTe** (t_nro_cte / ajaxEnvia P3) para
   obter o CTRC real do SSW — nao depende do `nCT`+`cDV` deduzido do XML.

Ambos aplicam o padrao R15 (SSL drop resilience) — ver
`app/carvia/CLAUDE.md` e `app/carvia/SSW_INTEGRATION.md`. Tipico:
~60-120s por CTRC (Playwright headless).

Fila: `default` (low-priority). Nao-bloqueante no fluxo principal.
"""
import argparse
import asyncio
import logging
import os
import re
import sys
import time

logger = logging.getLogger(__name__)

# Path dos scripts Playwright SSW
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)
SSW_SCRIPTS = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'operando-ssw', 'scripts'
)


# ────────────────────────────────────────────────────────────────────────────
# Helpers compartilhados
# ────────────────────────────────────────────────────────────────────────────

def _formatar_ctrc_ssw(ctrc_completo):
    """Converte formato SSW para formato sistema.

    Ex: 'CAR000113-9' → 'CAR-113-9'
        'CAR000110-4' → 'CAR-110-4'

    Se `ctrc_completo` nao bate o padrao, retorna como veio.
    """
    if not ctrc_completo:
        return None
    m = re.match(r'^([A-Z]{2,4})0*(\d+)-(\d)$', ctrc_completo.strip())
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    return ctrc_completo.strip()


def _liberar_conexao_antes_playwright():
    """R15: Libera conexao do pool ANTES do Playwright (60-120s+).

    PostgreSQL (Render) tem tcp_keepalive que mata conexoes idle.
    pool_pre_ping NAO ajuda — a conexao ja estava checked-out.
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


def _commit_com_retry(apply_fn, max_retries=3):
    """Aplica funcao + commit com retry em SSL/DBAPI errors.

    `apply_fn()` e chamada DENTRO do retry — deve (re)buscar objetos,
    aplicar updates e deixar a session pronta pra commit. Backoff
    exponencial 1s, 2s, 4s.
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
                tentativa + 1, max_retries, e
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


def _consultar_101_por_cte(cte_numero, filial='CAR'):
    """Executa consultar_ctrc_101.py --cte via asyncio.run.

    Returns:
        dict com o resultado do script (chaves: sucesso, dados, erro, ...)
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
        output_dir='/tmp/ssw_operacoes/verificar_ctrc_op',
    )
    return asyncio.run(consultar_ctrc(args_101))


# ────────────────────────────────────────────────────────────────────────────
# Job: CarviaCteComplementar (existente — sem mudanca de comportamento)
# ────────────────────────────────────────────────────────────────────────────

def verificar_ctrc_cte_comp_job(cte_comp_id: int) -> dict:
    """Job RQ: consulta SSW opcao 101 e atualiza ctrc_numero se divergir.

    Usa `resolver_ctrc_ssw` (persistencia CTe Comp.) que ja pesquisa via
    CTRC atual armazenado.

    Args:
        cte_comp_id: ID do CarviaCteComplementar a verificar

    Returns:
        dict com {status, ctrc_anterior, ctrc_novo, motivo}
        status: 'CORRIGIDO' | 'OK' | 'SKIPPED' | 'ERRO'
    """
    from app import create_app, db
    from app.carvia.models import CarviaCteComplementar
    from app.carvia.services.cte_complementar_persistencia import (
        resolver_ctrc_ssw,
    )
    from app.utils.timezone import agora_utc_naive

    app = create_app()
    with app.app_context():
        cte_comp = db.session.get(CarviaCteComplementar, cte_comp_id)
        if not cte_comp:
            logger.warning(
                "verificar_ctrc_cte_comp_job: CTe Comp %s nao encontrado",
                cte_comp_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'CTe Comp nao encontrado',
            }

        if not cte_comp.ctrc_numero:
            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s sem ctrc_numero "
                "(nada a verificar)",
                cte_comp_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'CTe Comp sem ctrc_numero',
            }

        ctrc_anterior = cte_comp.ctrc_numero
        try:
            ctrc_corrigido = resolver_ctrc_ssw(
                ctrc_atual=ctrc_anterior,
                filial='CAR',
            )
        except Exception as e:
            logger.exception(
                "verificar_ctrc_cte_comp_job: erro ao consultar SSW "
                "para CTe Comp %s",
                cte_comp_id,
            )
            return {
                'status': 'ERRO',
                'erro': str(e),
                'ctrc_anterior': ctrc_anterior,
            }

        if ctrc_corrigido and ctrc_corrigido != ctrc_anterior:
            cte_comp.ctrc_numero = ctrc_corrigido
            cte_comp.atualizado_em = agora_utc_naive()
            db.session.commit()
            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC corrigido "
                "%s -> %s",
                cte_comp_id, ctrc_anterior, ctrc_corrigido,
            )
            return {
                'status': 'CORRIGIDO',
                'ctrc_anterior': ctrc_anterior,
                'ctrc_novo': ctrc_corrigido,
            }

        logger.info(
            "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC %s confirmado "
            "(sem alteracao)",
            cte_comp_id, ctrc_anterior,
        )
        return {
            'status': 'OK',
            'ctrc': ctrc_anterior,
        }


# ────────────────────────────────────────────────────────────────────────────
# Job: CarviaOperacao (novo — pesquisa por --cte)
# ────────────────────────────────────────────────────────────────────────────

def verificar_ctrc_operacao_job(operacao_id: int) -> dict:
    """Job RQ: consulta SSW opcao 101 por `--cte {nCT}` e corrige
    `CarviaOperacao.ctrc_numero` se divergir do real do SSW.

    Fluxo:
      1. Carrega operacao → snapshot (cte_numero, ctrc_anterior, filial)
      2. Se nao tem cte_numero → SKIPPED
      3. R15: commit + close + dispose (libera conexao pool)
      4. asyncio.run(consultar_ctrc(--cte=cte_numero))
      5. Extrai `dados.ctrc_completo` → `_formatar_ctrc_ssw()`
      6. Re-get operacao + atualiza ctrc_numero (retry SSL/DBAPI)
      7. Atualiza tambem CarviaEmissaoCte.ctrc_numero (se houver emissao
         mais recente vinculada) para manter coerencia

    Args:
        operacao_id: ID da CarviaOperacao

    Returns:
        dict com {status, ctrc_anterior, ctrc_novo, motivo}
        status: 'CORRIGIDO' | 'OK' | 'SKIPPED' | 'ERRO'
    """
    from app import create_app, db
    from app.carvia.models import CarviaOperacao, CarviaEmissaoCte
    from app.utils.timezone import agora_utc_naive

    app = create_app()
    with app.app_context():
        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            logger.warning(
                "verificar_ctrc_operacao_job: Operacao %s nao encontrada",
                operacao_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'Operacao nao encontrada',
            }

        # Snapshot ORM em variaveis locais (objeto stale durante Playwright)
        cte_numero_local = operacao.cte_numero
        ctrc_anterior_local = operacao.ctrc_numero
        filial_local = 'CAR'  # CarVia opera apenas CAR atualmente

        if not cte_numero_local:
            logger.info(
                "verificar_ctrc_operacao_job: Operacao %s sem cte_numero "
                "(nada a verificar)",
                operacao_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'Operacao sem cte_numero',
                'ctrc_anterior': ctrc_anterior_local,
            }

        # cte_numero pode vir como "000000161" ou "161" — normalizar
        try:
            cte_numero_str = str(int(str(cte_numero_local).strip()))
        except (ValueError, TypeError):
            cte_numero_str = str(cte_numero_local).strip()

        # R15: libera conexao antes do Playwright (60-120s+)
        _liberar_conexao_antes_playwright()

        try:
            resultado = _consultar_101_por_cte(
                cte_numero_str, filial=filial_local
            )
        except Exception as e:
            logger.exception(
                "verificar_ctrc_operacao_job: erro ao consultar SSW "
                "opcao 101 --cte %s (op=%s)",
                cte_numero_str, operacao_id,
            )
            return {
                'status': 'ERRO',
                'erro': str(e),
                'ctrc_anterior': ctrc_anterior_local,
            }

        if not resultado.get('sucesso'):
            erro_msg = resultado.get('erro', 'Falha na consulta 101')
            logger.warning(
                "verificar_ctrc_operacao_job: 101 nao encontrou CTe %s "
                "(op=%s): %s",
                cte_numero_str, operacao_id, erro_msg,
            )
            return {
                'status': 'ERRO',
                'erro': erro_msg,
                'ctrc_anterior': ctrc_anterior_local,
            }

        dados = resultado.get('dados', {}) or {}
        ctrc_completo_ssw = dados.get('ctrc_completo')
        ctrc_novo = _formatar_ctrc_ssw(ctrc_completo_ssw)

        if not ctrc_novo:
            logger.warning(
                "verificar_ctrc_operacao_job: 101 nao retornou "
                "ctrc_completo (op=%s, cte=%s, dados=%s)",
                operacao_id, cte_numero_str, list(dados.keys()),
            )
            return {
                'status': 'ERRO',
                'erro': 'SSW nao retornou ctrc_completo',
                'ctrc_anterior': ctrc_anterior_local,
            }

        if ctrc_novo == ctrc_anterior_local:
            logger.info(
                "verificar_ctrc_operacao_job: op %s — CTRC %s confirmado "
                "(sem alteracao)",
                operacao_id, ctrc_anterior_local,
            )
            # Mesmo quando OK, garantir que a conexao esta viva antes de
            # retornar (evita deixar session morta pro proximo job).
            try:
                from app.utils.database_helpers import ensure_connection
                ensure_connection()
            except Exception:
                pass
            return {
                'status': 'OK',
                'ctrc': ctrc_anterior_local,
            }

        # CTRC divergente — persistir com retry
        def _aplicar_correcao():
            op = db.session.get(CarviaOperacao, operacao_id)
            if not op:
                raise ValueError(
                    f"Operacao {operacao_id} desapareceu pos-Playwright"
                )
            op.ctrc_numero = ctrc_novo

            # Atualizar tambem a CarviaEmissaoCte mais recente (se houver)
            # para manter a tela de tracking coerente com a operacao.
            emissao = (
                CarviaEmissaoCte.query
                .filter_by(operacao_id=op.id)
                .order_by(CarviaEmissaoCte.criado_em.desc())
                .first()
            )
            if emissao and emissao.ctrc_numero != ctrc_novo:
                emissao.ctrc_numero = ctrc_novo
                emissao.atualizado_em = agora_utc_naive()

        _commit_com_retry(_aplicar_correcao)

        logger.info(
            "verificar_ctrc_operacao_job: op %s — CTRC corrigido %s -> %s "
            "(via 101 --cte %s)",
            operacao_id, ctrc_anterior_local, ctrc_novo, cte_numero_str,
        )
        return {
            'status': 'CORRIGIDO',
            'ctrc_anterior': ctrc_anterior_local,
            'ctrc_novo': ctrc_novo,
            'cte_numero': cte_numero_str,
        }
