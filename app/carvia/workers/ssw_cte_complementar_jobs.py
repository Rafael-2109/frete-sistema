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
            # Usa helper compartilhado (fonte unica de verdade). A funcao
            # antiga _resolver_ctrc_ssw neste arquivo foi removida.
            from app.carvia.services.cte_complementar_persistencia import (
                resolver_ctrc_ssw,
            )
            ctrc_pai = emissao.ctrc_pai
            ctrc_resolvido = resolver_ctrc_ssw(
                ctrc_pai, emissao.filial_ssw or 'CAR'
            )
            if ctrc_resolvido and ctrc_resolvido != ctrc_pai:
                logger.info(
                    "EmissaoCteComp %s — CTRC resolvido: %s → %s",
                    emissao_comp_id, ctrc_pai, ctrc_resolvido
                )
                ctrc_pai = ctrc_resolvido
                emissao.ctrc_pai = ctrc_resolvido
                db.session.commit()

            # ── Fase A: Emitir CTe Complementar (opcao 222 + 007 + 101) ──
            # O script consulta opcao 101 do pai para extrair ICMS ao vivo e
            # calcula o grossing up automaticamente. Passamos valor_base (bruto)
            # em vez de valor_outros para que o calculo use o ICMS real atual
            # do CTe pai no SSW (fonte de verdade) em vez do snapshot stale.
            custo_valor_base = float(emissao.custo_entrega.valor)
            args_222 = argparse.Namespace(
                ctrc_pai=ctrc_pai,
                motivo=emissao.motivo_ssw,
                valor_base=custo_valor_base,
                valor_outros=None,
                tp_doc='C',
                unid_emit='D',
                enviar_sefaz=True,
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

            # ── Fase B: Sucesso — backfill CarviaCteComplementar + persistir S3 ──
            ctrc_comp = resultado.get('ctrc_complementar')

            cte_comp = db.session.get(
                CarviaCteComplementar, emissao.cte_complementar_id
            )
            extras_resultado = {}
            if cte_comp and ctrc_comp:
                cte_comp.ctrc_numero = ctrc_comp
                cte_comp.status = 'EMITIDO'
                try:
                    extras_resultado = _persistir_artefatos_complementar(
                        cte_comp, resultado
                    )
                except Exception as e_persist:
                    logger.exception(
                        "EmissaoCteComp %s — sucesso no SSW mas falha ao "
                        "persistir artefatos: %s", emissao_comp_id, e_persist
                    )
                    extras_resultado = {'persistencia_erro': str(e_persist)}
                emissao.status = 'SUCESSO'
            elif cte_comp:
                # SSW retornou sucesso mas sem CTRC — marcar como pendente
                emissao.status = 'SUCESSO'
                emissao.erro_ssw = (
                    resultado.get('aviso')
                    or 'SSW nao retornou CTRC — verificar manualmente'
                )
                # CteComplementar permanece RASCUNHO ate confirmar no SSW

            # Snapshot do resultado (+ paths S3) e metadados na emissao.
            # Merge com precedencia explicita ao extras do helper: ha colisao
            # de chaves entre o output do Playwright e do helper (sucesso,
            # ctrc_complementar, valor_outros, icms_pai). O helper tem fonte
            # mais precisa (XML real + path S3) entao ganha sempre.
            sanitized = _sanitize_resultado(resultado)
            merged = {**sanitized, **(extras_resultado or {})}
            emissao.resultado_json = merged
            emissao.etapa = None

            # valor_outros do script = valor_calculado real (ICMS extraido ao vivo)
            if resultado.get('valor_outros') is not None:
                try:
                    emissao.valor_calculado = float(resultado['valor_outros'])
                except (TypeError, ValueError):
                    pass
            icms_pai = resultado.get('icms_pai') or {}
            aliquota_real = icms_pai.get('aliquota_icms')
            if aliquota_real is not None:
                try:
                    emissao.icms_aliquota_usada = float(aliquota_real)
                except (TypeError, ValueError):
                    pass

            emissao.atualizado_em = agora_utc_naive()
            db.session.commit()

            logger.info(
                "EmissaoCteComp %s concluida: CTRC=%s, valor=%s, icms=%s%%, "
                "xml=%s",
                emissao_comp_id, ctrc_comp,
                resultado.get('valor_outros'),
                aliquota_real,
                extras_resultado.get('xml_s3_path'),
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


def _extrair_xml_do_zip(xml_path_local):
    """Extrai bytes do XML de dentro do ZIP baixado pela opcao 101 do SSW.

    Returns:
        Tupla (xml_bytes, xml_nome) ou (None, None) se falhar.
    """
    import zipfile

    if not xml_path_local or not os.path.exists(xml_path_local):
        return None, None

    try:
        with zipfile.ZipFile(xml_path_local) as z:
            for nome in z.namelist():
                if nome.lower().endswith('.xml'):
                    return z.read(nome), os.path.basename(nome)
    except zipfile.BadZipFile:
        # Fallback: XML pode vir direto (sem ZIP) em casos extremos
        try:
            with open(xml_path_local, 'rb') as f:
                return f.read(), os.path.basename(xml_path_local)
        except Exception as e_read:
            logger.warning("Falha ao ler XML local: %s", e_read)
            return None, None

    return None, None


def _ler_arquivo_local(path):
    """Le bytes de um arquivo local. Returns None se falhar."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.warning("Falha ao ler arquivo local %s: %s", path, e)
        return None


def _persistir_artefatos_complementar(cte_comp, resultado):
    """Wrapper para o helper compartilhado de persistencia.

    Extrai bytes do XML (do ZIP) e do DACTE local, depois delega TUDO
    (parser, S3 upload, atualizacao de CarviaEmissaoCteComplementar,
    vinculo de CarviaCustoEntrega) para o helper compartilhado.

    Args:
        cte_comp: CarviaCteComplementar ja com ctrc_numero preenchido
                  (capturado pelo Playwright na opcao 222)
        resultado: dict retornado por emitir_cte_complementar() com chaves
                   'xml' (path local do ZIP), 'dacte' (path local PDF),
                   'icms_pai' (dict extraido ao vivo pelo script da opcao 101),
                   'valor_outros' (valor real apos grossing up)

    Returns:
        dict (mesmo schema do `resultado_json` da emissao):
        sucesso, status, xml_s3_path, dacte_s3_path, icms_pai, etc.
    """
    from app.carvia.services.cte_complementar_persistencia import (
        persistir_cte_complementar_completo,
    )

    # Extrair bytes do XML (do ZIP) e DACTE local
    xml_bytes, xml_nome = _extrair_xml_do_zip(resultado.get('xml'))
    dacte_bytes = _ler_arquivo_local(resultado.get('dacte'))

    # Custo entrega ja foi vinculado pela rota gerar_cte_complementar
    # ANTES de enfileirar o job (cte_comp.custos_entrega tem 1 elemento)
    custo_entrega = None
    try:
        custo_entrega = cte_comp.custos_entrega.first()
    except Exception:
        pass

    # ICMS pai vem do resultado do script (extraido ao vivo do SSW opcao 101)
    icms_pai_dict = resultado.get('icms_pai')
    valor_outros = resultado.get('valor_outros')
    valor_calculado_final = (
        float(valor_outros) if valor_outros is not None else None
    )

    return persistir_cte_complementar_completo(
        cte_comp=cte_comp,
        xml_bytes=xml_bytes,
        xml_nome=xml_nome,
        dacte_bytes=dacte_bytes,
        custo_entrega=custo_entrega,
        # motivo_ssw e filial_ssw ja estao na emissao existente — helper
        # nao recria, apenas atualiza. Os defaults aqui sao fallback se
        # por algum motivo a emissao nao existir.
        motivo_ssw='C',
        filial_ssw='CAR',
        icms_pai=icms_pai_dict,
        valor_calculado=valor_calculado_final,
        criado_por='worker_ssw',
        origem='WORKER_SSW',
    )
