"""
Modelos do IA Trainer.

Tabelas:
- codigo_sistema_gerado: Codigo gerado pelo Claude (loaders, filtros, etc)
- versao_codigo_gerado: Historico de versoes de cada codigo
- sessao_ensino_ia: Sessao de ensino (pergunta -> explicacao -> codigo)

Criado em: 23/11/2025
"""

from datetime import datetime
from app import db
from app.utils.timezone import agora_brasil

# IMPORTANTE: Importa modelo de referencia para resolver FK
# O SQLAlchemy precisa que ClaudePerguntaNaoRespondida esteja no metadata
# antes de definir CodigoSistemaGerado que referencia sua tabela
from app.claude_ai_lite.models import ClaudePerguntaNaoRespondida  # noqa: F401


class CodigoSistemaGerado(db.Model):
    """
    Codigo gerado pelo Claude atraves do sistema de ensino.

    Tipos de codigo:
    - prompt: Regra adicionada ao prompt de classificacao
    - filtro: Condicao SQL/ORM para filtrar dados
    - entidade: Nova entidade para extracao de texto
    - conceito: Termo de negocio estruturado
    - loader: Codigo Python completo para buscar dados
    - capability: Capacidade completa (mais complexo)
    """
    __tablename__ = 'codigo_sistema_gerado'

    id = db.Column(db.Integer, primary_key=True)

    # === IDENTIFICACAO ===
    nome = db.Column(db.String(100), nullable=False, unique=True, index=True)
    # Ex: "item_parcial_pendente", "cliente_atacadao_183"

    tipo_codigo = db.Column(db.String(30), nullable=False, index=True)
    # Valores: 'prompt', 'filtro', 'entidade', 'conceito', 'loader', 'capability'

    dominio = db.Column(db.String(50), nullable=True, index=True)
    # Ex: 'carteira', 'estoque', 'fretes', etc

    # === GATILHOS (o que ativa este codigo) ===
    gatilhos = db.Column(db.JSON, nullable=False)
    # Ex: ["item parcial pendente", "parcial pendente", "pendencia parcial"]

    # Composicao com outras partes
    composicao = db.Column(db.String(200), nullable=True)
    # Ex: "parcial_pendente + {cliente}"

    # === DEFINICAO TECNICA ===
    definicao_tecnica = db.Column(db.Text, nullable=False)
    # Para filtro: "CarteiraPrincipal.qtd_saldo > 0 AND qtd_produto > qtd_saldo"
    # Para loader: codigo Python completo
    # Para prompt: texto a adicionar no prompt

    # Tabelas/Models referenciados
    models_referenciados = db.Column(db.JSON, nullable=True)
    # Ex: ["CarteiraPrincipal", "Separacao"]

    # Campos referenciados
    campos_referenciados = db.Column(db.JSON, nullable=True)
    # Ex: ["qtd_saldo_produto_pedido", "qtd_produto_pedido"]

    # === DOCUMENTACAO PARA O CLAUDE ===
    descricao_claude = db.Column(db.Text, nullable=False)
    # Descricao que sera incluida no contexto do Claude

    exemplos_uso = db.Column(db.JSON, nullable=True)
    # Ex: ["Tem parcial pendente pro cliente X?", "Itens com pendencia parcial"]

    variacoes = db.Column(db.Text, nullable=True)
    # Notas sobre variacoes e casos especiais

    # === CONTROLE DE ESTADO ===
    ativo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    # So ativa apos passar nos testes

    validado = db.Column(db.Boolean, default=False, nullable=False)
    # Se foi testado e aprovado

    data_validacao = db.Column(db.DateTime, nullable=True)
    validado_por = db.Column(db.String(100), nullable=True)

    # Resultado do ultimo teste
    ultimo_teste_sucesso = db.Column(db.Boolean, nullable=True)
    ultimo_teste_erro = db.Column(db.Text, nullable=True)
    ultimo_teste_em = db.Column(db.DateTime, nullable=True)

    # === PERMISSOES ===
    permite_acao = db.Column(db.Boolean, default=False, nullable=False)
    # Se permite acoes (apenas admin pode criar com True)

    apenas_admin = db.Column(db.Boolean, default=False, nullable=False)
    # Se so admin pode usar

    # === RASTREABILIDADE ===
    versao_atual = db.Column(db.Integer, default=1, nullable=False)

    # Origem
    pergunta_origem_id = db.Column(
        db.Integer,
        db.ForeignKey('claude_perguntas_nao_respondidas.id'),
        nullable=True,
        index=True
    )
    sessao_ensino_id = db.Column(
        db.Integer,
        db.ForeignKey('sessao_ensino_ia.id'),
        nullable=True
    )

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # === RELACIONAMENTOS ===
    versoes = db.relationship('VersaoCodigoGerado', backref='codigo', lazy='dynamic',
                              order_by='VersaoCodigoGerado.versao.desc()')

    # Indices
    __table_args__ = (
        db.Index('idx_codigo_tipo_ativo', 'tipo_codigo', 'ativo'),
        db.Index('idx_codigo_dominio', 'dominio', 'ativo'),
    )

    def __repr__(self):
        return f'<CodigoSistemaGerado {self.nome} ({self.tipo_codigo}) v{self.versao_atual}>'

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo_codigo': self.tipo_codigo,
            'dominio': self.dominio,
            'gatilhos': self.gatilhos,
            'composicao': self.composicao,
            'definicao_tecnica': self.definicao_tecnica,
            'models_referenciados': self.models_referenciados,
            'campos_referenciados': self.campos_referenciados,
            'descricao_claude': self.descricao_claude,
            'exemplos_uso': self.exemplos_uso,
            'variacoes': self.variacoes,
            'ativo': self.ativo,
            'validado': self.validado,
            'versao_atual': self.versao_atual,
            'permite_acao': self.permite_acao,
            'apenas_admin': self.apenas_admin,
            'ultimo_teste_sucesso': self.ultimo_teste_sucesso,
            'ultimo_teste_erro': self.ultimo_teste_erro,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por
        }

    def criar_versao(self, motivo: str, autor: str):
        """Cria uma nova versao antes de modificar."""
        versao = VersaoCodigoGerado(
            codigo_id=self.id,
            versao=self.versao_atual,
            tipo_codigo=self.tipo_codigo,
            gatilhos=self.gatilhos,
            definicao_tecnica=self.definicao_tecnica,
            descricao_claude=self.descricao_claude,
            motivo_alteracao=motivo,
            criado_por=autor
        )
        db.session.add(versao)
        self.versao_atual += 1
        return versao


