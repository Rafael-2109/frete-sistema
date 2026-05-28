"""Modelos do módulo Inventário.

Spec: docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md
"""
from app import db
from app.utils.timezone import agora_utc_naive


class CicloInventario(db.Model):
    """Ciclo de inventário (ex.: INV-2026-05-16)."""
    __tablename__ = 'inventario_ciclo'

    id            = db.Column(db.Integer, primary_key=True)
    codigo        = db.Column(db.String(50), unique=True, nullable=False)
    data_snapshot = db.Column(db.Date, nullable=False)
    descricao     = db.Column(db.String(200))
    status        = db.Column(db.String(20), default='ATIVO', nullable=False)
    criado_em     = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por    = db.Column(db.String(100))

    __table_args__ = (
        db.Index('ix_inventario_ciclo_status', 'status'),
    )

    def __repr__(self):
        return f'<CicloInventario {self.codigo}>'


class InventarioBase(db.Model):
    """Snapshot físico FB/CD/LF (uma linha por cod + empresa)."""
    __tablename__ = 'inventario_base'

    id           = db.Column(db.Integer, primary_key=True)
    ciclo_id     = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                             nullable=False, index=True)
    cod_produto  = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200))
    empresa      = db.Column(db.String(10), nullable=False)
    qtd          = db.Column(db.Numeric(15, 3), nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'cod_produto', 'empresa',
                            name='uq_inv_base_ciclo_cod_empresa'),
    )


class AjusteManualInventario(db.Model):
    """Ajustes manuais (Planilha2 — preenchido pelo time)."""
    __tablename__ = 'inventario_ajuste_manual'

    id            = db.Column(db.Integer, primary_key=True)
    ciclo_id      = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                              nullable=False, index=True)
    cod_produto   = db.Column(db.String(50), nullable=False, index=True)
    nome_produto  = db.Column(db.String(200))
    local         = db.Column(db.String(20))
    qtd           = db.Column(db.Numeric(15, 3), nullable=False)
    tipo_ajuste   = db.Column(db.String(20))
    observacao    = db.Column(db.String(500))
    criado_em     = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)
    criado_por    = db.Column(db.String(100))


class InventarioSnapshotOdoo(db.Model):
    """Cache de estoque + apontamentos + compras do Odoo + MOV local (botão refresh).

    Freeze 2026-05-27: alem dos campos Odoo (estoque_*, pa_qtd, componente_qtd,
    compras_qtd), grava tambem agregacoes de MovimentacaoEstoque local
    (mov_*) no mesmo momento T0 do refresh. Garante que ODOO-MOV e SIST-MOV
    do Confronto sejam matematicamente validas (mesmo momento).

    AjusteManualInventario PERMANECE LIVE (nao snapshotado) — usuario edita
    AJ.LOCAL/AJ.QTD inline pelo confronto e espera ver na hora. AJ nao
    entra no calculo de ODOO-MOV/SIST-MOV (colunas independentes), entao
    manter live preserva matematica + UX.
    """
    __tablename__ = 'inventario_snapshot_odoo'

    id             = db.Column(db.Integer, primary_key=True)
    ciclo_id       = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                               nullable=False, index=True)
    cod_produto    = db.Column(db.String(50), nullable=False, index=True)
    nome_produto   = db.Column(db.String(200))
    # Odoo (origem snapshot_odoo_service._baixar_*)
    estoque_fb     = db.Column(db.Numeric(15, 3), default=0)
    estoque_cd     = db.Column(db.Numeric(15, 3), default=0)
    estoque_lf     = db.Column(db.Numeric(15, 3), default=0)
    pa_qtd         = db.Column(db.Numeric(15, 3), default=0)
    componente_qtd = db.Column(db.Numeric(15, 3), default=0)
    compras_qtd    = db.Column(db.Numeric(15, 3), default=0)
    # MOV local congelado (origem MovimentacaoEstoque desde data_snapshot do ciclo)
    mov_compras    = db.Column(db.Numeric(15, 3), default=0)
    mov_vendas     = db.Column(db.Numeric(15, 3), default=0)
    mov_consumo    = db.Column(db.Numeric(15, 3), default=0)
    mov_producao   = db.Column(db.Numeric(15, 3), default=0)
    # SIST congelado (sum total MovimentacaoEstoque ATIVA, sem filtro de data)
    mov_sist_total = db.Column(db.Numeric(15, 3), default=0)
    # NF inter-company em transito por DESTINO (NFs emitidas mas nao escrituradas no
    # destino). Calculado a partir de NfTransferenciaSnapshot no momento do refresh.
    # Somado ao estoque_<destino> em odoo_total via ConfrontoService.
    em_transito_fb = db.Column(db.Numeric(15, 3), default=0)
    em_transito_cd = db.Column(db.Numeric(15, 3), default=0)
    em_transito_lf = db.Column(db.Numeric(15, 3), default=0)
    refresh_em     = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'cod_produto',
                            name='uq_inv_snapshot_ciclo_cod'),
    )
