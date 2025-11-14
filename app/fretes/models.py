from app import db
from datetime import datetime
from app.utils.timezone import agora_brasil

class Frete(db.Model):
    """
    Modelo principal para registro de fretes
    1 Frete = 1 CTe = 1 Valor = 1 Vencimento = 1 CNPJ = 1 Embarque
    Mas pode ter N pedidos e N NFs por frete
    """
    __tablename__ = 'fretes'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False)
    cnpj_cliente = db.Column(db.String(20), nullable=False, index=True)
    nome_cliente = db.Column(db.String(255), nullable=False)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    
    # Dados básicos do frete
    tipo_carga = db.Column(db.String(20), nullable=False)  # 'FRACIONADA' ou 'DIRETA'
    modalidade = db.Column(db.String(50), nullable=False)  # VALOR, PESO, VAN, etc.
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)
    
    # Totais das NFs deste CNPJ no embarque
    peso_total = db.Column(db.Float, nullable=False)
    valor_total_nfs = db.Column(db.Float, nullable=False)
    quantidade_nfs = db.Column(db.Integer, nullable=False)
    numeros_nfs = db.Column(db.Text, nullable=False)  # Lista das NFs separadas por vírgula
    
    # Dados da tabela utilizada (copiados do embarque/embarque_item)
    tabela_nome_tabela = db.Column(db.String(100))
    tabela_valor_kg = db.Column(db.Float)
    tabela_percentual_valor = db.Column(db.Float)
    tabela_frete_minimo_valor = db.Column(db.Float)
    tabela_frete_minimo_peso = db.Column(db.Float)
    tabela_icms = db.Column(db.Float)
    tabela_percentual_gris = db.Column(db.Float)
    tabela_pedagio_por_100kg = db.Column(db.Float)
    tabela_valor_tas = db.Column(db.Float)
    tabela_percentual_adv = db.Column(db.Float)
    tabela_percentual_rca = db.Column(db.Float)
    tabela_valor_despacho = db.Column(db.Float)
    tabela_valor_cte = db.Column(db.Float)
    tabela_icms_incluso = db.Column(db.Boolean, default=False)
    tabela_icms_destino = db.Column(db.Float)
    
    # ===== NOVOS CAMPOS DE VALORES MÍNIMOS E ICMS =====
    tabela_gris_minimo = db.Column(db.Float, default=0)    # Valor mínimo de GRIS
    tabela_adv_minimo = db.Column(db.Float, default=0)     # Valor mínimo de ADV
    tabela_icms_proprio = db.Column(db.Float, nullable=True)  # ICMS próprio da tabela
    
    # OS 4 TIPOS DE VALORES DO FRETE
    valor_cotado = db.Column(db.Float, nullable=False)  # Calculado automaticamente pela tabela
    valor_cte = db.Column(db.Float)  # Valor cobrado pela transportadora
    valor_considerado = db.Column(db.Float)  # Valor que consideramos válido (inicialmente = valor_cotado)
    valor_pago = db.Column(db.Float)  # Valor que efetivamente pagamos
    
    # Dados do CTe
    numero_cte = db.Column(db.String(255), index=True)
    data_emissao_cte = db.Column(db.Date)
    vencimento = db.Column(db.Date)
    
    # Fatura de frete (uma fatura pode ter N fretes)
    fatura_frete_id = db.Column(db.Integer, db.ForeignKey('faturas_frete.id'))
    
    # Status e aprovação
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, EM_TRATATIVA, APROVADO, REJEITADO, PAGO, CANCELADO
    requer_aprovacao = db.Column(db.Boolean, default=False)
    aprovado_por = db.Column(db.String(100))
    aprovado_em = db.Column(db.DateTime)
    observacoes_aprovacao = db.Column(db.Text)
    
    # Controle
    considerar_diferenca = db.Column(db.Boolean, default=False)  # Para lançar na conta corrente mesmo com diferença até R$ 5,00
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    lancado_em = db.Column(db.DateTime)
    lancado_por = db.Column(db.String(100))
    
    # Relacionamentos
    embarque = db.relationship('Embarque', backref='fretes')
    transportadora = db.relationship('Transportadora', backref='fretes')
    fatura_frete = db.relationship('FaturaFrete', backref='fretes')
    despesas_extras = db.relationship('DespesaExtra', backref='frete', cascade='all, delete-orphan')

    def diferenca_cotado_cte(self):
        """Retorna a diferença entre valor cotado e valor CTe"""
        if self.valor_cte and self.valor_cotado:
            return self.valor_cte - self.valor_cotado
        return 0

    def diferenca_considerado_pago(self):
        """Retorna a diferença entre valor considerado e valor pago (para conta corrente)"""
        if self.valor_pago and self.valor_considerado:
            return self.valor_pago - self.valor_considerado
        return 0

    def classificacao_valor_pago_considerado(self):
        """Classifica a relação entre valor pago e considerado"""
        if not self.valor_pago or not self.valor_considerado:
            return ""
        
        if self.valor_pago < self.valor_considerado:
            return "Valor abaixo da tabela"
        elif self.valor_pago > self.valor_considerado:
            return "Transportadora deve para a Nacom"
        else:
            return "Valores iguais"

    def classificacao_valor_cte_cotado(self):
        """Classifica a relação entre valor CTe e cotado"""
        if not self.valor_cte or not self.valor_cotado:
            return ""
        
        if self.valor_cte > self.valor_cotado:
            return "Cobrança maior que a Cotação"
        elif self.valor_cte < self.valor_cotado:
            return "Cobrança menor que a Cotação"
        else:
            return "Valores iguais"

    def requer_aprovacao_por_valor(self):
        """
        Verifica se requer aprovação baseado nas regras de R$ 5,00
        - Diferença > R$ 5,00 entre Valor Considerado e Valor Pago: EM_TRATATIVA 
        - Diferença > R$ 5,00 entre Valor Considerado e Valor Cotado: EM_TRATATIVA
        """
        requer = False
        motivos = []
        
        # Verifica diferença entre valor considerado e valor pago
        if self.valor_considerado and self.valor_pago:
            diferenca = abs(self.valor_considerado - self.valor_pago)
            if diferenca > 5.00:
                requer = True
                if self.valor_pago > self.valor_considerado:
                    motivos.append(f"Valor Pago (R$ {self.valor_pago:.2f}) superior ao Considerado (R$ {self.valor_considerado:.2f}) em R$ {diferenca:.2f}")
                else:
                    motivos.append(f"Valor Considerado (R$ {self.valor_considerado:.2f}) superior ao Pago (R$ {self.valor_pago:.2f}) em R$ {diferenca:.2f}")
        
        # Verifica diferença entre valor considerado e valor cotado
        if self.valor_considerado and self.valor_cotado:
            diferenca = abs(self.valor_considerado - self.valor_cotado)
            if diferenca > 5.00:
                requer = True
                if self.valor_considerado > self.valor_cotado:
                    motivos.append(f"Valor Considerado (R$ {self.valor_considerado:.2f}) superior ao Cotado (R$ {self.valor_cotado:.2f}) em R$ {diferenca:.2f}")
                else:
                    motivos.append(f"Valor Cotado (R$ {self.valor_cotado:.2f}) superior ao Considerado (R$ {self.valor_considerado:.2f}) em R$ {diferenca:.2f}")
        
        return requer, motivos

    def deve_lancar_conta_corrente(self):
        """
        Verifica se deve lançar na conta corrente baseado nas regras:
        - Diferença até R$ 5,00 E flag 'considerar_diferenca' = True: lança
        - Diferença até R$ 5,00 E flag 'considerar_diferenca' = False: não lança
        - Diferença > R$ 5,00: só lança após aprovação
        """
        if not self.valor_considerado or not self.valor_pago:
            return False, "Valores não informados"

        diferenca = abs(self.valor_considerado - self.valor_pago)

        if diferenca <= 5.00:
            if self.considerar_diferenca:
                return True, f"Diferença de R$ {diferenca:.2f} será lançada (flag ativa)"
            else:
                return False, f"Diferença de R$ {diferenca:.2f} ignorada (flag inativa)"
        else:
            if self.status == 'APROVADO':
                return True, f"Diferença de R$ {diferenca:.2f} aprovada"
            else:
                return False, f"Diferença de R$ {diferenca:.2f} requer aprovação"

    def buscar_ctes_relacionados(self):
        """
        Busca CTes relacionados do Odoo baseado em:
        1. Pelo menos 1 NF em comum entre frete e CTe
        2. Prefixo do CNPJ da transportadora (primeiros 8 dígitos: XX.XXX.XXX)
        3. ✅ Tomador deve ser a empresa (CNPJ começa com 61.724.241)

        Returns:
            list: Lista de ConhecimentoTransporte relacionados
        """
        if not self.numeros_nfs or not self.transportadora:
            return []

        # Extrair lista de NFs do frete
        nfs_frete = [nf.strip() for nf in self.numeros_nfs.split(',') if nf.strip()]

        if not nfs_frete:
            return []

        # Extrair prefixo do CNPJ da transportadora (primeiros 8 dígitos)
        # Formato: XX.XXX.XXX/XXXX-XX -> pegar XX.XXX.XXX
        cnpj_transportadora = self.transportadora.cnpj or ''
        # Remover formatação e pegar primeiros 8 dígitos
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj_transportadora))

        if len(cnpj_limpo) < 8:
            return []

        prefixo_cnpj = cnpj_limpo[:8]  # Primeiros 8 dígitos

        # Buscar CTes que:
        # 1. Tenham prefixo CNPJ da transportadora batendo
        # 2. Tenham pelo menos 1 NF em comum
        # 3. Estejam ativos
        # 4. ✅ Tomador seja a empresa
        from sqlalchemy import and_, or_

        ctes_relacionados = ConhecimentoTransporte.query.filter(
            and_(
                ConhecimentoTransporte.ativo == True,
                ConhecimentoTransporte.cnpj_emitente.isnot(None),
                ConhecimentoTransporte.numeros_nfs.isnot(None),
                ConhecimentoTransporte.tomador_e_empresa == True  # ✅ FILTRO ADICIONADO
            )
        ).all()

        # Filtrar em Python (mais eficiente que LIKE no SQL para múltiplas NFs)
        ctes_validos = []

        for cte in ctes_relacionados:
            # Verificar prefixo CNPJ
            cnpj_cte_limpo = ''.join(filter(str.isdigit, cte.cnpj_emitente or ''))
            if len(cnpj_cte_limpo) < 8 or cnpj_cte_limpo[:8] != prefixo_cnpj:
                continue

            # Verificar se tem pelo menos 1 NF em comum
            nfs_cte = [nf.strip() for nf in (cte.numeros_nfs or '').split(',') if nf.strip()]

            # Interseção de NFs
            nfs_comuns = set(nfs_frete) & set(nfs_cte)

            if nfs_comuns:
                ctes_validos.append(cte)

        return ctes_validos

    def __repr__(self):
        return f'<Frete {self.id} - {self.nome_cliente} - CTe: {self.numero_cte}>'


