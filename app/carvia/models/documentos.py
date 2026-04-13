"""
Modelos de Documentos CarVia — NFs, Operacoes, Subcontratos
"""

from sqlalchemy import func

from app import db
from app.utils.timezone import agora_utc_naive


class CarviaNf(db.Model):
    """NFs importadas (mercadoria) — PDF DANFE, XML NF-e ou entrada manual"""
    __tablename__ = 'carvia_nfs'

    id = db.Column(db.Integer, primary_key=True)
    numero_nf = db.Column(db.String(20), nullable=False, index=True)
    serie_nf = db.Column(db.String(5))
    chave_acesso_nf = db.Column(db.String(44), unique=True, nullable=True)
    data_emissao = db.Column(db.Date)

    # Emitente (remetente da carga)
    cnpj_emitente = db.Column(db.String(20), nullable=False, index=True)
    nome_emitente = db.Column(db.String(255))
    uf_emitente = db.Column(db.String(2))
    cidade_emitente = db.Column(db.String(100))

    # Destinatario
    cnpj_destinatario = db.Column(db.String(20), index=True)
    nome_destinatario = db.Column(db.String(255))
    uf_destinatario = db.Column(db.String(2))
    cidade_destinatario = db.Column(db.String(100))

    # Valores e pesos
    valor_total = db.Column(db.Numeric(15, 2))
    peso_bruto = db.Column(db.Numeric(15, 3))
    peso_liquido = db.Column(db.Numeric(15, 3))
    quantidade_volumes = db.Column(db.Integer)

    # Arquivos
    arquivo_pdf_path = db.Column(db.String(500))
    arquivo_xml_path = db.Column(db.String(500))
    arquivo_nome_original = db.Column(db.String(255))

    # Tipo de fonte: PDF_DANFE, XML_NFE, MANUAL
    tipo_fonte = db.Column(db.String(20), nullable=False)

    # Status: ATIVA, CANCELADA (soft-delete conforme GAP-20)
    status = db.Column(db.String(20), nullable=False, default='ATIVA', index=True)

    # Auditoria de cancelamento
    cancelado_em = db.Column(db.DateTime)
    cancelado_por = db.Column(db.String(100))
    motivo_cancelamento = db.Column(db.Text)

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    operacoes = db.relationship(
        'CarviaOperacao',
        secondary='carvia_operacao_nfs',
        back_populates='nfs',
        lazy='dynamic'
    )

    def get_faturas_cliente(self):
        """Retorna faturas cliente que referenciam esta NF via itens."""
        from app.carvia.models.faturas import CarviaFaturaCliente, CarviaFaturaClienteItem
        return CarviaFaturaCliente.query.join(
            CarviaFaturaClienteItem,
            CarviaFaturaClienteItem.fatura_cliente_id == CarviaFaturaCliente.id
        ).filter(
            CarviaFaturaClienteItem.nf_id == self.id
        ).all()

    def get_faturas_transportadora(self):
        """Retorna faturas transportadora que referenciam esta NF via itens."""
        from app.carvia.models.faturas import (
            CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
        )
        return CarviaFaturaTransportadora.query.join(
            CarviaFaturaTransportadoraItem,
            CarviaFaturaTransportadoraItem.fatura_transportadora_id == CarviaFaturaTransportadora.id
        ).filter(
            CarviaFaturaTransportadoraItem.nf_id == self.id
        ).all()

    # ------------------------------------------------------------------ #
    #  Validacoes de Bloqueio (Sprint 0 — Fundacao)
    # ------------------------------------------------------------------ #

    def pode_cancelar(self):
        """Verifica se NF pode ser cancelada (soft-delete).

        Bloqueios (fluxo unidirecional — reverter downstream antes):
        - Ja CANCELADA
        - Vinculada a CTe CarVia ativo (operacao != CANCELADO)
        - Em item de Fatura Cliente
        - Em item de Fatura Transportadora
        - Em CarviaFrete ativo via CSV `numeros_nfs` (backfill path)
          — review Sprint 2 IMP-2

        Returns:
            tuple[bool, str]: (pode_cancelar, razao_se_nao com lista)
        """
        if self.status == 'CANCELADA':
            return False, "NF ja esta cancelada."

        bloqueios = []

        # 1. CTe CarVia ativo via junction
        ops_ativas = [op for op in self.operacoes.all() if op.status != 'CANCELADO']
        if ops_ativas:
            ids = ', '.join(op.cte_numero or f"#{op.id}" for op in ops_ativas[:3])
            extra = f" (+{len(ops_ativas)-3})" if len(ops_ativas) > 3 else ""
            bloqueios.append(f"{len(ops_ativas)} CTe(s) CarVia: {ids}{extra}")

        # 2. Fatura Cliente via item
        faturas_c = self.get_faturas_cliente()
        if faturas_c:
            ids = ', '.join(f.numero_fatura for f in faturas_c[:3])
            extra = f" (+{len(faturas_c)-3})" if len(faturas_c) > 3 else ""
            bloqueios.append(f"{len(faturas_c)} Fatura(s) Cliente: {ids}{extra}")

        # 3. Fatura Transportadora via item
        faturas_t = self.get_faturas_transportadora()
        if faturas_t:
            ids = ', '.join(f.numero_fatura for f in faturas_t[:3])
            extra = f" (+{len(faturas_t)-3})" if len(faturas_t) > 3 else ""
            bloqueios.append(f"{len(faturas_t)} Fatura(s) Transportadora: {ids}{extra}")

        # 4. CarviaFrete ativo via CSV numeros_nfs (review Sprint 2 IMP-2)
        #    Backfill path: CarviaFrete nao tem FK para CarviaNf — usa CSV
        #    de numeros de NF. Filtra por correspondencia exata do numero.
        from app.carvia.models.frete import CarviaFrete
        if self.numero_nf:
            fretes_ativos = CarviaFrete.query.filter(
                CarviaFrete.status != 'CANCELADO',
                CarviaFrete.numeros_nfs.isnot(None),
                # Match exato dentro do CSV: ",NF," ou inicio/fim
                db.or_(
                    CarviaFrete.numeros_nfs == self.numero_nf,
                    CarviaFrete.numeros_nfs.like(f"{self.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{self.numero_nf},%"),
                    CarviaFrete.numeros_nfs.like(f"%,{self.numero_nf}"),
                ),
            ).all()
            if fretes_ativos:
                ids = ', '.join(f"#{f.id}" for f in fretes_ativos[:3])
                extra = f" (+{len(fretes_ativos)-3})" if len(fretes_ativos) > 3 else ""
                bloqueios.append(f"{len(fretes_ativos)} Frete(s) CarVia: {ids}{extra}")

        if bloqueios:
            return (
                False,
                "NF vinculada a: " + "; ".join(bloqueios) +
                ". Reverta os documentos na ordem inversa (Fatura → CTe → NF)."
            )

        return True, ""

    def pode_desvincular_de_operacao(self, operacao_id):
        """Verifica se NF pode ser removida de uma operacao especifica.

        Bloqueios:
        - Operacao FATURADA
        - NF referenciada em itens de fatura (cliente ou transportadora)

        Returns:
            tuple[bool, str]: (pode_desvincular, razao_se_nao)
        """
        from app.carvia.models.documentos import CarviaOperacao
        op = db.session.get(CarviaOperacao, operacao_id)
        if not op:
            return False, "Operacao nao encontrada."

        if op.status == 'FATURADO':
            return (
                False,
                f"Operacao {op.cte_numero or op.id} ja faturada. "
                "Desvincule da fatura antes de remover NFs."
            )

        # Checar NF em itens de fatura
        faturas_c = self.get_faturas_cliente()
        if faturas_c:
            ids = ', '.join(f.numero_fatura for f in faturas_c[:3])
            return (
                False,
                f"NF presente em Fatura(s) Cliente: {ids}. "
                "Desvincule a fatura primeiro."
            )

        faturas_t = self.get_faturas_transportadora()
        if faturas_t:
            ids = ', '.join(f.numero_fatura for f in faturas_t[:3])
            return (
                False,
                f"NF presente em Fatura(s) Transportadora: {ids}. "
                "Desanexe a fatura primeiro."
            )

        return True, ""

    def __repr__(self):
        return f'<CarviaNf {self.numero_nf} ({self.tipo_fonte})>'


