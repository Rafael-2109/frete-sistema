"""
Job RQ: Emissao automatica de CTe Complementar no SSW (opcao 222).

Executado pelo worker_atacadao.py na fila 'high'.
Cada job dura 60-120s (Playwright headless) e atualiza
CarviaEmissaoCteComplementar.etapa para tracking de progresso via polling.

Etapas:
  1. PREENCHIMENTO — Preencher tela 222 (CTRC pai, motivo, valor)
  2. SEFAZ — Enviar ao SEFAZ
  3. CONSULTA_101 — Consultar resultado (opcional, se implementado)
"""
import argparse
import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SSW_SCRIPTS = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'operando-ssw', 'scripts'
)


def emitir_cte_complementar_job(emissao_comp_id: int) -> dict:
    """Job RQ: executa emissao de CTe Complementar via SSW opcao 222.

    Args:
        emissao_comp_id: ID do registro CarviaEmissaoCteComplementar

    Returns:
        dict com {status, ctrc_complementar, erro}
    """
    from app import create_app, db

    app = create_app()
    with app.app_context():
        from app.carvia.models import (
            CarviaEmissaoCteComplementar, CarviaCteComplementar,
        )
        from app.utils.timezone import agora_utc_naive

        emissao = db.session.get(CarviaEmissaoCteComplementar, emissao_comp_id)
        if not emissao:
            logger.error("EmissaoCteComp %s nao encontrada", emissao_comp_id)
            return {'status': 'ERRO', 'erro': 'Emissao nao encontrada'}

        if emissao.status not in ('PENDENTE', 'EM_PROCESSAMENTO'):
            logger.warning(
                "EmissaoCteComp %s nao esta PENDENTE (status=%s)",
                emissao_comp_id, emissao.status
            )
            return {'status': emissao.status}

        emissao.status = 'EM_PROCESSAMENTO'
        emissao.etapa = 'PREENCHIMENTO'
        emissao.atualizado_em = agora_utc_naive()
        db.session.commit()

        try:
            # ── Fase 0: Resolver CTRC real via SSW (fallback) ──
            ctrc_pai = emissao.ctrc_pai
            ctrc_resolvido = _resolver_ctrc_ssw(ctrc_pai, emissao.filial_ssw or 'CAR')
            if ctrc_resolvido and ctrc_resolvido != ctrc_pai:
                logger.info(
                    "EmissaoCteComp %s — CTRC resolvido: %s → %s",
                    emissao_comp_id, ctrc_pai, ctrc_resolvido
                )
                ctrc_pai = ctrc_resolvido
                emissao.ctrc_pai = ctrc_resolvido
                db.session.commit()

            # ── Fase A: Emitir CTe Complementar (opcao 222) ──
            args_222 = argparse.Namespace(
                ctrc_pai=ctrc_pai,
                motivo=emissao.motivo_ssw,
                valor_outros=float(emissao.valor_calculado),
                filial=emissao.filial_ssw or 'CAR',
                dry_run=False,
            )
            resultado = _executar_script_222(args_222)

            if not resultado.get('sucesso'):
                emissao.status = 'ERRO'
                emissao.erro_ssw = resultado.get('erro', 'Falha na emissao')
                emissao.resultado_json = _sanitize_resultado(resultado)
                emissao.atualizado_em = agora_utc_naive()
                db.session.commit()
                logger.error(
                    "EmissaoCteComp %s falhou: %s",
                    emissao_comp_id, emissao.erro_ssw
                )
                return {'status': 'ERRO', 'erro': emissao.erro_ssw}

            # ── Fase B: Sucesso — atualizar registros ──
            ctrc_comp = resultado.get('ctrc_complementar')
            emissao.resultado_json = _sanitize_resultado(resultado)
            emissao.etapa = None

            # Atualizar CTe Complementar — so marca EMITIDO se tiver CTRC real
            cte_comp = db.session.get(
                CarviaCteComplementar, emissao.cte_complementar_id
            )
            if cte_comp and ctrc_comp:
                cte_comp.status = 'EMITIDO'
                cte_comp.ctrc_numero = ctrc_comp
                emissao.status = 'SUCESSO'
            elif cte_comp:
                # SSW retornou sucesso mas sem CTRC — marcar como pendente de verificacao
                emissao.status = 'SUCESSO'
                emissao.erro_ssw = (
                    resultado.get('aviso')
                    or 'SSW nao retornou CTRC — verificar manualmente'
                )
                # CteComplementar permanece RASCUNHO ate confirmar no SSW

            emissao.atualizado_em = agora_utc_naive()
            db.session.commit()

            logger.info(
                "EmissaoCteComp %s concluida: CTRC=%s",
                emissao_comp_id, ctrc_comp
            )
            return {
                'status': 'SUCESSO',
                'ctrc_complementar': ctrc_comp,
                'cte_complementar_id': emissao.cte_complementar_id,
            }

        except Exception as e:
            emissao.status = 'ERRO'
            emissao.erro_ssw = str(e)
            emissao.atualizado_em = agora_utc_naive()
            db.session.commit()
            logger.exception("EmissaoCteComp %s — excecao: %s", emissao_comp_id, e)
            return {'status': 'ERRO', 'erro': str(e)}


