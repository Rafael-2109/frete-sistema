"""
Modelos para Sistema de Permissões Granular Avançado
====================================================

Sistema que permite:
- Múltiplos vendedores por usuário
- Múltiplas equipes de vendas por usuário  
- Permissões granulares por módulo/função
- Gestão centralizada de acessos
- Log de auditoria completo
"""

from app import db
from datetime import datetime
from app.utils.timezone import agora_brasil
from sqlalchemy import Index, UniqueConstraint
import logging
import json

logger = logging.getLogger(__name__)

# ============================================================================
# 1. PERFIS DE USUÁRIO (mais flexível que enum fixo)
# ============================================================================

class PerfilUsuario(db.Model):
    """
    Perfis flexíveis de usuário (substitui enum hardcoded)
    Permite criar novos perfis sem alteração de código
    """
    __tablename__ = 'perfil_usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)  # ex: "Gerente Regional"
    descricao = db.Column(db.String(255), nullable=True)
    nivel_hierarquico = db.Column(db.Integer, default=0)  # 0=mais baixo, 10=mais alto
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    usuarios = db.relationship('Usuario', backref='perfil_detalhado', lazy='select')
    
    def __repr__(self):
        return f'<PerfilUsuario {self.nome}>'
    
    @classmethod
    def get_or_create_default_profiles(cls):
        """Cria perfis padrão se não existirem"""
        perfis_padrao = [
            {'nome': 'administrador', 'descricao': 'Acesso total ao sistema', 'nivel_hierarquico': 10},
            {'nome': 'gerente_comercial', 'descricao': 'Gestão comercial e equipes', 'nivel_hierarquico': 8},
            {'nome': 'financeiro', 'descricao': 'Módulos financeiros e faturamento', 'nivel_hierarquico': 7},
            {'nome': 'logistica', 'descricao': 'Embarques, portaria e operações', 'nivel_hierarquico': 6},
            {'nome': 'portaria', 'descricao': 'Controle de portaria e veículos', 'nivel_hierarquico': 4},
            {'nome': 'vendedor', 'descricao': 'Acesso restrito a vendas próprias', 'nivel_hierarquico': 2},
        ]
        
        for perfil_data in perfis_padrao:
            if not cls.query.filter_by(nome=perfil_data['nome']).first():
                perfil = cls(**perfil_data)
                db.session.add(perfil)
        
        db.session.commit()

# ============================================================================
# 2. MÓDULOS DO SISTEMA  
# ============================================================================

