"""
Modelo ValePallet - Modelo Legado

Este é o modelo original para controle de Vale Pallets.
Será gradualmente substituído pelo sistema v2 (PalletDocumento + PalletCredito + PalletSolucao).

NOTA: Manter para compatibilidade durante período de transição.
Novos desenvolvimentos devem usar os modelos v2.

Spec: .claude/ralph-loop/specs/prd-reestruturacao-modulo-pallets.md
"""
from datetime import datetime
from app import db
from app.utils.timezone import agora_utc_naive


class ValePallet(db.Model):
    """
    Modelo para controle de Vale Pallets (LEGADO).

    O vale pallet é emitido pelo cliente quando ele não aceita NF de remessa de pallet.
    A transportadora deve retornar o vale para nossa empresa, que então deve
    resolver (coletar os pallets ou vendê-los).

    DEPRECAÇÃO: Este modelo será migrado para:
    - PalletDocumento (documentos tipo CANHOTO ou VALE_PALLET)
    - PalletCredito (rastreamento de créditos)
    - PalletSolucao (resoluções)
    """
    __tablename__ = 'vale_pallets'

    id = db.Column(db.Integer, primary_key=True)

    # Referência à NF de remessa/pallet
    nf_pallet = db.Column(db.String(20), nullable=False, index=True)

    # Dados do vale
    data_emissao = db.Column(db.Date, nullable=False)
    data_validade = db.Column(db.Date, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)

    # Cliente que emitiu o vale
    cnpj_cliente = db.Column(db.String(20), nullable=True, index=True)
    nome_cliente = db.Column(db.String(255), nullable=True)

    # Tipo do vale
    # VALE_PALLET = Vale pallet emitido pelo cliente
    # CANHOTO_ASSINADO = Canhoto da NF assinado pelo cliente
    tipo_vale = db.Column(db.String(20), default='CANHOTO_ASSINADO')

    # Posse e rastreamento
    # TRANSPORTADORA = Transportadora tem o vale, deve entregar
    # NACOM = Nossa empresa tem o vale, deve resolver
    # CLIENTE = Cliente ainda não emitiu
    posse_atual = db.Column(db.String(50), default='TRANSPORTADORA')
    cnpj_posse = db.Column(db.String(20), nullable=True)
    nome_posse = db.Column(db.String(255), nullable=True)

    # Transportadora responsável por entregar o vale
    cnpj_transportadora = db.Column(db.String(20), nullable=True, index=True)
    nome_transportadora = db.Column(db.String(255), nullable=True)

    # Arquivamento físico
    pasta_arquivo = db.Column(db.String(100), nullable=True)
    aba_arquivo = db.Column(db.String(50), nullable=True)

    # Resolução
    # PENDENTE = Ainda não resolvido
    # VENDA = Pallets serão vendidos
    # COLETA = Pallets serão coletados
    tipo_resolucao = db.Column(db.String(20), default='PENDENTE')
    responsavel_resolucao = db.Column(db.String(255), nullable=True)  # Empresa que comprou/coleta
    cnpj_resolucao = db.Column(db.String(20), nullable=True)
    valor_resolucao = db.Column(db.Numeric(15, 2), nullable=True)  # Valor venda ou custo coleta
    nf_resolucao = db.Column(db.String(20), nullable=True)  # NF de venda ou recebimento

    # Status
    recebido = db.Column(db.Boolean, default=False)  # Vale foi recebido pela Nacom
    recebido_em = db.Column(db.DateTime, nullable=True)
    recebido_por = db.Column(db.String(100), nullable=True)

    enviado_coleta = db.Column(db.Boolean, default=False)  # Vale foi enviado para coleta/venda
    enviado_coleta_em = db.Column(db.DateTime, nullable=True)
    enviado_coleta_por = db.Column(db.String(100), nullable=True)

    resolvido = db.Column(db.Boolean, default=False)  # Vale foi totalmente resolvido
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)

    # Observações
    observacao = db.Column(db.Text, nullable=True)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=True)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    atualizado_por = db.Column(db.String(100), nullable=True)

    # Soft delete
    ativo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<ValePallet #{self.id} - NF {self.nf_pallet} - Qtd: {self.quantidade}>"

    @property
    def dias_para_vencer(self):
        """Calcula quantos dias faltam para o vale vencer"""
        if self.data_validade:
            hoje = datetime.now().date()
            delta = self.data_validade - hoje
            return delta.days
        return None

    @property
    def vencido(self):
        """Verifica se o vale está vencido"""
        dias = self.dias_para_vencer
        return dias is not None and dias < 0

    @property
    def prestes_a_vencer(self):
        """Verifica se o vale está prestes a vencer (menos de 30 dias)"""
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= 30

    @property
    def status_display(self):
        """Retorna o status formatado para exibição"""
        if self.resolvido:
            return 'RESOLVIDO'
        if self.enviado_coleta:
            return 'EM RESOLUÇÃO'
        if self.recebido:
            return 'RECEBIDO'
        if self.vencido:
            return 'VENCIDO'
        if self.prestes_a_vencer:
            return 'A VENCER'
        return 'PENDENTE'
