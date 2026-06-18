"""Coletas CarVia — "papel de pao" (stream 3 do redesign, .claire/rascunho.md topico 1).

Uma COLETA agrupa N NFs (rascunho ou reais) em 1 veiculo. O operador trabalha como
papel de pao: digita NF na mao + cliente como achar que e, e conforme as NFs reais
"nascem" no sistema (CarviaNf) cada linha pode ser VINCULADA a NF real — consolidando
o nome livre com o nome real e puxando PDF/CTE/valor.

- Cabecalho `CarviaColeta`: contratado (texto livre + FK opcional a Transportadora),
  placa, valor da coleta (custo -> vira CarviaDespesa tipo COLETA a conciliar),
  destino (local_cd VM/TM — alimenta o Stream 1), data prevista, data coletada (bool+hora).
- Linha `CarviaColetaNf`: numero_nf, cliente (rascunho), cidade/destino, qtd motos/volumes,
  valor total frete, vendedor, transportadora de embarque (rascunho) + FK opcional a CarviaNf.

GAP-20 (modulo CarVia nao deleta): coletas sao CANCELADAS via status, nao apagadas.
Linhas (CarviaColetaNf) podem ser editadas/removidas enquanto a coleta esta em RASCUNHO.
"""

from app import db
from app.utils.timezone import agora_utc_naive

# Status da coleta
COLETA_STATUS_RASCUNHO = 'RASCUNHO'
COLETA_STATUS_COLETADA = 'COLETADA'
COLETA_STATUS_CANCELADA = 'CANCELADA'
COLETA_STATUSES = (COLETA_STATUS_RASCUNHO, COLETA_STATUS_COLETADA, COLETA_STATUS_CANCELADA)

# Tipo de despesa gerado pela coleta (adicionado a TIPOS_DESPESA em despesa_routes)
COLETA_TIPO_DESPESA = 'COLETA'


class CarviaColeta(db.Model):
    """Coleta CarVia ('papel de pao'): N NFs em 1 veiculo, com custo a conciliar."""
    __tablename__ = 'carvia_coletas'

    id = db.Column(db.Integer, primary_key=True)

    # Contratado (papel de pao): texto livre + vinculo opcional a Transportadora cadastrada
    contratado_nome = db.Column(db.String(255))
    transportadora_id = db.Column(
        db.Integer, db.ForeignKey('transportadoras.id'), nullable=True, index=True
    )

    placa = db.Column(db.String(10))
    valor_coleta = db.Column(db.Numeric(15, 2))  # custo pago ao contratado (-> CarviaDespesa)

    # Destino = CD de expedicao (Victorio Marchezine / Tenente Marques). Alimenta o Stream 1:
    # ao vincular uma linha a CarviaNf, propaga este local_cd para a NF. Constantes em
    # app/utils/local_cd.py.
    local_cd = db.Column(
        db.String(20), nullable=False, default='VICTORIO_MARCHEZINE',
        server_default='VICTORIO_MARCHEZINE',
        info={'description': 'Destino: VICTORIO_MARCHEZINE | TENENTE_MARQUES'},
    )

    data_prevista = db.Column(db.Date)            # previsao de COLETA
    data_prevista_chegada = db.Column(db.Date)    # previsao de CHEGADA na matriz/CD
    data_coletada = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    data_coletada_em = db.Column(db.DateTime)  # BRT naive

    # Despesa a conciliar (criada ao marcar coletada). FK opcional.
    despesa_id = db.Column(
        db.Integer, db.ForeignKey('carvia_despesas.id'), nullable=True, index=True
    )

    status = db.Column(
        db.String(20), nullable=False, default=COLETA_STATUS_RASCUNHO,
        server_default=COLETA_STATUS_RASCUNHO, index=True,
    )
    observacoes = db.Column(db.Text)

    criado_por = db.Column(db.String(150))
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='carvia_coletas')
    despesa = db.relationship('CarviaDespesa', foreign_keys=[despesa_id])
    nfs = db.relationship(
        'CarviaColetaNf', backref='coleta', lazy='dynamic',
        cascade='all, delete-orphan', order_by='CarviaColetaNf.id',
    )

    @property
    def numero_coleta(self):
        """Codigo exibivel COL-### (id zero-padded)."""
        return f'COL-{self.id:03d}'

    @property
    def total_nfs(self):
        return self.nfs.count()

    @property
    def total_motos(self):
        return sum((n.qtd_motos or 0) for n in self.nfs)

    @property
    def total_vinculadas(self):
        return self.nfs.filter(CarviaColetaNf.carvia_nf_id.isnot(None)).count()

    @property
    def contratado_efetivo(self):
        """Nome do contratado: razao_social da transportadora vinculada, senao o texto livre."""
        if self.transportadora is not None:
            return self.transportadora.razao_social
        return self.contratado_nome

    def pode_editar(self):
        """Coleta so e editavel enquanto RASCUNHO (apos coletada/cancelada, congela)."""
        return self.status == COLETA_STATUS_RASCUNHO

    def __repr__(self):
        return f'<CarviaColeta {self.numero_coleta} ({self.status})>'


class CarviaColetaNf(db.Model):
    """Linha do papel de pao: uma NF (rascunho ou real) dentro de uma coleta."""
    __tablename__ = 'carvia_coleta_nfs'
    # Uma CarviaNf real pertence a no maximo 1 linha de coleta (NULL = rascunho, multiplos ok).
    __table_args__ = (
        db.UniqueConstraint('carvia_nf_id', name='uq_carvia_coleta_nf'),
    )

    id = db.Column(db.Integer, primary_key=True)
    coleta_id = db.Column(
        db.Integer, db.ForeignKey('carvia_coletas.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )

    # Rascunho (como a pessoa digita / xerox da planilha)
    numero_nf = db.Column(db.String(20))
    nome_cliente_rascunho = db.Column(db.String(255))
    cidade_destino = db.Column(db.String(120))
    # UF do destino: rascunho (digitavel) que se CONSOLIDA com a NF real ao vincular
    # (uf_destinatario da CarviaNf vence, igual a cidade/nome — papel de pao -> real).
    uf = db.Column(db.String(2))
    qtd_motos = db.Column(db.Integer)             # qtd de motos / volumes
    valor_frete = db.Column(db.Numeric(15, 2))    # "valor total frete" da linha
    vendedor = db.Column(db.String(150))
    transportadora_embarque = db.Column(db.String(255))  # transportadora de embarque (rascunho)

    # Vinculo a NF real (consolida rascunho <-> dados reais; bridge p/ recebimento por chassi)
    carvia_nf_id = db.Column(
        db.Integer, db.ForeignKey('carvia_nfs.id'), nullable=True, index=True
    )

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    carvia_nf = db.relationship('CarviaNf')

    @property
    def vinculada(self):
        return self.carvia_nf_id is not None

    @property
    def nome_cliente_efetivo(self):
        """Nome real (da NF vinculada) quando houver; senao o rascunho digitado."""
        if self.carvia_nf is not None:
            return self.carvia_nf.nome_destinatario or self.nome_cliente_rascunho
        return self.nome_cliente_rascunho

    def __repr__(self):
        vinc = f' -> NF#{self.carvia_nf_id}' if self.carvia_nf_id else ''
        return f'<CarviaColetaNf {self.numero_nf or "?"}{vinc}>'
