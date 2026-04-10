"""
Persistência completa de CTe Complementar — helper compartilhado
==================================================================

Fonte única de verdade para gravar registros de CTe Complementar de modo
funcionalmente IDÊNTICO em todos os fluxos:

  - **Worker SSW** (`app/carvia/workers/ssw_cte_complementar_jobs.py`):
    emissão automática via Playwright (opção 222 do SSW). XML+DACTE
    vêm baixados da opção 101.
  - **Importação manual** (`app/carvia/services/parsers/importacao_service.py`):
    usuário sobe XML (e opcionalmente DACTE) via `/carvia/importar`.

Operações:
  1. Parser XML (`CTeXMLParserCarvia`) → preenche metadados em `CarviaCteComplementar`
  2. Detecta status `EMITIDO` via `<protCTe>/cStat=100`
  3. Upload XML para S3 em `carvia/ctes_complementares_xml/`
  4. Upload DACTE PDF para S3 em `carvia/ctes_complementares_dacte/` (opcional)
  5. Vincula `CarviaCustoEntrega.cte_complementar_id` (FK)
  6. Cria `CarviaEmissaoCteComplementar` com `resultado_json` no schema esperado
     pela rota `/ctes-complementares/<id>/download/dacte`
  7. Resolução opcional de CTRC via SSW (consulta opção 101)

**Não commita** — o caller é responsável por `db.session.commit()`.
"""

import asyncio
import logging
import os
import re
import sys
from datetime import date, datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Folders S3 — DEVEM ser idênticos aos usados pelo worker SSW.
# Mudar aqui exige atualizar a rota de download (cte_complementar_routes.py).
S3_FOLDER_XML = 'carvia/ctes_complementares_xml'
S3_FOLDER_DACTE = 'carvia/ctes_complementares_dacte'


# ────────────────────────────────────────────────────────────────────────────
# Parser XML
# ────────────────────────────────────────────────────────────────────────────

def parsear_xml_complementar(xml_bytes: bytes) -> Dict[str, Any]:
    """Parseia XML de CTe Complementar e retorna dict com metadados.

    Returns:
        dict com chaves:
            cte_chave_acesso, cte_numero, ctrc_numero, cte_valor,
            cte_data_emissao (str ISO), tipo_cte, info_complementar,
            impostos, protocolo_autorizacao
    """
    from app.carvia.services.parsers.cte_xml_parser_carvia import (
        CTeXMLParserCarvia,
    )

    xml_str = xml_bytes.decode('utf-8', errors='replace')
    parser = CTeXMLParserCarvia(xml_str)
    return {
        'cte_chave_acesso': parser.get_chave_acesso(),
        'cte_numero': parser.get_numero_cte(),
        'ctrc_numero': parser.get_ctrc_formatado(),
        'cte_valor': parser.get_valor_prestacao(),
        'cte_data_emissao': parser.get_data_emissao(),
        'tipo_cte': parser.get_tipo_cte(),
        'info_complementar': parser.get_info_complementar(),
        'impostos': parser.get_impostos(),
        'protocolo_autorizacao': parser.get_protocolo_autorizacao(),
    }


def parsear_data_emissao(data_str: Optional[Any]) -> Optional[date]:
    """Converte string ISO da tag `<dhEmi>` para `date`.

    Aceita:
      - `date` ou `datetime` (passa direto)
      - `'2026-04-09T14:30:00-03:00'` (ISO com timezone)
      - `'2026-04-09'` (apenas data)
    """
    if data_str is None:
        return None
    if isinstance(data_str, date) and not isinstance(data_str, datetime):
        return data_str
    if isinstance(data_str, datetime):
        return data_str.date()
    if not isinstance(data_str, str):
        return None
    try:
        if 'T' in data_str:
            try:
                # Python 3.11+ aceita timezone em fromisoformat
                return datetime.fromisoformat(data_str).date()
            except ValueError:
                # Fallback: limpa timezone manualmente
                clean = data_str
                if '+' in clean:
                    clean = clean.split('+')[0]
                elif clean.count('-') > 2:
                    parts = clean.rsplit('-', 1)
                    if ':' in parts[-1]:
                        clean = parts[0]
                return datetime.fromisoformat(clean).date()
        return date.fromisoformat(data_str[:10])
    except (ValueError, TypeError) as e:
        logger.warning(
            "Falha ao parsear data emissao CTe '%s': %s", data_str, e
        )
        return None


