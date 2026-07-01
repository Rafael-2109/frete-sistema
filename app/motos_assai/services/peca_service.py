"""peca_service — catalogo de pecas e compatibilidade por modelo (Spec 1 §11).

`criar/vincular/...` fazem add+flush SEM commit (caller controla a transacao).
"""
from decimal import Decimal

from app import db
from app.motos_assai.models import AssaiModelo, AssaiPeca, AssaiPecaModelo
from app.utils.timezone import agora_brasil_naive


class PecaError(Exception):
    """Erro de dominio de peca_service."""


def criar_peca(*, nome, codigo=None, custo_referencia=None, modelo_ids=None, operador_id):
    if not nome or not nome.strip():
        raise PecaError('nome obrigatorio')
    peca = AssaiPeca(
        nome=nome.strip(),
        codigo=(codigo.strip() if codigo else None),
        custo_referencia=(Decimal(str(custo_referencia)) if custo_referencia is not None else None),
        ativo=True,
        criado_por_id=operador_id,
        criado_em=agora_brasil_naive(),
    )
    db.session.add(peca)
    db.session.flush()
    for mid in (modelo_ids or []):
        vincular_modelo(peca_id=peca.id, modelo_id=mid)
    db.session.flush()
    return peca


def editar_peca(*, peca_id, **campos):
    peca = db.session.get(AssaiPeca, peca_id)
    if not peca:
        raise PecaError(f'peca {peca_id} nao encontrada')
    for campo in ('nome', 'codigo', 'ativo'):
        if campo in campos:
            setattr(peca, campo, campos[campo])
    if 'custo_referencia' in campos:
        valor = campos['custo_referencia']
        peca.custo_referencia = Decimal(str(valor)) if valor is not None else None
    db.session.flush()
    return peca


def vincular_modelo(*, peca_id, modelo_id):
    existente = AssaiPecaModelo.query.filter_by(peca_id=peca_id, modelo_id=modelo_id).first()
    if existente:
        return existente
    if not db.session.get(AssaiPeca, peca_id):
        raise PecaError(f'peca {peca_id} nao encontrada')
    if not db.session.get(AssaiModelo, modelo_id):
        raise PecaError(f'modelo {modelo_id} nao encontrado')
    link = AssaiPecaModelo(peca_id=peca_id, modelo_id=modelo_id)
    db.session.add(link)
    db.session.flush()
    return link


def desvincular_modelo(*, peca_id, modelo_id):
    link = AssaiPecaModelo.query.filter_by(peca_id=peca_id, modelo_id=modelo_id).first()
    if link:
        db.session.delete(link)
        db.session.flush()
    return None


def listar_compativeis(modelo_id):
    return (
        AssaiPeca.query
        .join(AssaiPecaModelo, AssaiPecaModelo.peca_id == AssaiPeca.id)
        .filter(AssaiPecaModelo.modelo_id == modelo_id, AssaiPeca.ativo.is_(True))
        .order_by(AssaiPeca.nome)
        .all()
    )


def listar(*, ativo=True, busca=None):
    q = AssaiPeca.query
    if ativo is not None:
        q = q.filter(AssaiPeca.ativo.is_(ativo))
    if busca:
        like = f'%{busca}%'
        q = q.filter(db.or_(AssaiPeca.nome.ilike(like), AssaiPeca.codigo.ilike(like)))
    return q.order_by(AssaiPeca.nome).all()
