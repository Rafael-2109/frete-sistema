"""Orquestracao de importacao do recibo Motochefe + resolucao de duplicidade.

Aceita PDF e Excel. Estrategia:
1. Detecta tipo (mime/extensao)
2. Roda extractor deterministico apropriado
3. Calcula confianca = (chassis_extraidos / total_motos_declarado_no_header)
4. Se confianca < 0.80 ou zero chassis: aciona LLM fallback
5. Salva arquivo em S3 (SOMENTE apos parsing OK — licao C2)
6. Detecta chassis ja existentes em outros recibos ativos:
   - Sem duplicidade: persiste tudo ativo, status RECEBIDO_AGUARDANDO_CONFERENCIA.
   - Com duplicidade: persiste itens duplicados como `ativo=False`, status
     RESOLVENDO_DUPLICIDADE. Caller redireciona para tela de resolucao.
7. Resolve modelo_id via modelo_resolver para cada item.

Tambem expoe funcoes de resolucao (opcoes A/B/C), soft-delete de item e
exclusao de recibo inteiro.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from decimal import Decimal
from typing import Optional, Dict, Any, List

from app import db
from app.utils.file_storage import FileStorage
from app.motos_assai.models import (
    AssaiCompraMotochefe, AssaiReciboMotochefe, AssaiReciboItem,
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_RESOLVENDO_DUPLICIDADE,
    DIVERGENCIA_DESCARTADO_DUPLICIDADE,
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
from app.motos_assai.services.moto_evento_service import status_efetivo

logger = logging.getLogger(__name__)

CONFIANCA_LIMIAR = 0.80

# Quando o total de motos do recibo NAO foi extraido do header, nao ha como
# verificar se a extracao deterministica esta completa. Retornar confianca ABAIXO
# do limiar forca o fallback LLM (que le o documento inteiro). E mais seguro
# escalar do que persistir uma extracao possivelmente parcial — recibo incompleto
# = perda de moto no estoque. Incidente: recibo ID=16 importou 3 de 60 motos
# porque total ausente devolvia 0.85 (acima do limiar) e o LLM nunca disparava.
CONFIANCA_TOTAL_DESCONHECIDO = 0.50


class ReciboParserError(Exception):
    pass


class ReciboValidationError(Exception):
    """Operacao invalida sobre o recibo (estado incompativel, item conferido, etc)."""


# ---------------------------------------------------------------------------
# Importacao
# ---------------------------------------------------------------------------

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
    3. Roda parser deterministico
    4. Calcula confianca; aciona LLM se baixa
    5. Upload S3 APENAS APOS parsing validado (licao C2)
    6. Detecta duplicidade contra outros recibos ATIVOS
    7. Persiste header + itens em transacao com rollback
       - Itens duplicados: `ativo=False`
       - Status: RESOLVENDO_DUPLICIDADE quando ha duplicados, senao AGUARDANDO

    Raises:
        ReciboParserError: zero chassis extraidos ou tipo nao suportado.
    """
    AssaiCompraMotochefe.query.get_or_404(compra_id)

    tipo_doc = _detectar_tipo(nome_arquivo, mime_type)

    # 1. Deterministico
    items: List[Dict[str, Any]] = []
    parser_usado = 'DETERMINISTICO'

    if tipo_doc == 'PDF':
        extractor = MotochefeReciboPdfExtractor()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            items = extractor.extract(tmp)
        finally:
            os.unlink(tmp)
    else:
        extractor = MotochefeReciboXlsxExtractor()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            items = extractor.extract(tmp)
        finally:
            os.unlink(tmp)

    confianca = _calcular_confianca(items)

    # 2. Fallback LLM
    if not items or confianca < CONFIANCA_LIMIAR:
        logger.warning(f'Confianca {confianca:.2f} ou zero items. Acionando LLM.')
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
                raise ReciboParserError(f'Deterministico zero + LLM falhou: {e}')
            logger.error(f'LLM falhou; usando deterministico com baixa confianca: {e}')

    if not items:
        raise ReciboParserError('Zero chassis extraidos')

    # 3. Parsing OK -> upload S3 (licao C2: nunca antes de validar)
    ext = 'pdf' if tipo_doc == 'PDF' else 'xlsx'
    buf = io.BytesIO(file_bytes)
    buf.name = nome_arquivo
    s3_key = FileStorage().save_file(
        buf, folder=f'motos_assai/recibos/{compra_id}',
        filename=nome_arquivo,
        allowed_extensions=[ext],
    )

    # 4. Deteccao de duplicidade (contra outros recibos ativos)
    chassis_extraidos = []
    chassis_vistos = set()
    for it in items:
        c = (it.get('chassi') or '').strip().upper()
        if c and c not in chassis_vistos:
            chassis_extraidos.append(c)
            chassis_vistos.add(c)

    duplicados = set()
    if chassis_extraidos:
        rows = (
            db.session.query(AssaiReciboItem.chassi)
            .filter(AssaiReciboItem.chassi.in_(chassis_extraidos))
            .filter(AssaiReciboItem.ativo.is_(True))
            .all()
        )
        duplicados = {r[0] for r in rows}

    status_inicial = (
        RECIBO_STATUS_RESOLVENDO_DUPLICIDADE if duplicados
        else RECIBO_STATUS_AGUARDANDO
    )

    # 5. Persistir
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
            status=status_inicial,
            criado_por_id=importado_por_id,
        )
        db.session.add(recibo)
        db.session.flush()

        ja_inserido = set()
        for it in items:
            chassi = (it.get('chassi') or '').strip().upper()
            if not chassi or chassi in ja_inserido:
                continue
            ja_inserido.add(chassi)

            modelo = resolver_modelo(it.get('modelo_texto', ''), origem='RECIBO_MOTOCHEFE')

            db.session.add(AssaiReciboItem(
                recibo_id=recibo.id,
                chassi=chassi,
                modelo_texto_recibo=it.get('modelo_texto'),
                modelo_id=modelo.id if modelo else None,
                cor_texto=it.get('cor'),
                motor=it.get('motor'),
                conferido=False,
                ativo=(chassi not in duplicados),
            ))

        db.session.commit()

    except Exception:
        db.session.rollback()
        if s3_key:
            try:
                FileStorage().delete_file(s3_key)
            except Exception as s3_err:
                logger.warning(f'Nao foi possivel remover arquivo orfao do S3 ({s3_key}): {s3_err}')
        raise

    return recibo