# ────────────────────────────────────────────────────────────────────────────
# Upload S3
# ────────────────────────────────────────────────────────────────────────────

def upload_xml_s3(xml_bytes: bytes, xml_nome: str) -> Optional[str]:
    """Upload XML para folder padronizado e retorna path S3."""
    from app.utils.file_storage import get_file_storage

    storage = get_file_storage()
    buf = BytesIO(xml_bytes)
    buf.name = xml_nome
    try:
        path = storage.save_file(
            buf, folder=S3_FOLDER_XML, filename=xml_nome
        )
        if path:
            logger.info("XML CTe Comp salvo em S3: %s", path)
        return path
    except Exception as e:
        logger.warning("Falha upload XML CTe Comp: %s", e)
        return None


def upload_dacte_s3(dacte_bytes: bytes, dacte_nome: str) -> Optional[str]:
    """Upload DACTE PDF para folder padronizado e retorna path S3."""
    from app.utils.file_storage import get_file_storage

    storage = get_file_storage()
    buf = BytesIO(dacte_bytes)
    buf.name = dacte_nome
    try:
        path = storage.save_file(
            buf, folder=S3_FOLDER_DACTE, filename=dacte_nome
        )
        if path:
            logger.info("DACTE CTe Comp salvo em S3: %s", path)
        return path
    except Exception as e:
        logger.warning("Falha upload DACTE CTe Comp: %s", e)
        return None


# ────────────────────────────────────────────────────────────────────────────
# Auto-match Custo Entrega
# ────────────────────────────────────────────────────────────────────────────

def auto_match_custo_entrega(operacao_id: int) -> List:
    """Busca CarviaCustoEntrega candidatos para vincular um CTe Complementar.

    Critérios:
      - `operacao_id` == operacao_id da operação pai
      - `cte_complementar_id` IS NULL (ainda não vinculado)
      - `status` != 'PAGO' (custos pagos não podem ter vínculo alterado)

    Returns:
        Lista de CarviaCustoEntrega ordenados por `criado_em` DESC.
    """
    from app.carvia.models import CarviaCustoEntrega

    query = CarviaCustoEntrega.query.filter(
        CarviaCustoEntrega.operacao_id == operacao_id,
        CarviaCustoEntrega.cte_complementar_id.is_(None),
        CarviaCustoEntrega.status != 'PAGO',
    ).order_by(CarviaCustoEntrega.criado_em.desc())
    return query.all()


# ────────────────────────────────────────────────────────────────────────────
# Extração de ICMS do CTe pai
# ────────────────────────────────────────────────────────────────────────────

def extrair_icms_do_pai(operacao) -> Dict[str, Any]:
    """Extrai ICMS do CTe pai (operação).

    Tenta:
      1. `operacao.icms_aliquota` se preenchido
      2. Re-parseia XML da operação via `FileStorage.download_file`

    Side-effect: se conseguir extrair via XML, persiste em
    `operacao.icms_aliquota` (NÃO commita — caller é responsável).

    Returns:
        dict com chaves:
            aliquota_icms (float),
            valor_icms (Optional[float]),
            base_icms (Optional[float]),
            fonte ('campo_persistido' | 'xml_reparseado' | 'nao_encontrado' | 'erro'),
            erro (Optional[str], somente se fonte='erro')
    """
    if not operacao:
        return {'aliquota_icms': 0.0, 'fonte': 'nao_encontrado'}

    aliquota = float(operacao.icms_aliquota or 0)
    if aliquota > 0:
        return {
            'aliquota_icms': aliquota,
            'valor_icms': None,
            'fonte': 'campo_persistido',
        }

    if not operacao.cte_xml_path:
        return {'aliquota_icms': 0.0, 'fonte': 'nao_encontrado'}

    try:
        from app.utils.file_storage import get_file_storage
        from app.carvia.services.parsers.cte_xml_parser_carvia import (
            CTeXMLParserCarvia,
        )

        storage = get_file_storage()
        xml_bytes = storage.download_file(operacao.cte_xml_path)
        if not xml_bytes:
            return {'aliquota_icms': 0.0, 'fonte': 'xml_nao_baixou'}

        parser = CTeXMLParserCarvia(
            xml_bytes.decode('utf-8', errors='replace')
        )
        impostos = parser.get_impostos() or {}
        aliquota_xml = float(impostos.get('aliquota_icms') or 0)

        # Persistir para futuro (não commita aqui — caller controla)
        if aliquota_xml > 0:
            operacao.icms_aliquota = aliquota_xml

        return {
            'aliquota_icms': aliquota_xml,
            'valor_icms': impostos.get('valor_icms'),
            'base_icms': impostos.get('base_icms'),
            'fonte': 'xml_reparseado',
        }
    except Exception as e:
        logger.warning(
            "Falha ao extrair ICMS do XML pai op=%s: %s", operacao.id, e
        )
        return {
            'aliquota_icms': 0.0,
            'fonte': 'erro',
            'erro': str(e),
        }