class FaturaFrete(db.Model):
    """
    Modelo para faturas de frete emitidas pelas transportadoras
    1 Fatura pode ter N CTes de N CNPJs
    """
    __tablename__ = 'faturas_frete'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    numero_fatura = db.Column(db.String(50), nullable=False, index=True)
    data_emissao = db.Column(db.Date, nullable=False)
    valor_total_fatura = db.Column(db.Float, nullable=False)
    vencimento = db.Column(db.Date)
    
    # Arquivo da fatura
    arquivo_pdf = db.Column(db.String(255))  # Caminho para o arquivo PDF da fatura
    
    # Status da conferência
    status_conferencia = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, EM_CONFERENCIA, CONFERIDO
    conferido_por = db.Column(db.String(100))
    conferido_em = db.Column(db.DateTime)
    observacoes_conferencia = db.Column(db.Text)
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='faturas_frete')

    def total_fretes(self):
        """Retorna o total de fretes desta fatura"""
        return len(self.fretes)

    def valor_total_fretes(self):
        """Retorna o valor total dos fretes desta fatura"""
        return sum(f.valor_cte or 0 for f in self.fretes)
    
    def total_despesas_extras(self):
        """Retorna o total de despesas extras vinculadas a esta fatura via FK"""
        return DespesaExtra.query.filter_by(fatura_frete_id=self.id).count()

    def valor_total_despesas_extras(self):
        """Retorna o valor total das despesas extras vinculadas a esta fatura via FK"""
        despesas = DespesaExtra.query.filter_by(fatura_frete_id=self.id).all()
        return sum(despesa.valor_despesa for despesa in despesas)

    def todas_despesas_extras(self):
        """Retorna todas as despesas extras vinculadas a esta fatura via FK"""
        return DespesaExtra.query.filter_by(fatura_frete_id=self.id).all()

    def __repr__(self):
        return f'<FaturaFrete {self.numero_fatura} - {self.transportadora.razao_social if self.transportadora else "N/A"}>'


