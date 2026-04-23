"""Service de permissoes granulares HORA.

Regras (alinhadas com plano confirmado pelo usuario):
- Admin (perfil='administrador') passa em qualquer checagem (sempre True).
- Usuario sem `sistema_lojas` nem admin: bloqueia tudo.
- Usuario com `sistema_lojas=True` mas sem entry na tabela: BLOQUEADO por default
  (qualquer acao exige permissao explicita do admin).
- Usuario com entry: usa flags pode_ver / pode_criar / pode_editar / pode_apagar.
"""
from __future__ import annotations

from typing import Iterable

from app import db
from app.auth.models import Usuario
from app.hora.models import HoraUserPermissao, MODULOS_HORA, ACOES_HORA


# Helpers ---------------------------------------------------------------

def _validar_modulo(modulo: str) -> None:
    if modulo not in {m for m, _ in MODULOS_HORA}:
        raise ValueError(f'modulo invalido: {modulo!r}')


def _validar_acao(acao: str) -> None:
    if acao not in {a for a, _ in ACOES_HORA}:
        raise ValueError(f'acao invalida: {acao!r}')


# API publica ----------------------------------------------------------

def listar_modulos() -> list[tuple[str, str]]:
    """Lista canonica de modulos do HORA: [(slug, label), ...]."""
    return list(MODULOS_HORA)


def listar_acoes() -> list[tuple[str, str]]:
    """Lista canonica de acoes: [(slug, label), ...]."""
    return list(ACOES_HORA)


def is_admin(usuario: Usuario | None) -> bool:
    if usuario is None:
        return False
    return getattr(usuario, 'perfil', None) == 'administrador'


def tem_perm(usuario: Usuario | None, modulo: str, acao: str = 'ver') -> bool:
    """Checa se `usuario` tem permissao de `acao` em `modulo`.

    - Admin com status='ativo' sempre True.
    - Usuario com status != 'ativo' (bloqueado/rejeitado/pendente): False.
    - Usuarios sem sistema_lojas e nao-admin: False.
    - Default para usuario com sistema_lojas mas sem entry: False (bloqueado).
    """
    _validar_modulo(modulo)
    _validar_acao(acao)

    if usuario is None or not getattr(usuario, 'is_authenticated', False):
        return False
    # Bloqueia bloqueado/rejeitado/pendente independente de sistema_lojas/admin.
    if getattr(usuario, 'status', None) != 'ativo':
        return False
    if is_admin(usuario):
        return True
    if not getattr(usuario, 'sistema_lojas', False):
        return False

    perm = (
        HoraUserPermissao.query
        .filter_by(user_id=usuario.id, modulo=modulo)
        .first()
    )
    if perm is None:
        return False
    return bool(getattr(perm, f'pode_{acao}'))


def _perm_to_dict(p: HoraUserPermissao | None) -> dict[str, bool]:
    """Converte uma linha de HoraUserPermissao (ou None) em dict de flags.

    Fonte unica para a estrutura {acao: bool} usada por get_matriz e get_matrizes_batch.
    """
    return {
        'ver':     bool(p and p.pode_ver),
        'criar':   bool(p and p.pode_criar),
        'editar':  bool(p and p.pode_editar),
        'apagar':  bool(p and p.pode_apagar),
        'aprovar': bool(p and p.pode_aprovar),
    }


def get_matriz(user_id: int) -> dict[str, dict[str, bool]]:
    """Retorna matriz {modulo: {acao: bool}} para um usuario.

    Modulos sem entry vem com todas as acoes False. Util para a tela
    de gestao mostrar o estado completo e para cache por request.
    """
    perms = {
        p.modulo: p
        for p in HoraUserPermissao.query.filter_by(user_id=user_id).all()
    }
    return {slug: _perm_to_dict(perms.get(slug)) for slug, _ in MODULOS_HORA}


def get_matrizes_batch(user_ids: Iterable[int]) -> dict[int, dict[str, dict[str, bool]]]:
    """Versao batch de get_matriz para listagens (1 query)."""
    ids = list(user_ids)
    if not ids:
        return {}
    perms = (
        HoraUserPermissao.query
        .filter(HoraUserPermissao.user_id.in_(ids))
        .all()
    )
    bucket: dict[int, dict[str, HoraUserPermissao]] = {uid: {} for uid in ids}
    for p in perms:
        bucket[p.user_id][p.modulo] = p

    return {
        uid: {slug: _perm_to_dict(bucket[uid].get(slug)) for slug, _ in MODULOS_HORA}
        for uid in ids
    }


def upsert_perm(
    user_id: int,
    modulo: str,
    *,
    pode_ver: bool,
    pode_criar: bool,
    pode_editar: bool,
    pode_apagar: bool,
    pode_aprovar: bool = False,
    atualizado_por_id: int | None = None,
) -> HoraUserPermissao:
    """Insere ou atualiza permissao para (user_id, modulo). Commit responsabilidade do caller."""
    _validar_modulo(modulo)
    perm = (
        HoraUserPermissao.query
        .filter_by(user_id=user_id, modulo=modulo)
        .first()
    )
    if perm is None:
        perm = HoraUserPermissao(user_id=user_id, modulo=modulo)
        db.session.add(perm)
    perm.pode_ver = bool(pode_ver)
    perm.pode_criar = bool(pode_criar)
    perm.pode_editar = bool(pode_editar)
    perm.pode_apagar = bool(pode_apagar)
    perm.pode_aprovar = bool(pode_aprovar)
    perm.atualizado_por_id = atualizado_por_id
    return perm


def salvar_matriz_completa(
    user_id: int,
    matriz: dict[str, dict[str, bool]],
    *,
    atualizado_por_id: int | None = None,
) -> int:
    """Aplica matriz completa (10 modulos x N acoes) para um usuario em batch.

    Retorna numero de modulos efetivamente persistidos. Faz commit ao final.
    """
    salvos = 0
    for modulo, _ in MODULOS_HORA:
        flags = matriz.get(modulo, {})
        upsert_perm(
            user_id=user_id,
            modulo=modulo,
            pode_ver=flags.get('ver', False),
            pode_criar=flags.get('criar', False),
            pode_editar=flags.get('editar', False),
            pode_apagar=flags.get('apagar', False),
            pode_aprovar=flags.get('aprovar', False),
            atualizado_por_id=atualizado_por_id,
        )
        salvos += 1
    db.session.commit()
    return salvos
