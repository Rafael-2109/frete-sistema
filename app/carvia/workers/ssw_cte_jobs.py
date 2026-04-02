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
"""
import argparse
import asyncio
import json
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Path do projeto para imports dos scripts SSW
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SSW_SCRIPTS = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'operando-ssw', 'scripts'
)


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

            args_cte = _montar_args_cte(emissao)
            resultado_cte = _executar_script_cte(args_cte)

            # Detectar erros SSW
            erro = SswEmissaoService.detectar_erro_ssw(resultado_cte)
            if erro or not resultado_cte.get('sucesso'):
                emissao.status = 'ERRO'
                emissao.erro_ssw = erro or resultado_cte.get('erro', 'Falha na emissao')
                emissao.resultado_json = _sanitize_resultado(resultado_cte)
                emissao.atualizado_em = agora_utc_naive()
                db.session.commit()
                logger.error(
                    "Emissao %s falhou: %s", emissao_id, emissao.erro_ssw
                )
                return {'status': 'ERRO', 'erro': emissao.erro_ssw}

            emissao.ctrc_numero = resultado_cte.get('ctrc')
            emissao.resultado_json = _sanitize_resultado(resultado_cte)
            emissao.etapa = 'IMPORTACAO_CTE'
            emissao.atualizado_em = agora_utc_naive()
            db.session.commit()

            logger.info("Emissao %s — CTe %s emitido", emissao_id, emissao.ctrc_numero)

            # ── Fase B: Baixar XML/DACTE via consultar_ctrc_101 e importar ──
            try:
                resultado_consulta = _executar_consulta_101(
                    emissao.ctrc_numero, filial=emissao.filial_ssw or 'CAR'
                )
                if resultado_consulta.get('sucesso'):
                    # Mesclar paths de XML/DACTE no resultado
                    resultado_cte['xml'] = resultado_consulta.get('xml')
                    resultado_cte['dacte'] = resultado_consulta.get('dacte')

                SswEmissaoService.importar_resultado_cte(emissao, resultado_cte)
                db.session.commit()
            except Exception as e:
                logger.warning("Falha ao importar XML (nao-bloqueante): %s", e)

            # ── Fase C: Gerar fatura SSW (tela 437, filial MTZ) ──
            if emissao.cnpj_tomador and emissao.ctrc_numero:
                emissao.etapa = 'FATURA_437'
                emissao.atualizado_em = agora_utc_naive()
                db.session.commit()

                args_fat = _montar_args_fatura(emissao)
                resultado_fat = _executar_script_fatura(args_fat)

                if resultado_fat.get('sucesso'):
                    emissao.fatura_numero = resultado_fat.get('fatura_numero')

                    # ── Fase D: Importar PDF fatura ──
                    emissao.etapa = 'IMPORTACAO_FAT'
                    emissao.atualizado_em = agora_utc_naive()
                    db.session.commit()

                    try:
                        SswEmissaoService.importar_resultado_fatura(emissao, resultado_fat)
                        db.session.commit()
                    except Exception as e:
                        logger.warning("Falha ao importar fatura (nao-bloqueante): %s", e)

                    logger.info(
                        "Emissao %s — Fatura %s gerada",
                        emissao_id, emissao.fatura_numero
                    )
                else:
                    erro_fat = resultado_fat.get('erro', 'Falha ao gerar fatura')
                    logger.warning("Fatura 437 falhou (nao-bloqueante): %s", erro_fat)
                    emissao.erro_ssw = (emissao.erro_ssw or '') + f"\nFatura: {erro_fat}"

            # ── Sucesso ──
            emissao.status = 'SUCESSO'
            emissao.etapa = None
            emissao.atualizado_em = agora_utc_naive()
            db.session.commit()

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
            emissao.status = 'ERRO'
            emissao.erro_ssw = str(e)
            emissao.atualizado_em = agora_utc_naive()
            db.session.commit()
            logger.exception("Emissao %s — excecao: %s", emissao_id, e)
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
    """Monta argparse.Namespace para gerar_fatura()."""
    # Data vencimento: converter para DDMMYY
    data_venc = None
    if emissao.data_vencimento:
        data_venc = emissao.data_vencimento.strftime('%d%m%y')

    return argparse.Namespace(
        cnpj_tomador=emissao.cnpj_tomador,
        ctrc=emissao.ctrc_numero,
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
    """Executa consultar_ctrc_101.py para baixar XML e DACTE do CTe emitido."""
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from consultar_ctrc_101 import consultar_ctrc

    args_101 = argparse.Namespace(
        ctrc=str(ctrc_numero),
        nf=None,
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
