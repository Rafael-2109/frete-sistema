"""
Modelos específicos do Portal Sendas
Incluindo tabela DE-PARA de produtos
"""

from app import db
from datetime import datetime
from app.utils.timezone import agora_utc_naive

class ProdutoDeParaSendas(db.Model):
    """
    Tabela DE-PARA para mapear códigos de produtos
    Nosso código <-> Código do cliente Sendas
    """
    __tablename__ = 'portal_sendas_produto_depara'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Nosso código e descrição
    codigo_nosso = db.Column(db.String(50), nullable=False, index=True)
    descricao_nosso = db.Column(db.String(255))
    
    # Código e descrição do Sendas
    codigo_sendas = db.Column(db.String(50), nullable=False, index=True)
    descricao_sendas = db.Column(db.String(255))
    
    # CNPJ do cliente (caso o mapeamento seja específico por cliente)
    cnpj_cliente = db.Column(db.String(20), index=True)
    
    # Fator de conversão (se houver diferença de unidade de medida)
    fator_conversao = db.Column(db.Numeric(10, 4), default=1.0)
    observacoes = db.Column(db.Text)
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    criado_por = db.Column(db.String(100))
    
    # Índice único para evitar duplicatas
    __table_args__ = (
        db.UniqueConstraint('codigo_nosso', 'codigo_sendas', 'cnpj_cliente', 
                          name='unique_depara_sendas'),
    )
    
    @classmethod
    def obter_codigo_sendas(cls, codigo_nosso, cnpj_cliente=None):
        """
        Obtém o código do Sendas correspondente ao nosso código
        
        Args:
            codigo_nosso: Nosso código de produto
            cnpj_cliente: CNPJ do cliente (opcional) - IGNORADO
            
        Returns:
            Código do Sendas ou None se não encontrar
        """
        # Ignorar CNPJ completamente - buscar apenas por código
        depara = cls.query.filter_by(
            codigo_nosso=codigo_nosso,
            ativo=True
        ).first()
        
        if depara:
            return depara.codigo_sendas
        
        return None
    
    @classmethod
    def obter_nosso_codigo(cls, codigo_sendas, cnpj_cliente=None):
        """
        Obtém nosso código correspondente ao código do Sendas
        
        Args:
            codigo_sendas: Código do produto no Sendas
            cnpj_cliente: CNPJ do cliente (opcional) - IGNORADO
            
        Returns:
            Nosso código ou None se não encontrar
        """
        # Ignorar CNPJ completamente - buscar apenas por código
        depara = cls.query.filter_by(
            codigo_sendas=codigo_sendas,
            ativo=True
        ).first()
        
        if depara:
            return depara.codigo_nosso
        
        return None
    
    @classmethod
    def importar_de_arquivo(cls, filepath, cnpj_cliente=None, criado_por='Sistema'):
        """
        Importa mapeamentos de um arquivo CSV ou XLSX
        
        Formato esperado:
        codigo_nosso,descricao_nosso,codigo_sendas,descricao_sendas,fator_conversao
        """
        import pandas as pd
        
        registros_criados = 0
        registros_atualizados = 0
        erros = []
        
        try:
            # Detectar formato do arquivo e ler
            if filepath.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            
            # Processar cada linha
            for index, row in df.iterrows():
                try:
                    # Converter valores para string (evita erro de tipo no PostgreSQL)
                    codigo_nosso = str(row['codigo_nosso']) if pd.notna(row['codigo_nosso']) else ''
                    codigo_sendas = str(row['codigo_sendas']) if pd.notna(row['codigo_sendas']) else ''
                    
                    # Verificar se já existe
                    depara = cls.query.filter_by(
                        codigo_nosso=codigo_nosso,
                        codigo_sendas=codigo_sendas,
                        cnpj_cliente=cnpj_cliente
                    ).first()
                    
                    if depara:
                        # Atualizar existente
                        depara.descricao_nosso = row.get('descricao_nosso', depara.descricao_nosso)
                        depara.descricao_sendas = row.get('descricao_sendas', depara.descricao_sendas)
                        depara.fator_conversao = float(row.get('fator_conversao', 1.0))
                        depara.atualizado_em = agora_utc_naive()
                        registros_atualizados += 1
                    else:
                        # Criar novo
                        depara = cls(
                            codigo_nosso=codigo_nosso,
                            descricao_nosso=row.get('descricao_nosso'),
                            codigo_sendas=codigo_sendas,
                            descricao_sendas=row.get('descricao_sendas'),
                            cnpj_cliente=cnpj_cliente,
                            fator_conversao=float(row.get('fator_conversao', 1.0)),
                            criado_por=criado_por,
                            ativo=True
                        )
                        db.session.add(depara)
                        registros_criados += 1
                            
                except Exception as e:
                    erros.append(f"Erro na linha {index + 2}: {e}")  # type: ignore
            
            db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao importar arquivo: {e}")
        
        return {
            'criados': registros_criados,
            'atualizados': registros_atualizados,
            'erros': erros
        }
    
    @classmethod
    def importar_de_csv(cls, filepath, cnpj_cliente=None, criado_por='Sistema'):
        """Mantém compatibilidade - chama importar_de_arquivo"""
        return cls.importar_de_arquivo(filepath, cnpj_cliente, criado_por)
    
    @classmethod
    def exportar_para_xlsx(cls, filepath=None, ativo=True):
        """
        Exporta mapeamentos para arquivo XLSX
        
        Args:
            filepath: Caminho do arquivo (se None, retorna bytes do Excel)
            ativo: Se True, exporta apenas registros ativos
            
        Returns:
            Se filepath fornecido: caminho do arquivo
            Se não: bytes do arquivo Excel
        """
        import pandas as pd
        from io import BytesIO
        
        # Buscar dados
        query = cls.query
        if ativo is not None:
            query = query.filter_by(ativo=ativo)
        
        mapeamentos = query.order_by(cls.codigo_nosso).all()
        
        # Criar DataFrame
        data = []
        for m in mapeamentos:
            data.append({
                'codigo_nosso': m.codigo_nosso,
                'descricao_nosso': m.descricao_nosso,
                'codigo_sendas': m.codigo_sendas,
                'descricao_sendas': m.descricao_sendas,
                'cnpj_cliente': m.cnpj_cliente or '',
                'fator_conversao': m.fator_conversao,
                'observacoes': m.observacoes or '',
                'ativo': 'Sim' if m.ativo else 'Não'
            })
        
        df = pd.DataFrame(data)
        
        # Exportar
        if filepath:
            df.to_excel(filepath, index=False, engine='openpyxl')
            return filepath
        else:
            # Retornar bytes para download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Produtos')
            output.seek(0)
            return output.getvalue()
    
    def __repr__(self):
        return f"<DeParaSendas {self.codigo_nosso} -> {self.codigo_sendas}>"