class ModuloSistema(db.Model):
    """
    Módulos funcionais do sistema (faturamento, carteira, etc.)
    Base para organização hierárquica de permissões
    """
    __tablename__ = 'modulo_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)  # ex: "faturamento"
    nome_exibicao = db.Column(db.String(100), nullable=False)     # ex: "Faturamento"
    descricao = db.Column(db.String(255), nullable=True)
    icone = db.Column(db.String(50), default='📊')  # Emoji ou classe CSS
    cor = db.Column(db.String(7), default='#007bff')  # Cor hex para interface
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)  # Para ordenação na interface
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    
    # Relacionamentos
    funcoes = db.relationship('FuncaoModulo', backref='modulo', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<ModuloSistema {self.nome}>'
    
    @classmethod
    def get_or_create_default_modules(cls):
        """Cria módulos padrão se não existirem"""
        modulos_padrao = [
            {'nome': 'faturamento', 'nome_exibicao': 'Faturamento', 'icone': '💰', 'cor': '#28a745', 'ordem': 1},
            {'nome': 'carteira', 'nome_exibicao': 'Carteira de Pedidos', 'icone': '📋', 'cor': '#007bff', 'ordem': 2},
            {'nome': 'monitoramento', 'nome_exibicao': 'Monitoramento', 'icone': '📊', 'cor': '#17a2b8', 'ordem': 3},
            {'nome': 'embarques', 'nome_exibicao': 'Embarques', 'icone': '🚛', 'cor': '#fd7e14', 'ordem': 4},
            {'nome': 'portaria', 'nome_exibicao': 'Portaria', 'icone': '🚪', 'cor': '#6c757d', 'ordem': 5},
            {'nome': 'financeiro', 'nome_exibicao': 'Financeiro', 'icone': '💳', 'cor': '#dc3545', 'ordem': 6},
            {'nome': 'usuarios', 'nome_exibicao': 'Gestão de Usuários', 'icone': '👥', 'cor': '#6f42c1', 'ordem': 7},
            {'nome': 'admin', 'nome_exibicao': 'Administração', 'icone': '⚙️', 'cor': '#343a40', 'ordem': 8},
        ]
        
        for modulo_data in modulos_padrao:
            if not cls.query.filter_by(nome=modulo_data['nome']).first():
                modulo = cls(**modulo_data)
                db.session.add(modulo)
        
        db.session.commit()

# ============================================================================
# 3. FUNÇÕES DENTRO DOS MÓDULOS
# ============================================================================

class FuncaoModulo(db.Model):
    """
    Funções específicas dentro de cada módulo
    Nível mais granular de controle de permissões
    """
    __tablename__ = 'funcao_modulo'
    
    id = db.Column(db.Integer, primary_key=True)
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulo_sistema.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)  # ex: "listar_faturas"
    nome_exibicao = db.Column(db.String(100), nullable=False)  # ex: "Listar Faturas"
    descricao = db.Column(db.String(255), nullable=True)
    rota_padrao = db.Column(db.String(200), nullable=True)  # ex: "/faturamento/listar"
    nivel_critico = db.Column(db.String(10), default='NORMAL')  # BAIXO, NORMAL, ALTO, CRITICO
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    
    # Relacionamentos
    permissoes = db.relationship('PermissaoUsuario', backref='funcao', lazy='dynamic', cascade='all, delete-orphan')
    logs = db.relationship('LogPermissao', backref='funcao', lazy='dynamic')
    
    # Índices
    __table_args__ = (
        UniqueConstraint('modulo_id', 'nome', name='uq_funcao_modulo_nome'),
        Index('idx_funcao_modulo_ativo', 'modulo_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<FuncaoModulo {self.modulo.nome}.{self.nome}>'
    
    @property
    def nome_completo(self):
        """Retorna nome completo módulo.função"""
        return f"{self.modulo.nome}.{self.nome}"
    
    @classmethod
    def get_or_create_default_functions(cls):
        """Cria funções padrão para cada módulo"""
        # Não precisa importar ModuloSistema, já está no mesmo arquivo
        
        # Mapear funções por módulo
        funcoes_padrao = {
            'faturamento': [
                {'nome': 'listar', 'nome_exibicao': 'Listar Faturas', 'rota_padrao': '/faturamento/listar'},
                {'nome': 'visualizar', 'nome_exibicao': 'Visualizar Fatura', 'rota_padrao': '/faturamento/visualizar'},
                {'nome': 'editar', 'nome_exibicao': 'Editar Fatura', 'nivel_critico': 'ALTO'},
                {'nome': 'importar', 'nome_exibicao': 'Importar Dados', 'nivel_critico': 'CRITICO'},
                {'nome': 'exportar', 'nome_exibicao': 'Exportar Relatórios'},
            ],
            'carteira': [
                {'nome': 'listar', 'nome_exibicao': 'Listar Pedidos', 'rota_padrao': '/carteira/listar'},
                {'nome': 'visualizar', 'nome_exibicao': 'Visualizar Pedido'},
                {'nome': 'gerar_separacao', 'nome_exibicao': 'Gerar Separação', 'nivel_critico': 'ALTO'},
                {'nome': 'baixar_faturamento', 'nome_exibicao': 'Baixar Faturamento', 'nivel_critico': 'ALTO'},
                {'nome': 'configurar_carga', 'nome_exibicao': 'Configurar Tipo Carga'},
            ],
            'monitoramento': [
                {'nome': 'listar', 'nome_exibicao': 'Listar Entregas', 'rota_padrao': '/monitoramento/listar'},
                {'nome': 'visualizar', 'nome_exibicao': 'Visualizar Entrega'},
                {'nome': 'agendar', 'nome_exibicao': 'Agendar Entrega'},
                {'nome': 'upload_canhotos', 'nome_exibicao': 'Upload Canhotos'},
                {'nome': 'pendencias_financeiras', 'nome_exibicao': 'Pendências Financeiras'},
            ],
            'embarques': [
                {'nome': 'listar', 'nome_exibicao': 'Listar Embarques', 'rota_padrao': '/embarques/listar'},
                {'nome': 'criar', 'nome_exibicao': 'Criar Embarque', 'nivel_critico': 'ALTO'},
                {'nome': 'editar', 'nome_exibicao': 'Editar Embarque', 'nivel_critico': 'ALTO'},
                {'nome': 'finalizar', 'nome_exibicao': 'Finalizar Embarque', 'nivel_critico': 'CRITICO'},
            ],
            'portaria': [
                {'nome': 'dashboard', 'nome_exibicao': 'Dashboard Portaria', 'rota_padrao': '/portaria/dashboard'},
                {'nome': 'registrar_movimento', 'nome_exibicao': 'Registrar Movimento'},
                {'nome': 'historico', 'nome_exibicao': 'Histórico Portaria'},
            ],
            'financeiro': [
                {'nome': 'lancamento_freteiros', 'nome_exibicao': 'Lançamento Freteiros', 'nivel_critico': 'CRITICO'},
                {'nome': 'aprovar_faturas', 'nome_exibicao': 'Aprovar Faturas', 'nivel_critico': 'CRITICO'},
                {'nome': 'relatorios', 'nome_exibicao': 'Relatórios Financeiros'},
            ],
            'usuarios': [
                {'nome': 'listar', 'nome_exibicao': 'Listar Usuários'},
                {'nome': 'aprovar', 'nome_exibicao': 'Aprovar Usuários', 'nivel_critico': 'CRITICO'},
                {'nome': 'editar', 'nome_exibicao': 'Editar Usuários', 'nivel_critico': 'ALTO'},
                {'nome': 'permissoes', 'nome_exibicao': 'Gerenciar Permissões', 'nivel_critico': 'CRITICO'},
            ],
            'admin': [
                {'nome': 'acesso_total', 'nome_exibicao': 'Acesso Total Sistema', 'nivel_critico': 'CRITICO'},
                {'nome': 'configuracoes', 'nome_exibicao': 'Configurações Sistema', 'nivel_critico': 'CRITICO'},
                {'nome': 'logs', 'nome_exibicao': 'Logs do Sistema'},
            ],
        }
        
        for nome_modulo, funcoes in funcoes_padrao.items():
            modulo = ModuloSistema.query.filter_by(nome=nome_modulo).first()
            if not modulo:
                continue
                
            for i, funcao_data in enumerate(funcoes):
                funcao_data['modulo_id'] = modulo.id
                funcao_data['ordem'] = i + 1
                
                if not cls.query.filter_by(modulo_id=modulo.id, nome=funcao_data['nome']).first():
                    funcao = cls(**funcao_data)
                    db.session.add(funcao)
        
        db.session.commit()

# ============================================================================
# 4. PERMISSÕES GRANULARES
# ============================================================================

class PermissaoUsuario(db.Model):
    """
    Permissões específicas por usuário/função
    Controle granular de visualizar/editar
    """
    __tablename__ = 'permissao_usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_modulo.id'), nullable=False)
    pode_visualizar = db.Column(db.Boolean, default=False, nullable=False)
    pode_editar = db.Column(db.Boolean, default=False, nullable=False)
    concedida_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    concedida_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    expira_em = db.Column(db.DateTime, nullable=True)  # Permissão temporária
    observacoes = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='permissoes_detalhadas')
    concedente = db.relationship('Usuario', foreign_keys=[concedida_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('usuario_id', 'funcao_id', name='uq_permissao_usuario_funcao'),
        Index('idx_permissao_usuario_ativo', 'usuario_id', 'ativo'),
        Index('idx_permissao_funcao_ativo', 'funcao_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<PermissaoUsuario {self.usuario.nome} -> {self.funcao.nome_completo}>'
    
    
    @property
    def esta_expirada(self):
        """Verifica se permissão está expirada"""
        if not self.expira_em:
            return False
        return agora_brasil() > self.expira_em    
    @property
    def nivel_acesso(self):
        """Retorna nível de acesso como string"""
        if self.pode_editar:
            return 'Editar'
        elif self.pode_visualizar:
            return 'Visualizar'
        else:
            return 'Sem Acesso'
    @property
    def to_dict(self):
        """Serializa para JSON"""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'funcao_id': self.funcao_id,
            'modulo': self.funcao.modulo.nome,
            'funcao': self.funcao.nome,
            'pode_visualizar': self.pode_visualizar,
            'pode_editar': self.pode_editar,
            'nivel_acesso': self.nivel_acesso,
            'concedida_em': self.concedida_em.isoformat(),
            'expira_em': self.expira_em.isoformat() if self.expira_em else None,
            'esta_expirada': self.esta_expirada,
            'ativo': self.ativo
        }

# ============================================================================
# 5. VENDEDORES E EQUIPES (ENTIDADES)
# ============================================================================

class Vendedor(db.Model):
    """
    Cadastro de vendedores do sistema
    """
    __tablename__ = 'vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)  # Código único do vendedor
    nome = db.Column(db.String(100), nullable=False)
    razao_social = db.Column(db.String(200), nullable=True)
    cnpj_cpf = db.Column(db.String(18), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    telefone = db.Column(db.String(20), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    usuarios = db.relationship('UsuarioVendedor', backref='vendedor_obj', lazy='dynamic')
    permissoes = db.relationship('PermissaoVendedor', backref='vendedor_obj', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Vendedor {self.codigo} - {self.nome}>'

class EquipeVendas(db.Model):
    """
    Cadastro de equipes de vendas
    """
    __tablename__ = 'equipe_vendas'
    
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)  # Código único da equipe
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    gerente_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relacionamentos
    gerente = db.relationship('Usuario', foreign_keys=[gerente_id], backref='equipes_gerenciadas')
    usuarios = db.relationship('UsuarioEquipeVendas', backref='equipe_obj', lazy='dynamic')
    permissoes = db.relationship('PermissaoEquipe', backref='equipe_obj', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EquipeVendas {self.codigo} - {self.nome}>'

# ============================================================================
# 6. MÚLTIPLOS VENDEDORES POR USUÁRIO
# ============================================================================

class UsuarioVendedor(db.Model):
    """
    Relacionamento N:N entre usuários e vendedores
    Permite que um usuário tenha acesso a múltiplos vendedores
    """
    __tablename__ = 'usuario_vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'), nullable=False)
    tipo_acesso = db.Column(db.String(20), default='visualizar')  # visualizar, editar, total
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    observacoes = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='vendedores_associados')
    adicionado_por_user = db.relationship('Usuario', foreign_keys=[adicionado_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('usuario_id', 'vendedor_id', name='uq_usuario_vendedor'),
        Index('idx_usuario_vendedor_ativo', 'usuario_id', 'ativo'),
        Index('idx_vendedor_lookup', 'vendedor_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<UsuarioVendedor {self.usuario.nome} -> {self.vendedor_obj.nome}>'
    
    @classmethod
    def get_vendedores_usuario(cls, usuario_id):
        """Retorna lista de vendedores autorizados para o usuário"""
        return [uv.vendedor_obj for uv in cls.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).join(Vendedor).filter(Vendedor.ativo == True).all()]
    
    @classmethod
    def usuario_tem_vendedor(cls, usuario_id, vendedor_id):
        """Verifica se usuário tem acesso a vendedor específico"""
        return cls.query.filter_by(
            usuario_id=usuario_id, 
            vendedor_id=vendedor_id, 
            ativo=True
        ).first() is not None

# ============================================================================
# 7. MÚLTIPLAS EQUIPES DE VENDAS POR USUÁRIO
# ============================================================================

class UsuarioEquipeVendas(db.Model):
    """
    Relacionamento N:N entre usuários e equipes de vendas
    Permite que um usuário tenha acesso a múltiplas equipes
    """
    __tablename__ = 'usuario_equipe_vendas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    equipe_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas.id'), nullable=False)
    cargo_equipe = db.Column(db.String(50), nullable=True)  # Cargo do usuário na equipe
    tipo_acesso = db.Column(db.String(20), default='membro')  # membro, supervisor, gerente
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    observacoes = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='equipes_associadas')
    adicionado_por_user = db.relationship('Usuario', foreign_keys=[adicionado_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('usuario_id', 'equipe_id', name='uq_usuario_equipe'),
        Index('idx_usuario_equipe_ativo', 'usuario_id', 'ativo'),
        Index('idx_equipe_lookup', 'equipe_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<UsuarioEquipeVendas {self.usuario.nome} -> {self.equipe_obj.nome}>'
    
    @classmethod
    def get_equipes_usuario(cls, usuario_id):
        """Retorna lista de equipes autorizadas para o usuário"""
        return [ue.equipe_obj for ue in cls.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).join(EquipeVendas).filter(EquipeVendas.ativo == True).all()]
    
    @classmethod
    def usuario_tem_equipe(cls, usuario_id, equipe_id):
        """Verifica se usuário tem acesso a equipe específica"""
        return cls.query.filter_by(
            usuario_id=usuario_id, 
            equipe_id=equipe_id, 
            ativo=True
        ).first() is not None

# ============================================================================
# 8. PERMISSÕES POR VENDEDOR E EQUIPE
# ============================================================================

class PermissaoVendedor(db.Model):
    """
    Permissões atribuídas a nível de vendedor
    Todos os usuários do vendedor herdam essas permissões
    """
    __tablename__ = 'permissao_vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedor.id'), nullable=False)
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_modulo.id'), nullable=False)
    pode_visualizar = db.Column(db.Boolean, default=False, nullable=False)
    pode_editar = db.Column(db.Boolean, default=False, nullable=False)
    concedida_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    concedida_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    funcao = db.relationship('FuncaoModulo', backref='permissoes_vendedor')
    concedente = db.relationship('Usuario')
    
    # Índices
    __table_args__ = (
        UniqueConstraint('vendedor_id', 'funcao_id', name='uq_permissao_vendedor_funcao'),
        Index('idx_permissao_vendedor_ativo', 'vendedor_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<PermissaoVendedor {self.vendedor_obj.nome} -> {self.funcao.nome_completo}>'

class PermissaoEquipe(db.Model):
    """
    Permissões atribuídas a nível de equipe
    Todos os usuários da equipe herdam essas permissões
    """
    __tablename__ = 'permissao_equipe'
    
    id = db.Column(db.Integer, primary_key=True)
    equipe_id = db.Column(db.Integer, db.ForeignKey('equipe_vendas.id'), nullable=False)
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_modulo.id'), nullable=False)
    pode_visualizar = db.Column(db.Boolean, default=False, nullable=False)
    pode_editar = db.Column(db.Boolean, default=False, nullable=False)
    concedida_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    concedida_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relacionamentos
    funcao = db.relationship('FuncaoModulo', backref='permissoes_equipe')
    concedente = db.relationship('Usuario')
    
    # Índices
    __table_args__ = (
        UniqueConstraint('equipe_id', 'funcao_id', name='uq_permissao_equipe_funcao'),
        Index('idx_permissao_equipe_ativo', 'equipe_id', 'ativo'),
    )
    
    def __repr__(self):
        return f'<PermissaoEquipe {self.equipe_obj.nome} -> {self.funcao.nome_completo}>'

# ============================================================================
# 9. LOG DE AUDITORIA
# ============================================================================

class LogPermissao(db.Model):
    """
    Log completo de auditoria para permissões
    Rastreia todas as ações relacionadas a permissões
    """
    __tablename__ = 'log_permissao'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    acao = db.Column(db.String(50), nullable=False)  # CONCEDIDA, REVOGADA, USADA, LOGIN, TENTATIVA_NEGADA
    funcao_id = db.Column(db.Integer, db.ForeignKey('funcao_modulo.id'), nullable=True)
    detalhes = db.Column(db.Text, nullable=True)  # JSON com detalhes da ação
    resultado = db.Column(db.String(20), default='SUCESSO')  # SUCESSO, NEGADO, ERRO
    ip_origem = db.Column(db.String(45), nullable=True)  # IPv4 ou IPv6
    user_agent = db.Column(db.String(255), nullable=True)
    sessao_id = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', backref='logs_permissao')
    
    # Índices
    __table_args__ = (
        Index('idx_log_usuario_timestamp', 'usuario_id', 'timestamp'),
        Index('idx_log_acao_timestamp', 'acao', 'timestamp'),
        Index('idx_log_funcao_timestamp', 'funcao_id', 'timestamp'),
        Index('idx_log_resultado', 'resultado', 'timestamp'),
    )
    
    def __repr__(self):
        return f'<LogPermissao {self.acao} - {self.usuario.nome if self.usuario else "N/A"}>'
    
    @classmethod
    def registrar(cls, usuario_id, acao, funcao_id=None, detalhes=None, 
                  resultado='SUCESSO', ip_origem=None, user_agent=None, sessao_id=None):
        """Registra uma ação no log de auditoria"""
        try:
            log = cls(
                usuario_id=usuario_id,
                acao=acao,
                funcao_id=funcao_id,
                detalhes=detalhes,
                resultado=resultado,
                ip_origem=ip_origem,
                user_agent=user_agent,
                sessao_id=sessao_id
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            logger.error(f"Erro ao registrar log de permissão: {e}")
            db.session.rollback()
            return None
    
    @classmethod
    def buscar_atividade_usuario(cls, usuario_id, limite=50):
        """Busca atividades recentes de um usuário"""
        return cls.query.filter_by(usuario_id=usuario_id)\
                       .order_by(cls.timestamp.desc())\
                       .limit(limite).all()
    
    @classmethod
    def buscar_tentativas_negadas(cls, dias=30, limite=100):
        """Busca tentativas de acesso negadas"""
        from datetime import datetime, timedelta
        data_inicio = datetime.now() - timedelta(days=dias)
        
        return cls.query.filter(
            cls.resultado == 'NEGADO',
            cls.timestamp >= data_inicio
        ).order_by(cls.timestamp.desc()).limit(limite).all()

# ============================================================================
# 10. FUNÇÕES AUXILIARES PARA INICIALIZAÇÃO
# ============================================================================

def inicializar_dados_padrao():
    """
    Inicializa dados padrão do sistema de permissões
    Deve ser chamado após as migrações de banco
    """
    try:
        logger.info("Inicializando dados padrão do sistema de permissões...")
        
        # 1. Criar perfis padrão
        PerfilUsuario.get_or_create_default_profiles()
        logger.info("✅ Perfis padrão criados")
        
        # 2. Criar módulos padrão  
        ModuloSistema.get_or_create_default_modules()
        logger.info("✅ Módulos padrão criados")
        
        # 3. Criar funções padrão
        FuncaoModulo.get_or_create_default_functions()
        logger.info("✅ Funções padrão criadas")
        
        logger.info("🎉 Inicialização do sistema de permissões concluída com sucesso!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        db.session.rollback()
        return False

# ============================================================================
# 11. LEGACY SUBMODULE MODEL (for compatibility)
# ============================================================================

class SubModule(db.Model):
    """
    Legacy SubModule model for backward compatibility
    Maps to PermissionSubModule in new system
    """
    __tablename__ = 'submodule'
    
    id = db.Column(db.Integer, primary_key=True)
    modulo_id = db.Column(db.Integer, db.ForeignKey('modulo_sistema.id'), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    nome_exibicao = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    
    # This is a compatibility model that maps to PermissionSubModule
    def __repr__(self):
        return f'<SubModule {self.nome}>'

# ============================================================================
# 12. HIERARCHICAL PERMISSION MODELS (NEW)
# ============================================================================

class PermissionCategory(db.Model):
    """
    Permission categories (highest level)
    Groups related modules together
    """
    __tablename__ = 'permission_category'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)  # Changed from 'name' to 'nome'
    nome_exibicao = db.Column(db.String(100), nullable=False)     # Changed from 'display_name' to 'nome_exibicao'
    descricao = db.Column(db.String(255), nullable=True)          # Changed from 'description' to 'descricao'
    icone = db.Column(db.String(50), default='folder')            # Changed from 'icon' to 'icone'
    cor = db.Column(db.String(7), default='#007bff')              # Changed from 'color' to 'cor'
    ordem = db.Column(db.Integer, default=0)                      # Changed from 'order_index' to 'ordem'
    ativo = db.Column(db.Boolean, default=True, nullable=False)   # Changed from 'active' to 'ativo'
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)  # Changed from 'created_at' to 'criado_em'
    criado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)  # Changed from 'created_by' to 'criado_por'
    
    # Relationships
    modules = db.relationship('PermissionModule', backref='category', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PermissionCategory {self.nome}>'

class PermissionModule(db.Model):
    """
    Permission modules within categories
    """
    __tablename__ = 'permission_module'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('permission_category.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    icon = db.Column(db.String(50), default='file')
    color = db.Column(db.String(7), default='#6c757d')
    order_index = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Relationships
    submodules = db.relationship('PermissionSubModule', backref='module', lazy='dynamic', cascade='all, delete-orphan')
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('category_id', 'name', name='uq_module_category_name'),
        Index('idx_module_category', 'category_id', 'active'),
    )
    
    def __repr__(self):
        return f'<PermissionModule {self.category.name}.{self.name}>'

class PermissionSubModule(db.Model):
    """
    Permission submodules (most granular level)
    """
    __tablename__ = 'permission_submodule'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('permission_module.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    route_pattern = db.Column(db.String(200), nullable=True)
    critical_level = db.Column(db.String(10), default='NORMAL')  # LOW, NORMAL, HIGH, CRITICAL
    order_index = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('module_id', 'name', name='uq_submodule_module_name'),
        Index('idx_submodule_module', 'module_id', 'active'),
    )
    
    def __repr__(self):
        return f'<PermissionSubModule {self.module.name}.{self.name}>'

class UserPermission(db.Model):
    """
    User permissions for hierarchical entities
    """
    __tablename__ = 'user_permission'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)  # CATEGORY, MODULE, SUBMODULE
    entity_id = db.Column(db.Integer, nullable=False)
    can_view = db.Column(db.Boolean, default=False, nullable=False)
    can_edit = db.Column(db.Boolean, default=False, nullable=False)
    can_delete = db.Column(db.Boolean, default=False, nullable=False)
    can_export = db.Column(db.Boolean, default=False, nullable=False)
    custom_override = db.Column(db.Boolean, default=False, nullable=False)
    granted_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    user = db.relationship('Usuario', foreign_keys=[user_id], backref='hierarchical_permissions')
    granted_by_user = db.relationship('Usuario', foreign_keys=[granted_by])
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'entity_type', 'entity_id', name='uq_user_entity_permission'),
        Index('idx_user_permission_active', 'user_id', 'active'),
        Index('idx_entity_permission', 'entity_type', 'entity_id', 'active'),
    )
    
    def __repr__(self):
        return f'<UserPermission {self.user_id} -> {self.entity_type}:{self.entity_id}>'
    
    @property
    def is_expired(self):
        """Check if permission is expired"""
        if not self.expires_at:
            return False
        return agora_brasil() > self.expires_at

class PermissionTemplate(db.Model):
    """
    Permission templates for easy assignment
    """
    __tablename__ = 'permission_template'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(50), default='custom')  # roles, departments, custom
    template_data = db.Column(db.Text, nullable=False)  # JSON with permissions
    is_system = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    updated_at = db.Column(db.DateTime, onupdate=agora_brasil)
    
    def __repr__(self):
        return f'<PermissionTemplate {self.name}>'
    
    def get_permissions(self):
        """Get parsed permissions from template"""
        import json
        try:
            return json.loads(self.template_data)
        except:
            return {}

