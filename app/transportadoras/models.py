from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Transportadora(db.Model):
    __tablename__ = 'transportadoras'

    id = db.Column(db.Integer, primary_key=True)
    cnpj = db.Column(db.String(20), nullable=False)
    razao_social = db.Column(db.String(120), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    uf = db.Column(db.String(2), nullable=False)
    optante = db.Column(db.Boolean, default=False)  # Sim/Não
    condicao_pgto = db.Column(db.String(50), nullable=True)
    freteiro = db.Column(db.Boolean, default=False)  # Define se é freteiro
    ativo = db.Column(db.Boolean, default=True, nullable=False)  # Status ativo/inativo para cotações
    
    # ===== NOVOS CAMPOS DE CONTROLE DE CÁLCULO DE FRETE =====
    # Campos que devem ser aplicados APÓS comparação com frete mínimo
    aplica_gris_pos_minimo = db.Column(db.Boolean, default=False)     # Se True, GRIS é aplicado após frete mínimo
    aplica_adv_pos_minimo = db.Column(db.Boolean, default=False)      # Se True, ADV é aplicado após frete mínimo
    aplica_rca_pos_minimo = db.Column(db.Boolean, default=False)      # Se True, RCA é aplicado após frete mínimo
    aplica_pedagio_pos_minimo = db.Column(db.Boolean, default=False)  # Se True, Pedágio é aplicado após frete mínimo
    aplica_despacho_pos_minimo = db.Column(db.Boolean, default=False) # Se True, Despacho é aplicado após frete mínimo
    aplica_cte_pos_minimo = db.Column(db.Boolean, default=False)      # Se True, CTE é aplicado após frete mínimo
    aplica_tas_pos_minimo = db.Column(db.Boolean, default=False)      # Se True, TAS é aplicado após frete mínimo
    
    # Tipo de cálculo de pedágio
    pedagio_por_fracao = db.Column(db.Boolean, default=True)  # True = arredonda para cima, False = usa valor exato

    # Controle de NF de Pallet
    nao_aceita_nf_pallet = db.Column(db.Boolean, default=False, nullable=False)  # Transportadora não aceita NF de pallet

    def __repr__(self):
        return f'<Transportadora {self.razao_social}>'
