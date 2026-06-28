"""Cadastro de pecas (CRUD + foto + mapeamento TagPlus opcional).

NAO confundir com peca_faltando_service.py (peca FALTANDO em moto).
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from flask import current_app

from app import db
from app.hora.models import HoraPeca, HoraTagPlusPecaMap
from app.utils.file_storage import FileStorage


ALLOWED_FOTO_EXT = {'jpg', 'jpeg', 'png', 'webp', 'heic'}


def criar_peca(
    codigo_interno: str,
    descricao: str,
    ncm: Optional[str] = None,
    cfop_default: str = '5.102',
    unidade: str = 'UN',
    preco_venda_padrao: Decimal = Decimal('0'),
    custo: Decimal = Decimal('0'),
    ativo: bool = True,
) -> HoraPeca:
    """Cria peca. Levanta ValueError em duplicata de codigo_interno."""
    codigo = (codigo_interno or '').strip().upper()
    if not codigo:
        raise ValueError('codigo_interno e obrigatorio')
    if not (descricao or '').strip():
        raise ValueError('descricao e obrigatoria')

    existente = HoraPeca.query.filter_by(codigo_interno=codigo).first()
    if existente:
        raise ValueError(
            f'peca com codigo_interno={codigo!r} ja existe (id={existente.id})'
        )

    p = HoraPeca(
        codigo_interno=codigo,
        descricao=descricao.strip(),
        ncm=(ncm or '').strip() or None,
        cfop_default=(cfop_default or '5.102').strip(),
        unidade=(unidade or 'UN').strip().upper(),
        preco_venda_padrao=Decimal(str(preco_venda_padrao or 0)),
        custo=Decimal(str(custo or 0)),
        ativo=bool(ativo),
    )
    db.session.add(p)
    db.session.commit()
    return p


def editar_peca(peca_id: int, **campos) -> HoraPeca:
    """Atualiza campos editaveis de peca. Ignora chaves desconhecidas."""
    p = HoraPeca.query.get(peca_id)
    if not p:
        raise ValueError(f'peca {peca_id} nao encontrada')

    editaveis = {
        'descricao', 'ncm', 'cfop_default', 'unidade',
        'preco_venda_padrao', 'custo', 'ativo',
    }
    for k, v in campos.items():
        if k in editaveis:
            if k in ('preco_venda_padrao', 'custo'):
                v = Decimal(str(v or 0))
            setattr(p, k, v)
    db.session.commit()
    return p


def inativar_peca(peca_id: int) -> HoraPeca:
    return editar_peca(peca_id, ativo=False)


def ativar_peca(peca_id: int) -> HoraPeca:
    return editar_peca(peca_id, ativo=True)


def set_tagplus_map(
    peca_id: int,
    tagplus_produto_id: str,
    tagplus_codigo: Optional[str] = None,
    cfop_default: Optional[str] = None,
) -> HoraTagPlusPecaMap:
    """Cria ou atualiza mapeamento TagPlus para uma peca."""
    p = HoraPeca.query.get(peca_id)
    if not p:
        raise ValueError(f'peca {peca_id} nao encontrada')
    if not (tagplus_produto_id or '').strip():
        raise ValueError('tagplus_produto_id e obrigatorio')

    m = HoraTagPlusPecaMap.query.filter_by(peca_id=peca_id).first()
    if not m:
        m = HoraTagPlusPecaMap(peca_id=peca_id)
        db.session.add(m)
    m.tagplus_produto_id = str(tagplus_produto_id).strip()
    m.tagplus_codigo = (tagplus_codigo or '').strip() or None
    m.cfop_default = (cfop_default or '').strip() or None
    db.session.commit()
    return m


def remover_tagplus_map(peca_id: int) -> None:
    m = HoraTagPlusPecaMap.query.filter_by(peca_id=peca_id).first()
    if m:
        db.session.delete(m)
        db.session.commit()


def upload_foto(peca_id: int, file_obj, criado_por: Optional[str] = None) -> str:
    """Salva foto no S3 e atualiza foto_s3_key. Retorna a key."""
    p = HoraPeca.query.get(peca_id)
    if not p:
        raise ValueError(f'peca {peca_id} nao encontrada')

    storage = FileStorage()
    folder = f'hora/pecas/{p.id}'
    s3_key = storage.save_file(
        file=file_obj, folder=folder, allowed_extensions=ALLOWED_FOTO_EXT,
    )
    if not s3_key:
        raise ValueError('Falha ao salvar foto')
    p.foto_s3_key = s3_key
    db.session.commit()
    return s3_key


def get_foto_url(peca: HoraPeca) -> Optional[str]:
    if not peca or not peca.foto_s3_key:
        return None
    try:
        return FileStorage().get_file_url(peca.foto_s3_key)
    except Exception as exc:
        current_app.logger.warning(f'Erro foto peca {peca.id}: {exc}')
        return None


def listar_pecas(
    busca: Optional[str] = None,
    ativo: Optional[bool] = None,
    sem_tagplus: bool = False,
    limit: int = 200,
) -> List[HoraPeca]:
    q = HoraPeca.query
    if busca:
        b = f'%{busca.strip()}%'
        q = q.filter(
            db.or_(
                HoraPeca.codigo_interno.ilike(b),
                HoraPeca.descricao.ilike(b),
            )
        )
    if ativo is not None:
        q = q.filter(HoraPeca.ativo == ativo)
    if sem_tagplus:
        sub = db.session.query(HoraTagPlusPecaMap.peca_id).subquery()
        q = q.filter(~HoraPeca.id.in_(sub))
    return q.order_by(HoraPeca.codigo_interno).limit(limit).all()


def get_peca(peca_id: int) -> Optional[HoraPeca]:
    return HoraPeca.query.get(peca_id)
