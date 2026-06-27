"""Service de perfis de permissao das Lojas HORA.

Um perfil HORA e um TEMPLATE de permissoes (ver `app/hora/models/perfil.py`). Este
service cuida do CRUD do perfil, da edicao do esqueleto (matriz modulo x acao) e da
aplicacao do esqueleto sobre um usuario (pre-fill / redefinir).

Regras-chave:
- O admin informa apenas o NOME; o slug e derivado automaticamente com prefixo
  `hora_`, garantido unico e fora dos 6 slugs reservados (`PERFIS_SISTEMA_RESERVADOS`).
  => existe perfil HORA "Financeiro" sem colidir com o `financeiro` do sistema.
- Atribuir um perfil a um usuario grava `Usuario.perfil = slug` E copia o esqueleto
  para `hora_user_permissao` (que segue sendo a fonte de verdade da permissao efetiva).
  O perfil NAO e consultado em runtime — e so o template de pre-fill/reset.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from app import db
from app.auth.models import Usuario
from app.hora.models import (
    HoraPerfil,
    HoraPerfilPermissao,
    MODULOS_HORA,
    PERFIS_SISTEMA_RESERVADOS,
    PERFIL_HORA_SLUG_PREFIXO,
)
from app.hora.services import permissao_service
from app.utils.timezone import agora_utc_naive

_SLUG_MAXLEN = 30  # casa com Usuario.perfil String(30) e hora_perfil.slug


# --- Geracao de slug -------------------------------------------------------

def _slugify(nome: str) -> str:
    """Normaliza um nome livre para a base do slug: ascii, minusculo, [a-z0-9_]."""
    base = unicodedata.normalize('NFKD', nome or '').encode('ascii', 'ignore').decode('ascii')
    base = base.lower()
    base = re.sub(r'[^a-z0-9]+', '_', base)
    base = re.sub(r'_+', '_', base).strip('_')
    return base


def _slug_existe(slug: str) -> bool:
    return db.session.query(
        HoraPerfil.query.filter_by(slug=slug).exists()
    ).scalar()


def _gerar_slug_unico(nome: str) -> str:
    """Deriva um slug `hora_<nome>` unico e fora dos reservados (≤30 chars)."""
    corpo = _slugify(nome)
    if not corpo:
        raise ValueError('Nome do perfil invalido (vazio apos normalizacao).')

    prefixo = PERFIL_HORA_SLUG_PREFIXO
    corpo_max = _SLUG_MAXLEN - len(prefixo)

    candidato = (prefixo + corpo[:corpo_max]).rstrip('_')
    if candidato not in PERFIS_SISTEMA_RESERVADOS and not _slug_existe(candidato):
        return candidato

    # Dedup: sufixo numerico, reservando espaco para caber em 30.
    i = 2
    while True:
        sufixo = f'_{i}'
        corpo_trunc = corpo[: corpo_max - len(sufixo)].rstrip('_')
        candidato = f'{prefixo}{corpo_trunc}{sufixo}'
        if candidato not in PERFIS_SISTEMA_RESERVADOS and not _slug_existe(candidato):
            return candidato
        i += 1


# --- Consulta --------------------------------------------------------------

def listar_perfis(incluir_inativos: bool = False) -> list[HoraPerfil]:
    """Perfis HORA ordenados por nome. Por padrao so os ativos."""
    q = HoraPerfil.query
    if not incluir_inativos:
        q = q.filter(HoraPerfil.ativo.is_(True))
    return q.order_by(HoraPerfil.nome).all()


def get_perfil(perfil_id: int) -> HoraPerfil | None:
    return HoraPerfil.query.get(perfil_id)


def get_perfil_por_slug(slug: str | None) -> HoraPerfil | None:
    if not slug:
        return None
    return HoraPerfil.query.filter_by(slug=slug).first()


def mapa_perfis_por_slug(incluir_inativos: bool = True) -> dict[str, HoraPerfil]:
    """{slug: HoraPerfil} — para exibir o nome amigavel de um Usuario.perfil HORA.

    Inclui inativos por padrao: um usuario pode carregar o slug de um perfil que
    foi desativado depois; a tela ainda precisa renderizar o nome.
    """
    return {p.slug: p for p in listar_perfis(incluir_inativos=incluir_inativos)}


def slug_eh_perfil_hora(slug: str | None) -> bool:
    """True se `slug` corresponde a um perfil HORA cadastrado (ativo ou nao)."""
    return get_perfil_por_slug(slug) is not None


# --- CRUD do perfil --------------------------------------------------------

def criar_perfil(nome: str, *, criado_por_id: int | None = None) -> HoraPerfil:
    """Cria um perfil HORA a partir do NOME (slug derivado automaticamente).

    Cria tambem o esqueleto vazio (1 linha por modulo, tudo False). Faz commit.
    Levanta ValueError em nome invalido ou nome ja existente (entre ativos).
    """
    nome = (nome or '').strip()
    if len(nome) < 2:
        raise ValueError('Nome do perfil deve ter ao menos 2 caracteres.')
    if len(nome) > 80:
        raise ValueError('Nome do perfil muito longo (maximo 80 caracteres).')

    ja_existe = (
        HoraPerfil.query
        .filter(db.func.lower(HoraPerfil.nome) == nome.lower())
        .filter(HoraPerfil.ativo.is_(True))
        .first()
    )
    if ja_existe:
        raise ValueError(f'Ja existe um perfil ativo chamado "{nome}".')

    slug = _gerar_slug_unico(nome)
    perfil = HoraPerfil(slug=slug, nome=nome, ativo=True, criado_por_id=criado_por_id)
    db.session.add(perfil)
    db.session.flush()  # garante perfil.id

    for modulo, _ in MODULOS_HORA:
        db.session.add(HoraPerfilPermissao(perfil_id=perfil.id, modulo=modulo))

    db.session.commit()
    return perfil


def renomear_perfil(perfil_id: int, nome: str) -> HoraPerfil:
    """Renomeia o perfil (slug NAO muda — usuarios ja referenciam o slug). Commit."""
    nome = (nome or '').strip()
    if len(nome) < 2:
        raise ValueError('Nome do perfil deve ter ao menos 2 caracteres.')
    if len(nome) > 80:
        raise ValueError('Nome do perfil muito longo (maximo 80 caracteres).')
    perfil = HoraPerfil.query.get(perfil_id)
    if perfil is None:
        raise ValueError('Perfil nao encontrado.')

    colisao = (
        HoraPerfil.query
        .filter(db.func.lower(HoraPerfil.nome) == nome.lower())
        .filter(HoraPerfil.ativo.is_(True))
        .filter(HoraPerfil.id != perfil_id)
        .first()
    )
    if colisao:
        raise ValueError(f'Ja existe outro perfil ativo chamado "{nome}".')

    perfil.nome = nome
    db.session.commit()
    return perfil


def set_ativo(perfil_id: int, ativo: bool) -> HoraPerfil:
    """Ativa/desativa o perfil. Desativar NAO mexe nos usuarios que ja o usam —
    apenas o remove da lista de perfis oferecidos para novas atribuicoes. Commit.
    """
    perfil = HoraPerfil.query.get(perfil_id)
    if perfil is None:
        raise ValueError('Perfil nao encontrado.')
    perfil.ativo = bool(ativo)
    db.session.commit()
    return perfil


# --- Esqueleto (matriz modulo x acao) -------------------------------------

def get_skeleton(perfil_id: int) -> dict[str, dict[str, bool]]:
    """Matriz {modulo: {acao: bool}} do perfil, cobrindo todos os MODULOS_HORA."""
    rows = {
        p.modulo: p
        for p in HoraPerfilPermissao.query.filter_by(perfil_id=perfil_id).all()
    }
    return {
        slug: permissao_service._perm_to_dict(rows.get(slug))
        for slug, _ in MODULOS_HORA
    }


def salvar_skeleton(perfil_id: int, matriz: dict[str, dict[str, bool]]) -> int:
    """Aplica a matriz completa ao esqueleto do perfil (upsert por modulo). Commit.

    Retorna o numero de modulos persistidos.
    """
    perfil = HoraPerfil.query.get(perfil_id)
    if perfil is None:
        raise ValueError('Perfil nao encontrado.')

    existentes = {
        p.modulo: p
        for p in HoraPerfilPermissao.query.filter_by(perfil_id=perfil_id).all()
    }
    salvos = 0
    for modulo, _ in MODULOS_HORA:
        flags = matriz.get(modulo, {})
        row = existentes.get(modulo)
        if row is None:
            row = HoraPerfilPermissao(perfil_id=perfil_id, modulo=modulo)
            db.session.add(row)
        row.pode_ver = bool(flags.get('ver', False))
        row.pode_criar = bool(flags.get('criar', False))
        row.pode_editar = bool(flags.get('editar', False))
        row.pode_apagar = bool(flags.get('apagar', False))
        row.pode_aprovar = bool(flags.get('aprovar', False))
        salvos += 1

    perfil.atualizado_em = agora_utc_naive()
    db.session.commit()
    return salvos


# --- Aplicacao sobre o usuario --------------------------------------------

def aplicar_perfil_em_usuario(
    user_id: int,
    perfil_slug: str,
    *,
    atualizado_por_id: int | None = None,
) -> HoraPerfil:
    """Atribui o perfil a um usuario: grava Usuario.perfil = slug E copia o
    esqueleto para hora_user_permissao (pre-fill). As permissoes ficam editaveis
    depois. Faz commit (via salvar_matriz_completa). Levanta ValueError se o
    perfil nao existir/estiver inativo ou o usuario nao existir.
    """
    perfil = get_perfil_por_slug(perfil_slug)
    if perfil is None:
        raise ValueError('Perfil HORA nao encontrado.')
    if not perfil.ativo:
        raise ValueError(f'Perfil "{perfil.nome}" esta inativo.')

    usuario = Usuario.query.get(user_id)
    if usuario is None:
        raise ValueError('Usuario nao encontrado.')

    usuario.perfil = perfil.slug
    matriz = get_skeleton(perfil.id)
    # salvar_matriz_completa commita a sessao — inclui a mudanca de usuario.perfil.
    permissao_service.salvar_matriz_completa(
        user_id=user_id, matriz=matriz, atualizado_por_id=atualizado_por_id,
    )
    return perfil


def redefinir_permissoes_pelo_perfil(
    user_id: int,
    *,
    atualizado_por_id: int | None = None,
) -> HoraPerfil:
    """Re-aplica o esqueleto do perfil ATUAL do usuario (descarta ajustes manuais).

    Levanta ValueError se o usuario nao tiver um perfil HORA associado.
    """
    usuario = Usuario.query.get(user_id)
    if usuario is None:
        raise ValueError('Usuario nao encontrado.')
    perfil = get_perfil_por_slug(usuario.perfil)
    if perfil is None:
        raise ValueError(
            'Usuario nao esta associado a um perfil HORA. '
            'Atribua um perfil antes de redefinir.'
        )
    matriz = get_skeleton(perfil.id)
    permissao_service.salvar_matriz_completa(
        user_id=user_id, matriz=matriz, atualizado_por_id=atualizado_por_id,
    )
    return perfil


def contar_modulos_concedidos(perfil_id: int) -> int:
    """Quantos modulos do esqueleto tem ao menos uma flag True (para a listagem)."""
    rows = HoraPerfilPermissao.query.filter_by(perfil_id=perfil_id).all()
    return sum(
        1 for r in rows
        if r.pode_ver or r.pode_criar or r.pode_editar or r.pode_apagar or r.pode_aprovar
    )


def contar_modulos_concedidos_batch(perfil_ids: Iterable[int]) -> dict[int, int]:
    """Versao batch de contar_modulos_concedidos (1 query) para a listagem."""
    ids = list(perfil_ids)
    if not ids:
        return {}
    rows = (
        HoraPerfilPermissao.query
        .filter(HoraPerfilPermissao.perfil_id.in_(ids))
        .all()
    )
    contagem: dict[int, int] = {pid: 0 for pid in ids}
    for r in rows:
        if r.pode_ver or r.pode_criar or r.pode_editar or r.pode_apagar or r.pode_aprovar:
            contagem[r.perfil_id] = contagem.get(r.perfil_id, 0) + 1
    return contagem
