"""
Modelos de dados para memória do Claude AI Lite.

Tabelas:
- claude_historico_conversa: Histórico de mensagens por usuário
- claude_aprendizado: Conhecimento permanente (por usuário ou global)
"""

from datetime import datetime, timedelta
from app import db
from app.utils.timezone import agora_brasil


class ClaudeHistoricoConversa(db.Model):
    """
    Histórico de conversas por usuário.
    Mantém as últimas N mensagens para contexto.
    """
    __tablename__ = 'claude_historico_conversa'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com usuário
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, index=True)

    # Tipo da mensagem
    tipo = db.Column(db.String(20), nullable=False, index=True)
    # Valores: 'usuario', 'assistente', 'sistema', 'resultado'

    # Conteúdo
    conteudo = db.Column(db.Text, nullable=False)

    # Metadados (JSON) - intenção detectada, entidades, etc
    metadados = db.Column(db.JSON, nullable=True)

    # Timestamps
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)

    # Índices
    __table_args__ = (
        db.Index('idx_claude_hist_usuario_data', 'usuario_id', 'criado_em'),
    )

    def __repr__(self):
        return f'<ClaudeHistorico {self.id} - {self.tipo} - User:{self.usuario_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'tipo': self.tipo,
            'conteudo': self.conteudo,
            'metadados': self.metadados,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None
        }

    @classmethod
    def adicionar_mensagem(cls, usuario_id: int, tipo: str, conteudo: str, metadados: dict = None):
        """Adiciona uma mensagem ao histórico."""
        mensagem = cls(
            usuario_id=usuario_id,
            tipo=tipo,
            conteudo=conteudo,
            metadados=metadados
        )
        db.session.add(mensagem)
        db.session.commit()
        return mensagem

    @classmethod
    def buscar_historico(cls, usuario_id: int, limite: int = 40):
        """Busca últimas N mensagens do usuário."""
        return cls.query.filter_by(
            usuario_id=usuario_id
        ).order_by(
            cls.criado_em.desc()
        ).limit(limite).all()[::-1]  # Inverte para ordem cronológica

    @classmethod
    def limpar_historico_antigo(cls, dias: int = 7):
        """Remove histórico mais antigo que N dias."""
        data_limite = agora_brasil() - timedelta(days=dias)
        deletados = cls.query.filter(
            cls.criado_em < data_limite
        ).delete()
        db.session.commit()
        return deletados


class ClaudeAprendizado(db.Model):
    """
    Conhecimento permanente do Claude.
    Pode ser por usuário (personalizado) ou global (vale para todos).
    """
    __tablename__ = 'claude_aprendizado'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com usuário (NULL = global, aplica a todos)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)

    # Categoria do aprendizado
    categoria = db.Column(db.String(50), nullable=False, index=True)
    # Valores: 'preferencia', 'correcao', 'regra_negocio', 'fato', 'cliente', 'produto', 'processo'

    # Chave única para identificar o aprendizado
    chave = db.Column(db.String(100), nullable=False, index=True)
    # Ex: "cliente_vip_ceratti", "produto_sinonimo_azeitona", "regra_frete_sp"

    # Valor/Conteúdo do aprendizado
    valor = db.Column(db.Text, nullable=False)
    # Texto livre que será incluído no contexto do Claude

    # Contexto adicional (JSON)
    contexto = db.Column(db.JSON, nullable=True)
    # Ex: {"origem": "conversa_123", "confianca": 0.9}

    # Controle
    ativo = db.Column(db.Boolean, default=True, nullable=False, index=True)
    prioridade = db.Column(db.Integer, default=5, nullable=False)
    # 1-10, maior = mais importante (incluído primeiro no contexto)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Índices
    __table_args__ = (
        db.Index('idx_claude_aprend_usuario_cat', 'usuario_id', 'categoria'),
        db.Index('idx_claude_aprend_chave', 'chave'),
        db.UniqueConstraint('usuario_id', 'chave', name='uk_claude_aprend_usuario_chave'),
    )

    def __repr__(self):
        escopo = f"User:{self.usuario_id}" if self.usuario_id else "GLOBAL"
        return f'<ClaudeAprendizado {self.id} - {self.categoria}:{self.chave} ({escopo})>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'escopo': 'usuario' if self.usuario_id else 'global',
            'categoria': self.categoria,
            'chave': self.chave,
            'valor': self.valor,
            'contexto': self.contexto,
            'ativo': self.ativo,
            'prioridade': self.prioridade,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None,
            'atualizado_por': self.atualizado_por
        }

    @classmethod
    def adicionar(cls, categoria: str, chave: str, valor: str,
                  usuario_id: int = None, criado_por: str = None,
                  prioridade: int = 5, contexto: dict = None):
        """
        Adiciona ou atualiza um aprendizado.
        Se já existe (mesmo usuario_id + chave), atualiza.
        """
        existente = cls.query.filter_by(
            usuario_id=usuario_id,
            chave=chave
        ).first()

        if existente:
            existente.categoria = categoria
            existente.valor = valor
            existente.contexto = contexto
            existente.prioridade = prioridade
            existente.atualizado_por = criado_por
            existente.ativo = True
            db.session.commit()
            return existente, False  # Atualizado
        else:
            novo = cls(
                usuario_id=usuario_id,
                categoria=categoria,
                chave=chave,
                valor=valor,
                contexto=contexto,
                prioridade=prioridade,
                criado_por=criado_por
            )
            db.session.add(novo)
            db.session.commit()
            return novo, True  # Criado

    @classmethod
    def buscar_aprendizados(cls, usuario_id: int = None, incluir_globais: bool = True):
        """
        Busca aprendizados ativos.
        Retorna os do usuário + globais (se solicitado), ordenados por prioridade.
        """
        from sqlalchemy import or_

        query = cls.query.filter(cls.ativo == True)

        if usuario_id and incluir_globais:
            # Usuário específico + globais
            query = query.filter(or_(
                cls.usuario_id == usuario_id,
                cls.usuario_id.is_(None)
            ))
        elif usuario_id:
            # Apenas do usuário
            query = query.filter(cls.usuario_id == usuario_id)
        else:
            # Apenas globais
            query = query.filter(cls.usuario_id.is_(None))

        return query.order_by(cls.prioridade.desc(), cls.criado_em.desc()).all()

    @classmethod
    def desativar(cls, chave: str, usuario_id: int = None, desativado_por: str = None):
        """Desativa um aprendizado (soft delete)."""
        aprendizado = cls.query.filter_by(
            usuario_id=usuario_id,
            chave=chave
        ).first()

        if aprendizado:
            aprendizado.ativo = False
            aprendizado.atualizado_por = desativado_por
            db.session.commit()
            return True
        return False

    @classmethod
    def buscar_por_categoria(cls, categoria: str, usuario_id: int = None, incluir_globais: bool = True):
        """Busca aprendizados por categoria."""
        from sqlalchemy import or_

        query = cls.query.filter(
            cls.ativo == True,
            cls.categoria == categoria
        )

        if usuario_id and incluir_globais:
            query = query.filter(or_(
                cls.usuario_id == usuario_id,
                cls.usuario_id.is_(None)
            ))
        elif usuario_id:
            query = query.filter(cls.usuario_id == usuario_id)
        else:
            query = query.filter(cls.usuario_id.is_(None))

        return query.order_by(cls.prioridade.desc()).all()