def _detectar_tipo(nome_arquivo: str, mime_type: Optional[str]) -> str:
    nome_lower = (nome_arquivo or '').lower()
    if nome_lower.endswith('.pdf') or (mime_type and 'pdf' in mime_type):
        return 'PDF'
    if nome_lower.endswith(('.xlsx', '.xls')) or (mime_type and 'sheet' in (mime_type or '')):
        return 'EXCEL'
    raise ReciboParserError(f'Tipo de arquivo nao suportado: {nome_arquivo}')


def _calcular_confianca(items: list) -> float:
    if not items:
        return 0.0
    total_declarado = items[0].get('total_motos_declarado')
    if not total_declarado:
        # Total ausente => nao da para confirmar completude. Escala para LLM.
        return CONFIANCA_TOTAL_DESCONHECIDO
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


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

def get_recibo(recibo_id: int) -> AssaiReciboMotochefe:
    return AssaiReciboMotochefe.query.get_or_404(recibo_id)


def listar_recibos(
    compra_id: Optional[int] = None,
    chassi: Optional[str] = None,
    modelo_id: Optional[int] = None,
):
    """Lista recibos Motochefe.

    Filtros opcionais (2026-05-20):
    - chassi: recibos que contem um AssaiReciboItem com chassi ilike %chassi%.
    - modelo_id: recibos que contem um AssaiReciboItem do modelo informado.
    """
    q = AssaiReciboMotochefe.query
    if compra_id:
        q = q.filter_by(compra_id=compra_id)
    if chassi or modelo_id:
        sub = db.session.query(AssaiReciboItem.recibo_id)
        if chassi:
            sub = sub.filter(
                AssaiReciboItem.chassi.ilike(f'%{chassi.strip().upper()}%')
            )
        if modelo_id:
            sub = sub.filter(AssaiReciboItem.modelo_id == modelo_id)
        q = q.filter(AssaiReciboMotochefe.id.in_(sub))
    return q.order_by(AssaiReciboMotochefe.criado_em.desc()).all()


