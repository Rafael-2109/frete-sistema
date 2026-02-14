from app import db
from app.utils.timezone import agora_utc_naive


class GrupoTransportadora(db.Model):
    """
    Grupo de transportadoras que operam com multiplos CNPJs.
    Permite vincular CTes emitidos por qualquer CNPJ do grupo
    ao frete de qualquer transportadora membro.

    Exemplo: "JSL Logistica" opera com CNPJ 52.548.435/xxxx E 33.131.079/xxxx.
    Ambas as transportadoras pertencem ao mesmo grupo.
    """
    __tablename__ = 'grupo_transportadora'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)

    # Relationship
    transportadoras = db.relationship('Transportadora', backref='grupo', lazy='dynamic')

    def __repr__(self):
        return f'<GrupoTransportadora {self.nome}>'


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

    # ===== GRUPO DE TRANSPORTADORAS =====
    grupo_transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('grupo_transportadora.id'),
        nullable=True,
        index=True
    )

    # ===== CAMPOS DE CONTROLE DE CÁLCULO DE FRETE =====
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

    # Motorista próprio da empresa (não terceirizado)
    motorista_proprio = db.Column(db.Boolean, default=False, nullable=False)

    # ===== CAMPOS FINANCEIROS =====
    banco = db.Column(db.String(100), nullable=True)
    agencia = db.Column(db.String(20), nullable=True)
    conta = db.Column(db.String(30), nullable=True)
    tipo_conta = db.Column(db.String(20), nullable=True)  # 'corrente' ou 'poupanca'
    pix = db.Column(db.String(100), nullable=True)
    cpf_cnpj_favorecido = db.Column(db.String(20), nullable=True)
    obs_financ = db.Column(db.Text, nullable=True)

    def obter_prefixos_cnpj_grupo(self) -> set:
        """
        Retorna set de prefixos CNPJ (8 digitos) de todas transportadoras
        do mesmo grupo. Se nao pertence a grupo, retorna apenas o proprio.
        """
        prefixo_proprio = ''.join(filter(str.isdigit, self.cnpj or ''))[:8]
        prefixos = {prefixo_proprio} if len(prefixo_proprio) == 8 else set()

        if self.grupo_transportadora_id:
            membros = Transportadora.query.filter(
                Transportadora.grupo_transportadora_id == self.grupo_transportadora_id,
                Transportadora.id != self.id
            ).all()
            for m in membros:
                p = ''.join(filter(str.isdigit, m.cnpj or ''))[:8]
                if len(p) == 8:
                    prefixos.add(p)

        return prefixos

    def __repr__(self):
        return f'<Transportadora {self.razao_social}>'
