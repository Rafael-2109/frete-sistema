"""
Modelos específicos do Portal Tenda
Incluindo tabelas DE-PARA para produtos (EAN) e locais de entrega
"""

from app import db
from datetime import datetime


class ProdutoDeParaEAN(db.Model):
    """
    Tabela DE-PARA para mapear códigos de produtos para EAN
    Nosso código <-> EAN (código de barras)
    """
    __tablename__ = 'portal_tenda_produto_depara_ean'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Nosso código e descrição
    codigo_nosso = db.Column(db.String(50), nullable=False, index=True)
    descricao_nosso = db.Column(db.String(255))
    
    # EAN (código de barras) e descrição
    ean = db.Column(db.String(20), nullable=False, index=True)
    descricao_ean = db.Column(db.String(255))
    
    # CNPJ do cliente (caso o mapeamento seja específico por cliente)
    cnpj_cliente = db.Column(db.String(20), index=True)
    
    # Fator de conversão (se houver diferença de unidade de medida)
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0)
    observacoes = db.Column(db.Text)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    
    # Índice único para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('codigo_nosso', 'ean', 'cnpj_cliente', 
                          name='unique_depara_ean'),
    )
    
    @classmethod
    def obter_ean(cls, codigo_nosso, cnpj_cliente=None):
        """
        Obtém o EAN correspondente ao nosso código
        
        Args:
            codigo_nosso: Nosso código de produto
            cnpj_cliente: CNPJ do cliente (opcional)
            
        Returns:
            EAN ou None se não encontrar
        """
        query = cls.query.filter_by(
            codigo_nosso=codigo_nosso,
            ativo=True
        )
        
        if cnpj_cliente:
            # Primeiro tentar com CNPJ específico
            depara = query.filter_by(cnpj_cliente=cnpj_cliente).first()
            if depara:
                return depara.ean
            
            # Se não encontrar, tentar genérico (cnpj_cliente = NULL)
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.ean
        else:
            # Buscar genérico
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.ean
        
        return None
    
    @classmethod
    def obter_nosso_codigo(cls, ean, cnpj_cliente=None):
        """
        Obtém nosso código correspondente ao EAN
        
        Args:
            ean: EAN (código de barras) do produto
            cnpj_cliente: CNPJ do cliente (opcional)
            
        Returns:
            Nosso código ou None se não encontrar
        """
        query = cls.query.filter_by(
            ean=ean,
            ativo=True
        )
        
        if cnpj_cliente:
            # Primeiro tentar com CNPJ específico
            depara = query.filter_by(cnpj_cliente=cnpj_cliente).first()
            if depara:
                return depara.codigo_nosso
            
            # Se não encontrar, tentar genérico
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.codigo_nosso
        else:
            # Buscar genérico
            depara = query.filter(cls.cnpj_cliente.is_(None)).first()
            if depara:
                return depara.codigo_nosso
        
        return None
    
    @classmethod
    def importar_de_xlsx(cls, filepath, cnpj_cliente=None, criado_por='Sistema'):
        """
        Importa mapeamentos de um arquivo XLSX
        
        Formato esperado do XLSX:
        Colunas: codigo_nosso | descricao_nosso | ean | descricao_ean | fator_conversao
        """
        import pandas as pd
        
        registros_criados = 0
        registros_atualizados = 0
        erros = []
        
        try:
            # Ler arquivo XLSX
            df = pd.read_excel(filepath)
            
            # Verificar colunas obrigatórias
            colunas_obrigatorias = ['codigo_nosso', 'ean']
            for col in colunas_obrigatorias:
                if col not in df.columns:
                    raise Exception(f"Coluna obrigatória '{col}' não encontrada no arquivo")
            
            # Processar linha por linha
            for index, row in df.iterrows():
                try:
                    codigo_nosso = str(row['codigo_nosso']).strip()
                    ean = str(row['ean']).strip()
                    
                    # Pular linhas vazias
                    if pd.isna(codigo_nosso) or pd.isna(ean):
                        continue
                    
                    # Verificar se já existe
                    depara = cls.query.filter_by(
                        codigo_nosso=codigo_nosso,
                        ean=ean,
                        cnpj_cliente=cnpj_cliente
                    ).first()
                    
                    if depara:
                        # Atualizar existente
                        if 'descricao_nosso' in row and not pd.isna(row['descricao_nosso']):
                            depara.descricao_nosso = str(row['descricao_nosso'])
                        if 'descricao_ean' in row and not pd.isna(row['descricao_ean']):
                            depara.descricao_ean = str(row['descricao_ean'])
                        if 'fator_conversao' in row and not pd.isna(row['fator_conversao']):
                            depara.fator_conversao = float(row['fator_conversao'])
                        depara.atualizado_em = datetime.utcnow()
                        registros_atualizados += 1
                    else:
                        # Criar novo
                        depara = cls(
                            codigo_nosso=codigo_nosso,
                            descricao_nosso=str(row.get('descricao_nosso', '')) if 'descricao_nosso' in row and not pd.isna(row.get('descricao_nosso')) else None,
                            ean=ean,
                            descricao_ean=str(row.get('descricao_ean', '')) if 'descricao_ean' in row and not pd.isna(row.get('descricao_ean')) else None,
                            cnpj_cliente=cnpj_cliente,
                            fator_conversao=float(row.get('fator_conversao', 1.0)) if 'fator_conversao' in row and not pd.isna(row.get('fator_conversao')) else 1.0,
                            criado_por=criado_por,
                            ativo=True
                        )
                        db.session.add(depara)
                        registros_criados += 1
                        
                except Exception as e:
                    erros.append(f"Erro na linha {index + 2}: {e}")
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao importar arquivo: {e}")
        
        return {
            'criados': registros_criados,
            'atualizados': registros_atualizados,
            'erros': erros
        }
    
    def __repr__(self):
        return f"<DeParaEAN {self.codigo_nosso} -> {self.ean}>"


