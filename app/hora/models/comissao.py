"""Comissao de vendas — roadmap #28 (Fatia 1: cadastro de configuracao).

Decisoes do dono (2026-06-06):
  - Comissao da moto = VALOR UNICO geral (config singleton comissao_base_moto).
  - "Nivel de desconto": FAIXAS por valor de desconto em R$ dado na moto
    reduzem a comissao em R$ (hora_comissao_faixa_desconto).
  - Comissao de peca = valor por codigo de peca (hora_peca.valor_comissao —
    [ASSUNCAO] por unidade vendida; confirmar na Fatia 3 do calculo).
  - Teto de desconto = por MODELO (hora_modelo.desconto_maximo, em R$ —
    [ASSUNCAO] desconto em R$ coerente com as faixas; estourar exige aprovacao
    na Fatia 2).

Esta Fatia 1 cobre apenas o CADASTRO. Calculo de comissao e fila de aprovacao
de desconto vem nas Fatias 2 e 3.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraComissaoConfig(db.Model):
    """Configuracao global (singleton) de comissao. Use id=1."""
    __tablename__ = 'hora_comissao_config'

    id = db.Column(db.Integer, primary_key=True)
    # Comissao base por moto vendida (valor unico geral, R$).
    comissao_base_moto = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    atualizado_em = db.Column(
        db.DateTime, nullable=False, default=agora_utc_naive, onupdate=agora_utc_naive,
    )
    atualizado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<HoraComissaoConfig base_moto={self.comissao_base_moto}>'


class HoraComissaoFaixaDesconto(db.Model):
    """Faixa de valor de desconto (R$) dado na moto -> reducao da comissao (R$).

    Ex.: desconto_min=100, desconto_max=300, reducao_comissao=20 significa que,
    quando o desconto da moto cai em [100, 300), a comissao da moto e reduzida
    em R$ 20. desconto_max NULL = faixa aberta superiormente (>= desconto_min).
    """
    __tablename__ = 'hora_comissao_faixa_desconto'

    id = db.Column(db.Integer, primary_key=True)
    desconto_min = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    desconto_max = db.Column(db.Numeric(15, 2), nullable=True)  # NULL = sem limite superior
    reducao_comissao = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    def __repr__(self):
        return (f'<HoraComissaoFaixaDesconto [{self.desconto_min}, {self.desconto_max}) '
                f'-> -{self.reducao_comissao}>')


# Status da aprovacao de desconto (#28, Fatia 2).
APROVACAO_STATUS_PENDENTE = 'PENDENTE'
APROVACAO_STATUS_APROVADO = 'APROVADO'
APROVACAO_STATUS_REJEITADO = 'REJEITADO'
APROVACAO_STATUS_VALIDOS = (
    APROVACAO_STATUS_PENDENTE, APROVACAO_STATUS_APROVADO, APROVACAO_STATUS_REJEITADO,
)


class HoraAprovacaoDesconto(db.Model):
    """Solicitacao de aprovacao de desconto acima do teto do modelo (#28).

    Criada por confirmar_venda quando algum item-moto tem desconto acima do
    teto (hora_modelo.desconto_maximo). Enquanto houver solicitacao PENDENTE
    (e nenhuma APROVADO vigente), a venda NAO pode ser confirmada. Append-only
    de fato (status muda de PENDENTE -> APROVADO/REJEITADO; e o log).
    """
    __tablename__ = 'hora_aprovacao_desconto'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer, db.ForeignKey('hora_venda.id'), nullable=False, index=True,
    )
    status = db.Column(
        db.String(20), nullable=False, default=APROVACAO_STATUS_PENDENTE, index=True,
    )
    # Texto descritivo dos itens que estouraram (chassi/modelo/desconto/teto).
    detalhe = db.Column(db.Text, nullable=True)

    solicitado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    solicitado_por = db.Column(db.String(100), nullable=True)
    decidido_em = db.Column(db.DateTime, nullable=True)
    decidido_por = db.Column(db.String(100), nullable=True)
    motivo_decisao = db.Column(db.String(500), nullable=True)

    venda = db.relationship('HoraVenda', backref='aprovacoes_desconto')

    def __repr__(self):
        return f'<HoraAprovacaoDesconto venda={self.venda_id} {self.status}>'
