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


class ClaudePerguntaNaoRespondida(db.Model):
    """
    Log de perguntas que o sistema não conseguiu responder.
    Usado para análise e melhoria contínua do sistema.
    """
    __tablename__ = 'claude_perguntas_nao_respondidas'

    id = db.Column(db.Integer, primary_key=True)

    # Vínculo com usuário
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True, index=True)

    # Pergunta original
    consulta = db.Column(db.Text, nullable=False)

    # Classificação detectada
    intencao_detectada = db.Column(db.String(50), nullable=True)
    dominio_detectado = db.Column(db.String(50), nullable=True)
    confianca = db.Column(db.Float, nullable=True)

    # Entidades extraídas (JSON)
    entidades = db.Column(db.JSON, nullable=True)

    # Motivo da falha
    motivo_falha = db.Column(db.String(100), nullable=False, index=True)
    # Valores: 'sem_capacidade', 'sem_criterio', 'erro_execucao', 'sem_resultado', 'pergunta_composta'

    # Análise da complexidade
    tipo_pergunta = db.Column(db.String(20), default='simples', index=True)
    # Valores: 'simples', 'composta', 'ambigua'

    dimensoes_detectadas = db.Column(db.JSON, nullable=True)
    # Ex: ["cliente", "data", "estoque"] para perguntas compostas

    # Sugestão oferecida ao usuário
    sugestao_gerada = db.Column(db.Text, nullable=True)

    # Status de tratamento
    status = db.Column(db.String(20), default='pendente', index=True)
    # Valores: 'pendente', 'analisado', 'implementado', 'ignorado'

    # Notas de análise (preenchido manualmente depois)
    notas_analise = db.Column(db.Text, nullable=True)
    capacidade_sugerida = db.Column(db.String(100), nullable=True)

    # Timestamps
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False, index=True)
    analisado_em = db.Column(db.DateTime, nullable=True)
    analisado_por = db.Column(db.String(100), nullable=True)

    # Índices
    __table_args__ = (
        db.Index('idx_claude_nao_resp_motivo_data', 'motivo_falha', 'criado_em'),
        db.Index('idx_claude_nao_resp_status', 'status', 'criado_em'),
    )

    def __repr__(self):
        return f'<ClaudePerguntaNaoRespondida {self.id} - {self.motivo_falha}>'

    def to_dict(self):
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'consulta': self.consulta,
            'intencao_detectada': self.intencao_detectada,
            'dominio_detectado': self.dominio_detectado,
            'confianca': self.confianca,
            'entidades': self.entidades,
            'motivo_falha': self.motivo_falha,
            'tipo_pergunta': self.tipo_pergunta,
            'dimensoes_detectadas': self.dimensoes_detectadas,
            'sugestao_gerada': self.sugestao_gerada,
            'status': self.status,
            'notas_analise': self.notas_analise,
            'capacidade_sugerida': self.capacidade_sugerida,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'analisado_em': self.analisado_em.isoformat() if self.analisado_em else None,
            'analisado_por': self.analisado_por
        }

    @classmethod
    def registrar(
        cls,
        consulta: str,
        motivo_falha: str,
        usuario_id: int = None,
        intencao: dict = None,
        sugestao: str = None,
        tipo_pergunta: str = 'simples',
        dimensoes: list = None
    ):
        """Registra uma pergunta não respondida."""
        try:
            registro = cls(
                usuario_id=usuario_id,
                consulta=consulta,
                intencao_detectada=intencao.get('intencao') if intencao else None,
                dominio_detectado=intencao.get('dominio') if intencao else None,
                confianca=intencao.get('confianca') if intencao else None,
                entidades=intencao.get('entidades') if intencao else None,
                motivo_falha=motivo_falha,
                tipo_pergunta=tipo_pergunta,
                dimensoes_detectadas=dimensoes,
                sugestao_gerada=sugestao
            )
            db.session.add(registro)
            db.session.commit()
            return registro
        except Exception as e:
            db.session.rollback()
            import logging
            logging.getLogger(__name__).error(f"Erro ao registrar pergunta não respondida: {e}")
            return None

    @classmethod
    def buscar_pendentes(cls, limite: int = 50):
        """Busca perguntas pendentes de análise."""
        return cls.query.filter_by(
            status='pendente'
        ).order_by(
            cls.criado_em.desc()
        ).limit(limite).all()

    @classmethod
    def buscar_por_motivo(cls, motivo: str, limite: int = 50):
        """Busca perguntas por motivo de falha."""
        return cls.query.filter_by(
            motivo_falha=motivo
        ).order_by(
            cls.criado_em.desc()
        ).limit(limite).all()

    @classmethod
    def estatisticas(cls, dias: int = 7):
        """Retorna estatísticas de perguntas não respondidas."""
        from sqlalchemy import func
        data_limite = agora_brasil() - timedelta(days=dias)

        # Total por motivo
        por_motivo = db.session.query(
            cls.motivo_falha,
            func.count(cls.id).label('total')
        ).filter(
            cls.criado_em >= data_limite
        ).group_by(
            cls.motivo_falha
        ).all()

        # Total por tipo de pergunta
        por_tipo = db.session.query(
            cls.tipo_pergunta,
            func.count(cls.id).label('total')
        ).filter(
            cls.criado_em >= data_limite
        ).group_by(
            cls.tipo_pergunta
        ).all()

        # Top dimensões em perguntas compostas
        compostas = cls.query.filter(
            cls.criado_em >= data_limite,
            cls.tipo_pergunta == 'composta'
        ).all()

        dimensoes_count = {}
        for c in compostas:
            if c.dimensoes_detectadas:
                for d in c.dimensoes_detectadas:
                    dimensoes_count[d] = dimensoes_count.get(d, 0) + 1

        return {
            'periodo_dias': dias,
            'por_motivo': {m: t for m, t in por_motivo},
            'por_tipo': {t: c for t, c in por_tipo},
            'dimensoes_frequentes': sorted(dimensoes_count.items(), key=lambda x: -x[1])[:10],
            'total': sum(t for _, t in por_motivo)
        }