def _resolver_ctrc_ssw(ctrc_pai, filial='CAR'):
    """Verifica se o CTRC armazenado corresponde ao correto no SSW.

    O ctrc_pai pode ter sido construido errado (nCT em vez de CTRC).
    Consulta opcao 101 pelo numero e verifica se o CT-e bate.

    Args:
        ctrc_pai: CTRC armazenado (ex: 'CAR-110-9')
        filial: Filial SSW

    Returns:
        CTRC corrigido (ex: 'CAR-113-9') ou None se nao precisar corrigir
    """
    import re

    # Extrair numero do CTRC atual
    m = re.match(r'^[A-Z]+-(\d+)', ctrc_pai)
    if not m:
        return None

    ctrc_num = m.group(1)

    try:
        if SSW_SCRIPTS not in sys.path:
            sys.path.insert(0, SSW_SCRIPTS)

        from consultar_ctrc_101 import consultar_ctrc
        import argparse as ap

        args_101 = ap.Namespace(
            ctrc=ctrc_num,
            nf=None,
            filial=filial,
            baixar_xml=False,
            baixar_dacte=False,
            output_dir='/tmp/ssw_operacoes/resolver_ctrc',
        )
        resultado = asyncio.run(consultar_ctrc(args_101))

        if not resultado.get('sucesso'):
            logger.warning("Nao conseguiu consultar CTRC %s no SSW", ctrc_num)
            return None

        dados = resultado.get('dados', {})
        ctrc_completo = dados.get('ctrc_completo')  # Ex: CAR000113-9

        if ctrc_completo:
            # Formatar: CAR000113-9 → CAR-113-9
            m2 = re.match(r'^([A-Z]{2,4})0*(\d+)-(\d)$', ctrc_completo)
            if m2:
                return f'{m2.group(1)}-{m2.group(2)}-{m2.group(3)}'

        return None
    except Exception as e:
        logger.warning("Erro ao resolver CTRC via SSW: %s", e)
        return None


def _executar_script_222(args):
    """Executa emitir_cte_complementar() do script Playwright."""
    if SSW_SCRIPTS not in sys.path:
        sys.path.insert(0, SSW_SCRIPTS)

    from emitir_cte_complementar_222 import emitir_cte_complementar
    return asyncio.run(emitir_cte_complementar(args))


def _sanitize_resultado(resultado):
    """Remove campos muito grandes do resultado para armazenar no JSONB."""
    if not isinstance(resultado, dict):
        return resultado

    sanitized = {}
    for key, value in resultado.items():
        if key in ('screenshot', 'body_raw'):
            continue
        if isinstance(value, str) and len(value) > 5000:
            sanitized[key] = value[:5000] + '...(truncado)'
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_resultado(value)
        else:
            sanitized[key] = value

    return sanitized