class CarviaNfItem(db.Model):
    """Itens de produto da NF — extraidos do DANFE PDF ou XML NF-e"""
    __tablename__ = 'carvia_nf_itens'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id'),
        nullable=False,
        index=True
    )

    # Produto
    codigo_produto = db.Column(db.String(60))
    descricao = db.Column(db.String(255))
    ncm = db.Column(db.String(10))
    cfop = db.Column(db.String(10))

    # Quantidades e valores
    unidade = db.Column(db.String(10))
    quantidade = db.Column(db.Numeric(15, 4))
    valor_unitario = db.Column(db.Numeric(15, 4))
    valor_total_item = db.Column(db.Numeric(15, 2))

    # Modelo de moto detectado (persistido na importacao, editavel manualmente)
    modelo_moto_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_modelos_moto.id'),
        nullable=True,
        index=True,
    )

    # Auditoria
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamentos
    nf = db.relationship(
        'CarviaNf',
        backref=db.backref('itens', lazy='dynamic', cascade='all, delete-orphan')
    )
    modelo_moto = db.relationship('CarviaModeloMoto', lazy='select')

    def __repr__(self):
        return f'<CarviaNfItem {self.codigo_produto} qtd={self.quantidade}>'


class CarviaNfVeiculo(db.Model):
    """Veiculo extraido da NF — 1 chassi por linha (motos)"""
    __tablename__ = 'carvia_nf_veiculos'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    chassi = db.Column(db.String(30), nullable=False)
    modelo = db.Column(db.String(100))
    cor = db.Column(db.String(50))
    valor = db.Column(db.Numeric(15, 2))
    ano = db.Column(db.String(20))
    numero_motor = db.Column(db.String(30))
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    # Relacionamento
    nf = db.relationship(
        'CarviaNf',
        backref=db.backref('veiculos', lazy='dynamic', cascade='all, delete-orphan'),
    )

    __table_args__ = (
        db.UniqueConstraint('chassi', name='uq_carvia_nf_veiculo_chassi'),
    )

    def __repr__(self):
        return f'<CarviaNfVeiculo {self.chassi} {self.cor}>'