# ---------------------------------------------------------------------------
# Resolucao de duplicidade
# ---------------------------------------------------------------------------

def listar_duplicidades(recibo_id: int) -> List[Dict[str, Any]]:
    """Lista linhas em conflito entre o recibo novo e recibos antigos.

    Para cada item INATIVO do recibo novo (= duplicado na importacao),
    busca o item ativo correspondente em outros recibos e anota se a moto
    ja foi recebida (item antigo `conferido=True` ou status efetivo presente).

    Returns:
        Lista de dicts: {
            'novo_item': {...AssaiReciboItem...},
            'antigos': [{
                'item': {...},
                'recibo_id': int,
                'recibo_numero': str | None,
                'compra_id': int,
                'recibo_status': str,
                'pode_remover': bool,    # True se nao foi recebida
                'motivo_bloqueio': str | None,
                'status_efetivo_chassi': str | None,
            }, ...]
        }
    """
    from app.motos_assai.models import AssaiReciboMotochefe as Recibo

    novos_inativos = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, ativo=False)
        .order_by(AssaiReciboItem.id.asc())
        .all()
    )

    out = []
    for novo in novos_inativos:
        antigos_rows = (
            db.session.query(AssaiReciboItem, Recibo)
            .join(Recibo, Recibo.id == AssaiReciboItem.recibo_id)
            .filter(AssaiReciboItem.chassi == novo.chassi)
            .filter(AssaiReciboItem.ativo.is_(True))
            .filter(AssaiReciboItem.recibo_id != recibo_id)
            .all()
        )
        antigos = []
        for item_ant, rec_ant in antigos_rows:
            status_chassi = status_efetivo(item_ant.chassi)
            pode_remover = not item_ant.conferido
            motivo = None if pode_remover else 'moto_ja_recebida'
            antigos.append({
                'item': _serializa_item(item_ant),
                'recibo_id': rec_ant.id,
                'recibo_numero': rec_ant.numero_recibo,
                'compra_id': rec_ant.compra_id,
                'recibo_status': rec_ant.status,
                'pode_remover': pode_remover,
                'motivo_bloqueio': motivo,
                'status_efetivo_chassi': status_chassi,
            })
        out.append({
            'novo_item': _serializa_item(novo),
            'antigos': antigos,
        })
    return out


def _serializa_item(item: AssaiReciboItem) -> Dict[str, Any]:
    return {
        'id': item.id,
        'recibo_id': item.recibo_id,
        'chassi': item.chassi,
        'modelo_id': item.modelo_id,
        'modelo_texto_recibo': item.modelo_texto_recibo,
        'cor_texto': item.cor_texto,
        'motor': item.motor,
        'conferido': item.conferido,
        'tipo_divergencia': item.tipo_divergencia,
        'ativo': item.ativo,
    }


def recibos_antigos_passiveis_de_exclusao(recibo_id: int) -> List[AssaiReciboMotochefe]:
    """Lista recibos ANTIGOS que conflitam com o recibo novo e cujos itens
    duplicados nao foram recebidos (=> opcao B habilitada).

    Um recibo antigo so eh listado se TODOS os itens conflitantes podem ser
    removidos (todos `conferido=False`). Caso contrario, a opcao B nao se aplica
    para aquele recibo (mas ainda eh exibida em C linha-a-linha).

    Returns:
        Lista de AssaiReciboMotochefe.
    """
    from sqlalchemy.orm import aliased

    chassis_inativos = [
        r[0] for r in (
            db.session.query(AssaiReciboItem.chassi)
            .filter_by(recibo_id=recibo_id, ativo=False)
            .all()
        )
    ]
    if not chassis_inativos:
        return []

    # Recibos antigos que tem item ativo conflitante
    Antigo = aliased(AssaiReciboItem)
    recibos_ids = [
        r[0] for r in (
            db.session.query(Antigo.recibo_id)
            .filter(Antigo.chassi.in_(chassis_inativos))
            .filter(Antigo.ativo.is_(True))
            .filter(Antigo.recibo_id != recibo_id)
            .distinct()
            .all()
        )
    ]
    if not recibos_ids:
        return []

    # Filtra apenas os que nao tem nenhum item conflitante recebido
    bloqueados = set(
        r[0] for r in (
            db.session.query(AssaiReciboItem.recibo_id)
            .filter(AssaiReciboItem.recibo_id.in_(recibos_ids))
            .filter(AssaiReciboItem.chassi.in_(chassis_inativos))
            .filter(AssaiReciboItem.ativo.is_(True))
            .filter(AssaiReciboItem.conferido.is_(True))
            .all()
        )
    )
    elegiveis = [rid for rid in recibos_ids if rid not in bloqueados]
    if not elegiveis:
        return []
    return (
        AssaiReciboMotochefe.query
        .filter(AssaiReciboMotochefe.id.in_(elegiveis))
        .order_by(AssaiReciboMotochefe.id.asc())
        .all()
    )


