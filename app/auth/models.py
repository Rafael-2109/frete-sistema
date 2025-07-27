from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.orm import validates

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
    
    # Dados de controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    aprovado_em = db.Column(db.DateTime, nullable=True)
    aprovado_por = db.Column(db.String(120), nullable=True)  # Email do admin que aprovou
    ultimo_login = db.Column(db.DateTime, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)  # Observações do admin

    def set_senha(self, senha_plana):
        self.senha_hash = generate_password_hash(senha_plana)

    def verificar_senha(self, senha_plana):
        return check_password_hash(self.senha_hash, senha_plana)
    
    @property
    def is_active(self):
        """Usuário só está ativo se foi aprovado"""
        return self.status == 'ativo'
    
    def aprovar(self, admin_email, vendedor_vinculado=None):
        """Aprova o usuário"""
        self.status = 'ativo'
        self.aprovado_em = datetime.utcnow()
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

    def __repr__(self):
        return f'<Usuario {self.email}>'
    
    # ====== NOVOS MÉTODOS DE PERMISSÃO GRANULAR ======
    
    def tem_permissao(self, modulo, funcao=None, submodulo=None):
        """Verifica se usuário tem permissão para módulo/função"""
        # Administrador tem acesso total
        if self.perfil == 'administrador':
            return True
        
        # Importar modelos aqui para evitar importação circular
        from app.permissions.models import ModuloSistema, SubModule, FuncaoModulo, PermissaoUsuario
        
        # Buscar módulo
        modulo_obj = ModuloSistema.query.filter_by(nome=modulo, ativo=True).first()
        if not modulo_obj:
            return False
        
        # Se não especificou função, verificar se tem alguma permissão no módulo
        if not funcao:
            return PermissaoUsuario.query.join(FuncaoModulo).filter(
                PermissaoUsuario.usuario_id == self.id,
                PermissaoUsuario.ativo == True,
                PermissaoUsuario.pode_visualizar == True,
                FuncaoModulo.modulo_id == modulo_obj.id,
                FuncaoModulo.ativo == True
            ).first() is not None
        
        # Buscar função específica
        query = FuncaoModulo.query.filter_by(
            modulo_id=modulo_obj.id,
            nome=funcao,
            ativo=True
        )
        
        if submodulo:
            submodulo_obj = SubModule.query.filter_by(
                modulo_id=modulo_obj.id,
                nome=submodulo,
                ativo=True
            ).first()
            if submodulo_obj:
                query = query.filter_by(submodulo_id=submodulo_obj.id)
        
        funcao_obj = query.first()
        if not funcao_obj:
            return False
        
        # Verificar permissão
        permissao = PermissaoUsuario.query.filter_by(
            usuario_id=self.id,
            funcao_id=funcao_obj.id,
            ativo=True
        ).first()
        
        return permissao and permissao.pode_visualizar and not permissao.esta_expirada
    
    def pode_editar(self, modulo, funcao=None, submodulo=None):
        """Verifica se usuário pode editar no módulo/função"""
        # Administrador pode editar tudo
        if self.perfil == 'administrador':
            return True
        
        # Importar modelos aqui para evitar importação circular
        from app.permissions.models import ModuloSistema, SubModule, FuncaoModulo, PermissaoUsuario
        
        # Buscar módulo
        modulo_obj = ModuloSistema.query.filter_by(nome=modulo, ativo=True).first()
        if not modulo_obj:
            return False
        
        # Se não especificou função, verificar se pode editar em alguma função do módulo
        if not funcao:
            return PermissaoUsuario.query.join(FuncaoModulo).filter(
                PermissaoUsuario.usuario_id == self.id,
                PermissaoUsuario.ativo == True,
                PermissaoUsuario.pode_editar == True,
                FuncaoModulo.modulo_id == modulo_obj.id,
                FuncaoModulo.ativo == True
            ).first() is not None
        
        # Buscar função específica
        query = FuncaoModulo.query.filter_by(
            modulo_id=modulo_obj.id,
            nome=funcao,
            ativo=True
        )
        
        if submodulo:
            submodulo_obj = SubModule.query.filter_by(
                modulo_id=modulo_obj.id,
                nome=submodulo,
                ativo=True
            ).first()
            if submodulo_obj:
                query = query.filter_by(submodulo_id=submodulo_obj.id)
        
        funcao_obj = query.first()
        if not funcao_obj:
            return False
        
        # Verificar permissão
        permissao = PermissaoUsuario.query.filter_by(
            usuario_id=self.id,
            funcao_id=funcao_obj.id,
            ativo=True
        ).first()
        
        return permissao and permissao.pode_editar and not permissao.esta_expirada
    
    def get_modulos_permitidos(self):
        """Retorna lista de módulos que o usuário tem acesso"""
        from app.permissions.models import ModuloSistema, FuncaoModulo, PermissaoUsuario
        
        if self.perfil == 'administrador':
            return ModuloSistema.query.filter_by(ativo=True).order_by(ModuloSistema.ordem).all()
        
        # Buscar módulos através das permissões
        modulos_ids = db.session.query(FuncaoModulo.modulo_id).join(
            PermissaoUsuario
        ).filter(
            PermissaoUsuario.usuario_id == self.id,
            PermissaoUsuario.ativo == True,
            PermissaoUsuario.pode_visualizar == True,
            FuncaoModulo.ativo == True
        ).distinct().subquery()
        
        return ModuloSistema.query.filter(
            ModuloSistema.id.in_(modulos_ids),
            ModuloSistema.ativo == True
        ).order_by(ModuloSistema.ordem).all()
    
    def get_permissoes_modulo(self, modulo_nome):
        """Retorna todas as permissões do usuário em um módulo"""
        from app.permissions.models import ModuloSistema, FuncaoModulo, PermissaoUsuario
        
        modulo = ModuloSistema.query.filter_by(nome=modulo_nome, ativo=True).first()
        if not modulo:
            return []
        
        if self.perfil == 'administrador':
            # Admin tem todas as permissões
            funcoes = FuncaoModulo.query.filter_by(modulo_id=modulo.id, ativo=True).all()
            return [{
                'funcao': f.nome,
                'nome_exibicao': f.nome_exibicao,
                'pode_visualizar': True,
                'pode_editar': True
            } for f in funcoes]
        
        # Buscar permissões do usuário
        permissoes = PermissaoUsuario.query.join(FuncaoModulo).filter(
            PermissaoUsuario.usuario_id == self.id,
            PermissaoUsuario.ativo == True,
            FuncaoModulo.modulo_id == modulo.id,
            FuncaoModulo.ativo == True
        ).all()
        
        return [{
            'funcao': p.funcao.nome,
            'nome_exibicao': p.funcao.nome_exibicao,
            'pode_visualizar': p.pode_visualizar,
            'pode_editar': p.pode_editar
        } for p in permissoes if not p.esta_expirada]
    
    def aplicar_template_permissao(self, template_id, concedente_id=None):
        """Aplica um template de permissão ao usuário"""
        from app.permissions.models import PermissionTemplate
        
        template = PermissionTemplate.query.get(template_id)
        if not template or not template.ativo:
            return False
        
        return template.aplicar_para_usuario(self.id, concedente_id)
    
    def get_vendedores_autorizados(self):
        """Retorna lista de vendedores autorizados para o usuário"""
        from app.permissions.models import UsuarioVendedor
        return UsuarioVendedor.get_vendedores_usuario(self.id)
    
    def get_equipes_autorizadas(self):
        """Retorna lista de equipes autorizadas para o usuário"""
        from app.permissions.models import UsuarioEquipeVendas
        return UsuarioEquipeVendas.get_equipes_usuario(self.id)
    
    # ====== MÉTODOS DE COMPATIBILIDADE (mantém funcionamento antigo) ======
    
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
