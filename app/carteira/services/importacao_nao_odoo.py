"""
Serviço de importação de pedidos não-Odoo para CarteiraCopia
"""
import pandas as pd
import logging
from datetime import datetime
from app import db
from app.carteira.models import CarteiraCopia, CadastroCliente, CarteiraPrincipal
from app.utils.timezone import agora_brasil
from sqlalchemy import and_
import re

logger = logging.getLogger(__name__)

class ImportadorPedidosNaoOdoo:
    """Classe responsável pela importação de pedidos não-Odoo"""
    
    # Mapeamento de campos por modelo de planilha
    MODELO_1 = {
        'identificador': {'celula': 'C8', 'valor': 'CNPJ*'},  # Identificador do modelo
        'campos_cabecalho': {
            'num_pedido': 'D13',
            'cnpj_cpf': 'D8',
            'pedido_cliente': 'D12',
            'data_entrega': 'E5'
        },
        'campos_produtos': {
            'cod_produto': {'coluna': 'B', 'linha_inicial': 19},
            'qtd_produto_pedido': {'coluna': 'J', 'linha_inicial': 19},
            'preco_produto_pedido': {'coluna': 'K', 'linha_inicial': 19}
        }
    }
    
    MODELO_2 = {
        'identificador': {'celula': 'B8', 'valor': 'CNPJ*'},  # Identificador do modelo
        'campos_cabecalho': {
            'num_pedido': 'C14',
            'cnpj_cpf': 'C8',
            'pedido_cliente': 'C13',
            'data_entrega': 'D5'
        },
        'campos_produtos': {
            'cod_produto': {'coluna': 'A', 'linha_inicial': 20},
            'qtd_produto_pedido': {'coluna': 'G', 'linha_inicial': 20},
            'preco_produto_pedido': {'coluna': 'H', 'linha_inicial': 20}
        }
    }
    
    def __init__(self, usuario='Sistema'):
        self.usuario = usuario
        self.erros = []
        self.avisos = []
        self.pedidos_importados = []
        self.modelo_detectado = None
    
    def limpar_cnpj(self, cnpj):
        """Remove formatação do CNPJ/CPF mantendo apenas números"""
        if not cnpj:
            return None
        return re.sub(r'\D', '', str(cnpj))
    
    def formatar_cnpj(self, cnpj):
        """Formata CNPJ/CPF com máscara padrão"""
        cnpj = self.limpar_cnpj(cnpj)
        if not cnpj:
            return None
            
        # CNPJ: 14 dígitos
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        # CPF: 11 dígitos
        elif len(cnpj) == 11:
            return f"{cnpj[:3]}.{cnpj[3:6]}.{cnpj[6:9]}-{cnpj[9:]}"
        else:
            return cnpj
    
    def celula_para_indices(self, celula):
        """Converte referência de célula (ex: 'B8') para índices de linha e coluna"""
        coluna_letra = ''.join(filter(str.isalpha, celula))
        linha_num = int(''.join(filter(str.isdigit, celula)))
        
        # Converter letra(s) da coluna para índice (A=0, B=1, etc.)
        coluna_idx = 0
        for i, letra in enumerate(reversed(coluna_letra.upper())):
            coluna_idx += (ord(letra) - ord('A') + 1) * (26 ** i)
        coluna_idx -= 1  # Ajustar para índice base 0
        
        # Linha também em base 0
        linha_idx = linha_num - 1
        
        return linha_idx, coluna_idx
    
    def ler_celula(self, df, celula):
        """Lê o valor de uma célula específica no DataFrame"""
        try:
            linha_idx, coluna_idx = self.celula_para_indices(celula)
            if linha_idx < len(df) and coluna_idx < len(df.columns):
                valor = df.iloc[linha_idx, coluna_idx]
                return str(valor).strip() if pd.notna(valor) else None
            return None
        except Exception as e:
            logger.error(f"Erro ao ler célula {celula}: {e}")
            return None
    
    def detectar_modelo(self, df):
        """Detecta qual modelo de planilha está sendo usado"""
        # Verificar Modelo 1: CNPJ* em C8
        valor_c8 = self.ler_celula(df, self.MODELO_1['identificador']['celula'])
        if valor_c8 == self.MODELO_1['identificador']['valor']:
            logger.info("Modelo 1 detectado (CNPJ* em C8)")
            return self.MODELO_1
        
        # Verificar Modelo 2: CNPJ* em B8
        valor_b8 = self.ler_celula(df, self.MODELO_2['identificador']['celula'])
        if valor_b8 == self.MODELO_2['identificador']['valor']:
            logger.info("Modelo 2 detectado (CNPJ* em B8)")
            return self.MODELO_2
        
        # Se não encontrou nenhum modelo
        logger.error(f"Modelo de planilha não identificado. C8='{valor_c8}', B8='{valor_b8}'")
        return None
    
    def buscar_campo_excel(self, df, nome_campo_lista, tipo='celula'):
        """
        Busca um campo no Excel que pode ter múltiplos nomes possíveis
        tipo: 'celula' para campos específicos, 'coluna' para colunas
        """
        for nome_possivel in nome_campo_lista:
            if tipo == 'celula':
                # Buscar em células específicas (formato chave-valor)
                for idx, row in df.iterrows():
                    for col_idx, value in enumerate(row):
                        if pd.notna(value) and str(value).strip() == nome_possivel:
                            # Retornar valor da célula à direita
                            if col_idx + 1 < len(row):
                                return row.iloc[col_idx + 1]
            else:
                # Buscar em colunas - retornar apenas o índice da coluna onde foi encontrado
                for idx, row in df.iterrows():
                    for col_idx, value in enumerate(row):
                        if pd.notna(value) and str(value).strip() == nome_possivel:
                            # Retornar tupla (linha, coluna) para saber onde está o cabeçalho
                            return (idx, col_idx)
        return None
    
    def extrair_dados_cabecalho(self, df, modelo):
        """Extrai dados do cabeçalho do Excel baseado no modelo detectado"""
        dados = {}
        campos_cabecalho = modelo['campos_cabecalho']
        
        # Extrair cada campo do cabeçalho
        for campo, celula in campos_cabecalho.items():
            valor = self.ler_celula(df, celula)
            
            if valor:
                # Tratamento especial para data
                if campo == 'data_entrega':
                    try:
                        # Tentar converter para data se for string
                        if isinstance(valor, str) and '/' in valor:
                            data_obj = datetime.strptime(valor, '%d/%m/%Y')
                            dados[campo] = data_obj.date()
                        else:
                            dados[campo] = valor
                    except Exception as e:
                        logger.error(f"Erro ao converter data: {e}")
                        dados[campo] = valor
                else:
                    dados[campo] = valor
            else:
                if campo in ['num_pedido', 'cnpj_cpf']:
                    self.erros.append(f"Campo obrigatório não encontrado em {celula}: {campo}")
                else:
                    self.avisos.append(f"Campo opcional não encontrado em {celula}: {campo}")
        
        return dados
    
    def extrair_dados_produtos(self, df, modelo):
        """Extrai dados dos produtos baseado no modelo detectado"""
        produtos = []
        campos_produtos = modelo['campos_produtos']
        
        # Converter letras das colunas para índices
        col_indices = {}
        for campo, config in campos_produtos.items():
            coluna_letra = config['coluna']
            # Converter letra para índice (A=0, B=1, etc.)
            col_indices[campo] = ord(coluna_letra.upper()) - ord('A')
        
        # Linha inicial para produtos (base 0)
        linha_inicial = campos_produtos['cod_produto']['linha_inicial'] - 1
        
        
        # Processar linhas de produtos
        for idx in range(linha_inicial, len(df)):
            try:
                row = df.iloc[idx]
                
                # Ler valores das colunas
                valor_codigo = row.iloc[col_indices['cod_produto']] if col_indices['cod_produto'] < len(row) else None
                valor_qtd = row.iloc[col_indices['qtd_produto_pedido']] if col_indices['qtd_produto_pedido'] < len(row) else None
                valor_preco = row.iloc[col_indices['preco_produto_pedido']] if col_indices['preco_produto_pedido'] < len(row) else None
                
                # Pular se código estiver vazio
                if pd.isna(valor_codigo) or str(valor_codigo).strip() == '':
                    continue
                
                # Converter valores
                codigo = str(valor_codigo).strip()
                
                # Quantidade
                qtd = 0
                if pd.notna(valor_qtd):
                    try:
                        # Remover vírgulas e converter
                        qtd_str = str(valor_qtd).replace(',', '.')
                        qtd = float(qtd_str)
                    except Exception as e:
                        logger.error(f"Erro ao converter quantidade: {e}")
                        qtd = 0
                
                # Preço
                preco = 0
                if pd.notna(valor_preco):
                    try:
                        # Remover vírgulas e converter
                        preco_str = str(valor_preco).replace(',', '.')
                        preco = float(preco_str)
                    except Exception as e:
                        logger.error(f"Erro ao converter preço: {e}")
                        preco = 0
                
                # Adicionar produto se quantidade for válida (qtd != None e qtd > 0)
                if codigo and codigo != 'nan' and pd.notna(valor_qtd) and qtd > 0:
                    produto = {
                        'cod_produto': codigo,
                        'qtd_produto_pedido': qtd,
                        'preco_produto_pedido': preco
                    }
                    produtos.append(produto)
                    logger.info(f"Produto encontrado: {produto}")
                    
            except Exception as e:
                logger.warning(f"Erro ao processar linha {idx + 1}: {e}")
                continue
        
        logger.info(f"Total de produtos encontrados: {len(produtos)}")
        return produtos
    
    
    def buscar_dados_cliente(self, cnpj):
        """Busca dados do cliente no CadastroCliente"""
        cnpj_limpo = self.limpar_cnpj(cnpj)
        if not cnpj_limpo:
            return None
            
        cliente = CadastroCliente.query.filter_by(
            cnpj_cpf=cnpj_limpo,
            cliente_ativo=True
        ).first()
        
        return cliente
    
    def importar_arquivo(self, arquivo_path):
        """Importa um arquivo Excel com pedidos não-Odoo"""
        try:
            # Primeiro, verificar quantas planilhas existem
            xl_file = pd.ExcelFile(arquivo_path, engine='openpyxl')
            logger.info(f"Planilhas encontradas no arquivo: {xl_file.sheet_names}")
            
            # Ler a primeira planilha (ou a planilha ativa)
            df = pd.read_excel(arquivo_path, header=None, engine='openpyxl', sheet_name=0)
            
            logger.info(f"Lendo planilha com {df.shape[0]} linhas e {df.shape[1]} colunas")
            
            # Detectar modelo da planilha
            modelo = self.detectar_modelo(df)
            if not modelo:
                self.erros.append("Modelo de planilha não reconhecido. Verifique se é o formato correto.")
                return {
                    'success': False,
                    'erros': self.erros,
                    'avisos': self.avisos
                }
            
            self.modelo_detectado = modelo
            
            # Extrair dados do cabeçalho baseado no modelo
            dados_cabecalho = self.extrair_dados_cabecalho(df, modelo)
            
            if self.erros:
                return {
                    'success': False,
                    'erros': self.erros,
                    'avisos': self.avisos
                }
            
            # Buscar dados do cliente
            cnpj = dados_cabecalho.get('cnpj_cpf')
            cliente = self.buscar_dados_cliente(cnpj)
            
            if not cliente:
                self.erros.append(f"Cliente com CNPJ {cnpj} não cadastrado. Cadastre o cliente primeiro.")
                return {
                    'success': False,
                    'erros': self.erros,
                    'avisos': self.avisos
                }
            
            # Extrair produtos baseado no modelo
            produtos = self.extrair_dados_produtos(df, modelo)
            
            if not produtos:
                self.erros.append("Nenhum produto válido encontrado no arquivo")
                return {
                    'success': False,
                    'erros': self.erros,
                    'avisos': self.avisos
                }
            
            # Importar para CarteiraCopia
            resultado = self._criar_pedidos_carteira(dados_cabecalho, cliente, produtos)
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao importar arquivo: {e}")
            self.erros.append(f"Erro ao processar arquivo: {str(e)}")
            return {
                'success': False,
                'erros': self.erros,
                'avisos': self.avisos
            }
    
    def _criar_pedidos_carteira(self, dados_cabecalho, cliente, produtos):
        """Cria os pedidos na CarteiraCopia"""
        try:
            num_pedido = dados_cabecalho['num_pedido']
            cnpj_formatado = self.formatar_cnpj(cliente.cnpj_cpf)
            data_atual = agora_brasil()
            
            # Verifica se pode substituir pedido existente
            pode_substituir = self._verificar_pode_substituir_pedido(num_pedido)
            
            if pode_substituir:
                # Remove pedidos antigos para substituir
                self._remover_pedidos_antigos(num_pedido)
            
            # Processar cada produto
            for produto in produtos:
                # Verificar se já existe
                pedido_existente = CarteiraCopia.query.filter(
                    and_(
                        CarteiraCopia.num_pedido == num_pedido,
                        CarteiraCopia.cod_produto == produto['cod_produto']
                    )
                ).first()
                
                if pedido_existente and not pode_substituir:
                    self.avisos.append(f"Pedido {num_pedido} produto {produto['cod_produto']} já existe - pulando")
                    continue
                
                # Criar novo registro
                novo_pedido = CarteiraCopia(
                    # Chaves principais
                    num_pedido=num_pedido,
                    cod_produto=produto['cod_produto'],
                    
                    # Dados do pedido
                    pedido_cliente=dados_cabecalho.get('pedido_cliente'),
                    data_pedido=data_atual.date(),
                    cnpj_cpf=cnpj_formatado,
                    
                    # Dados do cliente (do cadastro)
                    raz_social=cliente.raz_social,
                    raz_social_red=cliente.raz_social_red,
                    municipio=cliente.municipio,
                    estado=cliente.estado,
                    vendedor=cliente.vendedor,
                    equipe_vendas=cliente.equipe_vendas,
                    
                    # Dados do produto
                    nome_produto=f"Produto {produto['cod_produto']}",  # Será atualizado depois
                    qtd_produto_pedido=produto['qtd_produto_pedido'],
                    qtd_saldo_produto_pedido=produto['qtd_produto_pedido'],
                    preco_produto_pedido=produto['preco_produto_pedido'],
                    
                    # Dados de entrega
                    data_entrega_pedido=dados_cabecalho.get('data_entrega'),
                    
                    # Endereço de entrega (do cadastro do cliente)
                    cnpj_endereco_ent=cliente.cnpj_endereco_ent,
                    empresa_endereco_ent=cliente.empresa_endereco_ent,
                    cep_endereco_ent=cliente.cep_endereco_ent,
                    nome_cidade=cliente.nome_cidade,
                    cod_uf=cliente.cod_uf,
                    bairro_endereco_ent=cliente.bairro_endereco_ent,
                    rua_endereco_ent=cliente.rua_endereco_ent,
                    endereco_ent=cliente.endereco_ent,
                    telefone_endereco_ent=cliente.telefone_endereco_ent,
                    
                    # Status
                    status_pedido='Pedido de venda',
                    
                    # Controle
                    baixa_produto_pedido=0,
                    qtd_saldo_produto_calculado=produto['qtd_produto_pedido'],
                    
                    # Auditoria
                    created_by=self.usuario,
                    updated_by=self.usuario,
                    ativo=True
                )
                
                db.session.add(novo_pedido)
                
                # Adicionar também à CarteiraPrincipal
                self._adicionar_carteira_principal(novo_pedido, cliente, data_atual)
                
                self.pedidos_importados.append({
                    'num_pedido': num_pedido,
                    'cod_produto': produto['cod_produto'],
                    'quantidade': produto['qtd_produto_pedido'],
                    'valor': produto['preco_produto_pedido']
                })
            
            # Commit das alterações
            db.session.commit()
            
            return {
                'success': True,
                'mensagem': f'Importação concluída com sucesso!',
                'pedidos_importados': len(self.pedidos_importados),
                'detalhes': self.pedidos_importados,
                'avisos': self.avisos
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao criar pedidos na carteira: {e}")
            self.erros.append(f"Erro ao salvar pedidos: {str(e)}")
            return {
                'success': False,
                'erros': self.erros,
                'avisos': self.avisos
            }
    
    def _adicionar_carteira_principal(self, pedido_copia, cliente, data_atual):
        """Adiciona o pedido também na CarteiraPrincipal"""
        try:
            # Verificar se já existe na principal
            pedido_existente = CarteiraPrincipal.query.filter(
                and_(
                    CarteiraPrincipal.num_pedido == pedido_copia.num_pedido,
                    CarteiraPrincipal.cod_produto == pedido_copia.cod_produto
                )
            ).first()
            
            if pedido_existente:
                logger.info(f"Pedido {pedido_copia.num_pedido}/{pedido_copia.cod_produto} já existe na CarteiraPrincipal")
                return
            
            # Buscar nome do produto no CadastroPalletizacao
            nome_produto = pedido_copia.nome_produto
            try:
                from app.producao.models import CadastroPalletizacao
                palletizacao = CadastroPalletizacao.query.filter_by(
                    cod_produto=pedido_copia.cod_produto
                ).first()
                if palletizacao and palletizacao.descricao:
                    nome_produto = palletizacao.descricao
            except Exception as e:
                logger.warning(f"Erro ao buscar produto {pedido_copia.cod_produto}: {e}")
            
            # Criar registro na CarteiraPrincipal
            novo_principal = CarteiraPrincipal(
                # Chaves principais
                num_pedido=pedido_copia.num_pedido,
                cod_produto=pedido_copia.cod_produto,
                
                # Dados do pedido
                pedido_cliente=pedido_copia.pedido_cliente,
                data_pedido=pedido_copia.data_pedido,
                data_atual_pedido=data_atual.date(),
                status_pedido=pedido_copia.status_pedido,
                
                # Dados do cliente
                cnpj_cpf=pedido_copia.cnpj_cpf,
                raz_social=pedido_copia.raz_social,
                raz_social_red=pedido_copia.raz_social_red,
                municipio=pedido_copia.municipio,
                estado=pedido_copia.estado,
                vendedor=pedido_copia.vendedor,
                equipe_vendas=pedido_copia.equipe_vendas,
                
                # Dados do produto
                nome_produto=nome_produto,
                unid_medida_produto='UN',  # Padrão
                qtd_produto_pedido=pedido_copia.qtd_produto_pedido,
                qtd_saldo_produto_pedido=pedido_copia.qtd_saldo_produto_pedido,
                qtd_cancelada_produto_pedido=0,
                preco_produto_pedido=pedido_copia.preco_produto_pedido,
                
                # Dados de entrega
                data_entrega_pedido=pedido_copia.data_entrega_pedido,
                metodo_entrega_pedido='CIF',  # Padrão
                cliente_nec_agendamento='Sim' if cliente.vendedor else 'Não',
                
                # Endereço de entrega
                cnpj_endereco_ent=pedido_copia.cnpj_endereco_ent,
                empresa_endereco_ent=pedido_copia.empresa_endereco_ent,
                cep_endereco_ent=pedido_copia.cep_endereco_ent,
                nome_cidade=pedido_copia.nome_cidade,
                cod_uf=pedido_copia.cod_uf,
                bairro_endereco_ent=pedido_copia.bairro_endereco_ent,
                rua_endereco_ent=pedido_copia.rua_endereco_ent,
                endereco_ent=pedido_copia.endereco_ent,
                telefone_endereco_ent=pedido_copia.telefone_endereco_ent,
                
                # Auditoria
                created_by=self.usuario,
                updated_by=self.usuario,
                ativo=True
            )
            
            db.session.add(novo_principal)
            logger.info(f"Pedido {pedido_copia.num_pedido}/{pedido_copia.cod_produto} adicionado à CarteiraPrincipal")
            
        except Exception as e:
            logger.error(f"Erro ao adicionar à CarteiraPrincipal: {e}")
            self.avisos.append(f"Pedido importado mas não foi possível adicionar à carteira principal: {str(e)}")
    
    def _verificar_pode_substituir_pedido(self, num_pedido):
        """Verifica se pode substituir um pedido existente"""
        try:
            # Busca separações vinculadas ao pedido
            from app.separacao.models import SeparacaoLote
            separacao = SeparacaoLote.query.filter_by(
                num_pedido=num_pedido,
                pedido='COTADO'  # Separação confirmada
            ).first()
            
            if separacao:
                logger.info(f"Pedido {num_pedido} tem separação cotada - não pode substituir")
                return False
            
            # Pode substituir se não tem separação cotada
            return True
            
        except Exception as e:
            logger.error(f"Erro ao verificar se pode substituir pedido: {e}")
            return False
    
    def _remover_pedidos_antigos(self, num_pedido):
        """Remove pedidos antigos para substituição"""
        try:
            # Remove da CarteiraCopia
            CarteiraCopia.query.filter_by(
                num_pedido=num_pedido
            ).delete()
            
            # Remove da CarteiraPrincipal
            CarteiraPrincipal.query.filter_by(
                num_pedido=num_pedido
            ).delete()
            
            logger.info(f"Pedidos antigos {num_pedido} removidos para substituição")
            
        except Exception as e:
            logger.error(f"Erro ao remover pedidos antigos: {e}")
            raise