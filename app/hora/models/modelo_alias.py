"""Unificacao de modelos: alias (N nomes -> 1 modelo) + pendencias.

Resolve o problema de N descricoes (TagPlus, NF, pedido) referenciando o
MESMO modelo fisico. Em vez de criar HoraModelo distintos para cada nome
(comportamento antigo de buscar_ou_criar_modelo), o resolver consulta
HoraModeloAlias e, se nao achar, cria HoraModeloPendente para o operador
decidir (vincular a modelo existente OU criar novo).

Ver `app/hora/CLAUDE.md` secao "Unificacao de modelos" e
`app/hora/services/modelo_resolver_service.py`.
"""
from __future__ import annotations

from app import db
from app.utils.timezone import agora_utc_naive


# ---------- Constantes de tipo de alias ----------
# Origem do nome — define como o resolver bate na tabela.
ALIAS_TIPO_TAGPLUS_PRODUTO_ID = 'TAGPLUS_PRODUTO_ID'
# Ex.: '10', '21' (ID inteiro do produto no TagPlus).
ALIAS_TIPO_TAGPLUS_CODIGO = 'TAGPLUS_CODIGO'
# Ex.: 'MT-BOB', 'MT-X12 10' (codigo curto exibido na coluna CODIGO da DANFE).
ALIAS_TIPO_NOME_NF = 'NOME_NF'
# Texto livre extraido de DANFE (item.modelo_texto_original).
ALIAS_TIPO_NOME_PEDIDO = 'NOME_PEDIDO'
# Texto digitado em pedido manual (operador).
ALIAS_TIPO_NOME_LIVRE = 'NOME_LIVRE'
# Geral — preserva nomes que ja foram modelo canonico antes da unificacao.

ALIAS_TIPOS_VALIDOS = (
    ALIAS_TIPO_TAGPLUS_PRODUTO_ID,
    ALIAS_TIPO_TAGPLUS_CODIGO,
    ALIAS_TIPO_NOME_NF,
    ALIAS_TIPO_NOME_PEDIDO,
    ALIAS_TIPO_NOME_LIVRE,
)


# ---------- Constantes de origem de pendencia ----------
PENDENTE_ORIGEM_TAGPLUS_BACKFILL = 'TAGPLUS_BACKFILL'
PENDENTE_ORIGEM_NF_ENTRADA = 'NF_ENTRADA'
PENDENTE_ORIGEM_PEDIDO_MANUAL = 'PEDIDO_MANUAL'
PENDENTE_ORIGEM_DANFE_PDF = 'DANFE_PDF'
PENDENTE_ORIGEM_RECEBIMENTO = 'RECEBIMENTO'

PENDENTE_ORIGENS_VALIDAS = (
    PENDENTE_ORIGEM_TAGPLUS_BACKFILL,
    PENDENTE_ORIGEM_NF_ENTRADA,
    PENDENTE_ORIGEM_PEDIDO_MANUAL,
    PENDENTE_ORIGEM_DANFE_PDF,
    PENDENTE_ORIGEM_RECEBIMENTO,
)


# ---------- Constantes de status de pendencia ----------
PENDENTE_STATUS_PENDENTE = 'PENDENTE'
PENDENTE_STATUS_VINCULADO = 'VINCULADO'
PENDENTE_STATUS_NOVO_MODELO = 'NOVO_MODELO'
PENDENTE_STATUS_IGNORADO = 'IGNORADO'

PENDENTE_STATUS_VALIDOS = (
    PENDENTE_STATUS_PENDENTE,
    PENDENTE_STATUS_VINCULADO,
    PENDENTE_STATUS_NOVO_MODELO,
    PENDENTE_STATUS_IGNORADO,
)
PENDENTE_STATUS_RESOLVIDO = (
    PENDENTE_STATUS_VINCULADO,
    PENDENTE_STATUS_NOVO_MODELO,
)


class HoraModeloAlias(db.Model):
    """N nomes -> 1 modelo canonico.

    Cada linha mapeia um `nome_alias` (de uma `tipo` especifica) para o
    `modelo_id` canonico. A UNIQUE (tipo, nome_alias) garante que um mesmo
    nome em uma mesma origem aponta para apenas 1 canonico — evita
    ambiguidade no resolver.

    Exemplos:
      modelo_id=9 (BOB), tipo=TAGPLUS_CODIGO, nome_alias='MT-BOB'
      modelo_id=9 (BOB), tipo=TAGPLUS_PRODUTO_ID, nome_alias='10'
      modelo_id=9 (BOB), tipo=NOME_LIVRE, nome_alias='BOB AM'
      modelo_id=9 (BOB), tipo=NOME_LIVRE, nome_alias='SCOOTER ELETRICA BOB'
    """
    __tablename__ = 'hora_modelo_alias'

    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_modelo.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    nome_alias = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(30), nullable=False, index=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    modelo = db.relationship('HoraModelo', backref='aliases')

    __table_args__ = (
        db.UniqueConstraint('tipo', 'nome_alias', name='uq_hora_modelo_alias_tipo_nome'),
    )

    def __repr__(self) -> str:
        return (
            f'<HoraModeloAlias modelo_id={self.modelo_id} '
            f'tipo={self.tipo} alias={self.nome_alias!r}>'
        )


class HoraModeloPendente(db.Model):
    """Fila de nomes nao reconhecidos aguardando decisao do operador.

    Sistema NAO cria modelo silenciosamente: quando ingestao (TagPlus,
    NF, pedido) encontra nome desconhecido, cria/incrementa uma linha
    aqui. O item da NF/pedido fica com modelo_id=NULL (ou nao cria
    HoraMoto para o chassi) ate operador resolver.

    Resolucao gera retroatividade: ao vincular/criar, todos os itens
    pendentes com mesmo `nome_observado` sao corrigidos.

    Ver `app/hora/services/modelo_resolver_service.py`.
    """
    __tablename__ = 'hora_modelo_pendente'

    id = db.Column(db.Integer, primary_key=True)
    nome_observado = db.Column(db.String(200), nullable=False)
    origem = db.Column(db.String(30), nullable=False, index=True)

    origem_id = db.Column(db.Integer, nullable=True)
    # ID da entidade que disparou (sem FK porque N tabelas distintas).

    tagplus_codigo = db.Column(db.String(50), nullable=True)
    tagplus_produto_id = db.Column(db.String(50), nullable=True)

    qtd_ocorrencias = db.Column(db.Integer, nullable=False, default=1)
    primeiro_visto = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    ultimo_visto = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    status = db.Column(
        db.String(20),
        nullable=False,
        default=PENDENTE_STATUS_PENDENTE,
        index=True,
    )

    resolvido_modelo_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_modelo.id'),
        nullable=True,
        index=True,
    )
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    modelo = db.relationship('HoraModelo', foreign_keys=[resolvido_modelo_id])

    __table_args__ = (
        db.UniqueConstraint(
            'nome_observado', 'origem',
            name='uq_hora_modelo_pendente_nome_origem',
        ),
    )

    @property
    def resolvido(self) -> bool:
        return self.status in PENDENTE_STATUS_RESOLVIDO

    def __repr__(self) -> str:
        return (
            f'<HoraModeloPendente {self.nome_observado!r} '
            f'origem={self.origem} status={self.status}>'
        )