class VersaoCodigoGerado(db.Model):
    """
    Historico de versoes de um codigo gerado.
    Nada e substituido sem historico.
    """
    __tablename__ = 'versao_codigo_gerado'

    id = db.Column(db.Integer, primary_key=True)

    # Referencia ao codigo
    codigo_id = db.Column(
        db.Integer,
        db.ForeignKey('codigo_sistema_gerado.id'),
        nullable=False,
        index=True
    )

    # Numero da versao
    versao = db.Column(db.Integer, nullable=False)

    # Snapshot do codigo nesta versao
    tipo_codigo = db.Column(db.String(30), nullable=False)
    gatilhos = db.Column(db.JSON, nullable=False)
    definicao_tecnica = db.Column(db.Text, nullable=False)
    descricao_claude = db.Column(db.Text, nullable=False)

    # Motivo da alteracao
    motivo_alteracao = db.Column(db.Text, nullable=True)

    # Resultado de teste desta versao
    teste_sucesso = db.Column(db.Boolean, nullable=True)
    teste_erro = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)

    # Indice composto
    __table_args__ = (
        db.UniqueConstraint('codigo_id', 'versao', name='uk_codigo_versao'),
    )

    def __repr__(self):
        return f'<VersaoCodigoGerado codigo={self.codigo_id} v{self.versao}>'


class SessaoEnsinoIA(db.Model):
    """
    Sessao de ensino: do problema ate a solucao.

    Fluxo:
    1. Pergunta nao respondida selecionada
    2. Usuario decompoe em partes
    3. Claude gera codigo
    4. Usuario debate/refina
    5. Teste e validacao
    6. Ativacao
    """
    __tablename__ = 'sessao_ensino_ia'

    id = db.Column(db.Integer, primary_key=True)

    # === ORIGEM ===
    pergunta_origem_id = db.Column(
        db.Integer,
        db.ForeignKey('claude_perguntas_nao_respondidas.id'),
        nullable=False,
        index=True
    )
    pergunta_original = db.Column(db.Text, nullable=False)

    # === DECOMPOSICAO ===
    # Partes da pergunta explicadas pelo usuario
    decomposicao = db.Column(db.JSON, nullable=True)
    # Ex: [
    #   {"parte": "item parcial pendente", "explicacao": "...", "tipo": "filtro"},
    #   {"parte": "Atacadao 183", "explicacao": "cliente", "campo": "raz_social_red"}
    # ]

    # === DEBATE COM CLAUDE ===
    historico_debate = db.Column(db.JSON, nullable=True)
    # Lista de mensagens: [{"role": "user/assistant", "content": "...", "timestamp": "..."}]

    # === CODIGO GERADO ===
    codigo_gerado_id = db.Column(
        db.Integer,
        db.ForeignKey('codigo_sistema_gerado.id'),
        nullable=True
    )

    # === STATUS ===
    status = db.Column(db.String(30), default='iniciada', nullable=False, index=True)
    # Valores: 'iniciada', 'decomposta', 'codigo_gerado', 'em_debate',
    #          'testando', 'validada', 'ativada', 'cancelada'

    # === RESULTADO ===
    solucao_criada = db.Column(db.Boolean, default=False, nullable=False)
    # True quando codigo foi validado e ativado

    # === AUDITORIA ===
    criado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    finalizado_em = db.Column(db.DateTime, nullable=True)

    # Relacionamentos
    codigo_gerado = db.relationship('CodigoSistemaGerado', foreign_keys=[codigo_gerado_id])

    def __repr__(self):
        return f'<SessaoEnsinoIA {self.id} - {self.status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'pergunta_origem_id': self.pergunta_origem_id,  # Necessario para "Continuar Ensino"
            'pergunta_original': self.pergunta_original,
            'decomposicao': self.decomposicao,
            'historico_debate': self.historico_debate,
            'status': self.status,
            'solucao_criada': self.solucao_criada,
            'codigo_gerado_id': self.codigo_gerado_id,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'criado_por': self.criado_por,
            'finalizado_em': self.finalizado_em.isoformat() if self.finalizado_em else None
        }

    def adicionar_mensagem_debate(self, role: str, content: str):
        """Adiciona mensagem ao historico de debate."""
        if self.historico_debate is None:
            self.historico_debate = []

        self.historico_debate.append({
            'role': role,
            'content': content,
            'timestamp': agora_brasil().isoformat()
        })
        # Marca como modificado para o SQLAlchemy detectar
        db.session.add(self)

    def atualizar_status(self, novo_status: str):
        """Atualiza status da sessao."""
        self.status = novo_status
        if novo_status == 'ativada':
            self.solucao_criada = True
            self.finalizado_em = agora_brasil()