class LocalEntregaDeParaTenda(db.Model):
    """
    Tabela DE-PARA para mapear CNPJ do cliente com filial no portal
    Mapeia: CNPJ cliente -> Grupo Empresarial (filtro_destinatario) + Filial (local_entrega)
    """
    __tablename__ = 'portal_tenda_local_entrega_depara'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # CNPJ do cliente
    cnpj_cliente = db.Column(db.String(20), nullable=False, unique=True, index=True)
    nome_cliente = db.Column(db.String(255))  # Opcional, para referência
    
    # Grupo Empresarial no portal (filtro_destinatario)
    grupo_empresarial_nome = db.Column(db.String(255), nullable=False)  # Ex: "TENDA ATACADO SA"
    
    # Filial no portal (local_entrega)
    filial_nome = db.Column(db.String(255), nullable=False)  # Ex: "CT03 - AMOREIRAS"
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    
    @classmethod
    def obter_local_entrega(cls, cnpj_cliente):
        """
        Obtém o grupo empresarial e filial para um CNPJ
        
        Args:
            cnpj_cliente: CNPJ do cliente
            
        Returns:
            Dict com informações ou None
        """
        from app.portal.utils.grupo_empresarial import GrupoEmpresarial
        
        # Limpar CNPJ
        cnpj_limpo = GrupoEmpresarial.limpar_cnpj(cnpj_cliente)
        
        local = cls.query.filter_by(
            cnpj_cliente=cnpj_limpo,
            ativo=True
        ).first()
        
        if local:
            return {
                'grupo_empresarial_nome': local.grupo_empresarial_nome,
                'filial_nome': local.filial_nome
            }
        
        return None
    
    @classmethod
    def listar_locais_ativos(cls):
        """
        Lista todos os locais de entrega ativos
        
        Returns:
            Lista de locais ativos
        """
        return cls.query.filter_by(ativo=True).all()
    
    @classmethod
    def importar_de_xlsx(cls, filepath, criado_por='Sistema'):
        """
        Importa mapeamentos de locais de um arquivo XLSX
        
        Formato esperado do XLSX:
        Colunas: cnpj_cliente | nome_cliente | grupo_empresarial_nome | filial_nome
        """
        import pandas as pd
        from app.portal.utils.grupo_empresarial import GrupoEmpresarial
        
        registros_criados = 0
        registros_atualizados = 0
        erros = []
        
        try:
            # Ler arquivo XLSX
            df = pd.read_excel(filepath)
            
            # Verificar colunas obrigatórias
            colunas_obrigatorias = ['cnpj_cliente', 'grupo_empresarial_nome', 'filial_nome']
            for col in colunas_obrigatorias:
                if col not in df.columns:
                    raise Exception(f"Coluna obrigatória '{col}' não encontrada no arquivo")
            
            # Processar linha por linha
            for index, row in df.iterrows():
                try:
                    cnpj_cliente = str(row['cnpj_cliente']).strip()
                    
                    # Pular linhas vazias
                    if pd.isna(cnpj_cliente):
                        continue
                    
                    cnpj_limpo = GrupoEmpresarial.limpar_cnpj(cnpj_cliente)
                    
                    # Verificar se já existe
                    local = cls.query.filter_by(cnpj_cliente=cnpj_limpo).first()
                    
                    if local:
                        # Atualizar existente
                        if 'nome_cliente' in row and not pd.isna(row['nome_cliente']):
                            local.nome_cliente = str(row['nome_cliente'])
                        local.grupo_empresarial_nome = str(row['grupo_empresarial_nome'])
                        local.filial_nome = str(row['filial_nome'])
                        local.atualizado_em = datetime.utcnow()
                        registros_atualizados += 1
                    else:
                        # Criar novo
                        local = cls(
                            cnpj_cliente=cnpj_limpo,
                            nome_cliente=str(row.get('nome_cliente', '')) if 'nome_cliente' in row and not pd.isna(row.get('nome_cliente')) else None,
                            grupo_empresarial_nome=str(row['grupo_empresarial_nome']),
                            filial_nome=str(row['filial_nome']),
                            criado_por=criado_por,
                            ativo=True
                        )
                        db.session.add(local)
                        registros_criados += 1
                        
                except Exception as e:
                    erros.append(f"Erro na linha {index + 2}: {e}")
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao importar arquivo: {e}")
        
        return {
            'criados': registros_criados,
            'atualizados': registros_atualizados,
            'erros': erros
        }
    
    def __repr__(self):
        return f"<LocalEntregaTenda {self.cnpj_cliente} -> {self.grupo_empresarial_nome} / {self.filial_nome}>"


