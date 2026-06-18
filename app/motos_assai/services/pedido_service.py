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
from typing import Optional, Dict
from datetime import datetime

import pdfplumber

from app import db
from app.utils.file_storage import FileStorage
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiPedidoVendaItem,
    AssaiLoja, AssaiModelo,
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
        lojas_cache: Dict[str, Optional[AssaiLoja]] = {}
        modelos_cache: Dict[str, Optional[AssaiModelo]] = {}
        # Cache de cabecalhos AssaiPedidoVendaLoja por loja_id (Plano 5 — Migration 10):
        # cada item DEVE apontar para um cabecalho via FK pedido_loja_id.
        pedido_loja_cache: Dict[int, AssaiPedidoVendaLoja] = {}

        items_persistidos = 0
        items_pulados = []

        for item in items:
            numero_loja = item.get('numero_loja')
            codigo_qpa = item.get('codigo_qpa')
            if not numero_loja or not codigo_qpa:
                items_pulados.append(_resumo_pulado(item, 'numero_loja ou codigo_qpa ausente'))
                continue

            # Resolver loja — match TOLERANTE a zero-padding (IMP-2026-06-18-001).
            # O PDF Consinco traz "LJ14"/"LJ61" e o extractor extrai "14"/"61"; o
            # cadastro assai_loja e inconsistente ("12" sem zero, "014" com zero).
            # O match exato anterior perdia em SILENCIO toda loja com formatacao
            # divergente. _resolver_loja tenta exato e variantes normalizadas.
            if numero_loja not in lojas_cache:
                lojas_cache[numero_loja] = _resolver_loja(numero_loja)
            loja = lojas_cache[numero_loja]
            if not loja:
                items_pulados.append(_resumo_pulado(item, f'loja {numero_loja} não cadastrada'))
                continue

            # Resolver modelo
            if codigo_qpa not in modelos_cache:
                modelos_cache[codigo_qpa] = resolver_por_codigo_qpa(codigo_qpa)
            modelo = modelos_cache[codigo_qpa]
            if not modelo:
                items_pulados.append(
                    _resumo_pulado(item, f'modelo codigo_qpa={codigo_qpa} não cadastrado')
                )
                continue

            # Verifica se já existe (evita duplicata em pages re-processed)
            existente = AssaiPedidoVendaItem.query.filter_by(
                pedido_id=pedido.id, loja_id=loja.id, modelo_id=modelo.id,
            ).first()
            if existente:
                existente.qtd_pedida += int(item['qtd'])
                existente.valor_total = (existente.valor_total or Decimal('0')) + Decimal(str(item['valor_total']))
                continue

            # Garantir cabecalho AssaiPedidoVendaLoja para esta loja (Plano 5).
            # Criado on-demand no primeiro item da loja; reutilizado pelos demais
            # via cache. INSERT ... ON CONFLICT teria sido mais seguro mas como
            # estamos dentro de uma transacao unica (commit no final), basta cache.
            if loja.id not in pedido_loja_cache:
                pvl = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
                db.session.add(pvl)
                db.session.flush()  # garante pvl.id
                pedido_loja_cache[loja.id] = pvl
            pedido_loja = pedido_loja_cache[loja.id]

            db.session.add(AssaiPedidoVendaItem(
                pedido_id=pedido.id,
                pedido_loja_id=pedido_loja.id,
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

        # Confiança HONESTA (IMP-2026-06-18-001, camada 2): reflete o que foi
        # efetivamente PERSISTIDO, não o que o extractor leu. A heurística antiga
        # media lojas_extraidas/paginas ANTES da persistência e gravava 1.00 mesmo
        # perdendo lojas no match de loja/modelo (silent data loss). Agora:
        #   confiança = lojas_gravadas / lojas_no_documento  (∈ [0, 1])
        lojas_no_doc = len({i.get('numero_loja') for i in items if i.get('numero_loja')})
        lojas_gravadas = len(pedido_loja_cache)
        if lojas_no_doc:
            confianca = round(lojas_gravadas / lojas_no_doc, 2)
        pedido.parsing_confianca = Decimal(str(confianca))
        pedido.import_resumo = {
            'lojas_extraidas': lojas_no_doc,
            'lojas_gravadas': lojas_gravadas,
            'itens_extraidos': len(items),
            'itens_gravados': items_persistidos,
            'pulados': items_pulados,
        }

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


def _variantes_numero_loja(numero_loja: str) -> set:
    """Conjunto de formas equivalentes de um número de loja (zero-padding).

    "14"  -> {"14", "014"}      "061" -> {"061", "61"}      "174" -> {"174"}
    Tolera o cadastro inconsistente de assai_loja (algumas "12", outras "014").
    """
    n = str(numero_loja).strip()
    sem_zero = n.lstrip('0') or '0'
    return {n, sem_zero, sem_zero.zfill(2), sem_zero.zfill(3)}


def _resolver_loja(numero_loja: str) -> Optional[AssaiLoja]:
    """Resolve AssaiLoja por número, tolerante a zero-padding divergente.

    Causa-raiz de IMP-2026-06-18-001: o PDF traz "LJ14" (extrai "14") mas o
    cadastro grava "014"; o match exato perdia a loja em silêncio. Estratégia:
    1. Match exato (caminho feliz, sem ambiguidade).
    2. Fallback por variantes normalizadas. Só resolve se houver UM candidato
       (>1 = ambiguidade real no cadastro → não adivinha, devolve None).
    """
    n = str(numero_loja).strip()
    loja = AssaiLoja.query.filter_by(numero=n).first()
    if loja:
        return loja

    variantes = _variantes_numero_loja(n)
    variantes.discard(n)
    if not variantes:
        return None
    candidatos = AssaiLoja.query.filter(AssaiLoja.numero.in_(variantes)).all()
    if len(candidatos) == 1:
        logger.warning(
            "Loja '%s' resolvida por normalização de zero-padding -> '%s' "
            "(cadastro assai_loja inconsistente — padronizar).",
            n, candidatos[0].numero,
        )
        return candidatos[0]
    if len(candidatos) > 1:
        logger.error(
            "Loja '%s' ambígua na normalização: %d candidatos %s. Não resolvida.",
            n, len(candidatos), [c.numero for c in candidatos],
        )
    return None


def _resumo_pulado(item: dict, motivo: str) -> dict:
    """Versão compacta e JSON-serializável de um item pulado (p/ import_resumo)."""
    return {
        'numero_loja': item.get('numero_loja'),
        'codigo_qpa': item.get('codigo_qpa'),
        'descricao': item.get('descricao'),
        'qtd': item.get('qtd'),
        'motivo': motivo,
    }


# =====================================================================
# Edição manual de pedido (IMP-2026-06-18-003 / -004)
# Fallback quando o parser perde lojas/itens ou o PDF não está disponível.
# Só permitido em pedido ABERTO. Status muda apenas com NF Q.P.A. (não aqui).
# =====================================================================

class PedidoVoeEdicaoError(Exception):
    """Edição manual inválida (status != ABERTO, separação ativa, dados inválidos)."""


def _assert_pedido_editavel(pedido: AssaiPedidoVenda) -> None:
    if pedido.status != PEDIDO_STATUS_ABERTO:
        raise PedidoVoeEdicaoError(
            f"Pedido {pedido.numero} está {pedido.status}; edição manual só é "
            "permitida em ABERTO."
        )


def _assert_sem_separacao_ativa(pedido_id: int, loja_id: int) -> None:
    """Bloqueia remoção quando há separação não-cancelada para (pedido, loja)."""
    from app.motos_assai.models import AssaiSeparacao, SEPARACAO_STATUS_CANCELADA
    sep = AssaiSeparacao.query.filter(
        AssaiSeparacao.pedido_id == pedido_id,
        AssaiSeparacao.loja_id == loja_id,
        AssaiSeparacao.status != SEPARACAO_STATUS_CANCELADA,
    ).first()
    if sep:
        raise PedidoVoeEdicaoError(
            f"Loja {loja_id} tem separação ativa (id={sep.id}); cancele a "
            "separação antes de remover itens dessa loja."
        )


def _marcar_editado_manual(pedido: AssaiPedidoVenda, operador_id: Optional[int]) -> None:
    """Registra no import_resumo que o pedido sofreu edição manual (auditoria).

    Reatribui o dict para o SQLAlchemy detectar a mudança (coluna JSON sem
    MutableDict não rastreia mutação in-place).
    """
    resumo = dict(pedido.import_resumo or {})
    resumo['editado_manual'] = True
    resumo['ultimo_editor_id'] = operador_id
    pedido.import_resumo = resumo


def _validar_qtd_valor(qtd, valor_unitario):
    qtd = int(qtd)
    if qtd <= 0:
        raise PedidoVoeEdicaoError("qtd deve ser > 0.")
    valor_unitario = Decimal(str(valor_unitario))
    if valor_unitario <= 0:
        raise PedidoVoeEdicaoError("valor_unitário deve ser > 0.")
    return qtd, valor_unitario


def adicionar_item_manual(
    pedido_id: int, loja_id: int, modelo_id: int,
    qtd, valor_unitario, operador_id: Optional[int] = None,
) -> AssaiPedidoVendaItem:
    """Adiciona (ou soma a) um item (loja × modelo) num pedido ABERTO.

    Cria o cabeçalho AssaiPedidoVendaLoja on-demand. Se o item já existe para
    (loja, modelo), SOMA a qtd e o valor_total (mesma semântica do importador).
    """
    pedido = AssaiPedidoVenda.query.get_or_404(pedido_id)
    _assert_pedido_editavel(pedido)
    qtd, valor_unitario = _validar_qtd_valor(qtd, valor_unitario)

    loja = AssaiLoja.query.get(loja_id)
    if not loja:
        raise PedidoVoeEdicaoError(f"Loja id={loja_id} não encontrada.")
    modelo = AssaiModelo.query.get(modelo_id)
    if not modelo:
        raise PedidoVoeEdicaoError(f"Modelo id={modelo_id} não encontrado.")

    pvl = AssaiPedidoVendaLoja.query.filter_by(
        pedido_id=pedido_id, loja_id=loja_id,
    ).first()
    if not pvl:
        pvl = AssaiPedidoVendaLoja(pedido_id=pedido_id, loja_id=loja_id)
        db.session.add(pvl)
        db.session.flush()

    item = AssaiPedidoVendaItem.query.filter_by(
        pedido_id=pedido_id, loja_id=loja_id, modelo_id=modelo_id,
    ).first()
    if item:
        item.qtd_pedida += qtd
        item.valor_total = (item.valor_total or Decimal('0')) + (valor_unitario * qtd)
    else:
        item = AssaiPedidoVendaItem(
            pedido_id=pedido_id, pedido_loja_id=pvl.id,
            loja_id=loja_id, modelo_id=modelo_id,
            qtd_pedida=qtd, valor_unitario=valor_unitario,
            valor_total=valor_unitario * qtd,
        )
        db.session.add(item)

    _marcar_editado_manual(pedido, operador_id)
    db.session.commit()
    logger.info(
        "Item manual %s pedido=%s loja=%s modelo=%s qtd=%s por user=%s",
        'somado' if item else 'criado', pedido_id, loja_id, modelo_id, qtd, operador_id,
    )
    return item


def editar_item_manual(
    item_id: int, qtd, valor_unitario, operador_id: Optional[int] = None,
) -> AssaiPedidoVendaItem:
    """Edita qtd e valor_unitário de um item de pedido ABERTO (substitui, não soma)."""
    item = AssaiPedidoVendaItem.query.get_or_404(item_id)
    pedido = AssaiPedidoVenda.query.get(item.pedido_id)
    _assert_pedido_editavel(pedido)
    qtd, valor_unitario = _validar_qtd_valor(qtd, valor_unitario)

    item.qtd_pedida = qtd
    item.valor_unitario = valor_unitario
    item.valor_total = valor_unitario * qtd
    _marcar_editado_manual(pedido, operador_id)
    db.session.commit()
    return item


def remover_item_manual(item_id: int, operador_id: Optional[int] = None) -> None:
    """Remove um item de pedido ABERTO. Remove o cabeçalho da loja se ficar órfão.

    Bloqueia se a loja tiver separação ativa (evita inconsistência com chassis
    já separados).
    """
    item = AssaiPedidoVendaItem.query.get_or_404(item_id)
    pedido = AssaiPedidoVenda.query.get(item.pedido_id)
    _assert_pedido_editavel(pedido)
    _assert_sem_separacao_ativa(item.pedido_id, item.loja_id)

    pedido_id, loja_id = item.pedido_id, item.loja_id
    db.session.delete(item)
    db.session.flush()

    restantes = AssaiPedidoVendaItem.query.filter_by(
        pedido_id=pedido_id, loja_id=loja_id,
    ).count()
    if restantes == 0:
        pvl = AssaiPedidoVendaLoja.query.filter_by(
            pedido_id=pedido_id, loja_id=loja_id,
        ).first()
        if pvl:
            db.session.delete(pvl)

    _marcar_editado_manual(pedido, operador_id)
    db.session.commit()