class DespesaExtra(db.Model):
    """
    Modelo para despesas extras dos fretes
    N despesas extras / 1 frete
    """
    __tablename__ = 'despesas_extras'

    id = db.Column(db.Integer, primary_key=True)
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)
    fatura_frete_id = db.Column(db.Integer, db.ForeignKey('faturas_frete.id'), nullable=True, index=True)

    # Tipos de despesa (conforme readme.md)
    TIPOS_DESPESA = [
        'REENTREGA', 'TDE', 'PERNOITE', 'DEVOLUÇÃO', 'DIARIA',
        'COMPLEMENTO DE FRETE', 'COMPRA/AVARIA', 'TRANSFERENCIA',
        'DESCARGA', 'ESTACIONAMENTO', 'CARRO DEDICADO', 'ARMAZENAGEM'
    ]
    
    # Setores responsáveis (conforme readme.md)
    SETORES_RESPONSAVEIS = [
        'COMERCIAL', 'QUALIDADE', 'FISCAL', 'FINANCEIRO',
        'LOGISTICA', 'COMPRAS'
    ]
    
    # Motivos das despesas (conforme readme.md)
    MOTIVOS_DESPESA = [
        'PEDIDO EM DESACORDO', 'PROBLEMA NO CLIENTE', 'SEM AGENDA',
        'DIVERGENCIA DE CADASTRO', 'ARQUIVO XML', 'FORA DO PADRÃO',
        'FALTA MERCADORIA', 'ATRASO', 'INVERSÃO', 'EXCESSO DE VEICULO',
        'VAZAMENTO', 'AUTORIZACAO INDEVIDA', 'PROBLEMA NO BOLETO',
        'COLETA CANCELADA', 'COLETA DE IMPROPRIOS', 'EXIGENCIA TRANSPORTADORA',
        'AJUDANTE DESCARGA', 'DEMORA COLETA', 'COMPLEMENTO DE FRETE',
        'DIVERGENTE IMPOSTO NACOM', 'ENTREGA 2° ANDAR', 'ENTREGA NOTURNA',
        'CUSTO DO PRODUTO', 'DEMORA RECEBIMENTO', 'SEM MONITORAMENTO', 'AVARIA'
    ]
    
    tipo_despesa = db.Column(db.String(50), nullable=False)
    setor_responsavel = db.Column(db.String(20), nullable=False)
    motivo_despesa = db.Column(db.String(50), nullable=False)
    
    # Documento da despesa
    tipo_documento = db.Column(db.String(20), nullable=False)  # CTe, NFS, RECIBO, etc.
    numero_documento = db.Column(db.String(50), nullable=False)
    
    # Valores
    valor_despesa = db.Column(db.Float, nullable=False)
    vencimento_despesa = db.Column(db.Date)
    
    # Observações
    observacoes = db.Column(db.Text)
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)

    # Relacionamentos
    fatura_frete = db.relationship('FaturaFrete', backref='despesas_extras')

    def __repr__(self):
        return f'<DespesaExtra {self.tipo_despesa} - R$ {self.valor_despesa}>'


