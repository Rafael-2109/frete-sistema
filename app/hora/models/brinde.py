"""Brinde de venda — roadmap #36.

Brinde = peca do catalogo dada ao cliente. Decisoes do dono (2026-06-06):
  - custo = hora_peca.preco_venda_padrao (snapshot no momento — proxy de custo);
  - NAO abate estoque (controle a parte) — por isso NAO reusa HoraVendaItemPeca
    (que e cobrado + debita estoque) e vive em tabela propria;
  - NAO entra no valor cobrado (valor_total da venda) — entra so no CUSTO,
    reduzindo a margem da venda (venda_preview_service).
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraVendaBrinde(db.Model):
    """Peca dada de brinde numa venda (custo na margem; nao cobrado; nao abate estoque)."""
    __tablename__ = 'hora_venda_brinde'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer, db.ForeignKey('hora_venda.id'), nullable=False, index=True,
    )
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'), nullable=False, index=True,
    )
    qtd = db.Column(db.Numeric(15, 3), nullable=False, default=1)
    # Snapshot de hora_peca.preco_venda_padrao no momento (proxy de custo).
    custo_unitario = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    custo_total = db.Column(db.Numeric(15, 2), nullable=False, default=0)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)

    venda = db.relationship('HoraVenda', backref='brindes')
    peca = db.relationship('HoraPeca')

    def __repr__(self):
        return (f'<HoraVendaBrinde venda={self.venda_id} peca={self.peca_id} '
                f'qtd={self.qtd} custo={self.custo_total}>')
