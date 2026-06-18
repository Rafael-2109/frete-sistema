"""CarviaPortalAuthService — registro/autenticacao/aprovacao do usuario externo do portal (stream 5).

Auto-registro (PENDENTE) -> aprovacao do admin (define escopo + ATIVO). Senha via werkzeug.
Service flush-only (compativel com fixture). Imports lazy (R2). NUNCA toca o Usuario interno.
"""

from app import db
from app.utils.timezone import agora_utc_naive


class PortalAuthError(Exception):
    """Erro de regra/validacao do portal (mensagem amigavel)."""


class CarviaPortalAuthService:

    # ------------------------------------------------------------ registro
    @staticmethod
    def registrar(*, nome, email, senha, telefone=None, grupo_empresa=None):
        from app.carvia.models.portal import CarviaPortalUsuario, PORTAL_STATUS_PENDENTE
        nome = (nome or '').strip()
        email = (email or '').strip().lower()
        if not nome or not email or not senha:
            raise PortalAuthError('Nome, email e senha sao obrigatorios.')
        if '@' not in email or '.' not in email:
            raise PortalAuthError('Email invalido.')
        if len(senha) < 6:
            raise PortalAuthError('Senha deve ter ao menos 6 caracteres.')
        if CarviaPortalUsuario.query.filter_by(email=email).first():
            raise PortalAuthError('Ja existe uma conta com esse email.')
        u = CarviaPortalUsuario(
            nome=nome, email=email, telefone=(telefone or '').strip() or None,
            grupo_empresa=(grupo_empresa or '').strip() or None,
            status=PORTAL_STATUS_PENDENTE, criado_em=agora_utc_naive())
        u.set_senha(senha)
        db.session.add(u)
        db.session.flush()
        return u

    # -------------------------------------------------------- autenticacao
    @staticmethod
    def autenticar(email, senha):
        """Retorna (usuario, None) se OK; (None, motivo) caso contrario. So ATIVO loga."""
        from app.carvia.models.portal import CarviaPortalUsuario, PORTAL_STATUS_ATIVO, PORTAL_STATUS_PENDENTE
        email = (email or '').strip().lower()
        u = CarviaPortalUsuario.query.filter_by(email=email).first()
        if u is None or not u.check_senha(senha):
            return None, 'Email ou senha invalidos.'
        if u.status == PORTAL_STATUS_PENDENTE:
            return None, 'Conta aguardando aprovacao do operador CarVia.'
        if u.status != PORTAL_STATUS_ATIVO:
            return None, 'Conta inativa. Contate a CarVia.'
        u.ultimo_login_em = agora_utc_naive()
        db.session.flush()
        return u, None

    # ----------------------------------------------------------- aprovacao
    @staticmethod
    def aprovar(usuario, *, operador, tipo_escopo, cnpjs=None, cliente_comercial_id=None):
        """Aprova a conta e define o escopo. Valida que o escopo nao fica vazio."""
        from app.carvia.models.portal import (
            CarviaPortalUsuario, PORTAL_STATUS_ATIVO,
            PORTAL_ESCOPO_CNPJ_DIRETO, PORTAL_ESCOPO_CLIENTE_COMERCIAL, PORTAL_ESCOPOS)
        if tipo_escopo not in PORTAL_ESCOPOS:
            raise PortalAuthError('Tipo de escopo invalido.')
        CarviaPortalAuthService.set_escopo(
            usuario, tipo_escopo=tipo_escopo, cnpjs=cnpjs, cliente_comercial_id=cliente_comercial_id)
        if not usuario.cnpjs_permitidos():
            raise PortalAuthError('Escopo vazio: informe ao menos 1 CNPJ ou um Cliente Comercial com CNPJs.')
        usuario.status = PORTAL_STATUS_ATIVO
        usuario.aprovado_por = operador
        usuario.aprovado_em = agora_utc_naive()
        db.session.flush()
        return usuario

    @staticmethod
    def set_escopo(usuario, *, tipo_escopo, cnpjs=None, cliente_comercial_id=None):
        from app.carvia.models.portal import (
            CarviaPortalUsuarioCnpj, PORTAL_ESCOPO_CNPJ_DIRETO, PORTAL_ESCOPO_CLIENTE_COMERCIAL)
        import re
        usuario.tipo_escopo = tipo_escopo
        if tipo_escopo == PORTAL_ESCOPO_CLIENTE_COMERCIAL:
            usuario.cliente_comercial_id = cliente_comercial_id
            # limpa lista direta (escopo vem do cliente comercial)
            for c in usuario.cnpjs.all():
                db.session.delete(c)
        else:  # CNPJ_DIRETO
            usuario.cliente_comercial_id = None
            existentes = {c.cnpj for c in usuario.cnpjs.all()}
            novos = set()
            for raw in (cnpjs or []):
                d = re.sub(r'\D', '', str(raw or ''))
                if len(d) == 14:
                    novos.add(d)
            # remove os que sairam
            for c in usuario.cnpjs.all():
                if re.sub(r'\D', '', c.cnpj) not in novos:
                    db.session.delete(c)
            # adiciona os novos
            existentes_norm = {re.sub(r'\D', '', e) for e in existentes}
            for d in novos:
                if d not in existentes_norm:
                    db.session.add(CarviaPortalUsuarioCnpj(portal_usuario_id=usuario.id, cnpj=d))
        db.session.flush()
        return usuario

    @staticmethod
    def rejeitar(usuario, operador=None):
        from app.carvia.models.portal import PORTAL_STATUS_REJEITADO
        usuario.status = PORTAL_STATUS_REJEITADO
        usuario.aprovado_por = operador
        usuario.aprovado_em = agora_utc_naive()
        db.session.flush()
        return usuario

    @staticmethod
    def definir_status(usuario, status):
        from app.carvia.models.portal import PORTAL_STATUSES
        if status not in PORTAL_STATUSES:
            raise PortalAuthError('Status invalido.')
        usuario.status = status
        db.session.flush()
        return usuario