# ────────────────────────────────────────────────────────────────────────────
# Criar CarviaEmissaoCteComplementar
# ────────────────────────────────────────────────────────────────────────────

def criar_ou_atualizar_emissao_complementar(
    cte_comp,
    custo_entrega,
    operacao_id: int,
    ctrc_pai: str,
    motivo_ssw: str,
    filial_ssw: str,
    valor_calculado: float,
    icms_aliquota_usada: Optional[float],
    resultado_json: Dict[str, Any],
    criado_por: str,
    status: str = 'SUCESSO',
):
    """Cria ou atualiza `CarviaEmissaoCteComplementar`.

    Idempotente: se já existe emissão para este `cte_comp`, atualiza os
    campos relevantes em vez de criar nova. O fluxo do worker SSW criou
    a emissão ANTES de enfileirar o job (na rota `gerar_cte_complementar`),
    então o helper precisa atualizar a existente. O fluxo de importação
    manual não tem emissão prévia, então o helper cria.

    O `resultado_json` DEVE conter ao menos:
      - sucesso: bool
      - ctrc_complementar: str
      - xml_s3_path: str
      - xml_nome_arquivo: str
      - dacte_s3_path: Optional[str]
      - dacte_nome_arquivo: Optional[str]
      - cte_chave_acesso, cte_numero, cte_data_emissao, cte_valor_parsed
      - icms_pai: dict {aliquota_icms, ...}
      - valor_outros: float (idêntico ao valor_calculado)
      - origem: 'IMPORTACAO_MANUAL' | 'WORKER_SSW'

    NÃO commita — caller é responsável.

    Returns:
        Instância de CarviaEmissaoCteComplementar (criada ou atualizada).
        None se `custo_entrega` é None (FK NOT NULL impede criação).
    """
    from app import db
    from app.carvia.models import CarviaEmissaoCteComplementar
    from app.utils.timezone import agora_utc_naive

    if not custo_entrega:
        logger.info(
            "Sem CarviaCustoEntrega vinculado — pulando criação de "
            "CarviaEmissaoCteComplementar para cte_comp=%s",
            cte_comp.id,
        )
        return None

    # Buscar emissão existente para esse cte_comp
    existente = (
        CarviaEmissaoCteComplementar.query
        .filter_by(cte_complementar_id=cte_comp.id)
        .order_by(CarviaEmissaoCteComplementar.criado_em.desc())
        .first()
    )

    if existente:
        # Atualiza campos relevantes (não toca em criado_por, criado_em, ctrc_pai original)
        existente.status = status
        existente.etapa = None
        existente.resultado_json = resultado_json
        existente.valor_calculado = valor_calculado
        if icms_aliquota_usada is not None:
            existente.icms_aliquota_usada = icms_aliquota_usada
        existente.atualizado_em = agora_utc_naive()
        db.session.flush()
        return existente

    emissao = CarviaEmissaoCteComplementar(
        custo_entrega_id=custo_entrega.id,
        cte_complementar_id=cte_comp.id,
        operacao_id=operacao_id,
        ctrc_pai=ctrc_pai or 'DESCONHECIDO',
        motivo_ssw=motivo_ssw,
        filial_ssw=filial_ssw,
        valor_calculado=valor_calculado,
        icms_aliquota_usada=icms_aliquota_usada,
        status=status,
        etapa=None,
        resultado_json=resultado_json,
        criado_por=criado_por,
    )
    db.session.add(emissao)
    db.session.flush()
    return emissao