def opcao_a_excluir_novo(recibo_id: int) -> None:
    """Opcao A: descarta o recibo novo inteiro (que esta em RESOLVENDO_DUPLICIDADE).

    Hard-delete do recibo + cascade dos itens + S3 cleanup.
    Idempotente quanto a S3 (best-effort).
    """
    recibo = AssaiReciboMotochefe.query.get_or_404(recibo_id)
    if recibo.status != RECIBO_STATUS_RESOLVENDO_DUPLICIDADE:
        raise ReciboValidationError(
            f'Recibo {recibo_id} nao esta em RESOLVENDO_DUPLICIDADE (status={recibo.status})'
        )
    _excluir_recibo_inteiro(recibo)


def opcao_b_excluir_antigo(recibo_id_novo: int, recibo_id_antigo: int) -> None:
    """Opcao B: descarta o recibo ANTIGO inteiro (somente se nenhum item dele
    foi recebido). Apos exclusao, ativa todos os itens INATIVOS do recibo novo
    cujo chassi pertencia ao recibo antigo. Se o recibo novo nao tiver mais
    duplicados pendentes, vai para AGUARDANDO_CONFERENCIA.
    """
    recibo_novo = AssaiReciboMotochefe.query.get_or_404(recibo_id_novo)
    if recibo_novo.status != RECIBO_STATUS_RESOLVENDO_DUPLICIDADE:
        raise ReciboValidationError(
            f'Recibo {recibo_id_novo} nao esta em RESOLVENDO_DUPLICIDADE'
        )
    recibo_antigo = AssaiReciboMotochefe.query.get_or_404(recibo_id_antigo)
    if recibo_antigo.id == recibo_novo.id:
        raise ReciboValidationError('Recibo novo e antigo coincidem')

    # Validacao de relacao: recibo_antigo precisa ter pelo menos um chassi
    # que esta INATIVO em recibo_novo (= conflito real). Sem isso, qualquer
    # recibo poderia ser excluido por essa rota.
    chassis_inativos_novo = {
        r[0] for r in (
            db.session.query(AssaiReciboItem.chassi)
            .filter_by(recibo_id=recibo_novo.id, ativo=False)
            .all()
        )
    }
    chassis_ativos_antigo = {
        r[0] for r in (
            db.session.query(AssaiReciboItem.chassi)
            .filter_by(recibo_id=recibo_antigo.id, ativo=True)
            .all()
        )
    }
    overlap = chassis_inativos_novo & chassis_ativos_antigo
    if not overlap:
        raise ReciboValidationError(
            f'Recibo antigo #{recibo_antigo.id} nao tem chassis em conflito '
            f'com o recibo novo #{recibo_novo.id}'
        )

    # Bloqueia se qualquer item antigo foi recebido
    if (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_antigo.id, conferido=True, ativo=True)
        .first()
    ):
        raise ReciboValidationError(
            f'Recibo antigo #{recibo_antigo.id} tem motos ja recebidas. '
            f'Use opcao por chassi.'
        )

    chassis_antigo = chassis_ativos_antigo
    s3_key_antigo = recibo_antigo.doc_s3_key
    recibo_antigo_id = recibo_antigo.id

    try:
        _excluir_recibo_inteiro(recibo_antigo, commit=False)

        # Reativa itens do recibo novo cujo chassi pertencia ao antigo
        novos_para_reativar = (
            AssaiReciboItem.query
            .filter(AssaiReciboItem.recibo_id == recibo_novo.id)
            .filter(AssaiReciboItem.ativo.is_(False))
            .filter(AssaiReciboItem.chassi.in_(chassis_antigo))
            .all()
        )
        for it in novos_para_reativar:
            outro = (
                AssaiReciboItem.query
                .filter(AssaiReciboItem.chassi == it.chassi)
                .filter(AssaiReciboItem.ativo.is_(True))
                .filter(AssaiReciboItem.recibo_id != recibo_novo.id)
                .first()
            )
            if outro is None:
                it.ativo = True

        _talvez_finalizar_resolucao(recibo_novo)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    # S3 cleanup pos-commit (best-effort, respeitando compartilhamento)
    if s3_key_antigo:
        _talvez_remover_s3(s3_key_antigo, recibo_antigo_id)