class BatchPermissionOperation(db.Model):
    """
    Track batch permission operations for audit and rollback
    """
    __tablename__ = 'batch_permission_operation'
    
    id = db.Column(db.Integer, primary_key=True)
    operation_type = db.Column(db.String(20), nullable=False)  # GRANT, REVOKE, COPY, UPDATE, MIGRATION
    description = db.Column(db.String(255), nullable=True)
    executed_by = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='PENDING')  # PENDING, IN_PROGRESS, COMPLETED, COMPLETED_WITH_ERRORS, FAILED
    affected_users = db.Column(db.Integer, default=0)
    affected_permissions = db.Column(db.Integer, default=0)
    details = db.Column(db.JSON, nullable=True)  # JSON with operation details
    error_details = db.Column(db.Text, nullable=True)
    
    # Relationships
    executor = db.relationship('Usuario', backref='batch_operations_executed')
    
    def __repr__(self):
        return f'<BatchPermissionOperation {self.operation_type} - {self.status}>'


class PermissionCache(db.Model):
    """
    Database-backed cache for permission lookups
    """
    __tablename__ = 'permission_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    cache_key = db.Column(db.String(255), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    permission_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_user', 'user_id'),
        Index('idx_cache_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f'<PermissionCache {self.cache_key}>'


def criar_templates_padrao():
    """Cria templates de permissão padrão para cada perfil"""
    templates_config = {
        'vendedor': {
            'nome': 'Template Vendedor',
            'descricao': 'Permissões padrão para vendedores',
            'permissions': {
                'carteira': {
                    'listar': 'visualizar',
                    'visualizar': 'visualizar'
                },
                'monitoramento': {
                    'listar': 'visualizar',
                    'visualizar': 'visualizar'
                }
            }
        },
        'gerente_comercial': {
            'nome': 'Template Gerente Comercial',
            'descricao': 'Permissões padrão para gerentes comerciais',
            'permissions': {
                'faturamento': {
                    'listar': 'editar',
                    'visualizar': 'editar',
                    'editar': 'editar',
                    'exportar': 'editar'
                },
                'carteira': {
                    'listar': 'editar',
                    'visualizar': 'editar',
                    'gerar_separacao': 'editar',
                    'baixar_faturamento': 'editar'
                },
                'monitoramento': {
                    'listar': 'editar',
                    'visualizar': 'editar',
                    'agendar': 'editar'
                },
                'usuarios': {
                    'listar': 'visualizar',
                    'aprovar': 'editar'
                }
            }
        },
        'financeiro': {
            'nome': 'Template Financeiro',
            'descricao': 'Permissões padrão para equipe financeira',
            'permissions': {
                'faturamento': {
                    'listar': 'editar',
                    'visualizar': 'editar',
                    'editar': 'editar',
                    'importar': 'editar',
                    'exportar': 'editar'
                },
                'financeiro': {
                    'lancamento_freteiros': 'editar',
                    'aprovar_faturas': 'editar',
                    'relatorios': 'editar'
                },
                'monitoramento': {
                    'pendencias_financeiras': 'editar'
                }
            }
        },
        'logistica': {
            'nome': 'Template Logística',
            'descricao': 'Permissões padrão para equipe de logística',
            'permissions': {
                'embarques': {
                    'listar': 'editar',
                    'criar': 'editar',
                    'editar': 'editar',
                    'finalizar': 'editar'
                },
                'portaria': {
                    'dashboard': 'editar',
                    'registrar_movimento': 'editar',
                    'historico': 'visualizar'
                },
                'monitoramento': {
                    'listar': 'editar',
                    'visualizar': 'editar',
                    'upload_canhotos': 'editar'
                }
            }
        },
        'portaria': {
            'nome': 'Template Portaria',
            'descricao': 'Permissões padrão para equipe de portaria',
            'permissions': {
                'portaria': {
                    'dashboard': 'visualizar',
                    'registrar_movimento': 'editar',
                    'historico': 'visualizar'
                },
                'embarques': {
                    'listar': 'visualizar',
                    'visualizar': 'visualizar'
                }
            }
        }
    }
    
    for perfil_nome, config in templates_config.items():
        # Buscar perfil
        perfil = PerfilUsuario.query.filter_by(nome=perfil_nome).first()
        if not perfil:
            continue
        
        # Verificar se template já existe
        if PermissionTemplate.query.filter_by(nome=config['nome']).first():
            continue
        
        # Criar template
        template = PermissionTemplate(
            nome=config['nome'],
            descricao=config['descricao'],
            perfil_id=perfil.id,
            permissions_json=json.dumps(config['permissions'])
        )
        db.session.add(template)
    
    db.session.commit() 