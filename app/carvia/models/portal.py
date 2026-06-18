"""Portal do Cliente CarVia — usuario EXTERNO (stream 5 do redesign, .claire/rascunho.md topicos 3/8).

ISOLAMENTO DE SEGURANCA: `CarviaPortalUsuario` e uma entidade DEDICADA, totalmente separada do
`Usuario` interno (auth, perfis, sistemas). O portal tem login proprio (sessao em chave distinta)
e NUNCA reusa `current_user`/perfis internos — um cliente externo jamais ganha acesso interno.

Escopo de acesso (topico 8) — 2 modos, ambos resolvem para um CONJUNTO DE CNPJs destino:
- CNPJ_DIRETO (8A): lista explicita de CNPJs em `CarviaPortalUsuarioCnpj`.
- CLIENTE_COMERCIAL (8B): vinculado a um `CarviaCliente`; os CNPJs vem de `CarviaClienteEndereco`
  (tipo DESTINO, ativo) — a entidade que "ja possui cnpj vinculado".

O cliente so enxerga NFs cujo `cnpj_destinatario` esteja no conjunto permitido. Auto-registro cria
PENDENTE; o admin aprova e define o escopo.
"""

from app import db
from app.utils.timezone import agora_utc_naive
from werkzeug.security import generate_password_hash, check_password_hash

# Status da conta
PORTAL_STATUS_PENDENTE = 'PENDENTE'
PORTAL_STATUS_ATIVO = 'ATIVO'
PORTAL_STATUS_REJEITADO = 'REJEITADO'
PORTAL_STATUS_BLOQUEADO = 'BLOQUEADO'
PORTAL_STATUSES = (PORTAL_STATUS_PENDENTE, PORTAL_STATUS_ATIVO, PORTAL_STATUS_REJEITADO, PORTAL_STATUS_BLOQUEADO)

# Tipo de escopo
PORTAL_ESCOPO_CNPJ_DIRETO = 'CNPJ_DIRETO'         # 8A: cliente final, lista de CNPJs
PORTAL_ESCOPO_CLIENTE_COMERCIAL = 'CLIENTE_COMERCIAL'  # 8B: vendedor -> CarviaCliente
PORTAL_ESCOPOS = (PORTAL_ESCOPO_CNPJ_DIRETO, PORTAL_ESCOPO_CLIENTE_COMERCIAL)


def _so_digitos(cnpj):
    import re
    return re.sub(r'\D', '', str(cnpj or ''))


class CarviaPortalUsuario(db.Model):
    """Usuario EXTERNO do Portal do Cliente CarVia (isolado do Usuario interno)."""
    __tablename__ = 'carvia_portal_usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    telefone = db.Column(db.String(20))

    status = db.Column(
        db.String(20), nullable=False, default=PORTAL_STATUS_PENDENTE,
        server_default=PORTAL_STATUS_PENDENTE, index=True)

    # Escopo de acesso
    tipo_escopo = db.Column(
        db.String(20), nullable=False, default=PORTAL_ESCOPO_CNPJ_DIRETO,
        server_default=PORTAL_ESCOPO_CNPJ_DIRETO)
    cliente_comercial_id = db.Column(
        db.Integer, db.ForeignKey('carvia_clientes.id'), nullable=True, index=True)

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    aprovado_por = db.Column(db.String(150))   # email do operador interno
    aprovado_em = db.Column(db.DateTime)
    ultimo_login_em = db.Column(db.DateTime)

    cliente_comercial = db.relationship('CarviaCliente')
    cnpjs = db.relationship(
        'CarviaPortalUsuarioCnpj', backref='usuario', lazy='dynamic',
        cascade='all, delete-orphan')

    # ----- senha (werkzeug) -----
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha or '')

    @property
    def is_ativo(self):
        return self.status == PORTAL_STATUS_ATIVO

    # ----- escopo -----
    def cnpjs_permitidos(self):
        """Conjunto de CNPJs (so digitos) que este usuario pode enxergar. Vazio = nada."""
        if self.tipo_escopo == PORTAL_ESCOPO_CLIENTE_COMERCIAL and self.cliente_comercial_id:
            from app.carvia.models.clientes import CarviaClienteEndereco
            enderecos = CarviaClienteEndereco.query.filter_by(
                cliente_id=self.cliente_comercial_id, tipo='DESTINO', ativo=True).all()
            return {_so_digitos(e.cnpj) for e in enderecos if e.cnpj}
        # CNPJ_DIRETO
        return {_so_digitos(c.cnpj) for c in self.cnpjs if c.cnpj}

    def __repr__(self):
        return f'<CarviaPortalUsuario {self.email} ({self.status})>'


class CarviaPortalUsuarioCnpj(db.Model):
    """CNPJ destino autorizado para um usuario do portal (modo CNPJ_DIRETO, 8A)."""
    __tablename__ = 'carvia_portal_usuario_cnpjs'
    __table_args__ = (
        db.UniqueConstraint('portal_usuario_id', 'cnpj', name='uq_carvia_portal_usuario_cnpj'),
    )

    id = db.Column(db.Integer, primary_key=True)
    portal_usuario_id = db.Column(
        db.Integer, db.ForeignKey('carvia_portal_usuarios.id', ondelete='CASCADE'),
        nullable=False, index=True)
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    nome_referencia = db.Column(db.String(255))  # rotulo opcional (filial/loja)

    def __repr__(self):
        return f'<CarviaPortalUsuarioCnpj {self.cnpj}>'
