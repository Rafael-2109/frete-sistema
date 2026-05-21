"""
Modelo de Anexos polimorfico CarVia
====================================

Anexos comprovatorios (PDFs, imagens, e-mails .msg/.eml via S3) para
CarviaFrete e CarviaSubcontrato — paridade com a Nacom (DespesaExtra.comprovante
+ EmailAnexado).

Espelha os campos de CarviaCustoEntregaAnexo (cte_custos.py) mas e POLIMORFICO:
uma unica tabela serve N entidades via (entidade_tipo, entidade_id), evitando
boilerplate de uma tabela por entidade.

DECISAO 2026-05-20: Despesas (CarviaCustoEntrega) MANTEM sua propria tabela
CarviaCustoEntregaAnexo intacta — nao ha migracao de dados existentes. Apenas
Frete e Subcontrato (que nao tinham anexo) usam esta tabela.
"""

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaAnexo(db.Model):
    """Anexos comprovatorios polimorficos (frete, subcontrato) via S3."""
    __tablename__ = 'carvia_anexos'

    # Tipos de entidade suportados (validados na rota e no service)
    ENTIDADE_FRETE = 'frete'
    ENTIDADE_SUBCONTRATO = 'subcontrato'
    ENTIDADES_VALIDAS = frozenset({ENTIDADE_FRETE, ENTIDADE_SUBCONTRATO})

    id = db.Column(db.Integer, primary_key=True)

    # Polimorfismo: (entidade_tipo, entidade_id). Sem FK fisica — a integridade
    # e garantida na camada de service (entidade validada antes de inserir).
    entidade_tipo = db.Column(db.String(30), nullable=False, index=True)
    entidade_id = db.Column(db.Integer, nullable=False, index=True)

    # Arquivo (S3) — espelha CarviaCustoEntregaAnexo
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_s3 = db.Column(db.String(500), nullable=False)
    tamanho_bytes = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    # Soft-delete (paridade CarviaCustoEntregaAnexo.ativo)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    # Metadados de email (nullable — populados apenas para .msg/.eml)
    email_remetente = db.Column(db.String(255), nullable=True)
    email_assunto = db.Column(db.String(500), nullable=True)
    email_data_envio = db.Column(db.DateTime, nullable=True)
    email_conteudo_preview = db.Column(db.String(500), nullable=True)

    __table_args__ = (
        db.Index('ix_carvia_anexo_entidade', 'entidade_tipo', 'entidade_id'),
    )

    def __repr__(self):
        return (
            f'<CarviaAnexo {self.id} {self.entidade_tipo}#{self.entidade_id} '
            f'{self.nome_original} ativo={self.ativo}>'
        )
