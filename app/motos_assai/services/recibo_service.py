"""Orquestração de importação do recibo Motochefe.

Aceita PDF e Excel. Estratégia:
1. Detecta tipo (mime/extensão)
2. Roda extractor determinístico apropriado
3. Calcula confiança = (chassis_extraidos / total_motos_declarado_no_header)
4. Se confiança < 0.80 ou zero chassis: aciona LLM fallback
5. Salva arquivo em S3 (SOMENTE após parsing OK — lição C2)
6. Persiste AssaiReciboMotochefe + N AssaiReciboItem
7. Resolve modelo_id via modelo_resolver para cada item
"""

from __future__ import annotations

import io
import logging
import tempfile
from decimal import Decimal
from typing import Optional

from app import db
from app.utils.file_storage import FileStorage
from app.motos_assai.models import (
    AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
    RECIBO_STATUS_AGUARDANDO,
)
from app.motos_assai.services.parsers.motochefe_recibo_pdf_extractor import (
    MotochefeReciboPdfExtractor,
)
from app.motos_assai.services.parsers.motochefe_recibo_xlsx_extractor import (
    MotochefeReciboXlsxExtractor,
)
from app.motos_assai.services.parsers.motochefe_recibo_llm_fallback import (
    parse_pdf_via_llm, parse_xlsx_via_llm, MotochefeReciboLlmFallbackError,
)
from app.motos_assai.services.modelo_resolver import resolver_modelo

logger = logging.getLogger(__name__)

CONFIANCA_LIMIAR = 0.80


class ReciboParserError(Exception):
    pass


def importar(
    compra_id: int,
    file_bytes: bytes,
    nome_arquivo: str,
    mime_type: Optional[str],
    importado_por_id: int,
) -> AssaiReciboMotochefe:
    """Importa recibo Motochefe (PDF ou XLSX).

    Fluxo:
    1. Valida compra existe
    2. Detecta tipo de arquivo
    3. Roda parser determinístico
    4. Calcula confiança; aciona LLM se baixa
    5. Upload S3 APENAS APÓS parsing validado (lição C2)
    6. Persiste header + itens em transação com rollback

    Raises:
        ReciboParserError: se zero chassis extraídos ou tipo não suportado.
    """
    AssaiCompraMotochefe.query.get_or_404(compra_id)

    tipo_doc = _detectar_tipo(nome_arquivo, mime_type)

    # 1. Determinístico — S3 upload SÓ DEPOIS de parsing OK (lição C2)
    items = []
    parser_usado = 'DETERMINISTICO'
    confianca = 0.0

    if tipo_doc == 'PDF':
        extractor = MotochefeReciboPdfExtractor()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            items = extractor.extract(tmp)
        finally:
            import os
            os.unlink(tmp)
    else:
        extractor = MotochefeReciboXlsxExtractor()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            items = extractor.extract(tmp)
        finally:
            import os
            os.unlink(tmp)

    confianca = _calcular_confianca(items)

    # 2. Fallback LLM
    if not items or confianca < CONFIANCA_LIMIAR:
        logger.warning(f'Confiança {confianca:.2f} ou zero items. Acionando LLM.')
        try:
            llm_result = (
                parse_pdf_via_llm(file_bytes) if tipo_doc == 'PDF'
                else parse_xlsx_via_llm(file_bytes)
            )
            items = llm_result['items']
            parser_usado = llm_result['parser_usado']
            confianca = 1.0
        except MotochefeReciboLlmFallbackError as e:
            if not items:
                raise ReciboParserError(f'Determinístico zero + LLM falhou: {e}')
            logger.error(f'LLM falhou; usando determinístico com baixa confiança: {e}')

    if not items:
        raise ReciboParserError('Zero chassis extraídos')

    # 3. Parsing OK → upload S3 (lição C2: nunca antes de validar)
    ext = 'pdf' if tipo_doc == 'PDF' else 'xlsx'
    buf = io.BytesIO(file_bytes)
    buf.name = nome_arquivo
    s3_key = FileStorage().save_file(
        buf, folder=f'motos_assai/recibos/{compra_id}',
        filename=nome_arquivo,
        allowed_extensions=[ext],
    )

    # 4. Persistir — try/except com rollback (lição H3)
    try:
        header = items[0]
        recibo = AssaiReciboMotochefe(
            compra_id=compra_id,
            numero_recibo=None,
            data_recibo=_parse_data(header.get('data_recibo')),
            equipe=header.get('equipe'),
            conferente_motochefe=header.get('conferente'),
            total_motos_declarado=header.get('total_motos_declarado'),
            doc_s3_key=s3_key,
            tipo_documento=tipo_doc,
            parser_usado=parser_usado,
            parsing_confianca=Decimal(str(round(confianca, 2))),
            status=RECIBO_STATUS_AGUARDANDO,
            criado_por_id=importado_por_id,
        )
        db.session.add(recibo)
        db.session.flush()

        chassis_vistos = set()
        for it in items:
            chassi = it.get('chassi', '').strip().upper()
            if not chassi or chassi in chassis_vistos:
                continue
            chassis_vistos.add(chassi)

            modelo = resolver_modelo(it.get('modelo_texto', ''), origem='RECIBO_MOTOCHEFE')

            db.session.add(AssaiReciboItem(
                recibo_id=recibo.id,
                chassi=chassi,
                modelo_texto_recibo=it.get('modelo_texto'),
                modelo_id=modelo.id if modelo else None,
                cor_texto=it.get('cor'),
                motor=it.get('motor'),
                conferido=False,
            ))

        db.session.commit()

    except Exception:
        db.session.rollback()
        # Best-effort cleanup do S3 se persistência falhou
        if s3_key:
            try:
                FileStorage().delete_file(s3_key)
            except Exception as s3_err:
                logger.warning(f'Não foi possível remover arquivo órfão do S3 ({s3_key}): {s3_err}')
        raise

    return recibo


def _detectar_tipo(nome_arquivo: str, mime_type: Optional[str]) -> str:
    nome_lower = (nome_arquivo or '').lower()
    if nome_lower.endswith('.pdf') or (mime_type and 'pdf' in mime_type):
        return 'PDF'
    if nome_lower.endswith(('.xlsx', '.xls')) or (mime_type and 'sheet' in (mime_type or '')):
        return 'EXCEL'
    raise ReciboParserError(f'Tipo de arquivo não suportado: {nome_arquivo}')


def _calcular_confianca(items: list) -> float:
    if not items:
        return 0.0
    total_declarado = items[0].get('total_motos_declarado')
    if not total_declarado:
        # Sem total declarado → confiança média se tem chassis
        return 0.85
    extraidos = len({i['chassi'] for i in items if i.get('chassi')})
    if total_declarado <= 0:
        return 0.0
    return min(1.0, extraidos / total_declarado)


def _parse_data(s: Optional[str]):
    from datetime import datetime
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], '%d/%m/%Y').date()
    except (ValueError, AttributeError):
        return None


def get_recibo(recibo_id: int) -> AssaiReciboMotochefe:
    return AssaiReciboMotochefe.query.get_or_404(recibo_id)


def listar_recibos(compra_id: Optional[int] = None):
    q = AssaiReciboMotochefe.query
    if compra_id:
        q = q.filter_by(compra_id=compra_id)
    return q.order_by(AssaiReciboMotochefe.criado_em.desc()).all()