class ContaCorrenteTransportadora(db.Model):
    """
    Modelo para conta corrente por transportadora
    Controla diferenças entre valores pagos e considerados
    """
    __tablename__ = 'conta_corrente_transportadoras'

    id = db.Column(db.Integer, primary_key=True)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)
    
    # Tipo de movimentação
    tipo_movimentacao = db.Column(db.String(20), nullable=False)  # CREDITO, DEBITO, COMPENSACAO
    
    # Valores
    valor_diferenca = db.Column(db.Float, nullable=False)  # Diferença entre valor_pago e valor_considerado
    valor_credito = db.Column(db.Float, default=0)  # Para créditos a favor da empresa
    valor_debito = db.Column(db.Float, default=0)  # Para débitos a favor da transportadora
    
    # Descrição da movimentação
    descricao = db.Column(db.String(255), nullable=False)
    observacoes = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='ATIVO')  # ATIVO, COMPENSADO, DESCONSIDERADO
    compensado_em = db.Column(db.DateTime)
    compensado_por = db.Column(db.String(100))
    compensacao_frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'))  # Frete usado para compensação
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    criado_por = db.Column(db.String(100), nullable=False)
    
    # Relacionamentos
    transportadora = db.relationship('Transportadora', backref='conta_corrente')
    frete = db.relationship('Frete', foreign_keys=[frete_id], backref='movimentacoes_conta_corrente')
    frete_compensacao = db.relationship('Frete', foreign_keys=[compensacao_frete_id])

    def __repr__(self):
        return f'<ContaCorrente {self.transportadora.nome if self.transportadora else "N/A"} - {self.tipo_movimentacao} R$ {abs(self.valor_diferenca)}>'


