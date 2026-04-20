"""Peca faltando: registro, fotos N:1, canibalizacao.

Canibalizacao: quando um mecanico tira uma peca da moto A para completar a
moto B, registramos:
    - peca_faltando de B vira RESOLVIDA com `chassi_doador=A`.
    - Automaticamente cria peca_faltando em A (mesma descricao) e emite
      evento FALTANDO_PECA em A.

Tambem permite registrar peca faltando avulsa (sem canibalizacao) com 1+ fotos.
"""
from __future__ import annotations

from typing import List, Optional

from flask import current_app

from app import db
from app.hora.models import (
    HoraMoto,
    HoraPecaFaltando,
    HoraPecaFaltandoFoto,
    HoraRecebimentoConferencia,
)
from app.hora.services.moto_service import registrar_evento, ultimo_evento
from app.utils.file_storage import FileStorage
from app.utils.timezone import agora_utc_naive


STATUS_VALIDOS = {'ABERTA', 'RESOLVIDA', 'CANCELADA'}
ALLOWED_FOTO_EXT = {'jpg', 'jpeg', 'png', 'webp', 'heic'}


def registrar_peca_faltando(
    numero_chassi: str,
    descricao: str,
    recebimento_conferencia_id: Optional[int] = None,
    loja_id: Optional[int] = None,
    observacoes: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraPecaFaltando:
    """Cria pendencia de peca faltando + emite evento FALTANDO_PECA na moto."""
    chassi = numero_chassi.strip().upper()
    moto = HoraMoto.query.get(chassi)
    if not moto:
        raise ValueError(f'chassi {chassi} nao existe em hora_moto')
    if not descricao or not descricao.strip():
        raise ValueError('descricao da peca e obrigatoria')

    if recebimento_conferencia_id:
        conf = HoraRecebimentoConferencia.query.get(recebimento_conferencia_id)
        if not conf:
            raise ValueError(
                f'conferencia {recebimento_conferencia_id} nao encontrada'
            )
        if conf.numero_chassi != chassi:
            raise ValueError('conferencia e de outro chassi')

    peca = HoraPecaFaltando(
        numero_chassi=chassi,
        descricao=descricao.strip(),
        status='ABERTA',
        recebimento_conferencia_id=recebimento_conferencia_id,
        observacoes=observacoes,
        criado_por=criado_por,
    )
    db.session.add(peca)
    db.session.flush()

    # Se loja_id nao foi passado, deriva do ultimo evento da moto.
    # Sem loja_id, a moto "desaparece" de listar_estoque com filtro de loja.
    loja_efetiva = loja_id
    if loja_efetiva is None:
        ev_atual = ultimo_evento(chassi)
        loja_efetiva = ev_atual.loja_id if ev_atual else None

    registrar_evento(
        numero_chassi=chassi,
        tipo='FALTANDO_PECA',
        origem_tabela='hora_peca_faltando',
        origem_id=peca.id,
        loja_id=loja_efetiva,
        operador=criado_por,
        detalhe=f'Peca faltando: {peca.descricao}',
    )

    db.session.commit()
    return peca


def adicionar_foto(
    peca_faltando_id: int,
    file_obj,
    legenda: Optional[str] = None,
    criado_por: Optional[str] = None,
) -> HoraPecaFaltandoFoto:
    """Salva arquivo no storage e cria linha em hora_peca_faltando_foto."""
    peca = HoraPecaFaltando.query.get(peca_faltando_id)
    if not peca:
        raise ValueError(f'peca_faltando {peca_faltando_id} nao encontrada')

    storage = FileStorage()
    folder = f'hora/peca_faltando/{peca.numero_chassi}'
    try:
        s3_key = storage.save_file(
            file=file_obj,
            folder=folder,
            allowed_extensions=ALLOWED_FOTO_EXT,
        )
    except ValueError as exc:
        raise ValueError(f'Erro ao salvar foto: {exc}')
    if not s3_key:
        raise ValueError('Falha ao salvar foto (retorno vazio do storage).')

    foto = HoraPecaFaltandoFoto(
        peca_faltando_id=peca.id,
        foto_s3_key=s3_key,
        legenda=legenda,
        criado_por=criado_por,
    )
    db.session.add(foto)
    db.session.commit()
    return foto


def remover_foto(peca_faltando_id: int, foto_id: int) -> None:
    peca = HoraPecaFaltando.query.get(peca_faltando_id)
    if not peca:
        raise ValueError(f'peca_faltando {peca_faltando_id} nao encontrada')
    foto = HoraPecaFaltandoFoto.query.get(foto_id)
    if not foto or foto.peca_faltando_id != peca.id:
        raise ValueError(f'foto {foto_id} nao pertence a esta pendencia')
    db.session.delete(foto)
    db.session.commit()


def canibalizar(
    peca_faltando_id: int,
    chassi_doador: str,
    operador: Optional[str] = None,
    descricao_override: Optional[str] = None,
) -> dict:
    """Resolve pendencia B (peca_faltando_id) usando peca da moto A (chassi_doador).

    - peca.status = RESOLVIDA, peca.chassi_doador = A
    - Cria nova peca_faltando em A (status ABERTA, mesma descricao) +
      emite evento FALTANDO_PECA em A.
    """
    peca_b = HoraPecaFaltando.query.get(peca_faltando_id)
    if not peca_b:
        raise ValueError(f'peca_faltando {peca_faltando_id} nao encontrada')
    if peca_b.status != 'ABERTA':
        raise ValueError(
            f'peca_faltando {peca_faltando_id} nao esta ABERTA '
            f'(status={peca_b.status})'
        )

    chassi_a = chassi_doador.strip().upper()
    if chassi_a == peca_b.numero_chassi:
        raise ValueError('chassi doador nao pode ser o mesmo da peca')

    moto_a = HoraMoto.query.get(chassi_a)
    if not moto_a:
        raise ValueError(f'chassi doador {chassi_a} nao existe')

    # Resolve B
    peca_b.chassi_doador = chassi_a
    peca_b.status = 'RESOLVIDA'
    peca_b.resolvido_em = agora_utc_naive()
    peca_b.resolvido_por = operador

    # Cria pendencia em A (mesma descricao, ou override)
    descricao = descricao_override or peca_b.descricao
    peca_a = HoraPecaFaltando(
        numero_chassi=chassi_a,
        descricao=descricao,
        status='ABERTA',
        observacoes=f'Canibalizacao: peca cedida para {peca_b.numero_chassi}',
        criado_por=operador,
    )
    db.session.add(peca_a)
    db.session.flush()

    # loja_id do doador = loja do ultimo evento (preserva visibilidade no estoque
    # da loja correta — sem isso, FALTANDO_PECA com loja_id=None faz a moto
    # desaparecer do estoque por filtro `loja_id IN (...)`).
    ev_doador = ultimo_evento(chassi_a)
    loja_id_doador = ev_doador.loja_id if ev_doador else None
    registrar_evento(
        numero_chassi=chassi_a,
        tipo='FALTANDO_PECA',
        origem_tabela='hora_peca_faltando',
        origem_id=peca_a.id,
        loja_id=loja_id_doador,
        operador=operador,
        detalhe=(
            f'Peca "{descricao}" cedida para {peca_b.numero_chassi} '
            f'(pendencia #{peca_b.id})'
        ),
    )

    db.session.commit()
    return {
        'peca_resolvida_id': peca_b.id,
        'peca_nova_id': peca_a.id,
        'chassi_doador': chassi_a,
    }


def resolver_peca(
    peca_faltando_id: int,
    operador: Optional[str] = None,
    observacoes: Optional[str] = None,
) -> HoraPecaFaltando:
    """Marca RESOLVIDA sem canibalizacao (peca chegou/foi comprada)."""
    peca = HoraPecaFaltando.query.get(peca_faltando_id)
    if not peca:
        raise ValueError(f'peca_faltando {peca_faltando_id} nao encontrada')
    if peca.status != 'ABERTA':
        raise ValueError(f'peca nao esta ABERTA (status={peca.status})')
    peca.status = 'RESOLVIDA'
    peca.resolvido_em = agora_utc_naive()
    peca.resolvido_por = operador
    if observacoes:
        peca.observacoes = (
            (peca.observacoes or '') + f'\n[RESOLVIDA] {observacoes}'
        ).strip()
    db.session.commit()
    return peca


def cancelar_peca(
    peca_faltando_id: int,
    operador: Optional[str] = None,
) -> HoraPecaFaltando:
    peca = HoraPecaFaltando.query.get(peca_faltando_id)
    if not peca:
        raise ValueError(f'peca_faltando {peca_faltando_id} nao encontrada')
    peca.status = 'CANCELADA'
    peca.resolvido_em = agora_utc_naive()
    peca.resolvido_por = operador
    db.session.commit()
    return peca


def listar_pecas(
    chassi: Optional[str] = None,
    status: Optional[str] = None,
    lojas_permitidas_ids: Optional[List[int]] = None,
    limit: int = 200,
) -> List[HoraPecaFaltando]:
    """Lista pecas. Se lojas_permitidas_ids, filtra chassis cuja loja atual
    (ultimo evento) esteja na lista — via JOIN SQL para preservar paginacao."""
    from sqlalchemy import and_, func
    from app.hora.models import HoraMotoEvento

    q = HoraPecaFaltando.query
    if chassi:
        q = q.filter(HoraPecaFaltando.numero_chassi == chassi.strip().upper())
    if status:
        q = q.filter(HoraPecaFaltando.status == status)

    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        # Subquery: ultimo evento por chassi.
        sub_ult = (
            db.session.query(
                HoraMotoEvento.numero_chassi.label('chassi'),
                func.max(HoraMotoEvento.id).label('max_id'),
            )
            .group_by(HoraMotoEvento.numero_chassi)
            .subquery()
        )
        q = (
            q.join(sub_ult, sub_ult.c.chassi == HoraPecaFaltando.numero_chassi)
            .join(
                HoraMotoEvento,
                and_(
                    HoraMotoEvento.id == sub_ult.c.max_id,
                    HoraMotoEvento.loja_id.in_(lojas_permitidas_ids),
                ),
            )
        )

    return (
        q.order_by(HoraPecaFaltando.criado_em.desc(), HoraPecaFaltando.id.desc())
        .limit(limit)
        .all()
    )


def get_foto_url(foto: HoraPecaFaltandoFoto) -> Optional[str]:
    """Wrapper sobre FileStorage.get_file_url."""
    try:
        return FileStorage().get_file_url(foto.foto_s3_key)
    except Exception as exc:  # pragma: no cover
        current_app.logger.warning(f'Erro ao gerar URL foto: {exc}')
        return None
