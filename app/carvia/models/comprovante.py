"""
Comprovantes de Pagamento CarVia
================================

Comprovante de pagamento (PIX, boleto, TED) anexado a documentos da cadeia de
frete: cotacao -> NF -> CTe CarVia (CarviaOperacao) -> Fatura Cliente. Util na
conciliacao bancaria: o cliente as vezes paga antecipado, com CNPJ diferente
da fatura, ou quita varios fretes de uma vez. O comprovante "enriquece" a
fatura e guia a busca da linha de extrato (modo "Conciliacao p/ Comprovante").

Modelo N:N (vs CarviaAnexo, que e 1 entidade): um comprovante pode cobrir
varios documentos (pagou 2 fretes juntos) e um documento pode ter varios
comprovantes. O arquivo vive UMA vez no S3 (espelha CarviaAnexo); os vinculos
(CarviaComprovanteVinculo) o tornam visivel ao longo da cadeia. "Propagar" =
criar vinculos PROPAGADO seguindo a cadeia (cotacao->NF->CTe->Fatura).

Storage: app.utils.file_storage.get_file_storage() (S3/local), mesmo padrao de
CarviaAnexo / CarviaCustoEntregaAnexo. Soft-delete via `ativo` (documentos
fiscais nao sao apagados — GAP-20).
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaComprovantePagamento(db.Model):
    """Comprovante de pagamento (arquivo S3) — N:N com documentos via vinculo."""
    __tablename__ = 'carvia_comprovantes_pagamento'

    id = db.Column(db.Integer, primary_key=True)

    # Arquivo (S3) — espelha CarviaAnexo
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_s3 = db.Column(db.String(500), nullable=False)
    tamanho_bytes = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)

    # Metadados que ajudam a conciliacao (todos opcionais — pagamento e
    # despadronizado: CNPJ do pagador pode diferir do CNPJ da fatura)
    valor = db.Column(db.Numeric(15, 2), nullable=True)
    data_pagamento = db.Column(db.Date, nullable=True)
    cnpj_pagador = db.Column(db.String(20), nullable=True, index=True)
    descricao = db.Column(db.Text, nullable=True)

    # Soft-delete (paridade CarviaAnexo.ativo)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    vinculos = db.relationship(
        'CarviaComprovanteVinculo',
        back_populates='comprovante',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return (
            f'<CarviaComprovantePagamento {self.id} {self.nome_original} '
            f'valor={self.valor} ativo={self.ativo}>'
        )


class CarviaComprovanteVinculo(db.Model):
    """Vinculo N:N polimorfico entre comprovante e documento da cadeia.

    Sem FK fisica para a entidade-alvo (polimorfico, como CarviaAnexo): a
    integridade e garantida no service (entidade validada antes de inserir).
    """
    __tablename__ = 'carvia_comprovante_vinculos'

    # Entidades-alvo suportadas (validadas no service)
    ENTIDADE_COTACAO = 'cotacao'
    ENTIDADE_NF = 'nf'
    ENTIDADE_OPERACAO = 'operacao'              # CTe CarVia
    ENTIDADE_FATURA_CLIENTE = 'fatura_cliente'
    ENTIDADES_VALIDAS = frozenset({
        ENTIDADE_COTACAO, ENTIDADE_NF, ENTIDADE_OPERACAO, ENTIDADE_FATURA_CLIENTE,
    })

    # Origem do vinculo
    ORIGEM_MANUAL = 'MANUAL'                    # upload direto na entidade
    ORIGEM_PROPAGADO = 'PROPAGADO'             # herdado ao percorrer a cadeia

    id = db.Column(db.Integer, primary_key=True)
    comprovante_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_comprovantes_pagamento.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    entidade_tipo = db.Column(db.String(30), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(20), nullable=False, default=ORIGEM_MANUAL)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    comprovante = db.relationship(
        'CarviaComprovantePagamento', back_populates='vinculos'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'comprovante_id', 'entidade_tipo', 'entidade_id',
            name='uq_carvia_comprovante_vinculo',
        ),
        db.Index(
            'ix_carvia_comprovante_vinculo_entidade',
            'entidade_tipo', 'entidade_id',
        ),
    )

    def __repr__(self):
        return (
            f'<CarviaComprovanteVinculo {self.id} comp#{self.comprovante_id} '
            f'{self.entidade_tipo}#{self.entidade_id} {self.origem}>'
        )
