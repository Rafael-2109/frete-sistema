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

            # Snapshot do resultado (+ paths S3) e metadados na emissao
            sanitized = _sanitize_resultado(resultado)
            if extras_resultado:
                sanitized.update(extras_resultado)
            emissao.resultado_json = sanitized
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


def _persistir_artefatos_complementar(cte_comp, resultado):
    """Extrai XML do ZIP baixado, parseia metadados e sobe XML+DACTE no S3.

    Preenche os campos do CarviaCteComplementar com os dados do XML real
    (chave_acesso, numero, data emissao, valor, xml_path) e retorna os
    caminhos S3 para persistir no resultado_json da emissao.

    Args:
        cte_comp: CarviaCteComplementar ja com ctrc_numero preenchido
        resultado: dict retornado por emitir_cte_complementar() com chaves
                   'xml' (path local do ZIP) e 'dacte' (path local PDF)

    Returns:
        dict com chaves xml_s3_path, dacte_s3_path, cte_chave_acesso,
        cte_numero, cte_data_emissao (ISO), cte_valor_parsed, e possiveis
        chaves *_erro quando algo falha.
    """
    import zipfile
    from datetime import date, datetime
    from io import BytesIO

    from app.utils.file_storage import get_file_storage
    from app.carvia.services.parsers.cte_xml_parser_carvia import (
        CTeXMLParserCarvia,
    )

    extras = {}
    storage = get_file_storage()

    # 1) Extrair XML do ZIP (SSW sempre retorna XML em ZIP via opcao 101)
    xml_path_local = resultado.get('xml')
    xml_bytes = None
    xml_nome = None
    if xml_path_local and os.path.exists(xml_path_local):
        try:
            with zipfile.ZipFile(xml_path_local) as z:
                for nome in z.namelist():
                    if nome.lower().endswith('.xml'):
                        xml_bytes = z.read(nome)
                        xml_nome = os.path.basename(nome)
                        break
        except zipfile.BadZipFile:
            # Fallback: XML pode vir direto (sem ZIP) em casos extremos
            try:
                with open(xml_path_local, 'rb') as f:
                    xml_bytes = f.read()
                xml_nome = os.path.basename(xml_path_local)
            except Exception as e_read:
                logger.warning("Falha ao ler XML local: %s", e_read)

    # 2) Parsear XML para extrair metadados e atualizar cte_comp
    if xml_bytes:
        try:
            xml_str = xml_bytes.decode('utf-8', errors='replace')
            parser = CTeXMLParserCarvia(xml_str)
            dados = parser.get_todas_informacoes_carvia()
            chave = dados.get('cte_chave_acesso')
            numero_cte = dados.get('cte_numero')
            data_emi_str = dados.get('cte_data_emissao')
            valor_prest = dados.get('cte_valor')

            if chave:
                cte_comp.cte_chave_acesso = chave
            if numero_cte:
                cte_comp.cte_numero = numero_cte
            if valor_prest is not None:
                try:
                    cte_comp.cte_valor = float(valor_prest)
                except (TypeError, ValueError):
                    pass
            if data_emi_str:
                try:
                    # dhEmi em ISO: 2026-04-09T14:30:00-03:00
                    if 'T' in data_emi_str:
                        # fromisoformat aceita timezone em Python 3.11+
                        cte_comp.cte_data_emissao = datetime.fromisoformat(
                            data_emi_str
                        ).date()
                    else:
                        cte_comp.cte_data_emissao = date.fromisoformat(
                            data_emi_str[:10]
                        )
                except (ValueError, TypeError) as e_date:
                    logger.warning(
                        "Parse data emissao CTe comp falhou (%s): %s",
                        data_emi_str, e_date
                    )

            extras.update({
                'cte_chave_acesso': chave,
                'cte_numero': numero_cte,
                'cte_data_emissao': data_emi_str,
                'cte_valor_parsed': (
                    float(valor_prest) if valor_prest is not None else None
                ),
            })

            # 3) Subir XML no S3
            if not xml_nome:
                xml_nome = (
                    f"{chave}-cte.xml" if chave else "cte-complementar.xml"
                )
            xml_buffer = BytesIO(xml_bytes)
            xml_buffer.name = xml_nome
            xml_s3_path = storage.save_file(
                xml_buffer,
                folder='carvia/ctes_complementares_xml',
                filename=xml_nome,
            )
            if xml_s3_path:
                cte_comp.cte_xml_path = xml_s3_path
                cte_comp.cte_xml_nome_arquivo = xml_nome
                extras['xml_s3_path'] = xml_s3_path
                extras['xml_nome_arquivo'] = xml_nome
        except Exception as e:
            logger.warning("Falha ao parsear/persistir XML complementar: %s", e)
            extras['xml_parse_erro'] = str(e)

    # 4) Subir DACTE PDF no S3 (caminho armazenado em resultado_json da emissao)
    dacte_path_local = resultado.get('dacte')
    if dacte_path_local and os.path.exists(dacte_path_local):
        try:
            with open(dacte_path_local, 'rb') as f:
                pdf_bytes = f.read()
            dacte_nome = (
                f"{cte_comp.ctrc_numero or cte_comp.numero_comp}-dacte.pdf"
            )
            pdf_buffer = BytesIO(pdf_bytes)
            pdf_buffer.name = dacte_nome
            dacte_s3_path = storage.save_file(
                pdf_buffer,
                folder='carvia/ctes_complementares_dacte',
                filename=dacte_nome,
            )
            if dacte_s3_path:
                extras['dacte_s3_path'] = dacte_s3_path
                extras['dacte_nome_arquivo'] = dacte_nome
        except Exception as e:
            logger.warning("Falha ao persistir DACTE: %s", e)
            extras['dacte_persist_erro'] = str(e)

    return extras
