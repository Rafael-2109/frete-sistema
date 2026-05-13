"""Model AssaiCce — Carta de Correcao Eletronica como entidade propria.

Motivacao: CCe pode chegar ANTES da NF correspondente. Precisa persistir
independentemente com flag `tem_nf` + match reverso ao importar NF.

Spec interna: feature CCe avulsa (2026-05-13).
Identidade SEFAZ: protocolo_cce (UNIQUE).
"""
from app import db
from app.utils.timezone import agora_brasil_naive


# Status do ciclo de vida da CCe
CCE_STATUS_PENDENTE = 'PENDENTE'      # tem_nf=False, aguardando NF chegar
CCE_STATUS_APLICADA = 'APLICADA'      # CHASSI: chassis trocados na NF
CCE_STATUS_IGNORADA = 'IGNORADA'      # DUPLICATAS / ENDERECO — registra mas nao aplica
CCE_STATUS_ERRO = 'ERRO'              # falha nao recuperavel

CCE_STATUS_VALIDOS = {
    CCE_STATUS_PENDENTE,
    CCE_STATUS_APLICADA,
    CCE_STATUS_IGNORADA,
    CCE_STATUS_ERRO,
}


class AssaiCce(db.Model):
    __tablename__ = 'assai_cce'

    id = db.Column(db.Integer, primary_key=True)

    # Identidade SEFAZ
    protocolo_cce = db.Column(db.String(30), unique=True, nullable=False)
    chave_nfe = db.Column(db.String(44), nullable=False, index=True)
    numero_nf_referenciada = db.Column(db.String(20), nullable=False, index=True)
    sequencia_cce = db.Column(db.Integer, nullable=False, default=1)

    # Metadados do parser
    numero_cce = db.Column(db.String(50))  # Gerado pelo parser (ex: "CCe-1-NF1729")
    tipo_correcao = db.Column(db.String(20), nullable=False, default='OUTRO')
    formato_detectado = db.Column(db.String(30))
    parser_usado = db.Column(db.String(40))
    confianca_parser = db.Column(db.Numeric(4, 3))
    dados_parsed = db.Column(db.JSON)  # dump completo do parser (chassis_detalhes, duplicatas, etc.)

    # Arquivo persistido em S3
    pdf_s3_key = db.Column(db.String(500))
    nome_arquivo_original = db.Column(db.String(255))
    data_emissao_cce = db.Column(db.Date)

    # Estado de aplicacao
    tem_nf = db.Column(db.Boolean, nullable=False, default=False, index=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_nf_qpa.id', ondelete='SET NULL'),
        index=True,
    )
    status = db.Column(db.String(20), nullable=False, default=CCE_STATUS_PENDENTE, index=True)

    aplicada_em = db.Column(db.DateTime)
    aplicada_por_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )

    # Auditoria
    chassis_aplicados = db.Column(db.JSON)  # [[antigo, novo], ...]
    observacao = db.Column(db.Text)

    # Origem (se veio do botao CCe em uma divergencia)
    divergencia_origem_id = db.Column(
        db.Integer,
        db.ForeignKey('assai_divergencia.id', ondelete='SET NULL'),
        index=True,
    )

    # Auditoria de criacao
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    criado_por_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id', ondelete='SET NULL'),
    )

    # Relacionamentos
    nf = db.relationship('AssaiNfQpa', lazy='joined', foreign_keys=[nf_id])
    divergencia_origem = db.relationship(
        'AssaiDivergencia', lazy='select', foreign_keys=[divergencia_origem_id],
    )

    def __repr__(self):
        return f'<AssaiCce {self.protocolo_cce} status={self.status} tem_nf={self.tem_nf}>'

    @property
    def numero_nf_normalizado(self):
        """numero_nf sem zeros a esquerda (para match com AssaiNfQpa.numero)."""
        return (self.numero_nf_referenciada or '').lstrip('0') or '0'
