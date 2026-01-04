from app import db
from datetime import datetime

class ContatoAgendamento(db.Model):
    __tablename__ = 'contatos_agendamento'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False, index=True)
    forma = db.Column(db.String(50))  # Portal, Telefone, E-mail, WhatsApp
    contato = db.Column(db.String(255))  # Usuário, telefone ou e-mail
    observacao = db.Column(db.String(255))
    nao_aceita_nf_pallet = db.Column(db.Boolean, default=False, nullable=False)  # Cliente não aceita NF de pallet
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContatoAgendamento {self.cnpj} - {self.forma}>"