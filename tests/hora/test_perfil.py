"""Testes do perfil_service HORA (perfis de permissao das Lojas HORA).

Cobre: derivacao de slug (prefixo hora_, sem colidir com reservados, dedup),
guarda de nome duplicado/invalido, esqueleto (get/salvar), aplicacao do perfil
sobre o usuario (pre-fill) e redefinicao.
"""
import uuid

import pytest

from app.auth.models import Usuario
from app.hora.models import PERFIS_SISTEMA_RESERVADOS
from app.hora.services import perfil_service, permissao_service


def _novo_usuario(db, *, perfil='financeiro', sistema_lojas=True, status='ativo'):
    u = Usuario(
        nome='Usuario Teste',
        email=f'{uuid.uuid4().hex[:10]}@test.local',
        senha_hash='x',
        perfil=perfil,
        status=status,
        sistema_lojas=sistema_lojas,
    )
    db.session.add(u)
    db.session.flush()
    return u


# --- slug -----------------------------------------------------------------

def test_criar_perfil_financeiro_nao_colide_com_reservado(db):
    """Perfil HORA "Financeiro" gera slug hora_financeiro, distinto do reservado."""
    p = perfil_service.criar_perfil('Financeiro')
    assert p.nome == 'Financeiro'
    assert p.slug == 'hora_financeiro'
    assert p.slug.startswith('hora_')
    assert p.slug not in PERFIS_SISTEMA_RESERVADOS
    assert 'financeiro' in PERFIS_SISTEMA_RESERVADOS  # o reservado segue intacto


def test_slug_dedup_para_nomes_que_normalizam_igual(db):
    """Dois perfis cujo nome normaliza para o mesmo slug recebem slugs distintos."""
    p1 = perfil_service.criar_perfil('Vendedor Loja')
    p2 = perfil_service.criar_perfil('Vendedor  Loja!')  # mesmo slugify, nome !=
    assert p1.slug == 'hora_vendedor_loja'
    assert p2.slug != p1.slug
    assert p2.slug.startswith('hora_vendedor_loja')


def test_slug_respeita_limite_30_chars(db):
    nome_longo = 'Perfil Com Nome Extremamente Longo Para Testar Truncamento'
    p = perfil_service.criar_perfil(nome_longo)
    assert len(p.slug) <= 30
    assert p.slug.startswith('hora_')


# --- guardas de criacao ---------------------------------------------------

def test_nome_duplicado_ativo_levanta(db):
    perfil_service.criar_perfil('Gerente')
    with pytest.raises(ValueError):
        perfil_service.criar_perfil('gerente')  # case-insensitive


def test_nome_invalido_levanta(db):
    with pytest.raises(ValueError):
        perfil_service.criar_perfil('')
    with pytest.raises(ValueError):
        perfil_service.criar_perfil('x')  # < 2 chars


# --- esqueleto ------------------------------------------------------------

def test_skeleton_round_trip(db):
    p = perfil_service.criar_perfil('Operador A')
    perfil_service.salvar_skeleton(p.id, {
        'estoque': {'ver': True},
        'vendas': {'ver': True, 'criar': True},
    })
    sk = perfil_service.get_skeleton(p.id)
    assert sk['estoque']['ver'] is True
    assert sk['estoque']['criar'] is False
    assert sk['vendas']['ver'] is True
    assert sk['vendas']['criar'] is True
    # modulo nao mencionado vem tudo False
    assert sk['lojas']['ver'] is False


# --- aplicacao sobre o usuario --------------------------------------------

def test_aplicar_perfil_preenche_permissoes_e_grava_slug(db):
    p = perfil_service.criar_perfil('Operador B')
    perfil_service.salvar_skeleton(p.id, {
        'estoque': {'ver': True},
        'vendas': {'ver': True, 'criar': True},
    })
    u = _novo_usuario(db)

    perfil_service.aplicar_perfil_em_usuario(u.id, p.slug)

    assert u.perfil == p.slug
    assert permissao_service.tem_perm(u, 'estoque', 'ver') is True
    assert permissao_service.tem_perm(u, 'vendas', 'criar') is True
    assert permissao_service.tem_perm(u, 'vendas', 'apagar') is False
    assert permissao_service.tem_perm(u, 'lojas', 'ver') is False


def test_aplicar_perfil_inativo_levanta(db):
    p = perfil_service.criar_perfil('Inativo C')
    perfil_service.set_ativo(p.id, False)
    u = _novo_usuario(db)
    with pytest.raises(ValueError):
        perfil_service.aplicar_perfil_em_usuario(u.id, p.slug)


def test_redefinir_descarta_ajuste_manual(db):
    p = perfil_service.criar_perfil('Operador D')
    perfil_service.salvar_skeleton(p.id, {'estoque': {'ver': True}})
    u = _novo_usuario(db)
    perfil_service.aplicar_perfil_em_usuario(u.id, p.slug)

    # ajuste manual: concede vendas/ver (fora do esqueleto)
    permissao_service.salvar_matriz_completa(
        u.id, {'estoque': {'ver': True}, 'vendas': {'ver': True}},
    )
    assert permissao_service.tem_perm(u, 'vendas', 'ver') is True

    # redefinir volta ao esqueleto (sem vendas)
    perfil_service.redefinir_permissoes_pelo_perfil(u.id)
    assert permissao_service.tem_perm(u, 'vendas', 'ver') is False
    assert permissao_service.tem_perm(u, 'estoque', 'ver') is True


def test_redefinir_sem_perfil_hora_levanta(db):
    u = _novo_usuario(db, perfil='financeiro')  # perfil do sistema, nao HORA
    with pytest.raises(ValueError):
        perfil_service.redefinir_permissoes_pelo_perfil(u.id)


# --- consulta -------------------------------------------------------------

def test_slug_eh_perfil_hora(db):
    p = perfil_service.criar_perfil('Consulta E')
    assert perfil_service.slug_eh_perfil_hora(p.slug) is True
    assert perfil_service.slug_eh_perfil_hora('financeiro') is False
    assert perfil_service.slug_eh_perfil_hora(None) is False


def test_listar_exclui_inativos_por_padrao(db):
    p = perfil_service.criar_perfil('Temp F')
    perfil_service.set_ativo(p.id, False)
    ativos_ids = [x.id for x in perfil_service.listar_perfis(incluir_inativos=False)]
    todos_ids = [x.id for x in perfil_service.listar_perfis(incluir_inativos=True)]
    assert p.id not in ativos_ids
    assert p.id in todos_ids
