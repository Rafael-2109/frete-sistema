"""
Job RQ: Emissao automatica de CTe no SSW + Fatura.

Executado pelo worker_ssw_carvia.py na fila 'ssw_carvia'.
Cada job dura 60-120s (Playwright headless) e atualiza
CarviaEmissaoCte.etapa para tracking de progresso via polling.

Etapas:
  1. LOGIN — Login SSW
  2. PREENCHIMENTO — Preencher tela 004 (placa, chave, medidas, frete)
  3. SEFAZ — Enviar ao SEFAZ
  4. CONSULTA_101 — Consultar resultado + baixar XML/DACTE
  5. IMPORTACAO_CTE — Importar XML no sistema (CarviaOperacao)
  6. FATURA_437 — Gerar fatura SSW (tela 437, filial MTZ)
  7. IMPORTACAO_FAT — Importar PDF fatura (CarviaFaturaCliente)

GOTCHA SSL Drop: Conexoes PostgreSQL ficam idle durante os 60-120s do
Playwright e Render fecha por timeout SSL. pool_pre_ping nao ajuda
porque a conexao ja estava checked-out. Solucao: commit+close ANTES de
cada chamada Playwright + _commit_pos_playwright() apos, que reabre
conexao via ensure_connection() e re-busca a emissao.
"""
import argparse
import asyncio
import json
import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

# Path do projeto para imports dos scripts SSW
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SSW_SCRIPTS = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'operando-ssw', 'scripts'
)


