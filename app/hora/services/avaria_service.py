"""Service de avaria em moto de estoque HORA.

Regra-chave: avaria NAO bloqueia venda. Apenas registra + emite evento
AVARIADA em hora_moto_evento. Moto continua em estoque vendavel (AVARIADA
esta em EVENTOS_EM_ESTOQUE).
"""
from __future__ import annotations

from typing import Iterable, Optional, Tuple, List

from app import db
from app.hora.models import HoraAvaria, HoraAvariaFoto, HoraMoto, HoraMotoEvento
from app.hora.services.moto_service import registrar_evento
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.utils.timezone import agora_utc_naive


def _ultimo_evento_tipo(numero_chassi: str) -> Optional[str]:
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=numero_chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )
    return ev.tipo if ev else None


def registrar_avaria(
    numero_chassi: str,
    descricao: str,
    fotos: Iterable[Tuple[str, Optional[str]]],
    usuario: str,
    loja_id: int,
) -> HoraAvaria:
    """Cria avaria + N fotos na mesma transaction. Emite evento AVARIADA.

    Args:
        numero_chassi: chassi da moto (deve estar em estoque).
        descricao: texto livre (>= 3 chars apos strip).
        fotos: iteravel de (foto_s3_key, legenda_opcional). Min 1.
        usuario: nome do operador.
        loja_id: loja onde moto esta (snapshot).

    Raises:
        ValueError: se >=1 foto nao fornecida, descricao curta, chassi
            inexistente, ou chassi fora de estoque.
    """
    fotos_list: List[Tuple[str, Optional[str]]] = list(fotos)
    if not fotos_list:
        raise ValueError("Avaria requer pelo menos 1 foto")

    desc_limpa = (descricao or '').strip()
    if len(desc_limpa) < 3:
        raise ValueError("descricao deve ter pelo menos 3 caracteres")

    chassi_norm = numero_chassi.strip().upper()
    moto = HoraMoto.query.get(chassi_norm)
    if not moto:
        raise ValueError(f"chassi inexistente: {chassi_norm}")

    ultimo = _ultimo_evento_tipo(chassi_norm)
    if ultimo is None or ultimo not in EVENTOS_EM_ESTOQUE:
        raise ValueError(
            f"chassi {chassi_norm} nao esta em estoque (ultimo evento: {ultimo})"
        )

    avaria = HoraAvaria(
        numero_chassi=chassi_norm,
        loja_id=loja_id,
        descricao=desc_limpa,
        status='ABERTA',
        criado_por=usuario,
    )
    db.session.add(avaria)
    db.session.flush()

    for foto_s3_key, legenda in fotos_list:
        if not foto_s3_key:
            continue
        foto = HoraAvariaFoto(
            avaria_id=avaria.id,
            foto_s3_key=foto_s3_key,
            legenda=legenda,
            criado_por=usuario,
        )
        db.session.add(foto)

    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='AVARIADA',
        origem_tabela='hora_avaria',
        origem_id=avaria.id,
        loja_id=loja_id,
        operador=usuario,
        detalhe=f"Avaria #{avaria.id}: {desc_limpa[:180]}",
    )
    db.session.flush()
    return avaria


def adicionar_foto(
    avaria_id: int,
    foto_s3_key: str,
    legenda: Optional[str],
    usuario: str,
) -> HoraAvariaFoto:
    avaria = HoraAvaria.query.get(avaria_id)
    if not avaria:
        raise ValueError(f"avaria inexistente: {avaria_id}")
    foto = HoraAvariaFoto(
        avaria_id=avaria.id,
        foto_s3_key=foto_s3_key,
        legenda=legenda,
        criado_por=usuario,
    )
    db.session.add(foto)
    db.session.flush()
    return foto


def resolver_avaria(avaria_id: int, observacao: str, usuario: str) -> HoraAvaria:
    return _finalizar_avaria(avaria_id, 'RESOLVIDA', observacao, usuario)


def ignorar_avaria(avaria_id: int, observacao: str, usuario: str) -> HoraAvaria:
    return _finalizar_avaria(avaria_id, 'IGNORADA', observacao, usuario)


def _finalizar_avaria(
    avaria_id: int, novo_status: str, observacao: str, usuario: str,
) -> HoraAvaria:
    avaria = HoraAvaria.query.get(avaria_id)
    if not avaria:
        raise ValueError(f"avaria inexistente: {avaria_id}")
    if avaria.status != 'ABERTA':
        raise ValueError(
            f"avaria {avaria_id} ja esta {avaria.status} — nao pode re-finalizar"
        )

    obs_limpa = (observacao or '').strip()
    if len(obs_limpa) < 3:
        raise ValueError("observacao de resolucao obrigatoria (min 3 chars)")

    avaria.status = novo_status
    avaria.resolvido_em = agora_utc_naive()
    avaria.resolvido_por = usuario
    avaria.resolucao_observacao = obs_limpa
    db.session.flush()
    return avaria


def avarias_abertas_por_chassi(chassis: list) -> dict:
    """Para badge na listagem de estoque. Retorna {chassi: count}."""
    if not chassis:
        return {}
    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(HoraAvaria.numero_chassi, db.func.count(HoraAvaria.id))
        .filter(
            HoraAvaria.numero_chassi.in_(chassis_norm),
            HoraAvaria.status == 'ABERTA',
        )
        .group_by(HoraAvaria.numero_chassi)
        .all()
    )
    return {chassi: count for chassi, count in rows}