def opcao_c_remover_chassi_antigo(recibo_id_novo: int, item_id_antigo: int) -> None:
    """Opcao C (linha): remove o chassi do recibo ANTIGO (soft-delete) e
    reativa o chassi correspondente no recibo NOVO.

    Bloqueia se item antigo `conferido=True`.
    """
    recibo_novo = AssaiReciboMotochefe.query.get_or_404(recibo_id_novo)
    if recibo_novo.status != RECIBO_STATUS_RESOLVENDO_DUPLICIDADE:
        raise ReciboValidationError(
            f'Recibo {recibo_id_novo} nao esta em RESOLVENDO_DUPLICIDADE'
        )

    item_antigo = AssaiReciboItem.query.get_or_404(item_id_antigo)
    if item_antigo.recibo_id == recibo_novo.id:
        raise ReciboValidationError('item_id_antigo pertence ao recibo novo')
    if item_antigo.conferido:
        raise ReciboValidationError(
            f'Item antigo #{item_antigo.id} ja foi recebido — nao pode ser removido'
        )
    if not item_antigo.ativo:
        raise ReciboValidationError(f'Item antigo #{item_antigo.id} ja esta inativo')

    novo_inativo = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_novo.id, chassi=item_antigo.chassi, ativo=False)
        .first()
    )
    if not novo_inativo:
        raise ReciboValidationError(
            f'Recibo novo nao tem item inativo com chassi {item_antigo.chassi}'
        )

    try:
        item_antigo.ativo = False
        novo_inativo.ativo = True
        _talvez_finalizar_resolucao(recibo_novo)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def opcao_c_remover_chassi_novo(recibo_id_novo: int, item_id_novo: int) -> None:
    """Opcao C (linha): mantem o chassi do recibo ANTIGO e descarta o item do
    recibo NOVO (permanece `ativo=False`).

    Como o item ja esta inativo, esta acao apenas marca a decisao no item
    (campo `tipo_divergencia=DIVERGENCIA_DESCARTADO_DUPLICIDADE` informativo)
    e finaliza a resolucao se nao houver mais pendencias.
    """
    recibo_novo = AssaiReciboMotochefe.query.get_or_404(recibo_id_novo)
    if recibo_novo.status != RECIBO_STATUS_RESOLVENDO_DUPLICIDADE:
        raise ReciboValidationError(
            f'Recibo {recibo_id_novo} nao esta em RESOLVENDO_DUPLICIDADE'
        )
    item_novo = AssaiReciboItem.query.get_or_404(item_id_novo)
    if item_novo.recibo_id != recibo_novo.id:
        raise ReciboValidationError('item_id_novo nao pertence ao recibo novo')
    if item_novo.ativo:
        raise ReciboValidationError(f'Item novo #{item_novo.id} ja esta ativo')

    try:
        # Marca como decidido (idempotente — mantem inativo)
        item_novo.tipo_divergencia = (
            item_novo.tipo_divergencia or DIVERGENCIA_DESCARTADO_DUPLICIDADE
        )
        _talvez_finalizar_resolucao(recibo_novo)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise


def _talvez_finalizar_resolucao(recibo_novo: AssaiReciboMotochefe) -> None:
    """Se nao ha mais conflitos pendentes (todos os inativos do novo tem
    decisao registrada OU nao tem mais item antigo ativo), passa o recibo
    novo para AGUARDANDO_CONFERENCIA."""
    inativos_novo = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_novo.id, ativo=False)
        .all()
    )
    pendentes = 0
    for it in inativos_novo:
        # Pendente = ainda existe outro item antigo ativo com mesmo chassi
        # E o item novo nao foi marcado com decisao
        outro_ativo = (
            AssaiReciboItem.query
            .filter(AssaiReciboItem.chassi == it.chassi)
            .filter(AssaiReciboItem.ativo.is_(True))
            .filter(AssaiReciboItem.recibo_id != recibo_novo.id)
            .first()
        )
        if outro_ativo and not it.tipo_divergencia:
            pendentes += 1

    if pendentes == 0:
        recibo_novo.status = RECIBO_STATUS_AGUARDANDO


