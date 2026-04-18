"""CRUD de cadastros: HoraLoja, HoraModelo, HoraTabelaPreco."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, Optional

from app import db
from app.hora.models import HoraLoja, HoraModelo, HoraTabelaPreco


# ----------------------------- Loja -----------------------------

def criar_loja(
    cnpj: str,
    nome: str,
    endereco: Optional[str] = None,
    cidade: Optional[str] = None,
    uf: Optional[str] = None,
) -> HoraLoja:
    cnpj_norm = ''.join(c for c in cnpj if c.isdigit())
    if len(cnpj_norm) != 14:
        raise ValueError(f"CNPJ inválido (esperado 14 dígitos): {cnpj}")

    existente = HoraLoja.query.filter_by(cnpj=cnpj_norm).first()
    if existente:
        raise ValueError(f"Loja já cadastrada com CNPJ {cnpj_norm}")

    loja = HoraLoja(
        cnpj=cnpj_norm,
        nome=nome,
        endereco=endereco,
        cidade=cidade,
        uf=uf.upper() if uf else None,
        ativa=True,
    )
    db.session.add(loja)
    db.session.commit()
    return loja


def listar_lojas(apenas_ativas: bool = True) -> Iterable[HoraLoja]:
    query = HoraLoja.query.order_by(HoraLoja.nome)
    if apenas_ativas:
        query = query.filter_by(ativa=True)
    return query.all()


def buscar_loja_por_cnpj(cnpj: str) -> Optional[HoraLoja]:
    cnpj_norm = ''.join(c for c in cnpj if c.isdigit())
    return HoraLoja.query.filter_by(cnpj=cnpj_norm).first()


# ----------------------------- Modelo -----------------------------

def criar_modelo(
    nome_modelo: str,
    potencia_motor: Optional[str] = None,
    descricao: Optional[str] = None,
) -> HoraModelo:
    nome_norm = nome_modelo.strip()
    if not nome_norm:
        raise ValueError("nome_modelo obrigatório")

    existente = HoraModelo.query.filter_by(nome_modelo=nome_norm).first()
    if existente:
        raise ValueError(f"Modelo já cadastrado: {nome_norm}")

    modelo = HoraModelo(
        nome_modelo=nome_norm,
        potencia_motor=potencia_motor,
        descricao=descricao,
        ativo=True,
    )
    db.session.add(modelo)
    db.session.commit()
    return modelo


def buscar_ou_criar_modelo(nome_modelo: str) -> HoraModelo:
    """Usado na ingestão: modelo extraído da NF pode ser novo."""
    nome_norm = (nome_modelo or '').strip()
    if not nome_norm:
        nome_norm = 'MODELO_DESCONHECIDO'

    existente = HoraModelo.query.filter_by(nome_modelo=nome_norm).first()
    if existente:
        return existente

    modelo = HoraModelo(nome_modelo=nome_norm, ativo=True)
    db.session.add(modelo)
    db.session.flush()
    return modelo


def listar_modelos(apenas_ativos: bool = True) -> Iterable[HoraModelo]:
    query = HoraModelo.query.order_by(HoraModelo.nome_modelo)
    if apenas_ativos:
        query = query.filter_by(ativo=True)
    return query.all()


# ----------------------------- Tabela de Preço -----------------------------

def criar_tabela_preco(
    modelo_id: int,
    preco_tabela: Decimal,
    vigencia_inicio: date,
    vigencia_fim: Optional[date] = None,
) -> HoraTabelaPreco:
    if preco_tabela <= 0:
        raise ValueError("preco_tabela deve ser > 0")

    tabela = HoraTabelaPreco(
        modelo_id=modelo_id,
        preco_tabela=Decimal(preco_tabela),
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=vigencia_fim,
        ativo=True,
    )
    db.session.add(tabela)
    db.session.commit()
    return tabela


def buscar_preco_vigente(modelo_id: int, na_data: date) -> Optional[HoraTabelaPreco]:
    """Retorna a linha de preço vigente do modelo na data informada.

    Critério: ativo=True, vigencia_inicio <= na_data <= vigencia_fim (ou fim NULL).
    Se houver múltiplas, retorna a mais recente (maior vigencia_inicio).
    """
    from sqlalchemy import or_

    return (
        HoraTabelaPreco.query
        .filter(
            HoraTabelaPreco.modelo_id == modelo_id,
            HoraTabelaPreco.ativo.is_(True),
            HoraTabelaPreco.vigencia_inicio <= na_data,
            or_(
                HoraTabelaPreco.vigencia_fim.is_(None),
                HoraTabelaPreco.vigencia_fim >= na_data,
            ),
        )
        .order_by(HoraTabelaPreco.vigencia_inicio.desc())
        .first()
    )