def _liberar_conexao_antes_playwright():
    """Commit + close + dispose antes de operacao Playwright longa.

    Libera a conexao do pool para evitar que ela fique idle durante
    os 60-120s do Playwright e seja fechada pelo Postgres (SSL drop).
    Apos o Playwright, usar _commit_pos_playwright() para reabrir.
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


def _commit_pos_playwright(emissao_id, max_retries=3, **updates):
    """Commit seguro apos operacao Playwright longa.

    Apos Playwright, a conexao SQL antiga pode estar morta (SSL drop).
    Este helper:
      1. Chama ensure_connection() para reabrir a conexao
      2. Re-busca o objeto emissao via db.session.get (estava detached)
      3. Aplica updates passados como kwargs
      4. Commita com retry em SSL/connection errors

    Args:
        emissao_id: ID da CarviaEmissaoCte
        max_retries: Tentativas em caso de SSL drop
        **updates: campo=valor a atualizar na emissao

    Returns:
        CarviaEmissaoCte atualizada (ou None se falhar max_retries)

    Raises:
        Exception: apos esgotar max_retries
    """
    from app import db
    from app.carvia.models import CarviaEmissaoCte
    from app.utils.database_helpers import ensure_connection
    from app.utils.timezone import agora_utc_naive

    last_exc = None
    for tentativa in range(max_retries):
        try:
            # Garantir conexao viva (reabre pool se necessario)
            ensure_connection()

            # Re-buscar emissao (pode estar detached pos-Playwright)
            emissao = db.session.get(CarviaEmissaoCte, emissao_id)
            if not emissao:
                raise ValueError(
                    f"Emissao {emissao_id} nao encontrada no commit pos-playwright"
                )

            # Aplicar updates
            for campo, valor in updates.items():
                setattr(emissao, campo, valor)
            emissao.atualizado_em = agora_utc_naive()

            db.session.commit()
            return emissao

        except Exception as e:
            last_exc = e
            logger.warning(
                "Commit pos-playwright emissao=%s tentativa %d/%d falhou: %s",
                emissao_id, tentativa + 1, max_retries, e
            )
            # Limpar sessao/pool
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
                # Backoff exponencial: 1s, 2s, 4s
                time.sleep(2 ** tentativa)

    logger.error(
        "Commit pos-playwright emissao=%s falhou definitivamente: %s",
        emissao_id, last_exc
    )
    raise last_exc


def emitir_cte_ssw_job(emissao_id: int) -> dict:
    """Job RQ: executa fluxo completo de emissao CTe + fatura SSW.

    Este job e executado fora do contexto Flask — cria seu proprio app context.
    Atualiza CarviaEmissaoCte.etapa a cada passo para tracking.

    Args:
        emissao_id: ID do registro CarviaEmissaoCte

    Returns:
        dict com {status, ctrc, fatura_numero, erro}
    """
    from app import create_app, db

    app = create_app()
    with app.app_context():
        from app.carvia.models import CarviaEmissaoCte
        from app.carvia.services.documentos.ssw_emissao_service import SswEmissaoService
        from app.utils.timezone import agora_utc_naive

        emissao = db.session.get(CarviaEmissaoCte, emissao_id)
        if not emissao:
            logger.error("Emissao %s nao encontrada", emissao_id)
            return {'status': 'ERRO', 'erro': 'Emissao nao encontrada'}

        if emissao.status not in ('PENDENTE', 'EM_PROCESSAMENTO'):
            logger.warning(
                "Emissao %s nao esta PENDENTE (status=%s) — ignorando",
                emissao_id, emissao.status
            )
            return {'status': emissao.status}

        emissao.status = 'EM_PROCESSAMENTO'
        emissao.etapa = 'LOGIN'
        emissao.atualizado_em = agora_utc_naive()
        db.session.commit()

        try:
            # ── Fase A: Emitir CTe (tela 004, filial CAR) ──
            emissao.etapa = 'PREENCHIMENTO'
            db.session.commit()

            # Extrair args DO ORM antes do Playwright (pattern P1: Anti-Detach)
            args_cte = _montar_args_cte(emissao)

            # P7: Commit + liberar conexao antes do Playwright longo
            # (60-120s) — evita SSL drop por idle timeout do Postgres.
            _liberar_conexao_antes_playwright()

            resultado_cte = _executar_script_cte(args_cte)

            # Detectar erros SSW
            erro = SswEmissaoService.detectar_erro_ssw(resultado_cte)
            if erro or not resultado_cte.get('sucesso'):
                erro_msg = erro or resultado_cte.get('erro', 'Falha na emissao')
                _commit_pos_playwright(
                    emissao_id,
                    status='ERRO',
                    erro_ssw=erro_msg,
                    resultado_json=_sanitize_resultado(resultado_cte),
                )
                logger.error("Emissao %s falhou: %s", emissao_id, erro_msg)
                return {'status': 'ERRO', 'erro': erro_msg}

            # Commit pos-Playwright com reconnect + retry (evita SSL drop)
            emissao = _commit_pos_playwright(
                emissao_id,
                ctrc_numero=resultado_cte.get('ctrc'),
                resultado_json=_sanitize_resultado(resultado_cte),
                etapa='IMPORTACAO_CTE',
            )

            logger.info("Emissao %s — CTe %s emitido", emissao_id, emissao.ctrc_numero)

            # ── Fase B: Baixar XML/DACTE via consultar_ctrc_101 e importar ──
            # Chamamos `consultar_ctrc_101.py` em NOVA sessao Playwright —
            # script read-only reusado por varios fluxos (verificar_ctrc,
            # baixar_pdf, botao manual). Separacao de responsabilidades:
            # 004 emite, 101 consulta/baixa. Retry 2x mitiga timing
            # do SSW (CTe recem-autorizado pode demorar a aparecer).
            #
            # Ao contrario do fluxo antigo, aplicamos o CTRC autoritativo
            # retornado pela 101 ANTES da importacao — elimina a race
            # condition em que `CarviaOperacao` nasce com ctrc_numero
            # provisorio e depois e corrigido por job tardio.
            ctrc_numero_local = emissao.ctrc_numero
            filial_local = emissao.filial_ssw or 'CAR'
            operacao_id_pos_import = None
            try:
                from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                    _formatar_ctrc_ssw,
                )
                from app.utils.database_helpers import ensure_connection

                # Libera conexao antes do Playwright (opcao 101)
                _liberar_conexao_antes_playwright()

                # Retry 2x — SSW as vezes demora pra 101 encontrar CTe
                # recem-emitido; backoff linear (8s extra na segunda).
                resultado_consulta = None
                for tentativa in range(2):
                    resultado_consulta = _executar_consulta_101(
                        ctrc_numero_local, filial=filial_local
                    )
                    if resultado_consulta.get('sucesso') and (
                        resultado_consulta.get('xml') or
                        resultado_consulta.get('dacte')
                    ):
                        break
                    if tentativa == 0:
                        logger.info(
                            "Emissao %s — 101 sem downloads na 1a tentativa, "
                            "retry em 8s", emissao_id,
                        )
                        time.sleep(8)

                if resultado_consulta and resultado_consulta.get('sucesso'):
                    resultado_cte['xml'] = resultado_consulta.get('xml')
                    resultado_cte['dacte'] = resultado_consulta.get('dacte')

                    # CTRC autoritativo retornado pela 101 (formato SSW)
                    ctrc_completo_ssw = (
                        resultado_consulta.get('dados', {}) or {}
                    ).get('ctrc_completo')
                    ctrc_final = _formatar_ctrc_ssw(ctrc_completo_ssw)

                    if not ctrc_final:
                        # Fluxo raro: 101 respondeu OK mas sem ctrc_completo
                        # no body. CTRC provisorio da Fase A sera importado;
                        # `verificar_ctrc_operacao_job` fallback corrige.
                        logger.warning(
                            "Emissao %s — 101 retornou sucesso mas sem "
                            "ctrc_completo; CTRC provisorio %s sera "
                            "importado (fallback job corrige)",
                            emissao_id, emissao.ctrc_numero,
                        )
                else:
                    # 101 falhou em ambas tentativas — import com CTRC
                    # provisorio; fallback job corrige em background.
                    ctrc_final = None
                    logger.warning(
                        "Emissao %s — 101 falhou apos retry; CTRC "
                        "provisorio %s importado, fallback job corrige",
                        emissao_id, emissao.ctrc_numero,
                    )

                # Re-conecta e re-busca emissao antes de importar
                ensure_connection()
                emissao = db.session.get(CarviaEmissaoCte, emissao_id)

                # Atualizar CTRC autoritativo ANTES da importacao — fica
                # coerente na criacao da CarviaOperacao.
                if ctrc_final and emissao.ctrc_numero != ctrc_final:
                    logger.info(
                        "Emissao %s — CTRC corrigido via 101: %s -> %s",
                        emissao_id, emissao.ctrc_numero, ctrc_final,
                    )
                    emissao.ctrc_numero = ctrc_final

                SswEmissaoService.importar_resultado_cte(emissao, resultado_cte)

                db.session.commit()

                # Capturar operacao_id APOS commit — usado como fallback
                # para enfileirar `verificar_ctrc_operacao_job` se a 101
                # nao retornou ctrc autoritativo (pos-fase C).
                operacao_id_pos_import = emissao.operacao_id
            except Exception as e:
                logger.warning("Falha ao importar XML (nao-bloqueante): %s", e)
                # Garantir sessao limpa mesmo se commit acima falhar
                try:
                    db.session.rollback()
                except Exception:
                    pass

            # ── Fase C: Gerar fatura SSW (tela 437, filial MTZ) ──
            # Re-buscar emissao garantidamente antes de checar dados
            try:
                from app.utils.database_helpers import ensure_connection
                ensure_connection()
                emissao = db.session.get(CarviaEmissaoCte, emissao_id)
            except Exception:
                emissao = None

            if emissao and emissao.cnpj_tomador and emissao.ctrc_numero:
                # Snapshot antes do Playwright
                cnpj_tomador_local = emissao.cnpj_tomador
                ctrc_numero_local = emissao.ctrc_numero
                data_venc_local = emissao.data_vencimento

                # Atualizar etapa com retry
                _commit_pos_playwright(emissao_id, etapa='FATURA_437')

                # Liberar conexao antes da fatura 437 (Playwright longo)
                _liberar_conexao_antes_playwright()

                args_fat = _montar_args_fatura_from_snapshot(
                    cnpj_tomador_local, ctrc_numero_local, data_venc_local
                )
                resultado_fat = _executar_script_fatura(args_fat)

                if resultado_fat.get('sucesso'):
                    fatura_numero = resultado_fat.get('fatura_numero')

                    # Atualizar etapa com retry + reconnect
                    _commit_pos_playwright(
                        emissao_id,
                        etapa='IMPORTACAO_FAT',
                        fatura_numero=fatura_numero,
                    )

                    # Re-buscar emissao para importar
                    try:
                        from app.utils.database_helpers import ensure_connection
                        ensure_connection()
                        emissao = db.session.get(CarviaEmissaoCte, emissao_id)
                        SswEmissaoService.importar_resultado_fatura(
                            emissao, resultado_fat
                        )
                        db.session.commit()
                    except Exception as e:
                        logger.warning(
                            "Falha ao importar fatura (nao-bloqueante): %s", e
                        )
                        try:
                            db.session.rollback()
                        except Exception:
                            pass

                    logger.info(
                        "Emissao %s — Fatura %s gerada",
                        emissao_id, fatura_numero
                    )
                else:
                    erro_fat = resultado_fat.get('erro', 'Falha ao gerar fatura')
                    logger.warning("Fatura 437 falhou (nao-bloqueante): %s", erro_fat)
                    # Anexar erro ao erro_ssw sem quebrar fluxo
                    try:
                        _commit_pos_playwright(
                            emissao_id,
                            erro_ssw=f"Fatura 437: {erro_fat}",
                        )
                    except Exception:
                        pass

            # ── Sucesso ──
            emissao = _commit_pos_playwright(
                emissao_id,
                status='SUCESSO',
                etapa=None,
            )

            # Fallback: se a 101 da Fase B NAO retornou ctrc_completo
            # (timing SSW, rede, etc.), enfileirar verificacao tardia
            # por `--cte {nCT}` (fonte autoritativa do XML). Em fluxo
            # normal — Fase B ja corrigiu o CTRC — este job retorna
            # status='OK' sem alteracao.
            op_id_verificar = operacao_id_pos_import or emissao.operacao_id
            if op_id_verificar:
                try:
                    from app.portal.workers import enqueue_job
                    from app.carvia.workers.verificar_ctrc_ssw_jobs import (
                        verificar_ctrc_operacao_job,
                    )
                    enqueue_job(
                        verificar_ctrc_operacao_job,
                        op_id_verificar,
                        queue_name='default',
                        timeout='10m',
                    )
                    logger.info(
                        "Emissao %s: job verificar_ctrc_operacao "
                        "enfileirado (fallback, op=%s)",
                        emissao_id, op_id_verificar,
                    )
                except Exception as e_job:
                    logger.warning(
                        "Falha ao enfileirar verificar_ctrc_operacao_job "
                        "para op %s: %s",
                        op_id_verificar, e_job,
                    )

            logger.info(
                "Emissao %s concluida: CTe=%s, Fatura=%s",
                emissao_id, emissao.ctrc_numero, emissao.fatura_numero
            )
            return {
                'status': 'SUCESSO',
                'ctrc': emissao.ctrc_numero,
                'fatura_numero': emissao.fatura_numero,
                'operacao_id': emissao.operacao_id,
            }

        except Exception as e:
            logger.exception("Emissao %s — excecao: %s", emissao_id, e)
            # Commit do ERRO com retry (SSL drop pode acontecer aqui tambem)
            try:
                _commit_pos_playwright(
                    emissao_id,
                    status='ERRO',
                    erro_ssw=str(e),
                )
            except Exception as e_commit:
                logger.error(
                    "Falha ao gravar ERRO da emissao %s: %s",
                    emissao_id, e_commit
                )
            return {'status': 'ERRO', 'erro': str(e)}


def _montar_args_cte(emissao):
    """Monta argparse.Namespace para emitir_cte()."""
    from app import db
    from app.carvia.models import CarviaNf

    nf = db.session.get(CarviaNf, emissao.nf_id)
    if not nf:
        raise ValueError(
            f"NF {emissao.nf_id} nao encontrada (deletada apos enfileiramento?)"
        )

    # Medidas: ja estao em metros no medidas_json
    medidas = None
    if emissao.medidas_json:
        medidas = json.dumps(emissao.medidas_json)

    return argparse.Namespace(
        chave_nfe=nf.chave_acesso_nf,
        placa=emissao.placa or 'ARMAZEM',
        frete_peso=float(emissao.frete_valor or 0),
        filial=emissao.filial_ssw or 'CAR',
        medidas=medidas,
        enviar_sefaz=True,
        consultar_101=True,
        baixar_dacte=True,
        baixar_xml=True,
        dry_run=False,
        discover=False,
        defaults_file=os.path.join(SSW_SCRIPTS, '..', 'ssw_defaults.json'),
    )


def _montar_args_fatura(emissao):
    """Monta argparse.Namespace para gerar_fatura() a partir do objeto ORM."""
    return _montar_args_fatura_from_snapshot(
        emissao.cnpj_tomador,
        emissao.ctrc_numero,
        emissao.data_vencimento,
    )


def _montar_args_fatura_from_snapshot(cnpj_tomador, ctrc_numero, data_vencimento):
    """Monta argparse.Namespace para gerar_fatura() sem depender do ORM.

    Usado no fluxo pos-Playwright quando a sessao foi liberada e o objeto
    emissao pode estar detached.
    """
    data_venc = None
    if data_vencimento:
        data_venc = data_vencimento.strftime('%d%m%y')

    return argparse.Namespace(
        cnpj_tomador=cnpj_tomador,
        ctrc=ctrc_numero,
        data_vencimento=data_venc,
        baixar_pdf=True,
        dry_run=False,
    )


def _executar_script_cte(args):
    """Executa emitir_cte() do script Playwright (async → sync via asyncio.run)."""
    # Adicionar path dos scripts SSW
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from emitir_cte_004 import emitir_cte
    return asyncio.run(emitir_cte(args))


def _executar_consulta_101(ctrc_numero, filial='CAR'):
    """Executa consultar_ctrc_101.py para baixar XML e DACTE do CTe emitido.

    Script READ-ONLY reusado por varios fluxos (emissao Fase B,
    verificar_ctrc_operacao_job, baixar_pdf_ssw_operacao_job,
    botao "Atualizar CTe SSW"). Sempre nova sessao Playwright
    (30-60s overhead) — trade-off aceito por clareza e reuso.
    """
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from consultar_ctrc_101 import consultar_ctrc

    args_101 = argparse.Namespace(
        ctrc=str(ctrc_numero),
        nf=None,
        cte=None,
        filial=filial,
        baixar_xml=True,
        baixar_dacte=True,
        output_dir='/tmp/ssw_operacoes/consulta_101',
    )
    return asyncio.run(consultar_ctrc(args_101))


def _executar_script_fatura(args):
    """Executa gerar_fatura() do script Playwright (async → sync via asyncio.run)."""
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from gerar_fatura_ssw_437 import gerar_fatura
    return asyncio.run(gerar_fatura(args))


def _sanitize_resultado(resultado):
    """Remove campos muito grandes do resultado para armazenar no JSONB."""
    if not isinstance(resultado, dict):
        return resultado

    sanitized = {}
    for key, value in resultado.items():
        if key in ('screenshot', 'body_raw'):
            continue  # Muito grande para JSONB
        if isinstance(value, str) and len(value) > 5000:
            sanitized[key] = value[:5000] + '...(truncado)'
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_resultado(value)
        else:
            sanitized[key] = value

    return sanitized



# NOTA: _montar_args_cte e _montar_args_fatura fazem lazy import de `db`
# dentro de suas funcoes (regra R2 — CarVia CLAUDE.md)