# ────────────────────────────────────────────────────────────────────────────
# Persistência completa (orquestrador principal)
# ────────────────────────────────────────────────────────────────────────────

def persistir_cte_complementar_completo(
    cte_comp,
    xml_bytes: Optional[bytes] = None,
    xml_nome: Optional[str] = None,
    dacte_bytes: Optional[bytes] = None,
    dacte_nome: Optional[str] = None,
    custo_entrega=None,
    motivo_ssw: str = 'C',
    filial_ssw: str = 'CAR',
    icms_pai: Optional[Dict[str, Any]] = None,
    valor_calculado: Optional[float] = None,
    criado_por: str = 'manual',
    origem: str = 'IMPORTACAO_MANUAL',
) -> Dict[str, Any]:
    """Persistência completa de CTe Complementar — usado por worker e importação.

    Operações:
      1. Parseia XML e atualiza campos do `cte_comp` (chave, número, data, valor)
      2. Detecta status `EMITIDO` via `<protCTe>/cStat=100`
      3. Upload XML para `S3_FOLDER_XML`
      4. Upload DACTE para `S3_FOLDER_DACTE` (se fornecido)
      5. Extrai ICMS do CTe pai (se `icms_pai` não fornecido)
      6. Vincula `custo_entrega.cte_complementar_id` (se `custo_entrega` fornecido)
      7. Cria `CarviaEmissaoCteComplementar` (se houver `custo_entrega`)

    NÃO commita.

    Args:
        cte_comp: `CarviaCteComplementar` (já adicionado à sessão)
        xml_bytes: bytes do XML (obrigatório para preenchimento de metadados)
        xml_nome: nome do arquivo XML (default: `'{chave}-cte.xml'`)
        dacte_bytes: bytes do PDF do DACTE (opcional)
        dacte_nome: nome do arquivo DACTE (default: `'{ctrc_numero}-dacte.pdf'`)
        custo_entrega: `CarviaCustoEntrega` para vincular (opcional)
        motivo_ssw: código SSW (C/D/E/R) — usado em `CarviaEmissaoCteComplementar`
        filial_ssw: filial SSW (default `'CAR'`)
        icms_pai: dict `{aliquota_icms, valor_icms, ...}` (opcional)
        valor_calculado: valor real do CTe Complementar (default = `cte_comp.cte_valor`)
        criado_por: email/identificador do usuário
        origem: `'IMPORTACAO_MANUAL'` | `'WORKER_SSW'` (rastreio)

    Returns:
        dict (também usado como `resultado_json` da emissão) com chaves:
            sucesso, status, origem, cte_comp_id, emissao_id,
            xml_s3_path, xml_nome_arquivo,
            dacte_s3_path, dacte_nome_arquivo,
            cte_chave_acesso, cte_numero, cte_data_emissao, cte_valor_parsed,
            ctrc_complementar, protocolo_autorizado, protocolo_codigo_status,
            icms_pai, valor_outros,
            custo_entrega_id, custo_entrega_numero,
            erros (lista)
    """
    from app import db
    from app.carvia.models import CarviaOperacao

    extras: Dict[str, Any] = {
        'origem': origem,
        'sucesso': True,
    }
    erros: List[str] = []

    # ── 1. Parsear XML e atualizar cte_comp ──
    parsed = None
    if xml_bytes:
        try:
            parsed = parsear_xml_complementar(xml_bytes)

            chave = parsed.get('cte_chave_acesso')
            numero_cte = parsed.get('cte_numero')
            data_emi_str = parsed.get('cte_data_emissao')
            valor_prest = parsed.get('cte_valor')
            ctrc_xml = parsed.get('ctrc_numero')
            protocolo = parsed.get('protocolo_autorizacao') or {}

            # Preenche apenas campos vazios — preserva valores já populados
            # (worker pode ter populado ctrc_numero antes via SSW captura).
            if chave and not cte_comp.cte_chave_acesso:
                cte_comp.cte_chave_acesso = chave
            if numero_cte and not cte_comp.cte_numero:
                cte_comp.cte_numero = numero_cte
            if ctrc_xml and not cte_comp.ctrc_numero:
                cte_comp.ctrc_numero = ctrc_xml
            if valor_prest is not None:
                try:
                    cte_comp.cte_valor = float(valor_prest)
                except (TypeError, ValueError):
                    pass
            if data_emi_str:
                parsed_date = parsear_data_emissao(data_emi_str)
                if parsed_date:
                    cte_comp.cte_data_emissao = parsed_date

            # Detectar status EMITIDO via protocolo SEFAZ (cStat=100 = autorizado)
            cstat = (protocolo.get('codigo_status') or '').strip()
            protocolo_autorizado = cstat == '100'
            if protocolo_autorizado and cte_comp.status == 'RASCUNHO':
                cte_comp.status = 'EMITIDO'

            # Convert data para string ISO no resultado_json (JSON-serializable)
            data_emi_iso = None
            if data_emi_str is not None:
                if isinstance(data_emi_str, (date, datetime)):
                    data_emi_iso = data_emi_str.isoformat()
                else:
                    data_emi_iso = str(data_emi_str)

            extras.update({
                'cte_chave_acesso': chave,
                'cte_numero': numero_cte,
                'cte_data_emissao': data_emi_iso,
                'cte_valor_parsed': (
                    float(valor_prest) if valor_prest is not None else None
                ),
                'ctrc_complementar': cte_comp.ctrc_numero,
                'protocolo_autorizado': protocolo_autorizado,
                'protocolo_codigo_status': cstat or None,
                'protocolo_numero': protocolo.get('numero'),
            })
        except Exception as e:
            logger.warning("Falha ao parsear XML CTe Comp: %s", e)
            extras['xml_parse_erro'] = str(e)
            erros.append(f"Parse XML: {e}")

    # ── 2. Upload XML para S3 ──
    if xml_bytes:
        if not xml_nome:
            chave_arq = (
                extras.get('cte_chave_acesso') or cte_comp.cte_chave_acesso
            )
            xml_nome = (
                f"{chave_arq}-cte.xml"
                if chave_arq
                else f"{cte_comp.numero_comp}-cte.xml"
            )
        xml_s3_path = upload_xml_s3(xml_bytes, xml_nome)
        if xml_s3_path:
            cte_comp.cte_xml_path = xml_s3_path
            cte_comp.cte_xml_nome_arquivo = xml_nome
            extras['xml_s3_path'] = xml_s3_path
            extras['xml_nome_arquivo'] = xml_nome
        else:
            erros.append("Upload XML S3 falhou")

    # ── 3. Upload DACTE para S3 ──
    if dacte_bytes:
        if not dacte_nome:
            # Prioriza cte_numero (numero do CT-e SEFAZ) sobre ctrc_numero
            # (CTRC interno do SSW) para o nome do arquivo de download.
            base = (
                cte_comp.cte_numero
                or cte_comp.ctrc_numero
                or cte_comp.numero_comp
            )
            dacte_nome = f"{base}-dacte.pdf"
        dacte_s3_path = upload_dacte_s3(dacte_bytes, dacte_nome)
        if dacte_s3_path:
            extras['dacte_s3_path'] = dacte_s3_path
            extras['dacte_nome_arquivo'] = dacte_nome
        else:
            erros.append("Upload DACTE S3 falhou")

    # ── 4. ICMS do pai (se não veio do worker SSW) ──
    if icms_pai is None and cte_comp.operacao_id:
        try:
            op = db.session.get(CarviaOperacao, cte_comp.operacao_id)
            if op:
                icms_pai = extrair_icms_do_pai(op)
        except Exception as e:
            logger.warning("Falha ao extrair ICMS do pai: %s", e)
            icms_pai = {'aliquota_icms': 0.0, 'fonte': 'erro', 'erro': str(e)}

    if icms_pai:
        extras['icms_pai'] = icms_pai

    # ── 5. Vincular CarviaCustoEntrega ──
    if custo_entrega:
        custo_entrega.cte_complementar_id = cte_comp.id
        extras['custo_entrega_id'] = custo_entrega.id
        extras['custo_entrega_numero'] = custo_entrega.numero_custo

    # ── 6. Criar CarviaEmissaoCteComplementar ──
    valor_calc_final = valor_calculado
    if valor_calc_final is None:
        try:
            valor_calc_final = float(cte_comp.cte_valor or 0)
        except (TypeError, ValueError):
            valor_calc_final = 0.0
    extras['valor_outros'] = valor_calc_final

    # Determinar ctrc_pai (operação pai) para a emissão
    ctrc_pai_final = None
    try:
        op = db.session.get(CarviaOperacao, cte_comp.operacao_id)
        if op and op.ctrc_numero:
            ctrc_pai_final = op.ctrc_numero
    except Exception:
        pass

    emissao = None
    if custo_entrega:
        try:
            emissao = criar_ou_atualizar_emissao_complementar(
                cte_comp=cte_comp,
                custo_entrega=custo_entrega,
                operacao_id=cte_comp.operacao_id,
                ctrc_pai=ctrc_pai_final or 'DESCONHECIDO',
                motivo_ssw=motivo_ssw or 'C',
                filial_ssw=filial_ssw or 'CAR',
                valor_calculado=valor_calc_final,
                icms_aliquota_usada=(
                    icms_pai.get('aliquota_icms') if icms_pai else None
                ),
                resultado_json=extras,
                criado_por=criado_por,
                status='SUCESSO',
            )
            extras['emissao_id'] = emissao.id if emissao else None
        except Exception as e:
            logger.exception(
                "Falha ao criar/atualizar CarviaEmissaoCteComplementar "
                "para cte_comp=%s",
                cte_comp.id,
            )
            extras['emissao_erro'] = str(e)
            erros.append(f"CarviaEmissaoCteComplementar: {e}")
    else:
        extras['emissao_id'] = None
        extras['aviso'] = (
            'Sem Custo Entrega vinculado — CarviaEmissaoCteComplementar '
            'não foi criada (FK NOT NULL).'
        )

    extras['erros'] = erros
    extras['cte_comp_id'] = cte_comp.id
    if erros:
        extras['status'] = 'PARCIAL'
        extras['sucesso'] = False
    else:
        extras['status'] = 'SUCESSO'

    return extras


