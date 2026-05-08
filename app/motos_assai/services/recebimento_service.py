"""Service de recebimento físico — valida chassi contra recibo, registra conferência,
finaliza com `MOTO_FALTANDO` em batch para chassis declarados que não chegaram.

Lock pessimista via UNIQUE parcial em (recibo_id, chassi) — race retorna 409.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from sqlalchemy.exc import IntegrityError

from app import db
from app.motos_assai.models import (
    AssaiReciboMotochefe, AssaiReciboItem, AssaiMoto, AssaiModelo,
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
    DIVERGENCIA_MODELO_DIFERENTE, DIVERGENCIA_COR_DIFERENTE,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO, DIVERGENCIA_AVARIA_FISICA,
    EVENTO_ESTOQUE, EVENTO_MOTO_FALTANDO,
    COMPRA_STATUS_RECEBIMENTO_PARCIAL, COMPRA_STATUS_FECHADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.chassi_validator import validar_chassi


class RecebimentoConflictError(Exception):
    """Race condition em conferência simultânea — caller retorna 409."""


class RecebimentoValidationError(Exception):
    pass


def validar_chassi_contra_recibo(recibo_id: int, chassi: str) -> Dict[str, Any]:
    """Valida chassi contra o recibo (sem persistir).

    Retorna:
        {
            'ok': bool,
            'item_id': int | None,
            'modelo_id_esperado': int | None,
            'cor_esperada': str | None,
            'modelo_texto_recibo': str | None,
            'ja_conferido': bool,
            'na_nf': bool,           # false → CHASSI_EXTRA
            'regex_check': dict,     # do chassi_validator
            'mensagem': str,
        }
    """
    chassi_norm = chassi.strip().upper()
    item = AssaiReciboItem.query.filter_by(
        recibo_id=recibo_id, chassi=chassi_norm,
    ).first()

    if not item:
        return {
            'ok': False, 'item_id': None,
            'modelo_id_esperado': None, 'cor_esperada': None,
            'modelo_texto_recibo': None,
            'ja_conferido': False, 'na_nf': False,
            'regex_check': {'ok': True, 'mensagem': 'sem regex (chassi não no recibo)', 'regex_usado': None},
            'mensagem': f'Chassi {chassi_norm} NÃO está no recibo (CHASSI_EXTRA)',
        }

    regex_check = validar_chassi(chassi_norm, item.modelo_id)

    return {
        'ok': not item.conferido,
        'item_id': item.id,
        'modelo_id_esperado': item.modelo_id,
        'cor_esperada': item.cor_texto,
        'modelo_texto_recibo': item.modelo_texto_recibo,
        'ja_conferido': item.conferido,
        'na_nf': True,
        'regex_check': regex_check,
        'mensagem': (
            f'Já conferido em conferência anterior' if item.conferido
            else f'Chassi pertence ao recibo, modelo esperado: {item.modelo_id}'
        ),
    }


def registrar_conferencia(
    recibo_id: int,
    chassi: str,
    modelo_conferido_id: Optional[int],
    cor_conferida: Optional[str],
    qr_code_lido: bool,
    foto_s3_key: Optional[str],
    operador_id: int,
    avaria_fisica: bool = False,
) -> AssaiReciboItem:
    """Registra conferência de 1 chassi.

    - Cria AssaiMoto se não existe (modelo/cor conferidos).
    - Atualiza AssaiMoto se moto existe e cor/modelo conferidos divergem do cadastrado
      (exceção autorizada: recebimento físico é SOT).
    - Atualiza AssaiReciboItem.conferido=True.
    - Emite evento ESTOQUE.
    - Se chassi não está no recibo, marca tipo_divergencia=CHASSI_EXTRA.
    - Se modelo/cor divergem do recibo: tipo_divergencia=MODELO_DIFERENTE/COR_DIFERENTE.

    Raises:
        RecebimentoConflictError: race em UNIQUE (recibo_id, chassi).
        RecebimentoValidationError: dados inválidos.
    """
    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        raise RecebimentoValidationError('Chassi vazio')

    if not modelo_conferido_id:
        raise RecebimentoValidationError('Modelo conferido obrigatório')

    item = AssaiReciboItem.query.filter_by(
        recibo_id=recibo_id, chassi=chassi_norm,
    ).first()

    # Race condition: item já conferido por outro operador (H2)
    if item and item.conferido:
        raise RecebimentoConflictError(
            f'Chassi {chassi_norm} já conferido — atualize a tela'
        )

    # Detecta divergências
    tipo_divergencia = None
    if not item:
        # Chassi NÃO está no recibo → CHASSI_EXTRA — cria item novo no recibo
        try:
            item = AssaiReciboItem(
                recibo_id=recibo_id,
                chassi=chassi_norm,
                modelo_id=modelo_conferido_id,
                modelo_texto_recibo=None,
                cor_texto=cor_conferida,
                tipo_divergencia=DIVERGENCIA_CHASSI_EXTRA,
                conferido=True,
                qr_code_lido=qr_code_lido,
                foto_s3_key=foto_s3_key,
            )
            db.session.add(item)
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            raise RecebimentoConflictError(
                f'Conflito: chassi {chassi_norm} sendo gravado simultaneamente'
            )
    else:
        if item.modelo_id and item.modelo_id != modelo_conferido_id:
            tipo_divergencia = DIVERGENCIA_MODELO_DIFERENTE
        elif item.cor_texto and cor_conferida and \
             item.cor_texto.upper() != (cor_conferida or '').upper():
            tipo_divergencia = DIVERGENCIA_COR_DIFERENTE
        if avaria_fisica:
            tipo_divergencia = DIVERGENCIA_AVARIA_FISICA

        item.conferido = True
        item.qr_code_lido = qr_code_lido
        item.foto_s3_key = foto_s3_key or item.foto_s3_key
        if tipo_divergencia:
            item.tipo_divergencia = tipo_divergencia

    try:
        # Cria/atualiza AssaiMoto
        # with_for_update(of=AssaiMoto) evita erro "FOR UPDATE cannot be applied to nullable side
        # of outer join" causado pelo lazy='joined' em AssaiMoto.modelo.
        moto = (
            db.session.query(AssaiMoto)
            .filter(AssaiMoto.chassi == chassi_norm)
            .with_for_update(of=AssaiMoto)
            .first()
        )
        if not moto:
            moto = AssaiMoto(
                chassi=chassi_norm,
                modelo_id=modelo_conferido_id,
                cor=cor_conferida,
                motor=item.motor if item else None,
            )
            db.session.add(moto)
        else:
            # Recebimento como SOT: UPDATE em cor/modelo se divergiu (exceção autorizada)
            if moto.modelo_id != modelo_conferido_id:
                moto.modelo_id = modelo_conferido_id
            if cor_conferida and moto.cor != cor_conferida:
                moto.cor = cor_conferida

        # Atualiza recibo para EM_CONFERENCIA se ainda AGUARDANDO
        recibo = AssaiReciboMotochefe.query.get(recibo_id)
        if recibo and recibo.status == RECIBO_STATUS_AGUARDANDO:
            recibo.status = RECIBO_STATUS_EM_CONFERENCIA

        # Emite evento ESTOQUE
        emitir_evento(
            chassi_norm, EVENTO_ESTOQUE,
            operador_id=operador_id,
            dados_extras={
                'recibo_id': recibo_id, 'item_id': item.id,
                'tipo_divergencia': tipo_divergencia,
            },
        )

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return item


def finalizar_recebimento(
    recibo_id: int, operador_id: int,
    confirmar_faltantes: bool = False,
) -> AssaiReciboMotochefe:
    """Finaliza conferência. Para cada item NÃO conferido, marca MOTO_FALTANDO.

    Args:
        confirmar_faltantes: True → operador confirmou ciência. False e há faltantes
            → raise (caller mostra modal e re-chama com True).
    """
    recibo = AssaiReciboMotochefe.query.get_or_404(recibo_id)

    nao_conferidos: List[AssaiReciboItem] = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id, conferido=False)
        .all()
    )

    if nao_conferidos and not confirmar_faltantes:
        raise RecebimentoValidationError(
            f'{len(nao_conferidos)} chassis não conferidos. Confirme MOTO_FALTANDO ou continue conferindo.'
        )

    try:
        # Marca cada não-conferido como MOTO_FALTANDO
        for item in nao_conferidos:
            item.tipo_divergencia = DIVERGENCIA_MOTO_FALTANDO
            emitir_evento(
                item.chassi, EVENTO_MOTO_FALTANDO,
                operador_id=operador_id,
                observacao='Declarado no recibo mas não chegou fisicamente',
                dados_extras={'recibo_id': recibo_id, 'item_id': item.id},
            )

        # Status final do recibo
        com_divergencia = (
            nao_conferidos
            or AssaiReciboItem.query.filter(
                AssaiReciboItem.recibo_id == recibo_id,
                AssaiReciboItem.tipo_divergencia.isnot(None),
            ).count() > 0
        )
        recibo.status = RECIBO_STATUS_COM_DIVERGENCIA if com_divergencia else RECIBO_STATUS_CONCLUIDO

        # Propaga status para AssaiCompraMotochefe quando TODOS os recibos estão finalizados
        if recibo.compra_id:
            todos_recibos = AssaiReciboMotochefe.query.filter_by(
                compra_id=recibo.compra_id,
            ).all()
            status_finais = {RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA}
            if all(r.status in status_finais or r.id == recibo_id for r in todos_recibos):
                compra = recibo.compra
                if compra:
                    algum_com_divergencia = any(
                        (r.status == RECIBO_STATUS_COM_DIVERGENCIA or com_divergencia and r.id == recibo_id)
                        for r in todos_recibos
                    )
                    compra.status = (
                        COMPRA_STATUS_RECEBIMENTO_PARCIAL
                        if algum_com_divergencia
                        else COMPRA_STATUS_FECHADA
                    )

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return recibo
