"""
Helpers de permissao para o catalogo de comandos do Ctrl+K.

Espelham EXATAMENTE as condicoes de _sidebar.html. Ao adicionar comando
em comandos.py, USAR um destes helpers (nunca duplicar logica de permissao).

IMPORTANTE: ao mudar regra de permissao na sidebar, atualizar aqui tambem.
Validador em scripts/audits/cmdk_catalog_validator.py garante sincronia.
"""
from flask_login import current_user


# =============================================================================
# Helpers basicos
# =============================================================================

def _u(user=None):
    """Retorna user (dado ou current_user)."""
    return user if user is not None else current_user


def autenticado(user=None):
    u = _u(user)
    return bool(u and u.is_authenticated)


def is_admin(user=None):
    """perfil == 'administrador'"""
    u = _u(user)
    return autenticado(u) and getattr(u, 'perfil', None) == 'administrador'


def is_comercial_only(user=None):
    """Restricao especifica para usuarios so-comercial (template-side)."""
    u = _u(user)
    return autenticado(u) and bool(getattr(u, 'is_comercial_only', False))


# =============================================================================
# Sistemas (sistema_*)
# =============================================================================

def has_logistica(user=None):
    """sistema_logistica OR admin — exclui is_comercial_only."""
    u = _u(user)
    if not autenticado(u) or is_comercial_only(u):
        return False
    return bool(getattr(u, 'sistema_logistica', False)) or is_admin(u)


def has_carvia(user=None):
    """sistema_carvia"""
    u = _u(user)
    return autenticado(u) and bool(getattr(u, 'sistema_carvia', False))


def has_motochefe(user=None):
    """pode_acessar_motochefe()"""
    u = _u(user)
    return autenticado(u) and bool(_call(u, 'pode_acessar_motochefe'))


def has_lojas(user=None):
    """pode_acessar_lojas()"""
    u = _u(user)
    return autenticado(u) and bool(_call(u, 'pode_acessar_lojas'))


def has_motos_assai(user=None):
    """pode_acessar_motos_assai()"""
    u = _u(user)
    return autenticado(u) and bool(_call(u, 'pode_acessar_motos_assai'))


# =============================================================================
# Cadastros logistica (combinacoes de tem_permissao + helpers)
# =============================================================================

def cadastros_transportadoras(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'transportadoras', 'editar')
        or _call(u, 'pode_editar_cadastros')
        or is_admin(u)
    )


def cadastros_motoristas(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'portaria', 'motoristas')
        or _call(u, 'pode_editar_cadastros')
        or is_admin(u)
    )


def cadastros_localidades(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'localidades', 'editar')
        or _call(u, 'pode_editar_cadastros')
        or is_admin(u)
    )


def cadastros_veiculos(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'veiculos', 'administrar')
        or _call(u, 'pode_editar_cadastros')
        or is_admin(u)
    )


def cadastros_agendamento(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'agendamento', 'visualizar')
        or _call(u, 'pode_editar_cadastros')
        or is_admin(u)
    )


def cadastros_tabelas(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'tabelas')
        or _call(u, 'pode_acessar_financeiro')
        or is_admin(u)
    )


# =============================================================================
# Financeiro
# =============================================================================

def acessa_financeiro_geral(user=None):
    """Header do bloco Financeiro: qualquer perm financeira."""
    u = _u(user)
    if not autenticado(u) or is_comercial_only(u):
        return False
    return (
        _call(u, 'tem_permissao', 'fretes')
        or _call(u, 'tem_permissao', 'financeiro')
        or _call(u, 'tem_permissao', 'faturamento')
        or _call(u, 'pode_acessar_financeiro')
        or is_admin(u)
    )


def fretes_visualizar(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'fretes', 'visualizar')
        or _call(u, 'pode_acessar_financeiro')
        or is_admin(u)
    )


def fretes_lancar(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'fretes', 'lancar')
        or _call(u, 'pode_editar', 'fretes')
        or is_admin(u)
    )


def fretes_aprovar(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'fretes', 'aprovar')
        or getattr(u, 'perfil', None) in ('administrador', 'financeiro', 'gerente_comercial')
    )


def fretes_faturas(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'fretes', 'faturas')
        or _call(u, 'pode_acessar_financeiro')
        or is_admin(u)
    )


def financeiro_pendencias(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'financeiro', 'pendencias')
        or _call(u, 'pode_acessar_financeiro')
        or is_admin(u)
    )


def pode_acessar_financeiro(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return _call(u, 'pode_acessar_financeiro') or is_admin(u)


def pode_gerar_remessa_vortx(user=None):
    u = _u(user)
    return autenticado(u) and bool(_call(u, 'pode_gerar_remessa_vortx'))


# =============================================================================
# Comercial
# =============================================================================

def comercial(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'tem_permissao', 'comercial')
        or _call(u, 'tem_permissao', 'vendas')
        or getattr(u, 'perfil', None) in (
            'administrador', 'diretoria', 'gerente_comercial', 'vendedor'
        )
    )


def comercial_nao_vendedor(user=None):
    """Acesso comercial mas perfil diferente de 'vendedor'."""
    u = _u(user)
    return comercial(u) and getattr(u, 'perfil', None) != 'vendedor'


def comercial_admin_ou_gerente(user=None):
    u = _u(user)
    return autenticado(u) and getattr(u, 'perfil', None) in (
        'administrador', 'gerente_comercial'
    )


# =============================================================================
# Administracao
# =============================================================================

def admin_usuarios(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'pode_aprovar_usuarios')
        or _call(u, 'tem_permissao', 'usuarios')
        or _call(u, 'tem_permissao', 'admin')
    )


def admin_usuarios_aprovar(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        _call(u, 'pode_aprovar_usuarios')
        or _call(u, 'tem_permissao', 'usuarios', 'aprovar')
    )


def is_user_pessoal(user=None):
    """Restrito aos usuarios id 1 e 62."""
    u = _u(user)
    return autenticado(u) and getattr(u, 'id', None) in (1, 62)


def agente_nacom(user=None):
    """Acesso ao Agente Nacom."""
    u = _u(user)
    if not autenticado(u):
        return False
    return (
        bool(getattr(u, 'sistema_logistica', False))
        or bool(getattr(u, 'sistema_motochefe', False))
        or is_admin(u)
    )


def agente_lojas(user=None):
    u = _u(user)
    if not autenticado(u):
        return False
    return bool(getattr(u, 'sistema_lojas', False)) or is_admin(u)


# =============================================================================
# Lojas HORA — permissoes granulares (tem_perm_hora('chave', 'verbo'))
# =============================================================================

def hora_perm(chave: str, verbo: str = 'ver'):
    """Factory de checker para permissoes HORA granulares."""
    def _check(user=None):
        u = _u(user)
        if not autenticado(u):
            return False
        return _call(u, 'tem_perm_hora', chave, verbo)
    _check.__name__ = f'hora_{chave}_{verbo}'
    return _check


# =============================================================================
# Util interno
# =============================================================================

def _call(user, method_name: str, *args):
    """Chama metodo do user com seguranca (retorna False se nao existir)."""
    method = getattr(user, method_name, None)
    if not callable(method):
        return False
    try:
        return bool(method(*args))
    except Exception:
        return False
