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


# ===========================================================================
# Inventário Cíclico — contagem parcial sob demanda (granularidade quant)
# Spec: docs/superpowers/specs/2026-05-31-inventario-ciclico-contagem-ajustes-design.md
# ===========================================================================


class ContagemInventario(db.Model):
    """Contagem cíclica parcial sob demanda (granularidade quant).

    Independente do Confronto (CicloInventario): NÃO há FK. A ligação com o
    Confronto é apenas temporal — o ConfrontoService soma os ajustes destas
    contagens nas colunas INV FB/CD/LF por (cod_produto, empresa) no intervalo
    de data do inventário completo vigente (confronto_service._agg_ajustes_ciclicos).
    """
    __tablename__ = 'inventario_contagem'

    id          = db.Column(db.Integer, primary_key=True)
    codigo      = db.Column(db.String(50), unique=True, nullable=False)
    empresa     = db.Column(db.String(10), nullable=False)        # FB / CD / LF
    filtro_locais        = db.Column(db.JSON)                     # [location_name] (None/[] = todos)
    filtro_codigos       = db.Column(db.JSON)                     # [cod_produto] (None/[] = todos)
    incluir_indisponivel = db.Column(db.Boolean, default=False, nullable=False)
    data_base   = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)  # T0 + corte Confronto
    status      = db.Column(db.String(20), default='BASE_GERADA', nullable=False)  # BASE_GERADA / CONTABILIZADA
    descricao   = db.Column(db.String(200))
    # Resumo (preenchido na contabilização — derivável)
    tot_itens      = db.Column(db.Integer, default=0)
    tot_com_ajuste = db.Column(db.Integer, default=0)
    tot_ajuste_pos = db.Column(db.Numeric(15, 3), default=0)
    tot_ajuste_neg = db.Column(db.Numeric(15, 3), default=0)
    qt_lotes_novos = db.Column(db.Integer, default=0)
    criado_em   = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por  = db.Column(db.String(100))

    itens = db.relationship('ContagemInventarioItem',
                            cascade='all, delete-orphan', lazy='dynamic')

    __table_args__ = (
        db.Index('ix_inventario_contagem_empresa_data', 'empresa', 'data_base'),
    )

    def __repr__(self):
        return f'<ContagemInventario {self.codigo}>'


class ContagemInventarioItem(db.Model):
    """1 linha = 1 stock.quant (location_name + cod + lote) de uma contagem cíclica."""
    __tablename__ = 'inventario_contagem_item'

    id            = db.Column(db.Integer, primary_key=True)
    contagem_id   = db.Column(db.Integer, db.ForeignKey('inventario_contagem.id'),
                              nullable=False, index=True)
    location_name = db.Column(db.String(120), nullable=False)
    location_id   = db.Column(db.Integer)                     # ID Odoo do location (determinismo)
    local_tipo    = db.Column(db.String(20))                  # Estoque / Indisponivel
    is_migracao   = db.Column(db.Boolean, default=False)
    cod_produto   = db.Column(db.String(50), nullable=False, index=True)
    nome_produto  = db.Column(db.String(200))
    lote          = db.Column(db.String(60), nullable=False, default='')  # '' = sem lote (sentinela)
    company_id    = db.Column(db.Integer)                     # 1 FB / 4 CD / 5 LF
    qtd_esperada       = db.Column(db.Numeric(15, 3), default=0)   # saldo Odoo no T0
    reservado_esperado = db.Column(db.Numeric(15, 3), default=0)   # reserved no T0
    contagem      = db.Column(db.Numeric(15, 3))                   # nullable até preencher
    # DOIS ajustes com semânticas DISTINTAS (não confundir):
    #  • ajuste            = contagem − qtd_esperada → delta a APLICAR NO ODOO
    #    (plano consumido pelas skills gestor-estoque-odoo via delta_esperado).
    #    Define a `classe`. Derivado SEMPRE da contagem; NÃO vem da planilha.
    #  • ajuste_inventario = valor LITERAL da coluna AJUSTE da planilha (autoritativo;
    #    vazio = 0) → delta SOMADO ao último inventário na coluna INV/MOV do Confronto
    #    (confronto_service._agg_ajustes_ciclicos). Independe do Odoo (qtd_esperada),
    #    para não carregar a divergência Odoo↔inventário ("semi-ajustado").
    ajuste            = db.Column(db.Numeric(15, 3), default=0)     # contagem − qtd_esperada (→ Odoo)
    ajuste_inventario = db.Column(db.Numeric(15, 3), default=0, nullable=False)  # coluna AJUSTE (→ Confronto)
    classe        = db.Column(db.String(20))                       # NORMAL/RESERVA_FANTASMA/NEGATIVO/LOTE_NOVO/SEM_AJUSTE
    obs           = db.Column(db.String(300))

    __table_args__ = (
        db.UniqueConstraint('contagem_id', 'location_name', 'cod_produto', 'lote',
                            name='uq_inv_contagem_item_quant'),
    )

    def __repr__(self):
        return f'<ContagemInventarioItem {self.cod_produto}/{self.lote}@{self.location_name}>'