class AprovacaoFrete(db.Model):
    """
    Modelo para controle de aprovações de fretes
    """
    __tablename__ = 'aprovacoes_frete'

    id = db.Column(db.Integer, primary_key=True)
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=False)
    
    # Dados da aprovação
    status = db.Column(db.String(20), default='PENDENTE')  # PENDENTE, APROVADO, REJEITADO
    solicitado_por = db.Column(db.String(100), nullable=False)
    solicitado_em = db.Column(db.DateTime, default=datetime.utcnow)
    motivo_solicitacao = db.Column(db.Text)
    
    # Dados do aprovador
    aprovador = db.Column(db.String(100))
    aprovado_em = db.Column(db.DateTime)
    observacoes_aprovacao = db.Column(db.Text)
    
    # Relacionamentos
    frete = db.relationship('Frete', backref='aprovacao')

    def __repr__(self):
        return f'<AprovacaoFrete {self.frete_id} - {self.status}>'


# Manter o modelo antigo para compatibilidade (será migrado)
class FreteLancado(db.Model):
    __tablename__ = 'fretes_lancados'

    id = db.Column(db.Integer, primary_key=True)
    embarque_id = db.Column(db.Integer, db.ForeignKey('embarques.id'), nullable=False)
    nota_fiscal = db.Column(db.String(20), nullable=False)
    cliente = db.Column(db.String(120), nullable=False)
    transportadora_id = db.Column(db.Integer, db.ForeignKey('transportadoras.id'), nullable=False)
    tipo_carga = db.Column(db.String(20), nullable=False)  # 'FRACIONADA' ou 'DIRETA'
    modalidade = db.Column(db.String(50), nullable=False)  # VALOR, PESO, VAN, etc.
    uf_destino = db.Column(db.String(2), nullable=False)
    cidade_destino = db.Column(db.String(100), nullable=False)

    peso = db.Column(db.Float, nullable=False)
    valor_nf = db.Column(db.Float, nullable=False)
    valor_frete = db.Column(db.Float, nullable=False)

    cte = db.Column(db.String(50))  # número do CTE
    vencimento = db.Column(db.Date)
    fatura = db.Column(db.String(50))
    divergencia = db.Column(db.String(255))

    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    embarque = db.relationship('Embarque', backref='fretes_lancados')
    transportadora = db.relationship('Transportadora')