# ---------------------------------------------------------------------------
# Soft-delete de item / exclusao de recibo (operacoes auxiliares)
# ---------------------------------------------------------------------------

def inativar_item(item_id: int) -> AssaiReciboItem:
    """Inativa um AssaiReciboItem (soft-delete).

    Bloqueado se item.conferido=True (moto ja recebida).
    """
    item = AssaiReciboItem.query.get_or_404(item_id)
    if item.conferido:
        raise ReciboValidationError(
            f'Chassi {item.chassi} ja foi recebido — nao pode ser inativado'
        )
    if not item.ativo:
        return item  # idempotente
    try:
        item.ativo = False
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return item


def reativar_item(item_id: int) -> AssaiReciboItem:
    """Reativa um item inativo. Bloqueado se ja existe item ativo com mesmo
    chassi em outro recibo (UNIQUE parcial)."""
    item = AssaiReciboItem.query.get_or_404(item_id)
    if item.ativo:
        return item

    conflito = (
        AssaiReciboItem.query
        .filter(AssaiReciboItem.chassi == item.chassi)
        .filter(AssaiReciboItem.ativo.is_(True))
        .filter(AssaiReciboItem.id != item.id)
        .first()
    )
    if conflito:
        raise ReciboValidationError(
            f'Chassi {item.chassi} ja esta ativo no recibo #{conflito.recibo_id}'
        )
    try:
        item.ativo = True
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return item


def excluir_recibo(recibo_id: int) -> None:
    """Exclui um recibo inteiro (somente se nenhum item foi recebido).

    Hard-delete + cascade dos itens + S3 cleanup.
    """
    recibo = AssaiReciboMotochefe.query.get_or_404(recibo_id)
    if (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, conferido=True)
        .first()
    ):
        raise ReciboValidationError(
            f'Recibo #{recibo_id} tem motos ja recebidas — nao pode ser excluido'
        )
    _excluir_recibo_inteiro(recibo)


def _excluir_recibo_inteiro(recibo: AssaiReciboMotochefe, commit: bool = True) -> None:
    """Helper: hard-delete do recibo + cascade dos itens + S3 cleanup.

    S3 cleanup respeita compartilhamento: se outro recibo ainda referencia
    o mesmo `doc_s3_key`, o arquivo NAO e removido.
    """
    s3_key = recibo.doc_s3_key
    recibo_id_excluido = recibo.id
    try:
        db.session.delete(recibo)  # cascade -> itens
        if commit:
            db.session.commit()
    except Exception:
        if commit:
            db.session.rollback()
        raise

    # S3 best-effort APOS commit (se commit=True). Se commit=False, S3 sera
    # limpo pelo caller depois do commit conjunto.
    if commit and s3_key:
        _talvez_remover_s3(s3_key, recibo_id_excluido)


def _talvez_remover_s3(s3_key: str, recibo_id_excluido: int) -> None:
    """Remove arquivo do S3 apenas se nenhum outro recibo referencia o mesmo key.

    Em prod foi detectado cenario com multiplos recibos compartilhando o
    mesmo `doc_s3_key` (re-importacao). Apagar incondicionalmente quebraria
    os outros recibos que apontam para o mesmo arquivo.
    """
    if not s3_key:
        return
    outros = (
        db.session.query(db.func.count(AssaiReciboMotochefe.id))
        .filter(AssaiReciboMotochefe.doc_s3_key == s3_key)
        .filter(AssaiReciboMotochefe.id != recibo_id_excluido)
        .scalar()
    )
    if outros and outros > 0:
        logger.info(
            f'S3 mantido ({s3_key}): {outros} outro(s) recibo(s) ainda referenciam.'
        )
        return
    try:
        FileStorage().delete_file(s3_key)
    except Exception as s3_err:
        logger.warning(f'Falha ao remover S3 ({s3_key}): {s3_err}')
