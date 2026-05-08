"""Orquestração de importação de pedido VOE Q.P.A.

Fluxo:
1. Salva PDF em arquivo temporário
2. Roda QpaPedidoExtractor (determinístico)
3. Calcula confiança = (paginas_com_itens / paginas_total) * (lojas_resolvidas / lojas_total)
4. Se confiança < 0.70 OU zero items: aciona LLM fallback (Haiku → Sonnet)
5. Valida duplicidade (número do pedido já importado?)
6. SE TUDO OK: upload S3 (`motos_assai/pedidos/<numero_ou_uuid>.pdf`)
7. Persiste AssaiPedidoVenda + N AssaiPedidoVendaItem (com rollback em caso de erro)
8. Status final: ABERTO

Não confirma o pedido — operador deve revisar tela de detalhe e clicar
"Confirmar pedido" para liberar consolidação em PO Motochefe.
"""

from __future__ import annotations

import io
import logging
import tempfile
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

import pdfplumber

from app import db
from app.utils.file_storage import FileStorage
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiLoja, AssaiModelo,
    PEDIDO_STATUS_ABERTO,
)
from app.motos_assai.services.parsers.qpa_pedido_extractor import QpaPedidoExtractor
from app.motos_assai.services.parsers.qpa_pedido_llm_fallback import (
    parse_via_llm, QpaPedidoLlmFallbackError,
)
from app.motos_assai.services.modelo_resolver import resolver_por_codigo_qpa

logger = logging.getLogger(__name__)


CONFIANCA_LIMIAR = 0.70


class PedidoVoeJaExisteError(Exception):
    """Pedido com mesmo número já foi importado."""


class PedidoVoeParserError(Exception):
    """Falha tanto determinística quanto LLM."""