class AgendamentoTenda(db.Model):
    """
    Registro de agendamentos realizados no portal Tenda
    """
    __tablename__ = 'portal_tenda_agendamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Identificação
    separacao_lote_id = db.Column(db.String(50), nullable=False, index=True)
    protocolo = db.Column(db.String(50), unique=True, index=True)
    pdd_numero = db.Column(db.String(50), index=True)  # Número do PDD selecionado
    
    # Dados do agendamento
    data_agendamento = db.Column(db.Date, nullable=False)
    horario_agendamento = db.Column(db.Time)
    
    # Cliente e local
    cnpj_cliente = db.Column(db.String(20), index=True)
    local_entrega_id = db.Column(db.String(100))
    local_entrega_nome = db.Column(db.String(255))
    
    # Configurações do agendamento
    tipo_veiculo = db.Column(db.String(50))
    tipo_carga = db.Column(db.String(50))
    tipo_volume = db.Column(db.String(50))
    quantidade_volume = db.Column(db.Integer)
    
    # Status
    status = db.Column(db.String(50), default='aguardando', index=True)
    confirmado = db.Column(db.Boolean, default=False)
    
    # Resposta do portal
    resposta_portal = db.Column(db.JSON)
    mensagem_retorno = db.Column(db.Text)
    
    # Controle
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    criado_por = db.Column(db.String(100))
    
    @classmethod
    def obter_por_protocolo(cls, protocolo):
        """
        Busca agendamento pelo protocolo
        
        Args:
            protocolo: Número do protocolo
            
        Returns:
            Objeto AgendamentoTenda ou None
        """
        return cls.query.filter_by(protocolo=protocolo).first()
    
    @classmethod
    def obter_por_lote(cls, separacao_lote_id):
        """
        Busca agendamento pelo ID do lote de separação
        
        Args:
            separacao_lote_id: ID do lote
            
        Returns:
            Objeto AgendamentoTenda ou None
        """
        return cls.query.filter_by(separacao_lote_id=separacao_lote_id).first()
    
    def __repr__(self):
        return f"<AgendamentoTenda {self.protocolo} - {self.status}>"