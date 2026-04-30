"""Empréstimo de moto entre nossa loja HORA e loja externa.

Cenários:
  SAIDA   = nossa loja HORA empresta moto para externa (chassi sai do
            estoque). Ressarcimento entra com OUTRA moto do mesmo modelo.
  ENTRADA = externa empresta moto para nossa loja HORA (chassi entra no
            estoque). Ressarcimento sai com OUTRA moto do mesmo modelo.

Estados:
  EM_ABERTO  -> RESSARCIDO (operacao concluida)
  EM_ABERTO  -> CANCELADO (revertido antes do ressarcimento)
"""
from __future__ import annotations

from app import db
from app.utils.timezone import agora_utc_naive


# Constantes de tipo/status
EMPRESTIMO_TIPO_SAIDA = 'SAIDA'      # nossa loja -> externa
EMPRESTIMO_TIPO_ENTRADA = 'ENTRADA'  # externa -> nossa loja
EMPRESTIMO_TIPOS = (EMPRESTIMO_TIPO_SAIDA, EMPRESTIMO_TIPO_ENTRADA)

EMPRESTIMO_STATUS_EM_ABERTO = 'EM_ABERTO'
EMPRESTIMO_STATUS_RESSARCIDO = 'RESSARCIDO'
EMPRESTIMO_STATUS_CANCELADO = 'CANCELADO'
EMPRESTIMO_STATUS_VALIDOS = (
    EMPRESTIMO_STATUS_EM_ABERTO,
    EMPRESTIMO_STATUS_RESSARCIDO,
    EMPRESTIMO_STATUS_CANCELADO,
)


class HoraEmprestimoMoto(db.Model):
    """1 emprestimo = 1 moto que sai/entra. Modelo de saida = modelo de
    ressarcimento (validado no service).
    """
    __tablename__ = 'hora_emprestimo_moto'

    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(db.String(10), nullable=False)
    # SAIDA | ENTRADA — checked via CHECK constraint na migration.
    status = db.Column(
        db.String(15), nullable=False,
        default=EMPRESTIMO_STATUS_EM_ABERTO,
        server_default=EMPRESTIMO_STATUS_EM_ABERTO,
    )

    loja_hora_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_loja.id'),
        nullable=False, index=True,
    )
    loja_externa_nome = db.Column(db.String(200), nullable=False)
    loja_externa_cnpj = db.Column(db.String(20), nullable=True)

    modelo_id = db.Column(
        db.Integer,
        db.ForeignKey('hora_modelo.id'),
        nullable=False, index=True,
    )

    # chassi que sai do nosso estoque:
    #   SAIDA: o emprestado.
    #   ENTRADA: o que enviamos no ressarcimento.
    chassi_saida = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=True, index=True,
    )

    # chassi que entra no nosso estoque:
    #   SAIDA: o ressarcimento.
    #   ENTRADA: o emprestado.
    chassi_entrada = db.Column(
        db.String(30),
        db.ForeignKey('hora_moto.numero_chassi'),
        nullable=True, index=True,
    )

    data_emprestimo = db.Column(db.Date, nullable=False, index=True)
    data_ressarcimento = db.Column(db.Date, nullable=True)

    observacoes = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    ressarcido_em = db.Column(db.DateTime, nullable=True)
    ressarcido_por = db.Column(db.String(100), nullable=True)

    cancelado_em = db.Column(db.DateTime, nullable=True)
    cancelado_por = db.Column(db.String(100), nullable=True)
    cancelamento_motivo = db.Column(db.Text, nullable=True)

    # Relacoes
    loja_hora = db.relationship('HoraLoja')
    modelo = db.relationship('HoraModelo')
    moto_saida = db.relationship(
        'HoraMoto',
        foreign_keys=[chassi_saida],
        primaryjoin='HoraEmprestimoMoto.chassi_saida == HoraMoto.numero_chassi',
    )
    moto_entrada = db.relationship(
        'HoraMoto',
        foreign_keys=[chassi_entrada],
        primaryjoin='HoraEmprestimoMoto.chassi_entrada == HoraMoto.numero_chassi',
    )

    @property
    def em_aberto(self) -> bool:
        return self.status == EMPRESTIMO_STATUS_EM_ABERTO

    @property
    def chassi_pendente(self) -> str | None:
        """Chassi que ainda falta (do lado oposto). None se ressarcido/cancelado."""
        if not self.em_aberto:
            return None
        if self.tipo == EMPRESTIMO_TIPO_SAIDA:
            return None if self.chassi_entrada else 'aguardando entrada'
        return None if self.chassi_saida else 'aguardando saida'

    def __repr__(self):
        return (
            f'<HoraEmprestimoMoto {self.id} {self.tipo} {self.status} '
            f'modelo={self.modelo_id} loja_externa={self.loja_externa_nome!r}>'
        )
