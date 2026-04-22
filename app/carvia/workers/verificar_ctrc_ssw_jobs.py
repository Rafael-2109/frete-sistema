"""
Jobs RQ: Verificacao de CTRC e download de DACTE via SSW (opcao 101).

Tres jobs independentes:

1. `verificar_ctrc_cte_comp_job(cte_comp_id)` — CTe Complementar.
   Tres casos (A3.2, 2026-04-17):
     - Caso A: ctrc_numero vazio + cte_numero preenchido -> busca SSW 101
       via --cte (extrai CTRC novo, simetrico a verificar_ctrc_operacao_job).
     - Caso B: ctrc_numero preenchido -> resolver_ctrc_ssw (verifica divergencia).
     - Caso C: ambos vazios -> SKIPPED.
   Disparado automaticamente pos-commit da importacao manual (CARVIA_FEATURE_ENQUEUE_CTRC_CTE_COMP_AUTO)
   e apos emissao 222 quando ctrc_complementar nao foi capturado.

2. `verificar_ctrc_operacao_job(operacao_id)` — CTe CarVia (Operacao).
   Disparado apos emissao automatica (worker `ssw_cte_jobs`), apos
   importacao manual de XML em `/carvia/importar`, ou sob demanda via
   botao "Atualizar CTRC" na tela de detalhe. Consulta opcao 101
   pesquisando pelo **numero do CTe** (t_nro_cte / ajaxEnvia P3) para
   obter o CTRC real do SSW — nao depende do `nCT`+`cDV` deduzido do XML.

3. `baixar_pdf_ssw_operacao_job(operacao_id)` — DACTE PDF sob demanda.
   Disparado pelo botao "PDF SSW" na tela de detalhe quando
   `cte_pdf_path` esta vazio. Consulta 101 com `--baixar-dacte`, faz
   upload para S3 em `carvia/ctes_pdf/` e atualiza `CarviaOperacao.cte_pdf_path`.
   NAO mexe em `cte_xml_path` (escopo limitado — decisao 2026-04-15).

Todos aplicam o padrao R15 (SSL drop resilience) — ver
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


def _consultar_101_por_cte_com_dacte(cte_numero, filial='CAR', operacao_id=None):
    """Como _consultar_101_por_cte mas com baixar_dacte=True.

    output_dir inclui operacao_id para evitar colisao entre jobs paralelos
    que rodem na mesma operacao. Nao baixa XML (escopo limitado ao PDF —
    decisao 2026-04-15).
    """
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from consultar_ctrc_101 import consultar_ctrc  # type: ignore

    output_dir = f'/tmp/ssw_operacoes/baixar_pdf_op/{operacao_id or "sem_id"}'
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


# ────────────────────────────────────────────────────────────────────────────
# Job: CarviaCteComplementar (existente — sem mudanca de comportamento)
# ────────────────────────────────────────────────────────────────────────────

def verificar_ctrc_cte_comp_job(cte_comp_id: int) -> dict:
    """Job RQ: consulta SSW opcao 101 para obter/verificar ctrc_numero
    de um CarviaCteComplementar.

    2026-04-22 (refator): **prioriza busca por --cte** sempre que
    `cte_numero` estiver preenchido, mesmo se `ctrc_numero` tambem tiver
    valor. O CTRC salvo pode estar divergente (captura manual errada ou
    dedupe 222 anterior); buscar pelo numero do CTe e a fonte confiavel.
    O CTRC existente e sobrescrito se o SSW retornar divergente.
    **Tambem baixa DACTE PDF em UMA CHAMADA** quando `cte_pdf_path`
    estiver vazio — evita segunda ida ao SSW pelo botao "Atualizar CTRC".

    Casos:
      - CTE_DISPONIVEL: cte_numero preenchido -> busca SSW via --cte e
        sobrescreve ctrc_numero com o valor retornado (EXTRAIDO ou
        CORRIGIDO conforme ctrc anterior estivesse ou nao vazio).
        Se `cte_pdf_path` vazio, tambem baixa DACTE -> S3 carvia/ctes_pdf/.
      - SO_CTRC (fallback): cte_numero vazio + ctrc_numero preenchido ->
        usa resolver_ctrc_ssw (logica antiga, busca por --ctrc).
      - SKIPPED: ambos vazios.

    R15 SSL resilience: aplica commit_com_retry nos casos que mexem em DB.

    Args:
        cte_comp_id: ID do CarviaCteComplementar a verificar

    Returns:
        dict com {status, ctrc_anterior, ctrc_novo, motivo, cte_numero?}
        status: 'EXTRAIDO' | 'CORRIGIDO' | 'OK' | 'SKIPPED' | 'ERRO'
    """
    from app import create_app, db
    from app.carvia.models import CarviaCteComplementar
    from app.carvia.services.cte_complementar_persistencia import (
        resolver_ctrc_ssw,
    )
    from app.carvia.workers._ssw_helpers import (
        consultar_101_por_cte,
        consultar_101_por_cte_com_dacte,
        formatar_ctrc_ssw,
        liberar_conexao_antes_playwright,
        commit_com_retry,
        normalizar_cte_numero,
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

        ctrc_anterior = cte_comp.ctrc_numero
        cte_numero_local = cte_comp.cte_numero
        pdf_path_anterior = cte_comp.cte_pdf_path
        baixar_dacte = not pdf_path_anterior

        # ────────────── SKIPPED: ambos vazios ──────────────
        if not ctrc_anterior and not cte_numero_local:
            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s sem ctrc_numero "
                "E sem cte_numero (nada a verificar)",
                cte_comp_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'CTe Comp sem ctrc_numero e sem cte_numero',
            }

        # ────────────── CTE_DISPONIVEL: usar --cte (prioritario) ──────────────
        # Busca por --cte sobrescreve ctrc_numero mesmo se ja existente
        # (CTRC salvo pode ser stale — confianca e no retorno da 101).
        if cte_numero_local:
            cte_numero_str = normalizar_cte_numero(cte_numero_local)

            # R15: libera conexao antes do Playwright (60-120s+)
            liberar_conexao_antes_playwright()

            try:
                if baixar_dacte:
                    # Uma so consulta 101: busca CTRC + baixa DACTE PDF
                    # (output_dir por cte_comp_id evita colisao entre jobs).
                    resultado = consultar_101_por_cte_com_dacte(
                        cte_numero_str, filial='CAR',
                        operacao_id=f'cte_comp_{cte_comp_id}',
                    )
                else:
                    resultado = consultar_101_por_cte(
                        cte_numero_str, filial='CAR'
                    )
            except Exception as e:
                logger.exception(
                    "verificar_ctrc_cte_comp_job: erro ao consultar SSW "
                    "opcao 101 --cte %s (cte_comp=%s, baixar_dacte=%s)",
                    cte_numero_str, cte_comp_id, baixar_dacte,
                )
                return {
                    'status': 'ERRO',
                    'erro': str(e),
                    'ctrc_anterior': ctrc_anterior,
                    'cte_numero': cte_numero_str,
                }

            if not resultado.get('sucesso'):
                erro_msg = resultado.get('erro', 'Falha na consulta 101')
                logger.warning(
                    "verificar_ctrc_cte_comp_job: 101 nao encontrou CTe "
                    "%s (cte_comp=%s): %s",
                    cte_numero_str, cte_comp_id, erro_msg,
                )
                return {
                    'status': 'ERRO',
                    'erro': erro_msg,
                    'ctrc_anterior': ctrc_anterior,
                    'cte_numero': cte_numero_str,
                }

            dados = resultado.get('dados', {}) or {}
            ctrc_completo_ssw = dados.get('ctrc_completo')
            ctrc_novo = formatar_ctrc_ssw(ctrc_completo_ssw)

            if not ctrc_novo:
                logger.warning(
                    "verificar_ctrc_cte_comp_job: 101 nao retornou "
                    "ctrc_completo (cte_comp=%s, cte=%s, dados=%s)",
                    cte_comp_id, cte_numero_str, list(dados.keys()),
                )
                return {
                    'status': 'ERRO',
                    'erro': 'SSW nao retornou ctrc_completo',
                    'ctrc_anterior': ctrc_anterior,
                    'cte_numero': cte_numero_str,
                }

            # Upload DACTE PDF para S3 (se baixado com sucesso) ANTES
            # do commit, para sincronizar ctrc_numero + cte_pdf_path.
            dacte_s3_path = None
            dacte_path_local = dados.get('dacte') if baixar_dacte else None
            if baixar_dacte and dacte_path_local and os.path.exists(dacte_path_local):
                try:
                    from app.utils.file_storage import get_file_storage
                    from io import BytesIO

                    storage = get_file_storage()
                    with open(dacte_path_local, 'rb') as f:
                        dacte_bytes = f.read()

                    buf = BytesIO(dacte_bytes)
                    # Inclui cte_comp_id na chave S3 para evitar colisao quando
                    # dois CTe Comps distintos compartilham o mesmo CTRC
                    # (caso raro mas possivel em complementares da mesma
                    # perna de transporte — sem o suffix, um sobrescreveria o outro).
                    buf.name = (
                        f"{ctrc_novo or cte_numero_str}-{cte_comp_id}-dacte.pdf"
                    )
                    dacte_s3_path = storage.save_file(
                        buf, folder='carvia/ctes_pdf', filename=buf.name,
                    )
                    if not dacte_s3_path:
                        logger.warning(
                            "verificar_ctrc_cte_comp_job: upload S3 retornou "
                            "vazio (cte_comp=%s)", cte_comp_id,
                        )
                except Exception as e_pdf:
                    logger.exception(
                        "verificar_ctrc_cte_comp_job: falha upload DACTE S3 "
                        "(cte_comp=%s): %s", cte_comp_id, e_pdf,
                    )
                    dacte_s3_path = None
            elif baixar_dacte:
                logger.warning(
                    "verificar_ctrc_cte_comp_job: baixar_dacte solicitado mas "
                    "SSW nao retornou arquivo (cte_comp=%s, dacte=%r)",
                    cte_comp_id, dacte_path_local,
                )

            # SSW confirmou o mesmo CTRC ja salvo → so atualizar se PDF mudou
            if ctrc_anterior and ctrc_novo == ctrc_anterior and not dacte_s3_path:
                logger.info(
                    "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC %s "
                    "confirmado pelo SSW (via --cte %s, sem alteracao)",
                    cte_comp_id, ctrc_anterior, cte_numero_str,
                )
                return {
                    'status': 'OK',
                    'ctrc': ctrc_anterior,
                    'cte_numero': cte_numero_str,
                }

            # Persistir com retry (R15) — sobrescreve ctrc se divergente
            # e/ou grava cte_pdf_path quando DACTE baixado.
            def _aplicar_ctrc_ssw():
                cc = db.session.get(CarviaCteComplementar, cte_comp_id)
                if not cc:
                    raise ValueError(
                        f"CTe Comp {cte_comp_id} desapareceu pos-Playwright"
                    )
                if ctrc_novo and ctrc_novo != cc.ctrc_numero:
                    cc.ctrc_numero = ctrc_novo
                if dacte_s3_path:
                    cc.cte_pdf_path = dacte_s3_path
                cc.atualizado_em = agora_utc_naive()

            commit_com_retry(_aplicar_ctrc_ssw)

            if ctrc_novo != ctrc_anterior:
                status_final = 'EXTRAIDO' if not ctrc_anterior else 'CORRIGIDO'
            else:
                status_final = 'OK'  # so PDF atualizado
            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC %s "
                "%s -> %s, pdf=%s (via 101 --cte %s)",
                cte_comp_id, status_final.lower(),
                ctrc_anterior or '(vazio)', ctrc_novo,
                'atualizado' if dacte_s3_path else 'mantido',
                cte_numero_str,
            )
            return {
                'status': status_final,
                'ctrc_anterior': ctrc_anterior,
                'ctrc_novo': ctrc_novo,
                'cte_numero': cte_numero_str,
                'cte_pdf_path': dacte_s3_path or pdf_path_anterior,
            }

        # ────────────── SO_CTRC: fallback sem cte_numero ──────────────
        # (Caso raro — legado. Usa busca por --ctrc.)
        # R15: resolver_ctrc_ssw tambem abre sessao Playwright (60-120s+),
        # entao precisamos liberar a conexao antes e usar commit_com_retry
        # depois — caso contrario o commit falha por SSL drop no Render.
        liberar_conexao_antes_playwright()

        try:
            ctrc_corrigido = resolver_ctrc_ssw(
                ctrc_atual=ctrc_anterior,
                filial='CAR',
            )
        except Exception as e:
            logger.exception(
                "verificar_ctrc_cte_comp_job: erro ao consultar SSW "
                "para CTe Comp %s (fallback --ctrc)",
                cte_comp_id,
            )
            return {
                'status': 'ERRO',
                'erro': str(e),
                'ctrc_anterior': ctrc_anterior,
            }

        if ctrc_corrigido and ctrc_corrigido != ctrc_anterior:
            def _aplicar_fallback_ctrc():
                cc = db.session.get(CarviaCteComplementar, cte_comp_id)
                if not cc:
                    raise ValueError(
                        f"CTe Comp {cte_comp_id} desapareceu pos-Playwright"
                    )
                cc.ctrc_numero = ctrc_corrigido
                cc.atualizado_em = agora_utc_naive()

            commit_com_retry(_aplicar_fallback_ctrc)

            logger.info(
                "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC corrigido "
                "%s -> %s (fallback --ctrc)",
                cte_comp_id, ctrc_anterior, ctrc_corrigido,
            )
            return {
                'status': 'CORRIGIDO',
                'ctrc_anterior': ctrc_anterior,
                'ctrc_novo': ctrc_corrigido,
            }

        logger.info(
            "verificar_ctrc_cte_comp_job: CTe Comp %s — CTRC %s confirmado "
            "(fallback --ctrc, sem alteracao)",
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


# ────────────────────────────────────────────────────────────────────────────
# Job: Baixar DACTE PDF do SSW (opcao 101 --cte --baixar-dacte)
# ────────────────────────────────────────────────────────────────────────────

def baixar_pdf_ssw_operacao_job(operacao_id: int) -> dict:
    """Job RQ: baixa DACTE PDF do SSW (101 --cte --baixar-dacte),
    faz upload para S3 em carvia/ctes_pdf/ e atualiza
    `CarviaOperacao.cte_pdf_path`.

    NAO mexe em `cte_xml_path` (escopo limitado ao PDF — decisao 2026-04-15).

    Fluxo:
      1. Carrega operacao -> snapshot (cte_numero)
      2. Se nao tem cte_numero -> SKIPPED
      3. R15: commit + close + dispose (libera conexao pool)
      4. asyncio.run(consultar_ctrc(--cte=cte_numero, baixar_dacte=True))
      5. Le bytes do DACTE local e faz upload S3 (padrao BytesIO)
      6. Re-get operacao + atualiza `cte_pdf_path` (retry SSL/DBAPI)

    Args:
        operacao_id: ID da CarviaOperacao

    Returns:
        dict com {status, cte_pdf_path, motivo/erro}
        status: 'SUCESSO' | 'SKIPPED' | 'ERRO'
    """
    from app import create_app, db
    from app.carvia.models import CarviaOperacao
    from io import BytesIO

    app = create_app()
    with app.app_context():
        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            logger.warning(
                "baixar_pdf_ssw_operacao_job: Operacao %s nao encontrada",
                operacao_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'Operacao nao encontrada',
            }

        # Snapshot ORM em variaveis locais (objeto stale durante Playwright)
        cte_numero_local = operacao.cte_numero

        if not cte_numero_local:
            logger.info(
                "baixar_pdf_ssw_operacao_job: Operacao %s sem cte_numero "
                "(nada a baixar)",
                operacao_id,
            )
            return {
                'status': 'SKIPPED',
                'motivo': 'Operacao sem cte_numero',
            }

        # cte_numero pode vir como "000000161" ou "161" — normalizar
        try:
            cte_numero_str = str(int(str(cte_numero_local).strip()))
        except (ValueError, TypeError):
            cte_numero_str = str(cte_numero_local).strip()

        # R15: libera conexao antes do Playwright (60-120s+)
        _liberar_conexao_antes_playwright()

        try:
            resultado = _consultar_101_por_cte_com_dacte(
                cte_numero_str, filial='CAR', operacao_id=operacao_id,
            )
        except Exception as e:
            logger.exception(
                "baixar_pdf_ssw_operacao_job: erro ao consultar SSW "
                "opcao 101 --cte %s --baixar-dacte (op=%s)",
                cte_numero_str, operacao_id,
            )
            return {
                'status': 'ERRO',
                'erro': str(e),
            }

        if not resultado.get('sucesso'):
            erro_msg = resultado.get('erro', 'Falha na consulta 101')
            logger.warning(
                "baixar_pdf_ssw_operacao_job: 101 nao encontrou CTe %s "
                "(op=%s): %s",
                cte_numero_str, operacao_id, erro_msg,
            )
            return {
                'status': 'ERRO',
                'erro': erro_msg,
            }

        dacte_path_local = resultado.get('dacte')
        if not dacte_path_local or not os.path.exists(dacte_path_local):
            logger.warning(
                "baixar_pdf_ssw_operacao_job: SSW nao retornou DACTE "
                "(op=%s, cte=%s, dacte=%r)",
                operacao_id, cte_numero_str, dacte_path_local,
            )
            return {
                'status': 'ERRO',
                'erro': 'SSW nao retornou DACTE (dados.dacte=None)',
            }

        # Upload para S3 — padrao cte_complementar_persistencia
        try:
            from app.utils.file_storage import get_file_storage
            storage = get_file_storage()
            with open(dacte_path_local, 'rb') as f:
                dacte_bytes = f.read()

            buf = BytesIO(dacte_bytes)
            buf.name = f'{cte_numero_str}-dacte.pdf'
            dacte_s3_path = storage.save_file(
                buf, folder='carvia/ctes_pdf', filename=buf.name,
            )
        except Exception as e:
            logger.exception(
                "baixar_pdf_ssw_operacao_job: upload S3 falhou (op=%s)",
                operacao_id,
            )
            return {
                'status': 'ERRO',
                'erro': f'Upload S3 falhou: {e}',
            }

        if not dacte_s3_path:
            return {
                'status': 'ERRO',
                'erro': 'Upload S3 falhou (save_file retornou vazio)',
            }

        # Persiste com retry SSL/DBAPI
        def _aplicar_pdf_path():
            op = db.session.get(CarviaOperacao, operacao_id)
            if not op:
                raise ValueError(
                    f'Operacao {operacao_id} desapareceu pos-Playwright'
                )
            op.cte_pdf_path = dacte_s3_path

        _commit_com_retry(_aplicar_pdf_path)

        logger.info(
            "baixar_pdf_ssw_operacao_job: op %s -> cte_pdf_path=%s",
            operacao_id, dacte_s3_path,
        )
        return {
            'status': 'SUCESSO',
            'cte_pdf_path': dacte_s3_path,
            'cte_numero': cte_numero_str,
        }
