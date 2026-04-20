"""Modelo central do HORA: a moto física (identidade imutável) + log de eventos.

**INVARIANTES** (ver docs/hora/INVARIANTES.md):
- HoraMoto é insert-once. Somente atributos imutáveis.
- Estado atual (localização, status, preço) vive em HoraMotoEvento e tabelas satélite.
- Nunca fazer UPDATE em HoraMoto após insert.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraMoto(db.Model):
    """Identidade imutável da moto física. Uma linha por chassi, insert-once.

    PROIBIDO adicionar status, loja_atual_id, preco_*, data_venda ou qualquer
    atributo que mude durante a vida da moto. Invariante 3.
    """
    __tablename__ = 'hora_moto'

    numero_chassi = db.Column(db.String(30), primary_key=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('hora_modelo.id'), nullable=False, index=True)
    cor = db.Column(db.String(50), nullable=False)
    numero_motor = db.Column(db.String(50), nullable=True, unique=True)
    ano_modelo = db.Column(db.Integer, nullable=True)

    modelo = db.relationship('HoraModelo', backref='motos')

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<HoraMoto {self.numero_chassi}>'


class HoraMotoEvento(db.Model):
    """Log append-only de transições de estado da moto.

    Fonte da verdade para "onde está esta moto agora?".
    Consulta: `SELECT * FROM hora_moto_evento WHERE chassi = ? ORDER BY timestamp DESC LIMIT 1`.
    """
    __tablename__ = 'hora_moto_evento'

    id = db.Column(db.Integer, primary_key=True)
    numero_chassi = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=False,
        index=True,
    )
    tipo = db.Column(db.String(20), nullable=False, index=True)
    # Valores: RECEBIDA, CONFERIDA, TRANSFERIDA, RESERVADA, VENDIDA,
    #          DEVOLVIDA, AVARIADA, FALTANDO_PECA

    origem_tabela = db.Column(db.String(50), nullable=True)
    # Ex.: 'hora_recebimento_conferencia', 'hora_venda_item'
    origem_id = db.Column(db.Integer, nullable=True)

    loja_id = db.Column(db.Integer, db.ForeignKey('hora_loja.id'), nullable=True, index=True)
    operador = db.Column(db.String(100), nullable=True)
    detalhe = db.Column(db.Text, nullable=True)

    timestamp = db.Column(db.DateTime, nullable=False, default=agora_utc_naive, index=True)

    moto = db.relationship('HoraMoto', backref='eventos')
    loja = db.relationship('HoraLoja', backref='eventos_moto')

    __table_args__ = (
        db.Index('ix_hora_moto_evento_chassi_timestamp', 'numero_chassi', 'timestamp'),
    )

    def __repr__(self):
        return f'<HoraMotoEvento {self.numero_chassi} {self.tipo} @ {self.timestamp}>'