class CarviaOperacao(db.Model):
    """Operacao principal — 1 CTe CarVia = N NFs do mesmo cliente/destino"""
    __tablename__ = 'carvia_operacoes'

    id = db.Column(db.Integer, primary_key=True)

    # CTe CarVia (pode ser NULL para entrada manual)
    cte_numero = db.Column(db.String(20), index=True)
    cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
    ctrc_numero = db.Column(db.String(30), index=True)  # CTRC SSW/SEFAZ: CAR-{nCT}-{cDV}
    cte_valor = db.Column(db.Numeric(15, 2))
    cte_xml_path = db.Column(db.String(500))
    cte_xml_nome_arquivo = db.Column(db.String(255))
    cte_pdf_path = db.Column(db.String(500))
    cte_data_emissao = db.Column(db.Date)
    icms_aliquota = db.Column(db.Numeric(5, 2))  # Aliquota ICMS do CTe original (ex: 12.00)

    # Cliente (remetente da carga)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255))

    # Rota
    uf_origem = db.Column(db.String(2))
    cidade_origem = db.Column(db.String(100))
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)

    # Pesos (nivel operacao, compartilhado entre subcontratos)
    peso_bruto = db.Column(db.Numeric(15, 3))
    peso_cubado = db.Column(db.Numeric(15, 3))
    peso_utilizado = db.Column(db.Numeric(15, 3))
    valor_mercadoria = db.Column(db.Numeric(15, 2))

    # Cubagem por dimensoes (opcional)
    cubagem_comprimento = db.Column(db.Numeric(10, 2))
    cubagem_largura = db.Column(db.Numeric(10, 2))
    cubagem_altura = db.Column(db.Numeric(10, 2))
    cubagem_fator = db.Column(db.Numeric(10, 2))
    cubagem_volumes = db.Column(db.Integer)

    # NFs referenciadas no CTe XML (persistido para re-linking retroativo)
    # Formato: [{"chave": "44dig", "numero_nf": "123", "cnpj_emitente": "14dig"}]
    nfs_referenciadas_json = db.Column(db.JSON)

    # Tipo e status
    # IMPORTADO, MANUAL_SEM_CTE, MANUAL_FRETEIRO
    tipo_entrada = db.Column(db.String(30), nullable=False)
    # RASCUNHO, COTADO, CONFIRMADO, FATURADO, CANCELADO
    status = db.Column(db.String(20), nullable=False, default='RASCUNHO')

    # Fatura CarVia (ao cliente)
    fatura_cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_cliente.id'),
        nullable=True,
        index=True
    )

    # Auditoria
    observacoes = db.Column(db.Text)

    # Condicao de pagamento e responsavel do frete (propagado da cotacao)
    condicao_pagamento = db.Column(db.String(20), nullable=True)   # A_VISTA | PRAZO
    prazo_dias = db.Column(db.Integer, nullable=True)              # 1-30 se PRAZO
    responsavel_frete = db.Column(db.String(30), nullable=True)    # 100_REMETENTE | 100_DESTINATARIO | 50_50 | PERSONALIZADO
    percentual_remetente = db.Column(db.Numeric(5, 2), nullable=True)
    percentual_destinatario = db.Column(db.Numeric(5, 2), nullable=True)

    # Tomador do frete extraido do CTe XML (<ide>/<toma3> ou <toma4>)
    # REMETENTE | EXPEDIDOR | RECEBEDOR | DESTINATARIO | TERCEIRO
    cte_tomador = db.Column(db.String(20), nullable=True)

    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    nfs = db.relationship(
        'CarviaNf',
        secondary='carvia_operacao_nfs',
        back_populates='operacoes',
        lazy='dynamic'
    )
    # GAP-07: cascade='all, delete-orphan' e INTENCIONAL. SQLAlchemy gerencia
    # o ciclo de vida dos subcontratos via ORM. O DB nao aciona cascade
    # (FK sem ON DELETE CASCADE) — a remocao e feita pelo session.delete() do ORM.
    # Na pratica, operacoes nunca sao deletadas (GAP-20: design sem DELETE).
    subcontratos = db.relationship(
        'CarviaSubcontrato',
        backref='operacao',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    fatura_cliente = db.relationship(
        'CarviaFaturaCliente',
        backref='operacoes',
        foreign_keys=[fatura_cliente_id]
    )

    def calcular_peso_utilizado(self):
        """Calcula peso_utilizado = max(peso_bruto, peso_cubado)"""
        bruto = float(self.peso_bruto or 0)
        cubado = float(self.peso_cubado or 0)
        self.peso_utilizado = max(bruto, cubado)
        return self.peso_utilizado

    # ------------------------------------------------------------------ #
    #  Validacoes de Bloqueio (Sprint 0 — Fundacao)
    #
    #  Metodos pode_* retornam (bool, str) — (pode_executar, razao_se_nao).
    #  Usados por rotas e admin_service para bloquear operacoes que violariam
    #  integridade com documentos downstream. Centralizados no model para
    #  garantir comportamento consistente independente do caller.
    # ------------------------------------------------------------------ #

    def pode_editar_valor(self):
        """Verifica se cte_valor pode ser editado.

        Bloqueios:
        - Operacao CANCELADO
        - Fatura cliente vinculada esta PAGA
        - Fatura cliente vinculada tem conciliacao parcial ativa
          (total_conciliado > 0) — review Sprint 1 IMP-1

        Returns:
            tuple[bool, str]: (pode_editar, razao_se_nao)
        """
        if self.status == 'CANCELADO':
            return False, "Operacao cancelada nao pode ser editada."

        if self.fatura_cliente_id:
            fatura = self.fatura_cliente
            if fatura:
                if fatura.status == 'PAGA':
                    return (
                        False,
                        f"Fatura {fatura.numero_fatura} esta PAGA. "
                        "Desconcilie e desvincule a operacao da fatura antes de alterar o valor."
                    )
                # Review Sprint 1 IMP-1: fatura PENDENTE mas parcialmente
                # conciliada — alterar valor do CTe descoordena com o valor
                # ja conciliado no extrato bancario.
                if fatura.total_conciliado and float(fatura.total_conciliado) > 0:
                    return (
                        False,
                        f"Fatura {fatura.numero_fatura} possui conciliacao "
                        f"parcial ativa (R$ {float(fatura.total_conciliado):.2f}). "
                        "Desconcilie no Extrato Bancario antes de alterar o CTe."
                    )

        return True, ""

    def pode_cancelar(self):
        """Verifica se operacao pode ser cancelada.

        NAO cascadeia — bloqueia se houver qualquer dependencia ativa.

        Bloqueios:
        - Status ja e CANCELADO
        - Status FATURADO com fatura nao-CANCELADA (edge case: se fatura
          ja esta cancelada, permitir cancelar a operacao orfa)
        - Subcontratos ativos (status != CANCELADO)
        - CTe Complementares ativos (status != CANCELADO)
        - CustoEntregas ativos (status != CANCELADO)
        - CarviaFrete ativo (status != CANCELADO) vinculado

        Returns:
            tuple[bool, str]: (pode_cancelar, razao_se_nao)
        """
        if self.status == 'CANCELADO':
            return False, "Operacao ja esta cancelada."

        # Edge case (review Sprint 1 IMP-2): se operacao esta FATURADO,
        # permitir cancelar APENAS se a fatura nao existe mais (dangling FK)
        # ou ja esta CANCELADA. Caso contrario, bloquear e pedir para
        # desvincular primeiro.
        if self.status == 'FATURADO':
            fatura = self.fatura_cliente
            if fatura is None:
                # fatura_cliente_id pode estar NULL ou apontar para
                # registro inexistente — operacao e orfa, permitir cancelar
                pass
            elif fatura.status == 'CANCELADA':
                # Fatura existe mas foi cancelada — permite cancelar
                pass
            else:
                return (
                    False,
                    "Operacao ja faturada. Desvincule da fatura antes de cancelar."
                )

        # Contar dependencias ativas — lazy import para evitar circular
        from app.carvia.models.cte_custos import (
            CarviaCteComplementar, CarviaCustoEntrega,
        )
        from app.carvia.models.frete import CarviaFrete

        subs_ativos = self.subcontratos.filter(
            CarviaSubcontrato.status != 'CANCELADO'
        ).count()

        ctes_comp_ativos = self.ctes_complementares.filter(
            CarviaCteComplementar.status != 'CANCELADO'
        ).count()

        custos_ativos = self.custos_entrega.filter(
            CarviaCustoEntrega.status != 'CANCELADO'
        ).count()

        # Review Sprint 0 ALTO #2: CarviaFrete ativo vinculado
        fretes_ativos = CarviaFrete.query.filter(
            CarviaFrete.operacao_id == self.id,
            CarviaFrete.status != 'CANCELADO',
        ).count()

        if subs_ativos or ctes_comp_ativos or custos_ativos or fretes_ativos:
            partes = []
            if subs_ativos:
                partes.append(f"{subs_ativos} subcontrato(s)")
            if ctes_comp_ativos:
                partes.append(f"{ctes_comp_ativos} CTe Complementar(es)")
            if custos_ativos:
                partes.append(f"{custos_ativos} Custo(s) de Entrega")
            if fretes_ativos:
                partes.append(f"{fretes_ativos} Frete CarVia")
            return (
                False,
                f"Cancele primeiro: {', '.join(partes)}."
            )

        return True, ""

    def calcular_cubagem(self):
        """Calcula peso cubado a partir das dimensoes"""
        if (self.cubagem_comprimento and self.cubagem_largura
                and self.cubagem_altura and self.cubagem_fator
                and self.cubagem_volumes):
            comp = float(self.cubagem_comprimento)
            larg = float(self.cubagem_largura)
            alt = float(self.cubagem_altura)
            fator = float(self.cubagem_fator)
            volumes = int(self.cubagem_volumes)
            if fator > 0:
                self.peso_cubado = (comp * larg * alt / fator) * volumes
                return float(self.peso_cubado)
        return None

    @staticmethod
    def gerar_numero_cte():
        """Gera proximo numero sequencial CTe-###."""
        max_num = db.session.query(
            func.max(CarviaOperacao.cte_numero)
        ).filter(
            CarviaOperacao.cte_numero.ilike('CTe-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('CTe-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'CTe-{next_num:03d}'

    def __repr__(self):
        return f'<CarviaOperacao {self.id} CTe={self.cte_numero} ({self.status})>'


class CarviaOperacaoNf(db.Model):
    """Junction N:N — Operacao <-> NFs"""
    __tablename__ = 'carvia_operacao_nfs'

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=False,
        index=True
    )
    # GAP-08: ondelete='CASCADE' — ao deletar NF, remove junctions automaticamente
    nf_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_nfs.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('operacao_id', 'nf_id', name='uq_operacao_nf'),
    )


class CarviaSubcontrato(db.Model):
    """Subcontratacao — 1 por transportadora por CarviaFrete.

    operacao_id e nullable: CarviaSubcontrato pode ser criado independente
    de CarviaOperacao. CarviaFrete e o eixo central.
    """
    __tablename__ = 'carvia_subcontratos'

    id = db.Column(db.Integer, primary_key=True)
    operacao_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_operacoes.id'),
        nullable=True,
        index=True
    )

    # Transportadora subcontratada
    transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('transportadoras.id'),
        nullable=False,
        index=True
    )

    # Numeracao sequencial por transportadora (auto-increment logico)
    numero_sequencial_transportadora = db.Column(db.Integer, nullable=True)

    # CTe do subcontratado (pode ser NULL para freteiro)
    cte_numero = db.Column(db.String(20), index=True)
    cte_chave_acesso = db.Column(db.String(44), unique=True, nullable=True)
    cte_valor = db.Column(db.Numeric(15, 2))
    cte_xml_path = db.Column(db.String(500))
    cte_xml_nome_arquivo = db.Column(db.String(255))
    cte_pdf_path = db.Column(db.String(500))
    cte_data_emissao = db.Column(db.Date)

    # Cotacao
    valor_cotado = db.Column(db.Numeric(15, 2))
    tabela_frete_id = db.Column(
        db.Integer,
        db.ForeignKey('tabelas_frete.id'),
        nullable=True
    )
    valor_acertado = db.Column(db.Numeric(15, 2))

    # FK para CarviaFrete (N:1 — um frete pode ter N subcontratos multi-leg)
    frete_id = db.Column(
        db.Integer, db.ForeignKey('carvia_fretes.id'),
        nullable=True, index=True
    )

    # Fatura do subcontratado
    fatura_transportadora_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_faturas_transportadora.id'),
        nullable=True,
        index=True
    )

    # PENDENTE, COTADO, CONFIRMADO, FATURADO, CONFERIDO, CANCELADO
    status = db.Column(db.String(20), nullable=False, default='PENDENTE')

    # Conferencia individual (CTe vs TabelaFrete)
    valor_considerado = db.Column(db.Numeric(15, 2), nullable=True)
    status_conferencia = db.Column(db.String(20), nullable=False, default='PENDENTE')
    conferido_por = db.Column(db.String(100), nullable=True)
    conferido_em = db.Column(db.DateTime, nullable=True)
    detalhes_conferencia = db.Column(db.JSON, nullable=True)

    # Pagamento (manual, igual padrao Nacom Frete.valor_pago)
    # Independente do pagamento da fatura (status_pagamento da FT) — granularidade por sub
    valor_pago = db.Column(db.Numeric(15, 2), nullable=True)
    valor_pago_em = db.Column(db.DateTime, nullable=True)
    valor_pago_por = db.Column(db.String(100), nullable=True)

    # Flag de tratativa: True quando existe CarviaAprovacaoSubcontrato PENDENTE
    requer_aprovacao = db.Column(db.Boolean, nullable=False, default=False)

    # Auditoria
    observacoes = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)

    # Relacionamentos
    transportadora = db.relationship('Transportadora', lazy='joined')
    fatura_transportadora = db.relationship(
        'CarviaFaturaTransportadora',
        backref='subcontratos',
        foreign_keys=[fatura_transportadora_id]
    )
    # N:1 com CarviaFrete via frete_id (back_populates com CarviaFrete.subcontratos)
    frete = db.relationship(
        'CarviaFrete',
        foreign_keys=[frete_id],
        back_populates='subcontratos',
    )
    # 1:N com aprovacoes (historico de tratativas)
    aprovacoes = db.relationship(
        'CarviaAprovacaoSubcontrato',
        backref='subcontrato',
        foreign_keys='CarviaAprovacaoSubcontrato.subcontrato_id',
        order_by='CarviaAprovacaoSubcontrato.solicitado_em.desc()',
        lazy='dynamic',
    )

    @staticmethod
    def gerar_numero_sub():
        """Gera proximo numero sequencial Sub-###."""
        max_num = db.session.query(
            func.max(CarviaSubcontrato.cte_numero)
        ).filter(
            CarviaSubcontrato.cte_numero.ilike('Sub-%'),
        ).scalar()

        next_num = 1
        if max_num:
            try:
                next_num = int(max_num.replace('Sub-', '')) + 1
            except (ValueError, TypeError):
                pass
        return f'Sub-{next_num:03d}'

    @property
    def valor_final(self):
        """Retorna valor_acertado se existir, senao valor_cotado"""
        if self.valor_acertado is not None:
            return self.valor_acertado
        return self.valor_cotado

    def __repr__(self):
        return f'<CarviaSubcontrato {self.id} op={self.operacao_id} ({self.status})>'
