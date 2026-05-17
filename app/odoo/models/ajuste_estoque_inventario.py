"""Model AjusteEstoqueInventario — controle de ciclo de inventario.

Tabela enxuta: 1 linha por divergencia (produto, company, lote) detectada
em um ciclo. Suporta multiplos ciclos via campo `ciclo`.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §7.2
"""
from app import db
from app.utils.timezone import agora_utc_naive


STATUS_VALIDOS = {'PROPOSTO', 'APROVADO', 'EXECUTADO', 'FALHA', 'CANCELADO'}

ACOES_VALIDAS = {
    'TRANSFERIR_CD_FB',
    'TRANSFERIR_FB_CD',
    'INDUSTRIALIZACAO_FB_LF',
    'PERDA_LF_FB',
    'DEV_FB_LF',
    'DEV_LF_FB',
    'DEV_CD_LF',
    'DEV_LF_CD',
    'INDISPONIBILIZAR_LOTE',
    'INDISPONIBILIZAR_LOCAL',
    'RENOMEAR_LOTE',
    'SEM_ACAO',
}


class AjusteEstoqueInventario(db.Model):
    __tablename__ = 'ajuste_estoque_inventario'

    id = db.Column(db.Integer, primary_key=True)
    ciclo = db.Column(db.String(40), nullable=False)
    cod_produto = db.Column(db.String(30), nullable=False)
    tipo_produto = db.Column(db.SmallInteger, nullable=False)
    company_id = db.Column(db.Integer, nullable=False)
    lote_inventariado = db.Column(db.String(60))
    lote_odoo = db.Column(db.String(60))
    qtd_inventario = db.Column(db.Numeric(15, 4), nullable=False)
    qtd_odoo = db.Column(db.Numeric(15, 4), nullable=False)
    qtd_ajuste = db.Column(db.Numeric(15, 4), nullable=False)
    custo_medio = db.Column(db.Numeric(15, 4))
    acao_decidida = db.Column(db.String(30), nullable=False)
    external_id_operacao = db.Column(db.String(64))
    canary_passou = db.Column(db.Boolean, default=False)
    aprovado_em = db.Column(db.DateTime)
    aprovado_por = db.Column(db.String(80))
    status = db.Column(db.String(20), nullable=False, default='PROPOSTO')
    # Campos adicionados pos-G004/D003 (pipeline em batches):
    fase_pipeline = db.Column(db.String(20))  # F5a..F5e ou FINALIZADO
    picking_id_odoo = db.Column(db.Integer)
    invoice_id_odoo = db.Column(db.Integer)
    chave_nfe = db.Column(db.String(44))
    erro_msg = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return (
            f'<AjusteEstoqueInventario id={self.id} ciclo={self.ciclo} '
            f'{self.cod_produto}@company={self.company_id} '
            f'acao={self.acao_decidida} status={self.status}>'
        )
