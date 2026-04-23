"""
Regra de permissao cruzada por sistemas.

Ver spec secao 5: `sistemas(A) >= sistemas(B)` para A adicionar B
(admin bypass total). `>=` em set Python e issuperset (inclui igualdade).
"""
from typing import Set

DOMAIN_NACOM = 'NACOM'
DOMAIN_CARVIA = 'CARVIA'
DOMAIN_MOTOCHEFE = 'MOTOCHEFE'
DOMAIN_HORA = 'HORA'


def sistemas(user) -> Set[str]:
    """Conjunto de sistemas acessiveis pelo usuario."""
    s = {DOMAIN_NACOM}  # todo usuario logado tem Nacom
    if getattr(user, 'sistema_carvia', False):
        s.add(DOMAIN_CARVIA)
    if getattr(user, 'sistema_motochefe', False):
        s.add(DOMAIN_MOTOCHEFE)
    if getattr(user, 'loja_hora_id', None) is not None:
        s.add(DOMAIN_HORA)
    return s


def pode_adicionar(actor, target) -> bool:
    """actor pode iniciar DM com target / adicionar target a grupo."""
    if getattr(actor, 'perfil', None) == 'administrador':
        return True
    return sistemas(actor) >= sistemas(target)


def pode_ver_thread(user, thread) -> bool:
    """user pode ler mensagens desta thread (membro ativo ou admin)."""
    if getattr(user, 'perfil', None) == 'administrador':
        return True
    from app.chat.models import ChatMember
    return ChatMember.query.filter_by(
        thread_id=thread.id, user_id=user.id, removido_em=None,
    ).first() is not None


def usuarios_elegiveis_query(actor):
    """
    Queryset de Usuarios que actor pode adicionar.

    Admin: todos. Outros: usuarios com subset de flags.
    """
    from app.auth.models import Usuario

    q = Usuario.query.filter(Usuario.id != actor.id)
    if getattr(actor, 'perfil', None) == 'administrador':
        return q

    if not getattr(actor, 'sistema_carvia', False):
        q = q.filter(Usuario.sistema_carvia.is_(False))
    if not getattr(actor, 'sistema_motochefe', False):
        q = q.filter(Usuario.sistema_motochefe.is_(False))
    if getattr(actor, 'loja_hora_id', None) is None:
        q = q.filter(Usuario.loja_hora_id.is_(None))
    return q
