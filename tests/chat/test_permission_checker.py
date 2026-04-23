"""
Tests para PermissionChecker — Task 5 chat in-app.

Todos os testes sao pure (sem DB): usam SimpleNamespace como stub de usuario.
"""
import pytest
from types import SimpleNamespace

from app.chat.services.permission_checker import (
    sistemas, pode_adicionar,
    DOMAIN_NACOM, DOMAIN_CARVIA, DOMAIN_MOTOCHEFE, DOMAIN_HORA,
)


def user(perfil='logistica', carvia=False, motochefe=False, hora=None):
    return SimpleNamespace(
        perfil=perfil,
        sistema_carvia=carvia,
        sistema_motochefe=motochefe,
        loja_hora_id=hora,
    )


def test_sistemas_base_nacom():
    assert sistemas(user()) == {DOMAIN_NACOM}


def test_sistemas_carvia():
    assert sistemas(user(carvia=True)) == {DOMAIN_NACOM, DOMAIN_CARVIA}


def test_sistemas_todos():
    u = user(carvia=True, motochefe=True, hora=5)
    assert sistemas(u) == {DOMAIN_NACOM, DOMAIN_CARVIA, DOMAIN_MOTOCHEFE, DOMAIN_HORA}


def test_pode_adicionar_superset():
    actor = user(carvia=True)         # {NACOM, CARVIA}
    target = user(carvia=False)       # {NACOM}
    assert pode_adicionar(actor, target) is True


def test_pode_adicionar_negado_se_faltar():
    actor = user(carvia=False)        # {NACOM}
    target = user(carvia=True)        # {NACOM, CARVIA}
    assert pode_adicionar(actor, target) is False


def test_pode_adicionar_iguais():
    a = user(carvia=True)
    b = user(carvia=True)
    assert pode_adicionar(a, b) is True


def test_admin_bypass():
    actor = user(perfil='administrador')
    target = user(carvia=True, motochefe=True)  # mais que actor
    assert pode_adicionar(actor, target) is True