class ConhecimentoTransporte(db.Model):
    """
    Modelo para registrar Conhecimentos de Transporte (CTe) do Odoo
    e vincular com fretes do sistema

    FONTE: Modelo l10n_br_ciel_it_account.dfe do Odoo (campo is_cte=True)
    FILTRO ODOO: ["&", "|", ("active", "=", True), ("active", "=", False), ("is_cte", "=", True)]
    """
    __tablename__ = 'conhecimento_transporte'

    id = db.Column(db.Integer, primary_key=True)

    # ================================================
    # VÍNCULO COM ODOO
    # ================================================
    dfe_id = db.Column(db.String(50), nullable=False, unique=True, index=True)  # ID do DFe no Odoo
    odoo_ativo = db.Column(db.Boolean, default=True)  # Campo 'active' do Odoo
    odoo_name = db.Column(db.String(100), nullable=True)  # Campo 'name' do Odoo (ex: DFE/2025/15797)

    # Status do Odoo (selection)
    # Valores: 01-Rascunho, 02-Sincronizado, 03-Ciência/Confirmado, 04-PO, 05-Rateio, 06-Concluído, 07-Rejeitado
    odoo_status_codigo = db.Column(db.String(2), nullable=True, index=True)  # Código (ex: '06')
    odoo_status_descricao = db.Column(db.String(50), nullable=True)  # Descrição (ex: 'Concluído')

    # ================================================
    # DADOS DO CTe (campos do DFe do Odoo)
    # ================================================
    # Chave e Numeração
    chave_acesso = db.Column(db.String(44), nullable=True, unique=True, index=True)  # protnfe_infnfe_chnfe
    numero_cte = db.Column(db.String(20), nullable=True, index=True)    # nfe_infnfe_ide_nnf
    serie_cte = db.Column(db.String(10), nullable=True)                 # nfe_infnfe_ide_serie

    # Datas
    data_emissao = db.Column(db.Date, nullable=True, index=True)        # nfe_infnfe_ide_dhemi
    data_entrada = db.Column(db.Date, nullable=True)                    # l10n_br_data_entrada

    # Valores
    valor_total = db.Column(db.Numeric(15, 2), nullable=True)           # nfe_infnfe_total_icmstot_vnf
    valor_frete = db.Column(db.Numeric(15, 2), nullable=True)           # nfe_infnfe_total_icms_vfrete
    valor_icms = db.Column(db.Numeric(15, 2), nullable=True)            # nfe_infnfe_total_icms_vicms

    # Vencimento (será preenchido posteriormente via fatura)
    vencimento = db.Column(db.Date, nullable=True)

    # Emissor (Transportadora)
    cnpj_emitente = db.Column(db.String(20), nullable=True, index=True) # nfe_infnfe_emit_cnpj
    nome_emitente = db.Column(db.String(255), nullable=True)            # nfe_infnfe_emit_xnome
    ie_emitente = db.Column(db.String(20), nullable=True)               # nfe_infnfe_emit_ie

    # Destinatário (Cliente que recebe a mercadoria)
    cnpj_destinatario = db.Column(db.String(20), nullable=True, index=True)  # nfe_infnfe_dest_cnpj

    # Remetente (Quem envia a mercadoria)
    cnpj_remetente = db.Column(db.String(20), nullable=True, index=True)     # nfe_infnfe_rem_cnpj

    # Expedidor (Se houver)
    cnpj_expedidor = db.Column(db.String(20), nullable=True)            # nfe_infnfe_exped_cnpj

    # Municípios (para rastreio de rotas)
    municipio_inicio = db.Column(db.String(10), nullable=True)          # cte_infcte_ide_cmunini (código IBGE)
    municipio_fim = db.Column(db.String(10), nullable=True)             # cte_infcte_ide_cmunfim (código IBGE)

    # Tomador do serviço
    tomador = db.Column(db.String(1), nullable=True)                    # cte_infcte_ide_toma3_toma (1-Remetente, 2-Expedidor, 3-Recebedor, 4-Destinatário)

    # ✅ Flag indicando se o tomador é a empresa (CNPJ começa com 61.724.241)
    tomador_e_empresa = db.Column(db.Boolean, default=False, nullable=False, index=True)

    # Dados Adicionais
    informacoes_complementares = db.Column(db.Text, nullable=True)      # nfe_infnfe_infadic_infcpl

    # Tipo de pedido Odoo
    tipo_pedido = db.Column(db.String(20), nullable=True)               # l10n_br_tipo_pedido (ex: 'servico')

    # Números das NFs contidas no CTe (extraídos de refs_ids)
    numeros_nfs = db.Column(db.Text, nullable=True)                     # String separada por vírgula: "141768,141769,141770,141771"

    # ================================================
    # ARQUIVOS (PDF/XML)
    # ================================================
    cte_pdf_path = db.Column(db.String(500), nullable=True)  # Caminho S3/local do PDF
    cte_xml_path = db.Column(db.String(500), nullable=True)  # Caminho S3/local do XML
    cte_pdf_nome_arquivo = db.Column(db.String(255), nullable=True)  # l10n_br_pdf_dfe_fname
    cte_xml_nome_arquivo = db.Column(db.String(255), nullable=True)  # l10n_br_xml_dfe_fname

    # ================================================
    # RELACIONAMENTOS ODOO (para referência futura)
    # ================================================
    odoo_partner_id = db.Column(db.Integer, nullable=True)  # ID do partner no Odoo (transportadora)
    odoo_invoice_ids = db.Column(db.Text, nullable=True)    # JSON: lista de IDs de invoices
    odoo_purchase_fiscal_id = db.Column(db.Integer, nullable=True)  # ID da compra fiscal no Odoo

    # ================================================
    # VÍNCULO COM FRETE DO SISTEMA
    # ================================================
    frete_id = db.Column(db.Integer, db.ForeignKey('fretes.id'), nullable=True, index=True)
    vinculado_manualmente = db.Column(db.Boolean, default=False)  # Se foi vinculado manualmente
    vinculado_em = db.Column(db.DateTime, nullable=True)
    vinculado_por = db.Column(db.String(100), nullable=True)

    # Relacionamento
    frete = db.relationship('Frete', backref='conhecimentos_transporte', lazy=True)

    # ================================================
    # AUDITORIA
    # ================================================
    importado_em = db.Column(db.DateTime, default=agora_brasil, nullable=False)
    importado_por = db.Column(db.String(100), default='Sistema Odoo')
    atualizado_em = db.Column(db.DateTime, default=agora_brasil, onupdate=agora_brasil)
    atualizado_por = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True, index=True)

    # ================================================
    # ÍNDICES
    # ================================================
    __table_args__ = (
        db.Index('idx_cte_chave_acesso', 'chave_acesso'),
        db.Index('idx_cte_numero_serie', 'numero_cte', 'serie_cte'),
        db.Index('idx_cte_cnpj_emitente', 'cnpj_emitente'),
        db.Index('idx_cte_cnpj_remetente', 'cnpj_remetente'),
        db.Index('idx_cte_cnpj_destinatario', 'cnpj_destinatario'),
        db.Index('idx_cte_data_emissao', 'data_emissao'),
        db.Index('idx_cte_frete', 'frete_id'),
        db.Index('idx_cte_status', 'odoo_status_codigo'),
    )

    def __repr__(self):
        return f'<CTe {self.numero_cte}/{self.serie_cte} - {self.nome_emitente}>'

    def to_dict(self):
        """Serializa o CTe para JSON"""
        return {
            'id': self.id,
            'dfe_id': self.dfe_id,
            'odoo_name': self.odoo_name,
            'odoo_status_codigo': self.odoo_status_codigo,
            'odoo_status_descricao': self.odoo_status_descricao,
            'chave_acesso': self.chave_acesso,
            'numero_cte': self.numero_cte,
            'serie_cte': self.serie_cte,
            'data_emissao': self.data_emissao.isoformat() if self.data_emissao else None,
            'valor_total': float(self.valor_total) if self.valor_total else 0,
            'valor_frete': float(self.valor_frete) if self.valor_frete else 0,
            'valor_icms': float(self.valor_icms) if self.valor_icms else 0,
            'cnpj_emitente': self.cnpj_emitente,
            'nome_emitente': self.nome_emitente,
            'cnpj_destinatario': self.cnpj_destinatario,
            'cnpj_remetente': self.cnpj_remetente,
            'frete_id': self.frete_id,
            'cte_pdf_path': self.cte_pdf_path,
            'cte_xml_path': self.cte_xml_path,
            'vinculado_manualmente': self.vinculado_manualmente,
            'importado_em': self.importado_em.isoformat() if self.importado_em else None
        }

    @staticmethod
    def get_status_descricao(codigo):
        """
        Retorna a descrição do status baseado no código

        Valores do Odoo (l10n_br_status):
        01-Rascunho, 02-Sincronizado, 03-Ciência/Confirmado,
        04-PO, 05-Rateio, 06-Concluído, 07-Rejeitado
        """
        status_map = {
            '01': 'Rascunho',
            '02': 'Sincronizado',
            '03': 'Ciência/Confirmado',
            '04': 'PO',
            '05': 'Rateio',
            '06': 'Concluído',
            '07': 'Rejeitado'
        }
        return status_map.get(codigo, 'Desconhecido')

    @staticmethod
    def formatar_cnpj(cnpj):
        """
        Formata CNPJ para o padrão XX.XXX.XXX/XXXX-XX

        Args:
            cnpj: CNPJ sem formatação (14 dígitos)

        Returns:
            str: CNPJ formatado ou original se inválido
        """
        if not cnpj:
            return ''

        # Remover caracteres não numéricos
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        # Validar tamanho
        if len(cnpj_limpo) != 14:
            return cnpj  # Retornar original se inválido

        # Formatar: XX.XXX.XXX/XXXX-XX
        return f"{cnpj_limpo[0:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

    def calcular_tomador_e_empresa(self, prefixo_cnpj='61724241'):
        """
        Calcula se o tomador do CTe é a empresa (CNPJ começa com 61.724.241)

        Args:
            prefixo_cnpj: Prefixo do CNPJ da empresa (8 primeiros dígitos, sem formatação)

        Returns:
            bool: True se o tomador for a empresa, False caso contrário
        """
        if not self.tomador:
            return False

        # Mapa código tomador -> campo CNPJ
        mapa_tomador = {
            '0': self.cnpj_remetente,  # Remetente
            '1': self.cnpj_remetente,  # Remetente
            '2': self.cnpj_expedidor,  # Expedidor
            '3': self.cnpj_destinatario,  # Recebedor
            '4': self.cnpj_destinatario,  # Destinatário
        }

        cnpj_tomador = mapa_tomador.get(self.tomador)

        if not cnpj_tomador:
            return False

        # Limpar CNPJ (remover formatação)
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj_tomador))

        # Verificar se começa com o prefixo (primeiros 8 dígitos)
        return cnpj_limpo.startswith(prefixo_cnpj)