class FilialDeParaSendas(db.Model):
    """
    Tabela DE-PARA para mapear CNPJs e códigos de filiais do Sendas
    CNPJ <-> Filial <-> CNPJ_Numero
    """
    __tablename__ = 'portal_sendas_filial_depara'

    id = db.Column(db.Integer, primary_key=True)

    # CNPJ completo (com ou sem formatação)
    cnpj = db.Column(db.String(20), nullable=False, unique=True, index=True)

    # Código da filial no Sendas (ex: "010 SAO BERNARDO PIRAPORI")
    filial = db.Column(db.String(100), nullable=False, unique=True, index=True)

    # Número da filial extraído (ex: "010") - para busca rápida por número
    numero = db.Column(db.String(10), nullable=True, index=True)

    # Informações adicionais
    nome_filial = db.Column(db.String(255))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    
    # Controle
    ativo = db.Column(db.Boolean, default=True, index=True)
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    criado_por = db.Column(db.String(100))
    
    @classmethod
    def cnpj_to_filial(cls, cnpj, filial_planilha=None):
        """
        Converte CNPJ para código de filial

        Args:
            cnpj: CNPJ formatado ou não (aceita com ou sem pontuação)
            filial_planilha: Nome da filial vinda da planilha para tentar fallback por números

        Returns:
            Código da filial ou None se não encontrar
        """
        import re

        # Remover formatação do CNPJ se houver
        cnpj_limpo = cls.limpar_cnpj(cnpj)

        # Buscar por CNPJ (formatado ou limpo)
        filial_depara = cls.query.filter(
            (cls.cnpj == cnpj) |
            (cls.cnpj == cnpj_limpo),
            cls.ativo == True
        ).first()

        # Se encontrou, retornar
        if filial_depara:
            return filial_depara.filial

        # FALLBACK: Se não encontrou e temos filial_planilha, tentar match por números
        if filial_planilha:
            # Extrair apenas números da filial da planilha
            numeros_planilha = ''.join(re.findall(r'\d+', str(filial_planilha)))

            if numeros_planilha:
                # Buscar todas as filiais ativas do DE-PARA
                filiais_depara = cls.query.filter_by(ativo=True).all()

                for depara in filiais_depara:
                    # Extrair números da filial do DE-PARA
                    numeros_depara = ''.join(re.findall(r'\d+', str(depara.filial)))

                    # Se os números batem, encontramos o match
                    if numeros_depara and numeros_depara == numeros_planilha:
                        # Log para debug
                        print(f"[FALLBACK] Match por números: '{filial_planilha}' ({numeros_planilha}) -> '{depara.filial}' ({numeros_depara})")
                        return depara.filial

                # Se não encontrou match nem por números
                print(f"[FALLBACK] Sem match para '{filial_planilha}' ({numeros_planilha})")

        return None
    
    @classmethod
    def filial_to_cnpj(cls, filial):
        """
        Converte código de filial para CNPJ

        Args:
            filial: Código da filial no Sendas

        Returns:
            CNPJ formatado ou None se não encontrar
        """
        filial_depara = cls.query.filter_by(
            filial=str(filial),
            ativo=True
        ).first()

        return filial_depara.cnpj if filial_depara else None

    @classmethod
    def buscar_por_numero(cls, numero_loja: str):
        """
        Busca filial pelo número (ex: "007", "010", "350")
        Usado na importação de pedidos do Assaí onde o PDF mostra apenas o número

        Args:
            numero_loja: Número da loja (3 dígitos)

        Returns:
            Objeto FilialDeParaSendas ou None se não encontrar
        """
        import re

        # Normaliza para 3 dígitos com zero à esquerda
        numero_normalizado = str(numero_loja).zfill(3)

        # Primeiro tenta buscar pelo campo 'numero' (se estiver populado)
        filial = cls.query.filter(
            cls.numero == numero_normalizado,
            cls.ativo == True
        ).first()

        if filial:
            return filial

        # Fallback: busca extraindo número do campo 'filial'
        filiais = cls.query.filter_by(ativo=True).all()

        for f in filiais:
            # Extrai números do início do campo filial
            # Ex: "010 SAO BERNARDO PIRAPORI" -> "010"
            match = re.match(r'^(\d+)', f.filial or '')
            if match:
                numero_depara = match.group(1).zfill(3)
                if numero_depara == numero_normalizado:
                    return f

        return None

    @classmethod
    def obter_info_por_numero(cls, numero_loja: str):
        """
        Obtém informações completas da filial pelo número

        Args:
            numero_loja: Número da loja (3 dígitos)

        Returns:
            Dicionário com informações da filial ou dict vazio
        """
        filial = cls.buscar_por_numero(numero_loja)

        if filial:
            return {
                'cnpj': filial.cnpj,
                'cnpj_limpo': cls.limpar_cnpj(filial.cnpj),
                'filial': filial.filial,
                'numero': filial.numero or numero_loja,
                'nome_filial': filial.nome_filial,
                'cidade': filial.cidade,
                'uf': filial.uf
            }

        return {}
    
    @classmethod
    def obter_info_filial(cls, identificador):
        """
        Obtém informações completas da filial por qualquer identificador
        (CNPJ formatado/limpo ou código de filial)
        
        Args:
            identificador: CNPJ ou código de filial
            
        Returns:
            Dicionário com informações da filial ou None
        """
        # Remover formatação se for CNPJ
        identificador_limpo = cls.limpar_cnpj(identificador)
        
        # Buscar por qualquer identificador
        filial_depara = cls.query.filter(
            (cls.cnpj == identificador) | 
            (cls.cnpj == identificador_limpo) |
            (cls.filial == str(identificador)),
            cls.ativo == True
        ).first()
        
        if filial_depara:
            return {
                'cnpj': filial_depara.cnpj,
                'cnpj_limpo': cls.limpar_cnpj(filial_depara.cnpj),
                'filial': filial_depara.filial,
                'nome_filial': filial_depara.nome_filial,
                'cidade': filial_depara.cidade,
                'uf': filial_depara.uf
            }
        
        return None
    
    @classmethod
    def importar_filiais_arquivo(cls, filepath, criado_por='Sistema'):
        """
        Importa mapeamento de filiais de um arquivo CSV ou XLSX
        
        Formato esperado:
        cnpj,filial,nome_filial,cidade,uf
        """
        import pandas as pd
        
        registros_criados = 0
        registros_atualizados = 0
        erros = []
        
        try:
            # Detectar formato do arquivo e ler
            if filepath.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            
            # Processar cada linha
            for index, row in df.iterrows():
                try:
                    # Converter valores para string e limpar CNPJ
                    cnpj_input = str(row['cnpj']) if pd.notna(row['cnpj']) else ''
                    cnpj_limpo = cls.limpar_cnpj(cnpj_input)
                    filial_codigo = str(row['filial']) if pd.notna(row['filial']) else ''
                    
                    # Verificar se já existe por CNPJ ou filial
                    filial_depara = cls.query.filter(
                        (cls.cnpj == cnpj_input) |
                        (cls.cnpj == cnpj_limpo) |
                        (cls.filial == filial_codigo)
                    ).first()
                    
                    if filial_depara:
                        # Atualizar existente
                        filial_depara.cnpj = cnpj_input
                        filial_depara.filial = filial_codigo
                        filial_depara.nome_filial = row.get('nome_filial')
                        filial_depara.cidade = row.get('cidade')
                        filial_depara.uf = row.get('uf')
                        filial_depara.atualizado_em = agora_utc_naive()
                        filial_depara.ativo = True
                        registros_atualizados += 1
                    else:
                        # Criar novo
                        filial_depara = cls(
                            cnpj=cnpj_input,
                            filial=filial_codigo,
                            nome_filial=row.get('nome_filial'),
                            cidade=row.get('cidade'),
                            uf=row.get('uf'),
                            criado_por=criado_por,
                            ativo=True
                        )
                        db.session.add(filial_depara)
                        registros_criados += 1
                            
                except Exception as e:
                    erros.append(f"Erro na linha {index + 2}: {e}")  # type: ignore
            
            db.session.commit()
                
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao importar arquivo: {e}")
        
        return {
            'criados': registros_criados,
            'atualizados': registros_atualizados,
            'erros': erros
        }
    
    @classmethod
    def importar_filiais_csv(cls, filepath, criado_por='Sistema'):
        """Mantém compatibilidade - chama importar_filiais_arquivo"""
        return cls.importar_filiais_arquivo(filepath, criado_por)
    
    @classmethod
    def exportar_filiais_xlsx(cls, filepath=None, ativo=True):
        """
        Exporta mapeamentos de filiais para arquivo XLSX
        
        Args:
            filepath: Caminho do arquivo (se None, retorna bytes do Excel)
            ativo: Se True, exporta apenas registros ativos
            
        Returns:
            Se filepath fornecido: caminho do arquivo
            Se não: bytes do arquivo Excel
        """
        import pandas as pd
        from io import BytesIO
        
        # Buscar dados
        query = cls.query
        if ativo is not None:
            query = query.filter_by(ativo=ativo)
        
        filiais = query.order_by(cls.cnpj).all()
        
        # Criar DataFrame
        data = []
        for f in filiais:
            data.append({
                'cnpj': f.cnpj,
                'filial': f.filial,
                'nome_filial': f.nome_filial or '',
                'cidade': f.cidade or '',
                'uf': f.uf or '',
                'ativo': 'Sim' if f.ativo else 'Não'
            })
        
        df = pd.DataFrame(data)
        
        # Exportar
        if filepath:
            df.to_excel(filepath, index=False, engine='openpyxl')
            return filepath
        else:
            # Retornar bytes para download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Filiais')
            output.seek(0)
            return output.getvalue()
    
    @staticmethod
    def formatar_cnpj(cnpj_numero):
        """
        Formata CNPJ numérico para o padrão XX.XXX.XXX/XXXX-XX
        
        Args:
            cnpj_numero: CNPJ apenas números (14 dígitos)
            
        Returns:
            CNPJ formatado
        """
        cnpj = str(cnpj_numero).zfill(14)
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    
    @staticmethod
    def limpar_cnpj(cnpj):
        """
        Remove formatação do CNPJ, deixando apenas números
        
        Args:
            cnpj: CNPJ com ou sem formatação
            
        Returns:
            CNPJ apenas números
        """
        return ''.join(filter(str.isdigit, str(cnpj)))
    
    def __repr__(self):
        return f"<FilialDeParaSendas {self.cnpj} -> {self.filial}>"