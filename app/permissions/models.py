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
        from . import ModuloSistema
        
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
# 5. MÚLTIPLOS VENDEDORES POR USUÁRIO
# ============================================================================

class UsuarioVendedor(db.Model):
    """
    Relacionamento N:N entre usuários e vendedores
    Permite que um usuário tenha acesso a múltiplos vendedores
    """
    __tablename__ = 'usuario_vendedor'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    vendedor = db.Column(db.String(100), nullable=False)  # Nome do vendedor
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    observacoes = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='vendedores_autorizados')
    adicionado_por_user = db.relationship('Usuario', foreign_keys=[adicionado_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('usuario_id', 'vendedor', name='uq_usuario_vendedor'),
        Index('idx_usuario_vendedor_ativo', 'usuario_id', 'ativo'),
        Index('idx_vendedor_lookup', 'vendedor', 'ativo'),
    )
    
    def __repr__(self):
        return f'<UsuarioVendedor {self.usuario.nome} -> {self.vendedor}>'
    
    @classmethod
    def get_vendedores_usuario(cls, usuario_id):
        """Retorna lista de vendedores autorizados para o usuário"""
        return [uv.vendedor for uv in cls.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).all()]
    
    @classmethod
    def usuario_tem_vendedor(cls, usuario_id, vendedor):
        """Verifica se usuário tem acesso a vendedor específico"""
        return cls.query.filter_by(
            usuario_id=usuario_id, 
            vendedor=vendedor, 
            ativo=True
        ).first() is not None

# ============================================================================
# 6. MÚLTIPLAS EQUIPES DE VENDAS POR USUÁRIO
# ============================================================================

class UsuarioEquipeVendas(db.Model):
    """
    Relacionamento N:N entre usuários e equipes de vendas
    Permite que um usuário tenha acesso a múltiplas equipes
    """
    __tablename__ = 'usuario_equipe_vendas'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    equipe_vendas = db.Column(db.String(100), nullable=False)  # Nome da equipe
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    adicionado_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    adicionado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    observacoes = db.Column(db.String(255), nullable=True)
    
    # Relacionamentos
    usuario = db.relationship('Usuario', foreign_keys=[usuario_id], backref='equipes_autorizadas')
    adicionado_por_user = db.relationship('Usuario', foreign_keys=[adicionado_por])
    
    # Índices
    __table_args__ = (
        UniqueConstraint('usuario_id', 'equipe_vendas', name='uq_usuario_equipe'),
        Index('idx_usuario_equipe_ativo', 'usuario_id', 'ativo'),
        Index('idx_equipe_lookup', 'equipe_vendas', 'ativo'),
    )
    
    def __repr__(self):
        return f'<UsuarioEquipeVendas {self.usuario.nome} -> {self.equipe_vendas}>'
    
    @classmethod
    def get_equipes_usuario(cls, usuario_id):
        """Retorna lista de equipes autorizadas para o usuário"""
        return [ue.equipe_vendas for ue in cls.query.filter_by(
            usuario_id=usuario_id, ativo=True
        ).all()]
    
    @classmethod
    def usuario_tem_equipe(cls, usuario_id, equipe_vendas):
        """Verifica se usuário tem acesso a equipe específica"""
        return cls.query.filter_by(
            usuario_id=usuario_id, 
            equipe_vendas=equipe_vendas, 
            ativo=True
        ).first() is not None

# ============================================================================
# 7. LOG DE AUDITORIA
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
# 8. FUNÇÕES AUXILIARES PARA INICIALIZAÇÃO
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