from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.timezone import agora_utc_naive

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    
    # Níveis de usuário conforme especificação
    perfil = db.Column(db.String(30), default='vendedor')  # portaria, vendedor, gerente_comercial, financeiro, logistica, administrador
    status = db.Column(db.String(20), default='pendente')  # pendente, ativo, rejeitado, bloqueado

    empresa = db.Column(db.String(100), nullable=True)  # Empresa do usuário
    cargo = db.Column(db.String(100), nullable=True)  # Cargo do usuário
    telefone = db.Column(db.String(20), nullable=True)  # Telefone para contato
    vendedor_vinculado = db.Column(db.String(100), nullable=True)  # Nome do vendedor no faturamento (para perfil vendedor)

    # Sistemas permitidos (novo - para separar logística de motochefe)
    sistema_logistica = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao sistema de logística
    sistema_motochefe = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao sistema motochefe
    
    # Dados de controle
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.String(120), nullable=True)  # Email do admin que aprovou
    ultimo_login = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)  # Observações do admin

    def set_senha(self, senha_plana):
        self.senha_hash = generate_password_hash(senha_plana)

    def verificar_senha(self, senha_plana):
        return check_password_hash(self.senha_hash, senha_plana)
    
    @property
    def is_approved(self):
        """Usuário só está aprovado se status == 'ativo'"""
        return self.status == 'ativo'
    
    # Flask-Login requer que is_active sempre retorne True
    # Usamos is_approved para verificar se o usuário foi aprovado
    
    def aprovar(self, admin_email, vendedor_vinculado=None):
        """Aprova o usuário"""
        self.status = 'ativo'
        self.aprovado_em = agora_utc_naive()
        self.aprovado_por = admin_email
        if vendedor_vinculado:
            self.vendedor_vinculado = vendedor_vinculado
    
    def rejeitar(self, motivo=None):
        """Rejeita o usuário"""
        self.status = 'rejeitado'
        if motivo:
            self.observacoes = motivo
    
    def bloquear(self, motivo=None):
        """Bloqueia o usuário"""
        self.status = 'bloqueado'
        if motivo:
            self.observacoes = motivo
    
    @property
    def status_badge_class(self):
        """Retorna a classe CSS para o badge de status"""
        classes = {
            'pendente': 'badge bg-warning',
            'ativo': 'badge bg-success', 
            'rejeitado': 'badge bg-danger',
            'bloqueado': 'badge bg-dark'
        }
        return classes.get(self.status, 'badge bg-secondary')
    
    @property
    def perfil_badge_class(self):
        """Retorna a classe CSS para o badge de perfil"""
        classes = {
            'administrador': 'badge bg-danger',
            'gerente_comercial': 'badge bg-primary',
            'financeiro': 'badge bg-success',
            'logistica': 'badge bg-info',
            'portaria': 'badge bg-warning text-dark',
            'vendedor': 'badge bg-secondary'
        }
        return classes.get(self.perfil, 'badge bg-light text-dark')
    
    @property
    def perfil_nome(self):
        """Retorna o nome amigável do perfil"""
        nomes = {
            'administrador': 'Administrador',
            'gerente_comercial': 'Gerente Comercial',
            'financeiro': 'Financeiro',
            'logistica': 'Logística',
            'portaria': 'Portaria',
            'vendedor': 'Vendedor'
        }
        return nomes.get(self.perfil, self.perfil.title())
    
    # Métodos de verificação de permissões
    def pode_aprovar_usuarios(self):
        """Verifica se pode aprovar usuários"""
        return self.perfil in ['administrador', 'gerente_comercial']
    
    def pode_acessar_financeiro(self):
        """Verifica se pode acessar módulos financeiros"""
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial']
    
    def pode_acessar_embarques(self):
        """Verifica se pode acessar embarques"""
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial', 'portaria']
    
    def pode_acessar_portaria(self):
        """Verifica se pode acessar módulos de portaria"""
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial', 'portaria']
    
    def pode_acessar_monitoramento_geral(self):
        """Verifica se pode acessar todo monitoramento"""
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial']
    
    def pode_acessar_monitoramento_vendedor(self):
        """Verifica se pode acessar monitoramento como vendedor"""
        return self.perfil == 'vendedor' and self.vendedor_vinculado
    
    def pode_editar_cadastros(self):
        """Verifica se pode editar cadastros"""
        return self.perfil in ['administrador', 'financeiro', 'logistica', 'gerente_comercial']

    # Métodos de verificação de acesso aos sistemas
    def pode_acessar_logistica(self):
        """Verifica se pode acessar o sistema de logística"""
        return self.sistema_logistica

    def pode_acessar_motochefe(self):
        """Verifica se pode acessar o sistema motochefe"""
        return self.sistema_motochefe

    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    # ====== METODOS DE PERMISSAO (VENDEDORES/EQUIPES) ======

    def get_vendedores_autorizados(self):
        """Retorna lista de vendedores autorizados para o usuário"""
        from app.permissions.models import UserVendedor
        return UserVendedor.get_vendedores_usuario(self.id)
    
    def get_equipes_autorizadas(self):
        """Retorna lista de equipes autorizadas para o usuário"""
        from app.permissions.models import UserEquipe
        return UserEquipe.get_equipes_usuario(self.id)
    
    # ====== MÉTODOS DE COMPATIBILIDADE (mantém funcionamento antigo) ======

    def tem_permissao(self, modulo, funcao=None, submodulo=None):
        """Verifica permissão usando sistema de perfis"""
        return self._tem_permissao_legacy(modulo)

    def pode_editar(self, modulo, funcao=None, submodulo=None):
        """Verifica se pode editar usando sistema de perfis"""
        return self._tem_permissao_legacy(modulo)

    def _tem_permissao_legacy(self, modulo):
        """Método de compatibilidade que usa o sistema antigo de perfis"""
        # Este método mantém a lógica antiga para garantir que nada quebre
        # enquanto migra-se gradualmente para o novo sistema
        if modulo == 'usuarios':
            return self.pode_aprovar_usuarios()
        elif modulo == 'financeiro':
            return self.pode_acessar_financeiro()
        elif modulo == 'embarques':
            return self.pode_acessar_embarques()
        elif modulo == 'portaria':
            return self.pode_acessar_portaria()
        elif modulo == 'monitoramento':
            return self.pode_acessar_monitoramento_geral() or self.pode_acessar_monitoramento_vendedor()
        return self.perfil == 'administrador'
