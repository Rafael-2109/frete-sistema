"""Carta de Correção (CCe) CarVia — anexo de documento (PDF/imagem).

Espelha o padrão Comprovante (N:N polimórfico): o arquivo vive UMA vez no S3;
os vínculos o tornam visível na cadeia cotacao <-> nf. Anexar na NF propaga
para a cotação vinculada e vice-versa (sincronizar_cadeia, eixo = NFs).

Model ENXUTO (decisão de design): arquivo + descrição. SEM campos fiscais —
o audit textual de campos do CTe já vive em CarviaEnderecoCorrecao (separado).
Soft-delete via `ativo` (GAP-20).
"""
from app import db
from app.utils.timezone import agora_utc_naive


class CarviaCartaCorrecao(db.Model):
    """Carta de Correção (arquivo S3) — N:N com cotacao/nf via vínculo."""
    __tablename__ = 'carvia_cartas_correcao'

    id = db.Column(db.Integer, primary_key=True)
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_s3 = db.Column(db.String(500), nullable=False)
    tamanho_bytes = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.Text, nullable=True)

    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    vinculos = db.relationship(
        'CarviaCartaCorrecaoVinculo',
        back_populates='carta',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<CarviaCartaCorrecao {self.id} {self.nome_original} ativo={self.ativo}>'


class CarviaCartaCorrecaoVinculo(db.Model):
    """Vínculo N:N polimórfico entre CCe e documento (cotacao/nf)."""
    __tablename__ = 'carvia_carta_correcao_vinculos'

    ENTIDADE_COTACAO = 'cotacao'
    ENTIDADE_NF = 'nf'
    ENTIDADES_VALIDAS = frozenset({ENTIDADE_COTACAO, ENTIDADE_NF})

    ORIGEM_MANUAL = 'MANUAL'
    ORIGEM_PROPAGADO = 'PROPAGADO'

    id = db.Column(db.Integer, primary_key=True)
    carta_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cartas_correcao.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    entidade_tipo = db.Column(db.String(30), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(20), nullable=False, default=ORIGEM_MANUAL)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    carta = db.relationship('CarviaCartaCorrecao', back_populates='vinculos')

    __table_args__ = (
        db.UniqueConstraint(
            'carta_id', 'entidade_tipo', 'entidade_id',
            name='uq_carvia_cce_vinculo',
        ),
        db.Index(
            'ix_carvia_cce_vinculo_entidade', 'entidade_tipo', 'entidade_id',
        ),
    )

    def __repr__(self):
        return (f'<CarviaCartaCorrecaoVinculo {self.id} carta#{self.carta_id} '
                f'{self.entidade_tipo}#{self.entidade_id} {self.origem}>')