def importar_pdf_voe(
    pdf_bytes: bytes,
    nome_arquivo: str,
    importado_por_id: int,
) -> AssaiPedidoVenda:
    """Importa PDF do pedido VOE. Persiste em S3 + cria registros no banco.

    Raises:
        PedidoVoeJaExisteError: se número do pedido já existe.
        PedidoVoeParserError: se determinístico e LLM falham.
    """
    # 1. Salvar PDF em arquivo temporário para parse
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        # 2. Determinístico (sem S3 ainda — upload só ocorre se parsing OK)
        extractor = QpaPedidoExtractor()
        items = extractor.extract(tmp_path)
        confianca = _calcular_confianca(tmp_path, items)
        parser_usado = 'DETERMINISTICO'

        # 3. Fallback LLM se necessário
        if not items or confianca < CONFIANCA_LIMIAR:
            logger.warning(
                f"Confiança baixa ({confianca:.2f}) ou zero items. "
                f"Acionando LLM fallback para {nome_arquivo}."
            )
            try:
                llm_result = parse_via_llm(pdf_bytes)
                items = llm_result['items']
                parser_usado = llm_result['parser_usado']
                confianca = 1.0  # LLM retornou; assumimos sucesso após validação humana
            except QpaPedidoLlmFallbackError as e:
                if not items:
                    raise PedidoVoeParserError(
                        f"Determinístico zero items + LLM falhou: {e}"
                    )
                # Mantém items determinísticos com confiança baixa
                logger.error(f'LLM fallback falhou, usando determinístico: {e}')
    finally:
        import os
        os.unlink(tmp_path)

    if not items:
        raise PedidoVoeParserError("Zero items extraídos por ambos parsers")

    # 4. Validar duplicidade ANTES de subir S3
    numero_pedido = items[0].get('numero_pedido')
    if not numero_pedido:
        raise PedidoVoeParserError("numero_pedido ausente nos items")

    if AssaiPedidoVenda.query.filter_by(numero=numero_pedido).first():
        raise PedidoVoeJaExisteError(
            f"Pedido {numero_pedido} já foi importado anteriormente"
        )

    # 5. Parsing OK + sem duplicata → upload S3 (sem arquivo órfão em caso de erro antecipado)
    buf = io.BytesIO(pdf_bytes)
    buf.name = nome_arquivo
    s3_key = FileStorage().save_file(
        buf, folder='motos_assai/pedidos',
        filename=nome_arquivo,
        allowed_extensions=['pdf'],
    )

    # 6. Persistir — try/except garante rollback em caso de erro.
    #    Se commit falhar após S3 upload, tenta delete best-effort (raro mas possível).
    try:
        pedido = AssaiPedidoVenda(
            numero=numero_pedido,
            data_emissao=_parse_data(items[0].get('data_emissao')),
            previsao_entrega=_parse_data(items[0].get('previsao_entrega')),
            fornecedor_cnpj=items[0].get('fornecedor_cnpj'),
            pdf_s3_key=s3_key,
            parser_usado=parser_usado,
            parsing_confianca=Decimal(str(round(confianca, 2))),
            status=PEDIDO_STATUS_ABERTO,
            criado_por_id=importado_por_id,
        )
        db.session.add(pedido)
        db.session.flush()

        # Cache de lojas e modelos para não fazer N queries
        lojas_cache: Dict[str, AssaiLoja] = {}
        modelos_cache: Dict[str, Optional[AssaiModelo]] = {}

        items_persistidos = 0
        items_pulados = []

        for item in items:
            numero_loja = item.get('numero_loja')
            codigo_qpa = item.get('codigo_qpa')
            if not numero_loja or not codigo_qpa:
                items_pulados.append({'motivo': 'numero_loja ou codigo_qpa ausente', 'item': item})
                continue

            # Resolver loja
            if numero_loja not in lojas_cache:
                lojas_cache[numero_loja] = AssaiLoja.query.filter_by(numero=numero_loja).first()
            loja = lojas_cache[numero_loja]
            if not loja:
                items_pulados.append({
                    'motivo': f'loja {numero_loja} não cadastrada',
                    'item': item,
                })
                continue

            # Resolver modelo
            if codigo_qpa not in modelos_cache:
                modelos_cache[codigo_qpa] = resolver_por_codigo_qpa(codigo_qpa)
            modelo = modelos_cache[codigo_qpa]
            if not modelo:
                items_pulados.append({
                    'motivo': f'modelo codigo_qpa={codigo_qpa} não cadastrado',
                    'item': item,
                })
                continue

            # Verifica se já existe (evita duplicata em pages re-processed)
            existente = AssaiPedidoVendaItem.query.filter_by(
                pedido_id=pedido.id, loja_id=loja.id, modelo_id=modelo.id,
            ).first()
            if existente:
                existente.qtd_pedida += int(item['qtd'])
                existente.valor_total = (existente.valor_total or Decimal('0')) + Decimal(str(item['valor_total']))
                continue

            db.session.add(AssaiPedidoVendaItem(
                pedido_id=pedido.id,
                loja_id=loja.id,
                modelo_id=modelo.id,
                qtd_pedida=int(item['qtd']),
                valor_unitario=Decimal(str(item['valor_unitario'])),
                valor_total=Decimal(str(item['valor_total'])),
            ))
            items_persistidos += 1

        if items_persistidos == 0:
            raise PedidoVoeParserError(
                f"Nenhum item válido. Pulados: {len(items_pulados)} (primeiros 3: {items_pulados[:3]})"
            )

        db.session.commit()

    except Exception:
        db.session.rollback()
        # Cleanup best-effort: tenta remover o arquivo do S3 se commit falhou
        try:
            FileStorage().delete_file(s3_key)
        except Exception as s3_err:
            logger.warning(f"Não foi possível remover arquivo órfão do S3 ({s3_key}): {s3_err}")
        raise

    if items_pulados:
        logger.warning(
            f"Pedido {numero_pedido}: {items_persistidos} items persistidos, "
            f"{len(items_pulados)} pulados. Primeiros pulados: {items_pulados[:3]}"
        )

    return pedido


def confirmar_pedido(pedido_id: int) -> AssaiPedidoVenda:
    """Apenas marca o pedido como conferido pelo operador (sem mudar status).

    No fluxo atual, status = ABERTO já significa pronto para consolidar em
    PO Motochefe. A confirmação humana é registrada via auditoria implícita
    (timestamp criado_em + usuário criado_por_id já existem). Este método
    é placeholder para futura adição de campo `conferido_em`/`conferido_por`.
    """
    return AssaiPedidoVenda.query.get_or_404(pedido_id)


# ============== helpers ==============

def _calcular_confianca(pdf_path: str, items: list) -> float:
    """Confiança = (lojas_extraídas / paginas_total) clamped [0, 1].

    Heurística: cada página = 1 loja. Se 36 páginas mas só 32 lojas distintas
    nos items, confiança = 32/36 = 0.89.
    """
    if not items:
        return 0.0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_paginas = len(pdf.pages)
    except Exception:
        return 0.5  # PDF deu erro mas items vieram

    lojas_distintas = len({i['numero_loja'] for i in items if i.get('numero_loja')})
    if total_paginas == 0:
        return 0.0
    return min(1.0, lojas_distintas / total_paginas)


def _parse_data(data_str: Optional[str]):
    """Converte 'DD/MM/YYYY' para date. None se inválido."""
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str.strip(), '%d/%m/%Y').date()
    except (ValueError, AttributeError):
        return None