# ────────────────────────────────────────────────────────────────────────────
# Resolução de CTRC via SSW (consulta opção 101)
# ────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..', '..')
)
SSW_SCRIPTS = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'operando-ssw', 'scripts'
)


def resolver_ctrc_ssw(
    ctrc_atual: str, filial: str = 'CAR'
) -> Optional[str]:
    """Verifica se o CTRC armazenado bate com o real no SSW (opção 101).

    O número `nCT` do XML pode divergir do CTRC real do SSW em casos raros
    onde o usuário operou opcao 222 manualmente. Esta função consulta a
    opção 101 pelo número e retorna o CTRC corrigido.

    Args:
        ctrc_atual: CTRC armazenado (ex: `'CAR-110-9'`)
        filial: Filial SSW (default `'CAR'`)

    Returns:
        CTRC corrigido (ex: `'CAR-113-9'`) se divergir, ou None se não
        precisar corrigir / falhar na consulta.
    """
    m = re.match(r'^[A-Z]+-(\d+)', ctrc_atual or '')
    if not m:
        return None

    ctrc_num = m.group(1)

    try:
        if SSW_SCRIPTS not in sys.path:
            sys.path.insert(0, SSW_SCRIPTS)

        from consultar_ctrc_101 import consultar_ctrc  # type: ignore
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
            logger.warning(
                "Não conseguiu consultar CTRC %s no SSW", ctrc_num
            )
            return None

        dados = resultado.get('dados', {}) or {}
        ctrc_completo = dados.get('ctrc_completo')  # Ex: CAR000113-9

        if ctrc_completo:
            # Formatar: CAR000113-9 → CAR-113-9
            m2 = re.match(
                r'^([A-Z]{2,4})0*(\d+)-(\d)$', ctrc_completo
            )
            if m2:
                return f'{m2.group(1)}-{m2.group(2)}-{m2.group(3)}'

        return None
    except Exception as e:
        logger.warning("Erro ao resolver CTRC via SSW: %s", e)
        return None
